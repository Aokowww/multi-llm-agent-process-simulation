#!/usr/bin/env python3
"""Plot the matched distributed multi-LLM repetitions for the manuscript."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams.update(
    {
        "font.size": 7,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    }
)

COLORS = {"control": "#7884B4", "llm": "#D58A63"}


def draw_panel(ax, frame: pd.DataFrame, metrics: list[str], labels: list[str]) -> None:
    x = np.arange(len(metrics))
    width = 0.34
    for offset, column, label, color in (
        (-width / 2, "mock_multi_agent", "Deterministic control", COLORS["control"]),
        (width / 2, "real_multi_llm", "Actual multi-LLM", COLORS["llm"]),
    ):
        values = [frame.loc[frame.metric == metric, column].to_numpy() for metric in metrics]
        means = np.array([v.mean() for v in values])
        errors = np.array([v.std(ddof=1) for v in values])
        ax.bar(
            x + offset,
            means,
            width,
            yerr=errors,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            capsize=2.5,
            error_kw={"elinewidth": 0.8, "capthick": 0.8, "ecolor": "#3F3F3F"},
            label=label,
            zorder=2,
        )
        for index, run_values in enumerate(values):
            jitter = np.linspace(-0.045, 0.045, len(run_values))
            ax.scatter(
                np.full(len(run_values), x[index] + offset) + jitter,
                run_values,
                s=11,
                facecolor="white",
                edgecolor="#303030",
                linewidth=0.55,
                zorder=3,
            )
    ax.set_xticks(x, labels)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Metric value")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.6, zorder=0)
    ax.tick_params(axis="both", length=3, width=0.7)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), constrained_layout=True)

    draw_panel(
        axes[0],
        data,
        [
            "trace_variant_distance",
            "activity_distribution_distance",
            "resource_distribution_distance",
            "mean_cycle_time_relative_error",
        ],
        ["Trace", "Activity", "Resource", "Cycle time"],
    )
    axes[0].set_title("Process-output distance", loc="left", fontweight="bold", pad=7)
    axes[0].text(-0.12, 1.04, "a", transform=axes[0].transAxes, fontweight="bold", fontsize=9)

    draw_panel(
        axes[1],
        data,
        [
            "proposal_execution_rate",
            "bid_disagreement_rate",
            "generated_resource_entropy_normalized",
        ],
        ["Proposal\nexecution", "Bid\ndisagreement", "Resource\nentropy"],
    )
    axes[1].set_title("Agent-level diagnostics", loc="left", fontweight="bold", pad=7)
    axes[1].text(-0.12, 1.04, "b", transform=axes[1].transAxes, fontweight="bold", fontsize=9)
    axes[1].legend(
        loc="upper center",
        bbox_to_anchor=(-0.08, 1.22),
        ncol=2,
        handlelength=1.4,
        columnspacing=1.4,
    )

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix, options in (
        (".svg", {}),
        (".pdf", {}),
        (".png", {"dpi": 300}),
        (".tiff", {"dpi": 600}),
    ):
        fig.savefig(args.output_prefix.with_suffix(suffix), bbox_inches="tight", **options)
    plt.close(fig)


if __name__ == "__main__":
    main()
