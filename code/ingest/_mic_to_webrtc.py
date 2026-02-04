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
# from av.audio.resampler import AudioResampler
import numpy as np
import sounddevice as sd

from common.dataTypes import AsyncSlidingQueue, AudioFrameSettings #, FrameData


assert aiortc  # for mypy type checking
assert av  # for mypy type checking


# # Constants
# WEBRTC_SETTINGS = AudioFrameSettings(
#     samplerate=48000,
#     channels=1,
#     blocksize=960,
#     dtype=np.dtype(np.float32).name,
# )


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
                self._loop.call_soon_threadsafe(self._output_queue.put_nowait, self.create_av_frame(indata))

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

        def create_av_frame(self, frame: np.ndarray) -> av.AudioFrame:
            """
            Creates an audio frame from a sounddevice frame with given settings.
            Expects a numpy array of float32 and mono or stereo samples.
            Can also do
            """

            # Transpose to (channels, frames) for av.AudioFrame compatibility
            if frame.ndim == 2:
                frame = frame.T  # (frames, channels) -> (channels, frames)
            elif frame.ndim == 1:
                frame = frame.reshape(1, -1)  # mono, ensure (1, frames)
            audio_frame = av.AudioFrame.from_ndarray(
                frame,
                format='flt',
                layout='mono' if self._device_settings.channels == 1 else 'stereo'
            )
            audio_frame.sample_rate = self._device_settings.samplerate
            return audio_frame


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


async def queue_to_speaker(
    input_queue: AsyncSlidingQueue,
    speaker_name: str,
    exit_event: asyncio.Event,
) -> None:
    """Play audio frames from the input queue to the specified speaker."""

    def _get_audio_output(device_name: str) -> int:
        """Check for the specified audio output device and return its ID."""
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device_name in device["name"]:
                try:
                    sd.check_output_settings(device=idx)
                    print(f"Found output device '{device_name}' (ID: {idx})")
                    return idx
                except sd.PortAudioError as e:
                    print(f"Found output device '{device_name}' (ID: {idx}) but cannot open with default settings: {e}")
        return -1  # Device not found

    device_id = _get_audio_output(speaker_name)
    if device_id == -1:
        raise RuntimeError(f"Speaker device '{speaker_name}' not found.")

    with sd.OutputStream(device=device_id, dtype=np.float32) as stream:
        print(f"Started playing audio to speaker '{speaker_name}'.")
        while not exit_event.is_set():
            frame: av.AudioFrame = await input_queue.get()
            # Convert av.AudioFrame to numpy array
            frame_data = frame.to_ndarray()
            # Transpose back to (frames, channels) for sounddevice
            if frame_data.ndim == 2:
                frame_data = frame_data.T  # (channels, frames) -> (frames, channels)
                # Ensure frame_data matches stream.channels
                expected_channels = stream.channels
                actual_channels = frame_data.shape[1] if frame_data.ndim == 2 else 1
                if actual_channels != expected_channels:
                    # Downmix or duplicate channels as needed
                    if actual_channels > expected_channels:
                        # Downmix by averaging extra channels
                        frame_data = frame_data[:, :expected_channels]
                        if frame_data.shape[1] != expected_channels:
                            # If still mismatched, average across all channels
                            frame_data = np.mean(frame_data, axis=1, keepdims=True)
                            frame_data = np.repeat(frame_data, expected_channels, axis=1)
                    else:
                        # Duplicate channels to match expected
                        frame_data = np.repeat(frame_data, expected_channels, axis=1)
            stream.write(frame_data)
    print(f"Stopped playing audio to speaker '{speaker_name}'.")

# async def prep_frame_for_webRTC(
#     input_queue: AsyncSlidingQueue,
#     output_queue: AsyncSlidingQueue,
#     exit_event: asyncio.Event,
# ) -> None:
#     """Convert microphone frames to WebRTC compatible frames."""

#     # TODO: Buffer frame into correct blocksize
#     # If the mic frame size is different from WEBRTC_SETTINGS.blocksize, implement buffering logic here.
#     resampler = AudioResampler(format='flt', layout='mono', rate=WEBRTC_SETTINGS.samplerate)

#     def downmix_to_mono(frame: np.ndarray, num_channels: int) -> np.ndarray:
#         """
#         Downmix multi-channel audio frame to mono by averaging channels.
#         Handles both interleaved (1D) and non-interleaved (2D) arrays.
#         """
#         if num_channels == 1:
#             return frame
#         if frame.ndim == 1:
#             # Interleaved: reshape to (samples, channels)
#             frame = frame.reshape(-1, num_channels)
#         # Now frame is (samples, channels)
#         return np.mean(frame, axis=1, keepdims=True)

#     def convert_to_float32(frame: np.ndarray, dtype: str) -> np.ndarray:
#         """Convert audio frame to float32 format."""
#         if frame.dtype != np.float32:
#             if np.issubdtype(frame.dtype, np.integer):
#                 info = np.iinfo(frame.dtype)
#                 frame = frame.astype(np.float32) / info.max
#             else:
#                 frame = frame.astype(np.float32)
#         return frame

#     def create_av_frame(frame: np.ndarray, sample_rate: int) -> av.AudioFrame:
#         """Creates an audio frame from a sounddevice frame with given settings."""
#         # Transpose to (channels, frames) for av.AudioFrame compatibility
#         if frame.ndim == 2:
#             frame = frame.T  # (frames, channels) -> (channels, frames)
#         elif frame.ndim == 1:
#             frame = frame.reshape(1, -1)  # mono, ensure (1, frames)
#         audio_frame = av.AudioFrame.from_ndarray(frame, format='flt', layout='mono')
#         audio_frame.sample_rate = sample_rate
#         return audio_frame

#     def resample_frame(frame: Optional[av.AudioFrame]) -> list[av.AudioFrame]:
#         """
#         Resample an av.AudioFrame to WebRTC settings.
#         Set frame to None to flush the resampler.
#         """
#         resampled = resampler.resample(frame)
#         return resampled


#     # Finally, put the converted frame into the output queue
#     print("prep_frame_for_webRTC loop started.")
#     while not exit_event.is_set():
#         frame_data: FrameData = await input_queue.get()
#         data = frame_data.data
#         pre_settings = frame_data.settings
#         if not isinstance(pre_settings, AudioFrameSettings):
#             print("Invalid frame settings, skipping frame.")
#             continue  # Skip if settings are missing

#         # Downmix to mono if needed
#         if pre_settings.channels > 1:
#             data = downmix_to_mono(data, pre_settings.channels)

#         # Convert to float32 if needed
#         if pre_settings.dtype != WEBRTC_SETTINGS.dtype:
#           data = convert_to_float32(data, WEBRTC_SETTINGS.dtype)

#         # Create av.AudioFrame
#         converted_frame = create_av_frame(data, pre_settings.samplerate)

#     # TODO: Handle flushing the resampler on exit if needed
#     # TODO  Implement buffering logic for blocksize alignment if needed

#     # Resample to WebRTC settings
#         resampled_frames = resample_frame(converted_frame)
#         for converted_frame in resampled_frames:
#             await output_queue.put(converted_frame)

#     print("prep_frame_for_webRTC loop completed.")
