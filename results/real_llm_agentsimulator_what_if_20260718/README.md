# Real-LLM AgentSimulator What-If Pilot

This directory contains paired what-if experiments comparing per-resource LLM
bids with the fixed-score control inside the same patched AgentSimulator
environment. The experiment uses the LoanApp log, seeds 9400, 9500, and 9600,
ten generated cases per run, a top-k shortlist of two, and a local memory of
three completed tasks.

## Scenarios

- `high_load`: the case-arrival rate is multiplied by 1.6 by compressing the
  discovered inter-arrival intervals.
- `resource_unavailability`: `Clerk-000005` and `Clerk-000001`, the first two
  high-frequency resources that can be removed while retaining at least one
  eligible resource for every activity, are unavailable for the complete run.

Each scenario is compared with the same policy and seed under the unchanged
baseline archived in `results/multi_llm_agent_loanapp_repeated/`. This design
measures scenario response rather than distance to an unavailable observed
counterfactual log.

## Execution Validity

The six real-LLM scenario runs contain 863 independent bids. All 863 calls
return valid structured outputs; no invalid output, rate-limit retry, or policy
fallback occurs. The unavailable resources execute no events in either policy.

## Main Descriptive Results

Values below are mean percentage changes from each policy's unchanged baseline
over three paired seeds.

| Scenario | Policy | Mean cycle time | Throughput | Mean WIP | Resource utilization |
|---|---|---:|---:|---:|---:|
| High load | Fixed-score | -36.8% | +106.8% | +2.8% | -1.4% |
| High load | LLM resource agents | -40.5% | +262.9% | +114.4% | +91.4% |
| Two resources unavailable | Fixed-score | -5.4% | +88.6% | +27.5% | +38.0% |
| Two resources unavailable | LLM resource agents | +81.7% | -0.9% | +74.8% | +90.1% |

The LLM condition responds more strongly on WIP and utilization in both
scenarios. Under resource unavailability, its mean cycle time increases in two
of three seeds and its mean throughput remains close to baseline. Under high
load, neither policy produces a stable congestion response in cycle time, even
though LLM allocation produces a larger WIP response.

These are sensitivity results, not counterfactual-accuracy results. Each run
contains only ten cases, seed-level variation is large, and no observed
counterfactual log is available. The experiment therefore motivates a larger,
calibrated what-if evaluation but does not establish that the LLM predicts the
true intervention outcome more accurately.

## Files

- `summary/what_if_response_runs.csv`: run-level values and changes from the
  unchanged baseline.
- `summary/what_if_response_summary.csv`: three-run descriptive summaries.
- `figures/agentsimulator_what_if_response.*`: vector and raster figures.
- Scenario and policy directories: generated logs, allocation traces, metrics,
  and experiment metadata.

API credentials are not stored. Raw response caches, bid text, diagnostics,
and local execution logs are excluded from the public artifact.
