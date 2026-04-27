"""Clipboard watcher that monitors and stores clipboard changes."""

import os
import signal
import sys
import time

from rich.console import Console

from yankit.clipboard import check_clipboard_available, get_clipboard
from yankit.config import config
from yankit.db import db, pid_manager

console = Console()


class ClipboardWatcher:
    """Watches the system clipboard for changes and stores them."""

    def __init__(self, interval: float = 0.5, daemon: bool = False):
        self.interval = interval
        self.daemon = daemon
        self._running = False
        self._entry_count = 0
        self._prune_counter = 0

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self._running = False

    @staticmethod
    def truncate(text: str, max_length: int = 80) -> str:
        """Truncate text for display, replacing newlines with visual indicators."""
        text = text.replace("\n", "↵ ").replace("\r", "")
        if len(text) > max_length:
            return text[:max_length] + "…"
        return text

    def watch(self) -> None:
        """
        Start watching the clipboard for changes.

        Polls the clipboard at the given interval (in seconds) and stores
        new entries in the database. Runs until interrupted with Ctrl+C
        or a SIGTERM signal.
        """
        self._running = True

        if self.daemon:
            self._daemonize()

        pid_manager.write_pid()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        if not check_clipboard_available():
            console.print(
                "[bold red]Error:[/] Clipboard access is not available on this system.",
            )
            console.print(
                "On Linux, make sure [bold]xclip[/] or [bold]xsel[/] is installed.",
            )
            pid_manager.remove_pid()
            return

        if not self.daemon:
            console.print(
                "[bold green]👀 Watching clipboard...[/] Press [bold]Ctrl+C[/] to stop.\n"
            )

        last_content = get_clipboard()

        while self._running:
            try:
                current = get_clipboard()

                if current and current != last_content:
                    was_added = db.add_entry(current)
                    if was_added:
                        self._entry_count += 1
                        self._prune_counter += 1

                        if not self.daemon:
                            preview = self.truncate(current)
                            console.print(f"  [dim]#{self._entry_count}[/] [green]✓[/] {preview}")

                        if self._prune_counter >= 100:
                            db.enforce_max_entries(config.max_entries)
                            if config.enable_auto_prune:
                                db.prune_older_than(config.auto_prune_days)
                            self._prune_counter = 0

                    last_content = current

                time.sleep(self.interval)
            except Exception as e:
                if not self.daemon:
                    console.print(f"  [red]Error:[/] {e}")
                time.sleep(self.interval)

        pid_manager.remove_pid()
        if not self.daemon:
            console.print(
                f"\n[bold yellow]Stopped.[/] Captured [bold]{self._entry_count}[/] entries."
            )

    def _daemonize(self) -> None:
        """Fork the process to run in the background (Unix only)."""
        if sys.platform == "win32":
            console.print("[bold red]Error:[/] Daemon mode is not supported on Windows.")
            console.print("Run [bold]yankit watch[/] in a terminal instead.")
            raise SystemExit(1)

        try:
            pid = os.fork()
            if pid > 0:
                console.print(f"[bold green]✓[/] Watcher started in background (PID: {pid})")
                console.print("  Run [bold]yankit stop[/] to stop it.")
                raise SystemExit(0)
        except OSError as e:
            console.print(f"[bold red]Error:[/] Fork failed: {e}")
            raise SystemExit(1)

        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                raise SystemExit(0)
        except OSError:
            raise SystemExit(1)

        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)


def watch(interval: float = 0.5, daemon: bool = False) -> None:
    """Legacy wrapper for cli compatibility. Instantiates and runs ClipboardWatcher."""
    watcher = ClipboardWatcher(interval, daemon)
    watcher.watch()
