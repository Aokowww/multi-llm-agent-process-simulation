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

Under the combined reduced-capacity and high-load scenario, the
LLM-agent proxy has the shortest mean cycle time (2.01 days) and the
highest throughput (2.33 cases per day), but it also produces slightly
more handovers per case (6.43) than the statistical policies. These are
intervention-response results, not held-out log-reproduction metrics.
