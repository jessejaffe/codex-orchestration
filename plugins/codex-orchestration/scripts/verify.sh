#!/bin/sh
# Repository-local verification for Codex Orchestration's eight-role companion migration.

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
state_migration=$script_dir/state_migration.py
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
      "$tmp_base"/codex-orchestration-verify.*) rm -rf "$tmp_dir" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}
trap cleanup 0 HUP INT TERM
tmp_dir=$(mktemp -d "$tmp_base/codex-orchestration-verify.XXXXXX") || fail "could not create disposable verification directory"

terra_medium_file=codex-orchestration-terra-medium-implementer.toml
terra_executive_file=codex-orchestration-terra-executive.toml
terra_file=codex-orchestration-terra-implementer.toml
sol_low_file=codex-orchestration-sol-low-implementer.toml
sol_medium_file=codex-orchestration-sol-medium-implementer.toml
sol_high_file=codex-orchestration-sol-high-implementer.toml
sol_file=codex-orchestration-sol-reviewer.toml
luna_file=codex-orchestration-luna-implementer.toml
legacy_terra_medium_file=sol-advisor-terra-medium-implementer.toml
legacy_terra_executive_file=sol-advisor-terra-executive.toml
legacy_terra_file=sol-advisor-terra-implementer.toml
legacy_sol_medium_file=sol-advisor-sol-medium-implementer.toml
legacy_sol_high_file=sol-advisor-sol-high-implementer.toml
legacy_sol_file=sol-advisor-sol-reviewer.toml
legacy_luna_file=sol-advisor-luna-implementer.toml
legacy_terra_sha256=4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca
legacy_luna_sha256=fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb
previous_terra_sha256=06c318e5e93f37452635906394e6ea69fb6a65ba9e6ad7172d37b444e0dc871d
previous_sol_medium_sha256=5360b683128ec2863bdaf95fd1bbb13eda615b67270dbbf3e45c553fbde60562

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
  for mapping in \
    "$luna_file:$legacy_luna_file:bc4c6a8c2f3f58288d970d9caba66e2ecc532a59820c08bb958d466ed561500d" \
    "$terra_medium_file:$legacy_terra_medium_file:309d1fd8f0bf17785fff53583d4e42067e637c0922b9f23da0653729e7f809cf" \
    "$terra_executive_file:$legacy_terra_executive_file:4849c6591202290ff63db140b56089e63a4d06e2eaabec7256d016dcb056dbdc" \
    "$terra_file:$legacy_terra_file:7b4549d971ddd7c07a886ebcc01bc9645cc0eedc4e81f32930bee6ec9ab8c44c" \
    "$sol_medium_file:$legacy_sol_medium_file:dd42eaeaac3063c43109c9b45f7d1efda0ef999976d9a2231f8833e42afa3974" \
    "$sol_high_file:$legacy_sol_high_file:712adee8e4d5e425cd6e1bc3fe4a41760befdb5b6f4e333e85a6fd6273b4c292" \
    "$sol_file:$legacy_sol_file:0333acf0ef562bcfebd06009ac09bd1dd8cbc04c4cf28e08e9e049bd8bf202d2"
  do
    current=${mapping%%:*}
    remainder=${mapping#*:}
    legacy=${remainder%%:*}
    expected=${remainder##*:}
    sed -e 's/7.3–7.9/6.6–7.9/g' -e 's/7.3 through 7.9/6.6 through 7.9/g' \
      -e 's/Codex Orchestration/Sol Advisor/g' -e 's/codex_orchestration/sol_advisor/g' \
      "$templates/$current" > "$target/$legacy"
    [ "$(shasum -a 256 "$target/$legacy" | awk '{print $1}')" = "$expected" ] ||
      fail "legacy 0.6.5 fixture digest drifted: $legacy"
  done
}

write_previous_terra() {
  target=$1
  mkdir -p "$target"
  cat > "$target/$legacy_terra_file" <<'PREVIOUS_TERRA'
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
  [ "$(shasum -a 256 "$target/$legacy_terra_file" | awk '{print $1}')" = "$previous_terra_sha256" ] || fail "previous Terra fixture digest drifted"
}

write_previous_sol_medium() {
  target=$1
  mkdir -p "$target"
  sed -e 's/7.3–7.9/6.6–7.9/g' -e 's/7.3 through 7.9/6.6 through 7.9/g' \
    "$templates/$sol_medium_file" > "$target/$sol_medium_file"
  [ "$(shasum -a 256 "$target/$sol_medium_file" | awk '{print $1}')" = "$previous_sol_medium_sha256" ] ||
    fail "previous Sol Medium fixture digest drifted"
}

for required in "$installer" "$reinstaller" "$runtime_inspector" "$daily_audit" "$usage_receipt" "$effectiveness_tracker" "$effectiveness_test" "$receipt_hook" "$receipt_hook_test" "$state_migration" "$hook_config" "$manifest" "$skill" "$contracts" "$receipt_contract" "$readme" "$ui" "$upstream_workflow"; do
  test -f "$required" || fail "required file missing: $required"
done

jq empty "$manifest"
manifest_version=$(jq -r '.version' "$manifest")
[ "$manifest_version" = 0.7.3 ] || fail "manifest version is not the required 0.7.3 release: $manifest_version"
case "$manifest_version" in *+*) fail "manifest version contains incompatible build metadata: $manifest_version" ;; esac
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'Turn Orchestration on' || fail "manifest does not describe Orchestration activation"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'hands executive ownership below 5.0' || fail "manifest omits low-band Terra ownership"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'no implementation handoff' || fail "manifest omits same-model no-handoff rule"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'at most one correction request' || fail "manifest omits bounded correction"
grep -Fqi 'Luna / Max' "$manifest" || fail "manifest does not describe Luna routing"
grep -Fq 'three-line savings receipt' "$manifest" || fail "manifest does not describe the savings receipt"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'independent review is exceptional' || fail "manifest does not bound independent review"
pass "manifest JSON, economical constitution, executive bands, and bounded correction"

python3 - "$templates" <<'PY'
from pathlib import Path
import sys, tomllib

