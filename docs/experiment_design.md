# Experiment Design

## Experiment Objective

Test whether an agentic process simulator with log-derived constraints can generate event logs closer to a held-out real log than a traditional centralized simulation baseline, and whether an LLM-agent decision module changes accuracy, interpretability, and failure modes.

## Experimental Units

- Input: event log with `case_id`, `activity`, `resource`, `start_time`, `end_time`.
- Output: simulated event log in the same schema.
- Unit of comparison: test log vs generated logs.

## Conditions

| Condition | Decision locus | Learned from log | LLM involvement |
|---|---|---|---|
| `central_baseline` | central scheduler | activity durations, resource capabilities | none |
| `agent_profile` | individual resource agents | capabilities, durations, preferences | none |
| `llm_agent_proxy` | individual resource agents | same guardrails | deterministic proxy for reproducible main experiments |
| `llm_agent_real` | individual resource agents | same guardrails | optional OpenAI-compatible API-backed implementation with JSON validation and guarded fallback |

The implemented real LLM condition preserves the same action-mask interface as the proxy. For the first optional smoke experiment, it may be invoked at every resource decision. For cost-controlled follow-up experiments, it should be narrowed to selected ambiguous local decision points rather than invoking an LLM for every event. Ordinary transitions can use log-derived priors; the LLM condition should activate when multiple valid local continuations or handover targets exist.

## Dual Evaluation Framework

The project uses a dual evaluation framework. The first layer evaluates generated event-log quality, while the second layer evaluates LLM-agent-specific behavioral quality.

### BPS Log-Quality Metrics

- Control-flow: trace variant distribution distance.
- Temporal: cycle-time error, activity duration error, waiting-time error.
- Resource: resource workload distribution distance.
- Composite: normalized average across metric families.

Full evaluation target:

- Use Chapela-Campa et al.'s `ComputeLogDistance.py` from the Zenodo artifact for formal metrics once real datasets are downloaded.

### LLM-Agent Behavioral Metrics

These metrics complement, rather than replace, BPS log-quality metrics:

| Dimension | Question | Example metrics |
|---|---|---|
| Validity / constraint compliance | Does the agent stay inside the event-log-derived action space? | Invalid output rate, fallback rate, feasible-action compliance, schema compliance. |
| Reasoning quality | Does the rationale match the selected action and local context? | Reason-action consistency, reason-context consistency, hallucinated resource/activity mentions. |
| Handover and coordination quality | Are cross-resource transitions coherent and explainable? | Handover-message consistency, handover rate, role-consistent transfer decisions. |
| Scenario adaptivity | Does the agent respond appropriately when workload or resource capacity changes? | High-load response, reduced-capacity response, bottleneck sensitivity, throughput/cycle-time change. |
| Auditability / governance | Can decisions be traced and reviewed? | Reasoning-log coverage, handover-log coverage, fallback traceability, judge/human-review agreement. |

The current implementation partially supports the second layer through action masks, fallback diagnostics, reasoning logs, handover logs, and what-if stress tests. Full LLM-specific evaluation should be added once API-backed `llm_agent_real` runs are archived.

## Pilot Result Interpretation

The pilot experiment is only a pipeline check. It can validate:

- code can learn profiles from logs,
- each simulator condition emits a valid event log,
- metrics are computed reproducibly,
- outputs are organized for the manuscript.

It cannot validate the research claim until run on real train/test logs.

## First Real-Log Smoke Test

The upgraded pilot was run on `AcademicCredentials_train.csv.gz` and `AcademicCredentials_test.csv.gz`. It successfully produced logs and metric files, but the temporal metric failed badly: the test log's mean cycle time is around 11,027 minutes, while the simple simulator generated roughly 110-158 minutes. This is expected because the current pilot learns service durations and trace variants, but not calendars, waiting time, extraneous delays, or arrival schedules.

Design implication:

