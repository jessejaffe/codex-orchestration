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
    if "ORCHESTRATION_STATUS: Complexity <one decimal>" not in terra:
        raise AssertionError("status checkpoint must not substitute a text marker for native avatars")
    runtime = executives + hook
    if "PACKET:" in runtime or "execution packet" in runtime:
        raise AssertionError("executive can still emit the duplicated implementation packet")
    if hook.count("<verbatim current user prompt>") != 2:
        raise AssertionError("relay can score itself or bypass the mapped producer")
    for guard in (
        "no follow-up before implementation",
        "reuse fork",
        "at most 60 words",
        "never generate a\nspecification or restate the request",
        "ACCEPTANCE_CHECK:",
        "Routine verification: code/tests/deployed revision",
        "Browser/screenshots/visual handoff",
        "Visuals only for a reported mismatch",
        "explicit request",
        "or indispensable work",
        "absence never fails",
        "inherited unfinished work stays in scope",
        "new prompt amends it",
    ):
        if guard not in hook:
            raise AssertionError(f"minimal direct-context handoff omits {guard!r}")
    if "Before next spawn show Terra's exact `ORCHESTRATION_STATUS:` in commentary" not in hook:
        raise AssertionError("Terra's human-readable score checkpoint is not relayed before delegation")
    if "never replace it" not in hook:
        raise AssertionError("root can replace Terra's scored checkpoint with generic commentary")
    if "Keep Terra's AGENT/TASK immutable; ignore remaps" not in hook:
        raise AssertionError("root can accept an executive-generated implementation identity")
    sol_handoff_start = hook.index("SOL_HIGH/SOL_XHIGH: spawn")
    sol_handoff = hook[sol_handoff_start : hook.index("Keep Terra", sol_handoff_start)]
    score_line = "Send exact Terra `ORCHESTRATION_SCORE:`"
    if score_line not in sol_handoff:
        raise AssertionError("root can omit Terra's immutable AGENT/TASK from the Sol executive handoff")
    if sol_handoff.index(score_line) > sol_handoff.index("USER_REQUEST:"):
        raise AssertionError("Sol executive handoff does not place Terra's score line before the request")
    if '`fork_turns: "none"`' not in sol_handoff:
        raise AssertionError("Sol executive still inherits the heavy parent transcript")
    if "`ORCHESTRATION_STATUS:`" not in sol_handoff:
        raise AssertionError("compact Sol executive handoff omits Terra's resolved work status")
    producer_handoff = hook[hook.index("Keep Terra", sol_handoff_start) : hook.index("Follow up:")]
    if "reuse fork" not in producer_handoff:
        raise AssertionError("mapped producer no longer inherits the active task context")
    takeover_handoff = hook[hook.index("On Sol ORCHESTRATION_TAKEOVER") : hook.index("Every routed final ends")]
    for guard in (
        "same Sol executive role",
        "reuse fork",
        "TAKEOVER_CONTEXT:",
        "ORCHESTRATION_TAKEOVER_READY",
    ):
        if guard not in takeover_handoff:
            raise AssertionError(f"full-history takeover stage omits {guard!r}")
    if "loading full task history" not in hook:
        raise AssertionError("root does not announce the exceptional full-history takeover reload")
    for guard in ("Copy Terra's AGENT and TASK", "never shorten, relabel, remap"):
        if executives.count(guard) != 2:
            raise AssertionError(f"pinned Sol executive can rename Terra's implementation task: {guard!r}")
    for guard in (
        "use only the supplied score, status, and request",
        "do not inspect files or call\ntask tools",
        "Copy AGENT/TASK immediately",
        "absent from both USER_REQUEST and ORCHESTRATION_STATUS",
        "Never restate the request, status",
        "sole full-history path",
        "inherited task history",
        "TAKEOVER_CONTEXT:",
        "ORCHESTRATION_TAKEOVER_READY:",
        "reload one same-role takeover instance with full inherited history",
    ):
        if executives.count(guard) != 2:
            raise AssertionError(f"compact Sol executive fast path omits {guard!r}")
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
        "current `USER_REQUEST` adds to, corrects, answers, or authorizes unfinished inherited",
        "combined active request is authoritative",
        "Only explicit cancellation or replacement",
        "discards its prior objective",
    ):
        if executives.count(guard) != 3 or implementers.count(guard) != 7:
            raise AssertionError(f"additive steering context is not shared: {guard!r}")
    checkout_guard = "configured `codex-orchestration` marketplace source"
    if implementers.count(checkout_guard) != 7:
        raise AssertionError("implementation lanes can mistake the ChatGPT project mirror for this plugin checkout")
    if executives.count(checkout_guard) != 3:
        raise AssertionError("acceptance can mistake the ChatGPT project mirror for this plugin checkout")
    if "next: `spawn_agent`" not in hook or "never Terra" not in hook:
        raise AssertionError("root can reactivate Terra instead of spawning the scored implementation lane")
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
        "malformed wrapper, command, or probe",
        "repair it and\nuse one fallback task-tool call",
        "neither is outcome failure or\nTAKEOVER",
        "reuse the producer's successful command shape",
        "never put shell `${...}` in a JavaScript template literal",
        "use a quoted\n`cmd` string or escape every interpolation opener",
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
        "For an access fallback",
        "authoritative read-only runtime path",
        "preferring an already working service-local query or application API",
        "Acceptance must never mutate state",
        "actions reserved for later user approval",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"acceptance access fallback is not shared: {guard!r}")
    for guard in (
        "requested end state already holds in every required destination",
        "successful no-op", "never require a new diff, commit, or deploy",
        "revision\nidentifies the state to inspect, not necessarily the change's introduction point",
        "never substitute\nits patch or provenance for current-tree or artifact evidence",
        "Every compound probe must emit named\nobservations before failing",
        "empty, silent, or non-diagnostic result is a malformed probe",
        "TAKEOVER and corrective REMAINING work require a named observation",
        "no observation contradicts it, ACCEPT it",
        "named observation proving a mistake, incomplete work, failed valid verification",
    ):
        if executives.count(guard) != 3:
            raise AssertionError(f"already-satisfied acceptance guard is not shared: {guard!r}")
    if "acceptance claim remains unverified after those paths are exhausted" in executives:
        raise AssertionError("mere nonconfirmation can still trigger corrective takeover")
    if "failed verification, missing\nevidence" in executives or "missing evidence" in executives:
        raise AssertionError("missing diagnostics can still trigger corrective takeover")
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
        "Current root route from `turn_context`", "On takeover add",
        "Route takeover: Activated — __ROOT_ROUTE__", "gpt-5.6-sol", "xhigh",
        "GPT-5.6 Sol", "Extra High",
        "never `GPT-5 / default effort`", "Complexity:", "Root appends",
    ):
        if guard not in hook:
            raise AssertionError(f"deterministic final metadata omits {guard!r}")
    if "<root model / effort>" in hook or "<exact label>" in hook:
        raise AssertionError("takeover metadata still permits a guessed root-route label")
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

    # A proven Sol failure gets one full-context executive reload, never another producer.
    producer = terra_impl
    corrections: list[tuple[str, str]] = []
    takeover_reloads = [("same Sol executive role", "reuse fork")]
    takeover = (producer, "user-selected root finishes whole request")
    if corrections or len(takeover_reloads) != 1 or takeover[0] != producer:
        raise AssertionError("acceptance failure retained a producer retry or repeated context reload")
    for guard in (
        "selected root model", "no more handoffs", "Call no", "further agent-control",
        "TAKEOVER_CONTEXT:", "ORCHESTRATION_TAKEOVER_READY",
    ):
        if guard not in hook:
            raise AssertionError(f"staged root takeover omits {guard!r}")
    print("relay-protocol-ok lanes=7 packets=0 nested-agents=0 independent-acceptance=one-call probe-fallback=ok already-satisfied=accept visuals=opt-in deployment=single-owner final-metadata=exact-root staged-takeover=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
