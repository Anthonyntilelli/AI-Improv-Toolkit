"""
NATS connection and publishing utilities.
"""

import asyncio
from asyncio import Queue
import contextlib
from pydantic import BaseModel, ConfigDict, Field
import ssl
import time
from typing import Literal, NamedTuple, AsyncIterator, Optional
import nats
from nats.aio.client import Client as NATS

from common.dataTypes import ButtonActions


NatsSubjects = Literal["INTERFACE"]


class ButtonData(BaseModel):
    """Represents Button event data for a Queue."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    avatar_id: int
    # action = button press, status = device connect/disconnect
    message_type: Literal["action", "status"]
    action: Optional[ButtonActions]
    # status: dead = device failed permanently
    status: Optional[Literal["connected", "disconnected", "dead"]]
    version: int = 1
    object_type: str = "ButtonData"
    time_stamp: float = Field(default_factory=lambda: time.time())


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
                raise ValueError("Client certificate path is required when TLS is enabled.")
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
            nc = await nats.connect(servers=network_settings.nats_server, tls=context)
        else:
            print("Attempting Nats connection without TLS.")
            stripped_tls = network_settings.nats_server.replace("tls://", "nats://")
            nc = await nats.connect(servers=stripped_tls)
        yield nc
    finally:
        if nc and nc.is_connected:
            print("Closing Nats connection.")
            await nc.flush()
            await nc.close()


async def nats_publish(nc: NATS, subject: NatsSubjects, queue: Queue[str], quit_event: asyncio.Event) -> None:
    """Publish a message to a NATS subject from the output queue."""
    try:
        while not quit_event.is_set():
            item = await queue.get()
            try:
                if not isinstance(item, str):
                    print("Invalid message, skipping publishing to NATS.")
                    continue
                payload = item.encode("utf-8")
                await nc.publish(subject, payload)
            finally:
                queue.task_done()

    # Allow task to be cancelled cleanly during shutdown.
    except asyncio.CancelledError:
        return
