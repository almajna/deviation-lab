# COPY INTO CODEX — Phase 0: Lead integrator and scientific protocol owner

You are the lead integrator for DEVIATION at `https://github.com/almajna/deviation-lab`. This repository already contains an initial scaffold and canonical instructions. Read `START_HERE.md`, `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, `docs/DATA_AUDIT.md`, `docs/CONTRACTS.md`, `docs/WORKFLOW.md`, `docs/ACCEPTANCE.md`, `docs/STATUS.md`.

**Objective:** turn this starter specification into an executable, issue-driven project. Do not mistakenly label the toy example a finished mechanism, market, benchmark or research result.

1. Inspect existing files, confirm Python toy CLI and unit tests run, verify `.github/workflows/ci.yml` does not overwrite prior files.
2. Identify inconsistencies in scientific assumptions, mechanism definitions and agent information barriers. Make reversible engineering fixes; raise scientific questions for human approval.
3. Define concrete type-safe Python interfaces and versioned JSON event schemas, with fixtures and schema validation, expanding `docs/CONTRACTS.md` only after documenting compatibility.
4. Create issues M1–M9 if authenticated GitHub access is available; otherwise create a PR-ready task backlog in docs. Each issue requires owner, dependencies, touched paths, proof artifacts, gates and a prompt link.
5. Verify data-audit work can begin separately and frontend can implement against fixture traces. Prepare integration order and worktree names. Keep integration/workers as actual sessions, not imaginary background tasks.
6. Run CI and produce a precise blocker/status report. Do not change visibility, commit to main, merge, publish, spend, or use paid inference without user approval.

**Deliverable:** a feature-branch PR containing reconciled architecture/docs/CI and issue backlog, with exact tests run. **Stop for human scientific-architecture review before beginning full implementation.**
