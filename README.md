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

## ✨ Key Features (v1.4.2 Update)

*   **🚀 Autostart (NEW):** You can now enable "Start with Windows" directly from the settings menu.
*   **👻 Stealth Mode:** Runs completely in the background via system tray. No console windows.
*   **⚙️ Core Stability:** Full OOP structure for maximum reliability and uptime.
*   **📝 Advanced Logging:** Actions are logged to `vram_guard.log`.
*   **🔔 Notifications & Audio Alerts:** Get notified when throttling kicks in or when temperatures hit panic levels.
*   **🚨 Panic Button:** Emergency kill of heavy GPU processes at 105°C to save hardware.
*   **🔌 Zero Friction Setup:** Automatic download and configuration of `LibreHardwareMonitor` (v0.9.5).
*   **🚀 Adaptive Polling:** The script intelligently changes its check frequency based on temperature.
*   **🔋 Idle Optimization:** `nvidia-smi` is called **only** when the temperature threshold is exceeded.
*   **🛠️ Watchdog System:** Automatically monitors the health of the background service and restarts it if necessary.
*   **⏱️ Startup Delay:** Built-in 30-second delay to avoid driver conflicts during Windows boot.
*   **🎨 Clean UI:** System tray integration with status-aware icons and a dedicated Settings window with an app icon.
*   🛡️ **Safe for Hardware:** Prevents heat soak and thermal degradation.

## 🚀 Installation & Setup

### 1. Download & Extract

1. Download the latest release `.zip` from the [Releases Page](https://github.com/Yp-pro/VRAM-Guard/releases).
2. Extract the archive to any folder (e.g., `C:\VRAM-Guard`).
3. Run **`install.bat`** (once).

### 2. Run VRAM Guard

Run **`Start_Protection.bat`** as **Administrator**.

*   *Note 1:* On the first run, the script will automatically download and configure LibreHardwareMonitor. This might take a few seconds.
*   *Note 2:* The script waits 30 seconds after launch before starting active monitoring (Warm-up phase).

## 🖥️ System Requirements

*   **OS:** Windows 10 or Windows 11 (64-bit).
*   **GPU:** Any NVIDIA GeForce RTX (20xx, 30xx, 40xx, 50xx series) with a VRAM temperature sensor.
*   **Dependencies:** .NET Framework 4.7.2+ (Included in all modern Windows versions).

## 📂 File Structure

```text
📂 VRAM-Guard
 ├── 📄 vram_guard.py         # Main Logic
 ├── 📄 Start_Protection.bat  # Launcher
 ├── 📄 install.bat           # Before 1st run
 ├── 📄 settings.json         # Configuration file for thresholds and timings
 ├── 📄 vram_guard.log        # Log file for debugging
 ├── 📂 resources             # Application resources
 │   ├── 📂 icons             # UI Assets (norm, fire, app icons)
 │   └── 📂 LibreHardwareMonitor # Monitoring Tool (auto-downloaded)
 ├── 📂 img                   # Documentation assets
 └── 📂 venv                  # Python Environment (created by install.bat)
```

## ⚙️ Configuration

### For Novice Users (System Tray)
- **Threshold Slider:** Set the temp to trigger cooling.
- **Start with Windows:** Toggle automatic launch on boot.
- **Windows Notifications:** Toggle toast pop-ups.
- **Audio Alert:** Toggle the panic beep sound on/off.

### For Advanced Users (settings.json)
- `vram_t1_threshold`: Cooling trigger temp.
- `cool_down_time_s`: Pause duration (Default: 3.0s).
- `work_time_s`: Work duration (Default: 2.0s).
- `enable_autostart`: Boolean for registry launch.

## 🛡️ Safety & Hardware Impact

*   **Is the "Sawtooth" load harmful?** No. Modern VRMs and GPUs are designed for transient loads. Switching load every few seconds is significantly safer than constant 100°C heat soak, which causes chip degradation and thermal pad failure.
*   **Will the app crash?** No. The `Suspend/Resume` mechanism is a native Windows function. The app may briefly show "(Not Responding)" during the pause phase, but it will resume processing exactly where it left off.
*   The **Panic Button** only triggers in extreme scenarios (e.g., failed drivers or blocked airflow). By default, it gives the system 10 seconds to cool down before terminating the app.

## 🤝 Support

If VRAM Guard helps keep your hardware safe, please give this repository a ⭐!

---

*Created by [Yp-pro](https://github.com/Yp-pro)*
