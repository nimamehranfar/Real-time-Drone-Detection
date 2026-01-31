"""
Drone Detection Demo - Simple GUI Runner

This GUI configures and runs the video-based drone demo detector.
It also hooks WARNING/ALERT event edges to two functions:
  - send_warning_to_esp()
  - send_alert_to_esp()

Both are mocked here (no hardware I/O).
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def _try_import_detector():
    # Prefer the standard module name if you saved the patched file as drone_detection.py
    try:
        from drone_detector import drone_detection as det
        return det
    except Exception:
        pass


class DroneDetectionGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drone Detection Demo - GUI")
        self.geometry("760x520")
        self.minsize(720, 480)

        self.det = _try_import_detector()

        self.event_q: "queue.Queue[str]" = queue.Queue()
        self.worker: threading.Thread | None = None

        # UI variables (requested set)
        self.var_video_path = tk.StringVar(value=str(getattr(self.det, "VIDEO_PATH", "")))

        self.var_cascade_mode = tk.StringVar(value="None")
        self.var_troi_enabled = tk.BooleanVar(value=True)

        self.var_show_gate = tk.BooleanVar(value=False)
        self.var_show_troi = tk.BooleanVar(value=False)
        self.var_show_cascade = tk.BooleanVar(value=False)

        self.var_top_left = tk.StringVar(value="windows_big")

        self.var_save_video = tk.BooleanVar(value=False)
        self.var_save_alert_frames = tk.BooleanVar(value=True)

        self.var_warn_cd = tk.StringVar(value="3.0")
        self.var_alert_cd = tk.StringVar(value="3.0")
        self.var_infer_fps = tk.StringVar(value=str(getattr(self.det, "INFER_FPS", 5)))

        self._build()
        self._poll_events()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        # Video path
        row0 = ttk.Frame(frm)
        row0.pack(fill="x", **pad)

        ttk.Label(row0, text="VIDEO_PATH").pack(side="left")
        ent = ttk.Entry(row0, textvariable=self.var_video_path)
        ent.pack(side="left", fill="x", expand=True, padx=(10, 10))
        ttk.Button(row0, text="Browse…", command=self._browse_video).pack(side="left")

        # Cascade mode
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="CASCADED_ROI_CONFIRM_MODE").pack(side="left")

        cascade_modes = ["None", "Cascade Low/Small", "Cascade All", "Alert-Window Cascade"]
        ttk.OptionMenu(row1, self.var_cascade_mode, self.var_cascade_mode.get(), *cascade_modes).pack(
            side="left", padx=(10, 0)
        )

        # Temporal ROI Propagation toggle + infer fps
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", **pad)

        ttk.Checkbutton(row2, text="TEMPORAL_ROI_PROP_ENABLED", variable=self.var_troi_enabled).pack(side="left")

        ttk.Label(row2, text="INFER_FPS").pack(side="left", padx=(25, 6))
        ttk.Entry(row2, textvariable=self.var_infer_fps, width=8).pack(side="left")

        # Overlay toggles
        row3 = ttk.Frame(frm)
        row3.pack(fill="x", **pad)

        ttk.Checkbutton(row3, text="SHOW_GATE", variable=self.var_show_gate).pack(side="left")
        ttk.Checkbutton(row3, text="SHOW_TROI", variable=self.var_show_troi).pack(side="left", padx=(18, 0))
        ttk.Checkbutton(row3, text="SHOW_CASCADE", variable=self.var_show_cascade).pack(side="left", padx=(18, 0))

        # Top-left log mode
        row4 = ttk.Frame(frm)
        row4.pack(fill="x", **pad)
        ttk.Label(row4, text="TOPLEFT_LOG_MODE").pack(side="left")

        log_modes = ["off", "full", "windows_big"]
        ttk.OptionMenu(row4, self.var_top_left, self.var_top_left.get(), *log_modes).pack(side="left", padx=(10, 0))

        # Output options
        row5 = ttk.Frame(frm)
        row5.pack(fill="x", **pad)

        ttk.Checkbutton(row5, text="SAVE_VIDEO", variable=self.var_save_video).pack(side="left")
        ttk.Checkbutton(row5, text="SAVE_ALERT_WINDOW_FRAMES", variable=self.var_save_alert_frames).pack(
            side="left", padx=(18, 0)
        )

        # Cooldowns
        row6 = ttk.Frame(frm)
        row6.pack(fill="x", **pad)

        ttk.Label(row6, text="WARNING_COOLDOWN_S").pack(side="left")
        ttk.Entry(row6, textvariable=self.var_warn_cd, width=8).pack(side="left", padx=(10, 18))

        ttk.Label(row6, text="ALERT_COOLDOWN_S").pack(side="left")
        ttk.Entry(row6, textvariable=self.var_alert_cd, width=8).pack(side="left", padx=(10, 0))

        # Run controls
        row7 = ttk.Frame(frm)
        row7.pack(fill="x", **pad)

        self.btn_run = ttk.Button(row7, text="Run detector", command=self._run_clicked)
        self.btn_run.pack(side="left")

        self.lbl_status = ttk.Label(row7, text="Idle")
        self.lbl_status.pack(side="left", padx=(14, 0))

        # Event log
        ttk.Label(frm, text="ESP triggers (WARNING / ALERT):").pack(anchor="w", padx=10, pady=(14, 0))

        self.txt = tk.Text(frm, height=12)
        self.txt.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.txt.configure(state="disabled")

        self._append_log(
            "Ready. Run detector and use the OpenCV window:\n"
            "  - p pauses/resumes\n"
            "  - q or ESC quits\n"
        )

    def _append_log(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + ("\n" if not msg.endswith("\n") else ""))
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if path:
            self.var_video_path.set(path)

    def _validate_float(self, s: str, name: str) -> float:
        try:
            v = float(s)
        except Exception:
            raise ValueError(f"{name} must be a number.")
        if v <= 0:
            raise ValueError(f"{name} must be > 0.")
        return v

    def _apply_config_to_detector(self):
        infer_fps = self._validate_float(self.var_infer_fps.get().strip(), "INFER_FPS")
        warn_cd = self._validate_float(self.var_warn_cd.get().strip(), "WARNING_COOLDOWN_S")
        alert_cd = self._validate_float(self.var_alert_cd.get().strip(), "ALERT_COOLDOWN_S")

        cfg = dict(
            VIDEO_PATH=self.var_video_path.get().strip(),
            CASCADED_ROI_CONFIRM_MODE=self.var_cascade_mode.get().strip(),
            TEMPORAL_ROI_PROP_ENABLED=bool(self.var_troi_enabled.get()),
            SHOW_GATE=bool(self.var_show_gate.get()),
            SHOW_TROI=bool(self.var_show_troi.get()),
            SHOW_CASCADE=bool(self.var_show_cascade.get()),
            TOPLEFT_LOG_MODE=self.var_top_left.get().strip(),
            SAVE_VIDEO=bool(self.var_save_video.get()),
            SAVE_ALERT_WINDOW_FRAMES=bool(self.var_save_alert_frames.get()),
            WARNING_COOLDOWN_S=float(warn_cd),
            ALERT_COOLDOWN_S=float(alert_cd),
            INFER_FPS=float(infer_fps),
        )

        # Wire ESP hooks (thread-safe via queue)
        def _esp_warning():
            self.event_q.put("WARNING")

        def _esp_alert():
            self.event_q.put("ALERT")

        # Override detector functions (it will call these on event edges)
        self.det.send_warning_to_esp = _esp_warning
        self.det.send_alert_to_esp = _esp_alert

        # Apply module-level config
        if hasattr(self.det, "apply_runtime_config"):
            self.det.apply_runtime_config(**cfg)
        else:
            # Fallback (should not happen with the patched file)
            for k, v in cfg.items():
                setattr(self.det, k, v)

    def _run_clicked(self):
        if self.worker is not None and self.worker.is_alive():
            return

        try:
            self._apply_config_to_detector()
        except Exception as e:
            messagebox.showerror("Config error", str(e))
            return

        self.btn_run.configure(state="disabled")
        self.lbl_status.configure(text="Running (use OpenCV window to quit)…")
        self._append_log("Running detector…")

        def _run():
            try:
                self.det.main()
            except Exception as e:
                self.event_q.put(f"ERROR: {e}")
            finally:
                self.event_q.put("__DONE__")

        self.worker = threading.Thread(target=_run, daemon=True)
        self.worker.start()

    def _poll_events(self):
        try:
            while True:
                msg = self.event_q.get_nowait()
                if msg == "__DONE__":
                    self.lbl_status.configure(text="Idle")
                    self.btn_run.configure(state="normal")
                    self._append_log("Detector stopped.")
                elif msg.startswith("ERROR:"):
                    self._append_log(msg)
                elif msg == "WARNING":
                    self._append_log("ESP32 trigger: WARNING")
                elif msg == "ALERT":
                    self._append_log("ESP32 trigger: ALERT")
                else:
                    self._append_log(str(msg))
        except queue.Empty:
            pass

        self.after(120, self._poll_events)


def main():
    app = DroneDetectionGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
