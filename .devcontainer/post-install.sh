#!/bin/bash
set -e

echo "=== Devcontainer post-create: minimal setup ==="

# Setup uv shell completions for vscode user
if command -v uv >/dev/null 2>&1; then
  echo "=== Setting up uv shell completions ==="
  if ! grep -q "uv generate-shell-completion bash" ~/.bashrc; then
    uv generate-shell-completion bash >> ~/.bashrc
  fi
  if command -v uvx >/dev/null 2>&1 && ! grep -q "uvx --generate-shell-completion bash" ~/.bashrc; then
    uvx --generate-shell-completion bash >> ~/.bashrc
  fi
fi

# Enable terraform autocomplete for vscode user
if command -v terraform >/dev/null 2>&1; then
  echo "=== Enabling terraform autocomplete ==="
  terraform -install-autocomplete >/dev/null 2>&1 || true
fi

# Install pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
  echo "=== Installing pre-commit hooks ==="
  pre-commit install --install-hooks
else
  echo "No .pre-commit-config.yaml found; skipping pre-commit install."
fi
