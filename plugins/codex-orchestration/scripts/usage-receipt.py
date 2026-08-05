#!/usr/bin/env python3
"""Estimate one Codex Orchestration task's share of the current Codex weekly allowance."""

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

from state_migration import StateMigrationError, migrate_default_state

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
    configured = os.environ.get("CODEX_ORCHESTRATION_USAGE_STATE_DIR")
    if not configured:
        # Compatibility fallback for existing automation; new documentation uses
        # CODEX_ORCHESTRATION_USAGE_STATE_DIR exclusively.
        configured = os.environ.get("SOL_ADVISOR_USAGE_STATE_DIR")
    if configured:
        root = Path(configured).expanduser()
    else:
        try:
            root = migrate_default_state(codex_home()) / "usage"
        except StateMigrationError as exc:
            raise ReceiptUnavailable(str(exc)) from exc
    if not root.is_absolute():
        raise ReceiptUnavailable("usage state directory must be absolute")
    if root.is_symlink():
        raise ReceiptUnavailable("refusing a symlinked usage state directory")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def sessions_root() -> Path:
    configured = os.environ.get("CODEX_ORCHESTRATION_SESSIONS_DIR")
    if not configured:
        # Compatibility fallback for pre-0.7.0 test and automation environments.
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
        PRICING_URL, headers={"User-Agent": "codex-orchestration-usage-receipt/1"}
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


