#!/usr/bin/env python3
"""Small, chat-scoped state helpers shared by Codex Orchestration hooks."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def state_root() -> Path | None:
    configured = os.environ.get("CODEX_ORCHESTRATION_RUNTIME_STATE_DIR")
    plugin_data = os.environ.get("PLUGIN_DATA")
    codex_home = os.environ.get("CODEX_HOME")
    value = configured or plugin_data or codex_home or str(Path.home() / ".codex")
    root = Path(value).expanduser()
    if not root.is_absolute() or root.is_symlink():
        return None
    if configured:
        pass
    elif plugin_data:
        root = root / "chat-state"
    else:
        root = root / "orchestration" / "chat-state"
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
    except OSError:
        return None
    return root


def state_path(session_id: str) -> Path | None:
    root = state_root()
    if root is None or not ID_RE.fullmatch(session_id):
        return None
    return root / f"{session_id}.json"


def read_state(session_id: str) -> dict[str, Any]:
    path = state_path(session_id)
    if path is None or not path.is_file() or path.is_symlink():
        return {"active": False}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"active": False}
    if not isinstance(value, dict) or not isinstance(value.get("active"), bool):
        return {"active": False}
    return value


def write_state(session_id: str, *, active: bool) -> bool:
    path = state_path(session_id)
    if path is None:
        return False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {"active": active, "session_id": session_id},
                handle,
                separators=(",", ":"),
                sort_keys=True,
            )
            handle.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
        return True
    except OSError:
        return False
    finally:
        if "temporary_name" in locals():
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def transcript_role(transcript_value: Any) -> str | None:
    """Read only the transcript header; never scan the active chat."""
    if not isinstance(transcript_value, str):
        return None
    transcript = Path(transcript_value)
    if not transcript.is_file() or transcript.is_symlink():
        return None
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for _ in range(12):
                line = handle.readline()
                if not line:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "session_meta":
                    continue
                role = (event.get("payload") or {}).get("agent_role")
                return role if isinstance(role, str) and role else None
    except OSError:
        return None
    return None


def is_active(session_id: Any) -> bool:
    return isinstance(session_id, str) and bool(read_state(session_id).get("active"))
