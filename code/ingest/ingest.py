"""
Ingest role module.
Use the main function to start the ingest process.
"""

import asyncio

from config import config as cfg
from ._config import _load_internal_config, _AudioSettings
from ._button import button_devices, print_events


def main(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")

    loop = asyncio.get_event_loop()

    # TODO: set signal handlers for graceful shutdown

    AudioConfig: _AudioSettings = _load_internal_config(config.Show["Actors_count"])
    print(f"Loaded audio config: {AudioConfig}")

    with button_devices(config) as buttons:
        for device in buttons:
            asyncio.ensure_future(print_events(device.device))

    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    print("Ingest role completed.")
