#!/usr/bin/env python3
"""Resource-agent discovery and simulation informed by AgentSimulator.

This module is an independent compatibility layer, not a copy of the upstream
implementation. It follows AgentSimulator's central modelling choices: one
stateful agent per observed resource, log-derived capabilities and processing
times, empirical calendars, and orchestrated or autonomous task allocation.
"""

from __future__ import annotations

import heapq
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean


RESOURCE_AGENT_MODES = {
    "resource_agent_orchestrated",
    "resource_agent_autonomous",
}


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def _fmt_dt(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _weighted_choice(weights: dict[str, int], rng: random.Random) -> str:
    total = sum(max(0, value) for value in weights.values())
    if total <= 0:
        return rng.choice(sorted(weights))
    pick = rng.uniform(0, total)
    cumulative = 0.0
    for key in sorted(weights):
        cumulative += max(0, weights[key])
        if cumulative >= pick:
            return key
    return sorted(weights)[-1]


def discover_resource_agent_profiles(rows: list[dict]) -> dict[str, dict]:
    """Discover JSON-serialisable, resource-centred profiles from an event log."""
    capabilities: dict[str, Counter] = defaultdict(Counter)
    durations: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    calendar_bounds: dict[str, dict[int, list[int]]] = defaultdict(dict)

    for row in rows:
        resource = row["resource"]
        activity = row["activity"]
        start = _parse_dt(row["start_time"])
        end = _parse_dt(row["end_time"])
        capabilities[resource][activity] += 1
        durations[resource][activity].append(max(0.0, (end - start).total_seconds() / 60.0))

        start_minute = start.hour * 60 + start.minute
        end_minute = end.hour * 60 + end.minute + (1 if end.second or end.microsecond else 0)
        if end.date() != start.date():
            end_minute = 1440
        bounds = calendar_bounds[resource].setdefault(start.weekday(), [start_minute, end_minute])
        bounds[0] = min(bounds[0], start_minute)
        bounds[1] = max(bounds[1], end_minute)

    signatures = sorted({tuple(sorted(values)) for values in capabilities.values()})
    role_by_signature = {signature: f"role_{index:03d}" for index, signature in enumerate(signatures, start=1)}
    profiles = {}
    for resource in sorted(capabilities):
        signature = tuple(sorted(capabilities[resource]))
        profiles[resource] = {
            "resource_id": resource,
            "agent_type": role_by_signature[signature],
            "capabilities": dict(capabilities[resource]),
            "duration_samples": dict(durations[resource]),
            "calendar": {
                str(weekday): bounds
                for weekday, bounds in sorted(calendar_bounds[resource].items())
            },
        }
    return profiles


@dataclass
class ResourceAgent:
    resource_id: str
    agent_type: str
    capabilities: dict[str, int]
    duration_samples: dict[str, list[float]]
    calendar: dict[str, list[int]]
    busy_until: datetime | None = None
    occupied_times: list[tuple[datetime, datetime]] = field(default_factory=list)
    assignment_count: int = 0
    memory: list[dict] = field(default_factory=list)

    @classmethod
    def from_profile(cls, profile: dict) -> "ResourceAgent":
        return cls(
            resource_id=profile["resource_id"],
            agent_type=profile["agent_type"],
            capabilities=dict(profile["capabilities"]),
            duration_samples={key: list(values) for key, values in profile["duration_samples"].items()},
            calendar={key: list(values) for key, values in profile.get("calendar", {}).items()},
        )

    def can_execute(self, activity: str) -> bool:
        return self.capabilities.get(activity, 0) > 0

    def expected_duration(self, activity: str) -> float:
        values = self.duration_samples.get(activity, [])
        return mean(values) if values else 30.0

    def _align_to_calendar(self, moment: datetime, duration_minutes: float) -> datetime:
        if not self.calendar:
            return moment
        for day_offset in range(15):
            day = moment + timedelta(days=day_offset)
            interval = self.calendar.get(str(day.weekday()))
            if not interval:
                continue
            start_minute, end_minute = interval
            shift_start = day.replace(
                hour=start_minute // 60,
                minute=start_minute % 60,
                second=0,
                microsecond=0,
            )
            if end_minute >= 1440:
                shift_end = shift_start.replace(hour=0, minute=0) + timedelta(days=1)
            else:
                shift_end = day.replace(
                    hour=end_minute // 60,
                    minute=end_minute % 60,
                    second=0,
                    microsecond=0,
                )
            candidate = max(moment, shift_start) if day_offset == 0 else shift_start
            duration = timedelta(minutes=duration_minutes)
            if candidate < shift_end and (candidate + duration <= shift_end or duration >= shift_end - shift_start):
                return candidate
        return moment

    def available_at(self, ready_time: datetime, duration_minutes: float) -> datetime:
        earliest = max(ready_time, self.busy_until) if self.busy_until else ready_time
        return self._align_to_calendar(earliest, duration_minutes)

    def assign(self, case_id: str, activity: str, start: datetime, end: datetime) -> None:
        if self.busy_until and start < self.busy_until:
            raise ValueError(f"Overlapping assignment for resource {self.resource_id}")
        self.busy_until = end
        self.occupied_times.append((start, end))
        self.assignment_count += 1
        self.memory.append(
            {
                "case_id": case_id,
                "activity": activity,
                "start_time": _fmt_dt(start),
                "end_time": _fmt_dt(end),
            }
        )


@dataclass(frozen=True)
class AgentDecisionContext:
    case_id: str
    activity: str
    previous_activity: str | None
    previous_resource: str | None
    ready_time: datetime


class StatisticalAgentPolicy:
    """AgentSimulator-style statistical allocation with two coordination modes."""

    def __init__(self, mode: str, handover_priors: dict[str, dict[str, int]], rng: random.Random):
        if mode not in RESOURCE_AGENT_MODES:
            raise ValueError(f"Unknown resource-agent mode: {mode}")
        self.mode = mode
        self.handover_priors = handover_priors
        self.rng = rng

    def choose(self, context: AgentDecisionContext, candidates: list[ResourceAgent]) -> ResourceAgent:
        if self.mode == "resource_agent_orchestrated":
            return min(
                candidates,
                key=lambda agent: (
                    agent.available_at(context.ready_time, agent.expected_duration(context.activity)),
                    -agent.capabilities.get(context.activity, 0),
                    agent.assignment_count,
                    agent.resource_id,
                ),
            )

        handover_key = (
            f"{context.previous_resource}||{context.previous_activity}||{context.activity}"
        )
        handover = self.handover_priors.get(handover_key, {}) if context.previous_resource else {}
        available_times = {
            agent.resource_id: agent.available_at(
                context.ready_time,
                agent.expected_duration(context.activity),
            )
            for agent in candidates
        }
        immediately_available = [
            agent for agent in candidates if available_times[agent.resource_id] <= context.ready_time
        ]
        if immediately_available:
            candidates = immediately_available
        else:
            earliest = min(available_times.values())
            candidates = [agent for agent in candidates if available_times[agent.resource_id] == earliest]
        weights = {
            agent.resource_id: handover.get(
                agent.resource_id,
                agent.capabilities.get(context.activity, 0),
            )
            for agent in candidates
        }
        selected = _weighted_choice(weights, self.rng)
        return next(agent for agent in candidates if agent.resource_id == selected)


def _sample(values: list[float] | None, fallback: float, rng: random.Random) -> float:
    return max(0.0, rng.choice(values) if values else fallback)


def _sample_trace(profiles: dict, rng: random.Random) -> list[str]:
    variants = profiles.get("trace_variants", {})
    if not variants:
        return []
    return _weighted_choice(variants, rng).split("||")


def simulate_resource_agent_process(
    profiles: dict,
    n_cases: int,
    mode: str,
    seed: int,
    base_start: datetime,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Run a chronological, stateful resource-agent simulation."""
    agent_profiles = profiles.get("resource_agents", {})
    if not agent_profiles:
        raise ValueError("Profiles do not contain discovered resource agents")
    agents = {key: ResourceAgent.from_profile(value) for key, value in agent_profiles.items()}
    structure_rng = random.Random(seed)
    decision_rng = random.Random(seed + 1_000_003)
    timing_rng = random.Random(seed + 2_000_003)
    policy = StatisticalAgentPolicy(mode, profiles.get("detailed_handover_priors", {}), decision_rng)

    case_states = {}
    queue = []
    arrival = base_start
    interarrivals = profiles.get("case_interarrival_samples", [])
    for case_index in range(n_cases):
        if case_index:
            arrival += timedelta(minutes=_sample(interarrivals, 20.0, structure_rng))
        case_id = f"S_{mode}_{case_index:04d}"
        trace = _sample_trace(profiles, structure_rng)
        case_states[case_id] = {"trace": trace, "previous_activity": None, "previous_resource": None}
        if trace:
            heapq.heappush(queue, (arrival, case_index, case_id, 0))

    rows = []
    handovers = []
    while queue:
        ready_time, case_index, case_id, step_index = heapq.heappop(queue)
        state = case_states[case_id]
        activity = state["trace"][step_index]
        previous_activity = state["previous_activity"]
        previous_resource = state["previous_resource"]
        candidates = [agent for agent in agents.values() if agent.can_execute(activity)]
        if not candidates:
            raise ValueError(f"No resource agent can execute activity {activity}")
        context = AgentDecisionContext(
            case_id,
            activity,
            previous_activity,
            previous_resource,
            ready_time,
        )
        agent = policy.choose(context, candidates)
        duration = _sample(agent.duration_samples.get(activity), agent.expected_duration(activity), timing_rng)
        start = agent.available_at(ready_time, duration)
        end = start + timedelta(minutes=duration)
        agent.assign(case_id, activity, start, end)
        rows.append(
            {
                "case_id": case_id,
                "activity": activity,
                "resource": agent.resource_id,
                "start_time": _fmt_dt(start),
                "end_time": _fmt_dt(end),
            }
        )
        if previous_resource and previous_resource != agent.resource_id:
            handovers.append(
                {
                    "case_id": case_id,
                    "from_resource": previous_resource,
                    "to_resource": agent.resource_id,
                    "activity": activity,
                    "timestamp": _fmt_dt(start),
                    "message": f"Task allocated by {mode} policy.",
                }
            )
        state["previous_activity"] = activity
        state["previous_resource"] = agent.resource_id
        if step_index + 1 < len(state["trace"]):
            heapq.heappush(queue, (end, case_index, case_id, step_index + 1))

    rows.sort(key=lambda row: (_parse_dt(row["start_time"]), row["case_id"], row["activity"]))
    return rows, [], handovers
