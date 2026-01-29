import os
import sys
import time
import threading
import subprocess
import psutil
import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image
import pystray

# ==========================
# CONFIGURATION
# ==========================

VRAM_T1 = 92         # Threshold to start cooling (Celsius)
STARTUP_DELAY = 30   # Seconds to wait after Windows boot
POLL_INTERVAL = 1    # Base check frequency (seconds)

# Pulse Throttling Timings
COOL_DOWN_TIME = 3.0 # Suspend duration (seconds)
WORK_TIME = 2.0      # Resume duration (seconds)

LHM_URL = "http://localhost:8085/data.json"
LHM_PROCESS_NAME = "LibreHardwareMonitor.exe"

# Processes to NEVER throttle
PROCESS_EXCLUSIONS = {
    "explorer.exe", "dwm.exe", "csrss.exe", "wininit.exe", 
    "taskmgr.exe", "system", "registry", "librehardwaremonitor.exe",
    "nvdisplay.container.exe", "nvidia share.exe", "nvidia broadcast.exe"
}

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
ICONS_DIR = os.path.join(BASE_DIR, "icons")
LHM_PATH = os.path.join(BASE_DIR, "LibreHardwareMonitor", "LibreHardwareMonitor.exe")

# ==========================
# GRAPHICS
# ==========================

def create_fallback_icon(color):
    return Image.new('RGB', (64, 64), color)

def load_icon(name, color):
    path = os.path.join(ICONS_DIR, name)
    if os.path.exists(path):
        return Image.open(path).convert("RGBA")
    return create_fallback_icon(color)

ICON_NORM  = load_icon("norm.ico", "green")
ICON_FIRE  = load_icon("fire.ico", "red")
ICON_PAUSE = load_icon("pause.ico", "gray")
ICON_WAIT  = load_icon("pause.ico", "yellow")

# ==========================
# SYSTEM LOGIC
# ==========================

def is_lhm_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == LHM_PROCESS_NAME:
                return True
        except: pass
    return False

def launch_lhm():
    if os.path.exists(LHM_PATH):
        work_dir = os.path.dirname(LHM_PATH)
        subprocess.Popen([LHM_PATH], cwd=work_dir, shell=True)
        return True
    return False

def get_gpu_pids():
    """Heavy call: used only during overheating to identify targets."""
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, creationflags=flags
        ).decode().splitlines()
        
        pids = []
        for line in out:
            pid_str = line.strip()
            if pid_str.isdigit():
                pids.append(int(pid_str))
        return pids
    except:
        return []

def get_vram_temp():
    """Light call: requests JSON data from LHM web server."""
    try:
        response = requests.get(LHM_URL, timeout=1)
        data = response.json()
        def find_memory_temp(node):
            if node.get("ImageURL") == "images_icon/nvidia.png" or "nvidia" in node.get("Text", "").lower():
                for child in node.get("Children", []):
                    if child.get("Text") == "Temperatures":
                        for sensor in child.get("Children", []):
                            if "memory" in sensor.get("Text", "").lower():
                                return float(sensor.get("Value", "0").replace(",", ".").split()[0])
            for child in node.get("Children", []):
                res = find_memory_temp(child)
                if res is not None: return res
            return None
        return find_memory_temp(data)
    except: return None

# ==========================
# CORE CLASS
# ==========================

