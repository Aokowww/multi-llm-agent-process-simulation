#!/usr/bin/env python3
"""Run Chapela-Campa distances across repeated simulation run folders."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from run_chapela_distances import add_short_names, copy_simulated_logs, prepare_script, run_distance_script


NON_METRIC_COLUMNS = {"run", "mode", "name"}


def read_distance_rows(path: Path, run_index: int) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["run"] = run_index
            rows.append(row)
        return rows


def metric_columns(rows: list[dict]) -> list[str]:
    return [
        column
        for column in rows[0]
        if column not in NON_METRIC_COLUMNS and not column.endswith("_runtime")
    ]


def summarize(rows: list[dict]) -> list[dict]:
    metrics = metric_columns(rows)
    modes = sorted({row["mode"] for row in rows})
    summary = []
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode]
        item = {"mode": mode, "runs": len(mode_rows)}
        for metric in metrics:
            values = [float(row[metric]) for row in mode_rows]
            item[f"{metric}_mean"] = statistics.mean(values)
            item[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            item[f"{metric}_min"] = min(values)
            item[f"{metric}_max"] = max(values)
        summary.append(item)
    return summary


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-log", type=Path, required=True)
    parser.add_argument("--repeated-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--distance-script",
        type=Path,
        required=True,
        help="Path to Chapela-Campa et al.'s ComputeLogDistance.py from the Zenodo artifact.",
    )
    parser.add_argument("--cfld", action="store_true")
    args = parser.parse_args()

    original_log = args.original_log.resolve()
    repeated_dir = args.repeated_dir.resolve()
    distance_script = args.distance_script.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    run_dirs = sorted(path for path in repeated_dir.glob("run_*") if path.is_dir())
    if not run_dirs:
        raise RuntimeError(f"No run_* directories found in {repeated_dir}")

    for run_index, run_dir in enumerate(run_dirs, start=1):
        run_output_dir = output_dir / run_dir.name
        run_output_dir.mkdir(parents=True, exist_ok=True)
        script = prepare_script(distance_script, run_output_dir)
        sim_dir = copy_simulated_logs(run_dir, run_output_dir)
        raw_output = run_distance_script(script, original_log, sim_dir, run_output_dir, args.cfld)
        named_output = add_short_names(raw_output)
        all_rows.extend(read_distance_rows(named_output, run_index))

    write_csv(output_dir / "chapela_runs.csv", all_rows)
    summary = summarize(all_rows)
    write_csv(output_dir / "chapela_summary.csv", summary)
    (output_dir / "chapela_runs.json").write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    (output_dir / "chapela_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
