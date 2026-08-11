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
MAX_PRIOR_ACCEPTANCE_CHARS = 4_096
MAX_PRIOR_COMPLETED_CHARS = 4_096
MAX_RECENT_CONTEXT_CHARS = 6_144
MAX_RECENT_MESSAGE_CHARS = 1_536
MAX_RECENT_MESSAGES = 8
INJECTED_USER_PREFIXES = (
    "<recommended_plugins>",
    "# AGENTS.md instructions for ",
    "<environment_context>",
)
ENVIRONMENT_CONTEXT_END = "</environment_context>"
WORKSPACE_ARTIFACT_PATTERN = re.compile(
    r"\b(?:spreadsheet|workbook|google\s+sheet|xlsx?|csv|tsv|"
    r"presentation|slide\s+deck|powerpoint|pptx?|word\s+document|docx|pdf)\b",
    re.IGNORECASE,
)
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

DISPATCH_CONTEXT = """Orchestration ON (0.10.4). Root applies the binary fast-path gate, then
mechanically coordinates Terra-selected roles. Root never classifies taxonomy, constructs
acceptance, implements, supervises, or judges change work.

DESKTOP ACTIVITY DISPLAY — The gray orchestration root reasoning summary is a user-facing activity
label, not internal dialogue. Keep it to one plain 2-7 word current milestone, with no Markdown.
Use the newest actual development, such as `Classifying the request`, `Waiting for Terra / Max
classification`, `Starting Luna / Max implementation`, `Waiting for Luna / Max checkpoint`,
`Reviewing the release candidate`, `Releasing with Terra / Max`, or `Checking the live experience`.
The model name must match the dynamic route. If no concrete milestone is known, use exactly
`Thinking`. Never expose planning, orchestration mechanics, taxonomy, contracts, packets, relays,
or the request text. Never begin a label with `Planning`, and never use any variation of
`verbatim request`.

FORK=`1` (inherit only the current root turn; never literal `all` or `none`)
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__
PRIOR_COMPLETED_RESULT: __PRIOR_COMPLETED_RESULT__
RECENT_CONTEXT_FRESHNESS: __RECENT_CONTEXT_FRESHNESS__
RECENT_CONTEXT: __RECENT_CONTEXT__
WORKSPACE_DEPENDENCIES_REQUIRED: __WORKSPACE_DEPENDENCIES_REQUIRED__
CURRENT_ROOT_ROUTE: __ROOT_ROUTE__

DIRECT READ-ONLY FAST PATH — answer in root immediately only with no active acceptance, no mutation,
tools, fresh verification, inspection, browsing, audit, or substantial research, and when the
explanation, summary, status, rationale, brief brainstorm, or plan is already supported by the
conversation, stable knowledge, PRIOR_COMPLETED_RESULT, or RECENT_CONTEXT. Use no tools or agents;
omit the Terra start message and routing metadata. When uncertain, use Terra.

FAST RELAY — Schema validation is mechanical. After a valid classifier or child result, emit the
next required tool call in the same assistant response with no reasoning item between them. Reason
only for a protocol error, route mismatch, blocker, or user decision.

Otherwise, say exactly `Starting Terra / Max classification now.` and, in the same assistant
response, immediately start one orchestrator named `terra_max_orchestrator_<objective_slug>` with
`fork_turns=1` and this exact classification packet:
ORCHESTRATE_CLASSIFY
PRIOR_ACTIVE_ACCEPTANCE=<exact value above>
PRIOR_COMPLETED_RESULT=<exact value above>
RECENT_CONTEXT_FRESHNESS=<exact value above>
RECENT_CONTEXT=<exact value above>
USER_REQUEST=INHERITED_CURRENT_QUERY

Use custom type `codex_orchestration_terra_orchestrator` when listed. Otherwise use built-in
`default` pinned to GPT-5.6 Terra / Max and tell it first to read and obey the
`developer_instructions` in `__ORCHESTRATOR_PROFILE_PATH__`. Make the lookup silently and once. Do
not pass WORKSPACE_DEPENDENCIES, task-specific skill instructions, repository contents, or a work
plan to the orchestrator. Its one-turn fork supplies the exact current query and attachment paths;
the packet supplies only bounded prior continuity.

Then call `wait_agent` with `timeout_ms: 3600000`; it returns immediately on activity. On expiry,
repeat silently. Never short-poll, call `list_agents` because time passed, or emit a heartbeat.

Require either one ORCHESTRATION_BLOCKED line or exactly ORCHESTRATION_RELATION,
ORCHESTRATION_ROUTE, and ORCHESTRATION_STATUS; reject any other payload. Preserve the three lines
verbatim as CLASSIFICATION. Require a nonempty exact `ORCHESTRATION_STATUS: REASON=` value and
validate mechanically against only these lanes:

- READ_ONLY: TERRA_MAX / NONE / NONE
- STANDARD_ARTIFACT: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- DESIGN_ARTIFACT: TERRA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- SMALL_TWEAK: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- BIG_TWEAK: TERRA_MAX / SOL_HIGH / ROOT_CAUSE,RELEASE_CANDIDATE
- BUILD: SOL_HIGH / SOL_XHIGH / ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE

For RELATION=CANCEL, return a concise result and stop. Otherwise, only after classification, resolve
WORKSPACE_DEPENDENCIES. If required, call root's `codex_app__load_workspace_dependencies` once and
preserve its complete result; never search paths or delegate loading. On failure, report the exact
blocker. If not required, use NONE. Never send dependencies to the orchestrator.

ROOT ROLE MAP — use the custom type when available; otherwise use the stated built-in with pinned
model/effort and the matching `developer_instructions` from `__AGENTS_DIR__`:

- TERRA_MAX orchestrator: `codex_orchestration_terra_orchestrator`; never reuse.
- TERRA_MAX implementer: `codex_orchestration_terra_implementer`; fallback `worker`, Terra / Max.
- LUNA_MAX implementer: `codex_orchestration_luna_implementer`; fallback `worker`, Luna / Max.
- SOL_HIGH implementer: `codex_orchestration_sol_high_implementer`; fallback `worker`, Sol / High.
- TERRA_MAX supervisor: `codex_orchestration_terra_supervisor`; fallback `default`, Terra / Max.
- SOL_HIGH supervisor: `codex_orchestration_sol_high_supervisor`; fallback `default`, Sol / High.
- SOL_XHIGH supervisor: `codex_orchestration_sol_xhigh_supervisor`; fallback `default`, Sol / Extra High.

Use `fork_turns=1` for the classifier and every initial implementer and supervisor. The inherited
current turn supplies the exact query once without copying it into tool arguments.
Child pills identify models, never work classes. Use exactly
`terra_max_implementer_<objective_slug>`, `terra_max_supervisor_<objective_slug>`,
`luna_max_implementer_<objective_slug>`,
`sol_high_implementer_<objective_slug>`, `sol_high_supervisor_<objective_slug>`, or
`sol_extra_high_supervisor_<objective_slug>`. Root owns every child. Initial role turns overlap only
for tool-free supervisor context loading; checkpoints are serial.

READ_ONLY — spawn only the Terra implementer with:
READ_ONLY_WORK
FORK=<FORK>
CLASSIFICATION=<exact three lines>
PRIOR_COMPLETED_RESULT=<exact value>
RECENT_CONTEXT=<exact value>
WORKSPACE_DEPENDENCIES=<exact value>
CURRENT_ROOT_ROUTE=<exact value>
USER_REQUEST=INHERITED_CURRENT_QUERY
Wait once. It may use task tools but not mutate. Accept an optional leading ORCHESTRATION_HANDOFF
then ORCHESTRATION_ACCEPT; remove both protocol pieces and return the remaining payload exactly.

CHANGE WORK — first spawn the selected implementer with:
IMPLEMENTATION_START
FORK=<FORK>
CLASSIFICATION=<exact three lines>
ACCEPTANCE=PENDING_SUPERVISOR_INIT
USER_REQUEST=INHERITED_CURRENT_QUERY
RECENT_CONTEXT=<exact value>
WORKSPACE_DEPENDENCIES=<exact value>
CURRENT_ROOT_ROUTE=<exact value>

Immediately spawn the selected supervisor second with:
SUPERVISOR_INIT
FORK=<FORK>
CLASSIFICATION=<exact three lines>
RECENT_CONTEXT=<exact value>
CURRENT_ROOT_ROUTE=<exact value>
USER_REQUEST=INHERITED_CURRENT_QUERY
Emit both `spawn_agent` tool calls in one assistant response, implementer first and supervisor
second. Do not wait for or process the implementer spawn output before emitting the supervisor
call. Accept either result first and preserve an early implementer checkpoint. Never replace a
child. A valid supervisor result starts SUPERVISOR_READY with one ORCHESTRATION_ACCEPTANCE line;
preserve it verbatim as ACCEPTANCE. On SUPERVISOR_SCOPE_REJECT or SUPERVISOR_BLOCKED, interrupt the
implementer, relay one concise scope question/blocker, and stop.

After readiness, lowercase CLASS, replace its underscore with a space, and post:
`This is a <friendly class> because <exact reason>. Implementation started with <implementer model>.
The <supervisor model> supervisor is ready.` Use dynamic lane labels exactly: LUNA_MAX=Luna / Max,
TERRA_MAX=Terra / Max, SOL_HIGH=Sol / High, and SOL_XHIGH=Sol / Extra High. Never hard-code the
big-tweak sentence or its models. Wait if the implementer checkpoint has not arrived.

COORDINATION LOOP — Root owns every child. After startup, every handoff to an idle child uses
`followup_task`, never `send_message`; wait for its structured final. Never activate implementer and
supervisor simultaneously after the first checkpoint.

- On `IMPLEMENTATION_CHECKPOINT`, reactivate the supervisor with `CHECKPOINT_REVIEW` plus only the
  exact checkpoint and ACCEPTANCE; then wait.
- On `SUPERVISOR_CONTINUE`, post `Supervisor approved <completed checkpoint>. Implementation
  continues to <next checkpoint>.`, reactivate the implementer with the exact decision and exact
  ACCEPTANCE, and wait.
- On `SUPERVISOR_CORRECT`, post one concise update naming the finding, reactivate the same
  implementer with the exact decision and exact ACCEPTANCE, and wait.
- On `SUPERVISOR_READY_TO_RELEASE`, post `Ready to release. The implementer is committing, pushing,
  deploying, and verifying now.`, reactivate the implementer with the exact decision and exact
  ACCEPTANCE, and wait.
- On `IMPLEMENTATION_RESULT`, reactivate the supervisor with `FINAL_REVIEW` plus only the exact
  result, ACCEPTANCE, and CURRENT_ROOT_ROUTE; then wait.
- On `SUPERVISOR_BLOCKED` or an implementer blocker, relay one concise blocker and stop.

`ORCHESTRATION_ROOT_VERIFY` is the only root verification path. Use root-only Browser/visual tools
for exactly the requested cache-bypassed live/artifact check at the requested viewport. Do not
change state, broaden the check, or judge acceptance. Then reactivate the same supervisor with:
ROOT_VERIFICATION_RESULT: START=<observed start>; ACTION=<actual action>; RESULT=<observed result>; ARTIFACTS=<URL or path, viewport, screenshots, and measurements or NONE>; BLOCKER=<NONE or exact access failure>
Wait for its decision.

A completed supervisor payload has one leading ORCHESTRATION_HANDOFF then `ORCHESTRATION_ACCEPT: `.
Omit the handoff, remove only the acceptance protocol prefix, and return all remaining Markdown
exactly, preserving line breaks, links, sections, and route metadata. Reject any other payload;
never summarize or rewrite it.

Never expose contracts, packets, waits, or relay mechanics. Outside the direct read-only fast path,
root's visible messages are only the specified classification, start, checkpoint, release, blocker,
and exact final result; the gray activity label may show only the latest safe milestone above. Root
coordinates and makes requested raw experience observations; it never classifies, implements,
supervises, or judges acceptance."""


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


