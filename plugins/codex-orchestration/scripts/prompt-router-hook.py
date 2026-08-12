#!/usr/bin/env python3
"""Inject the chat-local Terra dispatch contract once per user prompt."""

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
    write_context_bundle,
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
MAX_PRIOR_ACCEPTANCE_CHARS = 2_048
MAX_PRIOR_COMPLETED_CHARS = 2_048
MAX_RECENT_CONTEXT_CHARS = 3_072
MAX_RECENT_MESSAGE_CHARS = 1_024
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
PREVIOUS_TASK_PATTERNS = (
    re.compile(
        r"\b(?:read|review|check|open|inspect|look\s+at|get\s+familiar\s+with)\s+"
        r"(?:the\s+)?(?:last|previous|prior)\s+"
        r"(?:chat|task|thread|conversation|orchestration\s+run)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:last|previous|prior)\s+"
        r"(?:chat|task|thread|conversation|orchestration\s+run)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:pick|picking)\s+(?:up|off)\s+where\s+we\s+left\s+off\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bcontinue\s+(?:from|where)\s+we\s+left\s+off\b", re.IGNORECASE),
)
PREVIOUS_TASK_PROTOCOL = """PREVIOUS TASK CONTEXT REQUIRED — Before classification, root uses the
Codex task-history tools (`list_threads`, then `read_thread`; discover them once if needed). Exclude
the current task and select the newest task from the same project or working directory. If that is
ambiguous, ask one concise question and stop. Read the task once, then create two bounded payloads:

1. ROUTING_CONTEXT is at most 1,200 characters and contains only Previous objective, Last result,
Open work, Resolved current referent, and Critical paths. It goes only to the classifier. Do not
send the prior transcript, detailed evidence, screenshots, tests, or implementation history to the
classifier.
2. LAST_TASK_CONTEXT is at most 6,000 characters and preserves the final answer plus the last
relevant user/assistant turns, exact paths, links, decisions, constraints, and open work. It goes
only to supervisors and implementers, never to the classifier.

Both payloads resolve references; neither silently adds scope. Artifacts merely mentioned as
background are optional. Only the current request or an explicit prior instruction can require one,
and a missing optional artifact never blocks work."""
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

