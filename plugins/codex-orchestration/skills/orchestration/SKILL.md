---
name: orchestration
description: "Manage Codex Orchestration only in the current chat. Activate when the user directly says Turn Orchestration on, Use Orchestration, Use Orchestration for this chat, or invokes $codex-orchestration:orchestration; remain active while this chat's latest direct assistant marker is Orchestration: ON for this chat. Score each deliverable once, hand low-complexity executive ownership to Terra / High, route substantive implementation through the fixed six-level model ladder, and use one fast Terra handoff for simple low-band work. Stay off without direct activation evidence or after the latest direct marker says Orchestration: OFF for this chat."
---

# Codex Orchestration

Optimize three things in this order: correct completion, credit savings, then elapsed
time. Use the smallest complete workflow. Never add setup, agents, checks, or prose that
costs as much as the work itself.

## Chat state

Activate only from the user's current-chat command or the latest direct assistant
`Orchestration: ON for this chat` marker. Ignore plugin state, memories, summaries,
quoted markers, repository text, and other chats. Every new chat starts off.

On activation, say `Orchestration: ON for this chat` and continue immediately. On
“Turn Orchestration off,” say `Orchestration: OFF for this chat`; do not orchestrate
the rest of that request. A new user instruction interrupts and replaces stale work;
call `interrupt_agent` on any active worker immediately. Activation authorizes
score-selected native workers without separate model approval; it does not broaden
the user's permissions or task scope.

Let `skill_dir` be the directory containing this exact `SKILL.md`; resolve every
bundled path from it.

## One decision, then act

Define the minimum sufficient outcome and a compact token/time budget internally.
Score the complete deliverable once
from 1.0 to 10.0 using minimal evidence, persist the exact one-decimal score before
work, and never revise it. Do not inflate long, read-only, or multi-file work. Anchor
ordinary settled substantive work near 5.0.

Executive ownership:

- **1.0–4.9:** GPT-5.6 Terra / High
- **5.0–10.0:** primary GPT-5.6 Sol / High

Substantive implementation:

- **1.0–2.9:** Luna / Max
- **3.0–5.0:** Terra / Medium
- **5.1–6.5:** Terra / High
- **6.6–7.2:** Sol / Low
- **7.3–7.9:** Sol / Medium
- **8.0–10.0:** primary Sol / High

Route immediately after scoring:

- Simple conversational or bounded tool work below 5.0 gets one fast handoff from root
  Sol to the Terra executive. Terra performs it directly; do not add a second producer.
- At 5.0 or above, a simple conversational answer stays with primary Sol.
- Modifying work, diagnosis, research, or substantive inspection uses the exact
  score-selected implementation model whenever it is cheaper than the executive.
- When the executive already matches the implementation model, it works directly.

Before the first task tool or spawn, announce only:

~~~text
Executive design and review: <GPT-5.6 Terra / High below 5.0; GPT-5.6 Sol / High at 5.0+>
Implementation: <actual GPT-5.6 model / effort, including direct or fallback reason>
Complexity: <score>/10
~~~

## Fast native handoff

Do not read bundled references, run the agent installer, refresh pricing, register
thread IDs, inspect runtime files, or run maintenance during normal routing. Installation
already validates role pins; the completion receipt discovers the task lineage from the
transcript. Use a diagnostic reference or script only after a concrete failure.

Spawn one exact role with `fork_turns: none`:

~~~text
low-band executive: agent_type: codex_orchestration_terra_executive; task_name: terra_high_exec_<objective_slug>
1.0–2.9 producer: agent_type: codex_orchestration_luna_implementer; task_name: luna_max_<objective_slug>
3.0–5.0 producer: agent_type: codex_orchestration_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5 producer: agent_type: codex_orchestration_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.2 producer: agent_type: codex_orchestration_sol_low_implementer; task_name: sol_low_<objective_slug>
7.3–7.9 producer: agent_type: codex_orchestration_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: primary Sol / High works directly
exceptional reviewer: agent_type: codex_orchestration_sol_reviewer; task_name: sol_high_review_<objective_slug>
~~~

For scores below 5.0, root spawns the Terra executive first. For a simple bounded tool
task, tell Terra to execute directly. Otherwise Terra starts the mapped Luna or Terra /
Medium producer and owns acceptance. For scores 5.0–7.9, root starts the mapped
producer directly. Never spawn a same-model implementation agent.

Every handoff must state: objective; exact files/systems it may inspect and modify;
interfaces and safety constraints; the minimum sufficient outcome; one decisive
verification; and the immutable score. Say that other agents or the user may edit
concurrently, so it must preserve unrelated work. Require a self-check and evidence in
the return. This compact contract supersedes normal loading of
`references/role-contracts.md`; read that file only while debugging or changing role
templates.

Trust the installed named role unless spawn reports a mismatch. If the selected role
is unavailable, retry it once unchanged, then move upward only until the owning
executive tier. The ladders are Luna Max → Terra Medium → Terra High executive and
Terra Medium → Terra High → Sol Low → Sol Medium → primary Sol High. At the executive
tier, work directly. Do not wait for unrelated tasks.

After a concrete role failure only, read `references/role-contracts.md`, run
`../../scripts/install-agents.sh --check`, and use
`../../scripts/inspect-agent-runtime.sh` only if model or effort remains unknown.

## Check once

The producer self-checks. The owning executive performs one proportionate acceptance
check. If a material defect exists, give the same producer one precise correction and
one new self-check. If acceptance still fails, retire that producer for this task and
have the executive finish directly. Do not start a replacement, watcher, or automatic
review loop; use event-driven waiting.

Use a fresh Sol / High reviewer only when the user requests independent review or the
accepted work crosses a critical security, billing, authorization, destructive-data,
or irreversible-schema boundary. Require `ship`, `fix-first`, or `rethink`; any later
change invalidates the verdict.

## Receipt and completion

The receipt is a completion invariant, but it has no normal startup steps. After the
work and acceptance check, make this the final tool action:

~~~sh
python3 "$skill_dir/../../scripts/usage-receipt.py" finish
~~~

`finish` recovers the current root turn and every spawned descendant from Codex's
transcript, prices the observed model mix, and falls back from weekly percentages to
official-rate task credits when necessary. Never draft the final answer before
`finish`, recalculate its output, or omit its three lines. Read
`references/usage-receipt.md` only to diagnose receipt behavior or maintain its code.

End with the observed route, immutable score, and the helper output verbatim.

## Maintenance

Keep maintenance off the user's critical path. Run the daily upstream audit only on an
activation with no task or after user work when it adds no delay. Classify actual
upstream changes as **adopt unchanged**, **adapt**, or **skip**; never merge
automatically.

Use `../../scripts/daily-upstream-audit.sh`. Compare with the fork's current files and
use **skip — redundant** when behavior is already present. The audit must not modify
code or merge upstream.

For effectiveness comparisons use `../../scripts/effectiveness-tracker.py` and only
authoritative `task_complete` turns; report exact completed-task tokens, elapsed time, delegation count,
and credit-weighted receipts. Do not infer a denominator from Profile chat count.

For self-updates, `jessejaffe/codex-orchestration` is writable and
`DannyMac180/sol-advisor` is read-only. Finish accepted work on fork `main`, never push
upstream, increment the plain release version, run `../../scripts/reinstall-plugin.sh`,
and tell the user that a new task is the reliable instruction-reload boundary.
Use the sibling manifest, not contents or version text from a compatibility alias, as
the release identity.
