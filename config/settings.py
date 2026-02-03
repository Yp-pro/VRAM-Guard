import json
import logging
import winreg
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings:
    DEFAULT_SETTINGS = {
        "vram_t1_threshold": 92,
        "vram_t2_panic_threshold": 105,
        "cool_down_time_s": 3.0,
        "work_time_s": 2.0,
        "lhm_port": 8085,
        "enable_notifications": True,
        "enable_audio_alert": True,
        "enable_autostart": False
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.filename = project_root / "settings.json"
        self.data = self.DEFAULT_SETTINGS.copy()
        self._load()
        # Refresh autostart path on every init if enabled
        if self.get("enable_autostart"):
            self.set_autostart(True)

    def _load(self):
        if not self.filename.exists() or self.filename.stat().st_size == 0:
            self._save()
            return
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.data.update(json.load(f))
        except Exception as e:
            logger.error(f"Settings load error: {e}. Resetting to defaults.")
            self._save()

    def _save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Settings save error: {e}")

    def get(self, key: str):
        return self.data.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value):
        self.data[key] = value
        self._save()
        
        # Special handling for autostart toggle
        if key == "enable_autostart":
            self.set_autostart(value)

    def set_autostart(self, enabled: bool):
        """Manages Windows Registry for autostart."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "VRAMGuard"
        # Path to the launcher bat
        launcher_path = str(self.project_root / "Start_Protection.bat")
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{launcher_path}"')
                logger.info("Autostart enabled in registry.")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("Autostart disabled in registry.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to modify registry: {e}")
