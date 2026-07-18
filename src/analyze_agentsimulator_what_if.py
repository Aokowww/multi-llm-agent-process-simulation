#!/usr/bin/env python3
"""Aggregate paired AgentSimulator what-if responses against unchanged runs."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from import_agentsimulator_outputs import read_and_normalize
from run_agentsimulator_policy_experiment import process_performance


SEEDS = (9400, 9500, 9600)
SCENARIOS = ("high_load", "resource_unavailability")
POLICIES = ("fixed_score", "real_llm")
RESPONSE_METRICS = (
    "mean_cycle_time_minutes",
    "p90_cycle_time_minutes",
    "throughput_cases_per_day",
    "mean_work_in_process",
    "handover_per_case",
    "aggregate_resource_utilization",
    "maximum_resource_event_share",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_paths(repeated_dir: Path, policy: str, seed: int) -> tuple[Path, Path]:
    if policy == "real_llm":
        directory = repeated_dir / f"seed_{seed}"
        return directory / "simulated_agentsimulator_multi_llm_agent.csv", directory / "metrics.json"
    directory = repeated_dir / "baselines" / f"mock_seed_{seed}"
    return directory / "simulated_agentsimulator_mock_multi_agent.csv", directory / "metrics.json"


def scenario_paths(what_if_dir: Path, scenario: str, policy: str, seed: int) -> tuple[Path, Path, Path]:
    directory = what_if_dir / scenario / f"{policy}_seed_{seed}"
    filename = (
        "simulated_agentsimulator_multi_llm_agent.csv"
        if policy == "real_llm"
        else "simulated_agentsimulator_mock_multi_agent.csv"
    )
    return directory / filename, directory / "metrics.json", directory / "experiment_metadata.json"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeated-dir", type=Path, required=True)
    parser.add_argument("--what-if-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    baseline = {}
    for policy in POLICIES:
        for seed in SEEDS:
            log_path, metrics_path = baseline_paths(args.repeated_dir, policy, seed)
            baseline[(policy, seed)] = {
                **process_performance(read_and_normalize(log_path)),
                **read_json(metrics_path),
            }

    response_rows = []
    for scenario in SCENARIOS:
        for policy in POLICIES:
            for seed in SEEDS:
                log_path, metrics_path, metadata_path = scenario_paths(
                    args.what_if_dir, scenario, policy, seed
                )
                generated = read_and_normalize(log_path)
                current = {**process_performance(generated), **read_json(metrics_path)}
                metadata = read_json(metadata_path)
                base = baseline[(policy, seed)]
                unavailable = set(metadata.get("unavailable_resources", []))
                used = {row["resource"] for row in generated}
                row = {
                    "scenario": scenario,
                    "policy": policy,
                    "seed": seed,
                    "cases": metadata["generated_cases"],
                    "unavailable_resources": "|".join(sorted(unavailable)),
                    "unavailable_resources_used": len(unavailable & used),
                    "bottleneck_resource": current["bottleneck_resource"],
                    "baseline_bottleneck_resource": base["bottleneck_resource"],
                    "bottleneck_migrated": current["bottleneck_resource"] != base["bottleneck_resource"],
                    "valid_bid_rate": current["valid_bid_rate"],
                    "policy_fallbacks": current["policy_fallbacks"],
                    "agent_bids": current["agent_bids"],
                }
                for metric in RESPONSE_METRICS:
                    value = float(current[metric])
                    baseline_value = float(base[metric])
                    delta = value - baseline_value
                    row[metric] = value
                    row[f"baseline_{metric}"] = baseline_value
                    row[f"delta_{metric}"] = delta
                    row[f"relative_change_{metric}"] = (
                        delta / baseline_value if baseline_value else 0.0
                    )
                response_rows.append(row)

    summary_rows = []
    for scenario in SCENARIOS:
        for policy in POLICIES:
            selected = [
                row
                for row in response_rows
                if row["scenario"] == scenario and row["policy"] == policy
            ]
            summary = {
                "scenario": scenario,
                "policy": policy,
                "runs": len(selected),
                "cases_per_run": selected[0]["cases"],
                "total_agent_bids": sum(int(row["agent_bids"]) for row in selected),
                "valid_bid_rate": statistics.fmean(float(row["valid_bid_rate"]) for row in selected),
                "total_policy_fallbacks": sum(int(row["policy_fallbacks"]) for row in selected),
                "bottleneck_migration_rate": statistics.fmean(
                    float(row["bottleneck_migrated"]) for row in selected
                ),
                "unavailable_resources_used": sum(
                    int(row["unavailable_resources_used"]) for row in selected
                ),
            }
            for metric in RESPONSE_METRICS:
                values = [float(row[f"relative_change_{metric}"]) for row in selected]
                summary[f"relative_change_{metric}_mean"] = statistics.fmean(values)
                summary[f"relative_change_{metric}_sd"] = (
                    statistics.stdev(values) if len(values) > 1 else 0.0
                )
            summary_rows.append(summary)

    write_csv(args.output_dir / "what_if_response_runs.csv", response_rows)
    write_csv(args.output_dir / "what_if_response_summary.csv", summary_rows)
    (args.output_dir / "what_if_response_runs.json").write_text(
        json.dumps(response_rows, indent=2), encoding="utf-8"
    )
    (args.output_dir / "what_if_response_summary.json").write_text(
        json.dumps(summary_rows, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary_rows, indent=2))


if __name__ == "__main__":
    main()
