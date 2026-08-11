#!/usr/bin/env python3
"""Static contracts for the 0.10.0 six-class taxonomy and role boundary."""

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

ROUTES = (
    "READ_ONLY: TERRA_MAX / NONE / NONE",
    "STANDARD_ARTIFACT: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE",
    "DESIGN_ARTIFACT: TERRA_MAX / TERRA_MAX / RELEASE_CANDIDATE",
    "SMALL_TWEAK: LUNA_MAX / TERRA_MAX / RELEASE_CANDIDATE",
    "BIG_TWEAK: TERRA_MAX / SOL_HIGH / ROOT_CAUSE,RELEASE_CANDIDATE",
    "BUILD: SOL_HIGH / SOL_XHIGH / ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE",
)


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
    if manifest.get("version") != "0.10.0":
        raise AssertionError(f"manifest does not use 0.10.0: {manifest.get('version')!r}")

    orchestrator = documents["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "orchestrator role",
            "always GPT-5.6 Terra / Max",
            "current query plus its bounded conversation continuity",
            "Do not call tools",
            "Do not\nwrite an acceptance contract or a plan",
            "STANDARD_ARTIFACT: create or edit a non-code deliverable",
            "Specific spreadsheet formulas remain standard artifact work",
            "DESIGN_ARTIFACT: create or edit a non-code deliverable whose visual composition",
            "SMALL_TWEAK: one bounded change to existing code behavior in one component",
            "BIG_TWEAK: multiple existing code behavior changes",
            "BUILD: any net-new code capability, regardless of component count",
            "Writing an artifact is a mutation but is not a code tweak or build",
            "A UI change inside an app or\nwebsite is code",
            *ROUTES,
            "Root owns every subsequent spawn, handoff, wait, checkpoint, and relay",
        ),
        "Terra / Max orchestrator",
    )
    forbid(
        orchestrator,
        (
            "WORKSPACE_DEPENDENCIES=",
            "spawn_agent",
            "followup_task",
            "SUPERVISOR_INIT",
            "ORCHESTRATION_ACCEPTANCE:",
            "SMALL_BUILD",
            "BIG_BUILD",
        ),
        "taxonomy-only orchestrator",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "Orchestration ON (0.10.0)",
            "DIRECT READ-ONLY FAST PATH",
            "ORCHESTRATE_CLASSIFY",
            "fork_turns=none",
            "codex_orchestration_terra_orchestrator",
            *ROUTES,
            "codex_orchestration_luna_implementer",
            "codex_orchestration_terra_implementer",
            "codex_orchestration_sol_high_implementer",
            "codex_orchestration_terra_supervisor",
            "codex_orchestration_sol_high_supervisor",
            "codex_orchestration_sol_xhigh_supervisor",
            "Root owns every child",
            "Every handoff to an idle existing child uses\n`followup_task`",
            "Never activate implementer and supervisor simultaneously",
            "CHECKPOINT_REVIEW",
            "FINAL_REVIEW",
            "ORCHESTRATION_ROOT_VERIFY",
        ),
        "root coordinator contract",
    )
    forbid(
        router,
        (
            "SMALL_BUILD: TERRA_MAX",
            "BIG_BUILD: SOL_HIGH",
        ),
        "root routes",
    )

    luna = documents["codex-orchestration-luna-implementer.toml"]
    require(
        luna,
        (
            "`STANDARD_ARTIFACT` or `SMALL_TWEAK`",
            "content, data, formulas, structure",
            "one bounded\nchange to existing code behavior in one component",
            "artifact appearance is a\ndefining outcome",
        ),
        "Luna implementer",
    )

    terra_implementer = documents["codex-orchestration-terra-implementer.toml"]
    require(
        terra_implementer,
        (
            "`READ_ONLY`, `DESIGN_ARTIFACT`, or `BIG_TWEAK`",
            "On `READ_ONLY_WORK`",
            "`DESIGN_ARTIFACT`: `RELEASE_CANDIDATE` only",
            "does not add a software-design checkpoint",
            "`BIG_TWEAK`: `ROOT_CAUSE`, then `RELEASE_CANDIDATE`",
        ),
        "Terra implementer",
    )

    sol_implementer = documents["codex-orchestration-sol-high-implementer.toml"]
    require(
        sol_implementer,
        (
            "implementer for `BUILD`",
            "any net-new code capability, regardless of\ncomponent count",
            "`ARCHITECTURE`",
            "`VERTICAL_SLICE`",
            "`RELEASE_CANDIDATE`",
        ),
        "Sol / High implementer",
    )

    terra_supervisor = documents["codex-orchestration-terra-supervisor.toml"]
    require(
        terra_supervisor,
        (
            "`STANDARD_ARTIFACT`, `DESIGN_ARTIFACT`",
            "or\n`SMALL_TWEAK`",
            "SUPERVISOR_READY: CLASS=<STANDARD_ARTIFACT|DESIGN_ARTIFACT|SMALL_TWEAK>",
            "artifact class or `SMALL_TWEAK`, review RELEASE_CANDIDATE only",
            "does not add a software-design checkpoint",
            "For DESIGN_ARTIFACT, PROOF always starts with `ROOT_EXPERIENCE:`",
            "ORCHESTRATION_ACCEPT: ## Completed",
        ),
        "Terra supervisor",
    )

    big_tweak_supervisor = documents["codex-orchestration-sol-high-supervisor.toml"]
    require(
        big_tweak_supervisor,
        (
            "supervisor for `BIG_TWEAK`",
            "multiple existing\ncode behavior changes",
            "SUPERVISOR_READY: CLASS=BIG_TWEAK",
            "CHECKPOINT_REVIEW: PHASE=ROOT_CAUSE",
            "- Work class: BIG_TWEAK",
            "- Supervisor: GPT-5.6 Sol / High",
            "- Implementation: GPT-5.6 Terra / Max",
            "ORCHESTRATION_ACCEPT: ## Completed",
        ),
        "Sol / High big-tweak supervisor",
    )

    sol_supervisor = documents["codex-orchestration-sol-xhigh-supervisor.toml"]
    require(
        sol_supervisor,
        (
            "supervisor for `BUILD`: any net-new code",
            "SUPERVISOR_READY: CLASS=BUILD",
            "- Work class: BUILD",
            "ORCHESTRATION_ACCEPT: ## Completed",
        ),
        "Sol / Extra High supervisor",
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
                "Parse WORKSPACE_DEPENDENCIES before artifact work",
            ),
            filename,
        )

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "Exact 0.9.0 profiles accepted for the 0.10.0 taxonomy migration",
            "143f2b6d5c917352df0b5c6a57608ac70f702f0bbc0ff779eedd5cf1243babd4",
            "5e55237eabb9315b5ece06ae5239bf5740c69adc9ffcc508f7b0ac3ecaf060d1",
            "a5277a7f3870f57eca209d21c63a2ac1b95e6918ab4c7c31bd45534d452f64ec",
            "ed407f41f1d0c2b54417cac2d18647fd1f5156ae321eb3c28415ccbb833cebb4",
            "4e16a42744c5a2b3503f1ab1eb0638047a77bbf17470567306721fec95ec7b71",
            "48520a33a70bfceb920fee852ee991f0305170bd255bbf5455146e6ac88281d8",
            "7dc6715eec52fda116d10bb3154353b2020e093976dc47dc4cdee55bee12b24d",
        ),
        "0.9.0 migration digests",
    )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    expected_classes = {case["expected"] for case in fixtures["cases"]}
    all_classes = {
        "READ_ONLY",
        "STANDARD_ARTIFACT",
        "DESIGN_ARTIFACT",
        "SMALL_TWEAK",
        "BIG_TWEAK",
        "BUILD",
    }
    if expected_classes != all_classes:
        raise AssertionError(f"triage fixtures do not cover every class: {expected_classes!r}")
    ids = [case["id"] for case in fixtures["cases"]]
    if len(ids) != len(set(ids)):
        raise AssertionError("triage fixture ids are not unique")
    steering_relations = {case["expected_relation"] for case in fixtures["steering_cases"]}
    if steering_relations != {"AMEND", "REPLACE", "CANCEL"}:
        raise AssertionError("steering fixtures do not cover continuity relations")

    print("PASS: 0.10.0 six-class taxonomy and classifier/root boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
