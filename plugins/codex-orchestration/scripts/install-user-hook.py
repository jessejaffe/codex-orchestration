#!/usr/bin/env python3
"""Install and trust the stable user-level Orchestration prompt hook."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


EVENT = "userPromptSubmit"
PLUGIN_ID = "codex-orchestration@codex-orchestration"
RUNTIME_FILES = (
    "orchestration_state.py",
    "prompt-router-hook.py",
)
RETIRED_RUNTIME_DIGESTS = {
    "headless-grader.py": {
        "776152a8ba02f56a21c9df680755df2d641f45a1bfc0431f1c1b12167411399f"
    }
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def atomic_copy(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        fail(f"runtime source is missing or unsafe: {source}")
    if destination.exists() and (destination.is_symlink() or not destination.is_file()):
        fail(f"runtime destination is unsafe: {destination}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as target, source.open("rb") as origin:
            shutil.copyfileobj(origin, target)
        os.chmod(temporary_name, 0o700)
        os.replace(temporary_name, destination)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def preflight_retired_runtime_files(runtime_dir: Path, check_only: bool) -> None:
    for filename, known_digests in RETIRED_RUNTIME_DIGESTS.items():
        destination = runtime_dir / filename
        if not destination.exists() and not destination.is_symlink():
            continue
        if destination.is_symlink() or not destination.is_file():
            fail(f"retired runtime destination is unsafe: {destination}")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest not in known_digests:
            fail(f"refusing customized retired runtime file: {destination}")
        if check_only:
            fail(f"retired runtime file remains: {destination}")


def retire_runtime_files(runtime_dir: Path) -> None:
    for filename, known_digests in RETIRED_RUNTIME_DIGESTS.items():
        destination = runtime_dir / filename
        if not destination.exists() and not destination.is_symlink():
            continue
        if destination.is_symlink() or not destination.is_file():
            fail(f"retired runtime destination changed during install: {destination}")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest not in known_digests:
            fail(f"retired runtime file changed during install: {destination}")
        destination.unlink()


def is_owned_group(group: object) -> bool:
    if not isinstance(group, dict):
        return False
    handlers = group.get("hooks")
    if not isinstance(handlers, list):
        return False
    return any(
        isinstance(handler, dict)
        and isinstance(handler.get("command"), str)
        and "orchestration/prompt-router-hook.py" in handler["command"]
        for handler in handlers
    )


def merge_hook_document(document: object, command: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        fail("the user hooks file must contain a JSON object")
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        fail("the user hooks file has a non-object hooks value")
    groups = hooks.setdefault("UserPromptSubmit", [])
    if not isinstance(groups, list):
        fail("the user hooks file has a non-array UserPromptSubmit value")
    owned_indexes = [index for index, group in enumerate(groups) if is_owned_group(group)]
    if len(owned_indexes) > 1:
        fail("the user hooks file contains duplicate Codex Orchestration prompt hooks")
    owned_group = {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 15,
            }
        ]
    }
    if owned_indexes:
        groups[owned_indexes[0]] = owned_group
    else:
        groups.append(owned_group)
    return document


def read_hook_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"description": "User-level Codex lifecycle hooks.", "hooks": {}}
    if path.is_symlink() or not path.is_file():
        fail(f"user hooks path is unsafe: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"user hooks file is invalid JSON: {exc}")


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def send(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if process.stdin is None:
        fail("Codex app-server stdin is unavailable")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def receive(process: subprocess.Popen[str], request_id: int, timeout: float) -> dict[str, Any]:
    if process.stdout is None:
        fail("Codex app-server stdout is unavailable")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select(
            [process.stdout], [], [], max(0.0, deadline - time.monotonic())
        )
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
    fail(f"Codex app-server did not answer request {request_id}")


def request(
    process: subprocess.Popen[str], request_id: int, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    send(process, {"method": method, "id": request_id, "params": params})
    response = receive(process, request_id, 8)
    if "error" in response:
        fail(f"Codex {method} failed: {response['error']}")
    return response.get("result", {})


def find_installed_hook(
    result: dict[str, Any], cwd: Path, hook_path: Path, command: str
) -> dict[str, Any]:
    expected_source = hook_path.resolve()
    all_hooks = [
        hook
        for entry in result.get("data", [])
        if entry.get("cwd") == str(cwd)
        for hook in entry.get("hooks", [])
    ]
    stale_plugin_hooks = [
        hook
        for hook in all_hooks
        if hook.get("pluginId") == PLUGIN_ID and hook.get("eventName") == EVENT
    ]
    if stale_plugin_hooks:
        fail("the installed plugin still advertises its former versioned prompt hook")
    matches = [
        hook
        for hook in all_hooks
        if isinstance(hook.get("sourcePath"), str)
        and Path(hook["sourcePath"]).resolve() == expected_source
        and hook.get("eventName") == EVENT
        and hook.get("command") == command
    ]
    if len(matches) != 1:
        fail(f"expected one installed user-level {EVENT} hook, found {len(matches)}")
    return matches[0]


def trust_and_check(
    codex_bin: str,
    codex_home: Path,
    cwd: Path,
    hook_path: Path,
    command: str,
    check_only: bool,
) -> None:
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(codex_home)
    process = subprocess.Popen(
        [codex_bin, "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=environment,
    )
    try:
        send(
            process,
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "codex-orchestration-user-hook-installer",
                        "title": "Codex Orchestration User Hook Installer",
                        "version": "1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
        )
        initialized = receive(process, 1, 5)
        if "error" in initialized:
            fail(f"Codex app-server initialization failed: {initialized['error']}")
        send(process, {"method": "initialized", "params": {}})
        listed = request(process, 2, "hooks/list", {"cwds": [str(cwd)]})
        hook = find_installed_hook(listed, cwd, hook_path, command)
        if not hook.get("enabled"):
            fail("the user-level Codex Orchestration prompt hook is disabled")
        if hook.get("trustStatus") != "trusted":
            if check_only:
                fail("the user-level Codex Orchestration prompt hook is not trusted")
            request(
                process,
                3,
                "config/batchWrite",
                {
                    "edits": [
                        {
                            "keyPath": "hooks.state",
                            "value": {
                                hook["key"]: {
                                    "enabled": True,
                                    "trusted_hash": hook["currentHash"],
                                }
                            },
                            "mergeStrategy": "upsert",
                        }
                    ],
                    "reloadUserConfig": True,
                },
            )
            listed = request(process, 4, "hooks/list", {"cwds": [str(cwd)]})
            hook = find_installed_hook(listed, cwd, hook_path, command)
        if not hook.get("enabled") or hook.get("trustStatus") != "trusted":
            fail("the user-level Codex Orchestration prompt hook is not enabled and trusted")
    finally:
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--plugin-dir", type=Path)
    args = parser.parse_args()

    plugin_dir = (args.plugin_dir or Path(__file__).resolve().parent.parent).resolve()
    codex_home = args.codex_home or Path(
        os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    )
    codex_home = codex_home.expanduser()
    if not codex_home.is_absolute() or codex_home.is_symlink():
        fail(f"Codex home is unsafe: {codex_home}")
    if not codex_home.exists():
        if args.check:
            fail(f"Codex home does not exist: {codex_home}")
        codex_home.mkdir(parents=True, mode=0o700)
    if not codex_home.is_dir():
        fail(f"Codex home is not a directory: {codex_home}")

    runtime_dir = codex_home / "orchestration"
    if runtime_dir.exists() and (runtime_dir.is_symlink() or not runtime_dir.is_dir()):
        fail(f"Orchestration runtime path is unsafe: {runtime_dir}")
    if not runtime_dir.exists():
        if args.check:
            fail(f"Orchestration runtime is missing: {runtime_dir}")
        runtime_dir.mkdir(mode=0o700)
    if not args.check:
        os.chmod(runtime_dir, 0o700)

    preflight_retired_runtime_files(runtime_dir, args.check)
    for filename in RUNTIME_FILES:
        source = plugin_dir / "scripts" / filename
        destination = runtime_dir / filename
        if args.check:
            if (
                not destination.is_file()
                or destination.is_symlink()
                or source.read_bytes() != destination.read_bytes()
            ):
                fail(f"installed runtime file is not current: {destination}")
        else:
            atomic_copy(source, destination)
    if not args.check:
        retire_runtime_files(runtime_dir)

    router = runtime_dir / "prompt-router-hook.py"
    command = f"python3 {shlex.quote(str(router))}"
    hook_path = codex_home / "hooks.json"
    document = read_hook_document(hook_path)
    merged = merge_hook_document(copy.deepcopy(document), command)
    if args.check:
        if merged != document:
            fail(f"user-level hook declaration is not current: {hook_path}")
    else:
        atomic_write_json(hook_path, merged)

    check_cwds = tuple(dict.fromkeys((plugin_dir, Path.home().resolve())))
    for check_cwd in check_cwds:
        trust_and_check(
            args.codex_bin,
            codex_home,
            check_cwd,
            hook_path,
            command,
            args.check,
        )
    print(
        "PASS: stable user-level Orchestration hook is installed, enabled, and "
        "trusted across project and user scopes"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
