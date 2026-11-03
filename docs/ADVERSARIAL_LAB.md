# Adversarial economic laboratory

Phase 4 backend, issue #15. Synthetic engineering research only. No empirical holdout, observed autonomous LLM agents, paid inference, or frontend changes. The approved v0.3 mechanism and contracts are unchanged.

## Reproduce

Python 3.11+; standard-library runtime. From a clean checkout of this PR:

```sh
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python -m deviation.attacks campaign experiments/adversarial_protocol.json --out replay/campaign
cmp artifacts/attacks/phase4/campaign.json replay/campaign/campaign.json
python -m deviation.attacks replay artifacts/attacks/phase4/selected --out replay/selected
python -m deviation.attacks sensitivity artifacts/attacks/phase4/selected --out replay/sensitivity
cmp artifacts/attacks/phase4/sensitivity.json replay/sensitivity/sensitivity.json
```

Generated `replay/` directories are local outputs; do not commit them. The campaign emits complete counterexamples for all 21 verified redirects, not only the selected harmful case. Aggregate receipts and all counterexample manifest hashes are committed; the selected six-receipt bundle is committed in full. `audit_manifest.json` binds relative file paths and content hashes. Replay re-runs optimization, real transitions and settlement, comparing the complete canonical bundle; no generated code or dynamic policy loading.

For another frozen synthetic scenario, use `discover REQUEST.json --out replay/custom`. The JSON request contains `scenario`, `controller`, `mechanism`, and `options` (scope, method, max_nodes, beam_width, seed, environment_counts, public_report_model). `environment_counts` is evaluator-only: it is removed from optimization and used after selection to verify objective gains under the independent environment law. The package API exposes `prepare_game`, `search`, `discover`, `campaign.run_campaign`, and bundle read/write/replay functions. CLI accepts synthetic scenarios only through the underlying market runner.

## Information and search boundary

`Game` contains public decision metadata, frozen train-derived reservations, an outcome-free copied Phase 3 engine, the controller's common declared belief vector, its own private reward preferences, and public market history. It never contains sealed outcomes, other controllers' private reward preferences, unknown future reports/actions, or the evaluator realization seed. `observation()` binds the available information. The research sidecar's belief audit is post-run synthetic research data, not a policy packet or public market trace.

Terminal search executes a signal-following prefix in the trusted harness and searches only the remaining all-controlled suffix. It refuses schedules ending in an uncontrolled actor. Past honest actions are legitimate observations; future honest private actions are never simulated using hidden information inside the optimizer. Coalition members share a declared belief model; heterogeneous beliefs require an explicit future pooling model and are rejected now. These are exact terminal-subgame best responses, not full-game optimality, equilibria, adaptive opponent policies, or proofs of incentive compatibility.

Static report search covers pool, score and calibrated-pool with one final global commitment token and an explicitly public deterministic opponent-report model. It cannot inspect unrevealed opponent signals. Actual model agreement is checked only after strategy selection; mismatch is labeled unverified. This is a narrower information treatment than terminal trading. It cannot establish market/non-market superiority.

Depth-first exact search enumerates the complete declared finite action space using actual `Engine.apply` and its certified trade admissibility checks. A cap raises an exception; a partial run never earns an exact claim. Seeded bounded beam search evaluates real reachable action sequences, includes honest/no-action incumbents, and reports its expansion budget and best-found status. It is not evolutionary optimization or global optimality. Integer orders, holdings, fees, position/cash/controller/token/slot caps and funded scores come from the unchanged engine. No-op attempts exhausted by the engine's global action cap are forced idle transitions, not admitted invalid strategic orders.

## Economic verification

For a controlled suffix, expected utility is expected net cash profit (including original committed scoring rewards and remaining outcome claims) plus controller-level allocation benefit once, minus distinct effort. Original reports retain their proper-score obligation after revisions. Fees already transferred in the ledger are not subtracted twice. All common prefix rewards/cash are included in absolute totals and cancel in paired comparisons.

The independent verifier reconstructs cash changes and holdings from actual events, independently expands the categorical score expectation, and checks conserved transfers. It does not call the search objective. Every candidate selected for evidence must execute valid non-noop commands on the real engine. Selected, honest and no-action receipts have identical registry, resources, public config and schedule. A separate intervention removes external rewards and **reoptimizes**, producing three more receipts.

`VERIFIED_STRATEGIC_ALLOCATION_DEVIATION` means expected gain over both references under the declared belief and evaluator law, plus a changed allocation. It does not imply welfare harm, cash-only profitability, novelty or deception. Signed expected preference-proxy loss, realized loss and external incentive attribution are reported separately. A strategy can be an ordinary profitable trade, a beneficial redirect, subjective-only, model-unverified, or a null. Unsupported horizons are not null evidence.

## Synthetic environment and controls

`environment()` supplies arbitrary finite task/model marginals, common controller beliefs, correlated or independent exogenous belief errors, bounded aliases, capital, liquidity, fees, external incentives and action caps. Belief quality controls misspecification, not an informative signal experiment or calibrated Bayesian information acquisition. Public generator seeds can reveal the imposed marginal/error construction to a reader; misspecified beliefs are prescribed subjective strategies, not posterior-optimal agents. The calibrated selected case avoids that ambiguity.

Hidden realizations are drawn with an independent evaluator-only RNG. Generic generation uses fresh entropy unless an evaluator seed is supplied; campaigns freeze a separate audit seed. Neither this seed nor outcomes affect public source provenance or search observations. The committed audit seed is a reproducibility parameter for post-run researchers, not information supplied to actors. Mutation tests compare the entire search certificate across different hidden realizations.

Bounded Sybils are multiple pre-registered aliases sharing one controller's fixed cash, position, effort, action and token caps within a case. They can coordinate search actions. No free identities, new sponsor entitlements or unregistered mid-game aliases are assumed. Each attack/reference pair keeps the same registry and funding. Across alias-count profiles, the schedule and registration-dependent sponsor reserve can differ; those comparisons are not a normalized causal identity-splitting estimate. Full dynamic registration and repeated-game attacks remain outside this release.

The campaign covers honest, no-action, reoptimized zero-external controls; LMSR, interactive aggregation and static aggregation; liquidity/funding/belief/correlation/alias variations. Each mechanism enforces its real action capabilities. Different protocols have different feasible actions and supported horizons, explicitly recorded rather than disguised as perfectly matched treatments.

## Replay interface for Exploit Theater

Every receipt contains the existing v0.3 event stream: actual commitments/reveals, orders, prices, transfers, allocation and settlement. `attack-evidence-1` is a research sidecar, not a new shared frontend contract. Its causal sequence references actual event sequence numbers/types/payload hashes; it contains selected command plans, expected/realized payoff decompositions, allocation comparisons and observation bounds. Consumers should display expectation versus realization and credits versus synthetic cost separately. No invented frontend values or frontend source edits are included.

Historical simulator/market artifacts are immutable. `phase4_source` directories bind the enlarged package fingerprint. CI replays older receipts at their original historical sources, and current receipts at this source.
