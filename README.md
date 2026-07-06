# Resource-Centric LLM-Augmented Multi-Agent Process Simulation

This repository contains a reproducible research prototype for a study project on resource-centric, LLM-augmented multi-agent business process simulation.

The core idea is conservative: an LLM-style agent module should not freely generate process behavior. It should choose among event-log-derived feasible actions, emit process-mining-compatible event logs, and be evaluated with standard BPS quality measures.

## Repository Structure

```text
src/                 Python experiment scripts
results/             Paper-ready result summaries
docs/                Research plan and reproducibility notes
manuscript/          LaTeX manuscript source and figures
```

## Experiment Scripts

- `src/pilot_simulation.py`: learns log-derived profiles and simulates three policies.
- `src/run_repeated.py`: repeats simulations across random seeds and aggregates lightweight metrics.
- `src/run_chapela_distances.py`: wraps the public Chapela-Campa distance script for one generated-log directory.
- `src/run_chapela_repeated.py`: aggregates Chapela-Campa distances across repeated generated logs.

## Simulation Conditions

- `central_baseline`: centralized resource sampling from feasible resources.
- `agent_profile`: activity-resource frequency weighted resource-agent policy.
- `llm_agent_proxy`: constrained LLM-style local decision policy using handover priors, activity priors, and distributional guardrails.

## Data

The experiments use the public Zenodo artifact associated with:

Chapela-Campa, D., Benchekroun, I., Baron, O., Dumas, M., Krass, D., and Senderovich, A. 2025. "A Framework for Measuring the Quality of Business Process Simulation Models," Information Systems 127, 102447. https://doi.org/10.1016/j.is.2024.102447

Raw event logs and the original `ComputeLogDistance.py` are not vendored here. Download the artifact from Zenodo and point the scripts to the local files.

## Example Usage

Run repeated lightweight metrics:

```bash
python src/run_repeated.py \
  --train-log path/to/AcademicCredentials_train.csv.gz \
  --test-log path/to/AcademicCredentials_test.csv.gz \
  --output-dir outputs/repeated \
  --runs 10 \
  --seed 1000 \
  --save-logs
```

Run formal Chapela-Campa distances on repeated logs:

```bash
python src/run_chapela_repeated.py \
  --original-log path/to/AcademicCredentials_test.csv.gz \
  --repeated-dir outputs/repeated \
  --output-dir outputs/chapela \
  --distance-script path/to/ComputeLogDistance.py
```

## Current Result Summary

The `results/` folder contains the repeated lightweight metric summary and repeated Chapela-Campa summary used in the manuscript.

The main interpretation is not that the LLM-agent proxy dominates traditional BPS. The result is dimension-specific: the agent-profile policy is strongest on several formal control-flow and absolute/case-arrival timing metrics, while the LLM-agent proxy is competitive and strongest on workforce EMD.

## Manuscript

The `manuscript/` folder contains a LaTeX draft and figures. Compile from that folder with:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The title-page personal and supervisor fields should be replaced before final submission.
