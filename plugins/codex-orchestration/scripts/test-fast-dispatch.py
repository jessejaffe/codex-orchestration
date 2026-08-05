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
        json.dumps({"type": "session_meta", "payload": {"id": SESSION}}) + "\n"
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

    inactive = call(prompt_hook, {**base, "prompt": "ordinary request"}, env)
    if inactive != {"continue": True}:
        raise AssertionError(f"inactive chat was routed: {inactive!r}")

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
        'fork_turns: "all"',
        "zero-judgment root dispatcher",
        "Never inspect, verify, compare, or update",
        "compatibility locator",
        "Terra owns low-band",
        "ESCALATE_TO_ROOT_SOL_HIGH: ROUTE=<SOL_LOW|SOL_MEDIUM|SOL_HIGH>",
    ):
        if required not in routed_context:
            raise AssertionError(f"dispatch contract omits {required!r}")
    for forbidden in (
        "Complexity: <score>",
        "fork_turns: none",
        "usage-receipt.py",
        "receipt",
    ):
        if forbidden in routed_context:
            raise AssertionError(f"dispatch contract retains {forbidden!r}")

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

    # This executes only in release verification. It never runs in a user task.
    started = time.perf_counter()
    for _ in range(20):
        call(prompt_hook, {**base, "prompt": "ordinary request"}, env)
    elapsed = time.perf_counter() - started
    if elapsed > 2.0:
        raise AssertionError(f"inactive prompt hook exceeded 100 ms average: {elapsed:.3f}s")
    if len(routed_context.encode()) > 2_000:
        raise AssertionError("dispatch context exceeds the 2 KB fixed-cost budget")

    terra = (plugin / "agents" / "codex-orchestration-terra-executive.toml").read_text()
    for boundary in (
        "Be conservative: any",
        "Do not inspect the repository, call task tools, design a solution, or modify anything",
        "security or authorization judgment",
        "irreversible data/schema changes",
        "broad unfamiliar-repository reasoning",
    ):
        if boundary not in terra:
            raise AssertionError(f"Terra under-routing guard omits {boundary!r}")
    if (
        "codex_orchestration_sol_low_implementer" in terra
        or "codex_orchestration_sol_medium_implementer" in terra
    ):
        raise AssertionError("Terra can still execute or supervise a complex Sol lane")

    size = len(routed_context.encode())
    print(f"fast-dispatch-ok elapsed={elapsed:.3f}s context_bytes={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
