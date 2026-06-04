"""
screen_dashboard.py — Workflow-guided dashboard showing pipeline status,
KPIs, and quick-action buttons to guide the user through the execution flow.

Flow: Calibration (steps 1–4) → Analysis (steps 5–8) → Results
"""

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QSizePolicy,
)
# pyrefly: ignore [missing-import]
from PyQt6.QtCore import Qt, pyqtSignal
# pyrefly: ignore [missing-import]
from PyQt6.QtGui import QFont

from traffic_analysis_gui.controllers.results_manager import ResultsManager


class DashboardScreen(QWidget):
    # Signal to request navigation to another screen
    navigate_requested = pyqtSignal(str)

    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.rm = ResultsManager(ctrl.state.output_dir)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # --- Welcome / Next-step banner ---
        self.banner = QFrame()
        self.banner.setObjectName("Card")
        self.banner.setStyleSheet(
            "QFrame#Card { "
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a365d, stop:1 #2a4365); "
            "  border: none; "
            "  border-radius: 12px; "
            "}"
        )
        self.banner.setMinimumHeight(96)
        
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(24, 16, 24, 16)
        banner_layout.setSpacing(20)

        # Left side text layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        self.banner_title = QLabel("Welcome to FlowTrack")
        self.banner_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        text_layout.addWidget(self.banner_title)

        self.banner_subtitle = QLabel("Follow the workflow: Calibration > Analysis > Results")
        self.banner_subtitle.setStyleSheet("font-size: 12px; color: #a0aec0;")
        text_layout.addWidget(self.banner_subtitle)
        
        banner_layout.addLayout(text_layout)
        banner_layout.addStretch()

        # Right side button
        self.next_step_btn = QPushButton("Start Calibration")
        self.next_step_btn.setObjectName("PrimaryBtn")
        self.next_step_btn.setFixedWidth(180)
        self.next_step_btn.setFixedHeight(36)
        self.next_step_btn.setStyleSheet(
            "QPushButton#PrimaryBtn { "
            "  background-color: #3182ce; "
            "  color: white; "
            "  font-size: 12px; "
            "  font-weight: 700; "
            "  border-radius: 6px; "
            "}"
            "QPushButton#PrimaryBtn:hover { "
            "  background-color: #4299e1; "
            "}"
            "QPushButton#PrimaryBtn:pressed { "
            "  background-color: #2b6cb0; "
            "}"
        )
        self.next_step_btn.clicked.connect(self._go_next_step)
        banner_layout.addWidget(self.next_step_btn)

        layout.addWidget(self.banner)

        # --- Workflow progress row (3 big phase cards) ---
        phase_header = QLabel("Workflow Progress")
        phase_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #333;")
        layout.addWidget(phase_header)

        phase_row = QHBoxLayout()
        phase_row.setSpacing(12)

        self.phase_calib = self._create_phase_card(
            "① Calibration", "Steps 1–4", "Extract frame, mark GCPs,\nroad area, detection line",
            "#185FA5", "calibration"
        )
        self.phase_analysis = self._create_phase_card(
            "② Analysis", "Steps 5–8", "Detect & track, speed estimation,\ntraffic params, generate plots",
            "#D85A30", "analysis"
        )
        self.phase_results = self._create_phase_card(
            "③ Results", "View output", "Charts, data tables,\nexport reports",
            "#3B8a22", "results"
        )
        phase_row.addWidget(self.phase_calib)
        phase_row.addWidget(self.phase_analysis)
        phase_row.addWidget(self.phase_results)
        layout.addLayout(phase_row)

        # --- Pipeline step status row (8 steps) ---
        steps_header = QLabel("Individual Step Status")
        steps_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #333;")
        layout.addWidget(steps_header)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.step_cards = {}

        step_names = {
            1: "Extract\nframe",   2: "Mark\nGCPs",
            3: "Homography",       4: "Annotate",
            5: "Detect &\ntrack",  6: "Speed\nest.",
            7: "Traffic\nparams",  8: "Plots",
        }

        for step_num, name in step_names.items():
            card = self._create_step_card(step_num, name)
            status_row.addWidget(card)
            self.step_cards[step_num] = card

        layout.addLayout(status_row)

        # --- KPI cards row ---
        kpi_header = QLabel("Key Metrics")
        kpi_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #333;")
        layout.addWidget(kpi_header)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.kpi_vehicles = self._create_kpi_card("Vehicles Detected", "--", "#185FA5")
        self.kpi_speed = self._create_kpi_card("Avg Speed (km/h)", "--", "#3B8a22")
        self.kpi_flow = self._create_kpi_card("Peak Flow (veh/hr)", "--", "#D85A30")
        self.kpi_progress = self._create_kpi_card_with_progress("Pipeline Progress", "0%")

        kpi_row.addWidget(self.kpi_vehicles)
        kpi_row.addWidget(self.kpi_speed)
        kpi_row.addWidget(self.kpi_flow)
        kpi_row.addWidget(self.kpi_progress)
        layout.addLayout(kpi_row)

        layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Phase card (big workflow step)                                       #
    # ------------------------------------------------------------------ #
    def _create_phase_card(self, title: str, subtitle: str, desc: str,
                           accent: str, nav_target: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(
            f"QFrame#Card {{ "
            f"  background: #ffffff; "
            f"  border: 1px solid #e8e8e8; "
            f"  border-left: 4px solid {accent}; "
            f"  border-radius: 8px; "
            f"}}"
        )
        card.setMinimumHeight(146)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 12, 14, 12)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {accent};")
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("phase_subtitle")
        sub_lbl.setStyleSheet("font-size: 10px; color: #888; font-weight: 600;")
        layout.addWidget(sub_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 10px; color: #555; line-height: 14px;")
        layout.addWidget(desc_lbl)

        # Progress bar
        progress = QProgressBar()
        progress.setObjectName("phase_progress")
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        layout.addWidget(progress)

        # Open button
        open_btn = QPushButton("Open >")
        open_btn.setObjectName("SecondaryBtn")
        open_btn.setFixedHeight(26)
        open_btn.setStyleSheet(
            f"QPushButton {{ font-size: 10px; font-weight: 600; color: {accent}; border: 1px solid {accent}; border-radius: 4px; padding: 2px 10px; background: transparent; }}"
            f"QPushButton:hover {{ background: {accent}; color: white; }}"
        )
        open_btn.clicked.connect(lambda: self.navigate_requested.emit(nav_target))
        layout.addWidget(open_btn)

        return card

    # ------------------------------------------------------------------ #
    #  Step cards (small)                                                   #
    # ------------------------------------------------------------------ #
    def _create_step_card(self, step_num: int, name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        step_label = QLabel(f"STEP {step_num}")
        step_label.setStyleSheet("font-size: 8px; color: #888; font-weight: 600;")
        layout.addWidget(step_label)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #333;")
        layout.addWidget(name_label)

        status_label = QLabel("● Idle")
        status_label.setObjectName(f"step_status_{step_num}")
        status_label.setStyleSheet("font-size: 9px; color: #999; font-weight: 600;")
        layout.addWidget(status_label)

        return card

    # ------------------------------------------------------------------ #
    #  KPI cards                                                            #
    # ------------------------------------------------------------------ #
    def _create_kpi_card(self, title: str, value: str, accent: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(96)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 9px; color: #666; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("kpi_value")
        value_lbl.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {accent};")
        layout.addWidget(value_lbl)

        layout.addStretch()
        return card

    def _create_kpi_card_with_progress(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(96)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 9px; color: #666; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("kpi_value")
        value_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #185FA5;")
        layout.addWidget(value_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        layout.addWidget(self.progress_bar)

        return card

    # ------------------------------------------------------------------ #
    #  Next step logic                                                     #
    # ------------------------------------------------------------------ #
    def _go_next_step(self):
        """Navigate to the next incomplete phase."""
        # Check calibration (steps 1-4)
        calib_done = all(
            self.ctrl.state.step_status.get(s) == "done" for s in [1, 2, 3]
        )
        if not calib_done:
            self.navigate_requested.emit("calibration")
            return

        # Check analysis (steps 5-8)
        analysis_done = all(
            self.ctrl.state.step_status.get(s) == "done" for s in [5, 6, 7, 8]
        )
        if not analysis_done:
            self.navigate_requested.emit("analysis")
            return

        # All done — go to results
        self.navigate_requested.emit("results")

    # ------------------------------------------------------------------ #
    #  Refresh                                                             #
    # ------------------------------------------------------------------ #
    def refresh(self):
        """Re-read all CSV files and update widgets."""
        # Update step status cards
        status_map = {
            "idle": ("● Idle", "#999", "#ffffff", "#e8e8e8"),
            "running": ("● Running…", "#E8A020", "#FFF9E6", "#FFEAA7"),
            "done": ("✓ Done", "#3B8a22", "#F0F9EB", "#C2E7B0"),
            "error": ("✗ Error", "#cc3333", "#FFF0F0", "#FFC0C0"),
        }
        for step_num, card in self.step_cards.items():
            status = self.ctrl.state.step_status.get(step_num, "idle")
            text, color, bg, border = status_map.get(status, ("● Idle", "#999", "#ffffff", "#e8e8e8"))
            status_label = card.findChild(QLabel, f"step_status_{step_num}")
            if status_label:
                status_label.setText(text)
                status_label.setStyleSheet(f"font-size: 9px; color: {color}; font-weight: 600;")
            card.setStyleSheet(
                f"QFrame#Card {{ "
                f"  background-color: {bg}; "
                f"  border: 1px solid {border}; "
                f"  border-radius: 6px; "
                f"}}"
            )

        # Update phase progress bars
        calib_done = sum(1 for s in [1, 2, 3, 4] if self.ctrl.state.step_status.get(s) == "done")
        analysis_done = sum(1 for s in [5, 6, 7, 8] if self.ctrl.state.step_status.get(s) == "done")

        calib_prog = self.phase_calib.findChild(QProgressBar, "phase_progress")
        if calib_prog:
            calib_prog.setValue(int(calib_done / 4 * 100))

        analysis_prog = self.phase_analysis.findChild(QProgressBar, "phase_progress")
        if analysis_prog:
            analysis_prog.setValue(int(analysis_done / 4 * 100))

        results_prog = self.phase_results.findChild(QProgressBar, "phase_progress")
        if results_prog:
            results_prog.setValue(100 if analysis_done == 4 else 0)

        # Update banner
        if calib_done < 3:  # steps 1,2,3 needed
            self.banner_title.setText("Next: Complete Calibration")
            self.banner_subtitle.setText("Extract a video frame, mark GCPs, draw road area & detection line")
            self.next_step_btn.setText("Start Calibration")
        elif analysis_done < 4:
            self.banner_title.setText("Next: Run Analysis Pipeline")
            self.banner_subtitle.setText("Calibration complete! Run detection, speed estimation, and chart generation")
            self.next_step_btn.setText("Start Analysis")
        else:
            self.banner_title.setText("✓ Pipeline Complete!")
            self.banner_subtitle.setText("All steps finished. View your results.")
            self.next_step_btn.setText("View Results")

        # Update KPIs
        stats = self.rm.get_summary_stats()

        val = str(stats.get("total_vehicles", "--"))
        self.kpi_vehicles.findChild(QLabel, "kpi_value").setText(val)

        val = str(stats.get("speed_mean", "--"))
        self.kpi_speed.findChild(QLabel, "kpi_value").setText(val)

        val = str(stats.get("peak_flow", "--"))
        self.kpi_flow.findChild(QLabel, "kpi_value").setText(val)

        done_steps = sum(1 for s in self.ctrl.state.step_status.values() if s == "done")
        pct = int(done_steps / 8 * 100)
        self.kpi_progress.findChild(QLabel, "kpi_value").setText(f"{pct}%")
        self.progress_bar.setValue(pct)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
