"""Config loading with deep-merge resolution chain."""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import Any


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*.  Lists and scalars are replaced; dicts are merged."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_defaults() -> dict[str, Any]:
    """Return the generic default config bundled with the package."""
    ref = importlib.resources.files("swarm_lint") / "defaults" / "config.json"
    return json.loads(ref.read_text(encoding="utf-8"))


def load_config(root: Path, explicit_config: Path | None = None) -> dict[str, Any]:
    """Load and merge config using the resolution chain.

    Priority (highest to lowest):
        1. *explicit_config* (``--config`` CLI flag)
        2. ``.swarm-lint.json`` in *root*
        3. Bundled defaults
    """
    base = load_defaults()
    if explicit_config is not None:
        override = json.loads(explicit_config.read_text())
    else:
        project_cfg = root / ".swarm-lint.json"
        if project_cfg.exists():
            override = json.loads(project_cfg.read_text())
        else:
            override = {}
    return _deep_merge(base, override)
