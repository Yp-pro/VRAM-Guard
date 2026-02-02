import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class SettingsWindow:
    def __init__(self, settings):
        self.settings = settings
        self.root = None

    def show(self):
        if self.root and tk.Toplevel.winfo_exists(self.root):
            self.root.lift()
            return

        self.root = tk.Tk()
        self.root.title("VRAM Guard Settings")
        self.root.geometry("350x250")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # T1 Threshold
        ttk.Label(main_frame, text="Throttling Threshold (T1):").pack(anchor=tk.W)
        self.t1_var = tk.IntVar(value=self.settings.get("vram_t1_threshold"))
        t1_slider = ttk.Scale(main_frame, from_=70, to_=100, variable=self.t1_var, orient=tk.HORIZONTAL)
        t1_slider.pack(fill=tk.X, pady=(0, 10))
        
        val_label = ttk.Label(main_frame, text=f"{self.t1_var.get()}°C")
        val_label.pack()
        self.t1_var.trace_add("write", lambda *args: val_label.config(text=f"{self.t1_var.get()}°C"))

        # Checkboxes
        self.notify_var = tk.BooleanVar(value=self.settings.get("enable_notifications"))
        ttk.Checkbutton(main_frame, text="Enable Notifications", variable=self.notify_var).pack(anchor=tk.W, pady=5)

        self.audio_var = tk.BooleanVar(value=self.settings.get("enable_audio_alert"))
        ttk.Checkbutton(main_frame, text="Enable Audio Alerts", variable=self.audio_var).pack(anchor=tk.W, pady=5)

        # Save Button
        ttk.Button(main_frame, text="Save Settings", command=self._save).pack(pady=10)

        self.root.mainloop()

    def _save(self):
        self.settings.set("vram_t1_threshold", self.t1_var.get())
        self.settings.set("enable_notifications", self.notify_var.get())
        self.settings.set("enable_audio_alert", self.audio_var.get())
        logger.info("Settings updated via GUI.")
        self.root.destroy()