def conversation_message(event: dict[str, Any]) -> tuple[str, str] | None:
    """Return a root user/assistant conversation message, excluding injected wrappers."""
    if event.get("type") != "response_item":
        return None
    payload = event.get("payload") or {}
    if payload.get("type") != "message" or payload.get("role") not in {"user", "assistant"}:
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    values: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        value = item.get("text")
        if isinstance(value, str):
            values.append(value)
    message = "\n".join(values).strip()
    if payload.get("role") == "user":
        message = strip_injected_user_prefix(message)
    if not message:
        return None
    return str(payload["role"]), message


def strip_injected_user_prefix(message: str) -> str:
    """Remove the app's leading runtime envelope while preserving the user's prompt."""
    stripped = message.lstrip()
    if not stripped.startswith(INJECTED_USER_PREFIXES):
        return message.strip()
    boundary = stripped.rfind(ENVIRONMENT_CONTEXT_END)
    if boundary < 0:
        return message.strip()
    return stripped[boundary + len(ENVIRONMENT_CONTEXT_END) :].strip()


def bounded_single_line(value: str, limit: int) -> str:
    """Collapse trusted continuity text to one bounded packet line."""
    return " ".join(value.split())[:limit]


def bounded_recent_context(messages: list[tuple[str, str]]) -> str:
    """Keep the newest bounded conversation messages within the packet budget."""
    fragments = [
        f"{role.upper()}: {bounded_single_line(message, MAX_RECENT_MESSAGE_CHARS)}"
        for role, message in messages[-MAX_RECENT_MESSAGES:]
    ]
    while fragments and len(" || ".join(fragments)) > MAX_RECENT_CONTEXT_CHARS:
        fragments.pop(0)
    return " || ".join(fragments) or "NONE"


