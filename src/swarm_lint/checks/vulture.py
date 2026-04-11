"""Vulture dead-code detection runner.

Class-body findings (fields, methods inside a class) are filtered out here
and handled separately by checks/classes.py which understands Pydantic.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from . import is_excepted


@lru_cache(maxsize=64)
def _class_line_ranges(filepath: str) -> list[tuple[int, int]]:
    """Return (start, end) line ranges for all class bodies in *filepath*."""
    try:
        tree = ast.parse(Path(filepath).read_text())
    except (OSError, SyntaxError):
        return []
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            end = max(getattr(n, "lineno", node.lineno) for n in ast.walk(node))
            ranges.append((node.lineno, end))
    return ranges


def _is_inside_class(filepath: str, lineno: int) -> bool:
    """True when *lineno* is strictly inside a class body.

    The class declaration line itself (``class Foo:``) is *not* considered
    inside, so vulture's "unused class" findings still pass through.
    """
    return any(start < lineno <= end for start, end in _class_line_ranges(filepath))


def run_vulture(
    root: Path,
    vulture_config: dict,
    min_confidence: int,
    error_threshold: int,
    exceptions: dict[str, list[str]],
) -> list[str]:
    """Run vulture and return errors.

    vulture_config keys:
        targets           -- list of paths to scan (relative to root)
        venv_path         -- venv dir containing bin/vulture (relative to root), or None
        exclude           -- comma-separated exclusion string for vulture
        whitelist         -- path to whitelist file (relative to root), or None
        ignore_decorators -- comma-separated decorator patterns for --ignore-decorators
        ignore_names      -- comma-separated name patterns for --ignore-names
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

    ignore_decorators = vulture_config.get("ignore_decorators", "")
    if ignore_decorators:
        cmd.extend(["--ignore-decorators", ignore_decorators])

    ignore_names = vulture_config.get("ignore_names", "")
    if ignore_names:
        cmd.extend(["--ignore-names", ignore_names])

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
        if _is_inside_class(str(root / filepath), int(lineno)):
            continue
        conf = re.search(r"\((\d+)% confidence\)", message)
        confidence = int(conf.group(1)) if conf else 0
        severity = "error" if confidence >= error_threshold else "warning"
        errors.append(f"{filepath}:{lineno}:1: {severity}: [vulture] {message}")
    return errors
