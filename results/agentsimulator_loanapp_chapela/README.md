# AgentSimulator LoanApp Formal Distance Results

This directory contains formal log-distance metrics for the
AgentSimulator LoanApp robustness dataset. The metrics were computed
with the Chapela-Campa et al. `ComputeLogDistance.py` script.

## Files

- `chapela_runs.csv`: run-level formal distance metrics.
- `chapela_runs.json`: JSON version of the run-level metrics.
- `chapela_summary.csv`: mean, standard deviation, minimum, and maximum
  values by simulation policy.
- `chapela_summary.json`: JSON version of the summary table.

## Main Observation

The central baseline remains strongest on control-flow n-grams. The
LLM-agent proxy is strongest on workforce EMD and is close to the
agent-profile policy on cycle-time Wasserstein distance. The result
supports a bounded robustness claim: the proxy changes the quality
profile, but it is not a universal accuracy winner.
