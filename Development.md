# Development

## Getting Started

__Note__: All development and testing was done on Debian/Ubuntu servers.

1) Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

    ```bash
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
    source ~/.bashrc
    ```

2) Install terraform
    - install `whois` package for `mkpasswd`
3) Install shellcheck
4) Install detect-secrets

    ```bash
    uv tool install detect-secrets
    ```

5) Install ansible

    ```bash
    uv tool install --with-executables-from ansible-core ansible
    uv tool install ansible-lint
    ```

6) Install and configure pre-commit

    ```bash
    uv tool install pre-commit
    pre-commit install
    ```

## Development Standards

- LF line endings enforced via .gitattributes
- pre-commit hooks are used to enforce style and check for errors
  - Terraform with terraform fmt and validate
  - Script is through shell check
  - Secrets are detected with detect-secrets
  - Ansible linting with ansible-lint
  - Python (TODO)

### Note: make sure to run `pre-commit install` after cloning the repo to enable git hooks
