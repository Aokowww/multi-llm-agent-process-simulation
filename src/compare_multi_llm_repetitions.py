#!/usr/bin/env python3
"""Create a paired real-versus-mock summary for matched multi-agent seeds."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


METRICS = (
    "trace_variant_distance",
    "activity_distribution_distance",
    "resource_distribution_distance",
    "mean_cycle_time_relative_error",
    "proposal_execution_rate",
    "bid_disagreement_rate",
    "generated_resource_entropy_normalized",
)
LOWER_IS_BETTER = {
    "trace_variant_distance",
    "activity_distribution_distance",
    "resource_distribution_distance",
    "mean_cycle_time_relative_error",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeated-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    paired = []
    for real_path in sorted(args.repeated_dir.glob("seed_*/metrics.json")):
        seed = real_path.parent.name.removeprefix("seed_")
        mock_path = args.repeated_dir / "baselines" / f"mock_seed_{seed}" / "metrics.json"
        if not mock_path.exists():
            raise SystemExit(f"Missing paired mock metrics for seed {seed}: {mock_path}")
        real = json.loads(real_path.read_text(encoding="utf-8"))
        mock = json.loads(mock_path.read_text(encoding="utf-8"))
        for metric in METRICS:
            delta = float(real[metric]) - float(mock[metric])
            paired.append(
                {
                    "seed": int(seed),
                    "metric": metric,
                    "real_multi_llm": real[metric],
                    "mock_multi_agent": mock[metric],
                    "delta_real_minus_mock": delta,
                    "real_wins": metric in LOWER_IS_BETTER and delta < 0,
                }
            )

    summary = []
    for metric in METRICS:
        rows = [row for row in paired if row["metric"] == metric]
        real = [float(row["real_multi_llm"]) for row in rows]
        mock = [float(row["mock_multi_agent"]) for row in rows]
        deltas = [float(row["delta_real_minus_mock"]) for row in rows]
        summary.append(
            {
                "metric": metric,
                "n": len(rows),
                "real_mean": statistics.fmean(real),
                "mock_mean": statistics.fmean(mock),
                "mean_delta_real_minus_mock": statistics.fmean(deltas),
                "delta_sample_sd": statistics.stdev(deltas) if len(deltas) > 1 else 0.0,
                "real_wins": sum(bool(row["real_wins"]) for row in rows)
                if metric in LOWER_IS_BETTER
                else "not_directional",
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "paired_comparison.csv",
        paired,
        [
            "seed",
            "metric",
            "real_multi_llm",
            "mock_multi_agent",
            "delta_real_minus_mock",
            "real_wins",
        ],
    )
    write_csv(
        args.output_dir / "paired_comparison_summary.csv",
        summary,
        [
            "metric",
            "n",
            "real_mean",
            "mock_mean",
            "mean_delta_real_minus_mock",
            "delta_sample_sd",
            "real_wins",
        ],
    )
    (args.output_dir / "paired_comparison.json").write_text(
        json.dumps(paired, indent=2), encoding="utf-8"
    )
    (args.output_dir / "paired_comparison_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
