"""
step5_detect_track.py — YOLOv9 + DeepSORT Vehicle Detection & Tracking Pipeline

This is the core analysis script. It:
  1. Loads the video and homography matrix
  2. Runs YOLOv9 on each frame to detect vehicles
  3. Tracks vehicles across frames with DeepSORT
  4. Maps pixel positions to real-world coordinates via homography
  5. Counts vehicles crossing the detection line
  6. Assigns each vehicle to a lane
  7. Saves tracking data and optionally an annotated video

Usage:
    python step5_detect_track.py
    python step5_detect_track.py --no-video   # skip annotated video output
"""

import cv2
import json
import numpy as np
import os
import pandas as pd
import pickle
import time
import sys
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import config


def pixel_to_world(px, py, H):
    """Convert pixel coordinates to real-world coordinates using homography."""
    pt = np.array([[px, py]], dtype=np.float32).reshape(-1, 1, 2)
    world = cv2.perspectiveTransform(pt, H)[0][0]
    return float(world[0]), float(world[1])


def load_road_mask(width, height):
    """Load road area polygon from JSON and create a binary mask.
    Returns (mask, polygon_pts) or (None, None) if file not found."""
    if not os.path.exists(config.ROAD_AREA_PATH):
        return None, None
    with open(config.ROAD_AREA_PATH) as f:
        data = json.load(f)
    pts = np.array([(v["x"], v["y"]) for v in data["vertices"]], dtype=np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    return mask, pts


def load_detection_line():
    """Load detection line endpoints from JSON.
    Returns ((x1,y1), (x2,y2)) or None if file not found."""
    if not os.path.exists(config.DETECTION_LINE_PATH):
        return None
    with open(config.DETECTION_LINE_PATH) as f:
        data = json.load(f)
    start = (data["start"]["x"], data["start"]["y"])
    end = (data["end"]["x"], data["end"]["y"])
    return (start, end)


def point_crosses_line(prev_pos, curr_pos, line_start, line_end):
    """Check if a point moved from prev_pos to curr_pos across the line segment.
    Uses a cross-product sign change test."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(line_start, line_end, prev_pos)
    d2 = cross(line_start, line_end, curr_pos)
    # Sign change means the point crossed the line
    return (d1 > 0 and d2 <= 0) or (d1 < 0 and d2 >= 0)


def assign_lane(world_x):
    """Assign a lane based on real-world X position."""
    if world_x < config.LANE_BOUNDARY_M:
        return "Lane 1"
    else:
        return "Lane 2"


def refine_vehicle_type(base_type, box_w, box_h, frame_area):
    """Refine COCO base class into detailed Sri-Lankan vehicle types.

    YOLOv9 (COCO) does not have three-wheeler or van classes natively.
    We post-process using bounding-box geometry:
      - Car  -> Three-Wheeler (small area) | Van (wide aspect) | Car
      - Truck -> HGV (large area) | LGV
    """
    box_area = box_w * box_h
    area_ratio = box_area / frame_area if frame_area > 0 else 0

    if base_type == "Car":
        aspect = box_w / box_h if box_h > 0 else 1
        if area_ratio < config.THREE_WHEELER_MAX_AREA_RATIO and aspect <= config.THREE_WHEELER_MAX_ASPECT_RATIO:
            return "Three-Wheeler"
        if aspect >= config.VAN_MIN_ASPECT_RATIO:
            return "Van"
        return "Car"

    if base_type == "Truck":
        if area_ratio >= config.HGV_MIN_AREA_RATIO:
            return "Heavy Goods Vehicle"
        return "Light Goods Vehicle"

    return base_type   # Motorcycle, Bus stay as-is


def main(write_video=True, max_frames=None):
    print("=" * 60)
    print("VEHICLE DETECTION & TRACKING PIPELINE")
    print("=" * 60)

    # --- Load homography -------------------------------------------------
    H = np.load(config.HOMOGRAPHY_PATH)
    print(f"[OK] Homography matrix loaded from: {config.HOMOGRAPHY_PATH}")

    # --- Load YOLO model -------------------------------------------------
    print(f"\nLoading YOLO model: {config.YOLO_MODEL}")
    model = YOLO(config.YOLO_MODEL)
    print("[OK] YOLO model ready")

    # --- Initialize DeepSORT tracker -------------------------------------
    tracker = DeepSort(max_age=config.DEEPSORT_MAX_AGE)
    print("[OK] DeepSORT tracker initialized")

    # --- Open video ------------------------------------------------------
    print(f"\nOpening video: {config.VIDEO_PATH}")
    cap = cv2.VideoCapture(config.VIDEO_PATH)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {config.VIDEO_PATH}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or config.FALLBACK_FPS
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps

    print(f"  Frames     : {total_frames}")
    print(f"  FPS        : {fps}")
    print(f"  Resolution : {width} x {height}")
    print(f"  Duration   : {duration_sec:.1f}s ({duration_sec/60:.1f} min)")

    # --- Load road area mask (ROI) -----------------------------------------
    road_mask, road_polygon = load_road_mask(width, height)
    if road_mask is not None:
        print(f"[OK] Road area mask loaded from: {config.ROAD_AREA_PATH}")
    else:
        print("[--] No road area mask found. All detections will be kept.")

    # --- Load detection line -------------------------------------------------
    det_line = load_detection_line()
    if det_line is not None:
        det_line_start, det_line_end = det_line
        print(f"[OK] Detection line loaded: {det_line_start} -> {det_line_end}")
        # For backward compat, also compute a horizontal Y from the midpoint
        det_y = (det_line_start[1] + det_line_end[1]) // 2
    else:
        det_y = config.DETECTION_LINE_Y or height // 2
        det_line_start = (0, det_y)
        det_line_end = (width, det_y)
        print(f"[--] No detection line file. Using horizontal line at y={det_y}")

    # --- Optional: annotated video writer --------------------------------
    video_writer = None
    if write_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(
            config.ANNOTATED_VIDEO_PATH, fourcc, fps, (width, height)
        )
        print(f"\n[OK] Annotated video will be saved to: {config.ANNOTATED_VIDEO_PATH}")

    # --- Processing ------------------------------------------------------
    records = []
    track_history = {}
    frame_no = 0
    start_time = time.time()

    print(f"\n{'-'*60}")
    print("Processing frames... (this may take a while)")
    print(f"{'-'*60}\n")

    while True:
        if max_frames is not None and frame_no >= max_frames:
            print(f"Reached max frames ({max_frames}). Stopping detection.")
            break
            
        ret, frame = cap.read()
        if not ret:
            break

        # Run YOLO detection
        results = model(frame, verbose=False, conf=config.YOLO_CONFIDENCE)[0]
        detections = []
        frame_area = width * height

        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in config.YOLO_CLASS_MAP:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            # Filter by road area mask (skip detections outside ROI)
            if road_mask is not None:
                cx_det, cy_det = (x1 + x2) // 2, (y1 + y2) // 2
                if road_mask[min(cy_det, height - 1), min(cx_det, width - 1)] == 0:
                    continue
            base_type = config.YOLO_CLASS_MAP[cls_id]
            vtype = refine_vehicle_type(base_type, x2 - x1, y2 - y1, frame_area)
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, vtype))

        # Update tracker
        tracks = tracker.update_tracks(detections, frame=frame)

        for track in tracks:
            if not track.is_confirmed():
                continue

            tid = track.track_id
            vtype = track.get_det_class()
            x1, y1, x2, y2 = map(int, track.to_ltrb())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Map pixel centroid to real-world coordinates
            try:
                wx, wy = pixel_to_world(cx, cy, H)
            except Exception:
                continue

            # Initialize track history
            if tid not in track_history:
                track_history[tid] = {
                    "type": vtype,
                    "positions": [],
                    "counted": False,
                    "lane": None,
                }

            track_history[tid]["positions"].append((frame_no, wx, wy))
            lane = assign_lane(wx)
            track_history[tid]["lane"] = lane

            # Count when vehicle crosses detection line
            # Use previous position to detect crossing via cross-product test
            positions = track_history[tid]["positions"]
            crossed = False
            if len(positions) >= 2 and not track_history[tid]["counted"]:
                prev_frame, _, _ = positions[-2]
                # Get previous pixel centroid (approximate from world isn't great;
                # store pixel centroids separately for crossing test)
                pass  # We use the pixel centroid approach below

            if not track_history[tid]["counted"]:
                # Store pixel centroid for crossing test
                if "prev_pixel" not in track_history[tid]:
                    track_history[tid]["prev_pixel"] = (cx, cy)
                else:
                    prev_px = track_history[tid]["prev_pixel"]
                    if point_crosses_line(prev_px, (cx, cy),
                                          det_line_start, det_line_end):
                        crossed = True
                    track_history[tid]["prev_pixel"] = (cx, cy)

            if crossed:
                track_history[tid]["counted"] = True
                timestamp_sec = frame_no / fps
                records.append({
                    "track_id": tid,
                    "vehicle_type": vtype,
                    "lane": lane,
                    "timestamp_sec": round(timestamp_sec, 3),
                    "world_x": round(wx, 3),
                    "world_y": round(wy, 3),
                    "frame_no": frame_no,
                })

            # Draw on annotated frame — colour by vehicle type
            if write_video and video_writer:
                color = config.VEHICLE_COLORS.get(vtype, (255, 255, 255))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{vtype} #{tid}"
                # Draw label background for readability
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # Draw road area polygon on annotated frame
        if write_video and video_writer and road_polygon is not None:
            overlay = frame.copy()
            cv2.polylines(overlay, [road_polygon.reshape((-1, 1, 2))],
                          isClosed=True, color=(255, 200, 0), thickness=1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        # Draw detection line on annotated frame
        if write_video and video_writer:
            cv2.line(frame, det_line_start, det_line_end, (0, 0, 255), 2)

            # Progress overlay
            progress_text = f"Frame: {frame_no}/{total_frames} | Vehicles: {len(records)}"
            (tw, th), _ = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(frame, progress_text, (width - tw - 10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            video_writer.write(frame)

        # Progress reporting (for GUI parsing)
        frame_no += 1
        if frame_no % 50 == 0:
            print(f"Frame {frame_no}/{total_frames}", flush=True)
        if frame_no % 500 == 0:
            elapsed = time.time() - start_time
            pct = frame_no / total_frames * 100
            fps_actual = frame_no / elapsed if elapsed > 0 else 0
            eta = (total_frames - frame_no) / fps_actual if fps_actual > 0 else 0
            print(f"  [{pct:5.1f}%] Frame {frame_no}/{total_frames} | "
                  f"Vehicles: {len(records)} | "
                  f"Speed: {fps_actual:.1f} fps | "
                  f"ETA: {eta/60:.1f} min")

    cap.release()
    if video_writer:
        video_writer.release()

    elapsed = time.time() - start_time

    # --- Save results ----------------------------------------------------
    df = pd.DataFrame(records)
    df.to_csv(config.VEHICLE_COUNTS_CSV, index=False)

    with open(config.TRACK_HISTORY_PATH, "wb") as f:
        pickle.dump(track_history, f)

    print(f"\n{'='*60}")
    print("DETECTION & TRACKING COMPLETE")
    print(f"{'='*60}")
    print(f"  Total frames processed : {frame_no}")
    print(f"  Total vehicles counted : {len(records)}")
    print(f"  Total tracks created   : {len(track_history)}")
    print(f"  Processing time        : {elapsed/60:.1f} min ({elapsed:.0f} sec)")
    print(f"  Effective speed        : {frame_no/elapsed:.1f} fps")
    print(f"\n  Counts CSV : {config.VEHICLE_COUNTS_CSV}")
    print(f"  Track data : {config.TRACK_HISTORY_PATH}")
    if write_video:
        print(f"  Video      : {config.ANNOTATED_VIDEO_PATH}")

    # Quick summary
    if not df.empty:
        print(f"\nVehicle Summary:")
        print(df.groupby(["lane", "vehicle_type"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    write_vid = "--no-video" not in sys.argv
    
    # Set default max frames to 1000. Change this to None to process the whole video.
    max_frames = None
    
    # Still allow overriding via command line if needed
    if "--frames" in sys.argv:
        try:
            idx = sys.argv.index("--frames")
            max_frames = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            print("Warning: Invalid value for --frames. Processing all frames.")
            
    main(write_video=write_vid, max_frames=max_frames)
