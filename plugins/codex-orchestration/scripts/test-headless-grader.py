#!/usr/bin/env python3
"""Hermetic execution tests for the no-chip Terra / Max grader."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run_helper(
    helper: Path,
    fake_codex: Path,
    state: Path,
    token: str,
    result: dict[str, object],
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["CODEX_ORCHESTRATION_CODEX_BIN"] = str(fake_codex)
    environment["CODEX_ORCHESTRATION_RUNTIME_STATE_DIR"] = str(state)
    environment["FAKE_GRADER_RESULT"] = json.dumps(result, separators=(",", ":"))
    return subprocess.run(
        [sys.executable, str(helper), "--request-token", token],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def stage_request(plugin: Path, state: Path, prompt: str, prior: str = "NONE") -> str:
    sys.path.insert(0, str(plugin / "scripts"))
    from orchestration_state import write_grader_request

    os.environ["CODEX_ORCHESTRATION_RUNTIME_STATE_DIR"] = str(state)
    token = write_grader_request(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        prompt=prompt,
        prior_acceptance=prior,
        recent_context="USER: Keep the existing layout.",
    )
    if token is None:
        raise AssertionError("could not stage a grader request")
    return token


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test-headless-grader.py <plugin-dir> <temp-dir>")
    plugin = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    temporary.mkdir(parents=True, exist_ok=True)
    state = temporary / "state"
    state.mkdir()
    helper = plugin / "scripts" / "headless-grader.py"
    fake_codex = temporary / "fake-codex"
    fake_codex.write_text(
        """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
required = ["exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "--sandbox", "read-only", "--model",
            "gpt-5.6-terra", "--config", 'model_reasoning_effort="max"',
            "--output-schema", "--json", "-"]
for value in required:
    if value not in args:
        raise SystemExit(3)
schema = pathlib.Path(args[args.index("--output-schema") + 1])
if not schema.is_file() or json.loads(schema.read_text()).get("additionalProperties") is not False:
    raise SystemExit(4)
prompt = sys.stdin.read()
for value in ("SMALL_TWEAK", "A feature release is a build", "USER_REQUEST"):
    if value not in prompt:
        raise SystemExit(5)
message = os.environ["FAKE_GRADER_RESULT"]
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": message}}))
print(json.dumps({"type": "turn.completed"}))
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o700)

    token = stage_request(plugin, state, "Fix the existing subtitle")
    result = {
        "relation": "NEW",
        "active_objective": "Fix the existing subtitle",
        "explicit_signal": "NONE",
        "work_class": "SMALL_TWEAK",
        "complexity": 2.4,
        "outcome": "Subtitle is concise; and accurate",
        "must": "Change only the subtitle",
        "must_not": "Alter the layout",
        "destinations": "repository and local runtime",
        "proof": "focused UI test",
    }
    completed = run_helper(helper, fake_codex, state, token, result)
    if completed.returncode != 0:
        raise AssertionError(f"headless grader failed: {completed.stderr}")
    required_lines = (
        "ORCHESTRATION_RELATION: RELATION=NEW",
        "ORCHESTRATION_ROUTE: CLASS=SMALL_TWEAK; COMPLEXITY=2.4; IMPLEMENTER=LUNA_MAX; SUPERVISOR=TERRA_MAX; CHECKPOINTS=RELEASE_CANDIDATE",
        "ORCHESTRATION_STATUS: Small tweak -> Luna / Max.",
        "OUTCOME=Subtitle is concise, and accurate",
    )
    for value in required_lines:
        if value not in completed.stdout:
            raise AssertionError(f"headless output omitted {value!r}: {completed.stdout}")
    request_path = state / "grader-requests" / f"{token}.json"
    if request_path.exists():
        raise AssertionError("consumed grader request remained on disk")

    cancel_token = stage_request(
        plugin,
        state,
        "Cancel that change",
        "ORCHESTRATION_ACCEPTANCE: OUTCOME=Ship subtitle; MUST=edit; MUST_NOT=NONE; DESTINATIONS=repo; PROOF=test",
    )
    cancel = dict(result)
    cancel.update(
        relation="CANCEL",
        explicit_signal="Cancel that change",
        work_class="BIG_BUILD",
        complexity=9.0,
    )
    cancelled = run_helper(helper, fake_codex, state, cancel_token, cancel)
    if cancelled.returncode != 0:
        raise AssertionError(f"cancel grading failed: {cancelled.stderr}")
    if (
        "CLASS=READ_ONLY; COMPLEXITY=1.0; IMPLEMENTER=NONE; SUPERVISOR=NONE; CHECKPOINTS=NONE"
        not in cancelled.stdout
    ):
        raise AssertionError(f"cancel route was not normalized: {cancelled.stdout}")

    print("PASS: headless Terra / Max grading emits fixed routes without a subagent chip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
