#!/usr/bin/env python3
"""Evaluate resource decisions independently of end-to-end log distances."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

from pilot_simulation import (
    OpenAICompatibleResourceSelector,
    learn_profiles,
    normalized_priors,
    parse_dt,
    read_log,
    top_items,
    write_table,
)
from run_repeated import PROVIDERS, select_cases


def argmax_resource(candidates: dict[str, int]) -> str:
    return min(candidates, key=lambda resource: (-candidates[resource], resource))


def decision_contexts(rows: list[dict], profiles: dict) -> list[dict]:
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)

    contexts = []
    for case_id, events in by_case.items():
        events.sort(key=lambda row: parse_dt(row["start_time"]))
        previous_resource = None
        for step_index, event in enumerate(events, start=1):
            activity = event["activity"]
            activity_candidates = profiles["capabilities"].get(activity, {})
            handover_key = f"{previous_resource}||{activity}" if previous_resource else ""
            handover_candidates = profiles.get("handover_priors", {}).get(handover_key, {})
            local_candidates = {
                resource: count
                for resource, count in (handover_candidates or activity_candidates).items()
                if resource in activity_candidates
            }
            if not local_candidates:
                local_candidates = activity_candidates
            contexts.append(
                {
                    "case_id": case_id,
                    "step_index": step_index,
                    "activity": activity,
                    "previous_resource": previous_resource,
                    "actual_resource": event["resource"],
                    "activity_candidates": activity_candidates,
                    "local_candidates": local_candidates,
                    "used_handover_context": bool(handover_candidates),
                }
            )
            previous_resource = event["resource"]
    return contexts


def sample_contexts(contexts: list[dict], max_decisions: int | None, seed: int) -> list[dict]:
    if not max_decisions or max_decisions >= len(contexts):
        return contexts
    rng = random.Random(seed)
    return [contexts[index] for index in sorted(rng.sample(range(len(contexts)), max_decisions))]


def summarize(rows: list[dict], total_contexts: int) -> list[dict]:
    output = []
    for policy in sorted({row["policy"] for row in rows}):
        group = [row for row in rows if row["policy"] == policy]
        covered = [row for row in group if row["actual_resource_feasible"]]
        output.append(
            {
                "policy": policy,
                "sampled_decisions": total_contexts,
                "evaluated_decisions": len(group),
                "actual_resource_coverage": len(covered) / total_contexts if total_contexts else 0.0,
                "top1_accuracy": sum(row["correct"] for row in covered) / len(covered) if covered else 0.0,
                "handover_context_share": sum(row["used_handover_context"] for row in group) / len(group)
                if group
                else 0.0,
                "mean_feasible_resources": sum(row["feasible_resource_count"] for row in group) / len(group)
                if group
                else 0.0,
                "fallback_rate": sum(row["fallback"] for row in group) / len(group) if group else 0.0,
                "reason_mentions_action_rate": sum(row["reason_mentions_action"] for row in group) / len(group)
                if group
                else 0.0,
                "valid_factor_rate": sum(row["valid_factors"] for row in group) / len(group) if group else 0.0,
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-log", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-cases", type=int, default=100)
    parser.add_argument("--max-decisions", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7300)
    parser.add_argument("--include-real-llm", action="store_true")
    parser.add_argument("--llm-provider", choices=sorted(PROVIDERS), default="groq")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-api-key-env")
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    parser.add_argument("--llm-min-interval", type=float)
    args = parser.parse_args()

    train = read_log(args.train_log)
    test = select_cases(read_log(args.test_log), args.max_cases, args.seed)
    profiles = learn_profiles(train)
    contexts = sample_contexts(decision_contexts(test, profiles), args.max_decisions, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    provider = PROVIDERS[args.llm_provider]
    model = args.llm_model or provider["model"]
    base_url = args.llm_base_url or provider["base_url"]
    api_key_env = args.llm_api_key_env or provider["api_key_env"]
    min_interval = args.llm_min_interval if args.llm_min_interval is not None else provider["min_interval"]
    selector = None
    if args.include_real_llm:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set; a real-LLM decision benchmark cannot run.")
        selector = OpenAICompatibleResourceSelector(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=args.llm_timeout,
            min_interval=min_interval,
            seed=args.seed,
            cache_path=args.output_dir / "llm_response_cache.jsonl",
        )

    rows = []
    resource_usage = Counter()
    valid_factor_names = {"historical_capability", "handover_continuity", "workload_balance"}
    for context in contexts:
        actual = context["actual_resource"]
        local = context["local_candidates"]
        activity_candidates = context["activity_candidates"]
        policies = {
            "activity_prior_argmax": argmax_resource(activity_candidates) if activity_candidates else "",
            "handover_prior_argmax": argmax_resource(local) if local else "",
        }
        llm_reason = ""
        llm_factors: list[str] = []
        fallback = False
        if selector and local:
            try:
                decision = selector.choose(
                    context["activity"],
                    context["previous_resource"],
                    local,
                    normalized_priors(activity_candidates),
                    resource_usage,
                    reason_hint="handover_prior_argmax",
                )
                policies["llm_agent_real"] = decision["resource"]
                llm_reason = decision["reason"]
                llm_factors = [str(value) for value in decision.get("factors", [])]
            except Exception:
                selector.fallbacks += 1
                policies["llm_agent_real"] = policies["handover_prior_argmax"]
                fallback = True

        for policy, selected in policies.items():
            reason = llm_reason if policy == "llm_agent_real" else ""
            factors = llm_factors if policy == "llm_agent_real" else []
            rows.append(
                {
                    "case_id": context["case_id"],
                    "step_index": context["step_index"],
                    "activity": context["activity"],
                    "previous_resource": context["previous_resource"] or "",
                    "actual_resource": actual,
                    "selected_resource": selected,
                    "policy": policy,
                    "correct": int(selected == actual),
                    "actual_resource_feasible": int(actual in local),
                    "used_handover_context": int(context["used_handover_context"]),
                    "feasible_resource_count": len(local),
                    "feasible_resources_top": "|".join(top_items(local)),
                    "fallback": int(fallback if policy == "llm_agent_real" else False),
                    "reason": reason,
                    "factors": "|".join(factors),
                    "reason_mentions_action": int(bool(reason) and selected.lower() in reason.lower()),
                    "valid_factors": int(bool(factors) and set(factors).issubset(valid_factor_names)),
                }
            )
        resource_usage[actual] += 1

    write_table(args.output_dir / "decision_rows.csv", rows, list(rows[0].keys()))
    summary = summarize(rows, len(contexts))
    write_table(args.output_dir / "decision_summary.csv", summary, list(summary[0].keys()))
    (args.output_dir / "decision_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    metadata = {
        "train_log": str(args.train_log),
        "test_log": str(args.test_log),
        "sampled_cases": len({row["case_id"] for row in test}),
        "sampled_decisions": len(contexts),
        "seed": args.seed,
        "real_llm_included": bool(selector),
        "llm_provider": args.llm_provider if selector else None,
        "llm_model": model if selector else None,
        "llm_api_key_env": api_key_env if selector else None,
    }
    if selector:
        metadata.update(selector.summary())
        write_table(
            args.output_dir / "llm_call_diagnostics.csv",
            selector.call_diagnostics,
            list(selector.call_diagnostics[0].keys()),
        )
    (args.output_dir / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
