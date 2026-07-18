# Upstream Integration Patch

`agentsimulator_multi_llm_policy.patch` contains the minimal local
changes used to inject a resource-selection policy into AgentSimulator
commit `665a6926878859072769aa25c12fe9d6056ad510`.

The patch exposes the execution model to the external policy, allows a
bounded number of cases for API pilots, lets the contractor request a
permutation of feasible agents, and reports actual task execution back
to the policy. It also supports an arrival-rate multiplier and the
scenario-specific removal of high-frequency resources while retaining
at least one eligible resource per activity. The per-resource bidding
logic and scenario analysis remain in this repository under `src/`.

Apply it from a clean upstream clone:

```bash
git checkout 665a6926878859072769aa25c12fe9d6056ad510
git apply path/to/agentsimulator_multi_llm_policy.patch
```
