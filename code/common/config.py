"""
Validated General configuration model for the AI Improv Toolkit. Makes use of pydantic for validation.
"""

import logging
import socket
from annotated_types import Gt
from typing import Annotated, Literal

from pydantic import ConfigDict, BaseModel, model_validator

# Types
NonZeroPositiveInt = Annotated[int, Gt(0)]

ComponentRole = Literal["frontend", "backend"]

debug_level_options = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


# Config Helper Functions
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


def check_server_tcp(host: str, port: int) -> bool:
    """Check if a TCP server is reachable at the given host and port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, port))
            return True
    except socket.error:
        return False


# Configuration Models
class ShowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    description: str
    actor_count: NonZeroPositiveInt
    avatar_count: NonZeroPositiveInt

    @model_validator(mode="after")
    def mvp_limits(cls, self):
        if self.actor_count != 1:
            raise ValueError("MVP supports only 1 actor for now.")
        if self.avatar_count != 1:
            raise ValueError("MVP supports only 1 avatar for now.")
        return self


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


class WebrtcConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    peer_server: str
    port: NonZeroPositiveInt
    pre_shared_key: str
    ice_servers: list[str]

    # Peer server is not validated here, frontend will wait for the server to be available and backend will start these server.

    @model_validator(mode="after")
    def validate_port(cls, self):
        if not (1 <= self.port <= 65535):
            raise ValueError("Port number must be between 1 and 65535.")
        return self

    @model_validator(mode="after")
    def validate_pre_shared_key(cls, self):
        if len(self.pre_shared_key) < 8:
            raise ValueError("Pre-shared key must be at least 8 characters long.")
        return self

    @model_validator(mode="after")
    def validate_ice_servers(cls, self):
        if len(self.ice_servers) == 0:
            raise ValueError("At least one ICE server must be provided.")
        for server in self.ice_servers:
            if not isinstance(server, str):
                raise ValueError(f"ICE server entry must be a string: {server}")
            _, port = server.split(":") if ":" in server else (server, None)
            if port is None:
                raise ValueError(f"ICE server entry must include port: {server}")
            try:
                port = int(port)
            except ValueError:
                raise ValueError(f"ICE server port must be must be convertible to an integer: {server}")
            if not (1 <= int(port) <= 65535):
                raise ValueError(f"ICE server port must be between 1 and 65535: {server}")
        return self
