#!/bin/sh
# Install the seven Codex Orchestration 0.12.5 companion profiles and retire obsolete identities safely.

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

current_roles='luna-implementer
terra-implementer
sol-high-implementer
terra-orchestrator
terra-supervisor
sol-high-supervisor
sol-xhigh-supervisor'

retired_roles='terra-read-only
terra-grader
terra-executive
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
  # Exact 0.12.4 supervisor profiles accepted for the 0.12.5 positive-acceptance migration.
  case "$1" in
    terra-supervisor) printf '%s\n' 8fc6bdccbf27ec2344adca5e458d2330a16fac98d3db6b0fec0cdb14da8480f4 ;;
    sol-high-supervisor) printf '%s\n' b4e326ac895bc23df8bd30f6ed209b44fa80c049617a2ba605049599c0b4e6fd ;;
    sol-xhigh-supervisor) printf '%s\n' 9fd4345c1481e4775a0340b54cd64b16932f42cafff06505396cbfd39a92b418 ;;
  esac
  # Exact 0.12.3 profiles accepted for the 0.12.4 prompt-simplification migration.
  case "$1" in
    luna-implementer) printf '%s\n' cb92150a2164cc1d1f89952320119111669e9953a0b8a837a539eec191167430 ;;
    terra-implementer) printf '%s\n' d2084c6421ef931e0efd1b7b377df59662a2fcbd526b7e023492d0bc875e24e2 ;;
    sol-high-implementer) printf '%s\n' 52b773dd1602abcf38e1bc04b7e4271b46547a19a30b2dbb2b8a15410c4f3429 ;;
    terra-orchestrator) printf '%s\n' 4b0f87ceca26a8525524a56e520a2595c5ee95fb8ee216d7f6bd6bba2192471a ;;
    terra-supervisor) printf '%s\n' 15a433bdc6435bb1dae245967c93edd439e93f44d91c604de46ec276b9dded6e ;;
    sol-high-supervisor) printf '%s\n' 92cd6c7967721fcfdc806809aba07fa0270b6ff1c3c189822efc782388f328eb ;;
    sol-xhigh-supervisor) printf '%s\n' 7d3263b72da6fd4f032e1b054f93edd439e93f44d91c604de46ec276b9dded6e ;;
  esac
  # Exact 0.12.2 profiles accepted for the 0.12.3 recovery-policy migration.
  case "$1" in
    luna-implementer) printf '%s\n' 9e28f2e3d38aa6300a399d12be19f2ab5e787d3efdd616d38e2653009dfc375b ;;
    sol-high-implementer) printf '%s\n' 0091625c0a072a2a5638b4a8d20ecbe4c2e019d3ce9fba5f1e2a47dac2fe7ef2 ;;
    sol-high-supervisor) printf '%s\n' 92cd6c7967721fcfdc806809aba07fa0270b6ff1c3c189822efc782388f328eb ;;
    sol-xhigh-supervisor) printf '%s\n' 7d3263b72da6fd4f032e1b054f93edd439e93f44d91c604de46ec276b9dded6e ;;
    terra-implementer) printf '%s\n' 5afb5cc35dfc8019af35c716a70cca1bf208d2c7116972671f97a64813885d76 ;;
    terra-orchestrator) printf '%s\n' 4b0f87ceca26a8525524a56e520a2595c5ee95fb8ee216d7f6bd6bba2192471a ;;
    terra-supervisor) printf '%s\n' 15a433bdc6435bb1dae245967c93ac439ed775624eb723ffe4d647750b037066 ;;
  esac
  # Exact 0.12.1 profiles accepted for the 0.12.2 implementer-first migration.
  case "$1" in
    luna-implementer) printf '%s\n' e2e6ff81543ba52fb032beab6c3169a2fea9cacc177cb29ef077a88576d41468 ;;
    sol-high-implementer) printf '%s\n' ba553fd5ece225cc3d01c9d16065802bcad97d066f3931b9d2ae2f22eaa2344a ;;
    sol-high-supervisor) printf '%s\n' 68def43161e10a599bad5a4e63d12d79178b487ed4f5fb58fe81dd42b0b2c557 ;;
    sol-xhigh-supervisor) printf '%s\n' 1224f0bbe949d0aa170924fb2d34978d02762d6f6cb02036e3629f645b8da6a5 ;;
    terra-implementer) printf '%s\n' c7a70970173bccf55eac14393541a72be027a27e58362213e958acb35e63a69c ;;
    terra-orchestrator) printf '%s\n' 4b0f87ceca26a8525524a56e520a2595c5ee95fb8ee216d7f6bd6bba2192471a ;;
    terra-supervisor) printf '%s\n' caf2176d6ad6f3aba1f3ed27e3bf4b7b1bfd393fa269149daf25812bdcf24b0f ;;
  esac
  # Exact 0.12.0 profiles accepted for the 0.12.1 split-context migration.
  case "$1" in
    luna-implementer) printf '%s\n' e2e6ff81543ba52fb032beab6c3169a2fea9cacc177cb29ef077a88576d41468 ;;
    sol-high-implementer) printf '%s\n' ba553fd5ece225cc3d01c9d16065802bcad97d066f3931b9d2ae2f22eaa2344a ;;
    sol-high-supervisor) printf '%s\n' 68def43161e10a599bad5a4e63d12d79178b487ed4f5fb58fe81dd42b0b2c557 ;;
    sol-xhigh-supervisor) printf '%s\n' 1224f0bbe949d0aa170924fb2d34978d02762d6f6cb02036e3629f645b8da6a5 ;;
    terra-implementer) printf '%s\n' c7a70970173bccf55eac14393541a72be027a27e58362213e958acb35e63a69c ;;
    terra-orchestrator) printf '%s\n' 368699b87b35b1704e4b32b9781471183682c18e8ba7d73538bf448551b1e538 ;;
    terra-supervisor) printf '%s\n' caf2176d6ad6f3aba1f3ed27e3bf4b7b1bfd393fa269149daf25812bdcf24b0f ;;
  esac
  # Exact 0.11.1 profiles accepted for the 0.12.0 lean-context migration.
  case "$1" in
    luna-implementer) printf '%s\n' 0d7289514349fc3ecf7891f8a77a98c275af6389b2ed9a3df73cfde4a87762de ;;
    sol-high-implementer) printf '%s\n' d225c7ffa7cb27cafc427140b4926d4ccd43132a622a23e97cb9974fa61b1eb1 ;;
    sol-high-supervisor) printf '%s\n' bcee12a8397d09cf9900243f4b98149b447d18c4fbf4b727e2a9dd069a5a3b0b ;;
    sol-xhigh-supervisor) printf '%s\n' 40ce291a1ea9b0de52d5e7e3b6b25ce9beb3c83c1ed4569d16de8c40e8ef6399 ;;
    terra-implementer) printf '%s\n' 811a02078feff67e9fa91140b9d143c44637fcde2d3543054f77567a1ef46662 ;;
    terra-orchestrator) printf '%s\n' 2b4064414c7b5064584608a4322c7fca06357327ef4eaaf36ce6895a3916c97a ;;
    terra-supervisor) printf '%s\n' d46cb59fb0eddc68f7deff81e83f1379ecee9d9a561c2cc22a904626aa165cf2 ;;
  esac
  # Exact 0.11.0 profiles accepted for the 0.11.1 readable-protocol migration.
  case "$1" in
    luna-implementer) printf '%s\n' 57fa0c83e001f8300054982123580bf63ec8d2ac6c5adbd9ea5c5a47e395310f ;;
    sol-high-implementer) printf '%s\n' 3df9d5071bd120ba4ff63f372277f09d38e650c0b914362e5057864ffc2d72a6 ;;
    sol-high-supervisor) printf '%s\n' 3e3aae30c769489c8776467a5b6497f76eacfbdf424a9e0b098b642abd00bfbd ;;
    sol-xhigh-supervisor) printf '%s\n' 12f3d61ec1705cbfdc3ac8e60dd338d7fec7716b055371d632a2ffa6f2e25a24 ;;
    terra-implementer) printf '%s\n' 2a5154885d32df32c87713dba1e7e58ec09f98e6720fd13a2d01b5f2ebd931b2 ;;
    terra-orchestrator) printf '%s\n' a4b93a9a04494d93a9b8b902888bf123ae0dafa76972124f2e2e2a3d84b97cc5 ;;
    terra-supervisor) printf '%s\n' b1d57d6e649bef6275a87994587010594dc16344f27ec2979f7964b295964dc4 ;;
  esac
  # Exact 0.10.5 profiles accepted for the 0.11.0 seven-class migration.
  case "$1" in
    luna-implementer) printf '%s\n' 57fa0c83e001f8300054982123580bf63ec8d2ac6c5adbd9ea5c5a47e395310f ;;
    sol-high-implementer) printf '%s\n' eb96828e0c7e76d2b08f2a1950f09b833c305d03b0c154e1a4f43982c7e340df ;;
    sol-high-supervisor) printf '%s\n' 5f1fd1f92efe8ee64818db1377a4bd396bea77224f1881ea7f8e7297cbed0d1c ;;
    sol-xhigh-supervisor) printf '%s\n' 4b5daaf3eeb4c4476b9f1b91f847b96ed0eccb2594bb706ecdc720e64ffa2898 ;;
    terra-implementer) printf '%s\n' b973df71184208d9f2bdc1fb18fe92364a402e2140d3b2eac932b4d31fd1532d ;;
    terra-orchestrator) printf '%s\n' 91aaffded1378dee480edbb7a0ce928b8b354c1def6fd1c78be4129c042eb084 ;;
    terra-supervisor) printf '%s\n' b1d57d6e649bef6275a87994587010594dc16344f27ec2979f7964b295964dc4 ;;
  esac
  # Exact 0.10.4 profiles accepted for the 0.10.5 context-bundle migration.
  case "$1" in
    luna-implementer) printf '%s\n' daad8fa64a161d02615b2df99e7ffef1a56e7a6114e3831b116d42a2e1c18fa2 ;;
    sol-high-implementer) printf '%s\n' 06e935c579bc2797cbb86a2f146cdc1eddfdd1a389ebded53e4e57cea9a64079 ;;
    sol-high-supervisor) printf '%s\n' 8a7e78e5480f19449753194d5171b7ee06d44ea9bd4ea5768beed45947ba5ab3 ;;
    sol-xhigh-supervisor) printf '%s\n' 3be0b8c8ee64cb00fc642ed5fac1c0bb44ac3ba726b5fb3329d11691546a6f17 ;;
    terra-implementer) printf '%s\n' a9db7125294104eede7c587f22db62901e2af857ff3a5ccfbff10f13d26bba97 ;;
    terra-orchestrator) printf '%s\n' 22e2167ebceaacabbeec00b5fa4ad822187921182f0d14a7528408e58fc16e6e ;;
    terra-supervisor) printf '%s\n' 1b49c843b4794cfba17d708b6d01fdfd498ef5011e72fd288d469df81ec221cf ;;
  esac
  # Exact 0.10.3 profiles accepted for the 0.10.4 startup-latency migration.
  case "$1" in
    luna-implementer) printf '%s\n' b7f25d2474fbe35e42b14f6683fca4a2398da5bc9a5a9c7ca70b7c7fa8f543cb ;;
    sol-high-implementer) printf '%s\n' fd962b99e92a116957c867299d9bc1713cd8faed721c8bc79b35685c5f58470a ;;
    sol-high-supervisor) printf '%s\n' fe023cd9d4f1ece2ed386679afb5a3ad50f2f2048d8cfe40605397b5780dc4b7 ;;
    sol-xhigh-supervisor) printf '%s\n' 75340397335c5a18b1112233d75d2a51d3033bf3a8ef578841b4d2da1aafedc8 ;;
    terra-implementer) printf '%s\n' 66af783589d285cd99e5a427cbcdc0c87de279f0005ab03e55b3fa3d3c93eee3 ;;
    terra-orchestrator) printf '%s\n' 3678c195db31f3bf54fcac7d8d0d31afe19d9edb108ed1e33aedcef4b1717ae8 ;;
    terra-supervisor) printf '%s\n' 02ea1e6f7242f20ef761962b9c6a8c25f4d7cc5ce88ff8c6ee9674d2f89f9995 ;;
  esac
  # Exact 0.10.2 profiles accepted for the 0.10.3 readable release migration.
  case "$1" in
    luna-implementer) printf '%s\n' 142b58957a44c91e45bd4f110f30fce855a6e6cb23ec8069bba87e900ccc3e33 ;;
    sol-high-implementer) printf '%s\n' db744d545558fd8f93dfa93392c0ea1ace9d451e074fa700121d69a7d10f8fd8 ;;
    sol-high-supervisor) printf '%s\n' d781b21e3292ce238770cd4b424f8430a319fdf0e4c7d4342617b54a55d3f5f1 ;;
    sol-xhigh-supervisor) printf '%s\n' a9341b5e3d2a463a5a094bd0268b6413371b71c65f13cf3b46ee9132ae6f4071 ;;
    terra-implementer) printf '%s\n' cdcaf2f3ddb1fb265398b9196a9124fcbe8f2c7b0c8617b15293faf5d6f41e48 ;;
    terra-supervisor) printf '%s\n' 97dbcc78d98cc74231a08c30d60c5ab057726fdf2a866dd620194df00503be5b ;;
  esac
  # Exact 0.10.0 profiles accepted for the 0.10.1 startup migration.
  case "$1" in
    terra-orchestrator) printf '%s\n' fc3b2c7ac8b13f48153d30010841f1e9f1bbe60bebb4c514474922b98f3ec8cd ;;
    luna-implementer) printf '%s\n' b3152056861c84c5484cb4379345a32487abac083dd04aec358a670236fc010b ;;
    terra-implementer) printf '%s\n' 50bc87e9dac98c05b5516fedc6991ab12e9358e40d8bfd27be90e3433b5389f0 ;;
    sol-high-implementer) printf '%s\n' bdad29925cdc5ab880439ab8eda6ce2f81499625e0a5040176008153799c933d ;;
    terra-supervisor) printf '%s\n' 280fee892205538302205df54baa28fe97e43a53173673098bfa66c8bb21ead4 ;;
    sol-high-supervisor) printf '%s\n' 356432b1c0578f3066b017fe28eb5436708532eb89d4ec754919db7fcc209991 ;;
    sol-xhigh-supervisor) printf '%s\n' b68755047b744057258b4957e6894692588fb8462cb78c466acb4b98a87a4f8b ;;
  esac
  # Exact 0.9.0 profiles accepted for the 0.10.0 taxonomy migration.
  case "$1" in
    luna-implementer) printf '%s\n' 5e55237eabb9315b5ece06ae5239bf5740c69adc9ffcc508f7b0ac3ecaf060d1 ;;
    terra-implementer) printf '%s\n' a5277a7f3870f57eca209d21c63a2ac1b95e6918ab4c7c31bd45534d452f64ec ;;
    sol-high-implementer) printf '%s\n' ed407f41f1d0c2b54417cac2d18647fd1f5156ae321eb3c28415ccbb833cebb4 ;;
    terra-supervisor) printf '%s\n' 4e16a42744c5a2b3503f1ab1eb0638047a77bbf17470567306721fec95ec7b71 ;;
    sol-high-supervisor) printf '%s\n' 7dc6715eec52fda116d10bb3154353b2020e093976dc47dc4cdee55bee12b24d ;;
    sol-xhigh-supervisor) printf '%s\n' 48520a33a70bfceb920fee852ee991f0305170bd255bbf5455146e6ac88281d8 ;;
  esac
  case "$1" in
    terra-orchestrator) printf '%s\n' 143f2b6d5c917352df0b5c6a57608ac70f702f0bbc0ff779eedd5cf1243babd4 ;;
    luna-implementer) printf '%s\n' 17977b485b042a6f0612d5e444d5232591fbe45ff679131a20eb61fad0edfef0 44bec276050bd6c342317b2c1d01c70fe310da7ff5f44c36754ef371491b300f de0169757da493d85b323b5d288036c0489a4700ebced8303ded58045d673d0a 983f3d6a4a9d674bc46d828b1f5c648a4b77940a4ff51d407302b3761ad010d9 ee39d10609e279369abb42801e9436417c609355b7f018da42b1bf50cf9d0263 7fc50da2bb0efae58a6be4f083170f7b046870c8217f0f94241363a8404537e3 dc769716110ab9b99b0c7caa7de8c5992c39414096d5a79c7b0f6619ee2592e5 fd75a5160451b266bc8ae35b34e0865d23ccb96f5019e656ef8e898ccafd8d5d 485804b5bd058d30c16feedf404595c6f3c347b5e6e5ef794d92b7e35edeb2a5 ;;
    terra-implementer) printf '%s\n' c8a65ab5b313fdbe285aa47fba0b5ff13cd0040c8d1d06479e662b405503987b c36e4ccf25a51f911ad8fac00e235f2d23f623184dc71c08cdddebc8f7d71342 1fe32ab9230c3827f7abc489a5062d6cce2847f15341cbad1cac4e062ef5ece3 a24c4a1a67b4730f24d9d883cbbc6fb46b535847ddafa1599ff2127f5ca8b974 d0b22605fe4fb415efc8ea14e6243de85c792aff566295c3de32d00176c54e72 c878b68faf44eae87c12c349f58ff90f086068c6c9b40f771757e432db54bb75 35723b41371a65bf52af621aafc0663022aa51ffb6236b816bc21cd65cdb080e 8001b202cede42454fa4cbcd0bb29cb580716e738cb533396e033dc132f402f4 e28c539964354adca6423c19a0da1746a8db60b94b734f7f00fd88b5a03a41d1 ;;
    sol-high-implementer) printf '%s\n' ad165e2c75a24c8f9a6a2a53ccc3010e7ff5a2932e6b72541592d3aea53bb475 98c135e10d0b66fa911eab99c1229b530e27d7ac0e5dc983dcef181806e67e6f ac4fb9c02a6d4d53d767fa2667dff3b7e6a41ce8b5032f1f179ee5607cd73c94 b9c8acb6206331972722cba1943c5a86aaaccdbaa85714188e8cfcce2f0a9ec0 938ae440dde9c136fbdc75f757cfcc3030b5c344b9b187e1898c1bfeff27376b 5d8156c3e42105180b6bee35d457aac6f7fd371f55aeba5c58f822d0ad5ab473 ad167cec124a4ad4389d92b7e49fe5ba2effbe070bf3a9ced51fc1550edfda83 c1d47ebd4825dd497cfddc7dfe9b6d3f6685eb1323019f2c969851b8861eb674 11e5654f28517b4556d9fc13a374f6b97240d8da6f2d8673078730be847f998f ;;
    terra-supervisor) printf '%s\n' d533709aa442d916dd1b05a7173710a2d24dcd5a4a7040a29b0ce4510d1465f7 0c3afffbeb7d4235c59e39b7ad331db3cefb07c49779441b25279200b18aae15 47ca1d10eba36a709f782f52d1c867d9b50094075ea620fae549d1a308f4fe9f 2ab30773626f82c998f2f4373ccf39080881565e0c12a07e211ea6bf08b974cb e9d35bf4dcc8f1e78d32953107821aea477998afb407ad8b8661d791afa8195d 2e124c8a94ff4aaad427c85910e52b370f732321aaa4e3689af0c9dffffc346b d44f6d70de581d3e8895b396cc7a2bba0a2e7fc35cb6ea8531e920cae457aab4 bcf97708c68712984c6345476595e832c933763d2e5edde854cfcc295794e1a5 c296cd101b91debb8ac800d4d18339f9da8d9606a7048c70e72d37cf0b8885b4 fb1a6905fca9345fabfc3b1ff9d98cfb784514600d67b372bd4fb60c6afcd85f cb7d464796bc18b9f371ce9f6036ffbdfe32914946c9ac18c78c8aec1c4bec44 310f47cd149493a376a1625786a98f0f763b8f4558faccc1e28b9a2b4394cc39 47a605dbf390f842a0bd373fb20511bfd630cf5f647f76dab71c9085627a8465 65e904176779be864c6f2cd3d41a5c9424bbc95cc25190a96fc6d02e130655cc ;;
    sol-high-supervisor) printf '%s\n' ee8b10c4f69c84305bd43f521b1a40d777f91b124f4e163e7d44e7a02d8848b2 8f25a162a0c979163c262ff7cd24542dc64b7daef882fd288b1c29a53a1902bd ff700c6a648c7a42d589229288fd9b3611d473cddefaa2e540dd24565149acd2 4120bf9285995b66d6ca08c11cb01d87b389b58b535127b83a2fe339b471a568 5993929d08fb1003e8def633e41b8aa457cfcd6a748399f513a3c942b5877857 427075380b9a3a8a136a6fde53a95252c3031621d51181ec1161318330d027a0 3283d5d4c93674855694d10b96922911d9bafb186ee08fb85b0b7548daa72b5a c0361a14a8436a89760398d3823a5796f62fb1cfd30f1460a3827a0d9e0d3db9 ;;
    sol-xhigh-supervisor) printf '%s\n' 351f19272ae01016a9cd7891ec3700b5ec85e12e518ee1d219d85274879943a1 ece9ac3d0d82e346b0b2c449f92907ca1110e7b8af680ed3fa7e547d026385b9 9bc0ad2492f0fbf8636a8945c3ae366eb1a12e8b63f2eac65ad38d0c9538a192 156bdc43364274c698294159ba6ff3c2c7e98912f214c6560e389bf51463cd6d c4d37bc0579ed9a2c035bee510fa6fa7a236122fd5178e004bfb3c5df78059b3 30ba4bbee0dcb1ecf22dfb6c6ce98377e72740e717011f7d319e9ccc1f7104bf 9bf1374469493ef6ad866ba6e11082a86427210c23806d86a643c1325e0f6576 8628097f5fddd161710598d5f433f3cbf183d675376e36c5b3cfdebb2d6b18b6 ;;
    *) printf '%s\n' '' ;;
  esac
}

retired_digest() {
  case "$1" in
    terra-read-only) printf '%s\n' 8ef1a321b88f798326f76b458aa411e771b84056f041196aec65bf1af8d3f7ee 9bda4860b024839aa91a744ebb3c82116a7fa1009209bed67057c2c3c3461d19 ;;
    terra-grader) printf '%s\n' 3dd2e18abbc9dae807f679da68505eda33470eb537f1373740542e0f0b1bfb73 7f7d361950ed434f309e9915f0cf1a606aa00728d4bc0d3c99cc8ae4f7669f3f ;;
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
  printf '%s\n' 'CHECK PASSED: seven 0.12.5 companion profiles are current and obsolete roles are absent.'
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
printf '%s\n' 'INSTALL PASSED: seven 0.12.5 companion profiles are current and obsolete identities were retired.'
