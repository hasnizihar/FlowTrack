# AI Agent Build Instructions
## YOLOv9 Traffic Analysis Pipeline — Python Desktop GUI Application

---

## MISSION

Convert the existing command-line pipeline at
`https://github.com/hasnizihar/YOLOv9-Traffic-Analysis-Pipeline`
into a **fully self-contained PyQt6 desktop application** that wraps every script
in a modern GUI. The original scripts must remain runnable standalone; the GUI
calls them as modules, it does not rewrite them. The finished app must be
packageable with PyInstaller into a single executable.

---

## GROUND RULES FOR THE AGENT

1. Read every existing script in `scripts/` before writing any GUI code.
   Understand exactly what parameters each script uses, what files it reads,
   and what files it writes.
2. Never rewrite the core algorithm code. Only import and call it.
3. The GUI runs on the main Qt thread. All heavy work (detection, tracking,
   speed estimation) runs on QThread workers. Violating this will freeze the UI.
4. Write every file from scratch — do not patch existing scripts.
5. After creating each file, verify it imports cleanly with
   `python -m py_compile <file>` before moving to the next.
6. Commit (or checkpoint) after each major section below.

---

## SECTION 0 — ENVIRONMENT SETUP

### 0.1 Clone the original repository

```
git clone https://github.com/hasnizihar/YOLOv9-Traffic-Analysis-Pipeline.git
cd YOLOv9-Traffic-Analysis-Pipeline
```

### 0.2 Create a virtual environment

```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 0.3 Install all dependencies

Run this exact command (order matters):

```
pip install -r requirements.txt
pip install PyQt6 PyQt6-Qt6 PyQt6-sip
pip install matplotlib
pip install pyinstaller
```

Verify the install:

```python
import PyQt6.QtWidgets
import cv2
import ultralytics
import matplotlib
print("All imports OK")
```

### 0.4 Download model weights

Place `yolov9t.pt` inside the `models/` directory.
Download from: https://docs.ultralytics.com/models/yolov9/
If the directory does not exist, create it: `mkdir -p models`

### 0.5 Place a test video

Put any MP4 traffic video at `Raw video/traffic_video.mp4`.
Create the directory if needed: `mkdir -p "Raw video"`

---

## SECTION 1 — DIRECTORY STRUCTURE TO CREATE

Create the following new directories and files alongside the existing repo.
Do not move or rename any existing files.

```
traffic_analysis_gui/          ← new top-level package
    __init__.py
    main.py                    ← application entry point

    gui/
        __init__.py
        main_window.py         ← QMainWindow with sidebar + stacked screens
        screen_dashboard.py    ← live KPI cards + pipeline status row
        screen_calibration.py  ← interactive canvas + GCP editor
        screen_analysis.py     ← pipeline runner + progress + log
        screen_results.py      ← chart viewer + data tables + file list
        screen_settings.py     ← config editor

    controllers/
        __init__.py
        app_controller.py      ← global state, project file load/save
        calib_manager.py       ← GCP / ROI / homography logic
        pipeline_runner.py     ← QThread orchestrator for steps 5-8
        results_manager.py     ← reads CSVs and PNGs from output/

    workers/
        __init__.py
        step5_worker.py        ← QThread wrapper: step5_detect_track.py
        step6_worker.py        ← QThread wrapper: step6_speed.py
        step7_worker.py        ← QThread wrapper: step7_traffic_params.py
        step8_worker.py        ← QThread wrapper: step8_plots.py
        calib_worker.py        ← QThread wrapper: steps 1-4

    assets/
        icons/                 ← any PNG icons needed
        style.qss              ← Qt stylesheet
```

---

## SECTION 2 — STYLESHEET (assets/style.qss)

Create `traffic_analysis_gui/assets/style.qss` with these exact rules.
This stylesheet is loaded once at startup and applies globally.

```qss
/* Global */
QWidget {
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #1a1a1a;
    background-color: #f5f5f5;
}

/* Main window background */
QMainWindow, QDialog {
    background-color: #f5f5f5;
}

/* Sidebar */
#Sidebar {
    background-color: #1e2329;
    border-right: 1px solid #2e3640;
    min-width: 54px;
    max-width: 54px;
}

#SidebarButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 6px;
    color: #8a9bb0;
    font-size: 20px;
    text-align: center;
}
#SidebarButton:hover  { background: #2e3640; color: #c8d6e5; }
#SidebarButton:checked { background: #163a5f; color: #4a9eff; }

/* Topbar */
#Topbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    min-height: 44px;
    max-height: 44px;
}

/* Content area */
#ContentStack {
    background-color: #f5f5f5;
}

/* Cards */
QFrame#Card {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 12px;
}

/* Primary button */
QPushButton#PrimaryBtn {
    background-color: #185FA5;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton#PrimaryBtn:hover   { background-color: #1a70bf; }
QPushButton#PrimaryBtn:pressed { background-color: #134e8a; }
QPushButton#PrimaryBtn:disabled { background-color: #9ab8d6; }

/* Secondary button */
QPushButton#SecondaryBtn {
    background-color: transparent;
    color: #555;
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 6px 16px;
}
QPushButton#SecondaryBtn:hover   { background-color: #f0f0f0; }
QPushButton#SecondaryBtn:pressed { background-color: #e0e0e0; }

/* Log panel */
QTextEdit#LogPanel {
    background: #1a1d21;
    color: #a8b4c0;
    border: none;
    border-radius: 0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
}

