"""
calib_worker.py — Wraps calibration scripts in a QThread so they don't block the UI.
Emits: started_step(step), finished_step(step), error_step(step, msg), log(msg)
"""

from PyQt6.QtCore import QThread, pyqtSignal
import importlib.util
import sys
import os
from pathlib import Path


class CalibWorker(QThread):
    started_step = pyqtSignal(int)
    finished_step = pyqtSignal(int)
    error_step = pyqtSignal(int, str)
    log = pyqtSignal(str)

    def __init__(self, step: int, controller, frame_number: int = 5000, parent=None):
        super().__init__(parent)
        self.step = step
        self.controller = controller
        self.frame_number = frame_number

    def run(self):
        try:
            self.started_step.emit(self.step)
            state = self.controller.state

            # Ensure working directory is at repo root for script compatibility
            original_cwd = os.getcwd()
            os.chdir(str(state.repo_root))

            # Add scripts dir to path
            scripts_dir = str(state.repo_root / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            try:
                if self.step == 1:
                    self._run_step1(state)
                elif self.step == 3:
                    self._run_step3(state)
                elif self.step == 4:
                    self._run_step4(state)
            finally:
                os.chdir(original_cwd)

            self.finished_step.emit(self.step)

        except Exception as e:
            self.error_step.emit(self.step, str(e))

    def _run_step1(self, state):
        """Extract still frame from video."""
        self.log.emit(f"Extracting still frame at frame index {self.frame_number}...")
        spec = importlib.util.spec_from_file_location(
            "step1", state.repo_root / "scripts" / "step1_extract_frame.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Call the extract_frame function with specified frame number!
        mod.extract_frame(frame_number=self.frame_number)
        # step1 writes output/still_frame.jpg
        state.still_frame_path = state.output_dir / "still_frame.jpg"
        self.log.emit(f"Frame saved: {state.still_frame_path}")

    def _run_step3(self, state):
        """Compute homography matrix."""
        import json
        import numpy as np
        self.log.emit("Computing homography matrix...")
        spec = importlib.util.spec_from_file_location(
            "step3", state.repo_root / "scripts" / "step3_homography.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
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
        spec = importlib.util.spec_from_file_location(
            "step4", state.repo_root / "scripts" / "step4_annotate_frame.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        self.log.emit("Annotated frame saved.")
