# Native Codex role contracts

Use these contracts after the immutable score selects a cheaper implementation owner.
Scores 1.0–4.9 use the Terra / High executive; scores 5.0–10.0 use primary Sol / High.
The goal is one economical producer handoff, producer self-check, one executive
acceptance check, and no review spiral.

## One preflight per task

Before the first native spawn:

1. Run the bundled agent installer with `--check` and require all installed role files
   to match the shipped templates.
2. Require the exact selected agent type in the current tool surface. For a score below
   5.0, require and start `codex_orchestration_terra_executive` first.
3. After spawn, inspect public metadata first. Use the runtime inspector only when
   model or effort is omitted. Accept only the selected pin.
4. For a reviewer, capture the actual sandbox and permission-profile types.

Do not repeat the installer check during the same task unless agent files changed. A
missing selected tier moves immediately upward; unrelated roles do not block a healthy
tier. When fallback reaches the owning executive's own model, it works directly rather
than spawning a same-model producer. Never silently substitute an unnamed role.

## Shared producer contract

Every producer prompt contains these sections:

~~~text
OBJECTIVE
<Observable outcome and why it matters.>

FILES AND OWNERSHIP
You may inspect only:
- <exact evidence sources, files, or modules>
You may modify only:
- <exact files or modules, or none for read-only work>

You are not alone in the codebase. Other agents or the user may edit concurrently.
Preserve their edits, do not revert unrelated work, and adapt to current state.

INTERFACES
- <Signatures, schemas, commands, or behavior that must remain compatible.>

CONSTRAINTS
- <Safety boundaries, repository conventions, and excluded scope.>

EFFICIENCY BOUNDARY
- Minimum sufficient outcome: <smallest complete result and evidence>.
- Complexity: <root Sol's immutable one-decimal score>.
- Token budget: <focused boundary and excluded work>.
- Time budget: <expected useful work and escalation point>.
- Checkpoint: <none, or the exact risky/expensive milestone>.
- Escalate before broadening scope, adding a dependency, accessing an unapproved
  external system, modifying unowned files, or repeating a failed approach.

VERIFICATION
- Run: <smallest decisive command>
  Success: <concrete expected evidence>
- Inspect: <diff or artifact>
  Success: <concrete expected evidence>
- Self-check: compare the completed result with every objective and constraint before
  returning. Fix any issue found during this self-check within the same attempt.

RETURN
Return actual commands and evidence. A completion claim without evidence is invalid.

WORKER REPORT
STATUS: complete | partial | blocked
ROUTE: <GPT-5.6 Luna / Max | Terra / Medium | Terra / High | Sol / Medium | Sol / High> — native subagent
LABEL: <Luna Max | Terra Medium | Terra High | Sol Medium | Sol High>
OBJECTIVE: <one line>
RESULT: <evidence-backed answer or file summary>
VERIFIED: <exact commands and concrete output>
JUDGMENT CALLS: <decisions left open, or none>
GAPS: <unfinished work, or none>
~~~

A time-budget checkpoint triggers replanning, not abandonment. Use at most one
unchanged spawn retry. After implementation, the same producer may receive exactly one
bounded correction request from the owning executive. If that correction fails
acceptance, the producer is retired for the task and the owning executive finishes.

## Producer lanes

Spawn exactly one mapped producer by default, always with `fork_turns: none`:

~~~text
1.0–2.9: agent_type: codex_orchestration_luna_implementer; task_name: luna_max_<objective_slug>
3.0–5.0: agent_type: codex_orchestration_terra_medium_implementer; task_name: terra_medium_<objective_slug>
5.1–6.5: agent_type: codex_orchestration_terra_implementer; task_name: terra_high_<objective_slug>
6.6–7.9: agent_type: codex_orchestration_sol_medium_implementer; task_name: sol_medium_<objective_slug>
8.0–10.0: primary Sol / High implements directly; no producer spawn
~~~

The custom-agent files pin model and effort. Omit per-spawn overrides. Register the
real thread ID against the root receipt immediately after spawn.

Prompt:

~~~text
ROLE
Act as Codex Orchestration's score-selected producer. Execute the settled specification
within the stated ownership and constraints. Surface ambiguity instead of taking over
executive decisions.

<paste and complete the Shared producer contract>
~~~

## Owning-executive acceptance and correction

The producer self-checks before returning. The owning Terra or Sol executive inspects
the result and reruns the smallest decisive verification once. If it finds a material
defect, send one precise correction request to the same producer. After that producer's
second self-check, the executive performs one new acceptance check. If a material
defect remains, retire the producer for this task; the owning executive completes and
verifies the work directly. Do not spawn a replacement producer.

## Exceptional independent Sol review

Do not review by score alone. Spawn a fresh reviewer only for a user-requested
independent review or a critical security, billing, authorization, destructive-data,
or irreversible-schema boundary that genuinely requires independent context after the
owning executive's acceptance.

~~~text
agent_type: codex_orchestration_sol_reviewer
task_name: sol_high_review_<objective_slug>
fork_turns: none
~~~

Prompt:

~~~text
ROLE
Act as the fresh final reviewer. Remain strictly read-only in behavior; do not edit.

STATED GOAL
<Requested outcome.>

CHANGE SET
<Exact files and complete diff or revisions.>

CONSTRAINTS
- <Compatibility and safety boundaries.>

VERIFICATION EVIDENCE
- <command> -> <actual evidence>

REVIEW
Judge correctness, completeness, regressions, scope, and material risk.

SOL REVIEW
VERDICT: ship | fix-first | rethink
LABEL: Sol High
REASON: <decisive evidence>
FINDINGS: <precise required fixes, or none>
RESIDUAL RISK: <largest remaining risk, or none>
~~~

Any subsequent fix invalidates the verdict. If the host does not enforce read-only,
proceed only when hard isolation is unnecessary, the prompt forbids edits, and exact
before/after state proves no mutation.

## Low-band Terra executive

For every immutable score from 1.0 through 4.9, primary Sol starts
`codex_orchestration_terra_executive` and gives it the original request, constraints,
relevant evidence, immutable score, selected producer, root thread ID, and resolved
receipt helper. Terra owns requirements, the producer packet, the one acceptance check,
the one correction opportunity, direct takeover when correction fails, and final
acceptance. Root Sol must not duplicate that work.

~~~text
agent_type: codex_orchestration_terra_executive
task_name: terra_high_exec_<objective_slug>
fork_turns: none
~~~

The Terra executive emits the same three-line route before its first nested producer
call and registers every descendant against the root receipt immediately. Its Stop is
not a separate task completion. If the selected producer falls upward to Terra / High,
the Terra executive implements directly instead of spawning another Terra / High
agent. If scope materially grows beyond the low band, it escalates to root Sol without
changing the immutable score.
