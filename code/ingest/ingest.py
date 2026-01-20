"""
Ingest role module.
Use the start function to start the ingest process.
"""
# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio

# import evdev, nats

from config import config as cfg
from ._config import load_internal_config, IngestSettings


def start(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")
    # Simulate some ingest processing
    asyncio.run(async_loop(load_internal_config(config)))
    ingest_settings: IngestSettings = load_internal_config(config)
    print(f"Loaded audio config: {ingest_settings}")
    print("Ingest role completed.")


# TODO: Async Context Manager for NATS connection

# TODO: Device management class for evdev devices


async def async_loop(ingest_settings: IngestSettings) -> None:
    """Asyncio event loop for ingest role."""
    print("Ingest async loop started.")
    await asyncio.sleep(1)  # Simulate async work
    print("Ingest async loop completed.")

    # Connect to nats server
    # TODO: Implement NATS connection with and without TLS

    # Connect and grab to relevant devices

    # Listen for button presses and update timestamp for debounce

    # Pass button presses to Nats server

    # Close NATS connection and cleanup on exit
