import sys
import os
import logging
import logging.handlers
import threading
import time
from pathlib import Path

# Import core modules
from config.settings import Settings
from config.license_manager import LicenseManager
from core.lhm_client import LHMClient
from core.process_throttler import Throttler
from core.vram_guard_core import VRAMGuardCore

# --- GLOBAL CONFIGURATION ---
LOG_FILE = "vram_guard.log"
APP_NAME = "VRAM Guard"
STARTUP_DELAY_S = 30 # Delay to avoid driver conflicts during Windows boot

def setup_logging():
    """
    Configures the logging system to write to a file and console.
    """
    log_path = Path(LOG_FILE)
    
    # File handler: limit size to 1MB, keep 1 backup
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1024 * 1024, backupCount=1, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler (only shows INFO/WARNING/ERROR)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.setLevel(logging.INFO)

    # Root logger setup
    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
    logging.getLogger('urllib3').setLevel(logging.WARNING) # Suppress noisy requests logs

def main():
    """
    Main entry point of the application. Initializes all core components.
    """
    setup_logging()
    logger = logging.getLogger(APP_NAME)
    
    logger.info(f"--- {APP_NAME} v1.4.0 (Core Stability) Started ---")
    
    # 1. Initialization
    settings = Settings()
    license_manager = LicenseManager()
    
    logger.info(f"VRAM T1 Threshold: {settings.get('vram_t1_threshold')}°C")
    logger.info(f"Pro Features Active: {license_manager.is_pro_active()}")
    
    # 2. Startup Delay (Critical for driver stability)
    logger.info(f"Waiting {STARTUP_DELAY_S} seconds for system/driver warm-up...")
    time.sleep(STARTUP_DELAY_S)
    logger.info("Startup delay complete. Starting core services.")
    
    # 3. Component Instantiation
    lhm_client = LHMClient()
    throttler = Throttler()
    
    # Check if we have admin rights before starting the core loop
    if not throttler._is_admin:
        logger.critical("Application lacks Administrator privileges. Throttling will fail.")
        logger.critical("Please re-run Start_Protection.bat as Administrator.")
        # NOTE: In v1.5, we would add a Windows Toast notification here.
        # We continue running to allow LHM monitoring, but throttling is disabled.
        # For now, we exit gracefully.
        time.sleep(5)
        sys.exit(1)
        
    # 4. Core Logic Setup
    core = VRAMGuardCore(
        settings=settings,
        license_manager=license_manager,
        lhm_client=lhm_client,
        throttler=throttler
    )
    
    # 5. Start Core Logic in a separate thread
    core_thread = threading.Thread(
        target=core.run_monitoring_loop, 
        daemon=True
    )
    core_thread.start()
    
    # 6. Start UI (Placeholder - Tkinter/pystray will go here)
    logger.info("Starting System Tray Icon (Placeholder)...")
    
    # Keep the main thread alive (this would be the GUI loop in a real app)
    try:
        while True:
            time.sleep(1)
            if not core_thread.is_alive():
                logger.error("Core monitoring thread died unexpectedly!")
                break
    except KeyboardInterrupt:
        logger.info("Application stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Unhandled exception in main thread: {e}")
    finally:
        # Clean up LHM process on exit
        lhm_client.stop()
        logger.info("Application terminated gracefully.")

if __name__ == "__main__":
    # Ensure the script is run from the correct directory for path resolution
    if getattr(sys, 'frozen', False):
        # Running as a compiled executable
        pass
    else:
        # Running as a script: change directory to script location
        os.chdir(Path(__file__).parent)
        
    main()