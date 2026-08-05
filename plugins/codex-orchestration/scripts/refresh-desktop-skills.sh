#!/bin/sh
# Refresh Codex Desktop's live skill catalog after a plugin update.

set -eu

pass() { printf '%s\n' "PASS: $*"; }
fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }

case "$(uname -s 2>/dev/null || true)" in
  Darwin) ;;
  *)
    printf '%s\n' "NOTICE: Codex Desktop skill refresh is only needed on a running macOS desktop app."
    exit 0
    ;;
esac

command -v osascript >/dev/null 2>&1 ||
  fail "osascript is required to refresh a running Codex Desktop app"

app_running=$(osascript -e 'application "ChatGPT" is running') ||
  fail "could not determine whether Codex Desktop is running"
if [ "$app_running" != true ]; then
  printf '%s\n' "NOTICE: Codex Desktop is not running; its next launch will read the installed plugin."
  exit 0
fi

# Codex Desktop exposes this built-in action in its command menu. It calls
# skills/list with forceReload=true, so the running host drops stale plugin skills
# without an app restart or any per-task work.
osascript \
  -e 'tell application "ChatGPT" to activate' \
  -e 'delay 0.3' \
  -e 'tell application "System Events"' \
  -e 'keystroke "k" using command down' \
  -e 'delay 0.3' \
  -e 'keystroke "Force reload skills"' \
  -e 'delay 0.5' \
  -e 'key code 36' \
  -e 'delay 0.5' \
  -e 'end tell' >/dev/null ||
  fail "Codex Desktop could not run Force reload skills; allow Accessibility control and retry"

pass "refreshed the running Codex Desktop skill catalog without restarting it"
