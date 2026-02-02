import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings:
    """
    Manages application settings with robust file handling.
    """
    DEFAULT_SETTINGS = {
        "vram_t1_threshold": 92,
        "vram_t2_panic_threshold": 105,
        "cool_down_time_s": 3.0,
        "work_time_s": 2.0,
        "lhm_port": 8085,
        "enable_notifications": True,
        "enable_audio_alert": True
    }

    def __init__(self, project_root: Path):
        self.filename = project_root / "settings.json"
        self.data = self.DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        """Loads settings or creates default if file is missing or empty."""
        if not self.filename.exists() or self.filename.stat().st_size == 0:
            logger.info("Settings file missing or empty. Creating defaults.")
            self._save()
            return

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                self.data.update(loaded)
            logger.info("Settings loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}. Reverting to defaults.")
            self._save()

    def _save(self):
        """Saves current settings to JSON."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str):
        return self.data.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value):
        self.data[key] = value
        self._save()