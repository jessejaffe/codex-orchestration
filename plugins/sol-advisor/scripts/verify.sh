#!/bin/sh
# Repository-local verification for Sol Advisor's seven-role companion migration.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH= cd "$script_dir/.." && pwd) || exit 1
repo_dir=$(CDPATH= cd "$plugin_dir/../.." && pwd) || exit 1
installer=$script_dir/install-agents.sh
reinstaller=$script_dir/reinstall-plugin.sh
runtime_inspector=$script_dir/inspect-agent-runtime.sh
daily_audit=$script_dir/daily-upstream-audit.sh
usage_receipt=$script_dir/usage-receipt.py
effectiveness_tracker=$script_dir/effectiveness-tracker.py
effectiveness_test=$script_dir/test-effectiveness-tracker.py
receipt_hook=$script_dir/receipt-stop-hook.py
receipt_hook_test=$script_dir/test-receipt-hook.py
templates=$plugin_dir/agents
manifest=$plugin_dir/.codex-plugin/plugin.json
hook_config=$plugin_dir/hooks/hooks.json
skill=$plugin_dir/skills/orchestration/SKILL.md
contracts=$plugin_dir/skills/orchestration/references/role-contracts.md
receipt_contract=$plugin_dir/skills/orchestration/references/usage-receipt.md
readme=$repo_dir/README.md
ui=$plugin_dir/skills/orchestration/agents/openai.yaml
upstream_workflow=$repo_dir/.github/workflows/upstream-review.yml

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
tmp_dir=''
cleanup() {
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    case "$tmp_dir" in
      "$tmp_base"/sol-advisor-verify.*) rm -rf "$tmp_dir" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}
trap cleanup 0 HUP INT TERM
tmp_dir=$(mktemp -d "$tmp_base/sol-advisor-verify.XXXXXX") || fail "could not create disposable verification directory"

terra_medium_file=sol-advisor-terra-medium-implementer.toml
terra_executive_file=sol-advisor-terra-executive.toml
terra_file=sol-advisor-terra-implementer.toml
sol_medium_file=sol-advisor-sol-medium-implementer.toml
sol_high_file=sol-advisor-sol-high-implementer.toml
sol_file=sol-advisor-sol-reviewer.toml
luna_file=sol-advisor-luna-implementer.toml
legacy_terra_sha256=4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca
legacy_luna_sha256=fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb
previous_terra_sha256=06c318e5e93f37452635906394e6ea69fb6a65ba9e6ad7172d37b444e0dc871d

snapshot_files() {
  target=$1
  if [ ! -d "$target" ]; then
    printf '%s\n' MISSING
    return
  fi
  find "$target" -mindepth 1 -maxdepth 1 -print | LC_ALL=C sort | while IFS= read -r path; do
    if [ -L "$path" ]; then
      printf 'L %s -> %s\n' "$(basename "$path")" "$(readlink "$path")"
    elif [ -f "$path" ]; then
      shasum -a 256 "$path"
    else
      printf 'O %s\n' "$(basename "$path")"
    fi
  done
}

write_legacy_roles() {
  target=$1
  mkdir -p "$target"
  cat > "$target/$terra_file" <<'LEGACY_TERRA'
name = "sol_advisor_terra_implementer"
description = "Sol Advisor's complex implementation lane for context-heavy or higher-risk work."
model = "gpt-5.6-terra"
model_reasoning_effort = "max"

developer_instructions = """
You are Sol Advisor's complex implementation worker. Resolve difficult implementation
details within the settled architecture, including context-heavy, higher-risk, or
wider-blast-radius work. Preserve every stated interface and constraint, stay within
the owned file set, and document material judgment calls.

You are not alone in the codebase: preserve concurrent edits and do not revert
unrelated work. Surface ambiguity, scope conflicts, or verification failures rather
than changing the architecture without direction. Run the requested checks and report
actual evidence. Do not silently substitute a different role, model, or reasoning
level; this installed custom-agent profile is the required complex lane.
"""
LEGACY_TERRA
  cat > "$target/$luna_file" <<'LEGACY_LUNA'
name = "sol_advisor_luna_implementer"
description = "Sol Advisor's routine implementation lane for bounded, fully specified work."
model = "gpt-5.6-luna"
model_reasoning_effort = "max"

developer_instructions = """
You are Sol Advisor's routine implementation worker. Execute the supplied five-part
implementation specification exactly when it is bounded and largely determined by
the contract. Preserve stated interfaces and constraints, make only the files you
own, and adapt to concurrent edits instead of reverting work you do not own.

Surface material ambiguity, missing acceptance criteria, scope conflicts, or failed
verification rather than redesigning the architecture. Run the requested checks and
report actual evidence. Do not silently substitute a different role, model, or
reasoning level; this installed custom-agent profile is the required routine lane.
"""
LEGACY_LUNA
  cp "$templates/$sol_file" "$target/$sol_file"
  [ "$(shasum -a 256 "$target/$terra_file" | awk '{print $1}')" = "$legacy_terra_sha256" ] || fail "legacy Terra fixture digest drifted"
  [ "$(shasum -a 256 "$target/$luna_file" | awk '{print $1}')" = "$legacy_luna_sha256" ] || fail "legacy Luna fixture digest drifted"
}

write_previous_terra() {
  target=$1
  mkdir -p "$target"
  cat > "$target/$terra_file" <<'PREVIOUS_TERRA'
name = "sol_advisor_terra_implementer"
description = "Sol Advisor's sole implementation lane for routine and complex work."
model = "gpt-5.6-terra"
model_reasoning_effort = "high"

developer_instructions = """
You are Sol Advisor's sole implementation worker for routine, context-heavy,
higher-risk, and wider-blast-radius work. Execute the supplied five-part specification
within the settled architecture. Preserve every stated interface and constraint, stay
within the owned file set, and document material judgment calls.

You are not alone in the codebase: preserve concurrent edits and do not revert
unrelated work. Surface ambiguity, scope conflicts, or verification failures rather
than redesigning the architecture without direction. Run the requested checks and
report actual evidence. Do not silently substitute a different role, model, or
reasoning level; this installed custom-agent profile is the only implementation lane.
"""
PREVIOUS_TERRA
  [ "$(shasum -a 256 "$target/$terra_file" | awk '{print $1}')" = "$previous_terra_sha256" ] || fail "previous Terra fixture digest drifted"
}

for required in "$installer" "$reinstaller" "$runtime_inspector" "$daily_audit" "$usage_receipt" "$effectiveness_tracker" "$effectiveness_test" "$receipt_hook" "$receipt_hook_test" "$hook_config" "$manifest" "$skill" "$contracts" "$receipt_contract" "$readme" "$ui" "$upstream_workflow"; do
  test -f "$required" || fail "required file missing: $required"
