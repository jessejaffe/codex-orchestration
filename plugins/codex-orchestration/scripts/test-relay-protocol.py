#!/usr/bin/env python3
"""Static contracts for the 0.12.5 lean orchestration protocol."""

from __future__ import annotations

import ast
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
    "Small tweak: Luna / Max; Terra / Max; no checkpoints",
    "Big tweak: Terra / Max; Sol / High; Release candidate",
    "Small build: Terra / Max; Sol / High; Architecture → Release candidate",
    "Big build: Sol / High; Sol / Extra High; Architecture → Vertical slice → Release candidate",
)

MACHINE_PREFIXES = (
    "ORCHESTRATION_RELATION:", "ORCHESTRATION_ROUTE:", "ORCHESTRATION_ACCEPTANCE:",
    "IMPLEMENTATION_CHECKPOINT:", "IMPLEMENTATION_RESULT:", "SUPERVISOR_READY:",
    "SUPERVISOR_CORRECT:", "SUPERVISOR_READY_TO_RELEASE:",
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
    if {path.name for path in agents_dir.glob("*.toml")} != set(EXPECTED_AGENTS):
        raise AssertionError("agent inventory mismatch")

    documents: dict[str, str] = {}
    prompts: dict[str, str] = {}
    for filename, expected in EXPECTED_AGENTS.items():
        text = (agents_dir / filename).read_text(encoding="utf-8")
        parsed = tomllib.loads(text)
        documents[filename] = text
        prompts[filename] = parsed["developer_instructions"]
        actual = (parsed.get("name"), parsed.get("model"), parsed.get("model_reasoning_effort"))
        if actual != expected:
            raise AssertionError(f"wrong model pin for {filename}: {actual!r}")
        if "supervisor" in filename or "orchestrator" in filename:
            if parsed.get("sandbox_mode") != "read-only":
                raise AssertionError(f"read-only role is not sandboxed: {filename}")
        forbid(text, MACHINE_PREFIXES, filename)

    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("version") != "0.12.5":
        raise AssertionError(f"manifest does not use 0.12.5: {manifest.get('version')!r}")

    if sum(map(len, prompts.values())) > 19_000:
        raise AssertionError("agent prompts exceed the 19,000-character lean budget")

    orchestrator = prompts["codex-orchestration-terra-orchestrator.toml"]
    require(
        orchestrator,
        (
            "only classify", "Use only the current request and bounded routing context",
            "## Classification blocked",
            "## Classification", "- Relationship: <New|Amend|Replace|Cancel>",
            "- Work class:", "- Complexity:", "- Why: <brief reason>",
        ),
        "orchestrator",
    )
    forbid(
        orchestrator,
        (
            "Do not call tools", "prior transcripts", "The current request controls",
            "UI work is code", "Ambiguity routes", "Fixed lanes", "- Implementation:",
            "- Supervision:", "- Checkpoints:", "Do not expose uppercase lane identifiers",
        ),
        "orchestrator",
    )

    router = (plugin / "scripts" / "prompt-router-hook.py").read_text(encoding="utf-8")
    if dispatch_prompt_chars(router) > 7_500:
        raise AssertionError("root dispatch prompt exceeds the 7,500-character lean budget")
    require(
        router,
        (
            "Orchestration ON (0.12.5)", "PREVIOUS TASK CONTEXT REQUIRED", "list_threads",
            "read_thread", "ROUTING_CONTEXT", "at most 1,200 characters",
            "Send it to the classifier", "LAST_TASK_CONTEXT", "at most 6,000 characters",
            "Send it to supervisors and implementers",
            "missing optional artifact never blocks work", "Starting Terra / Extra High classification now.",
            "fork_turns=1", "fork_turns=none", *HUMAN_ROUTES,
            "CHANGE WORK — Start implementation before acceptance construction",
            "Launch the selected implementer first", "Launch the selected supervisor immediately next",
            "ACCEPTANCE=PENDING_SUPERVISOR_INIT",
            "Deliver it immediately", "`send_message` if the implementer runs",
            "stop or redirect work that no longer matches",
            "Small tweak starts immediately",
            "activity label must stay exactly `Thinking`", "dynamic phase, plan, repository",
            "big tweak has three", "## Root verification needed", "## Continuity", "## Completed",
        ),
        "root coordinator",
    )
    implementer_start = router.index("Launch the selected implementer first")
    supervisor_start = router.index("Launch the selected supervisor immediately next")
    if implementer_start >= supervisor_start:
        raise AssertionError("the implementer is not launched before the supervisor")
    forbid(
        router,
        (
            "Small tweak: Luna / Max; Terra / Max; Release candidate",
            "Big tweak: Terra / Max; Sol / High; Root cause → Release candidate",
            "Spawn the selected supervisor first", "Emit both `spawn_agent` calls back-to-back",
            "RELATIONSHIPS —", "Never mutate under superseded acceptance",
            "latest verified milestone", "Building with Luna / Max",
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
                "TASK_CONTEXT_BUNDLE", "start immediately", "Before acceptance",
                "do not commit", "deploy", "return `## Awaiting acceptance`",
                "fetch GitHub once", "Reuse one", "synchronization baseline",
                "## Checkpoint", "**Release plan**", "## Implementation result",
                "**Acceptance evidence**", "**Release**", "**Remaining**",
            ),
            filename,
        )
        forbid(
            prompt,
            (
                "TASK_CONTEXT_REVISION", "LAST_TASK_CONTEXT", "not a blocker",
                "background artifacts", "Inspect dirt first", "stopped-run edits",
                "dirt does not prove active ownership", "Isolate only", "project discovery",
                "narrowest decisive", "applicable skills", "fresh deployment research",
            ),
            filename,
        )

    require(
        prompts["codex-orchestration-luna-implementer.toml"],
        ("`SMALL_TWEAK` has no implementer checkpoint", "commit/push"),
        "Luna small-tweak flow",
    )
    require(
        prompts["codex-orchestration-terra-implementer.toml"],
        ("`BIG_TWEAK`: `RELEASE_CANDIDATE` only", "On `READ_ONLY_WORK`"),
        "Terra flow",
    )

    for filename in (
        "codex-orchestration-terra-supervisor.toml",
        "codex-orchestration-sol-high-supervisor.toml",
        "codex-orchestration-sol-xhigh-supervisor.toml",
    ):
        prompt = prompts[filename]
        require(
            prompt,
            (
                "read TASK_CONTEXT_BUNDLE", "## Ready", "already working", "do not wait",
                "Inspect no workspace yet", "Keep optional material outside Must",
                "- Work class:", "- Outcome:", "- Must:", "- Destinations:",
                "- Open commitments:", "- Proof:",
                "## Corrections required", "## Ready to release", "## Blocked",
                "## Root verification needed", "## Continuity", "## Completed",
            ),
            filename,
        )
        forbid(
            prompt,
            (
                "TASK_CONTEXT_REVISION", "LAST_TASK_CONTEXT", "mentioned attachment",
                "On route conflict", "## Scope mismatch", "AMENDMENT_REVIEW",
                "Optional evidence cannot block", "without broadening", "Never fix",
                "- Must not:",
            ),
            filename,
        )

    require(
        prompts["codex-orchestration-terra-supervisor.toml"],
        ("`SMALL_TWEAK`: no implementer checkpoint", "review only `FINAL_REVIEW`"),
        "Terra supervisor small-tweak flow",
    )
    require(
        prompts["codex-orchestration-sol-high-supervisor.toml"],
        ("`BIG_TWEAK`: `RELEASE_CANDIDATE` only",),
        "Sol supervisor big-tweak flow",
    )

    installer = (plugin / "scripts" / "install-agents.sh").read_text(encoding="utf-8")
    require(
        installer,
        (
            "Exact 0.12.4 supervisor profiles accepted for the 0.12.5 positive-acceptance migration",
            "8fc6bdccbf27ec2344adca5e458d2330a16fac98d3db6b0fec0cdb14da8480f4",
            "b4e326ac895bc23df8bd30f6ed209b44fa80c049617a2ba605049599c0b4e6fd",
            "9fd4345c1481e4775a0340b54cd64b16932f42cafff06505396cbfd39a92b418",
            "Exact 0.12.3 profiles accepted for the 0.12.4 prompt-simplification migration",
            "cb92150a2164cc1d1f89952320119111669e9953a0b8a837a539eec191167430",
            "d2084c6421ef931e0efd1b7b377df59662a2fcbd526b7e023492d0bc875e24e2",
            "52b773dd1602abcf38e1bc04b7e4271b46547a19a30b2dbb2b8a15410c4f3429",
            "Exact 0.12.2 profiles accepted for the 0.12.3 recovery-policy migration",
            "9e28f2e3d38aa6300a399d12be19f2ab5e787d3efdd616d38e2653009dfc375b",
            "0091625c0a072a2a5638b4a8d20ecbe4c2e019d3ce9fba5f1e2a47dac2fe7ef2",
            "92cd6c7967721fcfdc806809aba07fa0270b6ff1c3c189822efc782388f328eb",
            "7d3263b72da6fd4f032e1b054f93edd439e93f44d91c604de46ec276b9dded6e",
            "5afb5cc35dfc8019af35c716a70cca1bf208d2c7116972671f97a64813885d76",
            "15a433bdc6435bb1dae245967c93ac439ed775624eb723ffe4d647750b037066",
            "Exact 0.12.1 profiles accepted for the 0.12.2 implementer-first migration",
            "4b0f87ceca26a8525524a56e520a2595c5ee95fb8ee216d7f6bd6bba2192471a",
            "Exact 0.12.0 profiles accepted for the 0.12.1 split-context migration",
            "e2e6ff81543ba52fb032beab6c3169a2fea9cacc177cb29ef077a88576d41468",
            "ba553fd5ece225cc3d01c9d16065802bcad97d066f3931b9d2ae2f22eaa2344a",
            "68def43161e10a599bad5a4e63d12d79178b487ed4f5fb58fe81dd42b0b2c557",
            "1224f0bbe949d0aa170924fb2d34978d02762d6f6cb02036e3629f645b8da6a5",
            "c7a70970173bccf55eac14393541a72be027a27e58362213e958acb35e63a69c",
            "368699b87b35b1704e4b32b9781471183682c18e8ba7d73538bf448551b1e538",
            "caf2176d6ad6f3aba1f3ed27e3bf4b7b1bfd393fa269149daf25812bdcf24b0f",
            "Exact 0.11.1 profiles accepted for the 0.12.0 lean-context migration",
            "0d7289514349fc3ecf7891f8a77a98c275af6389b2ed9a3df73cfde4a87762de",
            "d225c7ffa7cb27cafc427140b4926d4ccd43132a622a23e97cb9974fa61b1eb1",
            "bcee12a8397d09cf9900243f4b98149b447d18c4fbf4b727e2a9dd069a5a3b0b",
            "40ce291a1ea9b0de52d5e7e3b6b25ce9beb3c83c1ed4569d16de8c40e8ef6399",
            "811a02078feff67e9fa91140b9d143c44637fcde2d3543054f77567a1ef46662",
            "2b4064414c7b5064584608a4322c7fca06357327ef4eaaf36ce6895a3916c97a",
            "d46cb59fb0eddc68f7deff81e83f1379ecee9d9a561c2cc22a904626aa165cf2",
        ),
        "profile migration digests",
    )

    fixtures = json.loads((plugin / "scripts" / "triage-cases.json").read_text())
    classes = {case["expected"] for case in fixtures["cases"]}
    expected_classes = {
        "READ_ONLY", "STANDARD_ARTIFACT", "DESIGN_ARTIFACT", "SMALL_TWEAK",
        "BIG_TWEAK", "SMALL_BUILD", "BIG_BUILD",
    }
    if classes != expected_classes:
        raise AssertionError(f"triage fixtures do not cover every class: {classes!r}")

    print("PASS: 0.12.5 lean orchestration protocol")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
