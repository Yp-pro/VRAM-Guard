import logging
import psutil
import subprocess
import os
import ctypes
from typing import List, Optional

logger = logging.getLogger(__name__)

class Throttler:
    """
    Manages the suspension and resumption of GPU-intensive processes.
    Requires Administrator privileges.
    """
    
    def __init__(self):
        self._is_admin = self._check_admin()
        self.throttled_pids: List[int] = []
        
        if not self._is_admin:
            logger.critical("Throttler initialized without Administrator privileges. Suspend/Resume will fail.")

    def _check_admin(self) -> bool:
        """
        Checks if the script is running with Administrator privileges on Windows.
        """
        try:
            # Check if the process has elevated privileges (Windows specific)
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            logger.error(f"Failed to check admin status: {e}. Assuming non-admin.")
            return False

    def _get_gpu_pids(self) -> List[int]:
        """
        Uses nvidia-smi to find the PIDs of processes currently using the GPU.
        
        :return: List of PIDs.
        """
        pids = []
        try:
            # Command to query PIDs and memory usage
            cmd = ["nvidia-smi", "--query-compute-apps=pid,gpu_bus_id", "--format=csv,noheader"]
            
            # Use a short timeout to prevent hanging if the GPU is asleep/unresponsive
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        # Format is typically: pid, gpu_bus_id
                        pid_str = line.split(',')[0].strip()
                        pids.append(int(pid_str))
                    except ValueError:
                        continue
            
            # Filter out the current process's PID to prevent self-suspension
            if os.getpid() in pids:
                pids.remove(os.getpid())
                
            logger.debug(f"Detected GPU PIDs: {pids}")
            return pids
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"nvidia-smi failed (Code {e.returncode}). Is NVIDIA driver installed? Output: {e.stderr.strip()}")
        except FileNotFoundError:
            logger.critical("nvidia-smi not found. Ensure it is in PATH.")
        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi timed out. GPU might be unresponsive.")
        except Exception as e:
            logger.error(f"Error during PID detection: {e}")
            
        return []

    def _control_pids(self, pids: List[int], action: str):
        """
        Suspends or resumes a list of processes using psutil.
        :param pids: List of PIDs to control.
        :param action: 'suspend' or 'resume'.
        """
        if not self._is_admin:
            logger.error(f"Cannot perform '{action}'. Missing admin rights.")
            return

        for pid in pids:
            try:
                process = psutil.Process(pid)
                if action == 'suspend':
                    process.suspend()
                    self.throttled_pids.append(pid)
                    logger.debug(f"Suspended PID {pid} ({process.name()})")
                elif action == 'resume':
                    process.resume()
                    if pid in self.throttled_pids:
                        self.throttled_pids.remove(pid)
                    logger.debug(f"Resumed PID {pid} ({process.name()})")
            except psutil.NoSuchProcess:
                logger.warning(f"Process with PID {pid} not found (already terminated).")
            except psutil.AccessDenied:
                logger.error(f"Access denied to PID {pid}. Cannot {action}.")
            except Exception as e:
                logger.error(f"Error during {action} of PID {pid}: {e}")

    def suspend_gpu_processes(self):
        """
        Finds all GPU processes and suspends them.
        """
        pids_to_throttle = self._get_gpu_pids()
        if not pids_to_throttle:
            logger.info("No GPU processes found to suspend.")
            return
            
        self._control_pids(pids_to_throttle, 'suspend')

    def resume_all_processes(self):
        """
        Resumes all processes that were previously suspended by the throttler.
        """
        if not self.throttled_pids:
            logger.info("No processes are currently suspended.")
            return
            
        # Create a copy of the list to safely iterate and modify
        pids_to_resume = self.throttled_pids[:]
        self._control_pids(pids_to_resume, 'resume')
        
    def emergency_kill(self):
        """
        Terminates all GPU-intensive processes (Panic Button).
        """
        pids_to_kill = self._get_gpu_pids()
        if not pids_to_kill:
            logger.info("No GPU processes found to kill.")
            return
            
        logger.critical(f"PANIC MODE: Terminating PIDs: {pids_to_kill}")
        for pid in pids_to_kill:
            try:
                process = psutil.Process(pid)
                process.terminate()
                logger.critical(f"Terminated PID {pid} ({process.name()})")
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                logger.error(f"Failed to kill PID {pid}: {e}")