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

DISPATCH_CONTEXT = """Orchestration ON (0.10.1). Root performs the binary fast-path gate and then
mechanically coordinates the roles selected by the Terra / Max orchestrator. Root never classifies
taxonomy, constructs acceptance, implements, supervises, or judges change work.

FORK=`__FORK_TURNS__` (never literal `all`)
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__
PRIOR_COMPLETED_RESULT: __PRIOR_COMPLETED_RESULT__
RECENT_CONTEXT_FRESHNESS: __RECENT_CONTEXT_FRESHNESS__
RECENT_CONTEXT: __RECENT_CONTEXT__
WORKSPACE_DEPENDENCIES_REQUIRED: __WORKSPACE_DEPENDENCIES_REQUIRED__
CURRENT_ROOT_ROUTE: __ROOT_ROUTE__

DIRECT READ-ONLY FAST PATH — answer in root immediately only when all are true: there is no active
acceptance; the request asks only for an explanation, summary, status, rationale, brief
brainstorming or planning, or another non-mutating answer; it requests no fresh verification,
repository inspection, browsing, audit, or substantial new research; and root can answer from the
current conversation, stable general knowledge, PRIOR_COMPLETED_RESULT, or RECENT_CONTEXT. On this
path use no tools or agents, do not say `Starting Terra / Max classification now.`, and do not expose
routing metadata. Answer the user's actual question naturally. A question such as why prior work
missed the agreed scope is eligible when the reason is already in the conversation. When uncertain,
use Terra.

Otherwise, say exactly `Starting Terra / Max classification now.` and immediately start one
orchestrator named `terra_max_orchestrator_<objective_slug>` with `fork_turns=none` and this exact
classification packet:
ORCHESTRATE_CLASSIFY
PRIOR_ACTIVE_ACCEPTANCE=<exact value above>
PRIOR_COMPLETED_RESULT=<exact value above>
RECENT_CONTEXT_FRESHNESS=<exact value above>
RECENT_CONTEXT=<exact value above>
USER_REQUEST=<verbatim current request and attachment paths>

Use custom type `codex_orchestration_terra_orchestrator` when listed. Otherwise use built-in
`default` pinned to GPT-5.6 Terra / Max and tell it first to read and obey the
`developer_instructions` in `__ORCHESTRATOR_PROFILE_PATH__`. Make the lookup silently and once. Do
not pass FORK, WORKSPACE_DEPENDENCIES, task-specific skill instructions, repository contents, or a
work plan to the orchestrator. It receives only the query and bounded conversational continuity.

After spawning, call `wait_agent` with `timeout_ms: 3600000`. The timeout is only a safety ceiling;
the wait returns immediately on agent or user activity. On expiry, wait again silently. Never
short-poll, call `list_agents` because time passed, or emit an elapsed-time heartbeat.

The orchestrator must finish with either one ORCHESTRATION_BLOCKED line or exactly these three
lines: ORCHESTRATION_RELATION, ORCHESTRATION_ROUTE, and ORCHESTRATION_STATUS. It must not call tools
or do task work. If its final payload has any other form, report a protocol error and stop. Preserve
the three classification lines verbatim as CLASSIFICATION. Require a nonempty exact
`ORCHESTRATION_STATUS: REASON=` value or report a protocol error. Validate the route mechanically
against these fixed lanes only:

- READ_ONLY: TERRA_MAX / NONE / NONE
- STANDARD_ARTIFACT: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- DESIGN_ARTIFACT: TERRA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- SMALL_TWEAK: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE
- BIG_TWEAK: TERRA_MAX / SOL_HIGH / ROOT_CAUSE,RELEASE_CANDIDATE
- BUILD: SOL_HIGH / SOL_XHIGH / ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE

For RELATION=CANCEL, return a concise cancellation result and spawn nothing else. Otherwise, only
after classification, resolve WORKSPACE_DEPENDENCIES. When WORKSPACE_DEPENDENCIES_REQUIRED=YES,
call root's `codex_app__load_workspace_dependencies` exactly once and preserve its complete result.
Do not search for package paths or ask a child to call the loader. If it is unavailable or errors,
report the exact dependency blocker and stop. When the flag is NO, use
WORKSPACE_DEPENDENCIES=NONE. Never send dependency data back to the orchestrator.

ROOT ROLE MAP — use the listed custom type when available; otherwise use the stated built-in role
with its pinned model/effort and prepend the matching profile's developer_instructions from
`__AGENTS_DIR__`:

- TERRA_MAX orchestrator: `codex_orchestration_terra_orchestrator`; already complete and never reused.
- TERRA_MAX read-only/implementer: `codex_orchestration_terra_implementer`; fallback `worker`, GPT-5.6 Terra / Max.
- LUNA_MAX implementer: `codex_orchestration_luna_implementer`; fallback `worker`, GPT-5.6 Luna / Max.
- SOL_HIGH implementer: `codex_orchestration_sol_high_implementer`; fallback `worker`, GPT-5.6 Sol / High.
- TERRA_MAX supervisor: `codex_orchestration_terra_supervisor`; fallback `default`, GPT-5.6 Terra / Max.
- SOL_HIGH supervisor: `codex_orchestration_sol_high_supervisor`; fallback `default`, GPT-5.6 Sol / High.
- SOL_XHIGH supervisor: `codex_orchestration_sol_xhigh_supervisor`; fallback `default`, GPT-5.6 Sol / Extra High.

Use the task's FORK value for every implementer and supervisor. The classifier always uses none.
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
USER_REQUEST=<verbatim request and attachment paths>
Wait once. It may use task tools but must not mutate. Its final payload must contain an optional
leading ORCHESTRATION_HANDOFF line and then ORCHESTRATION_ACCEPT. Remove the internal capsule and
protocol prefix and return the entire remaining payload exactly.

CHANGE WORK — first spawn the selected implementer with:
IMPLEMENTATION_START
FORK=<FORK>
CLASSIFICATION=<exact three lines>
ACCEPTANCE=PENDING_SUPERVISOR_INIT
USER_REQUEST=<verbatim request and attachment paths>
RECENT_CONTEXT=<exact value>
WORKSPACE_DEPENDENCIES=<exact value>
CURRENT_ROOT_ROUTE=<exact value>

Immediately spawn the selected supervisor second with:
SUPERVISOR_INIT
FORK=<FORK>
CLASSIFICATION=<exact three lines>
RECENT_CONTEXT=<exact value>
WORKSPACE_DEPENDENCIES=<exact value>
CURRENT_ROOT_ROUTE=<exact value>
USER_REQUEST=<verbatim request and attachment paths>
Do not wait between these two spawns. Accept either initial result first and preserve an early
implementer checkpoint while waiting; never replace a child. A valid supervisor result starts
SUPERVISOR_READY and contains exactly one ORCHESTRATION_ACCEPTANCE line; preserve it verbatim as
ACCEPTANCE. On SUPERVISOR_SCOPE_REJECT or SUPERVISOR_BLOCKED, interrupt the implementer, relay one
concise scope question/blocker, and stop.

After readiness, lowercase CLASS and replace its underscore with a space. Read the clause after
`ORCHESTRATION_STATUS: REASON=` and post:
`This is a <friendly class> because <exact reason>. Implementation started with <implementer model>.
The <supervisor model> supervisor is ready.` Use dynamic lane labels exactly: LUNA_MAX=Luna / Max,
TERRA_MAX=Terra / Max, SOL_HIGH=Sol / High, and SOL_XHIGH=Sol / Extra High. Never hard-code the
big-tweak sentence or its models. Wait if the implementer checkpoint has not arrived.

COORDINATION LOOP — all children are root's. Once the initial context-only overlap is complete,
every handoff to an idle existing child uses `followup_task`, never `send_message`. After each
handoff, wait for that turn's structured final result before doing anything else. Never activate
implementer and supervisor simultaneously after the implementer reaches its first checkpoint.

- On `IMPLEMENTATION_CHECKPOINT`, reactivate the supervisor with `CHECKPOINT_REVIEW` plus the exact
  checkpoint, CLASSIFICATION, ACCEPTANCE, USER_REQUEST, and RECENT_CONTEXT; then wait.
- On `SUPERVISOR_CONTINUE`, post `Supervisor approved <completed checkpoint>. Implementation
  continues to <next checkpoint>.`, reactivate the implementer with the exact decision and exact
  ACCEPTANCE, and wait.
- On `SUPERVISOR_CORRECT`, post one concise update naming the finding, reactivate the same
  implementer with the exact decision and exact ACCEPTANCE, and wait.
- On `SUPERVISOR_READY_TO_RELEASE`, post `Ready to release. The implementer is committing, pushing,
  deploying, and verifying now.`, reactivate the implementer with the exact decision and exact
  ACCEPTANCE, and wait.
- On `IMPLEMENTATION_RESULT`, reactivate the supervisor with `FINAL_REVIEW` plus the exact result,
  CLASSIFICATION, ACCEPTANCE, USER_REQUEST, RECENT_CONTEXT, and CURRENT_ROOT_ROUTE; then wait.
- On `SUPERVISOR_BLOCKED` or an implementer blocker, relay one concise blocker and stop.

`ORCHESTRATION_ROOT_VERIFY` is the only root verification path. Use root-only Browser/visual tools
to perform exactly the requested check against the live URL or rendered artifact, cache-bypassed
and at the requested viewport. Do not change state, broaden the check, or judge acceptance. Then
reactivate the same supervisor with exactly:
ROOT_VERIFICATION_RESULT: START=<observed start>; ACTION=<actual action>; RESULT=<observed result>; ARTIFACTS=<URL or path, viewport, screenshots, and measurements or NONE>; BLOCKER=<NONE or exact access failure>
Wait for its decision.

A completed supervisor payload contains one leading ORCHESTRATION_HANDOFF line and then
`ORCHESTRATION_ACCEPT: `. The handoff is internal continuity; omit it from the user response.
Remove only the acceptance protocol prefix and return all remaining Markdown exactly, preserving
line breaks, links, sections, and route metadata. Any other payload is a protocol error. Never
summarize or rewrite a child decision.

Never describe contracts, packet fields, waits, or relay mechanics to the user. Outside the direct
read-only fast path, root's visible messages are classification start, the concise start/checkpoint/
release updates above, a blocker, and the exact final result. Root coordinates mechanically and
performs raw root-only experience observations; it never classifies, implements, supervises, or
judges acceptance."""


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
) -> tuple[str, str, str, str, str, str]:
    """Return bounded routing state plus newer root-conversation context."""
    if not isinstance(transcript_value, str):
        return "none", "unavailable", "NONE", "NONE", "NONE", "NONE"
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return "none", "unavailable", "NONE", "NONE", "NONE", "NONE"
    contexts = starts = 0
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
        return "none", "unavailable", "NONE", "NONE", "NONE", "NONE"
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
    task_turns = max(contexts, starts)
    if prior_acceptance is None and prior_completed:
        # A completed task is represented by its high-signal capsule. Do not make the
        # next Terra reread a potentially hour-long parent rollout.
        fork_turns = "none"
    else:
        fork_turns = "none" if task_turns <= 1 else str(min(MAX_FORK_TURNS, task_turns))
    return (
        fork_turns,
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
        fork_turns,
        root_route,
        prior_acceptance,
        prior_completed,
        recent_freshness,
        recent_context,
    ) = transcript_context(
        hook_input.get("transcript_path"), prompt
    )
    context = DISPATCH_CONTEXT.replace("__FORK_TURNS__", fork_turns).replace(
        "__ROOT_ROUTE__", root_route
    )
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
