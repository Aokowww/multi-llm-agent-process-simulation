#!/usr/bin/env python3
"""Plot paired real-LLM and fixed-score responses to AgentSimulator scenarios."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PANELS = (
    ("mean_cycle_time_minutes", "Mean cycle time"),
    ("throughput_cases_per_day", "Throughput"),
    ("mean_work_in_process", "Mean work in process"),
    ("aggregate_resource_utilization", "Resource utilization"),
)
SCENARIOS = ("high_load", "resource_unavailability")
POLICIES = ("fixed_score", "real_llm")
COLORS = {"fixed_score": "#777777", "real_llm": "#2166AC"}
LABELS = {"fixed_score": "Fixed-score control", "real_llm": "LLM resource agents"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.runs.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    x = np.arange(len(SCENARIOS), dtype=float)
    offsets = {"fixed_score": -0.12, "real_llm": 0.12}
    for panel_index, (metric, title) in enumerate(PANELS):
        ax = axes.flat[panel_index]
        for policy in POLICIES:
            for scenario_index, scenario in enumerate(SCENARIOS):
                selected = [
                    row
                    for row in rows
                    if row["policy"] == policy and row["scenario"] == scenario
                ]
                values = np.array(
                    [100.0 * float(row[f"relative_change_{metric}"]) for row in selected]
                )
                positions = np.full(len(values), x[scenario_index] + offsets[policy])
                ax.scatter(
                    positions,
                    values,
                    s=23,
                    color=COLORS[policy],
                    alpha=0.72,
                    edgecolors="white",
                    linewidths=0.45,
                    zorder=3,
                )
                ax.scatter(
                    x[scenario_index] + offsets[policy],
                    values.mean(),
                    marker="D",
                    s=44,
                    facecolors="white",
                    edgecolors=COLORS[policy],
                    linewidths=1.5,
                    zorder=4,
                    label=LABELS[policy] if panel_index == 0 and scenario_index == 0 else None,
                )
        ax.axhline(0, color="#222222", linewidth=0.75)
        ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
        ax.set_xticks(x, ["High load", "Two resources\nunavailable"])
        if panel_index % 2 == 0:
            ax.set_ylabel("Change from baseline (%)")
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)

    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    fig.tight_layout(rect=(0.02, 0.01, 1.0, 0.93), h_pad=1.6, w_pad=1.4)
    for suffix in ("pdf", "png", "svg"):
        fig.savefig(args.output_dir / f"agentsimulator_what_if_response.{suffix}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
