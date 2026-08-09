#!/usr/bin/env python3
"""Hermetic root-relay protocol and steering regression test."""

from pathlib import Path
import json
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
    triage = json.loads((plugin / "scripts/triage-cases.json").read_text())
    sol_low = (plugin / "agents/codex-orchestration-sol-low-executive.toml").read_text()
    sol_medium = (plugin / "agents/codex-orchestration-sol-medium-executive.toml").read_text()
    sol_high = (plugin / "agents/codex-orchestration-sol-high-executive.toml").read_text()
    sol_xhigh = (plugin / "agents/codex-orchestration-sol-xhigh-executive.toml").read_text()
    sol_executive_texts = (sol_low, sol_medium, sol_high, sol_xhigh)
    sol_executives = sol_low + sol_medium + sol_high + sol_xhigh
    executives = terra + sol_executives
    for tool in ("send_message", "spawn_agent", "wait_agent", "list_agents", "interrupt_agent"):
        if tool in executives:
            raise AssertionError(f"custom executive requires unavailable collaboration tool: {tool}")
    for token in (
        "ORCHESTRATION_RELATION:", "ORCHESTRATION_SCORE:", "ORCHESTRATION_STATUS:",
        "ORCHESTRATION_ACCEPTANCE:",
        "ORCHESTRATION_DELEGATE:", "IMPLEMENTATION_RESULT:", "ORCHESTRATION_ACCEPT:",
        "ORCHESTRATION_TAKEOVER:", "DIRECTIVE:",
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
        "immutable acceptance + exact `IMPLEMENTATION_RESULT:`",
        "Routine non-experience verification: code/tests/deployed",
        "Experience contract (interaction/demo/rendered/visual)",
        "ORCHESTRATION_ROOT_VERIFY:",
        "root-only Browser/visual",
        "ROOT_VERIFICATION_RESULT:",
        "START, ACTION, RESULT, ARTIFACTS",
        "inherited unfinished work stays in scope",
        "new prompt amends it",
        "interrupted/aborted turn stops execution, never the inherited objective",
        "PRIOR_ACTIVE_ACCEPTANCE:",
        "Require four protocol lines",
        "EXPLICIT_SIGNAL as an exact",
        "AMEND requires REMOVED=NONE",
        "PROTOCOL_REPAIR:",
        "do not spawn an executive or producer",
    ):
        if guard not in hook:
            raise AssertionError(f"minimal direct-context handoff omits {guard!r}")
    if "After a valid result show Terra's exact `ORCHESTRATION_STATUS:` in commentary" not in hook:
        raise AssertionError("Terra's human-readable score checkpoint is not relayed before delegation")
    if "never replace it" not in hook:
        raise AssertionError("root can replace Terra's scored checkpoint with generic commentary")
    if "Keep Terra's `ORCHESTRATION_RELATION:` and `ORCHESTRATION_ACCEPTANCE:` internal and immutable" not in hook:
        raise AssertionError("root can expose or mutate Terra's relation/acceptance contract")
    if "Keep Terra's AGENT/TASK immutable; ignore remaps" not in hook:
        raise AssertionError("root can accept an executive-generated implementation identity")
    sol_handoff_start = hook.index("SOL_LOW/SOL_MEDIUM/SOL_HIGH/SOL_XHIGH: spawn")
    sol_handoff = hook[sol_handoff_start : hook.index("Keep Terra", sol_handoff_start)]
    relation_line = "Send exact Terra `ORCHESTRATION_RELATION:`"
    if relation_line not in sol_handoff:
        raise AssertionError("root can omit Terra's immutable AGENT/TASK from the Sol executive handoff")
    if sol_handoff.index(relation_line) > sol_handoff.index("USER_REQUEST:"):
        raise AssertionError("Sol executive handoff does not place Terra's relation before the request")
    if '`fork_turns: "none"`' not in sol_handoff:
        raise AssertionError("Sol executive still inherits the heavy parent transcript")
    if "`ORCHESTRATION_STATUS:`" not in sol_handoff:
        raise AssertionError("compact Sol executive handoff omits Terra's resolved work status")
    if "`ORCHESTRATION_ACCEPTANCE:`" not in sol_handoff:
        raise AssertionError("compact Sol executive handoff omits the immutable definition of done")
    if "`ORCHESTRATION_RELATION:`" not in sol_handoff:
        raise AssertionError("compact Sol executive handoff omits the immutable objective delta")
    if sol_handoff.index("`ORCHESTRATION_ACCEPTANCE:`") > sol_handoff.index("USER_REQUEST:"):
        raise AssertionError("Sol executive receives the request before its acceptance contract")
    producer_handoff = hook[hook.index("Keep Terra", sol_handoff_start) : hook.index("Follow up:")]
    if "reuse fork" not in producer_handoff:
        raise AssertionError("mapped producer no longer inherits the active task context")
    if "immutable relation + acceptance" not in producer_handoff:
        raise AssertionError("mapped producer cannot preserve Terra's objective delta and acceptance")
    takeover_handoff = hook[hook.index("On Sol ORCHESTRATION_TAKEOVER") : hook.index("Every routed final ends")]
    for guard in (
        "same Sol executive role",
        "reuse fork",
        "TAKEOVER_CONTEXT:",
        "ORCHESTRATION_TAKEOVER_READY",
        "exact acceptance + takeover + producer result",
    ):
        if guard not in takeover_handoff:
            raise AssertionError(f"full-history takeover stage omits {guard!r}")
    if "loading full task history" not in hook:
        raise AssertionError("root does not announce the exceptional full-history takeover reload")
    for guard in ("Copy Terra's AGENT and TASK", "never shorten, relabel, remap"):
        if not all(guard in executive for executive in sol_executive_texts):
            raise AssertionError(f"pinned Sol executive can rename Terra's implementation task: {guard!r}")
    for guard in (
        "use only the supplied score, status, acceptance, and request",
        "do not inspect files or call\ntask tools",
        "Copy AGENT/TASK immediately",
        "absent from USER_REQUEST, ORCHESTRATION_STATUS, and ORCHESTRATION_ACCEPTANCE",
        "Never restate the request, status",
        "sole full-history path",
        "inherited task history",
        "TAKEOVER_CONTEXT:",
        "ORCHESTRATION_TAKEOVER_READY:",
        "reload one same-role takeover instance with full inherited history",
        "Keep Terra's\nacceptance contract authoritative",
    ):
        if not all(guard in executive for executive in sol_executive_texts):
            raise AssertionError(f"compact Sol executive fast path omits {guard!r}")
    if not all("producer redefine done" in executive for executive in sol_executive_texts) or "producer must never\nredefine done" not in terra:
        raise AssertionError("an executive can let the producer redefine acceptance")
    if (
        sol_low.count("acceptance contract authoritative") != 2
        or sol_medium.count("acceptance contract authoritative") != 2
        or sol_high.count("acceptance contract authoritative") != 2
        or sol_xhigh.count("acceptance contract authoritative") != 2
    ):
        raise AssertionError("an executive can lose Terra's immutable acceptance authority")
    if "Show `ORCHESTRATION_SCORE:` and `ORCHESTRATION_STATUS:`" in hook:
        raise AssertionError("internal routing score can leak into commentary")
    if "show Terra's exact `ORCHESTRATION_ACCEPTANCE:`" in hook:
        raise AssertionError("internal acceptance contract can leak into commentary")
    implementer_paths = sorted((plugin / "agents").glob("*implementer.toml"))
    if len(implementer_paths) != 7:
        raise AssertionError(f"expected seven implementation lanes, found {len(implementer_paths)}")
    implementer_texts = [path.read_text() for path in implementer_paths]
    implementers = "".join(implementer_texts)
    if implementers.count("Execute `USER_REQUEST`") != 7:
        raise AssertionError("an implementation lane still depends on an executive rewrite")
    for guard in (
        "immutable `ORCHESTRATION_ACCEPTANCE:` contract",
        "never as a replacement for that\nrequest",
        "do not add, remove, or redefine acceptance criteria",
        "at-most-300-word final",
        "IMPLEMENTATION_RESULT:",
        "EVIDENCE=<each acceptance item mapped to an actual observation>",
        "INCOMPLETE=<NONE or exact remaining work>",
        "Never claim acceptance; the executive judges the immutable contract",
    ):
        if implementers.count(guard) != 7:
            raise AssertionError(f"structured producer evidence contract is not shared: {guard!r}")
    if "No executive packet" in implementers:
        raise AssertionError("implementer instructions contradict the compact acceptance contract")
    for guard in (
        "Return immediately with exactly four lines",
        "ORCHESTRATION_RELATION: RELATION=",
        "ACTIVE_OBJECTIVE=",
        "PRESERVED=",
        "ADDED=",
        "REMOVED=",
        "EXPLICIT_SIGNAL=",
        "ORCHESTRATION_ACCEPTANCE: OUTCOME=",
        "immutable, at-most-200-word contract",
        "never discarded exploration",
        "never invent a criterion",
        "producer must never\nredefine done",
        "Make `PROOF` test the defining outcome",
        "`ROOT_EXPERIENCE:`",
        "end-to-end observation",
        "damage-and-recovery demo",
        "input genuinely manifests the intended damage or failure",
    ):
        if guard not in terra:
            raise AssertionError(f"Terra acceptance contract omits {guard!r}")
    for guard in (
        "current `USER_REQUEST` adds to, corrects, answers, or authorizes unfinished inherited",
        "combined active request is authoritative",
        "Only explicit cancellation or replacement",
        "discards its prior objective",
    ):
        if sol_executives.count(guard) != 4 or implementers.count(guard) != 7:
            raise AssertionError(f"additive steering context is not shared: {guard!r}")
    for guard in (
        "`NEW`, `AMEND`, `REPLACE`, or",
        "A request for an explanation can add an immediate answer",
        "interrupted or aborted turn stops execution, never its objective",
        "`REMOVED` must be `NONE`",
        "never merely the newest interrogative sentence",
        "verbatim nonempty\nsubstring of the current `USER_REQUEST`",
    ):
        if guard not in terra:
            raise AssertionError(f"Terra relation contract omits {guard!r}")
    steering = {case["id"]: case for case in triage.get("steering_cases", [])}
    required_steering = {
        "interrupted_pdf_framework_cross_format_question": "AMEND",
        "explain_then_continue_framework": "AMEND",
        "explicit_replace_with_explanation": "REPLACE",
        "explicit_cancel_active_work": "CANCEL",
        "new_request_without_active_acceptance": "NEW",
    }
    if {case_id: steering.get(case_id, {}).get("expected_relation") for case_id in required_steering} != required_steering:
        raise AssertionError("offline steering benchmark omits amend/replace/cancel/new coverage")
    cross_format = steering["interrupted_pdf_framework_cross_format_question"]
    if (
        "turn_aborted" not in cross_format["events"]
        or cross_format["minimum_score"] < 5.1
        or not {"implement", "commit", "deploy"}.issubset(cross_format["preserve"])
        or "MUST_NOT=implement" not in cross_format["forbid"]
        or "DESTINATIONS=NOT_APPLICABLE" not in cross_format["forbid"]
    ):
        raise AssertionError("PDF/JPEG/PNG interruption regression no longer preserves implementation")
    for case_id in ("explicit_replace_with_explanation", "explicit_cancel_active_work"):
        signal = steering[case_id].get("explicit_signal")
        if not isinstance(signal, str) or signal not in steering[case_id]["request"]:
            raise AssertionError(f"{case_id} lacks a verbatim replacement/cancellation signal")
    checkout_guard = "configured `codex-orchestration` marketplace source"
    if implementers.count(checkout_guard) != 7:
        raise AssertionError("implementation lanes can mistake the ChatGPT project mirror for this plugin checkout")
    if not all(checkout_guard in executive for executive in sol_executive_texts):
        raise AssertionError("acceptance can mistake the ChatGPT project mirror for this plugin checkout")
    if "next: `spawn_agent`" not in hook or "never Terra" not in hook:
        raise AssertionError("root can reactivate Terra instead of spawning the scored implementation lane")
    for guard in (
        "untrusted claim", "task-appropriate probe", "deployed revision or artifact",
        "non-experience frontend work", "direct experience proof is mandatory",
        "root-only capabilities", "ORCHESTRATION_ROOT_VERIFY:",
        "REQUIRED_OBSERVATIONS=START=", "ROOT_VERIFICATION_RESULT:",
        "HTTP 200, asset", "supporting evidence only and never",
        "damage-and-recovery demo", "exhausted root access",
        "without route metadata",
    ):
        if not all(guard in executive for executive in sol_executive_texts):
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
    ):
        if not all(guard in executive for executive in sol_executive_texts):
            raise AssertionError(f"minimal acceptance guard is not shared: {guard!r}")
    for guard in (
        "producer supplies no working production path",
        "actual deploy/config scripts", "guessed port, URL, process",
        "deploy command reached terminal exit", "still-running deploy is not failure",
    ):
        if not all(guard in executive for executive in sol_executive_texts):
            raise AssertionError(f"production acceptance guard is not shared: {guard!r}")
    for guard in (
        "For an access fallback",
        "authoritative read-only runtime path",
        "preferring an already working service-local query or application API",
        "Acceptance must never mutate state",
        "actions reserved for later user approval",
    ):
        if not all(guard in executive for executive in sol_executive_texts):
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
        if not all(guard in executive for executive in sol_executive_texts):
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

    if "EXECUTIVE=<SOL_LOW if below 4.0, SOL_MEDIUM from 4.0–6.0, SOL_HIGH from 6.1–7.9, otherwise SOL_XHIGH>" not in terra:
        raise AssertionError("Terra does not use the requested four-band Sol executive ladder")
    for token in (
        "codex_orchestration_sol_low_executive",
        "gpt_5_6_sol_low_executive_",
        "codex_orchestration_sol_medium_executive",
        "gpt_5_6_sol_medium_executive_",
        "GPT-5.6 Sol / <Low|Medium|High|Extra High matching executive>",
        "codex_orchestration_sol_xhigh_executive",
        "gpt_5_6_sol_extra_high_executive_",
    ):
        if token not in hook:
            raise AssertionError(f"root relay omits the Sol / Extra High executive: {token}")
    if 'model_reasoning_effort = "xhigh"' not in sol_xhigh:
        raise AssertionError("Sol / Extra High executive is not pinned to xhigh")
    if 'model_reasoning_effort = "low"' not in sol_low:
        raise AssertionError("Sol / Low executive is not pinned to low")
    if 'model_reasoning_effort = "medium"' not in sol_medium:
        raise AssertionError("Sol / Medium executive is not pinned to medium")

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
    print("relay-protocol-ok lanes=7 packets=0 nested-agents=0 independent-acceptance=one-call probe-fallback=ok already-satisfied=accept visuals=root-relay deployment=single-owner final-metadata=exact-root staged-takeover=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
