import threading
import logging
import time
from queue import PriorityQueue
from typing import Callable, Any
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.theme import Theme

# Setting up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

custom_theme = Theme({
    "progress.bar": "dark_green",
    "progress.spinner": "bright_cyan",
    "progress.description": "bold white",
})
console = Console(theme=custom_theme)

class ThreadManager:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.thread_pool = PriorityQueue()
        self.threads = {}
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=60),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
            transient=True,
        )

    def add_task(self, name: str, target: Callable, args: tuple = (), kwargs: dict = None, priority: int = 0):
        if name in self.threads:
            logging.warning(f"Thread with name '{name}' already exists. Skipping.")
            return

        thread = threading.Thread(target=self._wrapper, name=name, args=(target, name) + args, kwargs=kwargs or {})
        self.threads[name] = {
            "thread": thread,
            "priority": priority,
            "progress_id": None,
            "failed": False,
        }
        self.thread_pool.put((priority, name))

    def _wrapper(self, target: Callable, name: str, *args, **kwargs):
        task_id = self.threads[name]["progress_id"]
        try:
            total = kwargs.pop("total", 100)
            for _ in range(total):
                time.sleep(0.1)
                self.progress.update(task_id, advance=1)
                target(*args, **kwargs)
        except Exception as e:
            self.threads[name]["failed"] = True
            logging.error(f"Thread {name} failed: {e}")
        finally:
            self.progress.update(task_id, completed=100)
            logging.info(f"Thread {name} finished.")

    def run(self):
        active_threads = []

        with self.progress:
            while not self.thread_pool.empty() or active_threads:
                active_threads = [t for t in active_threads if t.is_alive()]

                while len(active_threads) < self.max_workers and not self.thread_pool.empty():
                    _, name = self.thread_pool.get()
                    thread = self.threads[name]["thread"]
                    progress_id = self.progress.add_task(name, total=100)
                    self.threads[name]["progress_id"] = progress_id
                    thread.start()
                    active_threads.append(thread)

                time.sleep(0.1)

        logging.info("All threads finished.")

    def get_status(self):
        return {
            name: {
                "is_alive": thread_info["thread"].is_alive(),
                "progress": self.progress.tasks[thread_info["progress_id"]].completed
                if thread_info["progress_id"] is not None else 0,
                "failed": thread_info["failed"],
            }
            for name, thread_info in self.threads.items()
        }

    def retry_failed_tasks(self):
        for name, info in self.threads.items():
            if info["failed"]:
                logging.info(f"Retrying thread {name}")
                self.add_task(
                    name=f"{name}_retry",
                    target=info["thread"]._target,
                    args=info["thread"]._args[2:],
                    kwargs=info["thread"]._kwargs,
                    priority=info["priority"],
                )
        self.run()

# def example_task(name: str, duration: int):
#     for i in range(duration):
#         # logging.info(f"{name} - Task iteration {i + 1}/{duration}")
#         time.sleep(1)

# if __name__ == "__main__":
#     manager = ThreadManager(max_workers=3)

#     for i in range(5):
#         manager.add_task(
#             name=f"Task-{i + 1}",
#             target=example_task,
#             args=(f"Task-{i + 1}", i + 2),
#             priority=i
#         )

#     manager.run()

#     manager.retry_failed_tasks()

#     logging.info(manager.get_status())