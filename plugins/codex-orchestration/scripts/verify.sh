#!/bin/sh
# Verify the Codex Orchestration 0.13.0 single-agent workflow without network access.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH= cd "$script_dir/.." && pwd) || exit 1
agents=$plugin_dir/agents
manifest=$plugin_dir/.codex-plugin/plugin.json
repo_readme=$(CDPATH= cd "$plugin_dir/../.." && pwd)/README.md

for command in python3 jq shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required"
done

jq -e . "$manifest" >/dev/null || fail 'plugin manifest is invalid JSON'
[ "$(jq -r .name "$manifest")" = codex-orchestration ] || fail 'wrong plugin name'
manifest_version=$(jq -r .version "$manifest")
printf '%s\n' "$manifest_version" | grep -Eq '^0\.13\.0(\+codex\.[0-9A-Za-z._-]+)?$' ||
  fail "manifest version is not on the 0.13.0 development line: $manifest_version"
pass "manifest uses the 0.13.0 development line ($manifest_version)"

for shell_script in "$script_dir"/*.sh; do
  sh -n "$shell_script" || fail "invalid shell syntax: $shell_script"
done
for python_script in "$script_dir"/*.py; do
  python3 - "$python_script" <<'PY'
import pathlib
import sys
source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
compile(source, sys.argv[1], "exec")
PY
done
pass 'script syntax'

python3 - "$agents" <<'PY'
import pathlib
import sys
import tomllib

expected = {
    "codex-orchestration-terra-orchestrator.toml": ("gpt-5.6-terra", "xhigh"),
    "codex-orchestration-luna-implementer.toml": ("gpt-5.6-luna", "max"),
    "codex-orchestration-terra-implementer.toml": ("gpt-5.6-terra", "max"),
    "codex-orchestration-sol-high-implementer.toml": ("gpt-5.6-sol", "high"),
}
root = pathlib.Path(sys.argv[1])
actual = {path.name for path in root.glob("*.toml")}
if actual != set(expected):
    raise SystemExit(f"agent inventory mismatch: {actual!r}")
for name, pin in expected.items():
    document = tomllib.loads((root / name).read_text(encoding="utf-8"))
    if (document.get("model"), document.get("model_reasoning_effort")) != pin:
        raise SystemExit(f"wrong model pin: {name}")
    if not document.get("developer_instructions"):
        raise SystemExit(f"missing developer instructions: {name}")
    if "orchestrator" in name and document.get("sandbox_mode") != "read-only":
        raise SystemExit("classifier is not read-only")
    if "implementer" in name and "sandbox_mode" in document:
        raise SystemExit(f"end-to-end agent is unexpectedly read-only: {name}")
PY
pass 'exact four-profile inventory and model pins'

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
temporary=$(mktemp -d "$tmp_base/codex-orchestration-verify.XXXXXX") || fail 'cannot create temporary workspace'
cleanup() {
  case "${temporary:-}" in "$tmp_base"/codex-orchestration-verify.*) rm -rf "$temporary" ;; esac
}
trap cleanup EXIT HUP INT TERM

python3 "$script_dir/test-fast-dispatch.py" "$plugin_dir" "$temporary/dispatch"
python3 "$script_dir/test-relay-protocol.py" "$plugin_dir"
python3 "$script_dir/test-effectiveness-tracker.py" "$plugin_dir" "$temporary/effectiveness"
pass 'dispatch, relay, and effectiveness fixtures'

target=$temporary/agents
sh "$script_dir/install-agents.sh" --target-dir "$target" >/dev/null
sh "$script_dir/install-agents.sh" --target-dir "$target" --check >/dev/null
[ "$(find "$target" -maxdepth 1 -type f -name 'codex-orchestration-*.toml' | wc -l | tr -d ' ')" = 4 ] ||
  fail 'agent installer did not produce exactly four profiles'

printf '%s\n' '# user customization' >> "$target/codex-orchestration-luna-implementer.toml"
custom_digest=$(shasum -a 256 "$target/codex-orchestration-luna-implementer.toml" | awk '{print $1}')
if sh "$script_dir/install-agents.sh" --target-dir "$target" >/dev/null 2>&1; then
  fail 'agent installer overwrote a customized active profile'
fi
[ "$(shasum -a 256 "$target/codex-orchestration-luna-implementer.toml" | awk '{print $1}')" = "$custom_digest" ] ||
  fail 'customized active profile changed during rejected migration'
cp "$agents/codex-orchestration-luna-implementer.toml" "$target/codex-orchestration-luna-implementer.toml"

printf '%s\n' '# customized former supervisor' > "$target/codex-orchestration-terra-supervisor.toml"
retired_digest=$(shasum -a 256 "$target/codex-orchestration-terra-supervisor.toml" | awk '{print $1}')
if sh "$script_dir/install-agents.sh" --target-dir "$target" >/dev/null 2>&1; then
  fail 'agent installer deleted an unrecognized former supervisor'
fi
[ "$(shasum -a 256 "$target/codex-orchestration-terra-supervisor.toml" | awk '{print $1}')" = "$retired_digest" ] ||
  fail 'customized former supervisor changed during rejected migration'
pass 'conflict-safe four-profile installer behavior'

grep -Fq 'requires the 0.13.0 development line' "$script_dir/reinstall-plugin.sh" ||
  fail 'reinstaller does not enforce the 0.13.0 development line'
for role in terra-orchestrator luna-implementer terra-implementer sol-high-implementer; do
  grep -Fq "agents/codex-orchestration-$role.toml" "$script_dir/reinstall-plugin.sh" ||
    fail "reinstaller package inventory omits $role"
done
if grep -Eq 'agents/codex-orchestration-(terra|sol-high|sol-xhigh)-supervisor\.toml' "$script_dir/reinstall-plugin.sh"; then
  fail 'reinstaller package inventory retains supervisor profiles'
fi
pass 'reinstaller package inventory'

if [ -f "$repo_readme" ] && [ ! -L "$repo_readme" ]; then
  for value in \
    'two-stage workflow' \
    'Terra / Extra High classifies' \
    'One selected agent owns the task end to end' \
    'There is exactly one task agent after classification' \
    'READ_ONLY' \
    'STANDARD_ARTIFACT' \
    'DESIGN_ARTIFACT' \
    'SMALL_TWEAK' \
    'BIG_TWEAK' \
    'SMALL_BUILD' \
    'BIG_BUILD' \
    'Root-only visual evidence' \
    'defining outcome depends on' \
    'terminal handoff' \
    'Ground truth' \
    'Root checks once' \
    'never hands the check back' \
    "work performed remains the report's primary content" \
    'mentioned only as the second Next step' \
    'actual work next step' \
    'A request to implement locally does not itself authorize deployment' \
    '## Reports' \
    'no Recommendations section' \
    'Actionable future guidance belongs only in Next' \
    'Next step section gives an evidence-backed action' \
    'never invents work' \
    'four companion profiles' \
    '0.13.0'; do
    grep -Fq "$value" "$repo_readme" || fail "README omits $value"
  done
  if grep -Fq 'Supervision: None' "$repo_readme"; then
    fail 'README retains the removed supervision route receipt'
  fi
  if grep -Fxq '## Route' "$repo_readme"; then
    fail 'README retains the removed route receipt'
  fi
  pass '0.13.0 workflow documentation'
else
  pass 'repository documentation is intentionally outside the installed plugin package'
fi

pass 'Codex Orchestration 0.13.0 single-agent verification complete'
