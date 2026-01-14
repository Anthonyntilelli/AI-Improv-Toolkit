# AI Tool kit code

This repository contains code for the AI Tool kit project. Each folder contains a particular micro-service of the overall
project.
Each micro-service will have its own README.md file with details on how to deploy and manage that service.
These micro-services work together to create the overall system. I am making use of micro-services architecture to allow
part of the system to be run in the cloud while the smaller parts can run in the show. The ram shortage is preventing
finding a strong enough edge
device to run the entire system locally.

The `infra` directory contains the infrastructure as code to deploy the overall system.

## Micro-services

- Settings - Reads and validates configuration settings for the AI Toolkit.  The validated settings are then uploaded to
 the KV in NATS service to be used by other micro-services.

## Contents

- `settings` -  settings micro-service code.

## General Development

Each micro-service will have it own virtual environment and dependencies.
Please refer to the individual micro-service README.md files for details on how to set up the development environment
for each micro-service.

If you are using the the recommended vscode extensions you may need to install additional tools to get the full functionality.

__Note__: All development and testing was done on Debian/Ubuntu servers.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

    ```bash
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
    source ~/.bashrc
    ```
