import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class VRAMGuardCore:
    """
    The main logic core for VRAM Guard v1.4.1.
    Handles monitoring, adaptive polling, pulse throttling, and panic mode.
    Provides real-time state for the UI (Tray Icon).
    """
    
    # --- CONSTANTS ---
    PANIC_DURATION_S = 10.0  # Time allowed above T2 before emergency kill
    
    def __init__(self, settings, license_manager, lhm_client, throttler):
        """
        Initializes the core with required components.
        """
        self.settings = settings
        self.license_manager = license_manager
        self.lhm_client = lhm_client
        self.throttler = throttler
        
        # State variables
        self.is_running = True
        self.is_throttling = False
        self.current_temp: Optional[float] = None
        self.panic_start_time: Optional[float] = None
        self.first_run = True

    def _handle_panic_mode(self, temp: float):
        """
        Monitors T2 threshold and performs emergency kill if necessary.
        """
        T2 = self.settings.get('vram_t2_panic_threshold')
        
        if temp >= T2:
            if self.panic_start_time is None:
                self.panic_start_time = time.time()
                logger.critical(f"CRITICAL: VRAM {temp}°C >= T2 {T2}°C! Panic timer started.")
                
            elapsed = time.time() - self.panic_start_time
            if elapsed >= self.PANIC_DURATION_S:
                logger.critical(f"PANIC ACTIVATED: VRAM at {temp}°C for {elapsed:.1f}s. Killing processes!")
                self.throttler.emergency_kill()
                # We don't stop the core, but we reset the timer
                self.panic_start_time = None
        else:
            if self.panic_start_time is not None:
                logger.info(f"Panic aborted. VRAM cooled down to {temp}°C.")
                self.panic_start_time = None

    def _perform_throttling_cycle(self, temp: float):
        """
        Executes one cycle of Suspend -> Sleep -> Resume -> Sleep.
        """
        T1 = self.settings.get('vram_t1_threshold')
        COOL_TIME = self.settings.get('cool_down_time_s')
        WORK_TIME = self.settings.get('work_time_s')

        self.is_throttling = True
        logger.warning(f"THROTTLING: {temp}°C >= {T1}°C. Suspending GPU processes...")
        
        # Phase 1: Suspend
        self.throttler.suspend_gpu_processes()
        time.sleep(COOL_TIME)
        
        # Phase 2: Resume
        logger.info(f"Resume: Cooling phase over. Resuming work for {WORK_TIME}s...")
        self.throttler.resume_all_processes()
        time.sleep(WORK_TIME)

    def run_monitoring_loop(self):
        """
        Continuous monitoring loop. Should be run in a separate thread.
        """
        logger.info("VRAM Guard Core loop started.")
        wait_count = 0

        while self.is_running:
            # 1. Ensure LHM is running and responding
            if not self.lhm_client.check_and_start():
                logger.warning("LHM not available. Retrying in 10s...")
                time.sleep(10)
                continue

            # 2. Fetch current temperature
            temp, sensor_name = self.lhm_client.get_vram_temp()
            self.current_temp = temp # Shared with UI

            if temp is None:
                wait_count += 1
                if wait_count % 5 == 0:
                    logger.info("Waiting for VRAM sensor data from LHM...")
                time.sleep(2)
                continue

            # 3. Handle first successful detection
            if self.first_run:
                logger.info(f"SUCCESS: Linked to sensor '{sensor_name}'")
                logger.info(f"Initial VRAM Temp: {temp}°C")
                self.first_run = False
                wait_count = 0

            # 4. Check Panic Threshold (T2)
            self._handle_panic_mode(temp)

            # 5. Check Throttling Threshold (T1)
            T1 = self.settings.get('vram_t1_threshold')
            if temp >= T1:
                self._perform_throttling_cycle(temp)
            else:
                self.is_throttling = False
                
                # 6. Adaptive Polling (Idle Optimization)
                # If cool, check less often to let GPU sleep (D3 Cold)
                if temp < 60:
                    sleep_time = 30.0 
                elif temp < 80:
                    sleep_time = 5.0
                else:
                    sleep_time = 1.0
                
                time.sleep(sleep_time)

        logger.info("VRAM Guard Core loop stopped.")