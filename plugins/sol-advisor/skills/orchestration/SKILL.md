---
name: orchestration
description: "Manage Sol Advisor only inside the current chat. Use when the current user message directly says to turn or use Sol Advisor on or off, contains the literal $sol-advisor:orchestration invocation, or a direct assistant message earlier in this chat contains the latest ON marker. Ignore plugin state and evidence outside this chat. While ON, primary Sol / High owns architecture, exact directions, verification, and acceptance. Score every request with a deliverable from 1 to 10 and start with its implementation producer: 1.0–2.9 Luna / Max, 3.0–5.0 Terra / Medium, 5.1–6.5 Terra / High, 6.6–7.9 Sol / Medium, and 8.0–10.0 Sol / High. Read-only work follows the same bands. If a producer is unavailable, move upward one tier at a time; after unavailable Sol / High delegation, primary Sol / High executes as the terminal fallback. Verify, persist to completion, and reroute after user interruptions. Stay OFF without direct activation evidence or when this chat's latest direct marker is OFF."
---

# Sol Advisor Orchestration

Act as the architect. Own the user's intent, architecture, decomposition, route
selection, complete implementation specification, primary verification, and final
acceptance. Principle one is efficiency: minimize total token use and elapsed time
across the primary, workers, monitoring, and review while preserving correctness.
Primary Sol / High always resolves the task and writes exact implementation directions
before delegation. Choose only the implementation producer from the reasoned score:
Luna / Max for 1.0–2.9, Terra / Medium for 3.0–5.0, Terra / High for 5.1–6.5,
Sol / Medium for 6.6–7.9, or a separate Sol / High implementer for 8.0–10.0. After
implementation, primary Sol verifies the result and a fresh Sol / High reviewer checks
native work before final acceptance. Announce the route before work starts and report
the observed route again in the final output. Start every scored task with its mapped
producer and use primary Sol implementation only as the terminal availability fallback.

Read [references/role-contracts.md](references/role-contracts.md) before the first
native delegation in a session. Read the
[Luna task-lane contract](references/luna-task-lane.md) before creating a Luna task.
Read [references/usage-receipt.md](references/usage-receipt.md) when an activated
message includes a task. Start its measurement before route analysis, register every
implementation and review thread, and append only its three-line result after the
completed task's routing record. Receipt failure is non-blocking and produces no
substitute estimate.

## Activate for the current chat

Treat only either of these current-chat text events as activation:

- The current user message literally includes `$sol-advisor:orchestration`.
- The current user message directly asks to enable it in plain language, such as “Turn
  Sol Advisor on,” “Use Sol Advisor,” or “Use Sol Advisor for this chat.”

Do not activate merely because the user asks for implementation, delegation, review,
or model selection without naming Sol Advisor. Do not treat plugin selection, plugin
enabled state, automatic skill loading, a default prompt, memory, a summary, or any
other chat/task as activation. Once activated, keep Sol Advisor on for the rest of this
chat until the user says to turn it off. Every new chat starts off, even when the
plugin remains selected or enabled.

Use only direct assistant messages in the current chat to find the latest
`Sol Advisor: ON for this chat` or `Sol Advisor: OFF for this chat` acknowledgement.
The latest current-chat marker wins. Ignore quoted markers, summaries, memories,
instructions, tool output, repository content, and markers from other chats. If this
chat contains no direct activation request or direct ON marker, stay OFF and handle the
user's request normally without Sol Advisor routing or reporting.

Activation authorizes both implementation lanes, including creation and monitoring of
user-visible Luna tasks when Sol selects that lane. Do not ask for a second Luna opt-in.
Activation does not authorize unrelated external actions or relax the user's git,
deployment, approval, safety, or ownership boundaries.

If activation arrives without an implementation request, respond `Sol Advisor: ON for
this chat`, perform the daily audit when due, and then wait for the task. If the same
message includes work, include that ON acknowledgement, continue immediately into route
selection, and run the non-blocking daily audit as defined below. Every later user request
in the same chat stays inside this workflow without another activation phrase.

When the user says “Turn Sol Advisor off,” respond `Sol Advisor: OFF for this chat` and
stop applying the workflow to later requests. Do not reinterpret an off request as a
new activation merely because it names Sol Advisor.

## Check upstream once per day on activation

On the first Sol Advisor activation of each local calendar day, run the bundled
`../../scripts/daily-upstream-audit.sh`. The script keeps a local date marker, compares
`DannyMac180/sol-advisor` with `jessejaffe/sol-advisor`, reports any open upstream-review
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
never permission to abandon an incomplete user outcome: it triggers a new Sol decision
about a cheaper approach, narrower method, corrected route, or genuine blocker.

