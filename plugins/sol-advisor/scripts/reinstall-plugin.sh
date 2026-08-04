#!/bin/sh
# Reinstall Sol Advisor without leaving stale skill paths in Codex Desktop.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
plugin_dir=$(CDPATH= cd "$script_dir/.." && pwd) || exit 1
manifest=$plugin_dir/.codex-plugin/plugin.json
codex_bin=${SOL_ADVISOR_CODEX_BIN:-codex}
marketplace=${SOL_ADVISOR_MARKETPLACE:-sol-advisor}

command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v "$codex_bin" >/dev/null 2>&1 || fail "Codex executable not found: $codex_bin"
test -f "$manifest" || fail "plugin manifest is missing: $manifest"

manifest_version=$(jq -er '.version | select(type == "string" and length > 0)' "$manifest") || \
  fail "plugin manifest has no valid version"
case "$manifest_version" in
  *+*) fail "plugin version must not contain build metadata: $manifest_version" ;;
  [0-9]*.[0-9]*.[0-9]*) ;;
  *) fail "plugin version must be a numeric release version: $manifest_version" ;;
esac

if [ -n "${SOL_ADVISOR_CACHE_ROOT:-}" ]; then
  cache_root=$SOL_ADVISOR_CACHE_ROOT
elif [ -n "${CODEX_HOME:-}" ]; then
  cache_root=$CODEX_HOME/plugins/cache/sol-advisor/sol-advisor
else
  cache_root=$HOME/.codex/plugins/cache/sol-advisor/sol-advisor
