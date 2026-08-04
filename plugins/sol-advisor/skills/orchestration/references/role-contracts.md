# Native Codex role contracts

Use these contracts with Sol Advisor's namespaced, role-pinned native custom agents.
They do not launch a nested Codex CLI or change global default-subagent routing. Adapt
every placeholder without removing a required field.

## Required preflight

Before every native spawn, complete steps 1-2 of SKILL.md's preflight. After spawning,
complete steps 3-4 before accepting the result:

1. Require the non-mutating companion check to prove all seven installed files exactly
   match current templates. Use only a check performed in the current turn.
2. Require native exposure of the exact selected implementation type. Do not require
   unrelated implementation roles or the reviewer to start that worker. Check each
   fallback tier only when it is attempted, and check `sol_advisor_sol_reviewer`
   separately only when that review is required. For a score below 5.0, first require
   `sol_advisor_terra_executive`.
3. Observe the selected role, model, and effort through public spawn/details metadata
   first, using the local runtime inspector only for omitted fields. Accept only
   the score-selected implementation pin, Terra / High for the low-band executive,
   and Sol / High for high-band implementation review.
4. For the reviewer, capture actual sandbox policy and permission profile types.

A missing, stale, unsafe, conflicting, unavailable, inconsistent, or unobservable
selected role/model/effort makes only that tier unavailable. An unrelated role cannot
block a healthy selected tier. Never reuse a prior-turn failure or a “known issue” as
current evidence. Never silently fall back; the owning executive must report the exact
current-turn failure and reselect a capable route toward completion. Model and effort
are pinned by custom-agent TOML, so omit native per-spawn overrides.

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
- Complexity: <root Sol's immutable 1.0–10.0 task score and selected band>.
- Token budget: <focused implementation boundary and explicitly excluded work>.
- Time budget: <expected bounded effort and the point at which to escalate for replanning>.
- Checkpoint: <none for routine bounded work, or the exact first milestone to report
  before an expensive, external, risky, or scope-expanding action>.
- Escalate to the owning executive before broadening scope, accessing an external
  system not explicitly required above, adding a dependency, modifying unowned files,
  repeating a failed approach, or exceeding the stated budget. Do not abandon the
  objective or return an avoidable partial result merely because a budget estimate was
  exceeded.

VERIFICATION
- Run: <exact command>
  Success: <concrete expected result>
- Inspect: <exact file, diff, or generated artifact>
  Success: <concrete expected evidence>

RETURN
Return exact commands and actual evidence. A completion claim without evidence is invalid.

WORKER REPORT
STATUS: complete | partial (only after user cancellation or owning-executive-authorized
scope change) | blocked
ROUTE: <GPT-5.6 Luna / Max | Terra / Medium | Terra / High | Sol / Medium | Sol / High> — native subagent
LABEL: <Luna Max | Terra Medium | Terra High | Sol Medium | Sol High>
OBJECTIVE: <one-line restatement>
RESULT: <answer with cited evidence, or file-by-file summary from the actual diff>
VERIFIED: <exact commands plus concrete output evidence>
JUDGMENT CALLS: <decisions the specification left open, or none>
GAPS: <unfinished work, ambiguity, or none>
~~~

## Low-band Terra executive contract

For an immutable score from 1.0 through 4.9, spawn
`sol_advisor_terra_executive` with task name `terra_high_exec_<objective_slug>` and
`fork_turns: none`. Give it the original user request, current constraints, relevant
prior evidence, root thread ID, resolved receipt-helper path, exact immutable score,
exact executive line, actual producer line, producer mapping, and explicit root receipt
state. It owns requirements,
architecture, the mapped producer, verification, corrections, final review, and
acceptance. Root Sol registers this executive. Before its first nested producer or
reviewer tool call, the executive must emit the same exact executive, implementation,
and complexity lines inside its own session so its PreToolUse gate persists the score.
Immediately after every descendant spawn, it must run:

~~~sh
python3 "<resolved-receipt-helper-path>" add-thread <descendant-id> --root-thread-id <root-thread-id>
~~~

It must complete registration before monitoring or accepting descendant work; recovery
recursion is not a substitute for this normal lifecycle.
Its delegated Stop must release without requiring or recording a separate receipt or
effectiveness completion. Root Stop remains the sole user-task completion record.

~~~text
agent_type: sol_advisor_terra_executive
task_name: terra_high_exec_<objective_slug>
fork_turns: none
~~~

The executive performs final review itself. Do not add `sol_advisor_sol_reviewer`
unless the user explicitly requests independent Sol review. If the work materially
grows beyond 4.9, it must stop further implementation and escalate to root Sol. Root
Sol may make a fresh executive decision, but must not revise the persisted score.

Use this exact fallback line only after current-turn Terra-executive unavailability:

~~~text
Executive design and review: GPT-5.6 Sol / High — Terra executive fallback: <current-turn verified reason>
~~~

A budget overrun alone never permits `partial` or `blocked`; escalate and await the
owning executive's replanned route toward the complete objective.

Every visible worker name starts with its spelled-out model/effort: `Luna Max`,
`Terra Medium`, `Terra High`, `Sol Medium`, or `Sol High`. For native `task_name`
values, use the schema-safe prefixes `luna_max_`, `terra_medium_`, `terra_high_`,
`sol_medium_`, and `sol_high_` before the concise objective slug.

The owning executive must inspect the evidence or diff and rerun verification itself.
It must also apply the minimum-sufficient, token-budget, and time-budget checkpoints
before producer delegation and at every worker checkpoint. Before a low-band executive
handoff, root Sol applies those gates only to the minimum initial scoring evidence and
the bounded Terra-executive handoff; after handoff, the Terra executive owns all
producer-delegation and worker checkpoints. The owning executive must not add a second
Sol reviewer during implementation by default; use the adherence check from SKILL.md
only when its triggers apply.

## Native implementation lanes

The selected executive must settle architecture and give every producer a complete packet.
Select exactly one role from the implementation score:

~~~text
1.0–2.9: agent_type: sol_advisor_luna_implementer; task_name: luna_max_<objective_slug>
3.0–5.0: agent_type: sol_advisor_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: sol_advisor_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: sol_advisor_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: agent_type: sol_advisor_sol_high_implementer; task_name: sol_high_<objective_slug>
fork_turns: none
~~~

The installed roles pin Luna / Max, Terra / Medium, Terra / High, Sol / Medium, and Sol / High.
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

After owning-executive verification at score 5.0+, spawn a new native thread exactly.
Below 5.0, the Terra executive reviews read-only and modifying results directly; add a
fresh Sol reviewer only when high stakes or an expressly requested independent review
justifies the added cost.

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
