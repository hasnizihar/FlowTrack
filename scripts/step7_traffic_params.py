"""
step7_traffic_params.py — Extract Traffic Parameters

Reads vehicle_counts.csv and vehicle_speeds.csv to compute:
  1. Flow rates at 1, 5, and 10-minute intervals (per lane)
  2. Vehicle composition (count + percentage by type, per lane)
  3. Speed statistics (mean, std, min, max, percentiles) by type and lane

Usage:
    python step7_traffic_params.py
"""

import pandas as pd
import numpy as np
import config


def compute_flow_rates(df):
    """Compute flow rates at different time intervals."""
    df = df.copy()
    df["timestamp_min"] = df["timestamp_sec"] / 60.0

    for interval in config.FLOW_INTERVALS:
        df[f"interval"] = (df["timestamp_min"] // interval * interval).astype(int)

        # Count vehicles per lane per interval
        flow = df.groupby(["lane", "interval"]).size().reset_index(name="count")
        flow.rename(columns={"interval": f"time_min"}, inplace=True)

        # Convert to vehicles per hour
        flow["flow_rate_veh_hr"] = flow["count"] * (60 / interval)

        # Save
        out_path = config.flow_csv_path(interval)
        flow.to_csv(out_path, index=False)
        print(f"  [OK] {interval}-min flow rates -> {out_path}")

        # Summary
        for lane in sorted(flow["lane"].unique()):
            sub = flow[flow["lane"] == lane]["flow_rate_veh_hr"]
            print(f"    {lane}: mean={sub.mean():.0f}, max={sub.max():.0f} veh/hr")

        df.drop(columns=["interval"], inplace=True)


def compute_composition(df):
    """Compute vehicle type composition."""
    # Per-lane composition
    composition = df.groupby(["lane", "vehicle_type"]).size().reset_index(name="count")
    total = df.shape[0]
    composition["percentage"] = (composition["count"] / total * 100).round(2)

    # Add lane totals
    lane_totals = df.groupby("lane").size().reset_index(name="lane_total")
    composition = composition.merge(lane_totals, on="lane")
    composition["lane_percentage"] = (
        composition["count"] / composition["lane_total"] * 100
    ).round(2)
    composition.drop(columns=["lane_total"], inplace=True)

    composition.to_csv(config.COMPOSITION_CSV, index=False)
    print(f"  [OK] Composition -> {config.COMPOSITION_CSV}")

    # Print summary
    print("\n  Vehicle Composition:")
    print(f"  {'Lane':<10} {'Type':<15} {'Count':>6} {'%':>8} {'Lane%':>8}")
    print(f"  {'-'*10} {'-'*15} {'-'*6} {'-'*8} {'-'*8}")
    for _, row in composition.iterrows():
        print(f"  {row['lane']:<10} {row['vehicle_type']:<15} "
              f"{row['count']:>6} {row['percentage']:>7.1f}% {row['lane_percentage']:>7.1f}%")


def compute_speed_stats(speed_df):
    """Compute speed statistics by vehicle type and lane."""
    stats = speed_df.groupby(["lane", "vehicle_type"])["speed_kmh"].agg(
        count="count",
        mean="mean",
        std="std",
        min="min",
        q25=lambda x: x.quantile(0.25),
        median="median",
        q75=lambda x: x.quantile(0.75),
        max="max",
    ).round(2).reset_index()

    stats.to_csv(config.SPEED_STATS_CSV, index=False)
    print(f"  [OK] Speed stats -> {config.SPEED_STATS_CSV}")

    # Print summary
    print("\n  Speed Statistics (km/h):")
    print(f"  {'Lane':<10} {'Type':<15} {'n':>5} {'Mean':>7} {'Std':>7} "
          f"{'Min':>7} {'Q25':>7} {'Med':>7} {'Q75':>7} {'Max':>7}")
    print(f"  {'-'*10} {'-'*15} {'-'*5} {'-'*7} {'-'*7} "
          f"{'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for _, row in stats.iterrows():
        print(f"  {row['lane']:<10} {row['vehicle_type']:<15} "
              f"{row['count']:>5.0f} {row['mean']:>7.1f} {row['std']:>7.1f} "
              f"{row['min']:>7.1f} {row['q25']:>7.1f} {row['median']:>7.1f} "
              f"{row['q75']:>7.1f} {row['max']:>7.1f}")


def main():
    print("=" * 60)
    print("TRAFFIC PARAMETER EXTRACTION")
    print("=" * 60)

    # Load data
    print(f"\nLoading: {config.VEHICLE_COUNTS_CSV}")
    df = pd.read_csv(config.VEHICLE_COUNTS_CSV)
    print(f"  Records: {len(df)}")

    if df.empty:
        print("[!] No vehicle count data. Run step5 first.")
        return

    # 1. Flow rates
    print(f"\n-- Flow Rates --")
    compute_flow_rates(df)

    # 2. Composition
    print(f"\n-- Vehicle Composition --")
    compute_composition(df)

    # 3. Speed stats
    print(f"\n-- Speed Statistics --")
    try:
        speed_df = pd.read_csv(config.VEHICLE_SPEEDS_CSV)
        print(f"  Speed records: {len(speed_df)}")
        if not speed_df.empty:
            compute_speed_stats(speed_df)
        else:
            print("  [!] No speed data available.")
    except FileNotFoundError:
        print(f"  [!] Speed file not found: {config.VEHICLE_SPEEDS_CSV}")
        print("    Run step6_speed.py first.")

    print(f"\n{'='*60}")
    print("TRAFFIC PARAMETER EXTRACTION COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
