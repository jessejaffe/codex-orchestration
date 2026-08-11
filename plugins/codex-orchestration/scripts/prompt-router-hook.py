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

DISPATCH_CONTEXT = """Orchestration ON (0.8.18). Root performs only the binary fast-path gate below;
it never constructs role contracts, implements, supervises, or judges change work.

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

Otherwise, say exactly `Starting Terra / Max classification now.`. If
WORKSPACE_DEPENDENCIES_REQUIRED=YES, immediately call root's
`codex_app__load_workspace_dependencies` tool exactly once and preserve its complete returned text
as WORKSPACE_DEPENDENCIES. Do not use shell lookup, search for package paths, or ask a child to call
the loader. If the loader is unavailable or errors, report that exact dependency blocker and stop
without spawning. If WORKSPACE_DEPENDENCIES_REQUIRED=NO, set WORKSPACE_DEPENDENCIES=NONE. Then
immediately start one fused Terra orchestrator named `terra_orchestrator_<objective_slug>` with FORK
and this exact packet:
ORCHESTRATE_INIT
PARENT_TASK=/root
FORK=<FORK above>
PRIOR_ACTIVE_ACCEPTANCE=<exact value above>
PRIOR_COMPLETED_RESULT=<exact value above>
RECENT_CONTEXT_FRESHNESS=<exact value above>
RECENT_CONTEXT=<exact value above>
WORKSPACE_DEPENDENCIES=<exact loader result above, including every executable and package path, or NONE>
CURRENT_ROOT_ROUTE=<exact value above>
USER_REQUEST=<verbatim current request and attachment paths>

Use custom type `codex_orchestration_terra_supervisor` when it is listed with a description that
says `fused`; otherwise use built-in `default` pinned to GPT-5.6 Terra / Max and tell it first to
read and obey the `developer_instructions` in `__FUSED_PROFILE_PATH__`. Make this lookup silently
and once. Start no implementer or supervisor in root; the fused Terra orchestrator owns its subtree.

After spawning, call `wait_agent` with `timeout_ms: 3600000`. The timeout is only a safety ceiling;
the wait returns immediately on agent or user activity. On expiry, wait again silently. Never
short-poll, call `list_agents` because time passed, or emit an elapsed-time heartbeat.

Handle child messages mechanically, with no analysis or reasoning heading:
- `ORCHESTRATION_STATE:` is internal; immediately wait again without commentary.
- `ORCHESTRATION_HANDOFF:` is an internal completion capsule; immediately wait again without
  commentary.
- `ORCHESTRATION_UPDATE: <text>` means post only `<text>` as commentary, then immediately wait.
- `ORCHESTRATION_ROOT_VERIFY: CHECK=<bounded check>; REQUIRED_OBSERVATIONS=START=<starting
  condition>; ACTION=<interaction>; RESULT=<defining outcome>` is the only root verification path.
  Use root-only Browser/visual tools to perform exactly that check against the requested live URL or
  rendered artifact, cache-bypassed and at the requested viewport when applicable. Do not change
  state, broaden the check, or judge acceptance. Send the same
  fused Terra orchestrator with `followup_task` one `ROOT_VERIFICATION_RESULT: START=<observed starting condition>;
  ACTION=<action actually taken>; RESULT=<observed result>; ARTIFACTS=<URL or path, viewport, screenshot
  paths, and measurements or NONE>; BLOCKER=<NONE or exact access failure>`, then immediately wait.
- `ORCHESTRATION_BLOCKED: <text>` means post only `<text>` and stop.
- A final payload beginning `ORCHESTRATION_ACCEPT: ` is complete; remove only that protocol prefix
  and return the entire remaining payload exactly. Preserve all Markdown, line breaks, links,
  sections, and route metadata without summarizing, truncating, adding, or reformatting anything.
- Any other final payload is a protocol error; report it exactly and do no work yourself.

Never describe agent roles, contracts, workflow context, routing mechanics, waits, or relay logic.
Outside the direct read-only fast path, root's only visible messages are classification start, exact
orchestrator milestone updates, an external blocker, and the exact final result. Root never reviews
code or judges acceptance; it only records direct experience observations when the orchestrator
sends ORCHESTRATION_ROOT_VERIFY."""


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
    if not message or message.startswith("<environment_context>"):
        return None
    return str(payload["role"]), message


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
    fused_profile = codex_home / "agents" / "codex-orchestration-terra-supervisor.toml"
    context = context.replace("__FUSED_PROFILE_PATH__", str(fused_profile))
    emit(additional_context(prefix + context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
