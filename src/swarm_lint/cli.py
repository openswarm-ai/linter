"""swarm-lint CLI: orchestrates structural checks, dead-code detection, and lint tools."""

import os
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from swarm_lint.checks import is_excluded, is_excepted
from swarm_lint.checks.structural import check_file_lines, check_folder_items, check_nested_imports
from swarm_lint.checks.vulture import run_vulture
from swarm_lint.checks.eslint import run_eslint
from swarm_lint.checks.knip import run_knip
from swarm_lint.checks.endpoints import run_endpoint_check
from swarm_lint.checks.classes import run_class_check
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


_SECTION_NAMES = ("structural", "vulture", "eslint", "knip", "endpoints", "classes")

_SECTION_META = {
    "structural": {"color": YELLOW, "label": "Violations found", "hint": "fix or add exceptions in config"},
    "vulture":    {"color": CYAN,   "label": "Dead code found",  "hint": "fix or add to vulture_whitelist.py"},
    "eslint":     {"color": YELLOW, "label": "Lint errors found", "hint": "fix or disable rules in eslint config"},
    "knip":       {"color": CYAN,   "label": "Unused code/dependencies found", "hint": "remove unused code or update knip config"},
    "endpoints":  {"color": YELLOW, "label": "Orphaned endpoints found", "hint": "fix or add to endpoint exceptions"},
    "classes":    {"color": CYAN,   "label": "Class issues found", "hint": "fix or add to class exceptions"},
}


