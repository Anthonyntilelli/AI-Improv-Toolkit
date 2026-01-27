"""
NATS connection and publishing utilities.
"""

import asyncio
import contextlib
from dataclasses import dataclass, field
from enum import Enum
import ssl
import time
from typing import Any, Literal, NamedTuple, AsyncIterator, Optional
import nats
from nats.aio.client import Client as NATS
import json

from common import config as cfg


NatsSubjects = Literal["INTERFACE"]


class QueuePriority(Enum):
    """Defines priority levels for the PriorityQueue."""

    Emergency = 1
    High = 10
    Medium = 20
    Standard = 30
    Low = 40


class ButtonData(NamedTuple):
    """Represents Button event data for a Queue."""

    avatar_id: int
    # action = button press, status = device connect/disconnect
    message_type: Literal["action", "status"]
    action: cfg.AllowedActions | None
    # status: dead = device failed permanently
    status: Optional[Literal["connected", "disconnected", "dead"]]
    version: int = 1
    object_type: str = "ButtonData"
    time_stamp: int = round(time.time())


@dataclass(order=False)  # Important: order=False prevents automatic comparison methods
class QueueRequest:
    """Represents a prioritized request for the PriorityQueue."""

    # Priority level (lower number = higher priority)
    priority: int = field(compare=False)
    request_data: Any = field(compare=False)  # Actual request data

    # This method is what the PriorityQueue uses to compare two objects
    def __lt__(self, other: "QueueRequest") -> bool:
        return self.priority < other.priority


class NatsConnectionSettings(NamedTuple):
    """NATS connection settings."""

    nats_server: str
    use_tls: bool
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    key_password: Optional[str] = None


@contextlib.asynccontextmanager
async def nats_init(network_settings: NatsConnectionSettings) -> AsyncIterator[NATS]:
    """Async context manager to initialize and cleanup NATS connection."""
    nc: Optional[NATS] = None
    try:
        if network_settings.use_tls:
            if network_settings.ca_cert_path is None:
                raise ValueError("CA certificate path is required when TLS is enabled.")
            if network_settings.client_cert_path is None:
                raise ValueError(
                    "Client certificate path is required when TLS is enabled."
                )
            if network_settings.client_key_path is None:
                raise ValueError("Client key path is required when TLS is enabled")
            print("Attempting Nats connection with TLS.")
            context: ssl.SSLContext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True
            context.load_verify_locations(cafile=network_settings.ca_cert_path)
            # Load client certificate and private key
            context.load_cert_chain(
                certfile=network_settings.client_cert_path,
                keyfile=network_settings.client_key_path,
                password=network_settings.key_password,
            )
            nc = await nats.connect(
                servers=f"tls://{network_settings.nats_server}", tls=context
            )
        else:
            print("Attempting Nats connection without TLS.")
            nc = await nats.connect(f"nats://{network_settings.nats_server}")
        yield nc
    finally:
        if nc and nc.is_connected:
            print("Closing Nats connection.")
            await nc.flush()
            await nc.close()


async def nats_publish(
    nc: NATS,
    subject: NatsSubjects,
    output_queue: asyncio.PriorityQueue[QueueRequest],
    quit_event: asyncio.Event,
) -> None:
    """Publish a message to a NATS subject from the output queue."""
    try:
        while not quit_event.is_set():
            item = await output_queue.get()
            try:
                payload = json.dumps(item.request_data._asdict()).encode("utf-8")
                await nc.publish(subject, payload)
            finally:
                output_queue.task_done()

    # Allow task to be cancelled cleanly during shutdown.
    except asyncio.CancelledError:
        return
