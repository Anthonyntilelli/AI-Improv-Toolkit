"""
Ingest role module.
Use the start function to start the ingest process.
"""

import asyncio

import common.config as cfg
import common.nats as nats

from ._config import (
    load_internal_config,
    IngestSettings,
)
from ._button import button_init, monitor_input_events
from ._audio import record_and_forward


def start(config: cfg.Config) -> None:
    """Function to start the ingest role."""
    print("Ingest role started.")
    try:
        # TODO: REMOVE skip_button_validation
        ingest_settings: IngestSettings = load_internal_config(
            config, skip_button_validation=True
        )
        print("Loaded ingest config")
    except Exception as e:
        print(f"Failed to load ingest configuration: {e}")
        return
    # asyncio.run(button_loop(ingest_settings)) # TODO: RE-ENABLE button_loop and stick in own thread or process ??
    mic_loop(ingest_settings)
    print("Ingest role completed.")


async def button_loop(ingest_settings: IngestSettings) -> None:
    """Loop to monitor button inputs and send events to NATS."""
    print("Ingest Button Loop started.")
    device_lock = asyncio.Lock()
    nats_queue: asyncio.PriorityQueue[nats.QueueRequest] = asyncio.PriorityQueue()

    # Initialize NATS connection and button devices
    nats_network = nats.NatsConnectionSettings(
        nats_server=ingest_settings.Network.Nats_server,
        use_tls=ingest_settings.Network.Use_tls,
        ca_cert_path=ingest_settings.Network.Ca_cert_path,
        client_cert_path=ingest_settings.Network.Client_cert_path,
        client_key_path=ingest_settings.Network.Client_key_path,
    )
    async with (
        button_init(
            ingest_settings.Buttons, ingest_settings.Buttons.Debounce_ms
        ) as avatar_devices,
        nats.nats_init(nats_network) as nc,
    ):
        tasks = [
            asyncio.create_task(
                monitor_input_events(device, avatar_devices, nats_queue, device_lock, 0)
            )
            for device in avatar_devices.values()
        ]
        tasks.append(
            asyncio.create_task(nats.nats_publish(nc, "INTERFACE", nats_queue))
        )
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    print("Ingest Button loop completed.")


def mic_loop(ingest_settings: IngestSettings) -> None:
    """Loop to monitor microphone and send to hearing server (not NATS)."""
    print("Ingest Mic Loop Started.")

    # TODO: Implement microphone monitoring and sending to hearing server

    record_and_forward(ingest_settings)

    # Set up ssl Context if tls is used
    # create context with microphone and hearing server connection
    # Create hearing server and microphone connection tasks
    # Gather tasks and handle cancellation

    print("Ingest Mic Loop Completed.")
    return
