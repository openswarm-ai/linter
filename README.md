# swarm-lint

Unified structural linter for Python + TypeScript projects. Runs multiple checks under one CLI:

- **Structural checks** (pure Python, stdlib only) — file line count limits, folder item count limits, nested import detection
- **Vulture** — dead Python code detection (shells out to `vulture`), with class-body filtering
- **ESLint** — TypeScript/React linting (shells out to local `node_modules/.bin/eslint`)
- **Knip** — unused TypeScript exports, dependencies, and files (shells out to local `node_modules/.bin/knip`)
- **Endpoints** — orphaned API route detection (cross-references backend routes with frontend/backend usage)
- **Classes** — class-level dead code detection with Pydantic/framework awareness

## Installation

```bash
pip install swarm-lint

# with optional extras
pip install "swarm-lint[watch]"    # adds --watch mode (watchfiles)
pip install "swarm-lint[vulture]"  # adds vulture dead-code detection
pip install "swarm-lint[all]"      # both of the above
```

## Quick start

```bash
# interactive setup wizard — the fastest way to get going
swarm-lint setup

# or scaffold a default config non-interactively
swarm-lint init --root /path/to/project

# run all checks once
swarm-lint check --root /path/to/project

# watch mode — re-checks on every file save
swarm-lint check --watch --root /path/to/project

# human-friendly grouped summary instead of VS Code output
swarm-lint check --format summary --root /path/to/project
```

## CLI reference

### `swarm-lint setup`

Interactive wizard that auto-detects your project structure (Python dirs, TypeScript dirs, virtual environments, `node_modules`) and walks you through choosing checks, setting rules, and scaffolding config files — all from the terminal.

### `swarm-lint check`

```
swarm-lint check [--root DIR] [--config FILE] [--watch/--no-watch] [--color/--no-color] [--format FORMAT]
```

| Flag | Description |
|------|-------------|
| `--root DIR` | Project root directory (default: `.`) |
| `--config FILE` | Explicit path to a JSON config file |
| `--watch` | Watch for file changes and re-lint continuously |
| `--no-color` | Disable colored terminal output |
| `--format FORMAT` | Output format: `default` (VS Code-compatible) or `summary` (human-friendly grouped output) |

Running `swarm-lint` with no subcommand is equivalent to `swarm-lint check`.

### `swarm-lint init`

```
swarm-lint init [--root DIR] [--with-tasks] [--with-pyright] [--with-whitelist]
```

Non-interactive scaffolding — creates a `swarm-lint-config/` folder with a `general-config.json` config file. Optional flags:

| Flag | Creates |
|------|---------|
| `--with-tasks` | `.vscode/tasks.json` + `.vscode/extensions.json` |
| `--with-pyright` | `swarm-lint-config/pyright-config.json` template |
| `--with-whitelist` | `swarm-lint-config/vulture_whitelist.py` stub |

The `.vscode/` files are always overwritten to stay in sync with swarm-lint. Other scaffolded files are skipped if they already exist.

### `swarm-lint config`

Manage configuration without hand-editing JSON.

```bash
# pretty-print the resolved config (defaults + your overrides)
swarm-lint config show

# set a value using dot-path notation
swarm-lint config set rules.max-file-lines 300
swarm-lint config set vulture.venv_path backend/.venv

# toggle checks on/off
swarm-lint config enable vulture
swarm-lint config disable eslint
swarm-lint config enable endpoints
```

## Configuration

swarm-lint looks for config in this order:

1. `--config` flag (explicit path)
2. `swarm-lint-config/general-config.json` in the `--root` directory
3. Built-in defaults

Your config is **deep-merged** on top of defaults — you only need to override what differs from the defaults.

### Example `swarm-lint-config/general-config.json`

```json
{
  "rules": {
    "vulture-min-confidence": 1,
    "vulture-error-threshold": 1,
    "endpoint-ignore-routes": ["*/callback", "*/callback/*"]
  },
  "exclude": [
    "node_modules", ".venv", "dist", "build", "__pycache__",
    ".git", ".cursor", ".vscode", "swarm-lint-config",
    "uv-bin", "data", "public"
  ],
  "vulture": {
    "targets": ["backend", "debug.py"],
    "venv_path": "backend/.venv",
    "exclude": ".venv,__pycache__,data,uv-bin",
    "whitelist": "swarm-lint-config/vulture_whitelist.py"
  },
  "eslint": {
    "directory": "frontend"
  },
  "knip": {
    "directory": "frontend"
  },
  "endpoints": {
    "backend_dir": "backend",
    "frontend_src_dir": "frontend/src"
  },
  "classes": {
    "directory": "backend"
  }
}
```

