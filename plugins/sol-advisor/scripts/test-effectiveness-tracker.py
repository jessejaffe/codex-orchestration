#!/usr/bin/env python3
"""Hermetic effectiveness baseline, completion-ledger, and comparison test."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


def run(*arguments: str) -> str:
    completed = subprocess.run(
        [sys.executable, *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def fixture(path: Path, lifetime: int) -> None:
    today = dt.datetime.now().astimezone().date()
    buckets = [
        {
            "startDate": (today - dt.timedelta(days=offset)).isoformat(),
            "tokens": offset * 10,
        }
        for offset in range(8, -1, -1)
    ]
    path.write_text(
        json.dumps(
            {
                "summary": {
                    "lifetimeTokens": lifetime,
                    "peakDailyTokens": 80,
                    "longestRunningTurnSec": 60,
                    "currentStreakDays": 9,
                    "longestStreakDays": 9,
                },
                "dailyUsageBuckets": buckets,
            }
        )
        + "\n"
    )


def transcript(path: Path, turn_id: str, terminal_type: str) -> None:
    path.write_text(
        json.dumps(
            {
                "type": "event_msg",
                "payload": {"type": terminal_type, "turn_id": turn_id},
            },
            separators=(",", ":"),
        )
        + "\n"
    )


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-effectiveness-tracker.py <plugin-dir> <temp-dir>")
    plugin = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    temporary.mkdir(parents=True, exist_ok=True)
    state = temporary / "state"
    first = temporary / "first.json"
    second = temporary / "second.json"
    fixture(first, 1_000)
    fixture(second, 1_600)
    tracker = plugin / "scripts" / "effectiveness-tracker.py"
    common = [str(tracker), "--state-dir", str(state)]
    baseline = run(
        *common,
        "--usage-file",
        str(first),
        "baseline",
    )
    if "Exact lifetime tokens: 1,000" not in baseline:
        raise AssertionError(f"baseline calculation is wrong: {baseline!r}")
    session_id = "11111111-1111-1111-1111-111111111111"
    turn_ids = [
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    ]
    for turn_id in turn_ids:
        transcript_path = temporary / f"{turn_id}.jsonl"
        transcript(transcript_path, turn_id, "task_complete")
        recorded = run(
            *common,
            "record-turn",
            "--session-id",
            session_id,
            "--turn-id",
            turn_id,
            "--complexity",
            "4.2",
            "--implementation",
            "Implementation: GPT-5.6 Terra / Medium",
            "--actual-weekly-usage",
            "0.20%",
            "--all-sol-equivalent",
            "0.30%",
            "--estimated-routing-savings",
            "0.10%",
            "--elapsed-seconds",
            "60",
            "--delegated-starts",
            "2",
            "--task-metrics-json",
            json.dumps(
                {
                    "input_tokens": 800,
                    "cached_input_tokens": 600,
                    "output_tokens": 200,
                    "total_tokens": 1_000,
                    "models": {"terra": 1_000},
                },
                separators=(",", ":"),
            ),
            "--transcript-path",
            str(transcript_path),
        )
        if "effectiveness-completion-recorded" not in recorded:
            raise AssertionError(f"completion was not recorded: {recorded!r}")
    duplicate = run(
        *common,
        "record-turn",
        "--session-id",
        session_id,
        "--turn-id",
        turn_ids[0],
        "--complexity",
        "4.2",
        "--implementation",
        "Implementation: GPT-5.6 Terra / Medium",
        "--actual-weekly-usage",
        "0.20%",
        "--all-sol-equivalent",
        "0.30%",
        "--estimated-routing-savings",
        "0.10%",
        "--elapsed-seconds",
        "60",
        "--delegated-starts",
        "2",
        "--task-metrics-json",
        json.dumps(
            {
                "input_tokens": 800,
                "cached_input_tokens": 600,
                "output_tokens": 200,
                "total_tokens": 1_000,
                "models": {"terra": 1_000},
            },
            separators=(",", ":"),
        ),
        "--transcript-path",
        str(temporary / f"{turn_ids[0]}.jsonl"),
    )
    if "effectiveness-completion-already-recorded" not in duplicate:
        raise AssertionError(f"duplicate completion was not idempotent: {duplicate!r}")
    interrupted_turn = "44444444-4444-4444-4444-444444444444"
    interrupted_transcript = temporary / f"{interrupted_turn}.jsonl"
    transcript(interrupted_transcript, interrupted_turn, "turn_aborted")
    interrupted = run(
        *common,
        "record-turn",
        "--session-id",
        session_id,
        "--turn-id",
        interrupted_turn,
        "--complexity",
        "4.2",
        "--implementation",
        "Implementation: GPT-5.6 Terra / Medium",
        "--actual-weekly-usage",
        "0.20%",
        "--all-sol-equivalent",
        "0.30%",
        "--estimated-routing-savings",
        "0.10%",
        "--elapsed-seconds",
        "60",
        "--delegated-starts",
        "2",
        "--task-metrics-json",
        '{"input_tokens":800,"cached_input_tokens":600,"output_tokens":200}',
        "--transcript-path",
        str(interrupted_transcript),
    )
    if "effectiveness-completion-recorded" not in interrupted:
        raise AssertionError(f"interruption race fixture was not recorded: {interrupted!r}")
    comparison = run(
        *common,
        "--usage-file",
        str(second),
        "compare",
    )
    expected = (
        "Completed Sol Advisor tasks: 2",
        "Exact recorded task tokens: 2,000",
        "Average tokens per completed Sol Advisor task: 1,000",
        "Task input tokens: 1,600",
        "Task cached input tokens: 1,200",
        "Task output tokens: 400",
        "Exact task-token coverage: 2/2 tasks",
        "Average completed-task duration: 1m 0s",
        "Delegated starts per completed task: 2.00",
        "Direct routed usage (summed receipts): 0.400% of weekly capacity",
        "All-Sol same-token counterfactual: 0.600% of weekly capacity",
        "Estimated direct routing savings: 0.200 percentage points",
        "Exact receipt aggregation coverage: 2/2 tasks",
        "Interrupted or redirected tasks excluded: 1",
        "Account-wide token change (background): 600",
    )
    for line in expected:
        if line not in comparison:
            raise AssertionError(f"comparison omitted {line!r}: {comparison!r}")
    report = run(*common, "report")
    if "Completed Sol Advisor tasks: 2" not in report:
        raise AssertionError(f"stored report is wrong: {report!r}")
    completions = list((state / "effectiveness" / "completions").glob("*.json"))
    if len(completions) != 3:
        raise AssertionError(f"completion ledger is not idempotent: {completions!r}")
    print("effectiveness baseline, ledger, and comparison passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
