import sys
import os
import logging
import logging.handlers
import threading
import time
import ctypes
from pathlib import Path

# Import core modules
from config.settings import Settings
from config.license_manager import LicenseManager
from core.lhm_client import LHMClient
from core.process_throttler import Throttler
from core.vram_guard_core import VRAMGuardCore
from ui.tray_icon import VRAMGuardTray
from ui.settings_window import SettingsWindow

APP_NAME = "VRAM Guard"

def hide_console():
    """
    Hides the console window if the script is running with a visible terminal.
    """
    try:
        # Get handle to the console window
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # ShowWindow with command 0 (SW_HIDE)
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

def setup_logging(project_root: Path):
    """
    Configures the logging system.
    """
    log_path = project_root / "vram_guard.log"
    
    # Rotating file handler (1MB limit)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1024 * 1024, backupCount=1, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))

    # Root logger setup
    logging.basicConfig(level=logging.INFO, handlers=[file_handler])
    # Suppress noisy external logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def main():
    """
    Main entry point for VRAM Guard v1.4.1.
    """
    # 0. Hide console immediately for stealth operation
    hide_console()

    # 1. Path and Environment Setup
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    setup_logging(project_root)
    logger = logging.getLogger(APP_NAME)
    logger.info(f"--- {APP_NAME} v1.4.1 Started ---")

    # 2. Initialize Components
    settings = Settings(project_root)
    license_manager = LicenseManager()
    lhm_client = LHMClient(project_root)
    throttler = Throttler()

    # 3. Admin Rights Check
    if not throttler._is_admin:
        logger.critical("Application requires Administrator privileges to manage processes.")
        # Without console, user needs a GUI message
        ctypes.windll.user32.MessageBoxW(
            0, "VRAM Guard requires Administrator privileges.\nPlease run Start_Protection.bat as Admin.", 
            "Critical Error", 0x10
        )
        sys.exit(1)

    # 4. Core Logic Setup
    core = VRAMGuardCore(settings, license_manager, lhm_client, throttler)
    
    # 5. Start Core Monitoring in background thread
    core_thread = threading.Thread(target=core.run_monitoring_loop, daemon=True)
    core_thread.start()

    # 6. UI Callbacks
    def on_exit(icon, item):
        logger.info("Exit requested by user.")
        icon.stop()
        lhm_client.stop()
        # Ensure all threads are killed
        os._exit(0)

    def on_settings(icon, item):
        logger.debug("Opening settings window.")
        SettingsWindow(settings).show()

    # 7. Initialize and Run Tray Icon
    tray = VRAMGuardTray(project_root, settings, core, on_exit, on_settings)

    # UI Update Loop (Updates tray info every 2 seconds)
    def update_ui_loop():
        while True:
            tray.update_state()
            time.sleep(2)

    threading.Thread(target=update_ui_loop, daemon=True).start()

    # Run Tray Icon (This blocks the main thread)
    try:
        tray.run()
    except Exception as e:
        logger.critical(f"Tray icon crashed: {e}")
    finally:
        lhm_client.stop()

if __name__ == "__main__":
    main()