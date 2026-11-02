# COPY INTO CODEX RESEARCH WORKER — Phase 7: robust policy search

Read `AGENTS.md`, `docs/RESEARCH.md`, `docs/CONTRACTS.md` and verified Phase-5 evaluator. Own `src/deviation/discovery/` and search tests in isolated branch.

Implement a zero-API, deterministic optimizer for bounded, typed policy parameters: exhaustive grid for toy cases plus random/local/Optuna search for bigger cases. Objective measures budget-feasible quality/cost and held-out attack robustness; include multi-objective Pareto results and trace every candidate's parameters, seed, code hash, training objective and validation objective.

Use training scenarios and validation for optimization. Freeze a single final candidate before touching held-out test tasks and attacker regimes. Search must not generate illegal action policies or leak truth labels.

OPTIONAL: inspect current SkyDiscover integration (repo: https://github.com/skydiscover-ai/skydiscover) and add a behind-a-flag adapter only if it can run on already authorized free/local inference; no spending or mandatory AI discovery. Document if the local model is weak or tool incompatible. Do not claim algorithmic novelty from a benchmark improvement.

Deliver tests, a reproducible candidate leaderboard and trace for Mechanism Evolution, and a PR. Project must remain full-featured when SkyDiscover is unavailable.
