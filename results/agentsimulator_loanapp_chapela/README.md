# AgentSimulator LoanApp Formal Chapela-Campa Metrics

This folder contains repeated formal log-distance metrics for the AgentSimulator `LoanApp` robustness dataset, computed with the Chapela-Campa et al. `ComputeLogDistance.py` script.

## Selected Result

Lower is better.

| Mode | Bigram | Trigram | Workforce EMD | Cycle-time Wasserstein |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.0288 | 0.0453 | 8.7934 | 67.9520 |
| `agent_profile` | 0.0353 | 0.0517 | 8.6541 | 55.4577 |
| `llm_agent_proxy` | 0.0399 | 0.0550 | 8.6489 | 55.6193 |

The formal robustness result is mixed. The central baseline remains best on control-flow n-grams and absolute/case-arrival timing. The LLM-agent proxy is best on workforce EMD and nearly tied with `agent_profile` on cycle-time Wasserstein. This supports a conservative cross-dataset claim: the proxy changes the resource/timing trade-off profile, but it is not a universal accuracy winner.

## Files

- `chapela_runs.csv`: one row per run, mode, and formal metric set.
- `chapela_summary.csv`: mean/std/min/max by mode.
