import logging
from PIL import Image
import pystray
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class VRAMGuardTray:
    def __init__(self, project_root, settings, core, on_exit_callback, on_settings_callback):
        self.project_root = project_root
        self.settings = settings
        self.core = core
        self.on_exit = on_exit_callback
        self.on_settings = on_settings_callback
        
        self.icon_dir = self.project_root / "resources" / "icons"
        self.icon = None
        self._setup_tray()

    def _get_icon_image(self, name="norm.ico"):
        path = self.icon_dir / name
        if not path.exists():
            # Fallback to a simple colored square if icon is missing
            return Image.new('RGB', (64, 64), color=(0, 128, 255))
        return Image.open(path)

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Settings", self.on_settings),
            pystray.MenuItem("Exit", self.on_exit)
        )
        
        self.icon = pystray.Icon(
            "VRAM Guard", 
            self._get_icon_image("norm.ico"), 
            "VRAM Guard: Monitoring...", 
            menu
        )

    def update_state(self):
        """Updates icon and tooltip based on current core state."""
        if not self.icon: return
        
        temp = self.core.current_temp if self.core.current_temp else 0
        status = "Throttling!" if self.core.is_throttling else "Safe"
        
        # Change icon based on throttling
        icon_name = "fire.ico" if self.core.is_throttling else "norm.ico"
        self.icon.icon = self._get_icon_image(icon_name)
        self.icon.title = f"VRAM: {temp}°C [{status}]"

    def run(self):
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()