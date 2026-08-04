#!/usr/bin/env python3
"""Track Sol Advisor account usage and terminally completed routed tasks over time."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import re
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

THREAD_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
SCORE_RE = re.compile(r"^(?:10|[1-9])\.\d$")


class TrackerUnavailable(RuntimeError):
    pass


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    home = os.environ.get("HOME")
    if not home:
        raise TrackerUnavailable("HOME and CODEX_HOME are unset")
    return Path(home) / ".codex"


def state_root(configured: str | None = None) -> Path:
    environment = os.environ.get("SOL_ADVISOR_USAGE_STATE_DIR")
    root = (
        Path(configured).expanduser()
        if configured
        else Path(environment).expanduser()
        if environment
        else codex_home() / "state" / "sol-advisor" / "usage"
    )
    if not root.is_absolute():
        raise TrackerUnavailable("tracker state directory must be absolute")
    if root.is_symlink():
        raise TrackerUnavailable("refusing a symlinked tracker state directory")
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
    except OSError as exc:
        raise TrackerUnavailable("tracker state directory is unavailable") from exc
    effectiveness = root / "effectiveness"
    if effectiveness.is_symlink():
        raise TrackerUnavailable("refusing a symlinked effectiveness directory")
    try:
        effectiveness.mkdir(exist_ok=True, mode=0o700)
        os.chmod(effectiveness, 0o700)
    except OSError as exc:
        raise TrackerUnavailable("effectiveness state directory is unavailable") from exc
    return effectiveness


def atomic_json(path: Path, value: dict[str, Any], *, replace: bool = True) -> bool:
    if path.is_symlink():
        raise TrackerUnavailable(f"refusing symlinked state file: {path.name}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        if replace:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                return False
    except OSError as exc:
        raise TrackerUnavailable(f"cannot write {path.name}") from exc
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return True


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise TrackerUnavailable(f"cannot read {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrackerUnavailable(f"cannot read {path.name}") from exc
    if not isinstance(value, dict):
        raise TrackerUnavailable(f"invalid state in {path.name}")
    return value


def send_message(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if process.stdin is None:
        raise TrackerUnavailable("Codex account connection has no input stream")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def wait_for_response(
    messages: queue.Queue[dict[str, Any]], request_id: int, timeout: float
) -> dict[str, Any]:
    deadline = dt.datetime.now().timestamp() + timeout
    while True:
        remaining = deadline - dt.datetime.now().timestamp()
        if remaining <= 0:
            raise TrackerUnavailable("Codex account usage request timed out")
        try:
            message = messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TrackerUnavailable("Codex account usage request timed out") from exc
        if message.get("id") == request_id:
            return message


def account_usage(codex_bin: str) -> dict[str, Any]:
    try:
        process = subprocess.Popen(
            [codex_bin, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        raise TrackerUnavailable("Codex app server is unavailable") from exc
    messages: queue.Queue[dict[str, Any]] = queue.Queue()

    def read_output() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                messages.put(message)

    threading.Thread(target=read_output, daemon=True).start()
    try:
        send_message(
            process,
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "sol_advisor_effectiveness_tracker",
                        "title": "Sol Advisor Effectiveness Tracker",
                        "version": "1.0.0",
                    }
                },
            },
        )
        initialized = wait_for_response(messages, 1, 15)
        if initialized.get("error"):
            raise TrackerUnavailable("Codex account connection was rejected")
        send_message(process, {"method": "initialized", "params": {}})
        send_message(process, {"method": "account/usage/read", "id": 2})
        response = wait_for_response(messages, 2, 15)
        if response.get("error"):
            raise TrackerUnavailable("Codex account token activity is unavailable")
        result = response.get("result")
        if not isinstance(result, dict):
            raise TrackerUnavailable("Codex account token activity is invalid")
        return validate_usage(result)
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def validate_usage(value: dict[str, Any]) -> dict[str, Any]:
    if "result" in value and isinstance(value.get("result"), dict):
        value = value["result"]
    summary = value.get("summary")
    buckets = value.get("dailyUsageBuckets")
    if not isinstance(summary, dict):
        raise TrackerUnavailable("account usage summary is unavailable")
    lifetime = summary.get("lifetimeTokens")
    if not isinstance(lifetime, int) or lifetime < 0:
        raise TrackerUnavailable("exact lifetime token total is unavailable")
    if buckets is not None and not isinstance(buckets, list):
        raise TrackerUnavailable("daily token activity is invalid")
    return {"summary": summary, "dailyUsageBuckets": buckets or []}


def usage_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.usage_file:
        return validate_usage(read_json(Path(args.usage_file).expanduser()))
    return account_usage(args.codex_bin)


def exact_percent(value: Any) -> float | None:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)%", str(value))
    return float(match.group(1)) if match else None


def transcript_terminal_status(value: dict[str, Any]) -> str:
    """Return completed, interrupted, or pending from Codex's terminal turn event."""
    transcript_value = value.get("transcript_path")
    turn_id = value.get("turn_id")
    if not isinstance(transcript_value, str) or not isinstance(turn_id, str):
        return "pending"
    transcript = Path(transcript_value)
    if not transcript.is_absolute() or not transcript.is_file() or transcript.is_symlink():
        return "pending"
    completed = False
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if event.get("type") != "event_msg" or payload.get("turn_id") != turn_id:
                    continue
                if payload.get("type") == "turn_aborted":
                    return "interrupted"
                if payload.get("type") == "task_complete":
                    completed = True
    except OSError:
        return "pending"
    return "completed" if completed else "pending"


