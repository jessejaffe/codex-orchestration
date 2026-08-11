#!/bin/sh
# Install Codex Orchestration 0.8.16 and safely retire obsolete identities.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH= cd "$script_dir/.." && pwd) || exit 1
manifest=$plugin_dir/.codex-plugin/plugin.json
codex_bin=${CODEX_ORCHESTRATION_CODEX_BIN:-${SOL_ADVISOR_CODEX_BIN:-codex}}
marketplace=${CODEX_ORCHESTRATION_MARKETPLACE:-codex-orchestration}
# Compatibility fallback: SOL_ADVISOR_MARKETPLACE names only the legacy marketplace.
legacy_marketplace=${CODEX_ORCHESTRATION_LEGACY_MARKETPLACE:-${SOL_ADVISOR_MARKETPLACE:-sol-advisor}}
current_plugin_id=codex-orchestration@$marketplace
legacy_plugin_id=sol-advisor@$legacy_marketplace

[ "$marketplace" != "$legacy_marketplace" ] ||
  fail "current and legacy marketplace names must be distinct: $marketplace"

command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v "$codex_bin" >/dev/null 2>&1 || fail "Codex executable not found: $codex_bin"
[ -f "$manifest" ] && [ ! -L "$manifest" ] || fail "plugin manifest is missing or unsafe: $manifest"
manifest_name=$(jq -er '.name | select(. == "codex-orchestration")' "$manifest") || fail "plugin manifest name must be codex-orchestration"
manifest_version=$(jq -er '.version | select(type == "string" and length > 0)' "$manifest") || fail "plugin manifest has no valid version"
printf '%s\n' "$manifest_version" | grep -Eq '^0\.8\.16$' ||
  fail "this installer requires the traditional release version 0.8.16: $manifest_version"

if [ -n "${CODEX_ORCHESTRATION_CACHE_ROOT:-}" ]; then
  cache_root=$CODEX_ORCHESTRATION_CACHE_ROOT
elif [ -n "${CODEX_HOME:-}" ]; then
  cache_root=$CODEX_HOME/plugins/cache/codex-orchestration/codex-orchestration
else
  [ -n "${HOME-}" ] || fail "HOME and CODEX_HOME are unset"
  cache_root=$HOME/.codex/plugins/cache/codex-orchestration/codex-orchestration
fi
if [ -n "${CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT:-}" ]; then
  legacy_cache_root=$CODEX_ORCHESTRATION_LEGACY_CACHE_ROOT
elif [ -n "${SOL_ADVISOR_CACHE_ROOT:-}" ]; then
  legacy_cache_root=$SOL_ADVISOR_CACHE_ROOT
elif [ -n "${CODEX_HOME:-}" ]; then
  legacy_cache_root=$CODEX_HOME/plugins/cache/sol-advisor/sol-advisor
else
  legacy_cache_root=$HOME/.codex/plugins/cache/sol-advisor/sol-advisor
fi
if [ -n "${CODEX_HOME:-}" ]; then
  codex_config=$CODEX_HOME/config.toml
else
  codex_config=$HOME/.codex/config.toml
