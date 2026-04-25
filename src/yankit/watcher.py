"""Clipboard watcher that monitors and stores clipboard changes."""

import os
import signal
import sys
import time

from rich.console import Console

from yankit.clipboard import check_clipboard_available, get_clipboard
from yankit.db import add_entry, enforce_max_entries, remove_pid, write_pid

console = Console()

# Flag for graceful shutdown
_running = True


def _handle_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    global _running
    _running = False


def truncate(text: str, max_length: int = 80) -> str:
    """Truncate text for display, replacing newlines with visual indicators."""
    text = text.replace("\n", "↵ ").replace("\r", "")
    if len(text) > max_length:
        return text[:max_length] + "…"
    return text


def watch(interval: float = 0.5, daemon: bool = False, max_entries: int = 10000) -> None:
    """
    Start watching the clipboard for changes.

    Polls the clipboard at the given interval (in seconds) and stores
    new entries in the database. Runs until interrupted with Ctrl+C
    or a SIGTERM signal.

    Args:
        interval: Polling interval in seconds.
        daemon: If True, fork to background (Unix only).
        max_entries: Maximum number of entries to keep in the database.
    """
    global _running
    _running = True

    if daemon:
        _daemonize()

    # Write PID file so `yankit stop` can find us
    write_pid()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if not check_clipboard_available():
        console.print(
            "[bold red]Error:[/] Clipboard access is not available on this system.",
        )
        console.print(
            "On Linux, make sure [bold]xclip[/] or [bold]xsel[/] is installed.",
        )
        remove_pid()
        return

    if not daemon:
        console.print("[bold green]👀 Watching clipboard...[/] Press [bold]Ctrl+C[/] to stop.\n")

    last_content = get_clipboard()
    entry_count = 0
    prune_counter = 0

    while _running:
        try:
            current = get_clipboard()

            if current and current != last_content:
                was_added = add_entry(current)
                if was_added:
                    entry_count += 1
                    prune_counter += 1

                    if not daemon:
                        preview = truncate(current)
                        console.print(f"  [dim]#{entry_count}[/] [green]✓[/] {preview}")

                    # Enforce max entries every 100 new entries
                    if prune_counter >= 100:
                        enforce_max_entries(max_entries)
                        prune_counter = 0

                last_content = current

            time.sleep(interval)
        except Exception as e:
            if not daemon:
                console.print(f"  [red]Error:[/] {e}")
            time.sleep(interval)

    # Cleanup
    remove_pid()
    if not daemon:
        console.print(f"\n[bold yellow]Stopped.[/] Captured [bold]{entry_count}[/] entries.")


def _daemonize() -> None:
    """Fork the process to run in the background (Unix only)."""
    if sys.platform == "win32":
        console.print("[bold red]Error:[/] Daemon mode is not supported on Windows.")
        console.print("Run [bold]yankit watch[/] in a terminal instead.")
        raise SystemExit(1)

    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process — exit cleanly
            console.print(f"[bold green]✓[/] Watcher started in background (PID: {pid})")
            console.print("  Run [bold]yankit stop[/] to stop it.")
            raise SystemExit(0)
    except OSError as e:
        console.print(f"[bold red]Error:[/] Fork failed: {e}")
        raise SystemExit(1)

    # Child process continues
    os.setsid()

    # Second fork to fully detach
    try:
        pid = os.fork()
        if pid > 0:
            raise SystemExit(0)
    except OSError:
        raise SystemExit(1)

    # Redirect standard file descriptors to /dev/null
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)
