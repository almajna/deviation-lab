# Scientific and system specification

## 1. Domain and terminology
- Task `i`: an input prompt/coding problem with stable ID.
- Model/arm `m`: a possible inference route; exactly one initially chosen per task.
- Recorded outcome `q[i,m]`: measured quality score **after** solving; hidden before decisions.
- Cost `c[i,m]`: dataset-provided observed or estimated resource/dollar cost, with clear unit and provenance.
- Allocation rule/policy `π`: chooses a route under aggregate budget `B` from allowed information.
- Forecaster `j`: participant with explicit noisy signal, belief and report/trades about modeled outcomes.
- Attacker: participant whose utility can differ from system welfare, within documented available actions.

## 2. Allocation objective
For approved exploratory retrospective development, maximize judged preference proxy `sum_i q[i, π(i)]`, subject to fixed training-only reservations `sum_i r[π(i)] <= B`. Freeze `r[m]` before decisions; historical realized `c[i,m]` is sealed until settlement. Report realized cost, overruns and violations separately. Reservation feasibility is not a real-world hard-budget guarantee. The proposed v0.2 contract specifies estimator, rounding, access and accounting. A general objective may weight tasks by publicly known `v_i`, but freeze values and origin per experiment. All baselines share reservations, budget and features. If no route is reservation-feasible, permit explicit abstention with zero reservation/realized cost.

Pre-decision fields: task text/features available beforehand, frozen training-only model reservations/public metadata, historical training outcomes for other task groups and explicitly synthetic private signals. Forbidden: current-task response, judged outcome, ground truth, realized cost/completion length, foreign private signals, future trades, settlement results or true uplift. Training groups are excluded from allocation in v0.2; cross-fitting/repeated-round extensions need a reviewed contract change.

## 3. Forecast contracts
Initial v0.2 forecasts target the expected judged preference proxy, not binary coding success. Future Gate B proposals may define binary `Y(i,m)=1` at a preregistered proxy threshold or an uplift event with explicit tie handling. They require a separately reviewed settlement contract and must not silently replace expected-proxy forecasts. Paired historical outcomes can support offline settlement of multiple arms; that does not imply live counterfactual observability.

A decision market creates an intervention problem when choosing routes changes which outcomes can be measured. Offline replay has stored counterfactual outcomes for matched historical rows, but this does not solve identification in deployment. A future live version would need audits/randomization or carefully defined decision-market contracts. Do not assert ordinary proper scoring remains truthful when participants can influence event outcomes.

Market-based decisions must be scored against both performance AND participation costs: virtual bankroll, information/cost assumptions, bounded trades, subsidies and transfers. Explain whether virtual credits are intrinsic utility, proxy rewards, or purely simulation currency.

## 4. Required mechanism interfaces
`Mechanism.initialize(config, public_state)`, `Mechanism.observe(agent_id, visible_history)`, `Mechanism.action(agent_id, information_set)`, `Mechanism.finalize(validated_messages, budget)->allocations`, `Mechanism.settle(outcomes)->ledger`, `Mechanism.export_trace()->events`. These are **conceptual** APIs until Phase 2 finalizes concrete Python typing; preserve semantics and schema versioning. No mechanism gets privileged access to hidden outcomes.

Core policies:
- Budget-feasible random; cheapest; best fixed affordable; cost-aware predictor; simple calibrated non-market aggregator; greedy/knapsack budgeted allocator; oracle **evaluation-only**.
- Report aggregation with proper scoring (benchmark not identical to a trading market).
- Finite-liquidity LMSR or equivalent cost-function market, with shares, trades and settlement correctly accounted for.
- Budget/bid mechanism with explicit strategy rules and payments; no unsubstantiated auction truthfulness claim.

## 5. Agent types and incentive modeling
- Honest signal reporter: maximizes expected scoring reward (under fixed event assumptions).
- Directional attacker: receives external benefit from assigning budget to a favored arm, minus trade/payment cost.
- Coalition: shares reports and potentially coordinates trades; accounts remain separate unless scenario allows pooled funding.
- Sybil: controls multiple identities only if mechanism's identity policy permits it; total capital/credit constraint must be clear.
- Sandbagging actor: in repeated games can influence reputation using available actions, not retroactively edit logged real-model outcomes.

Private-signal synthesis should produce calibrated noisy estimates with tunable accuracy and cross-agent correlation, seeded and fully documented. Ensure train/validation/test regimes include different correlation and attacker distributions. Do not advertise such signals as actual LLM forecasts.

## 6. Adversarial search
Objective = attacker utility difference relative to a fixed declared baseline, with corresponding system welfare and transaction costs. Enumerate small finite action spaces to certify a maximum or counterexample *within that space*. Heuristic search reports best found not provably optimal. Retain all attack parameters, information, costs, seeds, and event logs. Do not create 'exploits' by violating contract constraints or giving agents impossible knowledge.

## 7. User interface contract
Three views: arena, forensic replay, mechanism comparison. All visible numbers derived from versioned events/metrics; synthetic traces prominently labeled. Each named attack has a durable replay ID, config, seed, cost provenance, experiment build hash, and linkable source. Allow stepping, pausing, inspecting information available to an agent at that time, and baseline comparison. Reduced motion and mobile support required.

## 8. Claims guardrails
No '100 autonomous LLMs competed' unless actual LLMs performed those agent actions in a separately documented experiment. No 'new market mechanism discovered' without novelty survey and held-out validation. No 'compute dollars saved' without aligned price/cost data and explicit simulation assumptions. No 'strategy proof' beyond a proven formal model and action space. Dataset quality is not agent competence.
