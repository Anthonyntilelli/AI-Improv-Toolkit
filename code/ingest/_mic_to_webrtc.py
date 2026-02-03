"""
Captures microphone input and sends it as RTP packets.
It is expected that a media proxy (like MediaMtx) will be in front of this rtp stream to handle security and authorization
and relay to the appropriate destination.
"""

import asyncio
import time
from typing import Protocol, Optional

import aiortc
import av
import numpy as np
import sounddevice as sd

from common.dataTypes import AsyncSlidingQueue, AudioFrameSettings, FrameData


assert aiortc  # for mypy type checking
assert av  # for mypy type checking


# Constants
WEBRTC_SETTINGS = AudioFrameSettings(
    samplerate=48000,
    channels=1,
    blocksize=960,
    dtype=np.dtype(np.float32).name,
)


# Data structures and functions
class CallbackTimeInfo(Protocol):  # Protocol for sounddevice callback time info
    inputBufferAdcTime: float
    currentTime: float
    outputBufferDacTime: float


async def mic_to_queue(
    mic_name: str,
    output_queue: AsyncSlidingQueue,
    max_reconnect_attempts: int,
    exit_event: asyncio.Event,
) -> None:
    """Capture audio from the specified microphone and send it to the output queue."""

    class AudioCallback:
        """Audio callback for sounddevice InputStream. Handles audio data and xrun monitoring."""

        def __init__(
            self, loop: asyncio.AbstractEventLoop, output_queue: AsyncSlidingQueue, device_settings: AudioFrameSettings
        ) -> None:
            """Initialize the audio callback with loop, output queue, and device settings."""

            self._stream_heart_beat: float = time.monotonic()
            self._loop = loop
            self._xruns_total: int = 0
            self._xruns_consecutive: int = 0
            self._XRUN_RESTART_THRESHOLD: int = 5  # Number of consecutive xruns
            self._HEART_BEAT_TIMEOUT_S: float = 3.0  # Seconds without heartbeat to consider stream unhealthy
            self._output_queue = output_queue
            self._device_settings = device_settings

        def __call__(
            self, indata: np.ndarray, frames: int, callback_time: CallbackTimeInfo, status: sd.CallbackFlags
        ) -> None:
            """Handle incoming audio data and monitor for xruns."""
            self.update_heartbeat()
            if status and (status.input_overflow or status.output_underflow):
                self.increment_xruns()
                print(f"xrun detected: total={self._xruns_total} consecutive={self._xruns_consecutive}")
            else:  # reset consecutive xrun counter
                self.reset_xruns()
                frame_data = FrameData(
                    data=indata.copy(),  # Ensure data is copied to avoid issues with the buffer being reused
                    settings=self._device_settings,
                )
                self._loop.call_soon_threadsafe(self._output_queue.put_nowait, frame_data)

        def is_stream_healthy(self) -> bool:
            """Check if the stream is healthy based on xruns and heartbeat."""
            if self._xruns_consecutive >= self._XRUN_RESTART_THRESHOLD:
                print(
                    f"Stream is Unhealthy: total xruns={self._xruns_total}, consecutive xruns={self._xruns_consecutive}, threshold={self._XRUN_RESTART_THRESHOLD}"
                )
                return False
            if self._stream_heart_beat + self._HEART_BEAT_TIMEOUT_S < time.monotonic():  # 3 seconds without heartbeat
                print(
                    f"Stream is Unhealthy based on heartbeat: last heartbeat={self._stream_heart_beat}, current time={time.monotonic()}"
                )
                return False
            return True

        def update_heartbeat(self) -> None:
            """Update the heartbeat timestamp to the current time."""
            self._stream_heart_beat = time.monotonic()

        def reset_xruns(self) -> None:
            """Reset the consecutive xrun counter."""
            self._xruns_consecutive = 0

        def increment_xruns(self) -> None:
            """Increment the total and consecutive xrun counters."""
            self._xruns_total += 1
            self._xruns_consecutive += 1

        def reset_stream(self) -> None:
            """Reset the stream health monitoring counters."""
            self.reset_xruns()
            self.update_heartbeat()

    def _get_audio_input(device_name: str) -> tuple[int, Optional[AudioFrameSettings]]:
        """Check for the specified audio device and return its ID (check microphone with default settings)"""
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device_name in device["name"]:
                try:
                    sd.check_input_settings(device=idx)
                    device_settings = AudioFrameSettings(
                        samplerate=int(device["default_samplerate"]),
                        channels=device["max_input_channels"],
                        blocksize=0,  # Use default blocksize
                        dtype=np.dtype(np.float32).name,  # Use float32 for compatibility
                    )
                    print(f"Found device '{device_name}' (ID: {idx}) with default settings")
                    return idx, device_settings
                except sd.PortAudioError as e:
                    print(f"Found device '{device_name}' (ID: {idx}) but cannot open with default settings: {e}")
        return -1, None  # Device not found

    loop = asyncio.get_running_loop()
    reconnection_attempts: int = 0
    device_id, device_settings = _get_audio_input(mic_name)
    if device_id == -1 or device_settings is None:
        raise RuntimeError(f"Microphone device '{mic_name}' not found.")

    await asyncio.sleep(1)  # Initial delay before starting (allow other tasks to initialize)

    callback = AudioCallback(loop, output_queue, device_settings)
    while not exit_event.is_set() and reconnection_attempts < max_reconnect_attempts:
        try:
            callback.reset_stream()
            with sd.InputStream(device=device_id, callback=callback, dtype=np.float32):
                print(f"Started capturing audio from microphone '{mic_name}'.")
                reconnection_attempts = 0  # Reset on successful start
                while not exit_event.is_set():
                    await asyncio.sleep(0.5)  # Keep the stream alive
                    if not callback.is_stream_healthy():
                        print(f"Restarting audio stream for microphone '{mic_name}' due to unhealthy stream.")
                        break
        except Exception as e:
            print(
                f"Error capturing audio from microphone '{mic_name}', reconnection attempts left {max_reconnect_attempts - reconnection_attempts}: {e}"
            )
            reconnection_attempts += 1
        await asyncio.sleep(0.5)  # Small delay before restarting the stream
    if reconnection_attempts >= max_reconnect_attempts:
        raise RuntimeError(
            f"Failed to capture audio from microphone '{mic_name}' after {max_reconnect_attempts} attempts."
        )
    print(f"Stopped capturing audio from microphone '{mic_name}'.")


async def prep_frame_for_webRTC(
    input_queue: AsyncSlidingQueue,
    output_queue: AsyncSlidingQueue,
    exit_event: asyncio.Event,
) -> None:
    """Convert microphone frames to WebRTC compatible frames."""
    # TODO: Buffer frame into correct blocksize
    # If the mic frame size is different from WEBRTC_SETTINGS.blocksize, implement buffering logic here.

    # TODO: If the mic frame dtype is different from WEBRTC_SETTINGS.dtype, implement conversion logic here.
    # Handle Clipping/normalization: if converting from int to float, normalize; if converting from float to int, clip.

    # TODO: If mic is not mono, implement downmixing logic here.

    # TODO: Implement the conversion to av.AudioFrame

    # TODO: Resample if necessary

    # TODO: Check frame blocksize and pad or trim as needed with buffering logic

    # Finally, put the converted frame into the output queue
    pass
