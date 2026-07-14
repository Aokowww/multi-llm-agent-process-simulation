# Resource-Agent Sequentialisation Diagnostic

These files document an unsuccessful compatibility experiment. The prototype
added persistent resource state and queueing to the existing trace sampler.
On LoanApp, this increased mean cycle-time error because case activities that
overlap in the observed log were represented as a strict sequence.

`initial_double_waiting_run/` also sampled observed inter-activity waiting
times before resource queueing, thereby counting part of the delay twice.
`corrected_waiting_run/` removed that duplication and used
activity-conditioned handover priors, but cycle-time error remained high due
to structural sequentialisation.

These runs are retained as negative diagnostics. They are not official
AgentSimulator results and are excluded from manuscript performance claims.
The executable modes were subsequently renamed from `agent_simulator_*` to
`resource_agent_*` to prevent that confusion.
