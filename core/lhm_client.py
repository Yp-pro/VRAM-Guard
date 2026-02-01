import logging
import requests
import subprocess
import time
import socket
import json
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class LHMClient:
    """
    Manages the LibreHardwareMonitor (LHM) process and communicates with its API.
    Handles dynamic port assignment and VRAM temperature retrieval.
    """
    
    LHM_EXE_PATH = Path("resources") / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe"
    LHM_PORT_RANGE = (8085, 8095)
    
    def __init__(self):
        self.port: Optional[int] = None
        self.lhm_process: Optional[subprocess.Popen] = None
        self.api_url: str = ""
        
    def _find_free_port(self) -> Optional[int]:
        """
        Finds the first available port in the defined range.
        """
        for port in range(*self.LHM_PORT_RANGE):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        logger.error(f"No free port found in range {self.LHM_PORT_RANGE}")
        return None

    def _start_lhm(self) -> bool:
        """
        Starts the LibreHardwareMonitor process with the assigned port.
        LHM must be configured to run with WebServer enabled.
        """
        if not self.LHM_EXE_PATH.exists():
            logger.critical(f"LHM executable not found at {self.LHM_EXE_PATH}")
            # NOTE: In v1.5, we would add automatic download here.
            return False

        self.port = self._find_free_port()
        if not self.port:
            return False

        self.api_url = f"http://127.0.0.1:{self.port}/data.json"
        
        # Command to run LHM with web server enabled on the found port
        # NOTE: LHM requires configuration file setup to enable WebServer.
        # Assuming the config is set up by the user/installer to run the web server.
        cmd = [
            str(self.LHM_EXE_PATH),
            f"/webserver:start",
            f"/webserverport:{self.port}"
        ]
        
        try:
            # Use DETACHED_PROCESS to run LHM in the background without a console window
            self.lhm_process = subprocess.Popen(
                cmd, 
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            logger.info(f"LHM started on port {self.port} (PID: {self.lhm_process.pid})")
            time.sleep(3) # Give LHM time to initialize the web server
            return True
        except Exception as e:
            logger.critical(f"Failed to start LHM: {e}")
            return False

    def check_and_start(self) -> bool:
        """
        Checks if LHM is running and starts it if necessary.
        """
        if self.lhm_process and self.lhm_process.poll() is None:
            logger.debug("LHM process is already running.")
            return True
        
        if self.lhm_process and self.lhm_process.poll() is not None:
            logger.warning("LHM process has crashed. Attempting restart.")
            
        return self._start_lhm()

    def get_vram_temp(self) -> Tuple[Optional[float], Optional[str]]:
        """
        Retrieves the VRAM temperature from the LHM API.
        :return: Tuple of (temperature, gpu_name) or (None, None) on failure.
        """
        if not self.port:
            logger.warning("LHM port not set. Cannot retrieve data.")
            return None, None

        try:
            # Add a short timeout to prevent the monitoring thread from hanging
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # --- JSON PARSING LOGIC (Simplified for VRAM GDDR6) ---
            # LHM structure: Children -> Children (GPU) -> Children (Sensors)
            
            for child in data.get('Children', []):
                if child.get('Text') == 'NVIDIA':
                    for gpu in child.get('Children', []):
                        # Assuming the first NVIDIA GPU is the target
                        gpu_name = gpu.get('Text')
                        for sensor_group in gpu.get('Children', []):
                            if sensor_group.get('Text') == 'Temperatures':
                                for sensor in sensor_group.get('Children', []):
                                    # Look for 'GPU Memory Junction Temperature' or similar VRAM sensor
                                    if 'Memory' in sensor.get('Text', '') and sensor.get('Value'):
                                        temp = float(sensor['Value'].split()[0])
                                        logger.debug(f"VRAM Temp: {temp}°C from {gpu_name}")
                                        return temp, gpu_name
            
            logger.warning("VRAM temperature sensor not found in LHM output.")
            return None, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"LHM API request failed: {e}")
            self.lhm_process = None # Mark as potentially crashed
            return None, None
        except Exception as e:
            logger.error(f"Error parsing LHM data: {e}")
            return None, None
            
    def stop(self):
        """
        Terminates the LHM process.
        """
        if self.lhm_process and self.lhm_process.poll() is None:
            try:
                self.lhm_process.terminate()
                self.lhm_process.wait(timeout=5)
                logger.info("LHM process terminated.")
            except Exception as e:
                logger.error(f"Failed to terminate LHM process: {e}")