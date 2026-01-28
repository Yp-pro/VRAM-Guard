# ![VRAM Guard Logo](img/App_icon-small-small.png) VRAM Guard

**VRAM Guard** is a specialized utility for NVIDIA laptop owners (RTX 30xx/40xx series) who face extreme Video RAM (VRAM) overheating during AI-intensive tasks such as Image/Video Upscaling (Topaz, Gigapixel, ChaiNNer) or Stable Diffusion.

## 🔴 The Problem
Most gaming laptops use a **shared heat pipe design**. During AI workloads, the GPU Core might stay relatively cool (60-70°C), but the **VRAM (GDDR6/X)** can quickly hit **98-105°C**. 

Standard laptop cooling systems often ignore VRAM sensors and don't ramp up fans based on memory temperature. This leads to thermal pad "leakage," drying out of thermal paste, and eventual hardware degradation.

## 🟢 The Solution: Pulse Throttling
VRAM Guard monitors the VRAM temperature via `LibreHardwareMonitor`. When the temperature hits your defined limit (e.g., 92°C), it applies **Nuclear Pulse Throttling**:
1. It identifies **all** processes currently using the NVIDIA GPU (via `nvidia-smi`).
2. It **Suspends** these processes for a few seconds (`COOL_DOWN_TIME`).
3. It **Resumes** them for a short burst of work (`WORK_TIME`).
4. This "Sawtooth" load pattern allows the VRAM to shed heat effectively during pauses, keeping average temperatures significantly lower without crashing the application.

## ✨ Key Features
*   **Real-time VRAM Monitoring:** Connects to LibreHardwareMonitor's web server.
*   **Watchdog System:** Automatically launches and monitors LibreHardwareMonitor. If it crashes, the script restarts it.
*   **Startup Delay:** Built-in 30-second delay to avoid driver conflicts during Windows boot.
*   **Clean UI:** System tray integration with status-aware icons and a dedicated Settings window.
*   **Safe for Hardware:** Prevents heat soak and thermal degradation.

## 🚀 Installation & Setup

### 1. Prerequisites
*   Download [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor).
*   Extract it into a subfolder named `LibreHardwareMonitor` inside the VRAM Guard directory.
*   Run `LibreHardwareMonitor.exe` as **Administrator**.
*   Go to `Options -> Remote Web Server`, set the port to `8085`, and click **Run**.

### 2. Repository Setup
```bash
git clone https://github.com/Yp-pro/VRAM-Guard.git
cd VRAM-Guard
```

### 3. Environment Installation
Run **`install.bat`**. This will:
*   Create a local Python virtual environment (`venv`).
*   Install required libraries (`psutil`, `requests`, `pystray`, `Pillow`).

### 4. Running the App
Run **`Start_Protection.bat`** as **Administrator**. 
*The script will wait for 30 seconds (Warming up) before initializing the monitor to ensure all system drivers are ready.*

## 📂 File Structure
```text
📂 VRAM-Guard
 ├── 📄 vram_guard.py         # Main Logic
 ├── 📄 Start_Protection.bat  # Launcher
 ├── 📄 install.bat           # Dependency Installer
 ├── 📂 icons                 # UI Assets
 │    ├── norm.ico            # Healthy status
 │    ├── fire.ico            # Cooling active
 │    ├── pause.ico           # Script paused
 │    └── app.ico             # Settings window icon
 ├── 📂 venv                  # Python Environment
 └── 📂 LibreHardwareMonitor  # Monitoring Tool
```

## ⚙️ Configuration
Open `vram_guard.py` to tweak these variables:
*   `VRAM_T1`: Temperature threshold to trigger cooling (Recommended: 90-94°C).
*   `COOL_DOWN_TIME`: Duration of the pause (Default: 3.0s).
*   `WORK_TIME`: Duration of the work burst (Default: 2.0s).
*   `STARTUP_DELAY`: Delay before the first LHM launch (Default: 30s).

## 🛡️ Safety & Hardware Impact
*   **Is the "Sawtooth" load harmful?** No. Modern VRMs and GPUs are designed for transient loads. Switching load every few seconds is significantly safer than constant 100°C heat soak, which causes chip degradation.
*   **Will the app crash?** No. The `Suspend/Resume` mechanism is a native Windows function. The app may briefly show "(Not Responding)" during the 3-second pause, but it will resume processing exactly where it left off.

## 🤝 Support
If VRAM Guard helps keep your laptop cool, please give this repository a ⭐!

---
*Created by [Yp-pro](https://github.com/Yp-pro)*