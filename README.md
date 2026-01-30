# ![VRAM Guard Logo](img/Logo.png) 
**VRAM Guard** is a specialized utility for NVIDIA laptop owners (RTX 30xx/40xx series) who face extreme Video RAM (VRAM) overheating during AI-intensive tasks such as Image/Video Upscaling (Topaz, Gigapixel, ChaiNNer) or running local LLMs and Stable Diffusion.

## 🔴 The Problem
Most gaming laptops use a **shared heat pipe design**. During AI workloads, the GPU Core might stay relatively cool (60-70°C), but the **VRAM (GDDR6/X)** can quickly hit **98-105°C**. 

Standard laptop cooling systems often ignore VRAM sensors and don't ramp up fans based on memory temperature. This leads to thermal pad "leakage," drying out of thermal paste, and eventual hardware degradation.

## 🟢 The Solution: Pulse Throttling
VRAM Guard monitors the VRAM temperature via `LibreHardwareMonitor`. When the temperature hits your defined limit (e.g., 92°C), it applies **Nuclear Pulse Throttling**:
1. It identifies **all** processes currently using the NVIDIA GPU.
2. It **Suspends** these processes for a few seconds (`COOL_DOWN_TIME`).
3. It **Resumes** them for a short burst of work (`WORK_TIME`).
4. This "Sawtooth" load pattern allows the VRAM to shed heat effectively during pauses, keeping average temperatures significantly lower without crashing the application.

## ✨ Key Features (v1.2 Update)
*   **🚨 Panic Button (New):** The last line of defense. If Pulse Throttling fails and VRAM hits **105°C** for more than 10 seconds, VRAM Guard performs an **Emergency Kill** of the heavy process to prevent permanent hardware damage. Better a lost render than a dead GPU.
*   **🔌 Zero Friction Setup:** Automatic download and configuration of monitoring tools.

*   **🚀 Adaptive Polling:** The script intelligently changes its check frequency based on temperature. It checks once every **60 seconds** when idle (<60°C), ensuring zero impact on battery life and allowing the GPU to sleep.
*   **🔋 Idle Optimization:** `nvidia-smi` is called **only** when the temperature threshold is exceeded.
*   **🛠️ Watchdog System:** Automatically monitors the health of the background service and restarts it if necessary.
*   **⏱️ Startup Delay:** Built-in 30-second delay to avoid driver conflicts during Windows boot.

*   **🎨 Clean UI:** System tray integration with status-aware icons and a dedicated Settings window with an app icon.
*    🛡️ **Safe for Hardware:** Prevents heat soak and thermal degradation.

## 🚀 Installation & Setup

### 1. Download & Extract

1. Download the latest release `.zip` from the [Releases Page](https://github.com/Yp-pro/VRAM-Guard/releases).
2. Extract the archive to any folder (e.g., `C:\VRAM-Guard`).
3. Run **`install.bat`** (once).

### 2. Run VRAM Guard

Run **`Start_Protection.bat`** as **Administrator**.

*   *Note 1:* On the first run, the script will automatically download and configure LibreHardwareMonitor. This might take a few seconds.
*   *Note 2:* The script waits 30 seconds after launch before starting active monitoring (Warm-up phase).

## 📂 File Structure
```text
📂 VRAM-Guard
 ├── 📄 vram_guard.py         # Main Logic
 ├── 📄 Start_Protection.bat  # Launcher (Clean start)
 ├── 📄 install.bat           # Dependency Installer
 ├── 📂 icons                 # UI Assets
 │    ├── norm.ico            # Healthy status
 │    ├── fire.ico            # Cooling active
 │    ├── pause.ico           # Script paused
 │    └── app.ico             # Settings window icon
 ├── 📂 img                   # Documentation assets
 ├── 📂 venv                  # Python Environment (created by install.bat)
 └── 📂 LibreHardwareMonitor  # Monitoring Tool (user-provided)
```

## ⚙️ Configuration

Open `vram_guard.py` with any text editor to tweak these variables:

*   `VRAM_T1`: Temperature threshold to trigger cooling (Recommended: 90-94°C).
*   `COOL_DOWN_TIME`: Duration of the pause (Default: 3.0s).
*   `WORK_TIME`: Duration of the work burst (Default: 2.0s).

## 🛡️ Safety & Hardware Impact

*   **Is the "Sawtooth" load harmful?** No. Modern VRMs and GPUs are designed for transient loads. Switching load every few seconds is significantly safer than constant 100°C heat soak, which causes chip degradation and thermal pad failure.
*   **Will the app crash?** No. The `Suspend/Resume` mechanism is a native Windows function. The app may briefly show "(Not Responding)" during the pause phase, but it will resume processing exactly where it left off.
*   The **Panic Button** only triggers in extreme scenarios (e.g., failed drivers or blocked airflow). By default, it gives the system 10 seconds to cool down before terminating the app.

## 🤝 Support
If VRAM Guard helps keep your hardware safe, please give this repository a ⭐!

---
*Created by [Yp-pro](https://github.com/Yp-pro)*