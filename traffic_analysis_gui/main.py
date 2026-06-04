"""
main.py — Application entry point.
Run with: python -m traffic_analysis_gui.main
or after packaging: ./FlowTrack (or FlowTrack.exe)
"""

import sys
import os
from pathlib import Path

# Set matplotlib backend before any other matplotlib import
# pyrefly: ignore [missing-import]
import matplotlib
matplotlib.use("Agg")

# Add the repo root to sys.path so the existing scripts/ package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Add scripts/ directory to path for config imports
scripts_dir = str(REPO_ROOT / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import QApplication
# pyrefly: ignore [missing-import]
from PyQt6.QtCore import Qt
# pyrefly: ignore [missing-import]
from PyQt6.QtGui import QFont

from traffic_analysis_gui.gui.main_window import MainWindow


def main():
    # Enable high-DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("FlowTrack")
    app.setOrganizationName("FlowTrack")
    app.setApplicationDisplayName("FlowTrack")

    # Load stylesheet
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # Default font
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    window = MainWindow()
    window.setWindowTitle("FlowTrack - AI-Powered Traffic Flow Analysis")
    window.resize(1280, 760)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