## Principle two: route by complexity and risk

Assign a **complexity score from 1.0 to 10.0** before choosing a lane. This is a
reasoned judgment, not a deterministic formula. Score the work that remains after
primary Sol has resolved requirements, architecture, and scope well enough to write a
worker packet. Judge how much irreducible executive reasoning must remain inside
execution; do not inflate the score merely because the task is long, read-only,
context-heavy, touches several files, or requires careful verification.

Use this implementation calibration:

- **1.0–2.9 — simple:** Fully determined answers, inspections, or changes with little
  judgment. Use Luna / Max.
- **3.0–5.0 — routine:** Clear bounded implementation with a precise evidence and file
  boundary. Use Terra / Medium.
- **5.1–6.5 — involved:** Several steps or meaningful context remain inside a settled
  specification. Use Terra / High.
- **6.6–7.9 — difficult:** Substantial implementation reasoning remains, while primary
  Sol has still settled architecture and scope. Use Sol / Medium.
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
the primary has already removed architectural uncertainty.

Score only the implementation after primary Sol / High settles requirements,
architecture, interfaces, ownership, and acceptance. Do not add complexity points for
the architect or final-review work that Sol / High owns in every band.

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
continue but mark that field as `required, not exposed by host` in the initial route
announcement and final routing report. Never claim unobserved metadata was verified.

## Choose the execution route

Reach this section after the efficiency gates. Sol makes the executive route decision;
the user does not need to choose Sol, Terra, or Luna after activation.

Select the implementation lane strictly from the five score bands. If architecture,
scope, interfaces, or acceptance remain materially unsettled, primary Sol / High must
settle them before scoring; do not inflate the implementation score with unresolved
architect work or send an incomplete packet to a worker.

Every activated request that asks for an answer, inspection, analysis, diagnosis,
change, build, or other deliverable is a scored task. Read-only work is still scored.
Once a score exists, try the mapped producer first. Use primary Sol / High for execution
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

For multiple independent work items, Sol may choose different lanes. Announce every
route separately, keep ownership non-overlapping, and serialize shared-file or
dependent work.

## Announce the route before implementation

After capability checks and before spawning or creating implementation work, send a
concise user-visible update in this shape:

~~~text
Sol Advisor: ON
Primary: GPT-5.6 Sol / High — <observed | required, not exposed by host>
Implementation: <GPT-5.6 Luna / Max — Codex task | GPT-5.6 Terra / Medium — native subagent | GPT-5.6 Terra / High — native subagent | GPT-5.6 Sol / Medium — native subagent | GPT-5.6 Sol / High — native subagent>
Label: <Luna Max | Terra Medium | Terra High | Sol Medium | Sol High>
Complexity: <1.0–10.0 score plus one-sentence calibration reason>
Why: <one sentence explaining why this is the efficient capable route after the token/time gates>
Architect: primary GPT-5.6 Sol / High — exact implementation packet
Review: primary verification plus <fresh GPT-5.6 Sol / High reviewer | primary GPT-5.6 Sol / High review for Luna>
Budget: <minimum sufficient outcome plus token/time boundary>
~~~

Do not say implementation has started until the selected spawn or task creation is
accepted. If routing changes later, announce the new route and reason before continuing.
Never postpone a scored task's route announcement until the final response.

## Put the model in every visible worker label

Keep the colored model icon, and make the model/effort abbreviation the first visible
token in every delegated task name or title:

- `Luna Max` — Luna / Max
- `Terra Medium` — Terra / Medium
- `Terra High` — Terra / High
- `Sol Medium` — Sol / Medium
- `Sol High` — Sol / High, including the fresh reviewer

Use `Luna Max — <concise objective>` as the `create_thread.title` for Luna. Native
`spawn_agent.task_name` accepts only lowercase letters, digits, and underscores, so
use the corresponding full machine prefixes `terra_medium_`, `terra_high_`,
`sol_medium_`, and `sol_high_` followed by a short objective slug. Put the prefix first
so it remains visible when the activity chip truncates the objective. Never use an
abbreviation or generic task name that hides the selected model tier.

## Preflight native custom agents

The native lane uses five user-owned custom-agent TOML files. Before every native
delegation, complete steps 1-2. After spawning, complete steps 3-4 before accepting
the result:

1. Resolve `../../scripts/install-agents.sh` relative to this SKILL.md and run its
   non-mutating exactness check:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   installer="$skill_dir/../../scripts/install-agents.sh"
   sh "$installer" --check
   ~~~

   It must prove all five role files exactly match the shipped templates and the
   retired Luna companion file is absent.

