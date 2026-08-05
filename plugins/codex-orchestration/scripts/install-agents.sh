#!/bin/sh
# Install Codex Orchestration's eight custom agents and retire exact shipped legacy files.

set -eu

usage() {
  cat <<'EOF'
Usage: install-agents.sh [--target-dir PATH] [--check]

Install Codex Orchestration's eight current custom-agent templates. Normal mode also
removes the exact legacy sol-advisor-* counterpart for each role, but only when its
content matches a recognized shipped template. User-modified, nonregular, and
symlinked current or legacy files are conflicts and are never overwritten or deleted.

Without --target-dir, the target is "$CODEX_HOME/agents" when CODEX_HOME is set,
otherwise "$HOME/.codex/agents".

Options:
  --target-dir PATH  Explicit destination directory.
  --check            Require all eight current files and no legacy counterparts.
  --help             Show this help text.
EOF
}

fail() { printf '%s\n' "ERROR: $*" >&2; exit 1; }
report_error() { printf '%s\n' "ERROR: $*" >&2; preflight_failed=1; }
path_exists() { [ -e "$1" ] || [ -L "$1" ]; }
sha256_file() { shasum -a 256 "$1" 2>/dev/null | awk 'NF >= 1 && length($1) == 64 { print $1; exit }'; }

role_files() {
  role=$1
  current_file=codex-orchestration-$role.toml
  previous_current_digests=''
  # Compatibility migration only: these are the exact pre-0.7.0 shipped filenames.
  legacy_file=sol-advisor-$role.toml
  case "$role" in
    luna-implementer)
      legacy_digests='bc4c6a8c2f3f58288d970d9caba66e2ecc532a59820c08bb958d466ed561500d fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb'
      ;;
    terra-medium-implementer)
      legacy_digests='309d1fd8f0bf17785fff53583d4e42067e637c0922b9f23da0653729e7f809cf'
      ;;
    terra-executive)
      legacy_digests='4849c6591202290ff63db140b56089e63a4d06e2eaabec7256d016dcb056dbdc'
      ;;
    terra-implementer)
      legacy_digests='7b4549d971ddd7c07a886ebcc01bc9645cc0eedc4e81f32930bee6ec9ab8c44c 4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca 06c318e5e93f37452635906394e6ea69fb6a65ba9e6ad7172d37b444e0dc871d'
      ;;
    sol-low-implementer)
      # This role was introduced after the Sol Advisor identity was retired.
      legacy_digests=''
      ;;
    sol-medium-implementer)
      # Exact 0.7.2 companion template, safe to replace during the band split.
      previous_current_digests='5360b683128ec2863bdaf95fd1bbb13eda615b67270dbbf3e45c553fbde60562'
      legacy_digests='dd42eaeaac3063c43109c9b45f7d1efda0ef999976d9a2231f8833e42afa3974'
      ;;
    sol-high-implementer)
      legacy_digests='712adee8e4d5e425cd6e1bc3fe4a41760befdb5b6f4e333e85a6fd6273b4c292'
      ;;
    sol-reviewer)
      legacy_digests='0333acf0ef562bcfebd06009ac09bd1dd8cbc04c4cf28e08e9e049bd8bf202d2'
      ;;
    *) fail "unknown shipped role: $role" ;;
  esac
}

classify_current() {
  destination=$1
  template=$2
  previous_digests=$3
  if ! path_exists "$destination"; then
    printf '%s\n' missing
  elif [ -L "$destination" ] || [ ! -f "$destination" ]; then
    printf '%s\n' unsafe
  elif cmp -s "$template" "$destination"; then
    printf '%s\n' current
  else
    digest=$(sha256_file "$destination")
    for recognized in $previous_digests; do
      if [ "$digest" = "$recognized" ]; then
        printf '%s\n' previous
        return
      fi
    done
    printf '%s\n' conflict
  fi
}

classify_legacy() {
  destination=$1
  digests=$2
  if ! path_exists "$destination"; then
    printf '%s\n' missing
    return
  fi
  if [ -L "$destination" ] || [ ! -f "$destination" ]; then
    printf '%s\n' unsafe
    return
  fi
  digest=$(sha256_file "$destination")
  [ -n "$digest" ] || { printf '%s\n' unreadable; return; }
  for recognized in $digests; do
    if [ "$digest" = "$recognized" ]; then
      printf '%s\n' legacy
      return
    fi
  done
  printf '%s\n' conflict
}

install_missing() {
  template=$1
  destination=$2
  [ "$(classify_current "$destination" "$template" '')" = missing ] ||
    fail "current destination changed after preflight: $destination"
  staged=$(mktemp "$target_dir/.codex-orchestration-agent.XXXXXX") ||
    fail "could not stage template: $destination"
  if ! cp "$template" "$staged"; then rm -f "$staged"; fail "could not stage template: $destination"; fi
  if ! ln "$staged" "$destination"; then
    rm -f "$staged"
    fail "current destination changed after preflight and was not overwritten: $destination"
  fi
  rm -f "$staged" || fail "could not remove staged template: $staged"
  printf '%s\n' "INSTALLED: $destination"
}

