#!/usr/bin/env python3
"""Run the Terra / Max classifier without creating a visible subagent chip."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from orchestration_state import consume_grader_request


MODEL = "gpt-5.6-terra"
EFFORT = "max"
LANES = {
    "READ_ONLY": ("TERRA_MAX", "NONE", "NONE"),
    "SMALL_TWEAK": ("LUNA_MAX", "TERRA_MAX", "RELEASE_CANDIDATE"),
    "BIG_TWEAK": (
        "TERRA_MAX",
        "TERRA_MAX",
        "ROOT_CAUSE,RELEASE_CANDIDATE",
    ),
    "SMALL_BUILD": (
        "TERRA_MAX",
        "SOL_HIGH",
        "DESIGN,RELEASE_CANDIDATE",
    ),
    "BIG_BUILD": (
        "SOL_HIGH",
        "SOL_XHIGH",
        "ARCHITECTURE,VERTICAL_SLICE,RELEASE_CANDIDATE",
    ),
}
CLASS_STATUS = {
    "READ_ONLY": "Read-only -> Terra / Max. Gathering evidence now.",
    "SMALL_TWEAK": "Small tweak -> Luna / Max. Starting the focused change now.",
    "BIG_TWEAK": "Big tweak -> Terra / Max. Tracing the existing behavior before changing it.",
    "SMALL_BUILD": "Small build -> Terra / Max. Establishing the design before implementation.",
    "BIG_BUILD": "Big build -> Sol / High. Establishing architecture before implementation.",
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "relation": {
            "type": "string",
            "enum": ["NEW", "AMEND", "REPLACE", "CANCEL"],
        },
        "active_objective": {"type": "string", "minLength": 1},
        "explicit_signal": {"type": "string", "minLength": 1},
        "work_class": {"type": "string", "enum": list(LANES)},
        "complexity": {"type": "number", "minimum": 1, "maximum": 10},
        "outcome": {"type": "string", "minLength": 1},
        "must": {"type": "string", "minLength": 1},
        "must_not": {"type": "string", "minLength": 1},
        "destinations": {"type": "string", "minLength": 1},
        "proof": {"type": "string", "minLength": 1},
    },
    "required": [
        "relation",
        "active_objective",
        "explicit_signal",
        "work_class",
        "complexity",
        "outcome",
        "must",
        "must_not",
        "destinations",
        "proof",
    ],
    "additionalProperties": False,
}


def compact(value: str, limit: int = 4_096) -> str:
    return " ".join(value.replace(";", ",").split())[:limit] or "NONE"


def grader_prompt(request: dict[str, Any], repair: str | None = None) -> str:
    prompt = f"""You are Codex Orchestration's read-only grader-dispatcher. Do not call tools,
inspect files, spawn agents, implement, or explain. Return only the JSON required by the supplied
schema.

Classify relationship to PRIOR_ACTIVE_ACCEPTANCE as NEW, AMEND, REPLACE, or CANCEL. When prior is
NONE, use NEW unless the request explicitly cancels. With prior present, use AMEND and preserve the
unfinished outcome, mutation/read-only mode, prohibitions, destinations, and proof while adding the
new requirement. REPLACE or CANCEL requires an exact explicit quote from USER_REQUEST; an
interruption is not a signal.

Classify the combined objective:
- READ_ONLY: no mutation.
- SMALL_TWEAK: refine one existing behavior in one production component.
- BIG_TWEAK: refine existing behavior across 2+ components or an interface/runtime boundary.
- SMALL_BUILD: one new capability in at most 2 components with settled architecture.
- BIG_BUILD: 2+ capabilities, 3+ components, a runtime boundary, material risk, or open architecture.
Tests, docs, release work, and deployment do not add components. A feature release is a build.
Ambiguity routes upward. Complexity is one-decimal telemetry from 1.0 through 10.0 only.

PRIOR_ACTIVE_ACCEPTANCE:
{request['prior_acceptance']}

RECENT_TASK_CONTEXT:
{request['recent_context'] or 'NONE'}

