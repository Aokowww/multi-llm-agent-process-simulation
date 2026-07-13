#!/usr/bin/env python3
"""Pilot simulator for event-log-grounded agentic BPS.

The script intentionally uses a small synthetic log when no real log is provided.
It validates the experimental pipeline: learn profiles, simulate variants, and
compute lightweight log-distance metrics.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


SCHEMA = ["case_id", "activity", "resource", "start_time", "end_time"]
REASONING_SCHEMA = [
    "case_id",
    "step_index",
    "mode",
    "previous_resource",
    "activity",
    "selected_resource",
    "feasible_resource_count",
    "feasible_resources_top",
    "historical_prior",
    "selection_rule",
    "factors",
    "reason",
]
HANDOVER_SCHEMA = ["case_id", "from_resource", "to_resource", "activity", "timestamp", "message"]
ACTIVITIES = ["Submit", "Check", "Review", "Approve"]
RESOURCES = ["Alice", "Bob", "Cara"]
AGENTIC_MODES = {"llm_agent_proxy", "llm_agent_real"}


def parse_dt(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(normalized, pattern)
            except ValueError:
                continue
        raise


def fmt_dt(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def write_log(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(rows)


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_log(path: Path) -> list[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generate_synthetic_log(n_cases: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    base = datetime(2026, 1, 5, 9, 0, 0)
    skill = {
        "Submit": ["Alice", "Bob", "Cara"],
        "Check": ["Alice", "Bob"],
        "Review": ["Bob", "Cara"],
        "Approve": ["Cara"],
    }
    mean_minutes = {
        ("Alice", "Submit"): 16,
        ("Bob", "Submit"): 20,
        ("Cara", "Submit"): 24,
        ("Alice", "Check"): 35,
        ("Bob", "Check"): 28,
        ("Bob", "Review"): 42,
        ("Cara", "Review"): 38,
        ("Cara", "Approve"): 30,
    }
    for case in range(n_cases):
        t = base + timedelta(minutes=case * rng.randint(12, 30))
        case_id = f"C{case:04d}"
        for activity in ACTIVITIES:
            resource = rng.choice(skill[activity])
            wait = rng.randint(2, 25)
            start = t + timedelta(minutes=wait)
            mean = mean_minutes[(resource, activity)]
            duration = max(5, int(rng.gauss(mean, mean * 0.25)))
            end = start + timedelta(minutes=duration)
            rows.append(
                {
                    "case_id": case_id,
                    "activity": activity,
                    "resource": resource,
                    "start_time": fmt_dt(start),
                    "end_time": fmt_dt(end),
                }
            )
            t = end
    return rows


def split_by_case(rows: list[dict], test_ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    cases = sorted({r["case_id"] for r in rows})
    rng.shuffle(cases)
    n_test = max(1, int(len(cases) * test_ratio))
    test_cases = set(cases[:n_test])
    train, test = [], []
    for row in rows:
        (test if row["case_id"] in test_cases else train).append(row)
    return train, test


def learn_profiles(rows: list[dict]) -> dict:
    capabilities = defaultdict(Counter)
    durations = defaultdict(list)
    duration_fallbacks = defaultdict(list)
    waits = defaultdict(list)
    wait_fallbacks = defaultdict(list)
    handovers = defaultdict(Counter)
    activity_counts = Counter()
    resource_counts = Counter()
    by_case = defaultdict(list)
    for row in rows:
        resource = row["resource"]
        activity = row["activity"]
        start = parse_dt(row["start_time"])
        end = parse_dt(row["end_time"])
        capabilities[activity][resource] += 1
        duration = max(0, (end - start).total_seconds() / 60)
        durations[(resource, activity)].append(duration)
        duration_fallbacks[activity].append(duration)
        activity_counts[activity] += 1
        resource_counts[resource] += 1
        by_case[row["case_id"]].append(row)
    trace_variants = Counter()
    case_starts = []
    for events in by_case.values():
        events.sort(key=lambda r: parse_dt(r["start_time"]))
        case_starts.append(parse_dt(events[0]["start_time"]))
        trace_variants[tuple(e["activity"] for e in events)] += 1
        for previous, current in zip(events, events[1:]):
            previous_activity = previous["activity"]
            current_activity = current["activity"]
            wait = max(0, (parse_dt(current["start_time"]) - parse_dt(previous["end_time"])).total_seconds() / 60)
            waits[(previous_activity, current_activity)].append(wait)
            wait_fallbacks[current_activity].append(wait)
            handovers[(previous["resource"], current_activity)][current["resource"]] += 1
    mean_durations = {
        f"{resource}|{activity}": statistics.mean(values)
        for (resource, activity), values in durations.items()
    }
    case_starts.sort()
    interarrival_samples = [
        max(0, (current - previous).total_seconds() / 60)
        for previous, current in zip(case_starts, case_starts[1:])
    ]
    return {
        "capabilities": {a: dict(c) for a, c in capabilities.items()},
        "mean_durations": mean_durations,
        "duration_samples": {
            f"{resource}|{activity}": values
            for (resource, activity), values in durations.items()
        },
        "duration_fallback_samples": dict(duration_fallbacks),
        "wait_samples": {
            f"{previous}||{current}": values
            for (previous, current), values in waits.items()
        },
        "wait_fallback_samples": dict(wait_fallbacks),
        "handover_priors": {
            f"{previous_resource}||{activity}": dict(counter)
            for (previous_resource, activity), counter in handovers.items()
        },
        "case_interarrival_samples": interarrival_samples,
        "activity_counts": dict(activity_counts),
        "resource_counts": dict(resource_counts),
        "trace_variants": {"||".join(k): v for k, v in trace_variants.items()},
    }


def weighted_choice(counter: dict[str, int], rng: random.Random) -> str:
    total = sum(counter.values())
    pick = rng.uniform(0, total)
    upto = 0
    for key, weight in counter.items():
        upto += weight
        if upto >= pick:
            return key
    return next(iter(counter))


def normalized_priors(candidates: dict[str, int]) -> dict[str, float]:
    total = sum(candidates.values()) or 1
    return {resource: count / total for resource, count in candidates.items()}


def guarded_weighted_choice(
    candidates: dict[str, int],
    target_priors: dict[str, float],
    resource_usage: Counter,
    rng: random.Random,
) -> str:
    events_so_far = sum(resource_usage.values())
    adjusted = {}
    for resource, count in candidates.items():
        observed_share = resource_usage[resource] / events_so_far if events_so_far else 0.0
        target_share = target_priors.get(resource, 0.0)
        overuse_penalty = max(0.0, observed_share - target_share)
        adjusted[resource] = max(0.01, (count ** 0.5) / (1.0 + 8.0 * overuse_penalty))
    return weighted_choice(adjusted, rng)


def top_items(values: dict[str, int] | dict[str, float], limit: int = 12) -> dict:
    return dict(sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit])


class OpenAICompatibleResourceSelector:
    """Small OpenAI-compatible JSON client for constrained resource choices."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        min_interval: float = 0.0,
        seed: int | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = self._chat_completions_url(base_url)
        self.timeout = timeout
        self.min_interval = max(0.0, min_interval)
        self.seed = seed
        self.calls = 0
        self.successful_calls = 0
        self.invalid_outputs = 0
        self.fallbacks = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.total_latency_seconds = 0.0
        self.call_diagnostics: list[dict] = []
        self._last_request_at = 0.0

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    def choose(
        self,
        activity: str,
        previous_resource: str | None,
        candidates: dict[str, int],
        priors: dict[str, float],
        resource_usage: Counter,
        reason_hint: str,
    ) -> dict:
        feasible = [
            {
                "resource": resource,
                "historical_count": int(candidates[resource]),
                "historical_prior": round(priors.get(resource, 0.0), 6),
                "events_assigned_so_far": int(resource_usage[resource]),
            }
            for resource in sorted(candidates)
        ]
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 160,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a constrained business-process simulation agent. "
                        "Choose exactly one resource from feasible_resources. "
                        "Return only JSON with keys resource, reason, and factors. "
                        "The factors value must be a list containing one or more of "
                        "historical_capability, handover_continuity, and workload_balance. "
                        "Name the selected resource in the reason. "
                        "Do not invent resources, activities, timestamps, or schema fields."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "activity": activity,
                            "previous_resource": previous_resource,
                            "decision_goal": (
                                "Select a plausible next resource while respecting historical "
                                "capabilities, handover context, and workload balance."
                            ),
                            "feasible_resources": feasible,
                            "fallback_policy_if_uncertain": reason_hint,
                        },
                        sort_keys=True,
                    ),
                },
            ],
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        wait = self.min_interval - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        self.calls += 1
        started = time.monotonic()
        diagnostic = {
            "call": self.calls,
            "model": self.model,
            "activity": activity,
            "previous_resource": previous_resource or "",
            "feasible_resource_count": len(candidates),
            "status": "error",
            "selected_resource": "",
            "factors": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": 0.0,
            "error_type": "",
            "error_message": "",
        }
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                self._last_request_at = time.monotonic()
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            selected = str(parsed.get("resource", ""))
            factors = parsed.get("factors", [])
            if selected not in candidates:
                self.invalid_outputs += 1
                raise ValueError(f"LLM selected invalid resource: {selected!r}")
            if not isinstance(factors, list):
                factors = []
            usage = data.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.successful_calls += 1
            diagnostic.update(
                {
                    "status": "success",
                    "selected_resource": selected,
                    "factors": "|".join(str(value) for value in factors),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                }
            )
            return {
                "resource": selected,
                "reason": str(parsed.get("reason", "")).strip()
                or f"Selected feasible resource {selected}.",
                "factors": factors,
            }
        except Exception as exc:
            diagnostic["error_type"] = type(exc).__name__
            diagnostic["error_message"] = str(exc)[:500]
            raise
        finally:
            latency = time.monotonic() - started
            diagnostic["latency_seconds"] = round(latency, 6)
            self.total_latency_seconds += latency
            self.call_diagnostics.append(diagnostic)

    def summary(self) -> dict:
        return {
            "llm_model": self.model,
            "llm_calls": self.calls,
            "llm_successful_calls": self.successful_calls,
            "llm_invalid_outputs": self.invalid_outputs,
            "llm_fallbacks": self.fallbacks,
            "llm_prompt_tokens": self.prompt_tokens,
            "llm_completion_tokens": self.completion_tokens,
            "llm_total_tokens": self.total_tokens,
            "llm_total_latency_seconds": self.total_latency_seconds,
            "llm_mean_latency_seconds": self.total_latency_seconds / self.calls if self.calls else 0.0,
        }


