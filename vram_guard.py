# v1.4.0
import os
import sys
import time
import threading
import subprocess
import psutil
import requests
import tkinter as tk
import urllib.request
import zipfile
import shutil
import winsound
from tkinter import ttk
from PIL import Image
import pystray

# ==========================
# CONFIGURATION
# ==========================

VRAM_T1 = 92         # Threshold to start Pulse Cooling (Celsius)
PANIC_TEMP = 105     # CRITICAL Threshold for Emergency Kill (Celsius)
PANIC_TIMEOUT = 10   # Seconds to wait at >105°C before killing the process

STARTUP_DELAY = 30   # Seconds to wait after Windows boot
POLL_INTERVAL = 1    # Base check frequency

# Pulse Throttling Timings
COOL_DOWN_TIME = 3.0 # Suspend duration
WORK_TIME = 2.0      # Resume duration

# Monitoring Settings
LHM_PROCESS_NAME = "LibreHardwareMonitor.exe"
LHM_URL = "http://localhost:8085/data.json"
LHM_DOWNLOAD_URL = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.3/LibreHardwareMonitor-v0.9.3-net472.zip"

# Processes to NEVER throttle or kill
PROCESS_EXCLUSIONS = {
    "explorer.exe", "dwm.exe", "csrss.exe", "wininit.exe", 
    "taskmgr.exe", "system", "registry", "librehardwaremonitor.exe",
    "nvdisplay.container.exe", "nvidia share.exe", "nvidia broadcast.exe"
}

# Path Setup
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

ICONS_DIR = os.path.join(BASE_DIR, "icons")
LHM_DIR = os.path.join(BASE_DIR, "LibreHardwareMonitor")
LHM_PATH = os.path.join(LHM_DIR, "LibreHardwareMonitor.exe")

# ==========================
# GRAPHICS / UI HELPERS
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
# AUTO-SETUP LOGIC (LHM)
# ==========================

def ensure_lhm_exists():
    if os.path.exists(LHM_PATH): return True
    print(f"LHM not found. Downloading...")
    zip_path = os.path.join(BASE_DIR, "lhm.zip")
    try:
        urllib.request.urlretrieve(LHM_DOWNLOAD_URL, zip_path)
        if not os.path.exists(LHM_DIR): os.makedirs(LHM_DIR)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(LHM_DIR)
        os.remove(zip_path)
        if not os.path.exists(LHM_PATH):
            for root, dirs, files in os.walk(LHM_DIR):
                if LHM_PROCESS_NAME in files:
                    src_dir = root
                    if src_dir != LHM_DIR:
                        for item in os.listdir(src_dir):
                            shutil.move(os.path.join(src_dir, item), LHM_DIR)
                    break
        return True
    except Exception as e:
        print(f"Error downloading LHM: {e}")
        return False

def configure_lhm():
    config_path = os.path.join(LHM_DIR, "LibreHardwareMonitor.config")
    required_settings = {
        "HttpServerEnabled": "true",
        "HttpServerPort": "8085",
        "MinimizeToTray": "true",
        "MinimizeOnClose": "true",
        "ShowSystray": "true",
        "UpdateInterval": "2000",
        "MinUpdateInterval": "2000"
    }
    current_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        current_config[key] = val
        except: pass
    changed = False
    for key, val in required_settings.items():
        if current_config.get(key) != val:
            current_config[key] = val
            changed = True
    if changed or not os.path.exists(config_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                for key, val in current_config.items():
                    f.write(f"{key}={val}\n")
        except Exception as e: print(f"Config write error: {e}")

# ==========================
# SYSTEM & MONITORING LOGIC
# ==========================

def is_lhm_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == LHM_PROCESS_NAME: return True
        except: pass
    return False

def launch_lhm():
    if not ensure_lhm_exists(): return False
    configure_lhm()
    if os.path.exists(LHM_PATH):
        subprocess.Popen([LHM_PATH], cwd=LHM_DIR, shell=True)
        return True
    return False

def get_gpu_pids():
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, creationflags=flags
        ).decode().splitlines()
        pids = []
        for line in out:
            pid_str = line.strip()
            if pid_str.isdigit(): pids.append(int(pid_str))
        return pids
    except: return []

def get_vram_temp():
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
# MAIN APPLICATION CLASS
# ==========================

