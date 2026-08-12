#!/usr/bin/env python3
"""Static contracts for the 0.11.1 readable seven-class protocol."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-terra-orchestrator.toml": (
        "codex_orchestration_terra_orchestrator", "gpt-5.6-terra", "xhigh"
    ),
    "codex-orchestration-luna-implementer.toml": (
        "codex_orchestration_luna_implementer", "gpt-5.6-luna", "max"
    ),
    "codex-orchestration-terra-implementer.toml": (
        "codex_orchestration_terra_implementer", "gpt-5.6-terra", "max"
    ),
    "codex-orchestration-sol-high-implementer.toml": (
        "codex_orchestration_sol_high_implementer", "gpt-5.6-sol", "high"
    ),
    "codex-orchestration-terra-supervisor.toml": (
        "codex_orchestration_terra_supervisor", "gpt-5.6-terra", "max"
    ),
    "codex-orchestration-sol-high-supervisor.toml": (
        "codex_orchestration_sol_high_supervisor", "gpt-5.6-sol", "high"
    ),
    "codex-orchestration-sol-xhigh-supervisor.toml": (
        "codex_orchestration_sol_xhigh_supervisor", "gpt-5.6-sol", "xhigh"
    ),
}

HUMAN_ROUTES = (
    "Read-only: Terra / Max; no supervisor; no checkpoints",
    "Standard artifact: Luna / Max; Terra / Max; Release candidate",
    "Design artifact: Terra / Max; Terra / Max; Release candidate",
    "Small tweak: Luna / Max; Terra / Max; Release candidate",
    "Big tweak: Terra / Max; Sol / High; Root cause → Release candidate",
    "Small build: Terra / Max; Sol / High; Architecture → Release candidate",
    "Big build: Sol / High; Sol / Extra High; Architecture → Vertical slice → Release candidate",
)

MACHINE_OUTPUT_PREFIXES = (
    "ORCHESTRATION_RELATION:",
    "ORCHESTRATION_ROUTE:",
    "ORCHESTRATION_STATUS:",
    "ORCHESTRATION_ACCEPTANCE:",
    "ORCHESTRATION_HANDOFF:",
    "ORCHESTRATION_ACCEPT:",
    "IMPLEMENTATION_CHECKPOINT:",
    "IMPLEMENTATION_RESULT:",
    "SUPERVISOR_READY:",
    "SUPERVISOR_AMENDED:",
    "SUPERVISOR_CONTINUE:",
    "SUPERVISOR_CORRECT:",
    "SUPERVISOR_READY_TO_RELEASE:",
    "SUPERVISOR_BLOCKED:",
    "SUPERVISOR_SCOPE_REJECT:",
    "ORCHESTRATION_ROOT_VERIFY:",
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
        raise AssertionError(f"agent inventory mismatch: {paths!r}")

    documents: dict[str, str] = {}
    for filename, expected in EXPECTED_AGENTS.items():
        text = (agents / filename).read_text(encoding="utf-8")
        documents[filename] = text
        parsed = tomllib.loads(text)
        actual = (
            parsed.get("name"), parsed.get("model"), parsed.get("model_reasoning_effort")
        )
        if actual != expected:
            raise AssertionError(f"wrong model pin for {filename}: {actual!r}")
        if "supervisor" in filename or "orchestrator" in filename:
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.11.1":
        raise AssertionError(f"manifest does not use 0.11.1: {manifest.get('version')!r}")

    orchestrator = documents["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "always GPT-5.6 Terra / Extra High",
            "latency-critical bounded lookup",
            "## Classification blocked",
            "## Classification",
            "- Relationship: <New|Amend|Replace|Cancel>",
            "- Work class: <Read-only|Standard artifact|Design artifact|Small tweak|Big tweak|Small build|Big build>",
            "- Implementation: <Terra / Max|Luna / Max|Sol / High|None>",
            "- Supervision: <Terra / Max|Sol / High|Sol / Extra High|None>",
            "- Why: <one concise concrete clause",
            "do not expose the uppercase lane identifiers",
            "Do not use a generic phrase such as `substantial behavior\nchange`",
        ),
        "Terra / Extra High orchestrator",
    )
    forbid(orchestrator, MACHINE_OUTPUT_PREFIXES, "orchestrator output")

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "Orchestration ON (0.11.1)",
            "show exactly `Thinking` and nothing else",
            "Starting Terra / Extra High classification now.",
            "fork_turns=1",
            "fork_turns=none",
            "## Classification blocked",
            "Relationship, Active objective, Explicit signal, Work",
            *HUMAN_ROUTES,
            "## Ready",
            "## Acceptance updated",
            "CHANGE WORK — first spawn the selected implementer",
            "Immediately spawn the selected supervisor second",
            "Emit both `spawn_agent` tool calls in one assistant response",
            "## Checkpoint",
            "## Continue",
            "## Corrections required",
            "## Ready to release",
            "## Implementation result",
            "## Root verification needed",
            "## Continuity",
            "## Completed",
            "markdown_section",
            "markdown_bullets",
        ),
        "root coordinator contract",
    )
    implementer_spawn = router.index("CHANGE WORK — first spawn the selected implementer")
    supervisor_spawn = router.index("Immediately spawn the selected supervisor second")
    if implementer_spawn >= supervisor_spawn:
        raise AssertionError("change startup does not spawn the implementer first")

    for filename in (
        "codex-orchestration-luna-implementer.toml",
        "codex-orchestration-terra-implementer.toml",
        "codex-orchestration-sol-high-implementer.toml",
    ):
        document = documents[filename]
        require(
            document,
            (
                "TASK_CONTEXT_BUNDLE",
                "TASK_CONTEXT_REVISION",
                "## Checkpoint",
                "- Phase:",
                "**State**",
                "**Changes**",
                "**Evidence**",
                "**Release plan**",
                "## Implementation result",
                "**Outcome**",
                "**Release**",
                "**Remaining**",
            ),
            filename,
        )
        forbid(document, MACHINE_OUTPUT_PREFIXES, f"{filename} output")

    require(
        documents["codex-orchestration-terra-implementer.toml"],
        ("On `READ_ONLY_WORK`", "## Continuity", "## Completed"),
        "Terra read-only output",
    )

    for filename in (
        "codex-orchestration-terra-supervisor.toml",
        "codex-orchestration-sol-high-supervisor.toml",
        "codex-orchestration-sol-xhigh-supervisor.toml",
    ):
        document = documents[filename]
        require(
            document,
            (
                "TASK_CONTEXT_BUNDLE",
                "TASK_CONTEXT_REVISION",
                "## Ready",
                "- Work class:",
                "- Outcome:",
                "- Must:",
                "- Must not:",
                "- Destinations:",
                "- Open commitments:",
                "- Proof:",
                "## Acceptance updated",
                "## Scope mismatch",
                "## Corrections required",
                "## Ready to release",
                "## Blocked",
                "## Root verification needed",
                "## Continuity",
                "## Completed",
            ),
            filename,
        )
        forbid(document, MACHINE_OUTPUT_PREFIXES, f"{filename} output")

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "Exact 0.11.0 profiles accepted for the 0.11.1 readable-protocol migration",
            "57fa0c83e001f8300054982123580bf63ec8d2ac6c5adbd9ea5c5a47e395310f",
            "3df9d5071bd120ba4ff63f372277f09d38e650c0b914362e5057864ffc2d72a6",
            "3e3aae30c769489c8776467a5b6497f76eacfbdf424a9e0b098b642abd00bfbd",
            "12f3d61ec1705cbfdc3ac8e60dd338d7fec7716b055371d632a2ffa6f2e25a24",
            "2a5154885d32df32c87713dba1e7e58ec09f98e6720fd13a2d01b5f2ebd931b2",
            "a4b93a9a04494d93a9b8b902888bf123ae0dafa76972124f2e2e2a3d84b97cc5",
            "b1d57d6e649bef6275a87994587010594dc16344f27ec2979f7964b295964dc4",
        ),
        "0.11.0 migration digests",
    )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    expected_classes = {case["expected"] for case in fixtures["cases"]}
    all_classes = {
        "READ_ONLY", "STANDARD_ARTIFACT", "DESIGN_ARTIFACT", "SMALL_TWEAK",
        "BIG_TWEAK", "SMALL_BUILD", "BIG_BUILD",
    }
    if expected_classes != all_classes:
        raise AssertionError(f"triage fixtures do not cover every class: {expected_classes!r}")

    print("PASS: 0.11.1 readable seven-class context and relay protocol")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
