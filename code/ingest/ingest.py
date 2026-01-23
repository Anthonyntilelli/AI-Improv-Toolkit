"""
Ingest role module.
Use the start function to start the ingest process.
"""
# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
import contextlib
from dataclasses import dataclass, field
from enum import Enum
import ssl
import time
from typing import Final, Literal, NamedTuple, AsyncIterator, Optional
import evdev
import nats
from nats.aio.client import Client as NATS

from config import config as cfg
from ._config import (
    Button,
    ButtonSubSettings,
    load_internal_config,
    IngestSettings,
    NetworkSubSettings,
)

MAX_RECONNECT_ATTEMPTS: Final[int] = 5
RECONNECTION_DELAY_S: Final[int] = 2


class QueuePriority(Enum):
    reset = 1
    status = 5
    action = 10


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
    # action = button press, status = device connect/disconnect
    message_type: Literal["action", "status"]
    action: cfg.AllowedActions | None
    timestamp_ms: int
    status: (
        Literal["connected", "disconnected", "dead"] | None
    )  # dead = device failed permanently


@dataclass(order=False)  # Important: order=False prevents automatic comparison methods
class PrioritizedRequest:
    """Represents a prioritized request for the PriorityQueue."""

    # Priority level (lower number = higher priority)
    priority: int = field(compare=False)
    request_data: QueueData = field(compare=False)  # Actual request data

    # This method is what the PriorityQueue uses to compare two objects
    def __lt__(self, other: "PrioritizedRequest") -> bool:
        return self.priority < other.priority


@contextlib.asynccontextmanager
async def nats_init(network_settings: NetworkSubSettings) -> AsyncIterator[NATS]:
    """Async context manager to initialize and cleanup NATS connection."""
    nc: Optional[NATS] = None
    try:
        if network_settings.Use_tls:
            context: ssl.SSLContext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True
            context.load_verify_locations(cafile=network_settings.Ca_cert_path)
            # Load client certificate and private key
            context.load_cert_chain(
                certfile=network_settings.Client_cert_path,
                keyfile=network_settings.Client_key_path,
                password=None,
            )
            nc = await nats.connect(
                servers=f"tls://{network_settings.Nats_server}", tls=context
            )
        else:
            nc = await nats.connect(f"nats://{network_settings.Nats_server}")
        yield nc
    finally:
        if nc:
            await nc.flush()
            await nc.close()


@contextlib.asynccontextmanager
async def button_init(
    buttons_settings: ButtonSubSettings,
    debounce_ms: int,
) -> AsyncIterator[dict[str, ControlDevice]]:
    """Async context manager to initialize and cleanup button devices."""
    buttons: dict[str, ControlDevice] = {}
    try:
        for settings in buttons_settings.buttons:
            button = evdev.InputDevice(settings.device_path)
            if settings.grab:
                try:
                    button.grab()
                except OSError as e:
                    button.close()
                    print(
                        f"Unable to grab {settings.device_path}, device unavailable: {e}"
                    )
                    raise
            buttons[settings.device_path] = ControlDevice(
                device=button, settings=settings, debounce_ms=debounce_ms
            )
        yield buttons
    finally:
        for device in buttons.values():
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
    key: evdev.KeyEvent = evdev.categorize(event)  # type: ignore
    if key.keycode and key.keycode not in allowed_keys:
        print(f"{path}: Ignored Non-configured key event: {event}")
        return False
    return True


async def reconnect_device(
    path: str, settings: Button, debounce_ms: int
) -> ControlDevice:
    """Attempt to reconnect to a disconnected device."""
    while True:
        try:
            print(f"Attempting to reconnect to device: {path}")
            new_device = evdev.InputDevice(path)
            if settings.grab:
                new_device.grab()
            print(f"Reconnected to device: {path}")
            return ControlDevice(
                device=new_device, settings=settings, debounce_ms=debounce_ms
            )
        except OSError as e:
            print(
                f"Connection failed for device {path}, retrying in {RECONNECTION_DELAY_S} seconds: {e}"
            )
            await asyncio.sleep(RECONNECTION_DELAY_S)