USER_REQUEST:
{request['prompt']}
"""
    if repair:
        prompt += f"\nREPAIR THE PREVIOUS INVALID RESULT: {repair}\n"
    return prompt


def timeout_seconds() -> int:
    raw = os.environ.get("CODEX_ORCHESTRATION_GRADER_TIMEOUT_SECONDS", "40")
    try:
        value = int(raw)
    except ValueError:
        return 40
    return min(120, max(5, value))


def codex_binary() -> str | None:
    configured = os.environ.get("CODEX_ORCHESTRATION_CODEX_BIN")
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_absolute() and path.is_file() else None
    return shutil.which("codex")


def agent_message(stdout: str) -> str | None:
    final: str | None = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                final = text
    return final


def run_once(
    binary: str, request: dict[str, Any], schema_path: Path, repair: str | None
) -> tuple[dict[str, Any] | None, str]:
    command = [
        binary,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        MODEL,
        "--config",
        f'model_reasoning_effort="{EFFORT}"',
        "--output-schema",
        str(schema_path),
        "--json",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            input=grader_prompt(request, repair),
            capture_output=True,
            text=True,
            timeout=timeout_seconds(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"headless Terra grader could not run: {exc}"
    message = agent_message(completed.stdout)
    if completed.returncode != 0 or message is None:
        detail = compact(completed.stderr[-1_000:] or completed.stdout[-1_000:])
        return None, f"headless Terra grader failed ({completed.returncode}): {detail}"
    try:
        value = json.loads(message)
    except json.JSONDecodeError as exc:
        return None, f"grader output was not JSON: {exc}"
    return value if isinstance(value, dict) else None, "grader output was not an object"


def validate(value: dict[str, Any], prior: str) -> str | None:
    required = set(OUTPUT_SCHEMA["required"])
    if set(value) != required:
        return "grader output keys did not match the schema"
    relation = value.get("relation")
    work_class = value.get("work_class")
    complexity = value.get("complexity")
    if relation not in ("NEW", "AMEND", "REPLACE", "CANCEL"):
        return "invalid relation"
    if work_class not in LANES:
        return "invalid work class"
    if isinstance(complexity, bool) or not isinstance(complexity, (int, float)):
        return "complexity was not numeric"
    if not 1 <= float(complexity) <= 10:
        return "complexity was outside 1.0-10.0"
    prior_exists = prior != "NONE"
    if prior_exists and relation == "NEW":
        return "NEW cannot discard unfinished acceptance"
    if not prior_exists and relation in ("AMEND", "REPLACE"):
        return f"{relation} requires prior acceptance"
    signal = compact(str(value.get("explicit_signal", "")))
    if relation in ("REPLACE", "CANCEL") and signal == "NONE":
        return f"{relation} requires an explicit current-request signal"
    for field in required - {"complexity"}:
        if not isinstance(value.get(field), str) or not value[field].strip():
            return f"{field} was empty"
    return None


def render(value: dict[str, Any]) -> str:
    relation = value["relation"]
    work_class = value["work_class"]
    if relation == "CANCEL":
        work_class = "READ_ONLY"
        complexity = 1.0
        implementer, supervisor, checkpoints = "NONE", "NONE", "NONE"
        status = "Request cancelled. No implementation agent will start."
    else:
        complexity = round(float(value["complexity"]), 1)
        implementer, supervisor, checkpoints = LANES[work_class]
        status = CLASS_STATUS[work_class]
    lines = (
        "ORCHESTRATION_RELATION: "
        f"RELATION={relation}; ACTIVE_OBJECTIVE={compact(value['active_objective'])}; "
        f"EXPLICIT_SIGNAL={compact(value['explicit_signal'])}",
        "ORCHESTRATION_ROUTE: "
        f"CLASS={work_class}; COMPLEXITY={complexity:.1f}; IMPLEMENTER={implementer}; "
        f"SUPERVISOR={supervisor}; CHECKPOINTS={checkpoints}",
        f"ORCHESTRATION_STATUS: {status}",
        "ORCHESTRATION_ACCEPTANCE: "
        f"OUTCOME={compact(value['outcome'])}; MUST={compact(value['must'])}; "
        f"MUST_NOT={compact(value['must_not'])}; DESTINATIONS={compact(value['destinations'])}; "
        f"PROOF={compact(value['proof'])}",
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-token", required=True)
    args = parser.parse_args()
    request = consume_grader_request(args.request_token)
    if request is None:
        print("HEADLESS_GRADER_ERROR: request is missing, expired, or unsafe", file=sys.stderr)
        return 2
    binary = codex_binary()
    if binary is None:
        print("HEADLESS_GRADER_ERROR: Codex executable is unavailable", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="codex-orchestration-grader-") as temporary:
        schema_path = Path(temporary) / "schema.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA), encoding="utf-8")
        repair: str | None = None
        last_error = "unknown grader failure"
        for _ in range(2):
            value, execution_error = run_once(binary, request, schema_path, repair)
            if value is None:
                last_error = execution_error
            else:
                validation_error = validate(value, request["prior_acceptance"])
                if validation_error is None:
                    print(render(value))
                    return 0
                last_error = validation_error
            repair = last_error
    print(f"HEADLESS_GRADER_ERROR: {compact(last_error, 1_000)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
