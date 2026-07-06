# Reproducibility Protocol

## Purpose

This protocol records how the current experiments behind `06_manuscript/manuscript_draft.md` are generated. It is intended to make the method section reproducible and to support later submission auditing.

## Primary Scripts

| Script | Role |
|---|---|
| `pilot_simulation.py` | Learns profiles, simulates the default policies, optionally adds `llm_agent_real`, writes generated logs, reasoning logs, handover logs, and lightweight metrics. |
| `run_repeated.py` | Runs `pilot_simulation.py` logic for repeated seeds and aggregates lightweight metrics, optionally including the real LLM condition. |
| `run_chapela_distances.py` | Wraps the Chapela-Campa `ComputeLogDistance.py` script for one generated-log directory. |
| `run_chapela_repeated.py` | Runs formal Chapela-Campa distances across repeated run folders and aggregates results. |

## Canonical Event Schema

The generated and reference event logs use:

```text
case_id, activity, resource, start_time, end_time
```

The LLM-agent proxy and optional real LLM condition additionally emit:

```text
reasoning: case_id, step_index, mode, previous_resource, activity,
           selected_resource, feasible_resource_count, feasible_resources_top,
           historical_prior, selection_rule, reason

handover:  case_id, from_resource, to_resource, activity, timestamp, message
```

## Simulation Conditions

| Condition | Resource Decision Rule |
|---|---|
| `central_baseline` | Uniform sample from historically capable resources for the activity. |
| `agent_profile` | Weighted sample from historically capable resources using activity-resource frequency. |
| `llm_agent_proxy` | Handover-prior or activity-prior sampling constrained by feasible resources and adjusted by an overuse penalty. |
| `llm_agent_real` | Optional OpenAI-compatible API call over the same feasible resource set; invalid or unavailable calls fall back to the guarded proxy. |

## Repeated-Run Settings

- Runs per condition: 10.
- Base seed: 1000.
- Per-run seed rule: `1000 + run_index * 100 + mode_index`.
- Number of simulated cases: number of cases in the held-out test log.
- Simulation start: first timestamp of the held-out test log.
- Case arrivals: empirical inter-arrival samples learned from training cases.

## Current Primary Dataset

AcademicCredentials from the Chapela-Campa et al. Zenodo artifact:

- Train/test split already provided by the artifact.
- Approximately 398 cases per split.
- Approximately 1,800-1,900 events per split.
- 16 activities.
- Around 300 resources.

## Current Result Locations

| Output | Path |
|---|---|
| Repeated generated logs | `05_results/academic_credentials_repeated_arrival_logs_v7/` |
| Lightweight repeated metrics | `05_results/academic_credentials_repeated_arrival_v6/metrics_summary.csv` |
| Formal repeated Chapela-Campa metrics | `05_results/academic_credentials_chapela_repeated_v7/chapela_summary.csv` |

## Optional Real-LLM Extension

The real LLM module preserves the same interface as `llm_agent_proxy`: input structured local state and feasible actions; output a selected resource plus a rationale. It is not allowed to invent activities, resources, timestamps, or schema fields. The implementation records `llm_calls`, `llm_invalid_outputs`, and `llm_fallbacks` in the metrics output. Follow-up analysis should add feasible action-set size, reason-action consistency, and handover-message consistency summaries.

Run with:

```bash
export OPENAI_API_KEY=...
python3 src/pilot_simulation.py \
  --train-log path/to/AcademicCredentials_train.csv.gz \
  --test-log path/to/AcademicCredentials_test.csv.gz \
  --output-dir outputs/real_llm_smoke \
  --include-real-llm
```

If `OPENAI_API_KEY` is not set, the `llm_agent_real` condition exercises the same interface but records fallback decisions, so these outputs should be treated as an implementation smoke test rather than API-backed evidence.
