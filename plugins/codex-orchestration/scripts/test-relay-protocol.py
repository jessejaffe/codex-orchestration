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
        "codex_orchestration_luna_implementer", "gpt-5.6-luna", "max"
    ),
    "codex-orchestration-terra-implementer.toml": (
        "codex_orchestration_terra_implementer", "gpt-5.6-terra", "max"
    ),
    "codex-orchestration-sol-high-implementer.toml": (
        "codex_orchestration_sol_high_implementer", "gpt-5.6-sol", "high"
    ),
}

HUMAN_ROUTES = (
    "Read-only: Luna / Max",
    "Standard artifact: Luna / Max",
    "Design artifact: Terra / Max",
    "Small tweak: Luna / Max",
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

    if sum(map(len, prompts.values())) > 15_000:
        raise AssertionError("agent prompts exceed the 15,000-character single-agent budget")

    require(
        prompts["codex-orchestration-luna-implementer.toml"],
        ("You own `READ_ONLY`", "`STANDARD_ARTIFACT`", "`SMALL_TWEAK`", "never mutates"),
        "Luna implementer route ownership",
    )
    forbid(
        prompts["codex-orchestration-terra-implementer.toml"],
        ("You own `READ_ONLY`",),
        "Terra implementer route ownership",
    )

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
            "scope interpretation, implementation, verification, and authorized release",
            "terminal visual handoff",
            "PREMISE MISMATCH", "## Premise review", "same implementer",
            "## Root verification needed", "terminal root-only Browser/visual check", "cache-bypass",
            "Ground truth and Source", "ambiguous support",
            "capture a screenshot", "Judge pass, fail, or blocked",
            "editing, spawning, or calling `followup_task`",
            "Work report as the primary content", "Preserve its delivered work, nonvisual proof",
            "mention it only as", "Work: <next or None — reason>",
            "Visual check: <exact user check>", "never in",
            "Continuity or Current state", "Never replace the work recap",
            "Every terminal response",
            "## Continuity", "## Completed",
            "### Current state", "### Next step", "no Recommendations section",
            "preserve the completed work and decisive evidence",
            "A next step is valid only when supported by", "Reject a bare",
            "`None` or invented follow-on work", "REPORT_REVISION_REQUIRED",
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
            "`None` is invalid", "recommended future state and concrete action over current-state recap",
            "luna_high_implementer_<objective_slug>", "## Root verification result",
            "ROOT_VERIFICATION_RECOVERY_REQUIRED", "### Recommendations",
            "## Route", "- Supervision: None", "route footer",
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
                "Never infer a named product", "identity, purpose, wording, or canonical link",
                "one authoritative in-scope source", "rather than guess",
                "defining outcome", "rendered appearance", "user interaction",
                "reported visual mismatch", "not merely because UI files changed",
                "prepare an accessible target", "## Root verification needed",
                "- Requirement:", "- Ground truth:", "- Source:", "- Check:",
                "- Targets:", "- Viewport:", "- Work report:", "delivered work",
                "nonvisual proof", "legitimate work next",
                "This is a terminal handoff",
                "Stop permanently", "passes, fails, or is blocked",
                "Do not expect a result, retry, or correction", "## Blocked",
                "Make the report complete", "what exists, what was done or found, why it",
                "matters, and the supporting evidence", "Do not add a Recommendations section",
                "Put actionable future", "guidance only in Next step", "only when warranted",
                "- Next: <one legitimate evidence-backed action, or None — reason",
                "## Continuity", "## Completed", "### Current state",
                "### Next step", "Use `Action`, `Why`, and `Success` only when",
                "None — <why no further action is warranted>", "Never invent work",
            ),
            filename,
        )
        forbid(
            prompt,
            (
                "## Awaiting acceptance", "## Checkpoint", "## Implementation result",
                "## Ready to release", "supervisor ready", "final-review agent",
                "recommendation-led", "keep the current-state recap brief", "never None",
                "Spend more space on the future state", "Stop until root returns",
                "request another root check", "Alternatives exhausted",
                "### Recommendations", "## Route", "- Supervision: None",
            ),
            filename,
        )

    terra = prompts["codex-orchestration-terra-implementer.toml"]
    require(
        terra,
        ("`DESIGN_ARTIFACT`", "`BIG_TWEAK`", "`SMALL_BUILD`"),
        "Terra end-to-end lane",
    )

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "four Codex Orchestration 0.13.0 profiles",
            "Exact previously shipped profiles accepted for safe in-place migration",
            "f8c6190b3e4375ece24eb02ab9db0983a5f8c4cad47a126059cbc2c62f344194",
            "68179487b09d11667c6a0e69e48cec65348847df7ebb0e501e67ed47de0114a6",
            "86ad93904293ac3bc1613cdb1512274c4524ca19fd9ce1841e5744355207a6f6",
            "3bbb7c2464542eb135640782b52c9d213486bc351d60b8fe0c40ef21a1368e5c",
            "830aebc3d5c40da3aae60b20e6f760b29fe32c68d67fdd7db3d5ae9d49ff9bfa",
            "6ee395bb2287fd8fe8276e87f2ba7429a8eac67a771561ad71f30f5ed787a6cb",
            "82f9358fa7ed1d6ab7f9c297dccc721c626191879d1ec73ee5038dd8888afdce",
            "c61310125d3af082ffc6fcb9712fc0c07f630c9e08a3a582e727cfdf612c6d31",
            "b42701c0431ba0018f1e22ea7923d0c04b550e4232aa1221d8a9f067d45b8ef9",
            "89234fa1bcb7f3fe98e909cdf2775b61293a91174d04b6801169f2defd0204a2",
            "f01797baa0997b63c0ad9b70a29e1d07cdd5e8056b9520b711fc8482e180edd3",
            "153a8603fd959e951471a81cec4c7dbda293d6793d98e4c5d03a89b9f3abf744",
            "662c7b7010cc87e902f1f2608f74a8bce7bd06df659e3de778fc761d3667fbbe",
            "930bd325d9d19c93ffbb70497410ff9f0a03c657fde81e04a8ccd3272f206424",
            "2a8be332df4cd578f599c3f5dac89930f7cd13503393a0f380ee3a4a128492f7",
            "2716b3635a68f8fed0961e69be92c1b18338c6a1897876592fd58a061932e082",
            "dbcaf41ebdb469251ca316154d10ae6a8717ea0228c3e580c1e411851ceee8fb",
            "171fa0d31db51f032d323b417a063e8ff374709013c9f7751e8cf44f53f77cbc",
            "e4ab97f67fed62023c204dd8f3688b144c07f62ec0ee1ba169c5c791232a2d1b",
            "6181d4b59b74c3688c6c5e3c94482c152b52861cd1fbb68c0e003d60fa73f8f5",
            "4a9a6947e04ae14df2855b3c495bf03311571d20f5125ed50a62fd113c28401d",
            "08aa1335248a15ee305e30edb35662b28d95d31b266a67351acfa696ced1e3ec",
            "b21cd346b39eb94f4119bf180fc1b3354a9f3259f469fe22b43233fee1433177",
            "c0da09a763a31e77d4b9390e524eb61ead0b730a5024c9c322761a9b39f056a2",
            "66a549c67e7f81f0d0e6db89ec85af7d1a47253b376e255344c603459ec0ea7c",
            "2574ab7e01874599ed4b05940d7b9a0898e0fb21564a5ac8ce3961a6ebcbaaf3",
            "45e2549938493020446261a960b12d800d0244b794d10bb280fda0041720ed5f",
            "f980e92ded78673ecb3052af93492d0cc5bf295dbcf0e27aa3df41a05ebbd852",
            "6f4a5eb3d93109728ea2cf4bc955da0f3eee58422e8baa15b8c4d98354529064",
            "Preflight every target", "refusing $state retired role",
        ),
        "profile installer",
    )

    reinstaller = (plugin / "scripts" / "reinstall-plugin.sh").read_text(encoding="utf-8")
    require(
        reinstaller,
        (
            "installed plugin reported an unsafe cache alias",
            "reported cache alias $current differs from $manifest_version",
            "installed through reported cache alias $current",
        ),
        "plugin reinstaller",
    )
    forbid(
        reinstaller,
        ("installed version $current does not match $manifest_version",),
        "plugin reinstaller",
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
