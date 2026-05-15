"""
step2_mark_gcps.py — Interactive tool with three marking modes:
   Mode 1: Mark Ground Control Points (GCPs)
   Mode 2: Draw Road Area polygon (ROI)
   Mode 3: Draw Detection Line

HOW TO USE:
  1. Run this script. A window opens showing the still frame.
  2. Use keyboard shortcuts to switch between modes:
       [1] = GCP mode  |  [2] = Road Area mode  |  [3] = Detection Line mode
  3. In each mode:
       LEFT-CLICK  = add a point
       RIGHT-CLICK = undo the last point
  4. Press ENTER or Q to save everything and quit.
  5. Press ESC to quit without saving.

Outputs:
  - output/gcps_pixel.json     (GCP pixel coordinates)
  - output/road_area.json      (Road polygon vertices)
  - output/detection_line.json (Detection line endpoints)

Usage:
    python step2_mark_gcps.py
"""

import cv2
import json
import os
import numpy as np
import config


# ── Global state ─────────────────────────────────────────────────────────────
frame_display = None
frame_original = None

# Mode 1: GCP points
gcp_points = []

# Mode 2: Road area polygon vertices
road_points = []

# Mode 3: Detection line (exactly 2 points: start and end)
line_points = []

# Current mode: 1 = GCP, 2 = Road Area, 3 = Detection Line
current_mode = 1

MODE_NAMES = {1: "GCP Markers", 2: "Road Area", 3: "Detection Line"}
MODE_COLORS = {
    1: (0, 255, 0),     # Green for GCPs
    2: (255, 200, 0),   # Cyan-ish for Road Area
    3: (0, 0, 255),     # Red for Detection Line
}


