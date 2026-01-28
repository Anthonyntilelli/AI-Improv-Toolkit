import time
from typing import Final, NamedTuple, Protocol

import sounddevice as sd
import scipy.signal as signal
import numpy as np

from ._config import IngestSettings
from common.dataTypes import SlidingQueue, AudioQueueData


RECONNECT_TIMEOUT_SECONDS: Final[int] = 2
MAX_DEVICE_CHECKS: Final[int] = 5
XRUN_RESTART_THRESHOLD: Final[int] = 3
INT16_MAX: Final[float] = 32768.0
INT16_MIN: Final[float] = -32768.0


class DeviceInformation(NamedTuple):
    device_id: int
    sample_rate: float
    dtype: np.dtype


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
    sample_rate: float,
    default_data_type: np.dtype,
    input_device: bool,
) -> DeviceInformation:
    """Find the device ID and sample rate for the given device name, attempts default_sample_rate first."""
    devices = sd.query_devices()
    id: int = -1
    rate: float = -1.0
    for idx, device in enumerate(devices):
        if device_name in device["name"]:
            id = idx
            try:
                if input_device:
                    sd.check_input_settings(
                        device=id,
                        samplerate=sample_rate,
                        channels=1,
                        dtype=default_data_type,
                    )
                else:
                    sd.check_output_settings(
                        device=id,
                        samplerate=sample_rate,
                        channels=1,
                        dtype=default_data_type,
                    )
                rate = sample_rate
            except sd.PortAudioError:
                print(
                    f"Device '{device_name}' does not support the sample rate of {sample_rate} Hz. Using device's default sample rate of {device['default_samplerate']} Hz instead."
                )
                print("Resampling will be required.")
                rate = device["default_samplerate"]
            return DeviceInformation(
                device_id=id,
                sample_rate=rate,
                dtype=default_data_type,
            )
    raise ValueError(f"Input device '{device_name}' not found among available devices.")


def stream_audio_to_queue(
    config: IngestSettings, output_queue: SlidingQueue[AudioQueueData], actor_id: int
) -> None:
    """Records audio from the configured input device and forwards it to the defined output device."""

    stream_heart_beat: float = time.monotonic()
    xruns_total: int = 0
    xruns_consecutive: int = 0
    device_checks: int = 0

    def is_silence(indata: np.ndarray, threshold: float = 1e-4) -> bool:
        """
        Returns True if the RMS of the input audio buffer is below the given threshold.
        Handles int16 and float input types.
        NOTE: The threshold is set for "true silence" and will need adjustment based on environment.
        """
        arr = indata
        if arr.dtype == np.int16:
            arr = arr.astype(np.float32) / INT16_MAX
        rms = np.sqrt(np.mean(arr**2))
        return rms < threshold

    def callback(
        indata: np.ndarray,
        frames: int,
        callback_time: CallbackTimeInfo,
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
        if is_silence(indata, config.Audio.silence_threshold):
            return
        # Forward the audio data to the output queue
        output_queue.put(
            AudioQueueData(
                actor_id=actor_id,
                pcm_bytes=indata,
                timestamp_monotonic=callback_time.currentTime,
                sample_rate=input_stream.samplerate,
            )
        )

    while True:
        try:
            input_device = set_up_audio_devices(
                config.ActorMics[0].Mic_name,
                config.Audio.Sample_rate,
                np.dtype(config.Audio.Dtype),
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
    device: DeviceInformation
    try:
        device = set_up_audio_devices(
            "HDA Intel PCH: SN6140 Analog",
            config.Audio.Sample_rate,
            np.dtype(config.Audio.Dtype),
            False,
        )
    except ValueError as e:
        print(f"Output device not found: {e}")
        return
    with sd.OutputStream(
        device=device.device_id,
        samplerate=device.sample_rate,
        channels=1,
        dtype=device.dtype,
    ) as output_stream:
        print("Playing audio...")
        while True:
            audio_data = output_queue.get()
            output_stream.write(audio_data.pcm_bytes)


def audio_middleware(
    config: IngestSettings,
    pre_queue: SlidingQueue[AudioQueueData],
    post_queue: SlidingQueue[AudioQueueData],
):
    """Processed audio data from input_queue and forwards to output_queue."""

    def resample_audio(
        pcm_bytes: np.ndarray, original_rate: float, target_rate: float
    ) -> np.ndarray:
        """Resample audio from original_rate to target_rate."""
        num_samples = int(len(pcm_bytes) * (target_rate / original_rate))
        resampled = signal.resample(pcm_bytes, num_samples)
        rounded = np.round(resampled)  # typing: ignore
        resampled_int16 = np.clip(rounded, INT16_MIN, INT16_MAX).astype(np.int16)
        return resampled_int16

    while True:
        audio_data = pre_queue.get()
        post_queue.put(audio_data)

        # audio_data = pre_queue.get()
        # processed_pcm_bytes = resample_audio(
        #     audio_data.pcm_bytes,
        #     audio_data.sample_rate,
        #     config.Audio.Sample_rate,
        # )

        # post_queue.put(
        #     AudioQueueData(
        #         actor_id=audio_data.actor_id,
        #         pcm_bytes=processed_pcm_bytes,
        #         timestamp_monotonic=audio_data.timestamp_monotonic,
        #         sample_rate=config.Audio.Sample_rate,
        #     )
        # )
