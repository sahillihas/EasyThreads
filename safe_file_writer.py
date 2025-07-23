import threading
import logging
from typing import Union, List

class SafeFileWriter:
    """
    A thread-safe utility class for writing to a file.
    """

    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """
        Initialize the SafeFileWriter.

        Args:
            file_path (str): Path to the file to write.
            encoding (str): Encoding used to open the file.
        """
        self.file_path = file_path
        self.encoding = encoding
        self.lock = threading.Lock()

    def write(self, data: Union[str, List[str]]) -> None:
        """
        Write data to the file in a thread-safe manner.

        Args:
            data (Union[str, List[str]]): The data to write to the file. Can be a string or list of strings.
        """
        with self.lock:
            try:
                with open(self.file_path, 'a', encoding=self.encoding) as f:
                    if isinstance(data, list):
                        for line in data:
                            f.write(line + '\n')
                    else:
                        f.write(data + '\n')
            except IOError as e:
                logging.error(f"Error writing to file {self.file_path}: {e}")