# ── Drawing ──────────────────────────────────────────────────────────────────
def redraw():
    """Redraw the frame with all markers from every mode."""
    global frame_display
    frame_display = frame_original.copy()
    h, w = frame_display.shape[:2]

    # --- Draw Road Area polygon (Mode 2) — draw first so it's behind others ---
    if len(road_points) >= 3:
        overlay = frame_display.copy()
        pts = np.array(road_points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(overlay, [pts], (255, 200, 0, 80))
        cv2.addWeighted(overlay, 0.25, frame_display, 0.75, 0, frame_display)
        cv2.polylines(frame_display, [pts], isClosed=True,
                      color=MODE_COLORS[2], thickness=2)
    elif len(road_points) >= 2:
        for i in range(len(road_points) - 1):
            cv2.line(frame_display, road_points[i], road_points[i + 1],
                     MODE_COLORS[2], 2)

    for i, (x, y) in enumerate(road_points):
        cv2.circle(frame_display, (x, y), 6, MODE_COLORS[2], -1)
        cv2.circle(frame_display, (x, y), 8, MODE_COLORS[2], 2)
        cv2.putText(frame_display, f"R{i+1}", (x + 10, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, MODE_COLORS[2], 2)

    # --- Draw Detection Line (Mode 3) ---
    if len(line_points) == 2:
        cv2.line(frame_display, line_points[0], line_points[1],
                 MODE_COLORS[3], 3)
        # Draw arrowheads at both ends
        dx = line_points[1][0] - line_points[0][0]
        dy = line_points[1][1] - line_points[0][1]
        length = np.hypot(dx, dy)
        if length > 0:
            mid_x = (line_points[0][0] + line_points[1][0]) // 2
            mid_y = (line_points[0][1] + line_points[1][1]) // 2
            cv2.putText(frame_display, "DETECTION LINE",
                        (mid_x - 80, mid_y - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, MODE_COLORS[3], 2)

    for i, (x, y) in enumerate(line_points):
        label = "Start" if i == 0 else "End"
        cv2.circle(frame_display, (x, y), 8, MODE_COLORS[3], -1)
        cv2.putText(frame_display, label, (x + 10, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, MODE_COLORS[3], 2)

    # --- Draw GCP points (Mode 1) — draw last so they're on top ---
    for i, (x, y) in enumerate(points_for_mode(1)):
        label = f"GCP-{i + 1}"
        color = MODE_COLORS[1]

        # Draw crosshair
        cv2.drawMarker(frame_display, (x, y), color, cv2.MARKER_CROSS, 20, 2)
        # Draw circle
        cv2.circle(frame_display, (x, y), 8, color, 2)
        # Draw label
        cv2.putText(frame_display, f"{label} ({x},{y})", (x + 12, y - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # --- HUD (bottom bar) ---
    bar_h = 70
    overlay = frame_display.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame_display, 0.35, 0, frame_display)

    mode_color = MODE_COLORS[current_mode]
    mode_name = MODE_NAMES[current_mode]

    lines = [
        f"MODE: {mode_name}  |  [1] GCPs  [2] Road Area  [3] Det. Line  |  ENTER/Q = Save & Quit",
        f"GCPs: {len(gcp_points)}    Road pts: {len(road_points)}    Line pts: {len(line_points)}/2"
        f"    |  LEFT-CLICK = add    RIGHT-CLICK = undo",
    ]
    for j, txt in enumerate(lines):
        y_pos = h - bar_h + 22 + j * 24
        cv2.putText(frame_display, txt, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame_display, txt, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1)

    cv2.imshow("Mark GCPs / Road Area / Detection Line", frame_display)


def points_for_mode(mode):
    """Return the point list for a given mode."""
    if mode == 1:
        return gcp_points
    elif mode == 2:
        return road_points
    elif mode == 3:
        return line_points
    return []


# ── Mouse callback ───────────────────────────────────────────────────────────
def mouse_callback(event, x, y, flags, param):
    """Handle mouse clicks based on current mode."""
    global current_mode

    if event == cv2.EVENT_LBUTTONDOWN:
        if current_mode == 1:
            gcp_points.append((x, y))
            print(f"  [GCP] + GCP-{len(gcp_points)}: pixel ({x}, {y})")

        elif current_mode == 2:
            road_points.append((x, y))
            print(f"  [Road] + Point {len(road_points)}: pixel ({x}, {y})")

        elif current_mode == 3:
            if len(line_points) >= 2:
                # Replace: clear and start over
                line_points.clear()
                print("  [Line] Cleared previous line.")
            line_points.append((x, y))
            label = "Start" if len(line_points) == 1 else "End"
            print(f"  [Line] + {label}: pixel ({x}, {y})")

        redraw()

    elif event == cv2.EVENT_RBUTTONDOWN:
        pts = points_for_mode(current_mode)
        if pts:
            removed = pts.pop()
            mode_label = MODE_NAMES[current_mode]
            print(f"  [{mode_label}] - Removed last point: {removed}")
            redraw()


# ── Save functions ───────────────────────────────────────────────────────────
def save_gcps():
    """Save GCP pixel coordinates to JSON."""
    gcps = [{"id": f"GCP-{i+1}", "pixel_x": x, "pixel_y": y}
            for i, (x, y) in enumerate(gcp_points)]
    with open(config.GCPS_PIXEL_PATH, "w") as f:
        json.dump(gcps, f, indent=2)
    print(f"  [OK] {len(gcp_points)} GCPs saved to: {config.GCPS_PIXEL_PATH}")


def save_road_area():
    """Save road area polygon vertices to JSON."""
    data = {
        "description": "Road area polygon (pixel coordinates, clockwise or counter-clockwise)",
        "vertices": [{"x": x, "y": y} for x, y in road_points]
    }
    with open(config.ROAD_AREA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [OK] {len(road_points)}-point road polygon saved to: {config.ROAD_AREA_PATH}")


def save_detection_line():
    """Save detection line endpoints to JSON and update config."""
    if len(line_points) != 2:
        print(f"  [!] Detection line needs exactly 2 points (got {len(line_points)}). Skipping.")
        return

    data = {
        "description": "Detection line endpoints (pixel coordinates)",
        "start": {"x": line_points[0][0], "y": line_points[0][1]},
        "end":   {"x": line_points[1][0], "y": line_points[1][1]},
    }
    with open(config.DETECTION_LINE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [OK] Detection line saved to: {config.DETECTION_LINE_PATH}")


def create_world_template():
    """Create a template world coordinates file if it doesn't exist."""
    if not os.path.exists(config.GCPS_WORLD_PATH):
        world_template = [
            {"id": f"GCP-{i+1}", "world_x": 0.0, "world_y": 0.0,
             "description": "Fill in real-world X,Y in metres"}
            for i in range(len(gcp_points))
        ]
        with open(config.GCPS_WORLD_PATH, "w") as f:
            json.dump(world_template, f, indent=2)
        print(f"  [OK] Template world coords file created: {config.GCPS_WORLD_PATH}")
        print("       Edit this file with your measured real-world coordinates (metres).")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    global frame_original, current_mode

    print("=" * 60)
    print("INTERACTIVE MARKER TOOL")
    print("  Mode 1: Ground Control Points (GCPs)")
    print("  Mode 2: Road Area Polygon (ROI)")
    print("  Mode 3: Detection Line")
    print("=" * 60)
    print(f"Loading frame: {config.STILL_FRAME_PATH}")

    frame_original = cv2.imread(config.STILL_FRAME_PATH)
    if frame_original is None:
        raise FileNotFoundError(
            f"Still frame not found: {config.STILL_FRAME_PATH}\n"
            "Run step1_extract_frame.py first."
        )

    # Load existing data if available
    _load_existing()

    print("\nControls:")
    print("  • [1]          Switch to GCP mode")
    print("  • [2]          Switch to Road Area mode")
    print("  • [3]          Switch to Detection Line mode")
    print("  • LEFT-CLICK   Add a point in current mode")
    print("  • RIGHT-CLICK  Undo the last point in current mode")
    print("  • ENTER / Q    Save everything and quit")
    print("  • ESC          Quit without saving")
    print()

    win_name = "Mark GCPs / Road Area / Detection Line"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)
    cv2.setMouseCallback(win_name, mouse_callback)
    redraw()

    while True:
        key = cv2.waitKey(0) & 0xFF

        if key == ord('1'):
            current_mode = 1
            print(f"\n>> Switched to Mode 1: {MODE_NAMES[1]}")
            redraw()
        elif key == ord('2'):
            current_mode = 2
            print(f"\n>> Switched to Mode 2: {MODE_NAMES[2]}")
            redraw()
        elif key == ord('3'):
            current_mode = 3
            print(f"\n>> Switched to Mode 3: {MODE_NAMES[3]}")
            redraw()
        elif key in (13, ord('q'), ord('Q')):  # Enter or Q → save & quit
            break
        elif key == 27:  # ESC → quit without saving
            print("\n[!] Quit without saving.")
            cv2.destroyAllWindows()
            return

    cv2.destroyAllWindows()

    # ── Save all data ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SAVING ALL DATA")
    print(f"{'='*60}")

    # GCPs
    if gcp_points:
        save_gcps()
        if len(gcp_points) < 4:
            print(f"  [!] Only {len(gcp_points)} GCPs. You need >= 4 for homography.")
        create_world_template()
    else:
        print("  [!] No GCPs marked. Skipping GCP save.")

    # Road Area
    if len(road_points) >= 3:
        save_road_area()
    elif road_points:
        print(f"  [!] Only {len(road_points)} road points. Need >= 3 for a polygon. Skipping.")
    else:
        print("  [!] No road area marked. Skipping.")

    # Detection Line
    if line_points:
        save_detection_line()
    else:
        print("  [!] No detection line marked. Skipping.")

    print(f"\n{'='*60}")
    print("Done! Next steps:")
    print("  1. Edit world coordinates in gcps_world.json (if needed)")
    print("  2. Run step3_homography.py")
    print(f"{'='*60}")


def _load_existing():
    """Load previously saved data so the user can refine it."""
    global gcp_points, road_points, line_points

    # Load existing GCPs
    if os.path.exists(config.GCPS_PIXEL_PATH):
        try:
            with open(config.GCPS_PIXEL_PATH) as f:
                data = json.load(f)
            gcp_points[:] = [(p["pixel_x"], p["pixel_y"]) for p in data]
            print(f"  Loaded {len(gcp_points)} existing GCPs from {config.GCPS_PIXEL_PATH}")
        except Exception as e:
            print(f"  [!] Could not load existing GCPs: {e}")

    # Load existing road area
    if os.path.exists(config.ROAD_AREA_PATH):
        try:
            with open(config.ROAD_AREA_PATH) as f:
                data = json.load(f)
            road_points[:] = [(v["x"], v["y"]) for v in data["vertices"]]
            print(f"  Loaded {len(road_points)} road area points from {config.ROAD_AREA_PATH}")
        except Exception as e:
            print(f"  [!] Could not load existing road area: {e}")

    # Load existing detection line
    if os.path.exists(config.DETECTION_LINE_PATH):
        try:
            with open(config.DETECTION_LINE_PATH) as f:
                data = json.load(f)
            line_points[:] = [
                (data["start"]["x"], data["start"]["y"]),
                (data["end"]["x"], data["end"]["y"]),
            ]
            print(f"  Loaded detection line from {config.DETECTION_LINE_PATH}")
        except Exception as e:
            print(f"  [!] Could not load existing detection line: {e}")


if __name__ == "__main__":
    main()
