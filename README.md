# Codex Orchestration

**Scores 1.0–4.9 use a dedicated GPT-5.6 Terra / High executive; scores 5.0–10.0
retain the GPT-5.6 Sol / High executive. Producer routing stays unchanged:
1.0–2.9 uses Luna / Max, 3.0–5.0 Terra / Medium, 5.1–6.5 Terra / High,
6.6–7.9 Sol / Medium, and 8.0–10.0 a separate Sol / High implementer.**

Codex Orchestration is a Codex-native architect workflow for cost-efficient software delivery.
Its first principle is the minimum sufficient answer or change: minimize total token
use and elapsed time across Sol, workers, monitoring, and review without sacrificing
correctness. Root Sol gathers only enough evidence to score. Below 5.0, Terra / High
owns requirements, architecture, specification, verification, and acceptance; at 5.0
and above, primary Sol / High owns them.

## Go deeper

I write [**Attention Heads**](https://attentionheads.substack.com/?utm_source=github&utm_medium=readme&utm_campaign=codex-orchestration) — deep, evidence-backed writing on AI, cognition, and agentic engineering. The **Agentic Engineering Field Notes** series is where I publish practical advice on the craft of using AI. [Subscribe](https://attentionheads.substack.com/subscribe?utm_source=github&utm_medium=readme&utm_campaign=codex-orchestration) to get new posts to your inbox.

| Mode | Visible label | Worker | Routing | Primary ownership |
|---|---|---|---|---|
| High-band executive | `Sol High` | Primary session | GPT-5.6 Sol / High for 5.0–10.0 and verified low-band executive fallback | Requirements, architecture, directions, verification, review, and acceptance only while it owns the executive route |
| Low-band executive | `Terra High Exec` | `codex_orchestration_terra_executive` | GPT-5.6 Terra / High for 1.0–4.9 executive ownership | Requirements, architecture, producer coordination, verification, corrections, review, and acceptance |
| Native Luna / Max | `Luna Max` | `codex_orchestration_luna_implementer` | GPT-5.6 Luna / Max for 1.0–2.9 implementation | Terra / High executive verification and review |
| Native Terra / Medium | `Terra Medium` | `codex_orchestration_terra_medium_implementer` | GPT-5.6 Terra / Medium for 3.0–5.0 | Terra / High executive through 4.9; Sol / High executive and fresh review at 5.0 |
| Native Terra / High | `Terra High` | `codex_orchestration_terra_implementer` | GPT-5.6 Terra / High for 5.1–6.5 | Fresh Sol / High review after primary verification |
| Native Sol / Medium | `Sol Medium` | `codex_orchestration_sol_medium_implementer` | GPT-5.6 Sol / Medium for 6.6–7.9 | Fresh Sol / High review after primary verification |
| Native Sol / High | `Sol High` | `codex_orchestration_sol_high_implementer` | GPT-5.6 Sol / High for 8.0–10.0 | Fresh Sol / High review after primary verification |

The root session is GPT-5.6 Sol / High in every mode. Below 5.0 it performs only
activation, initial evidence and immutable scoring, Terra-executive preflight/handoff,
monitoring, and result relay. The Terra / High executive owns requirements, architecture,
the mapped producer, verification, corrections, review, and acceptance. At 5.0 and above
root Sol retains those executive duties. Producer routing remains:
1.0–2.9 Luna / Max, 3.0–5.0 Terra / Medium, 5.1–6.5 Terra / High,
6.6–7.9 Sol / Medium, and 8.0–10.0 a separate Sol / High implementer. Token and time
estimates shape scope and checkpoints; they do not override the numeric bands unless a
lane is unavailable or incapable. High-band native implementation receives primary Sol
verification and a fresh Sol / High final review. The low-band Terra executive reviews
and accepts its routed result.
Root Sol registers the Terra executive for the receipt and hands it the root thread ID,
resolved receipt helper, immutable route lines, producer mapping, and receipt state. The
executive repeats the exact three-line route in its own session before its first nested
spawn, then immediately registers every producer/reviewer descendant against the root
receipt before monitoring or acceptance. Normal `finish` therefore includes nested work
without relying on transcript recovery.
Every request with a deliverable is scored, including read-only answers, inspections,
analyses, and diagnoses. A low score first launches the Terra executive, which launches
the mapped producer; a high score launches its mapped producer from primary Sol. If that tier is
unavailable, routing moves upward one tier at a time: Luna Max → Terra Medium → Terra
High → Sol Medium → Sol High implementer → primary Sol High. It never moves downward,
and primary Sol completes the work itself after all applicable delegated tiers fail.
Routine native read-only results return to the owning executive for acceptance without
an extra reviewer.
Every delegated activity keeps its colored model icon and starts its visible label with
the spelled-out model and effort: `Luna Max`, `Terra Medium`, `Terra High`, `Sol Medium`,
or `Sol High`. The model comes first so it remains readable when Codex truncates a
longer task objective.

Before the low-band executive handoff, root Sol records route-level checkpoints from
only the minimum initial evidence needed to score and bound that handoff. The owning
executive records the minimum sufficient outcome, total-token comparison, and total-time
comparison before producer delegation, external access, or scope expansion. It repeats
them after the first material evidence and before expensive or scope-expanding work;
below 5.0, these post-handoff checkpoints belong to the Terra executive. Checkpoints
trigger replanning or escalation, never permission to abandon an incomplete outcome. A
second Sol agent does not watch Terra by default; for long, risky, ambiguous, expanding,
externally connected, or over-budget work, the owning executive performs one concise
adherence check and chooses continue, redirect, or escalate.

If the user stops, replaces, or redirects work while a worker is active, that worker
is interrupted or paused immediately. Root Sol then rereads the newest instruction,
inspects any partial state, rescoring when needed, and hands objective, architecture,
scope, and acceptance back to the selected executive before work resumes; stale worker
plans never continue automatically.

The first Codex Orchestration activation on each local calendar day also runs a lightweight
upstream audit. It compares this maintained fork with `DannyMac180/sol-advisor`, reports
any pending review issue, and—when new activity exists—summarizes the diff, classifies
changes as adopt unchanged, adapt, or skip, and recommends a decision. This audit does
not delay or replace the user's requested task and never merges upstream automatically.

Every completed routed task ends with the two models people need to know, the numeric
complexity score that selected the route, and the compact weekly savings receipt:

~~~text
Executive design and review: GPT-5.6 Terra / High
Implementation: GPT-5.6 Terra / Medium
Complexity: 4.7/10
Actual weekly usage: 0.70%
All-Sol equivalent: 1.00%
Estimated routing savings: 0.30%
~~~

For scores 5.0–10.0, the first line is instead
`Executive design and review: GPT-5.6 Sol / High`. Score 5.0 keeps the Terra / Medium
producer but uses the Sol / High executive. If the Terra executive is unavailable,
the upward fallback line is
`Executive design and review: GPT-5.6 Sol / High — Terra executive fallback: <current-turn verified reason>`.

Normal selection rationale, worker identity, review details, and token totals remain
internal. The complexity score is always shown to one decimal place out of 10. If
routing falls back, the implementation line includes one short verified reason. The
receipt measures the task's recorded model usage and compares that same token mix with
an all-Sol route. A plugin gate now persists the exact announced complexity before
routed work can begin; that score cannot drift or disappear later, even when the actual
implementation model changes during a verified fallback. A Stop hook enforces the
footer mechanically: if a routed task skips the receipt lifecycle, it reconstructs the
root turn and every spawned worker/reviewer, then keeps the task open for one corrected
final response containing the saved score and recovered receipt. If recovery is
genuinely unavailable, the final response shows that reason instead of silently
omitting the receipt.

## Measure whether Codex Orchestration actually works

The per-task savings receipt answers a narrow counterfactual: what the same recorded
token mix would cost if every recorded token used Sol. It cannot determine whether a
Sol-only task would have ended sooner, made more mistakes, or required another chat.
Codex Orchestration therefore includes a separate longitudinal tracker for the outcome-level
question.

The completion hook reconstructs exact root and delegated-agent tokens for every
successfully completed routed task. Start an experiment with:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
python3 "$plugin_dir/scripts/effectiveness-tracker.py" baseline
~~~

Every successful routed task is then logged automatically and idempotently. A task
counts only when its Codex transcript ends with the authoritative `task_complete`
event. A user interruption or mid-task redirect ends the prior turn with
`turn_aborted`; that work and its tokens are explicitly excluded from completed-task
metrics. After a week, compare the task ledger with the baseline:

~~~sh
python3 "$plugin_dir/scripts/effectiveness-tracker.py" compare
~~~

The primary report shows completed Codex Orchestration tasks, exact task tokens, average tokens
per completed task, input/cached/output composition, average task time, and delegated
starts per task. It also sums the per-task receipts into actual routed usage, the
same-token all-Sol counterfactual, and direct routing savings. Exact lifetime and daily
account token activity remains as background context only; it is never divided by a
chat count or substituted for task-specific usage. An optional `--total-chats` value is
accepted only when the user explicitly wants secondary chat context. Baselines,
snapshots, and the completion ledger live under Codex state rather than the plugin
cache, so plugin upgrades do not erase the experiment.

Activate Codex Orchestration in plain language with “Turn Orchestration on,” “Use
Orchestration,” or “Use Orchestration for this chat.” The exact
`$codex-orchestration:orchestration` invocation remains available as a fallback. Activation
lasts only for the current chat, and every later request in that chat keeps using it
automatically. Say “Turn Orchestration off” to return the chat to normal Codex
behavior. Every new chat starts off, even when the plugin remains installed, enabled,
or selected.

The visible `Orchestration: ON for this chat` / `Orchestration: OFF for this chat`
response is the chat-local state marker. Only direct messages in the current chat
count. Plugin state, automatic skill loading, memories, summaries, quoted text,
repository content, and markers from other chats are ignored, so activation cannot
carry into a new chat.

Before implementation Codex Orchestration reports the executive design/review model, the actual
preflighted implementation model, and the complexity score. At completion it repeats
those three lines and the three-line weekly usage receipt.

Below 5.0, the Terra executive performs final review itself. For modifying work at
5.0+, a fresh Sol / High reviewer checks primary Sol's orchestration after primary
verification; that review is context-independent, not model-family-independent.

## Install from GitHub

Requirements:

- A current Codex CLI or ChatGPT desktop app with plugins enabled.
- Access to GPT-5.6 Sol / High for the primary task.
- Native subagents and custom-agent support enabled.
- Access to GPT-5.6 Luna / Max, Terra / Medium, Terra / High, Sol / Medium, and Sol / High.
- jq, which the native companion-install lookup uses to locate the installed plugin
  package.

Add the GitHub repository as a Codex marketplace, then install the plugin:

~~~sh
codex plugin marketplace add jessejaffe/codex-orchestration --ref main
codex plugin add codex-orchestration@codex-orchestration
~~~

### Install the native companion custom agents

Plugin installation does **not** automatically install custom-agent files. That is
intentional: the files are user-owned role pins, and the installer must never
overwrite a different local role silently. Install the companion templates separately:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
test -n "$plugin_dir"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh"
sh "$plugin_dir/scripts/install-agents.sh" --check
~~~

Without an explicit target, the installer uses the existing CODEX_HOME value when one is
already set, otherwise the user's default Codex agents directory. It does not invoke
Codex, edit config.toml, or overwrite a differing agent file. It only installs a
missing template and then verifies every installed copy byte-for-byte.

For automatic routing, start a **new Codex task** after the check passes. Native agent types
are discovered at task creation, so an existing task may not see the installed roles.
Then select GPT-5.6 Sol with High reasoning for the primary session and activate Codex
Orchestration in plain language:

~~~text
Turn Orchestration on
~~~

You can also invoke `$codex-orchestration:orchestration` directly. Once active, Sol selects
Terra or Luna and does not ask for another lane authorization.

## Check and update native roles

Run this check whenever any routed worker must be trusted:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh" --check
~~~

To update the marketplace plugin and migrate exact recognized prior companion files:

~~~sh
codex plugin marketplace upgrade codex-orchestration
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
test -d "$plugin_dir"
sh "$plugin_dir/scripts/install-agents.sh"
sh "$plugin_dir/scripts/install-agents.sh" --check
sh "$plugin_dir/scripts/reinstall-plugin.sh"
sh "$plugin_dir/scripts/reinstall-plugin.sh" --check
~~~

### Upgrade from Sol Advisor 0.6.5

Add the renamed marketplace and plugin before removing the legacy installation:

~~~sh
codex plugin marketplace add jessejaffe/codex-orchestration --ref main
codex plugin add codex-orchestration@codex-orchestration
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
sh "$plugin_dir/scripts/install-agents.sh"
sh "$plugin_dir/scripts/install-agents.sh" --check
sh "$plugin_dir/scripts/reinstall-plugin.sh"
sh "$plugin_dir/scripts/reinstall-plugin.sh" --check
~~~

The reinstaller proves every required file in the complete new 0.7.0 package. It accepts
only numeric release aliases or the repository's historical `+codex.*` cachebuster
shape; arbitrary cache directories are refused and untouched. Before legacy removal,
it first runs the companion installer and proves that all seven new role files are
current without overwriting any customized legacy agent. It then copies every alias
replacement into same-filesystem transaction directories, validates the staged
packages, and retains recoverable backups. Alias activation uses renames, not
delete-then-copy updates. A persistent staging failure therefore blocks identity
removal. If activation, recovery, or final validation cannot complete after removal,
the reinstaller preserves the transaction directories and alias inventory for
inspection and recovery; it deletes them only after final validation succeeds.

The legacy plugin and marketplace are detected independently. After aliases are proven,
the reinstaller removes `sol-advisor@sol-advisor` when installed, restores every
recognized version-looking path under
`$CODEX_HOME/plugins/cache/sol-advisor/sol-advisor`, and removes the old `sol-advisor`
marketplace even when its plugin was already removed. `--check` fails if either legacy
identity remains. A successful migration therefore leaves no duplicate configured
plugin or marketplace identities.

#### Disposable real-CLI migration rehearsal

Before renaming the GitHub repository, the owning executive can rehearse an exact local
0.6.5-to-0.7.0 migration with two local checkouts. This procedure redirects every Codex,
home, XDG, and temporary path into one disposable directory; it never reads or writes
the user's real Codex configuration:

~~~sh
codex_bin="$(command -v codex)"
legacy_checkout=/absolute/path/to/sol-advisor-0.6.5
current_checkout=/absolute/path/to/codex-orchestration-0.7.0
test -x "$codex_bin"
test "$(jq -r .version "$legacy_checkout/plugins/sol-advisor/.codex-plugin/plugin.json")" = 0.6.5
test "$(jq -r .version "$current_checkout/plugins/codex-orchestration/.codex-plugin/plugin.json")" = 0.7.0

sandbox="$(mktemp -d "${TMPDIR:-/tmp}/codex-orchestration-real-cli.XXXXXX")"
export CODEX_HOME="$sandbox/codex-home"
export HOME="$sandbox/home"
export XDG_CONFIG_HOME="$sandbox/xdg-config"
export TMPDIR="$sandbox/tmp"
mkdir -p "$CODEX_HOME" "$HOME" "$XDG_CONFIG_HOME" "$TMPDIR"

"$codex_bin" plugin marketplace add "$legacy_checkout"
"$codex_bin" plugin add sol-advisor@sol-advisor
legacy_plugin_dir="$("$codex_bin" plugin list --json | jq -er '.installed[] | select(.pluginId == "sol-advisor@sol-advisor") | .source.path')"
sh "$legacy_plugin_dir/scripts/install-agents.sh"

"$codex_bin" plugin marketplace add "$current_checkout"
"$codex_bin" plugin add codex-orchestration@codex-orchestration
plugin_dir="$("$codex_bin" plugin list --json | jq -er '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
sh "$plugin_dir/scripts/install-agents.sh"
sh "$plugin_dir/scripts/install-agents.sh" --check
sh "$plugin_dir/scripts/reinstall-plugin.sh"
sh "$plugin_dir/scripts/reinstall-plugin.sh" --check

"$codex_bin" plugin list --json | jq -e '[.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration" and .version == "0.7.0")] | length == 1'
"$codex_bin" plugin list --json | jq -e '[.installed[] | select(.pluginId == "sol-advisor@sol-advisor")] | length == 0'
if "$codex_bin" plugin marketplace list --json | jq -e '.. | strings | select(. == "sol-advisor")' >/dev/null; then exit 1; fi
for alias in "$CODEX_HOME/plugins/cache/sol-advisor/sol-advisor"/*; do
  test -d "$alias"
  test ! -L "$alias"
  diff -qr "$plugin_dir" "$alias" >/dev/null
done

printf 'Disposable rehearsal retained for inspection: %s\n' "$sandbox"
# After inspecting the evidence, remove only that printed sandbox: rm -r "$sandbox"
~~~

Codex Desktop may keep a version-looking locator in a running task even though the
alias contents are current. Quit and reopen Codex Desktop when you need the displayed
locator itself to change.

Codex Orchestration uses plain release versions without SemVer `+` build metadata because Codex
can advertise a base-version skill path while retaining the full version in its cache.
All skill references resolve from the directory containing `SKILL.md`; for example, the
role contract is `skills/orchestration/references/role-contracts.md`, never
`skills/references/role-contracts.md`.

The current installer recognizes byte-exact companion templates shipped through 0.6.5,
including the historical Luna and Terra templates. It installs the seven renamed
`codex-orchestration-*` files, proves all seven exact replacements are present, and
only then removes each `sol-advisor-*` counterpart whose content matches a recognized
shipped digest. It refuses user-modified, nonregular,
or symlinked current or legacy files without partial agent-file mutation. `--check` is
non-mutating and fails until all seven renamed role files match exactly and legacy
counterparts are absent.

New persistent audit, receipt, and effectiveness state lives under
`$CODEX_HOME/state/codex-orchestration`. On first use, the scripts inspect the exact
legacy `$CODEX_HOME/state/sol-advisor` directory and copy its regular-file history
forward once. Symlinked sources or destinations and conflicting new files are refused;
new state is never overwritten. Existing automation may temporarily use these exact
compatibility fallbacks: `SOL_ADVISOR_CODEX_BIN`, `SOL_ADVISOR_USAGE_STATE_DIR`,
`SOL_ADVISOR_SESSIONS_DIR`, `SOL_ADVISOR_AUDIT_STATE_DIR`,
`SOL_ADVISOR_UPSTREAM_REPO`, and `SOL_ADVISOR_FORK_REPO`. The reinstaller additionally
accepts legacy `SOL_ADVISOR_CACHE_ROOT` and `SOL_ADVISOR_MARKETPLACE` only to locate
the old cache and marketplace being retired. All new configuration should use the
corresponding `CODEX_ORCHESTRATION_*` variables.
The native routing update was motivated by
[Eric Provencher's X post](https://x.com/pvncher/status/2083300990350954981).

Do not use a substitute agent as a shortcut. Start a fresh task after every successful
install or update so Codex discovers all seven roles.

## Native runtime routing evidence

Native spawn/details metadata is the primary source of routing evidence. It must show
the selected custom agent type. When it also exposes model and effort, the orchestrator
compares those values with the role pin. If Desktop omits model or effort and the local
rollout is accessible, use the companion inspector as the authoritative read-only
fallback for those omitted fields:

~~~sh
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "codex-orchestration@codex-orchestration") | .source.path')"
thread_id="<native-subagent-thread-id>"
sh "$plugin_dir/scripts/inspect-agent-runtime.sh" "$thread_id"
~~~

For a disposable fixture or a non-default local session root, pass it explicitly:

~~~sh
sh "$plugin_dir/scripts/inspect-agent-runtime.sh" --sessions-dir /absolute/path/to/sessions "$thread_id"
~~~

The helper searches only rollout filenames ending in that exact thread id, then emits a
single compact JSON object with allowlisted routing fields. It never prints prompts,
messages, environment variables, tokens, configuration contents, or arbitrary rollout
payloads. It refuses invalid ids, zero or multiple matches, and missing or inconsistent
role/model/effort; there is no inferred fallback. If public and local evidence both
exist, they must agree.

## How routing works

Root Sol scores the complete observed task from minimum initial evidence. Below 5.0,
Terra / High then settles requirements, architecture, and scope; at 5.0+, primary Sol
does so. The implementation ladder is Luna / Max at 1.0–2.9,
Terra / Medium at 3.0–5.0, Terra / High at 5.1–6.5, Sol / Medium at 6.6–7.9, and a
separate Sol / High implementer at 8.0–10.0. Every band uses the same complete native
worker contract with exact objective, ownership, interfaces, constraints, efficiency
boundary, verification, and structured return.

## Fork main and upstream review

Accepted changes to this maintained fork always finish on
[`jessejaffe/codex-orchestration` main](https://github.com/jessejaffe/codex-orchestration/tree/main).
A temporary `codex/*` branch may isolate work, but the same task must verify it, merge
it into fork `main`, and push `main`. The original
[`DannyMac180/sol-advisor`](https://github.com/DannyMac180/sol-advisor) repository is a
read-only upstream source and is never a push target.

The [Upstream Review workflow](.github/workflows/upstream-review.yml) runs daily at
12:17 UTC and can also be dispatched manually. It detects upstream commits not yet
represented by the latest review issue, then opens or updates an `upstream-review`
issue containing commits, changed files, and a comparison link. It has read-only
contents permission and issue-writing permission; it cannot merge or modify code.

The activation audit uses
[`daily-upstream-audit.sh`](plugins/codex-orchestration/scripts/daily-upstream-audit.sh) and a
local date marker to avoid duplicate daily network checks. When activity is pending,
Sol inspects the actual upstream diff and proposes one of three decisions for each
coherent change:

- **Adopt unchanged** when it is compatible and useful.
- **Adapt** when the idea is useful but must preserve this fork's policies.
- **Skip** when it conflicts, duplicates existing behavior, or adds no useful value.

The classification is against the fork's current implementation, not the upstream
patch in isolation. A patch for behavior the fork already provides is **Skip —
redundant**, including when upstream modifies a legacy prompt or path that this fork has
replaced. After a same-day review is resolved, `daily-upstream-audit.sh --force`
refreshes the local audit cache so later chats do not repeat the closed review.

Only the user's decision authorizes applying an upstream change.

### Native subagent lane

The owning executive selects one native implementation role for scores 1.0–10.0. The
installed roles pin Luna / Max, Terra / Medium, Terra / High, Sol / Medium, and Sol / High.
Below 5.0 the Terra executive verifies, reviews, and accepts; at 5.0+ primary Sol verifies
and a fresh Sol / High reviewer checks modifying work before acceptance.
Their schema-safe task names begin with `luna_max_`, `terra_medium_`, `terra_high_`,
`sol_medium_`, or `sol_high_`; the fresh reviewer
begins with `sol_high_review_`.

Before delegation and acceptance, the skill requires all of the following:

1. The installed role files pass the byte-for-byte companion check.
2. The native spawn tool exposes the exact selected role. Unrelated roles are not
   required; fallback tiers and the reviewer are checked only when attempted.
3. Public native spawn/details metadata identifies the selected role and, when exposed,
   its expected model and effort. If model or effort is omitted, the exact-rollout local
   inspector above must provide them instead.
4. The reviewer’s observed sandbox policy type and permission profile type are captured
   and reported.

A missing, stale, conflicting, unavailable, inconsistent, or unobservable selected
role/model/effort makes only that tier unavailable with current-turn evidence. A prior
turn's failure and an unrelated role cannot block a healthy selected worker. The owning executive then
tries the next-higher tier, never a lower one, and announces the actual route plus the
verified fallback reason before implementation. After the Sol / High implementer is
unavailable, primary Sol / High executes the settled packet directly. Native per-spawn
calls do not override role pins.

The Sol reviewer TOML requests read-only sandboxing, but the host permission profile
may broaden that request. If the observed sandbox policy type is read-only, review can
proceed with enforced isolation. If the host broadens it, review can proceed only as
behaviorally read-only when hard isolation is not required, the prompt forbids edits,
and the parent captures and verifies exact before-and-after repository/artifact state;
the broader sandbox and permission profile must be reported as residual risk. If hard
isolation is required, the sandbox cannot be observed, or any mutation occurs, stop the
review lane and do not claim enforced read-only isolation.

The owning executive inspects every diff and reruns verification. For modifying work at
5.0+, a fresh Sol reviewer returns ship, fix-first, or rethink; below 5.0 the Terra
executive performs final review itself. Codex Orchestration does not
globally reroute unrelated tasks.

Every completed task ends with the score-selected executive line—Terra / High below
5.0 or Sol / High at 5.0+, including verified fallback when applicable—and
`Implementation: <actual model / effort>`.

## Local development

Install a checkout as a local marketplace when you want Codex to use its skill:

~~~sh
cd /absolute/path/to/codex-orchestration
codex plugin marketplace add /absolute/path/to/codex-orchestration
sh plugins/codex-orchestration/scripts/reinstall-plugin.sh
sh plugins/codex-orchestration/scripts/reinstall-plugin.sh --check
~~~

Run the repository verifier separately. It uses only a disposable target directory and
never changes your Codex configuration:

~~~sh
cd /absolute/path/to/codex-orchestration
sh plugins/codex-orchestration/scripts/verify.sh
git diff --check
~~~

The installer commands below enable every score band, including Luna / Max.

To exercise the native installer itself against an explicit disposable target:

~~~sh
cd /absolute/path/to/codex-orchestration
scratch_agents="$(mktemp -d)"
sh plugins/codex-orchestration/scripts/install-agents.sh --target-dir "$scratch_agents"
sh plugins/codex-orchestration/scripts/install-agents.sh --target-dir "$scratch_agents" --check
~~~

To install this checkout's native templates for real local development, use the same
repository-relative commands without --target-dir, then begin a new task:

~~~sh
cd /absolute/path/to/codex-orchestration
sh plugins/codex-orchestration/scripts/install-agents.sh
sh plugins/codex-orchestration/scripts/install-agents.sh --check
~~~

After editing the plugin, validate both layers:

~~~sh
cd /absolute/path/to/codex-orchestration
if [ -n "$CODEX_HOME" ]; then
  codex_skills="$CODEX_HOME/skills/.system"
else
  codex_skills="$HOME/.codex/skills/.system"
fi
uv run --no-project --with pyyaml python "$codex_skills/skill-creator/scripts/quick_validate.py" plugins/codex-orchestration/skills/orchestration
uv run --no-project --with pyyaml python "$codex_skills/plugin-creator/scripts/validate_plugin.py" plugins/codex-orchestration
jq empty .agents/plugins/marketplace.json plugins/codex-orchestration/.codex-plugin/plugin.json
~~~

The verifier validates JSON and TOML, the seven exact native role pins, clean/current/
missing and idempotent installer behavior, exact legacy-agent migration, complete-package
and version-alias gates, seven-role-before-identity retirement, distinct-marketplace
enforcement, plugin/marketplace retirement, persistent-copy and preserved failed-recovery
transactions, state copy-forward and no-overwrite refusals, runtime-inspector safe fixtures,
native lane contracts, version/UI metadata,
stale-claim guards, and shell syntax. The uv commands supply the validators' PyYAML
dependency in a disposable environment. They do not install the marketplace or mutate
Codex configuration.

## License

MIT
