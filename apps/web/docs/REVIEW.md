# Frontend review record

## Codex independent review of `140e6f6` (PR #17): BLOCK — resolution

Every finding below has a named regression test. "U" = Vitest (`src/trace/trace.test.ts`), "E" = Playwright (`e2e/lab.spec.ts`, run on desktop 1440×900 and Pixel 7).

### Engineering

| # | Finding | Root cause | Fix | Regression test |
|---|---|---|---|---|
| R1 | `src/lib/hooks.ts` missing from Git; a clean clone does not build. | The repository root `.gitignore` (Python template) ignores every `lib/` directory. All earlier checks ran in the working directory, where the file existed. | `apps/web/.gitignore` re-includes `!src/lib/` and `!src/lib/**` (root file untouched). Verified by building and testing a fresh `git clone` of the pushed commit. | U `R1 repository hygiene`: fails if any file under `src`, `e2e` or `fixtures` is git-ignored (confirmed to fail with the old rule). Fresh-clone log in the PR. |
| R2 | Inspector leaked future information: at event 2 it listed later transfers, cash and utility. | Inspector read `bundle.trace.events` instead of the replay state. A wider audit found more: realized bar widths, the budget axis sized to the final cost, the settlement frame's loss tone and the pre-reveal utility row all derived from the final state. | One rule: every component renders from `replayAt(bundle, cursor)`, a fold over `events[0..cursor]` plus pre-run companions. `final` state removed. Inspector filters transfers/utility to the cursor and refuses events beyond it. The scale is sized from known values and widens at settlement. Accounts appear only when a transfer names them. | U `R2: state at k depends on events[0..k] only` (truncated-trace equality at every k). E `R2 knowledge boundary`: at each of 7 positions, page, timeline and every reachable inspector contain no identifier or multi-digit figure first introduced later; targeted test at event 5; no account/transfer/loss tone before settlement. Mutation-checked: reintroducing the old inspector code fails 2 tests. |
| R3 | Imported traces could display contradictory accounting. | Validator checked report arithmetic and utility identity, but not summary multiplicity, settlement actors, event ordering after the summary, roles, balances or receipts. | `validateTrace` now requires exactly one final `utility_summary`, rejects any event after it, requires `system` for settlement events, bars forecasts and transfers from reserved roles, requires utility receipts for fee payers and for any account that moves credits unless it is the fee sink or maker, and rejects zero-cost selections. `validateRunConfig` binds accounts, roles, fees, forecast actors and non-negative running balances. New `validateLedger` reconciles initial/final balances, transfers, utilities and maker P&L/loss. | U `R3 accounting reconciliation` (8 tests) and `R3/R4 companion validation` (6 tests). E `R3/R4 imports`: contradictory final balance, missing/duplicate summary, invalid settlement actor, post-summary transfer each rejected; a fully reconciled bundle shows balances 24/2/44. |
| R4 | Malformed companion metadata could blank the application. | `decision_tasks` were cast, not validated; no error boundary. | `validateTasks` (exact shape, unique ids, ≥2 options, forecast/reservation coverage); files with keys beyond `trace`, `run_config`, `decision_tasks`, `ledger` are refused (e.g. a pack with private information sets). A `Recoverable` error boundary keeps the app usable with "Return to the bundled fixture". | E `R3/R4 imports`: malformed `run_config`, malformed `decision_tasks`, ledger without config and private fields each show an alert, and the app still steps the bundled fixture. |
| R5 | Inspector was not an accessible modal; skip link invisible. | Drawer was an `aside`; skip link used `.sr-only` with no focus style. | `role="dialog"`, `aria-modal`, `aria-labelledby`; Tab/Shift+Tab contained; Escape and scrim close; page regions marked `data-page` become `inert` while open; focus returns synchronously to the trigger. Skip link slides into view on focus and targets a focusable `main`. | E `R5 accessibility`: modal semantics, 12 Tab/Shift+Tab presses stay inside, background inert, Escape restores focus; scrim closes; skip link visible on focus and moves focus to content. |
| R6 | Playwright could reuse another running application. | `reuseExistingServer: true` on a common port. | `webServer` runs `npm run build && vite preview --port 4317 --strictPort`, `reuseExistingServer: false`, `forbidOnly`. | E `R6`: the served HTML references the bundle produced in `dist/` for this run. |
| R7 | Reduced motion left transport-button transitions. | Per-selector exceptions missed `.tbtn`. | A global reduced-motion rule restricts every transition to opacity/colour, removes press scaling, bar growth, flow drawing and drawer movement. | E `R7`: computed `transition-property` on transport, playhead, bars, frames, drawer and tracks contains no transform/left/width; pressed button has no transform; bars have no animation. |

