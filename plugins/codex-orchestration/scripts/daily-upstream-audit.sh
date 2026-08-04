#!/bin/sh
# Run at most once per local calendar day and summarize pending upstream changes.

set -eu

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1

force=0
if [ "$#" -gt 1 ]; then
  printf '%s\n' 'ERROR: usage: daily-upstream-audit.sh [--force]' >&2
  exit 2
fi
case "${1-}" in
  '') ;;
  --force) force=1 ;;
  *)
    printf '%s\n' 'ERROR: usage: daily-upstream-audit.sh [--force]' >&2
    exit 2
    ;;
esac

upstream_repo=${CODEX_ORCHESTRATION_UPSTREAM_REPO:-${SOL_ADVISOR_UPSTREAM_REPO:-DannyMac180/sol-advisor}}
fork_repo=${CODEX_ORCHESTRATION_FORK_REPO:-${SOL_ADVISOR_FORK_REPO:-jessejaffe/codex-orchestration}}

if [ -n "${CODEX_ORCHESTRATION_AUDIT_STATE_DIR-}" ]; then
  state_dir=$CODEX_ORCHESTRATION_AUDIT_STATE_DIR
elif [ -n "${SOL_ADVISOR_AUDIT_STATE_DIR-}" ]; then
  # Compatibility fallback for pre-0.7.0 automation.
  state_dir=$SOL_ADVISOR_AUDIT_STATE_DIR
elif [ -n "${CODEX_HOME-}" ]; then
  state_dir=$(python3 "$script_dir/state_migration.py" --codex-home "$CODEX_HOME") || exit 1
else
  [ -n "${HOME-}" ] || { printf '%s\n' 'ERROR: HOME is unset.' >&2; exit 1; }
  state_dir=$(python3 "$script_dir/state_migration.py" --codex-home "$HOME/.codex") || exit 1
fi

today=$(date +%F)
state_file=$state_dir/upstream-audit.txt

if [ -L "$state_file" ]; then
  printf '%s\n' "ERROR: refusing symlinked audit state: $state_file" >&2
  exit 1
fi

if [ "$force" -eq 0 ] && [ -f "$state_file" ] && [ "$(sed -n 's/^CHECKED_DATE: //p' "$state_file" | head -1)" = "$today" ]; then
  printf '%s\n' 'STATUS: already-checked-today'
  cat "$state_file"
  exit 0
fi

for required_command in git gh jq; do
  command -v "$required_command" >/dev/null 2>&1 || {
    printf '%s\n' "ERROR: required command is unavailable: $required_command" >&2
    exit 1
  }
done

tmp_base=${TMPDIR:-/tmp}
case "$tmp_base" in /*) ;; *) tmp_base=/tmp ;; esac
tmp_dir=$(mktemp -d "$tmp_base/codex-orchestration-upstream-audit.XXXXXX") || exit 1
cleanup() {
  case "$tmp_dir" in
    "$tmp_base"/codex-orchestration-upstream-audit.*) rm -rf "$tmp_dir" ;;
    *) printf '%s\n' "REFUSING cleanup of unexpected directory: $tmp_dir" >&2 ;;
  esac
}
trap cleanup 0 HUP INT TERM

audit_repo=$tmp_dir/repository.git
git init --bare -q "$audit_repo"
git -C "$audit_repo" fetch -q "https://github.com/$upstream_repo.git" \
  refs/heads/main:refs/remotes/upstream/main
upstream_head=$(git -C "$audit_repo" rev-parse refs/remotes/upstream/main)

open_issues=$(gh issue list --repo "$fork_repo" --label upstream-review --state open \
  --limit 20 --json number,title,url,body,updatedAt)
open_issue=$(printf '%s' "$open_issues" | jq -c 'sort_by(.updatedAt) | last // empty')

all_issues=$(gh issue list --repo "$fork_repo" --label upstream-review --state all \
  --limit 100 --json number,title,url,body,updatedAt)
latest_issue=$(printf '%s' "$all_issues" | jq -c 'sort_by(.updatedAt) | last // empty')

marker_from_body() {
  printf '%s' "$1" | sed -n "s/.*<!-- $2:\([0-9a-f][0-9a-f]*\) -->.*/\1/p" | tail -1
}

