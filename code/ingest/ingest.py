"""
Ingest role module.
Use the start function to start the ingest process.
"""

import asyncio
from typing import Any, Final

from common.config import NetworkConfig, ModeConfig, ShowConfig
from ._config import IngestSettings
from ._button import button_init, monitor_input_event
import common.nats as common_nats

BUTTON_MAX_RECONNECT_ATTEMPTS: Final[int] = 5
BUTTON_RECONNECTION_DELAY_S: Final[int] = 2


# def start(config: cfg.Config) -> None:
#     """Function to start the ingest role."""
#     print("Ingest role started.")
#     try:
#         # TODO: REMOVE skip_button_validation
#         ingest_settings: IngestSettings = load_internal_config(config)
#         print("Loaded ingest config")
#     except Exception as e:
#         print(f"Failed to load ingest configuration: {e}")
#         return

#     audio_pre_queue = SlidingQueue(maxsize=128)
#     audio_post_queue = SlidingQueue(maxsize=128)

#     with ThreadPoolExecutor() as executor:
#         executor.submit(asyncio.run, button_loop(ingest_settings))
#         executor.submit(stream_audio_to_queue, ingest_settings, audio_pre_queue, 0)
#         executor.submit(audio_middleware, ingest_settings, audio_pre_queue, audio_post_queue)
#         executor.submit(consume_audio_queue, ingest_settings, audio_post_queue)

#     print("Ingest role completed.")


async def button_loop(networking_settings: NetworkConfig, ingest_config: IngestSettings) -> None:
    """Loop to monitor button inputs and send events to NATS."""

    print("Ingest Button Loop started.")
    device_lock = asyncio.Lock()
    nats_queue: asyncio.Queue[str] = asyncio.Queue()
    quit_event = asyncio.Event()

    nats_network_settings = common_nats.NatsConnectionSettings(
        nats_server=networking_settings.nats_server,
        use_tls=False,  # Set to False fo development/testing without TLS
        ca_cert_path=networking_settings.ca_cert_path,
        client_cert_path=networking_settings.client_cert_path,
        client_key_path=networking_settings.client_key_path,
    )
    button_init_settings = (ingest_config.avatar_controllers + [ingest_config.reset], ingest_config.button_debounce_ms)

    async with (
        button_init(button_init_settings[0], button_init_settings[1]) as buttons,
        common_nats.nats_init(nats_network_settings) as nc,
    ):
        tasks = [
            asyncio.create_task(
                monitor_input_event(
                    button,
                    buttons,
                    nats_queue,
                    device_lock,
                    BUTTON_MAX_RECONNECT_ATTEMPTS,
                    BUTTON_RECONNECTION_DELAY_S,
                    0,
                )
            )
            for button in buttons.values()
        ]
        tasks.append(asyncio.create_task(common_nats.nats_publish(nc, "Interface", nats_queue, quit_event)))
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    print("Ingest Button loop completed.")


def start(
    show_config: ShowConfig, network_config: NetworkConfig, mode_config: ModeConfig, raw_ingest_config: dict[str, Any]
) -> None:
    """Function to start the ingest role."""
    print("Ingest role started.")
    ingest_config = IngestSettings(**raw_ingest_config)
    if show_config.actor_count != len(ingest_config.actor_mics):
        raise ValueError(
            f"Actor count in Show config ({show_config.actor_count}) does not match number of actor mics in Ingest config ({len(ingest_config.actor_mics)})."
        )
    if show_config.avatar_count != len(ingest_config.avatar_controllers):
        raise ValueError(
            f"Avatar count in Show config ({show_config.avatar_count}) does not match number of avatar controllers in Ingest config ({len(ingest_config.avatar_controllers)})."
        )
    asyncio.run(button_loop(network_config, ingest_config))

    print("Ingest role completed.")
