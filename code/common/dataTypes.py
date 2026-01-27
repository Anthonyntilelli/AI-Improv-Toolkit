"""Common data types used throughout the codebase."""

from queue import Queue
import threading
from typing import NamedTuple, Optional, TypeVar, Generic

T = TypeVar("T")


class SlidingQueue(Generic[T]):
    """Automatic FIFO Queue that drops the oldest item when full. Backed by queue.Queue. Emits Standard queue exceptions."""

    def __init__(self, maxsize: int = 0):
        self.queue: Queue[T] = Queue(maxsize)
        self.lock = threading.Lock()

    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """Put an item into the queue, dropping the oldest item if full."""
        with self.lock:
            if self.queue.full():
                # Remove the oldest item without blocking to maintain sliding semantics
                self.queue.get_nowait()
            self.queue.put(item, block, timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> T:
        """Get an item from the queue."""
        return self.queue.get(block, timeout)

    def qsize(self) -> int:
        """Return the current size of the queue."""
        return self.queue.qsize()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.empty()

    def full(self) -> bool:
        """Check if the queue is full."""
        return self.queue.full()

    def shutdown(self, immediate: bool = False) -> None:
        """Shut down the queue, making put and get operations raise SHUTDOWN exception."""
        with self.lock:
            self.shutdown_flag = True
            shutdown_method = getattr(self.queue, "shutdown", None)
            if callable(shutdown_method):
                shutdown_method(immediate)


class AudioQueueData(NamedTuple):
    """Data structure for audio data in the queue."""

    pcm_bytes: bytes
    timestamp_monotonic: float
    sample_rate: int
