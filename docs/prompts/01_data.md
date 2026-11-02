# COPY INTO CODEX RESEARCH WORKER — Phase 1: empirical data feasibility

Read `AGENTS.md`, `docs/DATA_AUDIT.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, `docs/CONTRACTS.md` and the assigned issue. Work on `feat/data-audit` in a separate worktree. Never edit shared contracts without an integrator-approved PR.

**Objective:** establish whether actual recorded LLM outcomes provide a valid paired, budgeted routing benchmark.

Inspect source, metadata, license/access terms and a **small sample** of LLMRouterBench and, if needed, RouterBench. Confirm overlapping task IDs across models, aligned prompts/ground truth, fields for quality and costs, quality metric consistency, cost provenance, and response fields that might leak the label. Avoid downloading huge datasets by default.

Build `src/deviation/data/` loaders, record-level validators, task/model overlap report, manifest/checksum, deterministic grouped split builder, and a mocked sample for offline CI. Define pre-decision features precisely and document which fields are allowed or forbidden. Calculate actual overlapping task counts rather than repeating publication row counts.

Run tests for duplicate IDs, missing outcomes, mismatched cost units and split contamination. Do not commit raw third-party data without permission. Update `docs/DATA_AUDIT.md` to **GO/NO-GO** with citations to source revision and documented schema. Fallback to alternate source if needed; do not quietly weaken the scientific question.

**Done only when:** at least one audited source provides matched outcomes for >=2 model arms on enough prompts for a credible test; or you explicitly report NO-GO and block empirical claims. Provide a PR, precise commands, sample table and next-step recommendation.
