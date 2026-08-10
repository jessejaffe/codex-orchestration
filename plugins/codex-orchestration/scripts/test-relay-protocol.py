#!/usr/bin/env python3
"""Static contract tests for 0.8.3 classification, fallback, and supervision."""

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
        if any(role in filename for role in ("grader", "read-only", "supervisor", "executive")):
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.8.3":
        raise AssertionError(f"manifest does not use traditional 0.8.3: {manifest.get('version')!r}")
    if "+" in manifest["version"]:
        raise AssertionError("manifest still contains a cachebuster suffix")

    grader = documents["codex-orchestration-terra-grader.toml"]
    require(
        grader,
        (
            "Work class is the routing authority; numeric complexity is",
            "`READ_ONLY`",
            "`SMALL_TWEAK`",
            "`BIG_TWEAK`",
            "`SMALL_BUILD`",
            "`BIG_BUILD`",
            "A release containing a feature is a build",
            "Tests, documentation, generated metadata, routine release work",
            "Ambiguity routes upward",
            "IMPLEMENTER=`LUNA_MAX`",
            "IMPLEMENTER=`TERRA_MAX`",
            "IMPLEMENTER=`SOL_HIGH`",
            "SUPERVISOR=`TERRA_MAX`",
            "SUPERVISOR=`SOL_HIGH`",
            "SUPERVISOR=`SOL_XHIGH`",
            "Never emit `READY_TO_DISPATCH`",
        ),
        "grader contract",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "Spawn the implementer\nfirst and immediately spawn the supervisor second",
            "TASK-CATALOG COMPATIBILITY",
            "built-in `worker` with",
            "built-in `default` with",
            "Never use a legacy custom-agent identity",
            "same implementer fixes",
            "WAIT AND PROGRESS",
            "waits of at most 45 seconds",
            "READY_TO_DISPATCH",
            "Complexity telemetry:",
        ),
        "root relay contract",
    )
    if "attempt an unavailable identity" not in router:
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

    print("PASS: 0.8.3, five work classes, eight roles, direct fallback, and progress contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