/* Progress bar */
QProgressBar {
    border: none;
    border-radius: 3px;
    background: #e8e8e8;
    height: 5px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 3px;
    background: #185FA5;
}
QProgressBar#SuccessBar::chunk { background: #3B8a22; }

/* Tab bar */
QTabBar::tab {
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: #777;
    font-size: 12px;
}
QTabBar::tab:selected {
    border-bottom: 2px solid #185FA5;
    color: #185FA5;
    font-weight: 600;
}
QTabBar::tab:hover { color: #185FA5; }
QTabWidget::pane { border: none; }

/* Table */
QTableWidget {
    gridline-color: #f0f0f0;
    border: none;
    selection-background-color: #e8f0fb;
}
QHeaderView::section {
    background: #fafafa;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
    color: #666;
}

/* Input fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 5px 9px;
    background: white;
    font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #185FA5;
}

/* Scrollbar */
QScrollBar:vertical {
    width: 6px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #ccc;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
```

---

## SECTION 3 — ENTRY POINT (traffic_analysis_gui/main.py)

```python
"""
main.py — Application entry point.
Run with: python -m traffic_analysis_gui.main
or after packaging: ./TrafficAnalysis (or TrafficAnalysis.exe)
"""

import sys
import os
from pathlib import Path

# Add the repo root to sys.path so the existing scripts/ package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from traffic_analysis_gui.gui.main_window import MainWindow


def main():
    # Enable high-DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Traffic Analysis")
    app.setOrganizationName("YOLOv9Pipeline")
    app.setApplicationDisplayName("YOLOv9 Traffic Analysis")

    # Load stylesheet
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text())

    # Default font
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    window = MainWindow()
    window.setWindowTitle("YOLOv9 Traffic Analysis Pipeline")
    window.resize(1280, 760)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

---

## SECTION 4 — MAIN WINDOW (gui/main_window.py)

The main window is a `QMainWindow`. Its central widget is a horizontal `QHBoxLayout`
containing:
- A narrow sidebar (`QWidget`, objectName `"Sidebar"`, fixed width 54 px)
- A `QStackedWidget` for all five screens

### 4.1 Sidebar

The sidebar contains a vertical column of `QPushButton` widgets with
`setCheckable(True)`. Use icons from Qt's built-in `QStyle.StandardPixmap`
where possible, or text Unicode symbols as a fallback.

Button order (top to bottom):
1. Logo label (non-clickable, traffic cone icon or "TA" text)
2. Dashboard button — icon: grid/home
3. Calibration button — icon: crosshair/target
4. Analysis button — icon: play triangle
5. Results button — icon: bar chart
6. Spacer (QSpacerItem, expanding)
7. Settings button — icon: gear

When a button is clicked, call `stack.setCurrentIndex(N)` and uncheck all
other sidebar buttons.

### 4.2 Topbar

A `QWidget` (objectName `"Topbar"`) with a horizontal layout containing:
- A `QLabel` for the current screen title (bold, 14px)
- A thin vertical separator line
- A `QLabel` for the current project subtitle (muted, 12px)
- Expanding spacer
- A small `QLabel` chip showing model status ("● Model loaded", green)
- A small `QLabel` chip showing the current model filename ("yolov9t.pt")

The topbar title and subtitle update when screens change.

### 4.3 Screen registration

Import and instantiate all five screen classes. Pass the single
`AppController` instance to each screen's constructor so they share state.

```python
from traffic_analysis_gui.controllers.app_controller import AppController
from traffic_analysis_gui.gui.screen_dashboard   import DashboardScreen
from traffic_analysis_gui.gui.screen_calibration import CalibrationScreen
from traffic_analysis_gui.gui.screen_analysis    import AnalysisScreen
from traffic_analysis_gui.gui.screen_results     import ResultsScreen
from traffic_analysis_gui.gui.screen_settings    import SettingsScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctrl = AppController()
        self._build_layout()
        self._connect_signals()

    def _build_layout(self):
        # Build sidebar, topbar, stacked screens as described above
        ...

    def switch_screen(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = ["Dashboard", "Calibration", "Analysis", "Results", "Settings"]
        self.topbar_title.setText(titles[index])
        # Uncheck all sidebar buttons, check the active one
        ...
```

---

## SECTION 5 — APP CONTROLLER (controllers/app_controller.py)

The `AppController` is a plain Python class (not a QObject). It holds the
global mutable state of the application. All screens receive a reference to
the same instance.

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

@dataclass
class ProjectState:
    # Paths (all resolved relative to REPO_ROOT)
    repo_root:       Path = Path(".")
    video_path:      Optional[Path] = None
    output_dir:      Path = Path("output")
    models_dir:      Path = Path("models")
    still_frame_path:Optional[Path] = None

    # Calibration
    gcps_pixel:  List[Tuple[int,int]] = field(default_factory=list)
    gcps_world:  List[Tuple[float,float]] = field(default_factory=list)
    road_area:   List[Tuple[int,int]] = field(default_factory=list)
    detection_line: List[Tuple[int,int]] = field(default_factory=list)
    homography_matrix: Optional[object] = None   # np.ndarray when computed
    homography_error:  Optional[float] = None

    # Pipeline progress
    step_status: Dict[int, str] = field(default_factory=lambda: {
        1: "idle", 2: "idle", 3: "idle", 4: "idle",
        5: "idle", 6: "idle", 7: "idle", 8: "idle",
    })  # status values: "idle", "running", "done", "error"
    step_progress: Dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(1, 9)})

    # Results (populated after pipeline finishes)
    results_loaded: bool = False


