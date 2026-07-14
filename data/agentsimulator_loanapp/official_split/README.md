# Official AgentSimulator Split

This directory contains the canonical-schema export of the temporal split
created by the upstream AgentSimulator implementation from its public
`raw_data/LoanApp.csv.gz` file.

- `LoanApp_train_agentsimulator_split.csv.gz`: 797 training cases.
- `LoanApp_test_agentsimulator_split.csv.gz`: 200 held-out cases.

The split was imported without changing case membership, activities,
resources, or timestamps. Timestamp precision was reduced from nanoseconds to
microseconds solely for compatibility with Python's standard `datetime`
parser. The source repository was
`https://github.com/lukaskirchdorfer/AgentSimulator` and was used under its MIT
License. See `../AGENTSIMULATOR_LICENSE`.
