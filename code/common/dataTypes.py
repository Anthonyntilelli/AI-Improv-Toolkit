"""Common data types used throughout the codebase."""

from queue import Queue, Empty as QueueEmpty, ShutDown as QueueSHUTDOWN
import threading
from typing import NamedTuple, Optional, TypeVar, Generic

T = TypeVar("T")


class SlidingQueue(Generic[T]):
    """Automatic FIFO Queue that drops the oldest item when full."""

    def __init__(self, maxsize: int = 0):
        self.queue: Queue[T] = Queue(maxsize)
        self.lock = threading.Lock()
        self.shutdown_flag = False

    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """Put an item into the queue, dropping the oldest item if full."""
        with self.lock:
            if self.shutdown_flag:
                raise SHUTDOWN("Cannot put item into a shut down SlidingQueue")
            if self.queue.full():
                # Remove the oldest item without blocking to maintain sliding semantics
                self.queue.get_nowait()
            # Use a non-blocking put to avoid holding the lock across a blocking operation
            self.queue.put_nowait(item)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> T:
        """Get an item from the queue."""
        with self.lock:
            try:
                item = self.queue.get(block, timeout)
            except QueueEmpty:
                raise EMPTY("SlidingQueue is empty")
            except QueueSHUTDOWN:
                raise SHUTDOWN("SlidingQueue has been shut down")
            return item

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


class EMPTY(Exception):
    """Exception raised when attempting to get from an empty queue."""

    def __init__(self, message):
        super().__init__(message)


class SHUTDOWN(Exception):
    """Exception raised when put() or get() is called on a Queue object which has been shut down."""

    def __init__(self, message):
        super().__init__(message)