fi
for root in "$cache_root" "$legacy_cache_root"; do case "$root" in /*) ;; *) fail "cache root must be absolute: $root" ;; esac; done
[ "$cache_root" != "$legacy_cache_root" ] || fail "current and legacy cache roots must be distinct"

plugin_list() { "$codex_bin" plugin list --json; }
installed_version() {
  plugin_list | jq -er --arg id "$1" '[.installed[] | select(.pluginId == $id)][0].version | select(type == "string" and length > 0)'
}
marketplace_exists() {
  listing=$("$codex_bin" plugin marketplace list --json) || return 2
  printf '%s\n' "$listing" | jq -e . >/dev/null || return 2
  if printf '%s\n' "$listing" | jq -e --arg name "$1" '.. | strings | select(. == $name)' >/dev/null; then
    return 0
  fi
  return 1
}

legacy_config_enabled() {
  [ -f "$codex_config" ] || return 1
  grep -Eq '^[[:space:]]*\[plugins\."sol-advisor@sol-advisor"\][[:space:]]*$' "$codex_config"
}

is_version_alias() {
  printf '%s\n' "$1" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(\+codex\.[0-9A-Za-z._-]+)?$'
}

validate_cache_root() {
  root=$1
  [ ! -L "$root" ] || fail "refusing symlinked cache root: $root"
  [ ! -e "$root" ] || [ -d "$root" ] || fail "cache root is not a directory: $root"
  [ ! -d "$root" ] && return 0
  for cached in "$root"/*; do
    [ -e "$cached" ] || [ -L "$cached" ] || continue
    name=$(basename "$cached")
    is_version_alias "$name" || fail "refusing non-version cache entry: $cached"
    [ ! -L "$cached" ] || fail "refusing symlinked version cache entry: $cached"
    [ -d "$cached" ] || fail "version cache entry is not a directory: $cached"
  done
}

required_package_files() {
  cat <<'EOF'
.codex-plugin/plugin.json
agents/codex-orchestration-luna-implementer.toml
agents/codex-orchestration-terra-implementer.toml
agents/codex-orchestration-sol-high-implementer.toml
agents/codex-orchestration-terra-supervisor.toml
agents/codex-orchestration-sol-high-supervisor.toml
agents/codex-orchestration-sol-xhigh-supervisor.toml
scripts/effectiveness-tracker.py
scripts/inspect-agent-runtime.sh
scripts/install-agents.sh
scripts/install-user-hook.py
scripts/orchestration_state.py
scripts/prompt-router-hook.py
scripts/reinstall-plugin.sh
scripts/state_migration.py
scripts/test-effectiveness-tracker.py
scripts/test-fast-dispatch.py
scripts/test-relay-protocol.py
scripts/triage-cases.json
scripts/usage-receipt.py
scripts/verify.sh
EOF
}

package_is_complete() {
  package=$1
  [ -d "$package" ] && [ ! -L "$package" ] || return 1
  required_package_files | while IFS= read -r relative; do
    [ -f "$package/$relative" ] && [ ! -L "$package/$relative" ] || exit 1
  done || return 1
  [ "$(jq -r .name "$package/.codex-plugin/plugin.json" 2>/dev/null)" = codex-orchestration ] || return 1
  [ "$(jq -r .version "$package/.codex-plugin/plugin.json" 2>/dev/null)" = "$manifest_version" ] || return 1
}

validate_complete_package() {
  package=$1
  [ -d "$package" ] && [ ! -L "$package" ] || fail "plugin cache is missing or unsafe: $package"
  required_package_files | while IFS= read -r relative; do
    [ -f "$package/$relative" ] && [ ! -L "$package/$relative" ] || {
      printf '%s\n' "FAIL: incomplete plugin package is missing $relative: $package" >&2
      exit 1
    }
  done || exit 1
  [ "$(jq -r .name "$package/.codex-plugin/plugin.json")" = codex-orchestration ] || fail "cached package has the wrong plugin name: $package"
  [ "$(jq -r .version "$package/.codex-plugin/plugin.json")" = "$manifest_version" ] || fail "cached package has the wrong version: $package"
}

append_alias_name() {
  name=$1
  output=$2
  is_version_alias "$name" || fail "refusing non-version cache alias: $name"
  printf '%s\n' "$name" >> "$output"
  case "$name" in *+*) printf '%s\n' "${name%%+*}" >> "$output" ;; esac
}

collect_aliases() {
  root=$1
  output=$2
  skip=${3-}
  [ -d "$root" ] || return 0
  for cached in "$root"/*; do
    [ -e "$cached" ] || [ -L "$cached" ] || continue
    name=$(basename "$cached")
    is_version_alias "$name" || continue
    [ "$name" != "$skip" ] || continue
    [ -d "$cached" ] && [ ! -L "$cached" ] || fail "unsafe version cache alias: $cached"
    append_alias_name "$name" "$output"
  done
}

prepare_transaction() {
  root=$1
  names=$2
  transaction=$3
  parent=$(dirname "$root")
  [ ! -L "$parent" ] || fail "refusing symlinked cache parent: $parent"
  mkdir -p "$parent" || fail "could not create cache parent: $parent"
  [ ! -e "$transaction" ] && [ ! -L "$transaction" ] || fail "transaction path already exists: $transaction"
  mkdir -p "$transaction/staged" "$transaction/backups" "$transaction/displaced" || fail "could not create alias transaction"
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    cp -Rp "$current_cache" "$transaction/staged/$name" || fail "could not stage complete cache alias: $root/$name"
    validate_complete_package "$transaction/staged/$name"
    diff -qr "$current_cache" "$transaction/staged/$name" >/dev/null || fail "staged cache alias differs from $manifest_version: $root/$name"
  done < "$names"
}

activate_transaction() {
  root=$1
  names=$2
  transaction=$3
  mkdir -p "$root" || return 1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    destination=$root/$name
    if [ -e "$destination" ] || [ -L "$destination" ]; then
      [ -d "$destination" ] && [ ! -L "$destination" ] || return 1
      mv "$destination" "$transaction/backups/$name" || return 1
    fi
    mv "$transaction/staged/$name" "$destination" || return 1
  done < "$names"
}

complete_transaction() {
  root=$1
  names=$2
  transaction=$3
  mkdir -p "$root" || return 1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    destination=$root/$name
    if package_is_complete "$destination" && diff -qr "$current_cache" "$destination" >/dev/null; then
      continue
    fi
    if [ -e "$destination" ] || [ -L "$destination" ]; then
      displaced=$transaction/displaced/$name
      [ ! -e "$displaced" ] && [ ! -L "$displaced" ] || displaced=$transaction/displaced/$name.$$
      mv "$destination" "$displaced" || return 1
    fi
    [ -d "$transaction/staged/$name" ] || return 1
    mv "$transaction/staged/$name" "$destination" || return 1
    package_is_complete "$destination" && diff -qr "$current_cache" "$destination" >/dev/null || return 1
  done < "$names"
}

check_aliases() {
  root=$1
  names=$2
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    alias=$root/$name
    validate_complete_package "$alias"
    diff -qr "$current_cache" "$alias" >/dev/null || fail "cache alias differs from $manifest_version: $alias"
  done < "$names"
}

check_current() {
  current=$(installed_version "$current_plugin_id") || fail "Codex Orchestration is not installed"
  [ "$current" = "$manifest_version" ] || fail "installed version $current does not match $manifest_version"
  current_cache=$cache_root/$manifest_version
  validate_complete_package "$current_cache"
  for root in "$cache_root" "$legacy_cache_root"; do
    validate_cache_root "$root"
    [ -d "$root" ] || continue
    for alias in "$root"/*; do
      [ -e "$alias" ] || [ -L "$alias" ] || continue
      name=$(basename "$alias")
      is_version_alias "$name" || continue
      validate_complete_package "$alias"
      diff -qr "$current_cache" "$alias" >/dev/null || fail "cache alias differs from $manifest_version: $alias"
    done
  done
  installed_version "$legacy_plugin_id" >/dev/null 2>&1 && fail "legacy plugin identity remains installed: $legacy_plugin_id"
  legacy_config_enabled && fail "legacy plugin enablement remains in $codex_config"
  marketplace_status=0
  marketplace_exists "$legacy_marketplace" || marketplace_status=$?
  case "$marketplace_status" in
    0) fail "legacy marketplace remains configured: $legacy_marketplace" ;;
    1) ;;
    *) fail "could not verify configured marketplaces" ;;
  esac
  pass "Codex Orchestration $manifest_version is installed without legacy plugin or marketplace identities"
}

check_user_hook() {
  python3 "$current_cache/scripts/install-user-hook.py" --check --codex-bin "$codex_bin" --plugin-dir "$current_cache"
}

case "${1:-}" in
  --check) [ "$#" -eq 1 ] || fail "usage: $0 [--check]"; check_current; check_user_hook; exit 0 ;;
  '') [ "$#" -eq 0 ] || fail "usage: $0 [--check]" ;;
  *) fail "usage: $0 [--check]" ;;
esac

validate_cache_root "$cache_root"
validate_cache_root "$legacy_cache_root"
tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
tmp_dir=$(mktemp -d "$tmp_base/codex-orchestration-reinstall.XXXXXX") || fail "could not create temporary workspace"
new_aliases=$tmp_dir/new-aliases
legacy_aliases=$tmp_dir/legacy-aliases
: > "$new_aliases"
: > "$legacy_aliases"
collect_aliases "$cache_root" "$new_aliases" "$manifest_version"
collect_aliases "$legacy_cache_root" "$legacy_aliases"
legacy_version=''
if legacy_version=$(installed_version "$legacy_plugin_id" 2>/dev/null); then append_alias_name "$legacy_version" "$legacy_aliases"; fi
legacy_marketplace_present=0
marketplace_status=0
marketplace_exists "$legacy_marketplace" || marketplace_status=$?
case "$marketplace_status" in
  0) legacy_marketplace_present=1 ;;
  1) ;;
  *) fail "could not inspect configured marketplaces before migration" ;;
esac
LC_ALL=C sort -u "$new_aliases" -o "$new_aliases"
LC_ALL=C sort -u "$legacy_aliases" -o "$legacy_aliases"

new_transaction=$(dirname "$cache_root")/.$(basename "$cache_root").codex-orchestration-aliases.$$
legacy_transaction=$(dirname "$legacy_cache_root")/.$(basename "$legacy_cache_root").codex-orchestration-aliases.$$
new_activation_started=0
legacy_removal_started=0
transactions_ready=0
transaction_committed=0
cleanup() {
  transaction_found=0
  for transaction in "${new_transaction-}" "${legacy_transaction-}"; do
    [ -n "$transaction" ] && [ -d "$transaction" ] || continue
    transaction_found=1
    case "$transaction" in
      */.*.codex-orchestration-aliases.[0-9]*)
        if [ "$transaction_committed" -eq 1 ]; then
          rm -rf "$transaction"
        else
          printf '%s\n' "NOTICE: preserving recoverable alias transaction after incomplete migration: $transaction" >&2
        fi
        ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected transaction: $transaction" >&2 ;;
    esac
  done
  if [ -n "${tmp_dir:-}" ] && [ -d "$tmp_dir" ]; then
    case "$tmp_dir" in
      "$tmp_base"/codex-orchestration-reinstall.*)
        if [ "$transaction_committed" -eq 1 ] || [ "$transaction_found" -eq 0 ]; then
          rm -rf "$tmp_dir"
        else
          printf '%s\n' "NOTICE: preserving alias inventory for incomplete migration: $tmp_dir" >&2
        fi
        ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}
