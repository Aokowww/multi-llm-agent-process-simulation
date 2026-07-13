# Resource-Centric LLM-Augmented Multi-Agent Process Simulation

This repository contains the public research artifact for a
resource-centric, LLM-augmented business process simulation prototype.
The repository is intended to support inspection and reproducibility of
the implemented experiments. It contains data, source code, and result
files only; draft writing materials are intentionally not included.

## Purpose

The prototype studies whether an LLM-style local decision module can be
embedded in a data-driven business process simulation pipeline without
breaking event-log compatibility. The simulator does not allow the
LLM-style component to freely generate process behaviour. Instead, local
resource-assignment decisions are constrained by event-log-derived
capabilities, timing samples, resource priors, and handover priors.

## Repository Contents

```text
data/       Prepared public benchmark data and license information
src/        Python scripts for data preparation, simulation, and evaluation
results/    Archived result summaries used for analysis
```

The top-level files are:

- `README.md`: public repository guide.
- `requirements.txt`: minimal Python package requirements.
- `.gitignore`: local output, cache, and excluded writing folders.

## Simulation Conditions

The implementation compares three main policies:

- `central_baseline`: samples a feasible resource from the resources
  that historically performed the activity.
- `agent_profile`: samples feasible resources using learned
  activity-resource frequencies.
- `llm_agent_proxy`: uses handover priors, activity-resource priors, and
  a resource overuse penalty to emulate a constrained LLM-style local
  decision module.

The code also includes an optional `llm_agent_real` condition behind the
same action-masked interface. The real-LLM runner supports Groq, Gemini,
OpenRouter, and custom OpenAI-compatible endpoints. It records API
successes, invalid outputs, fallbacks, latency, and token use. A missing
API key causes the experiment to stop so that fallback-only output cannot
be reported as a real-LLM result.

## Data Sources

The primary evaluation uses the public artifact associated with:

Chapela-Campa, D., Benchekroun, I., Baron, O., Dumas, M., Krass, D., and
Senderovich, A. 2025. "A Framework for Measuring the Quality of Business
Process Simulation Models," Information Systems 127, 102447.
https://doi.org/10.1016/j.is.2024.102447

Raw AcademicCredentials logs and the original `ComputeLogDistance.py`
script are not redistributed in this repository. They should be
downloaded from the authors' public artifact and passed to the scripts
through command-line arguments.

The repository includes a prepared robustness dataset derived from:

Kirchdorfer, L., Blumel, R., Kampik, T., Van der Aa, H., and
Stuckenschmidt, H. 2024. "AgentSimulator: An Agent-Based Approach for
Data-Driven Business Process Simulation," ICPM 2024.
https://doi.org/10.1109/ICPM63005.2024.10680660

The included LoanApp source log is from the public AgentSimulator GitHub
repository and is distributed there under the MIT License. The license
text is included in `data/agentsimulator_loanapp/AGENTSIMULATOR_LICENSE`.

## Reproduction Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run repeated lightweight metrics on AcademicCredentials:

```bash
python src/run_repeated.py \
  --train-log path/to/AcademicCredentials_train.csv.gz \
  --test-log path/to/AcademicCredentials_test.csv.gz \
  --output-dir outputs/academic_credentials_repeated \
  --runs 10 \
  --seed 1000 \
  --save-logs
```

Run formal Chapela-Campa distances on repeated generated logs:

```bash
python src/run_chapela_repeated.py \
  --original-log path/to/AcademicCredentials_test.csv.gz \
  --repeated-dir outputs/academic_credentials_repeated \
  --output-dir outputs/academic_credentials_chapela \
  --distance-script path/to/ComputeLogDistance.py
```

Run a what-if intervention experiment:

```bash
python src/run_what_if.py \
  --train-log path/to/AcademicCredentials_train.csv.gz \
  --test-log path/to/AcademicCredentials_test.csv.gz \
  --output-dir outputs/academic_credentials_what_if \
  --runs 5 \
  --seed 3000 \
  --load-multiplier 1.6 \
  --capacity-factor 0.5 \
  --constrained-resource-limit 20
```

Run the AgentSimulator LoanApp robustness experiment:

```bash
python src/run_repeated.py \
  --train-log data/agentsimulator_loanapp/prepared/LoanApp_train.csv.gz \
  --test-log data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --output-dir outputs/agentsimulator_loanapp_repeated \
  --runs 10 \
  --seed 4200
```

Run a quota-aware real-LLM pilot on a fixed 100-case LoanApp sample. Groq
is the recommended no-cost starting point because its OpenAI-compatible
API supports JSON output. The default `openai/gpt-oss-20b` free quota is
sufficient for approximately one 100-case LoanApp run per daily quota
window. Create a Groq API key, expose it only through the environment,
and run one replication:

```bash
export GROQ_API_KEY="..."
python src/run_repeated.py \
  --train-log data/agentsimulator_loanapp/prepared/LoanApp_train.csv.gz \
  --test-log data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --output-dir outputs/agentsimulator_loanapp_real_llm \
  --runs 1 \
  --seed 8100 \
  --max-cases 100 \
  --include-real-llm \
  --llm-provider groq \
  --save-logs
```

Schedule additional replications over separate daily quota windows and
use distinct base seeds. The bounded study protocol uses three
replications in total.

Evaluate local resource choices separately from end-to-end log quality:

```bash
python src/evaluate_agent_decisions.py \
  --train-log data/agentsimulator_loanapp/prepared/LoanApp_train.csv.gz \
  --test-log data/agentsimulator_loanapp/prepared/LoanApp_test.csv.gz \
  --output-dir outputs/agentsimulator_loanapp_decisions \
  --max-cases 100 \
  --max-decisions 300 \
  --seed 7300 \
  --include-real-llm \
  --llm-provider groq
```

The provider presets use these environment variables: `GROQ_API_KEY`,
`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, and `OPENAI_API_KEY` for a custom
endpoint. API keys are never written to result files.

## Result Interpretation

The archived results support a bounded interpretation. The
`llm_agent_proxy` changes the quality profile of the simulator and adds
reasoning and handover traces, but it does not uniformly outperform the
statistical baselines. The repeated experiments use paired common random
numbers: policies share the same process-structure and timing draws in
each run, while resource decisions use a separate random stream. As a
result, control-flow distances are identical across policies by design
and are not evidence for or against a resource-assignment policy.

The proxy has the lowest mean workforce EMD on both archived datasets
and adds decision and handover traces. Other temporal and resource
metrics remain dataset- and scenario-dependent. These results motivate
a multidimensional comparison rather than a claim of overall
outperformance.

For real-LLM experiments, end-to-end BPS metrics should be reported with
decision-level accuracy, feasible-action coverage, invalid-output and
fallback rates, reason-action consistency, latency, and token use. This
prevents a local decision effect from being hidden by control-flow and
timing components that are shared across policies.

The archived Groq/GPT-OSS pilot validates the API-backed execution path:
149 of 149 end-to-end decisions and 100 of 100 benchmark decisions
completed without invalid output or fallback. It does not establish
outperformance. On 100 sampled held-out decisions, real-LLM top-1
agreement was 34.34%, compared with 33.33% for activity-prior argmax;
the paired confidence interval included zero. The corresponding files
are under `results/real_llm_loanapp_pilot/`.
