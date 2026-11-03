# Agent 3: real LLM-agent instrument, scientific validation blocked

Issue #21. **Actual LLM inference calls: 0. Actual LLM decisions: 0. Spend: $0.**
The scientific question—whether the economic vulnerabilities matter for real
LLM-driven agents—remains unanswered. No simulated strategy, transport fixture,
or recorded task answer is counted as a real LLM decision.

## What works

`deviation_llm_agents` is an independently packaged sibling of `deviation`, using
the existing approved engine through its injected-policy interface. Existing
market/simulator/attack sources, scientific contracts, historical artifacts,
README, license, frontend and holdout are unchanged. Keeping a separate package
also preserves the historical whole-`deviation` implementation fingerprint.

The optional Ollama adapter uses only a literal loopback endpoint, disables HTTP
proxies/redirects, refuses cloud names and remote descriptors, and requires an
installed GGUF model with a pinned digest and explicit source/license manifest.
It never downloads, trains, invokes a hosted model, or executes generated code.
Generation uses temperature zero, a fixed seed, bounded output and context.
Backend/server versions and model metadata accompany an observed run. Only a
trusted local server can establish local computation; loopback is not execution
attestation. The real server integration is not exercised in this environment.

Agent input is a closed recipient-specific packet: public state, its own
synthetic belief, holdings, cash, public history, fixed reservations and own
external benefits. Labels and realized costs enter the engine after allocation
locks. Tests mutate hidden outcomes and verify identical prompts/actions/plans.
Malformed and duplicate JSON, unsupported actions, unknown/nested fields and
future/private history fail explicitly. Valid output becomes an exact engine
command; invalid output produces a logged harness decline/no-op. There are no
retries, output repair, tools, or silent scripted substitution.

Two prompt modes separate truthful-instruction capability from utility
maximization. Exact supplied-signal reporting is a narrow operational measure,
not a proof of truthfulness or calibrated beliefs. A finite executable trade
menu includes quotes, fees and price changes; the adapter does not select the
optimal action for the model. `certificate_problem(packet)` exports immutable
context/menu hashes and an explicit unsupported-future-policy scope. It supplies
no new mathematical certificate or integration with Agents 1/2's new research.

Every decision records exact prompt, raw model text, usage, requested caps,
failures, fallback commands and attempted/skipped status. Malformed local HTTP
responses retain a bounded raw-body audit. Failed attempts with unknown usage
remain unknown. Backend attempts include pre-generation identity checks, so
they conservatively bound dispatch attempts rather than proving GPU calls.
Budgets bound dispatch count and input bytes; server token caps are requested
and observed separately. Over-limit output is rejected after receipt. The
client cannot forcibly stop a misbehaving server or prove its compute cost.

Observed local decisions, scripted controls and recorded decision replay have
separate origin labels. The unmodified v0.3 engine trace remains a **synthetic
economic transition receipt**; a versioned sidecar binds actor evidence to it.
No shared-contract support for live agents or public-frontend compatibility is
claimed. Live audit sidecars contain recipient-private prompts and must not be
treated as redacted public replay. Recorded replay makes zero new model calls,
requires identical prompt/context/source hashes and recomputes provenance,
counters, commands, economic receipts and metrics. Hashes check consistency,
not whether an investigator honestly obtained a transcript.

## Observed blocker

`artifacts/llm_agents/availability.json` records the actual local inventory:
arm64/Python 3.12.15; no torch, transformers, mlx_lm or llama_cpp import; no
ollama/llama-cli executable. The inspected Qwen3-0.6B cache has no named weight
files or blobs over 50 MB; this is not an inventory of every file on disk.
An attempted installation of torch 2.6.0 and transformers 4.51.3 into a temporary
venv failed with `Could not resolve pypi.org` / `NameResolutionError`. No package
or weights were downloaded, and no model was invoked. The network restriction
was not bypassed. Inventory uses no network or inference and is host-specific.

## Scripted instrument evidence

