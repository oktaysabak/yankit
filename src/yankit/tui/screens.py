"""Modal screens for the Yankit TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static


class InlineDeleteScreen(ModalScreen[bool]):
    """Transparent modal that shows a prompt at the bottom, trapping keys."""

    BINDINGS = [
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "cancel", "No", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    InlineDeleteScreen {
        background: transparent;
        align: center bottom;
    }
    #inline-prompt {
        width: 100%;
        height: 1;
        background: $error;
        color: auto;
        content-align: center middle;
        text-style: bold;
    }
    """

    def __init__(self, entry_id: int):
        super().__init__()
        self.entry_id = entry_id

    def compose(self) -> ComposeResult:
        yield Static(f"Delete entry #{self.entry_id}? Yes(y)/No(n)", id="inline-prompt")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        # Any key other than y/n/escape cancels the prompt
        if event.key.lower() not in ("y", "n", "escape"):
            self.dismiss(False)


class InlineQuitScreen(ModalScreen[bool]):
    """Transparent modal to confirm quitting."""

    BINDINGS = [
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "cancel", "No", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    InlineQuitScreen {
        background: transparent;
        align: center bottom;
    }
    #quit-prompt {
        width: 100%;
        height: 1;
        background: $error;
        color: auto;
        content-align: center middle;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "Quit Yankit? Yes(y)/No(n)",
            id="quit-prompt",
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key.lower() not in ("y", "n", "escape"):
            self.dismiss(False)
