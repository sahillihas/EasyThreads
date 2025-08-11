import threading
import logging
from typing import Callable, Tuple, List, Optional


class ThreadManager:
    """
    A utility class to manage multiple threads, providing
    easy start/join operations and optional error-safe execution.
    """

    def __init__(self, daemon: bool = False):
        """
        Initialize the ThreadManager.

        Args:
            daemon (bool): Whether all threads should run as daemon threads. Default is False.
        """
        self.threads: List[threading.Thread] = []
        self.daemon = daemon
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_thread(self, target: Callable, args: Tuple = (), name: Optional[str] = None, safe: bool = True):
        """
        Add a new thread to the manager.

        Args:
            target (Callable): The function the thread will execute.
            args (Tuple): Arguments for the target function.
            name (str, optional): Name for the thread.
            safe (bool): If True, wraps target in exception handling to prevent silent thread failures.
        """
        if safe:
            def safe_target(*a, **kw):
                try:
                    target(*a, **kw)
                except Exception as e:
                    self.logger.exception(f"Error in thread {name or target.__name__}: {e}")
        else:
            safe_target = target

        thread = threading.Thread(target=safe_target, args=args, name=name, daemon=self.daemon)
        self.threads.append(thread)

    def start_all(self):
        """Start all managed threads."""
        for thread in self.threads:
            self.logger.debug(f"Starting thread: {thread.name}")
            thread.start()

    def join_all(self, timeout: Optional[float] = None):
        """
        Wait for all managed threads to complete.

        Args:
            timeout (float, optional): Max seconds to wait for each thread. None means wait indefinitely.
        """
        for thread in self.threads:
            self.logger.debug(f"Joining thread: {thread.name}")
            thread.join(timeout=timeout)
