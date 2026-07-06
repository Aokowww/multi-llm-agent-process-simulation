#!/usr/bin/env python3
"""Run what-if intervention scenarios for resource-centric process simulation.

The reproduction experiments compare generated logs to a held-out log. This
script asks a different question: how do policies react when resource capacity
or workload changes? It uses a simple resource-availability queue so capacity
interventions affect waiting time, bottlenecks, handovers, and cycle time.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from pilot_simulation import (
    AGENTIC_MODES,
    HANDOVER_SCHEMA,
    REASONING_SCHEMA,
    decide_resource,
    first_case_start,
    fmt_dt,
    learn_profiles,
    parse_dt,
    read_log,
    sample_duration,
    sample_empirical,
    sample_trace,
    sample_wait,
    write_log,
    write_table,
)


WHAT_IF_MODES = ["central_baseline", "agent_profile", "llm_agent_proxy"]


def sample_case_interarrival_scaled(profiles: dict, rng, load_multiplier: float) -> float:
    samples = profiles.get("case_interarrival_samples", [])
    base = max(0, sample_empirical(samples, 20.0, rng))
    if load_multiplier <= 0:
        raise ValueError("--load-multiplier must be greater than zero")
    return base / load_multiplier


def top_resources(profiles: dict, limit: int) -> list[str]:
    counts = profiles.get("resource_counts", {})
    if not counts:
        raise ValueError("No resource counts are available in the learned profiles.")
    return [
        resource
        for resource, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def scenario_profiles(profiles: dict, constrained_resources: list[str]) -> dict:
    adjusted = deepcopy(profiles)
    adjusted["what_if_constrained_resources"] = constrained_resources
    return adjusted


def simulate_with_resource_queue(
    profiles: dict,
    n_cases: int,
    mode: str,
    seed: int,
    base_start: datetime,
    load_multiplier: float,
    resource_capacity: dict[str, float],
) -> tuple[list[dict], list[dict], list[dict]]:
    import random

    rng = random.Random(seed)
    rows = []
    reasoning_rows = []
    handover_rows = []
    resource_usage = Counter()
    resource_available_at: dict[str, datetime] = defaultdict(lambda: base_start)
    t_arrival = base_start

    for case in range(n_cases):
        if case > 0:
            t_arrival = t_arrival + timedelta(minutes=sample_case_interarrival_scaled(profiles, rng, load_multiplier))
        t = t_arrival
        case_id = f"W_{mode}_{case:04d}"
        previous_activity = None
        previous_resource = None
        for step_index, activity in enumerate(sample_trace(profiles, rng), start=1):
            decision = decide_resource(activity, previous_resource, profiles, mode, rng, resource_usage)
            resource = decision["resource"]
            duration = sample_duration(profiles, resource, activity, rng)
            wait = sample_wait(profiles, previous_activity, activity, rng)
            earliest_case_start = t + timedelta(minutes=wait)
            start = max(earliest_case_start, resource_available_at[resource])
            end = start + timedelta(minutes=duration)
            capacity = max(0.01, resource_capacity.get(resource, 1.0))
            resource_available_at[resource] = end + timedelta(minutes=duration * (1.0 / capacity - 1.0))
            rows.append(
                {
                    "case_id": case_id,
                    "activity": activity,
                    "resource": resource,
                    "start_time": fmt_dt(start),
                    "end_time": fmt_dt(end),
                }
            )
            resource_usage[resource] += 1
            if mode in AGENTIC_MODES:
                reasoning_rows.append(
                    {
                        "case_id": case_id,
                        "step_index": step_index,
                        "mode": mode,
                        "previous_resource": previous_resource or "",
                        "activity": activity,
                        "selected_resource": resource,
                        "feasible_resource_count": decision["feasible_resource_count"],
                        "feasible_resources_top": decision["feasible_resources_top"],
                        "historical_prior": decision["historical_prior"],
                        "selection_rule": decision["selection_rule"],
                        "reason": decision["reason"],
                    }
                )
                if previous_resource and previous_resource != resource:
                    handover_rows.append(
                        {
                            "case_id": case_id,
                            "from_resource": previous_resource,
                            "to_resource": resource,
                            "activity": activity,
                            "timestamp": fmt_dt(start),
                            "message": (
                                f"What-if handover for {activity}; selected {resource} from "
                                f"{decision['feasible_resource_count']} feasible resources."
                            ),
                        }
                    )
            t = end
            previous_activity = activity
            previous_resource = resource

    return rows, reasoning_rows, handover_rows


def cycle_times(rows: list[dict]) -> list[float]:
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    values = []
    for events in by_case.values():
        starts = [parse_dt(row["start_time"]) for row in events]
        ends = [parse_dt(row["end_time"]) for row in events]
        values.append((max(ends) - min(starts)).total_seconds() / 60)
    return values


def resource_busy_minutes(rows: list[dict]) -> Counter:
    busy = Counter()
    for row in rows:
        busy[row["resource"]] += (parse_dt(row["end_time"]) - parse_dt(row["start_time"])).total_seconds() / 60
    return busy


def handover_count(rows: list[dict]) -> int:
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    count = 0
    for events in by_case.values():
        events.sort(key=lambda row: parse_dt(row["start_time"]))
        for previous, current in zip(events, events[1:]):
            if previous["resource"] != current["resource"]:
                count += 1
    return count


def summarize_log(rows: list[dict], scenario: str, mode: str, constrained_resources: list[str], capacity: float) -> dict:
    cycles = cycle_times(rows)
    busy = resource_busy_minutes(rows)
    start = min(parse_dt(row["start_time"]) for row in rows)
    end = max(parse_dt(row["end_time"]) for row in rows)
    makespan = max(1.0, (end - start).total_seconds() / 60)
    bottleneck_resource, bottleneck_busy = max(busy.items(), key=lambda item: (item[1], item[0]))
    constrained_set = set(constrained_resources)
    constrained_busy = sum(busy[resource] for resource in constrained_resources)
    constrained_events = sum(1 for row in rows if row["resource"] in constrained_set)
    handovers = handover_count(rows)
    return {
        "scenario": scenario,
        "mode": mode,
        "cases": len({row["case_id"] for row in rows}),
        "events": len(rows),
        "constrained_resources": "|".join(constrained_resources),
        "constrained_resource_count": len(constrained_resources),
        "constrained_resource_capacity": capacity,
        "mean_cycle_time": statistics.mean(cycles),
        "median_cycle_time": statistics.median(cycles),
        "p90_cycle_time": statistics.quantiles(cycles, n=10)[8] if len(cycles) >= 10 else max(cycles),
        "handover_count": handovers,
        "handover_per_case": handovers / (len({row["case_id"] for row in rows}) or 1),
        "bottleneck_resource": bottleneck_resource,
        "bottleneck_busy_minutes": bottleneck_busy,
        "bottleneck_utilization": bottleneck_busy / makespan,
        "constrained_group_busy_minutes": constrained_busy,
        "constrained_group_event_share": constrained_events / (len(rows) or 1),
        "constrained_group_utilization": constrained_busy / makespan,
        "throughput_cases_per_day": len({row["case_id"] for row in rows}) / (makespan / 1440),
        "makespan_minutes": makespan,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def add_delta_rows(rows: list[dict]) -> list[dict]:
    baseline = {
        (row["run"], row["mode"]): row
        for row in rows
        if row["scenario"] == "baseline"
    }
    output = []
    for row in rows:
        item = dict(row)
        base = baseline.get((row["run"], row["mode"]))
        if base and row["scenario"] != "baseline":
            for metric in [
                "mean_cycle_time",
                "p90_cycle_time",
                "handover_per_case",
                "bottleneck_utilization",
                "constrained_group_event_share",
                "constrained_group_utilization",
            ]:
                base_value = float(base[metric])
                current_value = float(row[metric])
                item[f"{metric}_delta"] = current_value - base_value
                item[f"{metric}_relative_change"] = (current_value - base_value) / base_value if base_value else 0
        output.append(item)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-log", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=3000)
    parser.add_argument("--load-multiplier", type=float, default=1.6)
    parser.add_argument("--capacity-factor", type=float, default=0.5)
    parser.add_argument("--constrained-resource")
    parser.add_argument("--constrained-resource-limit", type=int, default=20)
    parser.add_argument("--save-logs", action="store_true")
    args = parser.parse_args()

    train = read_log(args.train_log)
    test = read_log(args.test_log)
    profiles = learn_profiles(train)
    constrained_resources = [args.constrained_resource] if args.constrained_resource else top_resources(
        profiles,
        args.constrained_resource_limit,
    )
    n_cases = len({row["case_id"] for row in test})
    base_start = first_case_start(test)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        ("baseline", 1.0, 1.0),
        ("reduced_capacity", 1.0, args.capacity_factor),
        ("high_load", args.load_multiplier, 1.0),
        ("reduced_capacity_high_load", args.load_multiplier, args.capacity_factor),
    ]
    all_rows = []
    for run_index in range(args.runs):
        for scenario, load_multiplier, capacity in scenarios:
            resource_capacity = {resource: capacity for resource in constrained_resources}
            scenario_profile = scenario_profiles(profiles, constrained_resources if capacity < 1.0 else [])
            for mode_index, mode in enumerate(WHAT_IF_MODES):
                seed = args.seed + run_index * 1000 + mode_index * 100 + len(scenario)
                generated, reasoning_rows, handover_rows = simulate_with_resource_queue(
                    scenario_profile,
                    n_cases,
                    mode,
                    seed,
                    base_start,
                    load_multiplier=load_multiplier,
                    resource_capacity=resource_capacity,
                )
                summary = summarize_log(generated, scenario, mode, constrained_resources, capacity)
                summary.update({"run": run_index + 1, "seed": seed, "load_multiplier": load_multiplier})
                all_rows.append(summary)
                if args.save_logs:
                    run_dir = args.output_dir / f"run_{run_index + 1:02d}" / scenario
                    write_log(run_dir / f"simulated_{mode}.csv", generated)
                    if reasoning_rows:
                        write_table(run_dir / f"reasoning_{mode}.csv", reasoning_rows, REASONING_SCHEMA)
                    if handover_rows:
                        write_table(run_dir / f"handover_{mode}.csv", handover_rows, HANDOVER_SCHEMA)

    write_csv(args.output_dir / "what_if_runs.csv", add_delta_rows(all_rows))

    grouped = defaultdict(list)
    for row in all_rows:
        grouped[(row["scenario"], row["mode"])].append(row)
    summary_rows = []
    metrics = [
        "mean_cycle_time",
        "p90_cycle_time",
        "handover_per_case",
        "bottleneck_utilization",
        "constrained_group_event_share",
        "constrained_group_utilization",
        "throughput_cases_per_day",
    ]
    for (scenario, mode), group in sorted(grouped.items()):
        item = {
            "scenario": scenario,
            "mode": mode,
            "runs": len(group),
            "constrained_resources": "|".join(constrained_resources),
            "constrained_resource_count": len(constrained_resources),
            "capacity_factor": args.capacity_factor,
            "load_multiplier": args.load_multiplier if "high_load" in scenario else 1.0,
        }
        for metric in metrics:
            values = [float(row[metric]) for row in group]
            item[f"{metric}_mean"] = statistics.mean(values)
            item[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary_rows.append(item)
    write_csv(args.output_dir / "what_if_summary.csv", summary_rows)
    (args.output_dir / "what_if_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    print(json.dumps(summary_rows, indent=2))


if __name__ == "__main__":
    main()
