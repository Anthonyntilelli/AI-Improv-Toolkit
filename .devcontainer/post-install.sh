#!/bin/bash
set -e

# URL for Astral's uv installer script
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

# Tools we want uv to manage
readonly TOOLS_TO_ADD_UV=( "pre-commit" "ansible")

echo "=== Devcontainer post-create: ensure uv is available ==="
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found: installing uv with Astral's recommended installer..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf "${UV_INSTALL_URL}" | sh
    # shellcheck disable=SC2016
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
    # shellcheck disable=SC2016
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "${UV_INSTALL_URL}" | sh
    # shellcheck disable=SC2016
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
    # shellcheck disable=SC2016
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
  else
    echo "Error: neither curl nor wget is available to install uv." >&2
    exit 1
  fi
fi

echo "=== Adding tools with uv (idempotent) ==="
for t in "${TOOLS_TO_ADD_UV[@]}"; do
  echo "-> uv tool install ${t}"
  uv tool install "${t}" || true
done

# Install pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
  echo "=== Installing pre-commit hooks ==="
  pre-commit install
else
  echo "No .pre-commit-config.yaml found; skipping pre-commit install."
fi

echo "=== Setting up starship prompt if available ==="
# Setup starship prompt if available
if command -v starship &> /dev/null; then
    # Add starship initialization to .bashrc if not already present
    if ! grep -q "starship init bash" ~/.bashrc; then
        # shellcheck disable=SC2016
        echo 'eval "$(starship init bash)"' >> ~/.bashrc
    fi
fi
