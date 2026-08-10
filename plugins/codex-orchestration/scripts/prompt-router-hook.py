#!/usr/bin/env python3
"""Inject the fast chat-local Terra dispatch contract once per user prompt."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from orchestration_state import is_active, transcript_role, write_state


ON_COMMANDS = {
    "turn orchestration on",
    "use orchestration",
    "use orchestration for this chat",
}
OFF_COMMANDS = {"orchestration off", "turn orchestration off"}
CONTROL_COMMANDS = tuple(
    sorted(
        [(command, True) for command in ON_COMMANDS]
        + [(command, False) for command in OFF_COMMANDS],
        key=lambda item: len(item[0]),
        reverse=True,
    )
)
CONTROL_SEPARATORS = " \t,;:.!?\u2013\u2014-"
WORK_CONNECTORS = ("and", "then", "to")
POLITE_CONTROL_PREFIX = re.compile(
    r"^(?:(?:okay|ok|alright|all right|now|please|then|so)\s*[,;:]?\s+)*"
    r"(?:(?:can|could|would|will)\s+you(?:\s+please)?\s+|"
    r"i\s+(?:want|need)\s+you\s+to\s+|go\s+ahead\s+and\s+|let['’]s\s+)?$"
)
INLINE_CONTROL_BOUNDARY = re.compile(r"(?:\band|\bthen|[,;:–—-])\s*$")
MAX_FORK_TURNS = 64
MAX_PRIOR_ACCEPTANCE_CHARS = 4_096
MODEL_LABELS = {
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna",
}
EFFORT_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "xhigh": "Extra High",
    "max": "Max",
    "ultra": "Ultra",
}

DISPATCH_CONTEXT = """Orchestration ON.
Root is a zero-judgment relay and alone calls agent-control tools. Never classify, implement,
correct, or judge acceptance yourself. On steering, drain only this request's Orchestration
children. Unfinished inherited work remains active unless explicitly cancelled or replaced; an
interrupted turn stops execution, not its objective.

Full-context fork: `__FORK_TURNS__`; never use literal `all`.
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__

First spawn `codex_orchestration_terra_grader` with `fork_turns: "__FORK_TURNS__"`, task name
`terra_max_grader_<objective_slug>`, and this exact message shape:
`GRADE_AND_DISPATCH
PRIOR_ACTIVE_ACCEPTANCE: <exact value above>
USER_REQUEST: <verbatim current user prompt>`.

Before showing status or spawning work, validate exactly four protocol lines:
`ORCHESTRATION_RELATION`, `ORCHESTRATION_ROUTE`, `ORCHESTRATION_STATUS`, and
`ORCHESTRATION_ACCEPTANCE`. With prior `NONE`, relation must be `NEW` unless a valid explicit
`CANCEL`; with prior present it must be `AMEND` unless `REPLACE` or `CANCEL` includes an exact,
nonempty current-request `EXPLICIT_SIGNAL`. `<turn_aborted>` is never a signal. `AMEND` requires
`REMOVED=NONE` and must preserve prior outcome, action mode, prohibitions, destinations, and proof.

For non-CANCEL work, validate the route exactly:
- READ_ONLY -> terra_read_only, supervisor NONE, checkpoints NONE.
- SMALL_TWEAK -> luna_implementer, terra_supervisor, RELEASE_CANDIDATE.
- BIG_TWEAK -> terra_implementer, terra_supervisor, ROOT_CAUSE,RELEASE_CANDIDATE.
- SMALL_BUILD -> terra_implementer, sol_high_supervisor, DESIGN,RELEASE_CANDIDATE.
- BIG_BUILD -> sol_high_implementer, sol_xhigh_supervisor,
  ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE.
Names use the exact `codex_orchestration_` prefix. Complexity must be one decimal from 1.0 to 10.0
but never changes the class or route. On any violation, use `followup_task` once on the same grader
with `PROTOCOL_REPAIR: <named violation>; return all four corrected lines` plus the exact prior,
grader output, and user request. If still invalid, stop with a protocol error.

For `CANCEL`, require class READ_ONLY, complexity 1.0, and `NONE` for implementer,
implementation task, supervisor, supervisor task, and checkpoints; do not apply the normal
READ_ONLY worker mapping.

After validation, show Terra's exact `ORCHESTRATION_STATUS:` in commentary. Keep relation, route,
and acceptance internal and immutable. For `CANCEL`, drain children and finish without another
spawn.

For `READ_ONLY`, spawn only the exact implementer/task from the route with
`fork_turns: "__FORK_TURNS__"`. Send `READ_ONLY_WORK` plus the verbatim user request and all four
immutable Terra lines. Wait for it and return its answer. Never commit, push, or deploy read-only
work.

