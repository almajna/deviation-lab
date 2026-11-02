# Research protocol — preregistration draft

**Status: DESIGN DRAFT — freeze before the final holdout test.** Revise after dataset audit, record changes in `docs/DECISIONS.md`.

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

Use same task set, same budget and cost units, same allowed features for all deployable policies. Reference oracle may access outcomes only in analysis. Report best fixed affordable, cheapest, random budget-feasible, learned cost-aware router, non-market aggregation, market allocation, and offline oracle. If different policies spend different amounts, present the full budget/quality frontier rather than claiming 'better' at an incomparable cost.

## Synthetic signal protocol
Define noisy signals conditional on outcomes from historical paired data. Control signal calibration, quality and inter-forecaster correlation. Do not generate them by directly revealing the truth with zero noise. Forecasters may have explicit private preferences or external payoffs. Hold out new attacker budgets/types and information correlations, not just random seeds.

## Metrics
Primary: mean task quality at fixed total cost B; regret versus oracle under *same budget*; system welfare loss under attack. Secondary: budget utilization, Brier score/calibration on allowed settlement contracts, attack payoff gain net of costs, market-maker subsidy, percent of tasks rerouted, computational wall time. Define any normalization before evaluation.

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
