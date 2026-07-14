# Real-LLM LoanApp Llama Replications

This directory contains sanitized summaries for the planned three-seed,
100-case LoanApp experiment using Groq `llama-3.1-8b-instant` and prompt
`resource-choice-v3-compact-schema`.

The Llama condition is separate from the earlier GPT-OSS pilot. It is a
time-stamped free-tier experiment because the provider has announced
retirement of this endpoint on 16 August 2026.

Current completion status: **2 of 3 replications**.

No repeated-result or significance claim should be made until seeds
8200, 8300, and 8400 have all completed and been analyzed together.

Across the first two seeds, the real-LLM condition has the lowest mean
cycle-time distance and the lowest mean workforce EMD, but a much worse
identity-level resource-distribution distance. This is a preliminary
dimension-specific pattern, not an overall performance claim.

Raw prompts, response caches, reasoning traces, private paths, and API
credentials are not included in the public repository.
