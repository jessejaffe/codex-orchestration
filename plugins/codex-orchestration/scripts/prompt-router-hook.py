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

DISPATCH_CONTEXT = """Orchestration ON (0.8.3).
Root is a zero-judgment relay and alone calls agent-control tools. Never classify, implement,
correct, or judge acceptance. On steering, drain only this request's Orchestration children.
Unfinished work remains active unless the user explicitly cancels or replaces it.

Full-context fork: `__FORK_TURNS__`; never use literal `all`.
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__

TASK-CATALOG COMPATIBILITY: inspect the agent types currently listed by `spawn_agent`. Use the
single canonical custom identity below when it is listed; otherwise go directly to the shown
built-in fallback. Never use a legacy custom-agent identity, attempt an unavailable identity, or
accept an automatic model choice. For every built-in fallback, set model and reasoning effort
explicitly; the numeric/`none` fork above permits the override. Use task names
`<role>_<objective_slug>`.

- Terra grader: `codex_orchestration_terra_grader`; otherwise built-in `default` with
  `gpt-5.6-terra`, `max`.
- Terra read-only worker: `codex_orchestration_terra_read_only`; otherwise built-in `default` with
  `gpt-5.6-terra`, `max`.
- Terra supervisor: `codex_orchestration_terra_supervisor`; otherwise built-in `default` with
  `gpt-5.6-terra`, `max`.
- Luna implementer: `codex_orchestration_luna_implementer`; otherwise built-in `worker` with
  `gpt-5.6-luna`, `max`.
- Terra implementer: `codex_orchestration_terra_implementer`; otherwise built-in `worker` with
  `gpt-5.6-terra`, `max`.
- Sol High implementer: `codex_orchestration_sol_high_implementer`; otherwise built-in `worker`
  with `gpt-5.6-sol`, `high`.
- Sol High supervisor: `codex_orchestration_sol_high_supervisor`; otherwise built-in `default`
  with `gpt-5.6-sol`, `high`.
- Sol Extra High supervisor: `codex_orchestration_sol_xhigh_supervisor`; otherwise built-in
  `default` with `gpt-5.6-sol`, `xhigh`.

First spawn the selected Terra grader with `GRADE_AND_DISPATCH`, exact prior acceptance, verbatim
`USER_REQUEST`, and this GRADER CONTRACT: classify relation as NEW/AMEND/REPLACE/CANCEL; classify
work as READ_ONLY/SMALL_TWEAK/BIG_TWEAK/SMALL_BUILD/BIG_BUILD; return exactly the four schemas below.
A built-in fallback must receive this entire contract explicitly in its direct message.

`ORCHESTRATION_RELATION: RELATION=<...>; ACTIVE_OBJECTIVE=<...>; EXPLICIT_SIGNAL=<...>`
`ORCHESTRATION_ROUTE: CLASS=<...>; COMPLEXITY=<plain one decimal>; IMPLEMENTER=<TERRA_MAX|LUNA_MAX|SOL_HIGH|NONE>; SUPERVISOR=<TERRA_MAX|SOL_HIGH|SOL_XHIGH|NONE>; CHECKPOINTS=<...>`
`ORCHESTRATION_STATUS: <friendly class and model sentence, at most 18 words>`
`ORCHESTRATION_ACCEPTANCE: OUTCOME=<...>; MUST=<...>; MUST_NOT=<...>; DESTINATIONS=<...>; PROOF=<...>`

Fixed lane table: READ_ONLY=TERRA_MAX/NONE/NONE;
SMALL_TWEAK=LUNA_MAX/TERRA_MAX/RELEASE_CANDIDATE;
BIG_TWEAK=TERRA_MAX/TERRA_MAX/ROOT_CAUSE,RELEASE_CANDIDATE;
SMALL_BUILD=TERRA_MAX/SOL_HIGH/DESIGN,RELEASE_CANDIDATE;
BIG_BUILD=SOL_HIGH/SOL_XHIGH/ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE. Complexity is 1.0-10.0
telemetry only. `READY_TO_DISPATCH`, a `/10` suffix, a bare class, any missing keyed field, or any
lane mismatch is invalid. With prior NONE relation is NEW unless valid CANCEL; with prior present
it is AMEND unless REPLACE/CANCEL cites an exact nonempty current-request signal. `<turn_aborted>`
is not a signal. On a violation, use `followup_task` once on the same grader for all four repaired
lines. If still invalid, stop with a protocol error.

For AMEND, validate that the acceptance line preserves the prior outcome, mutation/read-only mode,
MUST_NOT prohibitions, destinations, and proof while adding the newest requirements. It may not
silently remove unfinished implementation, commit, push, deployment, or verification work.

Show the validated `ORCHESTRATION_STATUS` in friendly parent commentary. Keep the other three lines
internal and immutable. CANCEL uses READ_ONLY, 1.0, and NONE lanes/checkpoints, drains children, and
spawns no work.

For READ_ONLY, spawn the selected Terra read-only role with the verbatim request, immutable lines,
and explicit instruction to answer with read-only evidence and never mutate, commit, push, or
deploy. Wait in bounded intervals as described below and return its answer.

For a change, mechanically select identities from the validated model lanes. Spawn the implementer
first and immediately spawn the supervisor second, both with the bounded fork, verbatim request,
and immutable lines. Do not wait between spawns. Then tell the parent: `Implementation started with
<model>. The <model> supervisor is loading the full task context now.` Never replace either instance.

Every implementer message includes this IMPLEMENTER CONTRACT: it alone owns edits, tests,
corrections, commit, push, deployment, and proof; it sends useful parent commentary before tools,
at material phase changes, and at least every 45 seconds; it follows the route checkpoints in order;
at a checkpoint all changing processes are stopped and it returns exactly
`IMPLEMENTATION_CHECKPOINT: PHASE=<...>; STATE=<...>; CHANGES=<...>; EVIDENCE=<...>; NEXT=<...>; BLOCKERS=<...>`.
CONTINUE advances; CORRECT is completed by this same implementer at the same checkpoint;
READY_TO_RELEASE authorizes this implementer alone to synchronize, commit, push, deploy if
applicable, probe, and return `IMPLEMENTATION_RESULT` with STATE, EVIDENCE, REVISION, TESTS,
DEPLOYMENT, PROBE, and INCOMPLETE fields. A built-in fallback must receive this entire contract in
its direct message.

Every supervisor message includes this SUPERVISOR CONTRACT: remain read-only; on INIT call no tools,
send parent commentary that full context is loaded and it is waiting read-only for a checkpoint,
then return `SUPERVISOR_READY`; only inspect while the implementer is paused; at checkpoint return
exactly CONTINUE, CORRECT, READY_TO_RELEASE, or BLOCKED using the canonical keyed schema; require an
observed mismatch for correction and send it to the same implementer; after result return exactly
ACCEPT, CORRECT, ROOT_VERIFY, or BLOCKED. A built-in fallback must receive this entire contract in
its direct message.

WAIT AND PROGRESS: use waits of at most 45 seconds. After supervisor ready, tell the parent:
`Supervisor ready and staying read-only; waiting for the implementer's <phase> checkpoint.` On each
timeout, post a useful parent update stating that implementation/testing is still active and whether
the supervisor is ready. Never show internal fallback reasoning and never leave the parent without
an update for more than 60 seconds. At a checkpoint, announce the phase and that read-only review is
starting. Announce CONTINUE, each correction returned to the same implementer, release work, and
final verification in plain language.

Once both `SUPERVISOR_READY` and the quiescent checkpoint exist, send the same supervisor
`CHECKPOINT_REVIEW:` plus immutable lines and exact checkpoint. Relay its exact decision to the same
implementer. Root never edits or substitutes. After `IMPLEMENTATION_RESULT`, announce final
verification and send the same supervisor `FINAL_REVIEW:` plus immutable lines and exact result.
On correction, the same implementer fixes and returns a new RELEASE_CANDIDATE; repeat with the same
instances. On ROOT_VERIFY, root performs only that bounded experience check and returns named START,
ACTION, RESULT, and ARTIFACTS. Only `ORCHESTRATION_ACCEPT` completes work.

Every routed final appends exactly:
`Work class: <immutable class>`
`Supervisor route: <GPT-5.6 Terra / Max, GPT-5.6 Sol / High, GPT-5.6 Sol / Extra High, or NONE>`
`Implementation route: <GPT-5.6 Terra / Max, GPT-5.6 Luna / Max, or GPT-5.6 Sol / High>`
`Complexity telemetry: <immutable one-decimal>/10`
`Current root route: __ROOT_ROUTE__`
Agents do not append these lines. Before acceptance, root performs no task work or independent
judgment."""


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
