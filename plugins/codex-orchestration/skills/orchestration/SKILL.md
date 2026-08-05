---
name: orchestration
description: "Manage Codex Orchestration only inside the current chat. Use when the current user message directly says to turn or use Orchestration on or off, contains the literal $codex-orchestration:orchestration invocation, or a direct assistant message earlier in this chat contains the latest Orchestration: ON for this chat marker. Ignore plugin state and evidence outside this chat. Score every deliverable once from 1.0 to 10.0. For 1.0–4.9, hand executive ownership to GPT-5.6 Terra / High; for 5.0–10.0, primary Sol / High retains executive ownership. Keep producer bands unchanged: 1.0–2.9 Luna / Max, 3.0–5.0 Terra / Medium, 5.1–6.5 Terra / High, 6.6–7.9 Sol / Medium, and 8.0–10.0 Sol / High. Verify, persist to completion, and reroute after user interruptions. Stay OFF without direct activation evidence or when this chat's latest direct Orchestration: OFF for this chat marker is OFF."
---

# Codex Orchestration

Act as the root orchestrator. For scores 5.0–10.0, own the user's intent, architecture,
decomposition, complete implementation specification, primary verification, and final
acceptance. For scores 1.0–4.9, do only minimum-sufficient activation, initial evidence
needed to score, immutable score persistence and announcement, Terra-executive
preflight, complete request/evidence handoff, registration/monitoring, and relay of its
accepted result. Do not duplicate the Terra executive's architecture, specification,
verification, corrections, or acceptance. Principle one is efficiency: minimize total token use and elapsed time
across the primary, workers, monitoring, and review while preserving correctness.
Choose the executive and implementation producer from the immutable reasoned score.
Scores 1.0–4.9 use the dedicated GPT-5.6 Terra / High executive; scores 5.0–10.0
retain primary Sol / High executive ownership. Choose the implementation producer:
Luna / Max for 1.0–2.9, Terra / Medium for 3.0–5.0, Terra / High for 5.1–6.5,
Sol / Medium for 6.6–7.9, or a separate Sol / High implementer for 8.0–10.0. After
implementation, the owning executive verifies and accepts the result. High-band
modifying work retains a fresh Sol / High reviewer; the low-band Terra executive
performs final review itself. Announce the route before work starts and report
the observed route again in the final output. For scores 1.0–4.9, start with the
dedicated Terra / High executive, which then starts the mapped producer. For scores
5.0–10.0, start the mapped producer under the primary Sol / High executive. Use primary
Sol implementation only as the terminal availability fallback.

Let `skill_dir` be the directory that contains this exact `SKILL.md`. Resolve every
relative file from `skill_dir`, never from its parent `skills/` directory. The role
contract is exactly `skill_dir/references/role-contracts.md`; do not drop the
`orchestration/` path segment or report the contract absent without checking that exact
path. Read it before the first native delegation in a session. The receipt contract is
exactly `skill_dir/references/usage-receipt.md`; read it when an activated message
includes a task. Start its measurement before route analysis, register every spawned
implementation or review thread, and append only its three-line result after the
completed task's model lines. This lifecycle is a completion invariant: never compose
or send the final answer without first running the receipt's `finish` command. The
plugin's PreToolUse gate independently requires and persists the exact one-decimal
complexity score before routed work can start. That saved turn score is immutable even
if the implementation lane later falls back. The Stop hook reconstructs root and
delegated usage when the receipt lifecycle was skipped, and keeps the turn open until
the saved numeric complexity and receipt are visible. Weekly calibration failure uses
the official-rate task-credit fallback and must not make the receipt unavailable. A
deeper measurement failure remains non-blocking, but it must be reported explicitly
rather than silently dropping the receipt.

The effectiveness tracker is exactly
`skill_dir/../../scripts/effectiveness-tracker.py`. The Stop hook records each
successfully completed routed turn once in persistent state outside the replaceable
plugin cache, including exact root-and-delegated token usage. Only a Codex
`task_complete` terminal event qualifies for completed-task metrics. A user
interruption or redirect produces `turn_aborted` and must be excluded, even if a
provisional completion candidate was written during a timing race. When the user asks to
start an effectiveness experiment, run `baseline`; when they ask for the later
comparison, run `compare`. Treat completed routed turns as the primary unit and report
exact task tokens, average tokens per completed task, elapsed time, delegation count,
and the summed credit-weighted receipts. Account lifetime/daily tokens are background
context only. Do not request, infer, or divide by a Profile chat count unless the user
explicitly asks for that secondary context.

