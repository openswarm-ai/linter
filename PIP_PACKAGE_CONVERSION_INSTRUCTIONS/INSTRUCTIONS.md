# Pip Package Conversion Instructions

## Goal

Convert this linter into a standalone pip package called `swarm-lint` (importable as `swarm_lint`) that can be installed via `pip install swarm-lint`. After conversion, any Python+TypeScript project should be able to install this tool and use it — not just the original debugger project it was extracted from.

## What this linter does

A unified code quality orchestrator that runs multiple checks under one CLI:

- **Structural checks** (pure Python, stdlib only): file line count limits, folder item count limits, nested import detection
- **Vulture** (shells out to the `vulture` binary): dead Python code detection
- **ESLint** (shells out to local `node_modules/.bin/eslint`): TypeScript/React linting
- **Knip** (shells out to local `node_modules/.bin/knip`): unused TypeScript exports/deps/files

It also has a `--watch` mode that uses `watchfiles` to re-run all checks on every source file change.

## Current file structure

```
linter/
  lint.py                    # CLI entry point + orchestrator
  print_errors.sh            # colored terminal reporter (bash)
  README.md
  checks/
    __init__.py              # shared utilities (is_excluded, is_excepted, _matches_any)
    structural.py            # file lines, folder items, nested imports
    vulture.py               # vulture runner
    eslint.py                # eslint runner
    knip.py                  # knip runner
  config/
    config.json              # all settings
    pyrightconfig.json       # pyright type checking config (NOT used by lint.py — editor-only)
    vulture_whitelist.py     # vulture false-positive suppressions
```

## Target file structure

```
pyproject.toml                   # NEW — package metadata
README.md                        # updated
src/
  swarm_lint/
    __init__.py                  # package init, exports __version__
    cli.py                       # CLI entry point (evolved from lint.py)
    config.py                    # NEW — config loading, resolution, merging
    init_cmd.py                  # NEW — `swarm-lint init` scaffolding logic
    checks/
      __init__.py                # shared utilities (keep as-is)
      structural.py              # keep as-is
      vulture.py                 # updated: reads paths from config
      eslint.py                  # updated: reads paths from config
      knip.py                    # updated: reads paths from config
    defaults/
      config.json                # ships with the package (generic defaults)
      vulture_whitelist.py       # minimal/empty default whitelist
    templates/                   # files scaffolded by `swarm-lint init`
      tasks.json                 # VS Code tasks template
      pyrightconfig.json         # pyright config template
```

> `print_errors.sh` should be dropped. Its job (colorized terminal output) should be handled by the Python CLI itself, since the package should not depend on bash. If colorized output is desired, add it to `cli.py` using ANSI codes (or a lightweight dependency like `colorama` as an optional extra). The original script just called `lint.py` and parsed/colored its output — the CLI can do this natively.

## Step-by-step conversion

### Step 1: Create the package skeleton

1. Create `pyproject.toml` at the repo root (see EXAMPLE_PYPROJECT.toml in this folder).
2. Create `src/swarm_lint/` directory structure as shown above.
3. Move files into the new structure:
   - `lint.py` → `src/swarm_lint/cli.py`
   - `checks/` → `src/swarm_lint/checks/`
   - `config/config.json` → `src/swarm_lint/defaults/config.json` (but **generalized** — see Step 3)
   - `config/vulture_whitelist.py` → `src/swarm_lint/defaults/vulture_whitelist.py` (empty/minimal version)

### Step 2: Fix imports

All internal imports must use the `swarm_lint` namespace. Examples:

```python
# In cli.py (was lint.py):
# BEFORE:
from checks import is_excluded, is_excepted
from checks.structural import check_file_lines, check_folder_items, check_nested_imports
from checks.vulture import run_vulture
from checks.eslint import run_eslint
from checks.knip import run_knip

# AFTER:
from swarm_lint.checks import is_excluded, is_excepted
from swarm_lint.checks.structural import check_file_lines, check_folder_items, check_nested_imports
from swarm_lint.checks.vulture import run_vulture
from swarm_lint.checks.eslint import run_eslint
from swarm_lint.checks.knip import run_knip
```

Similarly, `checks/vulture.py` uses `from . import is_excepted` and `checks/structural.py` uses `from . import _matches_any` — these relative imports are fine and don't need changing.

### Step 3: Create the default config

The bundled `defaults/config.json` must be **generic** — no project-specific values. See EXAMPLE_DEFAULT_CONFIG.json in this folder. Key differences from the current config:

- `vulture.targets`, `vulture.venv_path`, `vulture.exclude` become explicit top-level fields (currently hardcoded in vulture.py)
- `eslint.directory` and `knip.directory` become explicit fields (currently hardcoded in eslint.py/knip.py)
- The `exclude` list drops project-specific entries like `"uv-bin"`, `"data"`, `"readme_assets"`, `"openswarm_debug.egg-info"`, `"frontend/src/assets"`
- The `exceptions` list is empty by default

### Step 4: Implement config resolution (`config.py`)

Create `src/swarm_lint/config.py` with this resolution order:

1. **`--config` CLI flag** — explicit path to a JSON config file
2. **`.swarm-lint.json`** in the `--root` directory
3. **Bundled defaults** from `swarm_lint/defaults/config.json`

The user's config merges on top of defaults — users only need to override what they care about. Use a **deep merge** strategy: dicts are merged recursively, lists and scalars are replaced entirely.

