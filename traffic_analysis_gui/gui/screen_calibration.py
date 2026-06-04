"""
screen_calibration.py — Interactive calibration screen with canvas, GCP editor, and step controls.

Three-column layout:
  - Left panel (200px): step list + mode selector
  - Centre: interactive CalibCanvas for marking GCPs/ROI/line
  - Right panel (220px): GCP coordinate editor + homography button
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QLineEdit, QFormLayout, QMessageBox,
    QFileDialog, QSizePolicy, QSpacerItem, QSpinBox, QDialog,
    QComboBox, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPixmap, QPen, QColor, QBrush, QPolygon, QFont

from traffic_analysis_gui.controllers.calib_manager import CalibManager
from traffic_analysis_gui.workers.calib_worker import CalibWorker


# ================================================================== #
#  CalibCanvas — interactive image widget                              #
# ================================================================== #
class CalibCanvas(QWidget):
    """
    Displays a QPixmap (the still frame) and lets the user click
    to place GCPs, draw a road-area polygon, or draw a detection line.
    Emits signals whenever points change so the right panel can update.
    """
    gcp_changed = pyqtSignal(list)   # list of (x, y) pixel tuples
    roi_changed = pyqtSignal(list)
    line_changed = pyqtSignal(list)  # exactly 2 points

    MODE_GCP = 1
    MODE_ROI = 2
    MODE_LINE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.mode = self.MODE_GCP
        self.gcps = []
        self.roi = []
        self.line = []
        self._scale_factor = 1.0
        self._x_off = 0
        self._y_off = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(400, 300)

    def load_frame(self, image_path: str):
        """Load the still frame JPEG into self.pixmap."""
        self.pixmap = QPixmap(image_path)
        self._scale_factor = 1.0
        self.update()

    def mousePressEvent(self, event):
        if self.pixmap is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._canvas_to_image(event.pos())
            if pt[0] < 0 or pt[1] < 0:
                return
            if self.mode == self.MODE_GCP:
                self.gcps.append(pt)
                self.gcp_changed.emit(list(self.gcps))
            elif self.mode == self.MODE_ROI:
                self.roi.append(pt)
                self.roi_changed.emit(list(self.roi))
            elif self.mode == self.MODE_LINE:
                if len(self.line) < 2:
                    self.line.append(pt)
                    self.line_changed.emit(list(self.line))
        elif event.button() == Qt.MouseButton.RightButton:
            if self.mode == self.MODE_GCP and self.gcps:
                self.gcps.pop()
                self.gcp_changed.emit(list(self.gcps))
            elif self.mode == self.MODE_ROI and self.roi:
                self.roi.pop()
                self.roi_changed.emit(list(self.roi))
            elif self.mode == self.MODE_LINE and self.line:
                self.line.pop()
                self.line_changed.emit(list(self.line))
        self.update()

    def paintEvent(self, event):
        if not self.pixmap:
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#999")))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "No frame loaded.\nExtract a frame first.")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the scaled pixmap centred in the widget
        scaled = self.pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_off = (self.width() - scaled.width()) // 2
        y_off = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x_off, y_off, scaled)
        self._scale_factor = scaled.width() / self.pixmap.width() if self.pixmap.width() > 0 else 1.0
        self._x_off = x_off
        self._y_off = y_off

        # Draw GCP dots (blue circles with labels)
        painter.setPen(QPen(QColor("#185FA5"), 2))
        painter.setBrush(QBrush(QColor(24, 95, 165, 180)))
        for i, (px, py) in enumerate(self.gcps):
            cx, cy = self._image_to_canvas(px, py)
            painter.drawEllipse(cx - 6, cy - 6, 12, 12)
            painter.setPen(QPen(QColor("#B5D4F4"), 1))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(cx + 9, cy - 4, f"GCP{i+1}")
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#185FA5"), 2))

        # Draw ROI polygon (green dashed)
        if self.roi:
            painter.setPen(QPen(QColor("#5DCAA5"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(93, 202, 165, 30)))
            pts = [QPoint(*self._image_to_canvas(px, py)) for px, py in self.roi]
            if len(pts) >= 3:
                polygon = QPolygon(pts)
                painter.drawPolygon(polygon)
            elif len(pts) == 2:
                painter.drawLine(pts[0], pts[1])
            # Draw dots at vertices
            painter.setBrush(QBrush(QColor("#5DCAA5")))
            for pt in pts:
                painter.drawEllipse(pt, 4, 4)

        # Draw detection line (red)
        if len(self.line) >= 1:
            painter.setPen(QPen(QColor("#D85A30"), 3))
            pts = [QPoint(*self._image_to_canvas(*p)) for p in self.line]
            for pt in pts:
                painter.setBrush(QBrush(QColor("#D85A30")))
                painter.drawEllipse(pt, 5, 5)
            if len(pts) == 2:
                painter.drawLine(pts[0], pts[1])

        painter.end()

    def _image_to_canvas(self, px, py):
        return (
            int(px * self._scale_factor + self._x_off),
            int(py * self._scale_factor + self._y_off),
        )

    def _canvas_to_image(self, pos):
        x = int((pos.x() - self._x_off) / self._scale_factor) if self._scale_factor else 0
        y = int((pos.y() - self._y_off) / self._scale_factor) if self._scale_factor else 0
        return (x, y)

    def set_mode(self, mode: int):
        self.mode = mode
        self.update()

    def clear_current_mode(self):
        if self.mode == self.MODE_GCP:
            self.gcps.clear()
            self.gcp_changed.emit([])
        elif self.mode == self.MODE_ROI:
            self.roi.clear()
            self.roi_changed.emit([])
        elif self.mode == self.MODE_LINE:
            self.line.clear()
            self.line_changed.emit([])
        self.update()


# ================================================================== #
#  CalibrationScreen                                                   #
# ================================================================== #
class CalibrationScreen(QWidget):
    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.cm = CalibManager(ctrl.state.output_dir)
        self._worker = None
        self._world_inputs = []
        self.gcp_gps_coords = {}
        self.ref_lat = 6.711571
        self.ref_lon = 79.907470
        self._build_ui()
        self._load_existing_data()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Video selector bar ---
        video_bar = QFrame()
        video_bar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e8e8e8; border-radius: 0; padding: 4px;")
        video_layout = QHBoxLayout(video_bar)
        video_layout.setContentsMargins(16, 8, 16, 8)
        video_layout.setSpacing(12)

        video_layout.addWidget(QLabel("Input Video:"))
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Select video file...")
        if self.ctrl.state.video_path:
            self.video_input.setText(str(self.ctrl.state.video_path))
        video_layout.addWidget(self.video_input, stretch=1)

        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryBtn")
        browse_btn.clicked.connect(self._browse_video)
        video_layout.addWidget(browse_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #e8e8e8;")
        sep.setFixedHeight(20)
        video_layout.addWidget(sep)

        # Frame extraction number
        video_layout.addWidget(QLabel("Extract at Frame:"))
        self.frame_number_spin = QSpinBox()
        self.frame_number_spin.setRange(0, 999999)
        self.frame_number_spin.setValue(5000)
        self.frame_number_spin.setFixedWidth(80)
        self.frame_number_spin.setToolTip("Frame index to extract for calibration still image")
        video_layout.addWidget(self.frame_number_spin)

        root_layout.addWidget(video_bar)

        # --- Main body ---
        body = QWidget()
        main_layout = QHBoxLayout(body)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left panel ---
        left_panel = self._build_left_panel()
        main_layout.addWidget(left_panel)

        # --- Centre: canvas ---
        self.canvas = CalibCanvas()
        main_layout.addWidget(self.canvas, stretch=1)

        # --- Right panel ---
        right_panel = self._build_right_panel()
        main_layout.addWidget(right_panel)

        root_layout.addWidget(body)

        # Connect canvas signals
        self.canvas.gcp_changed.connect(self._on_gcp_changed)
        self.canvas.roi_changed.connect(self._on_roi_changed)
        self.canvas.line_changed.connect(self._on_line_changed)

    # ------------------------------------------------------------------ #
    #  Left panel                                                          #
    # ------------------------------------------------------------------ #
    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(200)
        panel.setStyleSheet("background: #ffffff; border-right: 1px solid #e8e8e8;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Calibration Steps")
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #333;")
        layout.addWidget(title)

        # Step list
        steps = [
            ("1", "Extract Frame", "Get a still frame from the video"),
            ("2", "Mark GCPs", "Click to place ground control points"),
            ("3", "Road Area", "Draw the ROI polygon"),
            ("4", "Detection Line", "Draw the counting line"),
            ("5", "Compute", "Calculate homography matrix"),
        ]
        for num, name, desc in steps:
            step_frame = QFrame()
            step_frame.setStyleSheet(
                "QFrame { background: #f8f9fa; border-radius: 6px; padding: 4px; margin: 2px 0; }"
                "QFrame:hover { background: #e8f0fb; }"
            )
            sl = QVBoxLayout(step_frame)
            sl.setContentsMargins(8, 4, 8, 4)
            sl.setSpacing(1)
            header = QLabel(f"⬤ {num}. {name}")
            header.setStyleSheet("font-size: 11px; font-weight: 600; color: #185FA5;")
            sl.addWidget(header)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("font-size: 9px; color: #888;")
            desc_lbl.setWordWrap(True)
            sl.addWidget(desc_lbl)
            layout.addWidget(step_frame)

        layout.addSpacing(8)

        # Mode radio buttons
        mode_label = QLabel("Drawing Mode")
        mode_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #555; margin-top: 4px;")
        layout.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        modes = [
            (CalibCanvas.MODE_GCP, "GCP Points"),
            (CalibCanvas.MODE_ROI, "Road Area"),
            (CalibCanvas.MODE_LINE, "Detection Line"),
        ]
        for mode_id, label in modes:
            rb = QRadioButton(label)
            rb.setStyleSheet("font-size: 11px; color: #444;")
            self.mode_group.addButton(rb, mode_id)
            layout.addWidget(rb)
            if mode_id == CalibCanvas.MODE_GCP:
                rb.setChecked(True)

        self.mode_group.idClicked.connect(self._on_mode_changed)

        tip = QLabel("Left-click to add\nRight-click to undo")
        tip.setStyleSheet("font-size: 9px; color: #aaa; margin-top: 8px;")
        layout.addWidget(tip)

        layout.addStretch()

        # Bottom buttons
        self.extract_btn = QPushButton("Extract Frame")
        self.extract_btn.setObjectName("PrimaryBtn")
        self.extract_btn.clicked.connect(self._extract_frame)
        layout.addWidget(self.extract_btn)

        self.reset_btn = QPushButton("Reset Mode")
        self.reset_btn.setObjectName("SecondaryBtn")
        self.reset_btn.clicked.connect(self._reset_mode)
        layout.addWidget(self.reset_btn)

        return panel

    # ------------------------------------------------------------------ #
    #  Right panel                                                         #
    # ------------------------------------------------------------------ #
    def _build_right_panel(self) -> QWidget:
        # Container widget for the entire right side
        container = QWidget()
        container.setFixedWidth(240)
        container.setObjectName("RightPanelContainer")
        container.setStyleSheet("#RightPanelContainer { border-left: 1px solid #e8e8e8; background-color: #ffffff; }")
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 1. Scrollable area for inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("RightPanelScroll")
        scroll.setStyleSheet("#RightPanelScroll { border: none; background: transparent; }")

        panel = QWidget()
        panel.setObjectName("RightPanelContent")
        panel.setStyleSheet("#RightPanelContent { background-color: #ffffff; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # GCP pixel coordinates table
        px_header = QLabel("GCP Pixel Coordinates")
        px_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #333;")
        layout.addWidget(px_header)

        self.gcp_table = QTableWidget(0, 3)
        self.gcp_table.setHorizontalHeaderLabels(["#", "Pixel X", "Pixel Y"])
        self.gcp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gcp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.gcp_table.verticalHeader().setVisible(False)
        self.gcp_table.setMinimumHeight(150)
        self.gcp_table.setMaximumHeight(150)
        self.gcp_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.gcp_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.gcp_table)

        # Real-world coordinates inputs
        world_header_layout = QHBoxLayout()
        world_header = QLabel("Real-World (metres)")
        world_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #333; margin-top: 8px;")
        world_header_layout.addWidget(world_header)
        world_header_layout.addStretch()

        self.gps_tool_btn = QPushButton("GPS Tool")
        self.gps_tool_btn.setStyleSheet(
            "QPushButton { font-size: 9px; padding: 2px 6px; background: #e8f0fb; color: #185FA5; border: 1px solid #185FA5; border-radius: 4px; margin-top: 8px; }"
            "QPushButton:hover { background: #d0e1f9; }"
        )
        self.gps_tool_btn.clicked.connect(self._open_gps_converter)
        world_header_layout.addWidget(self.gps_tool_btn)
        layout.addLayout(world_header_layout)

        self.world_form = QFormLayout()
        self.world_form.setSpacing(4)
        layout.addLayout(self.world_form)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 10px; color: #666;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()
        scroll.setWidget(panel)
        container_layout.addWidget(scroll, stretch=1)

        # 2. Fixed bottom panel for action buttons
        bottom_panel = QFrame()
        bottom_panel.setObjectName("RightPanelBottom")
        bottom_panel.setStyleSheet("#RightPanelBottom { background-color: #ffffff; border-top: 1px solid #e8e8e8; border-radius: 0; }")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(8)

        # Compute homography
        self.compute_btn = QPushButton("Compute Homography")
        self.compute_btn.setObjectName("PrimaryBtn")
        self.compute_btn.clicked.connect(self._compute_homography)
        bottom_layout.addWidget(self.compute_btn)

        # Save all
        self.save_btn = QPushButton("Save All Annotations")
        self.save_btn.setObjectName("PrimaryBtn")
        self.save_btn.clicked.connect(self._save_all)
        bottom_layout.addWidget(self.save_btn)

        # Error display
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("font-size: 10px; color: #3B8a22;")
        self.error_label.setWordWrap(True)
        bottom_layout.addWidget(self.error_label)

        container_layout.addWidget(bottom_panel)
        return container

    # ------------------------------------------------------------------ #
    #  Signal handlers                                                     #
    # ------------------------------------------------------------------ #
    def _on_mode_changed(self, mode_id: int):
        self.canvas.set_mode(mode_id)

    def _on_gcp_changed(self, gcps: list):
        self.gcp_table.setRowCount(len(gcps))
        # Resize world inputs to match
        while len(self._world_inputs) < len(gcps):
            idx = len(self._world_inputs)
            x_input = QLineEdit("0.0")
            y_input = QLineEdit("0.0")
            x_input.setPlaceholderText("X (m)")
            y_input.setPlaceholderText("Y (m)")
            row_layout = QHBoxLayout()
            row_layout.addWidget(x_input)
            row_layout.addWidget(y_input)
            self.world_form.addRow(f"GCP{idx+1}:", row_layout)
            self._world_inputs.append((x_input, y_input))

        # Remove excess
        while len(self._world_inputs) > len(gcps):
            x_input, y_input = self._world_inputs.pop()
            x_input.deleteLater()
            y_input.deleteLater()
            # Remove last row from form
            if self.world_form.rowCount() > 0:
                self.world_form.removeRow(self.world_form.rowCount() - 1)

        for i, (x, y) in enumerate(gcps):
            self.gcp_table.setItem(i, 0, QTableWidgetItem(f"GCP{i+1}"))
            self.gcp_table.setItem(i, 1, QTableWidgetItem(str(x)))
            self.gcp_table.setItem(i, 2, QTableWidgetItem(str(y)))

        self.status_label.setText(f"{len(gcps)} GCP(s) marked")

    def _on_roi_changed(self, roi: list):
        self.status_label.setText(f"ROI: {len(roi)} vertices")

    def _on_line_changed(self, line: list):
        self.status_label.setText(f"Detection line: {len(line)}/2 points")

    def _reset_mode(self):
        self.canvas.clear_current_mode()
        self.status_label.setText("Mode reset.")

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", str(self.ctrl.state.repo_root),
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        if path:
            self.video_input.setText(path)
            self.ctrl.set_video(Path(path))
            try:
                self.ctrl.save_config({"VIDEO_PATH": path})
            except Exception as e:
                print(f"[Warning] Failed to save video path to config: {e}")
            
            # Automatically extract frame after selecting input video file!
            self._extract_frame()

    # ------------------------------------------------------------------ #
    #  Extract frame                                                       #
    # ------------------------------------------------------------------ #
    def _extract_frame(self):
        video_path = self.video_input.text().strip()
        if not video_path or not Path(video_path).exists():
            QMessageBox.warning(self, "Missing Video", "Please select a valid video file first.")
            return

        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("Extracting…")
        # Pass the selected frame index to the worker!
        self._worker = CalibWorker(1, self.ctrl, frame_number=self.frame_number_spin.value())
        self._worker.finished_step.connect(self._on_extract_done)
        self._worker.error_step.connect(self._on_extract_error)
        self._worker.log.connect(lambda msg: self.status_label.setText(msg))
        self._worker.start()

    def _on_extract_done(self, step):
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("Extract Frame")
        self.ctrl.set_step_status(1, "done")
        # Load the extracted frame into the canvas
        frame_path = self.ctrl.state.output_dir / "still_frame.jpg"
        if frame_path.exists():
            self.ctrl.state.still_frame_path = frame_path
            self.canvas.load_frame(str(frame_path))
        self.status_label.setText("✓ Frame extracted successfully.")

    def _on_extract_error(self, step, msg):
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("Extract Frame")
        self.ctrl.set_step_status(1, "error")
        QMessageBox.warning(self, "Extract Frame Error", f"Failed to extract frame:\n{msg}")

    # ------------------------------------------------------------------ #
    #  Compute homography                                                  #
    # ------------------------------------------------------------------ #
    def _compute_homography(self):
        gcps_pixel = self.canvas.gcps
        if len(gcps_pixel) < 4:
            QMessageBox.warning(self, "Insufficient GCPs",
                                f"Need at least 4 GCPs, have {len(gcps_pixel)}.")
            return

        # Collect world coordinates and validate
        gcps_world = []
        for i, (x_input, y_input) in enumerate(self._world_inputs):
            if i >= len(gcps_pixel):
                break
            try:
                wx = float(x_input.text().strip())
                wy = float(y_input.text().strip())
                gcps_world.append((wx, wy))
            except ValueError:
                QMessageBox.warning(self, "Invalid Coordinates",
                                    f"GCP{i+1} has invalid or empty world coordinates. Please enter numerical values.")
                return

        if len(gcps_world) < 4:
            QMessageBox.warning(self, "Insufficient World Coords",
                                "Fill in at least 4 world coordinate pairs.")
            return

        try:
            H, mean_error = self.cm.compute_homography(gcps_pixel, gcps_world)
            self.ctrl.state.homography_matrix = H
            self.ctrl.state.homography_error = mean_error
            self.ctrl.set_step_status(3, "done")
            self.error_label.setText(f"✓ Homography computed.\nMean error: {mean_error:.4f} m")
            self.error_label.setStyleSheet("font-size: 10px; color: #3B8a22;")
            
            # Auto-save all files to disk since it succeeded
            self._save_all_silent(gcps_world)
        except Exception as e:
            self.error_label.setText(f"✗ Error: {e}")
            self.error_label.setStyleSheet("font-size: 10px; color: #cc3333;")
            self.ctrl.set_step_status(3, "error")

    # ------------------------------------------------------------------ #
    #  Save all                                                            #
    # ------------------------------------------------------------------ #
    def _save_all(self):
        """Save all calibration annotations to JSON files."""
        # Validate world coordinates first
        gcps_world = []
        for i, (x_input, y_input) in enumerate(self._world_inputs):
            if i >= len(self.canvas.gcps):
                break
            try:
                wx = float(x_input.text().strip())
                wy = float(y_input.text().strip())
                gcps_world.append((wx, wy))
            except ValueError:
                QMessageBox.warning(self, "Invalid Coordinates",
                                    f"GCP{i+1} has invalid or empty world coordinates. Please enter numerical values.")
                return

        self._save_all_silent(gcps_world)
        QMessageBox.information(self, "Saved", "All calibration data saved successfully.")

    def _save_all_silent(self, gcps_world=None):
        try:
            # Save pixel GCPs
            if self.canvas.gcps:
                self.cm.save_gcps_pixel(self.canvas.gcps)
                self.ctrl.state.gcps_pixel = list(self.canvas.gcps)
                self.ctrl.set_step_status(2, "done")

            # Collect world coordinates if not passed
            if gcps_world is None:
                gcps_world = []
                for i, (x_input, y_input) in enumerate(self._world_inputs):
                    if i >= len(self.canvas.gcps):
                        break
                    try:
                        gcps_world.append((float(x_input.text().strip()), float(y_input.text().strip())))
                    except ValueError:
                        pass

            # Save world GCPs
            if gcps_world:
                self.cm.save_gcps_world(gcps_world)
                self.ctrl.state.gcps_world = gcps_world

            # Save ROI
            if self.canvas.roi:
                self.cm.save_road_area(self.canvas.roi)
                self.ctrl.state.road_area = list(self.canvas.roi)

            # Save detection line
            if len(self.canvas.line) == 2:
                self.cm.save_detection_line(self.canvas.line)
                self.ctrl.state.detection_line = list(self.canvas.line)

            # Save GPS Location.csv (user request)
            gps_csv_path = self.ctrl.state.repo_root / "data" / "GPS Location.csv"
            gps_csv_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                import csv
                with open(gps_csv_path, mode="w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Name", "Latitude", "Longitude", "X (m)", "Y (m)"])
                    writer.writerow(["Refrence_point", str(self.ref_lat), str(self.ref_lon), "0.0", "0.0"])
                    
                    for i in range(len(self.canvas.gcps)):
                        lat, lon = self.gcp_gps_coords.get(i, (None, None))
                        x_m = ""
                        y_m = ""
                        if i < len(self._world_inputs):
                            x_m = self._world_inputs[i][0].text().strip()
                            y_m = self._world_inputs[i][1].text().strip()
                            
                        # Fallback to template if lat/lon is empty
                        if lat is None or lon is None:
                            templates = {
                                0: (6.711711854987715, 79.9075807911768),
                                1: (6.711715851385014, 79.9075224435446),
                                2: (6.712122079175364, 79.9075311728432),
                                3: (6.712119415350414, 79.9075915225468),
                            }
                            lat, lon = templates.get(i, ("", ""))
                            
                        writer.writerow([f"GCP{i+1}", str(lat), str(lon), str(x_m), str(y_m)])
            except Exception as csv_err:
                print(f"[Warning] Failed to save GPS Location.csv: {csv_err}")

            self.status_label.setText("✓ All annotations & GPS data saved.")
        except Exception as e:
            print(f"[Warning] Silent save failed: {e}")

    # ------------------------------------------------------------------ #
    #  Load existing data                                                  #
    # ------------------------------------------------------------------ #
    def _load_existing_data(self):
        """Load existing calibration data if available."""
        # Load frame
        frame_path = self.ctrl.state.output_dir / "still_frame.jpg"
        if frame_path.exists():
            self.canvas.load_frame(str(frame_path))

        # Load GPS Location.csv if it exists
        gps_csv_path = self.ctrl.state.repo_root / "data" / "GPS Location.csv"
        if gps_csv_path.exists():
            try:
                import csv
                with open(gps_csv_path, mode="r") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    for row in reader:
                        if not row or len(row) < 3:
                            continue
                        name = row[0].strip()
                        try:
                            lat = float(row[1])
                            lon = float(row[2])
                            if name.lower() in ("refrence_point", "reference_point"):
                                self.ref_lat = lat
                                self.ref_lon = lon
                            elif name.lower().startswith("gcp"):
                                idx = int(name[3:]) - 1
                                self.gcp_gps_coords[idx] = (lat, lon)
                        except (ValueError, IndexError):
                            pass
            except Exception as e:
                print(f"[Warning] Failed to load GPS Location.csv: {e}")

        # Load GCPs
        gcps_pixel = self.cm.load_gcps_pixel()
        gcps_world = self.cm.load_gcps_world()
        if gcps_pixel:
            self.canvas.gcps = gcps_pixel
            self._on_gcp_changed(gcps_pixel)
            # Fill world coords
            for i, (wx, wy) in enumerate(gcps_world):
                if i < len(self._world_inputs):
                    self._world_inputs[i][0].setText(str(wx))
                    self._world_inputs[i][1].setText(str(wy))

        # Load ROI
        roi = self.cm.load_road_area()
        if roi:
            self.canvas.roi = roi

        # Load detection line
        line = self.cm.load_detection_line()
        if line:
            self.canvas.line = line

        self.canvas.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self.ctrl.state.video_path:
            self.video_input.setText(str(self.ctrl.state.video_path))
        else:
            self.video_input.setText("")

    def _open_gps_converter(self):
        # Ensure at least one GCP is marked
        gcps = self.canvas.gcps
        if not gcps:
            QMessageBox.warning(self, "No GCPs", "Please mark at least one GCP point on the image first.")
            return
            
        dialog = GPSConverterDialog(len(gcps), self)
        dialog.exec()

    def apply_gps_coordinates(self, gcp_idx: int, x_m: float, y_m: float, lat: float, lon: float):
        if gcp_idx >= len(self._world_inputs):
            QMessageBox.warning(
                self, 
                "GCP Not Placed", 
                f"Please mark GCP {gcp_idx+1} on the still frame (by clicking on it in GCP mode) before applying its GPS coordinates."
            )
            return
            
        self.gcp_gps_coords[gcp_idx] = (lat, lon)
        x_input, y_input = self._world_inputs[gcp_idx]
        x_input.setText(f"{x_m:.3f}")
        y_input.setText(f"{y_m:.3f}")
        self.status_label.setText(f"✓ GCP{gcp_idx+1} coordinates updated using GPS Tool.")


class GPSConverterDialog(QDialog):
    def __init__(self, gcps_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPS to Real-World Meter Converter")
        self.resize(380, 360)
        
        # Default reference values from parent
        self.ref_lat = getattr(parent, "ref_lat", 6.711571)
        self.ref_lon = getattr(parent, "ref_lon", 79.907470)
        
        self._build_ui(gcps_count)
        
    def _build_ui(self, gcps_count):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Group 1: Reference Point
        ref_frame = QFrame()
        ref_frame.setFrameShape(QFrame.Shape.StyledPanel)
        ref_frame.setStyleSheet("background: #fdfdfd; border: 1px solid #e8e8e8; border-radius: 6px; padding: 6px;")
        ref_layout = QFormLayout(ref_frame)
        ref_title = QLabel("Reference Point (Origin)")
        ref_title.setStyleSheet("font-weight: 700; color: #333; font-size: 11px;")
        ref_layout.addRow(ref_title)
        
        self.ref_lat_input = QLineEdit(str(self.ref_lat))
        self.ref_lon_input = QLineEdit(str(self.ref_lon))
        ref_layout.addRow("Ref Latitude:", self.ref_lat_input)
        ref_layout.addRow("Ref Longitude:", self.ref_lon_input)
        layout.addWidget(ref_frame)
        
        # Group 2: Target Geological Coordinates
        target_frame = QFrame()
        target_frame.setFrameShape(QFrame.Shape.StyledPanel)
        target_frame.setStyleSheet("background: #fdfdfd; border: 1px solid #e8e8e8; border-radius: 6px; padding: 6px;")
        target_layout = QFormLayout(target_frame)
        target_title = QLabel("Target GPS Coordinates")
        target_title.setStyleSheet("font-weight: 700; color: #333; font-size: 11px;")
        target_layout.addRow(target_title)
        
        # Target Selector row
        target_sel_layout = QHBoxLayout()
        self.gcp_combo = QComboBox()
        for i in range(gcps_count):
            self.gcp_combo.addItem(f"GCP {i+1}", i)
        target_sel_layout.addWidget(self.gcp_combo)
        
        self.load_tpl_btn = QPushButton("Load Template")
        self.load_tpl_btn.setStyleSheet("font-size: 10px; padding: 2px 8px; background: #e8f0fb; color: #185FA5; border: 1px solid #185FA5;")
        self.load_tpl_btn.clicked.connect(self._load_gcp_template)
        target_sel_layout.addWidget(self.load_tpl_btn)
        
        target_layout.addRow("Apply To:", target_sel_layout)
        
        self.target_lat_input = QLineEdit()
        self.target_lat_input.setPlaceholderText("e.g. 6.711712")
        self.target_lon_input = QLineEdit()
        self.target_lon_input.setPlaceholderText("e.g. 79.907581")
        
        target_layout.addRow("Target Latitude:", self.target_lat_input)
        target_layout.addRow("Target Longitude:", self.target_lon_input)
        layout.addWidget(target_frame)
        
        # Group 3: Real-World Results
        result_frame = QFrame()
        result_frame.setFrameShape(QFrame.Shape.StyledPanel)
        result_frame.setStyleSheet("background: #fdfdfd; border: 1px solid #e8e8e8; border-radius: 6px; padding: 6px;")
        result_layout = QFormLayout(result_frame)
        result_title = QLabel("Calculated Real-World Meters")
        result_title.setStyleSheet("font-weight: 700; color: #333; font-size: 11px;")
        result_layout.addRow(result_title)
        
        self.x_result_lbl = QLabel("0.000 m")
        self.y_result_lbl = QLabel("0.000 m")
        self.dist_result_lbl = QLabel("0.000 m")
        
        # Style them
        for lbl in (self.x_result_lbl, self.y_result_lbl, self.dist_result_lbl):
            lbl.setStyleSheet("font-weight: bold; color: #185FA5; font-size: 11px;")
            
        result_layout.addRow("X (meters East):", self.x_result_lbl)
        result_layout.addRow("Y (meters North):", self.y_result_lbl)
        result_layout.addRow("Total Distance:", self.dist_result_lbl)
        layout.addWidget(result_frame)
        
        # Connect text change signals for live updates
        self.ref_lat_input.textChanged.connect(self._recalculate)
        self.ref_lon_input.textChanged.connect(self._recalculate)
        self.target_lat_input.textChanged.connect(self._recalculate)
        self.target_lon_input.textChanged.connect(self._recalculate)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply to GCP")
        self.apply_btn.setObjectName("PrimaryBtn")
        self.apply_btn.clicked.connect(self._apply_to_gcp)
        btn_layout.addWidget(self.apply_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("SecondaryBtn")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        # Trigger initial template state
        self._on_gcp_combo_changed(0)
        self.gcp_combo.currentIndexChanged.connect(self._on_gcp_combo_changed)

    def _on_gcp_combo_changed(self, index: int):
        self.load_tpl_btn.setEnabled(index in [0, 1, 2, 3])
        
    def _load_gcp_template(self):
        idx = self.gcp_combo.currentIndex()
        templates = {
            0: (6.711711854987715, 79.9075807911768),
            1: (6.711715851385014, 79.9075224435446),
            2: (6.712122079175364, 79.9075311728432),
            3: (6.712119415350414, 79.9075915225468),
        }
        if idx in templates:
            lat, lon = templates[idx]
            self.target_lat_input.setText(f"{lat:.15f}")
            self.target_lon_input.setText(f"{lon:.15f}")

    def _apply_to_gcp(self):
        try:
            ref_lat = float(self.ref_lat_input.text())
            ref_lon = float(self.ref_lon_input.text())
            
            target_lat_str = self.target_lat_input.text().strip()
            target_lon_str = self.target_lon_input.text().strip()
            
            if not target_lat_str or not target_lon_str:
                QMessageBox.warning(self, "Missing Coordinates", "Please enter Latitude and Longitude coordinates first.")
                return
                
            target_lat = float(target_lat_str)
            target_lon = float(target_lon_str)
            
            # X (meters) = (Longitude - Ref_Longitude) * 110559.35
            # Y (meters) = (Latitude - Ref_Latitude) * 111135.93
            x_m = (target_lon - ref_lon) * 110559.35
            y_m = (target_lat - ref_lat) * 111135.93
            
            gcp_idx = self.gcp_combo.currentIndex()
            if self.parent():
                self.parent().ref_lat = ref_lat
                self.parent().ref_lon = ref_lon
                self.parent().apply_gps_coordinates(gcp_idx, x_m, y_m, target_lat, target_lon)
        except ValueError:
            QMessageBox.warning(self, "Invalid Inputs", "Please enter valid numerical coordinate values.")
        
    def _recalculate(self):
        try:
            ref_lat = float(self.ref_lat_input.text())
            ref_lon = float(self.ref_lon_input.text())
            
            target_lat_str = self.target_lat_input.text().strip()
            target_lon_str = self.target_lon_input.text().strip()
            
            if not target_lat_str or not target_lon_str:
                self.x_result_lbl.setText("0.000 m")
                self.y_result_lbl.setText("0.000 m")
                self.dist_result_lbl.setText("0.000 m")
                return
                
            target_lat = float(target_lat_str)
            target_lon = float(target_lon_str)
            
            # Conversion matches user data:
            # X (meters) = (Longitude - Ref_Longitude) * 110559.35
            # Y (meters) = (Latitude - Ref_Latitude) * 111135.93
            x_m = (target_lon - ref_lon) * 110559.35
            y_m = (target_lat - ref_lat) * 111135.93
            dist = (x_m**2 + y_m**2)**0.5
            
            self.x_result_lbl.setText(f"{x_m:.3f} m")
            self.y_result_lbl.setText(f"{y_m:.3f} m")
            self.dist_result_lbl.setText(f"{dist:.3f} m")
        except ValueError:
            self.x_result_lbl.setText("Invalid input")
            self.y_result_lbl.setText("Invalid input")
            self.dist_result_lbl.setText("Invalid input")
            
    def get_calculated_values(self):
        try:
            ref_lat = float(self.ref_lat_input.text())
            ref_lon = float(self.ref_lon_input.text())
            target_lat = float(self.target_lat_input.text())
            target_lon = float(self.target_lon_input.text())
            
            x_m = (target_lon - ref_lon) * 110559.35
            y_m = (target_lat - ref_lat) * 111135.93
            
            gcp_idx = self.gcp_combo.currentIndex()
            return gcp_idx, x_m, y_m
        except Exception:
            return None
