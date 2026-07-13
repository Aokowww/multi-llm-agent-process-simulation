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

## Files

- `end_to_end_metrics.csv`: lightweight end-to-end metrics by policy.
- `api_summary.csv`: aggregate API validity, token, and latency data.
- `decision_summary.csv`: held-out decision metrics by policy.
- `paired_comparison.csv`: paired uncertainty estimates for real LLM
  versus deterministic prior baselines.
