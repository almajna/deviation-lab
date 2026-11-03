# DEVIATION visual laboratory (`apps/web`)

A static Vite + React + TypeScript replay laboratory that consumes **contract v0.2 completed traces** (`docs/CONTRACTS.md`). Every figure on screen is recomputed from trace events; every figure links to its source event.

> **Data status.** The app bundles only `fixtures/gate-a.synthetic.json`: the public projection of the approved v0.2 conformance pack, pinned by `fixtures/manifest.json` (7 events, 1 synthetic agent, 2 tasks). It is hand-authored `SYNTHETIC` data, labelled in the masthead on every view, and is **not** simulator output, a mechanism result or a discovered exploit. The source pack also contains a private signal and is never imported by app code. The budget (600) and task prompts are not trace fields; they come from `fixtures/gate-a.annotations.json`, a labelled copy of public receipts whose source hash is pinned. Initial balances are not public, so the ledger shows net change only.

## Views

| View | State | Driven by |
|---|---|---|
| Market Arena | Working | Public forecasts, reservations, settlement report, ledger transfers, utility summary |
| Exploit Theater | Honest "unavailable" | Needs approved attack/market event types (Phase 3/4); nothing is staged |
| Mechanism Evolution | Empty axes only | Needs frozen held-out evaluation and policy-search traces (Gate D / Phase 7) |

## Commands

