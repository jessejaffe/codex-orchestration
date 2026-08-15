#!/usr/bin/env python3
"""Inject one chat-local root contract plus a compact per-turn routing packet."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from orchestration_state import (
    is_active,
    read_state,
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
MAX_COMPLETED_TASK_OUTCOMES = 20
CONTEXT_BUNDLE_SCOPE = (
    "Concise whole-chat representation: chronological user requests and substantive "
    "root-visible assistant facts, plus canonical outcomes for the 20 most recent "
    "completed tasks."
)
TRANSIENT_ASSISTANT_MESSAGES = {
    "starting the task",
    "working on it",
    "thinking",
}
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
ROUTE_FOOTER_PATTERN = re.compile(
    r"(?:\A|\n)## Route[ \t]*\r?\n"
    r"- Class: [^\r\n]+\r?\n"
    r"- Implementation: [^\r\n]+\r?\n"
    r"- Root: [^\r\n]+\Z"
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

ROOT_CONTRACT_REVISION = "0.9.0-direct-launch-v3"
ROOT_CONTRACT = """CODEX_ORCHESTRATION_ROOT_CONTRACT
REVISION=0.9.0-direct-launch-v3

Orchestration ON (0.9.0). Parent classifies in its first response; one selected implementer owns the
task end to end. Do not spawn a classifier. Root only performs the requested terminal visual check.

LAUNCH UX — Keep the desktop activity label exactly `Thinking`; no dynamic status. For a combined
activation-and-work prompt, the only pre-launch text is exactly `Orchestration: ON for this chat`.
For an already-active chat, emit no pre-launch commentary. Launch directly; never narrate analysis,
classification, planning, packet construction, tool choice, setup, tracing, or the selected lane.
Never print or echo the packet. The titled child
task is the only startup progress indicator.

ROUTE_AND_EXECUTE — classify internally from the current request and TURN, then
immediately spawn exactly one mapped implementer. Do not emit a separate classification message
or add a classification wait. Create this exact internal packet:
## Classification
- Relationship: <New|Amend|Replace|Cancel>
- Active objective: <concise objective>
- Work class: <friendly class>
- Complexity: <1.0-10.0 / 10>
- Why: <brief reason>

If essential information is missing, ask one concise user question and stop. Map Work class:

- Read-only: Luna / Max
- Standard artifact: Luna / Max
- Design artifact: Terra / Max
- Small tweak: Luna / Max
- Big tweak: Terra / Max
- Small build: Terra / Max
- Big build: Sol / High

ROLE — Terra: `codex_orchestration_terra_implementer`; Luna:
`codex_orchestration_luna_implementer`; Sol: `codex_orchestration_sol_high_implementer`.
If unavailable, read its matching `__AGENTS_DIR__` profile and use identically pinned `worker`.

DIRECT DESKTOP LAUNCH — After creating `packet`, immediately use this JavaScript. Do not first inspect
`ALL_TOOLS`, discover a schema, call generic `spawn_agent`, or make a separate planning turn:
```js
const launch = await tools.multi_agent_v1__spawn_agent({
  agent_type: <selected mapped custom agent>,
  fork_context: false,
  message: packet,
});
await tools.codex_app__set_thread_title({
  threadId: launch.agent_id,
  title: <exact mapped child title>,
});
text(JSON.stringify({agent_id: launch.agent_id}));
```
Map titles exactly: `GPT-5.6 Luna / Max`, `GPT-5.6 Terra / Max`, `GPT-5.6 Sol / High`.
The host may briefly create a nickname, but the immediate title call replaces it with model identity;
never output or report the nickname.

If `PREVIOUS_TASK_CONTEXT_REQUIRED: YES`, use `list_threads` then `read_thread` once: exclude this
task, choose newest same-project/directory task, and ask if ambiguous. Give only the implementer
`LAST_TASK_CONTEXT` (max 6,000 characters: final, relevant turns, paths, decisions, open work).

Silently load `codex_app__load_workspace_dependencies` once only when TURN says YES; otherwise use
NONE.

Spawn exactly one mapped implementer. Never spawn a supervisor, reviewer, grader, classifier, or a
second writer. Send the full private handoff; never shorten, summarize, or omit its context fields:
END_TO_END_WORK
CLASSIFICATION=<exact Markdown>
PRIOR_COMPLETED_RESULT=<TURN value>
TASK_CONTEXT_BUNDLE=<TURN path>
TASK_CONTEXT_REVISION=<TURN revision>
WORKSPACE_DEPENDENCIES=<exact result or NONE>
CURRENT_ROOT_ROUTE=<TURN value>
IMPLEMENTATION_ROUTE=<friendly selected model lane>
INSPECTION_POLICY=Group closely related low-output checks for one immediate question in one pass; keep unrelated or noisy checks separate.
LAST_TASK_CONTEXT=<exact full continuity block created above, only when TURN requires it>
The bundle is the complete private concise whole-chat context: every request and substantive
root-visible fact in chronological order, plus the 20 newest canonical outcomes. Pass its
path/revision unchanged; TURN values do not replace it. After launch, wait directly with
`tools.multi_agent_v1__wait_agent({targets:[<agent_id>], timeout_ms:3600000})`; repeat silently on
timeout without tool discovery. The implementer owns
scope interpretation, implementation, verification, and authorized release. It owns the final
report unless it makes the terminal visual handoff below.

