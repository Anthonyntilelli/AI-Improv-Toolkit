"""
Captures microphone input and sends it as RTP packets.
It is expected that a media proxy (like MediaMtx) will be in front of this rtp stream to handle security and authorization
and relay to the appropriate destination.
"""

import asyncio
import sys
import time
from typing import Protocol, Optional

import aiortc
import av
import numpy as np
import sounddevice as sd

from common.dataTypes import AsyncSlidingQueue, AudioFrameSettings, FrameData


# Constants
WEBRTC_SETTINGS = AudioFrameSettings(
    samplerate=48000,
    channels=1,
    blocksize=960,
    dtype=np.dtype(np.float32).name,
)


# Data structures and functions
class CallbackTimeInfo(Protocol):
    inputBufferAdcTime: float
    currentTime: float
    outputBufferDacTime: float


def _get_audio_input(device_name: str) -> tuple[int, Optional[AudioFrameSettings]]:
    """Check for the specified audio device and return its ID and audio frame settings. (-1 if not found)"""
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device_name in device["name"]:
            try:
                sd.check_input_settings(
                    device=idx,
                    channels=WEBRTC_SETTINGS.channels,
                    samplerate=WEBRTC_SETTINGS.samplerate,
                    dtype=WEBRTC_SETTINGS.dtype
                )
                print(f"Found device '{device_name}' (ID: {idx}) with webrtc settings")
                return idx, WEBRTC_SETTINGS
            except sd.PortAudioError as e:
                print(f"Found device '{device_name}' (ID: {idx}) but cannot open with webrtc settings: {e}")
                try:
                    sd.check_input_settings(device=idx,channels=WEBRTC_SETTINGS.channels,dtype=WEBRTC_SETTINGS.dtype)
                    adjusted_settings = AudioFrameSettings(
                        blocksize=WEBRTC_SETTINGS.blocksize,
                        channels=WEBRTC_SETTINGS.channels,
                        samplerate=device["default_samplerate"],
                        dtype=WEBRTC_SETTINGS.dtype
                    )
                    print(f"Using adjusted samplerate {adjusted_settings.samplerate} Hz for device '{device_name}'")
                    return idx, adjusted_settings
                except sd.PortAudioError as e2:
                    print(f"Cannot open device '{device_name}' with adjusted settings: {e2}")

    return -1, None  # Device not found


async def mic_to_queue(
    mic_name: str,
    output_queue: AsyncSlidingQueue,
    max_reconnect_attempts: int,
    reconnection_delay_s: float,
    exit_event: asyncio.Event,
) -> None:
    """Capture audio from the specified microphone and send it to the output queue."""
    XRUN_RESTART_THRESHOLD: int = 5  # Number of consecutive xruns to trigger a stream restart
    device_id, device_settings = _get_audio_input(mic_name)
    if device_id == -1:
        raise RuntimeError(f"Microphone device '{mic_name}' not found.")

    stream_heart_beat: float = time.monotonic()
    loop = asyncio.get_running_loop()
    reconnection_attempts: int = 0
    xruns_total: int = 0
    xruns_consecutive: int = 0
    xruns_healthy: bool = True

    await asyncio.sleep(1)  # Initial delay before starting (allow other tasks to initialize)

    def callback(indata: np.ndarray, frames: int, callback_time: CallbackTimeInfo, status: sd.CallbackFlags) -> None:
        nonlocal \
            output_queue, \
            loop, \
            stream_heart_beat, \
            xruns_total, \
            xruns_consecutive, \
            XRUN_RESTART_THRESHOLD, \
            xruns_healthy, \
            device_settings
        if device_settings is None:
            raise RuntimeError("Device settings not initialized in callback.") # Should not happen
        stream_heart_beat = time.monotonic()  # Update heartbeat to indicate stream is active
        if status and (status.input_overflow or status.output_underflow):
            xruns_total += 1
            xruns_consecutive += 1
            print(f"xrun detected: total={xruns_total} consecutive={xruns_consecutive}")
            if xruns_consecutive >= XRUN_RESTART_THRESHOLD:
                print("xrun threshold reached; restarting stream")
                xruns_healthy = False
        else:  # reset consecutive xrun counter
            xruns_consecutive = 0
            frame_data = FrameData(
                data=indata.copy(),  # Ensure data is copied to avoid issues with the buffer being reused
                settings=device_settings,
            )
            loop.call_soon_threadsafe(output_queue.put_nowait, frame_data)

    if device_settings is None:
        raise RuntimeError(f"Device settings could not be determined for microphone '{mic_name}'.") # Should not happen
    while not exit_event.is_set() and reconnection_attempts < max_reconnect_attempts:
        try:
            with sd.InputStream(device=device_id, channels=device_settings.channels, callback=callback, dtype=device_settings.dtype, samplerate=device_settings.samplerate):
                print(f"Started capturing audio from microphone '{mic_name}'.")
                while not exit_event.is_set():
                    await asyncio.sleep(0.5)  # Keep the stream alive
                    if not xruns_healthy:
                        print(f"Restarting audio stream for microphone '{mic_name}' due to excessive xruns.")
                        xruns_healthy = True
                        break
                    # Monitor stream heartbeat
                    if time.monotonic() - stream_heart_beat > reconnection_delay_s:
                        print(
                            f"Warning: No audio callback received for microphone '{mic_name}' in the last {reconnection_delay_s} seconds, restarting stream",
                            file=sys.stderr,
                        )
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
    input_queue: "AsyncSlidingQueue",
    output_queue: "AsyncSlidingQueue",
    exit_event: asyncio.Event,
) -> None:

    def convert_audio_to_webrtc_frame(frame_data: FrameData) -> av.AudioFrame:
        """Convert SoundDevice frame to WebRTC compatible av.AudioFrame."""

        dtype_to_format = {
            "float32": "flt32",
            "int16": "s16",
            "int32": "s32",
            "uint8": "u8",
        }
        np_dtype_name = str(frame_data.data.dtype)
        av_format = dtype_to_format.get(np_dtype_name)
        if av_format is None:
            raise ValueError(f"Unsupported audio dtype: {np_dtype_name}")
        audio_frame = av.AudioFrame.from_ndarray(
            frame_data.data,
            format=av_format,
            layout="mono" if frame_data.settings.channels == 1 else "stereo"
        )
        audio_frame.sample_rate = frame_data.settings.samplerate
        return audio_frame

    while not exit_event.is_set():
        frame_data = await input_queue.get()
        webrtc_frame = convert_audio_to_webrtc_frame(frame_data)
        await output_queue.put(webrtc_frame)