recover_complete_aliases() {
  status=0
  if [ "$transactions_ready" -eq 1 ] && [ "$new_activation_started" -eq 1 ]; then
    complete_transaction "$cache_root" "$new_aliases" "$new_transaction" || status=1
  fi
  if [ "$transactions_ready" -eq 1 ] && [ "$legacy_removal_started" -eq 1 ]; then
    complete_transaction "$legacy_cache_root" "$legacy_aliases" "$legacy_transaction" || status=1
  fi
  return "$status"
}
interrupted() {
  trap - HUP INT TERM
  recover_complete_aliases || printf '%s\n' 'FAIL: interruption recovery could not complete every prepared alias' >&2
  exit 130
}
trap cleanup 0
trap interrupted HUP INT TERM

install_status=0
"$codex_bin" plugin add "$current_plugin_id" || install_status=$?
[ "$install_status" -eq 0 ] || fail "Codex Orchestration install failed with status $install_status; legacy identities were not removed"
current=$(installed_version "$current_plugin_id") || fail "new plugin was not listed after installation; legacy identities were not removed"
[ "$current" = "$manifest_version" ] || fail "new installed version is $current, expected $manifest_version; legacy identities were not removed"
current_cache=$cache_root/$manifest_version
validate_complete_package "$current_cache"