For every change class, start the implementer first with `fork_turns: "__FORK_TURNS__"` and the
exact `IMPLEMENTATION_TASK`. Send `IMPLEMENTATION_START` plus the verbatim user request and all four
immutable Terra lines. Immediately after `spawn_agent` returns, before waiting or doing any other
work, start the exact supervisor with the same `fork_turns: "__FORK_TURNS__"` and exact
`SUPERVISOR_TASK`. Send `SUPERVISOR_INIT` plus the verbatim user request and all four immutable
Terra lines. This concurrent ordering is mandatory: implementer first, supervisor second, then
wait. Never replace either instance during the objective.

The supervisor's initial turn must return `SUPERVISOR_READY` without tools or worktree inspection.
The implementer returns one `IMPLEMENTATION_CHECKPOINT` at a quiescent state with no edit, test,
build, deploy, or migration process running. Require route checkpoints in order. Once both the
supervisor is ready and the checkpoint exists, send the same supervisor:
`CHECKPOINT_REVIEW:` plus the exact immutable lines and exact checkpoint. It may now inspect actual
state read-only because the implementer is paused.

Relay the supervisor decision verbatim to the same implementer:
- `SUPERVISOR_CONTINUE`: advance to the named checkpoint.
- `SUPERVISOR_CORRECT`: the same implementer performs every correction and repeats that checkpoint.
- `SUPERVISOR_READY_TO_RELEASE`: the same implementer alone commits, pushes, deploys, probes, and
  returns `IMPLEMENTATION_RESULT`.
- `SUPERVISOR_BLOCKED`: stop and report the exact blocker and evidence.
Root never edits, corrects, commits, pushes, deploys, or substitutes another implementer.

After `IMPLEMENTATION_RESULT`, send the same supervisor `FINAL_REVIEW:` plus the four immutable
lines and exact result. On `SUPERVISOR_CORRECT`, relay it to the same implementer, which corrects
the work and returns a new `RELEASE_CANDIDATE` checkpoint; repeat checkpoint review, release, and
final review with the same two instances. On `ORCHESTRATION_ROOT_VERIFY`, root performs only the
exact bounded experience check with root-only Browser or visual tools, then returns
`ROOT_VERIFICATION_RESULT:` with named START, ACTION, RESULT, and ARTIFACTS to the same supervisor.
Only `ORCHESTRATION_ACCEPT` completes the routed objective.

