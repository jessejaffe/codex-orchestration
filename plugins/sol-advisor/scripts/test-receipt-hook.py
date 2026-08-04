#!/usr/bin/env python3
"""Hermetic recovery and Stop-hook regression test."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events)
    )


def token_event(total: int, *, with_meter: bool = False) -> dict:
    payload = {
        "type": "token_count",
        "info": {
            "total_token_usage": {
                "input_tokens": total,
                "cached_input_tokens": 0,
                "output_tokens": 0,
            }
        },
    }
    if with_meter:
        payload["rate_limits"] = {
            "primary": {
                "used_percent": 50.0,
                "window_minutes": 10080,
                "resets_at": 2_000_000_000,
            }
        }
    return {"type": "event_msg", "payload": payload}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-receipt-hook.py <plugin-dir> <temp-dir>")
    plugin_dir = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    sessions = temporary / "sessions"
    state = temporary / "state"
    state.mkdir(parents=True)
    root_id = "11111111-1111-1111-1111-111111111111"
    turn_id = "22222222-2222-2222-2222-222222222222"
    child_id = "33333333-3333-3333-3333-333333333333"
    root_rollout = sessions / f"rollout-{root_id}.jsonl"
    child_rollout = sessions / f"rollout-{child_id}.jsonl"
    route = (
        "Executive design and review: GPT-5.6 Sol / High\n"
        "Implementation: GPT-5.6 Terra / Medium\n"
        "Complexity: 4.2/10"
    )
    write_jsonl(
        root_rollout,
        [
            token_event(100),
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": turn_id},
            },
            {
                "type": "turn_context",
                "payload": {"turn_id": turn_id, "model": "gpt-5.6-sol"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "content": [{"type": "output_text", "text": route}],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "kind": "started",
                    "agent_thread_id": child_id,
                },
            },
            token_event(200, with_meter=True),
        ],
    )
    write_jsonl(
        child_rollout,
        [
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-terra"},
            },
            token_event(50),
        ],
    )
    today = dt.datetime.now().astimezone().date().isoformat()
    pricing = {
        "checked_date": today,
        "source": "fixture",
        "models": {
            name: {"input": rate, "cached_input": rate, "output": rate}
            for name, rate in (("sol", 10.0), ("terra", 1.0), ("luna", 0.5))
        },
    }
    (state / "pricing.json").write_text(json.dumps(pricing) + "\n")
    (state / "weekly-calibration.json").write_text(
        json.dumps(
            {
                "checked_date": today,
                "pricing_date": today,
                "resets_at": 2_000_000_000,
                "used_percent": 50.0,
                "coverage": 1.0,
                "capacity_credits": 0.01,
            }
        )
        + "\n"
    )
    environment = os.environ.copy()
    environment["SOL_ADVISOR_USAGE_STATE_DIR"] = str(state)
    environment["SOL_ADVISOR_SESSIONS_DIR"] = str(sessions)
    receipt_helper = plugin_dir / "scripts" / "usage-receipt.py"
    receipt = subprocess.run(
        [
            sys.executable,
            str(receipt_helper),
            "recover",
            "--transcript",
            str(root_rollout),
            "--turn-id",
            turn_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()
    expected = (
        "Actual weekly usage: 10.50%\n"
        "All-Sol equivalent: 15.00%\n"
        "Estimated routing savings: 4.50%"
    )
    if receipt != expected:
        raise AssertionError(f"unexpected recovered receipt: {receipt!r}")

    hook = plugin_dir / "scripts" / "receipt-stop-hook.py"
    hook_input = {
        "transcript_path": str(root_rollout),
        "turn_id": turn_id,
        "last_assistant_message": route,
        "stop_hook_active": False,
    }
    blocked = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(hook_input),
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    blocked_output = json.loads(blocked.stdout)
    if blocked_output.get("decision") != "block" or expected not in blocked_output.get(
        "reason", ""
    ):
        raise AssertionError(f"hook did not enforce the receipt: {blocked_output!r}")

    hook_input["last_assistant_message"] = route + "\n" + expected
    allowed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(hook_input),
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    if json.loads(allowed.stdout) != {"continue": True}:
        raise AssertionError(f"hook rejected a complete receipt: {allowed.stdout!r}")
    print("receipt recovery and Stop-hook gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
