# Pilot and Implementation Check Summary

This file records the main implementation checks that led to the
archived experiment outputs. It is included to document how the final
prototype reached its current configuration.

## Synthetic Pipeline Check

The initial synthetic pipeline verified that the simulator could learn
resource profiles, generate event logs for the default policies, and
compute lightweight metrics. The check showed that a deterministic
resource-choice rule could over-select historically frequent resources.
This motivated the use of action masks and distributional guardrails in
the LLM-agent proxy.

## AcademicCredentials Smoke Test

The first real-log smoke test confirmed that the pipeline could run on
AcademicCredentials train/test logs. The initial temporal fidelity was
poor because the simulator did not yet model realistic inter-event
waiting time or case arrivals.

## Temporal and Arrival Corrections

The simulator was extended to sample empirical service times,
inter-event waiting times, and case inter-arrival times from the
training log. Simulations were also aligned to the first timestamp of
the held-out test log. These changes corrected the main timing failure
observed in the first smoke test.

## Guarded LLM-Agent Proxy

The proxy policy was changed from a deterministic "best resource" rule
to a guarded local resource-assignment rule. The final proxy uses
handover priors when available, activity-resource priors otherwise, and
an overuse penalty relative to historical target shares. It also writes
reasoning and handover logs.

## Final Repeated Evaluation

The final archived AcademicCredentials results use ten repeated runs per
condition. The final implementation uses paired common random numbers:
the policies share process-structure and timing draws within a run, and
resource choices use a separate random stream. This correction removes
random trace-generation differences from the policy comparison.

The formal Chapela-Campa results show a dimension-specific trade-off.
Control-flow and case-arrival metrics are identical across policies by
construction. The agent-profile policy has the lowest mean absolute
timing EMD, while the LLM-agent proxy has the lowest mean workforce EMD,
relative EMD, and cycle-time Wasserstein distance. These are descriptive
prototype results, not evidence of uniform or statistically robust
outperformance. The proxy also adds decision and handover traces that
the statistical policies do not provide.
