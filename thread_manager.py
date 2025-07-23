import threading
from typing import Callable, Tuple, List

class ThreadManager:
    """
    A utility class to manage threads and ensure safe execution.
    """

    def __init__(self):
        self.threads: List[threading.Thread] = []

    def add_thread(self, target: Callable, args: Tuple = (), name: str = None):
        """
        Add a new thread to the manager.

        Args:
            target (Callable): The function the thread will execute.
            args (Tuple): Arguments for the target function.
            name (str, optional): Optional name for the thread.
        """
        thread = threading.Thread(target=target, args=args, name=name)
        self.threads.append(thread)

    def start_all(self):
        """Start all managed threads."""
        for thread in self.threads:
            thread.start()

    def join_all(self):
        """Wait for all managed threads to complete."""
        for thread in self.threads:
            thread.join()
