"""
Ingest role module.
Use the start function to start the ingest process.
"""
# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
import contextlib
from typing import NamedTuple, AsyncIterator
import evdev  # , nats

from config import config as cfg
from ._config import Button, ButtonSubSettings, load_internal_config, IngestSettings


def start(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")
    ingest_settings: IngestSettings = load_internal_config(config)
    print("Loaded audio config")
    asyncio.run(async_loop(ingest_settings))
    print("Ingest role completed.")


class ControlDevice(NamedTuple):
    """Represents an avatar device with its evdev device and settings."""

    device: evdev.InputDevice
    settings: Button


# TODO: Async Context Manager for NATS connection


@contextlib.asynccontextmanager
async def button_init(
    buttons_settings: ButtonSubSettings,
) -> AsyncIterator[list[ControlDevice]]:
    """Async context manager to initialize and cleanup button devices."""
    buttons: list[ControlDevice] = []
    try:
        for settings in buttons_settings.buttons:
            button = evdev.InputDevice(settings.device_path)
            if settings.grab:
                button.grab()
            buttons.append(ControlDevice(device=button, settings=settings))
        yield buttons
    finally:
        for device in buttons:
            try:
                if device.settings.grab:
                    device.device.ungrab()
            finally:
                device.device.close()


async def print_events(device):
    async for event in device.async_read_loop():
        ## Filter only key events
        if event.type != evdev.ecodes.EV_KEY:
            continue  # Skip non-key events
        if event.value != 1:  # 1=down, 0=up, 2=repeat
            continue  # Skip key releases and repeats
        key = evdev.categorize(event)
        print(device.path, key, sep=": ")


async def async_loop(ingest_settings: IngestSettings) -> None:
    """Asyncio event loop for ingest role."""
    print("Ingest async loop started.")

    # Connect to nats server
    # TODO: Implement NATS connection with and without TLS

    # Connect and grab to relevant devices
    async with button_init(ingest_settings.Buttons) as avatar_devices:
        devices_tasks = [
            asyncio.create_task(print_events(device.device))
            for device in avatar_devices
        ]
        try:
            await asyncio.gather(*devices_tasks)
        finally:
            for t in devices_tasks:
                t.cancel()
            await asyncio.gather(*devices_tasks, return_exceptions=True)

    # Listen for button presses and update timestamp for debounce

    # Pass button presses to Nats server

    # Close NATS connection and cleanup on exit
    print("Ingest async loop completed.")
