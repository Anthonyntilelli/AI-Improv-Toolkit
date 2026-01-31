"""Button input device handling using evdev library."""

# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

import asyncio
import contextlib
import time
from typing import NamedTuple, AsyncIterator
import pydantic

import evdev

from common.dataTypes import ButtonActions


from ._config import ButtonConfig, KeyOptions
from common.nats import ButtonData


class Button(NamedTuple):
    """Represents a button with its evdev device and settings."""

    device: evdev.InputDevice
    settings: ButtonConfig
    debounce_ms: int


@contextlib.asynccontextmanager
async def button_init(buttons_settings: list[ButtonConfig], debounce_ms: int) -> AsyncIterator[dict[str, Button]]:
    """Async context manager to initialize and cleanup buttons."""
    button_dict: dict[str, Button] = {}
    print("Initializing button devices...")
    try:
        for button in buttons_settings:
            device = evdev.InputDevice(button.path)
            if button.grab:
                try:
                    device.grab()
                except OSError as e:
                    device.close()
                    raise RuntimeError(f"Unable to grab {button.path}, device unavailable: {e}") from e
            button_dict[button.path] = Button(device=device, settings=button, debounce_ms=debounce_ms)
        yield button_dict
    finally:
        print("Cleaning up button devices...")
        if len(button_dict) != 0:
            for button in button_dict.values():
                print(f"Cleaning up device: {button.settings.path}")
                try:
                    if button.settings.grab:
                        button.device.ungrab()
                except OSError as e:
                    print(f"Unable to ungrab {button.settings.path}, device unavailable: {e}")
                finally:
                    with contextlib.suppress(OSError):
                        button.device.close()


def time_stamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return round(time.time() * 1000)


def return_allowed_keys(event: evdev.InputEvent, path: str, allowed_keys: list[KeyOptions]) -> KeyOptions | None:
    """Filter to allow only key events, return key if allowed or None."""
    key_event = evdev.categorize(event)
    if not isinstance(key_event, evdev.KeyEvent):
        print(f"{path}: Ignored non-key event after categorization: {event}")
        return None
    if key_event.keystate != evdev.KeyEvent.key_down:
        print(f"{path}: Ignored key event that is not key down: {event}")
        return None
    # Filter only allowed keys
    if key_event.keycode and key_event.keycode not in allowed_keys:
        print(f"{path}: Ignored Non-configured key event: {event}")
        return None
    print(f"{path}: Allowed key event: {key_event.keycode}")
    return key_event.keycode  # type: ignore


async def reconnect_device(settings: ButtonConfig, debounce_ms: int, reconnection_delay_s: int) -> Button:
    """Attempt to reconnect to a disconnected device."""
    while True:
        try:
            print(f"Attempting to reconnect to device: {settings.path}")
            new_device = evdev.InputDevice(settings.path)
            if settings.grab:
                new_device.grab()
            print(f"Reconnected to device: {settings.path}")
            return Button(device=new_device, settings=settings, debounce_ms=debounce_ms)
        except OSError as e:
            print(f"Connection failed for device {settings.path}, retrying in {reconnection_delay_s} seconds: {e}")
            await asyncio.sleep(reconnection_delay_s)


async def monitor_input_event(
    device: Button,
    device_list: dict[str, Button],
    output_queue: asyncio.Queue[str],
    device_lock: asyncio.Lock,
    reconnect_attempts_max: int,
    reconnection_delay_s: int,
    reconnect_count: int,
) -> None:
    """Monitor input events from a button device and send to output queue."""
    print(f"Started monitoring device for actor {device.settings.avatar_id} at path: {device.device.path}")
    time_stamp: int = 0  # Initial timestamp for debounce
    disconnected: bool = False
    try:
        button_connected_event = ButtonData(
            avatar_id=device.settings.avatar_id,
            message_type="status",
            action=None,
            status="connected",
        )
        dumped_event = button_connected_event.model_dump_json()
        output_queue.put_nowait(dumped_event)
        print(f"Sent connected status for device {device.device.path} to output queue.")

        async for event in device.device.async_read_loop():
            # Skip non-key events or non-configured keys
            key = return_allowed_keys(event, device.device.path, list(device.settings.keys.keys()))
            if not key:
                continue
            # Debounce logic
            if (time_stamp + device.debounce_ms) > time_stamp_ms():
                print(f"{device.device.path}: Button press ignored due to debounce.")
                continue

            time_stamp = time_stamp_ms()
            print(f"Button pressed. {device.device.path}: {key}")
            key_action: ButtonActions = device.settings.keys.get(key, "unset")

            if key_action == "unset":
                print(f"{device.device.path}: Key {key} has no assigned action, ignoring.")
                continue
            button_event = ButtonData(
                avatar_id=device.settings.avatar_id,
                message_type="action",
                action=key_action,
                status=None,
            )
            dumped_event = button_event.model_dump_json()
            output_queue.put_nowait(dumped_event)
            print(f"Action for {key}: {key_action} sent to output queue.")
    except asyncio.CancelledError:
        raise
    except pydantic.ValidationError as e:
        print(f"Validation error in button event data for device {device.device.path}: {e}")
    except OSError as e:
        print(f"Device {device.device.path} disconnected, stopping listener: {e}")
        device.device.close()
        async with device_lock:
            device_list.pop(device.device.path)  # remove closed device from list
            disconnected = True
        button_event = ButtonData(
            avatar_id=device.settings.avatar_id, message_type="status", action=None, status="disconnected"
        )
        dumped_event = button_event.model_dump_json()
        output_queue.put_nowait(dumped_event)
    except Exception as e:
        print(f"Error in print_events for device {device.device.path}: {e}")

    # If disconnected, attempt to reconnect and restart event listening with new device
    # Limits reconnection to reconnect_attempts_max to prevent unbound recursions
    if reconnect_count >= reconnect_attempts_max:
        print(f"Stopped monitoring device: {device.device.path} device failed permanently.")
        button_event = ButtonData(
            avatar_id=device.settings.avatar_id, message_type="status", action=None, status="dead"
        )
        dumped_event = button_event.model_dump_json()
        output_queue.put_nowait(dumped_event)
        return  # exit without reconnecting
    if disconnected:
        async with device_lock:
            device_list[device.device.path] = await reconnect_device(
                device.settings, device.debounce_ms, reconnection_delay_s
            )
        # Restart event listening
        asyncio.create_task(
            monitor_input_event(
                device_list[device.device.path],
                device_list,
                output_queue,
                device_lock,
                reconnect_attempts_max,
                reconnection_delay_s,
                reconnect_count + 1,
            )
        )
