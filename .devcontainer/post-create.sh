#!/usr/bin/env bash
set -euo pipefail

# Post-create script run as the non-root `vscode` user inside the container.
# Responsibilities:
#  - Ensure uv is installed (Astral recommended installer)
#  - Use uv to add/manage developer tools (pre-commit, ansible)
#  - Provide sensible pip --user fallbacks if a CLI is still missing
#  - Install pre-commit hooks for the repo
#
# Usage:
#  - Installs: pre-commit, ansible

UV_INSTALL_URL="https://astral.sh/uv/install.sh"
export PATH="$HOME/.local/bin:$PATH"

echo "=== Devcontainer post-create: ensure uv is available ==="

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found: installing uv with Astral's recommended installer..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf "${UV_INSTALL_URL}" | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "${UV_INSTALL_URL}" | sh
  else
    echo "Error: neither curl nor wget is available to install uv." >&2
    exit 1
  fi

  # ensure user's local bin is on PATH for the remainder of this script
  export PATH="$HOME/.local/bin:$PATH"

  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv installation finished but 'uv' is not on PATH. Expected at ~/.local/bin/uv" >&2
    exit 1
  fi
else
  echo "uv already installed"
fi

# Tools we want uv to manage
TOOLS_TO_ADD=(
  "pre-commit"
  "ansible"
)

echo "=== Adding tools with uv (idempotent) ==="
for t in "${TOOLS_TO_ADD[@]}"; do
  echo "-> uv tool add ${t}"
  # uv tool add is idempotent in practice; ignore non-zero to continue
  uv tool add "${t}" || true
done

# Helper: ensure CLI is available or install fallback via pip --user
ensure_cli_or_pip_fallback() {
  local cmd="$1"
  local pip_pkg="$2"

  if command -v "${cmd}" >/dev/null 2>&1; then
    echo "Found ${cmd} on PATH"
    return 0
  fi

  echo "${cmd} not found on PATH; attempting pip --user install ${pip_pkg} as fallback..."
  python -m pip install --user "${pip_pkg}"
  export PATH="$HOME/.local/bin:$PATH"

  if command -v "${cmd}" >/dev/null 2>&1; then
    echo "Successfully installed ${cmd} via pip --user"
    return 0
  fi

  echo "Warning: ${cmd} still not available after pip install fallback" >&2
  return 1
}

# Ensure pre-commit CLI
ensure_cli_or_pip_fallback "pre-commit" "pre-commit"

# Ensure ansible CLI (use ansible-core as pip fallback)
ensure_cli_or_pip_fallback "ansible" "ansible-core"

# Install pre-commit git hooks if repo is a git working tree
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Installing pre-commit git hooks for this repository..."
  # --install-hooks will ensure hook environments are created; fall back to plain install if needed
  pre-commit install --install-hooks || pre-commit install || true
  echo "pre-commit hooks installed (or attempted)."
else
  echo "Not a git repository (no .git); skipping pre-commit install."
fi

echo ""
echo "Tool verification:"
command -v uv && uv --version || true
command -v pre-commit && pre-commit --version || true
command -v ansible && ansible --version || true

echo "=== post-create script finished successfully ==="
``` ````

Suggested PR title and description
- Title: Add VS Code devcontainer (uv, pre-commit, ansible, terraform, openssl, make)
- Description: Adds .devcontainer with Dockerfile, devcontainer.json, and post-create script. The container includes Python 3.14, Ansible, Terraform, Docker CLI, OpenSSL, and make. Post-create ensures uv is installed, uses uv to add pre-commit and ansible, and runs pre-commit install --install-hooks. Supports rootless Docker by mounting host socket (XDG_RUNTIME_DIR) and passing host UID/GID into build args.

How to create the branch, commit, push, and open the PR

1) From a clone of your repo (replace remote names if different):

git fetch origin
git checkout -b feat/add-devcontainer

2) Add the files:

mkdir -p .devcontainer
# create the three files with the exact contents above, ensure post-create.sh is executable:
chmod +x .devcontainer/post-create.sh

3) Commit and push the branch:

git add .devcontainer
git commit -m "Add VS Code devcontainer (uv, pre-commit, ansible, terraform, openssl, make)"
git push -u origin feat/add-devcontainer

4) Open a PR into ingestion branch

- Using GitHub CLI (if you have gh configured):
  gh pr create --base ingestion --head Anthonyntilelli:feat/add-devcontainer --title "Add VS Code devcontainer (uv, pre-commit, ansible, terraform, openssl, make)" --body "Adds .devcontainer with Dockerfile, devcontainer.json, and post-create script. Supports rootless Docker and installs uv-managed pre-commit and ansible (with pip fallbacks)."

- If the ingestion branch does not exist on the remote and you want to create it as the PR base, create ingestion first:
  git push origin feat/add-devcontainer:ingestion
  # then open PR from the same branch back into ingestion (or use a new branch if you prefer).

- Or open the PR with the GitHub web UI: navigate to your repo → "Compare & pull request" and set the base branch to ingestion and head to feat/add-devcontainer.

Important notes / troubleshooting
- If XDG_RUNTIME_DIR is not set on the machine opening the devcontainer, edit devcontainer.json and replace ${localEnv:XDG_RUNTIME_DIR} with /run/user/<UID> (e.g. /run/user/1000) or the correct path to your rootless docker socket.
- If ingestion branch is protected or requires a specific workflow, pick the correct base or create the ingestion branch per your repo rules.
- If you want the PR created by me directly, I can do that only if you explicitly grant me repository write/PR permissions through the integration you normally use (or provide me with a temporary token and confirm — I cannot accept tokens here). Otherwise follow the steps above.

If you want, I can:
- Update the Dockerfile to install only Docker CLI (smaller image) instead of docker.io.
- Pin Terraform/Ansible to specific versions (tell me which).
- Convert the Dockerfile to accept a PYTHON_VERSION build-arg so you can pick versions without editing the file.

Which of those (if any) would you like me to include before you open the PR?