import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings:
    """
    Manages application settings, reading from and writing to settings.json.
    """
    
    # --- DEFAULT PUBLIC SETTINGS ---
    DEFAULT_SETTINGS = {
        "vram_t1_threshold": 92,        # [C] Temp to start throttling
        "vram_t2_panic_threshold": 105, # [C] Temp to trigger emergency kill
        "cool_down_time_s": 3.0,        # [s] Duration of process pause
        "work_time_s": 2.0,             # [s] Duration of process resume
        "lhm_port": 8085,               # [Port] Start port for LibreHardwareMonitor
        "enable_notifications": True,   # [bool] Windows Toast notifications
        "enable_audio_alert": True,     # [bool] Panic mode sound alert
        "language": "en",               # [str] UI language (for v1.6+)
    }

    def __init__(self, filename: str = "settings.json"):
        """
        Initializes settings by loading the file or creating defaults.
        :param filename: The name of the settings file.
        """
        self.filename = Path(filename)
        self.data = self.DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        """
        Loads settings from the JSON file. Creates the file if it doesn't exist.
        """
        if not self.filename.exists():
            logger.info(f"Settings file not found. Creating default: {self.filename}")
            self._save()
            return

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Merge loaded data with defaults (ensures new settings are added)
            self.data.update(loaded_data)
            logger.info("Settings loaded successfully.")
            
        except json.JSONDecodeError:
            logger.error(f"Settings file is corrupted. Using default settings.")
            self._save() # Overwrite with defaults to fix corruption
        except Exception as e:
            logger.error(f"Error loading settings: {e}. Using defaults.")

    def _save(self):
        """
        Saves the current settings to the JSON file.
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            logger.debug(f"Settings saved to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str):
        """
        Retrieves a setting value.
        """
        return self.data.get(key)

    def set(self, key: str, value):
        """
        Sets a setting value and saves the file.
        """
        if key in self.data:
            self.data[key] = value
            self._save()
        else:
            logger.warning(f"Attempted to set unknown setting key: {key}")