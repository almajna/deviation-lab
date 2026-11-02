# COPY INTO CODEX CORE WORKER — Phase 2: deterministic simulator

Read `AGENTS.md`, `docs/SPEC.md`, `docs/CONTRACTS.md`, `docs/RESEARCH.md` and approved Phase-1 audit. Own `src/deviation/core/` and focused tests in a separate branch. The current `src/deviation/core.py` is only a toy and should be migrated carefully with backwards-compatible CLI tests.

Implement typed task, option, agent, information set, action, budget, ledger, and event models. Reject invalid cost/quality units, hidden-field leakage, over-budget allocation, negative credits under prohibited policy and malformed trace logs. Make seeded simulation deterministic across reruns. Expose a CLI to run fixtures and export schema-versioned JSON event traces.

Implement random budget-feasible, cheapest, best fixed affordable and budgeted cost-aware reference policies; an offline oracle can use labels for evaluation **only**. Create a compact exact knapsack or brute-force reference on small cases to test allocations; no mandatory external solver dependency.

Write unit and property/invariant tests: budget constraint, event ordering, action permissions, replay equivalence, stable seed, paired-outcome lookup, accounting sanity and no-oracle access to live policy. Provide one hand-computable synthetic example and a trace.

**Done only when:** fresh-install CLI, all core tests, reproducible sample traces and event-contract checks pass. Open a PR; provide exact command/output, limitations and interface dependencies.
