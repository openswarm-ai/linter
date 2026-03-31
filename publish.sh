#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYPIRC="$SCRIPT_DIR/.pypirc"
TARGET="${1:-}"

if [[ "$TARGET" != "test" && "$TARGET" != "real" ]]; then
    echo "Usage: ./publish.sh <test|real>"
    echo ""
    echo "  test  — build and upload to TestPyPI"
    echo "  real  — build and upload to PyPI (production)"
    exit 1
fi

if [[ ! -f "$PYPIRC" ]]; then
    echo "ERROR: .pypirc not found. Paste your API tokens into .pypirc first."
    echo "       (see .pypirc in the project root — it's gitignored)"
    exit 1
fi

if grep -q "PASTE_YOUR_" "$PYPIRC"; then
    echo "ERROR: .pypirc still has placeholder tokens. Edit it and paste your real tokens."
    exit 1
fi

VERSION=$(python -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")
echo "==> Package version: $VERSION"

# Ensure build tools are installed
echo "==> Ensuring build + twine are installed..."
python -m ensurepip --upgrade 2>/dev/null || true
python -m pip install --quiet --upgrade build twine

# Clean previous build artifacts
echo "==> Cleaning old dist/..."
rm -rf dist/ build/ src/*.egg-info

# Build sdist + wheel
echo "==> Building package..."
python -m build

# Verify the package description renders correctly
echo "==> Checking package..."
python -m twine check dist/*

# Upload
if [[ "$TARGET" == "test" ]]; then
    echo "==> Uploading to TestPyPI..."
    python -m twine upload --config-file "$PYPIRC" --repository testpypi dist/*
    echo ""
    echo "Done! Install with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ swarm-lint==$VERSION"
else
    echo "==> Uploading to PyPI (production)..."
    python -m twine upload --config-file "$PYPIRC" dist/*
    echo ""
    echo "Done! Install with:"
    echo "  pip install swarm-lint==$VERSION"
fi

echo ""
echo "Don't forget to tag the release:"
echo "  git tag v$VERSION && git push origin v$VERSION"
