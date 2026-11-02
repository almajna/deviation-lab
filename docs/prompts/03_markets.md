# COPY INTO CLAUDE CODE MARKET WORKER — Phase 3: mechanisms and forecasting

Read `AGENTS.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, `docs/CONTRACTS.md`, `docs/WORKFLOW.md`. Work in your own `feat/markets` worktree and own only the `markets/` package + focused tests. Ask integrator before changing shared schema. Core interfaces must already be merged.

Build a mechanism library with: (1) scoring-rule forecast reports, (2) simple calibrated non-market aggregation, (3) finite-liquidity LMSR-style binary contracts with trade costs, (4) at least one explicit bid/payment allocation rule, and (5) a market-informed budgeted allocation policy. Clearly distinguish proper-scoring report collection from an actual trade-based market.

For every mechanism, document information set, feasible actions, utility, credit/budget limits, settlement rules, market-maker subsidy and conditions under which truthful reports might be desirable. Implement virtual-money accounting with tests for conservation/known subsidy, bounded worst-case liability if claimed, no free-profit accounting loopholes, budget feasibility and deterministic tie resolution.

The offline experiment may settle two-arm contracts from recorded paired outcomes. Explain that live selected-only outcomes cause counterfactual/decision-market problems. Simulated private signals must be marked synthetic, tunable in quality and correlation, and genuinely inaccessible to other participants.

Deliver code, mathematical definitions, exact small numerical test cases, event traces and PR. A simulation where the 'market wins' because it sees hidden labels is an automatic failure. **Do not claim market superiority or incentive compatibility merely from implementation.**
