import time
from typing import Final, NamedTuple, Protocol

import sounddevice as sd
import numpy as np  # noqa: F401  # Required for type hints and sounddevice's NumPy-backed buffers

from ._config import AudioDataType, IngestSettings

import code


class DeviceInformation(NamedTuple):

    device_id: int
    sample_rate: float
    dtype:  AudioDataType # preferred for whisper 'int16'
    resample_required: bool


RECONNECT_TIMEOUT_SECONDS: Final[int] = 2
MAX_RECONNECT_ATTEMPTS: Final[int] = 5


def set_up_audio_devices(device_name: str, default_sample_rate: float, default_data_type: AudioDataType, input_device: bool) -> DeviceInformation:
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
                    sd.check_input_settings(device=id, samplerate=default_sample_rate, channels=1, dtype=default_data_type)
                else:
                    sd.check_output_settings(device=id, samplerate=default_sample_rate, channels=1, dtype=default_data_type)
                rate = default_sample_rate
            except sd.PortAudioError:
                print(f"Device '{device_name}' does not support the default sample rate of {default_sample_rate} Hz. Using device's default sample rate of {device['default_samplerate']} Hz instead.")
                print("Resampling will be required.")
                rate = device["default_samplerate"]
                resample_required = True
            return DeviceInformation(device_id=id, sample_rate=rate, dtype=default_data_type, resample_required=resample_required)
    raise ValueError(f"Input device '{device_name}' not found among available devices.")


def record_and_forward(config: IngestSettings) -> None:
    """Records audio from the configured input device and forwards it to the defined output device."""

    stream_heart_beat: float = time.monotonic()

    class CallbackTimeInfo(Protocol):
        inputBufferAdcTime: float
        currentTime: float
        outputBufferDacTime: float

    def callback(
        indata: np.ndarray,
        frames: int,
        call_back_time: CallbackTimeInfo,
        status: sd.CallbackFlags,
    ) -> None:
        """Audio callback function to process input and output audio data."""
        if status:
            print("Callback status:", status)
        nonlocal stream_heart_beat
        stream_heart_beat = time.monotonic()
        # Do something with indata here, e.g., forward it to an output stream or process it.
        pass  # Placeholder for actual processing logic
        code.interact(local=locals())


    while True:
      try:
        input_device = set_up_audio_devices(config.ActorMics[0].Mic_name, config.Audio.Sample_rate, config.Audio.Dtype, True)
        # output_device = set_up_audio_devices("HDA Intel PCH: SN6140 Analog", config.Audio.Sample_rate, config.Audio.Dtype, False)

        with sd.InputStream(
            device=input_device.device_id,
            samplerate=input_device.sample_rate,
            channels=1,  # Assuming mono input (MVP only)
            callback=callback,
            dtype=input_device.dtype,
        ) as input_stream:

            print("Recording... Press Ctrl+C to stop.")
            while input_stream.active:
                sd.sleep(2000)
                if time.monotonic() - stream_heart_beat > 2.0:
                  print("No audio callbacks received; restarting stream.")
                  break

      except (sd.PortAudioError, ValueError) as e:
        print(f"PortAudio error trying to reconnect: {e}")
        time.sleep(RECONNECT_TIMEOUT_SECONDS)
