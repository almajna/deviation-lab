# LLM Prediction Markets — visual laboratory (`apps/web`)

*An interactive laboratory for the economics of AI compute.* Public title of the DEVIATION project's frontend (the repository and codebase keep the name DEVIATION).

A static Vite + React + TypeScript replay that consumes **contract v0.2 completed traces** (`docs/CONTRACTS.md`) and tells them as an interactive film: one plain-language caption and one large diagram per scene, a compact player, and every technical detail one click away. Every number in the diagram is recorded in, or derived from, the trace's events; every element links to its source event.

> **Data status.** The app bundles only `fixtures/gate-a.synthetic.json`: the public projection of the approved v0.2 conformance pack, pinned by `fixtures/manifest.json` (7 events, 1 synthetic agent, 2 tasks). It is hand-authored `SYNTHETIC` data, labelled in the masthead on every view, and is **not** simulator output, a mechanism result or a discovered exploit. The source pack also contains a private signal and is never imported by app code. The budget (600) and task prompts are not trace fields; they come from `fixtures/gate-a.annotations.json`, a labelled copy of public receipts whose source hash is pinned. Initial balances are not public, so the ledger shows net change only.

## Views

| View | State | Driven by |
|---|---|---|
| Replay | Working | Public forecasts, reservations, settlement report, ledger transfers, utility summary |
| Exploit Theater | Honest "unavailable" | Needs approved attack/market event types (Phase 3/4); nothing is staged |
| Mechanism Evolution | Empty axes only | Needs frozen held-out evaluation and policy-search traces (Gate D / Phase 7) |

## Commands

Run from `apps/web/`. Node 22 LTS is recommended (Playwright's browser installer hangs while extracting on Node 26).

```bash
npm ci
npm run typecheck          # tsc -b
npm test                   # Vitest (44): provenance, validator, reconciliation, replay, narration, scene geometry, repo hygiene
npm run build              # static production build → dist/
npx playwright install chromium
npm run e2e                # Playwright (51 tests × desktop 1440×900 + Pixel 7). Builds first, then serves that
                           # build on 127.0.0.1:4317 (strictPort, never reuses another server)
npm run preview            # http://127.0.0.1:4173/
BASE=http://127.0.0.1:<port>/ node e2e/shots.mjs <dir>   # review screenshots from a running preview
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
src/scene/layout.ts     sceneLayout(state, 'wide' | 'tall'): pure geometry from the known state only
                        (positions, bars, arcs, labels, camera framings); unit-tested
src/scene/Scene.tsx     the diagram: tasks → models links, compute-budget bar, credit arcs; every part
                        with a source is a labelled button; meaningful motion only
src/components/Player   compact video-player bar: play, previous/next scene, scrubber, speed, Data, Inspect
src/components/Narration  caption: one headline, one plain sentence, "More detail" and "Source" on request
src/components/Inspector  modal: event JSON and provenance, account history, and the Data panel
                        (every known figure with its source event)
src/components/TraceBar  the quiet trace line: select, seed, provenance, download, load
src/views/Unavailable   Exploit Theater and Mechanism Evolution
```

- **Deterministic replay.** State at cursor *k* depends only on `events[0..k]` plus pre-run companions (task catalog, run configuration). The URL carries the cursor (`#/arena?t=3`); `t = events.length` is the closing frame.
- **Knowledge rule.** Every component, including the inspector, renders from that state alone, so nothing from a later event can reach the page: no figures, accounts, scale extents or tones. The player's scrubber shows only that later scenes exist, never their content. "Download complete trace" is the one deliberate exception: it exports the whole audit record.
- **Closing frame.** After the last event, a conclusion computed from the final state: budget fit, per-task over/under, credit conservation and utilities, with the synthetic caveat.
- **Swap-in real traces.** `Load trace file` accepts a bare v0.2 trace or a public bundle of `trace` plus optional `run_config`, `decision_tasks` and `ledger`. Any other key (for example a conformance pack's private information sets) is refused. Every companion is validated and bound to the trace: roles, fees, forecast actors, non-negative running balances, task coverage, and final balances, utilities and maker P&L reconciled against the events. Contradictory accounting is rejected, never displayed. A render failure is caught and offers a return to the bundled fixture.
- **Scale.** Accounts beyond 8 are aggregated into role cohorts (`cohortAccounts`); a 3,000-event stress trace replays in well under 250 ms (unit test). The scrubber draws one tick per scene without per-tick focus stops.

## Interaction

| Input | Action |
|---|---|
| Space | Play / pause |
| ← / → | Step one event |
| Home / End | Before first event / last event |
| I | Inspect the current event |
| Esc | Close inspector |
| Drag or click the scrubber | Seek; snaps to whole scenes |
| Any part of the diagram | Opens its source event (Enter/Space when focused) |
| Data (player) | Every known figure, each linked to its source event |
| Any figure | Opens its source event JSON |

## What the tests prove

See `docs/REVIEW.md` for each review finding, its fix and its named regression test.


- Every playback control: play to end, pause, Replay, rewind, step bounds and disabled states, speed control (measurably faster), scrubber click and drag (snaps to whole scenes), Data and Inspect, slider arrow keys, keyboard shortcuts including rapid presses, nav links, provenance, trace selector, file load (valid and invalid), JSON export (byte-for-byte equal to the bundled trace), copy JSON, inspector seek and focus return.
- Every clickable figure names its source event, and that event contains the figure; ledger deltas equal the sum of each account's transfers.
- At event 2 the DOM contains no post-settlement figure.
- The shipped HTML, JavaScript and CSS contain no private-signal keys or values, no training rows, and the page shows no balances.
- No horizontal overflow on any view at 1440 px or 412 px; reduced motion removes movement.

## Accessibility checklist

- [x] Keyboard: every control reachable; the scrubber is a `role="slider"` with arrow keys and a text value; every diagram element with a source is a labelled `role="button"`.
- [x] Narration region is `aria-live="polite"`; figures have descriptive `aria-label`s naming the source event.
- [x] Inspector is a modal dialog (`aria-modal`, labelled): focus contained, Esc and scrim close it, the page behind is `inert`, focus returns to the trigger.
- [x] Skip link becomes visible on focus and moves focus to the main content.
- [x] Phone touch targets for playback are 44 × 44 px; phone labels are at least 12 px.
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
