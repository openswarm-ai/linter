"""``swarm-lint init`` scaffolding logic."""

from __future__ import annotations

import importlib.resources
import json
import os
from pathlib import Path


def _pkg_text(subpath: str) -> str:
    """Read a text file bundled inside the swarm_lint package."""
    ref = importlib.resources.files("swarm_lint") / subpath
    return ref.read_text(encoding="utf-8")


def _write_if_missing(dest: Path, content: str, label: str) -> None:
    if dest.exists():
        print(f"  skip: {dest} already exists")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  created: {dest}  ({label})")


def run_init(
    root: Path,
    *,
    with_tasks: bool = False,
    with_pyright: bool = False,
    with_whitelist: bool = False,
) -> None:
    """Scaffold configuration files into *root*."""
    print(f"Initializing swarm-lint in {root}\n")

    defaults_json = _pkg_text("defaults/config.json")
    pretty = json.dumps(json.loads(defaults_json), indent=2) + "\n"
    _write_if_missing(root / ".swarm-lint.json", pretty, "config — customize to your project")

    if with_tasks:
        tasks_json = _pkg_text("templates/tasks.json")
        _write_if_missing(root / ".vscode" / "tasks.json", tasks_json, "VS Code lint:watch task")

    if with_pyright:
        pyright_json = _pkg_text("templates/pyrightconfig.json")
        _write_if_missing(root / "pyrightconfig.json", pyright_json, "Pyright config template")

    if with_whitelist:
        whitelist_py = _pkg_text("defaults/vulture_whitelist.py")
        _write_if_missing(root / "vulture_whitelist.py", whitelist_py, "Vulture false-positive suppressions")

    print(f"\nDone. Edit .swarm-lint.json to match your project layout.")
    print("Run  swarm-lint check --root .  to verify.")
