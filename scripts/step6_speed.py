"""
step6_speed.py — Speed Estimation from Tracked Vehicle Positions

Reads the track history (pickled from step5) and computes:
  - Frame-to-frame displacement in real-world metres
  - Instantaneous speed for each segment
  - Mean speed per vehicle (with outlier filtering)

Saves: output/vehicle_speeds.csv

Usage:
    python step6_speed.py
"""

import pickle
import numpy as np
import pandas as pd
import cv2
import config


def compute_speeds(track_history, fps):
    """Compute speed for each tracked vehicle."""
    speed_records = []

    for tid, data in track_history.items():
        positions = data["positions"]
        if len(positions) < 2:
            continue

        # Calculate instantaneous speeds between consecutive positions
        inst_speeds = []
        for i in range(1, len(positions)):
            f0, x0, y0 = positions[i - 1]
            f1, x1, y1 = positions[i]
            dt = (f1 - f0) / fps  # seconds
            dist = np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)  # metres

            if dt > 0:
                speed_ms = dist / dt
                # Filter out unrealistic speeds (> 200 km/h or < 0.5 km/h)
                speed_kmh = speed_ms * 3.6
                if 0.5 < speed_kmh < 200:
                    inst_speeds.append(speed_ms)

        if not inst_speeds:
            continue

        # Use median instead of mean to reduce outlier impact
        speed_ms_median = np.median(inst_speeds)
        speed_ms_mean = np.mean(inst_speeds)
        speed_kmh_median = speed_ms_median * 3.6
        speed_kmh_mean = speed_ms_mean * 3.6

        speed_records.append({
            "track_id": tid,
            "vehicle_type": data["type"],
            "lane": data["lane"],
            "speed_kmh": round(speed_kmh_median, 2),
            "speed_kmh_mean": round(speed_kmh_mean, 2),
            "num_positions": len(positions),
            "num_speed_samples": len(inst_speeds),
        })

    return speed_records


def main():
    print("=" * 60)
    print("SPEED ESTIMATION")
    print("=" * 60)

    # Load track history
    print(f"\nLoading track history: {config.TRACK_HISTORY_PATH}")
    with open(config.TRACK_HISTORY_PATH, "rb") as f:
        track_history = pickle.load(f)
    print(f"  Loaded {len(track_history)} tracks")

    # Get FPS from video
    cap = cv2.VideoCapture(config.VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or config.FALLBACK_FPS
    cap.release()
    print(f"  Video FPS: {fps}")

    # Compute speeds
    print("\nComputing speeds...")
    speed_records = compute_speeds(track_history, fps)
    speed_df = pd.DataFrame(speed_records)

    if speed_df.empty:
        print("\n[!] No speed data computed. Check your track history.")
        return

    speed_df.to_csv(config.VEHICLE_SPEEDS_CSV, index=False)

    print(f"\n[OK] Speed data saved to: {config.VEHICLE_SPEEDS_CSV}")
    print(f"  Vehicles with speed data: {len(speed_df)}")

    # Summary statistics
    print(f"\nSpeed Summary (km/h):")
    print(f"  {'Type':<15} {'Count':>6} {'Mean':>8} {'Median':>8} {'Min':>8} {'Max':>8}")
    print(f"  {'-'*15} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for vtype in sorted(speed_df["vehicle_type"].unique()):
        sub = speed_df[speed_df["vehicle_type"] == vtype]["speed_kmh"]
        print(f"  {vtype:<15} {len(sub):>6} {sub.mean():>8.1f} {sub.median():>8.1f} "
              f"{sub.min():>8.1f} {sub.max():>8.1f}")

    overall = speed_df["speed_kmh"]
    print(f"  {'OVERALL':<15} {len(overall):>6} {overall.mean():>8.1f} {overall.median():>8.1f} "
          f"{overall.min():>8.1f} {overall.max():>8.1f}")

    # Per-lane summary
    print(f"\nBy Lane:")
    for lane in sorted(speed_df["lane"].unique()):
        sub = speed_df[speed_df["lane"] == lane]["speed_kmh"]
        print(f"  {lane}: mean={sub.mean():.1f}, median={sub.median():.1f}, "
              f"n={len(sub)}")


if __name__ == "__main__":
    main()
