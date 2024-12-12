from ..thread_manager import ThreadManager
from ..safe_file_writer import SafeFileWriter

def worker(writer, message):
    """Thread worker function to write a message to the file."""
    writer.write(message)

if __name__ == "__main__":
    file_writer = SafeFileWriter("output.txt")
    manager = ThreadManager()

    for i in range(5):
        manager.add_thread(target=worker, args=(file_writer, f"Message {i}"))

    manager.start_all()
    manager.join_all()
    print("All threads have finished execution.")