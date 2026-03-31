"""Interactive setup wizard for swarm-lint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel

from swarm_lint.config import load_defaults

console = Console()

CHECKS: dict[str, str] = {
    "max-file-lines": "Structural: file line count limits",
    "max-folder-items": "Structural: folder item count limits",
    "no-nested-imports": "Structural: nested import detection",
    "vulture": "Vulture: dead Python code detection",
    "eslint": "ESLint: TypeScript/React linting",
    "knip": "Knip: unused TS exports/deps/files",
}

SKIP_DIRS = frozenset({
    "node_modules", "__pycache__", "dist", "build", ".venv", "venv",
    ".git", ".cursor", ".vscode", ".tox", ".mypy_cache", ".pytest_cache",
    "env", ".egg-info", "site-packages",
})


def _abort() -> None:
    console.print("\n[yellow]Aborted.[/yellow]")
    raise SystemExit(1)


def _ask(result: Any) -> Any:
    """Unwrap a questionary answer, aborting on Ctrl-C (None)."""
    if result is None:
        _abort()
    return result


def _detect_python_dirs(root: Path) -> list[str]:
    """Top-level directories containing .py files."""
    found: list[str] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        if any(entry.rglob("*.py")):
            found.append(entry.name)
    return found


def _detect_ts_dirs(root: Path) -> list[str]:
    """Top-level directories containing .ts / .tsx files."""
    found: list[str] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        has_ts = any(entry.rglob("*.ts")) or any(entry.rglob("*.tsx"))
        if has_ts:
            found.append(entry.name)
    return found


def _find_venvs(root: Path) -> list[str]:
    """Virtual-environment directories (top-level and one level deep)."""
    venvs: list[str] = []
    for name in (".venv", "venv", "env"):
        if (root / name / "bin").is_dir() or (root / name / "Scripts").is_dir():
            venvs.append(name)
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        for name in (".venv", "venv"):
            candidate = entry / name
            if (candidate / "bin").is_dir() or (candidate / "Scripts").is_dir():
                venvs.append(f"{entry.name}/{name}")
    return venvs


def _find_node_modules(root: Path) -> list[str]:
    """Directories that contain a node_modules folder."""
    dirs: list[str] = []
    if (root / "node_modules").is_dir():
        dirs.append(".")
    for entry in root.iterdir():
        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in SKIP_DIRS:
            if (entry / "node_modules").is_dir():
                dirs.append(entry.name)
    return dirs


def _scaffold_file(root: Path, subpath: str, dest: Path) -> None:
    from swarm_lint.init_cmd import _pkg_text
    if dest.exists():
        console.print(f"  [yellow]skip[/yellow] {dest.relative_to(root)} already exists")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_pkg_text(subpath), encoding="utf-8")
    console.print(f"  [green]\u2713[/green] Created [bold]{dest.relative_to(root)}[/bold]")


def run_setup(root: Path) -> None:
    console.print()
    console.print(Panel(
        "[bold]Let's configure swarm-lint for your project.[/bold]",
        title="swarm-lint setup",
        border_style="blue",
    ))
    console.print()

    # --- detect project layout ---
    py_dirs = _detect_python_dirs(root)
    ts_dirs = _detect_ts_dirs(root)
    venvs = _find_venvs(root)
    nm_dirs = _find_node_modules(root)

    if py_dirs or ts_dirs:
        parts: list[str] = []
        if py_dirs:
            parts.append(f"Python in [bold]{', '.join(py_dirs)}[/bold]")
        if ts_dirs:
            parts.append(f"TypeScript in [bold]{', '.join(ts_dirs)}[/bold]")
        sep = " \u00b7 "
        console.print(f"  Detected: {sep.join(parts)}")
        console.print()

    # --- choose checks ---
    defaults = load_defaults()
    check_choices = []
    for key, label in CHECKS.items():
        checked = defaults["enabled"].get(key, True)
        if key == "vulture" and not py_dirs:
            checked = False
        elif key in ("eslint", "knip") and not ts_dirs:
            checked = False
        check_choices.append(questionary.Choice(label, value=key, checked=checked))

    enabled_checks: list[str] = _ask(questionary.checkbox(
        "Which checks do you want to enable?",
        choices=check_choices,
    ).ask())

    # --- structural rules ---
    console.print()
    max_lines = _ask(questionary.text(
        "Max lines per file:",
        default=str(defaults["rules"]["max-file-lines"]),
        validate=lambda x: True if x.isdigit() and int(x) > 0 else "Enter a positive integer",
    ).ask())

    max_items = _ask(questionary.text(
        "Max items per folder:",
        default=str(defaults["rules"]["max-folder-items"]),
        validate=lambda x: True if x.isdigit() and int(x) > 0 else "Enter a positive integer",
    ).ask())

    config: dict[str, Any] = {
        "enabled": {k: (k in enabled_checks) for k in CHECKS},
        "rules": {
            "max-file-lines": int(max_lines),
            "max-folder-items": int(max_items),
            "no-nested-imports": "no-nested-imports" in enabled_checks,
        },
    }

    # --- vulture ---
    if "vulture" in enabled_checks:
        console.print()
        console.print("[bold]\u2500\u2500 Vulture Configuration \u2500\u2500[/bold]")

        default_targets = ", ".join(py_dirs) if py_dirs else "."
        targets = _ask(questionary.text(
            "Python directories to scan (comma-separated):",
            default=default_targets,
        ).ask())

        venv_default = venvs[0] if venvs else ""
        venv_path = _ask(questionary.text(
            "Virtual environment path (leave empty for system vulture):",
            default=venv_default,
        ).ask())

        config["vulture"] = {
            "targets": [t.strip() for t in targets.split(",") if t.strip()],
            "venv_path": venv_path or None,
            "exclude": defaults["vulture"]["exclude"],
            "whitelist": None,
        }
        config["rules"]["vulture-min-confidence"] = defaults["rules"]["vulture-min-confidence"]
        config["rules"]["vulture-error-threshold"] = defaults["rules"]["vulture-error-threshold"]

    # --- eslint / knip ---
    if "eslint" in enabled_checks or "knip" in enabled_checks:
        console.print()
        console.print("[bold]\u2500\u2500 Frontend Configuration \u2500\u2500[/bold]")

        fe_default = nm_dirs[0] if nm_dirs else (ts_dirs[0] if ts_dirs else ".")
        fe_dir = _ask(questionary.text(
            "Frontend directory (where node_modules lives):",
            default=fe_default,
        ).ask())

        if "eslint" in enabled_checks:
            config["eslint"] = {
                "directory": fe_dir,
                "args": defaults["eslint"]["args"],
            }
        if "knip" in enabled_checks:
            config["knip"] = {"directory": fe_dir}

    # --- scaffold extras ---
    console.print()
    scaffold_choices = [
        questionary.Choice(".vscode/tasks.json  \u2014 auto-run lint on workspace open", value="tasks", checked=True),
        questionary.Choice("pyrightconfig.json  \u2014 Python type checking template", value="pyright", checked=False),
        questionary.Choice("vulture_whitelist.py \u2014 false-positive suppressions", value="whitelist", checked=False),
    ]
    scaffolds: list[str] = _ask(questionary.checkbox(
        "Also generate these files?",
        choices=scaffold_choices,
    ).ask())

    # --- write config ---
    config_path = root / ".swarm-lint.json"
    console.print()

    if config_path.exists():
        overwrite = _ask(questionary.confirm(
            f"{config_path.name} already exists. Overwrite?",
            default=False,
        ).ask())
        if not overwrite:
            _abort()

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    console.print(f"  [green]\u2713[/green] Created [bold].swarm-lint.json[/bold]")

    # --- scaffold extra files ---
    if "tasks" in scaffolds:
        _scaffold_file(root, "templates/tasks.json", root / ".vscode" / "tasks.json")
    if "pyright" in scaffolds:
        _scaffold_file(root, "templates/pyrightconfig.json", root / "pyrightconfig.json")
    if "whitelist" in scaffolds:
        _scaffold_file(root, "defaults/vulture_whitelist.py", root / "vulture_whitelist.py")

    console.print()
    console.print("[bold green]Done![/bold green] Run [bold]swarm-lint check[/bold] to lint your project.")