If the user changes or cancels current work, stop or redirect obsolete work.

PREMISE MISMATCH — Inspect only cited evidence; return concise `## Premise review` (Confirmed,
Evidence, Reason) to the same implementer. Do not create another role.

On `## Root verification needed`, do one terminal root-only Browser/visual check against its Ground
truth and Source. Missing/ambiguous identity, wording, or links fails; never infer. For live pages,
cache-bypass at the requested viewport; capture screenshot and decisive visible/DOM/computed proof.
Judge pass, fail, or blocked; end without editing, spawning, or `followup_task`. Use the handoff's
Work report as primary content, preserving delivered work/proof/next step. Explain visual failure
after the work account; never replace it.

FINAL-REPORT VOICE — User-facing report changes. Use slightly less technical language:
lead with the outcome and briefly explain jargon. Keep internal work technical; preserve exact
details.

Every terminal response is a natural-language report: what happened, work done/found, outcome,
decisive evidence, and relevant links, limits, or open work; visual reports include pass/fail/blocked.
No fixed headings or field list except `## Next step`. Never call the implementer to fix structure.
Preserve the report body and locally add only a missing outcome or required ending from CLASSIFICATION/TURN.
Every completed user-facing task ends with this mandatory next-step section immediately above its
compact route footer. State one legitimate follow-on action; when none is warranted, write exactly
`None — no next step is needed.`:
## Next step
<one legitimate follow-on action, or None — no next step is needed.>

## Route
- Class: <friendly class>
- Implementation: <IMPLEMENTATION_ROUTE>
- Root: <CURRENT_ROOT_ROUTE>
Never include supervision. The selected implementer places this ending after its report; root uses it
for terminal visual results. RELAY valid nonvisual reports verbatim: preserve Markdown, wording,
detail, order, links; never summarize, assess, append, tool-call, or request a rewrite. Activation
is not completion. Never expose packets, waits, or contracts."""

TURN_CONTEXT = """CODEX_ORCHESTRATION_TURN
ROOT_CONTRACT_REVISION: 0.9.0-direct-launch-v3
TASK_CONTEXT_BUNDLE: __TASK_CONTEXT_BUNDLE__
TASK_CONTEXT_REVISION: __TASK_CONTEXT_REVISION__
PRIOR_ACTIVE_ACCEPTANCE: __PRIOR_ACTIVE_ACCEPTANCE__
PRIOR_COMPLETED_RESULT: __PRIOR_COMPLETED_RESULT__
RECENT_CONTEXT_FRESHNESS: __RECENT_CONTEXT_FRESHNESS__
RECENT_CONTEXT: __RECENT_CONTEXT__
PREVIOUS_TASK_CONTEXT_REQUIRED: __PREVIOUS_TASK_CONTEXT_REQUIRED__
WORKSPACE_DEPENDENCIES_REQUIRED: __WORKSPACE_DEPENDENCIES_REQUIRED__
CURRENT_ROOT_ROUTE: __ROOT_ROUTE__
CURRENT_USER_REQUEST=INHERITED_CURRENT_QUERY