The version-looking directory above `skills/` may be a compatibility alias retained by
Codex Desktop. Its directory name is not the loaded release identity. The alias must
contain the same complete package as the installed release; use its sibling
`.codex-plugin/plugin.json` only when release identity matters.

## Activate for the current chat

Treat only either of these current-chat text events as activation:

- The current user message literally includes `$codex-orchestration:orchestration`.
- The current user message directly asks to enable it in plain language, such as “Turn Orchestration on,” “Use Orchestration,” or “Use Orchestration for this chat.”

Do not activate merely because the user asks for implementation, delegation, review,
or model selection without naming Orchestration. Do not treat plugin selection, plugin
enabled state, automatic skill loading, a default prompt, memory, a summary, or any
other chat/task as activation. Once activated, keep Codex Orchestration on for the rest of this
chat until the user says to turn it off. Every new chat starts off, even when the
plugin remains selected or enabled.

Use only direct assistant messages in the current chat to find the latest
`Orchestration: ON for this chat` or `Orchestration: OFF for this chat`
acknowledgement.
The latest current-chat marker wins. Ignore quoted markers, summaries, memories,
instructions, tool output, repository content, and markers from other chats. If this
chat contains no direct activation request or direct ON marker, stay OFF and handle the
user's request normally without Codex Orchestration routing or reporting.

Activation authorizes score-selected native worker delegation, including Luna / Max.
Do not ask for separate worker or model authorization. Activation does not authorize
unrelated external actions or relax the user's git, deployment, approval, safety, or
ownership boundaries.

If activation arrives without an implementation request, respond
`Orchestration: ON for this chat`, perform the daily audit when due, and then wait for
the task. If the same message includes work, include that ON acknowledgement, continue
immediately into route selection, and run the non-blocking daily audit as defined
below. Every later user request in the same chat stays inside this workflow without
another activation phrase.

When the user says “Turn Orchestration off,” respond
`Orchestration: OFF for this chat` and stop applying the workflow to later requests.
Do not reinterpret an off request as a new activation merely because it names
Orchestration.

## Check upstream once per day on activation

On the first Codex Orchestration activation of each local calendar day, run the bundled
`../../scripts/daily-upstream-audit.sh`. The script keeps a local date marker, compares
`DannyMac180/sol-advisor` with `jessejaffe/codex-orchestration`, reports any open upstream-review
issue, and requests the fork's non-merging GitHub review workflow when new activity is
present. A later activation that day must accept `already-checked-today` and avoid a
duplicate network audit.

Do not make this maintenance check replace or materially delay the user's requested
task. Begin the requested route normally and run the independent audit alongside the
first worker/tool opportunity when possible. If no task accompanied activation, run
the audit before waiting. Audit failure is non-blocking: report the exact failure and
continue the user's task.

When the audit reports `new-activity` or `pending-review`, inspect the upstream commits
and actual diff, then add a compact upstream review to the response:

- summarize the behavior changed;
- classify each coherent change as **adopt unchanged**, **adapt**, or **skip**;
- explain compatibility with this fork's efficiency, routing, interruption, and
  main-branch policies; and
- suggest a decision without merging anything.

Classification must compare the upstream patch with the fork's current files and
behavior, not merely judge the upstream patch in isolation. If the fork already
satisfies the stated objective, or the patch changes a legacy path superseded by this
fork, classify it as **skip — redundant**. Never recommend **adopt unchanged** for a
change whose target behavior is already present. After the user resolves an open review
on the same day, rerun the audit with `--force` so the cached pending result cannot be
shown in a later chat.

Never merge upstream changes merely because the scheduled or activation audit found
them. Wait for the user's decision. The scheduled GitHub workflow may only open or
update an issue; it must not modify code or merge upstream.

## Principle one: minimum sufficient work

