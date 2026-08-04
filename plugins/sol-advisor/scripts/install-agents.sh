#!/bin/sh
# Install Sol Advisor's shipped custom-agent templates without changing Codex config.

set -eu

usage() {
  cat <<'EOF'
Usage: install-agents.sh [--target-dir PATH] [--check]

Install Sol Advisor's seven current custom-agent templates into the target directory.
Normal mode also migrates only exact known shipped files: it replaces the v0.2.0 Luna
and the v0.2.0 or immediately previous Terra templates. It never
overwrites a modified, nonregular, or symlinked destination.

Without --target-dir, the target is "$CODEX_HOME/agents" when CODEX_HOME is already
set, otherwise "$HOME/.codex/agents".

Options:
  --target-dir PATH  Explicit destination directory (absolute or relative).
  --check            Verify that all seven executive, implementation, and reviewer roles match
                     exactly; do not mutate anything.
  --help             Show this help text.
EOF
}

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

report_preflight_error() {
  printf '%s\n' "ERROR: $*" >&2
  preflight_failed=1
}

path_exists() {
  [ -e "$1" ] || [ -L "$1" ]
}

sha256_file() {
  shasum -a 256 "$1" 2>/dev/null | awk 'NF >= 1 && length($1) == 64 { print $1; exit }'
}

classify_current_or_legacy() {
  destination=$1
  template=$2
  legacy_digest=$3
  previous_digest=${4-}

  if ! path_exists "$destination"; then
    printf '%s\n' missing
  elif [ -L "$destination" ] || [ ! -f "$destination" ]; then
    printf '%s\n' unsafe
  elif cmp -s "$template" "$destination"; then
    printf '%s\n' current
  else
    digest=$(sha256_file "$destination")
    if { [ -n "$legacy_digest" ] && [ "$digest" = "$legacy_digest" ]; } ||
       { [ -n "$previous_digest" ] && [ "$digest" = "$previous_digest" ]; }; then
      printf '%s\n' legacy
    elif [ -z "$digest" ]; then
      printf '%s\n' unreadable
    else
      printf '%s\n' conflict
    fi
  fi
}

same_state() {
  label=$1
  expected=$2
  actual=$3
  [ "$expected" = "$actual" ] || fail "$label changed after preflight; no further destination files were changed."
}

install_missing() {
  template=$1
  destination=$2
  staged=''

  if path_exists "$destination"; then
    fail "destination changed after preflight and will not be overwritten: $destination"
  fi

  staged=$(mktemp "$target_dir/.sol-advisor-agent.XXXXXX") || fail "could not stage template for installation: $destination"
  if ! cp "$template" "$staged"; then
    rm -f "$staged"
    fail "could not stage template for installation: $destination"
  fi

  if ! ln "$staged" "$destination"; then
    rm -f "$staged"
    fail "destination changed after preflight and will not be overwritten: $destination"
  fi

  rm -f "$staged" || fail "could not remove staged template after installation: $staged"
  printf '%s\n' "INSTALLED: $destination"
}

replace_legacy_terra() {
  staged=''

  [ "$(classify_current_or_legacy "$terra_destination" "$terra_template" "$legacy_terra_sha256" "$previous_terra_sha256")" = legacy ] ||
    fail "legacy Terra destination changed after preflight and will not be replaced: $terra_destination"

  staged=$(mktemp "$target_dir/.sol-advisor-agent.XXXXXX") || fail "could not stage migrated Terra template: $terra_destination"
  if ! cp "$terra_template" "$staged"; then
    rm -f "$staged"
    fail "could not stage migrated Terra template: $terra_destination"
  fi

  [ "$(classify_current_or_legacy "$terra_destination" "$terra_template" "$legacy_terra_sha256" "$previous_terra_sha256")" = legacy ] || {
    rm -f "$staged"
    fail "legacy Terra destination changed after preflight and will not be replaced: $terra_destination"
  }

  if ! mv -f "$staged" "$terra_destination"; then
    rm -f "$staged"
    fail "could not replace exact legacy Terra template: $terra_destination"
  fi

  printf '%s\n' "MIGRATED: $terra_destination"
}

