# AgentSimulator LoanApp Repeated Metrics

This folder contains the lightweight repeated-log-reproduction metrics for the AgentSimulator `LoanApp` dataset.

## Dataset

- Source: `lukaskirchdorfer/AgentSimulator`, `raw_data/LoanApp.csv.gz`
- License: MIT License in the AgentSimulator repository
- Prepared split: 700 train cases and 300 test cases
- Size: 7,492 events, 1,000 cases, 12 activities, 19 resources

## Main Result

Lower is better.

| Mode | Trace distance | Activity distance | Resource distance | Mean cycle-time relative error |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.1450 | 0.0081 | 0.0426 | 0.4643 |
| `agent_profile` | 0.1573 | 0.0124 | 0.0503 | 0.3739 |
| `llm_agent_proxy` | 0.1580 | 0.0166 | 0.0459 | 0.3825 |

LoanApp is easier to reproduce than AcademicCredentials under the lightweight metrics, but the LLM-agent proxy does not dominate. The central baseline is strongest on trace, activity, and resource distribution distance. The proxy is better than the central baseline on mean cycle-time error and better than `agent_profile` on resource distance.

## Files

- `metrics_runs.csv`: one row per run and mode.
- `metrics_summary.csv`: mean/std/min/max by mode.