Apply the invariant Codex Orchestration root contract already installed in this chat. Classify
internally and launch exactly one implementer as the first action, with no pre-launch commentary."""


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


def unwrap_final_answer(value: str) -> str:
    """Drop an internal child-to-root transport envelope from a final report."""
    lines = value.strip().splitlines()
    if not lines or lines[0].strip() != "Message Type: FINAL_ANSWER":
        return value.strip()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "Payload:" and index + 1 < len(lines):
            return "\n".join(lines[index + 1 :]).strip()
    return value.strip()


def strip_route_footer(value: str) -> str:
    """Remove the repeated routing receipt from a stored historical outcome."""
    match = ROUTE_FOOTER_PATTERN.search(value.rstrip())
    return value[: match.start()].rstrip() if match is not None else value.strip()


def collapse_repeated_content(value: str) -> str:
    """Replace pathological repeated filler without dropping the distinct wording."""
    value = re.sub(
        r"(?P<char>[^\n])(?P=char){63,}",
        lambda match: f"{match.group('char')}×{len(match.group())}",
        value,
    )
    repeated_phrase = re.compile(
        r"(?P<unit>\b(?:[\w/-]+[ \t]+){1,5}[\w/-]+\b)"
        r"(?P<repeats>(?:[ \t]+(?P=unit)){2,})"
    )

    def replace_phrase(match: re.Match[str]) -> str:
        unit = match.group("unit")
        return f"{unit} [repeated {match.group(0).count(unit)}×]"

    return repeated_phrase.sub(replace_phrase, value)


def deduplicate_paragraphs(value: str) -> str:
    """Keep one copy of each exact paragraph in a report-like value."""
    paragraphs = re.split(r"\n[ \t]*\n", value.strip())
    retained: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        normalized = paragraph.strip()
        if normalized and normalized not in seen:
            retained.append(normalized)
            seen.add(normalized)
    return "\n\n".join(retained)


def without_leading_heading(section: str) -> str:
    """Remove a report-only heading while retaining its meaningful contents."""
    lines = section.splitlines()
    if lines and lines[0].strip().startswith("## "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def canonical_task_outcome(value: str) -> str:
    """Build a compact, faithful outcome record from a final report or handoff."""
    canonical = strip_route_footer(unwrap_final_answer(value))
    continuity = markdown_section(canonical, "Continuity")
    if continuity is not None and markdown_section(canonical, "Completed") is not None:
        canonical = without_leading_heading(continuity)
    canonical = deduplicate_paragraphs(canonical)
    canonical = collapse_repeated_content(canonical)
    return canonical.strip()


def completed_report_outcome(message: str) -> str | None:
    """Return the canonical outcome encoded by a terminal report, if present."""
    if has_route_footer(message):
        return canonical_task_outcome(message)
    completed = markdown_section(message, "Completed")
    if completed is None:
        return None
    return canonical_task_outcome(markdown_section(message, "Continuity") or completed)


def is_transient_assistant_message(message: str) -> bool:
    """Exclude status-only root commentary that conveys no durable chat fact."""
    normalized = bounded_single_line(message, 256).casefold().rstrip(".!")
    return normalized in TRANSIENT_ASSISTANT_MESSAGES


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


def has_route_footer(message: str) -> bool:
    """Return whether trusted final output ends in the required route receipt."""
    return ROUTE_FOOTER_PATTERN.search(message.rstrip()) is not None


def append_completed_task_outcome(outcomes: list[str], outcome: str | None) -> None:
    """Keep one canonical outcome per task, retaining the newest bounded history."""
    if not outcome:
        return
    canonical_outcome = canonical_task_outcome(outcome)
    if not canonical_outcome:
        return
    if outcomes and canonical_outcome == outcomes[-1]:
        return
    outcomes.append(canonical_outcome)
    del outcomes[:-MAX_COMPLETED_TASK_OUTCOMES]


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
) -> tuple[
    str,
    str,
    str,
    str,
    str,
    list[dict[str, Any]],
    list[str],
    dict[str, str | None],
]:
    """Return bounded routing state plus a concise private whole-chat record."""
    exact_current_prompt = strip_injected_user_prefix(current_prompt).strip()
    if not isinstance(transcript_value, str):
        return (
            "unavailable",
            "NONE",
            "NONE",
            "NONE",
            "NONE",
            [{"role": "user", "content": exact_current_prompt, "current": True}],
            [],
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
            [],
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
    chat_messages: list[dict[str, Any]] = []
    completed_task_outcomes: list[str] = []
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
                    root_visible_outcome = (
                        completed_report_outcome(conversation[1])
                        if conversation[0] == "assistant"
                        else None
                    )
                    if root_visible_outcome is not None:
                        exact_prior_completed = root_visible_outcome
                        prior_completed = bounded_single_line(
                            exact_prior_completed, MAX_PRIOR_COMPLETED_CHARS
                        )
                        prior_acceptance = None
                        exact_prior_acceptance = None
                        has_completion = True
                        post_completion_tail = []
                        append_completed_task_outcome(
                            completed_task_outcomes, exact_prior_completed
                        )
                    elif not (
                        conversation[0] == "assistant"
                        and is_transient_assistant_message(conversation[1])
                    ):
                        chat_messages.append(
                            {"role": conversation[0], "content": conversation[1]}
                        )
                message = agent_message_text(event)
                completed_outcome: str | None = None
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

                completed_outcome = completed_report_outcome(message)
                if completed_outcome is not None:
                    exact_prior_completed = completed_outcome
                    prior_completed = bounded_single_line(
                        exact_prior_completed, MAX_PRIOR_COMPLETED_CHARS
                    )
                    prior_acceptance = None
                    exact_prior_acceptance = None
                    has_completion = True
                    post_completion_tail = []
                    completed_outcome = exact_prior_completed

                message_lines = message.splitlines()
                for index, message_line in enumerate(message_lines):
                    if message_line.startswith(
                        "ORCHESTRATION_RELATION: RELATION=CANCEL;"
                    ):
                        cancelled = True
                    if (
                        message_line.startswith("ORCHESTRATION_ACCEPTANCE: OUTCOME=")
                        and "; MUST=" in message_line
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
                        exact_handoff = canonical_task_outcome(
                            message_line.removeprefix("ORCHESTRATION_HANDOFF: ")
                        )
                        completion_handoff = bounded_single_line(
                            exact_handoff, MAX_PRIOR_COMPLETED_CHARS
                        )
                        completion_handoffs[completion_scope] = completion_handoff
                        exact_completion_handoffs[completion_scope] = exact_handoff
                        prior_completed = completion_handoff
                        exact_prior_completed = exact_handoff
                    elif message_line.startswith("ORCHESTRATION_ACCEPT:"):
                        prior_acceptance = None
                        exact_prior_acceptance = None
                        accepted_result = canonical_task_outcome(
                            "\n".join(message_lines[index:]).removeprefix(
                                "ORCHESTRATION_ACCEPT:"
                            )
                        )
                        exact_prior_completed = exact_completion_handoffs.get(
                            completion_scope
                        ) or accepted_result.strip()
                        prior_completed = completion_handoffs.get(
                            completion_scope
                        ) or bounded_single_line(accepted_result, MAX_PRIOR_COMPLETED_CHARS)
                        has_completion = True
                        post_completion_tail = []
                        completed_outcome = exact_prior_completed
                append_completed_task_outcome(completed_task_outcomes, completed_outcome)
                if cancelled:
                    prior_acceptance = None
                    exact_prior_acceptance = None
    except OSError:
        return (
            "unavailable",
            "NONE",
            "NONE",
            "NONE",
            "NONE",
            [{"role": "user", "content": exact_current_prompt, "current": True}],
            [],
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
        chat_messages
        and chat_messages[-1]["role"] == "user"
        and chat_messages[-1]["content"].strip() == exact_current_prompt
    ):
        chat_messages.append(
            {"role": "user", "content": exact_current_prompt, "current": True}
        )
    else:
        chat_messages[-1]["current"] = True
    return (
        root_route,
        prior_acceptance or "NONE",
        prior_completed or "NONE",
        freshness,
        recent_context,
        chat_messages,
        completed_task_outcomes,
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
        "Reply in commentary exactly `Orchestration: ON for this chat`, with no other "
        "pre-launch text, then immediately execute the direct launch.\n"
        if activation
        else ""
    )
    (
        root_route,
        prior_acceptance,
        prior_completed,
        recent_freshness,
        recent_context,
        chat_messages,
        completed_task_outcomes,
        exact_continuity,
    ) = transcript_context(
        hook_input.get("transcript_path"), prompt
    )
    bundle = write_context_bundle(
        session_id,
        {
            "scope": CONTEXT_BUNDLE_SCOPE,
            "messages": chat_messages,
            "completed_task_outcomes": completed_task_outcomes,
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
    turn_context = TURN_CONTEXT.replace("__ROOT_ROUTE__", root_route)
    turn_context = turn_context.replace(
        "__PREVIOUS_TASK_CONTEXT_REQUIRED__",
        "YES" if previous_task_context_required(prompt) else "NO",
    )
    turn_context = turn_context.replace("__PRIOR_ACTIVE_ACCEPTANCE__", prior_acceptance)
    turn_context = turn_context.replace("__PRIOR_COMPLETED_RESULT__", prior_completed)
    turn_context = turn_context.replace("__RECENT_CONTEXT_FRESHNESS__", recent_freshness)
    turn_context = turn_context.replace("__RECENT_CONTEXT__", recent_context)
    turn_context = turn_context.replace("__TASK_CONTEXT_BUNDLE__", str(bundle_path))
    turn_context = turn_context.replace("__TASK_CONTEXT_REVISION__", bundle_revision)
    turn_context = turn_context.replace(
        "__WORKSPACE_DEPENDENCIES_REQUIRED__",
        workspace_dependencies_required(prompt),
    )
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    agents_dir = codex_home / "agents"
    state = read_state(session_id)
    contract_installed = state.get("contract_revision") == ROOT_CONTRACT_REVISION
    contract = ""
    if not contract_installed:
        contract = ROOT_CONTRACT.replace("__AGENTS_DIR__", str(agents_dir)) + "\n\n"
        if not write_state(
            session_id,
            active=True,
            contract_revision=ROOT_CONTRACT_REVISION,
        ):
            emit(
                additional_context(
                    "Reply exactly `Orchestration: ERROR; could not save the root "
                    "contract state`. Do not spawn."
                )
            )
            return 0
    emit(additional_context(prefix + contract + turn_context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
