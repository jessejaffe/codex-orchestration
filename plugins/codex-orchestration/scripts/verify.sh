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
pass "script syntax, offline benchmark, and exact ten-role pins"

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
grep -Fq 'never full-history' "$script_dir/prompt-router-hook.py" ||
  fail "custom-role full-history protection is missing"
grep -Fq 'same context fork/foundation' "$script_dir/prompt-router-hook.py" ||
  fail "direct-context producer handoff is missing"
for guard in \
  'ORCHESTRATION_SCORE:' \
  'ORCHESTRATION_STATUS:' \
  'top-level commentary' \
  'interrupt every running Orchestration child' \
  'list agents' \
  'repeat until none is running' \
  'ORCHESTRATION_DELEGATE' \
  'DIRECTIVE' \
  'at most 60 words' \
  'do not' \
  'follow up before implementation' \
  'never' \
  'generate a specification or restate the request' \
  'ACCEPTANCE_CHECK:' \
  'ORCHESTRATION_ACCEPT' \
  'ORCHESTRATION_TAKEOVER' \
  'every final answer, including takeover' \
  'Executive route:' \
  'Implementation route:' \
  'Complexity:' \
  'Root appends these' \
  'never rely on executive formatting' \
  'selected root model' \
  'no more handoffs' \
  'further agent-control'
do
  grep -Fq "$guard" "$script_dir/prompt-router-hook.py" ||
    fail "root progress/interruption contract omits: $guard"
done
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
  'ORCHESTRATION_STATUS: Complexity' \
  'Return immediately with exactly two lines' \
  'at most 20 words' \
  'ORCHESTRATION_ACCEPT:' \
  'ORCHESTRATION_TAKEOVER:' \
  'Never generate an implementation' \
  'untrusted claim' \
  'task-appropriate probe' \
  'production page with cache bypass' \
  'root owns final route metadata' \
  'zero correction loops'
do
  grep -Fq "$guard" "$agents/codex-orchestration-terra-executive.toml" ||
    fail "Terra score-based routing omits: $guard"
done
for guard in \
  'root task may use any model' \
  'Never rescore, remap, or execute implementation directly' \
  'ORCHESTRATION_DELEGATE:' \
  'DIRECTIVE:' \
  'at most 60 words' \
  'Never restate the request' \
  'ORCHESTRATION_ACCEPT:' \
  'ORCHESTRATION_TAKEOVER:' \
  'untrusted claim' \
  'task-appropriate probe' \
  'production page with cache bypass' \
  'Root owns and appends final route metadata' \
  'TAKEOVER is terminal'
do
  grep -Fq "$guard" "$agents/codex-orchestration-sol-high-executive.toml" ||
    fail "pinned Sol executive omits: $guard"
done
if rg -n 'PACKET:|execution packet|exact PACKET' \
  "$script_dir/prompt-router-hook.py" \
  "$agents/codex-orchestration-terra-executive.toml" \
  "$agents/codex-orchestration-sol-high-executive.toml"; then
  fail "runtime still allows duplicated executive implementation packets"
fi
for implementer in "$agents"/*-implementer.toml; do
  grep -Fq 'Execute `USER_REQUEST`' "$implementer" ||
    fail "implementation lane does not receive original task context: $implementer"
  grep -Fq 'requested observable outcome' "$implementer" ||
    fail "implementation lane can report deployment mechanics without behavior: $implementer"
  grep -Fq 'production page with cache bypass' "$implementer" ||
    fail "frontend implementation lane lacks live rendered verification: $implementer"
  grep -Fq 'perform the implementation yourself' "$implementer" ||
    fail "implementation lane can delegate its work: $implementer"
  grep -Fq 'Do not use collaboration or agent-control' "$implementer" ||
    fail "implementation lane can use agent-control tools: $implementer"
  grep -Fq 'do not spawn, delegate to, message, wait for, list, interrupt' "$implementer" ||
    fail "implementation lane lacks complete nested-agent guard: $implementer"
  grep -Fq 'do not create Recon, reviewer, helper, or' "$implementer" ||
    fail "implementation lane can create a named helper agent: $implementer"
done
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
  5a5897ddcc8d150656591c3f9e4c0327cd38697808d7a21249b4ee7842f1ad08
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
