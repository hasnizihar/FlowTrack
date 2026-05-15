"""
run_all.py — Master Runner for CE3163 Traffic Analysis Pipeline

Runs the full analysis pipeline (steps 5 -> 6 -> 7 -> 8) sequentially.

Prerequisites:
  - You must have already completed the calibration steps:
      1. python step1_extract_frame.py     (extract a still frame)
      2. python step2_mark_gcps.py         (mark GCPs interactively)
      3. Edit output/gcps_world.json       (fill in real-world coordinates)
      4. python step3_homography.py        (compute homography matrix)
      5. python step4_annotate_frame.py    (create annotated image)

Usage:
    python run_all.py              # Full run with annotated video
    python run_all.py --no-video   # Skip annotated video (faster)
"""

import time
import sys


def run_step(step_name, module_name, func_name="main", **kwargs):
    """Run a pipeline step with timing and error handling."""
    print(f"\n{'#' * 70}")
    print(f"# STEP: {step_name}")
    print(f"{'#' * 70}\n")

    start = time.time()
    try:
        module = __import__(module_name)
        func = getattr(module, func_name)
        func(**kwargs)
        elapsed = time.time() - start
        print(f"\n[OK] {step_name} completed in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[FAIL] {step_name} FAILED after {elapsed:.1f}s")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("  CE3163 TRAFFIC ANALYSIS PIPELINE — FULL RUN")
    print("  Piliyandala, Sri Lanka | 01 May 2026 | 08:57–09:58 AM")
    print("=" * 70)

    write_video = "--no-video" not in sys.argv

    if write_video:
        print("\n  Mode: Full (with annotated video output)")
    else:
        print("\n  Mode: Fast (no annotated video)")

    overall_start = time.time()

    # Step 5: Detection & Tracking
    ok = run_step(
        "Vehicle Detection & Tracking",
        "step5_detect_track",
        write_video=write_video,
    )
    if not ok:
        print("\n[!] Pipeline aborted due to detection failure.")
        return

    # Step 6: Speed Estimation
    run_step("Speed Estimation", "step6_speed")

    # Step 7: Traffic Parameters
    run_step("Traffic Parameter Extraction", "step7_traffic_params")

    # Step 8: Plots
    run_step("Plot Generation", "step8_plots")

    # -- Summary --
    overall_elapsed = time.time() - overall_start
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Total time: {overall_elapsed/60:.1f} minutes ({overall_elapsed:.0f} seconds)")
    print(f"{'=' * 70}")

    print(f"\nOutput files are in: output/")
    print("  • vehicle_counts.csv       — Raw detection records")
    print("  • vehicle_speeds.csv       — Speed per vehicle")
    print("  • flow_1min/5min/10min.csv — Flow rates")
    print("  • composition.csv          — Vehicle type breakdown")
    print("  • speed_stats.csv          — Speed statistics")
    print("  • flow_plot_*.png          — Flow rate charts")
    print("  • composition_pie.png      — Composition pie chart")
    print("  • composition_bar.png      — Composition bar chart")
    print("  • speed_histograms.png     — Speed distributions")
    print("  • speed_boxplot.png        — Speed box plots")
    if write_video:
        print("  • annotated_output.mp4   — Video with bounding boxes")


if __name__ == "__main__":
    main()
