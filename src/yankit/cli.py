"""CLI interface for yankit — clipboard history manager."""

import json
import os
import signal

import click
from rich.console import Console
from rich.panel import Panel

from yankit import __version__
from yankit.config import config
from yankit.db import db, pid_manager
from yankit.watcher import watch

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="yankit")
def cli(ctx):
    """📋 yankit — A clipboard history manager for your terminal.

    Track, search, and manage everything you copy.

    If run without any commands, yankit will open the interactive
    Terminal User Interface (TUI). If the watcher is not running, 
    the TUI will start it automatically in the background.

    Use 'yankit stop' to terminate the background watcher.
    """
    if ctx.invoked_subcommand is None:
        from yankit.tui import YankitApp

        app = YankitApp()
        app.run()


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
def watch_cmd(interval, daemon):
    """Start watching the clipboard for changes."""
    watch(interval=interval, daemon=daemon)


@cli.command()
def stop():
    """Stop the background watcher daemon."""
    pid = pid_manager.read_pid()
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
    pid = pid_manager.read_pid()
    if pid:
        console.print(f"\n  [green]●[/] Watcher is [bold green]running[/] (PID: {pid})\n")
    else:
        console.print("\n  [dim]○[/] Watcher is [bold]not running[/]\n")




@cli.command()
def stats():
    """Show clipboard history statistics."""
    stats_data = db.get_stats()

    if stats_data["total_entries"] == 0:
        console.print("\n  [dim]No clipboard history yet. Run [bold]yankit watch[/] to start.[/]\n")
        return

    lines = [
        f"[bold cyan]Total Entries[/]      {stats_data['total_entries']:,}",
        f"[bold cyan]Today's Entries[/]    {stats_data['today_entries']:,}",
        "",
        f"[bold magenta]Total Chars Copied[/] {stats_data['total_chars']:,}",
        f"[bold magenta]Avg Chars/Entry[/]    {stats_data['avg_chars']}",
        f"[bold magenta]Avg Words/Entry[/]    {stats_data['avg_words']}",
        "",
        f"[bold yellow]Longest Entry[/]      {stats_data['longest_entry']:,} chars",
        f"[bold yellow]Shortest Entry[/]     {stats_data['shortest_entry']:,} chars",
        f"[bold yellow]Database Size[/]      {stats_data['db_size']}",
        "",
        f"[dim]First entry:[/] {stats_data['first_entry'] or 'N/A'}",
        f"[dim]Last entry:[/]  {stats_data['last_entry'] or 'N/A'}",
    ]

    panel = Panel(
        "\n".join(lines),
        title="[bold]📋 Clipboard Statistics[/]",
        border_style="green",
        padding=(1, 3),
    )

    console.print()
    console.print(panel)
    console.print()


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
    count = db.prune_older_than(older_than)
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
    count = db.delete_all()
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
    entries = db.get_entries(limit=limit if limit > 0 else 999_999)
    data = {"version": __version__, "count": len(entries), "entries": entries}
    json_str = json.dumps(data, indent=2, default=str)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        console.print(f"\n  [green]✓[/] Exported {len(entries)} entries to [bold]{output}[/]\n")
    else:
        click.echo(json_str)


@cli.group("config")
def config_group():
    """Manage yankit configuration."""
    pass


@config_group.command("view")
def config_view():
    """View current configuration."""
    console.print("\n[bold]⚙️  Current Configuration:[/]")
    data = config.get_all()
    lines = [f"  [cyan]{k}[/]: {v}" for k, v in data.items()]
    console.print("\n".join(lines) + "\n")


@config_group.command("set")
@click.option("--max-entries", type=int, help="Maximum entries to keep.")
@click.option("--auto-prune-days", type=int, help="Days after which to prune entries.")
@click.option("--enable-auto-prune", type=bool, help="Enable automatic pruning.")
@click.option("--always-show-detail", type=bool, help="Always keep the detail panel open.")
@click.option(
    "--auto-start-watcher",
    type=bool,
    help="Automatically start watcher when TUI opens.",
)
def config_set(
    max_entries, auto_prune_days, enable_auto_prune, always_show_detail, auto_start_watcher
):
    """Update configuration values."""
    if max_entries is not None:
        config.set("max_entries", max_entries)
    if auto_prune_days is not None:
        config.set("auto_prune_days", auto_prune_days)
    if enable_auto_prune is not None:
        config.set("enable_auto_prune", enable_auto_prune)
    if always_show_detail is not None:
        config.set("always_show_detail", always_show_detail)
    if auto_start_watcher is not None:
        config.set("auto_start_watcher", auto_start_watcher)

    console.print("\n  [green]✓[/] Configuration updated successfully.")
    config_view.callback()
