#!/bin/sh
# Verify the Codex Orchestration 0.8.17 release without network access.

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
[ "$(jq -r .version "$manifest")" = 0.8.17 ] || fail 'manifest version must be exactly 0.8.17'
printf '%s\n' "$(jq -r .version "$manifest")" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' ||
  fail 'manifest must use traditional semantic versioning without a cachebuster'
pass 'manifest uses traditional version 0.8.17'

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
    "codex-orchestration-luna-implementer.toml": ("gpt-5.6-luna", "max"),
    "codex-orchestration-terra-implementer.toml": ("gpt-5.6-terra", "max"),
    "codex-orchestration-sol-high-implementer.toml": ("gpt-5.6-sol", "high"),
    "codex-orchestration-terra-supervisor.toml": ("gpt-5.6-terra", "max"),
    "codex-orchestration-sol-high-supervisor.toml": ("gpt-5.6-sol", "high"),
    "codex-orchestration-sol-xhigh-supervisor.toml": ("gpt-5.6-sol", "xhigh"),
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
    if "supervisor" in name:
        if document.get("sandbox_mode") != "read-only":
            raise SystemExit(f"read-only role is not sandboxed: {name}")
PY
pass 'exact six-profile inventory; fused router is pinned to Terra / Max'

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
[ "$(find "$target" -maxdepth 1 -type f -name 'codex-orchestration-*.toml' | wc -l | tr -d ' ')" = 6 ] ||
  fail 'agent installer did not produce exactly six companion profiles'
printf '%s\n' '# user customization' >> "$target/codex-orchestration-luna-implementer.toml"
custom_digest=$(shasum -a 256 "$target/codex-orchestration-luna-implementer.toml" | awk '{print $1}')
if sh "$script_dir/install-agents.sh" --target-dir "$target" >/dev/null 2>&1; then
  fail 'agent installer overwrote a customized current role'
fi
[ "$(shasum -a 256 "$target/codex-orchestration-luna-implementer.toml" | awk '{print $1}')" = "$custom_digest" ] ||
  fail 'customized current role changed during rejected migration'
cp "$agents/codex-orchestration-luna-implementer.toml" "$target/codex-orchestration-luna-implementer.toml"
printf '%s\n' '# customized retired role' > "$target/codex-orchestration-terra-medium-implementer.toml"
retired_digest=$(shasum -a 256 "$target/codex-orchestration-terra-medium-implementer.toml" | awk '{print $1}')
if sh "$script_dir/install-agents.sh" --target-dir "$target" >/dev/null 2>&1; then
  fail 'agent installer deleted an unrecognized retired role'
fi
[ "$(shasum -a 256 "$target/codex-orchestration-terra-medium-implementer.toml" | awk '{print $1}')" = "$retired_digest" ] ||
  fail 'customized retired role changed during rejected migration'
pass 'conflict-safe six-profile installer behavior'

grep -Fq "requires the traditional release version 0.8.17" "$script_dir/reinstall-plugin.sh" ||
  fail 'reinstaller does not enforce 0.8.17'
for role in luna-implementer terra-implementer sol-high-implementer terra-supervisor sol-high-supervisor sol-xhigh-supervisor; do
  grep -Fq "agents/codex-orchestration-$role.toml" "$script_dir/reinstall-plugin.sh" ||
    fail "reinstaller package inventory omits $role"
done
if grep -Eq 'agents/codex-orchestration-(terra-read-only|terra-grader|terra-executive|sol-(high|xhigh)-executive)\.toml' "$script_dir/reinstall-plugin.sh"; then
  fail 'reinstaller package inventory retains retired custom identities'
fi
pass 'reinstaller package inventory'

if [ -f "$repo_readme" ] && [ ! -L "$repo_readme" ]; then
  for value in \
    'READ_ONLY' \
    'SMALL_TWEAK' \
    'BIG_TWEAK' \
    'SMALL_BUILD' \
    'BIG_BUILD' \
    'binary gate' \
    'directly in root' \
    'open commitments' \
    'same implementer' \
    'ongoing task' \
    'waits until an agent' \
    'six companion profiles' \
    'standard service tier' \
    'ROOT_EXPERIENCE:' \
    'root-only Browser/visual check' \
    '0.8.17'; do
    grep -Fq "$value" "$repo_readme" || fail "README omits $value"
  done
  if grep -Eq '0\.8\.0\+codex|cachebuster version|seven implementation lanes|numeric routing' "$repo_readme"; then
    fail 'README still teaches the old version or routing scheme'
  fi
  pass '0.8.17 documentation'
else
  pass 'repository documentation is intentionally outside the installed plugin package'
fi

pass 'Codex Orchestration 0.8.17 release verification complete'
