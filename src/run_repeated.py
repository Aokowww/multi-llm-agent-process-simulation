#!/usr/bin/env python3
"""Run repeated simulations and aggregate metric stability."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from pathlib import Path

from pilot_simulation import (
    OpenAICompatibleResourceSelector,
    evaluate,
    first_case_start,
    learn_profiles,
    read_log,
    simulate,
    write_log,
    write_table,
)


METRIC_NAMES = [
    "trace_variant_distance",
    "activity_distribution_distance",
    "resource_distribution_distance",
    "mean_cycle_time_relative_error",
]


def summarize(rows: list[dict]) -> list[dict]:
    modes = sorted({row["mode"] for row in rows})
    summary = []
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode]
        item = {"mode": mode, "runs": len(mode_rows)}
        for metric in METRIC_NAMES:
            values = [float(row[metric]) for row in mode_rows]
            item[f"{metric}_mean"] = statistics.mean(values)
            item[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            item[f"{metric}_min"] = min(values)
            item[f"{metric}_max"] = max(values)
        summary.append(item)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-log", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--save-logs", action="store_true")
    parser.add_argument("--include-real-llm", action="store_true")
    parser.add_argument("--llm-model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument(
        "--llm-base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
    )
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = read_log(args.train_log)
    test = read_log(args.test_log)
    profiles = learn_profiles(train)
    n_cases = len({row["case_id"] for row in test})
    base_start = first_case_start(test)
    (args.output_dir / "learned_profiles.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")

    rows = []
    modes = ["central_baseline", "agent_profile", "llm_agent_proxy"]
    if args.include_real_llm:
        modes.append("llm_agent_real")
    api_key = os.getenv("OPENAI_API_KEY")
    if args.include_real_llm and not api_key:
        print("OPENAI_API_KEY is not set; llm_agent_real will use guarded fallback decisions.")
    for run_index in range(args.runs):
        for mode_index, mode in enumerate(modes):
            run_seed = args.seed + run_index * 100 + mode_index
            llm_selector = None
            if mode == "llm_agent_real" and api_key:
                llm_selector = OpenAICompatibleResourceSelector(
                    model=args.llm_model,
                    api_key=api_key,
                    base_url=args.llm_base_url,
                    timeout=args.llm_timeout,
                )
            generated, reasoning_rows, handover_rows = simulate(
                profiles,
                n_cases,
                mode,
                run_seed,
                base_start=base_start,
                llm_selector=llm_selector,
            )
            result = {
                "run": run_index + 1,
                "seed": run_seed,
                "mode": mode,
                **evaluate(test, generated),
                "generated_events": len(generated),
                "reasoning_rows": len(reasoning_rows),
                "handover_rows": len(handover_rows),
            }
            if mode == "llm_agent_real":
                result.update(
                    {
                        "llm_model": args.llm_model,
                        "llm_calls": llm_selector.calls if llm_selector else 0,
                        "llm_invalid_outputs": llm_selector.invalid_outputs if llm_selector else 0,
                        "llm_fallbacks": llm_selector.fallbacks if llm_selector else len(reasoning_rows),
                    }
                )
            rows.append(result)
            if args.save_logs:
                run_dir = args.output_dir / f"run_{run_index + 1:02d}"
                write_log(run_dir / f"simulated_{mode}.csv", generated)
                if reasoning_rows:
                    write_table(
                        run_dir / f"reasoning_{mode}.csv",
                        reasoning_rows,
                        list(reasoning_rows[0].keys()),
                    )
                if handover_rows:
                    write_table(
                        run_dir / f"handover_{mode}.csv",
                        handover_rows,
                        list(handover_rows[0].keys()),
                    )

    run_fields = sorted({key for row in rows for key in row})
    with (args.output_dir / "metrics_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=run_fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    summary_fields = list(summary[0].keys())
    with (args.output_dir / "metrics_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary)

    (args.output_dir / "metrics_runs.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (args.output_dir / "metrics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
