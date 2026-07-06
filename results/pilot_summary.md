# Pilot Summary

## Synthetic Pipeline Check

The synthetic pilot generated train/test logs, learned resource profiles, produced three simulated logs, and computed lightweight distance metrics. The `agent_profile` condition improved mean cycle-time relative error versus the central baseline in the latest run, while the deterministic `llm_agent_proxy` produced a much worse resource distribution because it over-selected the historically strongest resource.

Interpretation: LLM-style decision modules need action masks plus distributional guardrails. Otherwise, "rational" or greedy decisions can reduce resource realism.

## AcademicCredentials Smoke Test

The same pipeline was run on the Zenodo `AcademicCredentials` train/test logs.

Key finding:

- The pipeline is executable on real logs.
- Trace/activity/resource metrics are produced.
- The first version had poor temporal fidelity because it lacked arrival, calendar, waiting-time, and extraneous-delay modeling.

This is not a negative result; it identifies the next required implementation step and aligns the thesis with the BPS literature.

## Temporal V2 Result

The simulator was upgraded to learn empirical service-time samples and empirical inter-event waiting-time samples from the train log. This is a minimal executable approximation of an extraneous/inter-event delay layer.

`AcademicCredentials` result after this change:

| Mode | Trace variant distance | Activity distance | Resource distance | Mean cycle-time relative error |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.3266 | 0.0743 | 0.7436 | 0.0419 |
| `agent_profile` | 0.3090 | 0.0859 | 0.6117 | 0.0424 |
| `llm_agent_proxy` | 0.3643 | 0.1229 | 0.8926 | 0.0005 |

Interpretation:

- Adding empirical inter-event waiting times fixes the earlier temporal failure: mean cycle-time error drops from about 98.6% to about 4.2% for the non-LLM baselines.
- The deterministic `llm_agent_proxy` has excellent mean cycle-time error in this run, but very poor resource distribution distance. This is a useful warning: a greedy or overly deterministic agent decision policy can match one temporal statistic while destroying resource realism.
- The next model improvement should add distributional guardrails for resource selection and handover, not simply make the agent "choose the best" option.

## Guardrails V3 Result

The `llm_agent_proxy` was changed from a deterministic "choose the historically strongest resource" rule to a guarded local decision rule:

- prefer handover priors when a previous resource exists,
- otherwise use activity-level resource priors,
- sample from feasible resources rather than taking the maximum,
- penalize over-used resources relative to historical target shares,
- emit `reasoning_llm_agent_proxy.csv` and `handover_llm_agent_proxy.csv`.

`AcademicCredentials` result after this change:

| Mode | Trace variant distance | Activity distance | Resource distance | Mean cycle-time relative error |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.3266 | 0.0743 | 0.7436 | 0.0419 |
| `agent_profile` | 0.3090 | 0.0859 | 0.6117 | 0.0424 |
| `llm_agent_proxy` | 0.3241 | 0.0775 | 0.6442 | 0.0209 |

Interpretation:

- Resource distribution for `llm_agent_proxy` improved substantially compared with Temporal V2: 0.8926 -> 0.6442.
- Mean cycle-time error remains better than the non-LLM baselines in this single run: 2.09% vs about 4.2%.
- The proxy now produces the extra outputs required by the proposed framework `O=(L', R', H')`.
- The result is still only a pilot: the next step must run repeated simulations and formal BPS distance measures before making comparative claims.

## Repeated V4 Result

The `AcademicCredentials` experiment was repeated 10 times per condition with different seeds. Results are saved in:

- `academic_credentials_repeated_v4/metrics_runs.csv`
- `academic_credentials_repeated_v4/metrics_summary.csv`

Mean +/- standard deviation:

| Mode | Trace variant distance | Activity distance | Resource distance | Mean cycle-time relative error |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.3337 +/- 0.0181 | 0.0998 +/- 0.0151 | 0.7371 +/- 0.0069 | 0.0456 +/- 0.0280 |
| `agent_profile` | 0.3299 +/- 0.0232 | 0.0999 +/- 0.0164 | 0.6198 +/- 0.0066 | 0.0387 +/- 0.0197 |
| `llm_agent_proxy` | 0.3284 +/- 0.0162 | 0.0889 +/- 0.0168 | 0.6508 +/- 0.0098 | 0.0403 +/- 0.0494 |

Interpretation:

- `llm_agent_proxy` has the lowest mean trace variant distance and activity distribution distance in this lightweight metric set.
- `agent_profile` remains best on resource distribution distance, which is expected because it directly samples activity-resource frequencies.
- `llm_agent_proxy` cycle-time error is comparable to `agent_profile` on average but has larger variance, so stability is a real issue.
- The proxy emitted reasoning rows for every generated event and handover rows for cross-resource transitions, giving a first implementation of `O=(L', R', H')`.
- These are still lightweight pilot metrics. Formal Chapela-Campa distance measures should be run next.

## Arrival V6 And Chapela-Campa Distances

The formal Chapela-Campa distance wrapper first exposed an important bug: simulated logs started in 2026 while the held-out `AcademicCredentials` test log starts in 2016. This produced meaningless absolute and case-arrival distances around 85,000 hours.

The simulator was corrected to:

