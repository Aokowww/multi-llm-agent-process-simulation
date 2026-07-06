# Literature Map: Multi-LLM-Agent Process Simulation

## What The Kickoff Requires

From `260415_Kickoff.pdf`, the study project has a 3-month duration after registration and must deliver a 12-15 page scientific report plus final presentation. The work should apply Information Systems methods such as design science, experiments, and/or data analysis, and should aim for a scientific contribution that extends knowledge. The topic goal is to design and implement a novel multi-LLM-agent process simulation that reproduces a small real-world business process and generates event logs suitable for process mining, then evaluate it against traditional BPS.

Initial references named in the kickoff:

1. Kirchdorfer, L., Blumel, R., Kampik, T., Van der Aa, H., and Stuckenschmidt, H. 2024. "AgentSimulator: An Agent-Based Approach for Data-Driven Business Process Simulation." ICPM 2024. https://doi.org/10.1109/ICPM63005.2024.10680660
2. Gao, C. et al. 2024. "Large Language Models Empowered Agent-Based Modeling and Simulation: A Survey and Perspectives." Humanities and Social Sciences Communications 11, 1259. https://doi.org/10.1057/s41599-024-03611-3
3. Sargent, R. G. 2013. "Verification and Validation of Simulation Models." Journal of Simulation 7(1), 12-24. https://doi.org/10.1057/jos.2012.20

Added evaluation anchor:

4. Chapela-Campa, D., Benchekroun, I., Baron, O., Dumas, M., Krass, D., and Senderovich, A. 2025. "A Framework for Measuring the Quality of Business Process Simulation Models." Information Systems 127, 102447. https://doi.org/10.1016/j.is.2024.102447

## Core Synthesis

The literature has three mature but weakly connected streams:

1. Data-driven BPS learns control-flow, timing, arrival, resource, calendar, multitasking, and delay parameters from event logs. This stream is empirically grounded and evaluable, but it often treats resources as pools or parameterized servers.
2. Agent System Mining and AgentSimulator move from a process-first to a resource/agent-first view. Agents are discovered from event logs, and simulation decisions are shifted toward individual resources.
3. LLM-based multi-agent simulation provides reasoning, planning, communication, and behavioral heterogeneity, but current LLM-agent behavior is usually prompt-configured rather than calibrated against event logs.

The research gap is therefore not "can LLMs simulate a process?" in general. The sharper gap is: how can LLM-enabled agents be grounded and constrained by event-log-derived agent profiles so that their generated process logs remain measurable, reproducible, and comparable with traditional BPS?

## Paper Clusters

### A. BPS Quality And Evaluation

- Chapela-Campa et al. define a framework for measuring how well a BPS model reproduces observed process behavior. Their Zenodo artifact provides original event logs, simulated logs, distance measures, and code: https://zenodo.org/records/12126071
- This should be the thesis evaluation backbone because it avoids a vague "looks realistic" criterion.

### B. Agent-Centric BPS

- AgentSimulator discovers a multi-agent system from event logs, modeling distinct resource behaviors and interaction patterns. Its supplementary repository includes runnable code and evaluated datasets: https://github.com/lukaskirchdorfer/agentsimulator
- Agent System Mining and Agent Miner provide the conceptual route from event logs to agents, local behavior models, and interaction models.

### C. Resource-Centric And Data-Driven BPS

- Differentiated resources: individual resources can have distinct service-time distributions and calendars.
- Probabilistic calendars and multitasking: resources are not simply "available/unavailable"; they have stochastic availability and capacity profiles.
- Extraneous delays: some waiting cannot be explained by queues/resources and should be modeled as process delays.
- Data-aware BPS and hybrid DES/deep-learning methods show how case attributes and learned predictors can enter the simulation loop.

### D. LLM-Based ABM And Multi-Agent Systems

- Gao et al. survey LLM-empowered ABM and identify the promise of LLMs for richer agent cognition and communication.
- LLM multi-agent systems in manufacturing/scheduling show that LLMs can act as decision modules or coordinators, but they are often not log-calibrated.
- Agentic BPM and Agentic BPMS work frames a future BPM stack where process mining, event logs, and autonomous agents form a learning loop.

## Research Value

The project is valuable because it contributes at the intersection of three measurable needs:

- Scientific: bridges log-derived BPS and LLM-agent simulation with a concrete prototype and evaluation.
- Methodological: turns LLM-agent process simulation into an evaluable artifact rather than a speculative architecture.
- Practical: helps assess whether LLM agents can add behavior flexibility while preserving process-mining-compatible event logs and standard BPS quality.

## Feasible Study-Project Scope

Recommended scope for a 12-15 page report:

- One small process, preferably from the Chapela-Campa/Zenodo or AgentSimulator artifact family.
- Two or three simulation variants:
  - Traditional/resource-pool baseline.
  - Event-log-derived agent baseline.
  - LLM-agent or LLM-proxy agent variant with log-derived guardrails.
- Evaluation on held-out logs with control-flow, temporal, and resource distance metrics.
- Qualitative analysis of design trade-offs: interpretability, reproducibility, prompt instability, computational cost, and failure modes.

