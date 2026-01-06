# AI Improv ToolKit

Toolkit/Software use to run the AI power show for my local community improv team.

## Ethics Statement

This project is committed to upholding strict ethical standards regarding the use of AI in live improvisational theater.
Please see [Ethics.md](Ethics.md) for our ethics statement regarding the use of AI in improv performances.

## Secrets

Store sensitive values/secrets in the `secrets` folder, `.env` file, name the file have `*.no-git.*` or end a file with `.pass`.
detect-secrets with pre-commit is used to reduce the risk of committing sensitive values to git.

## Description

TODO

## Directory

- `.vscode` - config and hints for the vscode editor.
- `infra/` - Infrastructure as code for deploying the system.
- `secrets/` - holds most secrets for the project, most file in this directory will be ignored by git.
- `ethics/` - holds the ethics statement for the project.

## Deploy

See [infra/README.md](infra/README.md) for more info.
Note: The steps may change as the project is under active development.

## Development

See [Development.md](Development.md) for more info.
Note: The steps may change as the project is under active development.

### Installing

- TODO

### Executing program

- TODO

## Help

- TODO

## Authors

- Anthony Tilelli

## License

This project is licensed under the LGPLV3 License - see the LICENSE.md file for details

## Acknowledgments

- [improbotics](https://improbotics.org/)
- [DomPizzie (README template)](https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc)
- [Deepak Prasad](https://www.golinuxcloud.com/openssl-create-certificate-chain-linux/)
