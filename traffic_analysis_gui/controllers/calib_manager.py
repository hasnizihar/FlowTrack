"""
calib_manager.py — GCP / ROI / homography logic.
"""

import json
import numpy as np
import cv2
from pathlib import Path
from typing import List, Tuple, Optional


class CalibManager:
    """Handles calibration data persistence and homography computation."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def save_gcps_pixel(self, gcps: List[Tuple[int, int]], ids: List[str] = None):
        """Save pixel GCPs to JSON."""
        data = []
        for i, (x, y) in enumerate(gcps):
            data.append({
                "id": ids[i] if ids and i < len(ids) else f"GCP-{i+1}",
                "pixel_x": int(x),
                "pixel_y": int(y),
            })
        path = self.output_dir / "gcps_pixel.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def save_gcps_world(self, gcps: List[Tuple[float, float]], ids: List[str] = None):
        """Save world GCPs to JSON."""
        data = []
        for i, (x, y) in enumerate(gcps):
            data.append({
                "id": ids[i] if ids and i < len(ids) else f"GCP-{i+1}",
                "world_x": float(x),
                "world_y": float(y),
            })
        path = self.output_dir / "gcps_world.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def save_road_area(self, vertices: List[Tuple[int, int]]):
        """Save road area polygon to JSON."""
        data = {"vertices": [{"x": int(x), "y": int(y)} for x, y in vertices]}
        path = self.output_dir / "road_area.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def save_detection_line(self, line: List[Tuple[int, int]]):
        """Save detection line endpoints to JSON."""
        if len(line) < 2:
            return None
        data = {
            "start": {"x": int(line[0][0]), "y": int(line[0][1])},
            "end": {"x": int(line[1][0]), "y": int(line[1][1])},
        }
        path = self.output_dir / "detection_line.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def load_gcps_pixel(self) -> List[Tuple[int, int]]:
        """Load pixel GCPs from JSON."""
        path = self.output_dir / "gcps_pixel.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [(g["pixel_x"], g["pixel_y"]) for g in data]

    def load_gcps_world(self) -> List[Tuple[float, float]]:
        """Load world GCPs from JSON."""
        path = self.output_dir / "gcps_world.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [(g["world_x"], g["world_y"]) for g in data]

    def load_road_area(self) -> List[Tuple[int, int]]:
        """Load road area polygon from JSON."""
        path = self.output_dir / "road_area.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [(v["x"], v["y"]) for v in data["vertices"]]

    def load_detection_line(self) -> List[Tuple[int, int]]:
        """Load detection line from JSON."""
        path = self.output_dir / "detection_line.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [(data["start"]["x"], data["start"]["y"]),
                (data["end"]["x"], data["end"]["y"])]

    def compute_homography(self, pixel_pts: List[Tuple[int, int]],
                           world_pts: List[Tuple[float, float]]) -> Tuple[Optional[np.ndarray], float]:
        """Compute homography matrix and return (H, mean_reprojection_error)."""
        if len(pixel_pts) < 4 or len(world_pts) < 4:
            raise ValueError("Need at least 4 GCP pairs.")
        if len(pixel_pts) != len(world_pts):
            raise ValueError("Pixel and world GCP counts must match.")

        px = np.float32(pixel_pts)
        wx = np.float32(world_pts)

        H, mask = cv2.findHomography(px, wx, cv2.RANSAC, 5.0)
        if H is None:
            raise RuntimeError("Homography computation failed.")

        # Compute reprojection error
        projected = cv2.perspectiveTransform(
            px.reshape(-1, 1, 2), H
        ).reshape(-1, 2)
        errors = np.sqrt(np.sum((projected - wx) ** 2, axis=1))
        mean_error = float(np.mean(errors))

        # Save matrix
        np.save(str(self.output_dir / "homography_matrix.npy"), H)

        return H, mean_error
