import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ManagedThread:
    """Metadata and state for a managed thread."""
    name: str
    thread: threading.Thread
    started: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Any = None
    exception: Optional[Exception] = None
    done: threading.Event = field(default_factory=threading.Event, repr=False)

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
    Manage multiple threads with:
      - safe exception capture & per-thread results
      - duplicate name prevention
      - cancel-aware starts
      - start/join helpers and timeouts
      - status helpers & cleanup
      - context manager for auto-join
    """

    def __init__(self, default_daemon: bool = False) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._default_daemon = default_daemon
        self._items: Dict[str, ManagedThread] = {}
        self._lock = threading.RLock()
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
        Register a new (not yet started) thread.
        - safe=True: capture exceptions, store in ManagedThread.exception, and log.
        - kwargs supported; name auto-uniqued if omitted or duplicate.
        """
        if not callable(target):
            raise TypeError("target must be callable")

        kwargs = kwargs or {}
        base_name = name or getattr(target, "__name__", "worker")
        unique_name = self._unique_name(base_name)
        daemon = self._default_daemon if daemon is None else daemon

        def _runner() -> None:
            item = self._items[unique_name]
            item.started = True
            item.start_time = time.time()
            try:
                if safe:
                    try:
                        item.result = target(*args, **kwargs)
                    except Exception as exc:
                        item.exception = exc
                        self._log.exception("Thread %s raised: %s", unique_name, exc)
                else:
                    item.result = target(*args, **kwargs)
            finally:
                item.end_time = time.time()
                item.done.set()

        th = threading.Thread(target=_runner, name=unique_name, daemon=daemon)
        item = ManagedThread(name=unique_name, thread=th)
        with self._lock:
            self._items[unique_name] = item
        return item

    def start_all(self) -> List[str]:
        """
        Start all not-yet-started threads (skips if cancel_event is set).
        Returns list of started thread names.
        """
        started: List[str] = []
        with self._lock:
            if self.cancel_event.is_set():
                self._log.warning("Cancel flag set; start_all skipped.")
                return started
            for item in self._items.values():
                if not item.started and not item.thread.is_alive():
                    self._log.debug("Starting thread: %s", item.name)
                    item.thread.start()
                    started.append(item.name)
        return started

    def start(self, name: str) -> bool:
        """
        Start a specific thread. Returns True if started, False if it was already started
        or cancel flag is set.
        """
        with self._lock:
            if self.cancel_event.is_set():
                self._log.warning("Cancel flag set; start('%s') skipped.", name)
                return False
            item = self._require(name)
            if item.started or item.thread.is_alive():
                self._log.debug("Thread %s already started; skipping.", name)
                return False
            self._log.debug("Starting thread: %s", name)
            item.thread.start()
            return True

    def join_all(self, timeout: Optional[float] = None) -> List[str]:
        """
        Join all threads. `timeout` is an overall budget (not per-thread).
        Returns list of thread names still alive after the join attempt.
        """
        deadline = None if timeout is None else (time.time() + timeout)
        with self._lock:
            for item in self._items.values():
                remaining = None
                if deadline is not None:
                    remaining = max(0.0, deadline - time.time())
                    if remaining == 0.0:
                        break
                self._log.debug("Joining thread: %s", item.name)
                item.thread.join(timeout=remaining)
            return [n for n, it in self._items.items() if it.alive]

    def join(self, name: str, timeout: Optional[float] = None) -> bool:
        """Join one thread. Returns True if finished, False if still alive."""
        item = self._require(name)
        item.thread.join(timeout=timeout)
        return not item.thread.is_alive()

    def get_result(self, name: str, *, rethrow: bool = True) -> Any:
        """
        Get a thread's result. If an exception occurred and rethrow=True,
        re-raise it; else return None and leave it recorded.
        """
        item = self._require(name)
        if item.exception and rethrow:
            raise item.exception
        return item.result

    def results(self) -> Dict[str, Any]:
        """Return dict: name -> result (None if not set or errored)."""
        with self._lock:
            return {n: it.result for n, it in self._items.items()}

    def exceptions(self) -> Dict[str, Exception]:
        """Return dict: name -> exception for threads that raised."""
        with self._lock:
            return {n: it.exception for n, it in self._items.items() if it.exception is not None}

    def remove_completed(self) -> List[str]:
        """Remove finished threads from the manager; returns removed names."""
        removed: List[str] = []
        with self._lock:
            for name in list(self._items.keys()):
                it = self._items[name]
                if it.started and not it.alive:
                    removed.append(name)
                    del self._items[name]
        return removed

    def active_names(self) -> List[str]:
        """Names of currently alive threads."""
        with self._lock:
            return [n for n, it in self._items.items() if it.alive]

    def all_names(self) -> List[str]:
        """All registered thread names."""
        with self._lock:
            return list(self._items.keys())

    def is_all_done(self) -> bool:
        """True if no threads are alive."""
        with self._lock:
            return not any(it.alive for it in self._items.values())

    def cancel(self) -> None:
        """Set the cooperative cancel flag (workers should check it)."""
        self.cancel_event.set()

    # Context manager ensures a best-effort shutdown
    def __enter__(self) -> "ThreadManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.cancel_event.set()
        leftover = self.join_all(timeout=5.0)
        if leftover:
            self._log.warning("Threads still alive on exit: %s", leftover)
        # do not suppress exceptions from with-body
        return False

    # ---------- Internal helpers ----------

    def _require(self, name: str) -> ManagedThread:
        with self._lock:
            item = self._items.get(name)
            if item is None:
                raise KeyError(f"No thread named '{name}'")
            return item

    def _unique_name(self, base: str) -> str:
        with self._lock:
            if base not in self._items:
                return base
            i = 2
            while f"{base}-{i}" in self._items:
                i += 1
            return f"{base}-{i}"
