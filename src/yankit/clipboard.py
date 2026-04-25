"""Cross-platform clipboard access wrapper around pyperclip."""

import sys

import pyperclip


def get_clipboard() -> str | None:
    """
    Get the current clipboard content.

    Returns None if the clipboard is empty or an error occurs.
    """
    try:
        content = pyperclip.paste()
        return content if content else None
    except pyperclip.PyperclipException as e:
        print(f"Error reading clipboard: {e}", file=sys.stderr)
        return None


def set_clipboard(text: str) -> bool:
    """
    Set the clipboard content.

    Returns True on success, False on failure.
    """
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as e:
        print(f"Error writing to clipboard: {e}", file=sys.stderr)
        return False


def check_clipboard_available() -> bool:
    """Check if clipboard access is available on this system."""
    try:
        pyperclip.paste()
        return True
    except pyperclip.PyperclipException:
        return False
