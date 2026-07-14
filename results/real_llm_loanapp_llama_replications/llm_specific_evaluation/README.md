# LLM-Specific Evaluation Tables

These tables report diagnostics derived from the three completed
100-case LoanApp API runs (seeds 8200, 8300, and 8400).

- `llm_specific_policy_runs.csv` contains run-level allocation metrics
  for the central, agent-profile, proxy, and real-LLM policies.
- `llm_specific_reasoning_runs.csv` contains run-level interface and
  trace diagnostics for the real LLM.
- `llm_specific_summary.csv` contains means and sample standard
  deviations across the three paired seeds.

The metrics diagnose current behavior; they do not measure
counterfactual response, repeated-state stability, model drift, or
state-action support in sparse regions. Those dimensions require new
experiments.
