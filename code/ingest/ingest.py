"""
Ingest role module.
Use the main function to start the ingest process.
"""

# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

import evdev

from config import KeyOptions as KO

from config import config as cfg
from ._config import load_internal_config, _AudioSettings as AudioSettings


@dataclass
class _Button:
    device: evdev.InputDevice
    key: dict[KO, str]  # key with action name
    grabbed: bool
    last_pressed: int = 0


@contextmanager
def button_devices(config: cfg.Config) -> Generator[list[_Button], None, None]:
    """Context manager to handle button devices (grab device)."""
    devices: list[_Button] = []
    try:
        # Reset button
        devices.append(
            _Button(
                evdev.InputDevice(config.Buttons["Reset"]["Path"]),
                {config.Buttons["Reset"]["Key"]: "reset"},
                config.Buttons["Reset"]["grab"],
            )
        )

        # Avatar buttons
        for avatar_button in config.Buttons["Avatars"]:
            devices.append(
                _Button(
                    evdev.InputDevice(avatar_button["Path"]),
                    {avatar_button["Speak"]: "speak"},
                    avatar_button["grab"],
                )
            )

        for device in devices:
            if device.grabbed:
                device.device.grab()
        yield devices

    finally:
        for button in devices:
            if button.grabbed:
                button.device.ungrab()


async def print_events(device: evdev.InputDevice) -> None:
    async for event in device.async_read_loop():
        print(device.path, evdev.categorize(event), sep=": ")


def main(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")

    loop = asyncio.get_event_loop()

    # TODO: set signal handlers for graceful shutdown

    AudioConfig: AudioSettings = load_internal_config(config.Show["Actors_count"])
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