class AppController:
    def __init__(self):
        self.state = ProjectState()
        self._load_defaults()

    def _load_defaults(self):
        """Resolve paths relative to the repo root."""
        import sys
        self.state.repo_root = Path(sys.path[0])
        self.state.output_dir = self.state.repo_root / "output"
        self.state.models_dir = self.state.repo_root / "models"
        self.state.output_dir.mkdir(exist_ok=True)

    def set_video(self, path: Path):
        self.state.video_path = path

    def set_step_status(self, step: int, status: str):
        self.state.step_status[step] = status

    def set_step_progress(self, step: int, fraction: float):
        self.state.step_progress[step] = fraction

    def get_config(self) -> dict:
        """
        Read scripts/config.py and return a dict of name → value.
        Parse each top-level assignment with ast.literal_eval for safety.
        """
        import ast
        cfg = {}
        config_path = self.state.repo_root / "scripts" / "config.py"
        if not config_path.exists():
            return cfg
        for line in config_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                name, _, val = line.partition("=")
                try:
                    cfg[name.strip()] = ast.literal_eval(val.strip())
                except Exception:
                    cfg[name.strip()] = val.strip()
        return cfg

    def save_config(self, updates: dict):
        """
        Write updated values back to scripts/config.py.
        Only update lines whose key is in `updates`; leave all others intact.
        """
        config_path = self.state.repo_root / "scripts" / "config.py"
        if not config_path.exists():
            return
        lines = config_path.read_text().splitlines()
        result = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=")[0].strip()
                if name in updates:
                    result.append(f"{name} = {repr(updates[name])}")
                    continue
            result.append(line)
        config_path.write_text("\n".join(result))
```

---

## SECTION 6 — DASHBOARD SCREEN (gui/screen_dashboard.py)

This screen is a `QWidget` with a `QVBoxLayout`. It is read-only;
it only displays state from `AppController`.

### 6.1 Pipeline status row

A horizontal row of 8 equal-width `QFrame` cards (one per step).
Each card shows:
- Step number in muted 10px text at the top
- Step name in 12px bold
- A coloured dot + status label:
  - Gray dot + "Idle"    → step_status == "idle"
  - Amber dot + "Running…" → step_status == "running"  (animate dot opacity)
  - Green dot + "Done"   → step_status == "done"
  - Red dot   + "Error"  → step_status == "error"

Step names:
1. Extract frame, 2. Mark GCPs, 3. Homography, 4. Annotate,
5. Detect & track, 6. Speed est., 7. Traffic params, 8. Plots

### 6.2 KPI cards row

Four `QFrame` cards in a `QHBoxLayout`:
- **Vehicles detected** — reads `vehicle_counts.csv` row count if it exists, else "--"
- **Avg speed (km/h)** — reads mean of `vehicle_speeds.csv` "speed_kmh" column if exists
- **Flow rate (veh/hr)** — reads first value of `flow_1min.csv` if exists
- **Progress** — shows `step_progress[5]` as a percentage + QProgressBar

### 6.3 Live composition preview

Below the KPIs, show two side-by-side `QFrame` cards:
- Left: a matplotlib `FigureCanvasQTAgg` donut chart from `composition.csv`
  (if the file exists). If it does not exist, show "— Run pipeline to see results —"
- Right: a small `QTableWidget` (2 cols: Vehicle type, Mean speed)
  populated from `speed_stats.csv` if it exists.

### 6.4 Refresh logic

Add a `refresh()` method that re-reads all CSV files and updates widgets.
Call `refresh()`:
- When the screen becomes visible (override `showEvent`)
- When `AppController` emits any step-completed notification

---

## SECTION 7 — CALIBRATION SCREEN (gui/screen_calibration.py)

This is the most complex screen. It has a three-column layout:
- Left panel (200 px fixed): step list + mode selector
- Centre: interactive image canvas
- Right panel (200 px fixed): GCP coordinate editor

### 7.1 Left panel — step list

A `QListWidget` or hand-drawn `QVBoxLayout` of step items.
Each item shows a circle badge (✓ done, number if pending) + step name + description.
Clicking a completed step re-opens it.
The active step is highlighted blue.

Mode radio buttons below the list (three `QRadioButton`):
- [1] GCP points
- [2] Road area
- [3] Detection line

A small tip label: "Left-click to add · Right-click to undo · Enter to confirm"

### 7.2 Centre — CalibCanvas widget

Create a custom `QWidget` subclass called `CalibCanvas`.

```python
class CalibCanvas(QWidget):
    """
    Displays a QPixmap (the still frame) and lets the user click
    to place GCPs, draw a road-area polygon, or draw a detection line.
    Emits signals whenever points change so the right panel can update.
    """
    gcp_changed   = pyqtSignal(list)   # list of (x, y) pixel tuples
    roi_changed   = pyqtSignal(list)
    line_changed  = pyqtSignal(list)   # exactly 2 points

    MODE_GCP  = 1
    MODE_ROI  = 2
    MODE_LINE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap      = None      # QPixmap of the still frame
        self.mode        = self.MODE_GCP
        self.gcps        = []        # [(px, py), ...]
        self.roi         = []
        self.line        = []
        self.scale       = 1.0       # zoom factor
        self.offset      = (0, 0)    # pan offset
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def load_frame(self, image_path: str):
        """Load the still frame JPEG into self.pixmap."""
        self.pixmap = QPixmap(image_path)
        self.scale  = 1.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._canvas_to_image(event.pos())
            if self.mode == self.MODE_GCP:
                self.gcps.append(pt)
                self.gcp_changed.emit(self.gcps)
            elif self.mode == self.MODE_ROI:
                self.roi.append(pt)
                self.roi_changed.emit(self.roi)
            elif self.mode == self.MODE_LINE:
                if len(self.line) < 2:
                    self.line.append(pt)
                    self.line_changed.emit(self.line)
        elif event.button() == Qt.MouseButton.RightButton:
            if self.mode == self.MODE_GCP  and self.gcps:  self.gcps.pop()
            elif self.mode == self.MODE_ROI  and self.roi:  self.roi.pop()
            elif self.mode == self.MODE_LINE and self.line: self.line.pop()
            self.update()
        self.update()

    def paintEvent(self, event):
        if not self.pixmap:
            return
        painter = QPainter(self)
        # Draw the scaled pixmap centred in the widget
        scaled = self.pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_off = (self.width()  - scaled.width())  // 2
        y_off = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x_off, y_off, scaled)
        self._scale_factor = scaled.width() / self.pixmap.width()
        self._x_off = x_off
        self._y_off = y_off

        # Draw GCP dots (blue circles with labels)
        painter.setPen(QPen(QColor("#185FA5"), 2))
        painter.setBrush(QBrush(QColor(24, 95, 165, 180)))
        for i, (px, py) in enumerate(self.gcps):
            cx, cy = self._image_to_canvas(px, py)
            painter.drawEllipse(cx - 5, cy - 5, 10, 10)
            painter.setPen(QPen(QColor("#B5D4F4")))
            painter.drawText(cx + 7, cy - 3, f"GCP{i+1}")
            painter.setPen(QPen(QColor("#185FA5"), 2))

        # Draw ROI polygon (green dashed)
        if self.roi:
            painter.setPen(QPen(QColor("#5DCAA5"), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(93, 202, 165, 30)))
            pts = [QPoint(*self._image_to_canvas(px, py)) for px, py in self.roi]
            painter.drawPolygon(*pts)

        # Draw detection line (red)
        if len(self.line) == 2:
            painter.setPen(QPen(QColor("#D85A30"), 2))
            p1 = QPoint(*self._image_to_canvas(*self.line[0]))
            p2 = QPoint(*self._image_to_canvas(*self.line[1]))
            painter.drawLine(p1, p2)

        painter.end()

    def _image_to_canvas(self, px, py):
        return (
            int(px * self._scale_factor + self._x_off),
            int(py * self._scale_factor + self._y_off),
        )

    def _canvas_to_image(self, pos):
        if not hasattr(self, "_scale_factor"):
            return (0, 0)
        return (
            int((pos.x() - self._x_off) / self._scale_factor),
            int((pos.y() - self._y_off) / self._scale_factor),
        )

    def set_mode(self, mode: int):
        self.mode = mode
        self.update()

    def clear_current_mode(self):
        if self.mode == self.MODE_GCP:   self.gcps.clear()
        elif self.mode == self.MODE_ROI:  self.roi.clear()
        elif self.mode == self.MODE_LINE: self.line.clear()
        self.update()
