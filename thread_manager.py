import threading
from queue import Queue

# Thread Manager
class ThreadManager:
    """
    A utility class to manage threads and ensure safe execution.
    """
    def __init__(self):
        self.threads = Queue()

    def add_thread(self, target, args=()):
        """
        Add a new thread to the manager.

        Args:
            target (function): The function the thread will execute.
            args (tuple): Arguments for the target function
        """
        thread = threading.Thread(target=target, args=args)
        self.threads.put(thread)

    def start_all(self):
        """Start all managed threads."""
        while not self.threads.empty():
            thread = self.threads.get()
            thread.start()
            self.threads.put(thread)

    def join_all(self):
        """Wait for all managed threads to complete."""
        while not self.threads.empty():
            thread = self.threads.get()
            thread.join()
