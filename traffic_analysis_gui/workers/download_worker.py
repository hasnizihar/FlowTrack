import os
import urllib.request
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

class ModelDownloadWorker(QThread):
    progress = pyqtSignal(int)      # percentage
    finished = pyqtSignal(bool, str) # success, message/error

    def __init__(self, model_name: str, dest_dir: Path):
        super().__init__()
        self.model_name = model_name
        self.dest_dir = dest_dir

    def run(self):
        try:
            self.dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = self.dest_dir / self.model_name
            url = f"https://github.com/Ultralytics/assets/releases/download/v8.2.0/{self.model_name}"
            
            # Request setup
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_downloaded = 0
                chunk_size = 1024 * 64
                
                with open(dest_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((bytes_downloaded / total_size) * 100)
                            self.progress.emit(percent)
            
            self.finished.emit(True, f"Successfully downloaded {self.model_name}")
        except Exception as e:
            # Cleanup on failure
            dest_path = self.dest_dir / self.model_name
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except Exception:
                    pass
            self.finished.emit(False, str(e))
