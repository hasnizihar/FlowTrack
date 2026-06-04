# build.spec — PyInstaller spec file for packaging as a standalone executable
import sys
from pathlib import Path

block_cipher = None
app_name = "FlowTrack"

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
    icon=None,
)
