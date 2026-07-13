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

Control-flow n-gram and case-arrival distances are identical across
policies because paired runs share process-structure and arrival draws.
The LLM-agent proxy has the lowest mean workforce EMD, relative EMD, and
cycle-time Wasserstein distance, but the latter two metrics also have
the highest run-to-run variation. The result supports a bounded
robustness claim, not a universal accuracy claim.
