"""
step3_homography.py — Compute the homography matrix from GCP correspondences.

Reads:
  - output/gcps_pixel.json  (pixel coordinates from step2)
  - output/gcps_world.json  (real-world coordinates you filled in)

Saves:
  - output/homography_matrix.npy

The homography matrix maps pixel coordinates -> real-world coordinates (metres),
correcting for the perspective distortion of the camera.

Usage:
    python step3_homography.py
"""

import json
import numpy as np
import cv2
import config


def load_gcps():
    """Load pixel and world GCP coordinates from JSON files."""
    with open(config.GCPS_PIXEL_PATH, "r") as f:
        pixel_gcps = json.load(f)
    with open(config.GCPS_WORLD_PATH, "r") as f:
        world_gcps = json.load(f)

    if len(pixel_gcps) != len(world_gcps):
        raise ValueError(
            f"Mismatch: {len(pixel_gcps)} pixel GCPs vs {len(world_gcps)} world GCPs. "
            "Each pixel point must have a corresponding world point."
        )

    if len(pixel_gcps) < 4:
        raise ValueError(
            f"Need at least 4 GCP pairs, got {len(pixel_gcps)}. "
            "Go back to step2 and mark more points."
        )

    pixel_pts = np.float32([[g["pixel_x"], g["pixel_y"]] for g in pixel_gcps])
    world_pts = np.float32([[g["world_x"], g["world_y"]] for g in world_gcps])

    return pixel_pts, world_pts, pixel_gcps, world_gcps


def compute_homography(pixel_pts, world_pts):
    """Compute the homography matrix using RANSAC."""
    H, mask = cv2.findHomography(pixel_pts, world_pts, cv2.RANSAC, 5.0)

    if H is None:
        raise RuntimeError("Homography computation failed. Check your GCP points.")

    inliers = mask.ravel().sum()
    total = len(mask)
    print(f"  Inliers: {inliers}/{total}")

    return H, mask


def validate_homography(H, pixel_pts, world_pts):
    """Compute reprojection error to validate the homography."""
    projected = cv2.perspectiveTransform(
        pixel_pts.reshape(-1, 1, 2), H
    ).reshape(-1, 2)

    errors = np.sqrt(np.sum((projected - world_pts) ** 2, axis=1))
    mean_error = np.mean(errors)
    max_error = np.max(errors)

    print(f"\nReprojection Error:")
    print(f"  Mean: {mean_error:.4f} m")
    print(f"  Max:  {max_error:.4f} m")

    for i, err in enumerate(errors):
        status = "[OK]" if err < 1.0 else "[!]"
        print(f"  GCP-{i+1}: {err:.4f} m  {status}")

    if mean_error > 2.0:
        print("\n[!] WARNING: High reprojection error!")
        print("  Your GCP points may be inaccurate. Consider re-measuring.")

    return errors


def main():
    print("=" * 60)
    print("HOMOGRAPHY CALIBRATION")
    print("=" * 60)

    print(f"\nLoading pixel GCPs: {config.GCPS_PIXEL_PATH}")
    print(f"Loading world GCPs: {config.GCPS_WORLD_PATH}")

    pixel_pts, world_pts, pixel_gcps, world_gcps = load_gcps()

    print(f"\nGCP Correspondences ({len(pixel_pts)} points):")
    print(f"  {'ID':<8} {'Pixel (x,y)':<20} {'World (x,y) [m]':<20}")
    print(f"  {'-'*8} {'-'*20} {'-'*20}")
    for i in range(len(pixel_pts)):
        pid = pixel_gcps[i]["id"]
        px, py = pixel_pts[i]
        wx, wy = world_pts[i]
        print(f"  {pid:<8} ({px:.0f}, {py:.0f}){'':<10} ({wx:.2f}, {wy:.2f})")

    print("\nComputing homography matrix...")
    H, mask = compute_homography(pixel_pts, world_pts)

    validate_homography(H, pixel_pts, world_pts)

    # Save
    np.save(config.HOMOGRAPHY_PATH, H)
    print(f"\n[OK] Homography matrix saved to: {config.HOMOGRAPHY_PATH}")

    print("\nHomography Matrix (3×3):")
    print(H)


if __name__ == "__main__":
    main()
