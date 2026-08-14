#!/bin/sh
# Verify the official Codex Orchestration 0.9.0 single-agent workflow without network access.

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
[ "$manifest_version" = '0.9.0' ] ||
  fail "manifest version is not official version 0.9.0: $manifest_version"
pass "manifest uses official version 0.9.0"

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

grep -Fq 'requires official version 0.9.0' "$script_dir/reinstall-plugin.sh" ||
  fail 'reinstaller does not enforce official version 0.9.0'
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
    'automated, complexity-aware model router' \
    'Terra / Extra High evaluates each request' \
    'lightest model lane suited' \
    'without having to choose a' \
    'One routed implementer takes the task through implementation' \
    'terminal visual' \
    'user-facing result' \
    'Terra / Extra High evaluates scope + complexity' \
    'After classification, execution stays with one routed implementer' \
    'READ_ONLY' \
    'STANDARD_ARTIFACT' \
    'DESIGN_ARTIFACT' \
    'SMALL_TWEAK' \
    'BIG_TWEAK' \
    'SMALL_BUILD' \
    'BIG_BUILD' \
    '## Visual verification' \
    'Root verification is required' \
    'defining outcome depends on' \
    'Ground truth' \
    'Root checks once' \
    'never hands the check back' \
    "work performed remains the report's primary content" \
    'briefly explained after' \
    'work account rather than replacing it' \
    'A request to implement locally does not itself authorize deployment' \
    '## Reports' \
    'relayed verbatim to the user' \
    'Root does not summarize, condense, or add a second completion response' \
    'compact route footer naming the work class, selected implementation lane, and root' \
    'Each report ends with a mandatory Next step section' \
    'Every completed report finishes with this mandatory ending' \
    '## Next step' \
    'None — no next step is needed.' \
    '- Class: <friendly class>' \
    '- Implementation: <selected model lane>' \
    '- Root: <CURRENT_ROOT_ROUTE>' \
    'natural-language account rather than a fixed' \
    'evidence, with links, limitations, or open work' \
    'real follow-on action exists' \
    'never invents work to fill the required section' \
    '## Background' \
    'DannyMac180' \
    'added latency and complexity' \
    'sub-agent handoffs' \
    'four companion profiles' \
    '0.9.0'; do
    grep -Fq -e "$value" "$repo_readme" || fail "README omits $value"
  done
  if grep -Fq -e '- Supervision:' "$repo_readme"; then
    fail 'README retains supervision in the route receipt'
  fi
  pass '0.9.0 workflow documentation'
else
  pass 'repository documentation is intentionally outside the installed plugin package'
fi

pass 'Codex Orchestration 0.9.0 single-agent verification complete'
