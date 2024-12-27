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

    def add_task(self, name: str, target: Callable, args: tuple = (), kwargs: dict = None, priority: int = 0, total: int = 100):
        if name in self.threads:
            logging.warning(f"Thread with name '{name}' already exists. Skipping.")
            return

        kwargs = kwargs or {}
        kwargs["total"] = total  # Pass total to the task's kwargs

        thread = threading.Thread(target=self._wrapper, name=name, args=(target, name) + args, kwargs=kwargs)
        self.threads[name] = {
            "thread": thread,
            "priority": priority,
            "progress_id": None,
            "failed": False,
        }
        self.thread_pool.put((priority, name))


    def _wrapper(self, target: Callable, name: str, *args, **kwargs):
        task_id = self.threads[name]["progress_id"]
        total = kwargs.pop("total", 100)  # Use the provided total or default to 100

        try:
            for _ in range(total):
                time.sleep(0.1)
                self.progress.update(task_id, advance=1)
                target(*args, **kwargs)
        except Exception as e:
            self.threads[name]["failed"] = True
            logging.error(f"Thread {name} failed: {e}")
        finally:
            self.progress.update(task_id, completed=total)  # Mark the task as completed
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

    def run_llm_tasks(self, llm_function: Callable, prompts: list, **kwargs):
        for i, prompt in enumerate(prompts):
            self.add_task(
                name=f"LLM-Task-{i+1}",
                target=llm_function,
                args=(prompt,),
                kwargs=kwargs,
                priority=i
            )
        self.run()

def example_task(name: str, duration: int):
    for i in range(duration):
        logging.info(f"{name} - Task iteration {i + 1}/{duration}")
        time.sleep(1)

def example_llm_function(prompt: str):
    time.sleep(30)  # Simulate LLM response time
    #Add LLM call here..

if __name__ == "__main__":
    manager = ThreadManager(max_workers=3)

    # Can add more prompts or pass it via external list
    prompts = [
        "What is the capital of France?",
        "Explain quantum mechanics in simple terms.",
        "Write a poem about the sea.",
        "What are the benefits of machine learning?",
        "Describe the theory of relativity."
    ]

    manager.run_llm_tasks(example_llm_function, prompts)

    logging.info(manager.get_status())
