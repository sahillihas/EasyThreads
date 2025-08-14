import threading
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


@dataclass
class ManagedThread:
    name: str
    thread: threading.Thread
    started: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Any = None
    exception: Optional[BaseException] = None
    done: threading.Event = field(default_factory=threading.Event)

    @property
    def alive(self) -> bool:
        return self.thread.is_alive()

    @property
    def duration(self) -> Optional[float]:
        if self.start_time is None:
            return None
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time


class ThreadManager:
    """
    Manage multiple threads with safe execution, results, and lifecycle control.
    """

    def __init__(self, default_daemon: bool = False):
        self._log = logging.getLogger(self.__class__.__name__)
        self._default_daemon = default_daemon
        self._items: Dict[str, ManagedThread] = {}
        self._lock = threading.RLock()
        # Cooperative cancel token you may pass to workers (optional usage)
        self.cancel_event = threading.Event()

    # ---------- Public API ----------

    def add_thread(
        self,
        target: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        *,
        name: Optional[str] = None,
        daemon: Optional[bool] = None,
        safe: bool = True,
    ) -> ManagedThread:
        """
        Register a new thread (not started).
        - safe=True captures exceptions and stores them in ManagedThread.exception.
        - kwargs are supported.
        - Name is auto-unique if omitted or duplicated.
        """
        kwargs = kwargs or {}
        name = self._unique_name(name or getattr(target, "__name__", "worker"))
        daemon = self._default_daemon if daemon is None else daemon

        def wrapper():
            item = self._items[name]
            item.started = True
            item.start_time = time.time()
            try:
                if safe:
                    try:
                        item.result = target(*args, **kwargs)
                    except BaseException as e:
                        item.exception = e
                        # Full traceback in logs:
                        self._log.exception("Thread %s crashed: %s", name, e)
                else:
                    item.result = target(*args, **kwargs)
            finally:
                item.end_time = time.time()
                item.done.set()

        thread = threading.Thread(target=wrapper, name=name, daemon=daemon)
        item = ManagedThread(name=name, thread=thread)
        with self._lock:
            self._items[name] = item
        return item

    def start_all(self) -> None:
        """Start all not-yet-started threads."""
        with self._lock:
            for item in self._items.values():
                if not item.started and not item.thread.is_alive():
                    self._log.debug("Starting thread: %s", item.name)
                    item.thread.start()

    def start(self, name: str) -> None:
        """Start a specific thread by name."""
        item = self._require(name)
        if item.started or item.thread.is_alive():
            self._log.debug("Thread %s already started; skipping.", name)
            return
        self._log.debug("Starting thread: %s", name)
        item.thread.start()

    def join_all(self, timeout: Optional[float] = None) -> List[str]:
        """
        Join all threads.
        - timeout applies to the *overall* join window (not per thread).
        Returns list of thread names still alive after join attempt.
        """
        deadline = None if timeout is None else time.time() + timeout
        alive_after: List[str] = []
        with self._lock:
            for item in self._items.values():
                remaining = None
                if deadline is not None:
                    remaining = max(0.0, deadline - time.time())
                    if remaining == 0.0:
                        alive_after.extend(self._alive_names_unlocked())
                        break
                self._log.debug("Joining thread: %s", item.name)
                item.thread.join(timeout=remaining)
            # Gather any still-alive threads
            alive_after = self._alive_names_unlocked()
        return alive_after

    def join(self, name: str, timeout: Optional[float] = None) -> bool:
        """Join a specific thread; returns True if finished, False if still alive."""
        item = self._require(name)
        item.thread.join(timeout=timeout)
        return not item.thread.is_alive()

    def results(self) -> Dict[str, Any]:
        """Return dict of thread name -> result (None if not set)."""
        with self._lock:
            return {n: it.result for n, it in self._items.items()}

    def exceptions(self) -> Dict[str, BaseException]:
        """Return dict of thread name -> exception (only those that raised)."""
        with self._lock:
            return {n: it.exception for n, it in self._items.items() if it.exception is not None}

    def remove_completed(self) -> List[str]:
        """Remove finished threads from the manager; returns list of removed names."""
        removed: List[str] = []
        with self._lock:
            for name in list(self._items.keys()):
                if not self._items[name].alive and self._items[name].started:
                    removed.append(name)
                    del self._items[name]
        return removed

    def active_names(self) -> List[str]:
        """List names of currently alive threads."""
        with self._lock:
            return [n for n, it in self._items.items() if it.alive]

    def all_names(self) -> List[str]:
        """List all registered thread names."""
        with self._lock:
            return list(self._items.keys())

    def is_all_done(self) -> bool:
        """True if no threads are alive."""
        with self._lock:
            return not any(it.alive for it in self._items.values())

    # Context manager: ensures join on exit
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Best-effort graceful shutdown: signal cancel and join briefly
        self.cancel_event.set()
        leftover = self.join_all(timeout=5.0)
        if leftover:
            self._log.warning("Threads still alive after context exit: %s", leftover)
        # Do not suppress exceptions
        return False

    # ---------- Internal helpers ----------

    def _require(self, name: str) -> ManagedThread:
        with self._lock:
            if name not in self._items:
                raise KeyError(f"No thread named '{name}'")
            return self._items[name]

    def _alive_names_unlocked(self) -> List[str]:
        return [n for n, it in self._items.items() if it.alive]

    def _unique_name(self, base: str) -> str:
        with self._lock:
            if base not in self._items:
                return base
            i = 2
            while f"{base}-{i}" in self._items:
                i += 1
            return f"{base}-{i}"
