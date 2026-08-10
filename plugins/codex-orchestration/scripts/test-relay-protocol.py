#!/usr/bin/env python3
"""Static contract tests for 0.8.1 classification and checkpoint supervision."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-terra-grader.toml": ("codex_orchestration_terra_grader", "gpt-5.6-terra", "max"),
    "codex-orchestration-terra-read-only.toml": ("codex_orchestration_terra_read_only", "gpt-5.6-terra", "max"),
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

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.8.1":
        raise AssertionError(f"manifest does not use traditional 0.8.1: {manifest.get('version')!r}")
    if "+" in manifest["version"]:
        raise AssertionError("manifest still contains a cachebuster suffix")

    grader = documents["codex-orchestration-terra-grader.toml"]
    require(
        grader,
        (
            "authority; complexity is one-decimal telemetry only",
            "`READ_ONLY`",
            "`SMALL_TWEAK`",
            "`BIG_TWEAK`",
            "`SMALL_BUILD`",
            "`BIG_BUILD`",
            "A new release that contains a new feature is a build",
            "Tests, docs, generated metadata, and routine deployment are",
            "If a boundary is ambiguous, choose the larger class",
            "codex_orchestration_luna_implementer",
            "codex_orchestration_terra_implementer",
            "codex_orchestration_sol_high_implementer",
            "codex_orchestration_terra_supervisor",
            "codex_orchestration_sol_high_supervisor",
            "codex_orchestration_sol_xhigh_supervisor",
        ),
        "grader contract",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "start the implementer first",
            "Immediately after `spawn_agent` returns",
            "same `fork_turns",
            "supervisor is ready and the checkpoint exists",
            "same implementer performs every correction",
            "same implementer alone commits, pushes, deploys",
            "Complexity must be one decimal",
            "For `CANCEL`, require class READ_ONLY",
            "Complexity telemetry:",
        ),
        "root relay contract",
    )
    if router.index("start the implementer first") > router.index("Immediately after `spawn_agent` returns"):
        raise AssertionError("router does not specify implementer-before-supervisor ordering")

    for filename in (
        "codex-orchestration-terra-supervisor.toml",
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
            ),
            filename,
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
                "SUPERVISOR_CORRECT",
                "SUPERVISOR_READY_TO_RELEASE",
                "IMPLEMENTATION_RESULT:",
                "yourself",
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

    print("PASS: traditional version, five work classes, eight roles, and checkpoint relay contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
