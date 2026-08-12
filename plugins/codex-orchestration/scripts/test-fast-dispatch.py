#!/usr/bin/env python3
"""Hermetic tests for chat-scoped activation and 0.13.0 single-agent dispatch."""

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
        "Orchestration ON (0.13.0)",
        "exactly two stages",
        "one selected implementer owns the task end to end",
        "desktop activity label exactly `Thinking`",
        "never create a dynamic status label",
        "Keep startup quiet",
        "comment only on meaningful progress, blockers, release, and completion",
        "terra_extra_high_orchestrator_<objective_slug>",
        "ORCHESTRATE_CLASSIFY",
        "fork_turns=1",
        "fork_turns=none",
        "TASK_CONTEXT_BUNDLE:",
        "TASK_CONTEXT_REVISION:",
        "USER_REQUEST=INHERITED_CURRENT_QUERY",
        "PRIOR_COMPLETED_RESULT: NONE",
        "RECENT_CONTEXT_FRESHNESS: NONE",
        "RECENT_CONTEXT: NONE",
        "WORKSPACE_DEPENDENCIES_REQUIRED: NO",
        "codex_app__load_workspace_dependencies",
        "codex_orchestration_terra_orchestrator",
        "codex_orchestration_terra_implementer",
        "codex_orchestration_luna_implementer",
        "codex_orchestration_sol_high_implementer",
        "agents/codex-orchestration-terra-orchestrator.toml",
        "terra_max_implementer_<objective_slug>",
        "luna_high_implementer_<objective_slug>",
        "sol_high_implementer_<objective_slug>",
        "EXECUTE — Spawn exactly one mapped implementer",
        "Never spawn a supervisor, reviewer, grader, or a",
        "second writer",
        "END_TO_END_WORK",
        "IMPLEMENTATION_ROUTE=<friendly selected model lane>",
        "The implementer owns",
        "scope interpretation, implementation, verification, authorized release, and the final report",
        "stop or redirect obsolete work",
        "PREMISE MISMATCH",
        "inspect only its cited evidence",
        "same implementer",
        "Do not create another role lane",
        "## Classification blocked",
        "Accept only `## Classification blocked` or `## Classification`",
        "Small tweak: Luna / High",
        "Big tweak: Terra / Max",
        "Small build: Terra / Max",
        "Big build: Sol / High",
        "timeout_ms=3600000",
        "## Root verification needed",
        "## Root verification result",
        "hand the evidence back to the same implementer with `followup_task`",
        "same implementer corrects the work",
        "## Continuity",
        "## Completed",
        "- Supervision: None",
    )
    for value in required:
        if value not in routed_context:
            raise AssertionError(f"dispatch contract omits {value!r}")
    if routed_context.count("USER_REQUEST=INHERITED_CURRENT_QUERY") != 1:
        raise AssertionError("only the classifier should inherit the current query")
    if routed_context.count("TASK_CONTEXT_BUNDLE=<STATE path>") != 1:
        raise AssertionError("the only implementer packet does not reference the context bundle once")
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
    if len(routed_context) > 7_500:
        raise AssertionError(f"dispatch contract regressed above the latency budget: {len(routed_context)}")
    for capsule_line in (
        "ROUTING_CONTEXT=<exact structured capsule created above>",
        "LAST_TASK_CONTEXT=<exact full continuity block created above>",
    ):
        if capsule_line in routed_context:
            raise AssertionError("ordinary prompts received previous-task payload fields")

    previous_task_context = context(
        invoke(
            hook,
            state,
            active_id,
            "Read the last chat and pick off where we left off",
        )
    )
    for value in (
        "PREVIOUS TASK CONTEXT REQUIRED",
        "list_threads",
        "read_thread",
        "Exclude\nthe current task",
        "ROUTING_CONTEXT",
        "at most 1,200 characters",
        "Send it to the classifier",
        "LAST_TASK_CONTEXT",
        "at most 6,000 characters",
        "Send it to the selected implementer",
        "missing optional artifact never blocks work",
    ):
        if value not in previous_task_context:
            raise AssertionError(f"previous-task dispatch omits {value!r}")
    if len(previous_task_context) > 10_000:
        raise AssertionError("previous-task protocol exceeds its dispatch budget")
    if "PREVIOUS TASK CONTEXT REQUIRED" in routed_context:
        raise AssertionError("ordinary prompts pay the previous-task prompt cost")
    routing_line = "ROUTING_CONTEXT=<exact structured capsule created above>"
    full_line = "LAST_TASK_CONTEXT=<exact full continuity block created above>"
    if previous_task_context.count(routing_line) != 1:
        raise AssertionError("routing capsule is not isolated to one classifier packet")
    if previous_task_context.count(full_line) != 1:
        raise AssertionError("full continuity is not isolated to the selected implementer packet")
    classifier_packet = previous_task_context.split("ORCHESTRATE_CLASSIFY", 1)[1].split(
        "ROLE —", 1
    )[0]
    if routing_line not in classifier_packet or full_line in classifier_packet:
        raise AssertionError("classifier packet did not receive only the routing capsule")
    role_packets = previous_task_context.split("ROLE —", 1)[1]
    if routing_line in role_packets or full_line not in role_packets:
        raise AssertionError("task-role packets did not receive only full continuity")

    negative_previous = context(
        invoke(hook, state, active_id, "Don't read the last chat; fix only this label")
    )
    if "PREVIOUS TASK CONTEXT REQUIRED" in negative_previous:
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
    if "ORCHESTRATE_CLASSIFY" not in direct_question_context:
        raise AssertionError("read-only work skipped the classifier")
    for token in (
        "Every completed user-facing task must end with this compact",
        "## Route",
        "- Class: <friendly class>",
        "- Implementation: <model lane>",
        "- Supervision: None",
        "- Root: <CURRENT_ROOT_ROUTE>",
        "The activation-only acknowledgement",
    ):
        if token not in direct_question_context:
            raise AssertionError(f"direct route receipt contract is missing {token!r}")
    inspection_policy = (
        "INSPECTION_POLICY=Group closely related low-output checks for one immediate question "
        "in one pass; keep unrelated or noisy checks separate."
    )
    if direct_question_context.count(inspection_policy) != 1:
        raise AssertionError("inspection grouping policy is not isolated to the implementer packet")

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
    if "ORCHESTRATE_CLASSIFY" not in combined_context:
        raise AssertionError("combined activation did not select nested Terra orchestration")

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
        "CLASSIFIER_FORK=`1`",
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
            "__ORCHESTRATOR_PROFILE_PATH__",
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
    if exact_contents != [exact_original.strip(), "Starting the task.", exact_add_on]:
        raise AssertionError("early interruption did not preserve the unabridged original request")
    if "MUST_KEEP_THIS_MIDDLE_CONSTRAINT" not in exact_contents[0]:
        raise AssertionError("middle constraints were clipped from the private task bundle")
    if interruption_bundle["messages"][-1].get("current") is not True:
        raise AssertionError("task bundle does not mark the current amendment")

    accepted_transcript = temporary / "accepted.jsonl"
    handoff = """## Continuity

- Outcome: Shipped CSV export
- Delivered: Dashboard export and signed bundle
- Proof: 12 tests passed and production download observed
- Links: https://example.com/export
- Revision: 0123456789abcdef
- Open commitments: Add JSON export
- Next: Add JSON export
- Limitations: None"""
    detailed_report = (
        "## Completed\n\nCSV export is live.\n\n## Links\n\n"
        "- [Live website](https://example.com/export)"
    )
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
                    "content": [
                        {
                            "text": (
                                acceptance + "\n" + handoff + "\n" + detailed_report
                            )
                        }
                    ],
                },
            },
        ],
    )
    accepted = invoke(hook, state, active_id, "New question", accepted_transcript)
    accepted_context = context(accepted)
    if "PRIOR_ACTIVE_ACCEPTANCE: NONE" not in accepted_context:
        raise AssertionError("accepted objective was not cleared")
    if "CLASSIFIER_FORK=`1`" not in accepted_context:
        raise AssertionError("current query did not use one-turn inheritance with its capsule")
    bounded_handoff = " ".join(handoff.split())
    if f"PRIOR_COMPLETED_RESULT: {bounded_handoff}" not in accepted_context:
        raise AssertionError("completion handoff was not passed to the next Terra")
    if "RECENT_CONTEXT_FRESHNESS: FRESH" not in accepted_context:
        raise AssertionError("an immediate follow-up incorrectly made its completion capsule stale")
    if "CSV export is live" in accepted_context:
        raise AssertionError("detailed report replaced the preferred bounded handoff")

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
    if "CLASSIFIER_FORK=`1`" not in legacy:
        raise AssertionError("legacy follow-up did not use one-turn inheritance")
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
        "CLASSIFIER_FORK=`1`",
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
    if completed_value != oversized_handoff[:2_048]:
        raise AssertionError("classifier completion handoff was not bounded to 2,048 characters")
    oversized_bundle = json.loads(
        Path(context_field(oversized, "TASK_CONTEXT_BUNDLE")).read_text(encoding="utf-8")
    )
    if oversized_bundle.get("prior_completed_result") != oversized_handoff:
        raise AssertionError("task roles did not retain the exact unabridged completion handoff")
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

    print("PASS: chat controls, bounded continuity, and completed-rollout elision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
