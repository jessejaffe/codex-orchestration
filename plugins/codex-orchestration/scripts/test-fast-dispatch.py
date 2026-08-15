#!/usr/bin/env python3
"""Hermetic tests for chat-scoped activation and 0.9.0 single-agent dispatch."""

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


def context_field(value: str, name: str) -> str:
    prefix = f"{name}: "
    return next(
        line.removeprefix(prefix) for line in value.splitlines() if line.startswith(prefix)
    )


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
        "CODEX_ORCHESTRATION_ROOT_CONTRACT",
        "REVISION=0.9.0-named-launch-v4",
        "Orchestration ON (0.9.0)",
        "Parent classifies in its first response",
        "Do not spawn a classifier",
        "ROUTE_AND_EXECUTE",
        "classify internally from the current request and TURN",
        "immediately spawn exactly one mapped implementer",
        "Do not emit a separate classification message",
        "classification wait",
        "desktop activity label exactly `Thinking`",
        "no dynamic status",
        "LAUNCH UX",
        "only pre-launch text is exactly `Orchestration: ON for this chat`",
        "emit no pre-launch commentary",
        "never narrate analysis",
        "classification, planning, packet construction",
        "The named child lane is the only startup progress indicator",
        "## Classification",
        "- Relationship: <New|Amend|Replace|Cancel>",
        "- Active objective: <concise objective>",
        "- Work class: <friendly class>",
        "- Complexity: <1.0-10.0 / 10>",
        "- Why: <brief reason>",
        "DIRECT NAMED LAUNCH",
        "collaboration `spawn_agent`",
        "agent_type=<selected mapped custom agent>",
        "fork_turns=\"none\"",
        "message=packet",
        "luna_max_implementer_<objective_slug>",
        "terra_max_implementer_<objective_slug>",
        "sol_high_implementer_<objective_slug>",
        "visible model lane at creation time",
        "Never wrap launch in `exec`",
        "create a host-nicknamed child",
        "call `set_thread_title`",
        "`ALL_TOOLS`",
        "TASK_CONTEXT_BUNDLE:",
        "TASK_CONTEXT_REVISION:",
        "CURRENT_USER_REQUEST=INHERITED_CURRENT_QUERY",
        "PRIOR_COMPLETED_RESULT: NONE",
        "RECENT_CONTEXT_FRESHNESS: NONE",
        "RECENT_CONTEXT: NONE",
        "PREVIOUS_TASK_CONTEXT_REQUIRED: NO",
        "WORKSPACE_DEPENDENCIES_REQUIRED: NO",
        "codex_app__load_workspace_dependencies",
        "codex_orchestration_terra_implementer",
        "codex_orchestration_luna_implementer",
        "codex_orchestration_sol_high_implementer",
        "Never spawn a supervisor, reviewer, grader, classifier, or a",
        "second writer",
        "END_TO_END_WORK",
        "CLASSIFICATION=<exact Markdown>",
        "PRIOR_COMPLETED_RESULT=<TURN value>",
        "TASK_CONTEXT_BUNDLE=<TURN path>",
        "TASK_CONTEXT_REVISION=<TURN revision>",
        "WORKSPACE_DEPENDENCIES=<exact result or NONE>",
        "IMPLEMENTATION_ROUTE=<friendly selected model lane>",
        "LAST_TASK_CONTEXT=<exact full continuity block created above, only when TURN requires it>",
        "Send the full private handoff; never shorten, summarize, or omit its context fields",
        "every request and substantive",
        "root-visible fact in chronological order",
        "TURN values do not replace it",
        "The implementer owns",
        "scope interpretation, implementation, verification, and authorized release",
        "terminal visual handoff",
        "stop or redirect obsolete work",
        "PREMISE MISMATCH",
        "Inspect only cited evidence",
        "same implementer",
        "Do not create another role.",
        "Small tweak: Luna / Max",
        "Big tweak: Terra / Max",
        "Small build: Terra / Max",
        "Big build: Sol / High",
        "wait_agent(timeout_ms=3600000)",
        "## Root verification needed",
        "terminal root-only Browser/visual check",
        "cache-bypass",
        "Ground\ntruth and Source",
        "Missing/ambiguous identity",
        "capture screenshot",
        "Judge pass, fail, or blocked",
        "end without editing,",
        "`followup_task`",
        "primary content",
        "preserving delivered work/proof",
        "after the work account; never replace it.",
        "FINAL-REPORT VOICE",
        "User-facing report changes",
        "slightly less technical language",
        "lead with the outcome",
        "briefly explain jargon",
        "Keep internal work technical",
        "preserve exact",
        "details",
        "natural-language report",
        "what happened, work done/found",
        "outcome,\ndecisive evidence",
        "links, limits, or open work",
        "except `## Next step`",
        "immediately above its",
        "`None — no next step is needed.`",
        "No fixed headings or field list",
        "Never call the implementer",
        "locally add only",
        "request a rewrite",
        "Every completed user-facing task ends with this mandatory next-step section",
        "## Next step",
        "<one legitimate follow-on action, or None — no next step is needed.>",
        "## Route",
        "- Class: <friendly class>",
        "- Implementation: <IMPLEMENTATION_ROUTE>",
        "- Root: <CURRENT_ROOT_ROUTE>",
        "Never include supervision",
        "RELAY valid nonvisual reports verbatim",
        "never summarize, assess, append, tool-call, or request a rewrite",
    )
    for value in required:
        if value not in routed_context:
            raise AssertionError(f"dispatch contract omits {value!r}")
    if routed_context.count("CURRENT_USER_REQUEST=INHERITED_CURRENT_QUERY") != 1:
        raise AssertionError("the root turn should inherit the current query once")
    if routed_context.count("TASK_CONTEXT_BUNDLE=<TURN path>") != 1:
        raise AssertionError("the only implementer packet does not reference the context bundle once")
    state_document = json.loads((state / f"{active_id}.json").read_text(encoding="utf-8"))
    if state_document.get("contract_revision") != "0.9.0-named-launch-v4":
        raise AssertionError("first routed turn did not persist the root contract revision")
    bundle_path = Path(context_field(routed_context, "TASK_CONTEXT_BUNDLE"))
    bundle_revision = context_field(routed_context, "TASK_CONTEXT_REVISION")
    bundle_document = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle_document.get("revision") != bundle_revision:
        raise AssertionError("published task-context revision does not match its packet")
    if bundle_revision not in bundle_path.name:
        raise AssertionError("task-context bundle path is not an immutable revision")
    if bundle_document.get("messages") != [
        {"content": "Fix the existing label", "current": True, "role": "user"}
    ]:
        raise AssertionError(f"current request bundle is not exact: {bundle_document!r}")
    if bundle_document.get("completed_task_outcomes") != []:
        raise AssertionError("new chat bundle unexpectedly has completed task outcomes")
    if bundle_document.get("schema_version") != 2:
        raise AssertionError("task-context bundle did not publish the concise schema")
    if bundle_document.get("scope") != (
        "Concise whole-chat representation: chronological user requests and substantive "
        "root-visible assistant facts, plus canonical outcomes for the 20 most recent "
        "completed tasks."
    ):
        raise AssertionError("task-context bundle does not declare its concise whole-chat scope")
    if bundle_path.stat().st_mode & 0o077:
        raise AssertionError("task-context bundle is not private")
    for obsolete in (
        "headless-grader.py",
        "--request-token",
        "grader-requests",
        "codex_orchestration_terra_supervisor",
        "codex_orchestration_sol_high_supervisor",
        "codex_orchestration_sol_xhigh_supervisor",
        "FAST PATH",
        "ACCEPTANCE=PENDING_SUPERVISOR_INIT",
        "Launch the selected supervisor",
        "luna_high_implementer_<objective_slug>",
        "## Root verification result",
        "ROOT_VERIFICATION_RECOVERY_REQUIRED",
        "### Recommendations",
        "Fast-relay valid child results without extra reasoning",
        "codex_orchestration_terra_orchestrator",
        "ORCHESTRATE_CLASSIFY",
        "REPORT_REVISION_REQUIRED",
        "fork_turns=1",
        "fork_turns=none",
        "tools.multi_agent_v1__spawn_agent",
        "tools.codex_app__set_thread_title",
        "fork_context: false",
    ):
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
        "This is a <friendly class>. Implementation started",
        "Starting orchestration with verbatim request",
        "Planning orchestration and classification steps",
        "USER_REQUEST=<exact current request and attachment paths>",
        "USER_REQUEST=<exact request and attachment paths>",
        "The classifier always uses none",
        "Root cause → Release candidate",
        "latest verified milestone",
        "Building with Luna / Max",
        "Reviewing the release candidate",
        "Confirming Hetzner deployment priority",
        "Emit both `spawn_agent` calls back-to-back",
        "Never mutate under superseded acceptance",
        "Starting Terra / Extra High classification now.",
        "This is a <friendly class> because <Why>",
        "workspace setup now",
        "loading the project",
    ):
        if noisy in routed_context:
            raise AssertionError(f"dispatch retains noisy parent copy: {noisy!r}")
    if (state / "grader-requests").exists():
        raise AssertionError("dispatch still staged a grader request")
    if len(routed_context) > 8_000:
        raise AssertionError(f"dispatch contract regressed above the latency budget: {len(routed_context)}")

    previous_task_context = context(
        invoke(
            hook,
            state,
            active_id,
            "Read the last chat and pick off where we left off",
        )
    )
    if "PREVIOUS_TASK_CONTEXT_REQUIRED: YES" not in previous_task_context:
        raise AssertionError("previous-task request did not set the compact turn flag")
    if "CODEX_ORCHESTRATION_ROOT_CONTRACT" in previous_task_context:
        raise AssertionError("invariant root contract was repeated on a later turn")
    if len(previous_task_context) > 2_000:
        raise AssertionError("compact previous-task turn exceeded its latency budget")
    for value in (
        "list_threads",
        "read_thread",
        "exclude this",
        "`LAST_TASK_CONTEXT` (max 6,000 characters",
        "Give only the implementer",
    ):
        if value not in routed_context:
            raise AssertionError(f"invariant previous-task protocol omits {value!r}")

    negative_previous = context(
        invoke(hook, state, active_id, "Don't read the last chat; fix only this label")
    )
    if "PREVIOUS_TASK_CONTEXT_REQUIRED: NO" not in negative_previous:
        raise AssertionError("negative previous-task instruction was ignored")

    artifact_context = context(
        invoke(
            hook,
            state,
            active_id,
            "Make me a spreadsheet with photo filenames and final labels",
        )
    )
    if "WORKSPACE_DEPENDENCIES_REQUIRED: YES" not in artifact_context:
        raise AssertionError("spreadsheet work did not require root workspace dependencies")
    direct_question_context = context(
        invoke(hook, state, active_id, "Why did the spreadsheet task fail?")
    )
    if "CODEX_ORCHESTRATION_ROOT_CONTRACT" in direct_question_context:
        raise AssertionError("routine turn repeated the invariant root contract")
    if "CODEX_ORCHESTRATION_TURN" not in direct_question_context:
        raise AssertionError("routine read-only work omitted its compact turn packet")
    for token in (
        "Every completed user-facing task must end with this compact",
    ):
        if token in direct_question_context:
            raise AssertionError(f"dispatch retains obsolete route receipt {token!r}")
    for token in (
        "Every completed user-facing task ends with this mandatory next-step section",
        "## Next step",
        "<one legitimate follow-on action, or None — no next step is needed.>",
        "## Route",
        "- Class: <friendly class>",
        "- Implementation: <IMPLEMENTATION_ROUTE>",
        "- Root: <CURRENT_ROOT_ROUTE>",
        "Never include supervision",
        "FINAL-REPORT VOICE",
        "slightly less technical language",
        "briefly explain jargon",
    ):
        if token not in routed_context:
            raise AssertionError(f"root contract omits route receipt {token!r}")
    if "- Supervision:" in direct_question_context:
        raise AssertionError("dispatch retains supervision in the route receipt")
    inspection_policy = (
        "INSPECTION_POLICY=Group closely related low-output checks for one immediate question "
        "in one pass; keep unrelated or noisy checks separate."
    )
    if routed_context.count(inspection_policy) != 1:
        raise AssertionError("inspection grouping policy is not isolated to the implementer packet")

    combined_id = "33333333-3333-3333-3333-333333333333"
    combined = invoke(
        hook,
        state,
        combined_id,
        "Please turn orchestration on and add the new export feature",
    )
    combined_context = context(combined)
    if not combined_context.startswith(
        "Reply in commentary exactly `Orchestration: ON for this chat`, with no other "
        "pre-launch text"
    ):
        raise AssertionError("combined activation does not acknowledge ON")
    if "ROUTE_AND_EXECUTE" not in combined_context:
        raise AssertionError("combined activation did not install parent-first routing")

    transcript = temporary / "root.jsonl"
    acceptance = """## Ready

- Work class: Small build
- Outcome: Ship export
- Must: Implement and test
- Destinations: Repository
- Open commitments: None
- Proof: Focused tests"""
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
    bounded_acceptance = " ".join(acceptance.split())
    for value in (
        "ROOT_CONTRACT_REVISION: 0.9.0-named-launch-v4",
        "CURRENT_ROOT_ROUTE: GPT-5.6 Terra / Max",
        bounded_acceptance,
        "PRIOR_COMPLETED_RESULT: NONE",
    ):
        if value not in inherited_context:
            raise AssertionError(f"bounded inherited context omits {value!r}")
    if any(
        placeholder in inherited_context
        for placeholder in (
            "__FORK_TURNS__",
            "__ROOT_ROUTE__",
            "__PRIOR_COMPLETED_RESULT__",
            "__RECENT_CONTEXT_FRESHNESS__",
            "__RECENT_CONTEXT__",
            "__TASK_CONTEXT_BUNDLE__",
            "__TASK_CONTEXT_REVISION__",
            "__WORKSPACE_DEPENDENCIES_REQUIRED__",
            "__PREVIOUS_TASK_CONTEXT_REQUIRED__",
            "__AGENTS_DIR__",
        )
    ):
        raise AssertionError("dispatch placeholders leaked")
    inherited_bundle = json.loads(
        Path(context_field(inherited_context, "TASK_CONTEXT_BUNDLE")).read_text(
            encoding="utf-8"
        )
    )
    if [item["content"] for item in inherited_bundle["messages"]] != [
        "Build CSV export",
        "Also support JSON",
    ]:
        raise AssertionError("active task bundle lost exact original or amendment context")
    if inherited_bundle.get("prior_active_acceptance") != acceptance:
        raise AssertionError("active task bundle lost prior acceptance")
    if (state / "grader-requests").exists():
        raise AssertionError("inherited dispatch staged obsolete recent context")

    early_interruption = temporary / "early-interruption.jsonl"
    exact_original = (
        "Build the recovery workflow from /Users/example/Downloads/input.zip. "
        + ("original detail " * 260)
        + "MUST_KEEP_THIS_MIDDLE_CONSTRAINT "
        + ("more detail " * 260)
    )
    exact_add_on = "Also preserve both JPEG and PNG outputs."
    write_events(
        early_interruption,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": exact_original}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Starting the task."}],
                },
            },
        ],
    )
    interruption_context = context(
        invoke(hook, state, active_id, exact_add_on, early_interruption)
    )
    interruption_bundle = json.loads(
        Path(context_field(interruption_context, "TASK_CONTEXT_BUNDLE")).read_text(
            encoding="utf-8"
        )
    )
    exact_contents = [item["content"] for item in interruption_bundle["messages"]]
    if exact_contents != [exact_original.strip(), exact_add_on]:
        raise AssertionError("private bundle retained transient progress instead of chat facts")
    if "MUST_KEEP_THIS_MIDDLE_CONSTRAINT" not in exact_contents[0]:
        raise AssertionError("middle constraints were clipped from the private task bundle")
    if interruption_bundle["messages"][-1].get("current") is not True:
        raise AssertionError("task bundle does not mark the current amendment")

    accepted_transcript = temporary / "accepted.jsonl"
    handoff = """I shipped the CSV export for the dashboard and signed the production bundle.
The focused suite passed all 12 checks, and I confirmed a production download at
https://example.com/export. The change is at 0123456789abcdef. JSON export remains a useful
follow-up; there are no current limitations.

## Next step
Add JSON export after the CSV release has been adopted.

## Route
- Class: Small build
- Implementation: Terra / Max
- Root: GPT-5.6 Sol / High"""
    write_events(
        accepted_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [{"text": acceptance}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "text": (
                                "Message Type: FINAL_ANSWER\n"
                                "Task name: /root/example\n"
                                "Payload:\n"
                                + handoff
                            )
                        }
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [{"text": handoff}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": handoff}],
                },
            },
        ],
    )
    accepted = invoke(hook, state, active_id, "New question", accepted_transcript)
    accepted_context = context(accepted)
    if "PRIOR_ACTIVE_ACCEPTANCE: NONE" not in accepted_context:
        raise AssertionError("accepted objective was not cleared")
    if "ROOT_CONTRACT_REVISION: 0.9.0-named-launch-v4" not in accepted_context:
        raise AssertionError("current query did not use the compact routed turn")
    canonical_handoff = handoff.rsplit("\n\n## Route", 1)[0]
    bounded_handoff = " ".join(canonical_handoff.split())
    if f"PRIOR_COMPLETED_RESULT: {bounded_handoff}" not in accepted_context:
        raise AssertionError("completion handoff was not passed to the next Terra")
    if "RECENT_CONTEXT_FRESHNESS: FRESH" not in accepted_context:
        raise AssertionError("an immediate follow-up incorrectly made its completion capsule stale")
    if "I shipped the CSV export for the dashboard" not in accepted_context:
        raise AssertionError("natural-language completion was not retained for the next task")
    accepted_bundle = json.loads(
        Path(context_field(accepted_context, "TASK_CONTEXT_BUNDLE")).read_text(
            encoding="utf-8"
        )
    )
    if accepted_bundle.get("prior_completed_result") != canonical_handoff:
        raise AssertionError("task roles did not retain the canonical natural-language completion")
    if accepted_bundle.get("completed_task_outcomes") != [canonical_handoff]:
        raise AssertionError("task roles did not deduplicate the relayed completed outcome")

    root_visible_outcome = """Root completed the terminal visual check.

## Next step
None — no next step is needed.

## Route
- Class: Small build
- Implementation: Terra / Max
- Root: GPT-5.6 Sol / High"""
    root_visible_transcript = temporary / "root-visible-outcome.jsonl"
    write_events(
        root_visible_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": root_visible_outcome}],
                },
            },
        ],
    )
    root_visible_context = context(
        invoke(hook, state, active_id, "What did root verify?", root_visible_transcript)
    )
    root_visible_bundle = json.loads(
        Path(context_field(root_visible_context, "TASK_CONTEXT_BUNDLE")).read_text(
            encoding="utf-8"
        )
    )
    canonical_root_visible_outcome = root_visible_outcome.rsplit("\n\n## Route", 1)[0]
    if root_visible_bundle.get("completed_task_outcomes") != [canonical_root_visible_outcome]:
        raise AssertionError("private bundle lost a root-visible completed task outcome")
    if root_visible_bundle.get("prior_completed_result") != canonical_root_visible_outcome:
        raise AssertionError("root-visible completion did not update continuity")

    full_history_transcript = temporary / "full-history-context.jsonl"
    full_history_events: list[dict[str, object]] = [{"type": "session_meta", "payload": {}}]
    full_history_messages: list[str] = []
    full_history_outcomes: list[str] = []
    for task_number in range(1, 22):
        request = f"Task {task_number} request carries a durable chat fact."
        visible_update = f"Task {task_number} visible result carries a durable answer."
        detail = (
            "UNBOUNDED_FIRST_OUTCOME_MARKER " + ("first outcome detail " * 1_500)
            if task_number == 2
            else f"Outcome detail for task {task_number}."
        )
        outcome = (
            f"Task {task_number} completed. {detail}\n\n"
            "## Next step\n"
            "None — no next step is needed.\n\n"
            "## Route\n"
            "- Class: Read-only\n"
            "- Implementation: Luna / Max\n"
            "- Root: GPT-5.6 Sol / High"
        )
        full_history_messages.extend((request, visible_update))
        full_history_outcomes.append(outcome)
        full_history_events.extend(
            (
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": request}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": visible_update}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "content": [{"text": outcome}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": outcome}],
                    },
                },
            )
        )
    full_history_events.append(
        {
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "content": [
                    {"text": "## Classification\n\n- Relationship: Cancel"}
                ],
            },
        }
    )
    write_events(full_history_transcript, full_history_events)
    full_history_request = "Answer using the facts from task 1 and task 10."
    full_history_context = context(
        invoke(hook, state, active_id, full_history_request, full_history_transcript)
    )
    full_history_bundle = json.loads(
        Path(context_field(full_history_context, "TASK_CONTEXT_BUNDLE")).read_text(
            encoding="utf-8"
        )
    )
    if [item["content"] for item in full_history_bundle["messages"]] != [
        *full_history_messages,
        full_history_request,
    ]:
        raise AssertionError("private bundle dropped earlier root-visible chat history")
    retained_outcomes = full_history_bundle.get("completed_task_outcomes")
    if not isinstance(retained_outcomes, list) or len(retained_outcomes) != 20:
        raise AssertionError("private bundle did not retain exactly the newest 20 task outcomes")
    if any("Task 1 completed." in outcome for outcome in retained_outcomes):
        raise AssertionError("private bundle retained an outcome older than its 20-task window")
    for task_number, outcome in zip(range(2, 22), retained_outcomes):
        if not outcome.startswith(f"Task {task_number} completed."):
            raise AssertionError("private bundle reordered canonical task outcomes")
        if "## Route" in outcome:
            raise AssertionError("private bundle retained repeated route-footer boilerplate")
        if "## Next step\nNone — no next step is needed." not in outcome:
            raise AssertionError("private bundle lost the required next-step outcome section")
    verbose_outcome = retained_outcomes[0]
    if "UNBOUNDED_FIRST_OUTCOME_MARKER" not in verbose_outcome:
        raise AssertionError("private bundle lost a durable outcome fact while compacting")
    if "[repeated " not in verbose_outcome or len(verbose_outcome) >= len(full_history_outcomes[1]) // 8:
        raise AssertionError("private bundle did not compact pathological repeated outcome filler")

    legacy_transcript = temporary / "legacy-accepted.jsonl"
    legacy_result = "Released the benchmark to GitHub and Hetzner; verification passed."
    write_events(
        legacy_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "text": (
                                "Message Type: FINAL_ANSWER\nPayload:\n"
                                f"ORCHESTRATION_ACCEPT: {legacy_result}"
                            )
                        }
                    ],
                },
            },
        ],
    )
    legacy = context(invoke(hook, state, active_id, "Summarize that", legacy_transcript))
    if "ROOT_CONTRACT_REVISION: 0.9.0-named-launch-v4" not in legacy:
        raise AssertionError("legacy follow-up did not use the compact routed turn")
    if f"PRIOR_COMPLETED_RESULT: {legacy_result}" not in legacy:
        raise AssertionError("legacy completion did not fall back to its accepted result")

    stale_context_transcript = temporary / "stale-completion-context.jsonl"
    stale_capsule = (
        "OUTCOME=Released benchmark foundation; DELIVERED=private-repository validators; "
        "OPEN_COMMITMENTS=NONE; NEXT=next project milestone"
    )
    agreed_scope = (
        "The immediate step is to create a separate public licensed GitHub repository "
        "and publish the benchmark foundation there."
    )
    current_request = "Turn orchestration on and do the next immediate step"
    write_events(
        stale_context_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "text": (
                                f"ORCHESTRATION_HANDOFF: {stale_capsule}\n"
                                "ORCHESTRATION_ACCEPT: prior completion"
                            )
                        }
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Prior completion " + ("old detail " * 900),
                        }
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "What comes next?"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": agreed_scope}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": current_request}],
                },
            },
        ],
    )
    stale_context = context(
        invoke(hook, state, active_id, current_request, stale_context_transcript)
    )
    for value in (
        "ROOT_CONTRACT_REVISION: 0.9.0-named-launch-v4",
        "RECENT_CONTEXT_FRESHNESS: STALE",
        agreed_scope,
        f"PRIOR_COMPLETED_RESULT: {stale_capsule}",
    ):
        if value not in stale_context:
            raise AssertionError(f"stale-capsule regression omits {value!r}")
    if f"USER: {current_request}" in stale_context:
        raise AssertionError("current request was duplicated into RECENT_CONTEXT")

    wrapped_context_transcript = temporary / "wrapped-recent-context.jsonl"
    prior_question = "Which context should the next task receive?"
    prior_answer = "Use the bounded completion capsule and recent conversation."
    wrapped_current_request = "Continue with that context."
    injected_prefix = (
        "<recommended_plugins>\n- Example\n</recommended_plugins>\n"
        "# AGENTS.md instructions for /workspace\n\n"
        "<INSTRUCTIONS>\nKeep the workspace safe.\n</INSTRUCTIONS>\n"
        "<environment_context>\n  <cwd>/workspace</cwd>\n</environment_context>\n"
    )
    write_events(
        wrapped_context_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": injected_prefix + prior_question}
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": prior_answer}],
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
                            "text": injected_prefix + wrapped_current_request,
                        }
                    ],
                },
            },
        ],
    )
    wrapped_context = context(
        invoke(
            hook,
            state,
            active_id,
            wrapped_current_request,
            wrapped_context_transcript,
        )
    )
    for value in (prior_question, prior_answer):
        if value not in wrapped_context:
            raise AssertionError(f"clean recent context dropped {value!r}")
    for leaked in (
        "<recommended_plugins>",
        "# AGENTS.md instructions for /workspace",
        "<environment_context>",
        f"USER: {wrapped_current_request}",
    ):
        if leaked in wrapped_context:
            raise AssertionError(f"injected recent-context wrapper leaked: {leaked!r}")

    scoped_transcript = temporary / "turn-scoped-handoffs.jsonl"
    old_handoff = "OUTCOME=old completed build; NEXT=old follow-up"
    newest_result = "Completed the newer read-only review."
    write_events(
        scoped_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "text": (
                                f"ORCHESTRATION_HANDOFF: {old_handoff}\n"
                                "ORCHESTRATION_ACCEPT: old report"
                            )
                        }
                    ],
                    "internal_chat_message_metadata_passthrough": {"turn_id": "old-turn"},
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [{"text": f"ORCHESTRATION_ACCEPT: {newest_result}"}],
                    "internal_chat_message_metadata_passthrough": {"turn_id": "new-turn"},
                },
            },
        ],
    )
    scoped = context(invoke(hook, state, active_id, "Another follow-up", scoped_transcript))
    if f"PRIOR_COMPLETED_RESULT: {newest_result}" not in scoped:
        raise AssertionError("a prior turn's handoff leaked into a newer completion")
    if old_handoff in scoped:
        raise AssertionError("completed-result selection ignored root turn boundaries")

    oversized_transcript = temporary / "oversized-handoff.jsonl"
    oversized_handoff = "OUTCOME=" + ("x" * 5_000)
    write_events(
        oversized_transcript,
        [
            {"type": "session_meta", "payload": {}},
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "text": (
                                f"ORCHESTRATION_HANDOFF: {oversized_handoff}\n"
                                "ORCHESTRATION_ACCEPT: done"
                            )
                        }
                    ],
                },
            },
        ],
    )
    oversized = context(invoke(hook, state, active_id, "Follow up", oversized_transcript))
    completed_line = next(
        line for line in oversized.splitlines() if line.startswith("PRIOR_COMPLETED_RESULT: ")
    )
    completed_value = completed_line.removeprefix("PRIOR_COMPLETED_RESULT: ")
    canonical_oversized_handoff = "OUTCOME=x×5000"
    if completed_value != canonical_oversized_handoff:
        raise AssertionError("completion handoff was not canonically compacted")
    oversized_bundle = json.loads(
        Path(context_field(oversized, "TASK_CONTEXT_BUNDLE")).read_text(encoding="utf-8")
    )
    if oversized_bundle.get("prior_completed_result") != canonical_oversized_handoff:
        raise AssertionError("task roles did not retain the canonical compact completion handoff")
    if len(oversized) > 15_000:
        raise AssertionError(f"bounded completion dispatch exceeds latency budget: {len(oversized)}")

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

    reactivation = invoke(hook, state, active_id, "Turn orchestration on")
    if context(reactivation) != "Reply exactly `Orchestration: ON for this chat` and do not spawn.":
        raise AssertionError("reactivation-only response changed")
    reactivated_work = context(invoke(hook, state, active_id, "Explain the label again"))
    if "CODEX_ORCHESTRATION_ROOT_CONTRACT" not in reactivated_work:
        raise AssertionError("reactivation did not reinstall the invariant root contract")

    print("PASS: chat controls, one-time root contract, and concise private whole-chat context")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
