"""
app_controller.py — Global state and project configuration manager.

The AppController is a plain Python class (not a QObject). It holds the
global mutable state of the application. All screens receive a reference to
the same instance.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import sys
import ast


@dataclass
class ProjectState:
    # Paths (all resolved relative to REPO_ROOT)
    repo_root:       Path = field(default_factory=lambda: Path("."))
    video_path:      Optional[Path] = None
    output_dir:      Path = field(default_factory=lambda: Path("output"))
    models_dir:      Path = field(default_factory=lambda: Path("models"))
    still_frame_path: Optional[Path] = None

    # Calibration
    gcps_pixel:  List[Tuple[int, int]] = field(default_factory=list)
    gcps_world:  List[Tuple[float, float]] = field(default_factory=list)
    road_area:   List[Tuple[int, int]] = field(default_factory=list)
    detection_line: List[Tuple[int, int]] = field(default_factory=list)
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
        root = Path(sys.path[0]) if sys.path[0] else Path(".")
        root = root.resolve()
        if root.name in ("scripts", "traffic_analysis_gui"):
            root = root.parent
        self.state.repo_root = root
        self.state.output_dir = self.state.repo_root / "output"
        self.state.models_dir = self.state.repo_root / "models"
        self.state.output_dir.mkdir(exist_ok=True)

        # Load video path from config if available
        cfg = self.get_config()
        if "VIDEO_PATH" in cfg:
            vp = Path(str(cfg["VIDEO_PATH"]))
            if vp.exists():
                self.state.video_path = vp

        # Check if still frame exists
        sf = self.state.output_dir / "still_frame.jpg"
        if sf.exists():
            self.state.still_frame_path = sf

        # Check which steps are already done based on output files
        self._detect_completed_steps()

    def _detect_completed_steps(self):
        """Check output files to determine which pipeline steps are complete."""
        od = self.state.output_dir
        checks = {
            1: od / "still_frame.jpg",
            3: od / "homography_matrix.npy",
            4: od / "still_frame_annotated.jpg",
            5: od / "vehicle_counts.csv",
            6: od / "vehicle_speeds.csv",
            7: od / "composition.csv",
            8: od / "composition_pie.png",
        }
        for step, path in checks.items():
            if path.exists():
                self.state.step_status[step] = "done"
                self.state.step_progress[step] = 1.0

        # Step 2 (GCP marking) is done if gcps_pixel.json exists
        if (od / "gcps_pixel.json").exists():
            self.state.step_status[2] = "done"
            self.state.step_progress[2] = 1.0

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
        cfg = {}
        config_path = self.state.repo_root / "scripts" / "config.py"
        if not config_path.exists():
            return cfg
        try:
            for line in config_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#") and not line.startswith("def "):
                    name, _, val = line.partition("=")
                    name = name.strip()
                    val = val.strip()
                    # Skip lines with function calls, imports, or complex expressions
                    if name in ("os", "BASE_DIR") or "(" in name or "import" in line:
                        continue
                    try:
                        cfg[name] = ast.literal_eval(val)
                    except Exception:
                        cfg[name] = val
        except Exception as e:
            print(f"[Warning] Failed to parse config.py: {e}", file=sys.stderr)
        return cfg

    def save_config(self, updates: dict):
        """
        Write updated values back to scripts/config.py.
        Only update lines whose key is in `updates`; leave all others intact.
        """
        config_path = self.state.repo_root / "scripts" / "config.py"
        if not config_path.exists():
            return
        lines = config_path.read_text(encoding="utf-8").splitlines()
        result = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#") and not stripped.startswith("def "):
                name = stripped.split("=")[0].strip()
                if name in updates:
                    if name == "YOLO_MODEL":
                        result.append(f'{name} = os.path.join(MODELS_DIR, "{updates[name]}")')
                    else:
                        result.append(f"{name} = {repr(updates[name])}")
                    continue
            result.append(line)
        config_path.write_text("\n".join(result), encoding="utf-8")

    def get_model_path(self) -> Optional[Path]:
        """Return the resolved path to the configured YOLO model."""
        config_path = self.state.repo_root / "scripts" / "config.py"
        if not config_path.exists():
            return None
        try:
            import re
            for line in config_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("YOLO_MODEL") and "=" in line:
                    val = line.split("=")[1].strip()
                    match = re.search(r'["\']([^"\']+)["\']', val)
                    if match:
                        model_name = match.group(1)
                        # Resolve against models_dir
                        filename = Path(model_name).name
                        return self.state.models_dir / filename
        except Exception as e:
            print(f"[Warning] Failed to parse model path from config.py: {e}")
        
        # Fallback to first .pt file
        models_dir = self.state.models_dir
        if models_dir.exists():
            pts = list(models_dir.glob("*.pt"))
            if pts:
                return pts[0]
        return None

    def is_model_loaded(self) -> bool:
        """Check if the configured model file actually exists."""
        mp = self.get_model_path()
        return mp is not None and mp.exists()
