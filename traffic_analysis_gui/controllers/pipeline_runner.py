"""
pipeline_runner.py — Runs steps 5-8 sequentially in QThread workers.
Each step's script is imported and called as a module.
Progress and log messages are emitted as signals.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import importlib.util
import sys
import os
from pathlib import Path


class StepWorker(QThread):
    """Generic worker for a single pipeline step (steps 6, 7, 8)."""
    progress = pyqtSignal(int, float)   # step_number, fraction 0.0-1.0
    log = pyqtSignal(str)
    done = pyqtSignal(int)              # step_number
    error = pyqtSignal(int, str)        # step_number, message

    def __init__(self, step: int, script_path: Path, parent=None):
        super().__init__(parent)
        self.step = step
        self.script_path = script_path
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log.emit(f"[Step {self.step}] Starting {self.script_path.name}")

            # Ensure scripts directory is in path
            scripts_dir = str(self.script_path.parent)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            # Ensure cwd is at repo root
            repo_root = self.script_path.parent.parent
            original_cwd = os.getcwd()
            os.chdir(str(repo_root))

            # Remove from sys.modules if already imported to force reload
            mod_name = f"step{self.step}"
            if mod_name in sys.modules:
                del sys.modules[mod_name]

            try:
                spec = importlib.util.spec_from_file_location(
                    mod_name, self.script_path
                )
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "main"):
                    mod.main()
            finally:
                os.chdir(original_cwd)

            self.progress.emit(self.step, 1.0)
            self.log.emit(f"[Step {self.step}] ✓ Complete")
            self.done.emit(self.step)
        except Exception as e:
            self.log.emit(f"[Step {self.step}] ERROR: {e}")
            self.error.emit(self.step, str(e))
