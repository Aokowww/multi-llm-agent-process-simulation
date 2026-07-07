from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "results" / "academic_credentials_chapela_summary.csv"
FIG_DIR = Path(__file__).resolve().parent
CSV_OUT = FIG_DIR / "figure2_normalized_metrics.csv"
OUT_BASE = FIG_DIR / "figure2_formal_metric_tradeoffs"


PALETTE = {
    "blue_main": "#0F4D92",
    "green_3": "#8BCF8B",
    "red_2": "#E9A6A1",
    "neutral": "#767676",
    "ink": "#272727",
    "grid": "#DADADA",
}


METRICS = [
    ("bigram_mean", "Bigram"),
    ("trigram_mean", "Trigram"),
    ("absolute_emd_mean", "Absolute\nEMD"),
    ("case_arrival_emd_mean", "Case-arrival\nEMD"),
    ("circadian_emd_mean", "Circadian\nEMD"),
    ("workforce_emd_mean", "Workforce\nEMD"),
    ("relative_emd_mean", "Relative\nEMD"),
    ("cycle_time_wass_mean", "Cycle-time\nWass."),
]


MODES = ["central_baseline", "agent_profile", "llm_agent_proxy"]
MODE_LABELS = {
    "central_baseline": "Central baseline",
    "agent_profile": "Agent profile",
    "llm_agent_proxy": "LLM-agent proxy",
}
COLORS = {
    "central_baseline": PALETTE["neutral"],
    "agent_profile": PALETTE["green_3"],
    "llm_agent_proxy": PALETTE["blue_main"],
}
HATCHES = {
    "central_baseline": "",
    "agent_profile": "//",
    "llm_agent_proxy": "",
}


def apply_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 9,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 1.1,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )


def load_rows() -> list[dict[str, str]]:
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_normalized_csv(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    values = {
        row["mode"]: {metric: float(row[metric]) for metric, _ in METRICS}
        for row in rows
    }
    best = {metric: min(values[mode][metric] for mode in MODES) for metric, _ in METRICS}
    normalized = []
    for metric, label in METRICS:
        for mode in MODES:
            normalized.append(
                {
                    "metric": metric,
                    "label": label.replace("\n", " "),
                    "mode": mode,
                    "mean": values[mode][metric],
                    "relative_to_best": values[mode][metric] / best[metric],
                    "is_best": values[mode][metric] == best[metric],
                }
            )

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(normalized[0].keys()))
        writer.writeheader()
        writer.writerows(normalized)
    return values


def plot_tradeoffs(values: dict[str, dict[str, float]]) -> None:
    apply_publication_style()
    metric_keys = [metric for metric, _ in METRICS]
    labels = [label for _, label in METRICS]
    best = {metric: min(values[mode][metric] for mode in MODES) for metric in metric_keys}
    rel = {
        mode: np.array([values[mode][metric] / best[metric] for metric in metric_keys])
        for mode in MODES
    }

    fig, ax = plt.subplots(figsize=(11.6, 4.8))
    x = np.arange(len(METRICS))
    width = 0.23
    offsets = np.linspace(-width, width, len(MODES))

    for offset, mode in zip(offsets, MODES):
        bars = ax.bar(
            x + offset,
            rel[mode] - 1.0,
            bottom=1.0,
            width=width,
            label=MODE_LABELS[mode],
            color=COLORS[mode],
            edgecolor=PALETTE["ink"],
            linewidth=0.9,
            hatch=HATCHES[mode],
            zorder=3,
        )
        for bar, value in zip(bars, rel[mode]):
            if np.isclose(value, 1.0):
                ax.scatter(
                    bar.get_x() + bar.get_width() / 2,
                    1.004,
                    marker="*",
                    s=58,
                    color="#FFD700",
                    edgecolor=PALETTE["ink"],
                    linewidth=0.5,
                    zorder=5,
                )
            elif value >= 1.08:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.006,
                    f"{value:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color=PALETTE["ink"],
                )

    ax.axhline(1.0, color=PALETTE["ink"], linewidth=1.0)
    ax.set_ylim(0.995, 1.18)
    ax.set_xlim(-0.55, len(METRICS) - 0.45)
    ax.set_ylabel("Relative distance to best", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks([1.00, 1.05, 1.10, 1.15])
    ax.set_yticklabels(["1.00", "1.05", "1.10", "1.15"])
    ax.yaxis.grid(True, color=PALETTE["grid"], linewidth=0.6, alpha=0.7, zorder=0)
    ax.tick_params(axis="both", width=1.0, length=4)

    handles = [
        Patch(
            facecolor=COLORS[mode],
            edgecolor=PALETTE["ink"],
            linewidth=0.9,
            hatch=HATCHES[mode],
            label=MODE_LABELS[mode],
        )
        for mode in MODES
    ]
    star_handle = plt.Line2D(
        [0],
        [0],
        marker="*",
        color="none",
        markerfacecolor="#FFD700",
        markeredgecolor=PALETTE["ink"],
        markersize=9,
        label="Best mean",
    )
    ax.legend(
        handles=handles + [star_handle],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.18),
        ncols=4,
        fontsize=9,
        handlelength=1.5,
        columnspacing=1.5,
    )
    ax.text(
        0.0,
        -0.22,
        "Bars show mean distance divided by the best mean for each metric; lower is better. Values above 1.08 are labeled.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        color="#4D4D4D",
    )

    fig.tight_layout(pad=1.1)
    fig.savefig(f"{OUT_BASE}.svg", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT_BASE}.png", dpi=300, bbox_inches="tight")
    strip_trailing_whitespace(OUT_BASE.with_suffix(".svg"))
    plt.close(fig)


def strip_trailing_whitespace(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = load_rows()
    values = write_normalized_csv(rows)
    plot_tradeoffs(values)


if __name__ == "__main__":
    main()
