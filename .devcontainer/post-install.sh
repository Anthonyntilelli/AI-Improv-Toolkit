#!/bin/bash
set -e

# URL for Astral's uv installer script
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

apt-get update


# Tools we want uv to manage
readonly TOOLS_TO_ADD_UV=( "pre-commit" "ansible")

readonly REQUIRED_PACKAGES=( "portaudio19-dev" "libasound2-dev" "build-essential" "openssl" )

whoami


echo "=== Devcontainer post-create: ensure terraform and whois are available ==="
if ! command -v terraform >/dev/null 2>&1; then
    # Add HashiCorp apt repository and install terraform
    mkdir -p /etc/apt/keyrings
    wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /etc/apt/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/etc/apt/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list
    apt-get install -y --no-install-recommends terraform whois
fi

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


echo "=== Devcontainer post-create: ensure required packages are installed ==="
apt-get update
for package in "${REQUIRED_PACKAGES[@]}"; do
  if ! dpkg -s "$package" >/dev/null 2>&1; then
    echo "Installing package: $package"
    apt-get install -y --no-install-recommends "$package"
  else
    echo "Package $package is already installed."
  fi
done
rm -rf /var/lib/apt/lists/*

