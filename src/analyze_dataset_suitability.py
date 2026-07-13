#!/usr/bin/env python3
"""Measure whether event logs support constrained resource-agent evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from pilot_simulation import learn_profiles, parse_dt, read_log


def analyze(name: str, train_path: Path, test_path: Path) -> dict:
    train = read_log(train_path)
    test = read_log(test_path)
    profiles = learn_profiles(train)
    train_resources = {row["resource"] for row in train}
    test_resources = {row["resource"] for row in test}
    by_case = defaultdict(list)
    for row in test:
        by_case[row["case_id"]].append(row)

    capability_hits = 0
    handover_mask_hits = 0
    handover_contexts = 0
    capability_sizes = []
    local_sizes = []
    for events in by_case.values():
        events.sort(key=lambda row: parse_dt(row["start_time"]))
        previous_resource = None
        for event in events:
            activity = event["activity"]
            actual = event["resource"]
            activity_candidates = profiles["capabilities"].get(activity, {})
            capability_sizes.append(len(activity_candidates))
            capability_hits += int(actual in activity_candidates)
            key = f"{previous_resource}||{activity}" if previous_resource else ""
            handover_candidates = profiles.get("handover_priors", {}).get(key, {})
            local_candidates = handover_candidates or activity_candidates
            local_sizes.append(len(local_candidates))
            handover_contexts += int(bool(handover_candidates))
            handover_mask_hits += int(actual in local_candidates)
            previous_resource = actual

    total = len(test) or 1
    union = train_resources | test_resources
    return {
        "dataset": name,
        "train_cases": len({row["case_id"] for row in train}),
        "test_cases": len(by_case),
        "train_events": len(train),
        "test_events": len(test),
        "activities": len({row["activity"] for row in train + test}),
        "train_resources": len(train_resources),
        "test_resources": len(test_resources),
        "resource_overlap_jaccard": len(train_resources & test_resources) / len(union) if union else 0.0,
        "test_event_capability_coverage": capability_hits / total,
        "test_event_handover_mask_coverage": handover_mask_hits / total,
        "handover_context_share": handover_contexts / total,
        "mean_activity_feasible_resources": sum(capability_sizes) / len(capability_sizes),
        "mean_local_feasible_resources": sum(local_sizes) / len(local_sizes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        metavar="NAME=TRAIN,TEST",
        help="May be repeated.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for value in args.dataset:
        name, paths = value.split("=", 1)
        train, test = paths.split(",", 1)
        rows.append(analyze(name, Path(train), Path(test)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    args.output.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
