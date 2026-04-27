<p align="center">
  <img src="https://raw.githubusercontent.com/oktaysabak/yankit/main/assets/mascot.png" alt="yankit mascot" width="180" />
</p>

<h1 align="center">yankit</h1>

<p align="center">
  A clipboard history manager for your terminal.<br/>
  <strong>Yank it, track it, find it.</strong>
</p>

## Features

- **Interactive TUI** — Browse, search, and copy entries with keyboard navigation
- **Partial Selection** — Select and copy specific parts of text in the detail view
- **Watch** — Monitor your clipboard in real-time (foreground or daemon mode)
- **Stats** — See statistics about your clipboard usage
- **Copy back** — Re-copy any past entry back to your clipboard
- **Export** — Export your clipboard history as JSON
- **Prune** — Auto-cleanup old entries to keep your database lean
- **Daemon mode** — Run in background with `stop` and `status` commands

## Installation

### With uvx (recommended, no install needed)

```bash
uvx yankit watch
```

### With uv

```bash
uv tool install yankit
```

### With pip

```bash
pip install yankit
```

## Quick Start

### 1. Start watching your clipboard

```bash
# Foreground mode (Ctrl+C to stop)
yankit watch

# Background daemon mode
yankit watch --daemon
```

### 2. Browse with the Interactive TUI

The primary way to use yankit is through its interactive interface. Simply running `yankit` without any arguments will launch the TUI, where you can navigate your history, preview long texts, and search through everything you've copied.

```bash
# Launch the interactive browser
yankit
```

**Keybindings:**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate between entries / scroll text |
| `c` | Copy highlighted entry (or selection if in detail view) |
| `Enter` / `→` | Open detail panel / Focus content |
| `←` / `Escape` | Return to list / Close search |
| `TAB` / `Shift+TAB` | Cycle focus between Search, List, and Detail |
| `Enter` / `↓` | Jump to results (when in search) |
| `Alt` + `←` / `→` | Switch focus directly between List and Detail |
| `s` | Open search |
| `d` | Delete highlighted entry |
| `r` | Refresh entries |
| `q` | Quit |

### 3. Check watcher status / stop it

```bash
yankit status
yankit stop
```

### 4. Configuration

You can view and update your configuration directly from the CLI.

```bash
# View current config
yankit config view

# Update settings
yankit config set --max-entries 5000 --always-show-detail True
```

#### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `max_entries` | `10000` | Maximum number of entries to keep in the database. |
| `auto_prune_days` | `30` | Number of days after which entries are automatically deleted. |
| `enable_auto_prune` | `True` | Whether to automatically prune old entries when the watcher is running. |
| `always_show_detail` | `False` | If True, the detail panel stays open in the TUI even when no entry is selected. |
| `auto_start_watcher` | `True` | Automatically start the background watcher when you open the TUI if it's not running. |

### 5. View statistics

```bash
yankit stats
```

### 6. Export history

```bash
yankit export
yankit export --output history.json
```

### 7. Cleanup

```bash
# Delete entries older than 30 days
yankit prune --older-than 30

# Delete all history
yankit clear
```

## How It Works

yankit polls your system clipboard every 0.5 seconds and stores new entries in a local SQLite database. It deduplicates consecutive copies and enforces a configurable maximum entry limit to prevent unbounded growth.

```
yankit watch ──► polls clipboard ──► new content? ──► store in SQLite
                   every 0.5s              │
                                    same as last? ──► skip
```

### Database Location

All data is stored locally at `~/.yankit/history.db`. Your configuration is at `~/.yankit/config.json`. No data ever leaves your machine.

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| macOS    | ✅      | Uses `pbcopy`/`pbpaste` (pre-installed) |
| Linux    | ✅      | Requires `xclip` or `xsel` |

### Linux Prerequisites

```bash
# Debian/Ubuntu
sudo apt-get install xclip

# Arch
sudo pacman -S xclip

# Fedora
sudo dnf install xclip
```

## Development

```bash
git clone https://github.com/oktaysabak/yankit.git
cd yankit

uv sync
uv run yankit --help
```

## License

[MIT](LICENSE)
