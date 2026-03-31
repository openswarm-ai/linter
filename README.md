# swarm-lint

Unified structural linter for Python + TypeScript projects. Runs multiple checks under one CLI:

- **Structural checks** (pure Python, stdlib only) — file line count limits, folder item count limits, nested import detection
- **Vulture** — dead Python code detection (shells out to `vulture`)
- **ESLint** — TypeScript/React linting (shells out to local `node_modules/.bin/eslint`)
- **Knip** — unused TypeScript exports, dependencies, and files (shells out to local `node_modules/.bin/knip`)

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
```

## CLI reference

### `swarm-lint setup`

Interactive wizard that auto-detects your project structure (Python dirs, TypeScript dirs, virtual environments, `node_modules`) and walks you through choosing checks, setting rules, and scaffolding config files — all from the terminal.

### `swarm-lint check`

```
swarm-lint check [--root DIR] [--config FILE] [--watch/--no-watch] [--color/--no-color]
```

| Flag | Description |
|------|-------------|
| `--root DIR` | Project root directory (default: `.`) |
| `--config FILE` | Explicit path to a JSON config file |
| `--watch` | Watch for file changes and re-lint continuously |
| `--no-color` | Disable colored terminal output |

Running `swarm-lint` with no subcommand is equivalent to `swarm-lint check`.

### `swarm-lint init`

```
swarm-lint init [--root DIR] [--with-tasks] [--with-pyright] [--with-whitelist]
```

Non-interactive scaffolding — drops a `.swarm-lint.json` config file into the target directory. Optional flags:

| Flag | Creates |
|------|---------|
| `--with-tasks` | `.vscode/tasks.json` with problem-matcher integration |
| `--with-pyright` | `pyrightconfig.json` template |
| `--with-whitelist` | `vulture_whitelist.py` stub |

The command is non-destructive — it skips files that already exist.

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
```

## Configuration

swarm-lint looks for config in this order:

1. `--config` flag (explicit path)
2. `.swarm-lint.json` in the `--root` directory
3. Built-in defaults

Your config is **deep-merged** on top of defaults — you only need to override what differs from the defaults.

### Example `.swarm-lint.json`

```json
{
  "rules": {
    "vulture-min-confidence": 1,
    "vulture-error-threshold": 1
  },
  "exclude": [
    "node_modules", ".venv", "dist", "build", "__pycache__",
    ".git", ".cursor", ".vscode",
    "uv-bin", "data", "public"
  ],
  "vulture": {
    "targets": ["backend", "debug.py"],
    "venv_path": "backend/.venv",
    "exclude": ".venv,__pycache__,data,uv-bin",
    "whitelist": "vulture_whitelist.py"
  },
  "eslint": {
    "directory": "frontend"
  },
  "knip": {
    "directory": "frontend"
  }
}
```

### Config reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled.*` | `bool` | `true` | Toggle individual checks on/off |
| `rules.max-file-lines` | `int` | `250` | Max lines per source file |
| `rules.max-folder-items` | `int` | `7` | Max items per folder |
| `rules.vulture-min-confidence` | `int` | `80` | Min confidence to flag a vulture finding |
| `rules.vulture-error-threshold` | `int` | `90` | Confidence at which a finding becomes an error |
| `rules.no-nested-imports` | `bool` | `true` | Detect imports inside function bodies |
| `include_extensions` | `list[str]` | `[".py", ".ts", ...]` | File extensions to check |
| `exclude` | `list[str]` | `["node_modules", ...]` | Glob patterns for excluded dirs/files |
| `exceptions.<rule>` | `list[str]` | `[]` | Glob patterns for files exempt from a rule |
| `vulture.targets` | `list[str]` | `["."]` | Paths to scan (relative to root) |
| `vulture.venv_path` | `str\|null` | `null` | Venv dir containing `bin/vulture` |
| `vulture.exclude` | `str` | `".venv,__pycache__"` | Comma-separated vulture exclusions |
| `vulture.whitelist` | `str\|null` | `null` | Path to whitelist file (relative to root) |
| `eslint.directory` | `str` | `"."` | Directory containing `node_modules/.bin/eslint` |
| `eslint.args` | `list[str]` | `["src/", ...]` | Arguments passed to eslint |
| `knip.directory` | `str` | `"."` | Directory containing `node_modules/.bin/knip` |

## VS Code integration

Run `swarm-lint setup` (or `swarm-lint init --with-tasks`) to create a `.vscode/tasks.json` that:

- Auto-starts `swarm-lint --watch` when the workspace opens
- Feeds errors into the **Problems panel** via problem matchers
- Groups errors by check type (structural, vulture, eslint, knip)

## Output format

Every error line matches: `file:line:col: severity: message [rule-tag]`

Sections are delimited by `<name>: checking...` and `<name>: done. N error(s) found.` lines. This format is stable and consumed by VS Code problem matchers.

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