### Visual (target 9.5/10; previous independent rating 7.4)

| Ask | Change | Test |
|---|---|---|
| Keep narration, diagram and controls together on phones | Player docks to the bottom edge at every width. On phones the stage reorders so the row the current event writes to follows the narration directly. | E `mobile: narration, the current diagram and the player share the first screen` (events 1, 4 and 6). |
| Reduce the timeline's height | Phones and short screens use a single strip (no actor lanes), with a cycling speed control. | E `player is compact…` (≤ 130 px). |
| Evidence visible without scrolling | As above, plus a two-line maximum for desktop explanations. | Same test; screenshots in `docs/screenshots/viewport/`. |
| Label readability and touch targets | Phone labels ≥ 12 px; transport targets 44 × 44 px; figure buttons ≥ 32 px tall; inspector close 44 px. | E `player is compact and touch targets are at least 44px`, `labels are readable`. |
| Reservation vs change | Separate **reserved** and **realized** columns; the signed change sits beside the realized figure; accessible name states "700, 500 over the reservation". | E `reserved and realized are separate columns`. |
| Evidence-derived conclusion | A closing frame after the last event: headline and four findings computed from the final state (budget fit, per-task over/under, credit conservation, utility), plus the synthetic caveat. | E `closing frame states only what the events establish`. |
| Shorter unavailable views | One sentence, six beats (Theater) or empty axes (Evolution), one waiting line. Chapter tables, "Needs/Ready" mono and the empty comparison shell removed. | E `unavailable views are short and draw no data` (< 90 words, no marks). |

Also fixed during this round: ledger transfer arrows disappeared when the accounts mounted after settlement (width observer attached before the element existed) — now a callback ref, with test `ledger draws one arrow per known transfer`.

### Independent design review of this round

A fresh reviewer (no build context) scored the recaptured screenshots **8.3/10** and listed eight findings: indistinguishable rewind/step icons, dead space under one-line headlines, ambiguous table deltas, dock clipping evidence, empty-ledger gap, illegible ledger arcs, technical clutter (trace bar, footer) and Evolution's boxed grid. All were fixed. The verdict pass rated it **8.9/10**: six resolved, two partial. The two partials were then fixed and regression-tested: the arc label touching another arc (test `ledger arc labels do not touch another arc`, which fails with the old geometry) and a visible "Trace" label caused by a dropped `.sr-only` rule (test `visually hidden labels stay hidden`). The reviewer noted that 9.5 would need denser desktop frames on one-line beats and a stronger visual moment at settlement; both remain open design opportunities, not defects.

Totals for this commit: 37 Vitest unit tests; 104 Playwright tests listed (desktop + Pixel 7; phone-only tests skip on desktop).

## Earlier rounds (before PR #17 review)

## Independent finish review (round 1)

A fresh reviewer agent, given only the owner's brief, the direction contract, the source and 14 screenshots (no build conversation), returned **fix**: direction and honesty sound, composition and legibility not yet. All ten material findings were accepted.