def run_checks(
    root: Path, config: dict[str, Any],
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
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

    endpoint_errors: list[str] = []
    if enabled.get("endpoints", True):
        ignore_routes: list[str] = rules.get("endpoint-ignore-routes", [])
        endpoint_errors = run_endpoint_check(
            root, exceptions, ignore_routes,
            endpoints_config=config.get("endpoints", {}),
        )

    class_errors: list[str] = []
    if enabled.get("classes", True):
        class_errors = run_class_check(
            root, exceptions, excludes,
            classes_config=config.get("classes", {}),
        )

    return (
        sorted(structural_errors), sorted(vulture_errors),
        sorted(eslint_errors), sorted(knip_errors),
        sorted(endpoint_errors), sorted(class_errors),
    )


def _print_section(name: str, errors: list[str], color: bool) -> None:
    """Print a check section preserving the output format contract.

    The exact format of the 'checking...' / 'done.' lines must not change --
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
    results: tuple[list[str], ...],
    *, color: bool = False,
) -> None:
    """Machine-parseable output (default format, VS Code-compatible)."""
    for name, errors in zip(_SECTION_NAMES, results):
        _print_section(name, errors, color)


def print_summary(
    results: tuple[list[str], ...],
    *, color: bool = False,
) -> None:
    """Human-friendly grouped summary (--format summary)."""
    for name, errors in zip(_SECTION_NAMES, results):
        if not errors:
            continue
        meta = _SECTION_META[name]
        c = meta["color"] if color else ""
        b = BOLD if color else ""
        r = RESET if color else ""
        print(f"\n{c}{b}[{name}] {meta['label']}:{r}", flush=True)
        for e in errors:
            print(f"{c}  {e}{r}", flush=True)
        print(f"{c}{b}  {len(errors)} finding(s) -- {meta['hint']}{r}", flush=True)
    total = sum(len(e) for e in results)
    if total == 0:
        print("\nAll checks passed.", flush=True)
    else:
        print(f"\n{total} total finding(s).", flush=True)


def _output(results: tuple[list[str], ...], *, fmt: str, color: bool) -> None:
    if fmt == "summary":
        print_summary(results, color=color)
    else:
        print_results(results, color=color)


def watch_loop(root: Path, config: dict[str, Any], *, color: bool, fmt: str) -> None:
    from watchfiles import watch, DefaultFilter

    from swarm_lint.init_cmd import CONFIG_DIR, CONFIG_FILE
    config_file = root / CONFIG_DIR / CONFIG_FILE

    _output(run_checks(root, config), fmt=fmt, color=color)

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
        _output(run_checks(root, config), fmt=fmt, color=color)


# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    help="Unified structural linter for Python + TypeScript projects.",
    invoke_without_command=True,
    no_args_is_help=False,
)

config_app = typer.Typer(help="View and modify configuration.")
app.add_typer(config_app, name="config")


def _run_check(
    root_str: str,
    config_path: Optional[str],
    watch: bool,
    color: bool,
    fmt: str,
) -> None:
    root = Path(root_str).resolve()
    explicit_config = Path(config_path) if config_path else None
    cfg = load_config(root, explicit_config)
    use_color = color and _supports_color()

    if watch:
        watch_loop(root, cfg, color=use_color, fmt=fmt)
    else:
        results = run_checks(root, cfg)
        _output(results, fmt=fmt, color=use_color)
        raise typer.Exit(code=1 if any(results) else 0)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    root: str = typer.Option(".", help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Path to config JSON file"),
    watch: bool = typer.Option(False, "--watch/--no-watch", help="Watch for file changes and re-lint"),
    color: bool = typer.Option(True, "--color/--no-color", help="Colored terminal output"),
    fmt: str = typer.Option("default", "--format", help="Output format: 'default' (VS Code) or 'summary' (human-friendly)"),
) -> None:
    """Unified structural linter for Python + TypeScript projects."""
    if ctx.invoked_subcommand is not None:
        return
    _run_check(root, config, watch, color, fmt)


@app.command()
def check(
    root: str = typer.Option(".", help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Path to config JSON file"),
    watch: bool = typer.Option(False, "--watch/--no-watch", help="Watch for file changes and re-lint"),
    color: bool = typer.Option(True, "--color/--no-color", help="Colored terminal output"),
    fmt: str = typer.Option("default", "--format", help="Output format: 'default' (VS Code) or 'summary' (human-friendly)"),
) -> None:
    """Run lint checks (default when no subcommand is given)."""
    _run_check(root, config, watch, color, fmt)


@app.command()
def setup(
    root: str = typer.Option(".", help="Project root directory"),
) -> None:
    """Interactive setup wizard — configure swarm-lint for your project."""
    from swarm_lint.setup_cmd import run_setup
    run_setup(Path(root).resolve())


@app.command("init")
def init_cmd(
    root: str = typer.Option(".", help="Target directory"),
    with_tasks: bool = typer.Option(False, "--with-tasks/--without-tasks", help="Also create .vscode/tasks.json"),
    with_pyright: bool = typer.Option(False, "--with-pyright/--without-pyright", help="Also create pyright-config.json"),
    with_whitelist: bool = typer.Option(
        False, "--with-whitelist/--without-whitelist", help="Also create vulture_whitelist.py",
    ),
) -> None:
    """Scaffold a general-config.json config file (non-interactive)."""
    from swarm_lint.init_cmd import run_init
    run_init(
        root=Path(root).resolve(),
        with_tasks=with_tasks,
        with_pyright=with_pyright,
        with_whitelist=with_whitelist,
    )


@config_app.command("show")
def config_show(
    root: str = typer.Option(".", help="Project root directory"),
) -> None:
    """Display the resolved configuration."""
    from swarm_lint.config_cmd import show_config
    show_config(Path(root).resolve())


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Dot-path key (e.g. rules.max-file-lines)"),
    value: str = typer.Argument(help="Value to set"),
    root: str = typer.Option(".", help="Project root directory"),
) -> None:
    """Set a config value using dot-path notation."""
    from swarm_lint.config_cmd import set_config_value
    set_config_value(Path(root).resolve(), key, value)


@config_app.command("enable")
def config_enable(
    check_name: str = typer.Argument(help="Check to enable"),
    root: str = typer.Option(".", help="Project root directory"),
) -> None:
    """Enable a lint check."""
    from swarm_lint.config_cmd import toggle_check
    toggle_check(Path(root).resolve(), check_name, enable=True)


@config_app.command("disable")
def config_disable(
    check_name: str = typer.Argument(help="Check to disable"),
    root: str = typer.Option(".", help="Project root directory"),
) -> None:
    """Disable a lint check."""
    from swarm_lint.config_cmd import toggle_check
    toggle_check(Path(root).resolve(), check_name, enable=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
