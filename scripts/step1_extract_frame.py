"""
step1_extract_frame.py — Extract a still frame from the traffic video.

This frame is used for:
  - Marking Ground Control Points (GCPs)
  - Computing the homography matrix
  - Creating the annotated benchmark image for the report

Usage:
    python step1_extract_frame.py
"""

import cv2
import config

def extract_frame(frame_number=5000):
    """Extract a single frame from the video and save it."""
    print(f"Opening video: {config.VIDEO_PATH}")
    cap = cv2.VideoCapture(config.VIDEO_PATH)

    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {config.VIDEO_PATH}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"  Total frames : {total_frames}")
    print(f"  FPS          : {fps}")
    print(f"  Resolution   : {width} x {height}")
    print(f"  Duration     : {total_frames / fps:.1f} seconds ({total_frames / fps / 60:.1f} min)")

    # Extract frame at given position
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError(f"Failed to read frame {frame_number}")

    cv2.imwrite(config.STILL_FRAME_PATH, frame)
    print(f"\n[OK] Frame {frame_number} saved to: {config.STILL_FRAME_PATH}")
    print(f"  (approximately {frame_number / fps:.1f} seconds into the video)")

    return frame


if __name__ == "__main__":
    extract_frame()
