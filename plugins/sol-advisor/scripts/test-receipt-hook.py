#!/usr/bin/env python3
"""Hermetic complexity-persistence, recovery, and Stop-hook regression test."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events)
    )


def token_event(total: int, *, with_meter: bool = False) -> dict:
    payload = {
        "type": "token_count",
        "info": {
            "total_token_usage": {
                "input_tokens": total,
                "cached_input_tokens": 0,
                "output_tokens": 0,
            }
        },
    }
    if with_meter:
        payload["rate_limits"] = {
            "primary": {
                "used_percent": 50.0,
                "window_minutes": 10080,
                "resets_at": 2_000_000_000,
            }
        }
    return {"type": "event_msg", "payload": payload}


def run_hook(hook: Path, hook_input: dict, environment: dict[str, str]) -> dict:
    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(hook_input),
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(completed.stdout)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-receipt-hook.py <plugin-dir> <temp-dir>")
    plugin_dir = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    sessions = temporary / "sessions"
    state = temporary / "state"
    plugin_data = temporary / "plugin-data"
    state.mkdir(parents=True)
    root_id = "11111111-1111-1111-1111-111111111111"
    turn_id = "22222222-2222-2222-2222-222222222222"
    child_id = "33333333-3333-3333-3333-333333333333"
    child_turn_id = "33333333-3333-4333-8333-333333333334"
    grandchild_id = "44444444-4444-4444-4444-444444444444"
    root_rollout = sessions / f"rollout-{root_id}.jsonl"
    child_rollout = sessions / f"rollout-{child_id}.jsonl"
    grandchild_rollout = sessions / f"rollout-{grandchild_id}.jsonl"
    route_without_score = (
        "Executive design and review: GPT-5.6 Terra / High\n"
        "Implementation: GPT-5.6 Terra / Medium"
    )
    route = route_without_score + "\nComplexity: 4.2/10"

    def root_events(route_text: str) -> list[dict]:
        return [
            token_event(100),
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": turn_id},
            },
            {
                "type": "turn_context",
                "payload": {"turn_id": turn_id, "model": "gpt-5.6-sol"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "content": [{"type": "output_text", "text": route_text}],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "kind": "started",
                    "agent_thread_id": child_id,
                },
            },
            token_event(200, with_meter=True),
        ]

    write_jsonl(
        root_rollout,
        root_events(route_without_score),
    )
    write_jsonl(
        child_rollout,
        [
            {
                "type": "session_meta",
                "payload": {"agent_role": "sol_advisor_terra_executive"},
            },
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": child_turn_id},
            },
            {
                "type": "turn_context",
                "payload": {"turn_id": child_turn_id, "model": "gpt-5.6-terra"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "content": [{"type": "output_text", "text": route}],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "kind": "started",
                    "agent_thread_id": grandchild_id,
                },
            },
            token_event(50),
        ],
    )
    write_jsonl(
        grandchild_rollout,
        [
            {"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}},
            token_event(25),
        ],
    )
    today = dt.datetime.now().astimezone().date().isoformat()
    pricing = {
        "checked_date": today,
        "source": "fixture",
        "models": {
            name: {"input": rate, "cached_input": rate, "output": rate}
            for name, rate in (("sol", 10.0), ("terra", 1.0), ("luna", 0.5))
        },
    }
    (state / "pricing.json").write_text(json.dumps(pricing) + "\n")
    (state / "weekly-calibration.json").write_text(
        json.dumps(
            {
                "checked_date": today,
                "pricing_date": today,
                "resets_at": 2_000_000_000,
                "used_percent": 50.0,
                "coverage": 1.0,
                "capacity_credits": 0.01,
            }
        )
        + "\n"
    )
    environment = os.environ.copy()
    environment["SOL_ADVISOR_USAGE_STATE_DIR"] = str(state)
    environment["SOL_ADVISOR_SESSIONS_DIR"] = str(sessions)
    environment["PLUGIN_DATA"] = str(plugin_data)
    hook = plugin_dir / "scripts" / "receipt-stop-hook.py"
    child_pre_tool_input = {
        "hook_event_name": "PreToolUse",
        "transcript_path": str(child_rollout),
        "session_id": child_id,
        "turn_id": child_turn_id,
        "tool_input": {"agent_type": "sol_advisor_terra_medium_implementer"},
    }
    child_pre_tool_result = run_hook(hook, child_pre_tool_input, environment)
    if child_pre_tool_result != {}:
        raise AssertionError(
            "nested producer spawn was not authorized by the executive's repeated "
            f"route: {child_pre_tool_result!r}"
        )
    child_stop_input = {
        "hook_event_name": "Stop",
        "transcript_path": str(child_rollout),
        "session_id": child_id,
        "turn_id": child_turn_id,
        "last_assistant_message": "Terra executive accepted its producer result.",
        "stop_hook_active": False,
    }
    if run_hook(hook, child_stop_input, environment) != {"continue": True}:
        raise AssertionError("delegated Terra executive Stop required a separate receipt")
    if list((state / "effectiveness" / "completions").glob("*.json")):
        raise AssertionError("delegated Terra executive Stop recorded a completion")
    pre_tool_input = {
        "hook_event_name": "PreToolUse",
        "transcript_path": str(root_rollout),
        "session_id": root_id,
        "turn_id": turn_id,
        "tool_input": {"cmd": "read-only-check"},
    }
    denied = run_hook(hook, pre_tool_input, environment)
    decision = denied.get("hookSpecificOutput", {}).get("permissionDecision")
    if decision != "deny":
        raise AssertionError(f"complexity gate allowed a missing score: {denied!r}")

    write_jsonl(root_rollout, root_events(route_without_score + "\nComplexity: 4/10"))
    imprecise = run_hook(hook, pre_tool_input, environment)
    decision = imprecise.get("hookSpecificOutput", {}).get("permissionDecision")
    if decision != "deny":
        raise AssertionError(f"complexity gate allowed an imprecise score: {imprecise!r}")

    write_jsonl(
        root_rollout,
        root_events(
            "Executive design and review: GPT-5.6 Sol / High\n"
            "Implementation: GPT-5.6 Terra / Medium\nComplexity: 4.2/10"
        ),
    )
    invalid_low_executive = run_hook(hook, pre_tool_input, environment)
    if invalid_low_executive.get("hookSpecificOutput", {}).get("permissionDecision") != "deny":
        raise AssertionError("executive gate accepted low-band Sol without fallback evidence")

    write_jsonl(root_rollout, root_events(route))
    if run_hook(hook, pre_tool_input, environment) != {}:
        raise AssertionError("complexity gate rejected an exact route score")
    direct_root_producer = dict(
        pre_tool_input,
        tool_input={"agent_type": "sol_advisor_terra_medium_implementer"},
    )
    direct_denial = run_hook(hook, direct_root_producer, environment)
    if direct_denial.get("hookSpecificOutput", {}).get("permissionDecision") != "deny":
        raise AssertionError("root low route directly spawned a producer before its executive")
    root_executive_spawn = dict(
        pre_tool_input,
        tool_input={"agent_type": "sol_advisor_terra_executive"},
    )
    if run_hook(hook, root_executive_spawn, environment) != {}:
        raise AssertionError("root low route could not spawn Terra executive first")
    persisted_files = list((plugin_data / "route-scores").glob("*.json"))
    root_state_files = [path for path in persisted_files if path.name.startswith(root_id)]
    child_state_files = [path for path in persisted_files if path.name.startswith(child_id)]
    if len(root_state_files) != 1 or len(child_state_files) != 1:
        raise AssertionError(
            f"expected root and nested executive persisted scores, found {persisted_files!r}"
        )
    persisted = json.loads(root_state_files[0].read_text())
    if persisted.get("score") != "4.2":
        raise AssertionError(f"wrong persisted complexity: {persisted!r}")

    receipt_helper = plugin_dir / "scripts" / "usage-receipt.py"
    lifecycle_root = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    lifecycle_child = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    lifecycle_grandchild = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    lifecycle_root_rollout = sessions / f"rollout-{lifecycle_root}.jsonl"
    lifecycle_child_rollout = sessions / f"rollout-{lifecycle_child}.jsonl"
    lifecycle_grandchild_rollout = sessions / f"rollout-{lifecycle_grandchild}.jsonl"
    write_jsonl(
        lifecycle_root_rollout,
        [
            {"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}},
            token_event(100, with_meter=True),
        ],
    )
    write_jsonl(
        lifecycle_child_rollout,
        [{"type": "turn_context", "payload": {"model": "gpt-5.6-terra"}}, token_event(50)],
    )
    write_jsonl(
        lifecycle_grandchild_rollout,
        [{"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}}, token_event(25)],
    )

    def receipt_command(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(receipt_helper), *arguments],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

    receipt_command("start", "--thread-id", lifecycle_root)
    receipt_command("add-thread", lifecycle_child, "--root-thread-id", lifecycle_root)
    receipt_command(
        "add-thread", lifecycle_grandchild, "--root-thread-id", lifecycle_root
    )
    normal_state_path = state / "tasks" / f"{lifecycle_root}.json"
    normal_state = json.loads(normal_state_path.read_text())
    recorded_ids = {
        item.get("thread_id") for item in normal_state.get("threads", [])
        if isinstance(item, dict)
    }
    if recorded_ids != {lifecycle_root, lifecycle_child, lifecycle_grandchild}:
        raise AssertionError(
            f"normal receipt state omitted a nested descendant: {recorded_ids!r}"
        )
    write_jsonl(
        lifecycle_root_rollout,
        [{"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}}, token_event(120, with_meter=True)],
    )
    write_jsonl(
        lifecycle_child_rollout,
        [{"type": "turn_context", "payload": {"model": "gpt-5.6-terra"}}, token_event(60)],
    )
    write_jsonl(
        lifecycle_grandchild_rollout,
        [{"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}}, token_event(30)],
    )
    normal_finish = receipt_command("finish", "--root-thread-id", lifecycle_root, "--keep").stdout.strip()
    expected_normal_finish = (
        "Actual weekly usage: 2.75%\n"
        "All-Sol equivalent: 11.00%\n"
        "Estimated routing savings: 8.25%"
    )
    if normal_finish != expected_normal_finish:
        raise AssertionError(
            f"normal finish omitted or mispriced a nested descendant: {normal_finish!r}"
        )

    receipt = subprocess.run(
        [
            sys.executable,
            str(receipt_helper),
            "recover",
            "--transcript",
            str(root_rollout),
            "--turn-id",
            turn_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()
    expected = (
        "Actual weekly usage: 10.62%\n"
        "All-Sol equivalent: 17.50%\n"
        "Estimated routing savings: 6.88%"
    )
    if receipt != expected:
        raise AssertionError(f"unexpected recovered receipt: {receipt!r}")

    fallback = (
        "Implementation: GPT-5.6 Sol / High — fallback from GPT-5.6 Terra / Medium: "
        "current-turn role unavailable\nComplexity: 6.6/10"
    )
    write_jsonl(root_rollout, root_events(route) + [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "content": [{"type": "output_text", "text": fallback}],
            },
        }
    ])
    if run_hook(hook, pre_tool_input, environment) != {}:
        raise AssertionError("complexity gate rejected a later fallback tool call")
    persisted = json.loads(root_state_files[0].read_text())
    if persisted.get("score") != "4.2":
        raise AssertionError(f"fallback overwrote the route score: {persisted!r}")

    interrupted_session_id = "55555555-5555-5555-5555-555555555555"
    interrupted_turn_id = "66666666-6666-6666-6666-666666666666"
    interrupted_rollout = sessions / f"rollout-{interrupted_session_id}.jsonl"
    interrupted_footer = "\n".join(
        [
            "Executive design and review: GPT-5.6 Terra / High",
            "Implementation: GPT-5.6 Terra / Medium",
            "Complexity: 4.2/10",
            expected,
        ]
    )
    write_jsonl(
        interrupted_rollout,
        [
            token_event(10),
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": interrupted_turn_id},
            },
            {
                "type": "turn_context",
                "payload": {
                    "turn_id": interrupted_turn_id,
                    "model": "gpt-5.6-sol",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "content": [{"type": "output_text", "text": route}],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "turn_aborted",
                    "turn_id": interrupted_turn_id,
                    "reason": "interrupted",
                },
            },
        ],
    )
    interrupted_pre_tool = {
        "hook_event_name": "PreToolUse",
        "transcript_path": str(interrupted_rollout),
        "session_id": interrupted_session_id,
        "turn_id": interrupted_turn_id,
        "tool_input": {"cmd": "read-only-check"},
    }
    if run_hook(hook, interrupted_pre_tool, environment) != {}:
        raise AssertionError("complexity gate rejected the interrupted-turn fixture")
    interrupted_stop = {
        "hook_event_name": "Stop",
        "transcript_path": str(interrupted_rollout),
        "session_id": interrupted_session_id,
        "turn_id": interrupted_turn_id,
        "last_assistant_message": interrupted_footer,
        "stop_hook_active": False,
    }
    if run_hook(hook, interrupted_stop, environment) != {"continue": True}:
        raise AssertionError("hook did not release an interrupted turn")
    early_completions = list((state / "effectiveness" / "completions").glob("*.json"))
    if early_completions:
        raise AssertionError(
            f"hook counted an interrupted turn as completed: {early_completions!r}"
        )

    hook_input = {
        "hook_event_name": "Stop",
        "transcript_path": str(root_rollout),
        "session_id": root_id,
        "turn_id": turn_id,
        "last_assistant_message": fallback,
        "stop_hook_active": False,
    }
    blocked_output = run_hook(hook, hook_input, environment)
    if blocked_output.get("decision") != "block" or expected not in blocked_output.get(
        "reason", ""
    ):
        raise AssertionError(f"hook did not enforce the receipt: {blocked_output!r}")
    reason = blocked_output["reason"]
    if "Complexity: 4.2/10" not in reason or "Complexity: 6.6/10" in reason:
        raise AssertionError(f"hook did not preserve the original score: {reason!r}")
    if "Implementation: GPT-5.6 Sol / High — fallback" not in reason:
        raise AssertionError(f"hook did not report the latest implementation: {reason!r}")
    if "Executive design and review: GPT-5.6 Terra / High" not in reason:
        raise AssertionError(f"hook did not reconstruct the low-band executive: {reason!r}")

    hook_input["last_assistant_message"] = "\n".join(
        [
            "Executive design and review: GPT-5.6 Terra / High",
            fallback.splitlines()[0],
            "Complexity: 4.2/10",
            expected,
        ]
    )
    allowed = run_hook(hook, hook_input, environment)
    if allowed != {"continue": True}:
        raise AssertionError(f"hook rejected a complete receipt: {allowed!r}")
    completions = list((state / "effectiveness" / "completions").glob("*.json"))
    if len(completions) != 1:
        raise AssertionError(f"hook did not record one completion: {completions!r}")
    completion = json.loads(completions[0].read_text())
    if completion.get("session_id") != root_id or completion.get("turn_id") != turn_id:
        raise AssertionError(f"sole completion was not the root task: {completion!r}")
    if completion.get("complexity") != "4.2":
        raise AssertionError(f"hook recorded the wrong complexity: {completion!r}")
    if completion.get("delegated_starts") != 1:
        raise AssertionError(f"hook recorded the wrong delegation count: {completion!r}")
    if (completion.get("task_metrics") or {}).get("total_tokens") != 175:
        raise AssertionError(f"hook recorded the wrong task tokens: {completion!r}")

    high_session = "77777777-7777-7777-7777-777777777777"
    high_turn = "88888888-8888-8888-8888-888888888888"
    high_rollout = sessions / f"rollout-{high_session}.jsonl"
    high_route = (
        "Executive design and review: GPT-5.6 Terra / High\n"
        "Implementation: GPT-5.6 Terra / Medium\nComplexity: 5.0/10"
    )
    write_jsonl(high_rollout, [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": high_turn}},
        {"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": high_route}]}},
    ])
    high_input = dict(pre_tool_input, transcript_path=str(high_rollout), session_id=high_session, turn_id=high_turn)
    if run_hook(hook, high_input, environment).get("hookSpecificOutput", {}).get("permissionDecision") != "deny":
        raise AssertionError("executive gate accepted Terra executive at score 5.0")

    low_fallback_session = "99999999-9999-9999-9999-999999999999"
    low_fallback_turn = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    low_fallback_rollout = sessions / f"rollout-{low_fallback_session}.jsonl"
    low_fallback_route = (
        "Executive design and review: GPT-5.6 Sol / High — Terra executive fallback: current-turn role unavailable\n"
        "Implementation: GPT-5.6 Terra / Medium\nComplexity: 4.9/10"
    )
    write_jsonl(low_fallback_rollout, [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": low_fallback_turn}},
        {"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": low_fallback_route}]}},
    ])
    low_fallback_input = dict(pre_tool_input, transcript_path=str(low_fallback_rollout), session_id=low_fallback_session, turn_id=low_fallback_turn)
    if run_hook(hook, low_fallback_input, environment) != {}:
        raise AssertionError("executive gate rejected verified low-band Terra-executive fallback")
    fallback_root_producer = dict(
        low_fallback_input,
        tool_input={"agent_type": "sol_advisor_terra_medium_implementer"},
    )
    if run_hook(hook, fallback_root_producer, environment) != {}:
        raise AssertionError("verified fallback root could not spawn the mapped producer")

    transition_session = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    transition_turn = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    transition_rollout = sessions / f"rollout-{transition_session}.jsonl"
    transition_events = [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": transition_turn}},
        {"type": "turn_context", "payload": {"turn_id": transition_turn, "model": "gpt-5.6-sol"}},
        {"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": route}]}},
        token_event(10, with_meter=True),
    ]
    write_jsonl(transition_rollout, transition_events)
    transition_input = dict(
        pre_tool_input,
        transcript_path=str(transition_rollout),
        session_id=transition_session,
        turn_id=transition_turn,
    )
    if run_hook(hook, transition_input, environment) != {}:
        raise AssertionError("transition fixture could not persist initial Terra executive")
    exact_transition = (
        "Executive design and review: GPT-5.6 Sol / High — Terra executive fallback: current-turn role unavailable"
    )
    transition_events.append({"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": exact_transition}]}})
    write_jsonl(transition_rollout, transition_events)
    if run_hook(hook, transition_input, environment) != {}:
        raise AssertionError("valid Terra-to-Sol executive fallback was denied")
    transition_states = list((plugin_data / "route-scores").glob(f"{transition_session}-*.json"))
    transition_state = json.loads(transition_states[0].read_text())
    if transition_state.get("executive") != exact_transition:
        raise AssertionError(f"verified fallback was not persisted: {transition_state!r}")

    malformed = "Executive design and review: GPT-5.6 Sol / High — fallback unavailable"
    malformed_events = transition_events + [{"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": malformed}]}}]
    write_jsonl(transition_rollout, malformed_events)
    malformed_result = run_hook(hook, transition_input, environment)
    if malformed_result.get("hookSpecificOutput", {}).get("permissionDecision") != "deny":
        raise AssertionError("malformed executive fallback was accepted")
    transition_stop = {
        "hook_event_name": "Stop",
        "transcript_path": str(transition_rollout),
        "session_id": transition_session,
        "turn_id": transition_turn,
        "last_assistant_message": malformed,
        "stop_hook_active": False,
    }
    reconstructed = run_hook(hook, transition_stop, environment)
    if reconstructed.get("decision") != "block" or exact_transition not in reconstructed.get("reason", ""):
        raise AssertionError(f"Stop did not reconstruct the persisted fallback: {reconstructed!r}")
    if malformed in reconstructed.get("reason", ""):
        raise AssertionError("Stop reconstructed a malformed observed executive")

    downward_events = transition_events + [{"type": "response_item", "payload": {"type": "message", "content": [{"type": "output_text", "text": "Executive design and review: GPT-5.6 Terra / High"}]}}]
    write_jsonl(transition_rollout, downward_events)
    downward_result = run_hook(hook, transition_input, environment)
    if downward_result.get("hookSpecificOutput", {}).get("permissionDecision") != "deny":
        raise AssertionError("fallback route moved downward to Terra")
    print(
        "nested executive Stop suppression, root-first routing, monotonic executive "
        "fallback, root receipt descendant registration, and completion gate passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
