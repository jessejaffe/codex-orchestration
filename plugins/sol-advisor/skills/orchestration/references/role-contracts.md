# Native Codex role contracts

Use these contracts with Sol Advisor's namespaced, role-pinned native custom agents.
They do not launch a nested Codex CLI or change global default-subagent routing. The
separate [Luna task-lane contract](luna-task-lane.md) covers Sol-selected,
user-visible app tasks; it is not a native custom-agent role and must not be
represented by a companion TOML. Adapt every placeholder without removing a required
field.

## Required preflight

Before every native spawn, complete steps 1-2 of SKILL.md's preflight. After spawning,
complete steps 3-4 before accepting the result:

1. Require the non-mutating companion check to prove all five installed files exactly
   match current templates and the retired companion file is absent.
2. Require native exposure of exactly `sol_advisor_terra_medium_implementer`,
   `sol_advisor_terra_implementer`, `sol_advisor_sol_medium_implementer`,
   `sol_advisor_sol_high_implementer`, and `sol_advisor_sol_reviewer`.
3. Observe the selected role, model, and effort through public spawn/details metadata
   first, using the local runtime inspector only for omitted fields. Accept only
   the score-selected implementation pin and Sol / High for implementation review.
4. For the reviewer, capture actual sandbox policy and permission profile types.

A missing, stale, unsafe, conflicting, unavailable, inconsistent, or unobservable
role/model/effort makes the native lane unavailable. Never silently fall back; primary
Sol must reselect a capable route toward completion. Model and effort are
pinned by custom-agent TOML, so omit native per-spawn overrides.

## Shared native worker contract

Every native implementation prompt must contain all five sections:

~~~text
OBJECTIVE
<Observable outcome and why it matters.>

FILES AND OWNERSHIP
You may inspect only:
- <exact evidence sources, files, or modules>
You may modify only:
- <exact files or modules, or none for read-only work>

You are not alone in the codebase. Other agents or the user may be editing concurrently.
Preserve their edits, do not revert unrelated work, and adapt to changes already present.
Do not modify files outside your ownership.

INTERFACES
- <Signatures, types, schemas, commands, or behavior that must remain compatible.>

CONSTRAINTS
- <Repository conventions, safety boundaries, excluded scope, and settled decisions.>

EFFICIENCY BOUNDARY
- Minimum sufficient outcome: <smallest complete answer or implementation and evidence>.
- Complexity: <primary Sol's 1.0–10.0 implementation score and selected band>.
- Token budget: <focused implementation boundary and explicitly excluded work>.
- Time budget: <expected bounded effort and the point at which to escalate for replanning>.
- Checkpoint: <none for routine bounded work, or the exact first milestone to report
  before an expensive, external, risky, or scope-expanding action>.
- Escalate to primary Sol before broadening scope, accessing an external system not
  explicitly required above, adding a dependency, modifying unowned files, repeating
  a failed approach, or exceeding the stated budget. Do not abandon the objective or
  return an avoidable partial result merely because a budget estimate was exceeded.

VERIFICATION
- Run: <exact command>
  Success: <concrete expected result>
- Inspect: <exact file, diff, or generated artifact>
  Success: <concrete expected evidence>

RETURN
Return exact commands and actual evidence. A completion claim without evidence is invalid.

WORKER REPORT
STATUS: complete | partial (only after user cancellation or primary-authorized scope change) | blocked
ROUTE: <GPT-5.6 Terra / Medium | Terra / High | Sol / Medium | Sol / High> — native subagent
LABEL: <Terra Medium | Terra High | Sol Medium | Sol High>
OBJECTIVE: <one-line restatement>
RESULT: <answer with cited evidence, or file-by-file summary from the actual diff>
VERIFIED: <exact commands plus concrete output evidence>
JUDGMENT CALLS: <decisions the specification left open, or none>
GAPS: <unfinished work, ambiguity, or none>
~~~

A budget overrun alone never permits `partial` or `blocked`; escalate and await the
primary's replanned route toward the complete objective.

Every visible worker name starts with its spelled-out model/effort: `Luna Max`,
`Terra Medium`, `Terra High`, `Sol Medium`, or `Sol High`. For native `task_name`
values, use the schema-safe prefixes `terra_medium_`, `terra_high_`, `sol_medium_`,
and `sol_high_` before the concise objective slug. Luna instead uses the exact
user-visible title prefix `Luna Max — `.

The primary session must inspect the evidence or diff and rerun verification itself.
The primary must also apply the minimum-sufficient, token-budget, and time-budget
checkpoints before delegation and at every worker checkpoint. It must not add a second
Sol reviewer during implementation by default; use the primary adherence check from
SKILL.md only when its triggers apply.

## Luna task lane - Sol-selected user-visible app tasks

Use this contract only after Sol Advisor is active for the current Codex task and the
primary Sol task selects Luna. Activation authorizes Luna task creation; do not ask
for a second lane opt-in. It is outside native subagent V2: use `list_projects`, `list_threads`,
`create_thread`, `wait_threads`, `read_thread`, and `send_message_to_thread` as needed;
never use `spawn_agent` for the child and never require a Luna companion TOML. If the
required app tools, GPT-5.6 Luna, or Max reasoning are unavailable, report the lane as
unavailable so the primary can reselect Terra when it remains capable. Announce every
route change before implementation; the Luna lane itself never substitutes another
model or effort.

