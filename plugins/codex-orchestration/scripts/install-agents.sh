#!/bin/sh
# Install the eight Codex Orchestration 0.8.3 roles and retire obsolete identities safely.

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
    terra-grader) printf '%s\n' 3dd2e18abbc9dae807f679da68505eda33470eb537f1373740542e0f0b1bfb73 7f7d361950ed434f309e9915f0cf1a606aa00728d4bc0d3c99cc8ae4f7669f3f ;;
    terra-read-only) printf '%s\n' 8ef1a321b88f798326f76b458aa411e771b84056f041196aec65bf1af8d3f7ee 9bda4860b024839aa91a744ebb3c82116a7fa1009209bed67057c2c3c3461d19 ;;
    luna-implementer) printf '%s\n' 17977b485b042a6f0612d5e444d5232591fbe45ff679131a20eb61fad0edfef0 44bec276050bd6c342317b2c1d01c70fe310da7ff5f44c36754ef371491b300f de0169757da493d85b323b5d288036c0489a4700ebced8303ded58045d673d0a 983f3d6a4a9d674bc46d828b1f5c648a4b77940a4ff51d407302b3761ad010d9 ;;
    terra-implementer) printf '%s\n' c8a65ab5b313fdbe285aa47fba0b5ff13cd0040c8d1d06479e662b405503987b c36e4ccf25a51f911ad8fac00e235f2d23f623184dc71c08cdddebc8f7d71342 1fe32ab9230c3827f7abc489a5062d6cce2847f15341cbad1cac4e062ef5ece3 a24c4a1a67b4730f24d9d883cbbc6fb46b535847ddafa1599ff2127f5ca8b974 ;;
    sol-high-implementer) printf '%s\n' ad165e2c75a24c8f9a6a2a53ccc3010e7ff5a2932e6b72541592d3aea53bb475 98c135e10d0b66fa911eab99c1229b530e27d7ac0e5dc983dcef181806e67e6f ac4fb9c02a6d4d53d767fa2667dff3b7e6a41ce8b5032f1f179ee5607cd73c94 b9c8acb6206331972722cba1943c5a86aaaccdbaa85714188e8cfcce2f0a9ec0 ;;
    terra-supervisor) printf '%s\n' 0c3afffbeb7d4235c59e39b7ad331db3cefb07c49779441b25279200b18aae15 47ca1d10eba36a709f782f52d1c867d9b50094075ea620fae549d1a308f4fe9f ;;
    sol-high-supervisor) printf '%s\n' ee8b10c4f69c84305bd43f521b1a40d777f91b124f4e163e7d44e7a02d8848b2 8f25a162a0c979163c262ff7cd24542dc64b7daef882fd288b1c29a53a1902bd ;;
    sol-xhigh-supervisor) printf '%s\n' 351f19272ae01016a9cd7891ec3700b5ec85e12e518ee1d219d85274879943a1 ece9ac3d0d82e346b0b2c449f92907ca1110e7b8af680ed3fa7e547d026385b9 ;;
    *) printf '%s\n' '' ;;
  esac
}

