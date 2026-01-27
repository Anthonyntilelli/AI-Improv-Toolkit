# AI Tool kit code

This repository contains code for the AI Tool kit project.

The `infra` directory contains the infrastructure as code to deploy the overall system.

## Components

- Ingest - handles button and audio input and forwards to the backend components

## Extra files

- `cheat_sheet.md` - A cheat sheet with useful commands for development.
- `Dockerfile` - A Dockerfile to build a container image for the application.

## Dependencies

- Python 3.14+
- Docker
- Apt packages:
  - portaudio19-dev  # for SoundDevice
  - libasound2-dev
  - build-essential
  - openssl

## Build

Run the docker build command from this directory:
Currently devcontainer cannot building the image.

```bash
docker build -t local/ai-improv-toolkit .
```

## Running the code

This project uses uv to run the main application and pyproject.toml to manage dependencies.
All code and dependencies are contained within the `code` directory.

1) Install dependencies via apt
2) Install uv: `pip install uv`
3) use uv to run the main application:
   `uv run main.py`