def decide_resource(
    activity: str,
    previous_resource: str | None,
    profiles: dict,
    mode: str,
    rng: random.Random,
    resource_usage: Counter,
    llm_selector: OpenAICompatibleResourceSelector | None = None,
) -> dict:
    candidates = profiles["capabilities"].get(activity, {})
    if not candidates:
        selected = rng.choice(RESOURCES)
        return {
            "resource": selected,
            "feasible_resource_count": 1,
            "feasible_resources_top": selected,
            "historical_prior": "fallback",
            "selection_rule": "fallback_random",
            "factors": "fallback",
            "reason": "No learned capability set was available, so a fallback resource was sampled.",
        }
    priors = normalized_priors(candidates)
    if mode == "central_baseline":
        selected = rng.choice(list(candidates))
        rule = "uniform_capable_resource"
    if mode == "agent_profile":
        selected = weighted_choice(candidates, rng)
        rule = "activity_frequency_weighted"
    if mode in AGENTIC_MODES:
        handover_key = f"{previous_resource}||{activity}" if previous_resource is not None else ""
        handover_candidates = profiles.get("handover_priors", {}).get(handover_key)
        local_candidates = {
            resource: count
            for resource, count in (handover_candidates or candidates).items()
            if resource in candidates
        }
        if not local_candidates:
            local_candidates = candidates
        selected = guarded_weighted_choice(local_candidates, priors, resource_usage, rng)
        rule = "guarded_handover_prior" if handover_candidates else "guarded_activity_prior"
        candidates = local_candidates
        if mode == "llm_agent_real":
            if llm_selector is None:
                rule = f"real_llm_unavailable_fallback_{rule}"
            else:
                fallback_resource = selected
                fallback_rule = rule
                try:
                    llm_decision = llm_selector.choose(
                        activity,
                        previous_resource,
                        candidates,
                        priors,
                        resource_usage,
                        reason_hint=fallback_rule,
                    )
                    selected = llm_decision["resource"]
                    rule = f"real_llm_json_{fallback_rule}"
                    return {
                        "resource": selected,
                        "feasible_resource_count": len(candidates),
                        "feasible_resources_top": "|".join(top_items(candidates)),
                        "historical_prior": json.dumps(
                            {k: round(v, 4) for k, v in top_items(priors).items()},
                            sort_keys=True,
                        ),
                        "selection_rule": rule,
                        "factors": "|".join(llm_decision.get("factors", [])),
                        "reason": llm_decision["reason"],
                    }
                except (
                    ValueError,
                    KeyError,
                    IndexError,
                    TypeError,
                    json.JSONDecodeError,
                    urllib.error.URLError,
                    TimeoutError,
                ) as exc:
                    llm_selector.fallbacks += 1
                    selected = fallback_resource
                    rule = f"real_llm_fallback_{fallback_rule}"
                    return {
                        "resource": selected,
                        "feasible_resource_count": len(candidates),
                        "feasible_resources_top": "|".join(top_items(candidates)),
                        "historical_prior": json.dumps(
                            {k: round(v, 4) for k, v in top_items(priors).items()},
                            sort_keys=True,
                        ),
                        "selection_rule": rule,
                        "factors": "fallback",
                        "reason": (
                            f"Real LLM decision failed ({type(exc).__name__}); "
                            f"used guarded fallback resource {selected}."
                        ),
                    }
    if mode not in {"central_baseline", "agent_profile", *AGENTIC_MODES}:
        raise ValueError(f"Unknown mode: {mode}")
    return {
        "resource": selected,
        "feasible_resource_count": len(candidates),
        "feasible_resources_top": "|".join(top_items(candidates)),
        "historical_prior": json.dumps({k: round(v, 4) for k, v in top_items(priors).items()}, sort_keys=True),
        "selection_rule": rule,
        "factors": "handover_continuity|historical_capability|workload_balance"
        if mode in AGENTIC_MODES
        else "historical_capability",
        "reason": (
            f"Selected {selected} for {activity} from resource-local feasible candidates "
            f"using {rule}."
        ),
    }


