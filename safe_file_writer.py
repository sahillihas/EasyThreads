import threading
import logging
from pathlib import Path
from typing import Union, Sequence


class SafeFileWriter:
    """
    Thread-safe utility for writing to a file.
    Can handle strings or sequences of strings.
    """

    def __init__(self, file_path: Union[str, Path], encoding: str = "utf-8"):
        """
        Args:
            file_path: Path to the file to write.
            encoding: Encoding used to open the file.
        """
        self.file_path = Path(file_path)
        self.encoding = encoding
        self._lock = threading.Lock()

    def write(self, data: Union[str, Sequence[str]], add_newline: bool = True) -> None:
        """
        Write data to the file in a thread-safe manner.

        Args:
            data: String or sequence of strings to write.
            add_newline: Whether to append a newline after each entry.
        """
        with self._lock:
            try:
                with self.file_path.open("a", encoding=self.encoding) as f:
                    if isinstance(data, str):
                        f.write(data + ("\n" if add_newline else ""))
                    else:
                        f.write(
                            "\n".join(data) + ("\n" if add_newline else "")
                        )
            except OSError as e:
                logging.error(
                    f"Failed to write to file {self.file_path}: {e}",
                    exc_info=True
                )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Nothing to clean up — file is handled per write call
        return False
