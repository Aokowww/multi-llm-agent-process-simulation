from __future__ import annotations

import csv
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "results" / "academic_credentials_chapela_summary.csv"
FIG_DIR = Path(__file__).resolve().parent
SVG_OUT = FIG_DIR / "figure2_formal_metric_tradeoffs.svg"
CSV_OUT = FIG_DIR / "figure2_normalized_metrics.csv"


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

MODE_LABELS = {
    "central_baseline": "Central baseline",
    "agent_profile": "Agent profile",
    "llm_agent_proxy": "LLM-agent proxy",
}

COLORS = {
    "central_baseline": "#0072B2",
    "agent_profile": "#009E73",
    "llm_agent_proxy": "#D55E00",
}


def load_rows() -> list[dict[str, str]]:
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def svg_text(x, y, value, size=14, weight="400", anchor="start", fill="#1f2d3d"):
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, DejaVu Sans, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">'
        f"{escape(value)}</text>"
    )


def multiline_text(x, y, value, size=12, anchor="middle"):
    parts = []
    for i, line in enumerate(value.split("\n")):
        parts.append(svg_text(x, y + i * (size + 2), line, size=size, anchor=anchor))
    return "\n".join(parts)


def main() -> None:
    rows = load_rows()
    modes = ["central_baseline", "agent_profile", "llm_agent_proxy"]
    values = {
        row["mode"]: {metric: float(row[metric]) for metric, _ in METRICS}
        for row in rows
    }
    best = {metric: min(values[mode][metric] for mode in modes) for metric, _ in METRICS}
    normalized = []
    for metric, label in METRICS:
        for mode in modes:
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

    width, height = 1160, 640
    margin_l, margin_r, margin_t, margin_b = 88, 40, 66, 135
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    y_max = 1.18
    group_w = plot_w / len(METRICS)
    bar_w = 24
    gap = 7

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Relative formal BPS distance metrics by simulation condition">',
        '<rect x="0" y="0" width="1160" height="640" fill="#ffffff"/>',
        svg_text(40, 38, "Mean distance divided by best mean for each metric; lower is better and 1.0 is best.", 13),
    ]

    # Grid and y-axis labels
    for tick in [1.0, 1.05, 1.10, 1.15]:
        y = margin_t + plot_h - ((tick - 1.0) / (y_max - 1.0)) * plot_h
        parts.append(f'<line x1="{margin_l}" y1="{y:.1f}" x2="{width - margin_r}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(svg_text(margin_l - 12, y + 4, f"{tick:.2f}", 12, anchor="end", fill="#52616f"))
    parts.append(f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{margin_t + plot_h}" stroke="#334155" stroke-width="1.3"/>')
    parts.append(f'<line x1="{margin_l}" y1="{margin_t + plot_h}" x2="{width - margin_r}" y2="{margin_t + plot_h}" stroke="#334155" stroke-width="1.3"/>')

    # Bars
    for idx, (metric, label) in enumerate(METRICS):
        cx = margin_l + group_w * idx + group_w / 2
        group_start = cx - (3 * bar_w + 2 * gap) / 2
        for j, mode in enumerate(modes):
            rel = values[mode][metric] / best[metric]
            capped_rel = min(rel, y_max)
            bar_h = ((capped_rel - 1.0) / (y_max - 1.0)) * plot_h
            x = group_start + j * (bar_w + gap)
            y = margin_t + plot_h - bar_h
            fill = COLORS[mode]
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" fill="{fill}" rx="2"/>')
            if abs(rel - 1.0) < 1e-9:
                parts.append(f'<circle cx="{x + bar_w / 2:.1f}" cy="{y - 9:.1f}" r="4" fill="{fill}"/>')
            if rel > y_max:
                parts.append(svg_text(x + bar_w / 2, margin_t - 8, f"{rel:.2f}", 10, "700", "middle", fill))
        parts.append(multiline_text(cx, margin_t + plot_h + 26, label, 11, "middle"))

    # Legend
    lx, ly = 700, 27
    for i, mode in enumerate(modes):
        x = lx + i * 145
        parts.append(f'<rect x="{x}" y="{ly}" width="14" height="14" fill="{COLORS[mode]}" rx="2"/>')
        parts.append(svg_text(x + 20, ly + 12, MODE_LABELS[mode], 12))
    parts.append(svg_text(40, 606, "Dot marks the best mean for a metric. The complete mean +/- standard deviation values are reported in Table 4.", 12, fill="#52616f"))
    parts.append("</svg>")

    SVG_OUT.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
