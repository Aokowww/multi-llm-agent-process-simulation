# Multi-LLM-Agent LoanApp Pilot

This directory archives the technical pilot in which independently
prompted resource agents bid for tasks inside the upstream
AgentSimulator execution environment. It separates two conditions:

- `mock_10_cases/` uses a deterministic bidder to test the adapter,
  state updates, local memory, trace files, and evaluation code.
- `real_10_cases/` uses Groq `llama-3.1-8b-instant`. Each shortlisted
  resource receives only its own profile, current state, bounded recent
  memory, and the current task context.

Both runs use the LoanApp log, seed 9400, ten held-out cases, top-k 2,
and memory size 3. The required upstream AgentSimulator commit is
`665a6926878859072769aa25c12fe9d6056ad510`.

## Real-LLM Result

The real condition generated ten cases and 75 events from 79 allocation
decisions. It produced 147 independent bids:

- valid bid rate: 100.0%;
- fallback count: 0;
- proposal execution rate: 96.0%;
- bid disagreement rate: 24.0%;
- resource agents with non-empty memory: 18;
- normalized resource entropy: 0.9836;
- prompt, completion, and total tokens: 44,270, 6,462, and 50,732.

The generated-log distances were 0.9000 for trace variants, 0.0763 for
activity distribution, and 0.1804 for resource distribution. Mean cycle
time was 248.72 minutes versus 254.80 minutes in the ten-case reference,
giving a relative error of 2.39%.

## Interpretation

The pilot shows that independently prompted ResourceAgents can produce
valid machine-readable bids, maintain local memory, and drive an
upstream AgentSimulator execution without fallback. The low cycle-time
error is encouraging, but the other log distances do not improve
uniformly. Because this is one seed with ten cases, it supports an
artifact-feasibility claim only. It does not establish that multi-LLM
bidding outperforms AgentSimulator, the local agent-profile baseline, or
the earlier central LLM selector.

## Files

- `metrics.json`: log-level, bidding, coordination, token, and latency
  metrics.
- `experiment_metadata.json`: policy, dataset, model, seed, and protocol.
- `simulated_agentsimulator_multi_llm_agent.csv`: generated event log.
- `observed_test.csv.gz`: matched ten-case reference log.
- `allocation_traces.csv`: proposed and executed resource assignments.
- `agent_bids.csv`: one row per resource-agent bid.
- `bid_call_diagnostics.csv`: API validity, latency, and token use.
- `agent_bid_cache.jsonl`: resumable sanitized API responses and contexts.

No API credential is stored in these files.
