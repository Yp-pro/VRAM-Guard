import logging
import requests
import subprocess
import time
import socket
import zipfile
import io
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

class LHMClient:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.lhm_dir = self.project_root / "resources" / "LibreHardwareMonitor"
        self.lhm_exe = self.lhm_dir / "LibreHardwareMonitor.exe"
        self.lhm_config = self.lhm_dir / "LibreHardwareMonitor.config"
        self.port: Optional[int] = None
        self.lhm_process: Optional[subprocess.Popen] = None
        self.api_url: str = ""

    def _cleanup_old_instances(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "LibreHardwareMonitor.exe", "/T"], 
                           capture_output=True, check=False)
            time.sleep(2)
        except: pass

    def _create_config(self, port: int):
        xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <appSettings>
    <add key="startMinMenuItem" value="true" />
    <add key="runWebServerMenuItem" value="true" />
    <add key="listenerPort" value="{port}" />
    <add key="listenerIp" value="0.0.0.0" />
    <add key="updateIntervalMenuItem" value="1" />
  </appSettings>
</configuration>"""
        try:
            with open(self.lhm_config, "w", encoding="utf-8") as f:
                f.write(xml_content)
        except Exception as e:
            logger.error(f"Config error: {e}")

    def _download_lhm(self) -> bool:
        logger.info("Downloading LHM v0.9.5...")
        try:
            self.lhm_dir.mkdir(parents=True, exist_ok=True)
            headers = {'User-Agent': 'VRAM-Guard/1.4.1'}
            response = requests.get("https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.5/LibreHardwareMonitor.zip", headers=headers, timeout=30)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(self.lhm_dir)
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def _find_free_port(self) -> Optional[int]:
        for port in range(8085, 8095):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError: continue
        return None

    def _start_lhm(self) -> bool:
        if not self.lhm_exe.exists():
            if not self._download_lhm(): return False
        self._cleanup_old_instances()
        self.port = self._find_free_port()
        if not self.port: return False
        self._create_config(self.port)
        self.api_url = f"http://127.0.0.1:{self.port}/data.json"
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 

        try:
            self.lhm_process = subprocess.Popen(
                [str(self.lhm_exe)], cwd=str(self.lhm_dir),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
            logger.info(f"LHM process started (PID: {self.lhm_process.pid})")
            
            for i in range(15):
                try:
                    requests.get(self.api_url, timeout=1)
                    logger.info("LHM API is online.")
                    return True
                except: 
                    if i % 5 == 0: logger.info(f"Waiting for API... ({i}s)")
                    time.sleep(2)
            return False
        except Exception as e:
            logger.error(f"LHM start error: {e}")
            return False

    def _extract_float(self, value_str: str) -> Optional[float]:
        """
        Extracts a float number from a string like '64.5 °C' or '64,5 °C'.
        Uses regex for maximum reliability.
        """
        try:
            # Find the first sequence of digits, dots, or commas
            match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", value_str)
            if match:
                num_str = match.group(1).replace(',', '.')
                return float(num_str)
        except Exception as e:
            logger.debug(f"Failed to parse value '{value_str}': {e}")
        return None

    def _find_all_sensors(self, node: dict, found_sensors: list):
        text = node.get('Text', '')
        value = node.get('Value', '')
        children = node.get('Children', [])

        # We look for anything that looks like a temperature
        if value and ("°C" in value or "C" in value):
            found_sensors.append({'name': text, 'value': value})

        for child in children:
            self._find_all_sensors(child, found_sensors)

    def get_vram_temp(self) -> Tuple[Optional[float], str]:
        if not self.api_url: return None, "Unknown"
        try:
            response = requests.get(self.api_url, timeout=1)
            data = response.json()
            
            sensors = []
            self._find_all_sensors(data, sensors)
            
            # Search for the VRAM sensor (prioritizing "Junction" as seen in your screenshot)
            for s in sensors:
                name = s['name'].lower()
                # Match "GPU Memory Junction" or "GPU Memory" or just "Memory" if it's a GPU sensor
                if "memory" in name and ("junction" in name or "gpu" in name):
                    val = self._extract_float(s['value'])
                    if val is not None:
                        return val, s['name']

            # Fallback: Any sensor with "Memory"
            for s in sensors:
                if "memory" in s['name'].lower():
                    val = self._extract_float(s['value'])
                    if val is not None:
                        return val, s['name']
                
            return None, "Not Found"
        except Exception as e:
            return None, str(e)

    def check_and_start(self) -> bool:
        if self.lhm_process and self.lhm_process.poll() is None:
            return True
        return self._start_lhm()

    def stop(self):
        if self.lhm_process:
            try: self.lhm_process.terminate()
            except: pass