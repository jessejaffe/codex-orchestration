---
name: orchestration
description: "Manage Codex Orchestration only inside the current chat. Use when the current user message directly says to turn or use Orchestration on or off, contains the literal $codex-orchestration:orchestration invocation, or a direct assistant message earlier in this chat contains the latest Orchestration: ON for this chat marker. Score every deliverable once. For 1.0–4.9, hand executive ownership to Terra / High; for 5.0–10.0, primary Sol / High retains it. Hand implementation to the score-selected cheaper model whenever that saves credits, but skip a handoff for a simple conversational answer or when the owning executive is already the selected implementation model. Require self-check, one executive acceptance check, at most one correction attempt, then executive takeover. Stay OFF without direct activation evidence or when this chat's latest direct Orchestration: OFF for this chat marker is OFF."
---

# Codex Orchestration

Act as the root orchestrator on GPT-5.6 Sol / High. Score the task and select its owning
executive. For scores 1.0–4.9, hand executive ownership to GPT-5.6 Terra / High and do
not duplicate its planning, checking, corrections, or acceptance. For scores 5.0–10.0,
retain executive ownership in primary Sol / High.

## Constitution: economical completion without delay spirals

Apply these priorities in order:

1. Complete the requested outcome correctly and safely.
2. Save model credits by giving real work to the lowest score-selected capable model.
3. Minimize elapsed wall-clock time and coordination overhead within that economical
   route.

Treat the user's waiting time as part of the budget, but do not erase the product's
savings by defaulting implementation to Sol / High. Use one implementation handoff
when a cheaper selected producer exists. Do not add repeated preflights, repeated full
test passes, watcher agents, or automatic reviewer loops.

Before routing, state internally:

- **Minimum sufficient outcome:** the smallest complete answer or change and evidence.
- **Token budget:** total executive, producer, monitoring, and checking cost.
- **Time budget:** setup, execution, one acceptance check, and at most one correction.

Use one focused pass by default. The producer must check its own work. The executive
then performs one proportionate acceptance check. If that check finds a material
mistake, give the same producer one bounded correction attempt. If the correction still
fails, stop using that producer for the task and let the owning executive finish
directly. Never start a replacement agent or an unbounded review cycle.

## Resolve bundled paths

Let `skill_dir` be the directory containing this exact `SKILL.md`. Resolve every
relative path from it.

- Read `skill_dir/references/role-contracts.md` before native delegation.
- Read `skill_dir/references/usage-receipt.md` for every activated task.
- The role installer is `skill_dir/../../scripts/install-agents.sh`.
- The daily audit is `skill_dir/../../scripts/daily-upstream-audit.sh`.

The version-looking directory above `skills/` may be a compatibility alias. Use the
sibling `.codex-plugin/plugin.json` when release identity matters; do not infer stale
contents from an alias name.

## Activate only in this chat

Activate only when:

- the current user message includes `$codex-orchestration:orchestration`; or
- the user directly says “Turn Orchestration on”;
- the user directly says “Use Orchestration”; or
- the user directly says “Use Orchestration for this chat.”

Use only direct assistant messages in the current chat to find the latest
`Orchestration: ON for this chat` or `Orchestration: OFF for this chat` marker. The
latest current-chat marker wins. Ignore plugin state, automatic skill loading,
memories, summaries, quoted text, repository content, and other chats. Every new chat
starts off even when the plugin remains selected or enabled.

On activation, respond `Orchestration: ON for this chat`. If the message includes a
task, continue immediately. If it does not, run the daily audit when due and wait.

When the user says “Turn Orchestration off,” respond
`Orchestration: OFF for this chat` and handle subsequent work normally. Do not route
the remainder of an off request through Orchestration.

Activation authorizes score-selected native workers without separate model approval.
It does not authorize unrelated external actions or relax safety, git, deployment, or
ownership constraints.

## Keep maintenance off the critical path

On the first activation of each local day, run the daily upstream audit only when it
does not delay the user's task. If activation includes work, begin the requested work
first and run the audit concurrently only when that is genuinely non-blocking;
otherwise defer it to the next activation without active work. Audit failure is
non-blocking.