- learn empirical case inter-arrival samples from the training log,
- start each evaluation simulation at the first timestamp of the held-out test log,
- keep service-time and inter-event waiting-time sampling from earlier versions.

After this correction, `AcademicCredentials` repeated-run lightweight metrics were:

| Mode | Trace variant distance | Activity distance | Resource distance | Mean cycle-time relative error |
|---|---:|---:|---:|---:|
| `central_baseline` | 0.3357 +/- 0.0227 | 0.0988 +/- 0.0105 | 0.7391 +/- 0.0031 | 0.0507 +/- 0.0371 |
| `agent_profile` | 0.3281 +/- 0.0242 | 0.0912 +/- 0.0145 | 0.6123 +/- 0.0046 | 0.0413 +/- 0.0249 |
| `llm_agent_proxy` | 0.3271 +/- 0.0100 | 0.0945 +/- 0.0107 | 0.6404 +/- 0.0121 | 0.0362 +/- 0.0247 |

Formal Chapela-Campa distances were computed for the single `academic_credentials_arrival_v6` generated logs:

| Metric | Best mode | Central baseline | Agent profile | LLM-agent proxy |
|---|---|---:|---:|---:|
| Bigram distance | `agent_profile` | 0.1483 | 0.1480 | 0.1638 |
| Trigram distance | `agent_profile` | 0.1902 | 0.1843 | 0.2077 |
| Absolute event EMD | `agent_profile` | 139.7794 | 89.0428 | 213.7357 |
| Case arrival EMD | `agent_profile` | 161.7312 | 118.3191 | 260.6683 |
| Circadian event EMD | `llm_agent_proxy` | 2.5803 | 2.7430 | 2.5259 |
| Workforce EMD | `llm_agent_proxy` | 3.4426 | 3.1994 | 2.4025 |
| Relative event EMD | `llm_agent_proxy` | 24.2715 | 21.3163 | 12.3325 |
| Cycle-time Wasserstein | `llm_agent_proxy` | 23.0377 | 20.1256 | 19.1106 |

Interpretation:

- `agent_profile` better reproduces control-flow n-grams and absolute/case-arrival timing in this run.
- `llm_agent_proxy` better reproduces workforce, circadian timing, relative event timing, and cycle-time distribution.
- This supports a nuanced claim: the LLM-style local decision module is not uniformly more accurate, but it may improve behavioral/time-distribution dimensions while adding reasoning/handover traces.
- The next formal step is to run Chapela-Campa distances across repeated runs, not only one generated log per condition.

## Repeated Chapela-Campa V7 Result

Chapela-Campa distances were run across 10 generated logs per condition. Results are saved in:

- `academic_credentials_chapela_repeated_v7/chapela_runs.csv`
- `academic_credentials_chapela_repeated_v7/chapela_summary.csv`

Selected mean +/- standard deviation:

| Metric | Central baseline | Agent profile | LLM-agent proxy | Best mean |
|---|---:|---:|---:|---|
| Bigram | 0.1618 +/- 0.0093 | 0.1541 +/- 0.0117 | 0.1548 +/- 0.0071 | `agent_profile` |
| Trigram | 0.2065 +/- 0.0126 | 0.1982 +/- 0.0123 | 0.1988 +/- 0.0090 | `agent_profile` |
| Absolute EMD | 159.6972 +/- 95.8036 | 145.9101 +/- 56.3384 | 155.8600 +/- 84.0634 | `agent_profile` |
| Case-arrival EMD | 184.3430 +/- 99.4617 | 162.4802 +/- 53.4160 | 186.0864 +/- 90.8550 | `agent_profile` |
| Circadian EMD | 3.0208 +/- 0.1159 | 3.0959 +/- 0.3805 | 3.0387 +/- 0.2384 | `central_baseline` |
| Workforce EMD | 3.1951 +/- 0.2822 | 3.4284 +/- 0.3764 | 3.1338 +/- 0.3358 | `llm_agent_proxy` |
| Relative EMD | 16.8700 +/- 3.0403 | 17.3357 +/- 4.1486 | 19.3002 +/- 5.1290 | `central_baseline` |
| Cycle-time Wasserstein | 16.5231 +/- 2.5704 | 17.2359 +/- 3.4244 | 19.1726 +/- 5.4068 | `central_baseline` |

Interpretation:

- `agent_profile` is the strongest condition for control-flow n-grams and absolute/case-arrival event timing.
- `llm_agent_proxy` is close to `agent_profile` on n-grams and has the best workforce EMD, but it is not the best overall condition.
- `central_baseline` is strongest on circadian, relative-event, and cycle-time measures in this repeated formal run.
- The correct thesis claim is therefore not "LLM-agent simulation improves BPS quality overall." A defensible claim is: a resource-local LLM-style decision module can be integrated into a BPS pipeline, produces event/reasoning/handover logs, and yields competitive but dimension-specific quality trade-offs against statistical baselines.

## Next Code Tasks

1. Add basic LLM-specific metric summaries: fallback rate, handover count, feasible action-set size.
2. Draft the Results and Discussion section from the lightweight and Chapela-Campa tables.
3. Add an optional real LLM decision module behind the same local action-space interface.
