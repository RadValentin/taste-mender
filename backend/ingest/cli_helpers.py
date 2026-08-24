# Small helpers for interactive CLI messages during ingest scripts
import sys


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
