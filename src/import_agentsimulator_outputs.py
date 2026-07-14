#!/usr/bin/env python3
"""Import an upstream AgentSimulator split and generated log for comparison."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from pathlib import Path

from pilot_simulation import SCHEMA, evaluate


def normalize_timestamp(value: str) -> str:
    return re.sub(r"(\.\d{6})\d+(?=[+-]\d\d:\d\d$|Z$)", r"\1", value)


def read_and_normalize(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    normalized = []
    for row in rows:
        normalized.append(
            {
                "case_id": str(row["case_id"]),
                "activity": row.get("activity", row.get("activity_name", "")),
                "resource": row["resource"],
                "start_time": normalize_timestamp(
                    row.get("start_time", row.get("start_timestamp", ""))
                ),
                "end_time": normalize_timestamp(
                    row.get("end_time", row.get("end_timestamp", ""))
                ),
            }
        )
    return normalized


def write_gzip(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = read_and_normalize(args.train)
    test = read_and_normalize(args.test)
    generated = read_and_normalize(args.generated)
    write_gzip(args.output_dir / "LoanApp_train_agentsimulator_split.csv.gz", train)
    write_gzip(args.output_dir / "LoanApp_test_agentsimulator_split.csv.gz", test)
    write_csv(args.output_dir / "simulated_agentsimulator_autonomous.csv", generated)

    result = {
        "source": "upstream AgentSimulator autonomous condition",
        "train_cases": len({row["case_id"] for row in train}),
        "test_cases": len({row["case_id"] for row in test}),
        "generated_cases": len({row["case_id"] for row in generated}),
        "test_events": len(test),
        "generated_events": len(generated),
        **evaluate(test, generated),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
