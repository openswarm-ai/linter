"""ESLint runner for TypeScript projects."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_eslint(root: Path, eslint_config: dict) -> list[str]:
    """Run ESLint and return errors.

    eslint_config keys:
        directory – directory containing node_modules/.bin/eslint (relative to root)
        args      – argument list passed to eslint (must include --format json)
    """
    directory = eslint_config.get("directory", ".")
    target_dir = root / directory
    eslint_bin = target_dir / "node_modules" / ".bin" / "eslint"
    if not eslint_bin.exists():
        return []

    args: list[str] = eslint_config.get("args", ["src/", "--format", "json", "--no-warn-ignored"])
    cmd = [str(eslint_bin)] + args
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
    for entry in data:
        try:
            rel = str(Path(entry["filePath"]).relative_to(root))
        except (ValueError, KeyError):
            continue
        for msg in entry.get("messages", []):
            sev = "error" if msg.get("severity", 0) >= 2 else "warning"
            text = msg.get("message", "").replace("\n", " ").strip()
            rule = msg.get("ruleId") or "unknown"
            errors.append(
                f"{rel}:{msg.get('line', 1)}:{msg.get('column', 1)}: "
                f"{sev}: {text} [{rule}] [eslint]"
            )
    return errors