class VRAMGuard:
    def __init__(self):
        self.T1 = VRAM_T1
        self.PANIC_TEMP = PANIC_TEMP
        self.paused = False
        self.throttling = False
        self.current_temp = 0
        self.lhm_status = "Initializing..."
        self.is_warming_up = True
        self.last_action = "Waiting..."
        self.current_sleep = 1
        self.panic_start_time = None
        
        # User Preferences (defaults)
        self.enable_notifications = True
        self.enable_audio = True

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
        status_text = "COOLING ACTIVE" if self.throttling else f"Polling: {self.current_sleep}s"
        
        if self.panic_start_time:
             status_text = "⚠️ PANIC TIMER ACTIVE!"
             
        self.icon.title = f"VRAM: {self.current_temp}°C | {status_text}"

    def send_notification(self, title, message):
        """Sends a Windows Toast notification via pystray."""
        if self.enable_notifications:
            self.icon.notify(message, title)

    def play_panic_sound(self):
        """Plays a warning beep."""
        if self.enable_audio:
            # Frequency 1000Hz, Duration 500ms
            winsound.Beep(1000, 500)

    def control_apps(self, action, pids):
        if not pids: 
            self.last_action = "No GPU apps detected"
            return
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                if proc.name().lower() in PROCESS_EXCLUSIONS: continue
                
                if action == 'kill':
                    proc.kill()
                    self.last_action = f"KILLED: {proc.name()} (EMERGENCY)"
                elif action == 'suspend':
                    proc.suspend()
                    self.last_action = f"PAUSED: {proc.name()}"
                else:
                    proc.resume()
                    self.last_action = f"RUNNING: {proc.name()}"
            except: continue

    def monitor(self):
        for i in range(STARTUP_DELAY, 0, -1):
            self.lhm_status = f"Wait {i}s"
            self.update_icon()
            time.sleep(1)
        
        self.is_warming_up = False
        self.lhm_status = "Active"
        
        # State tracker to avoid spamming notifications
        was_throttling = False 

        while True:
            if not self.paused:
                # 1. Watchdog
                if not is_lhm_running():
                    self.last_action = "LHM offline. Launching..."
                    launch_lhm()
                    time.sleep(10)
                
                # 2. Get Data
                temp = get_vram_temp()
                if temp is not None:
                    self.current_temp = int(temp)
                    
                    # === PANIC BUTTON LOGIC ===
                    if self.current_temp >= self.PANIC_TEMP:
                        if self.panic_start_time is None:
                            self.panic_start_time = time.time()
                            self.send_notification("VRAM Guard CRITICAL", f"Temp reached {self.current_temp}°C! Preparing emergency kill.")
                        
                        # Audio Alert
                        self.play_panic_sound()
                        
                        elapsed_panic = time.time() - self.panic_start_time
                        self.last_action = f"CRITICAL TEMP! Killing in {int(PANIC_TIMEOUT - elapsed_panic)}s"
                        
                        if elapsed_panic > PANIC_TIMEOUT:
                            pids = get_gpu_pids()
                            self.control_apps('kill', pids)
                            self.send_notification("VRAM Guard", "Processes killed due to critical overheating.")
                            self.panic_start_time = None 
                            time.sleep(5) 
                    else:
                        self.panic_start_time = None
                    
                    # === ADAPTIVE POLLING ===
                    if self.current_temp < 60: self.current_sleep = 60
                    elif self.current_temp < 80: self.current_sleep = 10
                    elif self.current_temp < 85: self.current_sleep = 5
                    elif self.current_temp < 90: self.current_sleep = 2
                    else: self.current_sleep = 1

                    # === PULSE THROTTLING ===
                    if self.current_temp > self.T1 and self.panic_start_time is None:
                        self.throttling = True
                        self.update_icon()
                        
                        # Notify on state change (Idle -> Throttling)
                        if not was_throttling:
                            self.send_notification("VRAM Guard", f"Cooling Active. VRAM > {self.T1}°C")
                            was_throttling = True

                        pids = get_gpu_pids()
                        self.control_apps('suspend', pids)
                        time.sleep(COOL_DOWN_TIME)
                        self.control_apps('resume', pids)
                        self.current_sleep = 1
                    else:
                        self.throttling = False
                        if was_throttling: # Reset state when cooled down
                            was_throttling = False
                            
                        if not self.panic_start_time and "KILLED" not in self.last_action:
                             self.last_action = "Monitoring..."
                else:
                    self.current_temp = 0
                    self.last_action = "LHM Error"
                    self.current_sleep = 5
                
                self.update_icon()
            time.sleep(self.current_sleep)

    def open_settings(self, *_):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        root = tk.Tk()
        self.settings_window = root
        root.title("VRAM Guard Settings")
        root.geometry("400x380") # Increased height for checkboxes
        root.resizable(False, False)
        
        app_icon_path = os.path.join(ICONS_DIR, "app.ico")
        if os.path.exists(app_icon_path):
            try: root.iconbitmap(app_icon_path)
            except: pass

        t1 = tk.IntVar(value=self.T1)
        # Checkbox variables
        notif_var = tk.BooleanVar(value=self.enable_notifications)
        audio_var = tk.BooleanVar(value=self.enable_audio)
        
        ttk.Label(root, text="VRAM GUARD STATUS:", font=("Arial", 10, "bold")).pack(pady=5)
        self.gui_temp = ttk.Label(root, text="Temp: --", font=("Arial", 15))
        self.gui_temp.pack()
        self.gui_status = ttk.Label(root, text="Init...", foreground="blue")
        self.gui_status.pack()

        def update_gui():
            if not self.settings_window.winfo_exists(): return
            self.gui_temp.config(text=f"{self.current_temp}°C")
            
            if self.panic_start_time:
                status = f"⚠️ PANIC! KILLING IN {int(PANIC_TIMEOUT - (time.time() - self.panic_start_time))}s"
                color = "red"
            elif self.throttling:
                status = "🔴 PULSE COOLING ACTIVE"
                color = "orange"
            else:
                status = f"🟢 Monitoring (Poll: {self.current_sleep}s)"
                color = "green"
                
            self.gui_status.config(text=status, foreground=color)
            root.after(1000, update_gui)
        update_gui()

        # Sliders
        ttk.Label(root, text="Max VRAM Temp Threshold:").pack(pady=(20, 0))
        scale = ttk.Scale(root, from_=70, to=105, variable=t1, orient='horizontal')
        scale.pack(fill="x", padx=30)
        ttk.Label(root, textvariable=t1).pack()

        # Checkboxes
        check_frame = ttk.Frame(root)
        check_frame.pack(pady=10)
        ttk.Checkbutton(check_frame, text="Windows Notifications", variable=notif_var).pack(anchor="w")
        ttk.Checkbutton(check_frame, text="Panic Audio Alert (Beep)", variable=audio_var).pack(anchor="w")

        def apply():
            self.T1 = int(t1.get())
            self.enable_notifications = notif_var.get()
            self.enable_audio = audio_var.get()
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