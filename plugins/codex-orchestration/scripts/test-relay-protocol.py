#!/usr/bin/env python3
"""Static contracts for the 0.10.5 context-bundle and activity protocol."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


EXPECTED_AGENTS = {
    "codex-orchestration-terra-orchestrator.toml": (
        "codex_orchestration_terra_orchestrator",
        "gpt-5.6-terra",
        "xhigh",
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
    if manifest.get("version") != "0.10.5":
        raise AssertionError(f"manifest does not use 0.10.5: {manifest.get('version')!r}")

    orchestrator = documents["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "orchestrator role",
            "always GPT-5.6 Terra / Extra High",
            "inherited current query plus its bounded conversation continuity",
            "latency-critical bounded lookup",
            "USER_REQUEST=INHERITED_CURRENT_QUERY",
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
            "ORCHESTRATION_STATUS: REASON=",
            "This is a <friendly class> because <reason>.",
            "Do not use a generic phrase such as `substantial behavior\nchange`",
            "end REASON with punctuation",
            "Root owns every subsequent spawn, handoff, wait, checkpoint, and relay",
        ),
        "Terra / Extra High orchestrator",
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

    if "inherited root user request and attachments that precede this protocol packet" not in " ".join(orchestrator.split()):
        raise AssertionError("orchestrator omits one-turn current-query inheritance")
    for filename, document in documents.items():
        if "orchestrator" in filename:
            continue
        compact = " ".join(document.split())
        if "TASK_CONTEXT_BUNDLE" not in compact or "TASK_CONTEXT_REVISION" not in compact:
            raise AssertionError(f"{filename} omits exact task-context loading")

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    require(
        router,
        (
            "Orchestration ON (0.10.5)",
            "DESKTOP ACTIVITY DISPLAY",
            "one plain 2-7 word current milestone",
            "Waiting for Terra / Extra High classification",
            "Starting Luna / Max implementation",
            "show exactly `Thinking` and nothing else",
            "DIRECT READ-ONLY FAST PATH",
            "FAST RELAY",
            "ORCHESTRATE_CLASSIFY",
            "fork_turns=1",
            "fork_turns=none",
            "USER_REQUEST=INHERITED_CURRENT_QUERY",
            "TASK_CONTEXT_BUNDLE:",
            "TASK_CONTEXT_REVISION:",
            "codex_orchestration_terra_orchestrator",
            *ROUTES,
            "codex_orchestration_luna_implementer",
            "codex_orchestration_terra_implementer",
            "codex_orchestration_sol_high_implementer",
            "codex_orchestration_terra_supervisor",
            "codex_orchestration_sol_high_supervisor",
            "codex_orchestration_sol_xhigh_supervisor",
            "terra_extra_high_orchestrator_<objective_slug>",
            "terra_max_implementer_<objective_slug>",
            "terra_max_supervisor_<objective_slug>",
            "luna_max_implementer_<objective_slug>",
            "sol_high_implementer_<objective_slug>",
            "sol_high_supervisor_<objective_slug>",
            "sol_extra_high_supervisor_<objective_slug>",
            "CHANGE WORK — first spawn the selected implementer",
            "ACCEPTANCE=PENDING_SUPERVISOR_INIT",
            "ACTIVE STEERING",
            "AMENDMENT_REVIEW",
            "PAUSE_FOR_REVISED_ACCEPTANCE",
            "Immediately spawn the selected supervisor second",
            "Emit both `spawn_agent` tool calls in one assistant response",
            "Do not wait for or process the implementer spawn output",
            "ORCHESTRATION_STATUS: REASON=",
            "Require a nonempty exact `ORCHESTRATION_STATUS: REASON=` value",
            "This is a <friendly class> because <exact reason>.",
            "Use dynamic lane labels exactly: LUNA_MAX=Luna / Max",
            "TERRA_MAX=Terra / Max, SOL_HIGH=Sol / High, and SOL_XHIGH=Sol / Extra High",
            "Never hard-code the\nbig-tweak sentence or its models",
            "Root owns every child",
            "every handoff to an idle child uses `followup_task`",
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
            "first spawn only the selected supervisor",
            "Wait for that turn to finish before spawning an implementer",
            "This is a <friendly class>. Implementation started",
            "big_tweak_implementer_<objective_slug>",
            "big_tweak_supervisor_<objective_slug>",
            "Starting orchestration with verbatim request",
            "Planning orchestration and classification steps",
            "USER_REQUEST=<exact current request and attachment paths>",
            "USER_REQUEST=<exact request and attachment paths>",
            "The classifier always uses none",
        ),
        "root routes",
    )

    implementer_spawn = router.index("CHANGE WORK — first spawn the selected implementer")
    supervisor_spawn = router.index("Immediately spawn the selected supervisor second")
    if implementer_spawn >= supervisor_spawn:
        raise AssertionError("change startup does not spawn the implementer before the supervisor")
    supervisor_packet = router[
        router.index("Immediately spawn the selected supervisor second with:") :
        router.index("Emit both `spawn_agent` tool calls in one assistant response")
    ]
    if "WORKSPACE_DEPENDENCIES=" in supervisor_packet:
        raise AssertionError("context-only supervisor startup still copies workspace dependencies")
    coordination = router[
        router.index("COORDINATION LOOP") : router.index("`ORCHESTRATION_ROOT_VERIFY`")
    ]
    for repeated_context in ("USER_REQUEST", "RECENT_CONTEXT", "CLASSIFICATION"):
        if repeated_context in coordination:
            raise AssertionError(f"follow-up relays still repeat {repeated_context}")

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
                "`ACCEPTANCE=PENDING_SUPERVISOR_INIT` is expected and is not a\nblocker",
                "TASK_CONTEXT_BUNDLE",
                "TASK_CONTEXT_REVISION",
                "Load it fully before mutation",
                "On `TASK_CONTEXT_UPDATE`",
                "Root includes the",
                "with every later supervisor decision",
                "Before yielding `RELEASE_CANDIDATE`, resolve an executable release plan",
                "**Release plan**",
                "This is an execution-only turn",
                "## Outcome",
                "## Evidence",
                "## Release",
                "## Remaining",
                "never emit `STATE=`, `EVIDENCE=`",
            ),
            filename,
        )
        forbid(
            documents[filename],
            (
                "STATE=<completed outcome and artifacts>",
                "EVIDENCE=<each acceptance item mapped to actual evidence>",
                "REVISION=<commit and pushed branch or NOT_APPLICABLE>",
                "INCOMPLETE=<NONE or exact remaining work>",
            ),
            filename,
        )

    for filename in (
        "codex-orchestration-terra-supervisor.toml",
        "codex-orchestration-sol-high-supervisor.toml",
        "codex-orchestration-sol-xhigh-supervisor.toml",
    ):
        require(
            documents[filename],
            (
                "implementer's initial turn is already active",
                "TASK_CONTEXT_BUNDLE",
                "TASK_CONTEXT_REVISION",
                "AMENDMENT_REVIEW",
                "SUPERVISOR_AMENDED:",
                "**Approved release plan**",
                "- Repository: <exact synchronization, commit, and push sequence or NOT_APPLICABLE>",
                "- Deployment: <exact helper or narrow destination for the changed deliverables or NOT_APPLICABLE>",
                "- Verification: <one decisive released-state probe or NOT_APPLICABLE>",
                "- Tunnel: <exact open/close lifecycle or NOT_APPLICABLE>",
            ),
            filename,
        )
        compact_supervisor = " ".join(documents[filename].lower().split())
        if "executable without fresh topology or deployment research" not in compact_supervisor:
            raise AssertionError(f"{filename} permits release-time deployment discovery")
        if "inspect no workspace state" not in compact_supervisor:
            raise AssertionError(f"{filename} permits workspace inspection during startup overlap")
        if "read only the exact file named by task_context_bundle" not in compact_supervisor:
            raise AssertionError(f"{filename} can load more than the exact context bundle at startup")
        if "unabridged ordered root-visible" not in compact_supervisor:
            raise AssertionError(f"{filename} does not require the exact ordered task context")

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "Exact 0.10.4 profiles accepted for the 0.10.5 context-bundle migration",
            "daad8fa64a161d02615b2df99e7ffef1a56e7a6114e3831b116d42a2e1c18fa2",
            "06e935c579bc2797cbb86a2f146cdc1eddfdd1a389ebded53e4e57cea9a64079",
            "8a7e78e5480f19449753194d5171b7ee06d44ea9bd4ea5768beed45947ba5ab3",
            "3be0b8c8ee64cb00fc642ed5fac1c0bb44ac3ba726b5fb3329d11691546a6f17",
            "a9db7125294104eede7c587f22db62901e2af857ff3a5ccfbff10f13d26bba97",
            "22e2167ebceaacabbeec00b5fa4ad822187921182f0d14a7528408e58fc16e6e",
            "1b49c843b4794cfba17d708b6d01fdfd498ef5011e72fd288d469df81ec221cf",
            "Exact 0.10.3 profiles accepted for the 0.10.4 startup-latency migration",
            "b7f25d2474fbe35e42b14f6683fca4a2398da5bc9a5a9c7ca70b7c7fa8f543cb",
            "fd962b99e92a116957c867299d9bc1713cd8faed721c8bc79b35685c5f58470a",
            "fe023cd9d4f1ece2ed386679afb5a3ad50f2f2048d8cfe40605397b5780dc4b7",
            "75340397335c5a18b1112233d75d2a51d3033bf3a8ef578841b4d2da1aafedc8",
            "66af783589d285cd99e5a427cbcdc0c87de279f0005ab03e55b3fa3d3c93eee3",
            "3678c195db31f3bf54fcac7d8d0d31afe19d9edb108ed1e33aedcef4b1717ae8",
            "02ea1e6f7242f20ef761962b9c6a8c25f4d7cc5ce88ff8c6ee9674d2f89f9995",
            "Exact 0.10.2 profiles accepted for the 0.10.3 readable release migration",
            "142b58957a44c91e45bd4f110f30fce855a6e6cb23ec8069bba87e900ccc3e33",
            "db744d545558fd8f93dfa93392c0ea1ace9d451e074fa700121d69a7d10f8fd8",
            "d781b21e3292ce238770cd4b424f8430a319fdf0e4c7d4342617b54a55d3f5f1",
            "a9341b5e3d2a463a5a094bd0268b6413371b71c65f13cf3b46ee9132ae6f4071",
            "cdcaf2f3ddb1fb265398b9196a9124fcbe8f2c7b0c8617b15293faf5d6f41e48",
            "97dbcc78d98cc74231a08c30d60c5ab057726fdf2a866dd620194df00503be5b",
            "Exact 0.10.0 profiles accepted for the 0.10.1 startup migration",
            "fc3b2c7ac8b13f48153d30010841f1e9f1bbe60bebb4c514474922b98f3ec8cd",
            "b3152056861c84c5484cb4379345a32487abac083dd04aec358a670236fc010b",
            "50bc87e9dac98c05b5516fedc6991ab12e9358e40d8bfd27be90e3433b5389f0",
            "bdad29925cdc5ab880439ab8eda6ce2f81499625e0a5040176008153799c933d",
            "280fee892205538302205df54baa28fe97e43a53173673098bfa66c8bb21ead4",
            "356432b1c0578f3066b017fe28eb5436708532eb89d4ec754919db7fcc209991",
            "b68755047b744057258b4957e6894692588fb8462cb78c466acb4b98a87a4f8b",
            "Exact 0.9.0 profiles accepted for the 0.10.0 taxonomy migration",
            "143f2b6d5c917352df0b5c6a57608ac70f702f0bbc0ff779eedd5cf1243babd4",
            "5e55237eabb9315b5ece06ae5239bf5740c69adc9ffcc508f7b0ac3ecaf060d1",
            "a5277a7f3870f57eca209d21c63a2ac1b95e6918ab4c7c31bd45534d452f64ec",
            "ed407f41f1d0c2b54417cac2d18647fd1f5156ae321eb3c28415ccbb833cebb4",
            "4e16a42744c5a2b3503f1ab1eb0638047a77bbf17470567306721fec95ec7b71",
            "48520a33a70bfceb920fee852ee991f0305170bd255bbf5455146e6ac88281d8",
            "7dc6715eec52fda116d10bb3154353b2020e093976dc47dc4cdee55bee12b24d",
        ),
        "0.10.4, 0.10.3, 0.10.2, 0.10.0, and 0.9.0 migration digests",
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

    print("PASS: 0.10.5 exact-context activity and relay protocol")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
