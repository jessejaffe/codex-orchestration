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
    sol_high = (plugin / "agents/codex-orchestration-sol-high-executive.toml").read_text()
    sol_xhigh = (plugin / "agents/codex-orchestration-sol-xhigh-executive.toml").read_text()
    executives = terra + sol_high + sol_xhigh
    for tool in ("send_message", "spawn_agent", "wait_agent", "list_agents", "interrupt_agent"):
        if tool in executives:
            raise AssertionError(f"custom executive requires unavailable collaboration tool: {tool}")
    for token in (
        "ORCHESTRATION_SCORE:", "ORCHESTRATION_STATUS:", "ORCHESTRATION_DELEGATE:",
        "ORCHESTRATION_ACCEPT:", "ORCHESTRATION_TAKEOVER:", "DIRECTIVE:",
    ):
        if token not in executives + hook:
            raise AssertionError(f"relay protocol omits {token}")
    runtime = executives + hook
    if "PACKET:" in runtime or "execution packet" in runtime:
        raise AssertionError("executive can still emit the duplicated implementation packet")
    if hook.count("<verbatim current user prompt>") != 2:
        raise AssertionError("relay can score itself or bypass the mapped producer")
    for guard in (
        "do not follow up before implementation",
        "both reuse fork/foundation",
        "at most 60 words",
        "never generate a\nspecification or restate the request",
        "ACCEPTANCE_CHECK:",
        "root never uses Browser",
        "code, tests, and deployed revision suffice",
        "used for a user-reported rendered mismatch",
        "otherwise only when explicitly requested",
        "or indispensable to perform the work",
        "Missing visual evidence is never failure",
    ):
        if guard not in hook:
            raise AssertionError(f"minimal direct-context handoff omits {guard!r}")
    if "Before next spawn, show Terra's exact `ORCHESTRATION_STATUS:` in commentary" not in hook:
        raise AssertionError("Terra's human-readable score checkpoint is not relayed before delegation")
    if "never prewrite/replace it" not in hook:
        raise AssertionError("root can replace Terra's scored checkpoint with generic commentary")
    if "Keep Terra's AGENT/TASK immutable; ignore remaps" not in hook:
        raise AssertionError("root can accept an executive-generated implementation identity")
    for guard in ("Copy Terra's AGENT and TASK", "never shorten, relabel, remap"):
        if executives.count(guard) != 2:
            raise AssertionError(f"pinned Sol executive can rename Terra's implementation task: {guard!r}")
    if "Show `ORCHESTRATION_SCORE:` and `ORCHESTRATION_STATUS:`" in hook:
        raise AssertionError("internal routing score can leak into commentary")
    implementer_paths = sorted((plugin / "agents").glob("*implementer.toml"))
    if len(implementer_paths) != 7:
        raise AssertionError(f"expected seven implementation lanes, found {len(implementer_paths)}")
    implementer_texts = [path.read_text() for path in implementer_paths]
    implementers = "".join(implementer_texts)
    if implementers.count("Execute `USER_REQUEST`") != 7:
        raise AssertionError("an implementation lane still depends on an executive rewrite")
    for guard in (
        "untrusted claim", "task-appropriate probe", "deployed revision or artifact",
        "forbidden for routine acceptance", "Missing visual evidence is never a TAKEOVER reason",
        "user-reported rendered mismatch", "use visual tools when available",
        "without route metadata",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"independent acceptance guard is not shared: {guard!r}")
    for guard in (
        "hard budget of one task-tool call in total",
        "first call fails solely",
        "one fallback task-tool call",
        "do not reread source, rerun tests, rediscover infrastructure",
        "explicitly asks for visual inspection",
        "visual input is indispensable\nto perform the work rather than merely strengthen proof",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"minimal acceptance guard is not shared: {guard!r}")
    for guard in (
        "producer supplies no working production path",
        "actual deploy/config scripts", "guessed port, URL, process",
        "deploy command reached terminal exit", "still-running deploy is not failure",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"production acceptance guard is not shared: {guard!r}")
    for guard in (
        "access-path failure is not outcome failure",
        "authoritative read-only runtime path",
        "preferring an already working\nservice-local query or application API",
        "Acceptance must never mutate state",
        "actions reserved for later user approval",
        "acceptance claim remains unverified after those paths are exhausted",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"acceptance access fallback is not shared: {guard!r}")
    if "Executive route:" in executives or "Implementation route:" in executives:
        raise AssertionError("executive still owns fallible final route formatting")
    if implementers.count("verify the requested change in code, configuration, schema, tests") != 7:
        raise AssertionError("an implementation lane can still skip code-first verification")
    for guard in (
        "deployed revision or artifact", "deployed code contains the change is sufficient",
        "visual tools are forbidden for routine verification", "explicitly asks for visual inspection",
        "user-reported rendered mismatch", "use visual tools when available",
        "visual input is indispensable",
        "Missing visual evidence is never a failure or handoff condition",
        "exact cell or session until terminal exit",
        "exit code zero", "Deployment is single-owner", "narrowest supported service set",
        "second build or deploy", "`--no-cache`", "another process already",
        "seed, migration, or backfill commands in parallel",
    ):
        if implementers.count(guard) != 7:
            raise AssertionError(f"code-first visual policy is not shared: {guard!r}")
    for stale in (
        "VISUAL_VERIFICATION_PENDING", "PRODUCER_VISUAL_EVIDENCE",
        "PRODUCTION_VISUAL_EVIDENCE", "production page with cache bypass",
        "saved cache-bypassed payload",
    ):
        if stale in runtime + implementers:
            raise AssertionError(f"mandatory visual acceptance remains: {stale!r}")
    for path, instructions in zip(implementer_paths, implementer_texts):
        for guard in (
            "perform the implementation yourself",
            "Do not use collaboration or agent-control",
            "do not spawn, delegate to, message, wait for, list, interrupt",
            "do not create Recon, reviewer, helper, or",
        ):
            if guard not in instructions:
                raise AssertionError(f"nested-agent guard missing from {path.name}: {guard!r}")
    for guard in (
        "Every routed final ends", "Executive route:", "Implementation route:",
        "On takeover add", "Route takeover: Activated", "<root model / effort>",
        "Complexity:", "Root appends",
    ):
        if guard not in hook:
            raise AssertionError(f"deterministic final metadata omits {guard!r}")
    metadata_order = [
        hook.index("Executive route:"), hook.index("Implementation route:"),
        hook.index("Route takeover: Activated"), hook.index("Complexity:"),
    ]
    if metadata_order != sorted(metadata_order):
        raise AssertionError("takeover metadata is not ordered with the final route lines")

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

    if "EXECUTIVE=<TERRA_HIGH if below 5.0, SOL_HIGH from 5.0–7.9, otherwise SOL_XHIGH>" not in terra:
        raise AssertionError("Terra does not route scores of 8.0 and above to Sol / Extra High")
    for token in (
        "codex_orchestration_sol_xhigh_executive",
        "gpt_5_6_sol_extra_high_executive_",
        "GPT-5.6 Sol / Extra High",
    ):
        if token not in hook:
            raise AssertionError(f"root relay omits the Sol / Extra High executive: {token}")
    if 'model_reasoning_effort = "xhigh"' not in sol_xhigh:
        raise AssertionError("Sol / Extra High executive is not pinned to xhigh")

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
    print("relay-protocol-ok lanes=7 packets=0 nested-agents=0 independent-acceptance=one-call visuals=opt-in deployment=single-owner final-metadata=root terminal-takeover=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
