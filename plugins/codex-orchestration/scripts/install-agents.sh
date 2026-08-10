#!/bin/sh
# Install the eight Codex Orchestration 0.8.1 roles and safely retire exact 0.8.0 roles.

set -eu

usage() {
  printf '%s\n' 'Usage: install-agents.sh [--target-dir PATH] [--check]'
}

fail() { printf '%s\n' "ERROR: $*" >&2; exit 1; }
path_exists() { [ -e "$1" ] || [ -L "$1" ]; }
sha256_file() { shasum -a 256 "$1" 2>/dev/null | awk 'NF { print $1; exit }'; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
template_dir=$(CDPATH= cd "$script_dir/../agents" && pwd) || exit 1
target_dir=''
check_only=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-dir)
      [ "$#" -ge 2 ] || fail '--target-dir requires a path'
      target_dir=$2
      shift 2
      ;;
    --check) check_only=1; shift ;;
    --help) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
  esac
done

if [ -z "$target_dir" ]; then
  if [ -n "${CODEX_HOME:-}" ]; then
    target_dir=$CODEX_HOME/agents
  else
    [ -n "${HOME:-}" ] || fail 'HOME and CODEX_HOME are unset'
    target_dir=$HOME/.codex/agents
  fi
fi
case "$target_dir" in /*) ;; *) fail "target directory must be absolute: $target_dir" ;; esac
[ ! -L "$target_dir" ] || fail "target directory is a symlink: $target_dir"

current_roles='terra-grader
terra-read-only
luna-implementer
terra-implementer
sol-high-implementer
terra-supervisor
sol-high-supervisor
sol-xhigh-supervisor'

retired_roles='terra-executive
terra-medium-implementer
sol-low-implementer
sol-medium-implementer
sol-xhigh-implementer
sol-low-executive
sol-medium-executive
sol-high-executive
sol-xhigh-executive
sol-reviewer'

previous_digest() {
  case "$1" in
    luna-implementer) printf '%s\n' de0169757da493d85b323b5d288036c0489a4700ebced8303ded58045d673d0a ;;
    terra-implementer) printf '%s\n' 1fe32ab9230c3827f7abc489a5062d6cce2847f15341cbad1cac4e062ef5ece3 ;;
    sol-high-implementer) printf '%s\n' ac4fb9c02a6d4d53d767fa2667dff3b7e6a41ce8b5032f1f179ee5607cd73c94 ;;
    *) printf '%s\n' '' ;;
  esac
}

retired_digest() {
  case "$1" in
    terra-executive) printf '%s\n' b4628e57386b44ad8610024d345affa8187aafdfb042acd816459a9911c42100 ;;
    terra-medium-implementer) printf '%s\n' ca24ac9c31b6809bd83d3692b952b661e6fd4910c4ae8321bacee237d3dc69ee ;;
    sol-low-implementer) printf '%s\n' 146a5f633091fa54f24a526e9abc5bbf833d5097a0681e5401577be71ba2db09 ;;
    sol-medium-implementer) printf '%s\n' 1b385b81814b709d69759bd63959f7da4af29a36d376cf97150340d88e45c83c ;;
    sol-xhigh-implementer) printf '%s\n' 5bad9ec3a4d20acc8c966014a36394522bd25a0903da05b547328450c22bb299 ;;
    sol-low-executive) printf '%s\n' eaff986e10015a50c2975be60613750aff0be91e1e2e9df5dd82cae15b9ac677 ;;
    sol-medium-executive) printf '%s\n' 23600920e965df8edd9469d69fc617a7d5b13ec2b939afda660bf3950fbdf579 ;;
    sol-high-executive) printf '%s\n' 3c6e87c47d980fd8e7a3eaad17130346bc658f1e6083637dae3a7db73db01ae9 ;;
    sol-xhigh-executive) printf '%s\n' a697493f6144e3619f1334f1c49673f91cd5b3e2c3173efcfb149248fa2545ec ;;
    sol-reviewer) printf '%s\n' a538883589b409bd28fe983dfed246be2149ed1c7914c320cfc55f9833bee683 ;;
    *) fail "unknown retired role: $1" ;;
  esac
}

classify_current() {
  role=$1
  destination=$target_dir/codex-orchestration-$role.toml
  template=$template_dir/codex-orchestration-$role.toml
  path_exists "$destination" || { printf '%s\n' missing; return; }
  [ ! -L "$destination" ] && [ -f "$destination" ] || { printf '%s\n' unsafe; return; }
  cmp -s "$template" "$destination" && { printf '%s\n' current; return; }
  previous=$(previous_digest "$role")
  [ -n "$previous" ] && [ "$(sha256_file "$destination")" = "$previous" ] && {
    printf '%s\n' previous
    return
  }
  printf '%s\n' conflict
}

classify_retired() {
  role=$1
  destination=$target_dir/codex-orchestration-$role.toml
  path_exists "$destination" || { printf '%s\n' missing; return; }
  [ ! -L "$destination" ] && [ -f "$destination" ] || { printf '%s\n' unsafe; return; }
  [ "$(sha256_file "$destination")" = "$(retired_digest "$role")" ] && {
    printf '%s\n' retired
    return
  }
  printf '%s\n' conflict
}

for role in $current_roles; do
  template=$template_dir/codex-orchestration-$role.toml
  [ -f "$template" ] && [ ! -L "$template" ] || fail "missing or unsafe template: $template"
done

if [ "$check_only" -eq 1 ]; then
  [ -d "$target_dir" ] || fail "target directory does not exist: $target_dir"
  for role in $current_roles; do
    [ "$(classify_current "$role")" = current ] || fail "role is not current: codex-orchestration-$role.toml"
  done
  for role in $retired_roles; do
    [ "$(classify_retired "$role")" = missing ] || fail "retired role remains: codex-orchestration-$role.toml"
  done
  printf '%s\n' 'CHECK PASSED: eight 0.8.1 roles are current and 0.8.0 roles are absent.'
  exit 0
fi

mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"
[ -d "$target_dir" ] && [ ! -L "$target_dir" ] || fail "unsafe target directory: $target_dir"

# Preflight the complete migration before changing any file.
for role in $current_roles; do
  state=$(classify_current "$role")
  case "$state" in current|missing|previous) ;; *) fail "refusing $state current role: codex-orchestration-$role.toml" ;; esac
done
for role in $retired_roles; do
  state=$(classify_retired "$role")
  case "$state" in missing|retired) ;; *) fail "refusing $state retired role: codex-orchestration-$role.toml" ;; esac
done

for role in $current_roles; do
  state=$(classify_current "$role")
  destination=$target_dir/codex-orchestration-$role.toml
  template=$template_dir/codex-orchestration-$role.toml
  case "$state" in
    current) ;;
    missing)
      staged=$(mktemp "$target_dir/.codex-orchestration-agent.XXXXXX") || fail "could not stage $role"
      cp "$template" "$staged" || { rm -f "$staged"; fail "could not stage $role"; }
      ln "$staged" "$destination" || { rm -f "$staged"; fail "destination changed during install: $destination"; }
      rm -f "$staged"
      printf '%s\n' "INSTALLED: $destination"
      ;;
    previous)
      [ "$(classify_current "$role")" = previous ] || fail "destination changed during upgrade: $destination"
      staged=$(mktemp "$target_dir/.codex-orchestration-agent.XXXXXX") || fail "could not stage $role"
      cp "$template" "$staged" || { rm -f "$staged"; fail "could not stage $role"; }
      mv "$staged" "$destination" || { rm -f "$staged"; fail "could not upgrade $destination"; }
      printf '%s\n' "UPGRADED: $destination"
      ;;
  esac
done

# Retire only byte-for-byte 0.8.0 files, after every replacement role is proven current.
for role in $current_roles; do
  [ "$(classify_current "$role")" = current ] || fail "replacement role is not current: $role"
done
for role in $retired_roles; do
  [ "$(classify_retired "$role")" = retired ] || continue
  destination=$target_dir/codex-orchestration-$role.toml
  rm "$destination" || fail "could not retire $destination"
  printf '%s\n' "RETIRED: exact 0.8.0 role $destination"
done

sh "$0" --target-dir "$target_dir" --check >/dev/null
printf '%s\n' 'INSTALL PASSED: eight 0.8.1 roles are current and exact 0.8.0 roles were retired.'
