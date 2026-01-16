# Settings

This module is responsible for validating the configuration file for the AI Improv Toolkit and loading the settings into
a NATS server. It ensures that all necessary configurations are correctly set up before the main application runs.

## Requirements

- Python 3.14 or higher
- NATS server running and accessible
- Required Python packages listed in `pyproject.toml`

## Usage

The system is designed to be run inside a docker container as part of the overall AI Improv Toolkit deployment.
Deployment will be handled via the infrastructure as code in the `infra/` directory.

## Configuration

This component reads its configuration from a toml file located at `/config/settings.toml` inside the container.
The configuration file should contain all necessary settings for the AI Improv Toolkit. There is an example configuration
in `config/config.example.toml`.

## TLS

The component uses TLS for secure communication with the NATS server. Ensure that the appropriate TLS certificates are
available and correctly referenced in the configuration file. The certificates should be mounted into the container at
the specified paths.

## Docker

TODO: Add docker build and run instructions here.

## Testing

Unit tests can be found in the `tests/` directory. To run the tests, use the following command:

TODO: Add test command here
