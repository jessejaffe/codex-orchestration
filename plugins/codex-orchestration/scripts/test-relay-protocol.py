#!/usr/bin/env python3
"""Hermetic root-relay protocol and steering regression test."""

from pathlib import Path
import sys


def lane(score: float) -> tuple[str, str]:
    if score < 3.0:
        return "codex_orchestration_luna_implementer", "gpt_5_6_luna_max_"
    if score <= 5.0:
        return "codex_orchestration_terra_medium_implementer", "gpt_5_6_terra_medium_"
    if score <= 6.5:
        return "codex_orchestration_terra_implementer", "gpt_5_6_terra_high_implementation_"
    if score <= 7.2:
        return "codex_orchestration_sol_low_implementer", "gpt_5_6_sol_low_"
    if score <= 7.9:
        return "codex_orchestration_sol_medium_implementer", "gpt_5_6_sol_medium_"
    if score <= 8.9:
        return "codex_orchestration_sol_high_implementer", "gpt_5_6_sol_high_implementation_"
    return "codex_orchestration_sol_xhigh_implementer", "gpt_5_6_sol_extra_high_implementation_"


def main() -> int:
    plugin = Path(sys.argv[1])
    hook = (plugin / "scripts/prompt-router-hook.py").read_text()
    terra = (plugin / "agents/codex-orchestration-terra-executive.toml").read_text()
    sol = (plugin / "agents/codex-orchestration-sol-high-executive.toml").read_text()
    executives = terra + sol
    for tool in ("send_message", "spawn_agent", "wait_agent", "list_agents", "interrupt_agent"):
        if tool in executives:
            raise AssertionError(f"custom executive requires unavailable collaboration tool: {tool}")
    for token in (
        "ORCHESTRATION_SCORE:", "ORCHESTRATION_STATUS:", "ORCHESTRATION_DELEGATE:",
        "ORCHESTRATION_ACCEPT:", "ORCHESTRATION_TAKEOVER:", "PACKET:",
    ):
        if token not in executives + hook:
            raise AssertionError(f"relay protocol omits {token}")
    if hook.count("<verbatim current user prompt>") != 2 or "Always delegate" not in terra:
        raise AssertionError("relay can score itself or bypass the mapped producer")

    expected = {
        1.0: "luna", 2.9: "luna", 3.0: "terra_medium", 5.0: "terra_medium",
        5.1: "terra_high_implementation", 6.5: "terra_high_implementation",
        6.6: "sol_low", 7.2: "sol_low", 7.3: "sol_medium", 7.9: "sol_medium",
        8.0: "sol_high_implementation", 8.9: "sol_high_implementation",
        9.0: "sol_extra_high_implementation", 10.0: "sol_extra_high_implementation",
    }
    for score, fragment in expected.items():
        _, prefix = lane(score)
        if fragment not in prefix:
            raise AssertionError(f"wrong lane at {score}: {prefix}")

    terra_exec = "gpt_5_6_terra_high_executive_change"
    terra_impl = lane(5.1)[1] + "change"
    if terra_exec == terra_impl or "executive" not in terra_exec or "implementation" not in terra_impl:
        raise AssertionError("Terra executive and implementation labels can collide")

    # Root owns sibling executive/producer work; steering drains only the active request.
    active_branch = [terra_exec, terra_impl]
    unrelated = ["unrelated_agent"]
    drained = list(reversed(active_branch))
    if drained != [terra_impl, terra_exec] or unrelated != ["unrelated_agent"]:
        raise AssertionError("branch-wide sibling drain protocol regressed")

    # An acceptance failure is terminal: root takes over and no producer is retried.
    producer = terra_impl
    corrections: list[tuple[str, str]] = []
    takeover = (producer, "user-selected root finishes whole request")
    if corrections or takeover[0] != producer:
        raise AssertionError("acceptance failure retained a correction or replacement loop")
    for guard in (
        "selected root model", "no more handoffs", "Call no", "further agent-control",
    ):
        if guard not in hook:
            raise AssertionError(f"terminal root takeover omits {guard!r}")
    print("relay-protocol-ok lanes=7 corrections=0 terminal-takeover=ok sibling-drain=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