def sample_empirical(values: list[float] | None, fallback: float, rng: random.Random) -> float:
    if values:
        return rng.choice(values)
    return fallback


def sample_duration(profiles: dict, resource: str, activity: str, rng: random.Random) -> float:
    key = f"{resource}|{activity}"
    values = profiles.get("duration_samples", {}).get(key)
    fallback_values = profiles.get("duration_fallback_samples", {}).get(activity)
    fallback = profiles.get("mean_durations", {}).get(key, 30.0)
    return max(0, sample_empirical(values or fallback_values, fallback, rng))


def sample_wait(profiles: dict, previous_activity: str | None, activity: str, rng: random.Random) -> float:
    if previous_activity is None:
        return 0
    key = f"{previous_activity}||{activity}"
    values = profiles.get("wait_samples", {}).get(key)
    fallback_values = profiles.get("wait_fallback_samples", {}).get(activity)
    return max(0, sample_empirical(values or fallback_values, 0.0, rng))


def sample_trace(profiles: dict, rng: random.Random) -> list[str]:
    variants = profiles.get("trace_variants", {})
    if not variants:
        return ACTIVITIES
    variant = weighted_choice(variants, rng)
    return variant.split("||")


def first_case_start(rows: list[dict]) -> datetime:
    return min(parse_dt(row["start_time"]) for row in rows)


