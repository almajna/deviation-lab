# COPY INTO CLAUDE CODE FRONTEND WORKER — Phase 6: flagship visual laboratory

Read `AGENTS.md`, `docs/VISUAL_SPEC.md`, `docs/CONTRACTS.md`, `docs/ACCEPTANCE.md`, `docs/WORKFLOW.md`. Work only in `apps/web/` on your own `feat/visual-lab` worktree. Data APIs are read-only contracts; negotiate changes through integrator. No paid backend and no fake research charts.

Activation: wait for independent review, explicit owner approval and human merge of the v0.2 Gate A PR. Then use a separate `codex/visual-lab` worktree and `docs/IMPLEMENTATION_HANDOFF.md`. Prepare the public completed-replay consumer in parallel with the core. Initial v0.2 supports public forecasts/reservations and post-settlement costs/virtual ledger; unavailable market-price, exploit and evolution results must remain unavailable. No private-signal inspection without a reviewed viewer-specific extension. Do not merge or run a final evaluation.

Build a spectacular, scientifically legible static Vite + React + TypeScript lab with dark high-density editorial polish: (A) Market Arena showing economic interactions, prices and budget flows, (B) Exploit Theater showing frame-by-frame attack causality and alternate mechanism replay, and (C) Mechanism Evolution plotting held-out quality vs robustness, cost and uncertainties.

Start with versioned, conspicuously `SYNTHETIC_FIXTURE` event traces. UI must be entirely trace-driven and able to swap to genuine exported research traces with no code rewrites. Implement pause/play/step/speed, agent inspection, baseline/attacked split-screen, seed/trace selection and JSON export. Explanations must distinguish what participants knew at action time versus later outcomes.

Design quality: precise type, elegant restrained palette, cinematic but purposeful animations, accessible keyboard controls, reduced motion, responsive to phones, performance with aggregated hundreds/thousands of agents. No decorative particle animation masquerading as meaningful data.

Provide screenshot-based review, E2E interaction tests, a static production build, an accessibility checklist and a real-data-integration plan. A mockup is NOT complete; working controls and logged results required. Do not write a research result the backend has not established. Open a PR.