DISPATCH_CONTEXT = """Orchestration ON (0.12.2). Root coordinates fixed roles; it does not classify,
construct acceptance, implement, supervise, or judge change work.

STATE
CLASSIFIER_FORK=`1`; ROLE_FORK=`none`
TASK_CONTEXT_BUNDLE: __TASK_CONTEXT_BUNDLE__
TASK_CONTEXT_REVISION: __TASK_CONTEXT_REVISION__
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__
PRIOR_COMPLETED_RESULT: __PRIOR_COMPLETED_RESULT__
RECENT_CONTEXT_FRESHNESS: __RECENT_CONTEXT_FRESHNESS__
RECENT_CONTEXT: __RECENT_CONTEXT__
WORKSPACE_DEPENDENCIES_REQUIRED: __WORKSPACE_DEPENDENCIES_REQUIRED__
CURRENT_ROOT_ROUTE: __ROOT_ROUTE__

The gray desktop activity label is 2-7 plain words naming the latest verified milestone, such as
`Classifying the request`, `Building with Luna / Max`, or `Reviewing the release candidate`. If no
safe milestone exists, show exactly `Thinking`. Never expose request text or orchestration internals.

__PREVIOUS_TASK_PROTOCOL__

FAST PATH — Root may answer directly only when there is no active acceptance, mutation, tool use,
fresh verification, audit, browsing, or substantial research and the answer is already supported
by current continuity or stable knowledge. Otherwise classify.

CLASSIFY — Say `Starting Terra / Extra High classification now.` and immediately spawn
`terra_extra_high_orchestrator_<objective_slug>` with `fork_turns=1`:
ORCHESTRATE_CLASSIFY
PRIOR_ACTIVE_ACCEPTANCE=<STATE value>
PRIOR_COMPLETED_RESULT=<STATE value>
RECENT_CONTEXT_FRESHNESS=<STATE value>
RECENT_CONTEXT=<STATE value>
__ROUTING_CONTEXT_PACKET_LINE__
USER_REQUEST=INHERITED_CURRENT_QUERY

Use `codex_orchestration_terra_orchestrator`, or built-in `default` pinned Terra / Extra High after
reading `__ORCHESTRATOR_PROFILE_PATH__`. Pass no workspace dependencies, repository content, skill
instructions, or plan. Wait with `wait_agent(timeout_ms=3600000)` and repeat silently on timeout.
Accept only `## Classification blocked` or `## Classification` with Relationship, Active objective,
Explicit signal, Work class, Complexity, Implementation, Supervision, Checkpoints, and nonempty Why.
Validate exactly:

- Read-only: Terra / Max; no supervisor; no checkpoints
- Standard artifact: Luna / Max; Terra / Max; Release candidate
- Design artifact: Terra / Max; Terra / Max; Release candidate
- Small tweak: Luna / Max; Terra / Max; no checkpoints
- Big tweak: Terra / Max; Sol / High; Release candidate
- Small build: Terra / Max; Sol / High; Architecture → Release candidate
- Big build: Sol / High; Sol / Extra High; Architecture → Vertical slice → Release candidate

ROLES — Prefer these custom types; fallback to the stated built-in and matching profile in
`__AGENTS_DIR__`: Terra implementer `codex_orchestration_terra_implementer` (`worker`, Terra / Max),
Luna implementer `codex_orchestration_luna_implementer` (`worker`, Luna / Max), Sol implementer
`codex_orchestration_sol_high_implementer` (`worker`, Sol / High), Terra supervisor
`codex_orchestration_terra_supervisor` (`default`, Terra / Max), Sol supervisor
`codex_orchestration_sol_high_supervisor` (`default`, Sol / High), Sol Extra High supervisor
`codex_orchestration_sol_xhigh_supervisor` (`default`, Sol / Extra High). Initial task roles use
`fork_turns=none`. Name children by model: `terra_max_implementer_<objective_slug>`,
`luna_max_implementer_<objective_slug>`, `sol_high_implementer_<objective_slug>`,
`terra_max_supervisor_<objective_slug>`, `sol_high_supervisor_<objective_slug>`, or
`sol_extra_high_supervisor_<objective_slug>`.

After classification, load workspace dependencies once with
`codex_app__load_workspace_dependencies` only when STATE says YES; otherwise use NONE.

READ_ONLY — Spawn only Terra implementer:
READ_ONLY_WORK
CLASSIFICATION=<exact Markdown>
PRIOR_COMPLETED_RESULT=<STATE value>
TASK_CONTEXT_BUNDLE=<STATE path>
TASK_CONTEXT_REVISION=<STATE revision>
WORKSPACE_DEPENDENCIES=<exact result or NONE>
CURRENT_ROOT_ROUTE=<STATE value>
__LAST_TASK_CONTEXT_PACKET_LINE__
Wait and return its `## Completed` section unchanged.

CHANGE WORK — Start implementation before acceptance construction. Post `This is a <friendly
class> because <Why>. Starting <Implementation>; <Supervision> is defining acceptance.`
Then spawn the selected implementer first:
IMPLEMENTATION_START
CLASSIFICATION=<exact Markdown>
ACCEPTANCE=PENDING_SUPERVISOR_INIT
TASK_CONTEXT_BUNDLE=<STATE path>
TASK_CONTEXT_REVISION=<STATE revision>
WORKSPACE_DEPENDENCIES=<exact result or NONE>
CURRENT_ROOT_ROUTE=<STATE value>
__LAST_TASK_CONTEXT_PACKET_LINE__

Immediately spawn the selected supervisor second:
SUPERVISOR_INIT
CLASSIFICATION=<exact Markdown>
TASK_CONTEXT_BUNDLE=<STATE path>
TASK_CONTEXT_REVISION=<STATE revision>
CURRENT_ROOT_ROUTE=<STATE value>
__LAST_TASK_CONTEXT_PACKET_LINE__
Emit both `spawn_agent` calls back-to-back in that order; do not wait. Preserve the first result,
including `## Awaiting acceptance`, `## Checkpoint`, or `## Implementation result`. Preserve a
supervisor `## Ready` with all seven fields as ACCEPTANCE. Deliver it immediately with
`send_message` if the implementer runs, or `followup_task` if idle. On `## Scope mismatch` or
`## Blocked`, interrupt it, preserve local work, relay one issue, and stop.

RELATIONSHIPS — After Amend, Replace, or Cancel, call `list_agents` once. Cancel interrupts unfinished
owned roles and stops. Replace interrupts them and starts fresh. For Amend with unchanged lanes, send
running roles the new classification, bundle path/revision, and optional LAST_TASK_CONTEXT; tell the
implementer to pause. Reactivate the same supervisor with `AMENDMENT_REVIEW`, preserve its
`## Acceptance updated`, then resume the same implementer with that acceptance. A lane change starts
fresh. Never mutate under superseded acceptance.

LOOP — Use `send_message` only for acceptance/steering to a running implementer; use `followup_task`
for each idle-role handoff and wait.

- `## Awaiting acceptance` → same implementer with ACCEPTANCE after supervisor readiness.
- `## Checkpoint` → supervisor: `CHECKPOINT_REVIEW` plus checkpoint and ACCEPTANCE.
- `## Continue` → same implementer with decision and ACCEPTANCE.
- `## Corrections required` → same implementer with decision and ACCEPTANCE.
- `## Ready to release` → same implementer with decision and ACCEPTANCE; announce the release.
- `## Implementation result` → same supervisor: `FINAL_REVIEW` plus result, ACCEPTANCE, and route.
- `## Blocked` → relay one concise blocker and stop.

Small tweak starts immediately with no implementer checkpoint; after acceptance it may release.
Big tweak has only `RELEASE_CANDIDATE`. Thus small tweak has two
supervisory gates (acceptance and final review), while big tweak has three (acceptance, release
candidate, final review).

On `## Root verification needed`, perform exactly the requested read-only Browser/visual observation
and return to the supervisor:
## Root verification result
- Start: <observed condition>
- Action: <actual action>
- Result: <observed result>
- Artifacts: <URL/path, viewport, screenshots, measurements, or None>
- Blocker: <None or exact access failure>

A completed supervisor response contains `## Continuity` then `## Completed`. Return everything from
`## Completed` unchanged. Fast-relay valid child results without extra reasoning. Never expose
packets, waits, or contracts to the user."""


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


