# Small helpers for interactive CLI messages during ingest scripts
import sys
import time
import threading
from contextlib import contextmanager


def print_banner(title: str, description: str = ""):
    width = max(len(title), *(len(line) for line in description.splitlines()), 0) + 4
    print("=" * width)
    print(f"  {title}")
    if description:
        print("-" * width)
        for line in description.splitlines():
            print(f"  {line}")
    print("=" * width, flush=True)


def confirm(prompt: str = "Continue?", default: bool = False) -> bool:
    """Ask the user to confirm an action, returns False if input isn't a TTY."""
    if not sys.stdin.isatty():
        return default

    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def show_progress_bar(done: int, total: int, step=10000, message: str = ""):
    done = min(done, total)
    if ((done % step) == 0) or (done == total):
        percent = done / total
        filled = int(percent * 30)
        bar = "#" * filled + "-" * (30 - filled)
        if message:
            print(f"\r{message} [{bar}] {done}/{total} ({percent*100:5.1f}%)", end="", flush=True)
        else:
            print(f"\r[{bar}] {done}/{total} ({percent*100:5.1f}%)", end="", flush=True)



@contextmanager
def spinner(message: str):
    """Show an animated spinner while a blocking block of code runs."""
    frames = "|/-\\"
    stop_event = threading.Event()
    start = time.time()

    def _animate():
        i = 0
        while not stop_event.is_set():
            print(f"\r{message} {frames[i % len(frames)]}", end="", flush=True)
            i += 1
            stop_event.wait(0.1)

    thread = threading.Thread(target=_animate, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join()
        print(f"\r{message} done in {time.time() - start:.2f}s", flush=True)

