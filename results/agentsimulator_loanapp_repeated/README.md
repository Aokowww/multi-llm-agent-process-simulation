# AgentSimulator LoanApp Lightweight Repeated Results

This directory contains lightweight repeated log-reproduction metrics
for the AgentSimulator LoanApp robustness dataset.

## Files

- `metrics_runs.csv`: run-level lightweight metrics.
- `metrics_runs.json`: JSON version of the run-level metrics.
- `metrics_summary.csv`: mean, standard deviation, minimum, and maximum
  values by simulation policy.
- `metrics_summary.json`: JSON version of the summary table.

## Dataset Summary

- Cases: 1,000
- Events: 7,492
- Activities: 12
- Resources: 19
- Training split: 700 cases
- Test split: 300 cases

## Main Observation

LoanApp is easier to reproduce than AcademicCredentials under the
lightweight metrics. Trace-variant and activity-distribution distances
are identical across policies because paired runs share the same
process-structure draws. The central baseline has the lowest mean
resource-distribution distance, while the LLM-agent proxy has the lowest
mean cycle-time relative error. No policy is best across all dimensions.
