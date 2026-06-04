"""
screen_settings.py — Configuration editor with section navigation.

Two-column layout:
  - Left: QListWidget for section navigation
  - Right: QStackedWidget with one page per section
"""

import sys
import webbrowser
from pathlib import Path

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QListWidget, QStackedWidget, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QFormLayout, QMessageBox, QFileDialog,
    QSizePolicy, QSpacerItem, QScrollArea,
)
# pyrefly: ignore [missing-import]
from PyQt6.QtCore import Qt, pyqtSignal


class SettingsScreen(QWidget):
    config_saved = pyqtSignal(dict)

    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._fields = {}
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # --- Left: section list ---
        self.section_list = QListWidget()
        self.section_list.setFixedWidth(140)
        self.section_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item { padding: 8px 12px; border-radius: 6px; font-size: 12px; }"
            "QListWidget::item:selected { background: #e8f0fb; color: #185FA5; font-weight: 600; }"
            "QListWidget::item:hover { background: #f0f0f0; }"
        )
        sections = ["Model", "Paths", "Detection", "Speed", "Output", "About"]
        for s in sections:
            self.section_list.addItem(s)
        self.section_list.currentRowChanged.connect(self._switch_section)
        main_layout.addWidget(self.section_list)

        # --- Right: stacked sections ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.section_stack = QStackedWidget()
        self._build_model_section()
        self._build_paths_section()
        self._build_detection_section()
        self._build_speed_section()
        self._build_output_section()
        self._build_about_section()
        right_layout.addWidget(self.section_stack)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("SecondaryBtn")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)

        right_layout.addLayout(btn_row)
        main_layout.addWidget(right_panel, stretch=1)

        # Start on first section
        self.section_list.setCurrentRow(0)

    def _switch_section(self, index: int):
        self.section_stack.setCurrentIndex(index)

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #
    def _create_section_widget(self) -> tuple:
        """Create a scrollable section widget and return (scroll, form_layout)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        widget = QFrame()
        widget.setObjectName("Card")
        form = QFormLayout(widget)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(12)
        scroll.setWidget(widget)
        self.section_stack.addWidget(scroll)
        return scroll, form

    def _build_model_section(self):
        _, form = self._create_section_widget()

        header = QLabel("Model Configuration")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        # Model file
        self._fields["model_combo"] = QComboBox()
        self._populate_models()
        form.addRow("Model file:", self._fields["model_combo"])

        # Device
        self._fields["device_combo"] = QComboBox()
        self._fields["device_combo"].addItems(["cpu", "cuda:0", "cuda:1"])
        form.addRow("Device:", self._fields["device_combo"])

        # Confidence threshold
        self._fields["conf_thresh"] = QDoubleSpinBox()
        self._fields["conf_thresh"].setRange(0.0, 1.0)
        self._fields["conf_thresh"].setSingleStep(0.05)
        self._fields["conf_thresh"].setValue(0.25)
        form.addRow("Confidence threshold:", self._fields["conf_thresh"])

        # IoU threshold
        self._fields["iou_thresh"] = QDoubleSpinBox()
        self._fields["iou_thresh"].setRange(0.0, 1.0)
        self._fields["iou_thresh"].setSingleStep(0.05)
        self._fields["iou_thresh"].setValue(0.45)
        form.addRow("IoU threshold:", self._fields["iou_thresh"])

    def _build_paths_section(self):
        _, form = self._create_section_widget()

        header = QLabel("File Paths")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        # Video path
        video_row = QHBoxLayout()
        self._fields["video_path"] = QLineEdit()
        video_row.addWidget(self._fields["video_path"])
        browse_vid = QPushButton("Browse")
        browse_vid.setObjectName("SecondaryBtn")
        browse_vid.clicked.connect(lambda: self._browse_file("video_path", "Video Files (*.mp4 *.avi *.mkv)"))
        video_row.addWidget(browse_vid)
        form.addRow("Video path:", video_row)

        # Output directory
        out_row = QHBoxLayout()
        self._fields["output_dir"] = QLineEdit()
        out_row.addWidget(self._fields["output_dir"])
        browse_out = QPushButton("Browse")
        browse_out.setObjectName("SecondaryBtn")
        browse_out.clicked.connect(lambda: self._browse_dir("output_dir"))
        out_row.addWidget(browse_out)
        form.addRow("Output directory:", out_row)

        # Models directory
        model_row = QHBoxLayout()
        self._fields["models_dir"] = QLineEdit()
        model_row.addWidget(self._fields["models_dir"])
        browse_model = QPushButton("Browse")
        browse_model.setObjectName("SecondaryBtn")
        browse_model.clicked.connect(lambda: self._browse_dir("models_dir"))
        model_row.addWidget(browse_model)
        form.addRow("Models directory:", model_row)

    def _build_detection_section(self):
        _, form = self._create_section_widget()

        header = QLabel("Detection Settings")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        self._fields["frame_skip"] = QSpinBox()
        self._fields["frame_skip"].setRange(1, 10)
        self._fields["frame_skip"].setValue(1)
        form.addRow("Frame skip:", self._fields["frame_skip"])

        self._fields["max_frames"] = QSpinBox()
        self._fields["max_frames"].setRange(0, 999999)
        self._fields["max_frames"].setValue(0)
        self._fields["max_frames"].setToolTip("0 = process all frames")
        form.addRow("Max frames (0=all):", self._fields["max_frames"])

        self._fields["save_video"] = QCheckBox("Save annotated video")
        self._fields["save_video"].setChecked(True)
        form.addRow("", self._fields["save_video"])

    def _build_speed_section(self):
        _, form = self._create_section_widget()

        header = QLabel("Speed Estimation")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        self._fields["speed_smooth"] = QSpinBox()
        self._fields["speed_smooth"].setRange(1, 50)
        self._fields["speed_smooth"].setValue(5)
        form.addRow("Smoothing window:", self._fields["speed_smooth"])

        self._fields["min_track_len"] = QSpinBox()
        self._fields["min_track_len"].setRange(1, 100)
        self._fields["min_track_len"].setValue(3)
        form.addRow("Min track length:", self._fields["min_track_len"])

    def _build_output_section(self):
        _, form = self._create_section_widget()

        header = QLabel("Output Configuration")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        # Flow intervals
        self._fields["flow_1min"] = QCheckBox("1-minute intervals")
        self._fields["flow_1min"].setChecked(True)
        form.addRow("Flow intervals:", self._fields["flow_1min"])

        self._fields["flow_5min"] = QCheckBox("5-minute intervals")
        self._fields["flow_5min"].setChecked(True)
        form.addRow("", self._fields["flow_5min"])

        self._fields["flow_10min"] = QCheckBox("10-minute intervals")
        self._fields["flow_10min"].setChecked(True)
        form.addRow("", self._fields["flow_10min"])

        # Chart DPI
        self._fields["chart_dpi"] = QSpinBox()
        self._fields["chart_dpi"].setRange(72, 300)
        self._fields["chart_dpi"].setValue(150)
        form.addRow("Chart DPI:", self._fields["chart_dpi"])

        # Chart format
        self._fields["chart_format"] = QComboBox()
        self._fields["chart_format"].addItems(["png", "pdf", "svg"])
        form.addRow("Chart format:", self._fields["chart_format"])

    def _build_about_section(self):
        _, form = self._create_section_widget()

        header = QLabel("About")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #333; margin-bottom: 4px;")
        form.addRow(header)

        form.addRow("Application:", QLabel("FlowTrack"))
        form.addRow("Version:", QLabel("1.0.0"))
        form.addRow("Python:", QLabel(sys.version.split()[0]))

        try:
            # pyrefly: ignore [missing-import]
            from PyQt6.QtCore import PYQT_VERSION_STR
            form.addRow("PyQt6:", QLabel(PYQT_VERSION_STR))
        except Exception:
            form.addRow("PyQt6:", QLabel("Unknown"))

        form.addRow("Repository:", QLabel("github.com/hasnizihar/YOLOv9-Traffic-Analysis-Pipeline"))

        open_repo = QPushButton("Open Repository")
        open_repo.setObjectName("SecondaryBtn")
        open_repo.clicked.connect(
            lambda: webbrowser.open("https://github.com/hasnizihar/YOLOv9-Traffic-Analysis-Pipeline"))
        form.addRow("", open_repo)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    def _populate_models(self):
        combo = self._fields.get("model_combo")
        if not combo:
            return
        combo.clear()
        models_dir = self.ctrl.state.models_dir
        if models_dir.exists():
            for pt in sorted(models_dir.glob("*.pt")):
                combo.addItem(pt.name, str(pt))
        if combo.count() == 0:
            combo.addItem("No models found")

    def _browse_file(self, field_key: str, file_filter: str):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", str(self.ctrl.state.repo_root), file_filter)
        if path:
            self._fields[field_key].setText(path)

    def _browse_dir(self, field_key: str):
        path = QFileDialog.getExistingDirectory(
            self, "Select Directory", str(self.ctrl.state.repo_root))
        if path:
            self._fields[field_key].setText(path)

    def _load_from_config(self):
        """Populate fields from config.py."""
        cfg = self.ctrl.get_config()

        # Confidence
        if "YOLO_CONFIDENCE" in cfg:
            try:
                self._fields["conf_thresh"].setValue(float(cfg["YOLO_CONFIDENCE"]))
            except (ValueError, TypeError):
                pass

        # Plot DPI
        if "PLOT_DPI" in cfg:
            try:
                self._fields["chart_dpi"].setValue(int(cfg["PLOT_DPI"]))
            except (ValueError, TypeError):
                pass

        # Video path
        if "VIDEO_PATH" in cfg:
            self._fields["video_path"].setText(str(cfg["VIDEO_PATH"]))

        # Output dir
        self._fields["output_dir"].setText(str(self.ctrl.state.output_dir))
        self._fields["models_dir"].setText(str(self.ctrl.state.models_dir))

        self._populate_models()

    def _save_settings(self):
        """Save current field values back to config.py."""
        updates = {}

        # Confidence
        updates["YOLO_CONFIDENCE"] = self._fields["conf_thresh"].value()

        # DPI
        updates["PLOT_DPI"] = self._fields["chart_dpi"].value()

        # Flow intervals
        intervals = []
        if self._fields["flow_1min"].isChecked():
            intervals.append(1)
        if self._fields["flow_5min"].isChecked():
            intervals.append(5)
        if self._fields["flow_10min"].isChecked():
            intervals.append(10)
        updates["FLOW_INTERVALS"] = intervals

        try:
            self.ctrl.save_config(updates)
            self.config_saved.emit(updates)
            QMessageBox.information(self, "Settings Saved",
                                    "Configuration saved to scripts/config.py.")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save settings:\n{e}")

    def _reset_defaults(self):
        """Re-read config.py and populate fields."""
        self._load_from_config()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_from_config()
