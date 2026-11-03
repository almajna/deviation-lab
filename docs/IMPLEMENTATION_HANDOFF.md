# After Gate A approval and human merge

Activation receipt: the owner explicitly approved `a0449c9add2ee3aeb1741d48d41e725d5e8db261`; PR #6 is merged on synchronized main `cb4fb585171f4dde371e4dfa4319d21e9ca70bc1`, with approved-head and merged-main CI passing. Phase 2 is now active and the Phase 6 handoff is prepared. The instructions below describe the activation prerequisites; they are satisfied for this exact approval. Complete `GATE_A.md` first: independent review, explicit owner approval of current contract head, green CI, human merge verified on synchronized main. Do not create/dispatch implementation worktrees before the gate. Agents never merge or bypass review.

## Phase 2 — deterministic economic core

Create a separate `codex/economic-core` worktree from approved main. Owner: core worker. Paths: `src/deviation/simulator/` (preserves legacy `core.py`), focused core tests and synthetic core fixtures; shared `contracts.py`/schemas are read-only without integrator review.

Implement the approved interfaces, not new market mechanics: trusted data/split registry, train-only fixed-reservation fit/freeze service, isolated policy information projections, seeded event runner, explicit abstention and reservation counter, sealed settlement access, realized-cost diagnostics and conserved virtual-credit accounting. Keep synthetic private signals and modeled utilities visibly synthetic. Implement random/cheapest/best-fixed/cost-aware reference policies under the same reservations; offline oracle is evaluation-only. Preserve the v0.1 demo/CLI regression while adding a separate v0.2 execution path.

Evidence: hand-computable synthetic scenario matching v0.2 fixture; exact replay/hash equality; mutation-invariance tests changing hidden costs/quality without changing decisions/reservations/history; normalized-group training exclusion; exact budget boundary; realized overrun reporting; ledger conservation and no duplicate fee charge; private-signal/action permissions. No final holdout run, paid inference or superiority claim. Open a separate review PR; human merge only.

## Phase 6 preparation — parallel fixture consumer

After the same gate, create a separate `codex/visual-lab` worktree. Owner: frontend worker. Paths: `apps/web/` and frontend tests only. The approved v0.2 contract/index and synthetic fixture are read-only inputs; negotiate extensions through the integrator.

Prepare a static Vite/React/TypeScript replay consumer and fixture adapter. Start with clearly synthetic provenance, public forecast/reservation events and post-settlement cost/ledger receipts. Show reserved versus realized costs/overruns separately from virtual credits. Support play/pause/step, stable seeking, seed/scenario identity, keyboard/reduced-motion/responsive behavior and JSON inspection. The full completed replay is not an agent decision packet. Do not expose sealed/private live fields or label expected preference as coding success.

Initial screen/build work must show unavailable market-price, attack-causality and evolution results as unavailable, not fabricated charts. Later integration depends on verified core traces and separately approved Phase 3/4 event extensions. Private-signal inspection requires a viewer-specific contract extension; initial public replay does not export it. No visual backend/real-data publication is authorized merely by fixture UI work.

Evidence: production build, trace-driven controls, schema fixture checks, screenshots/accessibility/interaction tests and core integration plan. No shared-file edits, invented findings, paid services or automatic merges. Open a separate frontend PR.

## Integrator responsibilities

Pin approved contract/source fixture hashes in both task briefs, keep workers in distinct worktrees, and verify CI/review per exact head. Integrate one human-approved PR at a time; update dependent branches after main changes. Shared-contract extensions require versioned fixtures, independent review and owner approval. Keep the entire 247-task pool exploratory. Final protocol, fresh untouched holdout, one-run authorization, mechanism settlement math and release remain future gates.

Current task briefs: `docs/tasks/PHASE_2.md` (issue #7) and `apps/web/CLAUDE_HANDOFF.md` on `codex/visual-lab` (issue #8). Preparation does not claim an active Claude Code session. Shared contracts remain unchanged.
