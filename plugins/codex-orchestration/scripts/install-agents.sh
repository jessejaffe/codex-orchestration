#!/bin/sh
# Install Codex Orchestration's eleven custom agents and retire exact shipped legacy files.

set -eu

usage() {
  cat <<'EOF'
Usage: install-agents.sh [--target-dir PATH] [--check]

Install Codex Orchestration's eleven current custom-agent templates. Normal mode also
removes the exact legacy sol-advisor-* counterpart for each role, but only when its
content matches a recognized shipped template. User-modified, nonregular, and
symlinked current or legacy files are conflicts and are never overwritten or deleted.

Without --target-dir, the target is "$CODEX_HOME/agents" when CODEX_HOME is set,
otherwise "$HOME/.codex/agents".

Options:
  --target-dir PATH  Explicit destination directory.
  --check            Require all eleven current files and no legacy counterparts.
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
      previous_current_digests='250759da7eda6a2bde248931ee0c4f781258cc56818dad3e42c6d457a0eb4bd7 02c75dfdf71b0fb3e7a49587a86344d16ffc77ccc3403bd2ccc35d5c42672bc9 23d368f2cec1952b893d07822dd828174fa24b157a03cd9078acb43981cbde27 891775bf69356d3a37bd2a6d76879de0eb57c2311ed060d5f55157ae9d0d0806 522503971d3338c979deceb134d002e059334522291b6f038e0021a3c9bdddfb df71d4e728f22fb4f6c690a8c4a584bb172955d98458344aedd1747862aa0a20 dd0b95d4612b2bfb5ad6f5de2ef95956d39081ae4838810acb3d812be168cbd1'
      legacy_digests='bc4c6a8c2f3f58288d970d9caba66e2ecc532a59820c08bb958d466ed561500d fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb'
      ;;
    terra-medium-implementer)
      previous_current_digests='6ada178902fb621b0fb58b8a7bd48ab3f4d397d9192d41dab458924921919c4b 11f13314033c25246fee75cd230fc999250374ac4ab95988fdaf65b662a1ae07 5c3352b3d1535a5c9ed04b48124544259f935b0e3d301cf58bfa278298905097 5b24e884400f32a8e06d7e27048d58a40eaf580f2c266d30bb39950137b7f4a0 788177fb9ffb422cf791a8de5802a56fe1111e7f92f3ca427a9110a5a4f33963 f66ccd707d1d695e44b3709d6987cabc86f59a2a87a8ce6372c98e7decc4e2db 0618eaaf50040154f3d09371d1c8d4d184d461ccd760a5b85041e7c215fb3c0d'
      legacy_digests='309d1fd8f0bf17785fff53583d4e42067e637c0922b9f23da0653729e7f809cf'
      ;;
    terra-executive)
      # Exact previously shipped templates, safe to replace with the numeric scoring role.
      previous_current_digests='ee18e8ce854b5639790932d28c981f340b4b9ced3ea62cee7f03ab2c8f087c63 f679d6b97e5f537a9aeec0baf95f2267d9b42241a6e55598c191b2bf6d5f231d 8caf6c47bcc47d8e9ea2566047233f69cf88a672ff8e400c9698fc911550104e ed3042963ef39384293ed072e6531193f8c18a6d48cac6753907efe4ec6dae54 437c5d4a531dd2003db28e264a4ef39fa913de8df44b56922bc55a81d62e2301 d336e60b9b703f04c7bfe8aaa212818860b178c25f5b3119cbb6c87d6825e5f8 d843a907029caf949049cca3a9c417aba80a4584aa0af12f1aefbec1a691af28 31c69fe169e174d61437d1a24bc9323535494048a6c3e3b23877343f6078d389 6d8e3d86112624d1178915d1a829edc8866c732352cc7bbaa87386227f568206 911ffe0a751caed52a9ebd7c656d393c974ecb436532f19ce2e4308fb55c0341 9233d2be19c9350d79690ff23ae66cc6979d24a681996bc5ab02e6a57ccd3397 22f5de61931eec91bc2e339b791aa6568e85ba337bcfcddfad9d900ab68fa352 3790c4c9a5ac878a246df38e5222c5c9b6604bb4a7de8c1233f99ee510c22164 10a2d82f4a0466cd554917b02cc8952fa51522d970973dfc2cc68ed59287a2e0 ca9c68dff9bd288a912185d67352fcae8813c38baa2a2b3202f9709a51d4b0a9 764217265e9c4b56c4d857c56e959f604156533afeb66817667cab9b33109385'
      legacy_digests='4849c6591202290ff63db140b56089e63a4d06e2eaabec7256d016dcb056dbdc'
      ;;
    terra-implementer)
      previous_current_digests='894823383b6184c3a972e4fff04ad6274dad949699bc32272b2e8f04335c0f84 93eec7e0d93c6db721467d5ad2f6333724625a325c0b1dcf987f1e68c28ba5fe 484f126205150880ec2d24de223e11b677d1efccff87e792544ec8c78b821b04 36bfb3586ce1cc38b01ec80d3442b01705e3388914993df4426c14c69d400ed6 89c7d0f5399610b65f759758e5ff70319b8aefb79cede03ab4c03dc7864e4de5 5b84ec87d912cdac76a01dcaeb3b48f6057f6263dc3ac0b1d6e7be660f362f84 d88c4e5eef3a60f3934c2d0687f4e803d1bcd3f50e4ee533ad941f24097b0842 6a16584960723de84f551554943af3999f4578f09db593f66d5e4c0cf9c8960b'
      legacy_digests='7b4549d971ddd7c07a886ebcc01bc9645cc0eedc4e81f32930bee6ec9ab8c44c 4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca 06c318e5e93f37452635906394e6ea69fb6a65ba9e6ad7172d37b444e0dc871d'
      ;;
    sol-low-implementer)
      # This role was introduced after the Sol Advisor identity was retired.
      previous_current_digests='43a1531815e6674a023f9f21c03635253ded90e15eae72ce69776c8f54af8fb3 19765b8de4e331d8bf578dea89807003a5d072387c0b231215de1bee5878f86c d9532a53dc6cfac811e6d81a6b0084dd8b3aa5c6a4cd1957281f136c8363aa49 2498e53387833db6b708dc2ac94130af4572ce55f7769775b0ffe8a10d7070a9 6a65e112aadcbb0ec34949a2160d97c1b9054506277a94e598d0a6ac09a8e41f 1af4d9325b7a561c0bd4b355b12b2165df80c369c0365245d2b002512c48e9ab 4105ad6c0d0cd9af6869efff848ed5ce39370d252fd216e67153f4508df7363c'
      legacy_digests=''
      ;;
    sol-medium-implementer)
      # Exact 0.7.2 companion template, safe to replace during the band split.
      previous_current_digests='5360b683128ec2863bdaf95fd1bbb13eda615b67270dbbf3e45c553fbde60562 5a5897ddcc8d150656591c3f9e4c0327cd38697808d7a21249b4ee7842f1ad08 45170a1d3d0e5eeb9b5a85cc2cbc4d37b686cb0fcdab0b72fc2090018b7b70dd 58fd158736a08332ff78cecc891cdd0a421345937e9d032afd3b21f96f52603f e91e03388b2b61d423bc61b5346ebf4e7aed9584d17e73b2f506522f58cb64c8 cc2d56f12e33ef7190d5e97b827ed02c13ac6e06cb1553116c86449f1ab63c93 1ec3252a3798a68f29a800bec8acf59f4048b6dc4b833c0bc3fd285e42b523a9 1ab755e223b3cf942000166e8c339223c208d73f1cce096e78a4a541bd111ce4'
      legacy_digests='dd42eaeaac3063c43109c9b45f7d1efda0ef999976d9a2231f8833e42afa3974'
      ;;
    sol-high-implementer)
      previous_current_digests='d351037408fb4297f2b9a0336d709812628dfef4dc6d3e3db76fa427ca54d64a 862d3f8f5423cdc0db9d58913dbe761f6090f4a805a4be9e451dd503919e2812 fdf9b8b20ae40511652c4bfff3be0e93182ba2657663dbca189fc4e4dc6200bc 8259d6d0e182c50f6dbbcea502e82fd38874b9eb375285db367337e7111b68f4 fc502c3932c046005a7ba6f90cb408eb34f1d4a24efd369ced529f8b7b16bb15 f29efa9089205993a5d1b539190041d41f0619fbc820f80759d97ae62f9d393d 3f68fb41c3997008075de3c6a9b4b735ee378779758b594107ea7445e0c80c36'
      legacy_digests='712adee8e4d5e425cd6e1bc3fe4a41760befdb5b6f4e333e85a6fd6273b4c292'
      ;;
    sol-xhigh-implementer)
      previous_current_digests='3d272be23921d2a70185bb0b2868ed074e1e9a3d06cb261373ece3c6f7e72179 ec60d63cd610bbf3625048cc43a53021ba9fe09d56e100c2c127e2eb7a8899c4 b18073dcec9489ead67331e935d2628ef7d22d53c4603ebc0cb61342944aec40 2e3b7606cb7fe3b56ccee009086b1d3e16113c1836e3b3407685ce48b4da54ed 79b9606fcc279eaf835068cda4a9e85aeabe487042dd42832b614167e75cfbcc 443a053164880c3a08cc4cfe07b646569895b2c016d3c5b829de1f208cc2444e'
      legacy_digests=''
      ;;
    sol-high-executive)
      previous_current_digests='707bd6eb38462c2c005cfe6e6f2cc50a9952510b5ab69c83e544bfb9989202b8 9c2ec08dc3b1dc20fb33efca1f16358d0718c5635a2603bb52db56ebd7327deb 293a8e636d7676875e5bf7fff658cc59f4bb22f67bb62dc55f0517780ea775c6 65d6716e859f9636a16b59156f46bdca5a3196837e4514c88303d0f00a9ff64a 1caae6c7741549efe493f72e1d3c05483909747bdb69ab0d821f510e004a0376 cdb1e0401c40703e513059847ae89b047d6fa69e6ef6523d98dee67a3f4ee5a9 9ede0c022e578617b31c511e5967aa42b1bffc1c712697565863667205eee88e 1d7462700700fdf8c4d8c671d56bacfc51593dc997cc0a5ec1c41e732f1e2182'
      legacy_digests=''
      ;;
    sol-xhigh-executive)
      # Introduced for scores of 8.0 and higher.
      previous_current_digests='d32694987e8c22fea5efc2936498fb56ee160d84f4650e927e7c3ebdccc18540'
      legacy_digests=''
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

roles='luna-implementer terra-medium-implementer terra-executive terra-implementer sol-low-implementer sol-medium-implementer sol-high-implementer sol-xhigh-implementer sol-high-executive sol-xhigh-executive sol-reviewer'
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
  printf '%s\n' "CHECK PASSED: all eleven Codex Orchestration roles are current and legacy files are absent."
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

# Prove the complete eleven-role replacement set before any legacy file is removed.
for role in $roles; do
  role_files "$role"
  template=$template_dir/$current_file
  current_destination=$target_dir/$current_file
  [ "$(classify_current "$current_destination" "$template" "$previous_current_digests")" = current ] ||
    fail "could not prove current role before legacy retirement: $current_destination"
done
printf '%s\n' "PROVED: all eleven Codex Orchestration roles are current before legacy retirement."

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
printf '%s\n' "INSTALL PASSED: all eleven Codex Orchestration roles are current and exact shipped legacy files were removed."