| # | Finding | Fix | Verified by |
|---|---|---|---|
| 1 | Each frame's evidence sat below the fold (e.g. "+300 over" headline, red bar off-screen at 1440×900). | Recomposed: narration → Tasks → Budget (7fr) beside Ledger (5fr); timeline docked to the bottom edge on desktop. Headline and evidence share one viewport. | `docs/screenshots/viewport/desktop-arena-t{1,3,6}.png` |
| 2 | Three different "overrun" numbers with no stated comparison. | Every figure now names its baseline: "vs reserved +400 (overruns +500 · unused −100)", "vs budget +300"; the red segment reads "+300 over budget"; narration says "against its own reservations… against the budget…". | Unit test `states the overrun honestly…`; screenshot t3 |
| 3 | Pre-reveal utility row blurred and illegible with a lone "?". | Explicit sealed state at normal contrast: "agent-1 utility · revealed at event 6". Blur removed everywhere. | E2E `nothing post-settlement is rendered before settlement` |
| 4 | Ledger arcs carried no amount or direction. | Every drawn transfer has an arrowhead and its amount; the live transfer draws once in white. | Screenshot t6 |
| 5 | Evolution plot text scaled to ~4px on phones. | Plot text moved to HTML over a non-scaling SVG grid. | `mobile-evolution.png` |
| 6 | Evolution y-axis label rendered off-canvas. | HTML label "↑ held-out quality, budget-adjusted" inside the frame. | `desktop-evolution.png` |
| 7 | Phone masthead dropped "not a result". | Full label "Synthetic fixture · not a result" on every width. | `mobile-*.png` |
| 8 | Inspector ledger lines ambiguous (−2 beside fee_sink); "eff/ort" broke mid-word. | "−2 → fee_sink action fee", "+6 ← maker settlement"; only hashes may break anywhere. | E2E `inspect why an agent received credits` |
| 9 | Mobile nav clipped "Mechanism Evolutio"; lane label truncated. | Short tab labels (Arena / Theater / Evolution) under 860px; lane labels widened to 100px. | `mobile-*.png`, E2E nav test |
| 10 | 0–1 forecast bars under "forecast" invited a probability reading. | Caption "forecasts are expected judged-preference reward"; column "reward". | Unit test `never calls a forecast a probability` |

Minor items also addressed: axis now ends on a labelled tick (1,000); Play/Replay button has a fixed width; the hanging bullet markers were replaced by caption emphasis; Theater "Needs" text raised to secondary contrast.

## Issues found after the review (self-verification before PR)

| Issue | Severity | Fix |
|---|---|---|
| The app imported the whole conformance pack. Production tree-shaking dropped the private fields, but `npm run dev` served agent-1's private signal. | High | Bundle only `fixtures/gate-a.synthetic.json` (public projection pinned by `fixtures/manifest.json`). E2E fetches every shipped script/stylesheet and asserts no private keys or signal values. |
| Budget (600) and initial balances were shown from the pack's `run_config`, but they are not public trace fields. | Medium | Budget comes from a labelled `fixtures/gate-a.annotations.json` (public receipts only, source hash pinned, captioned "budget from fixture annotation, not the trace"). Ledger shows net change only. |
| "+300 over budget" text existed in the DOM (opacity 0) before settlement. | Medium | Rendered only after settlement; E2E asserts no post-settlement figure in the DOM at event 2. |
| The over-budget label intercepted clicks on the "900" figure. | Medium | Label moved inside the red segment, `pointer-events: none`. |
| Phone nav links had no accessible name (full label hidden, short label `aria-hidden`). | Medium | Short label exposed; the hidden one leaves the accessibility tree. |
| On phones the timeline moved as narration length changed (controls unstable during playback). | Medium | Timeline placed above the narration on phones; E2E asserts its position is unchanged after seeking. |
| Keys pressed immediately after Esc were dropped (stale listener; focus left on the hidden drawer). | Medium | Single keyboard listener reading a ref; focus restored synchronously on close. E2E `rapid key presses are never dropped`, suite repeated 5× (230/230). |

## Open design notes for the reviewer

- **Palette conflict.** `apps/web/CLAUDE_HANDOFF.md` proposes cyan/teal and amber, reserving red for attacks. The owner's later visual direction specifies a monochrome interface with green for gains and red for losses. This PR follows the owner. Red here marks realized overruns and credits paid, never an attack.
- **Naming.** The view is titled "Market Arena" per the owner; the trace bar states "Market prices and trades: unavailable". "Mechanism Evolution" is kept per the owner; `docs/VISUAL_SPEC.md` suggests "Policy Search" if SkyDiscover is not used.
- **v0.3.** Main now contains a v0.3 categorical market engine and replay artifact (PR #14). This UI consumes v0.2 only; v0.3 market-event support is the next frontend task, after its event types are confirmed for public replay.