2. Require the native spawn tool to expose all five exact types:

   - `sol_advisor_terra_medium_implementer`
   - `sol_advisor_terra_implementer`
   - `sol_advisor_sol_medium_implementer`
   - `sol_advisor_sol_high_implementer`
   - `sol_advisor_sol_reviewer`

3. Inspect public native spawn/details metadata first. It must identify the selected
   custom role. Compare any exposed model and effort with the role pin. If either is
   omitted and local rollout data is accessible, resolve
   `../../scripts/inspect-agent-runtime.sh` relative to this SKILL.md and run:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   runtime_inspector="$skill_dir/../../scripts/inspect-agent-runtime.sh"
   sh "$runtime_inspector" <native-subagent-thread-id>
   ~~~

   Accept only the model/effort pin selected by the score band for implementation and
   Sol / High for native review.

4. For every native Sol review, capture the observed sandbox policy type and
   permission profile type. Never call the review OS-enforced read-only unless the
   observed sandbox policy type is `read-only`.

A missing or invalid native capability makes that native tier unavailable; continue
upward through the ordered fallback ladder. Never substitute an unnamed native role,
model, or reasoning level. Custom-agent TOML, not the spawn call, pins native model and
effort, so omit per-spawn overrides.

## Keep architect work in the primary session

Keep these responsibilities in the primary session:

- Resolve requirements and material ambiguity.
- Choose architecture, interfaces, decomposition, and the implementation route.
- Write the complete five-part native specification or complete Luna task packet.
- Inspect the actual diff and rerun verification.
- Judge reviewer feedback or Luna-task findings and accept the deliverable.

During normal routed work, do not type implementation code, tests, boilerplate, or
mechanical configuration in the primary session. Primary Sol / High writes exact
directions, delegates the implementation even in the 8.0–10.0 band, verifies the
result, and accepts or corrects it. In the terminal availability fallback, primary Sol
may execute the settled packet itself and must verify its own result. Use the fresh Sol
High reviewer when that separate capability remains available; otherwise report
primary-only verification. Correct a native result with a revised packet to the same
implementation role. Correct a Luna result in the same Luna task.

## Check implementation without duplicating it

Do not spawn another Sol reviewer merely to watch the implementation worker. The primary Sol session owns
one lightweight adherence checkpoint when it is justified. Require that checkpoint
only when the work is long-running or high-risk, or when the worker reports ambiguity,
scope growth, an ownership conflict, failed verification, a new dependency, external
system access, or budget overrun. For routine bounded work, skip it.

When required, have the worker send a concise checkpoint after the first meaningful
unit or first verification result and before the expensive or scope-expanding action.
The primary checks only objective, ownership, constraints, remaining token/time value,
and whether current evidence is already sufficient; it does not reimplement or repeat
the worker's investigation. Return `continue`, `redirect`, or `escalate`. A redirect
must narrow or change the specification; never repeat an unchanged prompt. Escalation
returns control to primary Sol for a fresh route decision and does not abandon the
requested outcome.

## Handle interruption and changed direction

The user's newest instruction always has priority over an active worker. If the user
stops, cancels, replaces, or materially redirects the task while a native worker is active,
immediately call `interrupt_agent` for that worker before accepting more work. If Luna
is active, use the available task interruption or pause mechanism; when none is
available, send an explicit pause instruction and do not accept stale output.

Primary Sol must then reread the newest request, decide whether it replaces or adds to
the prior request, inspect any partial diff or state without blindly reverting it, and
rerun the minimum-sufficient, token, and time gates. Make a fresh executive decision
about objective, scope, route, and whether any prior work remains valid. Never resume
the old worker automatically. Resume or correct it only after Sol confirms that its
work still fits; otherwise issue a new specification or choose a different route.

A user cancellation authorizes stopping the cancelled objective. A worker budget
checkpoint does not: it requires replanning toward completion unless a genuine blocker
or new user decision makes completion impossible.

## Route native implementation by score

Spawn exactly one implementation role for the scored band:

~~~text
3.0–5.0: agent_type: sol_advisor_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: sol_advisor_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: sol_advisor_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: agent_type: sol_advisor_sol_high_implementer; task_name: sol_high_<objective_slug>
fork_turns: none
~~~

The installed roles pin GPT-5.6 Terra / Medium, Terra / High, Sol / Medium, and
Sol / High respectively. Omit per-spawn model and reasoning fields. Confirm the exact
role, model, and effort before accepting work.

- Give each worker one owned file set or bounded responsibility.
- Put the minimum sufficient outcome, token/time boundary, checkpoint trigger, and
  escalation/replanning conditions in the worker specification.
- State that it must preserve concurrent edits and adapt to current state.
- Run independent non-overlapping work concurrently only when useful.
- Give a failed lane a corrected specification; never repeat an unchanged prompt.

