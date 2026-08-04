#!/usr/bin/env python3
"""Estimate one Sol Advisor task's share of the current Codex weekly allowance."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PRICING_URL = "https://learn.chatgpt.com/docs/pricing.md"
THREAD_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
MODEL_NAMES = ("Sol", "Terra", "Luna")
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens")


class ReceiptUnavailable(RuntimeError):
    pass


def local_date() -> str:
    return dt.datetime.now().astimezone().date().isoformat()


def parse_timestamp(value: str) -> float:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def require_thread_id(value: str | None) -> str:
    if not value or not THREAD_RE.fullmatch(value):
        raise ReceiptUnavailable("a valid Codex thread ID is unavailable")
    return value


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    home = os.environ.get("HOME")
    if not home:
        raise ReceiptUnavailable("HOME and CODEX_HOME are unset")
    return Path(home) / ".codex"


def state_root() -> Path:
    configured = os.environ.get("SOL_ADVISOR_USAGE_STATE_DIR")
    root = (
        Path(configured).expanduser()
        if configured
        else codex_home() / "state" / "sol-advisor" / "usage"
    )
    if not root.is_absolute():
        raise ReceiptUnavailable("usage state directory must be absolute")
    if root.is_symlink():
        raise ReceiptUnavailable("refusing a symlinked usage state directory")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def sessions_root() -> Path:
    configured = os.environ.get("SOL_ADVISOR_SESSIONS_DIR")
    root = Path(configured).expanduser() if configured else codex_home() / "sessions"
    if not root.is_dir():
        raise ReceiptUnavailable("Codex session history is unavailable")
    return root


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ReceiptUnavailable(f"refusing symlinked state file: {path.name}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ReceiptUnavailable(f"refusing symlinked state file: {path.name}")
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptUnavailable(f"cannot read {path.name}") from exc
    if not isinstance(value, dict):
        raise ReceiptUnavailable(f"invalid state in {path.name}")
    return value


def fetch_pricing() -> dict[str, Any]:
    request = urllib.request.Request(
        PRICING_URL, headers={"User-Agent": "sol-advisor-usage-receipt/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            page = response.read().decode("utf-8")
    except (OSError, UnicodeError):
        try:
            fetched = subprocess.run(
                ["curl", "-fsSL", "--max-time", "15", PRICING_URL],
                check=True,
                capture_output=True,
                text=True,
            )
            page = fetched.stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ReceiptUnavailable(
                "official Codex pricing could not be checked"
            ) from exc
    rates: dict[str, dict[str, float]] = {}
    for name in MODEL_NAMES:
        pattern = re.compile(
            rf"<td>GPT-5\.6 {name}</td>\s*"
            rf"<td[^>]*>([0-9.]+) credits</td>\s*"
            rf"<td[^>]*>([0-9.]+) credits</td>\s*"
            rf"<td[^>]*>([0-9.]+) credits</td>",
            re.MULTILINE,
        )
        matches = pattern.findall(page)
        if len(matches) != 1:
            raise ReceiptUnavailable(
                f"official GPT-5.6 {name} pricing was not uniquely identifiable"
            )
        input_rate, cached_rate, output_rate = (float(item) for item in matches[0])
        rates[name.lower()] = {
            "input": input_rate,
            "cached_input": cached_rate,
            "output": output_rate,
        }
    return {"checked_date": local_date(), "source": PRICING_URL, "models": rates}


def current_pricing(root: Path, force: bool = False) -> dict[str, Any]:
    path = root / "pricing.json"
    if not force and path.exists():
        cached = read_json(path)
        if cached.get("checked_date") == local_date() and isinstance(
            cached.get("models"), dict
        ):
            return cached
    pricing = fetch_pricing()
    atomic_json(path, pricing)
    return pricing


def rollout_files(root: Path) -> Iterable[Path]:
    return root.rglob("*.jsonl")


def find_rollout(root: Path, thread_id: str) -> Path | None:
    direct = list(root.rglob(f"*{thread_id}.jsonl"))
    if direct:
        return max(direct, key=lambda item: item.stat().st_mtime)
    marker = f'"id":"{thread_id}"'
    session_marker = f'"session_id":"{thread_id}"'
    for path in rollout_files(root):
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for _ in range(8):
                    line = handle.readline()
                    if not line:
                        break
                    if marker in line or session_marker in line:
                        return path
        except OSError:
            continue
    return None


def empty_usage() -> dict[str, int]:
    return {key: 0 for key in TOKEN_KEYS}


def relevant_event(line: str) -> bool:
    return '"type":"turn_context"' in line or (
        '"type":"event_msg"' in line and '"type":"token_count"' in line
    )


def rollout_summary(path: Path) -> dict[str, Any]:
    model: str | None = None
    totals = empty_usage()
    rate_limit: dict[str, Any] | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not relevant_event(line):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "turn_context":
                    candidate = event.get("payload", {}).get("model")
                    if isinstance(candidate, str):
                        model = candidate
                    continue
                payload = event.get("payload", {})
                if (
                    event.get("type") != "event_msg"
                    or payload.get("type") != "token_count"
                ):
                    continue
                info = payload.get("info") or {}
                candidate_totals = info.get("total_token_usage") or {}
                for key in TOKEN_KEYS:
                    value = candidate_totals.get(key)
                    if isinstance(value, (int, float)) and value >= 0:
                        totals[key] = int(value)
                primary = (payload.get("rate_limits") or {}).get("primary")
                if isinstance(primary, dict):
                    rate_limit = primary
    except OSError as exc:
        raise ReceiptUnavailable(f"cannot inspect rollout {path.name}") from exc
    return {"model": model, "totals": totals, "rate_limit": rate_limit}


def normalize_model(model: str | None) -> str | None:
    lowered = (model or "").lower()
    for name in ("sol", "terra", "luna"):
        if re.search(rf"(^|[-_/]){name}($|[-_/])", lowered):
            return name
    return None


def priced_credits(usage: dict[str, int], model: str, pricing: dict[str, Any]) -> float:
    rates = pricing["models"][model]
    cached = max(0, usage["cached_input_tokens"])
    uncached = max(0, usage["input_tokens"] - cached)
    output = max(0, usage["output_tokens"])
    return (
        uncached * float(rates["input"])
        + cached * float(rates["cached_input"])
        + output * float(rates["output"])
    ) / 1_000_000


def scan_weekly_local_credits(
    sessions: Path, window_start: float, pricing: dict[str, Any]
) -> tuple[float, float]:
    credits = 0.0
    priced_weight = 0
    total_weight = 0
    for path in rollout_files(sessions):
        try:
            if path.stat().st_mtime < window_start:
                continue
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        model: str | None = None
        with handle:
            for line in handle:
                if not relevant_event(line):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "turn_context":
                    candidate = event.get("payload", {}).get("model")
                    if isinstance(candidate, str):
                        model = normalize_model(candidate)
                    continue
                payload = event.get("payload", {})
                if (
                    event.get("type") != "event_msg"
                    or payload.get("type") != "token_count"
                ):
                    continue
                try:
                    if parse_timestamp(str(event.get("timestamp", ""))) < window_start:
                        continue
                except (TypeError, ValueError):
                    continue
                last = (payload.get("info") or {}).get("last_token_usage") or {}
                usage = {key: max(0, int(last.get(key, 0))) for key in TOKEN_KEYS}
                weight = usage["input_tokens"] + usage["output_tokens"]
                total_weight += weight
                if model in pricing["models"]:
                    credits += priced_credits(usage, model, pricing)
                    priced_weight += weight
    coverage = priced_weight / total_weight if total_weight else 0.0
    return credits, coverage


def weekly_capacity(
    root: Path,
    sessions: Path,
    rate_limit: dict[str, Any],
    pricing: dict[str, Any],
) -> float:
    try:
        used_percent = float(rate_limit["used_percent"])
        window_minutes = int(rate_limit["window_minutes"])
        resets_at = int(rate_limit["resets_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReceiptUnavailable("the weekly Codex usage meter is unavailable") from exc
    if used_percent <= 0 or window_minutes <= 0 or resets_at <= 0:
        raise ReceiptUnavailable(
            "the weekly Codex usage meter cannot calibrate a receipt yet"
        )
    path = root / "weekly-calibration.json"
    if path.exists():
        cached = read_json(path)
        if (
            cached.get("checked_date") == local_date()
            and cached.get("resets_at") == resets_at
            and cached.get("pricing_date") == pricing.get("checked_date")
        ):
            value = cached.get("capacity_credits")
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
    window_start = resets_at - window_minutes * 60
    local_credits, coverage = scan_weekly_local_credits(sessions, window_start, pricing)
    if local_credits <= 0 or coverage < 0.95:
        raise ReceiptUnavailable(
            "local weekly usage is insufficient for a reliable calibration"
        )
    capacity = local_credits / (used_percent / 100.0)
    atomic_json(
        path,
        {
            "checked_date": local_date(),
            "pricing_date": pricing.get("checked_date"),
            "resets_at": resets_at,
            "used_percent": used_percent,
            "coverage": coverage,
            "capacity_credits": capacity,
        },
    )
    return capacity


def task_path(root: Path, thread_id: str) -> Path:
    tasks = root / "tasks"
    if tasks.is_symlink():
        raise ReceiptUnavailable("refusing a symlinked task-state directory")
    tasks.mkdir(exist_ok=True, mode=0o700)
    os.chmod(tasks, 0o700)
    return tasks / f"{thread_id}.json"


def command_pricing_check(args: argparse.Namespace) -> None:
    pricing = current_pricing(state_root(), force=args.force)
    print(f"STATUS: pricing-current ({pricing['checked_date']})")


def command_start(args: argparse.Namespace) -> None:
    thread_id = require_thread_id(args.thread_id or os.environ.get("CODEX_THREAD_ID"))
    root = state_root()
    sessions = sessions_root()
    pricing = current_pricing(root)
    rollout = find_rollout(sessions, thread_id)
    if rollout is None:
        raise ReceiptUnavailable("the primary rollout is unavailable")
    summary = rollout_summary(rollout)
    if summary["rate_limit"] is None:
        raise ReceiptUnavailable("the weekly Codex usage meter is unavailable")
    capacity = weekly_capacity(root, sessions, summary["rate_limit"], pricing)
    state = {
        "root_thread_id": thread_id,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pricing": pricing,
        "capacity_credits": capacity,
        "threads": [
            {
                "thread_id": thread_id,
                "baseline": summary["totals"],
                "model": summary["model"],
            }
        ],
    }
    atomic_json(task_path(root, thread_id), state)
    print("STATUS: usage-receipt-started")


def load_task(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    thread_id = require_thread_id(
        args.root_thread_id or os.environ.get("CODEX_THREAD_ID")
    )
    path = task_path(state_root(), thread_id)
    if not path.exists():
        raise ReceiptUnavailable("usage receipt was not started for this task")
    return path, read_json(path)


def command_add_thread(args: argparse.Namespace) -> None:
    path, state = load_task(args)
    child_id = require_thread_id(args.child_thread_id)
    threads = state.get("threads")
    if not isinstance(threads, list):
        raise ReceiptUnavailable("invalid task thread state")
    if any(
        item.get("thread_id") == child_id for item in threads if isinstance(item, dict)
    ):
        print("STATUS: thread-already-recorded")
        return
    rollout = find_rollout(sessions_root(), child_id)
    model = rollout_summary(rollout)["model"] if rollout else None
    threads.append({"thread_id": child_id, "baseline": empty_usage(), "model": model})
    atomic_json(path, state)
    print("STATUS: usage-thread-recorded")


def usage_delta(end: dict[str, int], baseline: dict[str, Any]) -> dict[str, int]:
    return {
        key: max(0, int(end.get(key, 0)) - int(baseline.get(key, 0)))
        for key in TOKEN_KEYS
    }


def format_percent(value: float) -> str:
    if value <= 0:
        return "0.00%"
    if value < 0.001:
        return "<0.001%"
    if value < 0.01:
        return f"{value:.3f}%"
    return f"{value:.2f}%"


def command_finish(args: argparse.Namespace) -> None:
    path, state = load_task(args)
    pricing = state.get("pricing")
    capacity = state.get("capacity_credits")
    threads = state.get("threads")
    if (
        not isinstance(pricing, dict)
        or not isinstance(capacity, (int, float))
        or capacity <= 0
    ):
        raise ReceiptUnavailable("usage receipt calibration is invalid")
    if not isinstance(threads, list) or not threads:
        raise ReceiptUnavailable("usage receipt has no recorded threads")
    actual_credits = 0.0
    all_sol_credits = 0.0
    sessions = sessions_root()
    for item in threads:
        if not isinstance(item, dict):
            raise ReceiptUnavailable("usage receipt thread state is invalid")
        thread_id = require_thread_id(item.get("thread_id"))
        rollout = find_rollout(sessions, thread_id)
        if rollout is None:
            raise ReceiptUnavailable(
                f"rollout unavailable for recorded thread {thread_id}"
            )
        summary = rollout_summary(rollout)
        usage = usage_delta(summary["totals"], item.get("baseline") or {})
        model = normalize_model(summary["model"] or item.get("model"))
        if model not in pricing.get("models", {}):
            raise ReceiptUnavailable(
                f"pricing unavailable for recorded thread {thread_id}"
            )
        actual_credits += priced_credits(usage, model, pricing)
        all_sol_credits += priced_credits(usage, "sol", pricing)
    actual_percent = actual_credits / float(capacity) * 100.0
    all_sol_percent = all_sol_credits / float(capacity) * 100.0
    savings_percent = max(0.0, all_sol_percent - actual_percent)
    print(f"Actual weekly usage: {format_percent(actual_percent)}")
    print(f"All-Sol equivalent: {format_percent(all_sol_percent)}")
    print(f"Estimated routing savings: {format_percent(savings_percent)}")
    if not args.keep:
        path.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    pricing = commands.add_parser(
        "pricing-check", help="refresh official GPT-5.6 pricing once daily"
    )
    pricing.add_argument("--force", action="store_true")
    pricing.set_defaults(handler=command_pricing_check)
    start = commands.add_parser(
        "start", help="start measuring the current Sol Advisor task"
    )
    start.add_argument("--thread-id")
    start.set_defaults(handler=command_start)
    add_thread = commands.add_parser(
        "add-thread", help="include a delegated Codex thread"
    )
    add_thread.add_argument("child_thread_id")
    add_thread.add_argument("--root-thread-id")
    add_thread.set_defaults(handler=command_add_thread)
    finish = commands.add_parser(
        "finish", help="print the three-line weekly savings receipt"
    )
    finish.add_argument("--root-thread-id")
    finish.add_argument("--keep", action="store_true")
    finish.set_defaults(handler=command_finish)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except ReceiptUnavailable as exc:
        print(f"STATUS: receipt-unavailable — {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
