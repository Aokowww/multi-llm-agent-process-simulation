# Research Plan

## Working Title

Resource-Centric LLM-Augmented Multi-Agent Process Simulation for Business Process Mining

## Candidate Research Question

How can log-derived resource-agent profiles and local behavior priors be used to constrain LLM-augmented agent decisions so that a resource-centric multi-agent simulator generates process-mining-compatible event logs and interpretable reasoning/handover traces?

## Sub-Questions

1. Which agent characteristics can be robustly derived from a business process event log?
2. How should these characteristics constrain LLM-agent decisions during simulation?
3. Does an agentic/LLM-agent simulation reproduce held-out event-log behavior better, worse, or differently than a traditional BPS baseline?
4. What failure modes appear when LLM agents are allowed to influence process decisions?

## Recommended Contribution Type

Design Science Research plus controlled experiment.

Artifact:

- A lightweight resource-centric simulator that represents resources as agents.
- A local policy interface with three implementations:
  - central or statistical baseline,
  - log-derived resource-agent policy,
  - constrained LLM-agent or deterministic LLM-proxy policy.
- Event-log output compatible with process mining.
- Reasoning-log and handover-log output for the LLM condition.

Formal framework:

```text
H_R-LLM = (L, A, P_env, X, Pi_log, M, B_LLM, S, O, V)
```

Key design principle:

> LLM agents should reason over log-grounded local feasible actions, not freely generate process behavior.

Evaluation:

- Compare simulated logs against held-out real logs.
- Use Chapela-Campa et al.'s BPS quality framework where feasible.
- Add prototype-level metrics when the full framework is too heavy for the first iteration.

## Chosen Feasible Path

Use a small real-world or benchmark process log with case id, activity, resource, start timestamp, and end timestamp. Split it into train/test. Learn agent profiles from train:

- capability matrix: resource -> activities,
- service-time distribution per resource/activity,
- activity preference distribution,
- simple workload/priority sensitivity,
- local next-activity priors,
- handover frequencies if present,
- inter-event waiting and extraneous-delay distributions.

Run three simulation variants on the same arrival schedule:

1. `central_baseline`: centralized FIFO scheduler and pooled/random qualified resources.
2. `agent_profile`: decentralized resource agents choose tasks according to learned preferences and workload heuristics.
3. `llm_agent`: same guardrails, but an LLM or LLM-proxy chooses among valid local actions using structured state, case context, memory, and historical priors.

Evaluate against the held-out test log:

- trace variant distribution distance,
- activity frequency distance,
- mean/median cycle-time error,
- resource workload distribution distance,
- waiting-time/service-time error when start/end timestamps are available,
- qualitative failure taxonomy.

## Data Choice

Primary recommendation: use the Chapela-Campa et al. Zenodo artifact because it already contains original event logs, simulated logs, BPS models, and distance-measure code.

Fallback: use AgentSimulator raw/event-log datasets if the Zenodo artifact is too large or difficult to normalize.

Pilot: use a synthetic mini-log to validate the experimental pipeline before downloading large artifacts.

## Expected Claims

Careful wording is important. The expected report should not claim that LLM agents are universally more accurate. A defensible claim is:

> A resource-centric LLM-agent simulation architecture can generate process-mining-compatible event logs plus reasoning/handover traces, but LLM behavior must be bounded by event-log-derived local action spaces and evaluated with standard BPS log-distance measures.

## Risks And Mitigations

- LLM nondeterminism: use temperature 0, structured prompts, action masks, repeated seeds, and a deterministic proxy baseline.
- LLM over-selection of "best" resources: use distributional guardrails and compare resource distribution distances.
- Evaluation complexity: first run proxy metrics, then integrate `ComputeLogDistance.py` from Zenodo.
- Data normalization: write one canonical event-log schema.
- Scope creep: limit the artifact to one process and three simulation variants.
- Weak novelty: emphasize the bridge between event-log-derived constraints and LLM-agent decision modules, not generic LLM prompting.
