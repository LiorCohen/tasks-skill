#!/usr/bin/env bash
# Install tasks-viewer VS Code extension
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION=$(node -p "require('./package.json').version")
EXT_DIR="${HOME}/.vscode/extensions/local.tasks-viewer-${VERSION}"

cd "$SCRIPT_DIR"
npm install
npm run compile

rm -rf "${HOME}"/.vscode/extensions/local.tasks-viewer-*
mkdir -p "$EXT_DIR"
cp -r out media node_modules package.json "$EXT_DIR/"

echo "Installed. Reload VS Code to activate."
