# Claude Code — Phase 6 visual laboratory

Issue: [#8](https://github.com/almajna/deviation-lab/issues/8). Owner: Claude Code frontend worker. Use the existing isolated `codex/visual-lab` branch/worktree. This preparation is not a completed app or evidence of an active Claude Code session.

## Authorization and ownership

The owner explicitly approved scientific v0.2 commit `a0449c9add2ee3aeb1741d48d41e725d5e8db261` for limited engineering. PR #6 is merged on starting main `cb4fb585171f4dde371e4dfa4319d21e9ca70bc1`; approved-head CI `41549422392` and merged-main CI `41549521955` passed. Gate A is satisfied. Codex implements Phase 2 separately on `codex/economic-core` (#7).

Read AGENTS.md and its prescribed reading order, then docs/IMPLEMENTATION_HANDOFF.md, docs/prompts/06_visual.md and docs/VISUAL_SPEC.md. Proposed/pending wording in those base documents describes the historical proposal; this explicit approval activates that exact revision. The branch here supersedes the prompt's older feat/visual-lab example.

Own only **apps/web/ and frontend tests within it**. Approved Python contracts, schemas, core, root CI, Phase 1 evidence, README and license are read-only. Propose interface changes to the integrator. Do not merge the unapproved core branch here; consume reviewed generated core traces after human merge. No backend, secrets, paid API, publication, final holdout experiment or invented findings. Agents never merge, enable auto-merge/queues, bypass review or change GitHub settings. Spend $0.

## Pinned inputs and ready-to-use public fixture

| Input | SHA-256 |
|---|---|
| src/deviation/contracts.py | dcd175fd35452cff07380eaca85dd7cbc5b6257709892d50356175e551bbe000 |
| schemas/contracts-v0.2.json | 15424b8232b455fd903dfffbbdac81ca3d189c1e766f2d728eb799df9fafcf06 |
| tests/fixtures/contracts_v0_2.json | 8aae9c65a592f1e3d0c80ca27accf78eefad5efd8f04705310dc50111ab03a5e |

fixtures/gate-a.synthetic.json is a reproducible extraction of **only .trace** from the approved conformance pack; fixtures/manifest.json pins its bytes and provenance. This is hand-authored SYNTHETIC conformance data, not simulator output, an empirical observation or discovered exploit. Do not bundle the source pack: it also contains private signal fields. The public extraction excludes them.

Use a typed fixture adapter, runtime shape checks and a pure event reducer. The component index is **not JSON Schema**; shared Python validators remain normative. Do not edit values for a better story. Before work and final review, run from repository root:

```bash
python3 apps/web/scripts/verify_fixture.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

No frontend dependencies are needed for these preparation checks. When implementing, add a local package manifest/lockfile and explicit build/test commands under apps/web. Avoid root dependency changes and stacked animation frameworks.

## Cinematic research instrument

Build static Vite + React + TypeScript. Compose a deliberate opening: DEVIATION identity, persistent **SYNTHETIC CONFORMANCE FIXTURE** badge, experiment/seed, central decision timeline and resource-flow stage. Dark ink, precise typography, thin grid, restrained cyan/teal for public forecasts/reservations and amber for uncertainty/realized overrun. Reserve red attack encoding for a later verified attack trace. No meaningless particles, random floating nodes or decorative motion masquerading as data.

The supported story is **reservation-feasible allocation followed by realized-cost overrun**. Reveal only public forecasts and reservations before settlement; then reveal realized costs, transfers and utility. Motion connects the exact event to changed state, with instant deterministic seeking and reduced motion. Expected judged preference is never coding-success probability.

Provide three destinations:

1. **Allocation Replay / Arena:** working supported-event stage, public forecasts, task/model selections, reservation versus realized cost, transfers/utility and provenance drawer. If called Market Arena, mark market-price/trade mechanics unavailable.
2. **Exploit Theater:** honest unavailable state until a reviewed attack trace exists. No invented attack, causal chain or honest-versus-attacked comparison. A reusable empty comparison shell is allowed.
3. **Policy Search / Evolution:** unavailable until verified search/evaluation artifacts exist. No fabricated scatterplot, leaderboard, confidence interval or superiority caption.

## Working interactions

- Play/pause, previous/next event, seek slider, speed and reset. One integer cursor and deterministic reducer; no render-time randomness.
- Trace/seed identity selector. Begin with one real fixture; do not fabricate another trace or imply a seed selector recomputes a simulation. Treat imported JSON as data, never executable code.
- Event selection shows exact JSON, actor, visibility and provenance. Agent drawer shows public forecasts, transfers and cash delta. Private signals and private action-time inspection are unavailable in this public ABI.
- JSON export preserves the exact loaded trace. Never insert display annotations into shared events.
- Keyboard operation, visible focus, screen-reader event descriptions, contrast, responsive phone layout and reduced-motion support. Controls stay stable during playback.
- No budget slider without a real approved recomputation. Static replay controls cannot change recorded decisions/outcomes.

## Facts the fixture actually supports

Seven events: exogenous seed-history forecast; eval-1/a reservation 200 and eval-2/b reservation 300; realized report; two transfers; utility summary. Unit is **nano_synthetic_units**, separate from USD and virtual_credit. Reserved 500, realized 900, positive task overruns 500, unused reservations 100, signed net overrun 400, realized budget excess 300. The matching approved allocation receipt has budget 600, but **budget is not a field in the public trace**. If displaying 600, extract and label a separate fixture annotation; do not extend the shared replay.

Fee transfer 2 and illustrative maker payout 6 yield cash delta 4, external benefit 3, noncash effort 1 and utility 6. Initial balances are not in this public trace: do not infer absolute balances from deltas. A generated core trace can differ in action count/fees while conforming to the same ABI.

No recorded-model quality results are in this public fixture. No correctness, savings, price, attack or final-holdout charts. The 247-task cohort is exploratory and is not bundled. Cost reservation feasibility is not a real-world hard-budget guarantee. Economic agents are synthetic; historical outputs are not observed autonomous-agent behavior.

## Delivery

Implement on this branch and open a separate frontend implementation PR linked to #8. The preparation PR is not a working app. Provide production build; reducer/contract tests; browser tests for play/seek/reset/export and unavailable views; desktop/mobile screenshots; reduced-motion and accessibility checks; and a verified-core-trace integration plan. Screenshots alone do not prove controls work. Coordinate root CI changes with the integrator. Request an independent reviewer; a human merges. No deployment, paid services or final evaluation.
