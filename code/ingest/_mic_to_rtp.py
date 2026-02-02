"""
Captures microphone input and sends it as RTP packets.
It is expected that a media proxy (like MediaMtx) will be in front of this rtp stream to handle security and authorization
and relay to the appropriate destination.
"""

import asyncio
import sys
import socket
import time
from typing import Protocol

import numpy as np
import sounddevice as sd

from common.dataTypes import AsyncSlidingQueue, FrameData
from common.helpers import OpusEncoder, RTPPacketizer, OPUS_FRAME_SAMPLES


# Data structures and functions
class CallbackTimeInfo(Protocol):
    inputBufferAdcTime: float
    currentTime: float
    outputBufferDacTime: float


def _get_audio_devices(device_name: str, channel_count: int, input_device: bool) -> int:
    """Check for the specified audio device and return its ID. (-1 if not found)"""
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device_name in device["name"]:
            try:
                if input_device:
                    sd.check_input_settings(device=idx, channels=channel_count)
                else:
                    sd.check_output_settings(device=idx, channels=channel_count)
            except sd.PortAudioError as e:
                raise RuntimeError(f"Error checking device '{device_name}': error {e}.")
            return idx
    return -1  # Device not found


async def mic_to_queue(
    mic_name: str,
    channel_count: int,
    output_queue: AsyncSlidingQueue,
    max_reconnect_attempts: int,
    reconnection_delay_s: float,
    exit_event: asyncio.Event,
) -> None:
    """Capture audio from the specified microphone and send it to the output queue."""
    XRUN_RESTART_THRESHOLD: int = 5  # Number of consecutive xruns to trigger a stream restart
    device_id = _get_audio_devices(mic_name, channel_count, input_device=True)
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
            xruns_healthy
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
                np_data_type=str(indata.dtype),
            )
            loop.call_soon_threadsafe(output_queue.put_nowait, frame_data)

    while not exit_event.is_set() and reconnection_attempts < max_reconnect_attempts:
        try:
            with sd.InputStream(
                device=device_id,
                channels=channel_count,
                callback=callback,
                dtype=np.int16,
                blocksize=OPUS_FRAME_SAMPLES,
            ):
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


async def middleware_converter(
    input_queue: AsyncSlidingQueue,
    output_queue: AsyncSlidingQueue,
    exit_event: asyncio.Event,
    mic_name: str,
    channels: int,
) -> None:
    """Middleware function to convert audio frames from input queue and put them into output queue."""

    mic_id = _get_audio_devices(mic_name, channels, input_device=True)
    if mic_id == -1:
        raise RuntimeError(f"Microphone device '{mic_name}' not found.")
    sample_rate = int(sd.query_devices(mic_id)["default_samplerate"])

    encoder = OpusEncoder(sample_rate=sample_rate, channels=channels)
    packetizer = RTPPacketizer(sample_rate=sample_rate, payload_type=111)
    print("Middleware converter started.")
    while not exit_event.is_set():
        frame_data = await input_queue.get()
        # Encode the PCM data to Opus
        opus_payload = encoder.encode(frame_data.data)
        # Build RTP packet
        rtp_packet = packetizer.build(opus_payload, OPUS_FRAME_SAMPLES)
        await output_queue.put(rtp_packet)
    print("Middleware converter stopped.")


async def queue_to_rtp_sender(
    input_queue: AsyncSlidingQueue, destination: str, port: int, exit_event: asyncio.Event
) -> None:
    """Send RTP packets from the input queue to the destination over UDP."""
    print("RTP sender started.")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while not exit_event.is_set():
            packet = await input_queue.get()
            sock.sendto(packet, (destination, port))
    print("RTP sender stopped.")
