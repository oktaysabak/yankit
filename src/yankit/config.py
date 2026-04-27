"""Configuration manager for Yankit."""

import json
from pathlib import Path

from yankit.db import DATA_DIR


class ConfigManager:
    """Manages the application configuration."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _default_config(self) -> dict:
        return {
            "max_entries": 10000,
            "auto_prune_days": 30,
            "enable_auto_prune": True,
            "always_show_detail": False,
        }

    def _load(self) -> dict:
        """Load configuration from JSON file or return defaults."""
        if not self.config_path.exists():
            defaults = self._default_config()
            self._save(defaults)
            return defaults

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            # Merge with defaults to ensure all keys exist
            defaults = self._default_config()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return self._default_config()

    def _save(self, data: dict) -> None:
        """Save configuration to JSON file."""
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.settings.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value and save."""
        self.settings[key] = value
        self._save(self.settings)

    def get_all(self) -> dict:
        """Return all configuration settings."""
        return self.settings

    @property
    def max_entries(self) -> int:
        return int(self.get("max_entries", 10000))

    @property
    def auto_prune_days(self) -> int:
        return int(self.get("auto_prune_days", 30))

    @property
    def enable_auto_prune(self) -> bool:
        # Convert to bool explicitly in case of bad json
        return bool(self.get("enable_auto_prune", True))
    @property
    def always_show_detail(self) -> bool:
        return bool(self.get("always_show_detail", False))

config = ConfigManager(DATA_DIR / "config.json")