upgrade_previous() {
  template=$1
  destination=$2
  previous_digests=$3
  [ "$(classify_current "$destination" "$template" "$previous_digests")" = previous ] ||
    fail "current destination changed after preflight and was not upgraded: $destination"
  staged=$(mktemp "$(dirname "$destination")/.codex-orchestration-agent.XXXXXX") ||
    fail "could not stage template: $destination"
  if ! cp "$template" "$staged"; then rm -f "$staged"; fail "could not stage template: $destination"; fi
  if ! mv "$staged" "$destination"; then
    rm -f "$staged"
    fail "could not upgrade exact previous template: $destination"
  fi
  printf '%s\n' "UPGRADED: exact previous shipped template $destination"
}

remove_legacy() {
  destination=$1
  digests=$2
  [ "$(classify_legacy "$destination" "$digests")" = legacy ] ||
    fail "legacy destination changed after preflight and was not removed: $destination"
  rm "$destination" || fail "could not remove exact shipped legacy file: $destination"
  printf '%s\n' "MIGRATED: removed exact shipped legacy file $destination"
}

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
template_dir=$script_dir/../agents
if [ -n "${CODEX_HOME-}" ]; then
  target_dir=$CODEX_HOME/agents
else
  [ -n "${HOME-}" ] || fail "HOME is unset and CODEX_HOME was not supplied; pass --target-dir."
  target_dir=$HOME/.codex/agents
fi
check_only=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-dir)
      [ "$#" -ge 2 ] && [ -n "$2" ] || fail "--target-dir requires a non-empty path."
      case "$2" in --*) fail "--target-dir path must be explicit." ;; esac
      target_dir=$2
      shift 2
      ;;
    --check) check_only=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) fail "unknown argument: $1 (run with --help for usage)." ;;
  esac
done

case "$target_dir" in /*) ;; *) target_dir=$(pwd -P)/$target_dir ;; esac
case "$target_dir" in /|//) fail "refusing the filesystem root as an agent target." ;; esac

roles='luna-implementer terra-medium-implementer terra-executive terra-implementer sol-low-implementer sol-medium-implementer sol-high-implementer sol-reviewer'
preflight_failed=0
if path_exists "$target_dir" && { [ -L "$target_dir" ] || [ ! -d "$target_dir" ]; }; then
  report_error "target directory is not a real directory: $target_dir"
fi

for role in $roles; do
  role_files "$role"
  template=$template_dir/$current_file
  current_destination=$target_dir/$current_file
  legacy_destination=$target_dir/$legacy_file
  [ -f "$template" ] && [ ! -L "$template" ] || report_error "shipped template is missing or unsafe: $template"
  current_state=$(classify_current "$current_destination" "$template" "$previous_current_digests")
  legacy_state=$(classify_legacy "$legacy_destination" "$legacy_digests")
  if [ "$check_only" -eq 1 ]; then
    [ "$current_state" = current ] || report_error "$current_file is $current_state, not current: $current_destination"
    [ "$legacy_state" = missing ] || report_error "$legacy_file is $legacy_state and must be migrated: $legacy_destination"
  else
    case "$current_state" in current|missing|previous) ;; *) report_error "$current_file is $current_state and will not be overwritten: $current_destination" ;; esac
    case "$legacy_state" in legacy|missing) ;; *) report_error "$legacy_file is $legacy_state and will not be removed: $legacy_destination" ;; esac
  fi
done
[ "$preflight_failed" -eq 0 ] || exit 1

if [ "$check_only" -eq 1 ]; then
  printf '%s\n' "CHECK PASSED: all eight Codex Orchestration roles are current and legacy files are absent."
  exit 0
fi

if [ ! -d "$target_dir" ]; then mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"; fi
[ -d "$target_dir" ] && [ ! -L "$target_dir" ] || fail "target directory changed after preflight: $target_dir"

# Install every missing current role before retiring any recognized legacy role.
for role in $roles; do
  role_files "$role"
  template=$template_dir/$current_file
  current_destination=$target_dir/$current_file
  case "$(classify_current "$current_destination" "$template" "$previous_current_digests")" in
    missing) install_missing "$template" "$current_destination" ;;
    previous) upgrade_previous "$template" "$current_destination" "$previous_current_digests" ;;
    current) printf '%s\n' "ALREADY CURRENT: $current_destination" ;;
    *) fail "current destination changed after preflight: $current_destination" ;;
  esac
done

# Prove the complete eight-role replacement set before any legacy file is removed.
for role in $roles; do
  role_files "$role"
  template=$template_dir/$current_file
  current_destination=$target_dir/$current_file
  [ "$(classify_current "$current_destination" "$template" "$previous_current_digests")" = current ] ||
    fail "could not prove current role before legacy retirement: $current_destination"
done
printf '%s\n' "PROVED: all eight Codex Orchestration roles are current before legacy retirement."

for role in $roles; do
  role_files "$role"
  legacy_destination=$target_dir/$legacy_file
  case "$(classify_legacy "$legacy_destination" "$legacy_digests")" in
    missing) ;;
    legacy) remove_legacy "$legacy_destination" "$legacy_digests" ;;
    *) fail "legacy destination changed after preflight: $legacy_destination" ;;
  esac
done

sh "$0" --target-dir "$target_dir" --check >/dev/null
printf '%s\n' "INSTALL PASSED: all eight Codex Orchestration roles are current and exact shipped legacy files were removed."
