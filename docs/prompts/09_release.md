# COPY INTO CODEX INTEGRATOR — Phase 9: flagship release qualification

Read canonical docs, `docs/RELEASE_CHECKLIST.md`, `docs/ACCEPTANCE.md`, latest independent scientific audit and all PRs. Work on release branch, not main.

Run clean-install reproducibility: Python tests, core/market/attacks/evaluation/discovery benchmarks, exact attack replay, frontend tests, accessible static production build, data-provenance validation and scans for secrets or third-party redistribution errors. Reconcile all metrics and screenshots to actual event logs.

Prepare polished public README with 45-second pitch, honest limitations, architecture, one-command repro, mechanism descriptions, documented results and direct links to visible replay cases. Create clear `docs/REPORT.md` outlining research questions, methods, baselines, statistical uncertainty, adversarial findings, negative outcomes, and future work. Provide concise demo script and optional screen recording instructions.

Score each rubric row based on independently checkable evidence links; do not gift points. Ensure critical blockers closed and final human approval requested before release or visibility/hosting changes. If below threshold or scientific audit fails, return a precise prioritized fix backlog, not a dishonest release announcement.

Deliver a PR and GO/NO-GO memo. Do not publish, merge final release, spend money or change visibility without explicit authorization.
