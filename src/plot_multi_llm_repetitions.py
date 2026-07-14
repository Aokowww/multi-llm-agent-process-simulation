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
    left = x - 0.13
    right = x + 0.13
    control_values = [
        frame.loc[frame.metric == metric, "mock_multi_agent"].to_numpy()
        for metric in metrics
    ]
    llm_values = [
        frame.loc[frame.metric == metric, "real_multi_llm"].to_numpy()
        for metric in metrics
    ]

    for index, (control, llm) in enumerate(zip(control_values, llm_values)):
        for control_value, llm_value in zip(control, llm):
            ax.plot(
                [left[index], right[index]],
                [control_value, llm_value],
                color="#A8ADB5",
                linewidth=0.75,
                zorder=1,
            )
        ax.scatter(
            np.full(len(control), left[index]),
            control,
            s=20,
            color=COLORS["control"],
            edgecolor="white",
            linewidth=0.5,
            label="Deterministic control" if index == 0 else None,
            zorder=3,
        )
        ax.scatter(
            np.full(len(llm), right[index]),
            llm,
            s=20,
            color=COLORS["llm"],
            edgecolor="white",
            linewidth=0.5,
            label="Actual multi-LLM" if index == 0 else None,
            zorder=3,
        )
        ax.scatter(
            [left[index], right[index]],
            [control.mean(), llm.mean()],
            s=48,
            marker="D",
            facecolor="white",
            edgecolor=[COLORS["control"], COLORS["llm"]],
            linewidth=1.2,
            zorder=4,
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
