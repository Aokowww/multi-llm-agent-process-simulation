# Official AgentSimulator LoanApp Result

This directory records one autonomous simulation produced by the upstream
AgentSimulator implementation from its public LoanApp log. It is the direct
AgentSimulator baseline, rather than the resource-agent compatibility
prototype implemented in this repository.

## Provenance

- Upstream repository: `https://github.com/lukaskirchdorfer/AgentSimulator`
- Upstream commit: `665a6926878859072769aa25c12fe9d6056ad510`
- Architecture: autonomous
- Extraneous-delay flag: disabled at the command line
- Simulations: 1
- Training cases: 797
- Test and generated cases: 200 each

The upstream command was:

```bash
python simulate.py \
  --log_path raw_data/LoanApp.csv.gz \
  --case_id case_id \
  --activity_name activity \
  --resource_name resource \
  --end_timestamp end_time \
  --start_timestamp start_time \
  --num_simulations 1
```

`simulated_agentsimulator_autonomous.csv` is the canonical-schema generated
log. `metrics.json` contains lightweight distances against the exact upstream
test split. The two compressed split files are retained here as provenance;
working copies are also stored under
`data/agentsimulator_loanapp/official_split/`.

This single run establishes an executable reference condition. It is not a
stability estimate; repeated, seeded upstream runs are still required before
inferential comparison.
