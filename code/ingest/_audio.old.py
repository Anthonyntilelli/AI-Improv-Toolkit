import time
from typing import Final, NamedTuple, Protocol
import copy

import sounddevice as sd
import scipy.signal as signal
import numpy as np
import webrtcvad
import noisereduce as nr

from ._config import IngestSettings
from common.dataTypes import SlidingQueue, AudioFrame, TaggedAudioFrame, VadState


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
    device_name: str, sample_rate: float, default_data_type: np.dtype, input_device: bool
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


def stream_audio_to_queue(ingest_config: IngestSettings, output_queue: SlidingQueue, actor_id: int) -> None:
    """Records audio from the configured input device and forwards AudioFrame to the defined output device."""

    # Temporary workaround to avoid mutating the original config (will need to move to frozen dataclass later)
    config: IngestSettings = copy.deepcopy(ingest_config)

    stream_heart_beat: float = time.monotonic()
    xruns_total: int = 0
    xruns_consecutive: int = 0
    device_checks: int = 0

    def callback(indata: np.ndarray, frames: int, callback_time: CallbackTimeInfo, status: sd.CallbackFlags) -> None:
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
        output_queue.put(AudioFrame(actor_id, indata, time.time(), input_stream.samplerate, str(indata.dtype)))

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


def consume_audio_queue(ingest_config: IngestSettings, output_queue: SlidingQueue) -> None:
    """Consume audio data from the output queue and process it."""

    # Temporary workaround to avoid mutating the original config (will need to move to frozen dataclass later)
    config: IngestSettings = copy.deepcopy(ingest_config)

    while True:
        _ = output_queue.get()
        # Placeholder for processing logic
        pass


def audio_middleware(ingest_config: IngestSettings, pre_queue: SlidingQueue, post_queue: SlidingQueue) -> None:
    """Processed audio data from input_queue and forwards to output_queue."""

    # Temporary workaround to avoid mutating the original config (will need to move to frozen dataclass later)
    config: IngestSettings = copy.deepcopy(ingest_config)
    vad = webrtcvad.Vad()
    vad.set_mode(config.Audio.Vad_aggressiveness)  # Set aggressiveness mode (0-3)
    vad_past_frames: VadState = "n/a"
    stream_sequence_num: int = 0

    def is_silence(indata: np.ndarray, threshold: float = 1e-4) -> tuple[bool, float]:
        """
        Returns True if the RMS of the input audio buffer is below the given threshold.
        Handles int16 and float input types.
        NOTE: The threshold is set for "true silence" and will need adjustment based on environment.
        returns a tuple of (is_silence, rms_value)
        """
        arr = indata
        if arr.dtype == np.int16:
            arr = arr.astype(np.float32) / INT16_MAX
        rms = np.sqrt(np.mean(arr**2))
        return rms < threshold, rms

    def resample_audio(pcm_bytes: np.ndarray, original_rate: float, target_rate: float) -> np.ndarray:
        """Resample audio from original_rate to target_rate using polyphase filtering."""
        arr = pcm_bytes.squeeze()
        if original_rate == target_rate:
            return arr.astype(np.int16) if arr.dtype != np.int16 else arr
        from math import gcd

        up = int(target_rate)
        down = int(original_rate)
        factor = gcd(up, down)
        up //= factor
        down //= factor
        resampled = signal.resample_poly(arr, up, down)
        resampled_int16 = np.clip(np.round(resampled), INT16_MIN, INT16_MAX).astype(np.int16)
        return resampled_int16

    while True:
        pre_process_audio: AudioFrame = pre_queue.get()
        preprocessing_start_time = time.time()
        processed_pcm_bytes = resample_audio(
            pre_process_audio.pcm_bytes,
            pre_process_audio.sample_rate,
            config.Audio.Sample_rate,
        )
        if processed_pcm_bytes.ndim > 1:
            processed_pcm_bytes = processed_pcm_bytes.squeeze()
        processed_pcm_bytes = processed_pcm_bytes.astype(np.int16)

        # Calculate RMS and silence BEFORE noise reduction
        is_silence_flag, rms_value = is_silence(processed_pcm_bytes, config.Audio.silence_threshold)

        # Run VAD BEFORE noise reduction
        is_vad_flag = vad.is_speech(processed_pcm_bytes.tobytes(), config.Audio.Sample_rate)
        if is_vad_flag:
            if vad_past_frames in ["n/a", "stop"]:
                vad_past_frames = "start"
            if vad_past_frames in ["start", "continue"]:
                vad_past_frames = "continue"
        else:
            if vad_past_frames in ["start", "continue"]:
                vad_past_frames = "stop"
            if vad_past_frames == "stop":
                vad_past_frames = "n/a"

        # Apply noise reduction AFTER VAD/RMS if enabled
        if config.Audio.Use_noise_reducer:
            processed_pcm_bytes = nr.reduce_noise(
                y=processed_pcm_bytes.astype(np.float32), sr=int(config.Audio.Sample_rate)
            )
            # Convert back to int16 for consistency
            processed_pcm_bytes = np.clip(np.round(processed_pcm_bytes), INT16_MIN, INT16_MAX).astype(np.int16)

        post_queue.put(
            TaggedAudioFrame(
                frame=AudioFrame(
                    actor_id=pre_process_audio.actor_id,
                    pcm_bytes=processed_pcm_bytes,
                    wall_time=pre_process_audio.wall_time,
                    sample_rate=config.Audio.Sample_rate,
                    dtype=str(processed_pcm_bytes.dtype),
                ),
                is_de_noised=config.Audio.Use_noise_reducer,
                is_silence=is_silence_flag,
                is_voice=is_vad_flag,
                vad_state=vad_past_frames,
                rms_db=rms_value,
                sequence_num=stream_sequence_num,
            )
        )
        pre_process_duration = time.time() - preprocessing_start_time
        print(
            f"Audio Frame Seq {stream_sequence_num}: VAD={is_vad_flag}, Silence={is_silence_flag}, RMS={rms_value:.6f}, VadState={vad_past_frames}, PreProcessDuration={pre_process_duration:.6f}s"
        )
        stream_sequence_num += 1
