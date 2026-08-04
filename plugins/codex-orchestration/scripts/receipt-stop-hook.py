#!/usr/bin/env python3
"""Persist Codex Orchestration complexity and enforce the completed route receipt."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SOL_EXECUTIVE = "Executive design and review: GPT-5.6 Sol / High"
TERRA_EXECUTIVE = "Executive design and review: GPT-5.6 Terra / High"
TERRA_FALLBACK_PREFIX = SOL_EXECUTIVE + " — Terra executive fallback: "
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
    executive = value.get("executive")
    if not isinstance(executive, str) or not valid_executive(score, executive):
        return None
    return value


def write_state(
    path: Path | None,
    *,
    session_id: str,
    turn_id: str,
    score: str,
    implementation: str,
    executive: str,
    executive_spawned: bool = False,
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
                        "executive": executive,
                        "executive_spawned": executive_spawned,
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


def replace_state(path: Path | None, state: dict[str, Any]) -> bool:
    if path is None:
        return False
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        return True
    except OSError:
        return False
    finally:
        if "temporary" in locals():
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


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


def executive_line(text: str) -> str | None:
    matches = re.findall(r"(?m)^Executive design and review: GPT-5\.6[^\r\n]*", text)
    return matches[-1] if matches else None


def valid_executive(score: str, line: str | None) -> bool:
    if line is None:
        return False
    if float(score) < 5.0:
        return line == TERRA_EXECUTIVE or (
            line.startswith(TERRA_FALLBACK_PREFIX)
            and bool(line[len(TERRA_FALLBACK_PREFIX) :].strip())
        )
    return line == SOL_EXECUTIVE


def expected_executive(score: str | None, observed: str | None) -> str:
    if score is not None and float(score) < 5.0:
        if observed and observed.startswith(TERRA_FALLBACK_PREFIX):
            return observed
        return TERRA_EXECUTIVE
    return SOL_EXECUTIVE


def session_role(transcript: Path) -> str | None:
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if event.get("type") == "session_meta":
                    role = payload.get("agent_role")
                    if isinstance(role, str):
                        return role
    except OSError:
        return None
    return None


def allowed_child_role(score: str, agent_type: str) -> bool:
    ladder = [
        "codex_orchestration_luna_implementer",
        "codex_orchestration_terra_medium_implementer",
        "codex_orchestration_terra_implementer",
        "codex_orchestration_sol_medium_implementer",
        "codex_orchestration_sol_high_implementer",
    ]
    start = 0 if float(score) < 3.0 else 1
    return agent_type in ladder[start:]


def receipt_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(\S[^\r\n]*)\s*$", text)
    return match.group(1) if match else None


def recover_task_metrics(transcript: Path, turn_id: str) -> dict[str, Any] | None:
    helper = Path(__file__).with_name("usage-receipt.py")
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(helper),
                "recover-tokens",
                "--transcript",
                str(transcript),
                "--turn-id",
                turn_id,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def turn_was_interrupted(transcript: Path, turn_id: str) -> bool:
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if (
                    event.get("type") == "event_msg"
                    and payload.get("type") == "turn_aborted"
                    and payload.get("turn_id") == turn_id
                ):
                    return True
    except OSError:
        return False
    return False


def record_completion(
    *,
    session_id: str,
    turn_id: str,
    score: str,
    implementation: str,
    final_message: str,
    elapsed_seconds: int,
    delegated_starts: int,
    task_metrics: dict[str, Any] | None,
    transcript: Path,
) -> None:
    values = [receipt_value(final_message, label) for label in RECEIPT_LABELS]
    if any(value is None for value in values):
        return
    tracker = Path(__file__).with_name("effectiveness-tracker.py")
    try:
        subprocess.run(
            [
                sys.executable,
                str(tracker),
                "record-turn",
                "--session-id",
                session_id,
                "--turn-id",
                turn_id,
                "--complexity",
                score,
                "--implementation",
                implementation,
                "--actual-weekly-usage",
                values[0],
                "--all-sol-equivalent",
                values[1],
                "--estimated-routing-savings",
                values[2],
                "--elapsed-seconds",
                str(elapsed_seconds),
                "--delegated-starts",
                str(delegated_starts),
                "--task-metrics-json",
                json.dumps(task_metrics or {}, separators=(",", ":")),
                "--transcript-path",
                str(transcript),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        # Effectiveness tracking must never hold a completed user task open.
        return


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


def turn_metrics(transcript: Path, turn_id: str) -> tuple[int, int]:
    active = False
    started_at: dt.datetime | None = None
    children: set[str] = set()
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
                    timestamp = event.get("timestamp")
                    if isinstance(timestamp, str):
                        try:
                            started_at = dt.datetime.fromisoformat(
                                timestamp.replace("Z", "+00:00")
                            )
                        except ValueError:
                            started_at = None
                continue
            if not active:
                continue
            if (
                event.get("type") == "event_msg"
                and payload.get("type") == "sub_agent_activity"
            ):
                child_id = payload.get("agent_thread_id")
                if payload.get("kind") == "started" and isinstance(child_id, str):
                    children.add(child_id)
            if (
                event.get("type") == "event_msg"
                and payload.get("type") == "task_complete"
                and payload.get("turn_id") == turn_id
            ):
                break
    elapsed = 0
    if started_at is not None:
        now = dt.datetime.now(dt.timezone.utc)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=dt.timezone.utc)
        elapsed = max(0, round((now - started_at).total_seconds()))
    return elapsed, len(children)


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
    transcript = Path(transcript_value)
    try:
        current_text = turn_text(transcript, turn_id)
    except OSError:
        emit({})
        return 0
    tool_input = hook_input.get("tool_input")
    agent_type = tool_input.get("agent_type") if isinstance(tool_input, dict) else None
    sol_agent_call = isinstance(agent_type, str) and agent_type.startswith("codex_orchestration_")
    routed = executive_line(current_text) is not None and "Implementation: GPT-5.6" in current_text
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
                        "Codex Orchestration complexity gate: announce the exact one-decimal "
                        "`Complexity: x.x/10` line with the route before starting any "
                        "implementation or worker. Then retry this tool call."
                    ),
                }
            }
        )
        return 0
    observed_executive = executive_line(current_text)
    if not valid_executive(score, observed_executive):
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Codex Orchestration executive gate: scores below 5.0 require "
                        f"`{TERRA_EXECUTIVE}`; scores 5.0 and above require "
                        f"`{SOL_EXECUTIVE}`. A low-band upward fallback must use "
                        f"`{TERRA_FALLBACK_PREFIX}<current-turn verified reason>`."
                    ),
                }
            }
        )
        return 0
    persisted = read_state(route_state)
    role = session_role(transcript)
    if persisted is not None:
        if persisted.get("score") != score:
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration complexity gate: the persisted score is immutable."}})
            return 0
        prior_executive = persisted.get("executive")
        if float(score) < 5.0:
            transition_valid = (
                prior_executive == TERRA_EXECUTIVE
                and (
                    observed_executive == TERRA_EXECUTIVE
                    or (observed_executive or "").startswith(TERRA_FALLBACK_PREFIX)
                )
            ) or (
                isinstance(prior_executive, str)
                and prior_executive.startswith(TERRA_FALLBACK_PREFIX)
                and observed_executive == prior_executive
            )
        else:
            transition_valid = prior_executive == SOL_EXECUTIVE and observed_executive == SOL_EXECUTIVE
        if not transition_valid:
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate: the executive route cannot move downward or change after fallback."}})
            return 0
        if observed_executive != prior_executive:
            persisted["executive"] = observed_executive
            if not replace_state(route_state, persisted):
                emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate could not persist the verified transition."}})
                return 0
    elif not write_state(
        route_state,
        session_id=session_id,
        turn_id=turn_id,
        score=score,
        implementation=implementation_line(current_text),
        executive=observed_executive or "",
    ):
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Codex Orchestration complexity gate could not persist the exact route "
                        "score, so implementation cannot start."
                    ),
                }
            }
        )
        return 0
    persisted = read_state(route_state)
    if sol_agent_call and persisted is not None:
        if role == "codex_orchestration_terra_executive":
            if not allowed_child_role(score, agent_type):
                emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate: the Terra executive may spawn only the score-mapped producer or an upward producer fallback."}})
                return 0
        elif float(score) < 5.0:
            if str(persisted.get("executive", "")).startswith(TERRA_FALLBACK_PREFIX):
                if not allowed_child_role(score, agent_type):
                    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate: fallback root Sol may spawn only the score-mapped producer or an upward producer fallback."}})
                    return 0
            elif not persisted.get("executive_spawned"):
                if agent_type != "codex_orchestration_terra_executive":
                    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate: the first low-band root role must be codex_orchestration_terra_executive."}})
                    return 0
                persisted["executive_spawned"] = True
                if not replace_state(route_state, persisted):
                    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate could not persist the root executive spawn."}})
                    return 0
            else:
                emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Codex Orchestration executive gate: low-band producer descendants belong to the Terra executive session."}})
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
    if session_role(transcript) == "codex_orchestration_terra_executive":
        emit({"continue": True})
        return 0
    try:
        current_text = turn_text(transcript, turn_id)
    except OSError:
        emit({"continue": True})
        return 0
    routed = executive_line(current_text) is not None and "Implementation: GPT-5.6" in current_text
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
            executive=executive_line(current_text) or "",
        )
        persisted = read_state(route_state)
    exact_score = persisted.get("score") if persisted else None
    observed_executive = executive_line(current_text)
    persisted_executive = persisted.get("executive") if persisted else None
    final_score = normalized_complexity(last_message)
    complexity_present = exact_score is not None and final_score == exact_score
    receipt_present = all(label in last_message for label in RECEIPT_LABELS)
    executive_present = (
        exact_score is not None
        and isinstance(persisted_executive, str)
        and executive_line(last_message) == persisted_executive
    )
    if complexity_present and receipt_present and executive_present:
        if turn_was_interrupted(transcript, turn_id):
            emit({"continue": True})
            return 0
        elapsed_seconds, delegated_starts = turn_metrics(transcript, turn_id)
        task_metrics = recover_task_metrics(transcript, turn_id)
        record_completion(
            session_id=session_id,
            turn_id=turn_id,
            score=exact_score,
            implementation=implementation_line(current_text),
            final_message=last_message,
            elapsed_seconds=elapsed_seconds,
            delegated_starts=delegated_starts,
            task_metrics=task_metrics,
            transcript=transcript,
        )
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
        [expected_executive(exact_score, persisted_executive or observed_executive), implementation, complexity, receipt_text]
    )
    reason = (
        "Codex Orchestration completion gate: revise the final answer without removing its task result, "
        "and end with this footer. If the complexity placeholder appears, announce the exact "
        "route score and retry one tool call so the gate can persist it. Do not finish until "
        "the persisted numeric complexity and savings "
        f"receipt are visible.\n\n{footer}"
    )
    emit({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
