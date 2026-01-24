"""
Ingest role module.
Use the start function to start the ingest process.
"""
# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
import contextlib
import time
from typing import Final, NamedTuple, AsyncIterator, Optional
import evdev

import common.config as cfg
import common.nats as nats
from ._config import Button, ButtonSubSettings


MAX_RECONNECT_ATTEMPTS: Final[int] = 5
RECONNECTION_DELAY_S: Final[int] = 2


class ControlDevice(NamedTuple):
    """Represents an avatar device with its evdev device and settings."""

    device: evdev.InputDevice
    settings: Button
    debounce_ms: int


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
    output_queue: asyncio.PriorityQueue[nats.QueueRequest],
    device_lock: asyncio.Lock,
    reconnect_count: int,
) -> None:
    interface = device.device  # type: evdev.InputDevice
    time_stamp: int = 0  # Initial timestamp for debounce
    disconnected: bool = False
    try:
        output_queue.put_nowait(
            nats.QueueRequest(
                priority=nats.QueuePriority.Medium.value,
                request_data=nats.ButtonData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
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
                data = nats.ButtonData(
                    device_path=interface.path,
                    message_type="action",
                    action=key_action,
                    status=None,
                )
                p_request = nats.QueueRequest(
                    priority=nats.QueuePriority.High.value
                    if key_action == "reset"
                    else nats.QueuePriority.Standard.value,
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
            nats.QueueRequest(
                priority=nats.QueuePriority.High.value,
                request_data=nats.ButtonData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
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
            nats.QueueRequest(
                priority=nats.QueuePriority.High.value,
                request_data=nats.ButtonData(
                    device_path=interface.path,
                    message_type="status",
                    action=None,
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
