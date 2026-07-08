# AcademicCredentials What-If Intervention Results

This directory contains the AcademicCredentials capacity and workload
intervention experiment.

## Scenario

The experiment uses the same learned resource profiles as the
AcademicCredentials log-reproduction evaluation. It adds a
resource-availability queue so that capacity and workload interventions
affect event start times.

The archived scenarios are:

- `baseline`: original arrival intensity and full resource availability.
- `reduced_capacity`: top high-frequency resources operate at reduced
  capacity.
- `high_load`: case arrivals are compressed by a load multiplier.
- `reduced_capacity_high_load`: both interventions are applied.

## Files

- `what_if_runs.csv`: run-level results by scenario and simulation
  policy.
- `what_if_summary.csv`: mean and standard deviation by scenario and
  simulation policy.
- `what_if_summary.json`: JSON version of the summary table.

## Main Observation

Under the combined reduced-capacity and high-load scenario, the central
baseline has the strongest temporal response, while the LLM-agent proxy
substantially reduces handovers per case. The result supports a
multidimensional interpretation rather than a single overall winner.
