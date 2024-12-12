# EasyThread

A Python package that provides easy-to-use threading utilities and a thread-safe mechanism for writing data to files. This package is designed to handle race conditions effectively while writing to files in a multi-threaded environment.

## Features

- **Thread Management**: Easily manage and execute multiple threads concurrently.
- **Thread-Safe File Writing**: Ensure thread-safe writing to files with a locking mechanism to prevent race conditions.
- **Optimized Execution**: Start and join threads efficiently with custom thread management.
  
## Installation

To install the `EasyThread` package, you can use the following pip command:

```bash
pip install EasyThread
```

## Usage
The package provides two main components:

- ThreadManager: A utility class for managing threads.
- SafeFileWriter: A thread-safe utility class to write data to files.

Example Usage
Below is an example showing how to use the package:

```bash
from EasyThread import ThreadManager, SafeFileWriter

# Worker function to write messages to a file
def worker(writer, message):
    writer.write(message)

if __name__ == "__main__":
    # Initialize the file writer and thread manager
    file_writer = SafeFileWriter("output.txt")
    manager = ThreadManager()

    # Add threads to the manager
    for i in range(5):
        manager.add_thread(target=worker, args=(file_writer, f"Message {i}"))

    # Start and join all threads
    manager.start_all()
    manager.join_all()
    
    print("All threads have finished execution.")
```

This example demonstrates how to create a SafeFileWriter object, add multiple threads using ThreadManager, and safely write data to a file using threading.

## File Structure

```bash
EasyThread/
  ├── __init__.py          # Package initialization
  ├── thread_manager.py    # Contains the ThreadManager class
  ├── safe_file_writer.py  # Contains the SafeFileWriter class
  ├── examples/            # Example usage scripts
  │   └── example_usage.py
  ├── tests/               # Unit tests for the package
  │   ├── test_thread_manager.py
  │   └── test_safe_file_writer.py
  └── setup.py             # Package setup file
```