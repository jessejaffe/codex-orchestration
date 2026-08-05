#!/usr/bin/env python3
"""Inject the fast chat-local Terra dispatch contract once per user prompt."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from orchestration_state import is_active, transcript_role, write_state


ON_COMMANDS = {
    "turn orchestration on",
    "use orchestration",
    "use orchestration for this chat",
}
OFF_COMMANDS = {"turn orchestration off"}
SKILL_TOKEN = "$codex-orchestration:orchestration"

DISPATCH_CONTEXT = """Codex Orchestration is ON for this chat.
Act as a zero-judgment root dispatcher. For a user request containing work, your first
action must be one spawn of `codex_orchestration_terra_executive` with
`fork_turns: \"all\"`. Use a short task name and this exact message: `Own the current
user request end to end. You inherited the full chat. Determine the minimum capable
model and reasoning effort internally, preserve every stated constraint, execute or
delegate once, verify, and return the accepted result with Executive and Implementation
route lines.` Do not read a skill, score complexity, inspect files, make a plan,
summarize context, announce a route, or call another task tool before that spawn.
Terra owns low-band classification, routing, implementation, and acceptance only.
Wait event-first for its result. If it returns
`ESCALATE_TO_ROOT_SOL_HIGH: ROUTE=<SOL_LOW|SOL_MEDIUM|SOL_HIGH>; REASON=<reason>`,
Terra has done no task work: become the Sol / High executive. For SOL_LOW or
SOL_MEDIUM, spawn the named producer once with `fork_turns: "all"`, then verify and
accept its work; for SOL_HIGH, execute directly without a same-model spawn. Otherwise
do not duplicate Terra's work or acceptance. Preserve the actual executive and
implementation route lines in the final answer. A new user instruction replaces stale work; interrupt the active
Orchestration agent before dispatching the replacement."""


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":")))


def normalized_command(prompt: str) -> str:
    return re.sub(r"[.!?]+$", "", " ".join(prompt.strip().lower().split()))


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
    session_id = hook_input.get("session_id")
    prompt = hook_input.get("prompt")
    if not isinstance(session_id, str) or not isinstance(prompt, str):
        emit({"continue": True})
        return 0
    command = normalized_command(prompt)
    activation_only = command in ON_COMMANDS or command == SKILL_TOKEN
    activation = activation_only or command.startswith(SKILL_TOKEN + " ")
    control = activation or command in OFF_COMMANDS
    # Inactive ordinary prompts return without touching the transcript.
    if not control and not is_active(session_id):
        emit({"continue": True})
        return 0
    # Subagents share the parent session id. Never redispatch or change root state.
    if transcript_role(hook_input.get("transcript_path")) is not None:
        emit({"continue": True})
        return 0
    if command in OFF_COMMANDS:
        write_state(session_id, active=False)
        emit(
            additional_context(
                "Reply exactly `Orchestration: OFF for this chat`. Do not orchestrate "
                "the remainder of this prompt."
            )
        )
        return 0
    if activation:
        write_state(session_id, active=True)
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
    emit(additional_context(prefix + DISPATCH_CONTEXT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
