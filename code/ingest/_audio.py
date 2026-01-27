import time
from typing import Final, NamedTuple, Protocol

import sounddevice as sd
import numpy as np  # noqa: F401  # Required for type hints and sounddevice's NumPy-backed buffers

from ._config import AudioDataType, IngestSettings
from common.dataTypes import SlidingQueue, AudioQueueData, EMPTY


class DeviceInformation(NamedTuple):
    device_id: int
    sample_rate: float
    dtype: AudioDataType  # preferred for whisper 'int16'
    resample_required: bool


RECONNECT_TIMEOUT_SECONDS: Final[int] = 2
MAX_DEVICE_CHECKS: Final[int] = 5
XRUN_RESTART_THRESHOLD: Final[int] = 3


class CallbackTimeInfo(Protocol):
    inputBufferAdcTime: float
    currentTime: float
    outputBufferDacTime: float


class RestartStreamException(Exception):
    """Exception to indicate that the audio stream should be restarted."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def set_up_audio_devices(
    device_name: str,
    default_sample_rate: float,
    default_data_type: AudioDataType,
    input_device: bool,
) -> DeviceInformation:
    """Find the device ID and sample rate for the given device name, attempts default_sample_rate first."""
    devices = sd.query_devices()
    id: int = -1
    rate: float = -1.0
    resample_required: bool = False
    for idx, device in enumerate(devices):
        if device_name in device["name"]:
            id = idx
            try:
                if input_device:
                    sd.check_input_settings(
                        device=id,
                        samplerate=default_sample_rate,
                        channels=1,
                        dtype=default_data_type,
                    )
                else:
                    sd.check_output_settings(
                        device=id,
                        samplerate=default_sample_rate,
                        channels=1,
                        dtype=default_data_type,
                    )
                rate = default_sample_rate
            except sd.PortAudioError:
                print(
                    f"Device '{device_name}' does not support the default sample rate of {default_sample_rate} Hz. Using device's default sample rate of {device['default_samplerate']} Hz instead."
                )
                print("Resampling will be required.")
                rate = device["default_samplerate"]
                resample_required = True
            return DeviceInformation(
                device_id=id,
                sample_rate=rate,
                dtype=default_data_type,
                resample_required=resample_required,
            )
    raise ValueError(f"Input device '{device_name}' not found among available devices.")


def stream_audio_to_queue(
    config: IngestSettings, output_queue: SlidingQueue[AudioQueueData]
) -> None:
    """Records audio from the configured input device and forwards it to the defined output device."""

    stream_heart_beat: float = time.monotonic()
    xruns_total: int = 0
    xruns_consecutive: int = 0
    device_checks: int = 0

    def callback(
        indata: np.ndarray,
        frames: int,
        call_back_time: CallbackTimeInfo,
        status: sd.CallbackFlags,
    ) -> None:
        """Audio callback function to process input and output audio data."""
        nonlocal stream_heart_beat, xruns_total, xruns_consecutive
        if status and (status.input_overflow or status.output_underflow):
            xruns_total += 1
            xruns_consecutive += 1
            print(f"xrun detected: total={xruns_total} consecutive={xruns_consecutive}")
            if xruns_consecutive >= XRUN_RESTART_THRESHOLD:
                print("xrun threshold reached; restarting stream")
                raise RestartStreamException("xrun threshold reached")
        else:  # reset consecutive xrun counter
            xruns_consecutive = 0
        stream_heart_beat = time.monotonic()
        # Forward the audio data to the output queue
        output_queue.put(
            AudioQueueData(
                pcm_bytes=indata.tobytes(),
                timestamp_monotonic=call_back_time.currentTime,
                sample_rate=config.Audio.Sample_rate,
            )
        )

    while True:
        try:
            input_device = set_up_audio_devices(
                config.ActorMics[0].Mic_name,
                config.Audio.Sample_rate,
                config.Audio.Dtype,
                True,
            )
            device_checks = 0  # Reset device checks on successful setup
            with sd.InputStream(
                device=input_device.device_id,
                samplerate=input_device.sample_rate,
                channels=1,  # Assuming mono input (MVP only)
                callback=callback,
                dtype=input_device.dtype,
            ) as input_stream:
                print("Recording...")
                while input_stream.active:
                    sd.sleep(2000)
                    if time.monotonic() - stream_heart_beat > 2.0:
                        print("No audio callbacks received; restarting stream.")
                        raise RestartStreamException("No audio callbacks received")

        except ValueError as e:
            if device_checks >= MAX_DEVICE_CHECKS:
                raise RuntimeError(
                    f"Maximum device check attempts ({MAX_DEVICE_CHECKS}) reached. Exiting audio stream."
                )
            print(f"Error when trying to set up audio device, trying to reconnect: {e}")
            device_checks += 1
            time.sleep(RECONNECT_TIMEOUT_SECONDS)
        except sd.PortAudioError as e:
            print(f"PortAudio error trying to reconnect: {e}")
            time.sleep(RECONNECT_TIMEOUT_SECONDS)
        except RestartStreamException as e:
            xruns_consecutive = 0
            print(f"Restarting audio stream due to: {e}")


def consume_audio_queue(
    config: IngestSettings, output_queue: SlidingQueue[AudioQueueData]
) -> None:
    """Consume audio data from the output queue and process it."""

    device_checks: int = 0
    while True:
        try:
            while True:
                audio_data = output_queue.get()
                if audio_data is EMPTY:
                    continue
                # Process the audio data as needed
                # For example, send it to a speech recognition module
                print(
                    f"Received audio data of length {len(audio_data.pcm_bytes)} bytes at timestamp {audio_data.timestamp_monotonic}"
                )

        except Exception as e:
            if device_checks >= MAX_DEVICE_CHECKS:
                raise RuntimeError(
                    f"Maximum device check attempts ({MAX_DEVICE_CHECKS}) reached. Exiting audio consumer."
                )
            print(f"Error in audio consumer, trying to reconnect: {e}")
            device_checks += 1
            time.sleep(RECONNECT_TIMEOUT_SECONDS)
