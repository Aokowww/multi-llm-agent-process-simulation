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

## What-If Stress Test

The what-if script complements the held-out log reproduction experiment. It adds a resource-availability queue and simulates intervention scenarios that change capacity and workload:

- `baseline`
- `reduced_capacity`
- `high_load`
- `reduced_capacity_high_load`

Run:

```bash
python3 run_what_if.py \
  --train-log ../03_data/original-event-logs/AcademicCredentials_train.csv.gz \
  --test-log ../03_data/original-event-logs/AcademicCredentials_test.csv.gz \
  --output-dir ../05_results/academic_credentials_what_if \
  --runs 5 \
  --seed 3000 \
  --load-multiplier 1.6 \
  --capacity-factor 0.5 \
  --constrained-resource-limit 20
```

The default intervention constrains the top 20 high-frequency resources to 50% capacity and optionally compresses case arrivals by 1.6x. Outputs:

- `what_if_runs.csv`: one row per run, scenario, and mode.
- `what_if_summary.csv`: mean/std by scenario and mode.
- Optional generated logs when `--save-logs` is used.

## AgentSimulator LoanApp Robustness Dataset

The repository includes a small prepared robustness dataset from the public AgentSimulator GitHub repository. The source file is `raw_data/LoanApp.csv.gz`, distributed under the AgentSimulator MIT License.

Prepare the split from a downloaded AgentSimulator source log:

```bash
python3 prepare_agentsimulator_loanapp.py \
  --input-log ../data/agentsimulator_loanapp/source/LoanApp.csv.gz \
  --output-dir ../data/agentsimulator_loanapp/prepared \
  --test-ratio 0.3 \
  --seed 2408
```

Run repeated lightweight metrics:

```bash
python3 run_repeated.py \
  --train-log ../data/agentsimulator_loanapp/prepared/LoanApp_train.csv.gz \
  --test-log ../data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --output-dir ../results/agentsimulator_loanapp_repeated \
  --runs 10 \
  --seed 4200
```

Run formal Chapela-Campa distances on saved repeated logs if needed:

```bash
python3 run_repeated.py \
  --train-log ../data/agentsimulator_loanapp/prepared/LoanApp_train.csv.gz \
  --test-log ../data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --output-dir ../outputs/agentsimulator_loanapp_repeated_logs \
  --runs 10 \
  --seed 4200 \
  --save-logs

python3 run_chapela_repeated.py \
  --original-log ../data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --repeated-dir ../outputs/agentsimulator_loanapp_repeated_logs \
  --output-dir ../results/agentsimulator_loanapp_chapela \
  --distance-script path/to/ComputeLogDistance.py
```

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
