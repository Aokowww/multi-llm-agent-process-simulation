#!/usr/bin/env python3
"""Per-resource bidding policy for the patched upstream AgentSimulator."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from llm_bid_client import DeterministicBidClient


class AgentSimulatorAllocationPolicy:
    """Collect independent local bids and rank the selected agent first."""

    def __init__(self, bid_client=None, top_k: int = 2, memory_size: int = 3):
        self.bid_client = bid_client or DeterministicBidClient()
        self.top_k = max(1, top_k)
        self.memory_size = max(0, memory_size)
        self.agent_memory: dict[str, list[dict]] = defaultdict(list)
        self.assignment_counts = Counter()
        self.allocation_traces: list[dict] = []
        self.bid_traces: list[dict] = []
        self.pending_by_case: dict[str, int] = {}
        self.fallbacks = 0

    @staticmethod
    def _resource_name(agent_id, model) -> str:
        return str(model.agent_to_resource.get(agent_id, agent_id))

    @staticmethod
    def _agent_type(agent_id, model) -> str:
        return str(
            next(
                (role for role, values in model.roles.items() if agent_id in values["agents"]),
                "unassigned_role",
            )
        )

    def _shortlist(self, activity: str, candidate_ids: list, context: dict, model) -> tuple[list, Counter]:
        counts = Counter(
            model.data.loc[
                (model.data["activity_name"] == activity)
                & (model.data["agent"].isin(candidate_ids)),
                "agent",
            ].tolist()
        )
        ready_ids = [
            agent_id
            for agent_id in candidate_ids
            if model.agents_busy_until.get(agent_id) <= context["current_timestamp"]
        ]
        pool = ready_ids or sorted(
            candidate_ids,
            key=lambda agent_id: (model.agents_busy_until.get(agent_id), agent_id),
        )
        ranked = sorted(
            pool,
            key=lambda agent_id: (
                self.assignment_counts[self._resource_name(agent_id, model)],
                -counts.get(agent_id, 0),
                self._resource_name(agent_id, model),
            ),
        )
        return ranked[: self.top_k], counts

    def rank(self, context: dict, candidate_ids: list, model) -> list:
        activity = context["activity"]
        shortlisted, counts = self._shortlist(activity, candidate_ids, context, model)
        total_activity_count = sum(counts.values()) or 1
        previous_agent = context.get("previous_agent")
        previous_resource = (
            self._resource_name(previous_agent, model) if previous_agent not in (-1, None) else None
        )
        valid_bids = []
        bid_indices = []
        for agent_id in shortlisted:
            resource = self._resource_name(agent_id, model)
            profile = {
                "resource": resource,
                "agent_type": self._agent_type(agent_id, model),
                "capability_count": int(counts.get(agent_id, 0)),
                "activity_prior": round(counts.get(agent_id, 0) / total_activity_count, 6),
                "assignment_count": int(self.assignment_counts[resource]),
                "available_at": str(model.agents_busy_until.get(agent_id)),
                "recent_tasks": self.agent_memory[resource][-self.memory_size :] if self.memory_size else [],
            }
            bid_context = {
                "agent_profile": profile,
                "task": {
                    "case_id": str(context["case_id"]),
                    "activity": activity,
                    "previous_activity": context.get("previous_activity"),
                    "previous_resource": previous_resource,
                    "current_timestamp": str(context["current_timestamp"]),
                },
            }
            error_type = ""
            try:
                bid = self.bid_client.bid(bid_context)
                valid = True
            except Exception as exc:
                self.fallbacks += 1
                valid = False
                error_type = type(exc).__name__
                bid = {
                    "accept": False,
                    "suitability": 0.0,
                    "expected_delay_minutes": 0.0,
                    "reason": f"Bid failed ({error_type}).",
                }
            bid_trace = {
                "case_id": str(context["case_id"]),
                "activity": activity,
                "resource": resource,
                "agent_type": profile["agent_type"],
                "valid": str(valid).lower(),
                "accept": str(bid["accept"]).lower(),
                "suitability": bid["suitability"],
                "expected_delay_minutes": bid["expected_delay_minutes"],
                "reason": bid["reason"],
                "memory_items": len(profile["recent_tasks"]),
                "error_type": error_type,
                "selected": "false",
            }
            self.bid_traces.append(bid_trace)
            bid_index = len(self.bid_traces) - 1
            bid_indices.append(bid_index)
            if valid and bid["accept"]:
                valid_bids.append((agent_id, bid, bid_index))

        selection_rule = "highest_valid_agent_bid"
        if valid_bids:
            selected_id, selected_bid, selected_bid_index = min(
                valid_bids,
                key=lambda item: (
                    -float(item[1]["suitability"]),
                    float(item[1]["expected_delay_minutes"]),
                    -counts.get(item[0], 0),
                    self._resource_name(item[0], model),
                ),
            )
        else:
            selection_rule = "no_accepted_bid_activity_prior_fallback"
            selected_id = min(
                shortlisted,
                key=lambda agent_id: (-counts.get(agent_id, 0), self._resource_name(agent_id, model)),
            )
            selected_bid_index = next(
                index
                for index in bid_indices
                if self.bid_traces[index]["resource"] == self._resource_name(selected_id, model)
            )
        self.bid_traces[selected_bid_index]["selected"] = "true"
        selected_resource = self._resource_name(selected_id, model)
        ranked_ids = [selected_id] + [agent_id for agent_id in candidate_ids if agent_id != selected_id]
        accepted_scores = [float(item[1]["suitability"]) for item in valid_bids]
        allocation = {
            "case_id": str(context["case_id"]),
            "activity": activity,
            "previous_activity": context.get("previous_activity") or "",
            "previous_resource": previous_resource or "",
            "decision_timestamp": str(context["current_timestamp"]),
            "candidate_count": len(candidate_ids),
            "shortlist_count": len(shortlisted),
            "shortlist_resources": "|".join(self._resource_name(value, model) for value in shortlisted),
            "valid_bid_count": sum(self.bid_traces[index]["valid"] == "true" for index in bid_indices),
            "accepted_bid_count": len(valid_bids),
            "bid_score_range": max(accepted_scores) - min(accepted_scores) if accepted_scores else 0.0,
            "proposed_resource": selected_resource,
            "executed_resource": "",
            "proposal_accepted": "",
            "selection_rule": selection_rule,
            "bid_indices": json.dumps(bid_indices),
        }
        self.allocation_traces.append(allocation)
        self.pending_by_case[str(context["case_id"])] = len(self.allocation_traces) - 1
        return ranked_ids

    def record_execution(self, case_id, executed_agent_id, timestamp, model) -> None:
        trace_index = self.pending_by_case.pop(str(case_id), None)
        if trace_index is None:
            return
        trace = self.allocation_traces[trace_index]
        resource = self._resource_name(executed_agent_id, model)
        trace["executed_resource"] = resource
        trace["proposal_accepted"] = str(resource == trace["proposed_resource"]).lower()
        trace["execution_timestamp"] = str(timestamp)
        self.assignment_counts[resource] += 1
        self.agent_memory[resource].append(
            {
                "case_id": str(case_id),
                "activity": trace["activity"],
                "timestamp": str(timestamp),
            }
        )

    def summary(self) -> dict:
        completed = [trace for trace in self.allocation_traces if trace["executed_resource"]]
        accepted = sum(trace["proposal_accepted"] == "true" for trace in completed)
        valid_bids = sum(trace["valid"] == "true" for trace in self.bid_traces)
        accepting_bids = sum(trace["accept"] == "true" for trace in self.bid_traces)
        disagreements = sum(
            trace["accepted_bid_count"] > 1 and float(trace["bid_score_range"]) > 0.05
            for trace in completed
        )
        return {
            "allocation_decisions": len(self.allocation_traces),
            "executed_decisions": len(completed),
            "agent_bids": len(self.bid_traces),
            "valid_bid_rate": valid_bids / len(self.bid_traces) if self.bid_traces else 0.0,
            "agent_acceptance_rate": accepting_bids / len(self.bid_traces) if self.bid_traces else 0.0,
            "proposal_execution_rate": accepted / len(completed) if completed else 0.0,
            "bid_disagreement_rate": disagreements / len(completed) if completed else 0.0,
            "policy_fallbacks": self.fallbacks,
            "agents_with_memory": sum(bool(values) for values in self.agent_memory.values()),
        }