issue_number=''
issue_url=''
reported_head=''
baseline=''

if [ -n "$open_issue" ]; then
  issue_number=$(printf '%s' "$open_issue" | jq -r '.number')
  issue_url=$(printf '%s' "$open_issue" | jq -r '.url')
  open_body=$(printf '%s' "$open_issue" | jq -r '.body')
  baseline=$(marker_from_body "$open_body" upstream-base)
  reported_head=$(marker_from_body "$open_body" upstream-head)
elif [ -n "$latest_issue" ]; then
  latest_body=$(printf '%s' "$latest_issue" | jq -r '.body')
  baseline=$(marker_from_body "$latest_body" upstream-head)
fi

if [ -z "$baseline" ] || ! git -C "$audit_repo" cat-file -e "$baseline^{commit}" 2>/dev/null; then
  git -C "$audit_repo" fetch -q "https://github.com/$fork_repo.git" \
    refs/heads/main:refs/remotes/fork/main
  baseline=$(git -C "$audit_repo" merge-base refs/remotes/fork/main refs/remotes/upstream/main)
fi

history_note='normal'
if ! git -C "$audit_repo" merge-base --is-ancestor "$baseline" refs/remotes/upstream/main; then
  git -C "$audit_repo" fetch -q "https://github.com/$fork_repo.git" \
    refs/heads/main:refs/remotes/fork/main
  baseline=$(git -C "$audit_repo" merge-base refs/remotes/fork/main refs/remotes/upstream/main)
  history_note='upstream history changed; comparison reset to current merge base'
fi

commit_count=$(git -C "$audit_repo" rev-list --count "$baseline..refs/remotes/upstream/main")
dispatch='not-needed'

if [ "$commit_count" -gt 0 ] && { [ -z "$open_issue" ] || [ "$reported_head" != "$upstream_head" ]; }; then
  if gh workflow run upstream-review.yml --repo "$fork_repo" >/dev/null 2>&1; then
    dispatch='requested'
  else
    dispatch='failed; run the Upstream Review workflow manually'
  fi
fi

report=$tmp_dir/report.txt
{
  printf 'CHECKED_DATE: %s\n' "$today"
  printf 'UPSTREAM: %s\n' "$upstream_repo"
  printf 'FORK: %s\n' "$fork_repo"
  printf 'BASELINE: %s\n' "$baseline"
  printf 'UPSTREAM_HEAD: %s\n' "$upstream_head"
  printf 'HISTORY: %s\n' "$history_note"
  printf 'NEW_COMMIT_COUNT: %s\n' "$commit_count"
  printf 'WORKFLOW_DISPATCH: %s\n' "$dispatch"
  if [ -n "$issue_number" ]; then
    printf 'REVIEW_ISSUE: #%s %s\n' "$issue_number" "$issue_url"
  fi
  if [ "$commit_count" -eq 0 ]; then
    printf '%s\n' 'STATUS: current'
  else
    if [ -n "$open_issue" ]; then
      printf '%s\n' 'STATUS: pending-review'
    else
      printf '%s\n' 'STATUS: new-activity'
    fi
    printf '%s\n' 'COMMITS:'
    git -C "$audit_repo" log --reverse --format='- %h %s' \
      "$baseline..refs/remotes/upstream/main"
    printf '%s\n' 'FILES:'
    git -C "$audit_repo" diff --name-status "$baseline..refs/remotes/upstream/main" | \
      sed 's/^/- /'
    printf '%s\n' 'DIFFSTAT:'
    git -C "$audit_repo" diff --stat "$baseline..refs/remotes/upstream/main"
  fi
} > "$report"

mkdir -p "$state_dir"
staged_state=$(mktemp "$state_dir/.upstream-audit.XXXXXX") || exit 1
cp "$report" "$staged_state"
mv -f "$staged_state" "$state_file"
cat "$report"
