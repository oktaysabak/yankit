"""Rich-powered terminal display for clipboard history."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def truncate(text: str, max_length: int = 60) -> str:
    """Truncate text for table display."""
    text = text.replace("\n", "↵ ").replace("\r", "")
    if len(text) > max_length:
        return text[:max_length] + "…"
    return text


def display_entries(entries: list[dict], title: str = "Clipboard History") -> None:
    """Display clipboard entries in a rich table."""
    if not entries:
        console.print("\n  [dim]No entries found.[/]\n")
        return

    table = Table(
        title=f"  {title}",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        padding=(0, 1),
    )

    table.add_column("ID", style="dim cyan", width=6, justify="right")
    table.add_column("Content", style="white", min_width=30, max_width=65)
    table.add_column("Chars", style="dim yellow", width=7, justify="right")
    table.add_column("Words", style="dim yellow", width=7, justify="right")
    table.add_column("Time", style="dim green", width=19)

    for entry in entries:
        table.add_row(
            str(entry["id"]),
            truncate(entry["content"]),
            str(entry["char_count"]),
            str(entry["word_count"]),
            entry["created_at"],
        )

    console.print()
    console.print(table)
    console.print()


def display_search_results(entries: list[dict], query: str) -> None:
    """Display search results with the query highlighted."""
    if not entries:
        console.print(f"\n  [dim]No results found for[/] [bold]'{query}'[/]\n")
        return

    table = Table(
        title=f"  Search results for '{query}'",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        padding=(0, 1),
    )

    table.add_column("ID", style="dim cyan", width=6, justify="right")
    table.add_column("Content", min_width=30, max_width=65)
    table.add_column("Time", style="dim green", width=19)

    for entry in entries:
        content = truncate(entry["content"])
        text = Text(content)
        text.highlight_words([query], style="bold yellow on dark_red")
        table.add_row(str(entry["id"]), text, entry["created_at"])

    console.print()
    console.print(table)
    console.print(f"  [dim]{len(entries)} result(s) found.[/]")
    console.print()


def display_stats(stats: dict) -> None:
    """Display clipboard history statistics in a rich panel."""
    if stats["total_entries"] == 0:
        console.print("\n  [dim]No clipboard history yet. Run [bold]yankit watch[/] to start.[/]\n")
        return

    lines = [
        f"[bold cyan]Total Entries[/]      {stats['total_entries']:,}",
        f"[bold cyan]Today's Entries[/]    {stats['today_entries']:,}",
        "",
        f"[bold magenta]Total Chars Copied[/] {stats['total_chars']:,}",
        f"[bold magenta]Avg Chars/Entry[/]    {stats['avg_chars']}",
        f"[bold magenta]Avg Words/Entry[/]    {stats['avg_words']}",
        "",
        f"[bold yellow]Longest Entry[/]      {stats['longest_entry']:,} chars",
        f"[bold yellow]Shortest Entry[/]     {stats['shortest_entry']:,} chars",
        f"[bold yellow]Database Size[/]      {stats['db_size']}",
        "",
        f"[dim]First entry:[/] {stats['first_entry'] or 'N/A'}",
        f"[dim]Last entry:[/]  {stats['last_entry'] or 'N/A'}",
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


def display_entry_detail(entry: dict) -> None:
    """Display a single clipboard entry in detail."""
    sub = (
        f"[dim]{entry['created_at']} · {entry['char_count']} chars · {entry['word_count']} words[/]"
    )
    panel = Panel(
        entry["content"],
        title=f"[bold]Entry #{entry['id']}[/]",
        subtitle=sub,
        border_style="cyan",
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()
