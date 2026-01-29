"""
Ingest role module.
Use the start function to start the ingest process.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import copy

from common.dataTypes import SlidingQueue
import common.config as cfg
import common.nats as nats

from ._config import (
    load_internal_config,
    IngestSettings,
)
from ._button import button_init, monitor_input_events
from ._audio import stream_audio_to_queue, consume_audio_queue, audio_middleware


def start(config: cfg.Config) -> None:
    """Function to start the ingest role."""
    print("Ingest role started.")
    try:
        # TODO: REMOVE skip_button_validation
        ingest_settings: IngestSettings = load_internal_config(config)
        print("Loaded ingest config")
    except Exception as e:
        print(f"Failed to load ingest configuration: {e}")
        return

    audio_pre_queue = SlidingQueue(maxsize=128)
    audio_post_queue = SlidingQueue(maxsize=128)

    with ThreadPoolExecutor() as executor:
        executor.submit(asyncio.run, button_loop(ingest_settings))
        executor.submit(stream_audio_to_queue, ingest_settings, audio_pre_queue, 0)
        executor.submit(audio_middleware, ingest_settings, audio_pre_queue, audio_post_queue)
        executor.submit(consume_audio_queue, ingest_settings, audio_post_queue)

    print("Ingest role completed.")


async def button_loop(ingest_config: IngestSettings) -> None:
    """Loop to monitor button inputs and send events to NATS."""

    # Temporary workaround to avoid mutating the original config (will need to move to frozen dataclass later)
    ingest_settings: IngestSettings = copy.deepcopy(ingest_config)
    # Now use ingest_settings safely in this coroutine

    print("Ingest Button Loop started.")
    device_lock = asyncio.Lock()
    nats_queue: asyncio.PriorityQueue[nats.QueueRequest] = asyncio.PriorityQueue()
    quit_event = asyncio.Event()  # TODO: set this event to quit the loop

    # Initialize NATS connection and button devices
    nats_network = nats.NatsConnectionSettings(
        nats_server=ingest_settings.Network.Nats_server,
        use_tls=ingest_settings.Network.Use_tls,
        ca_cert_path=ingest_settings.Network.Ca_cert_path,
        client_cert_path=ingest_settings.Network.Client_cert_path,
        client_key_path=ingest_settings.Network.Client_key_path,
    )
    async with (
        button_init(ingest_settings.Buttons, ingest_settings.Buttons.Debounce_ms) as avatar_devices,
        nats.nats_init(nats_network) as nc,
    ):
        tasks = [
            asyncio.create_task(monitor_input_events(device, avatar_devices, nats_queue, device_lock, 0))
            for device in avatar_devices.values()
        ]
        tasks.append(asyncio.create_task(nats.nats_publish(nc, "INTERFACE", nats_queue, quit_event)))
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    print("Ingest Button loop completed.")