def spawned_thread_ids(path: Path) -> list[str]:
    children: list[str] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"type":"sub_agent_activity"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                child_id = payload.get("agent_thread_id")
                if (
                    event.get("type") == "event_msg"
                    and payload.get("type") == "sub_agent_activity"
                    and payload.get("kind") == "started"
                    and isinstance(child_id, str)
                    and THREAD_RE.fullmatch(child_id)
                    and child_id not in children
                ):
                    children.append(child_id)
    except OSError as exc:
        raise ReceiptUnavailable(f"cannot inspect rollout {path.name}") from exc
    return children


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
) -> tuple[float, float, float]:
    credits = 0.0
    estimated_credits = 0.0
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
        model_context_seen = False
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
                        model_context_seen = True
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
                # Forked rollout files can replay a parent transcript's token events
                # before the child records its own model context. Those events belong
                # to the parent and must not reduce calibration coverage or be counted
                # twice in the child's history.
                if not model_context_seen:
                    continue
                weight = usage["input_tokens"] + usage["output_tokens"]
                total_weight += weight
                if model in pricing["models"]:
                    observed = priced_credits(usage, model, pricing)
                    credits += observed
                    estimated_credits += observed
                    priced_weight += weight
                else:
                    # A transcript with a model context that this release does not
                    # recognize still has exact token counts. Price those tokens at
                    # Sol as a conservative calibration estimate instead of making
                    # the entire task receipt unavailable.
                    estimated_credits += priced_credits(usage, "sol", pricing)
    coverage = priced_weight / total_weight if total_weight else 0.0
    return credits, coverage, estimated_credits


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
    cached_capacity: float | None = None
    if path.exists():
        cached = read_json(path)
        value = cached.get("capacity_credits")
        if (
            cached.get("pricing_date") == pricing.get("checked_date")
            and isinstance(value, (int, float))
            and value > 0
        ):
            cached_capacity = float(value)
        if (
            cached.get("checked_date") == local_date()
            and isinstance(cached.get("resets_at"), int)
            and abs(int(cached["resets_at"]) - resets_at) <= 60
            and cached.get("pricing_date") == pricing.get("checked_date")
        ):
            if cached_capacity is not None:
                return cached_capacity
    window_start = resets_at - window_minutes * 60
    local_credits, coverage, estimated_credits = scan_weekly_local_credits(
        sessions, window_start, pricing
    )
    if estimated_credits <= 0:
        if cached_capacity is not None:
            return cached_capacity
        raise ReceiptUnavailable(
            "local weekly usage is insufficient for a reliable calibration"
        )
    calibration_credits = local_credits if coverage >= 0.95 else estimated_credits
    basis = "observed" if coverage >= 0.95 else "unrecognized-models-priced-as-sol"
    capacity = calibration_credits / (used_percent / 100.0)
    atomic_json(
        path,
        {
            "checked_date": local_date(),
            "pricing_date": pricing.get("checked_date"),
            "resets_at": resets_at,
            "used_percent": used_percent,
            "coverage": coverage,
            "basis": basis,
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
    calibration_reason: str | None = None
    try:
        capacity = weekly_capacity(
            root, sessions, summary["rate_limit"] or {}, pricing
        )
    except ReceiptUnavailable as exc:
        # Task token accounting and official model pricing remain sufficient for a
        # rate-based receipt even when a weekly capacity cannot be calibrated.
        capacity = None
        calibration_reason = str(exc)
    state = {
        "root_thread_id": thread_id,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pricing": pricing,
        "capacity_credits": capacity,
        "calibration_reason": calibration_reason,
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


def recover_turn_usage(
    transcript: Path, turn_id: str
) -> tuple[list[tuple[str, dict[str, int]]], dict[str, Any] | None]:
    """Recover root and delegated usage for one completed or stopping Codex turn."""
    require_thread_id(turn_id)
    if not transcript.is_file() or transcript.is_symlink():
        raise ReceiptUnavailable("the root task transcript is unavailable")

    active = False
    baseline = empty_usage()
    latest_before = empty_usage()
    latest = empty_usage()
    root_model: str | None = None
    rate_limit: dict[str, Any] | None = None
    child_ids: list[str] = []
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                event_type = payload.get("type")
                if event.get("type") == "event_msg" and event_type == "task_started":
                    candidate = payload.get("turn_id")
                    if active and candidate != turn_id:
                        break
                    if candidate == turn_id:
                        active = True
                        baseline = dict(latest_before)
                    continue
                if not active:
                    if event.get("type") == "event_msg" and event_type == "token_count":
                        totals = (payload.get("info") or {}).get("total_token_usage") or {}
                        for key in TOKEN_KEYS:
                            value = totals.get(key)
                            if isinstance(value, (int, float)) and value >= 0:
                                latest_before[key] = int(value)
                    continue
                if event.get("type") == "turn_context" and payload.get("turn_id") == turn_id:
                    candidate = payload.get("model")
                    if isinstance(candidate, str):
                        root_model = candidate
                if event.get("type") == "event_msg" and event_type == "token_count":
                    info = payload.get("info") or {}
                    totals = info.get("total_token_usage") or {}
                    for key in TOKEN_KEYS:
                        value = totals.get(key)
                        if isinstance(value, (int, float)) and value >= 0:
                            latest[key] = int(value)
                    primary = (payload.get("rate_limits") or {}).get("primary")
                    if isinstance(primary, dict):
                        rate_limit = primary
                if event.get("type") == "event_msg" and event_type == "sub_agent_activity":
                    child_id = payload.get("agent_thread_id")
                    if (
                        payload.get("kind") == "started"
                        and isinstance(child_id, str)
                        and THREAD_RE.fullmatch(child_id)
                        and child_id not in child_ids
                    ):
                        child_ids.append(child_id)
                if (
                    event.get("type") == "event_msg"
                    and event_type == "task_complete"
                    and payload.get("turn_id") == turn_id
                ):
                    break
    except OSError as exc:
        raise ReceiptUnavailable("the root task transcript cannot be read") from exc

    if not active:
        raise ReceiptUnavailable("the requested Codex turn is absent from the transcript")
    usages: list[tuple[str, dict[str, int]]] = []
    normalized_root = normalize_model(root_model)
    if normalized_root is None:
        raise ReceiptUnavailable("the root task model is unavailable")
    usages.append((normalized_root, usage_delta(latest, baseline)))

    sessions = sessions_root()
    pending = list(child_ids)
    seen: set[str] = set()
    while pending:
        child_id = pending.pop(0)
        if child_id in seen:
            continue
        seen.add(child_id)
        rollout = find_rollout(sessions, child_id)
        if rollout is None:
            raise ReceiptUnavailable(f"rollout unavailable for delegated thread {child_id}")
        summary = rollout_summary(rollout)
        model = normalize_model(summary["model"])
        if model is None:
            raise ReceiptUnavailable(f"model unavailable for delegated thread {child_id}")
        usages.append((model, summary["totals"]))
        pending.extend(spawned_thread_ids(rollout))
    return usages, rate_limit


def active_turn_id(transcript: Path) -> str | None:
    active: str | None = None
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if event.get("type") != "event_msg":
                    continue
                event_type = payload.get("type")
                candidate = payload.get("turn_id")
                if event_type == "task_started" and isinstance(candidate, str):
                    active = candidate
                elif (
                    event_type in {"task_complete", "turn_aborted"}
                    and candidate == active
                ):
                    active = None
    except OSError:
        return None
    return active if active and THREAD_RE.fullmatch(active) else None


def turn_spawned_thread_ids(transcript: Path, turn_id: str) -> list[str]:
    """Return native descendants started during one exact root turn."""
    active = False
    children: list[str] = []
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                event_type = payload.get("type")
                if event.get("type") == "event_msg" and event_type == "task_started":
                    candidate = payload.get("turn_id")
                    if active and candidate != turn_id:
                        break
                    if candidate == turn_id:
                        active = True
                    continue
                if not active or event.get("type") != "event_msg":
                    continue
                if event_type == "sub_agent_activity" and payload.get("kind") == "started":
                    child_id = payload.get("agent_thread_id")
                    if (
                        isinstance(child_id, str)
                        and THREAD_RE.fullmatch(child_id)
                        and child_id not in children
                    ):
                        children.append(child_id)
                if event_type in {"task_complete", "turn_aborted"} and payload.get(
                    "turn_id"
                ) == turn_id:
                    break
    except OSError as exc:
        raise ReceiptUnavailable("the root task transcript cannot be read") from exc
    sessions = sessions_root()
    pending = list(children)
    visited: set[str] = set()
    while pending:
        child_id = pending.pop(0)
        if child_id in visited:
            continue
        visited.add(child_id)
        rollout = find_rollout(sessions, child_id)
        if rollout is None:
            continue
        for descendant_id in spawned_thread_ids(rollout):
            if descendant_id not in children:
                children.append(descendant_id)
                pending.append(descendant_id)
    return children


def format_percent(value: float) -> str:
    if value <= 0:
        return "0.00%"
    if value < 0.001:
        return "<0.001%"
    if value < 0.01:
        return f"{value:.3f}%"
    return f"{value:.2f}%"


def format_credits(value: float) -> str:
    if value <= 0:
        return "0.000 credits"
    if value < 0.001:
        return "<0.001 credits"
    return f"{value:.3f} credits"


def receipt_lines(
    usages: Iterable[tuple[str, dict[str, int]]],
    pricing: dict[str, Any],
    capacity: float | None,
) -> list[str]:
    actual_credits = 0.0
    all_sol_credits = 0.0
    for model, usage in usages:
        if model not in pricing.get("models", {}):
            raise ReceiptUnavailable(f"pricing unavailable for {model}")
        actual_credits += priced_credits(usage, model, pricing)
        all_sol_credits += priced_credits(usage, "sol", pricing)
    if isinstance(capacity, (int, float)) and capacity > 0:
        actual_percent = actual_credits / capacity * 100.0
        all_sol_percent = all_sol_credits / capacity * 100.0
        savings_percent = max(0.0, all_sol_percent - actual_percent)
        return [
            f"Actual weekly usage: {format_percent(actual_percent)}",
            f"All-Sol equivalent: {format_percent(all_sol_percent)}",
            f"Estimated routing savings: {format_percent(savings_percent)}",
        ]
    savings_percent = (
        max(0.0, (all_sol_credits - actual_credits) / all_sol_credits * 100.0)
        if all_sol_credits > 0
        else 0.0
    )
    return [
        f"Estimated task credits: {format_credits(actual_credits)}",
        f"All-Sol equivalent credits: {format_credits(all_sol_credits)}",
        f"Estimated routing savings: {format_percent(savings_percent)}",
    ]


def token_totals(
    usages: Iterable[tuple[str, dict[str, int]]]
) -> dict[str, Any]:
    totals = empty_usage()
    models: dict[str, int] = {}
    for model, usage in usages:
        for key in TOKEN_KEYS:
            totals[key] += max(0, int(usage.get(key, 0)))
        models[model] = models.get(model, 0) + max(
            0, int(usage.get("input_tokens", 0))
        ) + max(0, int(usage.get("output_tokens", 0)))
    return {
        **totals,
        "total_tokens": totals["input_tokens"] + totals["output_tokens"],
        "models": models,
    }


def command_finish(args: argparse.Namespace) -> None:
    root_thread_id = require_thread_id(
        args.root_thread_id or os.environ.get("CODEX_THREAD_ID")
    )
    root = state_root()
    path = task_path(root, root_thread_id)
    if not path.exists():
        # An early start can fail before it writes state (for example, while weekly
        # calibration is unavailable). Finish must still recover the active turn and
        # emit the official-rate fallback instead of repeating receipt-unavailable.
        transcript = find_rollout(sessions_root(), root_thread_id)
        turn_id = active_turn_id(transcript) if transcript is not None else None
        if transcript is None or turn_id is None:
            raise ReceiptUnavailable("usage receipt was not started and the active turn cannot be recovered")
        usages, rate_limit = recover_turn_usage(transcript, turn_id)
        pricing = current_pricing(root)
        try:
            capacity = weekly_capacity(root, sessions_root(), rate_limit or {}, pricing)
        except ReceiptUnavailable:
            capacity = None
        print("\n".join(receipt_lines(usages, pricing, capacity)))
        return
    state = read_json(path)
    pricing = state.get("pricing")
    capacity = state.get("capacity_credits")
    threads = state.get("threads")
    if (
        not isinstance(pricing, dict)
        or (
            capacity is not None
            and (not isinstance(capacity, (int, float)) or capacity <= 0)
        )
    ):
        raise ReceiptUnavailable("usage receipt calibration is invalid")
    if not isinstance(threads, list) or not threads:
        raise ReceiptUnavailable("usage receipt has no recorded threads")

    # Prefer the transcript's authoritative current-turn lineage over the manually
    # registered list. Native spawn surfaces do not always return a UUID, so a failed
    # add-thread call must not silently turn a routed Terra/Luna task into a Sol-only
    # receipt. Recovery also includes descendants spawned by a delegated executive.
    transcript = find_rollout(sessions_root(), root_thread_id)
    turn_id = active_turn_id(transcript) if transcript is not None else None
    recorded_ids = {
        item.get("thread_id") for item in threads if isinstance(item, dict)
    }
    missing_descendants = (
        set(turn_spawned_thread_ids(transcript, turn_id)) - recorded_ids
        if transcript is not None and turn_id is not None
        else set()
    )
    if transcript is not None and turn_id is not None and missing_descendants:
        try:
            recovered_usages, _ = recover_turn_usage(transcript, turn_id)
        except ReceiptUnavailable:
            # Retain the explicit-registration path for older or incomplete rollout
            # formats. It remains valid when every UUID was recorded successfully.
            recovered_usages = []
        if recovered_usages:
            print("\n".join(receipt_lines(recovered_usages, pricing, capacity)))
            if not args.keep:
                path.unlink(missing_ok=True)
            return

    usages: list[tuple[str, dict[str, int]]] = []
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
        usages.append((model, usage))
    print("\n".join(receipt_lines(usages, pricing, capacity)))
    if not args.keep:
        path.unlink(missing_ok=True)


def command_recover(args: argparse.Namespace) -> None:
    transcript = Path(args.transcript).expanduser()
    usages, rate_limit = recover_turn_usage(transcript, args.turn_id)
    root = state_root()
    sessions = sessions_root()
    pricing = current_pricing(root)
    try:
        capacity = weekly_capacity(root, sessions, rate_limit or {}, pricing)
    except ReceiptUnavailable:
        capacity = None
    print("\n".join(receipt_lines(usages, pricing, capacity)))


def command_recover_tokens(args: argparse.Namespace) -> None:
    transcript = Path(args.transcript).expanduser()
    usages, _ = recover_turn_usage(transcript, args.turn_id)
    print(json.dumps(token_totals(usages), separators=(",", ":"), sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    pricing = commands.add_parser(
        "pricing-check", help="refresh official GPT-5.6 pricing once daily"
    )
    pricing.add_argument("--force", action="store_true")
    pricing.set_defaults(handler=command_pricing_check)
    start = commands.add_parser(
        "start", help="start measuring the current Codex Orchestration task"
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
        "finish", help="print the three-line calibrated or rate-based savings receipt"
    )
    finish.add_argument("--root-thread-id")
    finish.add_argument("--keep", action="store_true")
    finish.set_defaults(handler=command_finish)
    recover = commands.add_parser(
        "recover", help="reconstruct a receipt from a root Codex turn transcript"
    )
    recover.add_argument("--transcript", required=True)
    recover.add_argument("--turn-id", required=True)
    recover.set_defaults(handler=command_recover)
    recover_tokens = commands.add_parser(
        "recover-tokens", help="reconstruct exact root-and-delegated task tokens"
    )
    recover_tokens.add_argument("--transcript", required=True)
    recover_tokens.add_argument("--turn-id", required=True)
    recover_tokens.set_defaults(handler=command_recover_tokens)
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
