#!/bin/bash
set -e

echo "=== Devcontainer post-create: minimal setup ==="


# Install pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
  echo "=== Installing pre-commit hooks ==="
  pre-commit autoupdate
  pre-commit install --install-hooks &
else
  echo "No .pre-commit-config.yaml found; skipping pre-commit install."
fi


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

echo "=== Creating Docker context and alias for devcontainer ==="
docker context create show-ingest --docker "host=ssh://developer@show-ingest"  # Run once to create context


# Options for convenience
{
echo 'alias dsc="docker --context show-ingest"'
echo 'alias dsc-b="dsc build -t local/ai-improv-toolkit:latest ."'
echo 'alias dsc-nats="dsc run --rm -d --name nats -p 4222:4222 -p 8222:8222 nats --http_port 8222" # Note: unencrypted'
echo 'alias dsc-ingest="dsc run --rm -it --name ingest -v /dev/show/:/dev/show/ --device=/dev/input -v /opt/show/ingest/config.toml:/etc/ai-show/config.toml local/ai-improv-toolkit"'
} >> ~/.bash_aliases

if jobs -p >/dev/null 2>&1; then
  wait $(jobs -p)  # Wait for background tasks to finish
fi

echo "=== Devcontainer post-create: setup complete ==="