Optimize total cost, not merely primary-Sol tokens. Count the task packet, worker
context, monitoring, retries, tool calls, and final review when comparing routes.
Terra exists to execute routine, bounded analysis and settled implementation more
cheaply than Sol. Read-only work is low mutation risk and is usually a strong Terra
candidate; read-only status alone is not a reason to keep work with Sol. Complexity,
material ambiguity, and executive judgment are reasons to keep work with Sol.

Before any preflight, worker creation, task creation, external-system access, or scope
expansion, perform all three gates:

1. **Minimum sufficient outcome.** State the smallest answer, change, and evidence that
   fully satisfy the user's exact request. Do not add downstream consequences,
   production data, database access, broad searches, robustness matrices, or adjacent
   deliverables unless they are required for that outcome or explicitly requested.
2. **Token budget checkpoint.** Estimate total tokens for the score-selected route,
   including its task packet, context, monitoring, and review. Use the estimate to set
   a focused scope and checkpoint, not to override the numeric lane mapping. If the
   selected lane is unavailable, return to route selection and announce the capable
   fallback rather than silently substituting it.
3. **Time budget checkpoint.** Include setup, preflight, task-packet construction,
   monitoring, retries, verification, and review. Use the estimate to set a focused
   checkpoint; time overhead never skips the score-selected producer.

Make each budget concrete. Use a user-supplied numeric limit when present. Otherwise
state an operational cap such as one focused inspection pass, one worker, an exact
variant or retry limit, and a named checkpoint before additional work. “Be efficient”
without an escalation or replanning boundary is not a budget. A budget checkpoint is
never permission to abandon an incomplete user outcome: it triggers a new owning-executive
decision about a cheaper approach, narrower method, corrected route, or genuine blocker.

## Principle two: route by complexity and risk

Assign a **complexity score from 1.0 to 10.0** from minimum initial evidence before
choosing a lane. This is a reasoned judgment, not a deterministic formula. Below 5.0,
do not resolve requirements or architecture before handoff; score the observed task so
the Terra executive owns that reasoning. At 5.0+, primary Sol owns it. In either band,
do not inflate the score merely because the task is long, read-only,
context-heavy, touches several files, or requires careful verification.

Use this implementation calibration:

- **1.0–2.9 — simple:** Fully determined answers, inspections, or changes with little
  judgment. Use Luna / Max.
- **3.0–5.0 — routine:** Clear bounded implementation with a precise evidence and file
  boundary. Use Terra / Medium.
- **5.1–6.5 — involved:** Several steps or meaningful context remain inside a settled
  specification. Use Terra / High.
- **6.6–7.9 — difficult:** Substantial implementation reasoning remains after the
  owning executive settles architecture and scope. Use Sol / Medium.
- **8.0–10.0 — hardest implementation:** Deep implementation reasoning, difficult
  tradeoffs, or high consequence remain inside the settled packet. Use a separate
  Sol / High implementer.

Use these exact implementation bands: **1.0–2.9 Luna / Max; 3.0–5.0 Terra / Medium;
5.1–6.5 Terra / High; 6.6–7.9 Sol / Medium; 8.0–10.0 Sol / High.** Token/time gates
shape scope and checkpoints but do not override the score-selected implementation
lane; only an unavailable or incapable lane triggers a clearly announced fallback.

Anchor an ordinary bounded task with settled requirements at **5.0**, not near the top
of the scale. A typical bounded bug investigation or settled multi-file change belongs
in Terra / Medium or Terra / High unless substantial implementation judgment remains.
Reserve the Sol implementation bands for genuinely difficult residual reasoning after
the owning executive removes architectural uncertainty.

Score the complete request once after only the initial evidence needed for a reasoned
route decision. Persist that one-decimal score before routed work and never revise it.
Do not create a second score inside the Terra executive or infer complexity from task
titles.

Map the score to the qualitative classes:

- **Luna / Max (1.0–2.9):** Fully determined implementation with little judgment.
- **Terra / Medium (3.0–5.0):** Routine bounded implementation.
- **Terra / High (5.1–6.5):** Involved implementation within a settled design.
- **Sol / Medium (6.6–7.9):** Difficult implementation with architecture already fixed.
- **Sol / High (8.0–10.0):** The hardest implementation packet, separate from the
  primary Sol / High architect and the fresh Sol / High reviewer.

