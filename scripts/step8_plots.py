"""
step8_plots.py — Generate Publication-Quality Traffic Analysis Plots

Creates (each as a separate PNG):
  1. Flow rate vs Time (line plots for 1, 5, 10-min intervals)
  2. Vehicle Composition — Pie chart (overall)
  3. Vehicle Composition — Bar chart (per lane)
  4. Speed Histogram — one SEPARATE file per vehicle type
  5. Speed Box Plot (comparative across types)

All plots are saved as 150 DPI PNGs in the output directory.

Usage:
    python step8_plots.py
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import config


# ---------- Colour Palette ------------------------------------------------
# One distinct colour per vehicle type (ordered as in config.VEHICLE_TYPES)
TYPE_COLORS = {
    "Motorcycle":           "#FF9800",
    "Three-Wheeler":        "#4CAF50",
    "Car":                  "#2196F3",
    "Van":                  "#9C27B0",
    "Light Goods Vehicle":  "#00BCD4",
    "Bus":                  "#F44336",
    "Heavy Goods Vehicle":  "#795548",
}

LANE_COLORS  = {"Lane 1": "#2196F3", "Lane 2": "#FF5722"}
LANE_MARKERS = {"Lane 1": "o",       "Lane 2": "s"}


def setup_style():
    """Set up consistent plot styling."""
    try:
        plt.style.use(config.PLOT_STYLE)
    except OSError:
        try:
            plt.style.use("seaborn-v0_8")
        except Exception:
            pass  # Use default style

    plt.rcParams.update({
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "figure.titlesize": 16,
    })


# ========================================================================= #
#  1.  FLOW RATE PLOTS  (already separate per interval)                     #
# ========================================================================= #
def plot_flow_rates():
    """Generate flow rate vs time plots for each interval."""
    print("\n-- Flow Rate Plots --")

    for interval in config.FLOW_INTERVALS:
        csv_path = config.flow_csv_path(interval)
        try:
            flow = pd.read_csv(csv_path)
        except FileNotFoundError:
            print(f"  [!] Missing: {csv_path}")
            continue

        fig, ax = plt.subplots(figsize=(14, 5))

        for lane in sorted(flow["lane"].unique()):
            sub = flow[flow["lane"] == lane]
            color  = LANE_COLORS.get(lane, "#333333")
            marker = LANE_MARKERS.get(lane, "^")
            ax.plot(sub["time_min"], sub["flow_rate_veh_hr"],
                    label=lane, marker=marker, markersize=4,
                    linewidth=1.5, color=color, alpha=0.9)

        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel("Flow Rate (vehicles/hour)")
        ax.set_title(f"Traffic Flow Rate — {interval}-Minute Intervals\n"
                     f"Piliyandala, Sri Lanka | 01 May 2026 | 08:57–09:58 AM")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        out_path = config.flow_plot_path(interval)
        plt.savefig(out_path, dpi=config.PLOT_DPI, bbox_inches="tight")
        plt.close()
        print(f"  [OK] {out_path}")


# ========================================================================= #
#  2.  COMPOSITION — PIE CHART  (separate file)                             #
# ========================================================================= #
def plot_composition_pie():
    """Generate overall vehicle composition pie chart."""
    print("\n-- Composition Pie Chart --")

    try:
        comp = pd.read_csv(config.COMPOSITION_CSV)
    except FileNotFoundError:
        print("  [!] Missing: composition.csv")
        return

    overall = comp.groupby("vehicle_type")["count"].sum().sort_values(ascending=False)

    colors = [TYPE_COLORS.get(vt, "#999") for vt in overall.index]
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        overall, labels=overall.index, autopct="%1.1f%%",
        startangle=140, colors=colors,
        pctdistance=0.85, wedgeprops=dict(linewidth=2, edgecolor="white")
    )
    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")

    ax.set_title("Vehicle Composition (Overall)\n"
                 "Piliyandala, Sri Lanka | 01 May 2026",
                 fontsize=14, fontweight="bold")

    # Donut centre
    centre_circle = plt.Circle((0, 0), 0.55, fc="white")
    ax.add_artist(centre_circle)
    ax.text(0, 0, f"Total\n{overall.sum()}", ha="center", va="center",
            fontsize=16, fontweight="bold")

    plt.tight_layout()
    plt.savefig(config.COMPOSITION_PIE_PATH, dpi=config.PLOT_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {config.COMPOSITION_PIE_PATH}")


# ========================================================================= #
#  3.  COMPOSITION — BAR CHART  (separate file)                             #
# ========================================================================= #
def plot_composition_bar():
    """Generate vehicle composition bar chart by lane."""
    print("\n-- Composition Bar Chart --")

    try:
        comp = pd.read_csv(config.COMPOSITION_CSV)
    except FileNotFoundError:
        print("  [!] Missing: composition.csv")
        return

    pivot = comp.pivot_table(index="vehicle_type", columns="lane",
                             values="count", fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(pivot.index))
    bar_width = 0.35

    for i, lane in enumerate(pivot.columns):
        bars = ax.bar(x + i * bar_width, pivot[lane], bar_width,
                      label=lane, color=LANE_COLORS.get(lane, "#999"),
                      edgecolor="white", linewidth=0.5)
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, height + 1,
                        f"{int(height)}", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Vehicle Type")
    ax.set_ylabel("Count")
    ax.set_title("Vehicle Composition by Lane\n"
                 "Piliyandala, Sri Lanka | 01 May 2026")
    ax.set_xticks(x + bar_width / 2)
    ax.set_xticklabels(pivot.index, rotation=25, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(config.COMPOSITION_BAR_PATH, dpi=config.PLOT_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {config.COMPOSITION_BAR_PATH}")


# ========================================================================= #
#  4.  SPEED HISTOGRAMS — one SEPARATE PNG per vehicle type                 #
# ========================================================================= #
def plot_speed_histograms():
    """Generate a separate speed-distribution histogram for each vehicle type."""
    print("\n-- Speed Histograms (separate per type) --")

    try:
        speed_df = pd.read_csv(config.VEHICLE_SPEEDS_CSV)
    except FileNotFoundError:
        print("  [!] Missing: vehicle_speeds.csv")
        return

    if speed_df.empty:
        print("  [!] No speed data.")
        return

    vtypes = sorted(speed_df["vehicle_type"].unique())
    if not vtypes:
        print("  [!] No vehicle types found.")
        return

    for vt in vtypes:
        data = speed_df[speed_df["vehicle_type"] == vt]["speed_kmh"].dropna()
        if data.empty:
            continue

        color = TYPE_COLORS.get(vt, "#607D8B")
        n     = len(data)
        mean  = data.mean()
        med   = data.median()
        std   = data.std()

        fig, ax = plt.subplots(figsize=(8, 5))

        n_bins = min(30, max(8, n // 5))
        ax.hist(data, bins=n_bins, edgecolor="white", color=color,
                alpha=0.85, zorder=3)

        # Mean & median lines
        ax.axvline(mean, color="#D32F2F", linestyle="--", linewidth=1.8,
                   label=f"Mean: {mean:.1f} km/h", zorder=4)
        ax.axvline(med,  color="#1565C0", linestyle=":",  linewidth=1.8,
                   label=f"Median: {med:.1f} km/h", zorder=4)

        # Stats text box
        stats_text = (f"n = {n}\n"
                      f"μ = {mean:.1f} km/h\n"
                      f"σ = {std:.1f} km/h\n"
                      f"Min = {data.min():.1f}\n"
                      f"Max = {data.max():.1f}")
        ax.text(0.97, 0.95, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment="top", horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#ccc", alpha=0.9))

        ax.set_title(f"Speed Distribution — {vt}\n"
                     f"Piliyandala, Sri Lanka | 01 May 2026",
                     fontweight="bold")
        ax.set_xlabel("Speed (km/h)")
        ax.set_ylabel("Frequency (number of vehicles)")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(axis="y", alpha=0.3, zorder=0)

        plt.tight_layout()
        safe_name = vt.lower().replace(" ", "_").replace("-", "")
        out_path = os.path.join(config.OUTPUT_DIR,
                                f"speed_hist_{safe_name}.png")
        plt.savefig(out_path, dpi=config.PLOT_DPI, bbox_inches="tight")
        plt.close()
        print(f"  [OK] {out_path}")

    # --- Also save the combined panel (for quick overview) ---
    _plot_speed_histograms_combined(speed_df, vtypes)


def _plot_speed_histograms_combined(speed_df, vtypes):
    """Save a single combined panel of all speed histograms."""
    n_types = len(vtypes)
    cols = min(n_types, 4)
    rows = (n_types + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4.5 * rows))
    axes_flat = np.array(axes).flatten() if n_types > 1 else [axes]

    for i, vt in enumerate(vtypes):
        ax = axes_flat[i]
        data = speed_df[speed_df["vehicle_type"] == vt]["speed_kmh"].dropna()
        color = TYPE_COLORS.get(vt, "#607D8B")

        n_bins = min(25, max(6, len(data) // 5))
        ax.hist(data, bins=n_bins, edgecolor="white", color=color, alpha=0.85)

        mean_val = data.mean()
        ax.axvline(mean_val, color="#D32F2F", linestyle="--", linewidth=1.5,
                   label=f"Mean: {mean_val:.1f}")

        ax.set_title(f"{vt}", fontweight="bold", fontsize=11)
        ax.set_xlabel("Speed (km/h)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    # Hide unused axes
    for j in range(n_types, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("Speed Distribution by Vehicle Type\n"
                 "Piliyandala, Sri Lanka | 01 May 2026",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(config.SPEED_HISTOGRAM_PATH, dpi=config.PLOT_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {config.SPEED_HISTOGRAM_PATH}  (combined panel)")


# ========================================================================= #
#  5.  SPEED BOX PLOT  (separate file)                                      #
# ========================================================================= #
def plot_speed_boxplot():
    """Generate comparative box plot of speeds across vehicle types."""
    print("\n-- Speed Box Plot --")

    try:
        speed_df = pd.read_csv(config.VEHICLE_SPEEDS_CSV)
    except FileNotFoundError:
        print("  [!] Missing: vehicle_speeds.csv")
        return

    if speed_df.empty:
        print("  [!] No speed data.")
        return

    vtypes = sorted(speed_df["vehicle_type"].unique())
    data_by_type = [speed_df[speed_df["vehicle_type"] == vt]["speed_kmh"].dropna().values
                    for vt in vtypes]

    fig, ax = plt.subplots(figsize=(12, 6))

    bp = ax.boxplot(data_by_type, tick_labels=vtypes, patch_artist=True,
                    showmeans=True, meanline=True,
                    meanprops=dict(color="#D32F2F", linewidth=1.5),
                    medianprops=dict(color="black", linewidth=1.5),
                    flierprops=dict(marker=".", markersize=3, alpha=0.4))

    for patch, vt in zip(bp["boxes"], vtypes):
        patch.set_facecolor(TYPE_COLORS.get(vt, "#999"))
        patch.set_alpha(0.65)

    ax.set_xlabel("Vehicle Type")
    ax.set_ylabel("Speed (km/h)")
    ax.set_title("Speed Comparison by Vehicle Type\n"
                 "Piliyandala, Sri Lanka | 01 May 2026")
    ax.grid(axis="y", alpha=0.3)

    # Add sample sizes
    y_low = ax.get_ylim()[0]
    for i, (vt, d) in enumerate(zip(vtypes, data_by_type)):
        ax.text(i + 1, y_low - 2, f"n={len(d)}",
                ha="center", va="top", fontsize=9, color="gray")

    ax.set_xticklabels(vtypes, rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(config.SPEED_BOXPLOT_PATH, dpi=config.PLOT_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {config.SPEED_BOXPLOT_PATH}")


# ========================================================================= #
#  MAIN                                                                     #
# ========================================================================= #
def main():
    print("=" * 60)
    print("GENERATING PLOTS")
    print("=" * 60)

    setup_style()

    plot_flow_rates()
    plot_composition_pie()
    plot_composition_bar()
    plot_speed_histograms()
    plot_speed_boxplot()

    print(f"\n{'='*60}")
    print("ALL PLOTS GENERATED")
    print(f"{'='*60}")
    print(f"Output directory: {config.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
