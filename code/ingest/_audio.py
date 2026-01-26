from typing import Protocol

import sounddevice as sd
import numpy as np  # noqa: F401  # Required for type hints and sounddevice's NumPy-backed buffers

from ._config import IngestSettings


class CallbackTimeInfo(Protocol):
    inputBufferAdcTime: float
    currentTime: float
    outputBufferDacTime: float


def callback(
    indata: np.ndarray,
    outdata: np.ndarray,
    frames: int,
    time: CallbackTimeInfo,
    status: sd.CallbackFlags,
) -> None:
    """Audio callback function to process input and output audio data."""
    if status:
        print("Callback status:", status)
    outdata[:] = indata


def callback_finished():
    print("Stream finished")


def device_name_to_id(device_name: str) -> int:
    """Convert a device name to its corresponding device ID."""
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device_name in device["name"]:
            return idx
    raise ValueError(f"Device name '{device_name}' not found among available devices.")


def record_and_forward(config: IngestSettings) -> None:
    """Records audio from the configured input device and forwards it to the defined output device."""
    input_device_id = device_name_to_id(config.ActorMics[0].Mic_name)
    output_device_id = sd.default.device[1]  # Default output device
    with sd.Stream(
        device=(input_device_id, output_device_id),
        samplerate=config.ActorMics[0].Sample_rate,
        channels=1,  # Assuming mono input (MVP)
        callback=callback,
        finished_callback=callback_finished,
    ):
        print("#" * 80)
        print("Recording and forwarding audio. Press Return to quit.")
        print("#" * 80)
        input()
        sd.wait()  # Wait until stream is finished