replace_legacy_luna() {
  staged=''

  [ "$(classify_current_or_legacy "$luna_destination" "$luna_template" "$legacy_luna_sha256")" = legacy ] ||
    fail "legacy Luna destination changed after preflight and will not be replaced: $luna_destination"

  staged=$(mktemp "$target_dir/.sol-advisor-agent.XXXXXX") || fail "could not stage migrated Luna template: $luna_destination"
  if ! cp "$luna_template" "$staged"; then
    rm -f "$staged"
    fail "could not stage migrated Luna template: $luna_destination"
  fi

  [ "$(classify_current_or_legacy "$luna_destination" "$luna_template" "$legacy_luna_sha256")" = legacy ] || {
    rm -f "$staged"
    fail "legacy Luna destination changed after preflight and will not be replaced: $luna_destination"
  }

  if ! mv -f "$staged" "$luna_destination"; then
    rm -f "$staged"
    fail "could not replace exact legacy Luna template: $luna_destination"
  fi

  printf '%s\n' "MIGRATED: $luna_destination"
}

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
template_dir=$script_dir/../agents

if [ -n "${CODEX_HOME-}" ]; then
  target_dir=$CODEX_HOME/agents
else
  [ -n "${HOME-}" ] || fail "HOME is unset and CODEX_HOME was not supplied; pass --target-dir explicitly."
  target_dir=$HOME/.codex/agents
fi

check_only=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-dir)
      [ "$#" -ge 2 ] || fail "--target-dir requires a path."
      [ -n "$2" ] || fail "--target-dir requires a non-empty path."
      case "$2" in
        --*) fail "--target-dir path must be explicit; prefix an option-like relative name with ./ or use an absolute path." ;;
      esac
      target_dir=$2
      shift 2
      ;;
    --check)
      check_only=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1 (run with --help for usage)."
      ;;
  esac
done

