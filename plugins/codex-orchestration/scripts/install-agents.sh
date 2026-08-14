#!/bin/sh
# Install the four Codex Orchestration 0.9.0 profiles and retire the former supervisors safely.

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

# Exact previously shipped profiles accepted for safe in-place migration.
previous_digest() {
  # The prior revision used the same report voice for users and internal technical work.
  case "$1" in
    luna-implementer) printf '%s\n' 4201842ecf8866231e1bfe1054da2f4e9ae270801b89ecaa322d35067d9ba020 ;;
    terra-implementer) printf '%s\n' 89d873c4455dd330c6e2b6b7f548b0f5291d83e19bbdccdd6cdc267d03c87d33 ;;
    sol-high-implementer) printf '%s\n' b2a432a98bd5178743fb4c93f56af9477567556972903d7b079a5f835bc42cea ;;
    *) ;;
  esac
  # The prior next-step draft placed explanatory prose between the two required sections.
  case "$1" in
    luna-implementer) printf '%s\n' ea67b6d86a803b74a743625a370d16fbc10c618f08201ad07c0556ec56c19c1b ;;
    terra-implementer) printf '%s\n' a9c73e0eb4849f9cf1c1e42bb2d648d8940b0a25cf89a1b478f6afba789663ad ;;
    sol-high-implementer) printf '%s\n' 40f71d7605dbd7d377675e2f4e6c0dd6a20ed6d264ddab7d847296a088248a3d ;;
    *) ;;
  esac
  # The immediately previous revision used a route footer without a mandatory next-step section.
  case "$1" in
    luna-implementer) printf '%s\n' 347b7a5816d1679902b6a83ab6aa3d3e55fe66ff643cde6bda4839ab5b0c7a04 ;;
    terra-implementer) printf '%s\n' 4a4835084db7ce7a6c803a932f04786c67cb895627d5a466311e61805e67efe4 ;;
    sol-high-implementer) printf '%s\n' 3796eabec1cc51c72ee0cb0baafd1471518c4ef65349e874015f250511d6aa56 ;;
    *) ;;
  esac
  # The prior revision retained the verbatim full chat and every task outcome.
  case "$1" in
    luna-implementer) printf '%s\n' 8abff60952e6d0610d55f966de1096a77170919a3bf8400e6186435af4df7ec7 ;;
    terra-implementer) printf '%s\n' 4bdce27f9a1e6a4d911812663944c21377a141587867256bd99f8e759913be03 ;;
    sol-high-implementer) printf '%s\n' c892d3514b27293255b27f1e0729167c129fbecc8e3ba7db22697dc8d83d8c9c ;;
    *) ;;
  esac
  # The prior revision retained only the active task's private context.
  case "$1" in
    luna-implementer) printf '%s\n' a1891e5c56abf70c510ab8c6ec10e83f901e7558c16c35bb275fd78a66fdf34f ;;
    terra-implementer) printf '%s\n' c03d3973435c9b8b68c3800bd7a10f2864e0cdd967bc20fe3b8d67c44137ba44 ;;
    sol-high-implementer) printf '%s\n' dcf42638109aca350f4bafc206da6e9554750c17234e5a7904ccc7f327c6816b ;;
    *) ;;
  esac
  # The prior revision used the structured completion template.
  case "$1" in
    luna-implementer) printf '%s\n' 622ba29ad12b5f0f3a785c41b9717235eb1be5f65021a9fa72a27664e3ae295a ;;
    terra-implementer) printf '%s\n' ab37dca70b29da614b3415bed1ce08fa674eac22eae6f6525fb5eb94926ea09e ;;
    sol-high-implementer) printf '%s\n' 284e79829e13f2128898d82377f815b36f14bea95ee7c9b0c03b6b8fca08b5d5 ;;
    *) ;;
  esac
  # The immediately previous revision omitted the route receipt.
  case "$1" in
    luna-implementer) printf '%s\n' ab612956e9cb73aa1494fb086d345be5a14ffb1de301b5fb55c540f0e37d886d ;;
    terra-implementer) printf '%s\n' a117ad6643923035f7eebcbdc9b7d3350d5eb2d89c1d284c2e93af4b243d55fc ;;
    sol-high-implementer) printf '%s\n' 84b9be0a605cb684d716db6f4e2f6b8986e8e1e93b86496ea187816a920ad3ce ;;
    *) ;;
  esac
  # The revision before that still emitted the four-field route receipt.
  case "$1" in
    luna-implementer) printf '%s\n' 2574ab7e01874599ed4b05940d7b9a0898e0fb21564a5ac8ce3961a6ebcbaaf3 ;;
    terra-implementer) printf '%s\n' 45e2549938493020446261a960b12d800d0244b794d10bb280fda0041720ed5f ;;
    sol-high-implementer) printf '%s\n' f980e92ded78673ecb3052af93492d0cc5bf295dbcf0e27aa3df41a05ebbd852 ;;
    *) ;;
  esac
  case "$1" in
    terra-orchestrator) printf '%s\n' aa0595bf14f360e7a217a7420ecce399a5393c1ce81d75abbfdbf30d8e4fe56d ;;
    luna-implementer) printf '%s\n' f8c6190b3e4375ece24eb02ab9db0983a5f8c4cad47a126059cbc2c62f344194 662c7b7010cc87e902f1f2608f74a8bce7bd06df659e3de778fc761d3667fbbe 2716b3635a68f8fed0961e69be92c1b18338c6a1897876592fd58a061932e082 3bbb7c2464542eb135640782b52c9d213486bc351d60b8fe0c40ef21a1368e5c 82f9358fa7ed1d6ab7f9c297dccc721c626191879d1ec73ee5038dd8888afdce 89234fa1bcb7f3fe98e909cdf2775b61293a91174d04b6801169f2defd0204a2 08aa1335248a15ee305e30edb35662b28d95d31b266a67351acfa696ced1e3ec c0da09a763a31e77d4b9390e524eb61ead0b730a5024c9c322761a9b39f056a2 ;;
    terra-implementer) printf '%s\n' 68179487b09d11667c6a0e69e48cec65348847df7ebb0e501e67ed47de0114a6 930bd325d9d19c93ffbb70497410ff9f0a03c657fde81e04a8ccd3272f206424 dbcaf41ebdb469251ca316154d10ae6a8717ea0228c3e580c1e411851ceee8fb 830aebc3d5c40da3aae60b20e6f760b29fe32c68d67fdd7db3d5ae9d49ff9bfa c61310125d3af082ffc6fcb9712fc0c07f630c9e08a3a582e727cfdf612c6d31 f01797baa0997b63c0ad9b70a29e1d07cdd5e8056b9520b711fc8482e180edd3 b21cd346b39eb94f4119bf180fc1b3354a9f3259f469fe22b43233fee1433177 66a549c67e7f81f0d0e6db89ec85af7d1a47253b376e255344c603459ec0ea7c ;;
    sol-high-implementer) printf '%s\n' 86ad93904293ac3bc1613cdb1512274c4524ca19fd9ce1841e5744355207a6f6 2a8be332df4cd578f599c3f5dac89930f7cd13503393a0f380ee3a4a128492f7 171fa0d31db51f032d323b417a063e8ff374709013c9f7751e8cf44f53f77cbc 6ee395bb2287fd8fe8276e87f2ba7429a8eac67a771561ad71f30f5ed787a6cb b42701c0431ba0018f1e22ea7923d0c04b550e4232aa1221d8a9f067d45b8ef9 153a8603fd959e951471a81cec4c7dbda293d6793d98e4c5d03a89b9f3abf744 6f4a5eb3d93109728ea2cf4bc955da0f3eee58422e8baa15b8c4d98354529064 ;;
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
  destination_digest=$(sha256_file "$destination")
  previous_digest "$role" | grep -Fxq "$destination_digest" && {
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
  printf '%s\n' 'CHECK PASSED: four 0.9.0 profiles are current and former supervisors are absent.'
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
printf '%s\n' 'INSTALL PASSED: four 0.9.0 profiles are current and former supervisors were retired.'
