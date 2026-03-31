"""Vulture dead-code detection runner."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import is_excepted


def run_vulture(
    root: Path,
    vulture_config: dict,
    min_confidence: int,
    error_threshold: int,
    exceptions: dict[str, list[str]],
) -> list[str]:
    """Run vulture and return errors.

    vulture_config keys:
        targets      – list of paths to scan (relative to root)
        venv_path    – venv dir containing bin/vulture (relative to root), or None
        exclude      – comma-separated exclusion string for vulture
        whitelist    – path to whitelist file (relative to root), or None
    """
    vulture_bin: Path | None = None
    venv_path = vulture_config.get("venv_path")
    if venv_path:
        candidate = root / venv_path / "bin" / "vulture"
        if candidate.exists():
            vulture_bin = candidate
    if vulture_bin is None:
        found = shutil.which("vulture")
        if not found:
            return []
        vulture_bin = Path(found)

    targets: list[str] = vulture_config.get("targets", ["."])
    cmd: list[str] = [str(vulture_bin)] + targets

    whitelist_rel = vulture_config.get("whitelist")
    if whitelist_rel:
        whitelist = root / whitelist_rel
        if whitelist.exists():
            cmd.append(str(whitelist))

    cmd.extend(["--min-confidence", str(min_confidence)])

    exclude_str = vulture_config.get("exclude", "")
    if exclude_str:
        cmd.extend(["--exclude", exclude_str])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(root), timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    errors: list[str] = []
    for line in result.stdout.strip().splitlines():
        m = re.match(r"^(.+):(\d+): (.+)$", line)
        if not m:
            continue
        filepath, lineno, message = m.groups()
        if is_excepted(filepath, "vulture", exceptions):
            continue
        conf = re.search(r"\((\d+)% confidence\)", message)
        confidence = int(conf.group(1)) if conf else 0
        severity = "error" if confidence >= error_threshold else "warning"
        errors.append(f"{filepath}:{lineno}:1: {severity}: {message} [vulture]")
    return errors
