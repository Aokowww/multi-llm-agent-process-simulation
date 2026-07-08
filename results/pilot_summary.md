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
condition. The formal Chapela-Campa results show a dimension-specific
trade-off: the agent-profile policy is strongest on several
control-flow and absolute/case-arrival timing metrics, the central
baseline is strongest on several temporal metrics, and the LLM-agent
proxy is strongest on workforce EMD while adding reasoning and handover
observability.
