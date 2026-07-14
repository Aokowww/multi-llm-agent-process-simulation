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


PROVIDERS = {
    "groq": {
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b",
        "min_interval": 4.2,
    },
    "gemini": {
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash-lite",
        "min_interval": 4.1,
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/free",
        "min_interval": 3.1,
    },
    "custom": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "min_interval": 0.0,
    },
}


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


def select_cases(rows: list[dict], max_cases: int | None, seed: int) -> list[dict]:
    if not max_cases:
        return rows
    cases = sorted({row["case_id"] for row in rows})
    if max_cases >= len(cases):
        return rows
    import random

    rng = random.Random(seed)
    selected = set(rng.sample(cases, max_cases))
    return [row for row in rows if row["case_id"] in selected]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-log", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--save-logs", action="store_true")
    parser.add_argument("--include-real-llm", action="store_true")
    parser.add_argument("--include-resource-agent-prototypes", action="store_true")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--llm-provider", choices=sorted(PROVIDERS), default="groq")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-api-key-env")
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    parser.add_argument("--llm-min-interval", type=float)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = read_log(args.train_log)
    test = select_cases(read_log(args.test_log), args.max_cases, args.seed)
    profiles = learn_profiles(train)
    n_cases = len({row["case_id"] for row in test})
    base_start = first_case_start(test)
    (args.output_dir / "learned_profiles.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    write_log(args.output_dir / "observed_test_subset.csv", test)

    provider = PROVIDERS[args.llm_provider]
    llm_model = args.llm_model or provider["model"]
    llm_base_url = args.llm_base_url or provider["base_url"]
    llm_api_key_env = args.llm_api_key_env or provider["api_key_env"]
    llm_min_interval = args.llm_min_interval if args.llm_min_interval is not None else provider["min_interval"]

    rows = []
    modes = ["central_baseline", "agent_profile", "llm_agent_proxy"]
    if args.include_resource_agent_prototypes:
        modes.extend(["resource_agent_orchestrated", "resource_agent_autonomous"])
    if args.include_real_llm:
        modes.append("llm_agent_real")
    api_key = os.getenv(llm_api_key_env)
    if args.include_real_llm and not api_key:
        raise RuntimeError(
            f"{llm_api_key_env} is not set. Refusing to label fallback-only output as a real-LLM experiment."
        )
    for run_index in range(args.runs):
        for mode in modes:
            run_seed = args.seed + run_index * 100
            run_dir = args.output_dir / f"run_{run_index + 1:02d}"
            llm_selector = None
            if mode == "llm_agent_real" and api_key:
                llm_selector = OpenAICompatibleResourceSelector(
                    model=llm_model,
                    api_key=api_key,
                    base_url=llm_base_url,
                    timeout=args.llm_timeout,
                    min_interval=llm_min_interval,
                    seed=run_seed,
                    cache_path=run_dir / "llm_response_cache.jsonl",
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
                result.update(llm_selector.summary())
                result["llm_provider"] = args.llm_provider
            rows.append(result)
            if args.save_logs:
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
                if mode == "llm_agent_real" and llm_selector.call_diagnostics:
                    write_table(
                        run_dir / "llm_call_diagnostics.csv",
                        llm_selector.call_diagnostics,
                        list(llm_selector.call_diagnostics[0].keys()),
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
    experiment_metadata = {
        "train_log": str(args.train_log),
        "test_log": str(args.test_log),
        "evaluated_cases": n_cases,
        "runs": args.runs,
        "seed": args.seed,
        "real_llm_included": args.include_real_llm,
        "resource_agent_prototypes_included": args.include_resource_agent_prototypes,
        "llm_provider": args.llm_provider if args.include_real_llm else None,
        "llm_model": llm_model if args.include_real_llm else None,
        "llm_api_key_env": llm_api_key_env if args.include_real_llm else None,
        "llm_base_url": llm_base_url if args.include_real_llm else None,
        "llm_min_interval": llm_min_interval if args.include_real_llm else None,
    }
    (args.output_dir / "experiment_metadata.json").write_text(
        json.dumps(experiment_metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
