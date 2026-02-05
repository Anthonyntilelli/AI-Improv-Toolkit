"""
Ingest role module.
Use the start function to start the ingest process.
"""

import asyncio
from typing import Any, Final

from common.config import NetworkConfig, ModeConfig, ShowConfig
from common.dataTypes import AsyncSlidingQueue
from ._config import IngestSettings
from ._button import button_init, monitor_input_event
from ._sound_hardware import mic_to_queue, queue_to_speaker
import common.nats as common_nats


BUTTON_MAX_RECONNECT_ATTEMPTS: Final[int] = 5
BUTTON_RECONNECTION_DELAY_S: Final[int] = 2

AUDIO_MAX_STREAM_RECONNECT_ATTEMPTS: Final[int] = 5
AUDIO_STREAM_RECONNECTION_DELAY_S: Final[int] = 2


async def _button_loop(networking_settings: NetworkConfig, ingest_config: IngestSettings) -> None:
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


async def _audio_loop(ingest_config: IngestSettings) -> None:
    """Loop to handle audio streaming."""
    print("Ingest Audio Loop started.")

    sliding_window_size = 250  # Number of audio frames in the sliding window

    frame_queue = AsyncSlidingQueue(maxsize=sliding_window_size)
    # packet_queue = AsyncSlidingQueue(maxsize=sliding_window_size)
    exit_event = asyncio.Event()

    async def placeholder() -> None:
        while True:
            _ = await frame_queue.get()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            mic_to_queue(
                mic_name=ingest_config.actor_mics[0].name,
                output_queue=frame_queue,
                max_reconnect_attempts=AUDIO_MAX_STREAM_RECONNECT_ATTEMPTS,
                exit_event=exit_event,
            )
        )
        # tg.create_task(placeholder())
        tg.create_task(
            queue_to_speaker(
                input_queue=frame_queue,
                speaker_name="HDA Intel PCH: SN6140 Analog",
                exit_event=exit_event,
            )
        )

        # tg.create_task(
        #     prep_frame_for_webRTC(
        #         input_queue=frame_queue,
        #         output_queue=packet_queue,
        #         exit_event=exit_event,
        #     )
        # )

    print("Ingest Audio loop completed.")


def start(
    show_config: ShowConfig, network_config: NetworkConfig, mode_config: ModeConfig, raw_ingest_config: dict[str, Any]
) -> None:
    """Function to start the ingest role."""
    print("Ingest role started.")
    ingest_config = IngestSettings(**raw_ingest_config)

    # Validate configuration consistency
    if show_config.actor_count != len(ingest_config.actor_mics):
        raise ValueError(
            f"Actor count in Show config ({show_config.actor_count}) does not match number of actor mics in Ingest config ({len(ingest_config.actor_mics)})."
        )
    if show_config.avatar_count != len(ingest_config.avatar_controllers):
        raise ValueError(
            f"Avatar count in Show config ({show_config.avatar_count}) does not match number of avatar controllers in Ingest config ({len(ingest_config.avatar_controllers)})."
        )

    # asyncio.run(button_loop(network_config, ingest_config))
    asyncio.run(_audio_loop(ingest_config))
    print("Ingest role completed.")
