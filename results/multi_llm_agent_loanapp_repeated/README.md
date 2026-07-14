# Repeated Multi-LLM-Agent LoanApp Experiment

This directory contains three actual per-resource LLM-bidding runs and
three matched deterministic multi-agent controls. All runs use the
LoanApp official train/test split, ten generated cases, top-k 2, memory
size 3, and seeds 9400, 9500, and 9600. The actual condition uses Groq
`llama-3.1-8b-instant` and the same upstream AgentSimulator integration
in every run.

## Actual Multi-LLM Reliability

Across 445 independent LLM bids, all responses were valid and no
fallback was used. Mean proposal execution was 98.27%, mean bid
disagreement was 22.69%, and 18 to 19 resource agents acquired local
memory. These results show stable interface-level execution across the
three seeds.

## Process-Output Results

The actual multi-LLM mean distances were 0.8667 for trace variants,
0.1006 for activity distribution, and 0.1597 for resource distribution.
Mean cycle-time relative error was 43.69%, with a wide range from 2.39%
to 102.73%.

Against the matched deterministic multi-agent control, the actual
multi-LLM condition had lower activity distance in two of three seeds
and lower cycle-time error in two of three seeds. Its mean activity
distance was 0.1006 versus 0.1450, and mean cycle-time error was 43.69%
versus 65.57%. Trace distance was worse on average, while resource
distance differed only slightly. With three ten-case runs, these values
are descriptive and do not establish statistical superiority.

## Interpretation

The repeated experiment separates two findings. The constrained
multi-LLM interface is technically reliable, but the downstream process
quality is seed-sensitive and dimension-specific. The results support
retaining both BPS log-quality metrics and LLM-agent behavior metrics.
They do not support replacing the statistical, proxy, central real-LLM,
or what-if results already reported in the study.

## Structure

- `seed_9400/`, `seed_9500/`, and `seed_9600/`: actual multi-LLM runs.
- `baselines/mock_seed_*/`: deterministic multi-agent controls.
- `summary/repeated_*`: actual multi-LLM per-run and aggregate metrics.
- `summary/paired_comparison*`: matched real-versus-mock differences.

No API credential is stored in this directory.
