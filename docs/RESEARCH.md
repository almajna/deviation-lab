# Research protocol — preregistration draft

**Status: DESIGN DRAFT — freeze before the final holdout test.** Revise after dataset audit, record changes in `docs/DECISIONS.md`.

## Owner-approved development scope — 2026-11-02

The owner accepted Phase 1 and approved these assumptions for development. The shared contracts still require their own exact-head approval and merge; no final holdout run or scientific superiority claim is authorized.

1. **Quality:** ArenaHard win/tie/loss is a noisy judged preference proxy, not objective coding correctness. Retain the ambiguity between losses and historical judging failures. Forecasts target expected proxy reward, not correctness probability.
2. **Cost:** Use reported historical model costs retrospectively. They are not verified bills, measured deployment savings, or actual future costs.
3. **Budget:** Fit fixed per-model reservations from training data only, before decisions. Initial contract choice: upward-rounded arithmetic mean, integer nanos, no held-out fallback. Exclude training prompt groups from allocation rather than unspecified cross-fitting. Report realized historical cost, positive per-task overruns, net overruns and budget violations separately; promise no real-world hard budget.
4. **Scope:** The 247-task cohort supports exploratory engineering/methodology only. Its 172/31/44 split is exploratory; the 44 `test` tasks are not an untouched final holdout. No broad conclusion may rest solely on this pool.
5. **Agents:** Forecasters, signals and adversaries are synthetic. Historical real-model task outputs are not observed agent behavior. Hidden outcomes, realized costs and foreign private signals are inaccessible in decision packets.

Historical Phase 1 NO-GO artifacts remain the original audit record. The owner has accepted their documented limitations for limited development, conditional on the shared-contract gate. This does not turn that audit into broad empirical GO.

## Sensitivity and final-evaluation plan (not executed)

- Compare the declared 1/0.5/0 proxy with alternative tie treatment and explicit pessimistic/optimistic bounds for uncertain zero scores. These do not recover missing judge status; report ambiguity and source/domain concentration.
- Compare training-only mean reservations with preregistered training-only median/quantile or safety-multiplier alternatives. Fit variants on training data, select on validation before final freeze. Report reservation utilization and realized cost/overrun distributions, including violations rather than suppressing them.
- Report complete-case selection and small-sample concentration. Assess semantic near-duplicates and source-family separation before final evaluation. Use paired task/group uncertainty; no superiority claim from this engineering pool.
- After protocol, claims, metrics, attacker regimes and code are finalized, obtain a separately sealed untouched evaluation cohort with provenance/group/split hashes and a designated outcome custodian. Do not relabel inspected pilot rows as untouched. Freeze protocol/config/code before access. Require explicit human authorization for one final evaluation; post-freeze changes need review and exploratory labeling or a new holdout.
- This PR contains synthetic conformance checks only: no real-data reservation fit, mechanism comparison or final evaluation.

## Questions
RQ1. Under budget constraints, can market-aggregated forecasts allocate historical LLM inference choices better than calibrated non-market aggregation and ordinary routing baselines?
RQ2. How does allocation welfare degrade when a subset of forecasters can strategically misreport or trade?
RQ3. Which mechanism design variables (liquidity, credit limits, randomized audits, reputation rules) improve robustness, and at what cost?
RQ4. Can bounded policy optimization improve held-out robustness without overfitting known attacks?

## Falsifiable hypotheses (do not pre-commit to success)
- H1: When forecasters possess complementary noisy information and have aligned incentives, market aggregation could improve decision quality relative to a fixed budgeted baseline.
- H2: Under correlated signals, simple calibrated averaging could match or beat market signals, particularly with transaction and subsidy cost accounted for.
- H3: Externally rewarded attackers can divert allocations in mechanisms that equate price with impartial information without accounting for strategic incentives.

## Data source audit
Candidate: https://github.com/ynulihao/LLMRouterBench ; fallback: https://huggingface.co/datasets/withmartian/routerbench . Verify current license, downloadable files, paired outcome overlap, costs, data types, and feasible local sample. Do not claim 400K complete per-task matrices until validated. The RouterBench dataset card describes >30K prompts, 11 LLMs and measured/estimated outcomes; 0-shot downloadable artifact is still relatively large. See `docs/DATA_AUDIT.md`.

## Offline protocol
Split at task ID (and shared near-duplicates if possible) before training; consider source benchmark or topical family holdouts. Prevent future outcome leakage from target task into forecaster signals or learned routers. Fit calibration and routing on training and select hyperparameters on validation only. Freeze a test manifest/hash and evaluate exactly once for headline results. If more experiments are needed after looking at test scores, declare them exploratory or create a fresh holdout.

Use the same task set, frozen training-only reservation artifact, simulated reservation budget, units and allowed features for all retrospective policies. Deployability is not established. Reference oracle may access outcomes only in separately labeled analysis. Report best fixed affordable, cheapest, random reservation-feasible, cost-aware routing, non-market aggregation, market allocation and offline oracle when implemented. Keep reservation/quality and realized-cost/quality frontiers separate rather than claiming an incomparable cost advantage.

## Synthetic signal protocol
Define noisy signals conditional on outcomes from historical paired data. Control signal calibration, quality and inter-forecaster correlation. Do not generate them by directly revealing the truth with zero noise. Forecasters may have explicit private preferences or external payoffs. Hold out new attacker budgets/types and information correlations, not just random seeds.

## Metrics
Primary: mean judged preference proxy at fixed reservation budget; regret versus a labeled offline oracle under the same reservation rule; welfare-proxy loss under attack. Separately report reservation spend, realized historical spend, positive per-task overruns, unused reservations, signed net overrun, realized budget excess and violation frequency. Secondary: expected-proxy forecast calibration, virtual-credit payoff gain with costs accounted once, initial maker subsidy, maker cash profit/loss, rerouting and runtime. Binary Brier scoring needs a separate event/threshold contract; expected preference is not correctness probability. Never mix historical-cost and virtual-credit units. Define normalizations before freezing.

## Statistical strategy
Paired comparisons on same tasks; cluster bootstrap by task (or by source/problem family when independence requires it); confidence intervals; multiple independent seeds for stochastic signals/strategies. Report absolute effect sizes and interval widths even for insignificant outcomes. Avoid treating thousands of correlated simulated trades as thousands of independent real observations.

## Manipulation validity
A finding is valid only if attacker actions are within stated protocol, net utility improves versus baseline, and replay deterministically reproduces. A small exhaustive finite search provides a bounded optimality claim; heuristic search only a found example. Use no-exploit controls to detect accounting and search bugs.

## Algorithm discovery
Optimization objective is a weighted or Pareto combination of quality, cost and worst-found attack welfare. Use training/validation only for discovery. Once selected, evaluate held-out attacks/tasks without revision. Optional SkyDiscover depends on a separately approved inference setup; deterministic parameter search is the default.

## Failure/null outcomes to publish
Market loses to aggregation; attack only works with unrealistic external incentives; exact search finds no exploit under a bounded rule; confidence intervals span zero; optimized rule overfits. All are valid scientific outcomes if protocol is honest.

## Research note template
For every reported result, publish: hypothesis, source data hash, split manifest, exact run command, mechanism and attacker code hash, observed effect and uncertainty, limitation, and the JSONL event trace where applicable.
