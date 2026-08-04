#!/usr/bin/env python3
"""Safely copy exact legacy Sol Advisor state into Codex Orchestration once."""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import stat
import tempfile
from pathlib import Path


class StateMigrationError(RuntimeError):
    pass


LEGACY_DIRECTORY = "sol-advisor"  # Compatibility source; never used for new writes.
CURRENT_DIRECTORY = "codex-orchestration"
MIGRATION_MARKER = ".legacy-sol-advisor-state-migrated"


def _kind(path: Path) -> str:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    return "other"


def _state_parent(codex_home: Path) -> Path:
    if not codex_home.is_absolute():
        raise StateMigrationError("CODEX_HOME must resolve to an absolute path")
    state = codex_home / "state"
    kind = _kind(state)
    if kind == "symlink":
        raise StateMigrationError(f"refusing symlinked state parent: {state}")
    if kind not in {"missing", "directory"}:
        raise StateMigrationError(f"state parent is not a directory: {state}")
    return state


def _inventory(source: Path) -> list[tuple[Path, str]]:
    inventory: list[tuple[Path, str]] = []
    for root, directories, files in os.walk(source, topdown=True, followlinks=False):
        root_path = Path(root)
        for name in sorted(directories):
            item = root_path / name
            kind = _kind(item)
            if kind != "directory":
                raise StateMigrationError(f"refusing unsafe legacy state entry: {item}")
            inventory.append((item.relative_to(source), kind))
        for name in sorted(files):
            item = root_path / name
            kind = _kind(item)
            if kind != "file":
                raise StateMigrationError(f"refusing unsafe legacy state entry: {item}")
            inventory.append((item.relative_to(source), kind))
    return inventory


def _preflight(source: Path, destination: Path, inventory: list[tuple[Path, str]]) -> None:
    destination_kind = _kind(destination)
    if destination_kind == "symlink":
        raise StateMigrationError(f"refusing symlinked state destination: {destination}")
    if destination_kind not in {"missing", "directory"}:
        raise StateMigrationError(f"state destination is not a directory: {destination}")
    marker = destination / MIGRATION_MARKER
    marker_kind = _kind(marker)
    if marker_kind == "symlink":
        raise StateMigrationError(f"refusing symlinked migration marker: {marker}")
    if marker_kind not in {"missing", "file"}:
        raise StateMigrationError(f"migration marker is unsafe: {marker}")
    for relative, source_kind in inventory:
        target = destination / relative
        target_kind = _kind(target)
        if target_kind == "missing":
            continue
        if target_kind == "symlink" or target_kind != source_kind:
            raise StateMigrationError(f"refusing conflicting state destination: {target}")
        if source_kind == "file" and not filecmp.cmp(source / relative, target, shallow=False):
            raise StateMigrationError(f"refusing to overwrite conflicting new state: {target}")


def _copy_exclusive(source: Path, destination: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.chmod(temporary, stat.S_IMODE(source.stat().st_mode) & 0o700 or 0o600)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            kind = _kind(destination)
            if kind != "file" or not filecmp.cmp(source, destination, shallow=False):
                raise StateMigrationError(f"refusing to overwrite conflicting new state: {destination}")
    finally:
        temporary.unlink(missing_ok=True)


def migrate_default_state(codex_home: Path) -> Path:
    codex_home = codex_home.expanduser()
    state = _state_parent(codex_home)
    source = state / LEGACY_DIRECTORY
    destination = state / CURRENT_DIRECTORY
    source_kind = _kind(source)
    if source_kind == "missing":
        if _kind(destination) == "symlink":
            raise StateMigrationError(f"refusing symlinked state destination: {destination}")
        return destination
    if source_kind != "directory":
        raise StateMigrationError(f"refusing unsafe legacy state source: {source}")

    marker = destination / MIGRATION_MARKER
    _preflight(source, destination, [])
    if _kind(marker) == "file":
        return destination

    inventory = _inventory(source)
    _preflight(source, destination, inventory)

    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.mkdir(exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    for relative, source_kind in inventory:
        target = destination / relative
        if source_kind == "directory":
            target.mkdir(exist_ok=True, mode=0o700)
            if _kind(target) != "directory":
                raise StateMigrationError(f"state destination changed during migration: {target}")
        elif _kind(target) == "missing":
            _copy_exclusive(source / relative, target)

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{MIGRATION_MARKER}.", dir=destination)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text("copied from state/sol-advisor without overwriting conflicts\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        try:
            os.link(temporary, marker)
        except FileExistsError:
            if _kind(marker) != "file":
                raise StateMigrationError(f"migration marker changed during migration: {marker}")
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(migrate_default_state(args.codex_home))
    except StateMigrationError as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
