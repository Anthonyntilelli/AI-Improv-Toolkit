# AI Improv ToolKit

Toolkit/Software use to run the AI power show for my local community improv team.

## Description

TODO

## Ethics Statement

This project is committed to upholding strict ethical standards regarding the
use of AI in live improvisational theater.

Please see [Ethics.md](Ethics.md) for our ethics statement regarding the use of AI in improv performances.

## Secrets

Store sensitive values/secrets in the `secrets` folder, `.env` file, name the file have `*.no-git.*`
or end a file with `.passwd`.

__NOTE__: Detect-secrets with pre-commit is used to reduce the risk of committing sensitive values to git.

## Directory

- `.vscode` - config and hints for the vscode editor.
- `.github` - github related files.
- `infra/` - Infrastructure as code for deploying the system.
- `secrets/` - holds most secrets for the project, most file in this directory
will be ignored by git.
- `ethics/` - holds the ethics statement for the project.
- `code/` - holds the code for the for the overall system.

## Deploy

See [infra/README.md](infra/README.md) for more info.
Note: The steps may change as the project is under active development.

## Development

See [code/README.md](code/README.md) for more info.
Note: The steps may change as the project is under active development.

## Pre-commit

Pre-commit hooks are used to enforce code quality and standards.

1) Install pre-commit.
2) Auto update pre-commit hooks.

    ```bash
    pre-commit autoupdate
    ```

3) Run the below commands to install the git hooks.

    ```bash
    pre-commit install
    ```

## Code Standards

- LF line endings enforced via .gitattributes
- pre-commit hooks are used to enforce style and check for errors
  - Markdown linting with markdownlint-cli2
  - Terraform with terraform fmt and validate
  - Script is through shell check
  - Secrets are detected with detect-secrets
  - Ansible linting with ansible-lint
  - Python linting with ruff and mypy

## Help

- TODO

## Authors

- Anthony Tilelli

## License

This project is licensed under the LGPLV3 License - see the LICENSE.md file for details

## Acknowledgments

- [Improbotics](https://improbotics.org/)
- [DomPizzie (README template)](https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc)
- [Deepak Prasad](https://www.golinuxcloud.com/openssl-create-certificate-chain-linux/)
