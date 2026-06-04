"""
step5_worker.py — Runs step5_detect_track.py as a subprocess via QProcess.
Parses stdout for "Frame N/M" lines to compute progress.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QProcess
import re
import sys


class Step5Worker(QObject):
    """
    Runs step5_detect_track.py as a subprocess via QProcess.
    Parses stdout for "Frame N/M" lines to compute progress.
    """
    progress = pyqtSignal(float)       # 0.0 to 1.0
    log = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    FRAME_RE = re.compile(r"Frame\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)

    def __init__(self, script_path: str, python_exe: str, frames: int = 0,
                 no_video: bool = False, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.python_exe = python_exe
        self.frames = frames
        self.no_video = no_video
        self.process = None

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

        self.log.emit(f"Starting: {self.python_exe} {' '.join(args)}")
        self.process.start(self.python_exe, args)

    def stop(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _on_output(self):
        raw = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in raw.splitlines():
            line = line.strip()
            if line:
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