- Add inter-event waiting and extraneous delay models.
- Preserve or sample realistic case-arrival timestamps.
- Add resource calendars or availability profiles.
- Treat LLM/agent policies as decision modules after temporal realism is controlled, otherwise LLM decisions will be evaluated against a broken time model.
- Add reasoning and handover logs only after the event-log generator is temporally plausible.

This failure should be kept in the methodology notes because it connects directly to the literature on resource calendars, multitasking, and extraneous delays.

## Temporal V2 Update

The pilot was upgraded to sample empirical service times and inter-event waiting times from the training log. On `AcademicCredentials`, this reduced mean cycle-time relative error from roughly 98.6% to roughly 4.2% for the central and agent-profile baselines.

The deterministic `llm_agent_proxy` achieved very low mean cycle-time error in this single run, but it had the worst resource distribution distance. This supports an important design rule for the thesis:

> LLM-agent decisions must be constrained not only by valid action masks, but also by distributional realism over resources, handovers, and local behavior priors.

Next experimental refinement:

- log the local feasible action set,
- make the LLM/proxy choose from `(activity, next_resource)` pairs with historical priors,
- report fallback/invalid/over-concentration rates,
- run repeated simulations before comparing conditions.

## Guardrails V3 Update

The `llm_agent_proxy` was revised to use handover priors, activity-level priors, stochastic sampling, and a penalty against over-concentrating work on resources that are already over-used relative to historical target shares. It also emits reasoning and handover logs.

On `AcademicCredentials`, this reduced the proxy's resource distribution distance from 0.8926 to 0.6442 while keeping mean cycle-time relative error at 0.0209. This supports the framework premise that an LLM-style agent policy should be:

- local, not global,
- constrained by feasible resources,
- informed by handover priors,
- checked against distributional realism,
- transparent through reasoning and handover traces.

This is still not a final comparative result because only one stochastic run has been executed.

## Repeated V4 Update

The `AcademicCredentials` experiment was repeated 10 times per condition. In the lightweight metric set, `llm_agent_proxy` has the lowest mean trace variant distance and activity distribution distance, while `agent_profile` remains best on resource distribution distance. Mean cycle-time error is similar for `agent_profile` and `llm_agent_proxy`, but the proxy has larger variance.

Implication for the paper:

- The LLM-style local decision module is plausible and can improve some behavioral distributions.
- The resource-centric statistical profile remains stronger for reproducing resource allocation.
- The LLM/proxy condition should be presented as an interpretable extension, not as a universally more accurate simulator.
- Formal BPS distance metrics are needed before final claims.

## Formal Chapela-Campa Metric Update

The project now wraps the public `ComputeLogDistance.py` artifact from Chapela-Campa et al. The first formal run revealed an evaluation-design issue: simulated logs must be aligned to the held-out evaluation window. After adding empirical case inter-arrival sampling and using the test-window start time, absolute/case-arrival metrics became meaningful.

Initial formal result on one `AcademicCredentials` generated log per condition:

- `agent_profile` is best on bigram/trigram control-flow and absolute/case-arrival distances.
- `llm_agent_proxy` is best on circadian event distance, workforce distance, relative event distance, and cycle-time distribution distance.

This strengthens the planned discussion: the proposed LLM-style behavior module should be evaluated as a trade-off across dimensions, not as a simple accuracy improvement.

## Repeated Formal Metric Update

Repeated Chapela-Campa metrics over 10 runs produce a more conservative result than the single-run formal table:

- `agent_profile` is best on bigram, trigram, absolute event EMD, and case-arrival EMD.
- `llm_agent_proxy` is close to `agent_profile` on n-grams and best on workforce EMD.
- `central_baseline` is best on circadian EMD, relative EMD, and cycle-time Wasserstein.

This means the final paper should frame the artifact as a feasible, interpretable extension of resource-centric BPS, not as an accuracy-dominating simulator. The contribution is the framework and the decision/reasoning trace capability, with quality trade-offs measured rigorously.

## Optional Real LLM Implementation Update

The code now includes `llm_agent_real`, an API-backed implementation behind the same constrained local decision interface. The simulator sends a structured state containing the current activity, previous resource, feasible resources, historical priors, and current resource usage to an OpenAI-compatible chat-completions endpoint. The model is instructed to return only JSON with `resource` and `reason`.

