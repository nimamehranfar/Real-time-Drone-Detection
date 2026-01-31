"""
Drone Detection Demo - GUI Runner (Qt)

A modern desktop GUI to configure and run the video-based drone demo detector.
The detector still renders video through the OpenCV window; this GUI is for control + event log.

Dependencies:
  pip install PySide6

Run:
  python drone_detection_gui.py
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


def _load_detector_module() -> object:
    try:
        from drone_detector import drone_detection as det
        return det
    except Exception:
        pass

class _DetectorWorker(QtCore.QThread):
    sig_done = QtCore.Signal()
    sig_error = QtCore.Signal(str)

    def __init__(self, det_module: object):
        super().__init__()
        self.det = det_module

    def run(self) -> None:
        try:
            self.det.main()
        except Exception:
            self.sig_error.emit(traceback.format_exc())
        finally:
            self.sig_done.emit()


class DroneDetectionGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Detection Demo")
        self.setMinimumSize(1060, 640)

        self.det = _load_detector_module()
        self.worker: Optional[_DetectorWorker] = None

        self._apply_dark_theme()
        self._build_ui()
        self._wire_detector_events()

        self._refresh_status("Ready")

    # -------------------------
    # UI
    # -------------------------
    def _apply_dark_theme(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(15, 23, 42))        # slate-900
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(226, 232, 240)) # slate-200
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(17, 24, 39))          # gray-900
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(30, 41, 59)) # slate-800
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(226, 232, 240))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(30, 41, 59))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(226, 232, 240))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(56, 189, 248))  # sky-400
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(15, 23, 42))
        app.setPalette(palette)

        app.setStyleSheet("""
            QMainWindow { background: #0f172a; }
            QLabel#Title { font-size: 22px; font-weight: 700; color: #e2e8f0; }
            QLabel#Subtitle { font-size: 12px; color: #94a3b8; }
            QLabel#SectionTitle { font-size: 13px; font-weight: 700; color: #e2e8f0; }
            QFrame#Card {
                background: #111827;
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 14px;
            }
            QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
                background: #0b1220;
                border: 1px solid rgba(148,163,184,0.22);
                border-radius: 10px;
                padding: 8px 10px;
                color: #e2e8f0;
            }
            QComboBox::drop-down { border: 0px; }
            QPushButton {
                background: #1e293b;
                border: 1px solid rgba(148,163,184,0.22);
                border-radius: 12px;
                padding: 10px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #243149; }
            QPushButton:pressed { background: #152033; }
            QPushButton#Primary {
                background: #10b981; /* emerald-500 */
                color: #06291f;
                border: 1px solid rgba(16,185,129,0.35);
            }
            QPushButton#Primary:hover { background: #34d399; }
            QPushButton:disabled { color: rgba(226,232,240,0.35); background: #111827; }
            QCheckBox { spacing: 10px; }
            QTextEdit {
                background: #0b1220;
                border: 1px solid rgba(148,163,184,0.22);
                border-radius: 14px;
                padding: 10px;
                color: #e2e8f0;
            }
            QScrollArea { border: 0px; }
        """)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        # Header
        header = QtWidgets.QFrame()
        header.setObjectName("Card")
        header_l = QtWidgets.QHBoxLayout(header)
        header_l.setContentsMargins(16, 14, 16, 14)

        left = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Drone Detection System")
        title.setObjectName("Title")
        subtitle = QtWidgets.QLabel("Real-time YOLO drone detection demo (video-based)")
        subtitle.setObjectName("Subtitle")
        left.addWidget(title)
        left.addWidget(subtitle)
        header_l.addLayout(left)

        header_l.addStretch(1)

        self.lbl_status_pill = QtWidgets.QLabel("● Ready")
        self.lbl_status_pill.setStyleSheet(
            "padding: 8px 12px; border-radius: 999px; "
            "background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.30); "
            "color: #34d399; font-weight: 700;"
        )
        header_l.addWidget(self.lbl_status_pill, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        outer.addWidget(header)

        # Main split
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # Left: big "preview placeholder" (we keep OpenCV window external)
        preview_card = QtWidgets.QFrame()
        preview_card.setObjectName("Card")
        pv = QtWidgets.QVBoxLayout(preview_card)
        pv.setContentsMargins(18, 18, 18, 18)
        pv.setSpacing(10)

        pv_title = QtWidgets.QLabel("Video Preview")
        pv_title.setObjectName("SectionTitle")
        pv.addWidget(pv_title)

        hint = QtWidgets.QLabel(
            "The detector renders frames in the OpenCV window.\n"
            "Controls there:\n"
            "  • p: pause/resume\n"
            "  • q or ESC: quit\n"
        )
        hint.setStyleSheet("color: #94a3b8;")
        hint.setAlignment(QtCore.Qt.AlignCenter)
        hint.setMinimumHeight(240)

        pv.addStretch(1)
        pv.addWidget(hint, 1)
        pv.addStretch(1)

        body.addWidget(preview_card, 2)

        # Right: controls (scrollable) + log
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(14)
        body.addLayout(right_col, 1)

        # Scroll area for controls
        controls_card = QtWidgets.QFrame()
        controls_card.setObjectName("Card")
        controls_l = QtWidgets.QVBoxLayout(controls_card)
        controls_l.setContentsMargins(12, 12, 12, 12)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        controls_l.addWidget(scroll)

        controls_inner = QtWidgets.QWidget()
        scroll.setWidget(controls_inner)
        form = QtWidgets.QVBoxLayout(controls_inner)
        form.setContentsMargins(6, 6, 6, 6)
        form.setSpacing(12)

        # --- Video source
        form.addWidget(self._section_label("Video source"))
        row = QtWidgets.QHBoxLayout()
        self.in_video = QtWidgets.QLineEdit(str(getattr(self.det, "VIDEO_PATH", "")))
        btn_browse = QtWidgets.QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_video)
        row.addWidget(self.in_video, 1)
        row.addWidget(btn_browse)
        form.addLayout(row)

        # --- Core options
        form.addWidget(self._section_label("Detection options"))

        self.cb_cascade = QtWidgets.QComboBox()
        self.cb_cascade.addItems(["None", "Cascade Low/Small", "Cascade All", "Alert-Window Cascade"])
        self.cb_cascade.setCurrentText(str(getattr(self.det, "CASCADED_ROI_CONFIRM_MODE", "None")))
        form.addWidget(self._labeled_widget("Cascaded ROI Confirmation", self.cb_cascade))

        self.chk_troi = QtWidgets.QCheckBox("Enable Temporal ROI Propagation")
        self.chk_troi.setChecked(bool(getattr(self.det, "TEMPORAL_ROI_PROP_ENABLED", False)))
        form.addWidget(self.chk_troi)

        self.spin_infer_fps = QtWidgets.QDoubleSpinBox()
        self.spin_infer_fps.setRange(0.1, 120.0)
        self.spin_infer_fps.setSingleStep(0.5)
        self.spin_infer_fps.setDecimals(2)
        self.spin_infer_fps.setValue(float(getattr(self.det, "INFER_FPS", 5)))
        form.addWidget(self._labeled_widget("INFER_FPS (stride-based)", self.spin_infer_fps))

        # --- Overlay options
        form.addWidget(self._section_label("Overlay"))
        self.cb_log_mode = QtWidgets.QComboBox()
        self.cb_log_mode.addItems(["off", "full", "windows_big"])
        self.cb_log_mode.setCurrentText(str(getattr(self.det, "TOPLEFT_LOG_MODE", "windows_big")))
        form.addWidget(self._labeled_widget("Top-left log mode", self.cb_log_mode))

        self.chk_show_gate = QtWidgets.QCheckBox("SHOW_GATE (Temporal Continuity gates)")
        self.chk_show_gate.setChecked(bool(getattr(self.det, "SHOW_GATE", False)))
        form.addWidget(self.chk_show_gate)

        self.chk_show_troi = QtWidgets.QCheckBox("SHOW_TROI (Temporal ROI Propagation ROIs)")
        self.chk_show_troi.setChecked(bool(getattr(self.det, "SHOW_TROI", False)))
        form.addWidget(self.chk_show_troi)

        self.chk_show_cascade = QtWidgets.QCheckBox("SHOW_CASCADE (log-only; no boxes)")
        self.chk_show_cascade.setChecked(bool(getattr(self.det, "SHOW_CASCADE", False)))
        form.addWidget(self.chk_show_cascade)

        # --- Output
        form.addWidget(self._section_label("Outputs"))
        self.chk_save_video = QtWidgets.QCheckBox("SAVE_VIDEO")
        self.chk_save_video.setChecked(bool(getattr(self.det, "SAVE_VIDEO", True)))
        form.addWidget(self.chk_save_video)

        self.chk_save_alert_frames = QtWidgets.QCheckBox("SAVE_ALERT_WINDOW_FRAMES")
        self.chk_save_alert_frames.setChecked(bool(getattr(self.det, "SAVE_ALERT_WINDOW_FRAMES", True)))
        form.addWidget(self.chk_save_alert_frames)

        # --- Cooldowns
        form.addWidget(self._section_label("Cooldowns"))
        self.spin_warn_cd = QtWidgets.QDoubleSpinBox()
        self.spin_warn_cd.setRange(0.0, 120.0)
        self.spin_warn_cd.setDecimals(2)
        self.spin_warn_cd.setValue(float(getattr(self.det, "WARNING_COOLDOWN_S", 3.0)))
        form.addWidget(self._labeled_widget("WARNING_COOLDOWN_S", self.spin_warn_cd))

        self.spin_alert_cd = QtWidgets.QDoubleSpinBox()
        self.spin_alert_cd.setRange(0.0, 120.0)
        self.spin_alert_cd.setDecimals(2)
        self.spin_alert_cd.setValue(float(getattr(self.det, "ALERT_COOLDOWN_S", 3.0)))
        form.addWidget(self._labeled_widget("ALERT_COOLDOWN_S", self.spin_alert_cd))

        form.addSpacing(6)

        # --- Run row
        run_row = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("Run")
        self.btn_run.setObjectName("Primary")
        self.btn_run.clicked.connect(self._run_clicked)
        self.btn_run.setMinimumHeight(42)

        self.lbl_run_state = QtWidgets.QLabel("Idle")
        self.lbl_run_state.setStyleSheet("color: #94a3b8; font-weight: 600;")

        run_row.addWidget(self.btn_run, 1)
        run_row.addWidget(self.lbl_run_state)
        form.addLayout(run_row)

        form.addStretch(1)
        right_col.addWidget(controls_card, 2)

        # Log card
        log_card = QtWidgets.QFrame()
        log_card.setObjectName("Card")
        log_l = QtWidgets.QVBoxLayout(log_card)
        log_l.setContentsMargins(14, 14, 14, 14)
        log_l.setSpacing(10)

        log_l.addWidget(self._section_label("Event log (WARNING / ALERT)"))
        self.txt_log = QtWidgets.QTextEdit()
        self.txt_log.setReadOnly(True)
        log_l.addWidget(self.txt_log, 1)

        self._append_log(
            "Ready.\n"
            "Notes:\n"
            " • Video is displayed in the OpenCV window.\n"
            " • Close it with q or ESC to end a run.\n"
        )

        right_col.addWidget(log_card, 3)

    def _section_label(self, text: str) -> QtWidgets.QLabel:
        lab = QtWidgets.QLabel(text)
        lab.setObjectName("SectionTitle")
        return lab

    def _labeled_widget(self, label: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        wrap = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lab = QtWidgets.QLabel(label)
        lab.setStyleSheet("color: #94a3b8;")
        lay.addWidget(lab, 1)
        lay.addWidget(widget, 1)
        return wrap

    def _append_log(self, msg: str) -> None:
        self.txt_log.moveCursor(QtGui.QTextCursor.End)
        self.txt_log.insertPlainText(msg if msg.endswith("\n") else msg + "\n")
        self.txt_log.moveCursor(QtGui.QTextCursor.End)

    def _refresh_status(self, text: str, ok: bool = True) -> None:
        if ok:
            self.lbl_status_pill.setText(f"● {text}")
            self.lbl_status_pill.setStyleSheet(
                "padding: 8px 12px; border-radius: 999px; "
                "background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.30); "
                "color: #34d399; font-weight: 700;"
            )
        else:
            self.lbl_status_pill.setText(f"● {text}")
            self.lbl_status_pill.setStyleSheet(
                "padding: 8px 12px; border-radius: 999px; "
                "background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.30); "
                "color: #f87171; font-weight: 700;"
            )

    # -------------------------
    # Detector event wiring
    # -------------------------
    def _wire_detector_events(self) -> None:
        def _warn():
            QtCore.QMetaObject.invokeMethod(self, "_on_warning", QtCore.Qt.QueuedConnection)

        def _alert():
            QtCore.QMetaObject.invokeMethod(self, "_on_alert", QtCore.Qt.QueuedConnection)

        # Override detector functions (it will call these on event edges)
        self.det.send_warning_to_esp = _warn
        self.det.send_alert_to_esp = _alert

    @QtCore.Slot()
    def _on_warning(self) -> None:
        self._append_log("WARNING event edge triggered.")

    @QtCore.Slot()
    def _on_alert(self) -> None:
        self._append_log("ALERT event edge triggered.")

    # -------------------------
    # Actions
    # -------------------------
    def _browse_video(self) -> None:
        start_dir = str(Path(self.in_video.text()).expanduser().resolve().parent) if self.in_video.text() else str(Path.cwd())
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select video file",
            start_dir,
            "Video files (*.mp4 *.avi *.mov *.mkv);;All files (*.*)",
        )
        if path:
            self.in_video.setText(path)

    def _apply_config_to_detector(self) -> None:
        cfg = dict(
            VIDEO_PATH=self.in_video.text().strip(),
            CASCADED_ROI_CONFIRM_MODE=self.cb_cascade.currentText().strip(),
            TEMPORAL_ROI_PROP_ENABLED=bool(self.chk_troi.isChecked()),
            SHOW_GATE=bool(self.chk_show_gate.isChecked()),
            SHOW_TROI=bool(self.chk_show_troi.isChecked()),
            SHOW_CASCADE=bool(self.chk_show_cascade.isChecked()),
            TOPLEFT_LOG_MODE=self.cb_log_mode.currentText().strip(),
            SAVE_VIDEO=bool(self.chk_save_video.isChecked()),
            SAVE_ALERT_WINDOW_FRAMES=bool(self.chk_save_alert_frames.isChecked()),
            WARNING_COOLDOWN_S=float(self.spin_warn_cd.value()),
            ALERT_COOLDOWN_S=float(self.spin_alert_cd.value()),
            INFER_FPS=float(self.spin_infer_fps.value()),
        )

        if hasattr(self.det, "apply_runtime_config"):
            self.det.apply_runtime_config(**cfg)
        else:
            for k, v in cfg.items():
                setattr(self.det, k, v)

    def _run_clicked(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return

        try:
            self._apply_config_to_detector()
        except Exception as e:
            self._append_log(f"Config error: {e}")
            self._refresh_status("Config error", ok=False)
            return

        self.btn_run.setEnabled(False)
        self.lbl_run_state.setText("Running (OpenCV window)…")
        self._refresh_status("Running")
        self._append_log("Running detector…")

        self.worker = _DetectorWorker(self.det)
        self.worker.sig_error.connect(self._on_worker_error)
        self.worker.sig_done.connect(self._on_worker_done)
        self.worker.start()

    @QtCore.Slot(str)
    def _on_worker_error(self, tb: str) -> None:
        self._append_log(tb)
        self._refresh_status("Error", ok=False)

    @QtCore.Slot()
    def _on_worker_done(self) -> None:
        self._append_log("Detector stopped.")
        self.btn_run.setEnabled(True)
        self.lbl_run_state.setText("Idle")
        self._refresh_status("Ready")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    w = DroneDetectionGUI()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
