#!/bin/sh
# Install the four Codex Orchestration 0.13.0 profiles and retire the former supervisors safely.

set -eu

fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
template_dir=$(CDPATH= cd "$script_dir/../agents" && pwd) || exit 1
target_dir=${CODEX_ORCHESTRATION_AGENTS_DIR:-}
check_only=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-dir)
      [ "$#" -ge 2 ] || fail '--target-dir requires a path'
      target_dir=$2
      shift 2
      ;;
    --check)
      check_only=1
      shift
      ;;
    *) fail "usage: $0 [--target-dir PATH] [--check]" ;;
  esac
done

if [ -z "$target_dir" ]; then
  if [ -n "${CODEX_HOME:-}" ]; then
    target_dir=$CODEX_HOME/agents
  else
    [ -n "${HOME-}" ] || fail 'HOME and CODEX_HOME are unset'
    target_dir=$HOME/.codex/agents
  fi
fi
case "$target_dir" in /*) ;; *) fail "target directory must be absolute: $target_dir" ;; esac

current_roles='terra-orchestrator
luna-implementer
terra-implementer
sol-high-implementer'
retired_roles='terra-supervisor
sol-high-supervisor
sol-xhigh-supervisor'

path_exists() { [ -e "$1" ] || [ -L "$1" ]; }
sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }

# Exact 0.12.10 profiles accepted for the single-agent migration.
previous_digest() {
  case "$1" in
    terra-orchestrator) printf '%s\n' aa0595bf14f360e7a217a7420ecce399a5393c1ce81d75abbfdbf30d8e4fe56d ;;
    luna-implementer) printf '%s\n' f8c6190b3e4375ece24eb02ab9db0983a5f8c4cad47a126059cbc2c62f344194 ;;
    terra-implementer) printf '%s\n' 68179487b09d11667c6a0e69e48cec65348847df7ebb0e501e67ed47de0114a6 ;;
    sol-high-implementer) printf '%s\n' 86ad93904293ac3bc1613cdb1512274c4524ca19fd9ce1841e5744355207a6f6 ;;
    *) fail "unknown current role: $1" ;;
  esac
}

retired_digest() {
  case "$1" in
    terra-supervisor) printf '%s\n' e4ab97f67fed62023c204dd8f3688b144c07f62ec0ee1ba169c5c791232a2d1b ;;
    sol-high-supervisor) printf '%s\n' 6181d4b59b74c3688c6c5e3c94482c152b52861cd1fbb68c0e003d60fa73f8f5 ;;
    sol-xhigh-supervisor) printf '%s\n' 4a9a6947e04ae14df2855b3c495bf03311571d20f5125ed50a62fd113c28401d ;;
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
  [ "$(sha256_file "$destination")" = "$(previous_digest "$role")" ] && {
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
  [ -d "$target_dir" ] && [ ! -L "$target_dir" ] || fail "target directory is missing or unsafe: $target_dir"
  for role in $current_roles; do
    [ "$(classify_current "$role")" = current ] || fail "role is not current: codex-orchestration-$role.toml"
  done
  for role in $retired_roles; do
    [ "$(classify_retired "$role")" = missing ] || fail "retired role remains: codex-orchestration-$role.toml"
  done
  printf '%s\n' 'CHECK PASSED: four 0.13.0 profiles are current and former supervisors are absent.'
  exit 0
fi

mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"
[ -d "$target_dir" ] && [ ! -L "$target_dir" ] || fail "unsafe target directory: $target_dir"

# Preflight every target so a customized profile aborts before any mutation.
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
  [ "$state" = current ] && continue
  staged=$(mktemp "$target_dir/.codex-orchestration-agent.XXXXXX") || fail "could not stage $role"
  cp "$template" "$staged" || { rm -f "$staged"; fail "could not stage $role"; }
  if [ "$state" = missing ]; then
    ln "$staged" "$destination" || { rm -f "$staged"; fail "destination changed during install: $destination"; }
    rm -f "$staged"
    printf '%s\n' "INSTALLED: $destination"
  else
    [ "$(classify_current "$role")" = previous ] || { rm -f "$staged"; fail "destination changed during upgrade: $destination"; }
    mv "$staged" "$destination" || { rm -f "$staged"; fail "could not upgrade $destination"; }
    printf '%s\n' "UPGRADED: $destination"
  fi
done

for role in $current_roles; do
  [ "$(classify_current "$role")" = current ] || fail "replacement role is not current: $role"
done
for role in $retired_roles; do
  [ "$(classify_retired "$role")" = retired ] || continue
  destination=$target_dir/codex-orchestration-$role.toml
  rm "$destination" || fail "could not retire $destination"
  printf '%s\n' "RETIRED: exact former supervisor $destination"
done

sh "$0" --target-dir "$target_dir" --check >/dev/null
printf '%s\n' 'INSTALL PASSED: four 0.13.0 profiles are current and former supervisors were retired.'
