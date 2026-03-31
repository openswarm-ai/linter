# Consumer Context

This linter was extracted from a larger project (a debugger tool with a Python backend and React/TypeScript frontend). This document describes how the original project consumed the linter, so you understand the contracts that must be preserved — especially the output format.

## How the original project invoked the linter

### 1. VS Code tasks (`.vscode/tasks.json`)

The original project ran the linter as a VS Code background task that auto-started on workspace open. The task used **problem matchers** to parse the linter's stdout and feed errors into the Problems panel.

```json
{
  "label": "lint:watch",
  "type": "shell",
  "command": "python3",
  "args": ["${workspaceFolder}/linter/lint.py", "--watch", "--root", "${workspaceFolder}"],
  "isBackground": true,
  "runOptions": { "runOn": "folderOpen" },
  "problemMatcher": [
    {
      "owner": "structural",
      "fileLocation": ["relative", "${workspaceFolder}"],
      "pattern": {
        "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning):\\s+(.+)$",
        "file": 1, "line": 2, "column": 3, "severity": 4, "message": 5
      },
      "background": {
        "activeOnStart": true,
        "beginsPattern": "^structural: checking\\.\\.\\.$",
        "endsPattern": "^structural: done\\."
      }
    },
    {
      "owner": "vulture",
      "fileLocation": ["relative", "${workspaceFolder}"],
      "pattern": {
        "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning):\\s+(.+)$",
        "file": 1, "line": 2, "column": 3, "severity": 4, "message": 5
      },
      "background": {
        "activeOnStart": true,
        "beginsPattern": "^vulture: checking\\.\\.\\.$",
        "endsPattern": "^vulture: done\\."
      }
    },
    {
      "owner": "eslint-project",
      "fileLocation": ["relative", "${workspaceFolder}"],
      "pattern": {
        "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning):\\s+(.+)$",
        "file": 1, "line": 2, "column": 3, "severity": 4, "message": 5
      },
      "background": {
        "activeOnStart": true,
        "beginsPattern": "^eslint: checking\\.\\.\\.$",
        "endsPattern": "^eslint: done\\."
      }
    },
    {
      "owner": "knip",
      "fileLocation": ["relative", "${workspaceFolder}"],
      "pattern": {
        "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning):\\s+(.+)$",
        "file": 1, "line": 2, "column": 3, "severity": 4, "message": 5
      },
      "background": {
        "activeOnStart": true,
        "beginsPattern": "^knip: checking\\.\\.\\.$",
        "endsPattern": "^knip: done\\."
      }
    }
  ]
}
```

After conversion, the consumer would change to:
```json
{
  "command": "swarm-lint",
  "args": ["--watch", "--root", "${workspaceFolder}"]
}
```

### 2. Startup script (`run.sh`)

The original project called the linter at dev server startup:
```bash
bash "$ROOT_DIR/linter/print_errors.sh" "$ROOT_DIR"
```

After conversion, the consumer would change to:
```bash
swarm-lint --root "$ROOT_DIR"
```

### 3. Package dependencies (`pyproject.toml`)

The original project declared vulture as a dev dependency:
```toml
[project.optional-dependencies]
dev = ["vulture"]
```

After conversion:
```toml
[project.optional-dependencies]
dev = ["swarm-lint[all]"]
```

### 4. VS Code settings (`.vscode/settings.json`)

These configure Pylance and ESLint editor extensions — they are NOT consumed by the linter itself. Included here for completeness:

```json
{
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.include": ["backend"],
  "python.analysis.exclude": ["backend/.venv", "backend/uv-bin", "backend/data", "backend/tests"],
  "python.analysis.diagnosticSeverityOverrides": { "reportMissingTypeStubs": "none" },
  "eslint.workingDirectories": ["frontend"]
}
```

### 5. Recommended extensions (`.vscode/extensions.json`)

```json
{
  "recommendations": ["dbaeumer.vscode-eslint"]
}
```

## What `swarm-lint init` should scaffold

Based on the above, `swarm-lint init` should at minimum create `.swarm-lint.json`. It could optionally offer to scaffold:

1. **`.vscode/tasks.json`** entries — the problem matcher config shown above, but using `swarm-lint` as the command
2. **`pyrightconfig.json`** — a template for Python type checking (the original is at `config/pyrightconfig.json` in the current linter folder)
3. **`vulture_whitelist.py`** — an empty whitelist file with a comment explaining its purpose

The `init` command should be non-destructive: if files already exist, print a warning and skip (or offer to merge).
