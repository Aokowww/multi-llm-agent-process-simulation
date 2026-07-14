import sys
import unittest
from collections import defaultdict
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pilot_simulation import generate_synthetic_log, learn_profiles, parse_dt, simulate
from resource_agents import ResourceAgent


class ResourceAgentTests(unittest.TestCase):
    def setUp(self):
        self.rows = generate_synthetic_log(24, 17)
        self.profiles = learn_profiles(self.rows)

    def test_discovers_one_agent_per_resource(self):
        profiles = self.profiles["resource_agents"]
        self.assertEqual(set(profiles), {"Alice", "Bob", "Cara"})
        self.assertEqual(set(profiles["Cara"]["capabilities"]), {"Submit", "Review", "Approve"})
        self.assertTrue(all(profile["agent_type"].startswith("role_") for profile in profiles.values()))

    def test_agent_rejects_overlapping_assignment(self):
        profile = self.profiles["resource_agents"]["Alice"]
        agent = ResourceAgent.from_profile(profile)
        start = datetime(2026, 1, 5, 9, 0)
        end = datetime(2026, 1, 5, 10, 0)
        agent.assign("C1", "Submit", start, end)
        with self.assertRaises(ValueError):
            agent.assign("C2", "Check", datetime(2026, 1, 5, 9, 30), datetime(2026, 1, 5, 10, 30))

    def test_resource_agent_modes_produce_non_overlapping_logs(self):
        for mode in ("resource_agent_orchestrated", "resource_agent_autonomous"):
            generated, _, _ = simulate(
                self.profiles,
                20,
                mode,
                91,
                base_start=datetime(2026, 1, 5, 9, 0),
            )
            intervals = defaultdict(list)
            for row in generated:
                intervals[row["resource"]].append((parse_dt(row["start_time"]), parse_dt(row["end_time"])))
            for values in intervals.values():
                values.sort()
                for previous, current in zip(values, values[1:]):
                    self.assertGreaterEqual(current[0], previous[1])

    def test_simulation_is_reproducible(self):
        first = simulate(self.profiles, 12, "resource_agent_autonomous", 101)[0]
        second = simulate(self.profiles, 12, "resource_agent_autonomous", 101)[0]
        self.assertEqual(first, second)

    def test_detailed_handover_priors_include_previous_activity(self):
        keys = self.profiles["detailed_handover_priors"]
        self.assertTrue(keys)
        self.assertTrue(all(len(key.split("||")) == 3 for key in keys))


if __name__ == "__main__":
    unittest.main()