```

### 7.3 Right panel — GCP coordinate editor

A `QScrollArea` containing:
- A `QLabel` section header "GCP pixel coordinates"
- A read-only `QTableWidget` (3 cols: #, Pixel X, Pixel Y) auto-populated
  from `CalibCanvas.gcp_changed` signal.
- A `QLabel` section header "Real-world (m)"
- For each GCP row, two `QLineEdit` widgets (X metres, Y metres)
  in a 2-column `QFormLayout`.
- A "Compute homography" `QPushButton` (primary)

### 7.4 Step execution buttons

In the bottom toolbar of the calibration screen:
- "Extract frame" runs `calib_worker.py` Step 1, loads the resulting JPEG
  into `CalibCanvas`.
- "Save & next →" saves current annotations to JSON files and marks the
  step done.
- "Reset" calls `CalibCanvas.clear_current_mode()`.

### 7.5 Homography computation

When "Compute homography" is clicked:
1. Validate that at least 4 GCPs have pixel AND world coordinates.
2. Run `scripts/step3_homography.py` logic in a `QThread` (use `calib_worker.py`).
3. On completion, show the reprojection error in the right panel and update
   `AppController.state.homography_matrix`.

---

## SECTION 8 — CALIB WORKER (workers/calib_worker.py)

```python
"""
Wraps the four calibration scripts in a QThread so they don't block the UI.
Emits: started(step), finished(step), error(step, msg), log(msg)
"""

from PyQt6.QtCore import QThread, pyqtSignal
import sys
from pathlib import Path

