#!/usr/bin/env python3
"""Plot paired real-LLM replication results from sanitized CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


MODES = ["central_baseline", "agent_profile", "llm_agent_proxy", "llm_agent_real"]
LABELS = {
    "central_baseline": "Central",
    "agent_profile": "Agent profile",
    "llm_agent_proxy": "LLM proxy",
    "llm_agent_real": "Real LLM",
}
COLORS = {
    "central_baseline": "#767676",
    "agent_profile": "#4F8A55",
    "llm_agent_proxy": "#D17C55",
    "llm_agent_real": "#0F4D92",
}
MARKERS = {
    "central_baseline": "o",
    "agent_profile": "s",
    "llm_agent_proxy": "^",
    "llm_agent_real": "D",
}


def read_metric(path: Path, metric: str) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["mode"]: float(row[metric]) for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7,
            "axes.linewidth": 0.8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    run_dirs = sorted(args.results_dir.glob("run_*_seed*"))
    if len(run_dirs) != 3:
        raise RuntimeError(f"Expected three run directories, found {len(run_dirs)}")
    seeds = [path.name.rsplit("seed", 1)[1] for path in run_dirs]
    specifications = [
        ("lightweight_metrics.csv", "resource_distribution_distance", "Resource identity distance"),
        ("formal_distances.csv", "cycle_time_wass", "Cycle-time Wasserstein"),
        ("formal_distances.csv", "workforce_emd", "Workforce EMD"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35))
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.21, top=0.73, wspace=0.17)
    for panel_index, (panel, (filename, metric, title)) in enumerate(zip(axes, specifications)):
        values = [read_metric(path / filename, metric) for path in run_dirs]
        for mode in MODES:
            panel.plot(
                seeds,
                [run[mode] for run in values],
                marker=MARKERS[mode],
                markersize=4,
                linewidth=1.4 if mode == "llm_agent_real" else 1.0,
                color=COLORS[mode],
                label=LABELS[mode],
                zorder=3 if mode == "llm_agent_real" else 2,
            )
        panel.set_title(title, fontsize=8, fontweight="bold", pad=6)
        panel.set_xlabel("Seed")
        panel.grid(axis="y", color="#D9DDE2", linewidth=0.6, alpha=0.8)
        panel.tick_params(length=3, width=0.7)
        panel.text(-0.13, 1.07, "abc"[panel_index], transform=panel.transAxes, fontweight="bold", fontsize=9)

    axes[0].set_ylabel("Distance")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 0.98))
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_prefix.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(args.output_prefix.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(args.output_prefix.with_suffix(".png"), dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
