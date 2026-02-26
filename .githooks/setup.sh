#!/usr/bin/env bash
# .githooks/setup.sh
# Configures git to use this repo's hooks directory.
# Run once after cloning: bash .githooks/setup.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.githooks"

# Point git at the committed hooks directory.
git config core.hooksPath "$HOOKS_DIR"

# Ensure hooks are executable.
chmod +x "$HOOKS_DIR/pre-commit"

echo "Git hooks configured. Hook path: $HOOKS_DIR"
echo ""
echo "Active hooks:"
ls -1 "$HOOKS_DIR" | grep -v setup.sh | grep -v README || true
echo ""
echo "To verify:"
echo "  git config core.hooksPath"
