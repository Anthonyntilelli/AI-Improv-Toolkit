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

echo "=== Creating Docker context ==="
if docker context inspect show-ingest >/dev/null 2>&1; then
  echo "Docker context 'show-ingest' already exists; skipping creation."
else
  echo "Creating docker context 'show-ingest'..."
  docker context create show-ingest --docker "host=ssh://developer@show-ingest"  # Run once to create context
fi


# Options for convenience

echo "=== Adding docker context aliases to ~/.bash_aliases ==="
if ! grep -q "dsc" ~/.bash_aliases; then
  {
    echo 'alias cd-c="cd /workspaces/AI-Improv-Toolkit/code"'
    echo 'alias dsc="cd-c && docker --context show-ingest"'
    echo 'alias dsc-b="dsc build -t local/ai-improv-toolkit:latest ."'
    echo 'alias dsc-nats="dsc run --network dev_network --rm -d --name nats_server -p 4222:4222 -p 8222:8222 nats --http_port 8222" # Note: unencrypted'
    echo 'alias dsc-ingest="dsc run --network dev_network --rm -it --name ingest -v /dev/show/:/dev/show/ --device=/dev/input --device /dev/snd:/dev/snd -v /opt/show/ingest/:/etc/ai-show local/ai-improv-toolkit:latest"'
    echo 'alias dsc-stop-all="dsc stop \$(dsc ps -q)"'

  } >> ~/.bash_aliases
fi

pids="$(jobs -pr || true)"
if [ -n "$pids" ]; then
  # shellcheck disable=SC2086
  wait $pids
fi

echo "=== Devcontainer post-create: setup complete ==="
