# Terra-first routing contract

This is a maintenance reference. Runtime routing is injected by
`scripts/prompt-router-hook.py`; normal user turns never read this file.

## Critical path

1. `UserPromptSubmit` reads chat-local state once.
2. Active root Sol immediately spawns `codex_orchestration_terra_executive` with
   `fork_turns: all` and a constant prompt.
3. Terra conservatively classifies the request as low-band or complex.
4. Low-band: Terra selects Luna, Terra Medium, or direct Terra High and owns acceptance.
5. Complex: Terra returns a Sol-lane recommendation without task work; root Sol High
   owns architecture and acceptance, using Sol Low, Sol Medium, or direct Sol High.
6. Root returns the result with the observed executive and implementation lines.

There is no runtime receipt, PostToolUse hook, or Stop hook. Detailed usage comparison
is an on-demand diagnostic and never delays a task.

Root must not score, inspect, plan, summarize, or construct a task packet before the
Terra spawn. This is the main credit and latency invariant.

## Continuity

Root-to-Terra and Terra-to-producer spawns use `fork_turns: all`. The models receive
the original requirements and later corrections directly rather than relying on a
lossy summary. Keep the explicit spawn message short and add only ownership boundaries
that are absent from the conversation.

## Model selection

Terra chooses internally without a visible numeric score. It may own only:

- Luna / Max: fully settled mechanical work.
- Terra / Medium: settled ordinary work.
- Terra / High: direct conversational, bounded tool, or settled routine implementation.

Any uncertainty, deep diagnosis, broad unfamiliar-repository work, cross-system work,
unresolved architecture, security or authorization judgment, high-stakes advice, or
irreversible data/schema change returns immediately to root Sol High. Terra may
recommend Sol Low or Sol Medium as producer, but it must not design, execute, or accept
that complex work. Root Sol High remains its executive.

The selected producer self-checks. The owning executive performs one acceptance check
and may send one correction to the same producer. Independent review remains
exceptional.

## Return contract

Every accepted Terra result begins with:

```text
Executive design and review: GPT-5.6 Terra / High
Implementation: <actual GPT-5.6 model / effort, or Terra / High direct>
```

Then return the result, modified files, decisive verification, and unresolved gaps.
Complex work returns only this line, before repository inspection or mutation:

```text
ESCALATE_TO_ROOT_SOL_HIGH: ROUTE=<SOL_LOW|SOL_MEDIUM|SOL_HIGH>; REASON=<one sentence>
```

The offline benchmark cases live in `scripts/triage-cases.json`. Under-routing a
complex case is a correctness failure; over-routing a low-band case is measured as
overhead. The normal runtime never reads that fixture.
