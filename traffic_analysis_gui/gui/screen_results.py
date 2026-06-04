"""
screen_results.py — Chart viewer, data tables, file list, and summary sidebar.

Uses QTabWidget with three tabs: Charts, Data Tables, Output Files.
Right sidebar shows summary statistics.
"""

import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QScrollArea, QSizePolicy, QMenu,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QAction

from traffic_analysis_gui.controllers.results_manager import ResultsManager


class ResultsScreen(QWidget):
    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.rm = ResultsManager(ctrl.state.output_dir)
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # --- Main content (tabs) ---
        self.tabs = QTabWidget()
        self._build_charts_tab()
        self._build_data_tab()
        self._build_files_tab()
        main_layout.addWidget(self.tabs, stretch=1)

        # --- Right sidebar ---
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

    # ------------------------------------------------------------------ #
    #  Charts tab                                                          #
    # ------------------------------------------------------------------ #
    def _build_charts_tab(self):
        widget = QWidget()
        self.charts_grid = QGridLayout(widget)
        self.charts_grid.setSpacing(12)
        self.chart_labels = {}

        chart_info = [
            ("flow_plot_5min", "Flow Rate (5-min)", 0, 0),
            ("composition_pie", "Vehicle Composition", 0, 1),
            ("speed_histograms", "Speed Distributions", 1, 0),
            ("composition_bar", "Composition by Lane", 1, 1),
        ]

        for name, title, row, col in chart_info:
            card = self._create_chart_card(name, title)
            self.charts_grid.addWidget(card, row, col)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, "Charts")

    def _create_chart_card(self, name: str, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header
        header_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #333;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        dl_btn = QPushButton("💾")
        dl_btn.setToolTip("Save chart")
        dl_btn.setFixedSize(28, 28)
        dl_btn.setStyleSheet("border: none; font-size: 14px;")
        dl_btn.clicked.connect(lambda checked, n=name: self._download_chart(n))
        header_row.addWidget(dl_btn)
        layout.addLayout(header_row)

        # Image label
        img_label = QLabel("— Not yet generated —")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("color: #aaa; font-size: 11px;")
        img_label.setMinimumHeight(220)
        img_label.setScaledContents(False)
        layout.addWidget(img_label)

        self.chart_labels[name] = img_label
        return card

    def _download_chart(self, name: str):
        charts = self.rm.get_chart_paths()
        src = charts.get(name)
        if src and src.exists():
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save Chart", f"{name}.png", "PNG (*.png)")
            if dest:
                shutil.copy2(str(src), dest)
                QMessageBox.information(self, "Saved", f"Chart saved to:\n{dest}")
        else:
            QMessageBox.information(self, "Not Available", "This chart has not been generated yet.")

    # ------------------------------------------------------------------ #
    #  Data tables tab                                                     #
    # ------------------------------------------------------------------ #
    def _build_data_tab(self):
        self.data_tabs = QTabWidget()
        self.data_tables = {}

        csv_files = [
            ("vehicle_counts.csv", "Vehicle Counts"),
            ("vehicle_speeds.csv", "Vehicle Speeds"),
            ("flow_1min.csv", "Flow (1 min)"),
            ("flow_5min.csv", "Flow (5 min)"),
            ("composition.csv", "Composition"),
            ("speed_stats.csv", "Speed Stats"),
        ]

        for filename, label in csv_files:
            table = QTableWidget()
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            self.data_tables[filename] = table
            self.data_tabs.addTab(table, label)

        self.tabs.addTab(self.data_tabs, "Data Tables")

    # ------------------------------------------------------------------ #
    #  Output files tab                                                    #
    # ------------------------------------------------------------------ #
    def _build_files_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.files_list = QListWidget()
        self.files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.files_list.customContextMenuRequested.connect(self._file_context_menu)
        layout.addWidget(self.files_list)

        self.tabs.addTab(widget, "Output Files")

    def _file_context_menu(self, pos):
        item = self.files_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        open_action = menu.addAction("Open in Explorer")
        copy_action = menu.addAction("Copy path")

        action = menu.exec(self.files_list.mapToGlobal(pos))
        filename = item.text().split(" — ")[0].strip()
        filepath = self.ctrl.state.output_dir / filename

        if action == open_action:
            os.startfile(str(filepath.parent))
        elif action == copy_action:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(str(filepath))

    # ------------------------------------------------------------------ #
    #  Right sidebar                                                       #
    # ------------------------------------------------------------------ #
    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Card")
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Speed statistics
        speed_header = QLabel("Speed Statistics")
        speed_header.setStyleSheet("font-size: 12px; font-weight: 700; color: #333;")
        layout.addWidget(speed_header)

        self.stat_labels = {}
        speed_stats = [
            ("speed_mean", "Mean Speed"),
            ("speed_std", "Std Dev"),
            ("speed_85pct", "85th Percentile"),
            ("speed_max", "Max Speed"),
        ]
        for key, label in speed_stats:
            row = QHBoxLayout()
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("font-size: 10px; color: #777;")
            row.addWidget(name_lbl)
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #333;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(val_lbl)
            layout.addLayout(row)
            self.stat_labels[key] = val_lbl

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e8e8e8;")
        layout.addWidget(sep)

        # Flow summary
        flow_header = QLabel("Flow Summary")
        flow_header.setStyleSheet("font-size: 12px; font-weight: 700; color: #333;")
        layout.addWidget(flow_header)

        flow_stats = [
            ("peak_flow", "Peak Flow (veh/hr)"),
            ("total_vehicles", "Total Vehicles"),
        ]
        for key, label in flow_stats:
            row = QHBoxLayout()
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("font-size: 10px; color: #777;")
            row.addWidget(name_lbl)
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #333;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(val_lbl)
            layout.addLayout(row)
            self.stat_labels[key] = val_lbl

        layout.addStretch()

        # Reset Data button
        self.reset_btn = QPushButton("Reset Data")
        self.reset_btn.setObjectName("SecondaryBtn")
        self.reset_btn.setStyleSheet(
            "QPushButton { color: #cc3333; border: 1px solid #cc3333; }"
            "QPushButton:hover { background: #feebeb; }"
        )
        self.reset_btn.clicked.connect(self._reset_data)
        layout.addWidget(self.reset_btn)

        # Export all button
        export_btn = QPushButton("Export All")
        export_btn.setObjectName("PrimaryBtn")
        export_btn.clicked.connect(self._export_all)
        layout.addWidget(export_btn)

        return sidebar

    def _export_all(self):
        dest = QFileDialog.getExistingDirectory(self, "Export Output To")
        if dest:
            try:
                dest_dir = Path(dest) / "traffic_analysis_output"
                if dest_dir.exists():
                    shutil.rmtree(str(dest_dir))
                shutil.copytree(str(self.ctrl.state.output_dir), str(dest_dir))
                QMessageBox.information(self, "Exported",
                                        f"All output files exported to:\n{dest_dir}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))

    def _reset_data(self):
        reply = QMessageBox.question(
            self, "Reset Data",
            "Are you sure you want to delete all generated analysis results, plots, and tables?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                od = self.ctrl.state.output_dir
                # List of generated files to remove
                files_to_remove = [
                    "vehicle_counts.csv",
                    "vehicle_speeds.csv",
                    "flow_1min.csv",
                    "flow_5min.csv",
                    "flow_10min.csv",
                    "composition.csv",
                    "speed_stats.csv",
                    "track_history.pkl",
                    "annotated_output.mp4",
                    "still_frame_annotated.jpg"
                ]
                
                # Delete files
                for fname in files_to_remove:
                    fpath = od / fname
                    if fpath.exists():
                        try:
                            fpath.unlink()
                        except Exception:
                            pass
                
                # Also delete all png files in output directory
                for f in od.glob("*.png"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
                
                # Clear pipeline state in controller
                for step in range(5, 9):
                    self.ctrl.set_step_status(step, "idle")
                    self.ctrl.set_step_progress(step, 0.0)

                self.refresh()
                QMessageBox.information(self, "Reset Successful", "All analysis results have been reset.")
            except Exception as e:
                QMessageBox.warning(self, "Reset Error", f"Failed to reset data:\n{e}")

    # ------------------------------------------------------------------ #
    #  Refresh                                                             #
    # ------------------------------------------------------------------ #
    def refresh(self):
        """Reload all charts, tables, and statistics."""
        # Charts
        charts = self.rm.get_chart_paths()
        for name, label in self.chart_labels.items():
            path = charts.get(name)
            if path and path.exists():
                pixmap = QPixmap(str(path))
                scaled = pixmap.scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(scaled)
            else:
                label.setText("— Not yet generated —")

        # Data tables
        try:
            import pandas as pd
            for filename, table in self.data_tables.items():
                csv_path = self.ctrl.state.output_dir / filename
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    table.setRowCount(len(df))
                    table.setColumnCount(len(df.columns))
                    table.setHorizontalHeaderLabels(list(df.columns))
                    for row_i, row in df.iterrows():
                        for col_i, val in enumerate(row):
                            table.setItem(row_i, col_i, QTableWidgetItem(str(val)))
                    table.horizontalHeader().setSectionResizeMode(
                        QHeaderView.ResizeMode.Stretch
                    )
                else:
                    table.setRowCount(0)
                    table.setColumnCount(0)
        except ImportError:
            pass

        # Output files list
        self.files_list.clear()
        od = self.ctrl.state.output_dir
        if od.exists():
            for f in sorted(od.iterdir()):
                if f.is_file():
                    size_kb = f.stat().st_size / 1024
                    self.files_list.addItem(f"{f.name} — {size_kb:.1f} KB")

        # Summary stats
        stats = self.rm.get_summary_stats()
        for key, label in self.stat_labels.items():
            val = stats.get(key)
            if val is not None:
                suffix = " km/h" if "speed" in key else ""
                label.setText(f"{val}{suffix}")
            else:
                label.setText("—")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
