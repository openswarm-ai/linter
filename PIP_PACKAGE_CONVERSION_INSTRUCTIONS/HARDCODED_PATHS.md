# Hardcoded Paths Reference

Exact line-by-line reference of every hardcoded project-specific value in the current code that must become config-driven.

## checks/vulture.py

### Line 12: CONFIG_DIR
```python
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
```
**Problem**: Assumes package-relative config directory.
**Fix**: Remove. The whitelist path will come from the config dict.

### Line 20: vulture binary location
```python
vulture_bin = root / "backend" / ".venv" / "bin" / "vulture"
```
**Problem**: Hardcodes `backend/.venv/bin/vulture`.
**Fix**: Use `config["vulture"]["venv_path"]` if set, constructing `root / venv_path / "bin" / "vulture"`. Fall back to `shutil.which("vulture")`.

### Line 27-28: whitelist path and scan targets
```python
whitelist = CONFIG_DIR / "vulture_whitelist.py"
cmd = [str(vulture_bin), "backend", "debug.py"]
```
**Problem**: Hardcodes whitelist location and scan targets (`backend`, `debug.py`).
**Fix**: Whitelist from `config["vulture"]["whitelist"]` (resolved relative to root, or None to skip). Targets from `config["vulture"]["targets"]` (list of paths).

### Line 31-33: vulture excludes
```python
cmd.extend([
    "--min-confidence", str(min_confidence),
    "--exclude", ".venv,__pycache__,data,uv-bin",
])
```
**Problem**: Hardcodes `".venv,__pycache__,data,uv-bin"`.
**Fix**: Use `config["vulture"]["exclude"]` (string, comma-separated).

## checks/eslint.py

### Line 12: frontend directory
```python
frontend_dir = root / "frontend"
```
**Problem**: Hardcodes `frontend` as the directory containing `node_modules/.bin/eslint` and `eslint.config.*`.
**Fix**: Use `root / config["eslint"]["directory"]`.

### Line 17: eslint arguments
```python
cmd = [str(eslint_bin), "src/", "--format", "json", "--no-warn-ignored"]
```
**Problem**: Hardcodes `"src/"` as the lint target and specific flags.
**Fix**: Use `config["eslint"]["args"]` (list of strings). Default: `["src/", "--format", "json", "--no-warn-ignored"]`. Note: `--format json` is required for the output parser to work — document this.

## checks/knip.py

### Line 23: frontend directory
```python
frontend_dir = root / "frontend"
```
**Problem**: Same as eslint — hardcodes `frontend`.
**Fix**: Use `root / config["knip"]["directory"]`.

### Line 45: output path prefix
```python
rel = f"frontend/{filepath}"
```
**Problem**: Hardcodes `"frontend/"` as the prefix for file paths in error output.
**Fix**: Use `f"{config['knip']['directory']}/{filepath}"`.

## lint.py (becomes cli.py)

### Line 20: config file location
```python
CONFIG_FILE = SCRIPT_DIR / "config" / "config.json"
```
**Problem**: Loads config from a path relative to the script file.
**Fix**: Replace with `from swarm_lint.config import load_config`. Resolution order: `--config` flag → `.swarm-lint.json` in root → bundled defaults.

### Line 107: config directory for watch filter
```python
config_dir = SCRIPT_DIR / "config"
```
**Problem**: Watches the package's own config directory for changes.
**Fix**: Watch the project's `.swarm-lint.json` (and/or the `--config` path) instead. The watch filter's JSON detection should look for the project config file, not the package's internal defaults.

## Summary table

| File | Line(s) | Hardcoded value | Config key |
|------|---------|----------------|------------|
| vulture.py | 20 | `backend/.venv/bin/vulture` | `vulture.venv_path` |
| vulture.py | 28 | `"backend", "debug.py"` | `vulture.targets` |
| vulture.py | 33 | `".venv,__pycache__,data,uv-bin"` | `vulture.exclude` |
| vulture.py | 27 | `CONFIG_DIR / "vulture_whitelist.py"` | `vulture.whitelist` |
| eslint.py | 12 | `"frontend"` | `eslint.directory` |
| eslint.py | 17 | `"src/", "--format", "json", ...` | `eslint.args` |
| knip.py | 23 | `"frontend"` | `knip.directory` |
| knip.py | 45 | `f"frontend/{filepath}"` | `knip.directory` (reuse) |
| lint.py | 20 | `SCRIPT_DIR / "config" / "config.json"` | Config resolution chain |
| lint.py | 107 | `SCRIPT_DIR / "config"` | Watch the project config file |
