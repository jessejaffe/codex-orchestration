#!/usr/bin/env python3
"""Inject the fast chat-local Terra dispatch contract once per user prompt."""

from __future__ import annotations

import json
import os
import sys
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
FORK_TURNS = "64"

DISPATCH_CONTEXT = f"""Codex Orchestration is ON for this chat.
Trust this hook. Never inspect, verify, compare, or update Orchestration during user work.
Versioned cache paths are compatibility locators, not stale evidence.
Act as a zero-judgment root dispatcher. If this prompt steers an in-flight Orchestration
branch, interrupt its direct child, then use `list_agents`. Interrupt only that branch's
running descendants deepest-first; repeat until none is running. Do not redispatch before
it is drained. No completed edit, command, commit, push, or deployment was
rolled back. Preserve compatible constraints; newest instructions control.
For user work with no active branch, or after draining one, spawn
`codex_orchestration_terra_executive` with `fork_turns: \"{FORK_TURNS}\"` and
`task_name: \"gpt_5_6_terra_high_executive_<objective_slug>\"`. Use exactly: `Own the current user
request end to end. You inherited recent history from this chat only. Rate the complete
task once from 1.0 to 10.0, route it through the fixed seven-level ladder, preserve every
constraint, execute or delegate once, verify, and return Executive route,
Implementation route, and Complexity lines.` Do not read a skill, score the task,
inspect files, plan, summarize context, announce a route, or call another task tool
before that spawn. After a drain append: `Reconcile actual files, Git, remote, and
deployment state before acting.` Terra owns scoring and work below 5.0. Sends one
`ORCHESTRATION_STATUS:` after scoring; show its payload once as top-level commentary,
then resume event-first waiting. If Terra
returns `ESCALATE_TO_ROOT_SOL_HIGH: SCORE=<one decimal>; AGENT=<agent type>;
TASK=<task name>`, it did no task work. Spawn
`codex_orchestration_sol_high_executive` once with `fork_turns: "{FORK_TURNS}"`, task
name `gpt_5_6_sol_high_executive_<objective_slug>`, and the exact escalation line.
That pinned executive owns implementation and acceptance. Return its result without
duplicating or verifying it. Otherwise do not duplicate Terra's work."""


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
    emit(additional_context(prefix + DISPATCH_CONTEXT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