done

jq empty "$manifest"
manifest_version=$(jq -r '.version' "$manifest")
[ "$manifest_version" = 0.6.5 ] || fail "manifest version is not the cache-compatible 0.6.5 release: $manifest_version"
case "$manifest_version" in *+*) fail "manifest version contains incompatible build metadata: $manifest_version" ;; esac
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'Direct Orchestration: ON for this chat and Orchestration: OFF for this chat markers' || fail "manifest does not describe Orchestration task activation state"
grep -Fq 'Scores 1.0\u20134.9 use a dedicated native GPT-5.6 Terra / High executive' "$manifest" || fail "manifest does not describe low-band Terra executive"
grep -Fq 'Scores 5.0\u201310.0 retain primary GPT-5.6 Sol / High executive ownership' "$manifest" || fail "manifest does not describe high-band Sol executive"
grep -Fqi 'GPT-5.6 Luna' "$manifest" || fail "manifest does not describe Luna routing"
grep -Fq 'native GPT-5.6 Luna / Max' "$manifest" || fail "manifest does not describe native Luna routing"
grep -Fq 'unchanged three-line weekly savings receipt' "$manifest" || fail "manifest does not describe the savings receipt"
grep -Fq 'Current-turn preflight checks only attempted roles' "$manifest" || fail "manifest does not describe tier-specific preflight"
grep -Fq 'persists that immutable one-decimal score' "$manifest" || fail "manifest does not require deterministic complexity persistence"
grep -Fq 'persisted complexity' "$manifest" || fail "manifest does not describe persisted complexity"
grep -Fq 'Completed tasks show the actual executive' "$manifest" || fail "manifest does not describe receipt completion output"
grep -Fq 'Every descendant thread is registered' "$manifest" || fail "manifest does not describe descendant receipt tracking"
grep -Fq 'turn_aborted work is excluded' "$manifest" || fail "manifest does not exclude interrupted tasks"
grep -Fq 'fresh Sol' "$manifest" || fail "manifest does not preserve native fresh Sol review"
pass "manifest JSON, version, executive bands, and five producer bands"

python3 - "$templates" <<'PY'
from pathlib import Path
import sys, tomllib