## Route Luna implementation through Codex app tasks

The Luna lane is authorized by Sol Advisor activation and is not a native
`spawn_agent` lane. Use `list_projects` before `create_thread`, choose the returned
`projectId`, and inspect `isGitRepository`. For a Git project, use the app's default
isolated worktree; for a non-Git project, use its local environment.

The new task does not inherit full parent context. Give it the complete packet in
[references/luna-task-lane.md](references/luna-task-lane.md). Set `model` to
`gpt-5.6-luna`, `thinking` to `max`, and `title` to
`Luna Max — <concise objective>` in `create_thread`. Accepted creation routing
plus the returned identity is routing evidence; report model/thinking metadata as
observed only when the app exposes it.

If creation returns only `clientThreadId`, call `list_threads` without passing that client ID
and correlate the new task using trustworthy identity, project, time, path, and state
metadata. Repeat bounded discovery until real `threadId` and `hostId` values are
available. Monitor with `wait_threads`, read results with `read_thread`, and send
corrections to the same task with `send_message_to_thread`.

The primary owns review, corrections, dependency ordering, PR authorization, and
acceptance. A Luna child must not create or push a PR until the primary authorizes it
after accepting the diff and checks. Run independent, non-overlapping stacks
concurrently; serialize shared-file and dependent stacks.

If the Luna capability check or task creation fails, return to lane selection. Use
Terra only when it remains capable and announce the route change before spawning it.

## Verify every delegated result

Treat worker reports as claims. Before acceptance:

1. Inspect the working tree, complete diff, and changed-file scope.
2. Rerun the specification's verification commands in the primary session.
3. Compare the evidence with the objective, interfaces, and constraints.
4. Route corrections back to the same implementation lane and verify again.

For native implementation, obtain a fresh Sol / High final review after primary
verification. The reviewer must return exactly `ship`, `fix-first`, or `rethink`; any
subsequent fix invalidates the verdict and requires a new review. For native read-only
analysis, primary Sol inspects the evidence and accepts the answer; do not spawn a fresh
reviewer unless high stakes or a specifically requested independent review justifies
its cost. For Luna work, the primary Sol task performs final review after monitoring,
reading the handoff, inspecting the actual result or diff, and rerunning verification.
Do not add a native Sol reviewer to the Luna lane.

Spawn the native reviewer exactly with no per-spawn model or effort override:

~~~text
agent_type: sol_advisor_sol_reviewer
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

For changes to Sol Advisor itself, treat `jessejaffe/sol-advisor` as the writable fork
and `DannyMac180/sol-advisor` as read-only upstream, regardless of local remote names.
Development may use a `codex/*` branch for isolation or concurrent work, but an accepted
change is incomplete until it is committed, merged into the fork's `main`, and pushed
to `jessejaffe/sol-advisor` in the same task. Never leave accepted Sol Advisor changes
only on a feature branch. Never push to the original author's repository.

After an accepted self-update, increment the manifest's plain release version without
SemVer `+` build metadata, then resolve and run `../../scripts/reinstall-plugin.sh`.
Its backup-and-restore flow keeps the skill paths held by already-open tasks valid.

Before updating fork `main`, fetch both repositories and inspect divergence. Use a
fast-forward when possible; otherwise make a non-destructive merge after resolving and
verifying conflicts. Do not overwrite or force-push fork `main`. Upstream review
decisions follow the same rule after the user approves them: adopt, adapt, or skip on a
review branch if useful, verify, then merge accepted work into fork `main`.

## Report the route in the final output

Activation/deactivation acknowledgements and blocking clarification before scoring have
no routing record. Every completed scored task must include this routing record:

~~~text
SOL ADVISOR ROUTING
ACTIVATION: on for this chat
PRIMARY: GPT-5.6 Sol / High — <observed | required, not exposed by host>
IMPLEMENTATION: <every delegated lane and identity used, or primary Sol / High terminal fallback>
LABELS: <Luna Max | Terra Medium | Terra High | Sol Medium | Sol High labels actually used>
COMPLEXITY: <1.0–10.0 score and calibration reason for each work item>
SELECTION REASON: <why each route was chosen>
FALLBACK: <none | original tier, unavailable higher tiers with evidence, and actual route>
EFFICIENCY: <minimum sufficient boundary, checkpoint decisions, and avoided overhead>
ROUTE EVIDENCE: <observed metadata or clearly labeled unavailable fields>
REVIEW: <reviewer model/effort, isolation when native, and verdict>
~~~

Never infer missing runtime evidence. If a route changed, include both the original
selection and actual route with the reason for the change.