def sample_case_interarrival(profiles: dict, rng: random.Random) -> float:
    samples = profiles.get("case_interarrival_samples", [])
    return max(0, sample_empirical(samples, 20.0, rng))


def simulate(
    profiles: dict,
    n_cases: int,
    mode: str,
    seed: int,
    base_start: datetime | None = None,
    llm_selector: OpenAICompatibleResourceSelector | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    structure_rng = random.Random(seed)
    decision_rng = random.Random(seed + 1_000_003)
    timing_rng = random.Random(seed + 2_000_003)
    rows = []
    reasoning_rows = []
    handover_rows = []
    resource_usage = Counter()
    t_arrival = base_start or datetime(2026, 2, 2, 9, 0, 0)
    for case in range(n_cases):
        if case > 0:
            t_arrival = t_arrival + timedelta(minutes=sample_case_interarrival(profiles, structure_rng))
        t = t_arrival
        case_id = f"S_{mode}_{case:04d}"
        previous_activity = None
        previous_resource = None
        for step_index, activity in enumerate(sample_trace(profiles, structure_rng), start=1):
            decision = decide_resource(
                activity,
                previous_resource,
                profiles,
                mode,
                decision_rng,
                resource_usage,
                llm_selector=llm_selector,
            )
            resource = decision["resource"]
            duration = sample_duration(profiles, resource, activity, timing_rng)
            wait = sample_wait(profiles, previous_activity, activity, timing_rng)
            start = t + timedelta(minutes=wait)
            end = start + timedelta(minutes=duration)
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
                        "factors": decision["factors"],
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
                                f"Handover for {activity}; selected {resource} from "
                                f"{decision['feasible_resource_count']} feasible resources."
                            ),
                        }
                    )
            t = end
            previous_activity = activity
            previous_resource = resource
    return rows, reasoning_rows, handover_rows


