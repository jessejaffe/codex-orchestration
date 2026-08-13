#!/usr/bin/env python3
"""Static contracts for the 0.13.0 classifier-to-single-agent protocol."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-terra-orchestrator.toml": (
        "codex_orchestration_terra_orchestrator", "gpt-5.6-terra", "xhigh"
    ),
    "codex-orchestration-luna-implementer.toml": (
        "codex_orchestration_luna_implementer", "gpt-5.6-luna", "high"
    ),
    "codex-orchestration-terra-implementer.toml": (
        "codex_orchestration_terra_implementer", "gpt-5.6-terra", "max"
    ),
    "codex-orchestration-sol-high-implementer.toml": (
        "codex_orchestration_sol_high_implementer", "gpt-5.6-sol", "high"
    ),
}

HUMAN_ROUTES = (
    "Read-only: Terra / Max",
    "Standard artifact: Luna / High",
    "Design artifact: Terra / Max",
    "Small tweak: Luna / High",
    "Big tweak: Terra / Max",
    "Small build: Terra / Max",
    "Big build: Sol / High",
)


def require(text: str, values: tuple[str, ...], label: str) -> None:
    for value in values:
        if value not in text:
            raise AssertionError(f"{label} omits {value!r}")


def forbid(text: str, values: tuple[str, ...], label: str) -> None:
    for value in values:
        if value in text:
            raise AssertionError(f"{label} retains forbidden {value!r}")


def dispatch_prompt_chars(router: str) -> int:
    module = ast.parse(router)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "DISPATCH_CONTEXT" for target in node.targets
        ):
            return len(ast.literal_eval(node.value))
    raise AssertionError("DISPATCH_CONTEXT assignment is missing")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test-relay-protocol.py <plugin-dir>")
    plugin = Path(sys.argv[1])
    agents_dir = plugin / "agents"
    actual_agents = {path.name for path in agents_dir.glob("*.toml")}
    if actual_agents != set(EXPECTED_AGENTS):
        raise AssertionError(f"agent inventory mismatch: {actual_agents!r}")

    prompts: dict[str, str] = {}
    for filename, expected in EXPECTED_AGENTS.items():
        parsed = tomllib.loads((agents_dir / filename).read_text(encoding="utf-8"))
        actual = (parsed.get("name"), parsed.get("model"), parsed.get("model_reasoning_effort"))
        if actual != expected:
            raise AssertionError(f"wrong model pin for {filename}: {actual!r}")
        prompt = parsed.get("developer_instructions")
        if not isinstance(prompt, str) or not prompt.strip():
            raise AssertionError(f"missing developer instructions: {filename}")
        prompts[filename] = prompt
        if "orchestrator" in filename and parsed.get("sandbox_mode") != "read-only":
            raise AssertionError("the classifier must remain read-only")
        if "implementer" in filename and "sandbox_mode" in parsed:
            raise AssertionError(f"end-to-end agent is unexpectedly read-only: {filename}")

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"0\.13\.0(?:\+codex\.[0-9A-Za-z._-]+)?", version
    ):
        raise AssertionError(f"manifest does not use the 0.13.0 line: {version!r}")

    if sum(map(len, prompts.values())) > 11_600:
        raise AssertionError("agent prompts exceed the 11,600-character single-agent budget")

    orchestrator = prompts["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "only classify", "Use only the current request and bounded routing context",
            "## Classification blocked", "## Classification",
            "- Relationship: <New|Amend|Replace|Cancel>", "- Work class:",
            "- Complexity:", "- Why: <brief reason>",
        ),
        "orchestrator",
    )
    forbid(
        orchestrator,
        ("- Implementation:", "- Supervision:", "- Checkpoints:", "call tools"),
        "orchestrator",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    if dispatch_prompt_chars(router) > 6_500:
        raise AssertionError("root dispatch prompt exceeds the 6,500-character budget")
    require(
        router,
        (
            "Orchestration ON (0.13.0)", "exactly two stages",
            "one selected implementer owns the task end to end",
            "PREVIOUS TASK CONTEXT REQUIRED", "list_threads", "read_thread",
            "Send it to the classifier", "Send it to the selected implementer",
            "Keep startup quiet", "fork_turns=1", "fork_turns=none", *HUMAN_ROUTES,
            "EXECUTE — Spawn exactly one mapped implementer",
            "Never spawn a supervisor, reviewer, grader, or a", "second writer",
            "END_TO_END_WORK", "IMPLEMENTATION_ROUTE=<friendly selected model lane>",
            "scope interpretation, implementation, verification, authorized release, and the final report",
            "PREMISE MISMATCH", "## Premise review", "same implementer",
            "## Root verification needed", "perform exactly the requested read-only Browser/visual observation",
            "hand the evidence back to the same implementer with `followup_task`",
            "## Root verification result", "- Start:", "- Action:", "- Result:",
            "same implementer corrects the work", "## Continuity", "## Completed",
            "## Next step", "`None` is invalid", "recommended future state and concrete action",
            "replacement inputs or behavior", "REPORT_REVISION_REQUIRED",
            "## Route", "- Supervision: None", "- Root: <CURRENT_ROOT_ROUTE>",
        ),
        "root coordinator",
    )
    inspection_policy = (
        "INSPECTION_POLICY=Group closely related low-output checks for one immediate question "
        "in one pass; keep unrelated or noisy checks separate."
    )
    if router.count(inspection_policy) != 1:
        raise AssertionError("inspection policy must appear only in the selected-agent packet")
    forbid(
        router,
        (
            "FAST PATH", "Launch the selected supervisor", "PENDING_SUPERVISOR",
            "codex_orchestration_terra_supervisor", "codex_orchestration_sol_high_supervisor",
            "codex_orchestration_sol_xhigh_supervisor", "IMPLEMENTATION_CHECKPOINT",
            "SUPERVISOR_READY", "FINAL_REVIEW", "Awaiting acceptance",
        ),
        "root coordinator",
    )

    for filename in (
        "codex-orchestration-luna-implementer.toml",
        "codex-orchestration-terra-implementer.toml",
        "codex-orchestration-sol-high-implementer.toml",
    ):
        prompt = prompts[filename]
        require(
            prompt,
            (
                "own", "end to end", "Never spawn agents", "END_TO_END_WORK",
                "read TASK_CONTEXT_BUNDLE and start immediately", "use applicable skills",
                "proportionate", "verification", "finish the user-facing",
                "## Premise mismatch", "## Premise review", "working copy as given",
                "A request to implement locally does not itself authorize",
                "Browser and visual acceptance observations are root-only",
                "## Root verification needed", "- Requirement:", "- Check:", "- Targets:",
                "Stop until root returns `## Root verification result`",
                "correct the work and request another root check", "## Blocked",
                "recommendation-led", "keep the current-state recap brief",
                "target behavior, input, or configuration", "never stop at abstractions",
                "exact signals or fields", "values or thresholds", "confidence/provenance",
                "Spend more space on the future state", "action than on status",
                "- Next: <one concrete highest-leverage action; never None>",
                "## Continuity", "## Completed", "## Next step", "- Action:", "- Why:",
                "- Success:", "## Route",
                "- Implementation: <IMPLEMENTATION_ROUTE>", "- Supervision: None",
                "- Root: <CURRENT_ROOT_ROUTE>",
            ),
            filename,
        )
        forbid(
            prompt,
            (
                "## Awaiting acceptance", "## Checkpoint", "## Implementation result",
                "## Ready to release", "supervisor ready", "final-review agent",
            ),
            filename,
        )

    terra = prompts["codex-orchestration-terra-implementer.toml"]
    require(
        terra,
        ("`READ_ONLY`", "`DESIGN_ARTIFACT`", "`BIG_TWEAK`", "`SMALL_BUILD`", "never mutates"),
        "Terra end-to-end lane",
    )

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "four Codex Orchestration 0.13.0 profiles",
            "Exact 0.12.10 and initial 0.13.0 profiles accepted for safe in-place migration",
            "f8c6190b3e4375ece24eb02ab9db0983a5f8c4cad47a126059cbc2c62f344194",
            "68179487b09d11667c6a0e69e48cec65348847df7ebb0e501e67ed47de0114a6",
            "86ad93904293ac3bc1613cdb1512274c4524ca19fd9ce1841e5744355207a6f6",
            "662c7b7010cc87e902f1f2608f74a8bce7bd06df659e3de778fc761d3667fbbe",
            "930bd325d9d19c93ffbb70497410ff9f0a03c657fde81e04a8ccd3272f206424",
            "2a8be332df4cd578f599c3f5dac89930f7cd13503393a0f380ee3a4a128492f7",
            "e4ab97f67fed62023c204dd8f3688b144c07f62ec0ee1ba169c5c791232a2d1b",
            "6181d4b59b74c3688c6c5e3c94482c152b52861cd1fbb68c0e003d60fa73f8f5",
            "4a9a6947e04ae14df2855b3c495bf03311571d20f5125ed50a62fd113c28401d",
            "Preflight every target", "refusing $state retired role",
        ),
        "profile installer",
    )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    classes = {case["expected"] for case in fixtures["cases"]}
    expected_classes = {
        "READ_ONLY", "STANDARD_ARTIFACT", "DESIGN_ARTIFACT", "SMALL_TWEAK",
        "BIG_TWEAK", "SMALL_BUILD", "BIG_BUILD",
    }
    if classes != expected_classes:
        raise AssertionError(f"triage fixtures do not cover every class: {classes!r}")

    print("PASS: 0.13.0 classifier-to-single-agent protocol")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
