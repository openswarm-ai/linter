"""Configuration management commands for swarm-lint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

from swarm_lint.config import load_config

console = Console()

VALID_CHECKS = frozenset({
    "max-file-lines", "max-folder-items", "no-nested-imports",
    "vulture", "eslint", "knip", "endpoints", "classes",
})


def _config_path(root: Path) -> Path:
    from swarm_lint.init_cmd import CONFIG_DIR, CONFIG_FILE
    return root / CONFIG_DIR / CONFIG_FILE


def _load_user_config(root: Path) -> dict[str, Any]:
    cp = _config_path(root)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    return {}


def _save_user_config(root: Path, config: dict[str, Any]) -> None:
    cp = _config_path(root)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _parse_value(raw: str) -> Any:
    """Coerce a CLI string into a typed Python value."""
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False
    if raw.lower() in ("null", "none"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.startswith(("[", "{")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw


def _set_nested(d: dict[str, Any], keys: list[str], value: Any) -> None:
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


# ---------------------------------------------------------------------------
# Public API (called from cli.py)
# ---------------------------------------------------------------------------

def show_config(root: Path) -> None:
    resolved = load_config(root)
    console.print()
    console.print(Syntax(
        json.dumps(resolved, indent=2),
        "json",
        theme="monokai",
        line_numbers=False,
    ))

    cp = _config_path(root)
    console.print()
    if cp.exists():
        console.print(f"[dim]Source: {cp}  (merged with built-in defaults)[/dim]")
    else:
        console.print(f"[dim]Source: built-in defaults (no {cp.relative_to(root)} found)[/dim]")


def set_config_value(root: Path, dot_key: str, raw_value: str) -> None:
    user_cfg = _load_user_config(root)
    keys = dot_key.split(".")
    value = _parse_value(raw_value)
    _set_nested(user_cfg, keys, value)
    _save_user_config(root, user_cfg)
    console.print(f"  [green]\u2713[/green] Set [bold]{dot_key}[/bold] = {json.dumps(value)}")


def toggle_check(root: Path, check_name: str, *, enable: bool) -> None:
    if check_name not in VALID_CHECKS:
        console.print(f"[red]Unknown check:[/red] {check_name}")
        console.print(f"Valid checks: {', '.join(sorted(VALID_CHECKS))}")
        raise SystemExit(1)

    user_cfg = _load_user_config(root)
    user_cfg.setdefault("enabled", {})[check_name] = enable
    _save_user_config(root, user_cfg)

    state = "[green]enabled[/green]" if enable else "[red]disabled[/red]"
    console.print(f"  [green]\u2713[/green] {check_name} {state}")
