# Source Code

This directory contains the Python scripts used to prepare data, run
simulations, and compute evaluation metrics.

## Scripts

- `prepare_agentsimulator_loanapp.py`: normalizes the AgentSimulator
  LoanApp log and creates a train/test split.
- `pilot_simulation.py`: learns log-derived profiles, simulates the
  default policies, and writes generated event logs and diagnostics.
- `run_repeated.py`: repeats simulations across random seeds and
  aggregates lightweight log-reproduction metrics. It also provides
  quota-aware real-LLM provider presets, fixed case sampling, fail-fast
  API-key checks, per-call diagnostics, prompt-version metadata, and a
  resumable context-validated response cache.
- `evaluate_agent_decisions.py`: evaluates resource selections separately
  from end-to-end event-log distances, including top-1 agreement,
  feasible-action coverage, fallback rate, and structured-reason checks.
- `plot_llm_replications.py`: produces paired three-seed real-LLM
  figures in PDF, SVG, and PNG formats from sanitized result tables.
- `analyze_llm_specific_evaluation.py`: computes resource coverage,
  assignment entropy, effective resource count, HHI, activity-conditional
  diversity, interface validity, trace grounding, latency, and token use
  from the three completed LoanApp API runs.
- `analyze_dataset_suitability.py`: reports train/test resource overlap,
  action-mask coverage, handover-context coverage, and feasible-set size
  before a dataset is used for resource-agent evaluation.
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

For long API-backed runs, completed decisions are stored in
`llm_response_cache.jsonl`. Restarting an identical command replays the
validated cache before issuing new requests. This file contains model
outputs and diagnostics but never the API key.
