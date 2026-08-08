#!/bin/sh
# Repository-local release verification. Nothing here runs in a user task.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH= cd "$script_dir/.." && pwd) || exit 1
repo_dir=$(CDPATH= cd "$plugin_dir/../.." && pwd) || exit 1
manifest=$plugin_dir/.codex-plugin/plugin.json
agents=$plugin_dir/agents
installer=$script_dir/install-agents.sh

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
tmp_dir=$(mktemp -d "$tmp_base/codex-orchestration-verify.XXXXXX") || fail "cannot create temporary directory"
cleanup() {
  case "$tmp_dir" in "$tmp_base"/codex-orchestration-verify.*) rm -rf "$tmp_dir" ;; esac
}
trap cleanup 0 HUP INT TERM

for command in jq python3 rg shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required"
done

jq -e '.name == "codex-orchestration" and (.skills | not)' "$manifest" >/dev/null ||
  fail "manifest identity/version is wrong"
manifest_version=$(jq -r .version "$manifest")
printf '%s\n' "$manifest_version" | grep -Eq '^0\.8\.0\+codex\.[0-9A-Za-z._-]+$' ||
  fail "manifest lacks the required unique 0.8.0 cachebuster: $manifest_version"
if [ -d "$plugin_dir/skills" ] && find "$plugin_dir/skills" -type f -print | grep -q .; then
  fail "hook-only plugin still contains an auto-discovered skill"
fi
[ ! -e "$plugin_dir/hooks/hooks.json" ] || fail "versioned plugin still bundles a restart-sensitive prompt hook"
grep -Fq 'UserPromptSubmit' "$script_dir/install-user-hook.py" || fail "user-level prompt hook installer is missing"
pass "manifest and stable user-hook runtime topology"