```python
import importlib.resources
import json
from pathlib import Path
from typing import Any


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Lists/scalars are replaced, dicts are merged."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_defaults() -> dict[str, Any]:
    ref = importlib.resources.files("swarm_lint") / "defaults" / "config.json"
    return json.loads(ref.read_text(encoding="utf-8"))


def load_config(root: Path, explicit_config: Path | None = None) -> dict[str, Any]:
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
```

### Step 5: Make check runners config-driven

Each runner currently hardcodes project-specific paths. Here's exactly what to change:

#### vulture.py

The config will have a `"vulture"` section. The runner should accept these values instead of hardcoding them.

Current hardcoded values (lines referenced from the existing file):
- `root / "backend" / ".venv" / "bin" / "vulture"` → use `config["vulture"]["venv_path"]` to construct, or just `shutil.which("vulture")` as fallback
- `cmd = [str(vulture_bin), "backend", "debug.py"]` → use `config["vulture"]["targets"]`
- `"--exclude", ".venv,__pycache__,data,uv-bin"` → use `config["vulture"]["exclude"]`
- `CONFIG_DIR / "vulture_whitelist.py"` → use `config["vulture"]["whitelist"]` (resolved relative to root)

New signature:
```python
def run_vulture(
    root: Path,
    vulture_config: dict,
    min_confidence: int,
    error_threshold: int,
    exceptions: dict[str, list[str]],
) -> list[str]:
```

#### eslint.py

Current hardcoded value:
- `root / "frontend"` → use `config["eslint"]["directory"]`

New signature:
```python
def run_eslint(root: Path, eslint_config: dict) -> list[str]:
```

#### knip.py

Current hardcoded values:
- `root / "frontend"` → use `config["knip"]["directory"]`
- `f"frontend/{filepath}"` → use the directory value from config for the prefix

New signature:
```python
def run_knip(root: Path, knip_config: dict) -> list[str]:
```

### Step 6: Update the CLI (`cli.py`)

Evolve `lint.py` into `cli.py` with subcommands:

```
swarm-lint [check] [--root DIR] [--config FILE] [--watch]
swarm-lint init [--root DIR]
```

- The default command (no subcommand, or `check`) runs the linter once and exits with code 1 if errors found.
- `--watch` enters watch mode.
- `--config` overrides config file location.
- `init` scaffolds a `.swarm-lint.json` into the root directory.

Key changes from current `lint.py`:
- Replace `CONFIG_FILE = SCRIPT_DIR / "config" / "config.json"` with `from swarm_lint.config import load_config`
- Pass `--config` through to `load_config()`
- Pass config sections to the runners (vulture_config, eslint_config, knip_config)
- Add `init` subcommand handling (delegates to `init_cmd.py`)

### Step 7: Implement `swarm-lint init`

Create `src/swarm_lint/init_cmd.py`. When a user runs `swarm-lint init`, it should:

1. Copy `defaults/config.json` to `.swarm-lint.json` in the target directory
2. Print instructions telling the user to customize it
3. Optionally (prompted or via flags) also scaffold:
   - A `vulture_whitelist.py`
   - A `pyrightconfig.json` (from templates/)
   - A `.vscode/tasks.json` snippet (from templates/)

Use `importlib.resources` to read the bundled defaults/templates.

### Step 8: Create `__init__.py`

```python
"""swarm-lint: unified structural linter for Python + TypeScript projects."""

__version__ = "0.1.0"
```

### Step 9: Drop `print_errors.sh`

The bash script's functionality (colorized output) should be absorbed into the Python CLI. The current `_print_section` function in `lint.py` already does the plain-text output — adding ANSI color codes there is trivial:

```python
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"
```

This avoids a bash dependency and makes the package cross-platform.

## Output format contract (IMPORTANT)

The linter's stdout format is consumed by VS Code problem matchers. The exact format MUST be preserved:

### Section delimiters

```
structural: checking...
<errors>
structural: done. N error(s) found.

vulture: checking...
<errors>
vulture: done. N error(s) found.

eslint: checking...
<errors>
eslint: done. N error(s) found.

knip: checking...
<errors>
knip: done. N error(s) found.
```

### Error line format

Every error line must match this regex:
```
^(.+):(\d+):(\d+):\s+(error|warning):\s+(.+)$
```

i.e. `file:line:col: severity: message [rule-tag]`

The VS Code tasks that consume this output use `beginsPattern` / `endsPattern` regexes like `^structural: checking\.\.\.$` and `^structural: done\.` to delimit sections. **Do not change these patterns.**

## Dependencies

### Required (runtime)
None. Structural checks use only the stdlib. This is intentional.

### Optional extras
- `watch` extra: `watchfiles` (for `--watch` mode)
- `vulture` extra: `vulture` (for dead code detection)
- `all` extra: both of the above

### External tools (user's responsibility, NOT pip deps)
- `eslint` — installed via npm in the user's frontend directory
- `knip` — installed via npm in the user's frontend directory
- `pyright` — not used by the linter at all (editor-only), but the `init` command can scaffold its config

## Testing the package

After conversion, verify:

```bash
# Install in dev mode
pip install -e ".[all]"

# Check the CLI works
swarm-lint --help
swarm-lint init --help

# Run against the package's own source (should pass structural checks)
swarm-lint check --root .

# Watch mode starts and re-runs on changes
swarm-lint --watch --root .
```

## Reference: what the original consumer project looks like

See CONSUMER_CONTEXT.md in this folder for details on how the original project (a debugger tool) invoked the linter, including VS Code tasks, run.sh, and pyproject.toml references. This context helps you understand the output format contract and what `swarm-lint init` should scaffold.