The implementation is intentionally guarded:

- the LLM cannot choose resources outside the event-log-derived feasible set,
- invalid JSON or infeasible resources are counted,
- API errors and timeouts trigger a guarded proxy fallback,
- diagnostics are saved as `llm_calls`, `llm_invalid_outputs`, and `llm_fallbacks`,
- reasoning and handover logs are emitted for the real LLM condition as for the proxy.

In the current local verification environment, no `OPENAI_API_KEY` was available, so the real LLM smoke test exercised the fallback path rather than producing API-backed empirical results. Therefore, the paper's quantitative conclusions should continue to use the reproducible proxy results unless a real LLM run is executed, archived, and evaluated with the same metrics.

## What-If Stress-Test Update

The project now includes a separate what-if experiment for operational response analysis. Unlike the held-out log reproduction experiment, this test does not ask which generated log is closest to the original log. It asks how each policy behaves when the environment changes.

The implemented scenarios are:

- `baseline`: learned arrival intensity and full resource availability,
- `reduced_capacity`: the top 20 high-frequency resources operate at 50% capacity,
- `high_load`: case arrivals are compressed by a 1.6x load multiplier,
- `reduced_capacity_high_load`: both interventions are applied together.

The what-if simulator adds a resource-availability queue: if a selected resource is still busy or unavailable, the next event waits until that resource becomes available. This makes capacity interventions visible in cycle time, p90 cycle time, throughput, bottleneck utilization, constrained-resource usage, and handovers per case.

In the AcademicCredentials stress test, the central baseline is strongest on cycle-time and throughput response under the combined intervention. The LLM-agent proxy does not dominate temporally, but it produces far fewer handovers per case. The agent-profile policy relies most heavily on the constrained high-frequency resource group and has the weakest cycle-time response. This supports a multidimensional interpretation of LLM-agent BPS: the agentic policy changes coordination and bottleneck behavior, but it must be evaluated as an operational trade-off rather than as a universal improvement.

## AgentSimulator LoanApp Robustness Update

The project now includes a second dataset from the public AgentSimulator repository: `LoanApp.csv.gz`. This dataset is useful because it comes from the closest related agent-based BPS artifact, uses the same canonical fields needed by the prototype, and has a clearer role/resource structure than AcademicCredentials:

- 1,000 cases,
- 7,492 events,
- 12 activities,
- 19 resources,
- 700/300 case-level train/test split.

The expectation was that AgentSimulator-style data might better expose resource-centric and handover-aware behavior. The result is partly positive but still mixed:

- Under lightweight metrics, LoanApp is easier to reproduce overall than AcademicCredentials. Distances are much lower, especially resource distribution distance.
- The `llm_agent_proxy` does not dominate reproduction accuracy. `central_baseline` is best on trace, activity, and resource distance; the proxy is better than central on mean cycle-time relative error and better than `agent_profile` on resource distance.
- Under formal Chapela-Campa metrics, `central_baseline` is best on bigram and trigram distance, while `llm_agent_proxy` is best on workforce EMD and nearly tied with `agent_profile` on cycle-time Wasserstein.
- Under the high-load what-if scenario, `llm_agent_proxy` has the lowest mean cycle time, lowest p90 cycle time, and highest throughput. Under combined reduced-capacity and high-load stress, however, it performs worst temporally.

This means AgentSimulator LoanApp is a better second dataset for demonstrating conditional value, not a dataset that makes the LLM-agent proxy universally superior. It strengthens the paper's main claim because the same trade-off pattern appears across two datasets: log-grounded LLM-style agents can improve or expose resource/workforce and scenario-response dimensions, but conventional baselines remain strong for control-flow reproduction.


## Reproducibility Protocol

- Fixed random seeds.
- Save all generated logs and metrics.
- Keep raw data separate from derived outputs.
- Log configuration per run.
- Run each stochastic condition at least 10 times in the real experiment.