Repeat the three gates after the first material evidence, before any new external
access or scope expansion, and when actual cost is materially exceeding the initial
expectation. Ask: “Does current evidence already satisfy the request?”, “What exact
uncertainty remains?”, and “Will the next action likely change the answer enough to
justify its tokens and time?” When the request is fully satisfied, stop adding work and
deliver it. When the next action has poor value but the outcome is incomplete, replan
the method or route and continue toward completion; do not return an avoidable partial
result merely because an estimate was exceeded.

## Confirm the primary session

Run the primary Codex session on GPT-5.6 Sol with High reasoning. Inspect runtime
metadata when the host exposes it. If an observed model or effort differs, tell the
user to select Sol / High and stop before delegation. If the host omits either value,
continue without adding host-metadata diagnostics to user-visible routing lines. Never
claim unobserved metadata was verified.

## Choose the execution route

Reach this section after the efficiency gates. Root Sol makes the initial executive route decision;
the user does not need to choose Sol, Terra, or Luna after activation.

Select the producer strictly from the five score bands. Select the executive separately:
`1.0–4.9: codex_orchestration_terra_executive` and `5.0–10.0: primary Sol / High`. At exactly
5.0 the producer remains Terra / Medium while the executive is Sol / High.

Every activated request that asks for an answer, inspection, analysis, diagnosis,
change, build, or other deliverable is a scored task. Read-only work is still scored.
Once a low score exists, spawn the Terra executive first; it then tries the mapped
producer. Once a high score exists, primary Sol tries the mapped producer. Use primary Sol / High for execution
only after the selected producer and every higher delegated tier are unavailable. Only
activation or deactivation acknowledgements and a genuinely blocking clarification
before scoring have no implementation route.

Check the selected route's capabilities before announcing it. If a delegated lane is
unavailable or incapable, move upward without skipping an available tier:

`Luna Max → Terra Medium → Terra High → Sol Medium → Sol High implementer → primary Sol High`.

Begin this ladder at the score-selected tier; never move downward. Announce the original
selection, each failed capability, and the actual higher route before implementation.
Primary Sol High is the guaranteed terminal fallback and completes the work itself.
Availability fallback never permits a read-only, token, time, or convenience bypass.

Availability is a **per-tier, current-turn decision**. Before declaring the selected
or a fallback tier unavailable, check that exact role now and retain the concrete
failure from this turn. Never reuse a prior turn's failure, a “known preflight issue,”
or an earlier installation state as current evidence. A passing current check
invalidates every older failure of the same check. Missing or stale unrelated roles do
not block a healthy selected role; check the reviewer separately only when review is
required.

For multiple independent work items, Sol may choose different lanes. Announce every
route separately, keep ownership non-overlapping, and serialize shared-file or
dependent work.

## Announce the route before implementation

After current-turn capability checks identify the actual available route and before
spawning implementation work, send exactly these three user-visible lines. Format the
score to one decimal place, including a trailing `.0` for whole-number scores:

~~~text
Executive design and review: <GPT-5.6 Terra / High below 5.0; GPT-5.6 Sol / High at 5.0+>
Implementation: <actual available model / effort>
Complexity: <score>/10
~~~

Substitute exactly `Executive design and review: GPT-5.6 Terra / High` for scores
1.0–4.9 and exactly `Executive design and review: GPT-5.6 Sol / High` for scores
5.0–10.0.

The next implementation or worker tool call persists that exact score in plugin data.
If the complexity gate denies the call, repeat the complete three-line route with one
decimal place and retry. Once persisted, never revise the score during the turn; a
later availability fallback changes only the `Implementation:` line.

The score-selected model is an internal candidate until its current-turn preflight
passes. Never print that candidate as `Implementation:` and then perform its preflight.
If a producer route is a fallback, append one short verified reason to its line. If
the low-band Terra executive is unavailable, fall upward to root Sol / High and use
this stable syntax with a nonempty current-turn verified reason:

~~~text
Executive design and review: GPT-5.6 Sol / High — Terra executive fallback: <current-turn verified reason>
~~~

Do not say implementation has started until the selected spawn is accepted. If a spawn
or its runtime validation fails after the initial announcement, repeat only the
`Implementation:` line with the new actual model and the verified failure. Keep the
budgets, worker identity, and normal selection rationale internal. The numeric
complexity score itself is always visible. Never postpone a scored task's route
announcement until the final response.