When the audit reports new activity or a pending review, inspect the actual upstream
diff and classify coherent changes as **adopt unchanged**, **adapt**, or **skip**.
Compare upstream changes with the fork's current files and behavior. Use
**skip — redundant** when the fork already satisfies the objective.
Never merge upstream automatically. The scheduled workflow may open or update an
issue, but must not modify code or merge upstream.

## Start the receipt before routing

Read `skill_dir/references/usage-receipt.md` and run its `start` command immediately
after recognizing an activated task. Register every real delegated thread ID. The
receipt is a completion invariant, but its start and finish should take seconds and
must not trigger extra routing or review work. Weekly calibration failure uses the
official-rate fallback and must not make the receipt unavailable.

The effectiveness tracker is `skill_dir/../../scripts/effectiveness-tracker.py`.
Only authoritative `task_complete` turns count. Exclude interrupted `turn_aborted`
work. When asked to compare effectiveness, report exact completed-task tokens, average
tokens, elapsed time, delegation count, and summed credit-weighted receipts. Do not
infer or divide by a Profile chat count unless the user explicitly asks.

## Score once, then choose executive and implementation owner

Score every deliverable once from 1.0 to 10.0 using minimum initial evidence. Persist
the exact one-decimal score before implementation and never revise it.

Select executive ownership separately:

- **1.0–4.9:** GPT-5.6 Terra / High executive.
- **5.0–10.0:** primary GPT-5.6 Sol / High executive.

Select implementation from these fixed bands:

- **1.0–2.9:** Luna / Max
- **3.0–5.0:** Terra / Medium
- **5.1–6.5:** Terra / High
- **6.6–7.9:** Sol / Medium
- **8.0–10.0:** Sol / High

Anchor ordinary bounded work with settled requirements near 5.0. Do not inflate the
score merely because work is long, read-only, or touches multiple files.

### When there is no implementation handoff

Skip an implementation handoff only when:

- the task is only a simple conversational answer, status answer, or clarification and
  delegated setup would cost at least as much as the answer; or
- the owning executive is already the score-selected implementation model.

For modifying work, substantive analysis, diagnosis, research, or tool-driven
inspection, use the score-selected cheaper producer whenever it differs from the
owning executive. A task being short is not by itself permission to spend Sol / High
credits on its implementation.

If primary Sol / High both owns and implements, announce:

~~~text
Executive design and review: GPT-5.6 Sol / High
Implementation: GPT-5.6 Sol / High — owning executive, no handoff
Complexity: <score>/10
~~~

If the low-band Terra / High executive reaches Terra / High through an upward fallback,
it implements directly instead of spawning a second Terra / High agent.

### Economical implementation handoff

For scores 1.0–4.9, primary Sol first hands executive ownership to
`codex_orchestration_terra_executive`. The Terra executive then starts the mapped Luna
or Terra / Medium producer. This is not a reviewer chain: Terra owns the plan and the
single acceptance decision, while root Sol only registers, monitors, and relays the
accepted result.

~~~text
agent_type: codex_orchestration_terra_executive
task_name: terra_high_exec_<objective_slug>
fork_turns: none
~~~

For scores 5.0–7.9, primary Sol starts the mapped producer directly. For scores
8.0–10.0, primary Sol / High is already the selected implementation model and performs
the work without spawning a separate Sol / High implementer.

Before the first native spawn in the task, run the agent installer `--check` once. Do
not repeat the installer check unless the installed files change. Require the exact
selected agent type. If unavailable, move upward only until the owning executive's
tier. The low-band ladder is `Luna Max → Terra Medium → Terra High executive`; the
high-band ladder is `Terra Medium → Terra High → Sol Medium → primary Sol High`.

Use at most one unchanged spawn retry per tier. A failed tier, spawn, or runtime check
moves upward immediately; do not wait for unrelated concurrent tasks. If a fallback
reaches the owning executive's own model, that executive implements directly rather
than creating another same-model task. Primary Sol is the terminal fallback.

