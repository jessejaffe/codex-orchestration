#!/usr/bin/env python3
"""Static contract tests for 0.8.12 fused orchestration and live checkpoint handoffs."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-luna-implementer.toml": ("codex_orchestration_luna_implementer", "gpt-5.6-luna", "max"),
    "codex-orchestration-terra-implementer.toml": ("codex_orchestration_terra_implementer", "gpt-5.6-terra", "max"),
    "codex-orchestration-sol-high-implementer.toml": ("codex_orchestration_sol_high_implementer", "gpt-5.6-sol", "high"),
    "codex-orchestration-terra-supervisor.toml": ("codex_orchestration_terra_supervisor", "gpt-5.6-terra", "max"),
    "codex-orchestration-sol-high-supervisor.toml": ("codex_orchestration_sol_high_supervisor", "gpt-5.6-sol", "high"),
    "codex-orchestration-sol-xhigh-supervisor.toml": ("codex_orchestration_sol_xhigh_supervisor", "gpt-5.6-sol", "xhigh"),
}


def require(text: str, values: tuple[str, ...], label: str) -> None:
    for value in values:
        if value not in text:
            raise AssertionError(f"{label} omits {value!r}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test-relay-protocol.py <plugin-dir>")
    plugin = Path(sys.argv[1])
    agents = plugin / "agents"
    paths = {path.name for path in agents.glob("*.toml")}
    if paths != set(EXPECTED_AGENTS):
        raise AssertionError(
            f"agent inventory mismatch: missing={set(EXPECTED_AGENTS) - paths}, extra={paths - set(EXPECTED_AGENTS)}"
        )

    documents: dict[str, str] = {}
    for filename, expected in EXPECTED_AGENTS.items():
        path = agents / filename
        text = path.read_text(encoding="utf-8")
        documents[filename] = text
        parsed = tomllib.loads(text)
        actual = (parsed.get("name"), parsed.get("model"), parsed.get("model_reasoning_effort"))
        if actual != expected:
            raise AssertionError(f"wrong model pin for {filename}: {actual!r}")
        if "supervisor" in filename:
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.8.12":
        raise AssertionError(f"manifest does not use traditional 0.8.12: {manifest.get('version')!r}")
    if "+" in manifest["version"]:
        raise AssertionError("manifest still contains a cachebuster suffix")

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "FIRST ACTION",
            "transparent parent relay",
            "Starting Terra / Max classification now.",
            "terra_orchestrator_<objective_slug>",
            "ORCHESTRATE_INIT",
            "PARENT_TASK=/root",
            "codex_orchestration_terra_supervisor",
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
        ),
        "root relay contract",
    )
    for noisy in (
        "is loading the full task context now",
        "Supervisor ready and staying read-only",
        "On timeout report active phase",
        "Complexity telemetry:",
        "normal agent waits are at most 45 seconds",
        "timeout_ms: 45000",
        "Still working on <actual user outcome>.",
    ):
        if noisy in router:
            raise AssertionError(f"router retains noisy parent copy: {noisy!r}")
    for obsolete in ("headless-grader.py", "--request-token", "grader-requests"):
        if obsolete in router:
            raise AssertionError(f"router retains obsolete headless path: {obsolete!r}")
    for downstream in (
        "codex_orchestration_luna_implementer",
        "codex_orchestration_terra_implementer",
        "codex_orchestration_sol_high_implementer",
        "codex_orchestration_sol_high_supervisor",
        "codex_orchestration_sol_xhigh_supervisor",
    ):
        if downstream in router:
            raise AssertionError(f"root still owns downstream role {downstream!r}")
    for legacy_identity in ("terra_executive", "sol_high_executive", "sol_xhigh_executive"):
        if legacy_identity in router:
            raise AssertionError(f"router retains legacy identity {legacy_identity!r}")

    fused = documents["codex-orchestration-terra-supervisor.toml"]
    require(
        fused,
        (
            "fused GPT-5.6 Terra / Max orchestrator",
            "ORCHESTRATE_INIT",
            "PARENT_TASK",
            "READ_ONLY: TERRA_MAX / NONE / NONE",
            "SMALL_TWEAK: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE",
            "BIG_TWEAK: TERRA_MAX / TERRA_MAX / ROOT_CAUSE,RELEASE_CANDIDATE",
            "SMALL_BUILD: TERRA_MAX / SOL_HIGH / DESIGN,RELEASE_CANDIDATE",
            "BIG_BUILD: SOL_HIGH / SOL_XHIGH / ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE",
            "A feature release is a build",
            "ORCHESTRATION_RELATION: RELATION=<NEW|AMEND|REPLACE|CANCEL>",
            "COMPLEXITY=<1.0-10.0>",
            "Prefix it `ROOT_EXPERIENCE:`",
            "Merely touching frontend or UI files does not trigger it",
            "HTTP 200, asset presence, DOM text, source code",
            "direct experience proof is mandatory",
            "root-executable experience check with live URL or rendered artifact",
            "Do not perform the check\nyourself",
            "ROOT_VERIFICATION_RESULT",
            "For builds, use `followup_task` to reactivate the same\nSol supervisor with the exact result",
            "Do not end your turn after constructing them",
            "continue the workflow in this same turn",
            "For CANCEL use READ_ONLY/1.0/NONE/NONE/NONE",
            "ORCHESTRATION_STATE:",
            "ORCHESTRATION_UPDATE:",
            "ORCHESTRATION_BLOCKED",
            "codex_orchestration_luna_implementer",
            "codex_orchestration_sol_xhigh_supervisor",
            "`send_message`",
            "wait_agent",
            "timeout_ms: 3600000",
            "first start only the\nselected Sol supervisor",
            "initial turn finishes with `SUPERVISOR_READY`. Only then start the selected implementer",
            "keep sibling activity strictly serial",
            "Never activate the implementer and Sol supervisor at the same time",
            "concurrent descendants can be promoted into an unanchored parent activity row",
            "Use `send_message` only for PARENT_TASK",
            "it only queues text and does not start a\nturn",
            "Every handoff to an existing child must use collaboration `followup_task`",
            "use `followup_task` to reactivate the\nsame Sol supervisor",
            "use\n`followup_task` to reactivate the same implementer",
            "reactivate the same Sol supervisor with `FINAL_REVIEW`",
            "Downstream agents are your children, never root's",
        ),
        "fused Terra contract",
    )
    if "Return exactly four single lines and nothing else" in fused:
        raise AssertionError("fused Terra still stops after classification")
    if "orchestrator-executable experience check" in fused:
        raise AssertionError("fused Terra can still consume a root-only experience check")
    if "Build events may arrive out of order" in fused:
        raise AssertionError("fused Terra still permits overlapping build-child startup")
    supervisor_start = fused.index("first start only the\nselected Sol supervisor")
    implementer_start = fused.index(
        "initial turn finishes with `SUPERVISOR_READY`. Only then start the selected implementer"
    )
    if supervisor_start >= implementer_start:
        raise AssertionError("build startup no longer readies the supervisor before the implementer")
    if fused.count("`followup_task`") < 9:
        raise AssertionError("fused Terra does not reactivate every idle-child handoff")
    for deadlocking_copy in (
        "send the checkpoint and immutable lines",
        "then relay\n`SUPERVISOR_CONTINUE`",
        "or send `FINAL_REVIEW`",
        "forward the exact result to the same Sol",
    ):
        if deadlocking_copy in fused:
            raise AssertionError(f"fused Terra retains a message-only child handoff: {deadlocking_copy!r}")

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    previous_release_digests = {
        "luna": "dc769716110ab9b99b0c7caa7de8c5992c39414096d5a79c7b0f6619ee2592e5",
        "terra": "35723b41371a65bf52af621aafc0663022aa51ffb6236b816bc21cd65cdb080e",
        "sol-high": "ad167cec124a4ad4389d92b7e49fe5ba2effbe070bf3a9ced51fc1550edfda83",
        "terra-supervisor": "2e124c8a94ff4aaad427c85910e52b370f732321aaa4e3689af0c9dffffc346b",
        "sol-high-supervisor": "5993929d08fb1003e8def633e41b8aa457cfcd6a748399f513a3c942b5877857",
        "sol-xhigh-supervisor": "c4d37bc0579ed9a2c035bee510fa6fa7a236122fd5178e004bfb3c5df78059b3",
        "0.8.11-terra-supervisor": "d44f6d70de581d3e8895b396cc7a2bba0a2e7fc35cb6ea8531e920cae457aab4",
        "0.8.11-sol-high-supervisor": "427075380b9a3a8a136a6fde53a95252c3031621d51181ec1161318330d027a0",
        "0.8.11-sol-xhigh-supervisor": "30ba4bbee0dcb1ecf22dfb6c6ce98377e72740e717011f7d319e9ccc1f7104bf",
    }
    for role, digest in previous_release_digests.items():
        if digest not in installer:
            raise AssertionError(f"installer omits a released role digest for {role}")

    require(
        fused,
        (
            "read-only",
            "SUPERVISOR_CORRECT:",
            "SUPERVISOR_READY_TO_RELEASE:",
            "ORCHESTRATION_ACCEPT:",
            "same implementer",
            "not narrate role selection, contracts",
        ),
        "codex-orchestration-terra-supervisor.toml",
    )

    for filename in (
        "codex-orchestration-sol-high-supervisor.toml",
        "codex-orchestration-sol-xhigh-supervisor.toml",
    ):
        require(
            documents[filename],
            (
                "read-only",
                "SUPERVISOR_READY:",
                "SUPERVISOR_CORRECT:",
                "SUPERVISOR_READY_TO_RELEASE:",
                "ORCHESTRATION_ACCEPT:",
                "same implementer",
                "before the implementer starts",
                "sibling activity remains serial",
                "fused Terra orchestrator",
                "structured protocol outputs",
                "ROOT_EXPERIENCE",
                "direct experience proof is mandatory",
                "root-executable experience check with live URL or rendered artifact",
                "ROOT_VERIFICATION_RESULT follow-up",
                "ARTIFACTS, and BLOCKER",
            ),
            filename,
        )
        if "I have the full task context. I am staying read-only" in documents[filename]:
            raise AssertionError(f"{filename} retains the initial supervisor narration")

    for filename in (
        "codex-orchestration-luna-implementer.toml",
        "codex-orchestration-terra-implementer.toml",
        "codex-orchestration-sol-high-implementer.toml",
    ):
        require(
            documents[filename],
            (
                "IMPLEMENTATION_CHECKPOINT:",
                "SUPERVISOR_CORRECT",
                "SUPERVISOR_READY_TO_RELEASE",
                "IMPLEMENTATION_RESULT:",
                "yourself",
                "routine waiting",
                "orchestrator's milestone\nsignals",
                "If it does not start ROOT_EXPERIENCE",
                "visual criterion merely because UI files changed",
                "Browser, screenshot, and\nvisual acceptance tools are root-only; do not call or use them",
                "URL-or-path/viewport/START/ACTION/expected RESULT",
            ),
            filename,
        )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    expected_classes = {case["expected"] for case in fixtures["cases"]}
    all_classes = {"READ_ONLY", "SMALL_TWEAK", "BIG_TWEAK", "SMALL_BUILD", "BIG_BUILD"}
    if expected_classes != all_classes:
        raise AssertionError(f"triage fixtures do not cover every class: {expected_classes!r}")
    ids = [case["id"] for case in fixtures["cases"]]
    if len(ids) != len(set(ids)):
        raise AssertionError("triage fixture ids are not unique")
    steering_relations = {case["expected_relation"] for case in fixtures["steering_cases"]}
    if steering_relations != {"AMEND", "REPLACE", "CANCEL"}:
        raise AssertionError("steering fixtures do not cover continuity relations")

    print("PASS: 0.8.12 nested orchestration, live checkpoint handoffs, and root experience review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