retired_digest() {
  case "$1" in
    terra-executive) printf '%s\n' 806467d3c5a4cdd7d90636cd48d77f0c328de72b82aa81d56dac74bc8eb395bd b4628e57386b44ad8610024d345affa8187aafdfb042acd816459a9911c42100 820da651f6cdf3f39b7d4063ba78734cd9a23970d1464dd5cf7e8f8b8d585122 f76b6372e86e72ab78cd3e3a9b471a86bf89a9d0368fe77e16ddd9a02a39236d cd946559fa48432694fb420ecc05ea2a5516e75b1ecb2e05969fffab145feeed 554fb66aaeaff8c79ee820792c932039e67a2de81faf9d650468f478494120cb ;;
    terra-medium-implementer) printf '%s\n' ca24ac9c31b6809bd83d3692b952b661e6fd4910c4ae8321bacee237d3dc69ee 2e9d3f1f73cfd0348d9f3bf54abd880dc173377899e7bd50046102cfc3eb562e ;;
    sol-low-implementer) printf '%s\n' 146a5f633091fa54f24a526e9abc5bbf833d5097a0681e5401577be71ba2db09 688689237c80eccb4484cd9d2c2a112c90cf3ccd62bf159726926c3069503841 ;;
    sol-medium-implementer) printf '%s\n' 1b385b81814b709d69759bd63959f7da4af29a36d376cf97150340d88e45c83c ae3a117c76d0834baf82e6ee680c02b1ad8cc96c07914df5dd93daf54bb8a74c ;;
    sol-xhigh-implementer) printf '%s\n' 5bad9ec3a4d20acc8c966014a36394522bd25a0903da05b547328450c22bb299 fc5e3b701e30b9287d012b847da429449a8c3822dfa20693c139bc72ead4e4b2 ;;
    sol-low-executive) printf '%s\n' eaff986e10015a50c2975be60613750aff0be91e1e2e9df5dd82cae15b9ac677 7a71eda5e69a9bdf0f693c4a49a09803521f79e270a30eb86c2e552c136b1f6c ;;
    sol-medium-executive) printf '%s\n' 23600920e965df8edd9469d69fc617a7d5b13ec2b939afda660bf3950fbdf579 ;;
    sol-high-executive) printf '%s\n' b64892e03ee68651cd06dce7339dbd5ede187f41b31bdd62b50d5ac69659f5cc 3c6e87c47d980fd8e7a3eaad17130346bc658f1e6083637dae3a7db73db01ae9 d0b5a76a6857097e2838504bbb11346b2bc3a109aedf5d9ef395b5497f726914 c42d421890509b4e68ee2e664f588308341d749520f65ef964570f9a8cc412cd c1a8aa093923c2d2ddaf09adbac7ad801273f8c92141bff2f12994d56235e134 6d31cc7972d426dd21ea5729a7e7c96764b5ff2fad4d34f0667ea2cbebdc89e9 ;;
    sol-xhigh-executive) printf '%s\n' 8e6b784aa4578af68bebbe40be3fafec53631a7f76e436e17dada8b77216208d a697493f6144e3619f1334f1c49673f91cd5b3e2c3173efcfb149248fa2545ec 9ec152a58a5b7943985614f57710ac2560ffec65f8e89ba05346377dcdc96df7 35840c3b0dfaa0d25a67bc7de556200e8bf45069853417c9fce91debd1941091 99e1356e1e50185714c1da7d797e01cf0b3ff973ec120319aa1cc0af66957f72 ;;
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
  actual_digest=$(sha256_file "$destination")
  for previous in $(previous_digest "$role"); do
    [ "$actual_digest" = "$previous" ] && { printf '%s\n' previous; return; }
  done
  printf '%s\n' conflict
}

classify_retired() {
  role=$1
  destination=$target_dir/codex-orchestration-$role.toml
  path_exists "$destination" || { printf '%s\n' missing; return; }
  [ ! -L "$destination" ] && [ -f "$destination" ] || { printf '%s\n' unsafe; return; }
  actual_digest=$(sha256_file "$destination")
  for retired in $(retired_digest "$role"); do
    [ "$actual_digest" = "$retired" ] && { printf '%s\n' retired; return; }
  done
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
  printf '%s\n' 'CHECK PASSED: eight 0.8.3 roles are current and obsolete roles are absent.'
  exit 0
fi

mkdir -p "$target_dir" || fail "could not create target directory: $target_dir"
[ -d "$target_dir" ] && [ ! -L "$target_dir" ] || fail "unsafe target directory: $target_dir"

# Preflight the complete update before changing any file.
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

# Retire only obsolete byte-for-byte shipped files after all stable roles are proven current.
for role in $current_roles; do
  [ "$(classify_current "$role")" = current ] || fail "replacement role is not current: $role"
done
for role in $retired_roles; do
  [ "$(classify_retired "$role")" = retired ] || continue
  destination=$target_dir/codex-orchestration-$role.toml
  rm "$destination" || fail "could not retire $destination"
  printf '%s\n' "RETIRED: exact obsolete role $destination"
done

sh "$0" --target-dir "$target_dir" --check >/dev/null
printf '%s\n' 'INSTALL PASSED: eight 0.8.3 roles are current and obsolete identities were retired.'
