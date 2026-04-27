"""UI Components and widgets for the Yankit TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static, TextArea

from yankit.db import db


class EntryTable(DataTable):
    """Custom data table for clipboard entries with specific keybindings."""

    BINDINGS = [
        Binding("c", "copy_entry", "Copy"),
        Binding("enter", "show_detail", "Detail"),
        Binding("right", "show_detail", "Detail →", show=False),
        Binding("d", "delete_entry", "Delete"),
    ]

    def action_show_detail(self) -> None:
        self.app.action_show_detail()

    def action_hide_detail(self) -> None:
        self.app.action_hide_detail()

    def action_copy_entry(self) -> None:
        self.app.action_copy_entry()

    def action_delete_entry(self) -> None:
        self.app.action_delete_entry()


class DetailLog(TextArea):
    """TextArea for the detail panel that supports text selection and partial copying."""

    BINDINGS = [
        Binding("c", "copy_selection", "Copy"),
        Binding("ctrl+left", "focus_list", show=False, priority=True),
        Binding("alt+left", "focus_list", show=False, priority=True),
        Binding("ctrl+right", "focus_detail", show=False, priority=True),
        Binding("alt+right", "focus_detail", show=False, priority=True),
    ]

    def on_key(self, event) -> None:
        """Handle specific navigation keys in the detail view."""
        if event.key == "left" and self.cursor_location == (0, 0) and not self.selected_text:
            self.app.action_focus_list()
            event.prevent_default()

    def action_focus_list(self) -> None:
        """Delegate to app action."""
        self.app.action_focus_list()

    def action_focus_detail(self) -> None:
        """Delegate to app action (keeps focus here)."""
        self.app.action_focus_detail()

    def action_hide_detail(self) -> None:
        self.app.action_hide_detail()

    def action_copy_selection(self) -> None:
        """Copy the selected text, or the whole entry if nothing is selected."""
        if self.selected_text:
            content = self.selected_text
            label = "selection"
        else:
            content = self.text
            label = "entry"

        if not content:
            return

        from yankit.clipboard import set_clipboard

        if set_clipboard(content):
            db.add_entry(content)  # Track the partial copy as a new entry!
            # Show a brief preview in status bar
            preview = content[:30].replace("\n", " ").replace("\r", "")
            self.app._show_status(f"✓ Copied {label}: {preview}...", "green bold")
            self.app.notify(f"Copied {label} to clipboard!", title="Success")
        else:
            self.app._show_status(f"✗ Failed to copy {label}", "red bold")


class StatusBar(Horizontal):
    """Bottom status bar showing contextual messages and database capacity."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $surface;
        color: $text;
    }

    #status-text {
        width: 1fr;
        content-align: center middle;
    }

    #capacity-text {
        width: auto;
        content-align: right middle;
        padding-right: 2;
    }

    #capacity-text.danger {
        color: red;
        text-style: bold;
    }
    """

    def __init__(self, initial_text: str = ""):
        super().__init__()
        self._initial_text = initial_text

    def compose(self) -> ComposeResult:
        status_text = Static(self._initial_text, id="status-text")
        capacity_text = Static("", id="capacity-text")
        # Explicitly disable focus for status bar components
        status_text.can_focus = False
        capacity_text.can_focus = False
        self.can_focus = False

        yield status_text
        yield capacity_text

    def update(self, text: str) -> None:
        """Update the main status text."""
        self.query_one("#status-text", Static).update(text)

    def update_capacity(self, count: int, max_entries: int) -> None:
        """Update the capacity indicator."""
        cap_static = self.query_one("#capacity-text", Static)
        cap_static.update(f"{count}/{max_entries} records")
        if max_entries > 0 and count >= 0.95 * max_entries:
            cap_static.add_class("danger")
        else:
            cap_static.remove_class("danger")


class DetailPanel(Vertical):
    """Slide-out panel showing full content details."""

    DEFAULT_CSS = """
    DetailPanel {
        width: 0;
        height: 100%;
        dock: right;
        background: $surface;
        border-left: none;
        transition: width 0.3s in_out_cubic;
        overflow: hidden;
    }

    DetailPanel.visible {
        width: 50%;
        border-left: vkey $panel;
    }

    #detail-header {
        height: 3;
        padding: 1;
        background: $panel;
        color: $text;
        text-style: bold;
        border-bottom: solid $border;
    }

    #detail-content {
        padding: 1 2;
        height: 1fr;
    }

    #empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Entry Details", id="detail-header")
        log = DetailLog(id="detail-content")
        log.can_focus = True
        log.read_only = True
        log.show_line_numbers = False
        yield log

    def show_entry(self, entry: dict) -> None:
        """Populate and show the detail panel."""
        header = self.query_one("#detail-header", Static)
        header.update(
            f"Entry #{entry['id']} │ {entry['char_count']} chars │ {entry['word_count']} words"
        )

        log = self.query_one("#detail-content", DetailLog)
        log.text = entry["content"]

        self.add_class("visible")

    def hide_panel(self) -> None:
        """Hide the detail panel."""
        self.remove_class("visible")

    @property
    def is_visible(self) -> bool:
        """Check if the panel is currently visible."""
        return self.has_class("visible")
