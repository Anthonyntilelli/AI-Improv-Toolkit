"""Common data types used throughout the codebase."""

import asyncio
import queue
import threading
from typing import Literal, NamedTuple, Optional

import numpy as np


ButtonActions = Literal["speak", "reset", "unset", "exit"]


class FrameData(NamedTuple):
    """Data structure for audio frame data."""

    data: np.ndarray
    np_data_type: str  # e.g., 'int16', 'float32'


class SlidingQueue(queue.Queue):
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
                except queue.Empty:
                    pass
                print("SlidingQueue: Dropped oldest item to make space.")
            super().put(item, block=block, timeout=timeout)

    def put_nowait(self, item) -> None:
        """Put an item into the queue without blocking, dropping the oldest item if full."""
        with self._lock:
            if self.full():
                try:
                    self.get(block=False)
                except queue.Empty:
                    pass
                print("SlidingQueue: Dropped oldest item to make space.")
            super().put_nowait(item)


class AsyncSlidingQueue(asyncio.Queue):
    """Asynchronous FIFO Queue that drops the oldest item when full."""

    def __init__(self, maxsize: int):
        if maxsize <= 0:
            raise ValueError("AsyncSlidingQueue requires a positive maxsize")
        super().__init__(maxsize)
        self._lock = asyncio.Lock()

    async def put(self, item) -> None:
        """Put an item into the queue, dropping the oldest item if full."""
        async with self._lock:
            if self.full():
                try:
                    self.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                print("AsyncSlidingQueue: Dropped oldest item to make space.")
            await super().put(item)

    def put_nowait(self, item) -> None:
        """Put an item into the queue without blocking, dropping the oldest item if full."""
        # Note: asyncio.Queue is not thread-safe, so this lock is only for async context.
        # This method is synchronous, so we use the lock's synchronous context.
        if self.full():
            try:
                self.get_nowait()
            except asyncio.QueueEmpty:
                pass
            print("AsyncSlidingQueue: Dropped oldest item to make space.")
        super().put_nowait(item)
