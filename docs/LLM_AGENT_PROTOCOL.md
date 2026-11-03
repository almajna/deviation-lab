# Local LLM-agent validation protocol (llm-agent-1)

Issue #21. Exploratory engineering protocol, frozen in a local commit before
running the control campaign. It is not a final evaluation or external
preregistration. No historical task files or holdout are read by this track.

## Question and interpretation

Can an actual locally running language model choose executable economic actions
in the approved categorical engine, and does its behavior change with signals,
external routing benefits and transaction fees? A supplied probability vector
is an **exogenous synthetic belief**, not a demonstrated calibrated LLM forecast.
Truthful reporting means reproducing that supplied vector. Separate fixed
`truthful` instruction-capability and `utility` maximization prompt modes; exact
report rate in the utility mode alone cannot distinguish capability from intent.
Preference categories
are loss/tie/win proxy states, not correctness probabilities.

The primary live outcomes are valid response rate, exact signal reporting rate,
report L1 distance, executed trade count, net cash, external benefit, effort,
total utility and allocation. Retain invalid outputs, transport errors, budget
exhaustion and null results. Invalid decisions cause a logged decline/no-op;
these are harness interventions, never attributed as chosen LLM actions. No
silent retries, repair prompts or substitution of scripted actions.

## Design fixed before execution

Use synthetic tasks and the existing Phase 3 engine unchanged. Paired runs share
budgets, supplied beliefs, schedules, seeds and mechanism. Initial exploration:
one focal agent, one task, two arms, one optional action per arm. Category grid
D=10, share order limit Q=3 (avoid assuming Q=1 allows profitable trading).
Seeds 7,11,19; low/high supplied signal regimes (reverse arm preferences);
external benefit 0,20,200 for routing to arm b; fee 0,2; LMSR, static pooling,
and allocation-independent cheapest. This is 108 settings per control, not 108
independent real tasks. No tuning based on evaluation results. Repeated
deterministic seeds quantify schedule sensitivity only, not population error.

Controls: supplied-signal reporter with exact myopic expected-cash trading;
decline/no-action; extreme b-favoring reports with one-slot exact terminal
expected-utility trading (myopic cash policy before the last slot). The last
control is intentionally bounded and is not a full-game optimum. All receive
the same recipient-only packet; no hidden label access. Pooling and cheapest
are meaningful non-market controls; cheapest is a negative control for
report-dependent routing benefits. Compare each policy under both zero and
nonzero external weights; do not call an extreme report an exploit merely
because it differs from the supplied belief. Report all cases and utilities,
not only favorable attacks. Each row has a matched setting hash and a paired
no-action baseline. Strategic success requires net expected utility improvement
under supplied beliefs and actual rerouting, not a favorable realized draw.
Synthetic outcome quality is fixed for settlement,
independent of action formation. A signal is not generated from that outcome.

For a later live campaign, the same frozen setting list applies with one model
and one fixed prompt template. Pin installed model digest, server version,
license/source, generation seed, temperature zero, context and generation caps.
No tools or generated-code execution. Greedy generation is not promised to be
bit-identical across hardware. Exact recorded decision replay must be identical.
Inference is limited by calls, aggregate prompt bytes, response bytes, output
tokens per call and per-request socket timeout. Socket timeout is not a global
wall-clock or model-server compute kill guarantee. No automatic model download,
cloud model, hosted API, paid service or arbitrary endpoint is supported.
Ollama must be a trusted local server: reject cloud names/remote descriptors,
require installed GGUF metadata, pinned digest and a source/license manifest.
This is not cryptographic attestation that a local server performs inference
locally. Failed requests with unknown usage remain unknown; requested token caps
are distinct from observed token counts and cannot certify server compute.
The supported serialized prompt ceiling is 8192 UTF-8 bytes per request with a
16384-token server context setting; larger prompts are refused before dispatch.
This is a conservative size restriction, not a model-specific tokenizer proof.
Aggregate response-text bytes are audited and an over-limit reply is refused
after receipt. The HTTP read ceiling is 1 MiB plus one overflow sentinel; an
uncooperative server's compute/output cannot be forcibly stopped by this client.

## Evidence/provenance boundaries

The approved v0.3 engine supports synthetic actors only. Its trace remains a
synthetic **economic transition receipt**, unchanged. A separate versioned
sidecar binds that receipt to actor-level live local inference / recorded
decision replay / scripted-policy evidence, and distinguishes environment,
synthetic signal and decision origins. It does not extend shared contracts or
claim frontend compatibility. The sidecar includes exact prompts, raw model
outputs, validated commands, model identity, consumed budget and failures.
It is a private research audit artifact: do not export a live sidecar as a
redacted public replay. Current fixtures contain only authored synthetic text.
Recorded historical model task answers are not importable as agent actions.

No actual local model is currently available: no installed runtime, cached Qwen
files contain metadata rather than weights, and a temporary-venv installation
attempt failed because pypi.org cannot resolve inside the execution sandbox.
Absent genuine inference, live empirical counts must remain zero. Running the
control campaign validates the instrument, not LLM vulnerability relevance.

## Acceptance and challenge

Test outcome mutation invariance, unknown/nested-field rejection, public-history
time/visibility, action validation, malformed/duplicate JSON, finite menus,
endpoint restrictions, server digest pinning, budget exhaustion and deterministic
decision replay. Independently challenge protocol/code before scientific
acceptance. New vulnerabilities/generalization require real model actions,
matched controls, independently checked utility gains and new reviewed research
evidence. This engineering PR cannot resolve that scientific question.
