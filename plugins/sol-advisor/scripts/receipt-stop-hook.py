#!/usr/bin/env python3
"""Persist Sol Advisor complexity and enforce the completed route receipt."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROUTE_EXECUTIVE = "Executive design and review: GPT-5.6 Sol / High"
RECEIPT_LABELS = (
    "Actual weekly usage:",
    "All-Sol equivalent:",
    "Estimated routing savings:",
)
ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
COMPLEXITY_RE = re.compile(r"(?m)^Complexity: ((?:10|[1-9])\.\d)/10\s*$")


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":")))


def state_path(session_id: str, turn_id: str) -> Path | None:
    plugin_data = os.environ.get("PLUGIN_DATA")
    if (
        not plugin_data
        or not ID_RE.fullmatch(session_id)
        or not ID_RE.fullmatch(turn_id)
    ):
        return None
    root = Path(plugin_data) / "route-scores"
    if root.is_symlink():
        return None
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
    except OSError:
        return None
    return root / f"{session_id}-{turn_id}.json"


def read_state(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    score = value.get("score")
    if not isinstance(score, str) or not re.fullmatch(r"(?:10\.0|[1-9]\.\d)", score):
        return None
    return value


def write_state(
    path: Path | None,
    *,
    session_id: str,
    turn_id: str,
    score: str,
    implementation: str,
) -> bool:
    if path is None:
        return False
    current = read_state(path)
    if current is not None:
        return current.get("score") == score
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
    except OSError:
        return False
    try:
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "session_id": session_id,
                        "turn_id": turn_id,
                        "score": score,
                        "implementation": implementation,
                    },
                    handle,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                handle.write("\n")
            os.chmod(temporary, 0o600)
            # Link a complete temporary file into place without overwriting an
            # already-persisted score from a concurrent tool call.
            try:
                os.link(temporary, path)
            except FileExistsError:
                current = read_state(path)
                return current is not None and current.get("score") == score
        except OSError:
            return False
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return True


def normalized_complexity(text: str) -> str | None:
    matches = COMPLEXITY_RE.findall(text)
    if not matches:
        return None
    # The route announcement owns the score. Later repeated footer lines must never
    # replace it, so transcript recovery deliberately takes the first exact score.
    value = matches[0]
    if float(value) > 10.0:
        return None
    return value


def implementation_line(text: str) -> str:
    matches = re.findall(r"(?m)^Implementation: GPT-5\.6[^\r\n]*", text)
    return matches[-1] if matches else "Implementation: <actual routed model / effort>"


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


def pre_tool_gate(hook_input: dict[str, Any]) -> int:
    transcript_value = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id")
    turn_id = hook_input.get("turn_id")
    if not all(isinstance(item, str) for item in (transcript_value, session_id, turn_id)):
        emit({})
        return 0
    route_state = state_path(session_id, turn_id)
    if read_state(route_state) is not None:
        emit({})
        return 0
    transcript = Path(transcript_value)
    try:
        current_text = turn_text(transcript, turn_id)
    except OSError:
        emit({})
        return 0
    tool_input = hook_input.get("tool_input")
    agent_type = tool_input.get("agent_type") if isinstance(tool_input, dict) else None
    sol_agent_call = isinstance(agent_type, str) and agent_type.startswith("sol_advisor_")
    routed = ROUTE_EXECUTIVE in current_text and "Implementation: GPT-5.6" in current_text
    if not routed and not sol_agent_call:
        emit({})
        return 0
    score = normalized_complexity(current_text)
    if score is None:
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Sol Advisor complexity gate: announce the exact one-decimal "
                        "`Complexity: x.x/10` line with the route before starting any "
                        "implementation or worker. Then retry this tool call."
                    ),
                }
            }
        )
        return 0
    if not write_state(
        route_state,
        session_id=session_id,
        turn_id=turn_id,
        score=score,
        implementation=implementation_line(current_text),
    ):
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Sol Advisor complexity gate could not persist the exact route "
                        "score, so implementation cannot start."
                    ),
                }
            }
        )
        return 0
    emit({})
    return 0


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        emit({"continue": True})
        return 0
    if hook_input.get("hook_event_name") == "PreToolUse":
        return pre_tool_gate(hook_input)
    transcript_value = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id")
    turn_id = hook_input.get("turn_id")
    last_message = hook_input.get("last_assistant_message") or ""
    if not all(isinstance(item, str) for item in (transcript_value, session_id, turn_id)):
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
    route_state = state_path(session_id, turn_id)
    persisted = read_state(route_state)
    transcript_score = normalized_complexity(current_text)
    if persisted is None and transcript_score is not None:
        write_state(
            route_state,
            session_id=session_id,
            turn_id=turn_id,
            score=transcript_score,
            implementation=implementation_line(current_text),
        )
        persisted = read_state(route_state)
    exact_score = persisted.get("score") if persisted else None
    final_score = normalized_complexity(last_message)
    complexity_present = exact_score is not None and final_score == exact_score
    receipt_present = all(label in last_message for label in RECEIPT_LABELS)
    if complexity_present and receipt_present:
        emit({"continue": True})
        return 0

    receipt, recovery_error = recover_receipt(transcript, turn_id)
    # The score is immutable once work starts, but the implementation lane can move
    # upward after a live availability failure. Always report the latest observed lane.
    implementation = implementation_line(current_text)
    complexity = (
        f"Complexity: {exact_score}/10"
        if exact_score is not None
        else "Complexity: <announce and persist the exact one-decimal route score>/10"
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
        "and end with this footer. If the complexity placeholder appears, announce the exact "
        "route score and retry one tool call so the gate can persist it. Do not finish until "
        "the persisted numeric complexity and savings "
        f"receipt are visible.\n\n{footer}"
    )
    emit({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