def workspace_dependencies_required(prompt: str) -> str:
    """Flag artifact work whose bundled runtime must be loaded by root before dispatch."""
    return "YES" if WORKSPACE_ARTIFACT_PATTERN.search(prompt) else "NO"


def transcript_context(
    transcript_value: Any, current_prompt: str
) -> tuple[str, str, str, str, str]:
    """Return bounded routing state plus newer root-conversation context."""
    if not isinstance(transcript_value, str):
        return "unavailable", "NONE", "NONE", "NONE", "NONE"
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return "unavailable", "NONE", "NONE", "NONE", "NONE"
    root_route = "unavailable"
    prior_acceptance: str | None = None
    prior_completed: str | None = None
    completion_handoffs: dict[str, str] = {}
    conversation_tail: list[tuple[str, str]] = []
    post_completion_tail: list[tuple[str, str]] = []
    has_completion = False
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "turn_context":
                    payload = event.get("payload") or {}
                    model = payload.get("model")
                    effort = payload.get("effort")
                    if isinstance(model, str) and isinstance(effort, str):
                        root_route = (
                            f"{MODEL_LABELS.get(model, model)} / "
                            f"{EFFORT_LABELS.get(effort, effort)}"
                        )
                payload = event.get("payload") or {}
                conversation = conversation_message(event)
                if conversation is not None:
                    conversation_tail.append(conversation)
                    conversation_tail = conversation_tail[-MAX_RECENT_MESSAGES:]
                    if has_completion:
                        post_completion_tail.append(conversation)
                        post_completion_tail = post_completion_tail[-MAX_RECENT_MESSAGES:]
                message = agent_message_text(event)
                metadata = (event.get("payload") or {}).get(
                    "internal_chat_message_metadata_passthrough"
                ) or {}
                turn_id = metadata.get("turn_id")
                completion_scope = turn_id if isinstance(turn_id, str) else "unscoped"
                cancelled = False
                message_lines = message.splitlines()
                for index, message_line in enumerate(message_lines):
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
                        prior_completed = None
                        completion_handoffs.pop(completion_scope, None)
                    elif message_line.startswith("ORCHESTRATION_HANDOFF: "):
                        completion_handoff = bounded_single_line(
                            message_line.removeprefix("ORCHESTRATION_HANDOFF: "),
                            MAX_PRIOR_COMPLETED_CHARS,
                        )
                        completion_handoffs[completion_scope] = completion_handoff
                        prior_completed = completion_handoff
                    elif message_line.startswith("ORCHESTRATION_ACCEPT:"):
                        prior_acceptance = None
                        accepted_result = "\n".join(message_lines[index:]).removeprefix(
                            "ORCHESTRATION_ACCEPT:"
                        )
                        prior_completed = completion_handoffs.get(
                            completion_scope
                        ) or bounded_single_line(accepted_result, MAX_PRIOR_COMPLETED_CHARS)
                        has_completion = True
                        post_completion_tail = []
                if cancelled:
                    prior_acceptance = None
    except OSError:
        return "unavailable", "NONE", "NONE", "NONE", "NONE"
    selected_tail = post_completion_tail if prior_completed else conversation_tail
    normalized_prompt = bounded_single_line(current_prompt, MAX_RECENT_CONTEXT_CHARS)
    if (
        selected_tail
        and selected_tail[-1][0] == "user"
        and bounded_single_line(selected_tail[-1][1], MAX_RECENT_CONTEXT_CHARS)
        == normalized_prompt
    ):
        selected_tail = selected_tail[:-1]
    freshness = "NONE"
    if prior_completed:
        freshness = "STALE" if any(role == "user" for role, _ in selected_tail) else "FRESH"
    recent_context = bounded_recent_context(selected_tail)
    return (
        root_route,
        prior_acceptance or "NONE",
        prior_completed or "NONE",
        freshness,
        recent_context,
    )


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
    (
        root_route,
        prior_acceptance,
        prior_completed,
        recent_freshness,
        recent_context,
    ) = transcript_context(
        hook_input.get("transcript_path"), prompt
    )
    context = DISPATCH_CONTEXT.replace("__ROOT_ROUTE__", root_route)
    context = context.replace("__PRIOR_ACTIVE_ACCEPTANCE__", prior_acceptance)
    context = context.replace("__PRIOR_COMPLETED_RESULT__", prior_completed)
    context = context.replace("__RECENT_CONTEXT_FRESHNESS__", recent_freshness)
    context = context.replace("__RECENT_CONTEXT__", recent_context)
    context = context.replace(
        "__WORKSPACE_DEPENDENCIES_REQUIRED__",
        workspace_dependencies_required(prompt),
    )
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    agents_dir = codex_home / "agents"
    orchestrator_profile = agents_dir / "codex-orchestration-terra-orchestrator.toml"
    context = context.replace("__ORCHESTRATOR_PROFILE_PATH__", str(orchestrator_profile))
    context = context.replace("__AGENTS_DIR__", str(agents_dir))
    emit(additional_context(prefix + context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
