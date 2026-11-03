# Frontend review record

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