async def monitor_input_events(
    device: ControlDevice,
    device_list: dict[str, ControlDevice],
    output_queue: asyncio.PriorityQueue[PrioritizedRequest],
    device_lock: asyncio.Lock,
    reconnect_count: int,
) -> None:
    interface = device.device  # type: evdev.InputDevice
    time_stamp: int = 0  # Initial timestamp for debounce
    disconnected: bool = False
    try:
        output_queue.put_nowait(
            PrioritizedRequest(
                priority=QueuePriority.status.value,
                request_data=QueueData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
                    timestamp_ms=time_stamp_ms(),
                    status="connected",
                ),
            )
        )

        async for event in interface.async_read_loop():
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
            key: evdev.KeyEvent = evdev.categorize(event)  # type: ignore
            print(interface.path, key, sep=": ")
            key_action: Optional[cfg.AllowedActions] = device.settings.key.get(
                key.keycode  # type: ignore
            )
            if key_action:
                data = QueueData(
                    device_path=interface.path,
                    message_type="action",
                    action=key_action,
                    timestamp_ms=time_stamp_ms(),
                    status=None,
                )
                p_request = PrioritizedRequest(
                    priority=QueuePriority.action.value
                    if key_action == "reset"
                    else QueuePriority.reset.value,
                    request_data=data,
                )
                output_queue.put_nowait(p_request)
                print(f"Action for {key.keycode}: {key_action} sent to output queue.")
            else:
                print(f"No action configured for key: {key.keycode}")
    except asyncio.CancelledError:
        raise
    except OSError as e:
        print(f"Device {interface.path} disconnected, stopping listener: {e}")
        device.device.close()
        async with device_lock:
            device_list.pop(interface.path)  # remove closed device from list
            disconnected = True
        output_queue.put_nowait(
            PrioritizedRequest(
                priority=10,
                request_data=QueueData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
                    timestamp_ms=time_stamp_ms(),
                    status="disconnected",
                ),
            )
        )
    except Exception as e:
        print(f"Error in print_events for device {interface.path}: {e}")

    # If disconnected, attempt to reconnect and restart event listening with new device
    # Limits reconnection to MAX_RECONNECT_ATTEMPTS to prevent unbound recursions
    if reconnect_count >= MAX_RECONNECT_ATTEMPTS:
        print(f"Stopped monitoring device: {interface.path} device failed permanently.")
        output_queue.put_nowait(
            PrioritizedRequest(
                priority=10,
                request_data=QueueData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
                    timestamp_ms=time_stamp_ms(),
                    status="dead",
                ),
            )
        )
        return  # exit without reconnecting
    if disconnected:
        async with device_lock:
            device_list[interface.path] = await reconnect_device(
                interface.path, device.settings, device.debounce_ms
            )
        # Restart event listening
        asyncio.create_task(
            monitor_input_events(
                device_list[interface.path],
                device_list,
                output_queue,
                device_lock,
                reconnect_count + 1,
            )
        )


async def nats_task(nc: NATS, output_queue: asyncio.PriorityQueue[PrioritizedRequest]) -> None:
    """Consume events from the output_queue and publish them to NATS."""
    try:
        while True:
            item = await output_queue.get()
            try:
                # Publish the queued item to the INTERFACE subject.
                payload = str(item.request_data).encode("utf-8")
                await nc.publish("INTERFACE", payload)
            finally:
                output_queue.task_done()
    except asyncio.CancelledError:
        # Allow task to be cancelled cleanly during shutdown.
        return


async def async_loop(ingest_settings: IngestSettings) -> None:
    """Asyncio event loop for ingest role."""
    print("Ingest async loop started.")
    device_lock = asyncio.Lock()
    nats_queue: asyncio.PriorityQueue[PrioritizedRequest] = asyncio.PriorityQueue()

    # Initialize NATS connection and button devices
    async with (
        button_init(
            ingest_settings.Buttons, ingest_settings.Buttons.Debounce_ms
        ) as avatar_devices,
        nats_init(ingest_settings.Network) as nc,
    ):
        tasks = [
            asyncio.create_task(
                monitor_input_events(device, avatar_devices, nats_queue, device_lock, 0)
            )
            for device in avatar_devices.values()
        ]
        tasks.append(asyncio.create_task(nats_task(nc, nats_queue)))
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


    # Pass button presses to Nats server

    # Close NATS connection and cleanup on exit
    print("Ingest async loop completed.")
