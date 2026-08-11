#!/usr/bin/env python3
"""Hermetic tests for chat-scoped activation and 0.8.11 experience verification."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def invoke(
    hook: Path,
    state: Path,
    session_id: str,
    prompt: str,
    transcript: Path | None = None,
    *,
    plugin_root: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": session_id,
        "prompt": prompt,
    }
    if transcript is not None:
        payload["transcript_path"] = str(transcript)
    environment = os.environ.copy()
    environment["CODEX_ORCHESTRATION_RUNTIME_STATE_DIR"] = str(state)
    if plugin_root:
        environment["PLUGIN_ROOT"] = str(hook.parent.parent)
    else:
        environment.pop("PLUGIN_ROOT", None)
    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    return json.loads(completed.stdout)


def context(result: dict[str, object]) -> str:
    specific = result.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return ""
    value = specific.get("additionalContext")
    return value if isinstance(value, str) else ""


def write_events(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events),
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-fast-dispatch.py <plugin-dir> <temp-dir>")
    plugin = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    state = temporary / "state"
    state.mkdir(parents=True, exist_ok=True)
    hook = plugin / "scripts" / "prompt-router-hook.py"

    inactive_id = "11111111-1111-1111-1111-111111111111"
    inactive = invoke(hook, state, inactive_id, "Explain this helper")
    if inactive != {"continue": True}:
        raise AssertionError(f"inactive prompt was not a no-op: {inactive!r}")

    active_id = "22222222-2222-2222-2222-222222222222"
    activation = invoke(hook, state, active_id, "Turn orchestration on")
    if context(activation) != "Reply exactly `Orchestration: ON for this chat` and do not spawn.":
        raise AssertionError(f"activation-only response changed: {activation!r}")

    routed = invoke(hook, state, active_id, "Fix the existing label")
    routed_context = context(routed)
    required = (
        "FIRST ACTION",
        "transparent parent relay",
        "Starting Terra / Max classification now.",
        "terra_orchestrator_<objective_slug>",
        "ORCHESTRATE_INIT",
        "PARENT_TASK=/root",
        "codex_orchestration_terra_supervisor",
        "read and obey the `developer_instructions`",
        "agents/codex-orchestration-terra-supervisor.toml",
        "Start no implementer or supervisor in root",
        "timeout_ms: 3600000",
        "ORCHESTRATION_STATE:",
        "ORCHESTRATION_UPDATE: <text>",
        "ORCHESTRATION_ROOT_VERIFY: CHECK=<bounded check>",
        "root-only Browser/visual tools",
        "cache-bypassed and at the requested viewport",
        "ROOT_VERIFICATION_RESULT: START=<observed starting condition>",
        "with `followup_task`",
        "ARTIFACTS=<URL or path, viewport, screenshot",
        "broaden the check, or judge acceptance",
        "ORCHESTRATION_BLOCKED: <text>",
        "no analysis or reasoning heading",
        "return only the text after that",
    )
    for value in required:
        if value not in routed_context:
            raise AssertionError(f"dispatch contract omits {value!r}")
    for obsolete in ("headless-grader.py", "--request-token", "grader-requests"):
        if obsolete in routed_context:
            raise AssertionError(f"dispatch retains obsolete headless path: {obsolete!r}")
    for noisy in (
        "is loading the full task context now",
        "Supervisor ready and staying read-only",
        "On timeout report active phase",
        "Complexity telemetry:",
        "normal agent waits are at most 45 seconds",
        "timeout_ms: 45000",
        "Still working on <actual user outcome>.",
        "CHECKPOINT_REVIEW:",
        "SUPERVISOR_CONTINUE:",
        "Implementation started with <implementer model>",
    ):
        if noisy in routed_context:
            raise AssertionError(f"dispatch retains noisy parent copy: {noisy!r}")
    if (state / "grader-requests").exists():
        raise AssertionError("dispatch still staged a grader request")
    if len(routed_context) > 3_500:
        raise AssertionError(f"dispatch contract regressed above the latency budget: {len(routed_context)}")

    combined_id = "33333333-3333-3333-3333-333333333333"
    combined = invoke(
        hook,
        state,
        combined_id,
        "Please turn orchestration on and add the new export feature",
    )
    combined_context = context(combined)
    if not combined_context.startswith("Begin with `Orchestration: ON for this chat`"):
        raise AssertionError("combined activation does not acknowledge ON")
    if "ORCHESTRATE_INIT" not in combined_context:
        raise AssertionError("combined activation did not select nested Terra orchestration")

    transcript = temporary / "root.jsonl"
    acceptance = (
        "ORCHESTRATION_ACCEPTANCE: OUTCOME=Ship export; MUST=implement and test; "
        "MUST_NOT=discard work; DESTINATIONS=repository; PROOF=focused tests"
    )
    write_events(
        transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Build CSV export"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "<environment_context>private wrapper</environment_context>",
                        }
                    ],
                },
            },
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-sol", "effort": "high"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [{"text": acceptance}],
                },
            },
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-terra", "effort": "max"},
            },
        ],
    )
    inherited = invoke(hook, state, active_id, "Also support JSON", transcript)
    inherited_context = context(inherited)
    for value in (
        "FORK=`2`",
        "CURRENT_ROOT_ROUTE: GPT-5.6 Terra / Max",
        acceptance,
    ):
        if value not in inherited_context:
            raise AssertionError(f"bounded inherited context omits {value!r}")
    if any(
        placeholder in inherited_context
        for placeholder in ("__FORK_TURNS__", "__ROOT_ROUTE__", "__FUSED_PROFILE_PATH__")
    ):
        raise AssertionError("dispatch placeholders leaked")
    if (state / "grader-requests").exists():
        raise AssertionError("inherited dispatch staged obsolete recent context")

    accepted_transcript = temporary / "accepted.jsonl"
    write_events(
        accepted_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [{"text": acceptance + "\nORCHESTRATION_ACCEPT: done"}],
                },
            },
        ],
    )
    accepted = invoke(hook, state, active_id, "New question", accepted_transcript)
    if "PRIOR_ACTIVE_ACCEPTANCE: NONE" not in context(accepted):
        raise AssertionError("accepted objective was not cleared")

    subagent_transcript = temporary / "subagent.jsonl"
    write_events(
        subagent_transcript,
        [
            {
                "type": "session_meta",
                "payload": {"agent_role": "default"},
            }
        ],
    )
    subagent = invoke(hook, state, active_id, "Nested prompt", subagent_transcript)
    if subagent != {"continue": True}:
        raise AssertionError("subagent was recursively dispatched")

    stale_plugin = invoke(
        hook,
        state,
        active_id,
        "Prompt from stale plugin hook",
        plugin_root=True,
    )
    if stale_plugin != {"continue": True}:
        raise AssertionError("stale plugin hook was not suppressed")

    off = invoke(hook, state, active_id, "Turn orchestration off and explain the label")
    off_context = context(off)
    if "Orchestration: OFF for this chat" not in off_context or "handle the remaining" not in off_context:
        raise AssertionError("combined OFF did not preserve remaining work")
    if invoke(hook, state, active_id, "Another prompt") != {"continue": True}:
        raise AssertionError("OFF state did not persist")

    print("PASS: chat controls, bounded acceptance, and 0.8.11 root experience verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
