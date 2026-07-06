# AcademicCredentials What-If Experiment

This folder contains a lightweight intervention experiment that complements the log-reproduction evaluation.

## Scenario Design

The experiment uses the `AcademicCredentials` train/test split and the learned resource profiles from the main study. It introduces a resource-availability queue so that capacity and workload interventions affect event start times.

Four scenarios are simulated:

- `baseline`: original arrival intensity and full resource availability.
- `reduced_capacity`: the top 20 high-frequency resources operate at 50% capacity.
- `high_load`: case arrivals are compressed by a 1.6x load multiplier.
- `reduced_capacity_high_load`: both interventions are applied together.

The constrained resource group is:

```text
677, 19019, 22475, 3445, 22404, 1707, 716, 241, 1, 8824,
15930, 1007, 659, 18929, 7080, 11204, 2981, 387, 6004, 6979
```

## Main Interpretation

The what-if experiment should not be read as another held-out log reproduction score. It is a stress test of policy response.

Under the combined `reduced_capacity_high_load` scenario:

| Mode | Mean cycle time, days | P90 cycle time, days | Handover per case | Constrained-group event share | Throughput, cases/day |
|---|---:|---:|---:|---:|---:|
| `central_baseline` | 87.6 | 191.7 | 3.86 | 0.202 | 1.21 |
| `agent_profile` | 215.1 | 451.4 | 3.77 | 0.447 | 0.60 |
| `llm_agent_proxy` | 106.4 | 251.8 | 2.09 | 0.366 | 0.93 |

The central baseline remains strongest on cycle-time and throughput response in this setup. The LLM-agent proxy substantially reduces handovers, but it does not beat the central baseline on temporal performance. The agent-profile policy depends most strongly on the constrained resource group and suffers the largest cycle-time increase.

This supports the paper's conservative claim: LLM-agent simulation changes the operational response profile and improves observability/coordination traces, but it should be evaluated as a multidimensional trade-off rather than a universal accuracy improvement.

## Files

- `what_if_runs.csv`: one row per run, scenario, and mode.
- `what_if_summary.csv`: mean/std summary by scenario and mode.
- `what_if_summary.json`: JSON copy of the summary.
