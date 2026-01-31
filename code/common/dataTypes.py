"""Common data types used throughout the codebase."""

from queue import Queue, Empty
import threading
from typing import Literal, NamedTuple, Optional

import numpy as np


ButtonActions = Literal["speak", "reset", "unset", "exit"]


VadState = Literal["start", "stop", "continue", "n/a"]


class AudioFrame(NamedTuple):
    """Data structure for audio frame in the queue."""

    actor_id: int  # 0..n for actors in MVP (currently only 0)
    pcm_bytes: np.ndarray
    wall_time: float  # Wall-clock timestamp (UTC seconds since epoch) time.time()
    sample_rate: float
    dtype: str


class TaggedAudioFrame(NamedTuple):
    """Data structure for tagged audio frame in the queue."""

    frame: AudioFrame
    is_de_noised: bool  # True if frame has been de_noised
    is_silence: bool  # True if frame RMS is below silence threshold
    is_voice: bool  # True if voice activity is detected in this frame
    vad_state: VadState  # VAD segment boundaries
    rms_db: float  # Root Mean Square level in dBFS for the frame
    sequence_num: int  # Sequence number for ordering or loss detection


class SlidingQueue(Queue):
    """FIFO Queue that drops the oldest item when full."""

    def __init__(self, maxsize: int):
        if maxsize <= 0:
            raise ValueError("SlidingQueue requires a positive maxsize")
        super().__init__(maxsize)
        self._lock = threading.Lock()

    def put(self, item, block: bool = True, timeout: Optional[float] = None) -> None:
        """Put an item into the queue, dropping the oldest item if full."""
        with self._lock:
            if self.full():
                try:
                    self.get(block=False)
                except Empty:
                    pass
                print("SlidingQueue: Dropped oldest item to make space.")
            super().put(item, block=block, timeout=timeout)
