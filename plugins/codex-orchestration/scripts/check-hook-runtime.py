#!/usr/bin/env python3
"""Require the installed Orchestration prompt hook to be enabled and trusted."""

from __future__ import annotations

import argparse
import json
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PLUGIN_ID = "codex-orchestration@codex-orchestration"
EVENT = "userPromptSubmit"


def send(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin is unavailable")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def receive(process: subprocess.Popen[str], request_id: int, timeout: float) -> dict[str, Any]:
    if process.stdout is None:
        raise RuntimeError("Codex app-server stdout is unavailable")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([process.stdout], [], [], max(0.0, deadline - time.monotonic()))
        if not ready:
            break
        line = process.stdout.readline()
        if not line:
            break
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == request_id:
            return message
    raise RuntimeError(f"Codex app-server did not answer request {request_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", type=Path, required=True)
    args = parser.parse_args()
    cwd = args.cwd.resolve()

    process = subprocess.Popen(
        [args.codex_bin, "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    try:
        send(
            process,
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "codex-orchestration-hook-check",
                        "title": "Codex Orchestration Hook Check",
                        "version": "1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
        )
        initialized = receive(process, 1, 5)
        if "error" in initialized:
            raise RuntimeError(f"Codex app-server initialization failed: {initialized['error']}")
        send(process, {"method": "initialized", "params": {}})
        send(process, {"method": "hooks/list", "id": 2, "params": {"cwds": [str(cwd)]}})
        response = receive(process, 2, 8)
        if "error" in response:
            raise RuntimeError(f"Codex hooks/list failed: {response['error']}")
    except (OSError, RuntimeError) as exc:
        print(f"FAIL: could not verify the live Orchestration hook: {exc}", file=sys.stderr)
        return 1
    finally:
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=2)

    entries = response.get("result", {}).get("data", [])
    hooks = [
        hook
        for entry in entries
        if entry.get("cwd") == str(cwd)
        for hook in entry.get("hooks", [])
        if hook.get("pluginId") == PLUGIN_ID and hook.get("eventName") == EVENT
    ]
    if len(hooks) != 1:
        print(f"FAIL: expected exactly one installed {EVENT} hook, found {len(hooks)}", file=sys.stderr)
        return 1
    hook = hooks[0]
    if not hook.get("enabled"):
        print("FAIL: the Codex Orchestration prompt hook is disabled", file=sys.stderr)
        return 1
    if hook.get("trustStatus") != "trusted":
        print(
            "FAIL: the Codex Orchestration prompt hook is not trusted; open /hooks, "
            "review the exact hook, trust it once, and rerun the installer",
            file=sys.stderr,
        )
        return 1
    print("PASS: the installed Codex Orchestration prompt hook is enabled and trusted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
