# ShareCode

This directory contains shared code modules used across multiple components of the AI Improv Toolkit project.
These modules provide common functionality, configurations, and utilities to ensure consistency and reusability
throughout the codebase.

## Modules

- `config.py`: Contains validation and loading functions for configuration files.

## Usage

To use the shared code modules, simply import the required functions or classes into your project files.
For example, to use the configuration loading functionality, you can do the following:

### config.py

```python
from config import Config, generate_config
config = generate_config("path/to/config.toml")
```
