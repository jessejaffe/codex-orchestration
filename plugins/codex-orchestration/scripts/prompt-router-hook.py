#!/usr/bin/env python3
"""Inject the fast chat-local Terra dispatch contract once per user prompt."""

from __future__ import annotations

import json
import os
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
MAX_FORK_TURNS = 64

DISPATCH_CONTEXT = """Orchestration is ON.
Root is the zero-judgment relay and alone calls agent-control tools.
On steer, interrupt and list this request's Orchestration children until none runs;
preserve unrelated work.
Executive context fork is `__FORK_TURNS__`, never full-history. At 1–63, copy the oldest
omitted user/assistant turn verbatim to `FOUNDATION_CONTEXT`.
Spawn `codex_orchestration_terra_executive` with `fork_turns: "__FORK_TURNS__"`, name
`gpt_5_6_terra_high_executive_<objective_slug>`, and `Score the request once; return only
the score protocol. Do not score this relay instruction.
USER_REQUEST: <verbatim current user prompt>` Do nothing first; never summarize.
Show `ORCHESTRATION_STATUS:` once as top-level commentary; keep the score immutable.
For TERRA_HIGH use its AGENT/TASK and retain Terra; do not follow up before implementation.
For SOL_HIGH spawn `codex_orchestration_sol_high_executive` with the same context
fork/foundation, name `gpt_5_6_sol_high_executive_<objective_slug>`, exact score, and
`USER_REQUEST: <verbatim current user prompt>`. It returns ORCHESTRATION_DELEGATE and
DIRECTIVE: `NONE` or at most 60 words, never restating the request.
Spawn mapped AGENT with the same context fork/foundation and exact TASK. Send
`USER_REQUEST: <verbatim prompt + attachment paths>` plus DIRECTIVE; never generate a
specification or restate the request. A producer's `VISUAL_VERIFICATION_PENDING` is not
failure. For frontend acceptance, root uses Browser only to cache-bypass production at
needed viewports; save screenshots and computed measurements; judge nothing. Follow up
the executive with `ACCEPTANCE_CHECK: <exact producer result>` and
`ROOT_VISUAL_EVIDENCE: <URL, viewport, screenshot paths, measurements>`. Return
ORCHESTRATION_ACCEPT. Other failure, incompleteness, or ORCHESTRATION_TAKEOVER ends routing.
Every routed final ends:
`Executive route: <GPT-5.6 Terra / High if TERRA_HIGH, else GPT-5.6 Sol / High>`
`Implementation route: <model / effort from status>`
On takeover add `Route takeover: Activated — <root model / effort>` before
`Complexity: <immutable score>/10`. Root appends these; never rely on executive formatting.
Say `Orchestration fallback: I’m finishing directly with your selected root model; no more handoffs.`
Reconcile and finish the request. Call no further agent-control tool. Before takeover,
never score, plan, implement, or judge acceptance."""


def safe_fork_turns(transcript_value: Any) -> str:
    """Keep up to 64 task turns without ever asking for a full-history fork."""
    if not isinstance(transcript_value, str):
        return "none"
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return "none"
    contexts = starts = 0
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
                if event.get("type") == "event_msg" and payload.get("type") == "task_started":
                    starts += 1
    except OSError:
        return "none"
    task_turns = max(contexts, starts)
    return "none" if task_turns <= 1 else str(min(MAX_FORK_TURNS, task_turns - 1))


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":")))


def control_request(prompt: str) -> tuple[bool, bool] | None:
    """Return (activate, has_work) for the last imperative control line."""
    lines = prompt.splitlines()
    matched: tuple[bool, bool] | None = None
    for index, raw_line in enumerate(lines):
        line = " ".join(raw_line.strip().lower().split())
        if line.startswith(("- ", "* ")):
            line = line[2:].lstrip()
        for command, activate in CONTROL_COMMANDS:
            if not line.startswith(command):
                continue
            tail = line[len(command) :]
            if tail and tail[0] not in CONTROL_SEPARATORS:
                continue
            tail = tail.lstrip(CONTROL_SEPARATORS)
            for connector in WORK_CONNECTORS:
                if tail == connector:
                    tail = ""
                    break
                if tail.startswith(connector + " "):
                    tail = tail[len(connector) :].lstrip(CONTROL_SEPARATORS)
                    break
            later_work = any(candidate.strip() for candidate in lines[index + 1 :])
            matched = (activate, bool(tail) or later_work)
            break
    return matched


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
    fork_turns = safe_fork_turns(hook_input.get("transcript_path"))
    emit(additional_context(prefix + DISPATCH_CONTEXT.replace("__FORK_TURNS__", fork_turns)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
