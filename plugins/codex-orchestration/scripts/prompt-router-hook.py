#!/usr/bin/env python3
"""Inject the fast chat-local Terra dispatch contract once per user prompt."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from orchestration_state import (
    is_active,
    transcript_role,
    write_state,
)


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

DISPATCH_CONTEXT = """Orchestration ON (0.8.7). Act immediately as a zero-judgment relay.
Root alone controls agents; it never classifies, edits, corrects, or judges acceptance. Unfinished
work stays active unless the newest request explicitly cancels or replaces it. Keep every
current-activity description focused on the user's concrete outcome, never protocol execution.

FORK=`__FORK_TURNS__` (never literal `all`)
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__

FIRST ACTION — say `Starting Terra / Max classification now.`, then start exactly one Terra routing
supervisor with FORK, the verbatim request, PRIOR_ACTIVE_ACCEPTANCE, and `CLASSIFY_INIT`. This is the
common-path fused role: for READ_ONLY or tweaks the same Terra / Max instance continues. Do not
start another Terra worker or supervisor.

CLASSIFY_INIT calls no tools/commentary and returns exactly four lines: ORCHESTRATION_RELATION,
ORCHESTRATION_ROUTE, ORCHESTRATION_STATUS, ORCHESTRATION_ACCEPTANCE. Relationship is NEW, AMEND,
REPLACE, or CANCEL; only an explicit current signal permits REPLACE/CANCEL. Preserve unfinished
outcome, mutation mode, prohibitions, destinations, and proof. Classes: READ_ONLY=no mutation;
SMALL_TWEAK=one existing behavior/component; BIG_TWEAK=existing behavior across 2+ components or a
boundary; SMALL_BUILD=one new capability in <=2 components with settled architecture; BIG_BUILD=
2+ capabilities, 3+ components, a runtime boundary, material risk, or open architecture. Tests,
docs, release, and deploy add no components. Feature releases are builds; ambiguity routes upward.
Fixed lanes IMPLEMENTER/SUPERVISOR/CHECKPOINTS:
READ_ONLY=TERRA_MAX/NONE/NONE
SMALL_TWEAK=LUNA_MAX/TERRA_MAX/RELEASE_CANDIDATE
BIG_TWEAK=TERRA_MAX/TERRA_MAX/ROOT_CAUSE,RELEASE_CANDIDATE
SMALL_BUILD=TERRA_MAX/SOL_HIGH/DESIGN,RELEASE_CANDIDATE
BIG_BUILD=SOL_HIGH/SOL_XHIGH/ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE

Validate the four lines and lane mechanically; CANCEL is READ_ONLY/1.0/NONE/NONE/NONE. If invalid,
use `followup_task` once on the same Terra instance with `ROUTE_REPAIR` and the exact defect. Never
replace it or classify in root. On a second failure, report the blocker and start no work. CANCEL
drains only this request's Orchestration children and spawns no work.

TASK CATALOG: use the custom type if listed by `spawn_agent`; otherwise use its pinned built-in
fallback with FORK. For the fused router, the listed description must explicitly say `fused`;
otherwise treat the profile as stale and use built-in `default` Terra max. Never try an unavailable/
legacy type. Fallback messages include the full role rules in this contract.
fused router: `codex_orchestration_terra_supervisor` / `default` Terra max / `terra_max_router_`
Luna implementer: `codex_orchestration_luna_implementer` / `worker` Luna max / `luna_max_implementer_`
Terra implementer: `codex_orchestration_terra_implementer` / `worker` Terra max / `terra_max_implementer_`
Sol High implementer: `codex_orchestration_sol_high_implementer` / `worker` Sol high / `sol_high_implementer_`
Sol High supervisor: `codex_orchestration_sol_high_supervisor` / `default` Sol high / `sol_high_supervisor_`
Sol XHigh supervisor: `codex_orchestration_sol_xhigh_supervisor` / `default` Sol xhigh / `sol_xhigh_supervisor_`

READ_ONLY: use `followup_task` on the same Terra instance with `READ_ONLY_EXECUTE`, verbatim request,
and immutable lines. It may gather read-only evidence but cannot mutate, commit, push, or deploy.
Return its answer; do not spawn another role.

TWEAK: Terra is already the ready supervisor. Start only the selected implementer with FORK,
verbatim request, and immutable lines. Do not send SUPERVISOR_INIT or start another supervisor. Say
exactly `Implementation started with <implementer model>. The <supervisor model> supervisor is ready.`

BUILD: Terra ends after classification. Start the implementer, then immediately start the selected
Sol supervisor with FORK, verbatim request, and immutable lines. After `SUPERVISOR_READY`, use the
same combined start sentence. Never replace either instance.

IMPLEMENTER: it alone owns edits, tests, corrections, commit, push, deploy, and proof. It stops all
changing processes at each ordered checkpoint and returns exactly `IMPLEMENTATION_CHECKPOINT:
PHASE=<...>; STATE=<...>; CHANGES=<...>; EVIDENCE=<...>; NEXT=<...>; BLOCKERS=<...>`. CONTINUE
advances; CORRECT goes to this same implementer; READY_TO_RELEASE lets it release and return
`IMPLEMENTATION_RESULT` with STATE, EVIDENCE, REVISION, TESTS, DEPLOYMENT, PROBE, INCOMPLETE.
Built-in fallback messages include these full rules.

SUPERVISOR: stay read-only and inspect only while implementation is paused. Fused Terra is ready
after a valid tweak route; Sol INIT calls no tools/commentary and returns `SUPERVISOR_READY`.
Checkpoint decisions: CONTINUE, CORRECT, READY_TO_RELEASE, BLOCKED. Final decisions: ACCEPT,
CORRECT, ROOT_VERIFY, BLOCKED. CORRECT requires an observed mismatch and always goes to the same
implementer. Built-in fallback messages include these full rules.

WAIT/RELAY: normal agent waits are at most 45 seconds. Poll routine waits, checkpoint review,
continuation, protocol repair, and final review silently. Change-work updates after classification
are limited to the combined start, an actual correction, `Ready to release. The implementer is
committing, pushing, deploying, and verifying now.`, an external blocker, and the final result. If
the host forces a heartbeat after 60 seconds, say only `Still working on <actual user outcome>.`
Never expose spawn, contract, relay, or checkpoint in user-visible progress.

At a quiescent checkpoint, use `followup_task` on that same supervisor with `CHECKPOINT_REVIEW:`,
immutable lines, and checkpoint; relay its exact decision with `followup_task` to the same
implementer. After result, use `followup_task` on that same supervisor with `FINAL_REVIEW:`,
immutable lines, and exact result. Repeat corrections with the same pair. ROOT_VERIFY permits only
the named bounded experience check. Only ORCHESTRATION_ACCEPT completes work.

Every routed final appends exactly:
`Work class: <immutable class>`
`Supervisor route: <GPT-5.6 Terra / Max, GPT-5.6 Sol / High, GPT-5.6 Sol / Extra High, or NONE>`
`Implementation route: <GPT-5.6 Terra / Max, GPT-5.6 Luna / Max, or GPT-5.6 Sol / High>`
`Current root route: __ROOT_ROUTE__`
Agents do not append these lines."""


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
    """Return bounded fork, root route, and unfinished acceptance in one pass."""
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
