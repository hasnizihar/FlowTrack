"""
screen_analysis.py — Pipeline runner screen with progress bars, step cards, and log panel.

Three sections stacked vertically:
  - Top: configuration bar (video path, frames, save video, run button)
  - Middle: step cards for steps 5-8
  - Bottom: log panel
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QSpinBox, QCheckBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QScrollArea, QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from traffic_analysis_gui.workers.step5_worker import Step5Worker
from traffic_analysis_gui.controllers.pipeline_runner import StepWorker


class AnalysisScreen(QWidget):
    # Signals emitted for cross-screen communication
    pipeline_step_done = pyqtSignal(int)   # step number
    pipeline_all_done = pyqtSignal()
    model_downloaded = pyqtSignal()

    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._step5_worker = None
        self._current_worker = None
        self._running = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # --- Configuration bar ---
        config_frame = QFrame()
        config_frame.setObjectName("Card")
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(12, 8, 12, 8)
        config_layout.setSpacing(12)

        # Video path label
        config_layout.addWidget(QLabel("Video:"))
        self.video_label = QLabel("None")
        self.video_label.setStyleSheet("font-weight: 600; color: #185FA5;")
        if self.ctrl.state.video_path:
            self.video_label.setText(self.ctrl.state.video_path.name)
        config_layout.addWidget(self.video_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #ddd;")
        config_layout.addWidget(sep)

        # Run for whole video checkbox
        self.whole_video_cb = QCheckBox("Run for whole video")
        self.whole_video_cb.setChecked(False)
        self.whole_video_cb.toggled.connect(self._on_whole_video_toggled)
        config_layout.addWidget(self.whole_video_cb)

        # Frames
        self.frames_lbl = QLabel("Frames:")
        config_layout.addWidget(self.frames_lbl)
        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(1, 999999)
        self.frames_spin.setValue(500)
        self.frames_spin.setFixedWidth(80)
        config_layout.addWidget(self.frames_spin)

        # Save video checkbox
        self.save_video_cb = QCheckBox("Save video")
        self.save_video_cb.setChecked(True)
        config_layout.addWidget(self.save_video_cb)

        # Run / Stop buttons
        self.run_btn = QPushButton("▶ Run All")
        self.run_btn.setObjectName("PrimaryBtn")
        self.run_btn.setFixedWidth(100)
        self.run_btn.clicked.connect(self._run_pipeline)
        config_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setObjectName("SecondaryBtn")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_pipeline)
        config_layout.addWidget(self.stop_btn)

        layout.addWidget(config_frame)

        # --- Step cards ---
        steps_header = QLabel("Pipeline Steps")
        steps_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #333;")
        layout.addWidget(steps_header)

        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(8)
        self.step_cards = {}

        step_info = {
            5: ("Detect & Track", "YOLOv9 detection + DeepSORT tracking across all frames"),
            6: ("Speed Estimation", "Compute vehicle speeds from tracked positions"),
            7: ("Traffic Parameters", "Calculate flow rates, composition, and statistics"),
            8: ("Generate Plots", "Create charts and visualizations"),
        }

        for step_num, (name, desc) in step_info.items():
            card = self._create_step_card(step_num, name, desc)
            steps_layout.addWidget(card)
            self.step_cards[step_num] = card

        layout.addLayout(steps_layout)

        # --- Log panel ---
        log_header = QLabel("Pipeline Log")
        log_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #333; margin-top: 4px;")
        layout.addWidget(log_header)

        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("LogPanel")
        self.log_panel.setReadOnly(True)
        self.log_panel.setFixedHeight(160)
        layout.addWidget(self.log_panel)

    # ------------------------------------------------------------------ #
    #  Step card builder                                                    #
    # ------------------------------------------------------------------ #
    def _create_step_card(self, step_num: int, name: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(80)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Header row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        status_dot = QLabel("●")
        status_dot.setObjectName(f"dot_{step_num}")
        status_dot.setStyleSheet("font-size: 10px; color: #999;")
        status_dot.setFixedWidth(14)
        header_row.addWidget(status_dot)

        name_label = QLabel(f"Step {step_num}: {name}")
        name_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #333;")
        header_row.addWidget(name_label)

        header_row.addStretch()

        status_badge = QLabel("Idle")
        status_badge.setObjectName(f"badge_{step_num}")
        status_badge.setStyleSheet(
            "font-size: 9px; color: #888; background: #f0f0f0; "
            "border-radius: 3px; padding: 2px 8px; font-weight: 600;"
        )
        header_row.addWidget(status_badge)

        layout.addLayout(header_row)

        # Description
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(desc_label)

        # Progress bar
        progress = QProgressBar()
        progress.setObjectName(f"progress_{step_num}")
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(4)
        layout.addWidget(progress)

        return card

    # ------------------------------------------------------------------ #
    #  UI helpers                                                          #
    # ------------------------------------------------------------------ #
    def _on_whole_video_toggled(self, checked: bool):
        self.frames_spin.setEnabled(not checked)
        self.frames_lbl.setEnabled(not checked)

    def _set_step_ui(self, step: int, status: str):
        """Update step card UI."""
        card = self.step_cards.get(step)
        if not card:
            return
        dot = card.findChild(QLabel, f"dot_{step}")
        badge = card.findChild(QLabel, f"badge_{step}")
        progress = card.findChild(QProgressBar, f"progress_{step}")

        colors = {
            "idle": ("#999", "#f0f0f0", "#888"),
            "running": ("#E8A020", "#FFF3E0", "#E8A020"),
            "done": ("#3B8a22", "#E8F5E9", "#3B8a22"),
            "error": ("#cc3333", "#FFEBEE", "#cc3333"),
        }
        dot_c, bg_c, text_c = colors.get(status, colors["idle"])
        if dot:
            dot.setStyleSheet(f"font-size: 10px; color: {dot_c};")
        if badge:
            badge.setText(status.capitalize())
            badge.setStyleSheet(
                f"font-size: 9px; color: {text_c}; background: {bg_c}; "
                f"border-radius: 3px; padding: 2px 8px; font-weight: 600;"
            )

    def update_progress(self, step: int, fraction: float):
        """Update progress bar for a step."""
        card = self.step_cards.get(step)
        if not card:
            return
        progress = card.findChild(QProgressBar, f"progress_{step}")
        if progress:
            progress.setValue(int(fraction * 100))
        self.ctrl.set_step_progress(step, fraction)

    def append_log(self, text: str):
        """Append a log line with colour coding."""
        cursor = self.log_panel.textCursor()
        fmt = QTextCharFormat()

        if "✓" in text or "Complete" in text or "[OK]" in text:
            fmt.setForeground(QColor("#5DCAA5"))
        elif "ERROR" in text or "error" in text.lower() or "FAIL" in text:
            fmt.setForeground(QColor("#E85A5A"))
        elif "warning" in text.lower():
            fmt.setForeground(QColor("#E8A020"))
        else:
            fmt.setForeground(QColor("#a8b4c0"))

        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self.log_panel.setTextCursor(cursor)
        self.log_panel.ensureCursorVisible()

    # ------------------------------------------------------------------ #
    #  Pipeline execution                                                  #
    # ------------------------------------------------------------------ #
    def _run_pipeline(self):
        """Run steps 5 → 6 → 7 → 8 sequentially."""
        # Validate video
        video_path = self.ctrl.state.video_path
        if not video_path or not video_path.exists():
            QMessageBox.warning(self, "Missing Video",
                                "Please select a valid video file in the Calibration screen first.")
            return

        # Validate model
        if not self.ctrl.is_model_loaded():
            mp = self.ctrl.get_model_path()
            model_name = mp.name if mp else "yolov9t.pt"
            
            reply = QMessageBox.question(
                self, "Missing Model",
                f"The model '{model_name}' was not found in models/ directory.\n\n"
                "Would you like to download it automatically now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                from PyQt6.QtWidgets import QProgressDialog
                from PyQt6.QtCore import Qt, QEventLoop
                from traffic_analysis_gui.workers.download_worker import ModelDownloadWorker
                
                progress_dialog = QProgressDialog(f"Downloading {model_name}...", "Cancel", 0, 100, self)
                progress_dialog.setWindowTitle("Downloading Model")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setValue(0)
                progress_dialog.show()
                
                worker = ModelDownloadWorker(model_name, self.ctrl.state.models_dir)
                worker.progress.connect(progress_dialog.setValue)
                
                self._download_worker = worker
                loop = QEventLoop()
                
                success_status = [False]
                error_msg = [""]
                
                def on_finished(success, message):
                    success_status[0] = success
                    error_msg[0] = message
                    loop.quit()
                    
                worker.finished.connect(on_finished)
                progress_dialog.canceled.connect(worker.terminate)
                progress_dialog.canceled.connect(loop.quit)
                
                worker.start()
                loop.exec()
                
                if success_status[0]:
                    QMessageBox.information(self, "Download Complete", f"Successfully downloaded {model_name}!")
                    self.model_downloaded.emit()
                else:
                    QMessageBox.warning(self, "Download Failed", f"Failed to download {model_name}:\n{error_msg[0]}")
                    return
            else:
                return

        # Validate calibration
        od = self.ctrl.state.output_dir
        missing = []
        if not (od / "homography_matrix.npy").exists():
            missing.append("homography_matrix.npy")
        if not (od / "gcps_pixel.json").exists():
            missing.append("gcps_pixel.json")
        if not (od / "detection_line.json").exists():
            missing.append("detection_line.json")
        if missing:
            QMessageBox.warning(self, "Missing Calibration",
                                f"Calibration files missing:\n• " +
                                "\n• ".join(missing) +
                                "\n\nPlease complete the Calibration step first.")
            return

        self._running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_panel.clear()
        self.append_log("═══ Pipeline started ═══")

        # Start with step 5
        self._start_step5()

    def _start_step5(self):
        """Start step 5 via QProcess."""
        self._set_step_ui(5, "running")
        self.ctrl.set_step_status(5, "running")

        script_path = str(self.ctrl.state.repo_root / "scripts" / "step5_detect_track.py")
        python_exe = sys.executable

        frames_val = 0 if self.whole_video_cb.isChecked() else self.frames_spin.value()

        self._step5_worker = Step5Worker(
            script_path=script_path,
            python_exe=python_exe,
            frames=frames_val,
            no_video=not self.save_video_cb.isChecked(),
        )
        self._step5_worker.progress.connect(lambda f: self.update_progress(5, f))
        self._step5_worker.log.connect(self.append_log)
        self._step5_worker.done.connect(self._on_step5_done)
        self._step5_worker.error.connect(self._on_step_error_str)
        self._step5_worker.start()

    def _on_step5_done(self):
        self._set_step_ui(5, "done")
        self.ctrl.set_step_status(5, "done")
        self.pipeline_step_done.emit(5)
        if self._running:
            self._start_generic_step(6, "step6_speed.py")

    def _start_generic_step(self, step: int, script_name: str):
        """Start steps 6, 7, or 8 using StepWorker."""
        if not self._running:
            return
        self._set_step_ui(step, "running")
        self.ctrl.set_step_status(step, "running")

        script_path = self.ctrl.state.repo_root / "scripts" / script_name
        worker = StepWorker(step, script_path)
        worker.progress.connect(lambda s, f: self.update_progress(s, f))
        worker.log.connect(self.append_log)
        worker.done.connect(self._on_generic_step_done)
        worker.error.connect(self._on_step_error)
        self._current_worker = worker
        worker.start()

    def _on_generic_step_done(self, step: int):
        self._set_step_ui(step, "done")
        self.ctrl.set_step_status(step, "done")
        self.pipeline_step_done.emit(step)

        # Chain to next step
        next_steps = {6: ("step7_traffic_params.py", 7), 7: ("step8_plots.py", 8)}
        if step in next_steps:
            script_name, next_step = next_steps[step]
            self._start_generic_step(next_step, script_name)
        elif step == 8:
            self._on_pipeline_complete()

    def _on_pipeline_complete(self):
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_log("═══ Pipeline complete! ═══")
        self.pipeline_all_done.emit()

    def _on_step_error(self, step: int, msg: str):
        self._set_step_ui(step, "error")
        self.ctrl.set_step_status(step, "error")
        self.append_log(f"ERROR in step {step}: {msg}")
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_step_error_str(self, msg: str):
        """Error handler for Step5Worker which emits error(str)."""
        self._on_step_error(5, msg)

    def _stop_pipeline(self):
        """Stop the running pipeline."""
        self._running = False
        if self._step5_worker:
            self._step5_worker.stop()
        if self._current_worker:
            self._current_worker.stop()
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_log("Pipeline stopped by user.")
        # Reset running steps to idle
        for step in range(5, 9):
            if self.ctrl.state.step_status.get(step) == "running":
                self._set_step_ui(step, "idle")
                self.ctrl.set_step_status(step, "idle")

    def showEvent(self, event):
        super().showEvent(event)
        if self.ctrl.state.video_path:
            self.video_label.setText(self.ctrl.state.video_path.name)
        else:
            self.video_label.setText("None")

        # Refresh all step cards from current controller state
        for step in range(5, 9):
            status = self.ctrl.state.step_status.get(step, "idle")
            progress_val = self.ctrl.state.step_progress.get(step, 0.0)
            self._set_step_ui(step, status)
            card = self.step_cards.get(step)
            if card:
                progress = card.findChild(QProgressBar, f"progress_{step}")
                if progress:
                    progress.setValue(int(progress_val * 100))
