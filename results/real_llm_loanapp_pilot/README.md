# Real-LLM LoanApp Pilot

This directory contains reviewer-facing summary tables from the initial
API-backed `llm_agent_real` evaluation. The provider was Groq and the
model was `openai/gpt-oss-20b`. No API key, prompt payload, private path,
or manuscript file is included.

## End-to-End Smoke Test

The clean smoke test used 20 held-out LoanApp cases and seed 8100. All
149 API decisions succeeded, with no invalid outputs, fallbacks, or
rate-limit retries. The agent-profile policy had the lowest resource
distance and cycle-time error. The real LLM therefore validated the
execution path but did not outperform the statistical baseline.

## Decision Benchmark

The benchmark sampled 100 held-out resource decisions. Feasible-action
coverage was 99%. Real-LLM top-1 agreement was 34.34%, compared with
33.33% for activity-prior argmax and 28.28% for handover-prior argmax.
The real-LLM advantage over activity-prior argmax was 1.01 percentage
points, with a paired bootstrap 95% interval of -7.07 to +10.10 and an
exact McNemar p-value of 1.000. This is not evidence of a reliable
accuracy improvement.

The real LLM achieved 100% API success, 100% reason-action mention, and
100% valid factor labels in the benchmark. The pilot therefore supports
operational validity and auditability, not an outperformance claim.

Formal Chapela-Campa distances lead to the same interpretation. The
real LLM has the lowest absolute EMD by a small margin, while the central
baseline has the lowest workforce EMD and the agent-profile policy has
the lowest cycle-time Wasserstein distance. All formal results are based
on one 20-case run and remain descriptive.

## Files

- `end_to_end_metrics.csv`: lightweight end-to-end metrics by policy.
- `api_summary.csv`: aggregate API validity, token, and latency data.
- `decision_summary.csv`: held-out decision metrics by policy.
- `formal_distances.csv`: selected formal BPS distances for the same
  clean end-to-end pilot.
- `paired_comparison.csv`: paired uncertainty estimates for real LLM
  versus deterministic prior baselines.
mode,cases,seed,bigram,trigram,absolute_emd,case_arrival_emd,circadian_emd,workforce_emd,relative_emd,cycle_time_wass
central_baseline,20,8100,0.1686746988,0.2741935484,855.9335664336,818.75,8.3113953752,11.1201991869,1.9300699301,54.35
agent_profile,20,8100,0.1686746988,0.2741935484,860.0069930070,818.75,8.4300519849,11.3789949315,1.9370629371,33.10
llm_agent_proxy,20,8100,0.1686746988,0.2741935484,848.0524475524,818.75,11.5367492285,14.2681906126,8.7902097902,210.55
llm_agent_real,20,8100,0.1686746988,0.2741935484,847.5944055944,818.75,11.4255821049,13.6018674113,8.8671328671,188.20
