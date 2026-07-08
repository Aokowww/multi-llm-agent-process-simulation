# AgentSimulator LoanApp What-If Intervention Results

This directory contains capacity and workload intervention results for
the AgentSimulator LoanApp robustness dataset.

## Files

- `what_if_runs.csv`: run-level intervention results by scenario and
  simulation policy.
- `what_if_summary.csv`: mean and standard deviation by scenario and
  simulation policy.
- `what_if_summary.json`: JSON version of the summary table.

## Scenario

The experiment applies the same intervention logic as the
AcademicCredentials what-if analysis: a resource-availability queue,
capacity reduction for selected high-frequency resources, and workload
increase through compressed case arrivals.

## Main Observation

The LoanApp intervention results are included to inspect whether the
policy response changes on a dataset with fewer resources and clearer
role structure. They should be interpreted as intervention-response
evidence, not as held-out log-reproduction metrics.
