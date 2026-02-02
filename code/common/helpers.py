"""Helper functions and classes for common tasks."""

import struct
import random

import numpy as np
import pyogg

OPUS_FRAME_SAMPLES = 960  # 20 ms @ 48 kHz


class OpusEncoder:
    """converts a PCM numpy array to Opus-encoded bytes."""

    def __init__(self, sample_rate: int, channels: int) -> None:
        """
        Initialize an Opus encoder for the given sample rate and channel count.

        Args:
            sample_rate: Sampling frequency in Hz. Valid Opus sample rates are
                8000, 12000, 16000, 24000, or 48000 Hz.
            channels: Number of audio channels (e.g., 1 for mono, 2 for stereo).
        """
        self.sample_rate = sample_rate
        self.channels = channels

        self.encoder = pyogg.OpusEncoder()  # type: ignore
        self.encoder.set_application("audio")
        self.encoder.set_sampling_frequency(sample_rate)
        self.encoder.set_channels(channels)

    def encode(self, pcm: np.ndarray) -> bytes:
        """
        pcm: int16 numpy array, shape (samples, channels) or (samples,)
        """
        if pcm.dtype != np.int16:
            raise ValueError("PCM must be int16")
    def __init__(self, sample_rate: int, payload_type: int = 111) -> None:
        """Initialize an RTP packetizer for a given audio stream.

        Args:
            sample_rate: Sampling rate of the encoded audio stream, in Hz.
            payload_type: RTP payload type for the encoded audio. Defaults to
                111, which is the standard RTP payload type for Opus.
        """
        samples_per_channel = pcm.shape[0] // self.channels
        return self.encoder.encode(pcm.tobytes(), samples_per_channel)


class RTPPacketizer:
    """Builds RTP packets from payload data."""

    def __init__(self, sample_rate, payload_type=111):
        self.payload_type = payload_type
        self.sample_rate = sample_rate
        self.sequence = 0
        self.timestamp = 0
        self.ssrc = random.getrandbits(32)

    def build(self, payload: bytes, samples: int, marker=0) -> bytes:
        """Builds an RTP packet with the given payload and updates sequence and timestamp."""
        v_p_x_cc = 0x80  # V=2, P=0, X=0, CC=0
        m_pt = ((marker & 1) << 7) | (self.payload_type & 0x7F)

        header = struct.pack(
            "!BBHII",
            v_p_x_cc,
            m_pt,
            self.sequence,
            self.timestamp,
            self.ssrc,
        )

        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + samples) & 0xFFFFFFFF

        return header + payload
