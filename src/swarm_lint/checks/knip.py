"""Knip unused-code runner for TypeScript projects."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

KIND_LABELS = {
    "dependencies": "Unused dependency",
    "devDependencies": "Unused devDependency",
    "exports": "Unused export",
    "types": "Unused exported type",
    "unlisted": "Unlisted dependency",
    "binaries": "Unused binary",
    "files": "Unused file",
    "duplicates": "Duplicate export",
}


def run_knip(root: Path, knip_config: dict) -> list[str]:
    """Run Knip and return errors.

    knip_config keys:
        directory – directory containing node_modules/.bin/knip (relative to root)
    """
    directory = knip_config.get("directory", ".")
    target_dir = root / directory
    knip_bin = target_dir / "node_modules" / ".bin" / "knip"
    if not knip_bin.exists():
        return []

    cmd = [str(knip_bin), "--reporter", "json"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(target_dir), timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    errors: list[str] = []
    for entry in data.get("issues", []):
        filepath = entry.get("file", "")
        rel = f"{directory}/{filepath}" if directory != "." else filepath
        for kind, label in KIND_LABELS.items():
            for item in entry.get(kind, []):
                name = item.get("name", "")
                line = item.get("line", 1)
                col = item.get("col", 1)
                errors.append(
                    f"{rel}:{line}:{col}: error: "
                    f"{label} '{name}' [knip]"
                )
    return errors
