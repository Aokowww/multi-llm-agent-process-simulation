# AgentSimulator LoanApp Data

This directory contains the LoanApp robustness dataset used in the
experiments.

## Source

- Repository: `https://github.com/lukaskirchdorfer/AgentSimulator`
- Source file: `raw_data/LoanApp.csv.gz`
- License: MIT License, reproduced in `AGENTSIMULATOR_LICENSE`

## Files

- `source/LoanApp.csv.gz`: original LoanApp event log from the public
  AgentSimulator repository.
- `prepared/LoanApp_full.csv.gz`: normalized full event log using the
  canonical schema required by this prototype.
- `prepared/LoanApp_train.csv.gz`: training split used to learn
  resource profiles and timing samples.
- `prepared/LoanApp_test.csv.gz`: held-out test split used for
  evaluation.
- `prepared/README.md`: split parameters and dataset statistics.