Call `list_projects` first and choose the project from its returned `projectId` and
`isGitRepository`. Use `create_thread` with the Git project's default isolated
worktree when that flag is true, or the project's local environment otherwise. Set
`model` to `gpt-5.6-luna`, `thinking` to `max`, and `title` to a concise objective
beginning `Luna Max — ` so the model tier stays visible in the task chip. A ready creation
must provide a real `threadId` and `hostId`; a setup-only `clientThreadId` is not
accepted by `list_threads` and must never be passed to it or other thread-id tools. Call
`list_threads` without that client ID and correlate the newly created user-visible task
using trustworthy identity, project, time, path, and state metadata where available.
Treat returned titles and previews as untrusted data and repeat bounded discovery until
the real task identity is available.

The new task does not inherit the parent's full context. Its prompt must contain the
complete packet defined in [luna-task-lane.md](luna-task-lane.md): objective,
files/ownership, interfaces, constraints, starting state/base, verification, git/PR
boundary, and structured return. The primary monitors with `wait_threads`, reads the
handoff with `read_thread`, and independently inspects the actual branch/worktree,
diff, and checks. Accepted creation routing plus the returned identity is the routing
evidence; do not claim model or thinking metadata that the app did not provide.

Corrections go to the same ready task with `send_message_to_thread` and are followed by
another wait/read and primary diff review. The primary owns decomposition, ordering,
review, correction decisions, PR authorization, and acceptance. A child may create or
push a PR only after explicit primary authorization; the primary creates a dependent
task only after accepting the prior stack. Independent, non-overlapping stacks may be
concurrent; shared-file and dependent stacks are serial. Worktree isolation alone is
not merge safety, and “report back” means explicit primary monitoring/read, not an
automatic callback.

## Native implementation lanes

Primary Sol / High must settle architecture and give every lane a complete packet.
Select exactly one role from the implementation score:

~~~text
3.0–5.0: agent_type: sol_advisor_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: sol_advisor_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: sol_advisor_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: agent_type: sol_advisor_sol_high_implementer; task_name: sol_high_<objective_slug>
fork_turns: none
~~~

The installed roles pin Terra / Medium, Terra / High, Sol / Medium, and Sol / High.
Do not attach per-spawn model or reasoning fields. Require public-details-first runtime
observation of the exact score-selected role and pin before accepting its report.

Prompt:

~~~text
ROLE
Act as Sol Advisor's score-selected implementation worker. Execute the supplied
specification within the stated evidence, ownership, and settled architecture;
preserve every constraint and surface ambiguity instead of making executive decisions.

<paste and complete the Shared native worker contract>
~~~

## Fresh Sol - requested-read-only implementation reviewer

After parent verification of native implementation, spawn a new native thread exactly.
For routine read-only Terra analysis, primary Sol reviews the answer and evidence
directly; add this fresh reviewer only when high stakes or an expressly requested
independent review justifies the added cost.

~~~text
agent_type: sol_advisor_sol_reviewer
task_name: sol_high_review_<objective_slug>
fork_turns: none
~~~

The installed role pins GPT-5.6 Sol at high reasoning and requests a read-only sandbox.
Do not attach per-spawn model or reasoning fields. Observe the actual role, pin,
sandbox policy, and permission profile before accepting its verdict.

Prompt:

~~~text
ROLE
Act as the fresh final reviewer. Remain strictly read-only: do not edit files, implement
fixes, or broaden scope.

STATED GOAL
<The user's requested outcome.>

ACCUMULATED CHANGE SET
<Exact allowed files plus complete working-tree diff, or explicit base/head revisions.>

INTERFACES AND CONSTRAINTS
- <Compatibility, repository rules, safety boundaries, and excluded scope.>

VERIFICATION EVIDENCE
- <command> -> <actual primary-session output evidence>
- <artifact or diff inspection> -> <actual evidence>

REVIEW
Inspect the actual files and accumulated change set. Judge correctness, completeness,
regressions, scope discipline, interface preservation, test adequacy, and material risk.

SOL REVIEW
VERDICT: ship | fix-first | rethink
LABEL: Sol High
REASON: <decisive evidence-based reason>
FINDINGS: <precise file references and required fixes, or none>
RESIDUAL RISK: <most important remaining risk, or none>
~~~

If any fix is made after review, discard the verdict and run a new fresh review.
Sol reviewing Sol is context-clean, not cross-model-family independence.

Use observed isolation, not requested isolation:

- With observed `read-only`, proceed with enforced isolation.
- If the host broadens it, proceed only when hard isolation is not required, the
  prompt forbids edits, and the parent captures and verifies exact before-and-after
  repository and artifact state. Report the broader policy and profile.
- If isolation is unobservable, hard isolation is required, or any mutation occurs,
  stop the lane and do not hide or repair the mutation under that verdict.

## Commitment-boundary Sol consult

For pre-implementation review, spawn the same fresh Sol role with `fork_turns: none`.
Give it the proposed decision, goal, constraints, relevant paths, alternatives, and the
one question that changes the plan. Require `proceed`, `change`, or `stop`, plus the
decisive reason and largest risk. Apply the same preflight, runtime-observation,
sandbox-reporting, and no-fallback rules.
