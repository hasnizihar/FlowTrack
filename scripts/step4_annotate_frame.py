"""
step4_annotate_frame.py — Create an annotated benchmark image for the report.

Draws GCP markers, labels, measured distances, lane boundaries,
road area polygon, and detection line on the still frame.
This image goes into the Methodology section.

Usage:
    python step4_annotate_frame.py
"""

import cv2
import json
import os
import numpy as np
import config


def main():
    print("=" * 60)
    print("ANNOTATED BENCHMARK IMAGE")
    print("=" * 60)

    # Load frame
    frame = cv2.imread(config.STILL_FRAME_PATH)
    if frame is None:
        raise FileNotFoundError(f"Still frame not found: {config.STILL_FRAME_PATH}")

    # Load GCPs
    with open(config.GCPS_PIXEL_PATH, "r") as f:
        pixel_gcps = json.load(f)
    with open(config.GCPS_WORLD_PATH, "r") as f:
        world_gcps = json.load(f)

    h, w = frame.shape[:2]

    # --- Draw road area polygon (semi-transparent) -----------------------
    if os.path.exists(config.ROAD_AREA_PATH):
        with open(config.ROAD_AREA_PATH, "r") as f:
            road_data = json.load(f)
        road_pts = np.array(
            [(v["x"], v["y"]) for v in road_data["vertices"]], dtype=np.int32
        )
        # Semi-transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [road_pts.reshape((-1, 1, 2))], (255, 200, 0))
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        # Polygon outline
        cv2.polylines(frame, [road_pts.reshape((-1, 1, 2))],
                      isClosed=True, color=(255, 200, 0), thickness=2)
        # Label each vertex
        for i, (vx, vy) in enumerate(road_pts):
            cv2.circle(frame, (vx, vy), 5, (255, 200, 0), -1)
            cv2.putText(frame, f"R{i+1}", (vx + 8, vy - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
        cv2.putText(frame, "ROAD AREA", (road_pts[0][0] + 10, road_pts[0][1] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2)
        print(f"  Road area drawn ({len(road_pts)} vertices)")
    else:
        print("  [--] No road_area.json found. Skipping road area overlay.")

    # --- Draw detection line ----------------------------------------------
    if os.path.exists(config.DETECTION_LINE_PATH):
        with open(config.DETECTION_LINE_PATH, "r") as f:
            line_data = json.load(f)
        det_start = (line_data["start"]["x"], line_data["start"]["y"])
        det_end = (line_data["end"]["x"], line_data["end"]["y"])
        print(f"  Detection line loaded: {det_start} -> {det_end}")
    else:
        # Fallback: horizontal line at configured Y or frame center
        det_y = config.DETECTION_LINE_Y or h // 2
        det_start = (0, det_y)
        det_end = (w, det_y)
        print(f"  [--] No detection_line.json. Using horizontal line at y={det_y}")

    cv2.line(frame, det_start, det_end, (0, 0, 255), 2)
    # Label at midpoint of the line
    mid_x = (det_start[0] + det_end[0]) // 2
    mid_y = (det_start[1] + det_end[1]) // 2
    cv2.putText(frame, "DETECTION LINE", (mid_x - 80, mid_y - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    # Start / End labels
    cv2.circle(frame, det_start, 6, (0, 0, 255), -1)
    cv2.circle(frame, det_end, 6, (0, 0, 255), -1)

    # --- Draw GCP markers ------------------------------------------------
    colors = [
        (0, 255, 0),    # green
        (255, 0, 0),    # blue
        (0, 255, 255),  # yellow
        (255, 0, 255),  # magenta
        (255, 165, 0),  # orange
        (0, 128, 255),  # orange-red
        (128, 0, 255),  # purple
    ]

    for i, (pg, wg) in enumerate(zip(pixel_gcps, world_gcps)):
        px, py = int(pg["pixel_x"]), int(pg["pixel_y"])
        wx, wy = wg["world_x"], wg["world_y"]
        color = colors[i % len(colors)]

        # Crosshair marker
        cv2.drawMarker(frame, (px, py), color, cv2.MARKER_CROSS, 25, 2)
        cv2.circle(frame, (px, py), 10, color, 2)

        # Label with world coordinates
        label = f"{pg['id']} ({wx:.1f}m, {wy:.1f}m)"
        cv2.putText(frame, label, (px + 15, py - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # --- Draw distance lines between consecutive GCPs --------------------
    for i in range(len(pixel_gcps) - 1):
        p1 = (int(pixel_gcps[i]["pixel_x"]), int(pixel_gcps[i]["pixel_y"]))
        p2 = (int(pixel_gcps[i+1]["pixel_x"]), int(pixel_gcps[i+1]["pixel_y"]))
        w1 = np.array([world_gcps[i]["world_x"], world_gcps[i]["world_y"]])
        w2 = np.array([world_gcps[i+1]["world_x"], world_gcps[i+1]["world_y"]])

        dist = np.linalg.norm(w2 - w1)
        mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)

        cv2.line(frame, p1, p2, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"{dist:.1f}m", (mid[0] + 5, mid[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # --- Lane labels -----------------------------------------------------
    cv2.putText(frame, f"LANE 1 ({config.LANE_1_WIDTH_M:.0f}m - 3 sub-lanes)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"LANE 2 ({config.LANE_2_WIDTH_M:.0f}m - 2 sub-lanes)",
                (w // 2, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    # --- Vehicle type colour legend --------------------------------------
    legend_x = w - 260
    legend_y_start = 50
    cv2.putText(frame, "Vehicle Colors:", (legend_x, legend_y_start - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    for j, (vtype, color) in enumerate(config.VEHICLE_COLORS.items()):
        y_pos = legend_y_start + j * 22 + 10
        cv2.rectangle(frame, (legend_x, y_pos - 12), (legend_x + 16, y_pos + 4), color, -1)
        cv2.putText(frame, vtype, (legend_x + 22, y_pos + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    # --- Site info overlay -----------------------------------------------
    info_lines = [
        "CE3163 Assignment 03 - Benchmark Image",
        "GPS: 6.7115N, 79.9075E | Piliyandala, Sri Lanka",
        "Date: 01 May 2026 | 08:57 - 09:58 AM",
        f"Total Road Width: {config.TOTAL_ROAD_WIDTH_M:.0f}m",
    ]
    for j, txt in enumerate(info_lines):
        y_pos = h - 80 + j * 20
        cv2.putText(frame, txt, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, txt, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # Save
    cv2.imwrite(config.ANNOTATED_FRAME_PATH, frame)
    print(f"\n[OK] Annotated benchmark image saved to: {config.ANNOTATED_FRAME_PATH}")


if __name__ == "__main__":
    main()