fi
case "$cache_root" in /*) ;; *) fail "cache root must be absolute: $cache_root" ;; esac

installed_version() {
  "$codex_bin" plugin list --json | jq -er '
    [.installed[] | select(.pluginId == "sol-advisor@sol-advisor")][0].version
    | select(type == "string" and length > 0)
  '
}

check_current() {
  current=$(installed_version) || fail "Sol Advisor is not installed"
  [ "$current" = "$manifest_version" ] || \
    fail "installed version $current does not match manifest $manifest_version"
  current_cache=$cache_root/$manifest_version
  current_skill=$current_cache/skills/orchestration/SKILL.md
  test -f "$current_skill" || fail "installed skill cache is missing: $current_skill"

  for cached in "$cache_root"/*; do
    [ -e "$cached" ] || [ -L "$cached" ] || continue
    name=$(basename "$cached")
    case "$name" in
      *[!0-9A-Za-z.+_-]*) fail "unsafe cache entry name: $name" ;;
    esac
    [ ! -L "$cached" ] || fail "refusing symlinked cache entry: $cached"
    [ -d "$cached" ] || fail "cache entry is not a directory: $cached"
    for required_relative in \
      .codex-plugin/plugin.json \
      hooks/hooks.json \
      scripts/receipt-stop-hook.py \
      scripts/usage-receipt.py \
      skills/orchestration/SKILL.md \
      skills/orchestration/references/role-contracts.md \
      skills/orchestration/references/usage-receipt.md
    do
      test -f "$cached/$required_relative" || \
        fail "incomplete plugin cache alias is missing $required_relative: $cached"
    done
    diff -qr "$current_cache" "$cached" >/dev/null || \
      fail "stale plugin cache alias does not match $manifest_version: $cached"
  done

  pass "installed version and every skill cache alias match $manifest_version"
}

case "${1:-}" in
  --check) [ "$#" -eq 1 ] || fail "usage: $0 [--check]"; check_current; exit 0 ;;
  '') [ "$#" -eq 0 ] || fail "usage: $0 [--check]" ;;
  *) fail "usage: $0 [--check]" ;;
esac

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
tmp_dir=$(mktemp -d "$tmp_base/sol-advisor-reinstall.XXXXXX") || \
  fail "could not create a disposable backup directory"
backup_root=$tmp_dir/cache
mkdir -p "$backup_root"
backup_ready=0

cleanup() {
  if [ -n "${tmp_dir:-}" ] && [ -d "$tmp_dir" ]; then
    case "$tmp_dir" in
      "$tmp_base"/sol-advisor-reinstall.*) rm -rf "$tmp_dir" ;;
      *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
    esac
  fi
}

restore_cache() {
  [ "$backup_ready" -eq 1 ] || return 0
  if [ -L "$cache_root" ]; then
    printf '%s\n' "FAIL: refusing symlinked cache root: $cache_root" >&2
    return 1
  fi
  mkdir -p "$cache_root"
  for saved in "$backup_root"/*; do
    [ -e "$saved" ] || continue
    name=$(basename "$saved")
    destination=$cache_root/$name
    if [ -L "$destination" ]; then
      printf '%s\n' "FAIL: refusing symlinked cache destination: $destination" >&2
      return 1
    fi
    if [ ! -e "$destination" ]; then
      cp -Rp "$saved" "$destination"
    fi

    case "$name" in
      *+*)
        base=${name%%+*}
        base_destination=$cache_root/$base
        if [ -L "$base_destination" ]; then
          printf '%s\n' "FAIL: refusing symlinked compatibility destination: $base_destination" >&2
          return 1
        fi
        if [ ! -e "$base_destination" ]; then
          cp -Rp "$saved" "$base_destination"
        fi
        ;;
    esac
  done
}

refresh_cache_alias() {
  name=$1
  [ "$name" != "$manifest_version" ] || return 0

  marker=$tmp_dir/refreshed/$name
  [ ! -e "$marker" ] || return 0
  mkdir -p "$marker"

  current_cache=$cache_root/$manifest_version
  destination=$cache_root/$name
  staged=$tmp_dir/staged/$name
  mkdir -p "$tmp_dir/staged"
  cp -Rp "$current_cache" "$staged" || return 1

  if [ -L "$destination" ]; then
    printf '%s\n' "FAIL: refusing symlinked cache alias: $destination" >&2
    return 1
  fi
  if [ -e "$destination" ]; then
    [ -d "$destination" ] || return 1
    rm -rf "$destination" || return 1
  fi
  mv "$staged" "$destination" || return 1
}

refresh_cache_aliases() {
  current_cache=$cache_root/$manifest_version
  [ -d "$current_cache" ] && [ ! -L "$current_cache" ] || \
    fail "installed cache is missing or unsafe: $current_cache"

  mkdir -p "$tmp_dir/refreshed"
  for saved in "$backup_root"/*; do
    [ -e "$saved" ] || continue
    name=$(basename "$saved")
    refresh_cache_alias "$name" || return 1

    case "$name" in
      *+*)
        base=${name%%+*}
        refresh_cache_alias "$base" || return 1
        ;;
    esac
  done
}

interrupted() {
  trap - HUP INT TERM
  restore_cache || true
  exit 130
}
trap cleanup 0
trap interrupted HUP INT TERM

if [ -L "$cache_root" ]; then
  fail "refusing symlinked cache root: $cache_root"
fi
if [ -e "$cache_root" ] && [ ! -d "$cache_root" ]; then
  fail "cache root is not a directory: $cache_root"
fi
if [ -d "$cache_root" ]; then
  for cached in "$cache_root"/*; do
    [ -e "$cached" ] || [ -L "$cached" ] || continue
    name=$(basename "$cached")
    case "$name" in
      *[!0-9A-Za-z.+_-]*) fail "unsafe cache entry name: $name" ;;
    esac
    [ ! -L "$cached" ] || fail "refusing symlinked cache entry: $cached"
    [ -d "$cached" ] || fail "cache entry is not a directory: $cached"
    cp -Rp "$cached" "$backup_root/$name"
  done
fi
backup_ready=1

install_status=0
"$codex_bin" plugin add "sol-advisor@$marketplace" || install_status=$?
if [ "$install_status" -ne 0 ]; then
  restore_cache || fail "Codex plugin install failed and prior cache could not be restored"
  backup_ready=0
  fail "Codex plugin install failed with status $install_status"
fi
if ! refresh_cache_aliases; then
  restore_cache || fail "cache refresh failed and prior cache could not be restored"
  backup_ready=0
  fail "could not refresh preserved skill cache paths"
fi
backup_ready=0

check_current
pass "refreshed every preserved cache path to the installed release"
printf '%s\n' "NOTICE: Codex Desktop may display an older compatibility-path name until the app restarts; its checked contents are $manifest_version."