Protocol was committed locally before evaluation (`c72ef5d`, clarified before
execution in `c8543e7`). It was independently challenged before the campaign.
GitHub publication occurs after local evaluation; this is not an externally
timestamped preregistration. Review fixes hardened audit behavior; all 324
result rows remained identical. The final source hash is
`301add6d7f5b901203fd68123a6e05812716b45bff5b092456409d535f74c7fd`.

There are 108 settings × 3 scripted policies = **324 runs**, on one authored
synthetic task. Settings vary three schedules, two supplied-belief regimes,
three external benefits, two fees and three mechanisms. All cases, exact
expected/realized utilities, no-action controls, transfers and routing decisions
are retained. Existing independent event-level accounting recomputes payoff.
Each comparison below has 12 directional-control cases against matched signal
controls. “Joint” requires both strictly positive expected utility gain and
changed allocation; it does not imply a novel or real-agent exploit.

| Mechanism | External benefit | Rerouted | Positive expected gain | Joint |
|---|---:|---:|---:|---:|
| LMSR | 0 | 0/12 | 0/12 | 0/12 |
| LMSR | 20 | 9/12 | 0/12 | 0/12 |
| LMSR | 200 | 9/12 | 3/12 | 3/12 |
| Static pooling | 0 | 6/12 | 0/12 | 0/12 |
| Static pooling | 20 | 6/12 | 0/12 | 0/12 |
| Static pooling | 200 | 6/12 | 0/12 | 0/12 |
| Cheapest | 0 | 0/12 | 0/12 | 0/12 |
| Cheapest | 20 | 0/12 | 0/12 | 0/12 |
| Cheapest | 200 | 0/12 | 0/12 | 0/12 |

The three joint cases use b-favoring beliefs, benefit 200 and fee 2; expected
utility gains are exactly 831/5, 831/5 and 833/5. They illustrate a bounded
programmed control paying trading/scoring costs for a large external routing
reward. Static extreme reports often reroute but lose net expected utility.
Cheapest correctly ignores reports. The directional control is not optimized
over all reports or future policies; nulls do not prove robustness. Scoring
participation subsidies and external utility are separate in every result.
Synthetic beliefs are exogenous subjective vectors, not Bayesian observations;
realized quality/utility is not used to choose actions or establish expected
gain. Repeated schedules on one constructed task cannot support a population
confidence interval, LLM behavior claim or mechanism comparison/generalization.

## Reproduction

From the repository with Python >=3.11:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation_llm_agents controls --out /tmp/llm-controls.json
cmp artifacts/llm_agents/controls.json /tmp/llm-controls.json
PYTHONPATH=src python3 -m deviation_llm_agents replay \
  artifacts/llm_agents/test_transport_episode.json --out /tmp/llm-replay.json
cmp artifacts/llm_agents/test_transport_replay.json /tmp/llm-replay.json
PYTHONPATH=src python3 -m deviation_llm_agents inventory --out /tmp/llm-inventory.json
```

The sample sidecar is prominently `SCRIPTED_TRANSPORT_TEST`, with zero real
model decisions. Its measured transport timing is not a model performance
measurement. The replay command requires only the installed package, not tests,
Ollama or a dataset. CI additionally installs the package and reproduces both
artifacts with isolated Python.

To run a real experiment later, first install a reviewed open-weight model in
a trusted local Ollama server with cloud disabled. Check its license, use its
actual local `/api/tags` digest, and create a JSON manifest containing exactly
`model`, `digest` (64 lowercase hex), `source` (upstream HTTPS URL), and
`license` (reviewed identifier). No placeholder manifest is empirical evidence.
Then use the explicit live command:

```sh
python3 -m deviation_llm_agents live --model-manifest /tmp/local-model.json \
  --seed 7 --signal a_high --benefit 0 --fee 0 --mechanism lmsr \
  --mode truthful --max-calls 4 --out /tmp/llm-truthful.json
```

Use matched `utility` runs under the frozen settings before interpreting
incentive sensitivity. Do not select a favorable model/prompt after looking at
these results without labeling subsequent work exploratory. Preflight failures
produce a zero-inference blocker artifact and nonzero exit; per-decision
failures remain in the completed sidecar. A real-model campaign and scientific
review are the next research steps, not completed work.