def traces(rows: list[dict]) -> Counter:
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    variants = Counter()
    for events in by_case.values():
        events.sort(key=lambda r: parse_dt(r["start_time"]))
        variants[tuple(e["activity"] for e in events)] += 1
    return variants


def distribution_distance(left: Counter, right: Counter) -> float:
    keys = set(left) | set(right)
    l_total = sum(left.values()) or 1
    r_total = sum(right.values()) or 1
    return 0.5 * sum(abs(left[k] / l_total - right[k] / r_total) for k in keys)


def cycle_times(rows: list[dict]) -> list[float]:
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    values = []
    for events in by_case.values():
        starts = [parse_dt(e["start_time"]) for e in events]
        ends = [parse_dt(e["end_time"]) for e in events]
        values.append((max(ends) - min(starts)).total_seconds() / 60)
    return values


def evaluate(reference: list[dict], generated: list[dict]) -> dict:
    ref_cycle = statistics.mean(cycle_times(reference))
    gen_cycle = statistics.mean(cycle_times(generated))
    return {
        "trace_variant_distance": distribution_distance(traces(reference), traces(generated)),
        "activity_distribution_distance": distribution_distance(
            Counter(r["activity"] for r in reference),
            Counter(r["activity"] for r in generated),
        ),
        "resource_distribution_distance": distribution_distance(
            Counter(r["resource"] for r in reference),
            Counter(r["resource"] for r in generated),
        ),
        "mean_cycle_time_reference": ref_cycle,
        "mean_cycle_time_generated": gen_cycle,
        "mean_cycle_time_relative_error": abs(gen_cycle - ref_cycle) / ref_cycle if ref_cycle else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-log", type=Path)
    parser.add_argument("--train-log", type=Path)
    parser.add_argument("--test-log", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("../05_results/pilot"))
    parser.add_argument("--cases", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-real-llm", action="store_true")
    parser.add_argument("--llm-model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument(
        "--llm-base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
    )
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.train_log and args.test_log:
        train, test = read_log(args.train_log), read_log(args.test_log)
    else:
        observed = read_log(args.input_log) if args.input_log else generate_synthetic_log(args.cases, args.seed)
        train, test = split_by_case(observed, 0.3, args.seed)
    profiles = learn_profiles(train)

    write_log(args.output_dir / "observed_train.csv", train)
    write_log(args.output_dir / "observed_test.csv", test)
    (args.output_dir / "learned_profiles.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")

    metrics = []
    n_cases = len({r["case_id"] for r in test})
    base_start = first_case_start(test)
    modes = ["central_baseline", "agent_profile", "llm_agent_proxy"]
    llm_selector = None
    if args.include_real_llm:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            llm_selector = OpenAICompatibleResourceSelector(
                model=args.llm_model,
                api_key=api_key,
                base_url=args.llm_base_url,
                timeout=args.llm_timeout,
            )
        else:
            print("OPENAI_API_KEY is not set; llm_agent_real will use guarded fallback decisions.")
        modes.append("llm_agent_real")
    for mode in modes:
        generated, reasoning_rows, handover_rows = simulate(
            profiles,
            n_cases,
            mode,
            args.seed + len(mode),
            base_start=base_start,
            llm_selector=llm_selector if mode == "llm_agent_real" else None,
        )
        write_log(args.output_dir / f"simulated_{mode}.csv", generated)
        if reasoning_rows:
            write_table(args.output_dir / f"reasoning_{mode}.csv", reasoning_rows, REASONING_SCHEMA)
        if handover_rows:
            write_table(args.output_dir / f"handover_{mode}.csv", handover_rows, HANDOVER_SCHEMA)
        result = {"mode": mode, **evaluate(test, generated)}
        if mode == "llm_agent_real":
            result.update(
                {
                    "llm_model": args.llm_model,
                    "llm_calls": llm_selector.calls if llm_selector else 0,
                    "llm_invalid_outputs": llm_selector.invalid_outputs if llm_selector else 0,
                    "llm_fallbacks": llm_selector.fallbacks if llm_selector else len(reasoning_rows),
                }
            )
        metrics.append(result)

    metric_fields = sorted({key for row in metrics for key in row})
    with (args.output_dir / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=metric_fields)
        writer.writeheader()
        writer.writerows(metrics)
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
