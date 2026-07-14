#!/usr/bin/env python3
"""Aggregate repeated AgentSimulator multi-LLM pilot metrics."""

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
    "allocation_decisions",
    "executed_decisions",
    "agent_bids",
    "valid_bid_rate",
    "agent_acceptance_rate",
    "proposal_execution_rate",
    "bid_disagreement_rate",
    "policy_fallbacks",
    "agents_with_memory",
    "bid_total_tokens",
    "bid_total_latency_seconds",
    "generated_resource_count",
    "generated_resource_entropy_normalized",
)


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
    runs = []
    for metrics_path in sorted(args.repeated_dir.glob("seed_*/metrics.json")):
        run_dir = metrics_path.parent
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metadata = json.loads(
            (run_dir / "experiment_metadata.json").read_text(encoding="utf-8")
        )
        row = {"run": run_dir.name, "seed": metadata["seed"]}
        row.update({metric: metrics[metric] for metric in METRICS})
        runs.append(row)

    if not runs:
        raise SystemExit(f"No seed_*/metrics.json files found under {args.repeated_dir}")

    summary = []
    for metric in METRICS:
        values = [float(row[metric]) for row in runs]
        summary.append(
            {
                "metric": metric,
                "n": len(values),
                "mean": statistics.fmean(values),
                "sample_sd": statistics.stdev(values) if len(values) > 1 else 0.0,
                "minimum": min(values),
                "maximum": max(values),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "repeated_metrics.csv", runs, ["run", "seed", *METRICS])
    write_csv(
        args.output_dir / "repeated_summary.csv",
        summary,
        ["metric", "n", "mean", "sample_sd", "minimum", "maximum"],
    )
    (args.output_dir / "repeated_metrics.json").write_text(
        json.dumps(runs, indent=2), encoding="utf-8"
    )
    (args.output_dir / "repeated_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
