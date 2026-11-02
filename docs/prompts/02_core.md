# COPY INTO CODEX CORE WORKER — Phase 2: deterministic simulator

Read `AGENTS.md`, `docs/SPEC.md`, `docs/CONTRACTS.md`, `docs/RESEARCH.md` and approved Phase-1 audit. Own `src/deviation/core/` and focused tests in a separate branch. The current `src/deviation/core.py` is only a toy and should be migrated carefully with backwards-compatible CLI tests.

Activation: only after the v0.2 Gate A PR has independent review, explicit owner exact-head approval and a verified human merge. Follow `docs/IMPLEMENTATION_HANDOFF.md`; work in a separate `codex/economic-core` worktree. Do not merge automatically, bypass review or run a final holdout.

Implement the approved task/agent/information/action/reservation/ledger/event interfaces. Fit reservations only on approved training groups, freeze them, and exclude fit groups from decisions. Reject reservation-budget violations, invalid units, hidden-field leakage, negative virtual credits and malformed traces. Report realized historical spend/overruns/violations after decisions separately; do not treat them as a guaranteed hard budget or hide them as failed runs. Use deterministic seeds and export v0.2 replay, preserving the legacy v0.1 CLI.

Implement random budget-feasible, cheapest, best fixed affordable and budgeted cost-aware reference policies; an offline oracle can use labels for evaluation **only**. Create a compact exact knapsack or brute-force reference on small cases to test allocations; no mandatory external solver dependency.

Write unit and property/invariant tests: budget constraint, event ordering, action permissions, replay equivalence, stable seed, paired-outcome lookup, accounting sanity and no-oracle access to live policy. Provide one hand-computable synthetic example and a trace.

**Done only when:** fresh-install CLI, all core tests, reproducible sample traces and event-contract checks pass. Open a PR; provide exact command/output, limitations and interface dependencies.
