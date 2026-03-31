#!/usr/bin/env python3
"""swarm-lint CLI: orchestrates structural checks, dead-code detection, and lint tools."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from swarm_lint.checks import is_excluded, is_excepted
from swarm_lint.checks.structural import check_file_lines, check_folder_items, check_nested_imports
from swarm_lint.checks.vulture import run_vulture
from swarm_lint.checks.eslint import run_eslint
from swarm_lint.checks.knip import run_knip
from swarm_lint.config import load_config

YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def run_checks(
    root: Path, config: dict[str, Any],
) -> tuple[list[str], list[str], list[str], list[str]]:
    enabled: dict[str, bool] = config.get("enabled", {})
    rules: dict[str, int] = config["rules"]
    excludes: list[str] = config["exclude"]
    exceptions: dict[str, list[str]] = config["exceptions"]
    extensions: list[str] = config["include_extensions"]

    max_lines: int = rules["max-file-lines"]
    max_items: int = rules["max-folder-items"]
    check_imports: bool = rules.get("no-nested-imports", False)
    structural_errors: list[str] = []

    file_lines_on = enabled.get("max-file-lines", True)
    folder_items_on = enabled.get("max-folder-items", True)
    nested_imports_on = enabled.get("no-nested-imports", True)

    for dirpath_str, dirnames, filenames in os.walk(root):
        dp = Path(dirpath_str)

        if is_excluded(dp, root, excludes):
            dirnames.clear()
            continue

        rel_dir = str(dp.relative_to(root))
        if folder_items_on and rel_dir != "." and not is_excepted(rel_dir, "max-folder-items", exceptions):
            result = check_folder_items(dp, root, max_items, excludes)
            if result:
                structural_errors.append(result[0])

        for fname in filenames:
            fp = dp / fname
            if fp.suffix not in extensions:
                continue
            if is_excluded(fp, root, excludes):
                continue
            rel_file = str(fp.relative_to(root))
            if file_lines_on and not is_excepted(rel_file, "max-file-lines", exceptions):
                result = check_file_lines(fp, root, max_lines)
                if result:
                    structural_errors.append(result[0])
            if nested_imports_on and check_imports and not is_excepted(rel_file, "no-nested-imports", exceptions):
                structural_errors.extend(check_nested_imports(fp, root))

    vulture_errors: list[str] = []
    if enabled.get("vulture", True):
        vulture_confidence = rules.get("vulture-min-confidence")
        if vulture_confidence is not None:
            vulture_error_threshold = rules.get("vulture-error-threshold", 100)
            vulture_errors = run_vulture(
                root,
                vulture_config=config.get("vulture", {}),
                min_confidence=vulture_confidence,
                error_threshold=vulture_error_threshold,
                exceptions=exceptions,
            )

    eslint_errors: list[str] = []
    if enabled.get("eslint", True):
        eslint_errors = run_eslint(root, eslint_config=config.get("eslint", {}))

    knip_errors: list[str] = []
    if enabled.get("knip", True):
        knip_errors = run_knip(root, knip_config=config.get("knip", {}))

    return sorted(structural_errors), sorted(vulture_errors), sorted(eslint_errors), sorted(knip_errors)


def _print_section(name: str, errors: list[str], color: bool) -> None:
    """Print a check section preserving the output format contract.

    The exact format of the 'checking...' / 'done.' lines must not change —
    VS Code problem matchers depend on them.
    """
    if color:
        header = f"{BOLD}{YELLOW}{name}: checking...{RESET}"
        footer = f"{BOLD}{CYAN}{name}: done. {len(errors)} error(s) found.{RESET}"
    else:
        header = f"{name}: checking..."
        footer = f"{name}: done. {len(errors)} error(s) found."

    print(header, flush=True)
    for e in errors:
        print(e, flush=True)
    print(footer, flush=True)


def print_results(
    structural_errors: list[str], vulture_errors: list[str],
    eslint_errors: list[str], knip_errors: list[str],
    *, color: bool = False,
) -> None:
    _print_section("structural", structural_errors, color)
    _print_section("vulture", vulture_errors, color)
    _print_section("eslint", eslint_errors, color)
    _print_section("knip", knip_errors, color)


def watch_loop(root: Path, config: dict[str, Any], *, color: bool) -> None:
    from watchfiles import watch, DefaultFilter  # noqa: nested — optional dep

    config_file = root / ".swarm-lint.json"

    print_results(*run_checks(root, config), color=color)

    class SourceFilter(DefaultFilter):
        allowed_extensions = (".py", ".ts", ".tsx", ".js", ".jsx")

        def __call__(self, change: Any, path: str) -> bool:
            if not super().__call__(change, path):
                return False
            if Path(path).suffix in self.allowed_extensions:
                return True
            p = Path(path)
            if p.suffix == ".json" and p == config_file:
                return True
            return Path(path).is_dir()

    for _changes in watch(root, watch_filter=SourceFilter()):
        config = load_config(root)
        print_results(*run_checks(root, config), color=color)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm-lint",
        description="Unified structural linter for Python + TypeScript projects",
    )
    sub = parser.add_subparsers(dest="command")

    check_parser = sub.add_parser("check", help="Run lint checks (default)")
    for p in (parser, check_parser):
        p.add_argument("--root", type=str, default=".", help="Project root directory")
        p.add_argument("--config", type=str, default=None, help="Path to config JSON file")
        p.add_argument("--watch", action="store_true", help="Watch for file changes and re-lint")
        p.add_argument("--no-color", action="store_true", help="Disable colored output")

    init_parser = sub.add_parser("init", help="Scaffold a .swarm-lint.json config file")
    init_parser.add_argument("--root", type=str, default=".", help="Target directory")
    init_parser.add_argument("--with-tasks", action="store_true", help="Also create .vscode/tasks.json")
    init_parser.add_argument("--with-pyright", action="store_true", help="Also create pyrightconfig.json")
    init_parser.add_argument("--with-whitelist", action="store_true", help="Also create vulture_whitelist.py")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "init":
        from swarm_lint.init_cmd import run_init  # noqa: nested — keep startup fast
        run_init(
            root=Path(args.root).resolve(),
            with_tasks=args.with_tasks,
            with_pyright=args.with_pyright,
            with_whitelist=args.with_whitelist,
        )
        return

    root = Path(args.root).resolve()
    explicit_config = Path(args.config) if args.config else None
    config = load_config(root, explicit_config)
    color = not args.no_color and _supports_color()

    if args.watch:
        watch_loop(root, config, color=color)
    else:
        results = run_checks(root, config)
        print_results(*results, color=color)
        sys.exit(1 if any(results) else 0)


if __name__ == "__main__":
    main()