## Put the model in every visible worker label

Keep the colored model icon, and make the model/effort abbreviation the first visible
token in every delegated task name or title:

- `Luna Max` — Luna / Max
- `Terra Medium` — Terra / Medium
- `Terra High` — Terra / High
- `Terra High Exec` — Terra / High executive
- `Sol Medium` — Sol / Medium
- `Sol High` — Sol / High, including the fresh reviewer

Native `spawn_agent.task_name` accepts only lowercase letters, digits, and underscores,
so use the corresponding full machine prefixes `luna_max_`, `terra_medium_`, `terra_high_`, `terra_high_exec_`,
`sol_medium_`, and `sol_high_` followed by a short objective slug. Put the prefix first
so it remains visible when the activity chip truncates the objective. Never use an
abbreviation or generic task name that hides the selected model tier.

## Preflight native custom agents

The native lane uses seven user-owned custom-agent TOML files. Before every native
delegation, complete steps 1-2. After spawning, complete steps 3-4 before accepting
the result:

1. Resolve `../../scripts/install-agents.sh` relative to this SKILL.md and run its
   non-mutating exactness check:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   installer="$skill_dir/../../scripts/install-agents.sh"
   sh "$installer" --check
   ~~~

   It must prove all seven role files exactly match the shipped templates.

2. Require the native spawn tool to expose the exact type for the tier being attempted.
   Do not require unrelated implementation types or the reviewer merely to start the
   selected worker. When moving upward, check the next tier's exact type at that time.
   Check `codex_orchestration_sol_reviewer` separately only before a review that requires it.

3. Inspect public native spawn/details metadata first. It must identify the selected
   custom role. Compare any exposed model and effort with the role pin. If either is
   omitted and local rollout data is accessible, resolve
   `../../scripts/inspect-agent-runtime.sh` relative to this SKILL.md and run:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   runtime_inspector="$skill_dir/../../scripts/inspect-agent-runtime.sh"
   sh "$runtime_inspector" <native-subagent-thread-id>
   ~~~

   Accept only the model/effort pin selected by the score band for implementation,
   Terra / High for the low-band executive, and Sol / High for native review.

4. For every native Sol review, capture the observed sandbox policy type and
   permission profile type. Never call the review OS-enforced read-only unless the
   observed sandbox policy type is `read-only`.

A missing or invalid selected native capability makes only that tier unavailable;
continue upward through the ordered fallback ladder. An unrelated role failure cannot
invalidate a healthy selected tier. Every failure must come from this turn's actual
file, tool-exposure, spawn, or runtime evidence; never carry a failure forward from a
prior turn. Never substitute an unnamed native role, model, or reasoning level.
Custom-agent TOML, not the spawn call, pins native model and effort, so omit per-spawn
overrides.

## Keep executive work in the selected executive

For scores 5.0–10.0, keep these responsibilities in the primary session. For scores
1.0–4.9, transfer all of them to `codex_orchestration_terra_executive`:

- Resolve requirements and material ambiguity.
- Choose architecture, interfaces, decomposition, and the implementation route.
- Write the complete native specification.
- Inspect the actual diff and rerun verification.
- Judge reviewer feedback and accept the deliverable.

For a low route, root Sol may only activate, inspect enough evidence to score, persist
and announce the score, preflight and spawn the Terra executive, hand off the complete
original request/constraints/evidence, root thread ID, resolved receipt-helper path,
exact score, executive line, actual producer line, producer mapping, and explicit root
receipt state; register and monitor the Terra executive itself; and relay its accepted
result. The Terra executive may spawn, register, and monitor its own descendants against
the root receipt while coordinating the mapped producer. Before its first nested producer/reviewer tool call,
it must emit the same exact three-line route in its own session so the child PreToolUse
gate persists the score. Immediately after every descendant spawn, it must run
`usage-receipt.py add-thread <descendant-id> --root-thread-id <root-thread-id>` before
monitoring or accepting work. Root Sol still registers the Terra executive itself.
It performs final review itself; do not add a Sol reviewer unless the user explicitly
requests independent Sol review or risk is escalated out of the low band.
The Terra executive's delegated Stop releases without a separate receipt or
effectiveness completion; root Stop is the sole completion record for the user task.

