#!/usr/bin/env python3
"""Compute agent-specific diagnostics from the three LoanApp LLM runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


RUNS = (
    (8200, "loanapp_llama31_8b_100cases_run1_seed8200_20260714"),
    (8300, "loanapp_llama31_8b_100cases_run2_seed8300_20260714"),
    (8400, "loanapp_llama31_8b_100cases_run3_seed8400_20260714"),
)

MODES = (
    "central_baseline",
    "agent_profile",
    "llm_agent_proxy",
    "llm_agent_real",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    return -sum((n / total) * math.log(n / total) for n in counts.values())


def distribution_metrics(rows: list[dict[str, str]], available: int) -> dict[str, float]:
    counts = Counter(row["resource"] for row in rows)
    total = sum(counts.values())
    h = entropy(counts)
    return {
        "decisions": float(total),
        "resources_used": float(len(counts)),
        "resource_coverage": len(counts) / available,
        "max_resource_share": max(counts.values()) / total,
        "assignment_entropy": h,
        "normalized_assignment_entropy": h / math.log(available),
        "effective_resource_count": math.exp(h),
        "hhi": sum((n / total) ** 2 for n in counts.values()),
    }


def conditional_diversity(
    rows: list[dict[str, str]], feasible_by_activity: dict[str, int], resource_field: str
) -> dict[str, float]:
    by_activity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_activity[row["activity"]].append(row)

    weighted_coverage = 0.0
    weighted_entropy = 0.0
    eligible = 0
    for activity_rows in by_activity.values():
        feasible_count = feasible_by_activity[activity_rows[0]["activity"]]
        if feasible_count <= 1:
            continue
        weight = len(activity_rows)
        counts = Counter(row[resource_field] for row in activity_rows)
        weighted_coverage += weight * (len(counts) / feasible_count)
        weighted_entropy += weight * (entropy(counts) / math.log(feasible_count))
        eligible += weight

    return {
        "activity_capability_coverage": weighted_coverage / eligible,
        "activity_conditional_entropy": weighted_entropy / eligible,
        "conditional_decisions": float(eligible),
    }


def parse_prior(raw: str) -> dict[str, float]:
    value = json.loads(raw)
    return {str(key): float(probability) for key, probability in value.items()}


def reasoning_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    factors = Counter()
    feasible = 0
    action_named = 0
    selected_maximum = 0
    selected_prior_ratios = []

    for row in rows:
        selected = row["selected_resource"]
        feasible_resources = row["feasible_resources_top"].split("|")
        feasible += int(selected in feasible_resources)
        action_named += int(selected in row["reason"])
        for factor in filter(None, row["factors"].split("|")):
            factors[factor] += 1

        prior = parse_prior(row["historical_prior"])
        selected_value = prior.get(selected, 0.0)
        maximum = max(prior.get(resource, 0.0) for resource in feasible_resources)
        selected_maximum += int(math.isclose(selected_value, maximum, rel_tol=1e-9, abs_tol=1e-12))
        if maximum > 0:
            selected_prior_ratios.append(selected_value / maximum)

    total = len(rows)
    return {
        "decisions": float(total),
        "feasible_action_rate": feasible / total,
        "reason_action_consistency": action_named / total,
        "historical_capability_factor_rate": factors["historical_capability"] / total,
        "handover_continuity_factor_rate": factors["handover_continuity"] / total,
        "workload_balance_factor_rate": factors["workload_balance"] / total,
        "maximum_feasible_prior_selection_rate": selected_maximum / total,
        "mean_selected_to_max_prior_ratio": statistics.fmean(selected_prior_ratios),
    }


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.fmean(values), statistics.stdev(values)


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    policy_rows: list[dict[str, object]] = []
    reasoning_rows: list[dict[str, object]] = []
    api_rows: list[dict[str, str]] = []

    for seed, directory in RUNS:
        run_dir = args.results_root / directory
        mode_logs = {
            mode: read_csv(run_dir / "run_01" / f"simulated_{mode}.csv")
            for mode in MODES
        }
        available_resources = len(
            {row["resource"] for rows in mode_logs.values() for row in rows}
        )
        reasoning = read_csv(run_dir / "run_01" / "reasoning_llm_agent_real.csv")
        with (run_dir / "learned_profiles.json").open(encoding="utf-8") as handle:
            capabilities = json.load(handle)["capabilities"]
        feasible_by_activity = {
            activity: len(resources) for activity, resources in capabilities.items()
        }
        for mode, rows in mode_logs.items():
            metrics = distribution_metrics(rows, available_resources)
            conditional = conditional_diversity(rows, feasible_by_activity, "resource")
            policy_rows.append({"seed": seed, "mode": mode, **metrics, **conditional})

        reasoning_rows.append(
            {
                "seed": seed,
                **reasoning_metrics(reasoning),
            }
        )
        api_rows.extend(read_csv(run_dir / "run_01" / "llm_call_diagnostics.csv"))

    summary_rows: list[dict[str, object]] = []
    policy_metrics = [
        key for key in policy_rows[0] if key not in {"seed", "mode", "decisions"}
    ]
    for mode in MODES:
        selected = [row for row in policy_rows if row["mode"] == mode]
        for metric in policy_metrics:
            mean, sd = mean_sd([float(row[metric]) for row in selected])
            summary_rows.append(
                {"scope": mode, "metric": metric, "mean": mean, "sd": sd, "n": len(selected)}
            )

    reasoning_metrics_names = [key for key in reasoning_rows[0] if key != "seed"]
    for metric in reasoning_metrics_names:
        values = [float(row[metric]) for row in reasoning_rows]
        mean, sd = mean_sd(values)
        summary_rows.append(
            {"scope": "llm_agent_real", "metric": metric, "mean": mean, "sd": sd, "n": 3}
        )

    token_total = sum(int(row["total_tokens"]) for row in api_rows)
    decisions = len(api_rows)
    weighted_latency = statistics.fmean(float(row["latency_seconds"]) for row in api_rows)
    summary_rows.extend(
        [
            {
                "scope": "llm_agent_real",
                "metric": "tokens_per_decision",
                "mean": token_total / decisions,
                "sd": "",
                "n": decisions,
            },
            {
                "scope": "llm_agent_real",
                "metric": "weighted_mean_latency_seconds",
                "mean": weighted_latency,
                "sd": "",
                "n": decisions,
            },
        ]
    )

    write_rows(args.output_dir / "llm_specific_policy_runs.csv", policy_rows)
    write_rows(args.output_dir / "llm_specific_reasoning_runs.csv", reasoning_rows)
    write_rows(args.output_dir / "llm_specific_summary.csv", summary_rows)


if __name__ == "__main__":
    main()