Run from `apps/web/`. Node 22 LTS is recommended (Playwright's browser installer hangs while extracting on Node 26).

```bash
npm ci
npm run typecheck          # tsc -b
npm test                   # vitest: fixture provenance, validator, replay, narration (22 tests)
npm run build              # static production build → dist/
npx playwright install chromium
npm run e2e                # Playwright: 23 tests × desktop 1440×900 + Pixel 7 = 46
npm run preview            # http://127.0.0.1:4173/
node e2e/shots.mjs <dir>   # review screenshots (needs a running preview)
python3 scripts/verify_fixture.py   # from repo root: python3 apps/web/scripts/verify_fixture.py
```

## Architecture

```
src/trace/types.ts      v0.2 completed-trace, run_config and bundle types (mirror src/deviation/contracts.py)
src/trace/validate.ts   strict client validator: exact key sets, contiguous seq, visibility rules,
                        settlement ordering, report arithmetic recomputed from events, utility identity
src/trace/replay.ts     replayAt(bundle, k): a pure fold over events[0..k]; deterministic seek
src/trace/narrate.ts    plain-language narration from payloads only; never infers motives
src/data/fixtures.ts    bundled traces: public projection + labelled annotation (never the source pack)
src/components/         Stage (tasks, budget, ledger), Timeline (event-pitched lanes + transport),
                        Inspector (event JSON, visibility, provenance), Narration, TraceBar
src/views/Unavailable   Exploit Theater and Mechanism Evolution
```

- **Deterministic replay.** State at cursor *k* depends only on `events[0..k]`. The URL carries the cursor (`#/arena?t=3`), so any frame is a shareable deep link. No timers or randomness affect state.
- **Knowledge boundary.** The timeline draws a settlement line at the first `POST_SETTLEMENT` event. Before it, realized costs render as "sealed" and payoffs as placeholders; the DOM holds no post-settlement text.
- **Swap-in real traces.** `Load trace file` accepts a bare v0.2 trace or a pack (`trace` + optional `run_config` + `decision_tasks`); only those three keys are read, so other fields in a file are ignored. A budget appears only from a trusted `run_config` (cross-checked against the reported excess) or a labelled annotation.
- **Scale.** Accounts beyond 8 are aggregated into role cohorts (`cohortAccounts`); a 3,000-event stress trace replays in well under 250 ms (unit test). The timeline draws one mark per event without per-event focus stops.

## Interaction

| Input | Action |
|---|---|
| Space | Play / pause |
| ← / → | Step one event |
| Home / End | Before first event / last event |
| I | Inspect the current event |
| Esc | Close inspector |
| Drag or click the timeline | Seek; snaps to whole events |
| Any figure | Opens its source event JSON |

## What the tests prove

- Every playback control: play to end, pause, Replay, rewind, step bounds and disabled states, speed buttons (exclusive, measurably faster), timeline click and drag (snaps to whole events), slider arrow keys, keyboard shortcuts including rapid presses, nav links, provenance, trace selector, file load (valid and invalid), JSON export (byte-for-byte equal to the bundled trace), copy JSON, inspector seek and focus return.
- Every clickable figure names its source event, and that event contains the figure; ledger deltas equal the sum of each account's transfers.
- At event 2 the DOM contains no post-settlement figure.
- The shipped HTML, JavaScript and CSS contain no private-signal keys or values, no training rows, and the page shows no balances.
- No horizontal overflow on any view at 1440 px or 412 px; reduced motion removes movement.

## Accessibility checklist

- [x] Keyboard: every control reachable; timeline is a `role="slider"` with arrow keys and a text value.
- [x] Narration region is `aria-live="polite"`; figures have descriptive `aria-label`s naming the source event.
- [x] Inspector returns focus to its trigger, closes on Esc, and is `inert` while closed.
- [x] Colour never carries meaning alone: every red/green value is a signed number with a label.
- [x] Contrast: primary `#ededed` and secondary `#a1a1a1` on `#050505` exceed 4.5:1; tertiary `#7c7c7c` is used for metadata at ≥4.5:1.
- [x] `prefers-reduced-motion`: movement, blur and number tweens are removed; opacity fades remain (E2E checked).
- [x] Phone layout at 390 px with no horizontal overflow (E2E checked on all views).
- [ ] Screen-reader pass with VoiceOver/NVDA by a human (not done).

## Real-data integration plan

1. The Phase 2 core exports a v0.2 completed trace plus its trusted `run_config` and public `decision_tasks` as one pack (the shape of `tests/fixtures/contracts_v0_2.json`, minus sealed fields).
2. Add the pack under `src/data/` (or load it with `Load trace file`); no component changes are needed.
3. Recorded-outcome traces must carry a 40-hex `code_revision`; the validator rejects otherwise. The masthead then reads "Recorded outcomes" instead of "Synthetic".
4. Market prices, attacks and mechanism comparisons need reviewed, versioned event-type extensions (Phase 3/4/7). Each new type gets a validator case, a replay fold, a narration template and an E2E test before any view renders it.
5. Private-signal inspection stays out of the public replay until a viewer-specific contract extension is approved.

## Limitations

- The client validator checks what a public trace can prove on its own. It cannot authenticate provenance hashes or cross-check against the reservation artifact, allocation plan or ledger receipts, which the trace does not carry.
- The fixture has one agent, so "agents competing" cannot be shown honestly yet.
- Fonts: Geist and Geist Mono (SIL OFL 1.1, `src/fonts/OFL.txt`), self-hosted.

## CI

Root CI (`.github/workflows/ci.yml`) is integrator-owned and currently runs Python only. Proposed web job for Codex: Node 22, `npm ci`, `npm run typecheck`, `npm test`, `npm run build`, `npx playwright install --with-deps chromium`, `npm run e2e`, plus `python3 apps/web/scripts/verify_fixture.py`.

## Review

Independent review findings and fixes: `docs/REVIEW.md`. Screenshots: `docs/screenshots/` (full page) and `docs/screenshots/viewport/` (first viewport).

## Governance record

On 2026-11-02 the owner explicitly approved the merged v0.2 contract head (`a0449c9`, merged in `cb4fb58`) for Phase 6 work, and chose honest unavailable states for Exploit Theater and Mechanism Evolution. This frontend branch does not edit shared files; the integrator should record that approval in `docs/DECISIONS.md` and `docs/STATUS.md`.
