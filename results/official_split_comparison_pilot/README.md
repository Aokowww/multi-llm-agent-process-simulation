# Official-Split Comparison Pilot

This pilot evaluates the repository's central, activity-profile, and
constrained proxy policies on the exact 797/200-case temporal split generated
by upstream AgentSimulator. It contains three runs with base seed 9200.

The purpose is split alignment. These policies do not yet share
AgentSimulator's full simulation state or task-allocation implementation, so
the files must not be interpreted as a component-level ablation. A valid LLM
replacement experiment must hold the upstream environment fixed and replace
only the allocation policy.