root = Path(sys.argv[1])
expected = {
    "codex-orchestration-luna-implementer.toml": {
        "name": "codex_orchestration_luna_implementer",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "max",
    },
    "codex-orchestration-terra-medium-implementer.toml": {
        "name": "codex_orchestration_terra_medium_implementer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
    },
    "codex-orchestration-terra-executive.toml": {
        "name": "codex_orchestration_terra_executive",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "high",
    },
    "codex-orchestration-terra-implementer.toml": {
        "name": "codex_orchestration_terra_implementer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "high",
    },
    "codex-orchestration-sol-low-implementer.toml": {
        "name": "codex_orchestration_sol_low_implementer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "low",
    },
    "codex-orchestration-sol-medium-implementer.toml": {
        "name": "codex_orchestration_sol_medium_implementer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "medium",
    },
    "codex-orchestration-sol-high-implementer.toml": {
        "name": "codex_orchestration_sol_high_implementer",
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "high",
    },
    "codex-orchestration-sol-reviewer.toml": {
        "name": "codex_orchestration_sol_reviewer",
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
print("eight exact role pins are valid")
PY
pass "exact eight-role TOML inventory with six implementation levels"

grep -Fq '7b4549d971ddd7c07a886ebcc01bc9645cc0eedc4e81f32930bee6ec9ab8c44c' "$installer" || fail "installer omits shipped 0.6.5 Terra digest"
grep -Fq 'bc4c6a8c2f3f58288d970d9caba66e2ecc532a59820c08bb958d466ed561500d' "$installer" || fail "installer omits shipped 0.6.5 Luna digest"
grep -Fq "$legacy_terra_sha256" "$installer" || fail "installer omits recognized historical Terra digest"
grep -Fq "$legacy_luna_sha256" "$installer" || fail "installer omits recognized historical Luna digest"
grep -Fq "$previous_terra_sha256" "$installer" || fail "installer omits recognized previous Terra digest"
grep -Fq "$previous_sol_medium_sha256" "$installer" || fail "installer omits recognized 0.7.2 Sol Medium digest"
pass "recognized shipped legacy agent fingerprints"

reinstall_cache=$tmp_dir/reinstall-cache
legacy_reinstall_cache=$tmp_dir/legacy-reinstall-cache
old_build=0.6.5
old_alias=0.5.1+codex.20260804022121
prior_alias=0.7.2
mkdir -p "$reinstall_cache/$prior_alias/skills/orchestration"
printf '%s\n' prior-release-open-task-skill > "$reinstall_cache/$prior_alias/skills/orchestration/SKILL.md"
mkdir -p "$legacy_reinstall_cache/$old_build/skills/orchestration" "$legacy_reinstall_cache/$old_alias/skills/orchestration"
printf '%s\n' preserved-open-task-skill > "$legacy_reinstall_cache/$old_build/skills/orchestration/SKILL.md"
printf '%s\n' preserved-open-task-skill > "$legacy_reinstall_cache/$old_alias/skills/orchestration/SKILL.md"
fake_codex=$tmp_dir/fake-codex
fake_new_installed=$tmp_dir/fake-new-installed
fake_legacy_installed=$tmp_dir/fake-legacy-installed
fake_legacy_marketplace=$tmp_dir/fake-legacy-marketplace
fake_marketplace_removed=$tmp_dir/fake-marketplace-removed
fake_log=$tmp_dir/fake-codex.log
: > "$fake_legacy_installed"
: > "$fake_legacy_marketplace"
: > "$fake_log"
cat > "$fake_codex" <<'FAKE_CODEX'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$CODEX_ORCHESTRATION_TEST_LOG"
if [ "${1:-}" = plugin ] && [ "${2:-}" = list ] && [ "${3:-}" = --json ]; then
  if [ -e "$CODEX_ORCHESTRATION_TEST_NEW_INSTALLED" ] && [ -e "$CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED" ]; then
    printf '{"installed":[{"pluginId":"codex-orchestration@codex-orchestration","version":"0.7.3"},{"pluginId":"sol-advisor@sol-advisor","version":"0.6.5"}]}\n'
  elif [ -e "$CODEX_ORCHESTRATION_TEST_NEW_INSTALLED" ]; then
    printf '{"installed":[{"pluginId":"codex-orchestration@codex-orchestration","version":"0.7.3"}]}\n'
  elif [ -e "$CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED" ]; then
    printf '{"installed":[{"pluginId":"sol-advisor@sol-advisor","version":"0.6.5"}]}\n'
  else
    printf '{"installed":[]}\n'
  fi
  exit 0
fi
if [ "${1:-}" = plugin ] && [ "${2:-}" = marketplace ] && [ "${3:-}" = list ] && [ "${4:-}" = --json ]; then
  if [ -e "$CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE" ]; then
    printf '{"marketplaces":[{"name":"sol-advisor"},{"name":"codex-orchestration"}]}\n'
  else
    printf '{"marketplaces":[{"name":"codex-orchestration"}]}\n'
  fi
  exit 0
fi
if [ "${1:-}" = plugin ] && [ "${2:-}" = add ] && [ "${3:-}" = codex-orchestration@codex-orchestration ]; then
  [ "${CODEX_ORCHESTRATION_TEST_ADD_FAIL:-0}" -eq 0 ] || exit 42
  rm -rf "$CODEX_ORCHESTRATION_CACHE_ROOT"
  current=$(jq -r .version "$CODEX_ORCHESTRATION_TEST_MANIFEST")
  current_dir=$CODEX_ORCHESTRATION_CACHE_ROOT/$current
  mkdir -p "$current_dir"
  cp -Rp "$CODEX_ORCHESTRATION_TEST_PLUGIN"/. "$current_dir"
  if [ -n "${CODEX_ORCHESTRATION_TEST_OMIT_RELATIVE:-}" ]; then
    rm -f "$current_dir/$CODEX_ORCHESTRATION_TEST_OMIT_RELATIVE"
  fi
  : > "$CODEX_ORCHESTRATION_TEST_NEW_INSTALLED"
  exit 0
fi
if [ "${1:-}" = plugin ] && [ "${2:-}" = remove ] && [ "${3:-}" = sol-advisor@sol-advisor ]; then
  rm -rf "$CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT"
  if [ "${CODEX_ORCHESTRATION_TEST_REMOVE_FAIL:-0}" -eq 1 ]; then
    exit 43
  fi
  rm -f "$CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED"
  if [ "${CODEX_ORCHESTRATION_TEST_INTERRUPT_AFTER_REMOVE:-0}" -eq 1 ]; then
    kill -TERM "$PPID"
  fi
  exit 0
fi
if [ "${1:-}" = plugin ] && [ "${2:-}" = marketplace ] && [ "${3:-}" = remove ] && [ "${4:-}" = sol-advisor ]; then
  rm -f "$CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE"
  : > "$CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED"
  exit 0
fi
exit 64
FAKE_CODEX
chmod +x "$fake_codex"

equal_marketplace_log=$tmp_dir/equal-marketplace.log
equal_marketplace_cache=$tmp_dir/equal-marketplace-cache
equal_marketplace_legacy_cache=$tmp_dir/equal-marketplace-legacy-cache
mkdir -p "$equal_marketplace_legacy_cache/0.6.5/skills/orchestration"
printf '%s\n' untouched > "$equal_marketplace_legacy_cache/0.6.5/skills/orchestration/SKILL.md"
: > "$equal_marketplace_log"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_MARKETPLACE=same-marketplace \
  CODEX_ORCHESTRATION_LEGACY_MARKETPLACE=same-marketplace \
  CODEX_ORCHESTRATION_CACHE_ROOT="$equal_marketplace_cache" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$equal_marketplace_legacy_cache" \
  CODEX_ORCHESTRATION_TEST_LOG="$equal_marketplace_log" sh "$reinstaller"; then
  fail "reinstaller accepted equal current and legacy marketplace names"
fi
test ! -s "$equal_marketplace_log" || fail "equal marketplace refusal invoked Codex before failing"
grep -Fq untouched "$equal_marketplace_legacy_cache/0.6.5/skills/orchestration/SKILL.md" ||
  fail "equal marketplace refusal mutated the legacy cache"
test ! -e "$equal_marketplace_cache" || fail "equal marketplace refusal created the current cache"
pass "equal current and legacy marketplace names are refused before mutation"

reinstall_agent_home=$tmp_dir/reinstall-agent-home
write_legacy_roles "$reinstall_agent_home/agents"
if [ "${CODEX_HOME+x}" = x ]; then
  verify_had_codex_home=1
  verify_saved_codex_home=$CODEX_HOME
else
  verify_had_codex_home=0
  verify_saved_codex_home=''
fi
CODEX_HOME=$reinstall_agent_home
export CODEX_HOME
if [ "${TMPDIR+x}" = x ]; then
  verify_had_tmpdir=1
  verify_saved_tmpdir=$TMPDIR
else
  verify_had_tmpdir=0
  verify_saved_tmpdir=''
fi
TMPDIR=$tmp_dir
export TMPDIR

CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
CODEX_ORCHESTRATION_CACHE_ROOT="$reinstall_cache" \
CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$legacy_reinstall_cache" \
CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$fake_new_installed" \
CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$fake_legacy_installed" \
CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$fake_legacy_marketplace" \
CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$fake_marketplace_removed" \
CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" \
  sh "$reinstaller"
test -f "$reinstall_cache/$manifest_version/skills/orchestration/SKILL.md" || fail "reinstaller lost the current skill cache"
for alias in "$old_build" "$old_alias" 0.5.1; do
  diff -qr "$reinstall_cache/$manifest_version" "$legacy_reinstall_cache/$alias" >/dev/null || fail "legacy cache alias is not the complete $manifest_version package: $alias"
done
diff -qr "$reinstall_cache/$manifest_version" "$reinstall_cache/$prior_alias" >/dev/null ||
  fail "0.7.2 compatibility alias is not the complete $manifest_version package"
test ! -e "$fake_legacy_installed" || fail "legacy plugin identity was not removed"
test -e "$fake_marketplace_removed" || fail "legacy marketplace was not removed"
for role in luna-implementer terra-medium-implementer terra-executive terra-implementer sol-low-implementer sol-medium-implementer sol-high-implementer sol-reviewer; do
  cmp -s "$templates/codex-orchestration-$role.toml" "$reinstall_agent_home/agents/codex-orchestration-$role.toml" ||
    fail "reinstaller did not prove the current agent before identity retirement: $role"
  test ! -e "$reinstall_agent_home/agents/sol-advisor-$role.toml" ||
    fail "reinstaller left a recognized legacy agent after proving all eight roles: $role"
done
remove_line=$(grep -n '^plugin remove sol-advisor@sol-advisor$' "$fake_log" | cut -d: -f1)
marketplace_line=$(grep -n '^plugin marketplace remove sol-advisor$' "$fake_log" | cut -d: -f1)
[ -n "$remove_line" ] && [ -n "$marketplace_line" ] && [ "$remove_line" -lt "$marketplace_line" ] || fail "legacy marketplace removal order is unsafe"
CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
CODEX_ORCHESTRATION_CACHE_ROOT="$reinstall_cache" \
CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$legacy_reinstall_cache" \
CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$fake_new_installed" \
CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$fake_legacy_installed" \
CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$fake_legacy_marketplace" \
CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$fake_marketplace_removed" \
CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  sh "$reinstaller" --check
pass "0.6.5 identity migration, removal order, and complete legacy cache aliases"

failure_root=$tmp_dir/reinstall-failure
failure_legacy_root=$tmp_dir/reinstall-failure-legacy
failure_new_flag=$tmp_dir/reinstall-failure-new
failure_legacy_flag=$tmp_dir/reinstall-failure-old
failure_legacy_marketplace=$tmp_dir/reinstall-failure-marketplace-present
mkdir -p "$failure_legacy_root/0.6.5/skills/orchestration"
printf '%s\n' untouched > "$failure_legacy_root/0.6.5/skills/orchestration/SKILL.md"
: > "$failure_legacy_flag"
: > "$failure_legacy_marketplace"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$failure_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$failure_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$failure_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$failure_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$failure_legacy_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/failure-marketplace" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" \
  CODEX_ORCHESTRATION_TEST_ADD_FAIL=1 sh "$reinstaller"; then
  fail "reinstaller accepted a failed replacement install"
fi
test -e "$failure_legacy_flag" || fail "failed replacement removed the legacy plugin"
grep -Fq untouched "$failure_legacy_root/0.6.5/skills/orchestration/SKILL.md" || fail "failed replacement changed legacy cache"
test ! -e "$tmp_dir/failure-marketplace" || fail "failed replacement removed legacy marketplace"
pass "replacement-install failure leaves legacy identity and cache untouched"

omitted_root=$tmp_dir/reinstall-omitted
omitted_legacy_root=$tmp_dir/reinstall-omitted-legacy
omitted_new_flag=$tmp_dir/reinstall-omitted-new
omitted_legacy_flag=$tmp_dir/reinstall-omitted-old
omitted_marketplace=$tmp_dir/reinstall-omitted-marketplace
mkdir -p "$omitted_legacy_root/0.6.5/skills/orchestration"
printf '%s\n' untouched > "$omitted_legacy_root/0.6.5/skills/orchestration/SKILL.md"
: > "$omitted_legacy_flag"
: > "$omitted_marketplace"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$omitted_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$omitted_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$omitted_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$omitted_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$omitted_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/omitted-marketplace-removed" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" \
  CODEX_ORCHESTRATION_TEST_OMIT_RELATIVE=scripts/install-agents.sh sh "$reinstaller"; then
  fail "reinstaller accepted a package missing a required installer"
fi
test -e "$omitted_legacy_flag" || fail "incomplete replacement removed the legacy plugin"
test -e "$omitted_marketplace" || fail "incomplete replacement removed the legacy marketplace"
grep -Fq untouched "$omitted_legacy_root/0.6.5/skills/orchestration/SKILL.md" || fail "incomplete replacement changed legacy cache"
pass "omitted required package file blocks every legacy removal"

custom_agent_root=$tmp_dir/reinstall-custom-agent
custom_agent_home=$tmp_dir/reinstall-custom-agent-home
custom_agent_new_flag=$tmp_dir/reinstall-custom-agent-new
custom_agent_legacy_flag=$tmp_dir/reinstall-custom-agent-old
custom_agent_marketplace=$tmp_dir/reinstall-custom-agent-marketplace
mkdir -p "$custom_agent_root/0.6.5/skills/orchestration"
printf '%s\n' untouched > "$custom_agent_root/0.6.5/skills/orchestration/SKILL.md"
write_legacy_roles "$custom_agent_home/agents"
printf '%s\n' '# user customization' >> "$custom_agent_home/agents/$legacy_luna_file"
custom_agents_before=$(snapshot_files "$custom_agent_home/agents")
: > "$custom_agent_legacy_flag"
: > "$custom_agent_marketplace"
if CODEX_HOME="$custom_agent_home" CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$tmp_dir/reinstall-custom-agent-current" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$custom_agent_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$custom_agent_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$custom_agent_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$custom_agent_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/reinstall-custom-agent-marketplace-removed" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" sh "$reinstaller"; then
  fail "reinstaller accepted a customized legacy agent"
fi
[ "$(snapshot_files "$custom_agent_home/agents")" = "$custom_agents_before" ] ||
  fail "customized legacy-agent refusal partially mutated agent files"
test -e "$custom_agent_legacy_flag" || fail "customized legacy-agent refusal removed the legacy plugin"
test -e "$custom_agent_marketplace" || fail "customized legacy-agent refusal removed the legacy marketplace"
grep -Fq untouched "$custom_agent_root/0.6.5/skills/orchestration/SKILL.md" ||
  fail "customized legacy-agent refusal changed the legacy cache"
test ! -e "$tmp_dir/reinstall-custom-agent-marketplace-removed" ||
  fail "customized legacy-agent refusal attempted marketplace removal"
pass "customized legacy agents refuse migration without partial agent or identity retirement"

nonversion_root=$tmp_dir/reinstall-nonversion
nonversion_legacy_root=$tmp_dir/reinstall-nonversion-legacy
mkdir -p "$nonversion_legacy_root/notes"
printf '%s\n' keep > "$nonversion_legacy_root/notes/marker"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$nonversion_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$nonversion_legacy_root" sh "$reinstaller"; then
  fail "reinstaller accepted an arbitrary non-version cache directory"
fi
grep -Fq keep "$nonversion_legacy_root/notes/marker" || fail "non-version cache refusal changed arbitrary data"
pass "non-version cache directories are rejected and untouched"

persistent_root=$tmp_dir/reinstall-persistent-copy
persistent_legacy_root=$tmp_dir/reinstall-persistent-copy-legacy
persistent_new_flag=$tmp_dir/reinstall-persistent-copy-new
persistent_legacy_flag=$tmp_dir/reinstall-persistent-copy-old
persistent_marketplace=$tmp_dir/reinstall-persistent-copy-marketplace
persistent_bin=$tmp_dir/reinstall-persistent-bin
mkdir -p "$persistent_legacy_root" "$persistent_bin"
cp -Rp "$plugin_dir" "$persistent_legacy_root/0.6.5"
: > "$persistent_legacy_flag"
: > "$persistent_marketplace"
cat > "$persistent_bin/cp" <<'FAIL_STAGED_COPY'
#!/bin/sh
case "$*" in *codex-orchestration-aliases*) exit 97 ;; esac
exec /bin/cp "$@"
FAIL_STAGED_COPY
chmod +x "$persistent_bin/cp"
if PATH="$persistent_bin:$PATH" CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$persistent_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$persistent_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$persistent_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$persistent_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$persistent_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/persistent-marketplace-removed" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" sh "$reinstaller"; then
  fail "reinstaller accepted persistent alias staging failure"
fi
diff -qr "$plugin_dir" "$persistent_legacy_root/0.6.5" >/dev/null || fail "persistent copy failure left the prior alias missing or partial"
test -e "$persistent_legacy_flag" || fail "persistent copy failure removed the legacy plugin"
test -e "$persistent_marketplace" || fail "persistent copy failure removed the legacy marketplace"
pass "persistent staging failure preserves every complete prior alias and legacy identity"

remove_failure_root=$tmp_dir/reinstall-remove-failure
remove_failure_legacy_root=$tmp_dir/reinstall-remove-failure-legacy
remove_failure_new_flag=$tmp_dir/reinstall-remove-failure-new
remove_failure_legacy_flag=$tmp_dir/reinstall-remove-failure-old
remove_failure_legacy_marketplace=$tmp_dir/reinstall-remove-failure-marketplace-present
mkdir -p "$remove_failure_legacy_root/0.6.5/skills/orchestration"
printf '%s\n' old > "$remove_failure_legacy_root/0.6.5/skills/orchestration/SKILL.md"
: > "$remove_failure_legacy_flag"
: > "$remove_failure_legacy_marketplace"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$remove_failure_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$remove_failure_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$remove_failure_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$remove_failure_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$remove_failure_legacy_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/remove-failure-marketplace" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" \
  CODEX_ORCHESTRATION_TEST_REMOVE_FAIL=1 sh "$reinstaller"; then
  fail "reinstaller accepted a failed legacy-plugin removal"
fi
test -e "$remove_failure_legacy_flag" || fail "failed removal lost the legacy identity fixture"
diff -qr "$remove_failure_root/$manifest_version" "$remove_failure_legacy_root/0.6.5" >/dev/null || fail "failed removal did not restore the complete legacy alias"
test ! -e "$tmp_dir/remove-failure-marketplace" || fail "failed plugin removal removed legacy marketplace"
pass "legacy-plugin removal failure restores complete compatibility aliases"

interrupt_root=$tmp_dir/reinstall-interrupt
interrupt_legacy_root=$tmp_dir/reinstall-interrupt-legacy
interrupt_new_flag=$tmp_dir/reinstall-interrupt-new
interrupt_legacy_flag=$tmp_dir/reinstall-interrupt-old
interrupt_legacy_marketplace=$tmp_dir/reinstall-interrupt-marketplace-present
mkdir -p "$interrupt_legacy_root/0.6.5/skills/orchestration"
printf '%s\n' old > "$interrupt_legacy_root/0.6.5/skills/orchestration/SKILL.md"
mkdir -p "$interrupt_legacy_root/$old_alias/skills/orchestration"
printf '%s\n' old > "$interrupt_legacy_root/$old_alias/skills/orchestration/SKILL.md"
: > "$interrupt_legacy_flag"
: > "$interrupt_legacy_marketplace"
set +e
CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
CODEX_ORCHESTRATION_CACHE_ROOT="$interrupt_root" \
CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$interrupt_legacy_root" \
CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$interrupt_new_flag" \
CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$interrupt_legacy_flag" \
CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$interrupt_legacy_marketplace" \
CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/interrupt-marketplace" \
CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" \
CODEX_ORCHESTRATION_TEST_INTERRUPT_AFTER_REMOVE=1 sh "$reinstaller"
interrupt_status=$?
set -e
[ "$interrupt_status" -eq 130 ] || fail "interrupted reinstaller returned $interrupt_status, expected 130"
for alias in 0.6.5 "$old_alias" 0.5.1; do
  diff -qr "$interrupt_root/$manifest_version" "$interrupt_legacy_root/$alias" >/dev/null || fail "interruption left a legacy alias missing or partial: $alias"
done
test ! -e "$tmp_dir/interrupt-marketplace" || fail "interruption removed legacy marketplace"
pass "post-removal interruption restores complete legacy cache aliases"

recovery_failure_root=$tmp_dir/reinstall-recovery-current
recovery_failure_legacy_root=$tmp_dir/reinstall-recovery-legacy
recovery_failure_new_flag=$tmp_dir/reinstall-recovery-new
recovery_failure_legacy_flag=$tmp_dir/reinstall-recovery-old
recovery_failure_marketplace=$tmp_dir/reinstall-recovery-marketplace
recovery_failure_bin=$tmp_dir/reinstall-recovery-bin
mkdir -p "$recovery_failure_legacy_root/0.6.5/skills/orchestration" "$recovery_failure_bin"
printf '%s\n' old > "$recovery_failure_legacy_root/0.6.5/skills/orchestration/SKILL.md"
: > "$recovery_failure_legacy_flag"
: > "$recovery_failure_marketplace"
cat > "$recovery_failure_bin/mv" <<'FAIL_LEGACY_ACTIVATION'
#!/bin/sh
case "$*" in *reinstall-recovery-legacy.codex-orchestration-aliases.*/staged/*) exit 98 ;; esac
exec /bin/mv "$@"
FAIL_LEGACY_ACTIVATION
chmod +x "$recovery_failure_bin/mv"
if PATH="$recovery_failure_bin:$PATH" TMPDIR="$tmp_dir" \
  CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$recovery_failure_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$recovery_failure_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$recovery_failure_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$recovery_failure_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$recovery_failure_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$tmp_dir/reinstall-recovery-marketplace-removed" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
  CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
  CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" sh "$reinstaller"; then
  fail "reinstaller accepted persistent activation and recovery failure"
fi
test ! -e "$recovery_failure_legacy_flag" || fail "recovery failure fixture did not occur after legacy-plugin removal"
test -e "$recovery_failure_marketplace" || fail "recovery failure removed the legacy marketplace"
recovery_transaction=$(find "$tmp_dir" -maxdepth 1 -type d -name '.reinstall-recovery-legacy.codex-orchestration-aliases.*' -print | head -n 1)
[ -n "$recovery_transaction" ] || fail "recovery failure deleted its transaction directory"
diff -qr "$recovery_failure_root/$manifest_version" "$recovery_transaction/staged/0.6.5" >/dev/null ||
  fail "recovery failure did not preserve a complete staged legacy alias"
recovery_inventory=$(find "$tmp_dir" -maxdepth 1 -type d -name 'codex-orchestration-reinstall.*' -print | head -n 1)
[ -n "$recovery_inventory" ] || fail "recovery failure deleted its alias inventory"
grep -Fxq 0.6.5 "$recovery_inventory/legacy-aliases" || fail "preserved recovery inventory omits the legacy alias"
pass "persistent post-removal activation and recovery failure preserves recoverable transaction state"

marketplace_only_root=$tmp_dir/reinstall-marketplace-only
marketplace_only_legacy_root=$tmp_dir/reinstall-marketplace-only-legacy
marketplace_only_new_flag=$tmp_dir/reinstall-marketplace-only-new
marketplace_only_legacy_flag=$tmp_dir/reinstall-marketplace-only-old
marketplace_only_marketplace=$tmp_dir/reinstall-marketplace-only-marketplace
marketplace_only_removed=$tmp_dir/reinstall-marketplace-only-removed
mkdir -p "$marketplace_only_root"
cp -Rp "$plugin_dir" "$marketplace_only_root/$manifest_version"
: > "$marketplace_only_new_flag"
: > "$marketplace_only_marketplace"
if CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
  CODEX_ORCHESTRATION_CACHE_ROOT="$marketplace_only_root" \
  CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$marketplace_only_legacy_root" \
  CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$marketplace_only_new_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$marketplace_only_legacy_flag" \
  CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$marketplace_only_marketplace" \
  CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$marketplace_only_removed" \
  CODEX_ORCHESTRATION_TEST_LOG="$fake_log" sh "$reinstaller" --check; then
  fail "--check accepted a marketplace-only legacy identity"
fi
CODEX_ORCHESTRATION_CODEX_BIN="$fake_codex" \
CODEX_ORCHESTRATION_CACHE_ROOT="$marketplace_only_root" \
CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT="$marketplace_only_legacy_root" \
CODEX_ORCHESTRATION_TEST_NEW_INSTALLED="$marketplace_only_new_flag" \
CODEX_ORCHESTRATION_TEST_LEGACY_INSTALLED="$marketplace_only_legacy_flag" \
CODEX_ORCHESTRATION_TEST_LEGACY_MARKETPLACE="$marketplace_only_marketplace" \
CODEX_ORCHESTRATION_TEST_MARKETPLACE_REMOVED="$marketplace_only_removed" \
CODEX_ORCHESTRATION_TEST_LOG="$fake_log" \
CODEX_ORCHESTRATION_TEST_MANIFEST="$manifest" \
CODEX_ORCHESTRATION_TEST_PLUGIN="$plugin_dir" sh "$reinstaller"
test ! -e "$marketplace_only_marketplace" || fail "marketplace-only legacy identity was not removed"
test -e "$marketplace_only_removed" || fail "marketplace-only removal was not attempted"
pass "marketplace-only legacy identity is detected, checked, and retired independently"

if [ "$verify_had_codex_home" -eq 1 ]; then
  CODEX_HOME=$verify_saved_codex_home
  export CODEX_HOME
else
  unset CODEX_HOME
fi
if [ "$verify_had_tmpdir" -eq 1 ]; then
  TMPDIR=$verify_saved_tmpdir
  export TMPDIR
else
  unset TMPDIR
fi

clean_target=$tmp_dir/clean
sh "$installer" --target-dir "$clean_target"
cmp -s "$templates/$luna_file" "$clean_target/$luna_file" || fail "clean Luna/Max install mismatch"
cmp -s "$templates/$terra_medium_file" "$clean_target/$terra_medium_file" || fail "clean Terra/Medium install mismatch"
cmp -s "$templates/$terra_executive_file" "$clean_target/$terra_executive_file" || fail "clean Terra executive install mismatch"
cmp -s "$templates/$terra_file" "$clean_target/$terra_file" || fail "clean Terra install mismatch"
cmp -s "$templates/$sol_low_file" "$clean_target/$sol_low_file" || fail "clean Sol/Low install mismatch"
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
cmp -s "$templates/$sol_low_file" "$codex_home/agents/$sol_low_file" || fail "CODEX_HOME Sol/Low mismatch"
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
cmp -s "$templates/$sol_low_file" "$relative_parent/relative-agents/$sol_low_file" || fail "relative target Sol/Low mismatch"
pass "CODEX_HOME and relative target behavior"

migration_target=$tmp_dir/migration
write_legacy_roles "$migration_target"
sh "$installer" --target-dir "$migration_target"
cmp -s "$templates/$luna_file" "$migration_target/$luna_file" || fail "legacy Luna was not migrated"
cmp -s "$templates/$terra_medium_file" "$migration_target/$terra_medium_file" || fail "Terra/Medium was not added during migration"
cmp -s "$templates/$terra_executive_file" "$migration_target/$terra_executive_file" || fail "Terra executive was not added during migration"
cmp -s "$templates/$terra_file" "$migration_target/$terra_file" || fail "legacy Terra was not migrated"
cmp -s "$templates/$sol_low_file" "$migration_target/$sol_low_file" || fail "Sol/Low was not added during migration"
cmp -s "$templates/$sol_medium_file" "$migration_target/$sol_medium_file" || fail "Sol/Medium was not added during migration"
cmp -s "$templates/$sol_high_file" "$migration_target/$sol_high_file" || fail "Sol/High implementer was not added during migration"
cmp -s "$templates/$sol_file" "$migration_target/$sol_file" || fail "Sol changed during migration"
for legacy in "$legacy_luna_file" "$legacy_terra_medium_file" "$legacy_terra_executive_file" "$legacy_terra_file" "$legacy_sol_medium_file" "$legacy_sol_high_file" "$legacy_sol_file"; do
  test ! -e "$migration_target/$legacy" || fail "recognized legacy agent file was not removed: $legacy"
done
sh "$installer" --target-dir "$migration_target" --check
pass "all seven exact 0.6.5 legacy agent files migrated and removed"

previous_target=$tmp_dir/previous-terra
write_previous_terra "$previous_target"
cp "$templates/$sol_file" "$previous_target/$sol_file"
sh "$installer" --target-dir "$previous_target"
cmp -s "$templates/$luna_file" "$previous_target/$luna_file" || fail "Luna/Max was not added during previous-template migration"
cmp -s "$templates/$terra_medium_file" "$previous_target/$terra_medium_file" || fail "Terra/Medium was not added during previous-template migration"
cmp -s "$templates/$terra_executive_file" "$previous_target/$terra_executive_file" || fail "Terra executive was not added during previous-template migration"
cmp -s "$templates/$terra_file" "$previous_target/$terra_file" || fail "previous Terra was not migrated"
cmp -s "$templates/$sol_low_file" "$previous_target/$sol_low_file" || fail "Sol/Low was not added during previous-template migration"
cmp -s "$templates/$sol_medium_file" "$previous_target/$sol_medium_file" || fail "Sol/Medium was not added during previous-template migration"
cmp -s "$templates/$sol_high_file" "$previous_target/$sol_high_file" || fail "Sol/High implementer was not added during previous-template migration"
cmp -s "$templates/$sol_file" "$previous_target/$sol_file" || fail "previous-template migration changed Sol"
test ! -e "$previous_target/$legacy_terra_file" || fail "recognized previous Terra filename was not removed"
sh "$installer" --target-dir "$previous_target" --check
pass "exact previous Terra upgrade migration"

previous_sol_medium_target=$tmp_dir/previous-sol-medium
write_previous_sol_medium "$previous_sol_medium_target"
sh "$installer" --target-dir "$previous_sol_medium_target"
cmp -s "$templates/$sol_low_file" "$previous_sol_medium_target/$sol_low_file" ||
  fail "Sol/Low was not added during 0.7.2 companion upgrade"
cmp -s "$templates/$sol_medium_file" "$previous_sol_medium_target/$sol_medium_file" ||
  fail "exact 0.7.2 Sol/Medium template was not upgraded"
sh "$installer" --target-dir "$previous_sol_medium_target" --check
pass "exact 0.7.2 companion upgrade adds Sol/Low and updates Sol/Medium"

modified_luna=$tmp_dir/modified-luna
write_legacy_roles "$modified_luna"
printf '%s\n' modified >> "$modified_luna/$legacy_luna_file"
before=$(snapshot_files "$modified_luna")
if sh "$installer" --target-dir "$modified_luna"; then fail "installer replaced modified Luna"; fi
after=$(snapshot_files "$modified_luna")
[ "$before" = "$after" ] || fail "modified-Luna refusal partially mutated target"
pass "modified Luna refusal with zero partial mutation"

modified_terra=$tmp_dir/modified-terra
write_legacy_roles "$modified_terra"
printf '%s\n' modified >> "$modified_terra/$legacy_terra_file"
before=$(snapshot_files "$modified_terra")
if sh "$installer" --target-dir "$modified_terra"; then fail "installer replaced modified Terra"; fi
after=$(snapshot_files "$modified_terra")
[ "$before" = "$after" ] || fail "modified-Terra refusal partially mutated target"
pass "modified Terra refusal with zero partial mutation"

stale_luna=$tmp_dir/stale-luna
sh "$installer" --target-dir "$stale_luna"
stale_fixture=$tmp_dir/stale-fixture
write_legacy_roles "$stale_fixture"
cp "$stale_fixture/$legacy_luna_file" "$stale_luna/$luna_file"
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
test ! -e "$unsafe/$sol_low_file" || fail "symlink refusal partially installed Sol/Low"
test ! -e "$unsafe/$sol_medium_file" || fail "symlink refusal partially installed Sol/Medium"
test ! -e "$unsafe/$sol_high_file" || fail "symlink refusal partially installed Sol/High implementer"
pass "unsafe destination refusal with zero partial mutation"

state_home=$tmp_dir/state-home
legacy_state=$state_home/state/sol-advisor
current_state=$state_home/state/codex-orchestration
mkdir -p "$legacy_state/usage/effectiveness"
printf '%s\n' receipt-history > "$legacy_state/usage/task.json"
printf '%s\n' effectiveness-history > "$legacy_state/usage/effectiveness/baseline.json"
python3 "$state_migration" --codex-home "$state_home" >/dev/null
cmp -s "$legacy_state/usage/task.json" "$current_state/usage/task.json" || fail "receipt history was not copied forward"
cmp -s "$legacy_state/usage/effectiveness/baseline.json" "$current_state/usage/effectiveness/baseline.json" || fail "effectiveness history was not copied forward"
test -f "$current_state/.legacy-sol-advisor-state-migrated" || fail "state migration marker is missing"
printf '%s\n' late-legacy > "$legacy_state/usage/late.json"
printf '%s\n' changed-after-migration > "$legacy_state/usage/task.json"
python3 "$state_migration" --codex-home "$state_home" >/dev/null
test ! -e "$current_state/usage/late.json" || fail "one-time state migration reran after its marker"
grep -Fq receipt-history "$current_state/usage/task.json" || fail "one-time state migration overwrote history after its marker"

conflict_home=$tmp_dir/state-conflict
mkdir -p "$conflict_home/state/sol-advisor/usage" "$conflict_home/state/codex-orchestration/usage"
printf '%s\n' legacy > "$conflict_home/state/sol-advisor/usage/task.json"
printf '%s\n' current > "$conflict_home/state/codex-orchestration/usage/task.json"
if python3 "$state_migration" --codex-home "$conflict_home" >/dev/null 2>&1; then fail "state migration overwrote a conflicting new file"; fi
grep -Fq current "$conflict_home/state/codex-orchestration/usage/task.json" || fail "state conflict refusal changed new history"
test ! -e "$conflict_home/state/codex-orchestration/.legacy-sol-advisor-state-migrated" || fail "state conflict wrote a migration marker"

symlink_source_home=$tmp_dir/state-symlink-source
mkdir -p "$symlink_source_home/state" "$symlink_source_home/actual-legacy"
ln -s "$symlink_source_home/actual-legacy" "$symlink_source_home/state/sol-advisor"
if python3 "$state_migration" --codex-home "$symlink_source_home" >/dev/null 2>&1; then fail "state migration accepted a symlinked legacy source"; fi
symlink_destination_home=$tmp_dir/state-symlink-destination
mkdir -p "$symlink_destination_home/state/sol-advisor" "$symlink_destination_home/actual-current"
ln -s "$symlink_destination_home/actual-current" "$symlink_destination_home/state/codex-orchestration"
if python3 "$state_migration" --codex-home "$symlink_destination_home" >/dev/null 2>&1; then fail "state migration accepted a symlinked new destination"; fi
pass "one-time state copy-forward, no-overwrite conflicts, and symlink refusals"

runtime_sessions=$tmp_dir/runtime-sessions
runtime_day=$runtime_sessions/2026/08/02
mkdir -p "$runtime_day"
runtime_id=11111111-1111-7111-8111-111111111111
runtime_rollout=$runtime_day/rollout-2026-08-02T00-00-00-$runtime_id.jsonl
printf '%s\n' \
  '{"type":"response_item","payload":{"prompt":"DO_NOT_LEAK_PROMPT"}}' \
  "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$runtime_id\",\"parent_thread_id\":\"00000000-0000-7000-8000-000000000000\",\"agent_role\":\"codex_orchestration_terra_implementer\",\"agent_path\":\"/root/fixture\",\"model_provider\":\"openai\",\"cwd\":\"/fixture\"}}" \
  '{"type":"turn_context","payload":{"model":"gpt-5.6-terra","effort":"high","sandbox_policy":{"type":"danger-full-access"},"permission_profile":{"type":"disabled"},"cwd":"/fixture"}}' \
  > "$runtime_rollout"
runtime_output=$(sh "$runtime_inspector" --sessions-dir "$runtime_sessions" "$runtime_id")
printf '%s\n' "$runtime_output" | jq -e --arg id "$runtime_id" '
  .thread_id == $id and .agent_role == "codex_orchestration_terra_implementer"
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
  grep -Fq 'agent_type: codex_orchestration_terra_executive' "$document" || fail "missing Terra/High executive spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_luna_implementer' "$document" || fail "missing Luna/Max spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_terra_medium_implementer' "$document" || fail "missing Terra/Medium spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_terra_implementer' "$document" || fail "missing Terra/High spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_sol_low_implementer' "$document" || fail "missing Sol/Low spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_sol_medium_implementer' "$document" || fail "missing Sol/Medium spawn in $document"
  grep -Fq 'agent_type: codex_orchestration_sol_reviewer' "$document" || fail "missing Sol spawn in $document"
  grep -Fq 'fork_turns: none' "$document" || fail "missing fresh context in $document"
  grep -Fq 'task_name: luna_max_<objective_slug>' "$document" || fail "missing Luna Max visible task prefix in $document"
  grep -Fq 'task_name: terra_medium_<objective_slug>' "$document" || fail "missing Terra Medium visible task prefix in $document"
  grep -Fq 'task_name: terra_high_<objective_slug>' "$document" || fail "missing Terra High visible task prefix in $document"
  grep -Fq 'task_name: terra_high_exec_<objective_slug>' "$document" || fail "missing Terra High executive task prefix in $document"
  grep -Fq 'task_name: sol_low_<objective_slug>' "$document" || fail "missing Sol Low visible task prefix in $document"
  grep -Fq 'task_name: sol_medium_<objective_slug>' "$document" || fail "missing Sol Medium visible task prefix in $document"
  grep -Fq 'task_name: sol_high_review_<objective_slug>' "$document" || fail "missing Sol High reviewer task prefix in $document"
  if grep -Eq 'agent_type:.*terra_max' "$document"; then fail "retired implementation spawn remains in $document"; fi
  if grep -Eq '^[[:space:]]*(model|reasoning_effort):' "$document"; then fail "per-spawn override remains in $document"; fi
done
grep -Fq '../../scripts/install-agents.sh' "$skill" || fail "skill does not resolve installer relatively"
grep -Fq '../../scripts/reinstall-plugin.sh' "$skill" || fail "skill does not resolve safe reinstaller relatively"
grep -Fq '../../scripts/inspect-agent-runtime.sh' "$skill" || fail "skill does not resolve inspector relatively"
grep -Fqi 'Inspect public spawn metadata first' "$skill" || fail "skill lacks public-details-first evidence rule"
grep -Fqi 'before/after state proves no mutation' "$contracts" || fail "contracts lack behavioral read-only state check"
grep -Fq 'selected agent type. If unavailable' "$skill" || fail "skill still requires unrelated worker types"
grep -Fq 'unrelated roles do not block' "$contracts" || fail "contracts let unrelated roles block selected tier"
grep -Fq 'Announce the actual route only after current-turn preflight' "$skill" || fail "skill permits preflight after route announcement"
grep -Fq 'Complexity: <score>/10' "$skill" || fail "skill omits the visible numeric complexity score"
grep -Fq 'exact one-decimal score' "$skill" || fail "skill does not standardize visible complexity precision"
grep -Fq 'the exact one-decimal score before implementation' "$skill" || fail "skill does not persist complexity before work"
grep -Fq 'never revise it' "$skill" || fail "skill permits complexity drift after routing"
grep -Fq 'effectiveness-tracker.py' "$skill" || fail "skill omits the effectiveness tracker"
grep -Fq 'exact completed-task tokens' "$skill" || fail "skill omits exact per-task tokens"
grep -Fq 'infer or divide by a Profile chat count' "$skill" || fail "skill makes chat count the primary denominator"
grep -Fq 'skill_dir/references/role-contracts.md' "$skill" || fail "skill does not pin role-contract resolution to the skill directory"
grep -Fq 'relative path from it' "$skill" || fail "skill does not guard path resolution"
grep -Fq 'contents from an alias name' "$skill" || fail "skill mistakes a compatibility alias name for release identity"
grep -Fq 'incomplete plugin package is missing' "$reinstaller" || fail "reinstaller does not reject incomplete aliases"
grep -Fq 'already-open tasks may keep using version-looking paths' "$reinstaller" || fail "reinstaller hides the Desktop locator cache boundary"
for tool in list_projects list_threads create_thread wait_threads read_thread send_message_to_thread clientThreadId; do
  if rg -n "$tool" "$skill" "$contracts" "$readme" "$manifest"; then
    fail "retired Luna app-task tool remains: $tool"
  fi
done
grep -Fq 'model = "gpt-5.6-luna"' "$templates/$luna_file" || fail "Luna role omits Luna model pin"
grep -Fq 'model_reasoning_effort = "max"' "$templates/$luna_file" || fail "Luna role omits Max effort pin"
grep -Fq '| No implementation handoff |' "$readme" || fail "README omits no-handoff route"
grep -Fq 'the eight exact native role pins' "$readme" || fail "README does not describe the eight-role inventory"
grep -Fq 'eight roles: six implementation levels' "$readme" || fail "README omits eight-role/six-level inventory"
grep -Fq '| Luna producer |' "$readme" || fail "README omits Luna route"
grep -Fq '| Terra Medium producer |' "$readme" || fail "README omits Terra Medium route"
grep -Fq '| Terra High producer |' "$readme" || fail "README omits Terra High route"
grep -Fq '| Sol Low producer |' "$readme" || fail "README omits Sol Low route"
grep -Fq '| Sol Medium producer |' "$readme" || fail "README omits Sol Medium route"
grep -Fq '| Sol High implementation |' "$readme" || fail "README omits Sol High route"
for command in 'Turn Orchestration on' 'Use Orchestration' 'Use Orchestration for this chat'; do
  grep -Fq "$command" "$readme" || fail "README omits plain-language activation: $command"
done
grep -Fq 'Turn Orchestration off' "$readme" || fail "README omits plain-language deactivation"
grep -Fq 'Orchestration: ON for this chat' "$readme" || fail "README omits ON state marker"
grep -Fq 'Orchestration: OFF for this chat' "$readme" || fail "README omits OFF state marker"
grep -Fq '$codex-orchestration:orchestration' "$readme" || fail "README omits the namespaced skill invocation"
grep -Fq 'every later request in' "$readme" || fail "README omits persistent chat activation"
grep -Fq 'Every new chat starts off' "$readme" || fail "README permits cross-chat activation"
grep -Fq 'allow_implicit_invocation: true' "$ui" || fail "skill UI blocks plain-language activation"
for label in 'Luna / Max' 'Terra / Medium' 'Terra / High' 'Sol / Low' 'Sol / Medium' 'Sol / High'; do
  jq -r '.interface.longDescription' "$manifest" | grep -Fq "$label" || fail "manifest UI omits model route: $label"
done
grep -Fq 'Terra High executive ownership below 5.0' "$ui" || fail "skill UI omits low-band Terra ownership"
grep -Fq 'allow one correction' "$ui" || fail "skill UI omits bounded correction"
for command in 'Turn Orchestration on' 'Use Orchestration' 'Use Orchestration for this chat'; do
  grep -Fq "$command" "$skill" || fail "skill omits plain-language activation: $command"
done
grep -Fq 'Turn Orchestration off' "$skill" || fail "skill omits the off switch"
grep -Fq 'subsequent work normally' "$skill" || fail "skill omits persistent deactivation"
grep -Fq 'Use only direct assistant messages in the current chat' "$skill" || fail "skill accepts non-chat state markers"
grep -Fq 'latest current-chat marker wins' "$skill" || fail "skill does not define chat-local ON/OFF precedence"
grep -Fq 'Every new chat' "$skill" || fail "skill permits cross-chat activation"
grep -Fq 'plugin remains selected or enabled' "$skill" || fail "skill treats plugin state as activation"
grep -Fq 'memories, summaries' "$skill" || fail "skill permits remembered cross-chat activation"
grep -Fq 'Orchestration: ON for this chat' "$skill" || fail "skill omits initial ON acknowledgement"
grep -Fq 'Orchestration: OFF for this chat' "$skill" || fail "skill omits OFF acknowledgement"
grep -Fq '$codex-orchestration:orchestration' "$skill" || fail "skill omits the namespaced invocation"
grep -Fq '$codex-orchestration:orchestration' "$ui" || fail "skill UI omits the namespaced invocation"
if rg -Fq 'Turn Orchestration on for this chat' "$readme" "$skill" "$ui" "$manifest"; then
  fail "unsupported activation variant remains: Turn Orchestration on for this chat"
fi
for stale_command in 'Turn Codex Orchestration on' 'Turn Codex Orchestration off' 'Use Codex Orchestration' 'Codex Orchestration: ON' 'Codex Orchestration: OFF'; do
  if rg -Fq "$stale_command" "$readme" "$skill" "$ui" "$manifest"; then
    fail "stale Codex Orchestration plain-language control remains: $stale_command"
  fi
done
grep -Fq 'Executive design and review: GPT-5.6 Sol / High' "$skill" || fail "skill omits concise executive model line"
grep -Fq 'GPT-5.6 Terra / High executive' "$skill" || fail "skill omits low-band Terra executive"
grep -Fq 'Implementation: GPT-5.6 Sol / High — owning executive, no handoff' "$skill" || fail "skill omits same-model no-handoff route"
grep -Fq 'Save model credits by giving real work' "$skill" || fail "skill does not prioritize credit savings"
grep -Fq 'one bounded correction attempt' "$skill" || fail "skill omits bounded correction"
grep -Fq 'One preflight per task' "$contracts" || fail "contracts repeat preflight per agent"
grep -Fq 'Do not repeat the installer check' "$contracts" || fail "contracts permit redundant installer checks"
grep -Fq 'Owning-executive acceptance and correction' "$contracts" || fail "contracts omit bounded acceptance loop"
grep -Fq 'Low-band Terra executive' "$contracts" || fail "contracts omit active Terra executive"
grep -Fq 'normal finish omitted or mispriced a nested descendant' "$receipt_hook_test" || fail "hook fixture does not test normal nested receipt finish"
grep -Fq 'delegated Terra executive Stop required a separate receipt' "$receipt_hook_test" || fail "hook fixture omits delegated executive Stop suppression"
grep -Fq 'sole completion was not the root task' "$receipt_hook_test" || fail "hook fixture does not assert one root completion"
grep -Fq 'root low route directly spawned a producer before its executive' "$receipt_hook_test" || fail "hook fixture omits root-first executive enforcement"
grep -Fq 'Terra executive spawned a redundant same-model implementer' "$receipt_hook_test" || fail "hook fixture omits Terra no-handoff enforcement"
grep -Fq 'primary Sol spawned a redundant same-model implementer' "$receipt_hook_test" || fail "hook fixture omits Sol no-handoff enforcement"
grep -Fq 'Sol Low boundary route was rejected at score 6.6' "$receipt_hook_test" || fail "hook fixture omits Sol Low lower boundary"
grep -Fq 'Sol Medium boundary route was rejected at score 7.3' "$receipt_hook_test" || fail "hook fixture omits Sol Medium lower boundary"
grep -Fq 'fallback root Sol spawned a redundant same-model implementer' "$receipt_hook_test" || fail "hook fixture omits fallback Sol no-handoff enforcement"
grep -Fq 'valid Terra-to-Sol executive fallback was denied' "$receipt_hook_test" || fail "hook fixture omits monotonic fallback acceptance"
grep -Fq 'malformed executive fallback was accepted' "$receipt_hook_test" || fail "hook fixture omits malformed fallback denial"
grep -Fq 'fallback route moved downward to Terra' "$receipt_hook_test" || fail "hook fixture omits downward transition denial"
grep -Fq 'Stop did not reconstruct the persisted fallback' "$receipt_hook_test" || fail "hook fixture omits persisted fallback reconstruction"
grep -Fq 'session_role(transcript) == "codex_orchestration_terra_executive"' "$receipt_hook" || fail "Stop hook does not identify delegated Terra executive"
grep -Fq 'Implementation:' "$skill" || fail "skill omits pre-execution route announcement"
grep -Fq 'without separate model approval' "$skill" || fail "skill requires a second worker authorization"
grep -Fq '../../scripts/daily-upstream-audit.sh' "$skill" || fail "skill omits daily upstream audit"
if rg -n 'SOL ADVISOR ROUTING' "$skill" "$contracts" "$readme" "$manifest" "$ui"; then
  fail "retired verbose routing output remains"
fi
test ! -e "$plugin_dir/skills/orchestration/references/luna-task-lane.md" || fail "retired Luna task contract remains"
grep -Fq 'references/usage-receipt.md' "$skill" || fail "skill omits weekly usage receipt"
grep -Fq 'Actual weekly usage:' "$receipt_contract" || fail "usage receipt omits actual weekly usage"
grep -Fq 'All-Sol equivalent:' "$receipt_contract" || fail "usage receipt omits all-Sol equivalent"
grep -Fq 'Estimated task credits:' "$receipt_contract" || fail "usage receipt omits rate-based task credits fallback"
grep -Fq 'All-Sol equivalent credits:' "$receipt_contract" || fail "usage receipt omits rate-based all-Sol fallback"
grep -Fq 'Estimated routing savings:' "$receipt_contract" || fail "usage receipt omits routing savings"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$usage_receipt" || fail "usage receipt script does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$effectiveness_tracker" || fail "effectiveness tracker does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$effectiveness_test" || fail "effectiveness tracker test does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$receipt_hook" || fail "receipt Stop hook does not compile"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' "$receipt_hook_test" || fail "receipt Stop-hook test does not compile"
jq empty "$hook_config" || fail "receipt Stop-hook configuration is invalid JSON"
jq -er '.hooks.PreToolUse[0] | select(.matcher == "*") | .hooks[0] | select(.type == "command" and (.command | contains("receipt-stop-hook.py")))' "$hook_config" >/dev/null || fail "plugin hook does not register the complexity PreToolUse gate"
jq -er '.hooks.Stop[0].hooks[0] | select(.type == "command" and (.command | contains("receipt-stop-hook.py")))' "$hook_config" >/dev/null || fail "plugin hook does not register the receipt Stop gate"
grep -Fq 'receipt is a completion invariant' "$skill" || fail "skill permits skipping the receipt lifecycle"
grep -Fq 'Never draft the final answer before `finish`' "$skill" || fail "skill permits a final response before receipt finish"
grep -Fq 'Never omit the receipt' "$receipt_contract" || fail "receipt contract permits silent omission"
grep -Fq 'calibration did not exclude pre-context replay' "$receipt_hook_test" || fail "receipt fixture omits forked replay calibration regression"
grep -Fq 'completion gate rejected the rate-based fallback receipt' "$receipt_hook_test" || fail "receipt fixture omits rate-based completion fallback"
grep -Fq 'finish did not recover an unstarted task' "$receipt_hook_test" || fail "receipt fixture omits direct finish recovery"
python3 "$receipt_hook_test" "$plugin_dir" "$tmp_dir/receipt-hook" || fail "executive-band, fallback, complexity, receipt, or Stop-hook gate failed"
pass "both executive bands, fallback, complexity persistence, receipt recovery, and Stop-hook completion gate"
python3 "$effectiveness_test" "$plugin_dir" "$tmp_dir/effectiveness" || fail "effectiveness baseline, ledger, or comparison failed"
pass "effectiveness baseline, completion ledger, and comparison"
grep -Fq 'first activation of each local day' "$skill" || fail "skill omits once-daily activation boundary"
grep -Fq 'adopt unchanged' "$skill" || fail "skill omits upstream adoption classification"
grep -Fq 'adapt' "$skill" || fail "skill omits upstream adaptation classification"
grep -Fq 'skip' "$skill" || fail "skill omits upstream skip classification"
grep -Fq 'must not modify code or merge upstream' "$skill" || fail "skill permits automatic upstream merge"
grep -Fq 'merged into fork `main`' "$skill" || fail "skill does not require fork-main completion"
grep -Fq 'push to the original author' "$skill" || fail "skill permits pushes to upstream"
grep -Fq 'plain release versions without SemVer `+` build metadata' "$readme" || fail "README omits cache-compatible version policy"
grep -Fq 'reinstall-plugin.sh' "$readme" || fail "README omits safe plugin reinstall"

for document in "$readme" "$manifest" "$skill" "$contracts" "$ui"; do
  if grep -Eqi 'Terra / High is the sole implementation producer|one role-pinned .*handles all implementation|route all implementation through.*Terra|delegate all implementation to (the )?(native )?Terra' "$document"; then
    fail "stale single-mode implementation claim remains in $document"
  fi
done
forbidden_max='codex_orchestration_(terra|sol)_'"max"
forbidden_max_file='codex-orchestration-(terra|sol)-'"max"
if rg -n "$forbidden_max|$forbidden_max_file" "$readme" "$plugin_dir"; then fail "forbidden Max native role remains"; fi
pass "activation, automatic routing, reporting, and stale-claim checks"

grep -Fq 'Constitution: economical completion without delay spirals' "$skill" || fail "skill omits balanced constitution"
grep -Fq 'Minimum sufficient outcome' "$skill" || fail "skill omits minimum-sufficient gate"
grep -Fq '**Token budget:**' "$skill" || fail "skill omits token-budget gate"
grep -Fq '**Time budget:**' "$skill" || fail "skill omits time-budget gate"
grep -Fq 'Score every deliverable once from 1.0 to 10.0' "$skill" || fail "skill omits numeric complexity"
for band in '**1.0–2.9:** Luna / Max' '**3.0–5.0:** Terra / Medium' '**5.1–6.5:** Terra / High' '**6.6–7.2:** Sol / Low' '**7.3–7.9:** Sol / Medium' '**8.0–10.0:** Sol / High'; do
  grep -Fq "$band" "$skill" || fail "skill omits routing band: $band"
done
grep -Fq 'Anchor ordinary bounded work with settled requirements near 5.0' "$skill" || fail "skill lacks a score anchor"
grep -Fq 'A task being short is not by itself permission' "$skill" || fail "skill permits a short-work Sol bypass"
grep -Fq 'only the one mapped producer' "$skill" || fail "skill permits routine fan-out"
grep -Fq 'Use at most one unchanged spawn retry per tier' "$skill" || fail "skill permits repeated spawn retries"
grep -Fq 'give the same producer one bounded correction attempt' "$skill" || fail "skill omits one producer correction"
grep -Fq 'have the owning executive complete and verify' "$skill" || fail "skill omits executive takeover"
grep -Fq 'Do not spawn a replacement producer' "$skill" || fail "skill permits replacement-agent loops"
grep -Fq 'Luna Max → Terra Medium → Terra High executive' "$skill" || fail "skill omits low-band upward fallback ladder"
grep -Fq 'Terra Medium → Terra High → Sol Low → Sol Medium → primary Sol High' "$skill" || fail "skill omits high-band upward fallback ladder"
grep -Fq 'interrupt_agent' "$skill" || fail "skill omits interruption"
grep -Fq 'a stale worker plan automatically' "$skill" || fail "skill permits stale plans"
grep -Fq 'Only authoritative `task_complete` turns count' "$skill" || fail "skill omits completion authority"
grep -Fq 'EFFICIENCY BOUNDARY' "$contracts" || fail "contracts omit worker efficiency boundary"
grep -Fq 'replanning, not abandonment' "$contracts" || fail "contracts permit budget abandonment"
grep -Fq 'saves model credits without turning coordination into the task' "$readme" || fail "README omits balanced objective"
grep -Fq 'one precise correction attempt' "$readme" || fail "README omits bounded correction"
grep -Fq 'Terra / High so routine planning' "$readme" || fail "README omits low-band Terra ownership"
jq -r '.interface.longDescription' "$manifest" | grep -Fq 'Luna / Max at 1.0–2.9, Terra / Medium at 3.0–5.0, Terra / High at 5.1–6.5, Sol / Low at 6.6–7.2, Sol / Medium at 7.3–7.9, and Sol / High at 8.0–10.0' || fail "manifest omits numeric routing bands"
grep -Fq 'cheaper score-selected model' "$ui" || fail "skill UI omits savings route"
grep -Fq 'one executive acceptance check' "$ui" || fail "skill UI omits bounded acceptance"
pass "economical executive routing, self-check, bounded correction, and takeover policy"

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
grep -Fq 'jessejaffe/codex-orchestration' "$daily_audit" || fail "daily audit omits maintained fork"
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
CODEX_ORCHESTRATION_AUDIT_STATE_DIR="$audit_state" sh "$daily_audit" | \
  grep -Fq 'STATUS: already-checked-today' || fail "daily audit repeated a same-day network check"
audit_home=$tmp_dir/audit-home
mkdir -p "$audit_home/state/sol-advisor"
printf 'CHECKED_DATE: %s\nSTATUS: current\n' "$(date +%F)" > "$audit_home/state/sol-advisor/upstream-audit.txt"
CODEX_HOME="$audit_home" sh "$daily_audit" | grep -Fq 'STATUS: already-checked-today' ||
  fail "daily audit did not migrate and reuse exact legacy state"
test -f "$audit_home/state/codex-orchestration/upstream-audit.txt" || fail "daily audit did not copy legacy state forward"
pass "daily activation audit and non-merging upstream issue workflow"

sh -n "$installer"
sh -n "$reinstaller"
sh -n "$runtime_inspector"
sh -n "$daily_audit"
sh -n "$script_dir/verify.sh"
pass "shell syntax"

printf '%s\n' "VERIFY PASSED: Codex Orchestration eight-role/six-level migration and executive routing checks completed in $tmp_dir"
