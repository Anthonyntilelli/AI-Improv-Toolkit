"""
Validated General configuration model for the AI Improv Toolkit. Makes use of pydantic for validation.
"""

import logging
from pathlib import Path
import os
import socket
from annotated_types import Gt
import re
from typing import Annotated, Literal

from pydantic import ConfigDict, BaseModel, model_validator


NonZeroPositiveInt = Annotated[int, Gt(0)]

ComponentRole = Literal["ingest", "vision", "hearing", "brain", "output", "health_check"]


def get_logging_level(level: debug_level_options) -> int:
    """Get the logging level based on the Debug_level setting."""
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    # invalid levels default to CRITICAL
    return level_mapping.get(level, logging.CRITICAL)


debug_level_options = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def check_server(host: str, port: int) -> bool:
    """Check if a TCP server is reachable at the given host and port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, port))
            return True
    except socket.error:
        return False


class ModeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ethics: bool
    debug_level: debug_level_options
    role: ComponentRole

    @model_validator(mode="after")
    def check_health_check_role(cls, self):
        if self.ethics and self.debug_level not in ["ERROR", "CRITICAL"]:
            raise ValueError("Limited logging is required when ethics mode is enabled ['ERROR', 'CRITICAL'].")
        return self


class NetworkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    nats_server: str
    connection_timeout_s: NonZeroPositiveInt
    retry_attempts: NonZeroPositiveInt
    retry_backoff_ms: NonZeroPositiveInt
    ca_cert_path: str
    client_cert_path: str
    client_key_path: str

    @model_validator(mode="after")
    def check_nats_server(cls, self):
        # Validate format
        server_pattern = re.compile(r"^tls://.+:\d+$")
        if not server_pattern.match(self.nats_server):
            raise ValueError("NATS server must be in the format 'tls://hostname:port'")
        # Validate that the server is reachable
        host, port_str = self.nats_server[len("tls://") :].rsplit(":", 1)
        port = int(port_str)
        if not check_server(host, port):
            raise ValueError(f"NATS server {self.nats_server} is not reachable")
        return self

    @model_validator(mode="after")
    def check_tls_path(cls, self):
        if not self.ca_cert_path or not self.client_cert_path or not self.client_key_path:
            raise ValueError("TLS path must be provided for TLS connections")
        ca_cert_path = Path(self.ca_cert_path)
        client_cert_path = Path(self.client_cert_path)
        client_key_path = Path(self.client_key_path)
        for path in [ca_cert_path, client_cert_path, client_key_path]:
            if not path.is_file():
                raise ValueError(f"TLS file does not exist at path: {path}")
            if not os.access(path, os.R_OK):
                raise ValueError(f"TLS file is not readable at path: {path}")
        return self
