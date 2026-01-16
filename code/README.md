# AI Tool kit code

This repository contains code for the AI Tool kit project. Each folder contains a particular component of the overall
project.
Each component will have its own README.md file with details on how to deploy and manage that service.
These components work together to create the overall system.

The `infra` directory contains the infrastructure as code to deploy the overall system.

## Components

TODO

## Contents

- `sharedCode` -  SharedCode that is used by multiple components.
- `cheat_sheet.md` - A cheat sheet with useful commands for development.

## Tools

Most tools are installed globally or via pre-commit on the development machine as they are used across multiple components.

- ruff - Python linter and formatter.
- mypy - Static type checker for Python.

## General Development

Each component will have it own virtual environment and dependencies.
Please refer to the individual component README.md files for details on how to set up the development environment
for each component.

If you are using the the recommended vscode extensions you may need to install additional tools to get the full functionality.

__Note__: All development and testing was done on Debian/Ubuntu servers.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

    ```bash
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
    source ~/.bashrc
    ```
