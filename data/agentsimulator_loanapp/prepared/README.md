# Prepared LoanApp Event Log

This directory contains the normalized AgentSimulator LoanApp event log
and the train/test split used in the robustness experiments.

## Preparation

- Source: `../source/LoanApp.csv.gz`
- Canonical schema: `case_id`, `activity`, `resource`, `start_time`,
  `end_time`
- Split seed: `2408`
- Test ratio: `0.3`

## Dataset Statistics

| Quantity | Value |
|---|---:|
| Events | 7,492 |
| Cases | 1,000 |
| Activities | 12 |
| Resources | 19 |
| Training cases | 700 |
| Test cases | 300 |
| Training events | 5,239 |
| Test events | 2,253 |

## Files

- `LoanApp_full.csv.gz`: full normalized event log.
- `LoanApp_train.csv.gz`: training split.
- `LoanApp_test.csv.gz`: held-out test split.
