# Experiments

## Pilot

Run from this folder:

```bash
python3 pilot_simulation.py --output-dir ../05_results/pilot
```

The pilot creates:

- `observed_train.csv`
- `observed_test.csv`
- `learned_profiles.json`
- `simulated_central_baseline.csv`
- `simulated_agent_profile.csv`
- `simulated_llm_agent_proxy.csv`
- `simulated_llm_agent_real.csv` when `--include-real-llm` is used
- `metrics.csv`
- `metrics.json`

## Optional Real LLM Condition

The optional `llm_agent_real` mode calls an OpenAI-compatible chat-completions endpoint after the simulator has already applied the event-log-derived action mask. The model receives the activity, previous resource, feasible resources, historical priors, and current usage counts. It must return JSON:

```json
{"resource": "selected feasible resource", "reason": "brief rationale"}
```

Run:

```bash
export OPENAI_API_KEY=...
python3 pilot_simulation.py \
  --train-log ../03_data/original-event-logs/AcademicCredentials_train.csv.gz \
  --test-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --output-dir ../05_results/academic_credentials_real_llm_smoke \
  --include-real-llm \
  --llm-model "${OPENAI_MODEL:-gpt-4o-mini}"
```

If the API key is missing, if the call fails, or if the model returns an infeasible resource, the simulator records a guarded fallback decision and continues. Relevant diagnostic columns are written to `metrics.csv`: `llm_model`, `llm_calls`, `llm_invalid_outputs`, and `llm_fallbacks`.

## Next Implementation Steps

1. Archive one small API-backed `llm_agent_real` smoke run once API credentials are available.
2. Add summary metrics over `reasoning_llm_agent_proxy.csv`, `reasoning_llm_agent_real.csv`, and the handover logs.
3. Run Chapela-Campa distances across repeated generated logs and summarize mean/std for any archived real LLM condition.

## Repeated Runs

Run:

```bash
python3 run_repeated.py \
  --train-log ../03_data/original-event-logs/AcademicCredentials_train.csv.gz \
  --test-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --output-dir ../05_results/academic_credentials_repeated_v4 \
  --runs 10 \
  --seed 1000
```

Add `--include-real-llm` to include the optional API-backed condition. For cost control, run a one-seed smoke experiment before repeated real LLM runs.

Outputs:

- `metrics_runs.csv`: one row per run and condition.
- `metrics_summary.csv`: mean, standard deviation, min, and max by condition.

## Chapela-Campa Formal Distances

Run:

```bash
python3 run_chapela_distances.py \
  --original-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --simulated-dir ../05_results/academic_credentials_arrival_v6 \
  --output-dir ../05_results/academic_credentials_chapela_arrival_v6
```

Outputs:

- `chapela_distances.csv`: formal BPS log-distance metrics from the Chapela-Campa et al. artifact.
- `ComputeLogDistance_project_columns.py`: temporary patched copy using this project's simulated-log column names.
- `simulated_logs/`: copied simulated logs used for the formal run.

## Repeated Chapela-Campa Distances

First generate logs:

```bash
python3 run_repeated.py \
  --train-log ../03_data/original-event-logs/AcademicCredentials_train.csv.gz \
  --test-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --output-dir ../05_results/academic_credentials_repeated_arrival_logs_v7 \
  --runs 10 \
  --seed 1000 \
  --save-logs
```

Then run formal distances:

```bash
python3 run_chapela_repeated.py \
  --original-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --repeated-dir ../05_results/academic_credentials_repeated_arrival_logs_v7 \
  --output-dir ../05_results/academic_credentials_chapela_repeated_v7
```

Outputs:

- `chapela_runs.csv`: one row per run and condition.
- `chapela_summary.csv`: mean, standard deviation, min, and max by condition.
