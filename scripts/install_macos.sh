#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found."
  echo "Install it with one of:"
  echo "  brew install uv"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [ ! -f "pyproject.toml" ]; then
  echo "pyproject.toml was not found. Run this script from the project checkout."
  exit 1
fi

if [ -d "pywheels" ] && ! find pywheels -name "*.whl" -type f | grep -q .; then
  echo "pywheels/ exists but contains no .whl files."
  exit 1
fi

echo "Syncing Python environment with uv..."
uv sync --frozen

echo "Installing Playwright Chromium browser..."
uv run playwright install chromium

echo
echo "Install complete."
echo "Run the bot with:"
echo "  uv run python main.py"
