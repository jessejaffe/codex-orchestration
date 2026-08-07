#!/usr/bin/env python3
"""Hermetic activation, continuity, ownership, and latency regression test."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SESSION = "11111111-1111-7111-8111-111111111111"


def call(script: Path, payload: dict[str, object], env: dict[str, str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=True,
        timeout=3,
    )
    return json.loads(completed.stdout)


def context(output: dict[str, object]) -> str:
    specific = output.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return ""
    value = specific.get("additionalContext")
    return value if isinstance(value, str) else ""


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-fast-dispatch.py <plugin-dir> <temp-dir>")
    plugin = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    scripts = temporary / "scripts"
    state = temporary / "state"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("orchestration_state.py", "prompt-router-hook.py"):
        shutil.copy2(plugin / "scripts" / name, scripts / name)

    root_transcript = temporary / "root.jsonl"
    root_transcript.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": SESSION}})
        + "\n"
        + json.dumps(
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-sol", "effort": "xhigh"},
            }
        )
        + "\n"
    )
    worker_transcript = temporary / "worker.jsonl"
    worker_transcript.write_text(
        json.dumps(
            {
                "type": "session_meta",
                "payload": {
                    "id": "22222222-2222-7222-8222-222222222222",
                    "parent_thread_id": SESSION,
                    "agent_role": "codex_orchestration_terra_executive",
                },
            }
        )
        + "\n"
    )
    env = os.environ.copy()
    env["CODEX_ORCHESTRATION_RUNTIME_STATE_DIR"] = str(state)
    prompt_hook = scripts / "prompt-router-hook.py"
    base = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": SESSION,
        "transcript_path": str(root_transcript),
    }

    stale_plugin_env = env.copy()
    stale_plugin_env["PLUGIN_ROOT"] = str(plugin)
    stale_plugin = call(
        prompt_hook,
        {**base, "prompt": "Turn Orchestration on and implement the request"},
        stale_plugin_env,
    )
    if stale_plugin != {"continue": True}:
        raise AssertionError("the former plugin-bundled hook can still duplicate routing")

    inactive = call(prompt_hook, {**base, "prompt": "ordinary request"}, env)
    if inactive != {"continue": True}:
        raise AssertionError(f"inactive chat was routed: {inactive!r}")
    mention_only = call(
        prompt_hook,
        {**base, "prompt": "Explain why I might turn orchestration on later"},
        env,
    )
    if mention_only != {"continue": True}:
        raise AssertionError("a narrative Orchestration mention was treated as a command")
    near_match = call(prompt_hook, {**base, "prompt": "Turn orchestration online"}, env)
    if near_match != {"continue": True}:
        raise AssertionError("an activation prefix without a command boundary was accepted")

    activated = call(prompt_hook, {**base, "prompt": "Turn Orchestration on"}, env)
    activation_context = context(activated)
    if "do not spawn" not in activation_context:
        raise AssertionError("activation-only contract is incomplete")
    if "codex_orchestration_terra_executive" in activation_context:
        raise AssertionError("activation-only prompt paid for the routing contract")
    state_file = state / f"{SESSION}.json"
    if not json.loads(state_file.read_text())["active"]:
        raise AssertionError("activation was not persisted for the chat")

    routed = call(prompt_hook, {**base, "prompt": "Implement the current request"}, env)
    routed_context = context(routed)
    for required in (
        "codex_orchestration_terra_executive",
        'Executive fork: `none`',
        'fork_turns: "none"',
        "numeric recent context",
        "never literal `all`",
        'name\n`gpt_5_6_terra_high_executive_<objective_slug>`',
        "zero-judgment relay",
        "alone calls agent-control tools",
        "Do nothing first",
        "codex_orchestration_sol_high_executive",
        "gpt_5_6_sol_high_executive_<objective_slug>",
        "codex_orchestration_sol_xhigh_executive",
        "gpt_5_6_sol_extra_high_executive_<objective_slug>",
        "Before next spawn show Terra's exact `ORCHESTRATION_STATUS:` in commentary",
        "never replace it",
        "drain only this request's Orchestration children",
        "inherited unfinished work stays in scope",
        "new prompt amends it",
        "ORCHESTRATION_DELEGATE",
        "DIRECTIVE",
        "at most 60 words",
        "Keep Terra's AGENT/TASK immutable; ignore remaps",
        "spawn those values",
        "no follow-up before implementation",
        "reuse fork",
        "never generate a\nspecification or restate the request",
        "ACCEPTANCE_CHECK:",
        "Routine verification: code/tests/deployed revision",
        "Browser/screenshots/visual handoff",
        "Visuals only for a reported mismatch",
        "explicit request",
        "or indispensable work",
        "absence never fails",
        "ORCHESTRATION_ACCEPT",
        "ORCHESTRATION_TAKEOVER",
        "Every routed final ends",
        "Executive route:",
        "Implementation route:",
        "Current root route from `turn_context`: `GPT-5.6 Sol / Extra High`",
        "On takeover add `Route takeover: Activated — GPT-5.6 Sol / Extra High`",
        "never `GPT-5 / default effort`",
        "Complexity:",
        "Root appends",
        "never rely on executive formatting",
        "selected root model",
        "no more handoffs",
        "Call no",
        "further agent-control",
    ):
        if required not in routed_context:
            raise AssertionError(f"dispatch contract omits {required!r}")
    for forbidden in (
        'fork_turns: "all"', "usage-receipt.py", "receipt", "PACKET:",
        "Create the execution packet", "exact PACKET",
        "Show `ORCHESTRATION_SCORE:` and `ORCHESTRATION_STATUS:`",
        "VISUAL_VERIFICATION_PENDING", "PRODUCER_VISUAL_EVIDENCE",
        "PRODUCTION_VISUAL_EVIDENCE",
        "__ROOT_ROUTE__", "<root model / effort>", "<exact label>",
    ):
        if forbidden in routed_context:
            raise AssertionError(f"dispatch contract retains {forbidden!r}")

    additive_transcript = temporary / "additive.jsonl"
    additive_transcript.write_text(
        root_transcript.read_text()
        + json.dumps(
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-sol", "effort": "xhigh"},
            }
        )
        + "\n"
    )
    additive = context(
        call(
            prompt_hook,
            {
                **base,
                "transcript_path": str(additive_transcript),
                "prompt": "I forgot to add one requirement",
            },
            env,
        )
    )
    if 'Executive fork: `2`' not in additive or 'fork_turns: "2"' not in additive:
        raise AssertionError("additive steering omitted the preceding active request")

    terra_transcript = temporary / "terra-root.jsonl"
    terra_transcript.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": SESSION}})
        + "\n"
        + json.dumps(
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-terra", "effort": "high"},
            }
        )
        + "\n"
    )
    terra_route = context(
        call(
            prompt_hook,
            {**base, "transcript_path": str(terra_transcript), "prompt": "work"},
            env,
        )
    )
    if "Route takeover: Activated — GPT-5.6 Terra / High" not in terra_route:
        raise AssertionError("takeover footer is hard-coded to the screenshot's root route")
    if "Route takeover: Activated — GPT-5.6 Sol / Extra High" in terra_route:
        raise AssertionError("takeover footer ignores the current task's root route")

    partial_transcript = temporary / "partial.jsonl"
    partial_transcript.write_text(
        root_transcript.read_text()
        + "".join(json.dumps({"type": "turn_context", "payload": {}}) + "\n" for _ in range(2))
    )
    partial = context(
        call(prompt_hook, {**base, "transcript_path": str(partial_transcript), "prompt": "work"}, env)
    )
    if 'Executive fork: `3`' not in partial or 'fork_turns: "3"' not in partial:
        raise AssertionError("short-chat context fork omitted the preceding active turn")

    long_transcript = temporary / "long.jsonl"
    long_transcript.write_text(
        root_transcript.read_text()
        + "".join(json.dumps({"type": "turn_context", "payload": {}}) + "\n" for _ in range(69))
    )
    bounded = context(
        call(prompt_hook, {**base, "transcript_path": str(long_transcript), "prompt": "work"}, env)
    )
    if 'Executive fork: `64`' not in bounded or 'fork_turns: "64"' not in bounded:
        raise AssertionError("long-chat context fork is not bounded at 64")

    worker = call(
        prompt_hook,
        {**base, "transcript_path": str(worker_transcript), "prompt": "nested work"},
        env,
    )
    if worker != {"continue": True}:
        raise AssertionError("a subagent was recursively dispatched")

    call(prompt_hook, {**base, "prompt": "Turn Orchestration off"}, env)
    if json.loads(state_file.read_text())["active"]:
        raise AssertionError("deactivation was not persisted")

    combined = call(
        prompt_hook,
        {
            **base,
            "prompt": (
                "My workflow is: edit, commit, and deploy.\n\n"
                "turn Orchestration On, remove the mission statement from the website."
            ),
        },
        env,
    )
    combined_context = context(combined)
    if not combined_context.startswith("Begin with `Orchestration: ON for this chat`"):
        raise AssertionError("activation plus work did not acknowledge activation")
    if "codex_orchestration_terra_executive" not in combined_context:
        raise AssertionError("activation plus work did not route the work")
    if not json.loads(state_file.read_text())["active"]:
        raise AssertionError("combined activation was not persisted")

    combined_off = call(
        prompt_hook,
        {
            **base,
            "prompt": "Orchestration off. Explain what happened in the last test.",
        },
        env,
    )
    combined_off_context = context(combined_off)
    if not combined_off_context.startswith("Begin with `Orchestration: OFF for this chat`"):
        raise AssertionError("deactivation plus work did not acknowledge deactivation")
    if "handle the remaining user work directly" not in combined_off_context:
        raise AssertionError("deactivation plus work discarded the remaining request")
    if json.loads(state_file.read_text())["active"]:
        raise AssertionError("combined deactivation was not persisted")

    period_combined = call(
        prompt_hook,
        {
            **base,
            "prompt": (
                "Turn orchestration on. Change the sleep and disk sleep settings "
                "from 45 minutes to 40 minutes."
            ),
        },
        env,
    )
    if "codex_orchestration_terra_executive" not in context(period_combined):
        raise AssertionError("period-separated activation plus work did not route")
    if not json.loads(state_file.read_text())["active"]:
        raise AssertionError("period-separated activation was not persisted")
    call(prompt_hook, {**base, "prompt": "Turn Orchestration off"}, env)

    # This executes only in release verification. It never runs in a user task.
    started = time.perf_counter()
    for _ in range(20):
        call(prompt_hook, {**base, "prompt": "ordinary request"}, env)
    elapsed = time.perf_counter() - started
    if elapsed > 2.0:
        raise AssertionError(f"inactive prompt hook exceeded 100 ms average: {elapsed:.3f}s")
    if len(routed_context.encode()) > 2_400:
        raise AssertionError("dispatch context exceeds the 2.4 KB fixed-cost budget")

    terra = (plugin / "agents" / "codex-orchestration-terra-executive.toml").read_text()
    for boundary in (
        "Rate the user request",
        "exactly one decimal",
        "1.0–2.9",
        "3.0–5.0",
        "5.1–6.5",
        "6.6–7.2",
        "7.3–7.9",
        "8.0–8.9",
        "9.0–10.0",
        "from this chat only",
        "routine, fully specified repository catch-up, commit, push, SSH deployment",
        "does not by itself require Sol",
        "gpt_5_6_luna_max_",
        "gpt_5_6_terra_medium_",
        "gpt_5_6_terra_high_implementation_",
        "gpt_5_6_sol_high_implementation_",
        "gpt_5_6_sol_extra_high_implementation_",
        "SOL_XHIGH",
        "ORCHESTRATION_SCORE: SCORE=",
        "ORCHESTRATION_STATUS: Complexity",
        "Return immediately with exactly two lines",
        "at most 20 words",
        "ORCHESTRATION_ACCEPT:",
        "ORCHESTRATION_TAKEOVER:",
        "Never generate an implementation",
        "untrusted claim",
        "combined active request is authoritative",
        "Only explicit cancellation or replacement",
        "task-appropriate probe",
        "hard budget of one task-tool call in total",
        "one fallback task-tool call",
        "malformed wrapper, command, or probe",
        "neither is outcome failure or",
        "never put shell `${...}` in a JavaScript template literal",
        "quoted\n`cmd` string",
        "requested end state already holds in every required destination",
        "successful no-op",
        "never require a new diff, commit, or deploy",
        "not necessarily the change's introduction point",
        "patch or provenance for current-tree or artifact evidence",
        "empty, silent, or non-diagnostic result is a malformed probe",
        "corrective REMAINING work require a named observation",
        "no observation contradicts it, ACCEPT it",
        "named observation proving a mistake, incomplete work, failed valid verification",
        "deployed revision or artifact contains the change",
        "forbidden for routine acceptance",
        "user-reported rendered mismatch",
        "use visual tools when available",
        "explicitly asks for visual inspection",
        "Missing visual evidence is never a TAKEOVER reason",
        "view_image",
        "root owns final route metadata",
        "zero correction loops",
    ):
        if boundary not in terra:
            raise AssertionError(f"Terra score-based route omits {boundary!r}")
    for stale in ("Be conservative: any", "safely low-band", "without emitting a numeric score"):
        if stale in terra:
            raise AssertionError(f"Terra retains categorical routing language: {stale!r}")
    if "fork_turns: all" in terra or 'fork_turns: "all"' in terra:
        raise AssertionError("Terra retains the rejected custom-role full-history fork")

    size = len(routed_context.encode())
    print(f"fast-dispatch-ok elapsed={elapsed:.3f}s context_bytes={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