Every routed final appends exactly:
`Work class: <immutable class>`
`Supervisor route: <GPT-5.6 Terra / Max, GPT-5.6 Sol / High, GPT-5.6 Sol / Extra High, or NONE>`
`Implementation route: <GPT-5.6 Terra / Max, GPT-5.6 Luna / Max, or GPT-5.6 Sol / High>`
`Complexity telemetry: <immutable one-decimal>/10`
`Current root route: __ROOT_ROUTE__`
The root appends these lines; agents do not. Before acceptance, root never performs task work or
independent judgment."""


def agent_message_text(event: dict[str, Any]) -> str:
    """Return trusted child-to-root text, excluding user and list-agents payloads."""
    if event.get("type") != "response_item":
        return ""
    payload = event.get("payload") or {}
    if payload.get("type") != "agent_message":
        return ""
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    values: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        value = item.get("text")
        if isinstance(value, str):
            values.append(value)
    return "\n".join(values)


def transcript_context(transcript_value: Any) -> tuple[str, str, str]:
    """Return bounded fork, root route, and latest unfinished acceptance in one pass."""
    if not isinstance(transcript_value, str):
        return "none", "unavailable", "NONE"
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return "none", "unavailable", "NONE"
    contexts = starts = 0
    root_route = "unavailable"
    prior_acceptance: str | None = None
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "turn_context":
                    contexts += 1
                    payload = event.get("payload") or {}
                    model = payload.get("model")
                    effort = payload.get("effort")
                    if isinstance(model, str) and isinstance(effort, str):
                        root_route = (
                            f"{MODEL_LABELS.get(model, model)} / "
                            f"{EFFORT_LABELS.get(effort, effort)}"
                        )
                payload = event.get("payload") or {}
                if event.get("type") == "event_msg" and payload.get("type") == "task_started":
                    starts += 1
                message = agent_message_text(event)
                cancelled = False
                for message_line in message.splitlines():
                    if message_line.startswith(
                        "ORCHESTRATION_RELATION: RELATION=CANCEL;"
                    ):
                        cancelled = True
                    if (
                        message_line.startswith("ORCHESTRATION_ACCEPTANCE: OUTCOME=")
                        and "; MUST=" in message_line
                        and "; MUST_NOT=" in message_line
                        and "; DESTINATIONS=" in message_line
                        and "; PROOF=" in message_line
                    ):
                        prior_acceptance = message_line[
                            :MAX_PRIOR_ACCEPTANCE_CHARS
                        ]
                    elif message_line.startswith("ORCHESTRATION_ACCEPT:"):
                        prior_acceptance = None
                if cancelled:
                    prior_acceptance = None
    except OSError:
        return "none", "unavailable", "NONE"
    task_turns = max(contexts, starts)
    fork_turns = "none" if task_turns <= 1 else str(min(MAX_FORK_TURNS, task_turns))
    return fork_turns, root_route, prior_acceptance or "NONE"


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":")))


def control_request(prompt: str) -> tuple[bool, bool] | None:
    """Return (activate, has_work) for the last imperative control phrase."""
    clauses = [
        clause
        for raw_line in prompt.splitlines()
        for clause in re.split(r"(?<=[.!?])\s+", raw_line)
        if clause.strip()
    ]
    matched: bool | None = None
    remaining_work: list[str] = []
    for raw_clause in clauses:
        line = " ".join(raw_clause.strip().lower().split())
        if line.startswith(("- ", "* ")):
            line = line[2:].lstrip()
        clause_match: tuple[int, bool, str, str] | None = None
        for command, activate in CONTROL_COMMANDS:
            search_from = 0
            while True:
                start = line.find(command, search_from)
                if start < 0:
                    break
                end = start + len(command)
                search_from = start + 1
                if start and line[start - 1].isalnum():
                    continue
                tail = line[end:]
                if tail and tail[0] not in CONTROL_SEPARATORS:
                    continue
                prefix = line[:start]
                polite = bool(POLITE_CONTROL_PREFIX.fullmatch(prefix))
                inline = bool(INLINE_CONTROL_BOUNDARY.search(prefix))
                if start and not polite and not inline:
                    continue
                prefix_work = "" if polite else INLINE_CONTROL_BOUNDARY.sub("", prefix)
                prefix_work = prefix_work.strip(CONTROL_SEPARATORS)
                tail = tail.lstrip(CONTROL_SEPARATORS)
                for connector in WORK_CONNECTORS:
                    if tail == connector:
                        tail = ""
                        break
                    if tail.startswith(connector + " "):
                        tail = tail[len(connector) :].lstrip(CONTROL_SEPARATORS)
                        break
                candidate = (start, activate, prefix_work, tail)
                if clause_match is None or candidate[0] >= clause_match[0]:
                    clause_match = candidate
        if clause_match is None:
            remaining_work.append(line)
            continue
        matched = clause_match[1]
        if clause_match[2]:
            remaining_work.append(clause_match[2])
        if clause_match[3]:
            remaining_work.append(clause_match[3])
    if matched is None:
        return None
    return matched, any(remaining_work)


def additional_context(text: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        emit({"continue": True})
        return 0
    if hook_input.get("hook_event_name") != "UserPromptSubmit":
        emit({"continue": True})
        return 0
    # A desktop host may retain the former plugin hook definition until it exits.
    # Updated cache aliases make that stale source harmless while the stable user
    # hook owns routing without requiring a desktop restart.
    if os.environ.get("PLUGIN_ROOT"):
        emit({"continue": True})
        return 0
    session_id = hook_input.get("session_id")
    prompt = hook_input.get("prompt")
    if not isinstance(session_id, str) or not isinstance(prompt, str):
        emit({"continue": True})
        return 0
    control = control_request(prompt)
    # Inactive ordinary prompts return without touching the transcript.
    if control is None and not is_active(session_id):
        emit({"continue": True})
        return 0
    # Subagents share the parent session id. Never redispatch or change root state.
    if transcript_role(hook_input.get("transcript_path")) is not None:
        emit({"continue": True})
        return 0
    if control is not None and not control[0]:
        if not write_state(session_id, active=False):
            emit(
                additional_context(
                    "Reply exactly `Orchestration: ERROR; could not save OFF state`. "
                    "Do not orchestrate this prompt."
                )
            )
            return 0
        if control[1]:
            emit(
                additional_context(
                    "Begin with `Orchestration: OFF for this chat`, then handle the "
                    "remaining user work directly. Do not spawn an Orchestration agent."
                )
            )
            return 0
        emit(
            additional_context(
                "Reply exactly `Orchestration: OFF for this chat`. Do not orchestrate "
                "the remainder of this prompt."
            )
        )
        return 0
    activation = control is not None and control[0]
    activation_only = activation and not control[1]
    if activation and not write_state(session_id, active=True):
        emit(
            additional_context(
                "Reply exactly `Orchestration: ERROR; could not save ON state`. "
                "Do not spawn."
            )
        )
        return 0
    if activation_only:
        emit(
            additional_context(
                "Reply exactly `Orchestration: ON for this chat` and do not spawn."
            )
        )
        return 0
    prefix = (
        "Begin with `Orchestration: ON for this chat`, then dispatch the work.\n"
        if activation
        else ""
    )
    fork_turns, root_route, prior_acceptance = transcript_context(
        hook_input.get("transcript_path")
    )
    context = DISPATCH_CONTEXT.replace("__FORK_TURNS__", fork_turns).replace(
        "__ROOT_ROUTE__", root_route
    )
    context = context.replace("__PRIOR_ACTIVE_ACCEPTANCE__", prior_acceptance)
    emit(additional_context(prefix + context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
