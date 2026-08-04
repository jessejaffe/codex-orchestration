#!/usr/bin/env python3
"""Keep routed Sol Advisor turns open until their final receipt is present."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROUTE_EXECUTIVE = "Executive design and review: GPT-5.6 Sol / High"
RECEIPT_LABELS = (
    "Actual weekly usage:",
    "All-Sol equivalent:",
    "Estimated routing savings:",
)


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":")))


def turn_text(transcript: Path, turn_id: str) -> str:
    active = False
    messages: list[str] = []
    with transcript.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload") or {}
            if event.get("type") == "event_msg" and payload.get("type") == "task_started":
                candidate = payload.get("turn_id")
                if active and candidate != turn_id:
                    break
                if candidate == turn_id:
                    active = True
                continue
            if not active:
                continue
            if event.get("type") == "response_item" and payload.get("type") == "message":
                for item in payload.get("content") or []:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        messages.append(item["text"])
            elif event.get("type") == "event_msg" and payload.get("type") == "agent_message":
                message = payload.get("message")
                if isinstance(message, str):
                    messages.append(message)
            if (
                event.get("type") == "event_msg"
                and payload.get("type") == "task_complete"
                and payload.get("turn_id") == turn_id
            ):
                break
    return "\n".join(messages)


def recover_receipt(transcript: Path, turn_id: str) -> tuple[list[str], str | None]:
    helper = Path(__file__).with_name("usage-receipt.py")
    completed = subprocess.run(
        [
            sys.executable,
            str(helper),
            "recover",
            "--transcript",
            str(transcript),
            "--turn-id",
            turn_id,
        ],
        capture_output=True,
        text=True,
        timeout=25,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode == 0 and all(
        any(line.startswith(label) for line in lines) for label in RECEIPT_LABELS
    ):
        return lines, None
    reason = completed.stderr.strip() or "receipt recovery produced no measurement"
    return [], reason


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        emit({"continue": True})
        return 0
    transcript_value = hook_input.get("transcript_path")
    turn_id = hook_input.get("turn_id")
    last_message = hook_input.get("last_assistant_message") or ""
    if not isinstance(transcript_value, str) or not isinstance(turn_id, str):
        emit({"continue": True})
        return 0
    transcript = Path(transcript_value)
    try:
        current_text = turn_text(transcript, turn_id)
    except OSError:
        emit({"continue": True})
        return 0
    routed = ROUTE_EXECUTIVE in current_text and "Implementation: GPT-5.6" in current_text
    if not routed:
        emit({"continue": True})
        return 0
    complexity_present = bool(re.search(r"(?m)^Complexity: \d+(?:\.\d+)?/10\s*$", last_message))
    receipt_present = all(label in last_message for label in RECEIPT_LABELS)
    if complexity_present and receipt_present:
        emit({"continue": True})
        return 0

    receipt, recovery_error = recover_receipt(transcript, turn_id)
    implementation_matches = re.findall(
        r"(?m)^Implementation: GPT-5\.6[^\r\n]*", current_text
    )
    implementation = implementation_matches[-1] if implementation_matches else "Implementation: <actual routed model / effort>"
    complexity_matches = re.findall(
        r"(?m)^Complexity: (\d+(?:\.\d+)?)/10\s*$", current_text
    )
    complexity = (
        f"Complexity: {float(complexity_matches[-1]):.1f}/10"
        if complexity_matches
        else "Complexity: <repeat the exact one-decimal score assigned before routing>/10"
    )
    if recovery_error:
        receipt_text = f"Savings receipt unavailable: {recovery_error}"
    else:
        receipt_text = "\n".join(receipt)
    footer = "\n".join(
        [ROUTE_EXECUTIVE, implementation, complexity, receipt_text]
    )
    reason = (
        "Sol Advisor completion gate: revise the final answer without removing its task result, "
        "and end with this footer. Replace any angle-bracketed complexity placeholder with the "
        "exact score already assigned. Do not finish until the numeric complexity and savings "
        f"receipt are visible.\n\n{footer}"
    )
    emit({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
