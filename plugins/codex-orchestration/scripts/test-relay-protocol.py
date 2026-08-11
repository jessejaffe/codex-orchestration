#!/usr/bin/env python3
"""Static contracts for the 0.9.0 classifier/root role boundary."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-terra-orchestrator.toml": (
        "codex_orchestration_terra_orchestrator",
        "gpt-5.6-terra",
        "max",
    ),
    "codex-orchestration-luna-implementer.toml": (
        "codex_orchestration_luna_implementer",
        "gpt-5.6-luna",
        "max",
    ),
    "codex-orchestration-terra-implementer.toml": (
        "codex_orchestration_terra_implementer",
        "gpt-5.6-terra",
        "max",
    ),
    "codex-orchestration-sol-high-implementer.toml": (
        "codex_orchestration_sol_high_implementer",
        "gpt-5.6-sol",
        "high",
    ),
    "codex-orchestration-terra-supervisor.toml": (
        "codex_orchestration_terra_supervisor",
        "gpt-5.6-terra",
        "max",
    ),
    "codex-orchestration-sol-high-supervisor.toml": (
        "codex_orchestration_sol_high_supervisor",
        "gpt-5.6-sol",
        "high",
    ),
    "codex-orchestration-sol-xhigh-supervisor.toml": (
        "codex_orchestration_sol_xhigh_supervisor",
        "gpt-5.6-sol",
        "xhigh",
    ),
}


def require(text: str, values: tuple[str, ...], label: str) -> None:
    for value in values:
        if value not in text:
            raise AssertionError(f"{label} omits {value!r}")


def forbid(text: str, values: tuple[str, ...], label: str) -> None:
    for value in values:
        if value in text:
            raise AssertionError(f"{label} retains forbidden {value!r}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test-relay-protocol.py <plugin-dir>")
    plugin = Path(sys.argv[1])
    agents = plugin / "agents"
    paths = {path.name for path in agents.glob("*.toml")}
    if paths != set(EXPECTED_AGENTS):
        raise AssertionError(
            f"agent inventory mismatch: missing={set(EXPECTED_AGENTS) - paths}, "
            f"extra={paths - set(EXPECTED_AGENTS)}"
        )

    documents: dict[str, str] = {}
    for filename, expected in EXPECTED_AGENTS.items():
        text = (agents / filename).read_text(encoding="utf-8")
        documents[filename] = text
        parsed = tomllib.loads(text)
        actual = (
            parsed.get("name"),
            parsed.get("model"),
            parsed.get("model_reasoning_effort"),
        )
        if actual != expected:
            raise AssertionError(f"wrong model pin for {filename}: {actual!r}")
        if "supervisor" in filename or "orchestrator" in filename:
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.9.0":
        raise AssertionError(f"manifest does not use 0.9.0: {manifest.get('version')!r}")

    orchestrator = documents["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "orchestrator role",
            "always GPT-5.6 Terra / Max",
            "current query plus its bounded conversation continuity",
            "determine the existing orchestration taxonomy",
            "Terra /\nMax may separately be selected as an implementer or supervisor",
            "ORCHESTRATE_CLASSIFY",
            "Do not call tools",
            "Do not\nwrite an acceptance contract or a plan",
            "READ_ONLY: TERRA_MAX / NONE / NONE",
            "SMALL_TWEAK: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE",
            "BIG_TWEAK: TERRA_MAX / TERRA_MAX / ROOT_CAUSE,RELEASE_CANDIDATE",
            "SMALL_BUILD: TERRA_MAX / SOL_HIGH / DESIGN,RELEASE_CANDIDATE",
            "BIG_BUILD: SOL_HIGH / SOL_XHIGH / ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE",
            "exactly these three single lines and\nnothing else",
            "Root owns every subsequent spawn, handoff, wait, checkpoint, and relay",
        ),
        "Terra / Max orchestrator",
    )
    forbid(
        orchestrator,
        (
            "WORKSPACE_DEPENDENCIES=",
            "codex_app__load_workspace_dependencies",
            "spawn_agent",
            "followup_task",
            "wait_agent",
            "SUPERVISOR_INIT",
            "IMPLEMENTATION_CHECKPOINT",
            "ORCHESTRATION_ACCEPTANCE:",
            "ORCHESTRATION_HANDOFF:",
            "ORCHESTRATION_ACCEPT:",
        ),
        "classifier-only orchestrator",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "Orchestration ON (0.9.0)",
            "DIRECT READ-ONLY FAST PATH",
            "ORCHESTRATE_CLASSIFY",
            "fork_turns=none",
            "codex_orchestration_terra_orchestrator",
            "Do\nnot pass FORK, WORKSPACE_DEPENDENCIES, task-specific skill instructions",
            "exactly these three\nlines: ORCHESTRATION_RELATION, ORCHESTRATION_ROUTE, and ORCHESTRATION_STATUS",
            "only\nafter classification, resolve WORKSPACE_DEPENDENCIES",
            "ROOT ROLE MAP",
            "codex_orchestration_terra_implementer",
            "codex_orchestration_luna_implementer",
            "codex_orchestration_sol_high_implementer",
            "codex_orchestration_terra_supervisor",
            "codex_orchestration_sol_high_supervisor",
            "codex_orchestration_sol_xhigh_supervisor",
            "Root owns every child",
            "first spawn only the selected supervisor",
            "Every handoff to an idle existing child uses\n`followup_task`",
            "Never activate implementer and supervisor simultaneously",
            "CHECKPOINT_REVIEW",
            "FINAL_REVIEW",
            "ORCHESTRATION_ROOT_VERIFY",
            "omit it from the user response",
            "__ORCHESTRATOR_PROFILE_PATH__",
            "__AGENTS_DIR__",
        ),
        "root coordinator contract",
    )
    classifier_packet = router[
        router.index("classification packet:") : router.index("After spawning")
    ]
    forbid(
        classifier_packet,
        ("FORK=<", "WORKSPACE_DEPENDENCIES=<", "CURRENT_ROOT_ROUTE=<"),
        "classifier packet",
    )
    if router.index("only\nafter classification, resolve WORKSPACE_DEPENDENCIES") > router.index(
        "call root's `codex_app__load_workspace_dependencies` exactly once"
    ):
        raise AssertionError("workspace dependencies are no longer loaded after classification")

    terra_supervisor = documents["codex-orchestration-terra-supervisor.toml"]
    require(
        terra_supervisor,
        (
            "read-only supervisor for `SMALL_TWEAK` or `BIG_TWEAK`",
            "Root owns all\nagent spawning, waits, checkpoint handoffs, and user relays",
            "ORCHESTRATION_ACCEPTANCE:",
            "CHECKPOINT_REVIEW",
            "FINAL_REVIEW",
            "ORCHESTRATION_HANDOFF:",
            "ORCHESTRATION_ACCEPT: ## Completed",
        ),
        "Terra / Max supervisor",
    )
    forbid(terra_supervisor, ("fused", "spawn_agent", "followup_task"), "Terra supervisor")

    for filename in (
        "codex-orchestration-sol-high-supervisor.toml",
        "codex-orchestration-sol-xhigh-supervisor.toml",
    ):
        require(
            documents[filename],
            (
                "Root owns all",
                "SUPERVISOR_READY:",
                "ORCHESTRATION_ACCEPTANCE:",
                "SUPERVISOR_CORRECT:",
                "SUPERVISOR_READY_TO_RELEASE:",
                "ORCHESTRATION_ROOT_VERIFY:",
                "ORCHESTRATION_HANDOFF:",
                "ORCHESTRATION_ACCEPT: ## Completed",
            ),
            filename,
        )
        forbid(documents[filename], ("fused Terra orchestrator",), filename)

    terra_implementer = documents["codex-orchestration-terra-implementer.toml"]
    require(
        terra_implementer,
        (
            "`READ_ONLY`, `BIG_TWEAK`, or `SMALL_BUILD`",
            "On `READ_ONLY_WORK`",
            "without changing files or external state",
            "ORCHESTRATION_ACCEPT:",
            "Never mutate, commit, push, or deploy on this\nroute",
        ),
        "Terra implementer",
    )
    for filename in (
        "codex-orchestration-luna-implementer.toml",
        "codex-orchestration-terra-implementer.toml",
        "codex-orchestration-sol-high-implementer.toml",
    ):
        require(
            documents[filename],
            (
                "IMPLEMENTATION_CHECKPOINT:",
                "SUPERVISOR_READY_TO_RELEASE",
                "IMPLEMENTATION_RESULT:",
                "root's milestone\nsignals",
                "Root relays the supervisor's",
                "Parse WORKSPACE_DEPENDENCIES before artifact work",
            ),
            filename,
        )

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "485804b5bd058d30c16feedf404595c6f3c347b5e6e5ef794d92b7e35edeb2a5",
            "e28c539964354adca6423c19a0da1746a8db60b94b734f7f00fd88b5a03a41d1",
            "11e5654f28517b4556d9fc13a374f6b97240d8da6f2d8673078730be847f998f",
            "65e904176779be864c6f2cd3d41a5c9424bbc95cc25190a96fc6d02e130655cc",
            "c0361a14a8436a89760398d3823a5796f62fb1cfd30f1460a3827a0d9e0d3db9",
            "8628097f5fddd161710598d5f433f3cbf183d675376e36c5b3cfdebb2d6b18b6",
        ),
        "0.8.19 upgrade digests",
    )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    expected_classes = {case["expected"] for case in fixtures["cases"]}
    if expected_classes != {
        "READ_ONLY",
        "SMALL_TWEAK",
        "BIG_TWEAK",
        "SMALL_BUILD",
        "BIG_BUILD",
    }:
        raise AssertionError(f"triage fixtures do not cover every class: {expected_classes!r}")

    print("PASS: 0.9.0 classifier/root role boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
