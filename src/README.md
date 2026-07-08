# Source Code

This directory contains the Python scripts used to prepare data, run
simulations, and compute evaluation metrics.

## Scripts

- `prepare_agentsimulator_loanapp.py`: normalizes the AgentSimulator
  LoanApp log and creates a train/test split.
- `pilot_simulation.py`: learns log-derived profiles, simulates the
  default policies, and writes generated event logs and diagnostics.
- `run_repeated.py`: repeats simulations across random seeds and
  aggregates lightweight log-reproduction metrics.
- `run_chapela_distances.py`: runs the Chapela-Campa distance script for
  one generated-log directory.
- `run_chapela_repeated.py`: applies Chapela-Campa distances to repeated
  generated logs and summarizes the results.
- `run_what_if.py`: evaluates capacity and workload intervention
  scenarios with a resource-availability queue.

All scripts use the canonical event-log schema:

```text
case_id, activity, resource, start_time, end_time
```