case "$target_dir" in
  /*) ;;
  *) target_dir=$(pwd -P)/$target_dir ;;
esac

case "$target_dir" in
  /|//) fail "refusing to use the filesystem root as an agent target directory." ;;
esac

terra_medium_file=sol-advisor-terra-medium-implementer.toml
terra_executive_file=sol-advisor-terra-executive.toml
terra_file=sol-advisor-terra-implementer.toml
sol_medium_file=sol-advisor-sol-medium-implementer.toml
sol_high_file=sol-advisor-sol-high-implementer.toml
sol_file=sol-advisor-sol-reviewer.toml
luna_file=sol-advisor-luna-implementer.toml
luna_template=$template_dir/$luna_file
terra_medium_template=$template_dir/$terra_medium_file
terra_executive_template=$template_dir/$terra_executive_file
terra_template=$template_dir/$terra_file
sol_medium_template=$template_dir/$sol_medium_file
sol_high_template=$template_dir/$sol_high_file
sol_template=$template_dir/$sol_file
terra_medium_destination=$target_dir/$terra_medium_file
terra_executive_destination=$target_dir/$terra_executive_file
terra_destination=$target_dir/$terra_file
sol_medium_destination=$target_dir/$sol_medium_file
sol_high_destination=$target_dir/$sol_high_file
sol_destination=$target_dir/$sol_file
luna_destination=$target_dir/$luna_file

# Immutable v0.2.0 byte digests, calculated from:
# git show HEAD:plugins/sol-advisor/agents/sol-advisor-luna-implementer.toml | shasum -a 256
# git show HEAD:plugins/sol-advisor/agents/sol-advisor-terra-implementer.toml | shasum -a 256
legacy_luna_sha256=fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb
legacy_terra_sha256=4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca
# Immutable digest of the Terra template shipped immediately before the
# routine-analysis routing policy update.
previous_terra_sha256=06c318e5e93f37452635906394e6ea69fb6a65ba9e6ad7172d37b444e0dc871d

for template in "$luna_template" "$terra_medium_template" "$terra_executive_template" "$terra_template" "$sol_medium_template" "$sol_high_template" "$sol_template"; do
  [ -f "$template" ] && [ ! -L "$template" ] ||
    fail "shipped template is missing or not a regular file: $template"
done

preflight_failed=0
if path_exists "$target_dir"; then
  if [ -L "$target_dir" ] || [ ! -d "$target_dir" ]; then
    report_preflight_error "target directory is not a real directory: $target_dir"
  fi
fi

terra_medium_state=$(classify_current_or_legacy "$terra_medium_destination" "$terra_medium_template" '')
terra_executive_state=$(classify_current_or_legacy "$terra_executive_destination" "$terra_executive_template" '')
terra_state=$(classify_current_or_legacy "$terra_destination" "$terra_template" "$legacy_terra_sha256" "$previous_terra_sha256")
sol_medium_state=$(classify_current_or_legacy "$sol_medium_destination" "$sol_medium_template" '')
sol_high_state=$(classify_current_or_legacy "$sol_high_destination" "$sol_high_template" '')
sol_state=$(classify_current_or_legacy "$sol_destination" "$sol_template" '')
luna_state=$(classify_current_or_legacy "$luna_destination" "$luna_template" "$legacy_luna_sha256")

if [ "$check_only" -eq 1 ]; then
  [ "$luna_state" = current ] ||
    report_preflight_error "Luna / Max template is $luna_state, not the current exact file: $luna_destination"
  [ "$terra_medium_state" = current ] ||
    report_preflight_error "Terra / Medium template is $terra_medium_state, not the current exact file: $terra_medium_destination"
  [ "$terra_executive_state" = current ] ||
    report_preflight_error "Terra / High executive template is $terra_executive_state, not the current exact file: $terra_executive_destination"
  [ "$terra_state" = current ] ||
    report_preflight_error "Terra / High template is $terra_state, not the current exact file: $terra_destination"
  [ "$sol_medium_state" = current ] ||
    report_preflight_error "Sol / Medium template is $sol_medium_state, not the current exact file: $sol_medium_destination"
  [ "$sol_high_state" = current ] ||
    report_preflight_error "Sol / High implementer template is $sol_high_state, not the current exact file: $sol_high_destination"
  [ "$sol_state" = current ] ||
    report_preflight_error "Sol / High reviewer template is $sol_state, not the current exact file: $sol_destination"
else
  case "$luna_state" in
    current|legacy|missing) ;;
    *) report_preflight_error "Luna / Max destination is $luna_state and will not be replaced: $luna_destination" ;;
  esac
  case "$terra_medium_state" in
    current|missing) ;;
    *) report_preflight_error "Terra / Medium destination is $terra_medium_state and will not be replaced: $terra_medium_destination" ;;
  esac
  case "$terra_executive_state" in
    current|missing) ;;
    *) report_preflight_error "Terra / High executive destination is $terra_executive_state and will not be replaced: $terra_executive_destination" ;;
  esac
  case "$terra_state" in
    current|legacy|missing) ;;
    *) report_preflight_error "Terra / High destination is $terra_state and will not be replaced: $terra_destination" ;;
  esac
  case "$sol_medium_state" in
    current|missing) ;;
    *) report_preflight_error "Sol / Medium destination is $sol_medium_state and will not be replaced: $sol_medium_destination" ;;
  esac
  case "$sol_high_state" in
    current|missing) ;;
    *) report_preflight_error "Sol / High implementer destination is $sol_high_state and will not be replaced: $sol_high_destination" ;;
  esac
  case "$sol_state" in
    current|missing) ;;
    *) report_preflight_error "Sol / High reviewer destination is $sol_state and will not be replaced: $sol_destination" ;;
  esac
fi

[ "$preflight_failed" -eq 0 ] || exit 1

if [ "$check_only" -eq 1 ]; then
  printf '%s\n' "CHECK PASSED: all seven roles exactly match $template_dir."
  exit 0
fi

if [ ! -d "$target_dir" ]; then
  mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"
fi
[ -d "$target_dir" ] && [ ! -L "$target_dir" ] ||
  fail "target directory changed after preflight: $target_dir"

same_state "Luna / Max" "$luna_state" "$(classify_current_or_legacy "$luna_destination" "$luna_template" "$legacy_luna_sha256")"
same_state "Terra / Medium" "$terra_medium_state" "$(classify_current_or_legacy "$terra_medium_destination" "$terra_medium_template" '')"
same_state "Terra / High executive" "$terra_executive_state" "$(classify_current_or_legacy "$terra_executive_destination" "$terra_executive_template" '')"
same_state "Terra / High" "$terra_state" "$(classify_current_or_legacy "$terra_destination" "$terra_template" "$legacy_terra_sha256" "$previous_terra_sha256")"
same_state "Sol / Medium" "$sol_medium_state" "$(classify_current_or_legacy "$sol_medium_destination" "$sol_medium_template" '')"
same_state "Sol / High implementer" "$sol_high_state" "$(classify_current_or_legacy "$sol_high_destination" "$sol_high_template" '')"
same_state "Sol / High reviewer" "$sol_state" "$(classify_current_or_legacy "$sol_destination" "$sol_template" '')"

case "$luna_state" in
  missing) install_missing "$luna_template" "$luna_destination" ;;
  legacy) replace_legacy_luna ;;
  current) printf '%s\n' "ALREADY CURRENT: $luna_destination" ;;
esac

case "$terra_medium_state" in
  missing) install_missing "$terra_medium_template" "$terra_medium_destination" ;;
  current) printf '%s\n' "ALREADY CURRENT: $terra_medium_destination" ;;
esac

case "$terra_executive_state" in
  missing) install_missing "$terra_executive_template" "$terra_executive_destination" ;;
  current) printf '%s\n' "ALREADY CURRENT: $terra_executive_destination" ;;
esac

case "$terra_state" in
  missing) install_missing "$terra_template" "$terra_destination" ;;
  legacy) replace_legacy_terra ;;
  current) printf '%s\n' "ALREADY CURRENT: $terra_destination" ;;
esac

case "$sol_medium_state" in
  missing) install_missing "$sol_medium_template" "$sol_medium_destination" ;;
  current) printf '%s\n' "ALREADY CURRENT: $sol_medium_destination" ;;
esac

case "$sol_high_state" in
  missing) install_missing "$sol_high_template" "$sol_high_destination" ;;
  current) printf '%s\n' "ALREADY CURRENT: $sol_high_destination" ;;
esac

case "$sol_state" in
  missing) install_missing "$sol_template" "$sol_destination" ;;
  current) printf '%s\n' "ALREADY CURRENT: $sol_destination" ;;
esac

[ "$(classify_current_or_legacy "$luna_destination" "$luna_template" "$legacy_luna_sha256")" = current ] ||
  fail "post-install exactness check failed: $luna_destination"
[ "$(classify_current_or_legacy "$terra_medium_destination" "$terra_medium_template" '')" = current ] ||
  fail "post-install exactness check failed: $terra_medium_destination"
[ "$(classify_current_or_legacy "$terra_executive_destination" "$terra_executive_template" '')" = current ] ||
  fail "post-install exactness check failed: $terra_executive_destination"
[ "$(classify_current_or_legacy "$terra_destination" "$terra_template" "$legacy_terra_sha256" "$previous_terra_sha256")" = current ] ||
  fail "post-install exactness check failed: $terra_destination"
[ "$(classify_current_or_legacy "$sol_medium_destination" "$sol_medium_template" '')" = current ] ||
  fail "post-install exactness check failed: $sol_medium_destination"
[ "$(classify_current_or_legacy "$sol_high_destination" "$sol_high_template" '')" = current ] ||
  fail "post-install exactness check failed: $sol_high_destination"
[ "$(classify_current_or_legacy "$sol_destination" "$sol_template" '')" = current ] ||
  fail "post-install exactness check failed: $sol_destination"
printf '%s\n' "INSTALL PASSED: all seven roles exactly match $template_dir."