During normal routed work, do not type implementation code, tests, boilerplate, or
mechanical configuration in the root session. The owning executive writes exact
directions, delegates implementation, verifies, and accepts or corrects it. In the
terminal availability fallback, primary Sol
may execute the settled packet itself and must verify its own result. Use the fresh Sol
High reviewer when that separate capability remains available; otherwise report
primary-only verification. Correct a native result with a revised packet to the same
implementation role.

## Check implementation without duplicating it

Do not spawn another Sol reviewer merely to watch the implementation worker. The owning executive owns
one lightweight adherence checkpoint when it is justified. Require that checkpoint
only when the work is long-running or high-risk, or when the worker reports ambiguity,
scope growth, an ownership conflict, failed verification, a new dependency, external
system access, or budget overrun. For routine bounded work, skip it.

When required, have the worker send a concise checkpoint after the first meaningful
unit or first verification result and before the expensive or scope-expanding action.
The owning executive checks only objective, ownership, constraints, remaining token/time value,
and whether current evidence is already sufficient; it does not reimplement or repeat
the worker's investigation. Return `continue`, `redirect`, or `escalate`. A redirect
must narrow or change the specification; never repeat an unchanged prompt. Escalation
returns control to the owning executive for a fresh specification decision and does not
abandon the requested outcome.

If low-band work materially grows beyond 4.9, the Terra executive must pause further
implementation and escalate. Root Sol makes a fresh executive decision and replans,
but the persisted original score remains immutable. Report any observed transition
with the stable Terra-executive fallback syntax rather than rewriting the score.

## Handle interruption and changed direction

The user's newest instruction always has priority over an active worker. If the user
stops, cancels, replaces, or materially redirects the task while a native worker is active,
immediately call `interrupt_agent` for that worker before accepting more work.

Root Sol must then reread the newest request, decide whether it replaces or adds to
the prior request, inspect any partial diff or state without blindly reverting it, and
rerun the minimum-sufficient, token, and time gates, and select the owning executive
from a fresh score. Below 5.0, the new Terra executive decides objective, architecture,
scope, and whether prior work remains valid; at 5.0+, primary Sol decides them.
Never resume the old worker automatically or reuse stale worker plans without the
owning executive's fresh acceptance.

A user cancellation authorizes stopping the cancelled objective. A worker budget
checkpoint does not: it requires replanning toward completion unless a genuine blocker
or new user decision makes completion impossible.

## Route native implementation by score

For scores 1.0–4.9, root Sol first spawns exactly one executive:

~~~text
agent_type: codex_orchestration_terra_executive
task_name: terra_high_exec_<objective_slug>
fork_turns: none
~~~

Give it the original user request, current constraints, relevant prior evidence, root
thread ID, resolved receipt-helper path, immutable score, exact executive line, actual
producer line, mapped producer, and explicit root receipt state. It owns the producer spawn,
verification, corrections, review, and acceptance. For scores 5.0–10.0, primary Sol
continues directly with the producer mapping below.

Spawn exactly one implementation role for the scored band:

~~~text
1.0–2.9: agent_type: codex_orchestration_luna_implementer; task_name: luna_max_<objective_slug>
3.0–5.0: agent_type: codex_orchestration_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: codex_orchestration_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: codex_orchestration_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: agent_type: codex_orchestration_sol_high_implementer; task_name: sol_high_<objective_slug>
fork_turns: none
~~~

The installed roles pin GPT-5.6 Luna / Max, Terra / Medium, Terra / High, Sol / Medium,
and Sol / High respectively. Omit per-spawn model and reasoning fields. Confirm the
exact role, model, and effort before accepting work.

- Give each worker one owned file set or bounded responsibility.
- Put the minimum sufficient outcome, token/time boundary, checkpoint trigger, and
  escalation/replanning conditions in the worker specification.
- State that it must preserve concurrent edits and adapt to current state.
- Run independent non-overlapping work concurrently only when useful.
- Give a failed lane a corrected specification; never repeat an unchanged prompt.

## Verify every delegated result

Treat worker reports as claims. Before acceptance:

