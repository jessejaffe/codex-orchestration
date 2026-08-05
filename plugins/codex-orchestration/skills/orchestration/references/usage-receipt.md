# Weekly usage receipt

Measure each active Codex Orchestration task and end it with exactly three short
savings estimates. The helper uses Codex's recorded per-thread token mix, checks the
official GPT-5.6 credit rates once per local day, and normally calibrates those
weighted tokens to the current weekly usage meter. It reprices the same observed
tokens as Sol for the comparison; it does not pretend to know a counterfactual model's
token count. If a weekly denominator cannot be calibrated, it must still produce the
rate-based task-credit receipt described below.

## Normal completion

Resolve `../../../scripts/usage-receipt.py` relative to this reference. Normal routing
has no receipt startup or registration step. After verification, make this the final
tool action before composing the answer:

~~~sh
python3 "$usage_receipt" finish
~~~

`finish` uses the active root-turn boundary and authoritative `sub_agent_activity`
events to discover every native descendant recursively. It therefore remains correct
when the spawn surface returns only a task path rather than a UUID. A stale or failed
manual `add-thread` call cannot silently produce a valid-looking Sol-only receipt.

The legacy `start` and `add-thread` commands remain available for diagnostics and older
automation, but normal orchestration must not spend user time on them. When legacy
state exists, `finish` reconciles it with transcript descendants before pricing.

This command is mandatory for every completed scored task. Do not draft the final
answer and do not substitute hand-written model lines until the command has run.

When weekly calibration is available, append this output verbatim at the very end of
the response:

~~~text
Actual weekly usage: <percentage>
All-Sol equivalent: <percentage>
Estimated routing savings: <percentage>
~~~

When weekly calibration is unavailable, append the official-rate fallback verbatim:

~~~text
Estimated task credits: <credits>
All-Sol equivalent credits: <credits>
Estimated routing savings: <percentage>
~~~

The fallback prices the exact observed task tokens at their actual routed model rates,
reprices that same token mix at Sol rates, and reports the relative savings. It is not
a weekly-allowance percentage and must not be labeled as one.

Do not add a receipt heading, basis, confidence, token totals, pricing explanation, or
another savings sentence. The word `Estimated` already carries the necessary caveat.
The plugin's Stop hook verifies these lines before a routed turn can stop. It uses the
transcript's turn boundary and every spawned thread ID to run the equivalent recovery
command:

~~~sh
python3 "$usage_receipt" recover --transcript <root-rollout.jsonl> --turn-id <turn-id>
~~~

Weekly calibration failure alone must never produce `Savings receipt unavailable`;
normal finish and transcript recovery fall back to official-rate task credits. Only an
unrecoverable task transcript, missing task model, or unavailable official pricing may
produce one explicit `Savings receipt unavailable: <reason>` line. Never omit the receipt.
Preserve legacy task state for a later finish only when the current request is
interrupted rather than completed.

The calibrated receipt estimates the weekly denominator from local Codex history plus
the weekly meter. Forked transcripts can replay parent token events before recording a
child model context; the helper excludes that pre-context replay rather than counting
it twice. Unknown post-context models are conservatively priced at Sol rates for
calibration. A cached calibration tolerates up to 60 seconds of reset-timestamp drift.
Both receipt forms compare identical observed token mixes at different published
rates. Sol / Low, Sol / Medium, and Sol / High therefore have no rate-based difference; savings
arise from Luna or Terra implementation usage. Explain these details only if the user
asks.
