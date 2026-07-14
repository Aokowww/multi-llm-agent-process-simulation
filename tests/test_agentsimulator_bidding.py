import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentsimulator_policy_adapter import AgentSimulatorAllocationPolicy
from llm_bid_client import DeterministicBidClient, OpenAICompatibleBidClient


class AgentSimulatorBiddingTests(unittest.TestCase):
    def setUp(self):
        now = pd.Timestamp("2026-01-05T09:00:00Z")
        self.now = now
        self.model = SimpleNamespace(
            agent_to_resource={0: "R0", 1: "R1", 2: "R2"},
            roles={"Clerk": {"agents": [0, 1, 2]}},
            agents_busy_until={0: now, 1: now, 2: now},
            data=pd.DataFrame(
                [
                    {"agent": 0, "activity_name": "Check"},
                    {"agent": 0, "activity_name": "Check"},
                    {"agent": 1, "activity_name": "Check"},
                    {"agent": 2, "activity_name": "Check"},
                ]
            ),
            simulated_events=[],
        )
        self.context = {
            "case_id": 1,
            "activity": "Check",
            "previous_activity": "Submit",
            "previous_agent": 2,
            "current_timestamp": now,
        }

    def test_two_agents_submit_independent_bids(self):
        policy = AgentSimulatorAllocationPolicy(DeterministicBidClient(), top_k=2, memory_size=3)
        ranked = policy.rank(self.context, [0, 1, 2], self.model)
        self.assertEqual(len(policy.bid_traces), 2)
        self.assertEqual(len({row["resource"] for row in policy.bid_traces}), 2)
        self.assertEqual(set(ranked), {0, 1, 2})
        self.assertEqual(sum(row["selected"] == "true" for row in policy.bid_traces), 1)

    def test_memory_updates_only_executing_agent(self):
        policy = AgentSimulatorAllocationPolicy(DeterministicBidClient(), top_k=2, memory_size=3)
        ranked = policy.rank(self.context, [0, 1, 2], self.model)
        policy.record_execution(1, ranked[0], self.now, self.model)
        selected = self.model.agent_to_resource[ranked[0]]
        self.assertEqual(len(policy.agent_memory[selected]), 1)
        self.assertEqual(sum(len(values) for values in policy.agent_memory.values()), 1)

    def test_busy_agents_are_removed_before_shortlisting(self):
        self.model.agents_busy_until[0] = self.now + pd.Timedelta(hours=2)
        policy = AgentSimulatorAllocationPolicy(DeterministicBidClient(), top_k=2)
        policy.rank(self.context, [0, 1, 2], self.model)
        resources = {row["resource"] for row in policy.bid_traces}
        self.assertNotIn("R0", resources)

    def test_bid_schema_validation(self):
        valid = OpenAICompatibleBidClient._validate(
            {
                "accept": True,
                "suitability": 0.75,
                "expected_delay_minutes": 4,
                "reason": "I am available.",
            }
        )
        self.assertTrue(valid["accept"])
        with self.assertRaises(ValueError):
            OpenAICompatibleBidClient._validate(
                {
                    "accept": "yes",
                    "suitability": 1.2,
                    "expected_delay_minutes": -1,
                    "reason": "",
                }
            )


if __name__ == "__main__":
    unittest.main()
