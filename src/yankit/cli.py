"""CLI interface for yankit — clipboard history manager."""

import json
import os
import signal

import click
from rich.console import Console

from yankit import __version__
from yankit.clipboard import set_clipboard
from yankit.db import (
    delete_all,
    get_entries,
    get_entry_by_id,
    get_stats,
    get_today_entries,
    prune_older_than,
    read_pid,
    search_entries,
)
from yankit.display import (
    display_entries,
    display_entry_detail,
    display_search_results,
    display_stats,
)
from yankit.watcher import watch

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="yankit")
def cli():
    """📋 yankit — A clipboard history manager for your terminal.

    Track, search, and manage everything you copy.
    """


@cli.command("watch")
@click.option(
    "--interval",
    "-i",
    default=0.5,
    type=float,
    help="Polling interval in seconds.",
    show_default=True,
)
@click.option(
    "--daemon",
    "-d",
    is_flag=True,
    help="Run in background (Unix only).",
)
@click.option(
    "--max-entries",
    "-m",
    default=10000,
    type=int,
    help="Maximum entries to keep.",
    show_default=True,
)
def watch_cmd(interval, daemon, max_entries):
    """Start watching the clipboard for changes."""
    watch(interval=interval, daemon=daemon, max_entries=max_entries)


@cli.command()
def stop():
    """Stop the background watcher daemon."""
    pid = read_pid()
    if pid is None:
        console.print("\n  [dim]No running watcher found.[/]\n")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"\n  [green]✓[/] Stopped watcher (PID: {pid}).\n")
    except ProcessLookupError:
        console.print("\n  [dim]Watcher was already stopped.[/]\n")
    except PermissionError:
        console.print(f"\n  [red]Error:[/] Permission denied to stop PID {pid}.\n")


@cli.command()
def status():
    """Check if the watcher daemon is running."""
    pid = read_pid()
    if pid:
        console.print(f"\n  [green]●[/] Watcher is [bold green]running[/] (PID: {pid})\n")
    else:
        console.print("\n  [dim]○[/] Watcher is [bold]not running[/]\n")


@cli.command("list")
@click.option(
    "--limit",
    "-n",
    default=20,
    help="Number of entries to show.",
    show_default=True,
)
@click.option(
    "--today",
    "-t",
    is_flag=True,
    help="Show only today's entries.",
)
@click.option(
    "--offset",
    "-o",
    default=0,
    help="Offset for pagination.",
    show_default=True,
)
def list_cmd(limit, today, offset):
    """List recent clipboard entries."""
    if today:
        entries = get_today_entries()
        display_entries(entries, title="Today's Clipboard History")
    else:
        entries = get_entries(limit=limit, offset=offset)
        display_entries(entries)


@cli.command()
@click.argument("query")
@click.option(
    "--limit",
    "-n",
    default=50,
    help="Max results to show.",
    show_default=True,
)
def search(query, limit):
    """Search through clipboard history."""
    entries = search_entries(query, limit=limit)
    display_search_results(entries, query)


@cli.command()
def stats():
    """Show clipboard history statistics."""
    statistics = get_stats()
    display_stats(statistics)


@cli.command()
@click.argument("entry_id", type=int)
def copy(entry_id):
    """Copy a history entry back to the clipboard by its ID."""
    entry = get_entry_by_id(entry_id)
    if entry is None:
        console.print(f"\n  [red]Error:[/] Entry #{entry_id} not found.\n")
        raise SystemExit(1)

    if set_clipboard(entry["content"]):
        display_entry_detail(entry)
        console.print(f"  [green]✓[/] Copied entry #{entry_id} back to clipboard.\n")
    else:
        console.print("\n  [red]Error:[/] Failed to copy to clipboard.\n")
        raise SystemExit(1)


@cli.command()
@click.argument("entry_id", type=int)
def show(entry_id):
    """Show the full content of a clipboard entry."""
    entry = get_entry_by_id(entry_id)
    if entry is None:
        console.print(f"\n  [red]Error:[/] Entry #{entry_id} not found.\n")
        raise SystemExit(1)

    display_entry_detail(entry)


@cli.command()
@click.option(
    "--older-than",
    "-d",
    default=30,
    type=int,
    help="Delete entries older than N days.",
    show_default=True,
)
def prune(older_than):
    """Delete old clipboard entries."""
    count = prune_older_than(older_than)
    if count > 0:
        console.print(
            f"\n  [green]✓[/] Pruned [bold]{count:,}[/] entries older than {older_than} days.\n"
        )
    else:
        console.print(f"\n  [dim]No entries older than {older_than} days.[/]\n")


@cli.command()
@click.confirmation_option(
    prompt="Are you sure you want to delete all clipboard history?",
)
def clear():
    """Delete all clipboard history."""
    count = delete_all()
    console.print(f"\n  [green]✓[/] Deleted [bold]{count:,}[/] entries.\n")


@cli.command()
@click.option(
    "--limit",
    "-n",
    default=0,
    help="Max entries to export (0 = all).",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path.",
)
def export(limit, output):
    """Export clipboard history as JSON."""
    entries = get_entries(limit=limit if limit > 0 else 999_999)
    data = {"version": __version__, "count": len(entries), "entries": entries}
    json_str = json.dumps(data, indent=2, default=str)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        console.print(f"\n  [green]✓[/] Exported {len(entries)} entries to [bold]{output}[/]\n")
    else:
        click.echo(json_str)
