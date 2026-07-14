# Real-LLM LoanApp Llama Replications

This directory contains sanitized summaries for the planned three-seed,
100-case LoanApp experiment using Groq `llama-3.1-8b-instant` and prompt
`resource-choice-v3-compact-schema`.

The Llama condition is separate from the earlier GPT-OSS pilot. It is a
time-stamped free-tier experiment because the provider has announced
retirement of this endpoint on 16 August 2026.

Current completion status: **3 of 3 replications**.

Seeds 8200, 8300, and 8400 are summarized in
`three_run_summary.csv`. The table reports descriptive mean, sample
standard deviation, and within-seed win count. With only three paired
replications, these results are not presented as a significance test.

Across all three seeds, the real-LLM condition has the lowest mean
workforce EMD and wins that metric in two seeds. It does not have the
lowest mean cycle-time or relative-event distance. Its identity-level
resource-distribution distance is consistently much worse than every
comparison policy. The result is a dimension-specific trade-off, not
an overall performance gain.

`three_run_paired_metrics.pdf` and its SVG/PNG counterparts visualize
the paired resource-distribution, cycle-time, and workforce results.
They can be regenerated with `src/plot_llm_replications.py`.

`decision_mechanism_diagnostics.csv` and
`activity_selection_concentration.csv` summarize the factor labels and
within-activity concentration used to diagnose the resource-identity
failure without publishing raw model responses.

`llm_specific_evaluation/` contains run-level and summary tables for the
additional agent-level metrics. The real LLM has mean resource coverage
of 0.544, normalized assignment entropy of 0.656, and an effective
resource count of 6.90. All comparison policies have full coverage,
normalized entropy above 0.982, and more than 18 effective resources.
Within activities, the real LLM has mean capability coverage of 0.386
and conditional entropy of 0.078. The calculation is implemented in
`src/analyze_llm_specific_evaluation.py`.

Raw prompts, response caches, reasoning traces, private paths, and API
credentials are not included in the public repository.