def markdown_section(message: str, heading: str) -> str | None:
    """Return one exact level-two Markdown section from trusted child output."""
    lines = message.splitlines()
    marker = f"## {heading}"
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == marker)
    except StopIteration:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def markdown_bullets(section: str | None) -> dict[str, str]:
    """Parse single-line labeled bullets from one trusted Markdown section."""
    if not section:
        return {}
    values: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^- ([^:]+):\s*(.+)$", line.strip())
        if match:
            values[match.group(1).strip()] = match.group(2).strip()
    return values


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


def previous_task_context_required(prompt: str) -> bool:
    """Return whether the user explicitly asks root to recover a prior Codex task."""
    normalized = " ".join(prompt.split())
    if re.search(
        r"\b(?:do\s+not|don't|dont)\s+(?:read|open|inspect|review)\s+"
        r"(?:the\s+)?(?:last|previous|prior)\s+(?:chat|task|thread|conversation)\b",
        normalized,
        re.IGNORECASE,
    ):
        return False
    return any(pattern.search(normalized) for pattern in PREVIOUS_TASK_PATTERNS)


def transcript_context(
    transcript_value: Any, current_prompt: str
) -> tuple[str, str, str, str, str, list[dict[str, Any]], dict[str, str | None]]:
    """Return bounded routing state and exact root-visible active-task messages."""
    exact_current_prompt = strip_injected_user_prefix(current_prompt).strip()
    if not isinstance(transcript_value, str):
        return (
            "unavailable",
            "NONE",
            "NONE",
            "NONE",
            "NONE",
            [{"role": "user", "content": exact_current_prompt, "current": True}],
            {"prior_active_acceptance": None, "prior_completed_result": None},
        )
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return (
            "unavailable",
            "NONE",
            "NONE",
            "NONE",
            "NONE",
            [{"role": "user", "content": exact_current_prompt, "current": True}],
            {"prior_active_acceptance": None, "prior_completed_result": None},
        )
    root_route = "unavailable"
    prior_acceptance: str | None = None
    prior_completed: str | None = None
    exact_prior_acceptance: str | None = None
    exact_prior_completed: str | None = None
    completion_handoffs: dict[str, str] = {}
    exact_completion_handoffs: dict[str, str] = {}
    conversation_tail: list[tuple[str, str]] = []
    post_completion_tail: list[tuple[str, str]] = []
    task_messages: list[dict[str, Any]] = []
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
                    task_messages.append(
                        {"role": conversation[0], "content": conversation[1]}
                    )
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
                classification = markdown_bullets(
                    markdown_section(message, "Classification")
                )
                if classification.get("Relationship") == "Cancel":
                    cancelled = True

                readable_acceptance = markdown_section(message, "Acceptance updated")
                if readable_acceptance is None:
                    readable_acceptance = markdown_section(message, "Ready")
                acceptance_fields = markdown_bullets(readable_acceptance)
                required_acceptance_fields = {
                    "Work class",
                    "Outcome",
                    "Must",
                    "Must not",
                    "Destinations",
                    "Open commitments",
                    "Proof",
                }
                if required_acceptance_fields.issubset(acceptance_fields):
                    exact_prior_acceptance = readable_acceptance
                    prior_acceptance = bounded_single_line(
                        readable_acceptance, MAX_PRIOR_ACCEPTANCE_CHARS
                    )
                    prior_completed = None
                    exact_prior_completed = None
                    completion_handoffs.pop(completion_scope, None)
                    exact_completion_handoffs.pop(completion_scope, None)

                readable_completion = markdown_section(message, "Completed")
                if readable_completion is not None:
                    continuity = markdown_section(message, "Continuity")
                    exact_prior_completed = continuity or readable_completion
                    prior_completed = bounded_single_line(
                        exact_prior_completed, MAX_PRIOR_COMPLETED_CHARS
                    )
                    prior_acceptance = None
                    exact_prior_acceptance = None
                    has_completion = True
                    post_completion_tail = []
                    task_messages = []

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
                        exact_prior_acceptance = message_line
                        prior_acceptance = message_line[:MAX_PRIOR_ACCEPTANCE_CHARS]
                        prior_completed = None
                        exact_prior_completed = None
                        completion_handoffs.pop(completion_scope, None)
                        exact_completion_handoffs.pop(completion_scope, None)
                    elif message_line.startswith("ORCHESTRATION_HANDOFF: "):
                        completion_handoff = bounded_single_line(
                            message_line.removeprefix("ORCHESTRATION_HANDOFF: "),
                            MAX_PRIOR_COMPLETED_CHARS,
                        )
                        completion_handoffs[completion_scope] = completion_handoff
                        exact_completion_handoffs[
                            completion_scope
                        ] = message_line.removeprefix("ORCHESTRATION_HANDOFF: ")
                        prior_completed = completion_handoff
                        exact_prior_completed = exact_completion_handoffs[completion_scope]
                    elif message_line.startswith("ORCHESTRATION_ACCEPT:"):
                        prior_acceptance = None
                        exact_prior_acceptance = None
                        accepted_result = "\n".join(message_lines[index:]).removeprefix(
                            "ORCHESTRATION_ACCEPT:"
                        )
                        exact_prior_completed = exact_completion_handoffs.get(
                            completion_scope
                        ) or accepted_result.strip()
                        prior_completed = completion_handoffs.get(
                            completion_scope
                        ) or bounded_single_line(accepted_result, MAX_PRIOR_COMPLETED_CHARS)
                        has_completion = True
                        post_completion_tail = []
                        task_messages = []
                if cancelled:
                    prior_acceptance = None
                    exact_prior_acceptance = None
                    task_messages = []
    except OSError:
        return (
            "unavailable",
            "NONE",
            "NONE",
            "NONE",
            "NONE",
            [{"role": "user", "content": exact_current_prompt, "current": True}],
            {"prior_active_acceptance": None, "prior_completed_result": None},
        )
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
    if not (
        task_messages
        and task_messages[-1]["role"] == "user"
        and task_messages[-1]["content"].strip() == exact_current_prompt
    ):
        task_messages.append(
            {"role": "user", "content": exact_current_prompt, "current": True}
        )
    else:
        task_messages[-1]["current"] = True
    return (
        root_route,
        prior_acceptance or "NONE",
        prior_completed or "NONE",
        freshness,
        recent_context,
        task_messages,
        {
            "prior_active_acceptance": exact_prior_acceptance,
            "prior_completed_result": exact_prior_completed,
        },
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
        task_messages,
        exact_continuity,
    ) = transcript_context(
        hook_input.get("transcript_path"), prompt
    )
    bundle = write_context_bundle(
        session_id,
        {
            "scope": "Exact root-visible conversation since the last accepted or cancelled objective.",
            "messages": task_messages,
            "prior_active_acceptance": exact_continuity["prior_active_acceptance"],
            "prior_completed_result": exact_continuity["prior_completed_result"],
        },
    )
    if bundle is None:
        emit(
            additional_context(
                "Reply exactly `Orchestration: ERROR; could not save the private task "
                "context`. Do not spawn."
            )
        )
        return 0
    bundle_path, bundle_revision = bundle
    context = DISPATCH_CONTEXT.replace("__ROOT_ROUTE__", root_route)
    previous_task_required = previous_task_context_required(prompt)
    context = context.replace(
        "__PREVIOUS_TASK_PROTOCOL__",
        PREVIOUS_TASK_PROTOCOL if previous_task_required else "",
    )
    context = context.replace(
        "__ROUTING_CONTEXT_PACKET_LINE__",
        "ROUTING_CONTEXT=<exact structured capsule created above>"
        if previous_task_required
        else "",
    )
    context = context.replace(
        "__LAST_TASK_CONTEXT_PACKET_LINE__",
        "LAST_TASK_CONTEXT=<exact full continuity block created above>"
        if previous_task_required
        else "",
    )
    context = context.replace("__PRIOR_ACTIVE_ACCEPTANCE__", prior_acceptance)
    context = context.replace("__PRIOR_COMPLETED_RESULT__", prior_completed)
    context = context.replace("__RECENT_CONTEXT_FRESHNESS__", recent_freshness)
    context = context.replace("__RECENT_CONTEXT__", recent_context)
    context = context.replace("__TASK_CONTEXT_BUNDLE__", str(bundle_path))
    context = context.replace("__TASK_CONTEXT_REVISION__", bundle_revision)
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
