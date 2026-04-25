<p align="center">
  <img src="https://raw.githubusercontent.com/oktaysabak/yankit/main/assets/mascot.png" alt="yankit mascot" width="180" />
</p>

<h1 align="center">yankit</h1>

<p align="center">
  A clipboard history manager for your terminal.<br/>
  <strong>Yank it, track it, find it.</strong>
</p>

## Features

- **Watch** — Monitor your clipboard in real-time (foreground or daemon mode)
- **List** — View your clipboard history with timestamps and word counts
- **Search** — Find anything you've copied with highlighted results
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

### 2. Check watcher status / stop it

```bash
yankit status
yankit stop
```

### 3. View your clipboard history

```bash
yankit list
yankit list --today
yankit list --limit 50
```

### 4. Search through history

```bash
yankit search "password"
yankit search "https://"
```

### 5. View statistics

```bash
yankit stats
```

### 6. Re-copy an old entry

```bash
yankit copy 42
```

### 7. Show full content of an entry

```bash
yankit show 42
```

### 8. Export history

```bash
yankit export
yankit export --output history.json
```

### 9. Cleanup

```bash
# Delete entries older than 30 days
yankit prune --older-than 30

# Delete all history
yankit clear
```

## How It Works

yankit polls your system clipboard every 0.5 seconds and stores new entries in a local SQLite database. It deduplicates consecutive copies and enforces a configurable maximum entry limit (default: 10,000) to prevent unbounded growth.

```
yankit watch ──► polls clipboard ──► new content? ──► store in SQLite
                   every 0.5s              │
                                    same as last? ──► skip
```

### Database Location

All data is stored locally at `~/.yankit/history.db`. No data is ever sent anywhere.

### Database Size Management

- **Max entries limit**: `yankit watch --max-entries 5000`
- **Age-based pruning**: `yankit prune --older-than 30` (days)
- **Full reset**: `yankit clear`
- **Monitor size**: `yankit stats` shows current DB size

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