### Config reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled.*` | `bool` | `true` | Toggle individual checks on/off |
| `rules.max-file-lines` | `int` | `250` | Max lines per source file |
| `rules.max-folder-items` | `int` | `7` | Max items per folder |
| `rules.vulture-min-confidence` | `int` | `1` | Min confidence to flag a vulture finding |
| `rules.vulture-error-threshold` | `int` | `1` | Confidence at which a finding becomes an error |
| `rules.no-nested-imports` | `bool` | `true` | Detect imports inside function bodies |
| `rules.endpoint-ignore-routes` | `list[str]` | `[]` | Route glob patterns to skip in endpoint checks |
| `include_extensions` | `list[str]` | `[".py", ".ts", ...]` | File extensions to check |
| `exclude` | `list[str]` | `["node_modules", ...]` | Glob patterns for excluded dirs/files |
| `exceptions.<rule>` | `list[str]` | `[]` | Glob patterns for files exempt from a rule |
| `vulture.targets` | `list[str]` | `["."]` | Paths to scan (relative to root) |
| `vulture.venv_path` | `str\|null` | `null` | Venv dir containing `bin/vulture` |
| `vulture.exclude` | `str` | `".venv,__pycache__"` | Comma-separated vulture exclusions |
| `vulture.whitelist` | `str\|null` | `null` | Path to whitelist file (relative to root) |
| `vulture.ignore_decorators` | `str` | `"@*.router.*,..."` | Comma-separated decorator patterns for `--ignore-decorators` |
| `vulture.ignore_names` | `str` | `"cls"` | Comma-separated name patterns for `--ignore-names` |
| `eslint.directory` | `str` | `"."` | Directory containing `node_modules/.bin/eslint` |
| `eslint.args` | `list[str]` | `["src/", ...]` | Arguments passed to eslint |
| `knip.directory` | `str` | `"."` | Directory containing `node_modules/.bin/knip` |
| `endpoints.backend_dir` | `str` | `"backend"` | Directory containing Python route files |
| `endpoints.frontend_src_dir` | `str` | `"frontend/src"` | Directory containing TS/JS source that references routes |
| `classes.directory` | `str` | `"backend"` | Directory to scan for Python class files |

## VS Code integration

Run `swarm-lint setup` (or `swarm-lint init --with-tasks`) to create `.vscode/tasks.json` and `.vscode/extensions.json`:

- **tasks.json** — auto-starts `swarm-lint --watch` when the workspace opens, feeds errors into the **Problems panel** via problem matchers, groups errors by check type (structural, vulture, eslint, knip, endpoints, classes)
- **extensions.json** — recommends the ESLint VS Code extension

These files are always overwritten on re-run to stay in sync with swarm-lint.

## Output format

### Default format (`--format default`)

Every error line matches: `file:line:col: severity: [rule-tag] message`

Sections are delimited by `<name>: checking...` and `<name>: done. N error(s) found.` lines. This format is stable and consumed by VS Code problem matchers.

### Summary format (`--format summary`)

Groups errors by category, only shows categories with errors, and includes actionable hints:

```
[vulture] Dead code found:
  backend/foo.py:12:1: error: [vulture] unused function 'bar' (100% confidence)
  1 finding(s) -- fix or add to vulture_whitelist.py

[endpoints] Orphaned endpoints found:
  backend/apps/tools/routes.py:45:1: warning: [endpoints] orphaned endpoint 'list_tools' ...
  1 finding(s) -- fix or add to endpoint exceptions

2 total finding(s).
```

## External tools

swarm-lint shells out to these tools when their checks are enabled. Install them yourself:

- **vulture** — `pip install vulture` (or use the `swarm-lint[vulture]` extra)
- **eslint** — `npm install eslint` in your frontend directory
- **knip** — `npm install knip` in your frontend directory

## Development

```bash
git clone <repo-url>
cd linter
pip install -e ".[all]"
swarm-lint check --root .
```

## License

MIT
