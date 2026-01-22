"""
Ingest role module.
Use the start function to start the ingest process.
"""
# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
import contextlib
from dataclasses import dataclass, field
import time
from typing import Literal, NamedTuple, AsyncIterator
import evdev
# import nats

from config import config as cfg
from ._config import Button, ButtonSubSettings, load_internal_config, IngestSettings

def start(config: cfg.Config) -> None:
    """Function to start the ingest role."""
    print("Ingest role started.")
    ingest_settings: IngestSettings = load_internal_config(config)
    print("Loaded ingest config")
    asyncio.run(async_loop(ingest_settings))
    print("Ingest role completed.")


class ControlDevice(NamedTuple):
    """Represents an avatar device with its evdev device and settings."""

    device: evdev.InputDevice
    settings: Button
    debounce_ms: int

class QueueData(NamedTuple):
    """Represents data for a Queue."""

    device_path: str
    message_type: Literal["action", "status"] # action = button press, status = device connect/disconnect
    action: cfg.AllowedActions | None
    timestamp_ms: int
    status: Literal["connected", "disconnected"] | None

@dataclass(order=False) # Important: order=False prevents automatic comparison methods
class PrioritizedRequest:
    """Represents a prioritized request for the PriorityQueue."""

    priority: int = field(compare=False) # Priority level (lower number = higher priority)
    request_data: QueueData = field(compare=False) # Actual request data

    # This method is what the PriorityQueue uses to compare two objects
    def __lt__(self, other: "PrioritizedRequest") -> bool:
        return self.priority < other.priority

# TODO: Async Context Manager for NATS connection


@contextlib.asynccontextmanager
async def button_init(
    buttons_settings: ButtonSubSettings,
    debounce_ms: int,
) -> AsyncIterator[list[ControlDevice]]:
    """Async context manager to initialize and cleanup button devices."""
    buttons: list[ControlDevice] = []
    try:
        for settings in buttons_settings.buttons:
            button = evdev.InputDevice(settings.device_path)
            if settings.grab:
                button.grab()
            buttons.append(
                ControlDevice(device=button, settings=settings, debounce_ms=debounce_ms)
            )
        yield buttons
    finally:
        for device in buttons:
            print(f"Cleaning up device:{device.device.path}")
            try:
                if device.settings.grab:
                    device.device.ungrab()
            except OSError as e:
                print(f"Unable to ungrab {device.device.path}, device unavailable: {e}")
            finally:
                with contextlib.suppress(OSError):
                    device.device.close()


def time_stamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return round(time.time() * 1000)


def event_filter(event, path: str, allowed_keys: list[cfg.KeyOptions]) -> bool:
    """Filter to allow only key events."""
    ## Filter only key events
    if event.type != evdev.ecodes.EV_KEY:
        print(f"{path}: Ignored non-key event: {event}")
        return False
    # Skip key releases and repeats
    if event.value != 1:  # 1=down, 0=up, 2=repeat
        return False
    # Only respond to selected keys based on configuration
    key = evdev.categorize(event)
    if key.keycode not in allowed_keys:  # type: ignore
        print(f"{path}: Ignored Non-configured key event: {event}")
        return False
    return True


async def print_events(device: ControlDevice) -> None:
    interface = device.device  # type: evdev.InputDevice
    time_stamp: int = 0  # Initial timestamp for debounce
    try:
        async for event in interface.async_read_loop():
            # TODO: Implement logic to handle disconnected devices and reconnection

            # Skip non-key events or non-configured keys
            if not event_filter(
                event, interface.path, list(device.settings.key.keys())
            ):
                continue
            # Debounce logic
            if (time_stamp + device.debounce_ms) > time_stamp_ms():
                print(interface.path, "Button press ignored due to debounce.", sep=": ")
                continue

            time_stamp = time_stamp_ms()
            key = evdev.categorize(event)
            print(interface.path, key, sep=": ")
            key_action = device.settings.key.get(key.keycode)  # type: ignore
            if key_action:
                print(f"Action for {key.keycode}: {key_action}")
            else:
                print(f"No action configured for key: {key.keycode}")
    except asyncio.CancelledError:
        raise
    except OSError as e:
        print(f"Device {interface.path} disconnected, stopping listener: {e}")
    except Exception as e:
        print(f"Error in print_events for device {interface.path}: {e}")


async def async_loop(ingest_settings: IngestSettings) -> None:
    """Asyncio event loop for ingest role."""
    print("Ingest async loop started.")

    # Connect to nats server
    # TODO: Implement NATS connection with and without TLS

    # Connect and grab to relevant devices
    async with button_init(
        ingest_settings.Buttons, ingest_settings.Buttons.Debounce_ms
    ) as avatar_devices:

        devices_tasks = [
            asyncio.create_task(print_events(device)) for device in avatar_devices
        ]
        try:
            await asyncio.gather(*devices_tasks)
        finally:
            for t in devices_tasks:
                t.cancel()
            await asyncio.gather(*devices_tasks, return_exceptions=True)

    # Pass button presses to Nats server

    # Close NATS connection and cleanup on exit
    print("Ingest async loop completed.")

# nats_queue: asyncio.PriorityQueue[PrioritizedRequest] = asyncio.PriorityQueue()

# test_event = QueueData(
#             device_path="/dev/input/event0",
#             type="action",
#             action="reset",
#             timestamp_ms=time_stamp_ms(),
#             status=None
#         )
# nats_queue.put_nowait(PrioritizedRequest(priority=1, request_data=test_event))
