#!/bin/sh
# Reinstall Sol Advisor without invalidating skill paths held by open Codex tasks.

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
  current_skill=$cache_root/$manifest_version/skills/orchestration/SKILL.md
  test -f "$current_skill" || fail "installed skill cache is missing: $current_skill"
  pass "installed version and skill cache match $manifest_version"
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
restore_cache || fail "could not restore preserved skill cache paths"
backup_ready=0
[ "$install_status" -eq 0 ] || fail "Codex plugin install failed with status $install_status"

check_current
pass "preserved cache paths for already-open Codex tasks"
