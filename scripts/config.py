"""
config.py — Central configuration for CE3163 Assignment 03 Traffic Analysis Pipeline
All tuneable parameters live here so every script reads from one place.
"""

import os

# --- Paths --------------------------------------------------------------------
# BASE_DIR is the project root (parent of scripts/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_PATH = os.path.join(BASE_DIR, "data", "Raw video", "TimeVideo_20260501_085748.mp4")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STILL_FRAME_PATH       = os.path.join(OUTPUT_DIR, "still_frame.jpg")
ANNOTATED_FRAME_PATH   = os.path.join(OUTPUT_DIR, "still_frame_annotated.jpg")
HOMOGRAPHY_PATH        = os.path.join(OUTPUT_DIR, "homography_matrix.npy")
GCPS_PIXEL_PATH        = os.path.join(OUTPUT_DIR, "gcps_pixel.json")
GCPS_WORLD_PATH        = os.path.join(OUTPUT_DIR, "gcps_world.json")
ROAD_AREA_PATH         = os.path.join(OUTPUT_DIR, "road_area.json")
DETECTION_LINE_PATH    = os.path.join(OUTPUT_DIR, "detection_line.json")
VEHICLE_COUNTS_CSV     = os.path.join(OUTPUT_DIR, "vehicle_counts.csv")
VEHICLE_SPEEDS_CSV     = os.path.join(OUTPUT_DIR, "vehicle_speeds.csv")
TRACK_HISTORY_PATH     = os.path.join(OUTPUT_DIR, "track_history.pkl")
COMPOSITION_CSV        = os.path.join(OUTPUT_DIR, "composition.csv")
SPEED_STATS_CSV        = os.path.join(OUTPUT_DIR, "speed_stats.csv")
ANNOTATED_VIDEO_PATH   = os.path.join(OUTPUT_DIR, "annotated_output.mp4")

def flow_csv_path(interval):
    return os.path.join(OUTPUT_DIR, f"flow_{interval}min.csv")

def flow_plot_path(interval):
    return os.path.join(OUTPUT_DIR, f"flow_plot_{interval}min.png")

COMPOSITION_PIE_PATH   = os.path.join(OUTPUT_DIR, "composition_pie.png")
COMPOSITION_BAR_PATH   = os.path.join(OUTPUT_DIR, "composition_bar.png")
SPEED_HISTOGRAM_PATH   = os.path.join(OUTPUT_DIR, "speed_histograms.png")
SPEED_BOXPLOT_PATH     = os.path.join(OUTPUT_DIR, "speed_boxplot.png")

# --- Site Parameters ----------------------------------------------------------
# GPS: ~6.7115°N, 79.9075°E  (Panadura, Kalutara, Western Province, Sri Lanka)
# Recording: 01 May 2026, 08:57:48 -> 09:58:35 AM

# Lane 1: 3 sub-lanes × 3.5 m = 10.5 m  (vehicles COMING towards camera)
# Lane 2: 2 sub-lanes × 3.5 m = 7 m  (vehicles GOING away from camera)
LANE_1_WIDTH_M = 10.5   # metres
LANE_2_WIDTH_M = 7.0   # metres
SUB_LANE_WIDTH_M = 3.5  # metres per sub-lane
TOTAL_ROAD_WIDTH_M = LANE_1_WIDTH_M + LANE_2_WIDTH_M  # 15 m

# Lane assignment: world X in [0, 9) -> Lane 1,  [9, 15] -> Lane 2
LANE_BOUNDARY_M = LANE_1_WIDTH_M  # 9.0 m

# --- YOLO Configuration ------------------------------------------------------
MODELS_DIR = os.path.join(BASE_DIR, "models")
YOLO_MODEL = os.path.join(MODELS_DIR, "yolov9t.pt")
# YOLO_MODEL = os.path.join(MODELS_DIR, "yolov9c.pt")  # use this if u have GPU — better mAP for South-Asian traffic
YOLO_CONFIDENCE = 0.25       # Minimum detection confidence

# COCO class IDs -> base vehicle type names
# YOLOv9 detects standard COCO classes; we refine Car -> Car/Van/Three-Wheeler
# and Truck -> LGV/HGV using bounding-box geometry post-detection.
YOLO_CLASS_MAP = {
    2:  "Car",              # refined to Car / Van / Three-Wheeler
    3:  "Motorcycle",
    5:  "Bus",
    7:  "Truck",            # refined to LGV / HGV
}

# Full list of vehicle types used in this project (7 Sri-Lankan classes)
VEHICLE_TYPES = [
    "Motorcycle",
    "Three-Wheeler",
    "Car",
    "Van",
    "Light Goods Vehicle",
    "Bus",
    "Heavy Goods Vehicle",
]

# --- Size-based sub-classification thresholds --------------------------------
# These refine COCO base classes into Sri-Lankan vehicle sub-types using
# bounding-box geometry, since COCO does not have three-wheeler / van classes.
THREE_WHEELER_MAX_AREA_RATIO = 0.0035  # box_area / frame_area < this -> three-wheeler
THREE_WHEELER_MAX_ASPECT_RATIO = 1.05  # width/height <= this -> three-wheeler (tuk-tuks are typically taller/square)
VAN_MIN_ASPECT_RATIO         = 1.4     # width/height >= this -> van
HGV_MIN_AREA_RATIO           = 0.04    # box_area / frame_area >= this -> HGV

# --- Annotation Colors (BGR for OpenCV) --------------------------------------
# Each vehicle type gets a unique, visually distinct colour
VEHICLE_COLORS = {
    "Motorcycle":           (0, 255, 255),   # Yellow
    "Three-Wheeler":        (0, 165, 255),   # Orange
    "Car":                  (0, 255, 0),     # Green
    "Van":                  (255, 255, 0),   # Cyan
    "Light Goods Vehicle":  (255, 0, 255),   # Magenta
    "Bus":                  (0, 0, 255),     # Red
    "Heavy Goods Vehicle":  (255, 0, 0),     # Blue
}

# --- Tracker Configuration ---------------------------------------------------
DEEPSORT_MAX_AGE = 30        # Frames to keep lost track alive

# --- Detection Line ----------------------------------------------------------
# Set to None -> auto-detect as vertical center of the frame
# If detection_line.json exists (from step2), it will be used instead.
DETECTION_LINE_Y = None

# --- Video --------------------------------------------------------------------
# FPS will be auto-read from video; fallback value:
FALLBACK_FPS = 28

# --- Plot Style ---------------------------------------------------------------
PLOT_DPI = 150
PLOT_STYLE = "seaborn-v0_8-whitegrid"   # matplotlib style
FLOW_INTERVALS = [1, 5, 10]             # minutes