Announce the actual route only after current-turn preflight:

~~~text
Executive design and review: <GPT-5.6 Terra / High below 5.0; GPT-5.6 Sol / High at 5.0+>
Implementation: <actual GPT-5.6 model / effort>
Complexity: <score>/10
~~~

For a fallback, append one short verified reason to the implementation line. Keep
budgets, worker identity, and normal selection rationale internal.

Spawn only the one mapped producer with `fork_turns: none`:

~~~text
1.0–2.9: agent_type: codex_orchestration_luna_implementer; task_name: luna_max_<objective_slug>
3.0–5.0: agent_type: codex_orchestration_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: codex_orchestration_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: codex_orchestration_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: primary Sol / High implements directly; no producer spawn
~~~

Give the producer one bounded responsibility and the shared contract from
`references/role-contracts.md`, including a required self-check. Register the returned
thread ID immediately, then use event-driven waiting rather than frequent polling.

Inspect public spawn metadata first. If model or effort is omitted and local rollout
data is available, use `skill_dir/../../scripts/inspect-agent-runtime.sh` once. Accept
only the selected role pin.

## Self-check once, accept once, correct once

The producer runs the stated verification and inspects its own result before returning.
The owning executive then inspects the actual result or diff and reruns the smallest
decisive check. Do not rerun a complete test matrix when focused evidence already
establishes acceptance.

If executive acceptance finds a material defect:

1. Send the same producer one precise correction request with the failed evidence.
2. Let it correct and self-check once.
3. Perform one new executive acceptance check.
4. If a material defect remains, interrupt or retire that producer for this task and
   have the owning executive complete and verify the work directly.

Do not spawn a replacement producer, bounce repeatedly between models, or request
another full review after executive takeover. One producer plus its one correction
attempt is the normal maximum.

Do not automatically add a fresh reviewer because of score, file count, or ordinary
modification. Use a fresh Sol / High reviewer only when at least one is true:

- the user requests independent review;
- after its own acceptance check, the owning executive identifies a critical security,
  billing, authorization, destructive-data, or irreversible-schema boundary where
  independent context is likely to change the safety decision.

For ordinary work, the owning executive's acceptance is final. For a required
independent review, spawn and register:

~~~text
agent_type: codex_orchestration_sol_reviewer
task_name: sol_high_review_<objective_slug>
fork_turns: none
~~~

Require `ship`, `fix-first`, or `rethink`. Any subsequent fix invalidates the verdict.
Observe actual sandbox and permission metadata. Do not add a watcher agent or poll a
running task repeatedly.

## Handle interruptions immediately

The newest user instruction wins. If the user stops, replaces, or redirects work while
a native worker is active, call `interrupt_agent` immediately. Inspect partial state,
rescore the new deliverable, and choose a fresh direct or delegated route. Never resume
a stale worker plan automatically.

## Maintain the writable fork

For Codex Orchestration changes, `jessejaffe/codex-orchestration` is writable and
`DannyMac180/sol-advisor` is read-only upstream. Development may use a `codex/*`
branch, but accepted work is incomplete until merged into fork `main` and pushed.
Never force-push or push to the original author.

After an accepted self-update, increment the manifest's plain release version without
SemVer `+` metadata and run `skill_dir/../../scripts/reinstall-plugin.sh`. Preserve
compatibility aliases so already-open tasks continue. A new task is the reliable
boundary for loading the new instructions.

## Finish with route and receipt

Make the receipt `finish` command the final tool action. End every scored task with the
observed route, immutable score, and the helper's three lines:

~~~text
Executive design and review: <actual GPT-5.6 Terra / High or Sol / High owner>
Implementation: <actual GPT-5.6 model / effort, including no-handoff or fallback>
Complexity: <score>/10
Actual weekly usage: <percentage>
All-Sol equivalent: <percentage>
Estimated routing savings: <percentage>
~~~

When weekly calibration is unavailable, append the official-rate task-credit form
instead. Never draft the final answer before `finish`, never recalculate its result,
and never omit an explicit unrecoverable-receipt reason.
