"""Main application module for the Yankit TUI."""

import subprocess

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Input

from yankit.clipboard import set_clipboard
from yankit.config import config
from yankit.db import db, pid_manager
from yankit.tui.components import DetailPanel, EntryTable, StatusBar
from yankit.tui.screens import InlineDeleteScreen, InlineQuitScreen


class YankitApp(App):
    """Interactive clipboard history browser."""

    CSS = """
    #search-bar {
        height: 0;
        overflow: hidden;
        transition: height 0.2s in_out_cubic;
    }
    
    #search-bar.visible {
        height: 3;
    }
    
    #main-area {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
        Binding("s", "search", "Search"),
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+right", "focus_detail", "Focus Detail", show=False, priority=True),
        Binding("ctrl+left", "focus_list", "Focus List", show=False, priority=True),
        Binding("alt+right", "focus_detail", show=False, priority=True),
        Binding("alt+left", "focus_list", show=False, priority=True),
    ]

    # Reactive state
    current_query: reactive[str] = reactive("")
    entries: reactive[list[dict]] = reactive(list, init=False)
    selected_entry: reactive[dict | None] = reactive(None, init=False)

    def __init__(self, initial_query: str | None = None):
        super().__init__()
        self._initial_query = initial_query

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="search-bar"):
            yield Input(placeholder="Search clipboard history…", id="search-input")
        with Horizontal(id="main-area"):
            yield EntryTable(id="entry-table", cursor_type="row", zebra_stripes=True)
            yield DetailPanel()
        yield StatusBar(
            initial_text=(
                "↑↓ Navigate  │  c Copy  │  Enter/→ Detail  │  d Delete  │  s Search  │  q Quit"
            )
        )
        yield Footer()

    def on_key(self, event) -> None:
        """Global key handler for specific focus transitions."""
        # If Down arrow is pressed in search input, jump to results table
        if event.key == "down":
            search_input = self.query_one("#search-input", Input)
            if search_input.has_focus:
                self.query_one("#entry-table", EntryTable).focus()
                event.prevent_default()

    def on_mount(self) -> None:
        """Set up the table and load initial data."""
        table = self.query_one("#entry-table", EntryTable)
        table.add_column("ID", width=7, key="id")
        table.add_column("Content", key="content")
        table.add_column("Chars", width=8, key="chars")
        table.add_column("Words", width=8, key="words")
        table.add_column("Time", width=20, key="time")

        # Ensure decorative widgets don't take focus to keep focus cycle clean
        self.query_one(Header).can_focus = False
        self.query_one(Footer).can_focus = False

        if config.always_show_detail:
            detail = self.query_one(DetailPanel)
            detail.add_class("visible")

        if self._initial_query:
            self.current_query = self._initial_query
            search_bar = self.query_one("#search-bar")
            search_bar.add_class("visible")
            search_input = self.query_one("#search-input", Input)
            search_input.value = self._initial_query
            self._load_search_results(self._initial_query)
        else:
            self._load_entries()
            table = self.query_one("#entry-table", EntryTable)
            table.focus()
            # If always_show_detail is true, show the first entry immediately
            if config.always_show_detail and self.entries:
                self.query_one(DetailPanel).show_entry(self.entries[0])

        # Check for new entries every second for live updates
        self.set_interval(1.0, self._check_new_entries)

        # Initial watcher status check
        self._check_watcher()

    def _check_watcher(self) -> None:
        """Check if the clipboard watcher is running and update status bar."""
        is_running = pid_manager.read_pid() is not None
        status_bar = self.query_one(StatusBar)
        status_bar.update_watcher(is_running)

        if not is_running:
            if config.auto_start_watcher:
                try:
                    # Attempt to start the watcher in background
                    subprocess.Popen(
                        ["yankit", "watch", "-d"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    self._show_status(
                        "✓ Watcher started in background. Use 'yankit stop' to stop it.",
                        "green",
                    )
                    # Update UI immediately
                    status_bar.update_watcher(True)
                except Exception:
                    self._show_status(
                        "⚠ Watcher is NOT running! Start it with: yankit watch -d",
                        "red bold",
                    )
            else:
                self._show_status(
                    "⚠ Watcher is NOT running! Start it with: yankit watch -d", "red bold"
                )

    def _check_new_entries(self) -> None:
        """Background task to refresh the table if new entries are found in DB."""
        self._check_watcher()
        if self.current_query or len(self.screen_stack) > 1:
            return

        detail = self.query_one(DetailPanel)
        if getattr(detail, "is_visible", False):
            # Skip auto-refresh while viewing details to avoid jarring jumps
            return

        # skip if a screen is on top (like delete/quit)
        pass

        latest = db.get_entries(limit=1)
        if not latest:
            return

        db_latest_id = latest[0]["id"]

        if not self.entries or db_latest_id > self.entries[0]["id"]:
            # Auto-refresh and maintain live feed
            self._load_entries()
            table = self.query_one("#entry-table", EntryTable)
            if table.has_focus and table.row_count > 0:
                # Reset cursor to top for new entry
                table.move_cursor(row=0)

    def _truncate(self, text: str, max_length: int = 60) -> str:
        """Truncate text for table display."""
        text = text.replace("\n", "↵ ").replace("\r", "")
        if len(text) > max_length:
            return text[:max_length] + "…"
        return text

    def _load_entries(self, target_id: int | None = None) -> None:
        """Load recent entries into the table."""
        self.entries = db.get_entries(limit=100)
        self._populate_table(self.entries, target_id=target_id)
        self._update_capacity()

    def _update_capacity(self) -> None:
        """Fetch total count and update the capacity indicator."""
        total_count = db.get_count()
        status = self.query_one(StatusBar)
        status.update_capacity(total_count, config.max_entries)

    def _load_search_results(self, query: str, target_id: int | None = None) -> None:
        """Load search results into the table."""
        if not query.strip():
            self._load_entries(target_id=target_id)
            return
        self.entries = db.search_entries(query, limit=100)
        self._populate_table(self.entries, target_id=target_id)

    def _populate_table(self, entries: list[dict], target_id: int | None = None) -> None:
        """Clear and repopulate the data table."""
        table = self.query_one("#entry-table", EntryTable)
        table.clear()

        if not entries:
            self.query_one(DetailPanel).clear()
            if not config.always_show_detail:
                self.query_one(DetailPanel).hide_panel()

            table.add_row("-", "Clipboard history is empty...", "-", "-", "-")
            self._show_status("Clipboard history is empty.", "dim")
            return

        for entry in entries:
            table.add_row(
                str(entry["id"]),
                self._truncate(entry["content"]),
                str(entry.get("char_count", 0)),
                str(entry["word_count"]),
                entry["created_at"],
                key=str(entry["id"]),
            )

        if target_id is not None:
            table.focus_by_id(target_id)

        self._show_status(
            "↑↓ Navigate  │  c Copy  │  Enter/→ Detail  │  d Delete  │  s Search  │  q Quit"
        )

    def _get_selected_entry(self) -> dict | None:
        """Get the entry dict for the currently highlighted row."""
        table = self.query_one("#entry-table", EntryTable)
        if table.row_count == 0 or not self.entries:
            return None

        try:
            row_index = table.cursor_coordinate.row
            if 0 <= row_index < len(self.entries):
                return self.entries[row_index]
        except Exception:
            return None
        return None

    def _show_status(self, text: str, style: str = "") -> None:
        """Update the status bar."""
        try:
            status = self.query_one(StatusBar)
            if style:
                status.update(f"[{style}]{text}[/]")
            else:
                status.update(text)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update detail panel when a row is highlighted if the panel is open."""
        try:
            detail = self.query_one(DetailPanel)
            if detail.is_visible:
                entry = self._get_selected_entry()
                if entry:
                    detail.show_entry(entry)
        except Exception:
            pass

    def action_focus_detail(self) -> None:
        """Switch focus to the detail panel log, opening it if necessary."""
        detail = self.query_one(DetailPanel)
        if not detail.is_visible:
            entry = self._get_selected_entry()
            if entry:
                detail.show_entry(entry)
            else:
                self._show_status("No entry to show.", "yellow")
                return

        from yankit.tui.components import DetailLog

        log = detail.query_one("#detail-content", DetailLog)
        log.focus()
        self._show_status("Focused Detail. Use arrow keys to scroll/select.", "cyan")

    def action_focus_list(self) -> None:
        """Switch focus back to the entries table."""
        self.query_one("#entry-table", EntryTable).focus()
        self.action_refresh()
        self._show_status("Focused List. ↑↓ to navigate.", "cyan")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.current_query = event.value
            self._load_search_results(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input to jump to results."""
        if event.input.id == "search-input":
            self.query_one("#entry-table", EntryTable).focus()
            self._show_status("Focused List. ↑↓ to navigate.", "cyan")

    def action_search(self) -> None:
        """Toggle the search bar."""
        search_bar = self.query_one("#search-bar")
        search_input = self.query_one("#search-input", Input)

        if search_bar.has_class("visible"):
            # Close search, clear it, return focus to table
            search_bar.remove_class("visible")
            search_input.value = ""
            self.current_query = ""
            self._load_entries()
            self.query_one("#entry-table", EntryTable).focus()
        else:
            # Open search and focus input
            search_bar.add_class("visible")
            search_input.focus()

    def action_back(self) -> None:
        """Close detail panel or search bar. If both are closed, request quit."""
        detail = self.query_one(DetailPanel)
        if detail.is_visible:
            if config.always_show_detail:
                # In persistent mode, back just returns focus to the list
                self.query_one("#entry-table", EntryTable).focus()
            else:
                detail.hide_panel()
                self.action_refresh()  # Refresh to show any new copies made in detail
                self.query_one("#entry-table", EntryTable).focus()
            return

        search_bar = self.query_one("#search-bar")
        if search_bar.has_class("visible"):
            search_bar.remove_class("visible")
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            self.current_query = ""
            self._load_entries()
            self.query_one("#entry-table", EntryTable).focus()
            return

        # If we are at the root view, Escape requests to quit the application
        self.action_request_quit()

    def action_request_quit(self) -> None:
        """Prompt to quit the application."""

        def check_quit(confirm: bool) -> None:
            if confirm:
                self.exit()

        self.push_screen(InlineQuitScreen(), check_quit)

    def action_copy_entry(self) -> None:
        """Copy the highlighted entry to the system clipboard."""
        entry = self._get_selected_entry()
        if entry is None:
            self._show_status("No entry selected.", "yellow")
            return

        if set_clipboard(entry["content"]):
            db.add_entry(entry["content"])  # Track it (moves to top if exists)
            preview = self._truncate(entry["content"], 40)
            self._show_status(f"✓ Copied #{entry['id']}: {preview}", "green bold")
            self.notify(
                "Copied to clipboard!", title="Success", severity="information", timeout=2.0
            )
        else:
            self._show_status("✗ Failed to copy to clipboard.", "red bold")
            self.notify("Failed to copy!", title="Error", severity="error", timeout=2.0)

    def action_show_detail(self) -> None:
        """Show the detail panel, or focus it if already shown to allow scrolling."""
        detail = self.query_one(DetailPanel)
        if detail.is_visible:
            # Focus the DetailLog so arrow keys scroll the text
            from yankit.tui.components import DetailLog

            log = detail.query_one("#detail-content", DetailLog)
            log.focus()
            self._show_status(
                "Focused detail panel. Use arrow keys to scroll. Press ← to go back.", "cyan"
            )
        else:
            entry = self._get_selected_entry()
            if entry:
                detail.show_entry(entry)
                self._show_status(f"✓ Detail opened for #{entry['id']}", "green")
            else:
                self._show_status("✗ Could not get entry details.", "red")

    def action_hide_detail(self) -> None:
        """If detail is focused, move focus back to list. If list is focused, hide detail."""
        detail = self.query_one(DetailPanel)
        if detail.is_visible:
            from yankit.tui.components import DetailLog

            log = detail.query_one("#detail-content", DetailLog)
            if log.has_focus:
                self.query_one("#entry-table", EntryTable).focus()
                self.action_refresh()
                self._show_status(
                    "↑↓ Navigate  │  c Copy  │  Enter/→ Detail  │  d Delete  │  s Search  │  q Quit"
                )
            else:
                if config.always_show_detail:
                    # In persistent mode, don't hide, just focus table
                    self.query_one("#entry-table", EntryTable).focus()
                else:
                    detail.hide_panel()
                    self.action_refresh()  # Refresh to show any new copies made in detail
                    self.query_one("#entry-table", EntryTable).focus()

    def action_delete_entry(self) -> None:
        """Prompt to delete the selected entry."""
        entry = self._get_selected_entry()
        if entry is None:
            return

        def check_delete(confirm: bool) -> None:
            if confirm:
                if db.delete_entry(entry["id"]):
                    self.notify(
                        f"Deleted entry #{entry['id']}", title="Deleted", severity="warning"
                    )
                    self.action_refresh()

        self.push_screen(InlineDeleteScreen(entry["id"]), check_delete)

    def action_refresh(self) -> None:
        """Reload entries from the database while maintaining cursor position."""
        # Capture current selection ID for cursor persistence
        current_id = None
        entry = self._get_selected_entry()
        if entry:
            current_id = entry["id"]

        if self.current_query:
            self._load_search_results(self.current_query, target_id=current_id)
        else:
            self._load_entries(target_id=current_id)
        self._show_status("✓ Refreshed", "green")