1. Inspect the working tree, complete diff, and changed-file scope.
2. Rerun the specification's verification commands in the owning executive session.
3. Compare the evidence with the objective, interfaces, and constraints.
4. Route corrections back to the same implementation lane and verify again.

For modifying native implementation at score 5.0 or above, obtain a fresh Sol / High
final review after primary verification. For 1.0–4.9, the Terra executive performs the
final review itself. The Sol reviewer must return exactly `ship`, `fix-first`, or `rethink`; any
subsequent fix invalidates the verdict and requires a new review. For native read-only
analysis, the owning executive inspects the evidence and accepts the answer; do not spawn a fresh
reviewer unless high stakes or a specifically requested independent review justifies
its cost.

Spawn the native reviewer exactly with no per-spawn model or effort override:

~~~text
agent_type: codex_orchestration_sol_reviewer
task_name: sol_high_review_<objective_slug>
fork_turns: none
~~~

Apply observed native reviewer isolation:

- With observed `read-only`, report enforced isolation.
- If the host broadens it, proceed only when hard isolation is not required, the
  prompt forbids edits, and exact before-and-after state proves no mutation. Report
  the broader sandbox and permission profile as residual risk.
- If isolation is unobservable, hard isolation is required, or mutation occurs, stop
  the native review.

## Keep the maintained fork on main

For changes to Codex Orchestration itself, treat `jessejaffe/codex-orchestration` as the writable fork
and `DannyMac180/sol-advisor` as read-only upstream, regardless of local remote names.
Development may use a `codex/*` branch for isolation or concurrent work, but an accepted
change is incomplete until it is committed, merged into the fork's `main`, and pushed
to `jessejaffe/codex-orchestration` in the same task. Never leave accepted Codex Orchestration changes
only on a feature branch. Never push to the original author's repository.

After an accepted self-update, increment the manifest's plain release version without
SemVer `+` build metadata, then resolve and run `../../scripts/reinstall-plugin.sh`.
Its backup-and-restore flow keeps the skill paths held by already-open tasks valid.
Codex Desktop may continue displaying an older compatibility-path name until the app
restarts even though that path contains the current release. Never infer stale contents
from the displayed directory name alone.

Before updating fork `main`, fetch both repositories and inspect divergence. Use a
fast-forward when possible; otherwise make a non-destructive merge after resolving and
verifying conflicts. Do not overwrite or force-push fork `main`. Upstream review
decisions follow the same rule after the user approves them: adopt, adapt, or skip on a
review branch if useful, verify, then merge accepted work into fork `main`.

## Report the route and receipt in the final output

Activation/deactivation acknowledgements and blocking clarification before scoring have
no model footer. End every completed scored task with the two model lines, the same
one-decimal complexity score persisted before work began, and then the successful
receipt output:

~~~text
Executive design and review: <GPT-5.6 Terra / High below 5.0; GPT-5.6 Sol / High at 5.0+, or stable low-band fallback line>
Implementation: <actual GPT-5.6 model / effort used, with verified fallback reason when applicable>
Complexity: <score>/10
Actual weekly usage: <percentage>
All-Sol equivalent: <percentage>
Estimated routing savings: <percentage>
~~~

If weekly calibration is unavailable, the successful receipt instead ends with:

~~~text
Estimated task credits: <credits>
All-Sol equivalent credits: <credits>
Estimated routing savings: <percentage>
~~~

Do not append a heading, activation state, labels, normal selection reason,
efficiency notes, route evidence, reviewer verdict, task IDs, or token totals. A
fallback line must include its compact current-turn reason. Append the receipt verbatim
when its helper succeeds. Never draft or send the final response before calling
`finish`; a task that merely prints model lines has not completed the Codex Orchestration
protocol. Never recalculate or replace the saved score at completion. Weekly
calibration failure is not a receipt failure: normal finish and transcript recovery
must emit the official-rate task-credit form. If direct measurement reports
`receipt-unavailable` for an unrecoverable transcript, task model, or official-pricing
failure, allow the Stop hook to recover the turn from its transcript. If both paths
are unavailable, include the hook's explicit `Savings receipt unavailable: <reason>`
line instead of silently omitting the receipt. Never claim an implementation model
that runtime evidence did not confirm.
