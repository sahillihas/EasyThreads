import threading

class SafeFileWriter:
    """
    A thread-safe utility class for writing to files.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.lock = threading.Lock()

    def write(self, data):
        """
        Write data to the file in a thread-safe manner.

        Args:
            data (str): The data to write to the file.
        """
        with self.lock:
            with open(self.file_path, 'a') as f:
                f.write(data + '\n')