class CalibWorker(QThread):
    started_step  = pyqtSignal(int)
    finished_step = pyqtSignal(int)
    error_step    = pyqtSignal(int, str)
    log           = pyqtSignal(str)

    def __init__(self, step: int, controller, parent=None):
        super().__init__(parent)
        self.step       = step
        self.controller = controller

    def run(self):
        try:
            self.started_step.emit(self.step)
            state = self.controller.state

            if self.step == 1:
                self._run_step1(state)
            elif self.step == 3:
                self._run_step3(state)
            elif self.step == 4:
                self._run_step4(state)

            self.finished_step.emit(self.step)

        except Exception as e:
            self.error_step.emit(self.step, str(e))

    def _run_step1(self, state):
        """Extract still frame from video."""
        self.log.emit("Extracting still frame...")
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "step1", state.repo_root / "scripts" / "step1_extract_frame.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # step1 writes output/still_frame.jpg
        state.still_frame_path = state.output_dir / "still_frame.jpg"
        self.log.emit(f"Frame saved: {state.still_frame_path}")

    def _run_step3(self, state):
        """Compute homography matrix."""
        import json, numpy as np
        self.log.emit("Computing homography matrix...")
        # Save GCPs to JSON files that step3_homography.py expects
        pixel_path = state.output_dir / "gcps_pixel.json"
        world_path = state.output_dir / "gcps_world.json"
        json.dump(state.gcps_pixel, pixel_path.open("w"))
        json.dump(state.gcps_world, world_path.open("w"))
        # Import and run step3
        spec = importlib.util.spec_from_file_location(
            "step3", state.repo_root / "scripts" / "step3_homography.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Load the saved matrix
        matrix_path = state.output_dir / "homography_matrix.npy"
        if matrix_path.exists():
            state.homography_matrix = np.load(str(matrix_path))
            self.log.emit("Homography matrix computed successfully.")
        else:
            raise FileNotFoundError("step3 did not write homography_matrix.npy")

    def _run_step4(self, state):
        """Create annotated benchmark image."""
        self.log.emit("Creating annotated frame...")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "step4", state.repo_root / "scripts" / "step4_annotate_frame.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.log.emit("Annotated frame saved.")
```

---

## SECTION 9 — ANALYSIS SCREEN (gui/screen_analysis.py)

### 9.1 Layout

Three sections stacked vertically:

**Top — configuration bar** (collapsible, 80 px when expanded):
A single row of controls:
- "Video" label + `QLineEdit` showing current video path + folder browse button
- "Frames" label + `QSpinBox` (0 = all) for `--frames` argument
- "Save video" `QCheckBox` (if unchecked, passes `--no-video`)
- "Run all" `QPushButton` (primary)

**Middle — step cards** (scrollable `QScrollArea`):
Four `QFrame` cards for steps 5, 6, 7, 8.
Each card has:
- Header row: animated status dot + step name + status badge chip
- Body: one-line description of what the step does
- A `QProgressBar` (0–100, updates from worker signals)
- A `QLabel` showing ETA or last log line from that step

**Bottom — log panel** (fixed 140 px):
A read-only `QTextEdit` (objectName `"LogPanel"`) that appends coloured
log lines:
- Green (#5DCAA5) for success lines
- Amber (#E8A020) for warning lines  
- Default muted grey for info lines
Detect colour by checking if the line contains "✓" or "error" or "warning".

### 9.2 Pipeline orchestration

Create `controllers/pipeline_runner.py`:

```python
"""
PipelineRunner: runs steps 5-8 sequentially in a QThread.
Each step's script is imported and called as a module.
Progress and log messages are emitted as signals.
"""
from PyQt6.QtCore import QThread, pyqtSignal
import importlib.util, sys, io, contextlib
from pathlib import Path


class StepWorker(QThread):
    """Generic worker for a single pipeline step."""
    progress = pyqtSignal(int, float)   # step_number, fraction 0.0-1.0
    log      = pyqtSignal(str)
    done     = pyqtSignal(int)          # step_number
    error    = pyqtSignal(int, str)     # step_number, message

    def __init__(self, step: int, script_path: Path, extra_args: dict = None, parent=None):
        super().__init__(parent)
        self.step        = step
        self.script_path = script_path
        self.extra_args  = extra_args or {}
        self._stop_flag  = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log.emit(f"[Step {self.step}] Starting {self.script_path.name}")
            spec = importlib.util.spec_from_file_location(
                f"step{self.step}", self.script_path
            )
            mod = importlib.util.module_from_spec(spec)
            # Monkey-patch any progress callback if the module supports it
            if hasattr(mod, "set_progress_callback"):
                mod.set_progress_callback(
                    lambda frac: self.progress.emit(self.step, frac)
                )
            spec.loader.exec_module(mod)
            self.progress.emit(self.step, 1.0)
            self.log.emit(f"[Step {self.step}] ✓ Complete")
            self.done.emit(self.step)
        except Exception as e:
            self.log.emit(f"[Step {self.step}] ERROR: {e}")
            self.error.emit(self.step, str(e))
```

**IMPORTANT NOTE FOR AGENT**: Step 5 (`step5_detect_track.py`) runs for
30–60 minutes on CPU. You must patch it to emit progress.
After importing the module, wrap its inner frame-processing loop so it calls
the progress callback every 100 frames. Do this by subclassing or by
monkey-patching the YOLO/tracker loop. Do NOT subprocess-call the script —
import it as a module so the UI thread can receive signals.

Alternatively, subprocess the script and parse its stdout for frame numbers.
If you choose subprocess, use `QProcess` (not Python `subprocess`), pipe
stdout, and parse lines of the form "Frame N/M" to compute progress.

### 9.3 Run/Pause/Stop controls

- "Run all" starts steps 5 → 6 → 7 → 8 in sequence via chained `done` signals.
- "Pause" calls `worker.requestInterruption()` on the current step worker;
  resume re-runs the step from the same frame if `step5` supports it, else
  restarts the step.
- "Stop" calls `worker.stop()` and marks remaining steps as "idle".

---

## SECTION 10 — STEP 5 WORKER (workers/step5_worker.py)

Step 5 is the most important to get right because it takes the longest.

**Approach — use QProcess to subprocess the script:**

```python
from PyQt6.QtCore import QObject, pyqtSignal, QProcess
import re

class Step5Worker(QObject):
    """
    Runs step5_detect_track.py as a subprocess via QProcess.
    Parses stdout for "Frame N/M" lines to compute progress.
    """
    progress = pyqtSignal(float)       # 0.0 to 1.0
    log      = pyqtSignal(str)
    done     = pyqtSignal()
    error    = pyqtSignal(str)

    FRAME_RE = re.compile(r"Frame\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)

    def __init__(self, script_path: str, python_exe: str, frames: int = 0, no_video: bool = False, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.python_exe  = python_exe
        self.frames      = frames
        self.no_video    = no_video
        self.process     = None

    def start(self):
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)

        args = [self.script_path]
        if self.frames > 0:
            args += ["--frames", str(self.frames)]
        if self.no_video:
            args.append("--no-video")

        self.process.start(self.python_exe, args)

    def stop(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _on_output(self):
        raw = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in raw.splitlines():
            self.log.emit(line)
            m = self.FRAME_RE.search(line)
            if m:
                current, total = int(m.group(1)), int(m.group(2))
                if total > 0:
                    self.progress.emit(current / total)

    def _on_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.progress.emit(1.0)
            self.done.emit()
        else:
            self.error.emit(f"Step 5 exited with code {exit_code}")
```

**Modify step5_detect_track.py** (the original script) to print progress lines
in the format `Frame N/M` inside its frame-processing loop. Add exactly one
`print(f"Frame {frame_idx}/{total_frames}", flush=True)` call every 50 frames.
This is the minimum change required in the original code.

---

## SECTION 11 — RESULTS SCREEN (gui/screen_results.py)

### 11.1 Tabs

Use a `QTabWidget` with three tabs:
- Charts
- Data tables
- Output files

### 11.2 Charts tab

A 2×2 grid `QGridLayout` of chart panels.
Each panel is a `QFrame` containing:
- A header with the chart title + a download `QPushButton`
- A `QLabel` displaying the PNG as a `QPixmap` scaled to fill the panel

On load, look for these files in `output/`:
- `flow_plot_5min.png` → Flow rate chart
- `composition_pie.png` → Donut chart
- `speed_histograms.png` → Combined speed panel
- `composition_bar.png` → Per-lane bar chart

If a file does not exist, show a muted placeholder "— Not yet generated —".

The download button copies the PNG to a user-chosen path via `QFileDialog.getSaveFileName`.

### 11.3 Data tables tab

A `QTabWidget` (inner) with tabs for each CSV:
- vehicle_counts.csv
- vehicle_speeds.csv
- flow_1min.csv
- composition.csv
- speed_stats.csv

For each CSV, load it with `pandas.read_csv()` and populate a `QTableWidget`.
Add column headers. Make cells read-only. Add a row count label.

```python
def load_csv_to_table(csv_path: Path, table: QTableWidget):
    import pandas as pd
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
```

### 11.4 Output files tab

A `QListWidget` showing all files in `output/` with their sizes and
modification dates. Right-click context menu: Open in Explorer, Copy path,
Delete.

### 11.5 Right sidebar

A narrow `QFrame` (180 px) fixed to the right of the chart grid,
showing two sections of summary stats loaded from CSVs:
- Speed statistics: Mean, Std, 85th percentile, Max (from `speed_stats.csv`)
- Flow summary: Peak flow, Peak time, Total vehicles (from `flow_1min.csv`)

At the bottom, an "Export all" `QPushButton` that opens a folder-picker and
copies the entire `output/` directory to the chosen location.

---

## SECTION 12 — SETTINGS SCREEN (gui/screen_settings.py)

### 12.1 Layout

A two-column `QHBoxLayout`:
- Left: `QListWidget` (120 px, no border) for section navigation
- Right: `QStackedWidget` with one page per section

### 12.2 Sections and their fields

All fields must read their initial value from `AppController.get_config()`
when the screen is shown. Saving calls `AppController.save_config(updates)`.

**Model section:**
- Model file: `QComboBox` populated by globbing `models/*.pt`; stores `MODEL_PATH`
- Device: `QComboBox` ["cpu", "cuda:0", "cuda:1"]; stores `DEVICE`
- Confidence threshold: `QDoubleSpinBox` 0.0–1.0 step 0.05; stores `CONF_THRESH`
- IoU threshold: `QDoubleSpinBox` 0.0–1.0 step 0.05; stores `IOU_THRESH`

**Paths section:**
- Video path: `QLineEdit` + browse button; stores `VIDEO_PATH`
- Output directory: `QLineEdit` + browse button; stores `OUTPUT_DIR`
- Model directory: `QLineEdit` + browse button; stores `MODEL_DIR`

**Detection section:**
- Frame skip: `QSpinBox` 1–10; stores `FRAME_SKIP`
- Max frames: `QSpinBox` 0 = all; stores `MAX_FRAMES`
- Save annotated video: `QCheckBox`; stores `SAVE_VIDEO` (True/False)

**Speed section:**
- Speed smoothing window: `QSpinBox`; stores `SPEED_SMOOTH_WINDOW`
- Min track length: `QSpinBox`; stores `MIN_TRACK_LEN`

**Output section:**
- Flow intervals (checkboxes): 1 min, 5 min, 10 min; stores `FLOW_INTERVALS`
- Chart DPI: `QSpinBox` 72–300; stores `CHART_DPI`
- Chart format: `QComboBox` ["png", "pdf", "svg"]; stores `CHART_FORMAT`

**About section:**
- Static text labels: version, Python version, PyQt6 version, repo URL.
- A "Open repo" `QPushButton` that opens the GitHub URL in the default browser.
- A "Check for model updates" button.

### 12.3 Save / reset

At the bottom of the right panel:
- "Save" primary button → `AppController.save_config(updates)` then show
  `QMessageBox.information("Settings saved")`
- "Reset to defaults" secondary button → reload from config.py without saving

---

## SECTION 13 — RESULTS MANAGER (controllers/results_manager.py)

```python
"""
ResultsManager: loads all output files and provides them to the Results screen.
"""
from pathlib import Path
from typing import Optional
import pandas as pd


class ResultsManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def load_composition(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "composition.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_speeds(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "vehicle_speeds.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_flow(self, interval: int = 5) -> Optional[pd.DataFrame]:
        p = self.output_dir / f"flow_{interval}min.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_speed_stats(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "speed_stats.csv"
        return pd.read_csv(p) if p.exists() else None

    def get_chart_paths(self) -> dict:
        names = [
            "flow_plot_5min", "composition_pie",
            "speed_histograms", "composition_bar", "speed_boxplot",
            "flow_plot_1min", "flow_plot_10min",
        ]
        return {
            name: self.output_dir / f"{name}.png"
            for name in names
        }

    def get_summary_stats(self) -> dict:
        stats = {}
        df = self.load_speeds()
        if df is not None and "speed_kmh" in df.columns:
            s = df["speed_kmh"]
            stats["speed_mean"]  = round(s.mean(), 1)
            stats["speed_std"]   = round(s.std(), 1)
            stats["speed_85pct"] = round(s.quantile(0.85), 1)
            stats["speed_max"]   = round(s.max(), 1)
        df = self.load_flow(1)
        if df is not None:
            flow_col = [c for c in df.columns if "flow" in c.lower() or "veh" in c.lower()]
            if flow_col:
                stats["peak_flow"] = int(df[flow_col[0]].max())
        counts_path = self.output_dir / "vehicle_counts.csv"
        if counts_path.exists():
            stats["total_vehicles"] = len(pd.read_csv(counts_path))
        return stats
```

---

## SECTION 14 — PACKAGING (pyinstaller)

Create `build.spec` at the repo root:

```python
# build.spec
import sys
from pathlib import Path

block_cipher = None
app_name = "TrafficAnalysis"

a = Analysis(
    ["traffic_analysis_gui/main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[
        ("traffic_analysis_gui/assets", "traffic_analysis_gui/assets"),
        ("scripts", "scripts"),
        ("models", "models"),
    ],
    hiddenimports=[
        "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "matplotlib.backends.backend_qt5agg",
        "ultralytics", "cv2", "pandas", "numpy", "scipy",
    ],
    hookspath=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name=app_name,
    debug=False,
    console=False,       # no terminal window on Windows
    icon="traffic_analysis_gui/assets/icons/app.ico",
)
```

Build command:
```
pyinstaller build.spec --clean --noconfirm
```

---

## SECTION 15 — IMPLEMENTATION ORDER FOR THE AGENT

Follow this exact order. Do not jump ahead. Verify each step before proceeding.

```
Step A:  Create all __init__.py files (empty)
Step B:  Create assets/style.qss
Step C:  Create main.py and run it — expect a blank window
Step D:  Create app_controller.py — test get_config() prints config keys
Step E:  Create main_window.py — sidebar + topbar + empty stack — test navigation
Step F:  Create screen_settings.py — test reading and writing config.py
Step G:  Create calib_manager.py
Step H:  Create CalibCanvas widget — test it loads and renders a JPEG
Step I:  Create screen_calibration.py — test GCP clicking and display
Step J:  Create calib_worker.py — test step 1 extracts a frame
Step K:  Create step5_worker.py — test it runs and emits log lines
Step L:  Create pipeline_runner.py
Step M:  Create screen_analysis.py — test progress bars update
Step N:  Create results_manager.py — test loading CSVs
Step O:  Create screen_results.py — test chart display
Step P:  Create screen_dashboard.py — test KPI cards populate
Step Q:  Wire all signal/slot connections in main_window.py
Step R:  End-to-end test: extract frame → mark GCPs → run step 5 → view results
Step S:  Run pyinstaller build and test the packaged executable
```

---

## SECTION 16 — SIGNAL / SLOT CONNECTION MAP

Document all the cross-screen signal/slot connections here.
Wire these in `MainWindow._connect_signals()`:

| Signal source                             | Signal name          | Slot target                                |
|-------------------------------------------|----------------------|--------------------------------------------|
| `calib_worker.finished_step`              | `(int)`              | `ctrl.set_step_status(step, "done")`       |
| `calib_worker.finished_step`              | `(int)`              | `dashboard.refresh()`                      |
| `calib_worker.log`                        | `(str)`              | `analysis.append_log(str)`                 |
| `step5_worker.progress`                   | `(float)`            | `analysis.update_progress(5, float)`       |
| `step5_worker.done`                       | `()`                 | `pipeline_runner.start_step(6)`            |
| `step5_worker.error`                      | `(str)`              | `analysis.show_error(str)`                 |
| `step6_worker.done`                       | `()`                 | `pipeline_runner.start_step(7)`            |
| `step7_worker.done`                       | `()`                 | `pipeline_runner.start_step(8)`            |
| `step8_worker.done`                       | `()`                 | `results.refresh()`                        |
| `step8_worker.done`                       | `()`                 | `dashboard.refresh()`                      |
| `calib_canvas.gcp_changed`                | `(list)`             | `right_panel.update_gcp_table(list)`       |
| `calib_canvas.line_changed`               | `(list)`             | `ctrl.state.detection_line = list`         |
| `settings.config_saved`                   | `(dict)`             | `ctrl.save_config(dict)`                   |

---

## SECTION 17 — ERROR HANDLING REQUIREMENTS

1. **Missing video file**: when `Analysis` screen's Run button is clicked,
   check that `ctrl.state.video_path` exists. If not, show a
   `QMessageBox.warning` with "Please select a valid video file."

2. **Missing model**: check that `models/yolov9t.pt` (or the configured model)
   exists before starting step 5. Show a dialog with a download link if missing.

3. **Missing calibration**: before running step 5, check that
   `output/homography_matrix.npy`, `output/gcps_pixel.json`, and
   `output/detection_line.json` all exist. If not, redirect the user to the
   Calibration screen with a toast notification.

4. **Worker crash**: any `error` signal from a worker must:
   - Append a red log line to the analysis log panel
   - Set the step status to "error" (red dot)
   - Enable the Run button again so the user can retry
   - NOT crash the main application

5. **Config parse error**: if `get_config()` fails to parse any line,
   skip that line silently and log a warning to stderr. Never crash on bad config.

---

## SECTION 18 — TESTING CHECKLIST

Before declaring the application complete, verify every item:

**Startup:**
- [ ] App launches without errors on Windows and Linux
- [ ] Sidebar navigation switches all five screens
- [ ] Topbar title updates correctly

**Calibration:**
- [ ] "Extract frame" correctly writes `output/still_frame.jpg`
- [ ] Still frame renders in CalibCanvas at correct aspect ratio
- [ ] Left-click adds GCP dots with labels
- [ ] Right-click removes the last GCP dot
- [ ] Switching mode (GCP/ROI/Line) works correctly
- [ ] ROI polygon draws with green dashed outline
- [ ] Detection line draws in red between exactly 2 points
- [ ] GCP pixel table in right panel updates live
- [ ] Real-world coordinate fields accept decimal input
- [ ] "Compute homography" runs step 3 and shows reprojection error

**Analysis:**
- [ ] Video path browse button opens a file picker
- [ ] "Run all" starts step 5 and shows progress bar moving
- [ ] Log panel streams lines in real time during step 5
- [ ] Step cards change status from idle → running → done sequentially
- [ ] "Pause" halts step 5 and disables further progress updates
- [ ] "Stop" terminates the process and resets all step statuses to idle

**Results:**
- [ ] Charts tab shows all four PNGs after a complete run
- [ ] Placeholder text shows for missing charts
- [ ] Download button saves PNG to user-chosen path
- [ ] Data tables tab loads CSVs with correct headers
- [ ] Output files tab lists all files in output/ with sizes
- [ ] Right sidebar shows correct summary statistics

**Settings:**
- [ ] All fields populate from config.py on screen show
- [ ] Save writes values back to config.py
- [ ] Reset re-reads config.py without saving
- [ ] Model ComboBox lists all .pt files in models/

**Dashboard:**
- [ ] KPI cards show "--" before pipeline runs
- [ ] KPI cards populate with real values after pipeline completes
- [ ] Pipeline status row shows correct dot colours
- [ ] Composition donut appears after composition.csv is created

---

## SECTION 19 — KNOWN PITFALLS

1. **Qt thread safety**: Never update a `QWidget` from inside a `QThread.run()`.
   Always emit a signal and let the main thread handle the update.

2. **importlib and config**: `scripts/config.py` uses relative paths like
   `Path("output")`. When importing these scripts from inside the GUI,
   the working directory may differ. Either `os.chdir(repo_root)` before
   importing, or patch the paths at import time.

3. **OpenCV and Qt**: Both OpenCV and Qt can fight over the display backend.
   Import OpenCV before PyQt6, and never show `cv2.imshow` from the GUI —
   use CalibCanvas instead.

4. **matplotlib and Qt**: Use `matplotlib.use("Qt5Agg")` or `"Qt6Agg"` before
   importing `pyplot`. Set it in `main.py` before any other matplotlib import.

5. **PyInstaller and ultralytics**: Ultralytics auto-downloads models at runtime.
   When packaged, the download cache must be writable. Set
   `YOLO_CONFIG_DIR` env var to a writable path inside the app bundle.

6. **step5 duration**: Do not set any GUI timeout shorter than 90 minutes.
   The detection step can take up to 60 minutes on CPU. The UI should remain
   fully responsive throughout (progress bar animating, log updating).

7. **Windows paths with spaces**: "Raw video/traffic_video.mp4" contains a space.
   Always use `Path()` objects, never raw string concatenation.

---

## SECTION 20 — FINAL DELIVERABLES

When complete, the repository should contain:

```
traffic_analysis_gui/           ← all new GUI code
    (as specified in Section 1)

scripts/                        ← original scripts (only step5 modified)
    step5_detect_track.py       ← added print(f"Frame N/M") every 50 frames

build.spec                      ← pyinstaller spec

README_GUI.md                   ← short readme explaining how to launch:
                                   python -m traffic_analysis_gui.main
                                   and how to build the executable
```

The original command-line workflow must still work unchanged:
```
python scripts/run_all.py
```

---

*End of instructions. Good luck, agent.*
