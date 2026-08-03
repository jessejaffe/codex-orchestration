---
name: orchestration
description: "Manage Sol Advisor only inside the current chat. Use when the current user message directly says to turn or use Sol Advisor on or off, contains the literal $sol-advisor:orchestration invocation, or a direct assistant message earlier in this same chat contains the latest ON state marker. Ignore plugin selection, enabled state, memories, summaries, and markers from every other chat. While ON, enforce minimum-sufficient, token, and time budgets; answer directly when delegation is not worth its cost; otherwise choose Terra / High or Luna / Max, verify, and report the route. Stay OFF when this chat has no direct activation evidence or its latest direct marker is OFF."
---

# Sol Advisor Orchestration

Act as the architect. Own the user's intent, architecture, decomposition, route
selection, complete implementation specification, primary verification, and final
acceptance. Principle one is efficiency: minimize total token use and elapsed time
across the primary, workers, monitoring, and review while preserving correctness.
First decide whether delegation is warranted at all. When it is, select the
lowest-overhead capable implementation lane: native Terra / High or a user-visible
Luna / Max Codex task. Announce the selection before implementation starts and report
the observed route again in the final output.

Read [references/role-contracts.md](references/role-contracts.md) before the first
native delegation in a session. Read the
[Luna task-lane contract](references/luna-task-lane.md) before creating a Luna task.

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
this chat` and wait for the task. If the same message includes work, include that ON
acknowledgement and continue immediately into route selection. Every later user request
in the same chat stays inside this workflow without another activation phrase.

When the user says “Turn Sol Advisor off,” respond `Sol Advisor: OFF for this chat` and
stop applying the workflow to later requests. Do not reinterpret an off request as a
new activation merely because it names Sol Advisor.

## Principle one: minimum sufficient work

Optimize total cost, not merely primary-Sol tokens. Count the task packet, worker
context, monitoring, retries, tool calls, and final review when comparing routes.
Terra exists to execute a settled implementation specification more cheaply than Sol;
it is not a reason to delegate research, scope discovery, or a direct answer.

Before any preflight, worker creation, task creation, external-system access, or scope
expansion, perform all three gates:

1. **Minimum sufficient outcome.** State the smallest answer, change, and evidence that
   fully satisfy the user's exact request. Do not add downstream consequences,
   production data, database access, broad searches, robustness matrices, or adjacent
   deliverables unless they are required for that outcome or explicitly requested.
2. **Token budget checkpoint.** Compare the expected total tokens for direct primary
   work with every proposed delegated route. Delegate only when it is expected to save
   total tokens, provides necessary isolation/capability, or materially reduces risk.
   If the comparison is unclear, use the direct route.
3. **Time budget checkpoint.** Include setup, preflight, task-packet construction,
   monitoring, retries, verification, and review. Reject a lane whose orchestration
   overhead is likely to cost more time than the minimum sufficient direct route.

Make each budget concrete. Use a user-supplied numeric limit when present. Otherwise
state an operational cap such as one focused inspection pass, one worker, an exact
variant or retry limit, and a named checkpoint before additional work. “Be efficient”
without a stopping boundary is not a budget.

Classify the work before choosing a lane:

- **Direct answer / inspection:** For explanation, audit, status, review, small
  read-only inspection, or another request that does not require implementation, keep
  the work in the primary Sol session. Do not preflight agents, delegate, create a
  task, access unrelated external systems, or launch a fresh reviewer. Answer once the
  minimum sufficient evidence is available.
- **Direct small action:** When a tightly bounded action is cheaper for the primary
  than the complete delegation-and-review cycle, perform it directly if current
  permissions allow it. Keep the same verification and scope discipline.
- **Delegated implementation:** Delegate only after the three gates show that a worker
  is the efficient capable route.

Repeat the three gates after the first material evidence, before any new external
access or scope expansion, and when actual cost is materially exceeding the initial
expectation. Ask: “Does current evidence already satisfy the request?”, “What exact
uncertainty remains?”, and “Will the next action likely change the answer enough to
justify its tokens and time?” Stop when the first answer is yes or the third is no.

## Confirm the primary session

Run the primary Codex session on GPT-5.6 Sol with High reasoning. Inspect runtime
metadata when the host exposes it. If an observed model or effort differs, tell the
user to select Sol / High and stop before delegation. If the host omits either value,
continue but mark that field as `required, not exposed by host` in the initial route
announcement and final routing report. Never claim unobserved metadata was verified.

## Choose the implementation lane

Reach this section only after the efficiency gates establish that delegated
implementation is warranted. Sol makes the lane decision; the user does not need to
choose Terra or Luna after activation.

Prefer native Terra / High when:

- a settled specification lets Terra save total tokens relative to Sol implementing;
- the change benefits from the current task's tightly controlled specification;
- implementation or correction should happen with low orchestration overhead;
- shared working-tree state, rapid iteration, or context-heavy debugging matters; or
- a user-visible child task and isolated worktree would add more cost than value.

Prefer a Luna / Max Codex task when:

- the work can be expressed as a complete, bounded task packet;
- an isolated worktree and user-visible progress are useful;
- the task is substantial enough to justify task-creation and monitoring overhead; or
- an independent work stack can proceed safely without overlapping ownership.

Choose Luna only when those benefits justify its task-creation, context-reconstruction,
monitoring, and primary-review overhead. Otherwise prefer Terra or direct primary work.

Check the selected lane's capabilities before announcing it. If the preferred lane is
unavailable, select the other authorized lane only when it can still satisfy the work
and all constraints. Announce the changed selection and the capability reason; never
fall back silently. If neither lane is viable, report the exact missing capability and
stop before implementation.

For multiple independent work items, Sol may choose different lanes. Announce every
route separately, keep ownership non-overlapping, and serialize shared-file or
dependent work.

## Announce the route before implementation

After capability checks and before spawning or creating implementation work, send a
concise user-visible update in this shape:

~~~text
Sol Advisor: ON
Primary: GPT-5.6 Sol / High — <observed | required, not exposed by host>
Implementation: <none — direct primary work | GPT-5.6 Terra / High — native subagent | GPT-5.6 Luna / Max — Codex task>
Why: <one sentence explaining why this is the efficient capable route>
Review: <fresh GPT-5.6 Sol / High reviewer | primary GPT-5.6 Sol / High review>
Budget: <minimum sufficient outcome plus token/time boundary>
~~~

Do not say implementation has started until the selected spawn or task creation is
accepted. If routing changes later, announce the new route and reason before continuing.
For direct answers or small direct actions, do not add a separate route-announcement
message; the compact final direct-route line is sufficient.

## Preflight native custom agents

The native lane uses two user-owned custom-agent TOML files. Before every native
delegation, complete steps 1-2. After spawning, complete steps 3-4 before accepting
the result:

1. Resolve `../../scripts/install-agents.sh` relative to this SKILL.md and run its
   non-mutating exactness check:

   ~~~sh
   skill_dir=<directory-containing-this-SKILL.md>
   installer="$skill_dir/../../scripts/install-agents.sh"
   sh "$installer" --check
   ~~~

   It must prove the Terra and Sol files exactly match the shipped templates and the
   retired Luna companion file is absent.

2. Require the native spawn tool to expose both exact types:

   - `sol_advisor_terra_implementer`
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

   Accept only Terra / High for implementation and Sol / High for native review.

4. For every native Sol review, capture the observed sandbox policy type and
   permission profile type. Never call the review OS-enforced read-only unless the
   observed sandbox policy type is `read-only`.

A missing or invalid native capability makes the native lane unavailable; return to
lane selection and use Luna only when it can satisfy the task. Never substitute an
unnamed native role, model, or reasoning level. Custom-agent TOML, not the spawn call,
pins native model and effort, so omit per-spawn overrides.

## Keep architect work in the primary session

Keep these responsibilities in the primary session:

- Resolve requirements and material ambiguity.
- Choose architecture, interfaces, decomposition, and the implementation route.
- Write the complete five-part native specification or complete Luna task packet.
- Inspect the actual diff and rerun verification.
- Judge reviewer feedback or Luna-task findings and accept the deliverable.

Do not type implementation code, tests, boilerplate, or mechanical configuration in
the primary session when a selected delegated lane can do it. Correct a native result
with a revised Terra specification. Correct a Luna result in the same Luna task.

## Check implementation without duplicating it

Do not spawn another Sol reviewer merely to watch Terra. The primary Sol session owns
one lightweight adherence checkpoint when it is justified. Require that checkpoint
only when the work is long-running or high-risk, or when the worker reports ambiguity,
scope growth, an ownership conflict, failed verification, a new dependency, external
system access, or budget overrun. For routine bounded work, skip it.

When required, have the worker send a concise checkpoint after the first meaningful
unit or first verification result and before the expensive or scope-expanding action.
The primary checks only objective, ownership, constraints, remaining token/time value,
and whether current evidence is already sufficient; it does not reimplement or repeat
the worker's investigation. Return `continue`, `correct`, or `stop`. A correction must
narrow or change the specification; never repeat an unchanged prompt.

## Route native implementation through Terra / High

Spawn exactly:

~~~text
agent_type: sol_advisor_terra_implementer
fork_turns: none
~~~

The installed role pins GPT-5.6 Terra at High reasoning. Omit per-spawn model and
reasoning fields. Confirm the role, model, and effort before accepting work.

- Give each worker one owned file set or bounded responsibility.
- Put the minimum sufficient outcome, token/time boundary, checkpoint trigger, and
  stop conditions in the implementation specification.
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
`gpt-5.6-luna` and `thinking` to `max` in `create_thread`. Accepted creation routing
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

## Verify every implementation

Treat worker reports as claims. Before acceptance:

1. Inspect the working tree, complete diff, and changed-file scope.
2. Rerun the specification's verification commands in the primary session.
3. Compare the evidence with the objective, interfaces, and constraints.
4. Route corrections back to the same implementation lane and verify again.

For native work, obtain a fresh Sol / High final review after primary verification.
The reviewer must return exactly `ship`, `fix-first`, or `rethink`; any subsequent fix
invalidates the verdict and requires a new review. For Luna work, the primary Sol task
performs final review after monitoring, reading the handoff, inspecting the actual
diff, and rerunning verification. Do not add a native Sol reviewer to the Luna lane.

Spawn the native reviewer exactly with no per-spawn model or effort override:

~~~text
agent_type: sol_advisor_sol_reviewer
fork_turns: none
~~~

Apply observed native reviewer isolation:

- With observed `read-only`, report enforced isolation.
- If the host broadens it, proceed only when hard isolation is not required, the
  prompt forbids edits, and exact before-and-after state proves no mutation. Report
  the broader sandbox and permission profile as residual risk.
- If isolation is unobservable, hard isolation is required, or mutation occurs, stop
  the native review.

## Report the route in the final output

For direct primary work, append only this compact line:

~~~text
SOL ADVISOR: direct primary / no delegation — <minimum sufficient boundary and stopping reason>
~~~

Every completed delegated task must include this routing record:

~~~text
SOL ADVISOR ROUTING
ACTIVATION: on for this chat
PRIMARY: GPT-5.6 Sol / High — <observed | required, not exposed by host>
IMPLEMENTATION: <direct primary work or every lane, model, effort, and task/agent identity used>
SELECTION REASON: <why each route was chosen>
EFFICIENCY: <minimum sufficient boundary, checkpoint decisions, and avoided overhead>
ROUTE EVIDENCE: <observed metadata or clearly labeled unavailable fields>
REVIEW: <reviewer model/effort, isolation when native, and verdict>
~~~

Never infer missing runtime evidence. If a route changed, include both the original
selection and actual route with the reason for the change.
