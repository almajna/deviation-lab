# DEVIATION — design system

The lab is an interactive research film: one narration line, one picture, one timeline. It refuses card grids, KPI tiles and sidebars. Colour is almost absent so that red and green mean something.

## Tokens (`src/styles.css :root`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#050505` | Ground everywhere, including the docked player and drawer |
| `--fg` | `#ededed` | Primary text, filled frames, reserved bars, playhead (16.8:1) |
| `--fg-2` | `#a1a1a1` | Secondary copy, captions (7.9:1) |
| `--fg-3` | `#7c7c7c` | Metadata, ticks, past flows (4.9:1) |
| `--rule` / `--rule-2` | `#1c1c1c` / `#2c2c2c` | Hairlines; tracks and outlines |
| `--gain` | `oklch(0.76 0.13 155)` | Favourable signed figures only: utility, unused reservations, credits received |
| `--loss` | `oklch(0.67 0.19 25)` | Unfavourable signed figures only: overruns, budget excess, credits paid, the settlement frame when the budget is violated |
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | Entrances, number tweens, playhead |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | Bars growing on screen |
| `--ease-drawer` | `cubic-bezier(0.32, 0.72, 0, 1)` | Inspector open (exit is a faster 240 ms ease-out) |

Red and green never appear without a signed number beside them.

## Type

- **Geist** (variable, self-hosted, OFL) for language; **Geist Mono** for every number, ID, event type and hash.
- Narration headline: `clamp(1.75rem, 1.15rem + 1.9vw, 2.75rem)`, weight 400, tracking −0.035em, measure 30ch, balanced. On desktop the narration block (not the headline) reserves 264 px so the stage never jumps while stepping.
- Captions: 13px in `--fg-2` with a 12px `--fg-3` note on the same line. No eyebrows, no all-caps, one weight (400) plus 500 for the wordmark.

## Composition

- **Arena (desktop):** masthead → narration (a fixed reserve keeps the picture still between frames) → Tasks → Budget (7fr) | Ledger (5fr). The player is fixed to the bottom edge; the page reserves its measured height.
- **Arena (phones, ≤860 px):** narration → the row the current event writes to → the other rows. The player is a compact fixed strip with 44 px targets and a cycling speed control.
- **Timeline:** one lane per actor on desktop, a single strip on phones; one mark per event plus a round closing frame; filled = seen, outlined = upcoming; a dashed settlement line marks the knowledge boundary; the playhead snaps to whole frames. Marks reveal that a later event exists, never its content.
- **Closing frame:** headline plus ruled findings computed from the final state; the synthetic caveat in secondary grey.
- **Tables:** separate *reserved* and *realized* columns; the change sits beside the realized figure as "+500 over" (loss red) or "100 under" (gain green).
- **Provenance:** one quiet line under the stage (trace, seed, Provenance, Download, Load). No footer.
- **Attention:** the row the current event writes to brightens its caption; other rows' graphics recede to 45% opacity (text never dims below contrast floors).
- **Unavailable views:** a large title, one honest sentence, then either the six story beats (Theater) or two empty axes (Evolution), and one waiting line. No grid, no marks.

## Motion

| Moment | Purpose | Ingredients |
|---|---|---|
| Narration line on step | State indication | 380 ms opacity + 6 px rise, `--ease-out`; skipped for keyboard steps |
| Figures changing | Elegant numerical update | rAF tween 420 ms, quartic ease-out; instant for keyboard and reduced motion |
| Reserved / realized bars | Explanation | `scaleX` 420 ms `--ease-in-out`; the over-budget segment follows 200 ms later |
| Scale widening at settlement | Explanation (the axis must grow to fit what was spent) | `left`/`width` 420 ms `--ease-in-out` on three bar segments, once |
| Keyboard steps | — | Every entrance and tween is skipped; state lands instantly |
| Ledger transfer | Spatial consistency (payer → payee) | Stroke draw 640 ms once, on the event's own frame |
| Playhead | Spatial consistency | `translateX` 260 ms `--ease-out`, interruptible transition |
| Inspector | Preventing a jarring change | 360 ms in, 240 ms out |

No looping, pulsing, particles or glow. Under `prefers-reduced-motion` all movement and tweens are removed; opacity changes remain.

## Browser surfaces

Selection inverts to `--fg` on `--bg`; focus is a 1px `--fg` outline at a 3px offset; scrollbars are thin `--rule-2`; numerals are tabular.
