#!/usr/bin/env python3
"""Prepare the AgentSimulator LoanApp dataset for local robustness runs."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from pilot_simulation import SCHEMA, read_log, split_by_case


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(rows)


def normalize_rows(rows: list[dict]) -> list[dict]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "case_id": row["case_id"],
                "activity": row["activity"],
                "resource": row["resource"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
            }
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--test-ratio", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=2408)
    args = parser.parse_args()

    rows = normalize_rows(read_log(args.input_log))
    train, test = split_by_case(rows, args.test_ratio, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "LoanApp_train.csv.gz", train)
    write_csv(args.output_dir / "LoanApp_test.csv.gz", test)
    write_csv(args.output_dir / "LoanApp_full.csv.gz", rows)
    summary = {
        "source": "https://github.com/lukaskirchdorfer/AgentSimulator/raw/main/raw_data/LoanApp.csv.gz",
        "license": "MIT License, AgentSimulator repository",
        "seed": args.seed,
        "test_ratio": args.test_ratio,
        "events": len(rows),
        "train_events": len(train),
        "test_events": len(test),
        "cases": len({row["case_id"] for row in rows}),
        "train_cases": len({row["case_id"] for row in train}),
        "test_cases": len({row["case_id"] for row in test}),
        "activities": len({row["activity"] for row in rows}),
        "resources": len({row["resource"] for row in rows}),
    }
    lines = ["# AgentSimulator LoanApp Prepared Dataset", ""]
    for key, value in summary.items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("The source log is distributed in the AgentSimulator GitHub repository under the MIT License.")
    (args.output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
