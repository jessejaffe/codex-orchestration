#!/usr/bin/env python3
"""Static contract tests for 0.8.4 native grading and checkpoint supervision."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
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
        if any(role in filename for role in ("grader", "read-only", "supervisor", "executive")):
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.8.4":
        raise AssertionError(f"manifest does not use traditional 0.8.4: {manifest.get('version')!r}")
    if "+" in manifest["version"]:
        raise AssertionError("manifest still contains a cachebuster suffix")

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "FIRST ACTION",
            "Starting Terra / Max classification now.",
            "built-in `default` with model",
            "`gpt-5.6-terra`, reasoning `max`",
            "`terra_max_grader_<objective_slug>`",
            "Terra / Max is classifying this request now.",
            "intervals of at most 15 seconds",
            "READ_ONLY=no mutation",
            "SMALL_TWEAK=one existing behavior/one component",
            "BIG_TWEAK=existing",
            "SMALL_BUILD=one new capability",
            "BIG_BUILD=2+ capabilities",
            "feature release is a build",
            "ambiguity routes upward",
            "READ_ONLY=TERRA_MAX/NONE/NONE",
            "SMALL_TWEAK=LUNA_MAX/TERRA_MAX/RELEASE_CANDIDATE",
            "BIG_TWEAK=TERRA_MAX/TERRA_MAX/ROOT_CAUSE,RELEASE_CANDIDATE",
            "SMALL_BUILD=TERRA_MAX/SOL_HIGH/DESIGN,RELEASE_CANDIDATE",
            "BIG_BUILD=SOL_HIGH/SOL_XHIGH/ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE",
            "Spawn the implementer first and immediately spawn",
            "same implementer",
            "normal work waits are at most 45 seconds",
            "READY_TO_DISPATCH",
            "Complexity telemetry:",
        ),
        "root relay contract",
    )
    if "codex_orchestration_terra_grader" in router:
        raise AssertionError("router retains the broken custom Terra grader presentation")
    if "Never attempt an unavailable or legacy type" not in router:
        raise AssertionError("router does not guard unavailable task-catalog identities")
    for legacy_identity in ("terra_executive", "sol_high_executive", "sol_xhigh_executive"):
        if legacy_identity in router:
            raise AssertionError(f"router retains legacy identity {legacy_identity!r}")

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
                "at least once every 45 seconds",
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

    print("PASS: 0.8.4, native Terra grader, seven companion profiles, and progress contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