root = Path(sys.argv[1])
expected = {
    "sol-advisor-luna-implementer.toml": {
        "name": "sol_advisor_luna_implementer",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "max",
    },
    "sol-advisor-terra-medium-implementer.toml": {
        "name": "sol_advisor_terra_medium_implementer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
    },
    "sol-advisor-terra-executive.toml": {
        "name": "sol_advisor_terra_executive",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "high",
    },
    "sol-advisor-terra-implementer.toml": {
        "name": "sol_advisor_terra_implementer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "high",
    },
    "sol-advisor-sol-medium-implementer.toml": {
        "name": "sol_advisor_sol_medium_implementer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "medium",
    },
    "sol-advisor-sol-high-implementer.toml": {
        "name": "sol_advisor_sol_high_implementer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "high",
    },
    "sol-advisor-sol-reviewer.toml": {
        "name": "sol_advisor_sol_reviewer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
}
actual = {path.name for path in root.glob("*.toml")}
if actual != set(expected):
    raise SystemExit(f"expected exactly {sorted(expected)}, found {sorted(actual)}")
for filename, pins in expected.items():
    data = tomllib.loads((root / filename).read_text(encoding="utf-8"))
    for field in ("name", "description", "developer_instructions"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise SystemExit(f"{filename}: missing {field}")
    for field, value in pins.items():
        if data.get(field) != value:
            raise SystemExit(f"{filename}: {field}={data.get(field)!r}, expected {value!r}")
print("seven exact role pins are valid")
PY
pass "exact seven-role TOML inventory"

grep -Fq "legacy_terra_sha256=$legacy_terra_sha256" "$installer" || fail "installer legacy Terra digest mismatch"
grep -Fq "legacy_luna_sha256=$legacy_luna_sha256" "$installer" || fail "installer legacy Luna digest mismatch"
grep -Fq "previous_terra_sha256=$previous_terra_sha256" "$installer" || fail "installer previous Terra digest mismatch"
pass "immutable v0.2.0 migration fingerprints"

reinstall_cache=$tmp_dir/reinstall-cache
old_build=0.5.1+codex.20260804022121
mkdir -p "$reinstall_cache/$old_build/skills/orchestration"
printf '%s\n' preserved-open-task-skill > "$reinstall_cache/$old_build/skills/orchestration/SKILL.md"
fake_codex=$tmp_dir/fake-codex
fake_state=$tmp_dir/fake-codex-version
printf '%s\n' "$old_build" > "$fake_state"
cat > "$fake_codex" <<'FAKE_CODEX'
#!/bin/sh
set -eu
if [ "${1:-}" = plugin ] && [ "${2:-}" = list ] && [ "${3:-}" = --json ]; then
  version=$(cat "$SOL_ADVISOR_TEST_STATE")
  printf '{"installed":[{"pluginId":"sol-advisor@sol-advisor","version":"%s"}]}\n' "$version"
  exit 0
fi
if [ "${1:-}" = plugin ] && [ "${2:-}" = add ] && [ "${3:-}" = sol-advisor@sol-advisor ]; then
  rm -rf "$SOL_ADVISOR_CACHE_ROOT"
  current=$(jq -r .version "$SOL_ADVISOR_TEST_MANIFEST")
  current_dir=$SOL_ADVISOR_CACHE_ROOT/$current
  mkdir -p "$current_dir"
  cp -Rp "$SOL_ADVISOR_TEST_PLUGIN"/. "$current_dir"
  printf '%s\n' "$current" > "$SOL_ADVISOR_TEST_STATE"
  exit 0
fi
exit 64
FAKE_CODEX
chmod +x "$fake_codex"
SOL_ADVISOR_CODEX_BIN="$fake_codex" \
SOL_ADVISOR_CACHE_ROOT="$reinstall_cache" \
SOL_ADVISOR_TEST_STATE="$fake_state" \
SOL_ADVISOR_TEST_MANIFEST="$manifest" \
SOL_ADVISOR_TEST_PLUGIN="$plugin_dir" \
  sh "$reinstaller"
test -f "$reinstall_cache/$manifest_version/skills/orchestration/SKILL.md" || fail "reinstaller lost the current skill cache"
cmp -s "$skill" "$reinstall_cache/$old_build/skills/orchestration/SKILL.md" || fail "reinstaller left the full-version cache alias stale"
cmp -s "$skill" "$reinstall_cache/0.5.1/skills/orchestration/SKILL.md" || fail "reinstaller left the base-version cache alias stale"
if grep -Fq preserved-open-task-skill "$reinstall_cache/$old_build/skills/orchestration/SKILL.md"; then
  fail "reinstaller preserved stale skill contents"
fi
SOL_ADVISOR_CODEX_BIN="$fake_codex" \
SOL_ADVISOR_CACHE_ROOT="$reinstall_cache" \
SOL_ADVISOR_TEST_STATE="$fake_state" \
  sh "$reinstaller" --check
pass "cache-compatible reinstall and stale desktop-path refresh"

clean_target=$tmp_dir/clean
sh "$installer" --target-dir "$clean_target"
cmp -s "$templates/$luna_file" "$clean_target/$luna_file" || fail "clean Luna/Max install mismatch"
cmp -s "$templates/$terra_medium_file" "$clean_target/$terra_medium_file" || fail "clean Terra/Medium install mismatch"
cmp -s "$templates/$terra_executive_file" "$clean_target/$terra_executive_file" || fail "clean Terra executive install mismatch"
cmp -s "$templates/$terra_file" "$clean_target/$terra_file" || fail "clean Terra install mismatch"
cmp -s "$templates/$sol_medium_file" "$clean_target/$sol_medium_file" || fail "clean Sol/Medium install mismatch"
cmp -s "$templates/$sol_high_file" "$clean_target/$sol_high_file" || fail "clean Sol/High implementer install mismatch"
cmp -s "$templates/$sol_file" "$clean_target/$sol_file" || fail "clean Sol install mismatch"
sh "$installer" --target-dir "$clean_target" --check
before=$(snapshot_files "$clean_target")
sh "$installer" --target-dir "$clean_target"
after=$(snapshot_files "$clean_target")
[ "$before" = "$after" ] || fail "idempotent install changed current roles"
pass "clean install, exact check, and idempotence"

missing_target=$tmp_dir/missing
if sh "$installer" --target-dir "$missing_target" --check; then fail "--check accepted missing target"; fi
test ! -e "$missing_target" || fail "--check mutated missing target"
pass "missing-target check refusal is non-mutating"

codex_home=$tmp_dir/codex-home
CODEX_HOME="$codex_home" sh "$installer"
cmp -s "$templates/$luna_file" "$codex_home/agents/$luna_file" || fail "CODEX_HOME Luna/Max mismatch"
cmp -s "$templates/$terra_medium_file" "$codex_home/agents/$terra_medium_file" || fail "CODEX_HOME Terra/Medium mismatch"
cmp -s "$templates/$terra_executive_file" "$codex_home/agents/$terra_executive_file" || fail "CODEX_HOME Terra executive mismatch"
cmp -s "$templates/$terra_file" "$codex_home/agents/$terra_file" || fail "CODEX_HOME Terra mismatch"
cmp -s "$templates/$sol_medium_file" "$codex_home/agents/$sol_medium_file" || fail "CODEX_HOME Sol/Medium mismatch"
cmp -s "$templates/$sol_high_file" "$codex_home/agents/$sol_high_file" || fail "CODEX_HOME Sol/High implementer mismatch"
cmp -s "$templates/$sol_file" "$codex_home/agents/$sol_file" || fail "CODEX_HOME Sol mismatch"
test ! -e "$codex_home/config.toml" || fail "installer created config.toml"
relative_parent=$tmp_dir/relative-parent
mkdir "$relative_parent"
(cd "$relative_parent" && sh "$installer" --target-dir relative-agents)
cmp -s "$templates/$luna_file" "$relative_parent/relative-agents/$luna_file" || fail "relative target Luna/Max mismatch"
cmp -s "$templates/$terra_medium_file" "$relative_parent/relative-agents/$terra_medium_file" || fail "relative target Terra/Medium mismatch"
cmp -s "$templates/$terra_executive_file" "$relative_parent/relative-agents/$terra_executive_file" || fail "relative target Terra executive mismatch"
cmp -s "$templates/$terra_file" "$relative_parent/relative-agents/$terra_file" || fail "relative target Terra mismatch"
pass "CODEX_HOME and relative target behavior"

migration_target=$tmp_dir/migration
write_legacy_roles "$migration_target"
sh "$installer" --target-dir "$migration_target"
cmp -s "$templates/$luna_file" "$migration_target/$luna_file" || fail "legacy Luna was not migrated"
cmp -s "$templates/$terra_medium_file" "$migration_target/$terra_medium_file" || fail "Terra/Medium was not added during migration"
cmp -s "$templates/$terra_executive_file" "$migration_target/$terra_executive_file" || fail "Terra executive was not added during migration"
cmp -s "$templates/$terra_file" "$migration_target/$terra_file" || fail "legacy Terra was not migrated"
cmp -s "$templates/$sol_medium_file" "$migration_target/$sol_medium_file" || fail "Sol/Medium was not added during migration"
cmp -s "$templates/$sol_high_file" "$migration_target/$sol_high_file" || fail "Sol/High implementer was not added during migration"
cmp -s "$templates/$sol_file" "$migration_target/$sol_file" || fail "Sol changed during migration"
sh "$installer" --target-dir "$migration_target" --check
pass "exact v0.2.0 Terra and Luna replacement"

previous_target=$tmp_dir/previous-terra
write_previous_terra "$previous_target"
cp "$templates/$sol_file" "$previous_target/$sol_file"
sh "$installer" --target-dir "$previous_target"
cmp -s "$templates/$luna_file" "$previous_target/$luna_file" || fail "Luna/Max was not added during previous-template migration"
cmp -s "$templates/$terra_medium_file" "$previous_target/$terra_medium_file" || fail "Terra/Medium was not added during previous-template migration"
cmp -s "$templates/$terra_executive_file" "$previous_target/$terra_executive_file" || fail "Terra executive was not added during previous-template migration"
cmp -s "$templates/$terra_file" "$previous_target/$terra_file" || fail "previous Terra was not migrated"
cmp -s "$templates/$sol_medium_file" "$previous_target/$sol_medium_file" || fail "Sol/Medium was not added during previous-template migration"
cmp -s "$templates/$sol_high_file" "$previous_target/$sol_high_file" || fail "Sol/High implementer was not added during previous-template migration"
cmp -s "$templates/$sol_file" "$previous_target/$sol_file" || fail "previous-template migration changed Sol"
sh "$installer" --target-dir "$previous_target" --check
pass "exact previous Terra upgrade migration"

modified_luna=$tmp_dir/modified-luna
write_legacy_roles "$modified_luna"
printf '%s\n' modified >> "$modified_luna/$luna_file"
before=$(snapshot_files "$modified_luna")
if sh "$installer" --target-dir "$modified_luna"; then fail "installer replaced modified Luna"; fi
after=$(snapshot_files "$modified_luna")
[ "$before" = "$after" ] || fail "modified-Luna refusal partially mutated target"
pass "modified Luna refusal with zero partial mutation"

modified_terra=$tmp_dir/modified-terra
write_legacy_roles "$modified_terra"
printf '%s\n' modified >> "$modified_terra/$terra_file"
before=$(snapshot_files "$modified_terra")
if sh "$installer" --target-dir "$modified_terra"; then fail "installer replaced modified Terra"; fi
after=$(snapshot_files "$modified_terra")
[ "$before" = "$after" ] || fail "modified-Terra refusal partially mutated target"
pass "modified Terra refusal with zero partial mutation"

stale_luna=$tmp_dir/stale-luna
sh "$installer" --target-dir "$stale_luna"
stale_fixture=$tmp_dir/stale-fixture
write_legacy_roles "$stale_fixture"
cp "$stale_fixture/$luna_file" "$stale_luna/$luna_file"
before=$(snapshot_files "$stale_luna")
if sh "$installer" --target-dir "$stale_luna" --check; then fail "--check accepted stale Luna"; fi
after=$(snapshot_files "$stale_luna")
[ "$before" = "$after" ] || fail "stale-Luna check mutated target"
pass "stale Luna check refusal is non-mutating"

unsafe=$tmp_dir/unsafe
mkdir "$unsafe"
ln -s "$templates/$terra_file" "$unsafe/$terra_file"
before=$(snapshot_files "$unsafe")
if sh "$installer" --target-dir "$unsafe"; then fail "installer accepted symlinked Terra"; fi
after=$(snapshot_files "$unsafe")
[ "$before" = "$after" ] || fail "symlink refusal partially mutated target"
test ! -e "$unsafe/$sol_file" || fail "symlink refusal partially installed Sol"
test ! -e "$unsafe/$luna_file" || fail "symlink refusal partially installed Luna/Max"
test ! -e "$unsafe/$terra_medium_file" || fail "symlink refusal partially installed Terra/Medium"
test ! -e "$unsafe/$terra_executive_file" || fail "symlink refusal partially installed Terra executive"
test ! -e "$unsafe/$sol_medium_file" || fail "symlink refusal partially installed Sol/Medium"
test ! -e "$unsafe/$sol_high_file" || fail "symlink refusal partially installed Sol/High implementer"
pass "unsafe destination refusal with zero partial mutation"

runtime_sessions=$tmp_dir/runtime-sessions
runtime_day=$runtime_sessions/2026/08/02
mkdir -p "$runtime_day"
runtime_id=11111111-1111-7111-8111-111111111111
runtime_rollout=$runtime_day/rollout-2026-08-02T00-00-00-$runtime_id.jsonl
printf '%s\n' \
  '{"type":"response_item","payload":{"prompt":"DO_NOT_LEAK_PROMPT"}}' \
  "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$runtime_id\",\"parent_thread_id\":\"00000000-0000-7000-8000-000000000000\",\"agent_role\":\"sol_advisor_terra_implementer\",\"agent_path\":\"/root/fixture\",\"model_provider\":\"openai\",\"cwd\":\"/fixture\"}}" \
  '{"type":"turn_context","payload":{"model":"gpt-5.6-terra","effort":"high","sandbox_policy":{"type":"danger-full-access"},"permission_profile":{"type":"disabled"},"cwd":"/fixture"}}' \
  > "$runtime_rollout"
runtime_output=$(sh "$runtime_inspector" --sessions-dir "$runtime_sessions" "$runtime_id")
printf '%s\n' "$runtime_output" | jq -e --arg id "$runtime_id" '
  .thread_id == $id and .agent_role == "sol_advisor_terra_implementer"
  and .model == "gpt-5.6-terra" and .effort == "high"
  and .sandbox_policy_type == "danger-full-access"
  and .permission_profile_type == "disabled"
' >/dev/null || fail "runtime inspector returned wrong Terra/High evidence"
if printf '%s\n' "$runtime_output" | grep -Fq DO_NOT_LEAK; then fail "runtime inspector leaked payload"; fi
if sh "$runtime_inspector" --sessions-dir "$runtime_sessions" invalid >/dev/null 2>&1; then fail "runtime inspector accepted invalid id"; fi
zero_id=22222222-2222-7222-8222-222222222222
if sh "$runtime_inspector" --sessions-dir "$runtime_sessions" "$zero_id" >/dev/null 2>&1; then fail "runtime inspector accepted zero matches"; fi
pass "runtime inspector Terra/High routing and safe refusal"

for document in "$skill" "$contracts"; do
  grep -Fq 'agent_type: sol_advisor_terra_executive' "$document" || fail "missing Terra/High executive spawn in $document"
  grep -Fq 'agent_type: sol_advisor_luna_implementer' "$document" || fail "missing Luna/Max spawn in $document"
  grep -Fq 'agent_type: sol_advisor_terra_medium_implementer' "$document" || fail "missing Terra/Medium spawn in $document"
  grep -Fq 'agent_type: sol_advisor_terra_implementer' "$document" || fail "missing Terra/High spawn in $document"
  grep -Fq 'agent_type: sol_advisor_sol_medium_implementer' "$document" || fail "missing Sol/Medium spawn in $document"
  grep -Fq 'agent_type: sol_advisor_sol_high_implementer' "$document" || fail "missing Sol/High implementer spawn in $document"
  grep -Fq 'agent_type: sol_advisor_sol_reviewer' "$document" || fail "missing Sol spawn in $document"
  grep -Fq 'fork_turns: none' "$document" || fail "missing fresh context in $document"
  grep -Fq 'task_name: luna_max_<objective_slug>' "$document" || fail "missing Luna Max visible task prefix in $document"
  grep -Fq 'task_name: terra_medium_<objective_slug>' "$document" || fail "missing Terra Medium visible task prefix in $document"
  grep -Fq 'task_name: terra_high_<objective_slug>' "$document" || fail "missing Terra High visible task prefix in $document"
  grep -Fq 'task_name: terra_high_exec_<objective_slug>' "$document" || fail "missing Terra High executive task prefix in $document"
  grep -Fq 'task_name: sol_medium_<objective_slug>' "$document" || fail "missing Sol Medium visible task prefix in $document"
  grep -Fq 'task_name: sol_high_<objective_slug>' "$document" || fail "missing Sol High visible task prefix in $document"
  grep -Fq 'task_name: sol_high_review_<objective_slug>' "$document" || fail "missing Sol High reviewer task prefix in $document"
  if grep -Eq 'agent_type:.*terra_max' "$document"; then fail "retired implementation spawn remains in $document"; fi
  if grep -Eq '^[[:space:]]*(model|reasoning_effort):' "$document"; then fail "per-spawn override remains in $document"; fi
done
grep -Fq '../../scripts/install-agents.sh' "$skill" || fail "skill does not resolve installer relatively"
grep -Fq '../../scripts/reinstall-plugin.sh' "$skill" || fail "skill does not resolve safe reinstaller relatively"
grep -Fq '../../scripts/inspect-agent-runtime.sh' "$skill" || fail "skill does not resolve inspector relatively"
grep -Fqi 'public native spawn/details metadata first' "$skill" || fail "skill lacks public-details-first evidence rule"
grep -Fqi 'parent captures and verifies exact before-and-after' "$contracts" || fail "contracts lack behavioral read-only state check"
grep -Fq 'exact type for the tier being attempted' "$skill" || fail "skill still requires unrelated worker types"
grep -Fq 'An unrelated role failure cannot' "$skill" || fail "skill lets unrelated roles block selected tier"
grep -Fq 'Never reuse a prior turn' "$skill" || fail "skill permits stale preflight reuse"
grep -Fq 'Never reuse a prior-turn failure' "$contracts" || fail "contracts permit stale preflight reuse"
grep -Fq 'Never print that candidate as `Implementation:`' "$skill" || fail "skill permits preflight after route announcement"
grep -Fq 'Complexity: <score>/10' "$skill" || fail "skill omits the visible numeric complexity score"
grep -Fq 'score to one decimal place' "$skill" || fail "skill does not standardize visible complexity precision"
grep -Fq 'complexity score itself is always visible' "$skill" || fail "skill permits hiding the complexity score"
grep -Fq 'PreToolUse gate independently requires and persists' "$skill" || fail "skill does not persist complexity before work"
grep -Fq 'Once persisted, never revise the score' "$skill" || fail "skill permits complexity drift after routing"
grep -Fq 'effectiveness-tracker.py' "$skill" || fail "skill omits the effectiveness tracker"
grep -Fq 'exact root-and-delegated token usage' "$skill" || fail "skill omits exact per-task tokens"
grep -Fq 'Do not request, infer, or divide by a Profile chat count' "$skill" || fail "skill makes chat count the primary denominator"
grep -Fq 'skill_dir/references/role-contracts.md' "$skill" || fail "skill does not pin role-contract resolution to the skill directory"
grep -Fq 'do not drop the' "$skill" || fail "skill does not guard the observed orchestration-path resolution failure"
grep -Fq 'directory name is not the loaded release identity' "$skill" || fail "skill mistakes a compatibility alias name for release identity"
grep -Fq 'incomplete plugin cache alias is missing' "$reinstaller" || fail "reinstaller does not reject incomplete aliases"
grep -Fq 'may display an older compatibility-path name until the app restarts' "$reinstaller" || fail "reinstaller hides the Desktop locator cache boundary"
for tool in list_projects list_threads create_thread wait_threads read_thread send_message_to_thread clientThreadId; do
  if rg -n "$tool" "$skill" "$contracts" "$readme" "$manifest"; then
    fail "retired Luna app-task tool remains: $tool"
  fi
done
grep -Fq 'model = "gpt-5.6-luna"' "$templates/$luna_file" || fail "Luna role omits Luna model pin"
grep -Fq 'model_reasoning_effort = "max"' "$templates/$luna_file" || fail "Luna role omits Max effort pin"
grep -Fq '| Native Luna / Max |' "$readme" || fail "README omits native Luna routing"
grep -Fq 'the seven exact native role pins' "$readme" || fail "README does not describe the seven-role inventory"
grep -Fq '| `Luna Max` |' "$readme" || fail "README omits Luna Max label"
grep -Fq '| `Terra Medium` |' "$readme" || fail "README omits Terra Medium label"
grep -Fq '| `Terra High` |' "$readme" || fail "README omits Terra High label"
grep -Fq '| `Sol Medium` |' "$readme" || fail "README omits Sol Medium label"
grep -Fq '| `Sol High` |' "$readme" || fail "README omits Sol High label"
for command in 'Turn Orchestration on' 'Use Orchestration' 'Use Orchestration for this chat'; do
  grep -Fq "$command" "$readme" || fail "README omits plain-language activation: $command"
done
grep -Fq 'Turn Orchestration off' "$readme" || fail "README omits plain-language deactivation"
grep -Fq 'Orchestration: ON for this chat' "$readme" || fail "README omits ON state marker"
grep -Fq 'Orchestration: OFF for this chat' "$readme" || fail "README omits OFF state marker"
grep -Fq 'every later request in' "$readme" || fail "README omits persistent chat activation"
grep -Fq 'Every new chat starts off' "$readme" || fail "README permits cross-chat activation"
grep -Fq 'allow_implicit_invocation: true' "$ui" || fail "skill UI blocks plain-language activation"
grep -Fq 'does not ask for another lane authorization' "$readme" || fail "README requires separate worker authorization"
grep -Fq 'without separate task or model authorization' "$manifest" || fail "manifest requires separate Luna authorization"
for label in 'Luna / Max' 'Terra / Medium' 'Terra / High' 'Sol / Medium' 'Sol / High'; do
  jq -r '.interface.longDescription' "$manifest" | grep -Fq "$label" || fail "manifest UI omits model route: $label"
done
grep -Fq 'Turn Orchestration on' "$ui" || fail "skill UI omits plain-language activation"
grep -Fq 'Luna Max, Terra Medium, Terra High, Sol Medium, and Sol High' "$ui" || fail "skill UI omits visible model labels"
grep -Fq 'Terra High executive ownership below 5.0' "$ui" || fail "skill UI omits low-band Terra executive"
for command in 'Turn Orchestration on' 'Use Orchestration' 'Use Orchestration for this chat'; do
  grep -Fq "$command" "$skill" || fail "skill omits plain-language activation: $command"
done
grep -Fq 'Turn Orchestration off' "$skill" || fail "skill omits the off switch"
grep -Fq 'Every later user request' "$skill" || fail "skill omits persistent activation"
grep -Fq 'Use only direct assistant messages in the current chat' "$skill" || fail "skill accepts non-chat state markers"
grep -Fq 'The latest current-chat marker wins' "$skill" || fail "skill does not define chat-local ON/OFF precedence"
grep -Fq 'Every new chat starts off' "$skill" || fail "skill permits cross-chat activation"
grep -Fq 'plugin remains selected or enabled' "$skill" || fail "skill treats plugin state as activation"
grep -Fq 'memory, a summary, or any' "$skill" || fail "skill permits remembered cross-chat activation"
grep -Fq 'stay OFF and handle the' "$skill" || fail "skill lacks inactive behavior"
grep -Fq 'Orchestration: ON for this chat' "$skill" || fail "skill omits initial ON acknowledgement"
grep -Fq 'Orchestration: OFF for this chat' "$skill" || fail "skill omits OFF acknowledgement"
for stale_command in 'Turn Sol Advisor on' 'Turn Sol Advisor off' 'Use Sol Advisor' 'Sol Advisor: ON' 'Sol Advisor: OFF'; do
  if rg -Fq "$stale_command" "$readme" "$skill" "$ui" "$manifest"; then
    fail "stale Sol Advisor plain-language control remains: $stale_command"
  fi
done
grep -Fq 'Executive design and review: GPT-5.6 Sol / High' "$skill" || fail "skill omits concise executive model line"
grep -Fq 'Executive design and review: GPT-5.6 Terra / High' "$skill" || fail "skill omits low-band executive model line"
grep -Fq 'Terra executive fallback:' "$skill" || fail "skill omits stable executive fallback syntax"
grep -Fq 'For scores 1.0–4.9, start with the' "$skill" || fail "skill does not start low-band work with the Terra executive"
if grep -Fq 'Start every scored task with its mapped producer' "$skill"; then
  fail "skill bypasses the low-band Terra executive"
fi
grep -Fq 'The owning executive must inspect the evidence or diff' "$contracts" || fail "contracts assign verification to the primary instead of the owning executive"
grep -Fq 'after handoff, the Terra executive owns all' "$contracts" || fail "contracts omit low-band post-handoff checkpoint ownership"
grep -Fq 'Before the low-band executive handoff, root Sol records route-level checkpoints' "$readme" || fail "README omits root's minimum-evidence handoff checkpoint"
grep -Fq 'these post-handoff checkpoints belong to the Terra executive' "$readme" || fail "README omits low-band checkpoint ownership"
if grep -Fq 'Before delegation, external access, or scope expansion, Sol records three checkpoints' "$readme"; then
  fail "README assigns all checkpoints to Sol"
fi
grep -Fq 'Escalate to the owning executive before broadening scope' "$contracts" || fail "contracts route producer escalation to primary Sol"
grep -Fq "owning executive's replanned route" "$contracts" || fail "contracts route budget replanning to primary Sol"
if grep -Fq 'Escalate to primary Sol before broadening scope' "$contracts" || grep -Fq "primary's replanned route" "$contracts"; then
  fail "contracts contain stale primary-Sol producer escalation"
fi
grep -Fq 'triggers a new owning-executive' "$skill" || fail "skill routes budget checkpoints away from the owning executive"
grep -Fq 'returns control to the owning executive for a fresh specification decision' "$skill" || fail "skill routes adherence escalation away from the owning executive"
if grep -Fq 'triggers a new Sol decision' "$skill" || grep -Fq 'returns control to primary Sol for a fresh route decision' "$skill"; then
  fail "skill contains stale primary-Sol budget or adherence escalation"
fi
grep -Fq 'Below 5.0, the Terra executive performs final review itself' "$readme" || fail "README omits low-band Terra self-review"
grep -Fq 'For modifying work at' "$readme" && grep -Fq 'a fresh Sol / High reviewer checks primary Sol' "$readme" || fail "README omits conditional high-band fresh Sol review"
if grep -Fq "Sol reviews Sol's orchestration with a fresh context" "$readme"; then
  fail "README contains unconditional Sol-final-review wording"
fi
grep -Fq 'At exactly' "$skill" && grep -Fq '5.0 the producer remains Terra / Medium while the executive is Sol / High' "$skill" || fail "skill omits the 5.0 executive boundary"
grep -Fq 'Immediately after every descendant spawn' "$skill" || fail "skill omits low-executive descendant registration"
grep -Fq 'root thread ID, resolved receipt-helper path' "$skill" || fail "skill omits root receipt handoff identity"
grep -Fq 'register and monitor the Terra executive itself' "$skill" || fail "skill assigns descendant registration to root Sol"
grep -Fq 'register, and monitor its own descendants against' "$skill" || fail "skill omits Terra executive descendant ownership"
grep -Fq 'emit the same exact three-line route in its own session' "$skill" || fail "skill does not authorize nested producer hooks"
grep -Fq 'add-thread <descendant-id> --root-thread-id <root-thread-id>' "$skill" || fail "skill omits explicit root descendant registration"
grep -Fq 'recovery' "$contracts" && grep -Fq 'recursion is not a substitute' "$contracts" || fail "contracts permit recovery to replace normal registration"
grep -Fq 'normal finish omitted or mispriced a nested descendant' "$receipt_hook_test" || fail "hook fixture does not test normal nested receipt finish"
grep -Fq 'delegated Terra executive Stop required a separate receipt' "$receipt_hook_test" || fail "hook fixture omits delegated executive Stop suppression"
grep -Fq 'sole completion was not the root task' "$receipt_hook_test" || fail "hook fixture does not assert one root completion"
grep -Fq 'root low route directly spawned a producer before its executive' "$receipt_hook_test" || fail "hook fixture omits root-first executive enforcement"
grep -Fq 'valid Terra-to-Sol executive fallback was denied' "$receipt_hook_test" || fail "hook fixture omits monotonic fallback acceptance"
grep -Fq 'malformed executive fallback was accepted' "$receipt_hook_test" || fail "hook fixture omits malformed fallback denial"
grep -Fq 'fallback route moved downward to Terra' "$receipt_hook_test" || fail "hook fixture omits downward transition denial"
grep -Fq 'Stop did not reconstruct the persisted fallback' "$receipt_hook_test" || fail "hook fixture omits persisted fallback reconstruction"
grep -Fq 'session_role(transcript) == "sol_advisor_terra_executive"' "$receipt_hook" || fail "Stop hook does not identify delegated Terra executive"
grep -Fq 'performs final review itself' "$skill" || fail "skill adds routine Sol review to the low route"
grep -Fq 'Implementation:' "$skill" || fail "skill omits pre-execution route announcement"
grep -Fq 'Do not ask for separate worker or model authorization' "$skill" || fail "skill requires a second worker authorization"
grep -Fq '../../scripts/daily-upstream-audit.sh' "$skill" || fail "skill omits daily upstream audit"
if rg -n 'SOL ADVISOR ROUTING' "$skill" "$contracts" "$readme" "$manifest" "$ui"; then
  fail "retired verbose routing output remains"
fi
test ! -e "$plugin_dir/skills/orchestration/references/luna-task-lane.md" || fail "retired Luna task contract remains"
grep -Fq 'references/usage-receipt.md' "$skill" || fail "skill omits weekly usage receipt"
grep -Fq 'Actual weekly usage:' "$receipt_contract" || fail "usage receipt omits actual weekly usage"
grep -Fq 'All-Sol equivalent:' "$receipt_contract" || fail "usage receipt omits all-Sol equivalent"
grep -Fq 'Estimated routing savings:' "$receipt_contract" || fail "usage receipt omits routing savings"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$usage_receipt" || fail "usage receipt script does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$effectiveness_tracker" || fail "effectiveness tracker does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$effectiveness_test" || fail "effectiveness tracker test does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$receipt_hook" || fail "receipt Stop hook does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$receipt_hook_test" || fail "receipt Stop-hook test does not compile"
jq empty "$hook_config" || fail "receipt Stop-hook configuration is invalid JSON"
jq -er '.hooks.PreToolUse[0] | select(.matcher == "*") | .hooks[0] | select(.type == "command" and (.command | contains("receipt-stop-hook.py")))' "$hook_config" >/dev/null || fail "plugin hook does not register the complexity PreToolUse gate"
jq -er '.hooks.Stop[0].hooks[0] | select(.type == "command" and (.command | contains("receipt-stop-hook.py")))' "$hook_config" >/dev/null || fail "plugin hook does not register the receipt Stop gate"
grep -Fq 'This lifecycle is a completion invariant' "$skill" || fail "skill permits skipping the receipt lifecycle"
grep -Fq 'Never draft or send the final response before calling' "$skill" || fail "skill permits a final response before receipt finish"
grep -Fq 'Never omit the receipt' "$receipt_contract" || fail "receipt contract permits silent omission"
python3 "$receipt_hook_test" "$plugin_dir" "$tmp_dir/receipt-hook" || fail "executive-band, fallback, complexity, receipt, or Stop-hook gate failed"
pass "both executive bands, fallback, complexity persistence, receipt recovery, and Stop-hook completion gate"
python3 "$effectiveness_test" "$plugin_dir" "$tmp_dir/effectiveness" || fail "effectiveness baseline, ledger, or comparison failed"
pass "effectiveness baseline, completion ledger, and comparison"
grep -Fq 'first Sol Advisor activation of each local calendar day' "$skill" || fail "skill omits once-daily activation boundary"
grep -Fq 'adopt unchanged' "$skill" || fail "skill omits upstream adoption classification"
grep -Fq 'adapt' "$skill" || fail "skill omits upstream adaptation classification"
grep -Fq 'skip' "$skill" || fail "skill omits upstream skip classification"
grep -Fq 'must not modify code or merge upstream' "$skill" || fail "skill permits automatic upstream merge"
grep -Fq 'merged into the fork' "$skill" || fail "skill does not require fork-main completion"
grep -Fq 'Never push to the original author' "$skill" || fail "skill permits pushes to upstream"
grep -Fq 'plain release versions without SemVer `+` build metadata' "$readme" || fail "README omits cache-compatible version policy"
grep -Fq 'reinstall-plugin.sh' "$readme" || fail "README omits safe plugin reinstall"

for document in "$readme" "$manifest" "$skill" "$contracts" "$ui"; do
  if grep -Eqi 'Terra / High is the sole implementation producer|one role-pinned .*handles all implementation|route all implementation through.*Terra|delegate all implementation to (the )?(native )?Terra' "$document"; then
    fail "stale single-mode implementation claim remains in $document"
  fi
done
forbidden_max='sol_advisor_(terra|sol)_'"max"
forbidden_max_file='sol-advisor-(terra|sol)-'"max"
if rg -n "$forbidden_max|$forbidden_max_file" "$readme" "$plugin_dir"; then fail "forbidden Max native role remains"; fi
pass "activation, automatic routing, reporting, and stale-claim checks"

grep -Fq 'Principle one: minimum sufficient work' "$skill" || fail "skill does not make efficiency principle one"
grep -Fq 'Minimum sufficient outcome' "$skill" || fail "skill omits minimum-sufficient gate"
grep -Fq 'Token budget checkpoint' "$skill" || fail "skill omits token-budget gate"
grep -Fq 'Time budget checkpoint' "$skill" || fail "skill omits time-budget gate"
grep -Fq 'Principle two: route by complexity and risk' "$skill" || fail "skill omits complexity-based routing principle"
grep -Fq 'complexity score from 1.0 to 10.0' "$skill" || fail "skill omits the numeric complexity scale"
grep -Fq '1.0–2.9 Luna / Max; 3.0–5.0 Terra / Medium;' "$skill" || fail "skill omits the first two numeric routing bands"
grep -Fq '5.1–6.5 Terra / High; 6.6–7.9 Sol / Medium; 8.0–10.0 Sol / High.' "$skill" || fail "skill omits the final three numeric routing bands"
grep -Fq 'only an unavailable or incapable lane triggers' "$skill" || fail "skill permits cost estimates to override numeric routing"
grep -Fq 'do not inflate the score merely because' "$skill" || fail "skill permits conservative score inflation"
grep -Fq 'Anchor an ordinary bounded task with settled requirements at **5.0**' "$skill" || fail "skill lacks a non-conservative score anchor"
grep -Fq 'typical bounded bug investigation or settled multi-file change' "$skill" || fail "skill overweights multi-step engineering work"
grep -Fq 'budgets, worker identity, and normal selection rationale internal' "$skill" || fail "skill does not keep normal routing diagnostics internal"
grep -Fq 'Read-only work is low mutation risk' "$skill" || fail "skill does not treat read-only work as a Terra candidate"
grep -Fq 'Terra / Medium (3.0–5.0)' "$skill" || fail "skill omits Terra/Medium route"
grep -Fq 'Terra / High (5.1–6.5)' "$skill" || fail "skill omits Terra/High route"
grep -Fq 'Sol / Medium (6.6–7.9)' "$skill" || fail "skill omits Sol/Medium route"
grep -Fq 'Sol / High (8.0–10.0)' "$skill" || fail "skill omits Sol/High route"
grep -Fq 'Luna / Max (1.0–2.9)' "$skill" || fail "skill omits Luna route"
grep -Fq '“Be efficient”' "$skill" || fail "skill permits a budget without a concrete boundary"
grep -Fq 'Do not spawn another Sol reviewer merely to watch the implementation worker' "$skill" || fail "skill adds redundant implementation review"
grep -Fq 'continue`, `redirect`, or `escalate' "$skill" || fail "skill omits primary replanning decisions"
grep -Fq 'Every activated request that asks for an answer, inspection, analysis, diagnosis' "$skill" || fail "skill does not score every deliverable"
grep -Fq 'Read-only work is still scored' "$skill" || fail "skill permits a read-only routing bypass"
grep -Fq 'only after the selected producer and every higher delegated tier are unavailable' "$skill" || fail "skill permits premature primary fallback"
grep -Fq 'Luna Max → Terra Medium → Terra High → Sol Medium → Sol High implementer → primary Sol High' "$skill" || fail "skill omits the ordered upward fallback ladder"
grep -Fq 'never move downward' "$skill" || fail "skill permits a lower-model fallback"
grep -Fq 'Availability fallback never permits a read-only, token, time, or convenience bypass' "$skill" || fail "skill permits a non-availability routing bypass"
for document in "$skill" "$readme" "$manifest" "$ui"; do
  if grep -Eqi 'primary Sol / no worker|direct primary work|reselect primary Sol|For primary Sol work' "$document"; then
    fail "direct-primary routing loophole remains in $document"
  fi
done
grep -Fq 'interrupt_agent' "$skill" || fail "skill omits native-worker interruption"
grep -Fq 'fresh executive decision' "$skill" || fail "skill omits fresh Sol decision after interruption"
grep -Fq '`task_complete` terminal event qualifies' "$skill" || fail "skill does not require authoritative task completion"
grep -Fq 'Never resume' "$skill" || fail "skill permits stale worker plans to resume automatically"
grep -Fq 'do not spawn a fresh' "$skill" || fail "skill adds routine read-only reviewer overhead"
for document in "$contracts"; do
  grep -Fq 'EFFICIENCY BOUNDARY' "$document" || fail "$document omits worker efficiency boundary"
  grep -Fq 'Minimum sufficient outcome' "$document" || fail "$document omits minimum-sufficient worker outcome"
  grep -Fq 'Complexity: <root Sol' "$document" || fail "$document omits the numeric complexity judgment"
  grep -Fq 'Token budget:' "$document" || fail "$document omits worker token budget"
  grep -Fq 'Time budget:' "$document" || fail "$document omits worker time budget"
  grep -Fq 'Do not abandon' "$document" || fail "$document permits budget-based abandonment"
done
grep -Fq 'first principle is the minimum sufficient answer or change' "$readme" || fail "README omits efficiency principle"
grep -Fq '1.0–2.9 uses Luna / Max' "$readme" || fail "README omits Luna band"
grep -Fq '3.0–5.0 Terra / Medium' "$readme" || fail "README omits Terra/Medium band"
grep -Fq '5.1–6.5 Terra / High' "$readme" || fail "README omits Terra/High band"
grep -Fq '6.6–7.9 Sol / Medium' "$readme" || fail "README omits Sol/Medium band"
grep -Fq '8.0–10.0 a separate Sol / High implementer' "$readme" || fail "README omits Sol/High band"
jq -r '.description + " " + .interface.shortDescription + " " + .interface.longDescription' "$manifest" | \
  grep -Fq '1.0–2.9 uses native GPT-5.6 Luna / Max, 3.0–5.0 uses native GPT-5.6 Terra / Medium, 5.1–6.5 uses native GPT-5.6 Terra / High, 6.6–7.9 uses native GPT-5.6 Sol / Medium, and 8.0–10.0 uses a separate native GPT-5.6 Sol / High implementer' || fail "manifest omits numeric routing bands"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'checkpoints shape scope without overriding' || fail "manifest permits budget-based abandonment"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'primary Sol High executes as the terminal fallback' || fail "manifest omits terminal primary fallback"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'Worker interruptions force fresh primary routing' || fail "manifest omits user-interruption rerouting"
grep -Fq 'keeping the Luna Max, Terra Medium, Terra High, Sol Medium, and Sol High producer bands unchanged' "$ui" || fail "skill UI permits a producer routing bypass"
grep -Fq 'Terra High executive ownership below 5.0 and primary Sol High executive ownership at 5.0 or above' "$ui" || fail "skill UI omits executive score bands"
grep -Fq 'preflight attempted roles with current-turn evidence' "$ui" || fail "skill UI omits role-specific current-turn preflight"
grep -Fq 'persist the exact one-decimal complexity score in root and nested executive sessions before work' "$ui" || fail "skill UI omits deterministic nested complexity persistence"
grep -Fq 'completion-gated three-line weekly savings receipt' "$ui" || fail "skill UI omits concise receipt output"
grep -Fq 'register every descendant against the root receipt immediately after spawn' "$ui" || fail "skill UI omits root descendant receipt registration"
pass "minimum-sufficient, token, time, and checkpoint policy"

grep -Fq '17 12 * * *' "$upstream_workflow" || fail "upstream workflow is not scheduled daily"
grep -Fq 'contents: read' "$upstream_workflow" || fail "upstream workflow has wrong contents permission"
grep -Fq 'issues: write' "$upstream_workflow" || fail "upstream workflow cannot open review issues"
grep -Fq 'gh issue create' "$upstream_workflow" || fail "upstream workflow does not create review issues"
grep -Fq 'gh issue edit' "$upstream_workflow" || fail "upstream workflow does not update an existing review issue"
grep -Fq 'upstream-base:' "$upstream_workflow" || fail "upstream workflow omits baseline marker"
grep -Fq 'upstream-head:' "$upstream_workflow" || fail "upstream workflow omits head marker"
if grep -Eq 'git push|gh pr merge|git cherry-pick|git rebase' "$upstream_workflow"; then
  fail "upstream workflow contains a code integration command"
fi
grep -Fq 'DannyMac180/sol-advisor' "$daily_audit" || fail "daily audit omits original repository"
grep -Fq 'jessejaffe/sol-advisor' "$daily_audit" || fail "daily audit omits maintained fork"
grep -Fq 'already-checked-today' "$daily_audit" || fail "daily audit omits same-day short circuit"
grep -Fq 'daily-upstream-audit.sh [--force]' "$daily_audit" || fail "daily audit omits forced cache refresh"
grep -Fq 'workflow run upstream-review.yml' "$daily_audit" || fail "daily audit cannot request issue workflow"
grep -Fq 'skip — redundant' "$skill" || fail "skill does not reject already-satisfied upstream patches"
grep -Fq 'current files and' "$skill" || fail "skill does not compare upstream changes with the fork"

if sh "$daily_audit" --invalid >/dev/null 2>&1; then
  fail "daily audit accepted an invalid option"
fi

audit_state=$tmp_dir/audit-state
mkdir -p "$audit_state"
printf 'CHECKED_DATE: %s\nSTATUS: current\n' "$(date +%F)" > "$audit_state/upstream-audit.txt"
SOL_ADVISOR_AUDIT_STATE_DIR="$audit_state" sh "$daily_audit" | \
  grep -Fq 'STATUS: already-checked-today' || fail "daily audit repeated a same-day network check"
pass "daily activation audit and non-merging upstream issue workflow"

sh -n "$installer"
sh -n "$reinstaller"
sh -n "$runtime_inspector"
sh -n "$daily_audit"
sh -n "$script_dir/verify.sh"
pass "shell syntax"

printf '%s\n' "VERIFY PASSED: Sol Advisor seven-role migration and executive routing checks completed in $tmp_dir"
