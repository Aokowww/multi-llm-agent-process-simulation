#!/usr/bin/env python3
"""Run a policy replacement inside a patched upstream AgentSimulator checkout."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from agentsimulator_policy_adapter import AgentSimulatorAllocationPolicy
from import_agentsimulator_outputs import read_and_normalize, write_csv, write_gzip
from llm_bid_client import DeterministicBidClient, OpenAICompatibleBidClient
from pilot_simulation import evaluate, parse_dt
from run_repeated import PROVIDERS


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def process_performance(rows: list[dict]) -> dict:
    """Summarize scenario outcomes without using a counterfactual test log."""
    if not rows:
        return {}
    by_case = {}
    busy_minutes = Counter()
    resource_events = Counter()
    handovers = 0
    waiting_minutes = []
    starts = []
    ends = []
    for row in rows:
        start = parse_dt(row["start_time"])
        end = parse_dt(row["end_time"])
        starts.append(start)
        ends.append(end)
        case_events = by_case.setdefault(row["case_id"], [])
        case_events.append((start, end, row["resource"]))
        busy_minutes[row["resource"]] += max(0.0, (end - start).total_seconds() / 60.0)
        resource_events[row["resource"]] += 1
    cycle_minutes = []
    case_intervals = []
    for events in by_case.values():
        events.sort(key=lambda item: (item[0], item[1]))
        case_start = min(item[0] for item in events)
        case_end = max(item[1] for item in events)
        case_intervals.append((case_start, case_end))
        cycle_minutes.append((case_end - case_start).total_seconds() / 60.0)
        for previous, current in zip(events, events[1:]):
            waiting_minutes.append(max(0.0, (current[0] - previous[1]).total_seconds() / 60.0))
            handovers += previous[2] != current[2]
    cycle_sorted = sorted(cycle_minutes)
    p90_index = max(0, min(len(cycle_sorted) - 1, math.ceil(0.9 * len(cycle_sorted)) - 1))
    horizon_minutes = max(1e-9, (max(ends) - min(starts)).total_seconds() / 60.0)
    wip_events = sorted(
        [(timestamp, delta) for start, end in case_intervals for timestamp, delta in ((start, 1), (end, -1))],
        key=lambda item: (item[0], item[1]),
    )
    current_wip = 0
    maximum_wip = 0
    wip_area_minutes = 0.0
    previous_timestamp = wip_events[0][0]
    for timestamp, delta in wip_events:
        wip_area_minutes += current_wip * (timestamp - previous_timestamp).total_seconds() / 60.0
        current_wip += delta
        maximum_wip = max(maximum_wip, current_wip)
        previous_timestamp = timestamp
    top_resource, top_events = resource_events.most_common(1)[0]
    return {
        "mean_cycle_time_minutes": sum(cycle_minutes) / len(cycle_minutes),
        "p90_cycle_time_minutes": cycle_sorted[p90_index],
        "mean_inter_activity_waiting_minutes": (
            sum(waiting_minutes) / len(waiting_minutes) if waiting_minutes else 0.0
        ),
        "throughput_cases_per_day": len(by_case) / (horizon_minutes / (24.0 * 60.0)),
        "mean_work_in_process": wip_area_minutes / horizon_minutes,
        "maximum_work_in_process": maximum_wip,
        "handover_per_case": handovers / len(by_case),
        "aggregate_resource_utilization": sum(busy_minutes.values()) / (
            horizon_minutes * max(1, len(resource_events))
        ),
        "bottleneck_resource": max(busy_minutes, key=busy_minutes.get),
        "bottleneck_busy_minutes": max(busy_minutes.values()),
        "maximum_resource_event_share": top_events / len(rows),
        "maximum_resource_event_share_resource": top_resource,
        "simulation_horizon_minutes": horizon_minutes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agentsimulator-path", type=Path, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--policy",
        choices=["mock_multi_agent", "multi_llm_agent"],
        default="mock_multi_agent",
    )
    parser.add_argument("--max-cases", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--memory-size", type=int, default=3)
    parser.add_argument("--seed", type=int, default=9400)
    parser.add_argument("--llm-provider", choices=sorted(PROVIDERS), default="groq")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-api-key-env")
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    parser.add_argument("--llm-min-interval", type=float)
    parser.add_argument(
        "--scenario",
        choices=["baseline", "high_load", "resource_unavailability", "combined"],
        default="baseline",
    )
    parser.add_argument("--arrival-rate-multiplier", type=float, default=1.6)
    parser.add_argument("--unavailable-resource-count", type=int, default=2)
    args = parser.parse_args()

    upstream = args.agentsimulator_path.resolve()
    log_path = args.log_path.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(upstream))
    from source.agent_simulator import AgentSimulator

    provider = PROVIDERS[args.llm_provider]
    model_name = args.llm_model or provider["model"]
    base_url = args.llm_base_url or provider["base_url"]
    api_key_env = args.llm_api_key_env or provider["api_key_env"]
    min_interval = (
        args.llm_min_interval if args.llm_min_interval is not None else provider["min_interval"]
    )
    bid_client = DeterministicBidClient()
    if args.policy == "multi_llm_agent":
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set")
        bid_client = OpenAICompatibleBidClient(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout=args.llm_timeout,
            min_interval=min_interval,
            seed=args.seed,
            cache_path=output_dir / "agent_bid_cache.jsonl",
        )
    policy = AgentSimulatorAllocationPolicy(
        bid_client=bid_client,
        top_k=args.top_k,
        memory_size=args.memory_size,
    )
    random.seed(args.seed)
    try:
        import numpy as np

        np.random.seed(args.seed)
    except ImportError:
        pass
    params = {
        "discover_extr_delays": False,
        "discover_parallel_work": False,
        "central_orchestration": False,
        "determine_automatically": False,
        "PATH_LOG": str(log_path),
        "PATH_LOG_test": None,
        "train_and_test": False,
        "column_names": {
            "case_id": "case_id",
            "activity": "activity_name",
            "resource": "resource",
            "end_time": "end_timestamp",
            "start_time": "start_timestamp",
        },
        "num_simulations": 1,
        "resource_selection_policy": policy,
        "max_cases": args.max_cases,
        "arrival_rate_multiplier": (
            args.arrival_rate_multiplier if args.scenario in {"high_load", "combined"} else 1.0
        ),
        "unavailable_resource_count": (
            args.unavailable_resource_count
            if args.scenario in {"resource_unavailability", "combined"}
            else 0
        ),
    }
    with working_directory(upstream):
        simulator = AgentSimulator(params)
        simulator.execute_pipeline()
        source_dir = Path(simulator.data_dir)

    test = read_and_normalize(source_dir / "test_preprocessed.csv")
    generated = read_and_normalize(source_dir / "simulated_log_0.csv")
    case_starts = {}
    for row in test:
        timestamp = parse_dt(row["start_time"])
        case_starts[row["case_id"]] = min(timestamp, case_starts.get(row["case_id"], timestamp))
    selected_cases = {
        case_id
        for case_id, _ in sorted(case_starts.items(), key=lambda item: (item[1], item[0]))[
            : args.max_cases
        ]
    }
    test = [row for row in test if row["case_id"] in selected_cases]
    write_gzip(output_dir / "observed_test.csv.gz", test)
    write_csv(output_dir / f"simulated_agentsimulator_{args.policy}.csv", generated)
    write_rows(output_dir / "allocation_traces.csv", policy.allocation_traces)
    write_rows(output_dir / "agent_bids.csv", policy.bid_traces)
    if getattr(bid_client, "diagnostics", None):
        write_rows(output_dir / "bid_call_diagnostics.csv", bid_client.diagnostics)
    resource_counts = Counter(row["resource"] for row in generated)
    total = sum(resource_counts.values()) or 1
    entropy = -sum((count / total) * math.log(count / total) for count in resource_counts.values())
    normalized_entropy = entropy / math.log(len(resource_counts)) if len(resource_counts) > 1 else 0.0
    metrics = {
        **evaluate(test, generated),
        **process_performance(generated),
        **policy.summary(),
        **bid_client.summary(),
        "generated_resource_count": len(resource_counts),
        "generated_resource_entropy_normalized": normalized_entropy,
    }
    metadata = {
        "policy": args.policy,
        "upstream_commit_required": "665a6926878859072769aa25c12fe9d6056ad510",
        "log_file": log_path.name,
        "test_cases": len({row["case_id"] for row in test}),
        "generated_cases": len({row["case_id"] for row in generated}),
        "max_cases": args.max_cases,
        "top_k": args.top_k,
        "memory_size": args.memory_size,
        "seed": args.seed,
        "scenario": args.scenario,
        "arrival_rate_multiplier": params["arrival_rate_multiplier"],
        "unavailable_resource_count": params["unavailable_resource_count"],
        "unavailable_resources": simulator.simulation_parameters.get(
            "what_if_unavailable_resources", []
        ),
        "llm_provider": args.llm_provider if args.policy == "multi_llm_agent" else None,
        "llm_model": model_name if args.policy == "multi_llm_agent" else None,
        "llm_api_key_env": api_key_env if args.policy == "multi_llm_agent" else None,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "experiment_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
