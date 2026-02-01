import logging
import time
from typing import TYPE_CHECKING, Optional

# Type hints for external classes (to avoid circular imports)
if TYPE_CHECKING:
    from config.settings import Settings
    from config.license_manager import LicenseManager
    from core.lhm_client import LHMClient
    from core.process_throttler import Throttler

logger = logging.getLogger(__name__)

class VRAMGuardCore:
    """
    The main logic core for VRAM Guard. 
    Manages monitoring, adaptive polling, throttling state, and panic mode.
    """
    
    # --- CONSTANTS ---
    DEFAULT_POLL_LOW = 60.0  # [s] Polling interval when VRAM is cool (<60C)
    DEFAULT_POLL_HIGH = 1.0  # [s] Polling interval when VRAM is hot (>90C)
    PANIC_DURATION_S = 10.0  # [s] Time allowed above T2 before emergency kill
    
    def __init__(self, settings: 'Settings', license_manager: 'LicenseManager', 
                 lhm_client: 'LHMClient', throttler: 'Throttler'):
        
        self.settings = settings
        self.license_manager = license_manager
        self.lhm_client = lhm_client
        self.throttler = throttler
        
        self.is_running = True
        self.is_throttling = False
        self.panic_start_time: Optional[float] = None
        
        logger.info("Core initialized. Starting LHM check...")
        if not self.lhm_client.check_and_start():
            logger.critical("Failed to start LHM. Monitoring will be disabled.")
            self.is_running = False

    def _get_current_temp(self) -> Optional[float]:
        """
        Retrieves the current VRAM temperature.
        """
        temp, gpu_name = self.lhm_client.get_vram_temp()
        
        if temp is None:
            # Check LHM status if data retrieval fails
            if not self.lhm_client.check_and_start():
                logger.warning("LHM data retrieval failed and restart failed.")
            return None
            
        return temp

    def _handle_throttling(self, temp: float):
        """
        Manages the Pulse Throttling state based on T1 threshold.
        """
        T1 = self.settings.get('vram_t1_threshold')
        COOL_DOWN_TIME = self.settings.get('cool_down_time_s')
        WORK_TIME = self.settings.get('work_time_s')
        
        if temp >= T1 and not self.is_throttling:
            # Start Throttling Cycle
            logger.warning(f"VRAM {temp}°C >= T1 {T1}°C. Activating Pulse Throttling.")
            self.is_throttling = True
            
        if self.is_throttling:
            # SUSPEND phase
            self.throttler.suspend_gpu_processes()
            # NOTE: In v1.6, we would add Windows Toast notification here.
            time.sleep(COOL_DOWN_TIME)
            
            # RESUME phase
            self.throttler.resume_all_processes()
            time.sleep(WORK_TIME)
            
            # Check if VRAM is cool enough to stop throttling
            current_temp = self._get_current_temp()
            if current_temp is not None and current_temp < T1 - 2: # Stop 2 degrees below T1
                logger.info(f"VRAM {current_temp}°C < T1-2. Deactivating Pulse Throttling.")
                self.is_throttling = False

    def _handle_panic_mode(self, temp: float):
        """
        Manages the Panic Button logic based on T2 threshold.
        """
        T2 = self.settings.get('vram_t2_panic_threshold')
        
        if temp >= T2:
            if self.panic_start_time is None:
                # Start the panic timer
                self.panic_start_time = time.time()
                logger.critical(f"VRAM {temp}°C >= T2 {T2}°C. Panic timer started.")
                
            elapsed = time.time() - self.panic_start_time
            
            if elapsed >= self.PANIC_DURATION_S:
                # Emergency Kill
                logger.critical(f"PANIC MODE ACTIVATED. VRAM at {temp}°C for {elapsed:.1f}s.")
                self.throttler.emergency_kill()
                self.is_running = False # Stop the core loop after killing processes
                
        elif self.panic_start_time is not None and temp < T2:
            # VRAM cooled down before panic threshold was reached
            logger.warning(f"VRAM cooled down to {temp}°C. Panic timer reset.")
            self.panic_start_time = None

    def run_monitoring_loop(self):
        """
        The main, continuous monitoring loop running in a separate thread.
        """
        logger.info("VRAM Guard Core loop started.")
        
        while self.is_running:
            temp = self._get_current_temp()
            
            if temp is None:
                # LHM failed or sensor not found. Wait and retry.
                time.sleep(self.DEFAULT_POLL_LOW)
                continue

            # 1. Panic Mode Check (Highest Priority)
            self._handle_panic_mode(temp)
            if not self.is_running: break # Exit if emergency kill was performed

            # 2. Throttling Check
            self._handle_throttling(temp)
            
            # 3. Adaptive Polling (Only if not in active throttling cycle)
            if not self.is_throttling:
                if temp < 60:
                    sleep_time = self.DEFAULT_POLL_LOW
                elif temp < self.settings.get('vram_t1_threshold'):
                    sleep_time = self.DEFAULT_POLL_HIGH
                else:
                    sleep_time = self.DEFAULT_POLL_HIGH
                    
                time.sleep(sleep_time)
                
        logger.warning("VRAM Guard Core loop terminated.")
        self.lhm_client.stop() # Ensure LHM is stopped if core exits