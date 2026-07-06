#!/usr/bin/env python3
"""Run Chapela-Campa et al. BPS log-distance measures on generated logs."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPS = PROJECT_ROOT / ".deps"


def prepare_script(source_script: Path, output_dir: Path) -> Path:
    target = output_dir / "ComputeLogDistance_project_columns.py"
    text = source_script.read_text(encoding="utf-8")
    old = """log_2_ids = EventLogIDs(
    case='case_id',
    activity='activity',
    start_time='Start_Time',
    end_time='End_Time',
    resource='resource'
)"""
    new = """log_2_ids = EventLogIDs(
    case='case_id',
    activity='activity',
    start_time='start_time',
    end_time='end_time',
    resource='resource'
)"""
    if old not in text:
        raise RuntimeError("Could not find default log_2_ids block to patch.")
    target.write_text(text.replace(old, new), encoding="utf-8")
    return target


def copy_simulated_logs(source_dir: Path, output_dir: Path) -> Path:
    sim_dir = output_dir / "simulated_logs"
    sim_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_dir.glob("simulated_*.csv")):
        shutil.copy2(path, sim_dir / path.name)
    if not list(sim_dir.glob("*.csv")):
        raise RuntimeError(f"No simulated_*.csv files found in {source_dir}")
    return sim_dir


def run_distance_script(script: Path, original_log: Path, sim_dir: Path, output_dir: Path, cfld: bool) -> Path:
    env = os.environ.copy()
    if DEPS.exists():
        env["PYTHONPATH"] = f"{DEPS}:{env.get('PYTHONPATH', '')}"
    cmd = [sys.executable, str(script.resolve())]
    if cfld:
        cmd.append("-cfld")
    cmd.extend([str(original_log.resolve()), str(sim_dir.resolve())])
    subprocess.run(cmd, cwd=output_dir, env=env, check=True)
    return output_dir / "output.csv"


def add_short_names(path: Path) -> Path:
    renamed = path.with_name("chapela_distances.csv")
    with path.open(newline="", encoding="utf-8") as src, renamed.open("w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        fieldnames = ["mode", *reader.fieldnames]
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            name = Path(row["name"]).stem
            mode = name.removeprefix("simulated_")
            writer.writerow({"mode": mode, **row})
    return renamed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-log", type=Path, required=True)
    parser.add_argument("--simulated-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--distance-script",
        type=Path,
        required=True,
        help="Path to Chapela-Campa et al.'s ComputeLogDistance.py from the Zenodo artifact.",
    )
    parser.add_argument("--cfld", action="store_true", help="Also compute the expensive CFLD measure.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    simulated_dir = args.simulated_dir.resolve()
    original_log = args.original_log.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script = prepare_script(args.distance_script.resolve(), output_dir)
    sim_dir = copy_simulated_logs(simulated_dir, output_dir)
    raw_output = run_distance_script(script, original_log, sim_dir, output_dir, args.cfld)
    renamed = add_short_names(raw_output)
    print(renamed)


if __name__ == "__main__":
    main()