for script in "$script_dir"/*.py; do
  python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$script" ||
    fail "Python syntax failed: $script"
done
for script in "$script_dir"/*.sh; do
  sh -n "$script" || fail "shell syntax failed: $script"
done
jq empty "$script_dir/triage-cases.json" || fail "triage benchmark is invalid JSON"
python3 - "$agents" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
expected = {
    "codex-orchestration-luna-implementer.toml": ("gpt-5.6-luna", "max"),
    "codex-orchestration-terra-medium-implementer.toml": ("gpt-5.6-terra", "medium"),
    "codex-orchestration-terra-executive.toml": ("gpt-5.6-terra", "high"),
    "codex-orchestration-terra-implementer.toml": ("gpt-5.6-terra", "high"),
    "codex-orchestration-sol-low-implementer.toml": ("gpt-5.6-sol", "low"),
    "codex-orchestration-sol-medium-implementer.toml": ("gpt-5.6-sol", "medium"),
    "codex-orchestration-sol-high-implementer.toml": ("gpt-5.6-sol", "high"),
    "codex-orchestration-sol-xhigh-implementer.toml": ("gpt-5.6-sol", "xhigh"),
    "codex-orchestration-sol-high-executive.toml": ("gpt-5.6-sol", "high"),
    "codex-orchestration-sol-xhigh-executive.toml": ("gpt-5.6-sol", "xhigh"),
    "codex-orchestration-sol-reviewer.toml": ("gpt-5.6-sol", "high"),
}
files = {path.name for path in root.glob("*.toml")}
if files != set(expected):
    raise SystemExit(f"wrong agent inventory: {sorted(files)}")
for filename, pins in expected.items():
    text = (root / filename).read_text(encoding="utf-8")
    values = {}
    for key in ("model", "model_reasoning_effort"):
        match = re.search(rf'^\s*{key}\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
        if match is None:
            raise SystemExit(f"missing {key} in {filename}")
        values[key] = match.group(1)
    actual = (values["model"], values["model_reasoning_effort"])
    if actual != pins:
        raise SystemExit(f"wrong pins in {filename}: {actual}")
PY
pass "script syntax, offline benchmark, and exact eleven-role pins"

python3 "$script_dir/test-fast-dispatch.py" "$plugin_dir" "$tmp_dir/hooks" ||
  fail "fast dispatch, continuity, ownership, or latency regression"
python3 "$script_dir/test-relay-protocol.py" "$plugin_dir" ||
  fail "root relay protocol regression"
python3 - "$script_dir/install-user-hook.py" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("install_user_hook", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
original = {
    "description": "existing",
    "hooks": {
        "UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": "python3 /tmp/other.py"}]}
        ],
        "Stop": [{"hooks": [{"type": "command", "command": "true"}]}],
    },
}
command = "python3 /tmp/.codex/orchestration/prompt-router-hook.py"
merged = module.merge_hook_document(original, command)
assert merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "true"
groups = merged["hooks"]["UserPromptSubmit"]
assert len(groups) == 2
assert groups[0]["hooks"][0]["command"] == "python3 /tmp/other.py"
assert groups[1]["hooks"][0]["command"] == command
again = module.merge_hook_document(merged, command)
assert again == merged
PY
python3 "$script_dir/test-effectiveness-tracker.py" "$plugin_dir" "$tmp_dir/effectiveness" ||
  fail "effectiveness tracker regression"
python3 "$script_dir/usage-receipt.py" --help >/dev/null || fail "usage receipt CLI is broken"
pass "fast-path and telemetry regression tests"

grep -Fq 'zero-judgment relay' "$script_dir/prompt-router-hook.py" ||
  fail "root still owns routing analysis"
grep -Fq 'MAX_FORK_TURNS = 64' "$script_dir/prompt-router-hook.py" ||
  fail "root-to-executive history bound is missing"
grep -Fq 'never literal `all`' "$script_dir/prompt-router-hook.py" ||
  fail "custom-role literal full-history protection is missing"
grep -Fq 'reuse fork' "$script_dir/prompt-router-hook.py" ||
  fail "direct-context producer handoff is missing"
for executive in \
  "$agents/codex-orchestration-sol-high-executive.toml" \
  "$agents/codex-orchestration-sol-xhigh-executive.toml"
do
for guard in \
  'ORCHESTRATION_STATUS:' \
  "show Terra's exact" \
  'never replace it' \
  "drain only this request's Orchestration children" \
  'inherited unfinished work stays in scope' \
  'new prompt amends it' \
  'ORCHESTRATION_DELEGATE' \
  'DIRECTIVE' \
  'at most 60 words' \
  "Keep Terra's AGENT/TASK immutable" \
  'spawn those values' \
  'do not' \
  'follow-up before implementation' \
  'reuse fork' \
  'never' \
  'specification or restate the request' \
  'ACCEPTANCE_CHECK:' \
  'Routine verification: code/tests/deployed revision' \
  'Browser/screenshots/visual handoff' \
  'Visuals only for a reported mismatch' \
  'explicit request' \
  'or indispensable work' \
  'absence never fails' \
  'ORCHESTRATION_ACCEPT' \
  'ORCHESTRATION_TAKEOVER' \
  'Every routed final ends' \
  'Executive route:' \
  'Implementation route:' \
  'Current root route from `turn_context`' \
  'On takeover add' \
  'Route takeover: Activated — __ROOT_ROUTE__' \
  'gpt-5.6-sol' \
  'xhigh' \
  'GPT-5.6 Sol' \
  'Extra High' \
  'never `GPT-5 / default effort`' \
  'Complexity:' \
  'Root appends' \
  'never rely on executive formatting' \
  'selected root model' \
  'no more handoffs' \
  'further agent-control'
do
  grep -Fq "$guard" "$script_dir/prompt-router-hook.py" ||
    fail "root progress/interruption contract omits: $guard"
done
if grep -Fq 'Show `ORCHESTRATION_SCORE:` and `ORCHESTRATION_STATUS:`' \
  "$script_dir/prompt-router-hook.py"; then
  fail "internal routing score is still exposed in commentary"
fi
if rg -n 'fork_turns: (none|all)|fork_turns: \\"all\\"|Be conservative: any|without emitting a numeric score' \
  "$script_dir/prompt-router-hook.py" "$agents/codex-orchestration-terra-executive.toml"; then
  fail "runtime contract retains a rejected fork shape or categorical routing"
fi
for guard in \
  'Rate the user request' \
  'exactly one decimal' \
  '1.0–2.9' \
  '3.0–5.0' \
  '5.1–6.5' \
  '6.6–7.2' \
  '7.3–7.9' \
  '8.0–8.9' \
  '9.0–10.0' \
  'from this chat only' \
  'routine, fully specified repository catch-up, commit, push, SSH deployment' \
  'does not by itself require Sol' \
  'ORCHESTRATION_SCORE: SCORE=' \
  'ORCHESTRATION_STATUS: <mapped visual marker> Complexity' \
  'Luna / Max: `🟡`' \
  'Terra / Medium: `🟢`' \
  'Terra / High: `🟩`' \
  'Sol / Low: `🔵`' \
  'Sol / Medium: `🟣`' \
  'Sol / High: `🟠`' \
  'Sol / Extra High: `🔴`' \
  'Return immediately with exactly two lines' \
  'at most 20 words' \
  'ORCHESTRATION_ACCEPT:' \
  'ORCHESTRATION_TAKEOVER:' \
  'Never generate an implementation' \
  'current `USER_REQUEST` adds to, corrects, answers, or authorizes unfinished inherited' \
  'combined active request is authoritative' \
  'Only explicit cancellation or replacement' \
  'untrusted claim' \
  'task-appropriate probe' \
  'hard budget of one task-tool call in total' \
  'one fallback task-tool call' \
  'malformed wrapper, command, or probe' \
  'repair it and' \
  'use one fallback task-tool call' \
  'neither is outcome failure or' \
  'reuse the producer' \
  'never put shell `${...}` in a JavaScript template literal' \
  'quoted' \
  '`cmd` string or escape every interpolation opener' \
  'requested end state already holds in every required destination' \
  'successful no-op' \
  'never require a new diff, commit, or deploy' \
  "not necessarily the change's introduction point" \
  'patch or provenance for current-tree or artifact evidence' \
  'empty, silent, or non-diagnostic result is a malformed probe' \
  'corrective REMAINING work require a named observation' \
  'no observation contradicts it, ACCEPT it' \
  'named observation proving a mistake, incomplete work, failed valid verification' \
  'do not reread source, rerun tests, rediscover infrastructure' \
  'actual deploy/config scripts' \
  'guessed port, URL, process' \
  'reached terminal exit' \
  'still-running deploy is not' \
  'deployed revision or artifact contains the change' \
  'forbidden for routine acceptance' \
  'user-reported rendered mismatch' \
  'use visual tools when available' \
  'explicitly asks for visual inspection' \
  'Missing visual evidence is never a TAKEOVER reason' \
  'view_image' \
  'root owns final route metadata' \
  'zero correction loops'
do
  grep -Fq "$guard" "$agents/codex-orchestration-terra-executive.toml" ||
    fail "Terra score-based routing omits: $guard"
done
for guard in \
  'root task may use any model' \
  "Copy Terra's AGENT and TASK" \
  'never shorten, relabel, remap' \
  'Never rescore or execute implementation directly' \
  'ORCHESTRATION_DELEGATE:' \
  'DIRECTIVE:' \
  'at most 60 words' \
  'Never restate the request' \
  'current `USER_REQUEST` adds to, corrects, answers, or authorizes unfinished inherited' \
  'combined active request is authoritative' \
  'Only explicit cancellation or replacement' \
  'ORCHESTRATION_ACCEPT:' \
  'ORCHESTRATION_TAKEOVER:' \
  'untrusted claim' \
  'task-appropriate probe' \
  'hard budget of one task-tool call in total' \
  'one fallback task-tool call' \
  'malformed wrapper, command, or probe' \
  'repair it and' \
  'use one fallback task-tool call' \
  'neither is outcome failure or' \
  'reuse the producer' \
  'never put shell `${...}` in a JavaScript template literal' \
  '`cmd` string or escape every interpolation opener' \
  'requested end state already holds in every required destination' \
  'successful no-op' \
  'never require a new diff, commit, or deploy' \
  "not necessarily the change's introduction point" \
  'patch or provenance for current-tree or artifact evidence' \
  'empty, silent, or non-diagnostic result is a malformed probe' \
  'corrective REMAINING work require a named observation' \
  'no observation contradicts it, ACCEPT it' \
  'named observation proving a mistake, incomplete work, failed valid verification' \
  'do not reread source, rerun tests, rediscover infrastructure' \
  'actual deploy/config scripts' \
  'guessed port, URL, process' \
  'reached terminal exit' \
  'still-running deploy is not' \
  'deployed revision or artifact contains the change' \
  'forbidden for routine acceptance' \
  'user-reported rendered mismatch' \
  'use visual tools when available' \
  'explicitly asks for visual inspection' \
  'Missing visual evidence is never a TAKEOVER reason' \
  'view_image' \
  'Root owns and appends final route metadata' \
  'TAKEOVER is terminal'
do
  grep -Fq "$guard" "$executive" ||
    fail "pinned Sol executive omits $guard: $executive"
done
done
if rg -n 'PACKET:|execution packet|exact PACKET' \
  "$script_dir/prompt-router-hook.py" \
  "$agents/codex-orchestration-terra-executive.toml" \
  "$agents/codex-orchestration-sol-high-executive.toml" \
  "$agents/codex-orchestration-sol-xhigh-executive.toml"; then
  fail "runtime still allows duplicated executive implementation packets"
fi
for implementer in "$agents"/*-implementer.toml; do
  grep -Fq 'Execute `USER_REQUEST`' "$implementer" ||
    fail "implementation lane does not receive original task context: $implementer"
  grep -Fq 'current `USER_REQUEST` adds to, corrects, answers, or authorizes unfinished inherited' "$implementer" ||
    fail "implementation lane can discard an additive steering turn: $implementer"
  grep -Fq 'combined active request is authoritative' "$implementer" ||
    fail "implementation lane does not preserve the cumulative active request: $implementer"
  grep -Fq 'Only explicit cancellation or replacement' "$implementer" ||
    fail "implementation lane can mistake an amendment for replacement: $implementer"
  grep -Fq 'verify the requested change in code, configuration, schema, tests' "$implementer" ||
    fail "implementation lane can skip code-first verification: $implementer"
  grep -Fq 'deployed code contains the change is sufficient' "$implementer" ||
    fail "frontend implementation lane can require rendered proof: $implementer"
  grep -Fq 'visual tools are forbidden for routine verification' "$implementer" ||
    fail "frontend implementation lane can browse by default: $implementer"
  grep -Fq 'user-reported rendered mismatch' "$implementer" ||
    fail "frontend implementation lane ignores a reported visual defect: $implementer"
  grep -Fq 'use visual tools when available' "$implementer" ||
    fail "frontend implementation lane cannot visually diagnose a reported defect: $implementer"
  grep -Fq 'explicitly asks for visual inspection' "$implementer" ||
    fail "frontend implementation lane lacks the visual opt-in boundary: $implementer"
  grep -Fq 'Missing visual evidence is never a failure or handoff condition' "$implementer" ||
    fail "frontend implementation lane can fail on absent screenshots: $implementer"
  grep -Fq 'exact cell or session' "$implementer" ||
    fail "implementation lane can abandon a running deployment: $implementer"
  grep -Fq 'terminal exit' "$implementer" ||
    fail "implementation lane can report before deployment exits: $implementer"
  grep -Fq 'exit code zero' "$implementer" ||
    fail "implementation lane can ignore a failed deployment exit: $implementer"
  grep -Fq 'Deployment is single-owner' "$implementer" ||
    fail "implementation lane can start competing deployments: $implementer"
  grep -Fq 'narrowest supported service set' "$implementer" ||
    fail "implementation lane can rebuild unrelated services: $implementer"
  grep -Fq 'second build or deploy' "$implementer" ||
    fail "implementation lane can replace a running deploy: $implementer"
  grep -Fq '`--no-cache`' "$implementer" ||
    fail "implementation lane can force an unnecessary uncached rebuild: $implementer"
  grep -Fq 'seed, migration, or backfill commands in parallel' "$implementer" ||
    fail "implementation lane can race project-managed database steps: $implementer"
  grep -Fq 'perform the implementation yourself' "$implementer" ||
    fail "implementation lane can delegate its work: $implementer"
  grep -Fq 'Do not use collaboration or agent-control' "$implementer" ||
    fail "implementation lane can use agent-control tools: $implementer"
  grep -Fq 'do not spawn, delegate to, message, wait for, list, interrupt' "$implementer" ||
    fail "implementation lane lacks complete nested-agent guard: $implementer"
  grep -Fq 'do not create Recon, reviewer, helper, or' "$implementer" ||
    fail "implementation lane can create a named helper agent: $implementer"
done
if rg -n 'VISUAL_VERIFICATION_PENDING|PRODUCER_VISUAL_EVIDENCE|PRODUCTION_VISUAL_EVIDENCE|production page with cache bypass|saved cache-bypassed payload' \
  "$script_dir/prompt-router-hook.py" "$agents"/*.toml; then
  fail "mandatory visual acceptance remains in runtime instructions"
fi
grep -Fq 'model_reasoning_effort = "xhigh"' "$agents/codex-orchestration-sol-xhigh-implementer.toml" ||
  fail "Extra High implementation role is not pinned to xhigh"
grep -Fq 'never reads the offline routing benchmark' "$repo_dir/README.md" ||
  fail "offline benchmark is not explicitly kept off the runtime path"
python3 - "$script_dir/triage-cases.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
cases = data.get("cases")
if not isinstance(cases, list) or len(cases) < 10:
    raise SystemExit("too few routing benchmark cases")
expected = {case.get("expected") for case in cases}
if not {"LOW", "SOL_LOW", "SOL_MEDIUM", "SOL_HIGH", "SOL_XHIGH"}.issubset(expected):
    raise SystemExit(f"routing benchmark misses a lane: {sorted(expected)}")
PY
pass "numeric seven-lane Terra routing and zero-runtime benchmark"

target=$tmp_dir/agents
sh "$installer" --target-dir "$target" >/dev/null || fail "fresh agent install failed"
sh "$installer" --target-dir "$target" --check >/dev/null || fail "agent check failed"
before=$(find "$target" -type f -maxdepth 1 -exec shasum -a 256 {} \; | LC_ALL=C sort)
sh "$installer" --target-dir "$target" >/dev/null || fail "idempotent agent install failed"
after=$(find "$target" -type f -maxdepth 1 -exec shasum -a 256 {} \; | LC_ALL=C sort)
[ "$before" = "$after" ] || fail "idempotent install changed role files"
printf '\n# user change\n' >> "$target/codex-orchestration-terra-executive.toml"
if sh "$installer" --target-dir "$target" >/dev/null 2>&1; then
  fail "installer overwrote a user-modified role"
fi
grep -Fq 'f679d6b97e5f537a9aeec0baf95f2267d9b42241a6e55598c191b2bf6d5f231d' "$installer" ||
  fail "0.7.4 Terra role is not recognized for safe upgrade"
grep -Fq 'd336e60b9b703f04c7bfe8aaa212818860b178c25f5b3119cbb6c87d6825e5f8' "$installer" ||
  fail "0.8.0 categorical Terra role is not recognized for safe upgrade"
grep -Fq 'd843a907029caf949049cca3a9c417aba80a4584aa0af12f1aefbec1a691af28' "$installer" ||
  fail "0.8.0 numeric Terra role is not recognized for safe upgrade"
grep -Fq '894823383b6184c3a972e4fff04ad6274dad949699bc32272b2e8f04335c0f84' "$installer" ||
  fail "0.8.0 Terra / High implementation role is not recognized for safe upgrade"
grep -Fq '31c69fe169e174d61437d1a24bc9323535494048a6c3e3b23877343f6078d389' "$installer" ||
  fail "current Terra executive role is not recognized for safe upgrade"
grep -Fq '93eec7e0d93c6db721467d5ad2f6333724625a325c0b1dcf987f1e68c28ba5fe' "$installer" ||
  fail "current Terra implementation role is not recognized for safe upgrade"
grep -Fq 'd351037408fb4297f2b9a0336d709812628dfef4dc6d3e3db76fa427ca54d64a' "$installer" ||
  fail "current Sol / High implementation role is not recognized for safe upgrade"
for digest in \
  250759da7eda6a2bde248931ee0c4f781258cc56818dad3e42c6d457a0eb4bd7 \
  6ada178902fb621b0fb58b8a7bd48ab3f4d397d9192d41dab458924921919c4b \
  43a1531815e6674a023f9f21c03635253ded90e15eae72ce69776c8f54af8fb3 \
  5a5897ddcc8d150656591c3f9e4c0327cd38697808d7a21249b4ee7842f1ad08 \
  df71d4e728f22fb4f6c690a8c4a584bb172955d98458344aedd1747862aa0a20 \
  f66ccd707d1d695e44b3709d6987cabc86f59a2a87a8ce6372c98e7decc4e2db \
  ca9c68dff9bd288a912185d67352fcae8813c38baa2a2b3202f9709a51d4b0a9 \
  d88c4e5eef3a60f3934c2d0687f4e803d1bcd3f50e4ee533ad941f24097b0842 \
  1af4d9325b7a561c0bd4b355b12b2165df80c369c0365245d2b002512c48e9ab \
  1ec3252a3798a68f29a800bec8acf59f4048b6dc4b833c0bc3fd285e42b523a9 \
  f29efa9089205993a5d1b539190041d41f0619fbc820f80759d97ae62f9d393d \
  79b9606fcc279eaf835068cda4a9e85aeabe487042dd42832b614167e75cfbcc \
  9ede0c022e578617b31c511e5967aa42b1bffc1c712697565863667205eee88e \
  dd0b95d4612b2bfb5ad6f5de2ef95956d39081ae4838810acb3d812be168cbd1 \
  0618eaaf50040154f3d09371d1c8d4d184d461ccd760a5b85041e7c215fb3c0d \
  764217265e9c4b56c4d857c56e959f604156533afeb66817667cab9b33109385 \
  6a16584960723de84f551554943af3999f4578f09db593f66d5e4c0cf9c8960b \
  4105ad6c0d0cd9af6869efff848ed5ce39370d252fd216e67153f4508df7363c \
  1ab755e223b3cf942000166e8c339223c208d73f1cce096e78a4a541bd111ce4 \
  3f68fb41c3997008075de3c6a9b4b735ee378779758b594107ea7445e0c80c36 \
  443a053164880c3a08cc4cfe07b646569895b2c016d3c5b829de1f208cc2444e \
  1d7462700700fdf8c4d8c671d56bacfc51593dc997cc0a5ec1c41e732f1e2182 \
  d32694987e8c22fea5efc2936498fb56ee160d84f4650e927e7c3ebdccc18540 \
  103029726efd75e1e322de17ae44ff64fcfe2a3ab6b661e3de9daf3d586c7677 \
  711efd898acae62727a70b22ecee159073775840e58c70e83e5d0cf2173298e9 \
  ea03a249d438d4cdacccf9d323cca3df55e63f13e84632b45f9fe53088bee2c7 \
  1994415d11c7db839d3ac337bf537b9fac145bb6db39f3f23f2705ad5bef597f \
  c9c51d1cfc4a2222b2923b7f4d7d395f5a958f9653d8e1d05074fedc0f3456eb \
  fdbea6a39f62f52f9433b0b725832ff220efecffb416b2526120d44b781a8aa1 \
  e8c702fbbd0140358c7c4a2035473b5c0d4fa3517766ad58bbed2b8da6c04068 \
  6dc11a26d3d27ece385feacef01fd1c64f69723ebfcd210b8165520059217cf5 \
  c4fe65f91579a5b8d61236eeeb5e4da6fa0d9342199db48f583cd86e97cc49b1 \
  61edbdbdfac01aedbbe45fa77e361f8a13e34d03d1d4e2b8f1f782fe0e8628a1 \
  7f848df4de7a409ef22f2a7419f5f33141a00cd73a445cecd2c824c524468069 \
  b600490a46d47642327bd964f18dd63fed8c5a17db0b7da5cf90c00ab2f8bf22 \
  f8a22b404c39d51035e88f9cd21409c91d884c3921d559cb83a4936046e876f7 \
  130f54bd67b8854971e49542dedf460c70d480502a1bdc0b326e48b1c89fe5d9 \
  ad993fd210e54300a1b937ee2fcaff672f2cf97c1184a0178711a63467c8375d \
  963e7e8b53189255db8649998a2fbe0d21ece3cf6914ddfb853bd24599d11cb5 \
  589eb68a6b5b20daee4a828ef5f80bc1190923bff8d00e5f6ed2a3d66e087244 \
  29f94c78aa84e3cd3fa4d9b47f0ee71d5db7a8dfd59cdfe5beecd96b2798f056 \
  5add5acaefe3c8ef35fa5d6a486257949cd66caa0c6fc5e07612f54913ff88d4 \
  bc7f257a0776adb3c63e591b33a065d16f1efebd9a3d83179f518cbe26bf0090 \
  c64a4788d5c7e8985d788d87cf86c0821e333fa6ff727aa61fbbf02d6020b314 \
  4c03b64fa48b0d65c2f3e7af61546046bf711c7056c1ed9a48d238f6486d9c6e \
  69ec4f11fb18e5b24d639bd706b94c4e0b8eb425aa57a8ca33a3d81061c8c586 \
  1f74f4f48092e8b343d4e6736eeb03f517f4696ba10499893f0eb016eacb4e3a \
  be1c6edf4de1d99e588a6ff9a3be5b7e3a9622dec32df38313717bc092693113 \
  7c0c3ccfc81c59e11262ca162e0adadb1d7ab5ca6c141720986d78d28da5f804 \
  dd4bacbda3ce8ae092fcf21956702f0493778db85b79cc3a035c4b8896faf7da \
  020a7aa2c885cb3b28a41134911d70f632007dd509baab5c9e799ab2e2faf5a6 \
  a1c5665569d2fa1d0b36038abae0228db185e9602acbbebdb2400fd991c6cd66 \
  b582e40b9d997fded1793d6f306c95c9dc55299d51ee44ef05b29ddd158a399b \
  8ffb06f0ac1520189f81d6dbabde710f5b3b82362d62485c4f8782665eb3a5a3 \
  b957aa28e1d9bb6fadf4683d250c7844c2942cb490cdde8e3ece3fc7b520bb04 \
  0fb3939c89c909f1a629219e536a71d9ce63a4dd5f5ca7b2e0e98588c4841d66 \
  f818d9f99a74c7411c663c32a5384e1bd7c8076d60200d696a217a8c6cdb7ab5 \
  4ef2b401095194cb3c043fbeaa8cf144bdb5549cba1c994da4e748d2af7185f6 \
  130ac3e9bfc04320547dfba1fbaf629a86feb4eb6f82d4c288b21e83da915c25 \
  d2eed98eb2a365d9cb797979bc045ca526fab94980ed8f00a62bdc66be33e784 \
  d5fdccc8037b2e4a621478fef04d50e1ea70ed8a530a4306e426700272c65d2a \
  fd504f4d5a0ffc3d4b64fa44859e0d53fafc89e35423ad7522a95d135f48ebd8 \
  70d6e82ba147d3c52fe56cfdbdc059a5428a34f39fcd5d81ccc7a6f6affc2627 \
  613dce87b620167033c528cd97a310985582d58f9ea949185db519da5fbfe51e
do
  grep -Fq "$digest" "$installer" || fail "current renamed-instruction role is not safe to upgrade: $digest"
done
for file in install-user-hook.py orchestration_state.py prompt-router-hook.py test-fast-dispatch.py test-relay-protocol.py triage-cases.json; do
  grep -Fq "scripts/$file" "$script_dir/reinstall-plugin.sh" ||
    fail "reinstaller package check omits $file"
done
pass "safe companion-agent install and complete package inventory"

for phrase in \
  'once-per-prompt hook' \
  'Terra / High scores the complete' \
  'seven implementation lanes' \
  'any user-selected starting model' \
  'Sol / Extra High' \
  'routine deployment does not force a Sol' \
  'one root-visible checkpoint' \
  'drains the entire active branch' \
  'no completed side effect is rolled back' \
  '64 recent turns' \
  'never reads the offline routing benchmark' \
  'unique cache-busted version' \
  'stable user-level hook' \
  'enabled and trusted' \
  'advertise a skill' \
  'Turn Orchestration on' \
  'Turn Orchestration off' \
  '0.8.0'
do
  grep -Fq "$phrase" "$repo_dir/README.md" || fail "README omits: $phrase"
done
if rg -n 'reads one consolidated skill|PreToolUse|conservative triage|without.*numeric' \
  "$repo_dir/README.md" "$manifest"; then
  fail "stale slow-path documentation remains"
fi
pass "user-hook runtime and current documentation"

[ ! -e "$repo_dir/.github/workflows/upstream-review.yml" ] ||
  fail "obsolete upstream-review workflow remains"
if rg -n -i 'daily-upstream-audit|upstream-review|upstream review' \
  "$script_dir" "$repo_dir/README.md" --glob '!verify.sh'; then
  fail "obsolete upstream-monitoring behavior remains"
fi
pass "no upstream-monitoring behavior"

pass "Codex Orchestration 0.8.0 numeric-routing release verification complete"