# A complete, conflict-free six-profile install is a prerequisite for retiring either
# legacy configured identity. The companion installer preflights every current and
# legacy file, proves all six current files, and only then removes exact obsolete
# legacy files. Customized legacy agents therefore stop this migration without being
# overwritten and before plugin or marketplace removal.
sh "$current_cache/scripts/install-agents.sh"
sh "$current_cache/scripts/install-agents.sh" --check

# Every replacement is copied and validated in same-filesystem sibling transactions
# before any legacy identity is removed. Activation uses renames only; backups remain
# recoverable until every destination has been validated.
prepare_transaction "$cache_root" "$new_aliases" "$new_transaction"
prepare_transaction "$legacy_cache_root" "$legacy_aliases" "$legacy_transaction"
transactions_ready=1
new_activation_started=1
if ! activate_transaction "$cache_root" "$new_aliases" "$new_transaction"; then
  recover_complete_aliases || fail "current alias activation failed and recovery was incomplete"
  fail "current alias activation failed; every prepared alias was completed"
fi
check_aliases "$cache_root" "$new_aliases"

legacy_removal_started=1
remove_status=0
# `plugin remove` is intentionally unconditional and idempotent. A previous updater
# could remove the legacy marketplace first and leave its enabled config table behind,
# even though `plugin list` no longer exposed that orphaned identity.
"$codex_bin" plugin remove "$legacy_plugin_id" || remove_status=$?
if [ "$remove_status" -ne 0 ]; then
  recover_complete_aliases || fail "legacy plugin removal failed and alias recovery was incomplete"
  fail "could not clear legacy plugin identity $legacy_plugin_id; complete version-cache copies were restored"
fi

legacy_removal_started=1
if ! activate_transaction "$legacy_cache_root" "$legacy_aliases" "$legacy_transaction"; then
  recover_complete_aliases || fail "legacy alias activation failed and recovery was incomplete"
  fail "legacy alias activation failed; every prepared alias was completed"
fi
check_aliases "$legacy_cache_root" "$legacy_aliases"

if [ "$legacy_marketplace_present" -eq 1 ]; then
  marketplace_status=0
  "$codex_bin" plugin marketplace remove "$legacy_marketplace" || marketplace_status=$?
  [ "$marketplace_status" -eq 0 ] || fail "legacy marketplace remains configured: $legacy_marketplace"
fi

python3 "$current_cache/scripts/install-user-hook.py" --codex-bin "$codex_bin" --plugin-dir "$current_cache"
check_current
transaction_committed=1
check_user_hook
pass "staged, atomically activated, and verified every recognized $manifest_version cache alias"
pass "cleared legacy plugin configuration $legacy_plugin_id after proving the replacement"
[ "$legacy_marketplace_present" -eq 0 ] || pass "removed legacy marketplace $legacy_marketplace independently"
printf '%s\n' "NOTICE: the first user-level hook install is available to new tasks; later releases update the stable runtime in place without desktop UI automation."