class VRAMGuard:
    def __init__(self):
        self.T1 = VRAM_T1
        self.paused = False
        self.throttling = False
        self.current_temp = 0
        self.lhm_status = "Initializing..."
        self.is_warming_up = True
        self.last_action = "Waiting..."
        self.current_sleep = 1

        self.icon = pystray.Icon("VRAM Guard", ICON_WAIT, menu=pystray.Menu(
            pystray.MenuItem("Settings", self.open_settings),
            pystray.MenuItem("Exit", self.stop)
        ))

    def update_icon(self):
        if self.is_warming_up:
            self.icon.icon = ICON_WAIT
            self.icon.title = f"VRAM Guard: Warming up... {self.lhm_status}"
            return
        
        self.icon.icon = ICON_FIRE if self.throttling else (ICON_PAUSE if self.paused else ICON_NORM)
        status_text = f"Polling: {self.current_sleep}s" if not self.throttling else "COOLING ACTIVE"
        self.icon.title = f"VRAM: {self.current_temp}°C | {status_text}"

    def control_apps(self, action, pids):
        if not pids: 
            self.last_action = "No GPU apps detected"
            return
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                if proc.name().lower() in PROCESS_EXCLUSIONS: continue
                
                if action == 'suspend':
                    proc.suspend()
                    self.last_action = f"PAUSED: {proc.name()}"
                else:
                    proc.resume()
                    self.last_action = f"RUNNING: {proc.name()}"
            except: continue

    def monitor(self):
        # Startup warm-up
        for i in range(STARTUP_DELAY, 0, -1):
            self.lhm_status = f"Wait {i}s"
            self.update_icon()
            time.sleep(1)
        
        self.is_warming_up = False
        self.lhm_status = "Active"

        while True:
            if not self.paused:
                # 1. Watchdog
                if not is_lhm_running():
                    self.last_action = "Restarting LHM..."
                    launch_lhm()
                    time.sleep(10)
                
                # 2. Adaptive Polling Logic
                temp = get_vram_temp()
                if temp is not None:
                    self.current_temp = int(temp)
                    
                    # Set sleep interval based on temperature
                    if self.current_temp < 60:
                        self.current_sleep = 60  # 1 minute
                    elif self.current_temp < 80:
                        self.current_sleep = 10  # 10 seconds
                    elif self.current_temp < 85:
                        self.current_sleep = 5   # 5 seconds
                    elif self.current_temp < 90:
                        self.current_sleep = 2   # 2 seconds
                    else:
                        self.current_sleep = 1   # 1 second (Danger zone)

                    # 3. Throttling Logic
                    if self.current_temp > self.T1:
                        self.throttling = True
                        self.update_icon()
                        
                        # Heavy call only when threshold exceeded
                        pids = get_gpu_pids()
                        
                        self.control_apps('suspend', pids)
                        time.sleep(COOL_DOWN_TIME)
                        self.control_apps('resume', pids)
                        
                        self.current_sleep = 1 # Immediate check after pulse
                    else:
                        self.throttling = False
                        self.last_action = "Monitoring..."
                else:
                    self.current_temp = 0
                    self.last_action = "LHM Connection Error"
                    self.current_sleep = 10
                
                self.update_icon()
            
            time.sleep(self.current_sleep)

    def open_settings(self, *_):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        root = tk.Tk()
        self.settings_window = root
        root.title("VRAM Guard Settings")
        root.geometry("400x320")
        root.resizable(False, False)

        app_icon_path = os.path.join(ICONS_DIR, "app.ico")
        if os.path.exists(app_icon_path):
            try: root.iconbitmap(app_icon_path)
            except: pass

        t1 = tk.IntVar(value=self.T1)
        
        ttk.Label(root, text="VRAM GUARD STATUS:", font=("Arial", 10, "bold")).pack(pady=5)
        self.gui_temp = ttk.Label(root, text="Temp: --", font=("Arial", 15))
        self.gui_temp.pack()
        self.gui_status = ttk.Label(root, text="Polling: --", foreground="blue")
        self.gui_status.pack()

        def update_gui():
            if not self.settings_window.winfo_exists(): return
            self.gui_temp.config(text=f"{self.current_temp}°C")
            status = f"Pulse Cooling Active" if self.throttling else f"Polling every {self.current_sleep}s"
            self.gui_status.config(text=status)
            root.after(1000, update_gui)
        update_gui()

        ttk.Label(root, text="Max VRAM Temp Threshold:").pack(pady=(20, 0))
        scale = ttk.Scale(root, from_=70, to=105, variable=t1, orient='horizontal')
        scale.pack(fill="x", padx=30)
        ttk.Label(root, textvariable=t1).pack()

        def apply():
            self.T1 = int(t1.get())
            root.destroy()
        ttk.Button(root, text="Apply", command=apply).pack(pady=20)
        root.mainloop()

    def stop(self, *_):
        self.paused = True
        pids = get_gpu_pids()
        for pid in pids:
            try: psutil.Process(pid).resume()
            except: pass
        self.icon.stop()
        os._exit(0)

    def run(self):
        threading.Thread(target=self.monitor, daemon=True).start()
        self.icon.run()

if __name__ == "__main__":
    VRAMGuard().run()