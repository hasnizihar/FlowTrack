"""
results_manager.py — Loads all output files and provides them to the Results and Dashboard screens.
"""

from pathlib import Path
from typing import Optional
import pandas as pd


class ResultsManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def load_composition(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "composition.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_speeds(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "vehicle_speeds.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_counts(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "vehicle_counts.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_flow(self, interval: int = 5) -> Optional[pd.DataFrame]:
        p = self.output_dir / f"flow_{interval}min.csv"
        return pd.read_csv(p) if p.exists() else None

    def load_speed_stats(self) -> Optional[pd.DataFrame]:
        p = self.output_dir / "speed_stats.csv"
        return pd.read_csv(p) if p.exists() else None

    def get_chart_paths(self) -> dict:
        names = [
            "flow_plot_5min", "composition_pie",
            "speed_histograms", "composition_bar", "speed_boxplot",
            "flow_plot_1min", "flow_plot_10min",
        ]
        return {
            name: self.output_dir / f"{name}.png"
            for name in names
        }

    def get_summary_stats(self) -> dict:
        stats = {}
        df = self.load_speeds()
        if df is not None and "speed_kmh" in df.columns:
            s = df["speed_kmh"]
            stats["speed_mean"] = round(s.mean(), 1)
            stats["speed_std"] = round(s.std(), 1)
            stats["speed_85pct"] = round(s.quantile(0.85), 1)
            stats["speed_max"] = round(s.max(), 1)

        df = self.load_flow(1)
        if df is not None:
            flow_col = [c for c in df.columns if "flow" in c.lower() or "veh" in c.lower()]
            if flow_col:
                stats["peak_flow"] = int(df[flow_col[0]].max())

        counts_path = self.output_dir / "vehicle_counts.csv"
        if counts_path.exists():
            try:
                stats["total_vehicles"] = len(pd.read_csv(counts_path))
            except Exception:
                pass
        return stats
