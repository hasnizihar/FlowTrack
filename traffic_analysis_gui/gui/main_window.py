"""
main_window.py — QMainWindow with sidebar navigation, topbar, and stacked screens.

The GUI follows the pipeline execution flow:
  1. Dashboard  — overview + quick-start guidance
  2. Calibration — steps 1–4 (extract frame, mark GCPs, road area, detection line, homography)
  3. Analysis   — steps 5–8 (detect/track, speed, params, plots)
  4. Results    — view charts, data tables, exports
  5. Settings   — configuration
"""

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QButtonGroup, QSpacerItem, QSizePolicy,
    QComboBox, QMessageBox
)
# pyrefly: ignore [missing-import]
from PyQt6.QtCore import Qt, QSize
# pyrefly: ignore [missing-import]
from PyQt6.QtGui import QFont, QIcon

from traffic_analysis_gui.controllers.app_controller import AppController
from traffic_analysis_gui.gui.screen_dashboard import DashboardScreen
from traffic_analysis_gui.gui.screen_calibration import CalibrationScreen
from traffic_analysis_gui.gui.screen_analysis import AnalysisScreen
from traffic_analysis_gui.gui.screen_results import ResultsScreen
from traffic_analysis_gui.gui.screen_settings import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctrl = AppController()
        self._build_layout()
        self._connect_signals()
        # Start on Dashboard
        self.switch_screen(0)

    # ------------------------------------------------------------------ #
    #  Layout construction                                                 #
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Topbar ---
        self.topbar = self._build_topbar()
        root_layout.addWidget(self.topbar)

        # --- Body (sidebar + content stack) ---
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        body_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")

        # Instantiate screens — order matches the workflow
        self.screen_dashboard = DashboardScreen(self.ctrl, self)
        self.screen_calibration = CalibrationScreen(self.ctrl)
        self.screen_analysis = AnalysisScreen(self.ctrl)
        self.screen_results = ResultsScreen(self.ctrl)
        self.screen_settings = SettingsScreen(self.ctrl)

        self.stack.addWidget(self.screen_dashboard)    # 0
        self.stack.addWidget(self.screen_calibration)  # 1
        self.stack.addWidget(self.screen_analysis)     # 2
        self.stack.addWidget(self.screen_results)      # 3
        self.stack.addWidget(self.screen_settings)     # 4

        body_layout.addWidget(self.stack)
        root_layout.addWidget(body)

    # ------------------------------------------------------------------ #
    #  Sidebar                                                             #
    # ------------------------------------------------------------------ #
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(54)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("FT")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            "color: #4a9eff; font-size: 16px; font-weight: 800; "
            "padding: 8px 0; border-bottom: 1px solid #2e3640; margin-bottom: 4px;"
        )
        layout.addWidget(logo)

        # Navigation buttons — labelled with step numbers to show flow
        self.sidebar_buttons = []
        self.sidebar_group = QButtonGroup(self)
        self.sidebar_group.setExclusive(True)

        icons = [
            ("⌂", "Dashboard"),
            ("⌖", "1. Calibration"),
            ("🔍", "2. Analysis"),
            ("📊", "3. Results"),
        ]

        for i, (icon_text, tooltip) in enumerate(icons):
            btn = QPushButton(icon_text)
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            btn.setFixedSize(42, 42)
            btn.setToolTip(tooltip)
            self.sidebar_group.addButton(btn, i)
            self.sidebar_buttons.append(btn)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Settings at bottom
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SidebarButton")
        settings_btn.setCheckable(True)
        settings_btn.setFixedSize(42, 42)
        settings_btn.setToolTip("Settings")
        self.sidebar_group.addButton(settings_btn, 4)
        self.sidebar_buttons.append(settings_btn)
        layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return sidebar

    # ------------------------------------------------------------------ #
    #  Topbar                                                              #
    # ------------------------------------------------------------------ #
    def _build_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(44)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.topbar_title = QLabel("Dashboard")
        self.topbar_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #1a1a1a;")
        layout.addWidget(self.topbar_title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #e0e0e0;")
        sep.setFixedHeight(24)
        layout.addWidget(sep)

        self.topbar_subtitle = QLabel("AI-Powered Traffic Flow Analysis and Vehicle Tracking System")
        self.topbar_subtitle.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(self.topbar_subtitle)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Model status chip
        model_loaded = self.ctrl.is_model_loaded()
        dot_color = "#3B8a22" if model_loaded else "#cc3333"
        status_text = "Model loaded" if model_loaded else "No model"
        self.model_status = QLabel(f"● {status_text}")
        self.model_status.setStyleSheet(f"color: {dot_color}; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.model_status)

        # Model selector dropdown
        layout.addWidget(QLabel("Model:"))
        self.model_selector = QComboBox()
        self.model_selector.setStyleSheet(
            "QComboBox { font-size: 11px; color: #333; background: #eee; "
            "border: 1px solid #ccc; border-radius: 4px; padding: 2px 6px; min-width: 130px; }"
            "QComboBox::drop-down { border: none; }"
        )
        layout.addWidget(self.model_selector)

        # Model download button
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("SecondaryBtn")
        self.download_btn.setStyleSheet(
            "QPushButton { font-size: 11px; padding: 3px 10px; background: #e8f0fb; color: #185FA5; border: 1px solid #185FA5; border-radius: 4px; }"
            "QPushButton:hover { background: #d0e1f9; }"
            "QPushButton:disabled { color: #aaa; border-color: #ddd; background: #f5f5f5; }"
        )
        self.download_btn.clicked.connect(self._download_selected_model)
        layout.addWidget(self.download_btn)

        self._populate_topbar_models()
        self.model_selector.currentIndexChanged.connect(self._on_model_changed_by_user)
        self._update_download_btn_state()

        return topbar

    # ------------------------------------------------------------------ #
    #  Screen switching                                                    #
    # ------------------------------------------------------------------ #
    def switch_screen(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = ["Dashboard", "Step 1: Calibration", "Step 2: Analysis", "Step 3: Results", "Settings"]
        subtitles = [
            "Pipeline overview & workflow guide",
            "Extract frame → Mark GCPs → Road area → Detection line → Homography",
            "Detect & track → Speed → Traffic params → Plots",
            "Charts, data tables & exports",
            "Configuration & preferences",
        ]
        if 0 <= index < len(titles):
            self.topbar_title.setText(titles[index])
            self.topbar_subtitle.setText(subtitles[index])
        # Update sidebar button states
        if 0 <= index < len(self.sidebar_buttons):
            self.sidebar_buttons[index].setChecked(True)

    def navigate_to(self, screen_name: str):
        """Navigate to a screen by name — used by Dashboard quick-action buttons."""
        mapping = {
            "calibration": 1,
            "analysis": 2,
            "results": 3,
            "settings": 4,
        }
        idx = mapping.get(screen_name, 0)
        self.switch_screen(idx)

    # ------------------------------------------------------------------ #
    #  Signal / slot wiring                                                #
    # ------------------------------------------------------------------ #
    def _connect_signals(self):
        # Sidebar navigation
        self.sidebar_group.idClicked.connect(self.switch_screen)

        # Dashboard quick-action buttons
        self.screen_dashboard.navigate_requested.connect(self.navigate_to)

        # Analysis screen pipeline signals → dashboard/results refresh
        self.screen_analysis.pipeline_step_done.connect(self._on_step_done)
        self.screen_analysis.pipeline_all_done.connect(self._on_pipeline_done)
        self.screen_analysis.model_downloaded.connect(self._on_model_downloaded)
        self.screen_settings.config_saved.connect(self._on_settings_saved)

    def _on_settings_saved(self, updates: dict):
        self._update_model_status_chip()
        self._populate_topbar_models()
        self._update_download_btn_state()

    def _on_step_done(self, step: int):
        """Called when any pipeline step completes."""
        self.ctrl.set_step_status(step, "done")
        self.ctrl.set_step_progress(step, 1.0)
        self.screen_dashboard.refresh()

    def _on_pipeline_done(self):
        """Called when the entire pipeline finishes."""
        self.screen_dashboard.refresh()
        self.screen_results.refresh()
        self._update_model_status_chip()
        self._populate_topbar_models()

    def _populate_topbar_models(self):
        self.model_selector.blockSignals(True)
        self.model_selector.clear()

        # Scan for existing models in models/
        existing_models = []
        models_dir = self.ctrl.state.models_dir
        if models_dir.exists():
            for pt in models_dir.glob("*.pt"):
                existing_models.append(pt.name)

        # Default choices
        presets = [
            "yolov9t.pt", "yolov9s.pt", "yolov9m.pt", "yolov9c.pt", "yolov9e.pt",
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"
        ]
        for p in presets:
            if p not in existing_models:
                existing_models.append(p)

        # Add items to combo box
        for m in sorted(existing_models):
            # Check if model exists locally
            local_path = self.ctrl.state.models_dir / m
            status = " (loaded)" if local_path.exists() else " (will download)"
            self.model_selector.addItem(f"{m}{status}", m)

        self.model_selector.addItem("Browse for model...", "browse")

        # Set active model
        mp = self.ctrl.get_model_path()
        active_name = mp.name if mp else "yolov9t.pt"

        # Select active
        for idx in range(self.model_selector.count()):
            if self.model_selector.itemData(idx) == active_name:
                self.model_selector.setCurrentIndex(idx)
                break

        self.model_selector.blockSignals(False)
        self._update_download_btn_state()

    def _on_model_changed_by_user(self, index: int):
        model_data = self.model_selector.itemData(index)
        if not model_data:
            return

        if model_data == "browse":
            # pyrefly: ignore [missing-import]
            from PyQt6.QtWidgets import QFileDialog
            from pathlib import Path
            path, _ = QFileDialog.getOpenFileName(
                self, "Select YOLO Model (.pt)", str(self.ctrl.state.repo_root),
                "YOLO Model Files (*.pt);;All Files (*)"
            )
            if path:
                path = Path(path)
                dest = self.ctrl.state.models_dir / path.name
                if path.resolve() != dest.resolve():
                    import shutil
                    self.ctrl.state.models_dir.mkdir(exist_ok=True)
                    try:
                        shutil.copy(str(path), str(dest))
                    except Exception as e:
                        print(f"[Warning] Failed to copy model: {e}")

                self.ctrl.save_config({"YOLO_MODEL": path.name})
                self._populate_topbar_models()
                self._update_model_status_chip()
            else:
                self._populate_topbar_models()
        else:
            self.ctrl.save_config({"YOLO_MODEL": model_data})
            self._update_model_status_chip()
            self._populate_topbar_models()
        
        self._update_download_btn_state()

    def _update_model_status_chip(self):
        model_loaded = self.ctrl.is_model_loaded()
        dot_color = "#3B8a22" if model_loaded else "#cc3333"
        status_text = "Model loaded" if model_loaded else "No model local"
        self.model_status.setText(f"● {status_text}")
        self.model_status.setStyleSheet(f"color: {dot_color}; font-size: 11px; font-weight: 600;")

    def _update_download_btn_state(self):
        model_name = self.model_selector.currentData()
        if not model_name or model_name == "browse":
            self.download_btn.hide()
            return
            
        local_path = self.ctrl.state.models_dir / model_name
        if local_path.exists():
            self.download_btn.hide()
        else:
            self.download_btn.show()
            self.download_btn.setEnabled(True)

    def _on_model_downloaded(self):
        self._update_model_status_chip()
        self._populate_topbar_models()
        self._update_download_btn_state()

    def _download_selected_model(self):
        model_name = self.model_selector.currentData()
        if not model_name or model_name == "browse":
            return
            
        # pyrefly: ignore [missing-import]
        from PyQt6.QtWidgets import QProgressDialog
        # pyrefly: ignore [missing-import]
        from PyQt6.QtCore import Qt
        from traffic_analysis_gui.workers.download_worker import ModelDownloadWorker
        
        self.download_btn.setEnabled(False)
        self.model_selector.setEnabled(False)
        
        # Create a progress dialog
        self.progress_dialog = QProgressDialog(f"Downloading {model_name}...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Downloading Model")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        
        self.download_worker = ModelDownloadWorker(model_name, self.ctrl.state.models_dir)
        self.download_worker.progress.connect(self.progress_dialog.setValue)
        
        def on_finished(success, message):
            self.model_selector.setEnabled(True)
            self._update_model_status_chip()
            self._populate_topbar_models()
            self._update_download_btn_state()
            
            if success:
                QMessageBox.information(self, "Download Complete", f"Successfully downloaded {model_name}!")
            else:
                QMessageBox.warning(self, "Download Failed", f"Failed to download {model_name}:\n{message}")
                
        self.download_worker.finished.connect(on_finished)
        self.progress_dialog.canceled.connect(self.download_worker.terminate)
        self.download_worker.start()