def completion_metrics(root: Path) -> dict[str, int | float]:
    directory = root / "completions"
    if not directory.is_dir() or directory.is_symlink():
        return {
            "count": 0,
            "elapsed_seconds": 0,
            "delegated_starts": 0,
            "exact_receipts": 0,
            "actual_percent": 0.0,
            "all_sol_percent": 0.0,
            "savings_percent": 0.0,
            "task_token_records": 0,
            "task_input_tokens": 0,
            "task_cached_input_tokens": 0,
            "task_output_tokens": 0,
            "task_tokens": 0,
            "completion_candidates": 0,
            "interrupted_tasks": 0,
            "pending_tasks": 0,
        }
    result: dict[str, int | float] = {
        "count": 0,
        "elapsed_seconds": 0,
        "delegated_starts": 0,
        "exact_receipts": 0,
        "actual_percent": 0.0,
        "all_sol_percent": 0.0,
        "savings_percent": 0.0,
        "task_token_records": 0,
        "task_input_tokens": 0,
        "task_cached_input_tokens": 0,
        "task_output_tokens": 0,
        "task_tokens": 0,
        "completion_candidates": 0,
        "interrupted_tasks": 0,
        "pending_tasks": 0,
    }
    for path in directory.glob("*.json"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            value = read_json(path)
            elapsed = max(0, int(value.get("elapsed_seconds", 0)))
            delegated = max(0, int(value.get("delegated_starts", 0)))
        except (TrackerUnavailable, TypeError, ValueError):
            continue
        result["completion_candidates"] += 1
        terminal_status = transcript_terminal_status(value)
        if terminal_status == "interrupted":
            result["interrupted_tasks"] += 1
            continue
        if terminal_status != "completed":
            result["pending_tasks"] += 1
            continue
        result["count"] += 1
        result["elapsed_seconds"] += elapsed
        result["delegated_starts"] += delegated
        receipt = (
            exact_percent(value.get("actual_weekly_usage")),
            exact_percent(value.get("all_sol_equivalent")),
            exact_percent(value.get("estimated_routing_savings")),
        )
        if all(item is not None for item in receipt):
            result["exact_receipts"] += 1
            result["actual_percent"] += float(receipt[0])
            result["all_sol_percent"] += float(receipt[1])
            result["savings_percent"] += float(receipt[2])
        task = value.get("task_metrics")
        if isinstance(task, dict):
            try:
                task_input = max(0, int(task["input_tokens"]))
                task_cached = max(0, int(task["cached_input_tokens"]))
                task_output = max(0, int(task["output_tokens"]))
            except (KeyError, TypeError, ValueError):
                continue
            if task_cached <= task_input:
                result["task_token_records"] += 1
                result["task_input_tokens"] += task_input
                result["task_cached_input_tokens"] += task_cached
                result["task_output_tokens"] += task_output
                result["task_tokens"] += task_input + task_output
    return result


def capture_snapshot(
    args: argparse.Namespace, *, label: str, profile_total_chats: int | None
) -> dict[str, Any]:
    if profile_total_chats is not None and profile_total_chats < 1:
        raise TrackerUnavailable("Profile Total chats must be a positive integer")
    root = state_root(args.state_dir)
    now = dt.datetime.now(dt.timezone.utc)
    snapshot = {
        "recorded_at": now.isoformat(),
        "local_date": dt.datetime.now().astimezone().date().isoformat(),
        "label": label,
        "profile_total_chats": profile_total_chats,
        "account_usage": usage_from_args(args),
        "sol_advisor_completion_metrics": completion_metrics(root),
    }
    snapshots = root / "snapshots"
    if snapshots.is_symlink():
        raise TrackerUnavailable("refusing a symlinked snapshots directory")
    snapshots.mkdir(exist_ok=True, mode=0o700)
    os.chmod(snapshots, 0o700)
    name = now.strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    atomic_json(snapshots / name, snapshot, replace=False)
    return snapshot


def lifetime_tokens(snapshot: dict[str, Any]) -> int:
    return int(snapshot["account_usage"]["summary"]["lifetimeTokens"])


def preceding_full_days(snapshot: dict[str, Any], count: int = 7) -> list[dict[str, Any]]:
    local_day = dt.date.fromisoformat(str(snapshot["local_date"]))
    valid: list[dict[str, Any]] = []
    for item in snapshot["account_usage"].get("dailyUsageBuckets") or []:
        if not isinstance(item, dict):
            continue
        try:
            day = dt.date.fromisoformat(str(item.get("startDate")))
            tokens = int(item.get("tokens"))
        except (TypeError, ValueError):
            continue
        if day < local_day and tokens >= 0:
            valid.append({"startDate": day.isoformat(), "tokens": tokens})
    return sorted(valid, key=lambda item: item["startDate"])[-count:]


def integer(value: float | int) -> str:
    return f"{round(value):,}"


def percent_change(current: float, baseline: float) -> str:
    if baseline <= 0:
        return "n/a"
    change = (current / baseline - 1.0) * 100.0
    return f"{change:+.1f}%"


def print_baseline(snapshot: dict[str, Any]) -> None:
    tokens = lifetime_tokens(snapshot)
    days = preceding_full_days(snapshot)
    prior_tokens = sum(int(item["tokens"]) for item in days)
    print(f"Baseline recorded: {snapshot['recorded_at']}")
    print(f"Exact lifetime tokens: {tokens:,}")
    if days:
        print(f"Previous {len(days)} full days: {prior_tokens:,} tokens")
        print(f"Previous daily average: {integer(prior_tokens / len(days))} tokens")
    metrics = snapshot["sol_advisor_completion_metrics"]
    print(f"Logged Sol Advisor completions: {metrics['count']:,}")
    if snapshot.get("profile_total_chats") is not None:
        print(f"Optional Profile chat context: {snapshot['profile_total_chats']:,}")


def duration(seconds: float) -> str:
    rounded = max(0, round(seconds))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_report(baseline: dict[str, Any], latest: dict[str, Any]) -> None:
    start_tokens = lifetime_tokens(baseline)
    end_tokens = lifetime_tokens(latest)
    token_delta = end_tokens - start_tokens
    start_metrics = baseline["sol_advisor_completion_metrics"]
    end_metrics = latest["sol_advisor_completion_metrics"]
    completion_delta = int(end_metrics["count"]) - int(start_metrics["count"])
    elapsed_delta = int(end_metrics["elapsed_seconds"]) - int(
        start_metrics["elapsed_seconds"]
    )
    delegated_delta = int(end_metrics["delegated_starts"]) - int(
        start_metrics["delegated_starts"]
    )
    exact_receipt_delta = int(end_metrics["exact_receipts"]) - int(
        start_metrics["exact_receipts"]
    )
    actual_percent_delta = float(end_metrics["actual_percent"]) - float(
        start_metrics["actual_percent"]
    )
    all_sol_percent_delta = float(end_metrics["all_sol_percent"]) - float(
        start_metrics["all_sol_percent"]
    )
    savings_percent_delta = float(end_metrics["savings_percent"]) - float(
        start_metrics["savings_percent"]
    )
    task_token_record_delta = int(end_metrics["task_token_records"]) - int(
        start_metrics["task_token_records"]
    )
    task_input_delta = int(end_metrics["task_input_tokens"]) - int(
        start_metrics["task_input_tokens"]
    )
    task_cached_delta = int(end_metrics["task_cached_input_tokens"]) - int(
        start_metrics["task_cached_input_tokens"]
    )
    task_output_delta = int(end_metrics["task_output_tokens"]) - int(
        start_metrics["task_output_tokens"]
    )
    task_token_delta = int(end_metrics["task_tokens"]) - int(
        start_metrics["task_tokens"]
    )
    start_time = dt.datetime.fromisoformat(str(baseline["recorded_at"]))
    end_time = dt.datetime.fromisoformat(str(latest["recorded_at"]))
    elapsed_days = max((end_time - start_time).total_seconds() / 86400.0, 0.0)
    print(f"Experiment window: {elapsed_days:.2f} days")
    print(f"Completed Sol Advisor tasks: {completion_delta:,}")
    if task_token_record_delta > 0:
        print(f"Exact recorded task tokens: {task_token_delta:,}")
        print(
            "Average tokens per completed Sol Advisor task: "
            f"{integer(task_token_delta / task_token_record_delta)}"
        )
        print(f"Task input tokens: {task_input_delta:,}")
        print(f"Task cached input tokens: {task_cached_delta:,}")
        print(f"Task output tokens: {task_output_delta:,}")
    else:
        print("Average tokens per completed Sol Advisor task: n/a")
    print(
        "Exact task-token coverage: "
        f"{task_token_record_delta}/{completion_delta} tasks"
        if completion_delta > 0
        else "Exact task-token coverage: 0/0 tasks"
    )
    if completion_delta > 0:
        print(
            "Average completed-task duration: "
            f"{duration(elapsed_delta / completion_delta)}"
        )
        print(
            "Delegated starts per completed task: "
            f"{delegated_delta / completion_delta:.2f}"
        )
        print(
            "Direct routed usage (summed receipts): "
            f"{actual_percent_delta:.3f}% of weekly capacity"
        )
        print(
            "All-Sol same-token counterfactual: "
            f"{all_sol_percent_delta:.3f}% of weekly capacity"
        )
        print(
            "Estimated direct routing savings: "
            f"{savings_percent_delta:.3f} percentage points"
        )
        print(
            "Exact receipt aggregation coverage: "
            f"{exact_receipt_delta}/{completion_delta} tasks"
        )
    else:
        print("Average completed-task duration: n/a")
    interrupted_delta = int(end_metrics.get("interrupted_tasks", 0)) - int(
        start_metrics.get("interrupted_tasks", 0)
    )
    pending_delta = int(end_metrics.get("pending_tasks", 0)) - int(
        start_metrics.get("pending_tasks", 0)
    )
    print(f"Interrupted or redirected tasks excluded: {max(0, interrupted_delta):,}")
    if pending_delta > 0:
        print(f"Awaiting authoritative completion signal: {pending_delta:,}")
    print(f"Account-wide token change (background): {token_delta:,}")
    start_chats = baseline.get("profile_total_chats")
    end_chats = latest.get("profile_total_chats")
    if isinstance(start_chats, int) and isinstance(end_chats, int):
        print(f"Optional new-chat context: {end_chats - start_chats:,}")
    prior_days = preceding_full_days(baseline)
    prior_daily = (
        sum(int(item["tokens"]) for item in prior_days) / len(prior_days)
        if prior_days
        else 0.0
    )
    if elapsed_days > 0:
        experiment_daily = token_delta / elapsed_days
        print(f"Experiment daily token pace: {integer(experiment_daily)}")
        if prior_daily > 0:
            print(
                "Versus previous full-day token pace: "
                f"{percent_change(experiment_daily, prior_daily)}"
            )


def command_baseline(args: argparse.Namespace) -> None:
    root = state_root(args.state_dir)
    baseline_path = root / "baseline.json"
    if baseline_path.exists() and not args.replace:
        raise TrackerUnavailable("a baseline already exists; use --replace intentionally")
    snapshot = capture_snapshot(
        args, label=args.label, profile_total_chats=args.total_chats
    )
    atomic_json(baseline_path, snapshot)
    print_baseline(snapshot)


def command_compare(args: argparse.Namespace) -> None:
    root = state_root(args.state_dir)
    baseline = read_json(root / "baseline.json")
    latest = capture_snapshot(
        args, label=args.label, profile_total_chats=args.total_chats
    )
    print_report(baseline, latest)


def latest_snapshot(root: Path) -> dict[str, Any]:
    directory = root / "snapshots"
    if not directory.is_dir() or directory.is_symlink():
        raise TrackerUnavailable("no effectiveness snapshots are available")
    paths = [path for path in directory.glob("*.json") if path.is_file() and not path.is_symlink()]
    if not paths:
        raise TrackerUnavailable("no effectiveness snapshots are available")
    return read_json(max(paths, key=lambda path: path.name))


def command_report(args: argparse.Namespace) -> None:
    root = state_root(args.state_dir)
    baseline = read_json(root / "baseline.json")
    latest = latest_snapshot(root)
    if latest.get("recorded_at") == baseline.get("recorded_at"):
        print_baseline(baseline)
        print("Comparison status: waiting for a later snapshot")
        return
    print_report(baseline, latest)


def command_record_turn(args: argparse.Namespace) -> None:
    if not THREAD_RE.fullmatch(args.session_id) or not THREAD_RE.fullmatch(args.turn_id):
        raise TrackerUnavailable("valid session and turn IDs are required")
    if not SCORE_RE.fullmatch(args.complexity):
        raise TrackerUnavailable("an exact one-decimal complexity score is required")
    try:
        task_metrics = json.loads(args.task_metrics_json)
    except json.JSONDecodeError as exc:
        raise TrackerUnavailable("task token metrics are invalid") from exc
    if not isinstance(task_metrics, dict):
        raise TrackerUnavailable("task token metrics are invalid")
    transcript = Path(args.transcript_path).expanduser()
    if not transcript.is_absolute() or not transcript.is_file() or transcript.is_symlink():
        raise TrackerUnavailable("an absolute regular transcript path is required")
    root = state_root(args.state_dir)
    completions = root / "completions"
    if completions.is_symlink():
        raise TrackerUnavailable("refusing a symlinked completions directory")
    completions.mkdir(exist_ok=True, mode=0o700)
    os.chmod(completions, 0o700)
    path = completions / f"{args.session_id}-{args.turn_id}.json"
    value = {
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "session_id": args.session_id,
        "turn_id": args.turn_id,
        "complexity": args.complexity,
        "implementation": args.implementation,
        "actual_weekly_usage": args.actual_weekly_usage,
        "all_sol_equivalent": args.all_sol_equivalent,
        "estimated_routing_savings": args.estimated_routing_savings,
        "elapsed_seconds": args.elapsed_seconds,
        "delegated_starts": args.delegated_starts,
        "task_metrics": task_metrics,
        "transcript_path": str(transcript),
    }
    if atomic_json(path, value, replace=False):
        print("STATUS: effectiveness-completion-recorded")
    else:
        print("STATUS: effectiveness-completion-already-recorded")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--state-dir")
    result.add_argument("--usage-file", help=argparse.SUPPRESS)
    result.add_argument("--codex-bin", default=os.environ.get("SOL_ADVISOR_CODEX_BIN", "codex"))
    commands = result.add_subparsers(dest="command", required=True)
    baseline = commands.add_parser("baseline", help="record the experiment baseline")
    baseline.add_argument("--total-chats", type=int)
    baseline.add_argument("--label", default="baseline")
    baseline.add_argument("--replace", action="store_true")
    baseline.set_defaults(handler=command_baseline)
    compare = commands.add_parser("compare", help="capture now and compare with baseline")
    compare.add_argument("--total-chats", type=int)
    compare.add_argument("--label", default="comparison")
    compare.set_defaults(handler=command_compare)
    report = commands.add_parser("report", help="report the latest stored comparison")
    report.set_defaults(handler=command_report)
    record = commands.add_parser("record-turn", help=argparse.SUPPRESS)
    record.add_argument("--session-id", required=True)
    record.add_argument("--turn-id", required=True)
    record.add_argument("--complexity", required=True)
    record.add_argument("--implementation", required=True)
    record.add_argument("--actual-weekly-usage", required=True)
    record.add_argument("--all-sol-equivalent", required=True)
    record.add_argument("--estimated-routing-savings", required=True)
    record.add_argument("--elapsed-seconds", required=True, type=int)
    record.add_argument("--delegated-starts", required=True, type=int)
    record.add_argument("--task-metrics-json", required=True)
    record.add_argument("--transcript-path", required=True)
    record.set_defaults(handler=command_record_turn)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except TrackerUnavailable as exc:
        print(f"STATUS: effectiveness-unavailable — {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
