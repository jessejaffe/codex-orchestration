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

for command in jq python3 shasum; do
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
pass "script syntax, offline benchmark, and exact eight-role pins"

python3 "$script_dir/test-fast-dispatch.py" "$plugin_dir" "$tmp_dir/hooks" ||
  fail "fast dispatch, continuity, ownership, or latency regression"
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

grep -Fq 'zero-judgment root dispatcher' "$script_dir/prompt-router-hook.py" ||
  fail "root still owns routing analysis"
grep -Fq 'FORK_TURNS = "64"' "$script_dir/prompt-router-hook.py" ||
  fail "root-to-Terra history bound is missing"
grep -Fq 'fork_turns: \"{FORK_TURNS}\"' "$script_dir/prompt-router-hook.py" ||
  fail "root-to-Terra continuity is missing"
grep -Fq 'fork_turns: "64"' "$agents/codex-orchestration-terra-executive.toml" ||
  fail "low-band producer continuity is missing"
if rg -n 'fork_turns: (none|all)|fork_turns: \\"all\\"|Complexity: <score>|exact one-decimal score' \
  "$script_dir/prompt-router-hook.py" "$agents/codex-orchestration-terra-executive.toml"; then
  fail "runtime contract retains a rejected fork shape or numeric scoring"
fi
if rg -n 'codex_orchestration_sol_(low|medium)_implementer' "$agents/codex-orchestration-terra-executive.toml"; then
  fail "Terra can still execute or supervise a complex Sol lane"
fi
for guard in \
  'Be conservative: any' \
  'Do not inspect the repository, call task tools, design a solution, or modify anything' \
  'security or authorization judgment' \
  'irreversible data/schema changes' \
  'broad unfamiliar-repository reasoning' \
  'ESCALATE_TO_ROOT_SOL_HIGH: ROUTE=<SOL_LOW|SOL_MEDIUM|SOL_HIGH>'
do
  grep -Fq "$guard" "$agents/codex-orchestration-terra-executive.toml" ||
    fail "Terra complex-work boundary omits: $guard"
done
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
if not {"LOW", "SOL_LOW", "SOL_MEDIUM", "SOL_HIGH"}.issubset(expected):
    raise SystemExit(f"routing benchmark misses a lane: {sorted(expected)}")
PY
pass "conservative Terra ownership boundary and zero-runtime benchmark"

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
for file in install-user-hook.py orchestration_state.py prompt-router-hook.py test-fast-dispatch.py triage-cases.json; do
  grep -Fq "scripts/$file" "$script_dir/reinstall-plugin.sh" ||
    fail "reinstaller package check omits $file"
done
pass "safe companion-agent install and complete package inventory"

for phrase in \
  'once-per-prompt hook' \
  'Terra is the triage gate, not the executive for complex work' \
  '64 recent turns' \
  'never reads the offline routing benchmark' \
  'unique cache-busted version' \
  'stable user-level hook' \
  'enabled and trusted' \
  'manifest does not advertise a skill' \
  'Turn Orchestration on' \
  'Turn Orchestration off' \
  '0.8.0'
do
  grep -Fq "$phrase" "$repo_dir/README.md" || fail "README omits: $phrase"
done
if rg -n 'reads one consolidated skill|score every deliverable once|Complexity: [<0-9]|PreToolUse' \
  "$repo_dir/README.md" "$manifest"; then
  fail "stale slow-path documentation remains"
fi
pass "user-hook runtime and current documentation"

grep -Fq '17 12 * * *' "$repo_dir/.github/workflows/upstream-review.yml" ||
  fail "daily upstream review schedule changed"
if grep -Eq 'git push|gh pr merge|git cherry-pick|git rebase' "$repo_dir/.github/workflows/upstream-review.yml"; then
  fail "upstream review can mutate the fork"
fi
pass "read-only upstream review"

pass "Codex Orchestration 0.8.0 release verification complete"
