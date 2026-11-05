# LLM Prediction Markets — design system

An interactive research film: **one concept per scene**. A plain-language caption, one large diagram that persists and transforms from scene to scene, and a compact player. Depth (exact values, source events, accounting) is one click away, never in the default view. Clarity and pacing in the spirit of 3Blue1Brown; restraint in the spirit of Vercel. No 3Blue1Brown palette or artwork.

## Tokens (`src/styles.css :root`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#050505` | Ground everywhere, including the player and dialogs |
| `--fg` | `#ededed` | Primary text, selected links, reserved compute, nodes in use (16.8:1) |
| `--fg-2` | `#a1a1a1` | Secondary copy, labels (7.9:1) |
| `--fg-3` | `#7c7c7c` | Metadata, candidate links, hints (4.9:1) |
| `--rule` / `--rule-2` | `#1c1c1c` / `#2c2c2c` | Hairlines, unselected links, the empty budget track |
| `--gain` | `oklch(0.76 0.13 155)` | Favourable signed figures only (credits received, cost under reservation, positive utility) |
| `--loss` | `oklch(0.67 0.19 25)` | Unfavourable signed figures only (overrun, over budget, credits paid) |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | Movement on screen: blocks, camera, tokens |
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | Entrances, scrubber |
| `--ease-drawer` | `cubic-bezier(0.32, 0.72, 0, 1)` | Inspector open |

Red and green never appear without a signed number or the words "over/under" beside them.

## Type

Geist for language, Geist Mono for identifiers and diagram figures. Inline numbers in prose use Geist's tabular figures (Mono's full-width decimal point reads as "0 . 60"). Title card: up to 4.25rem, tracking −0.045em. Scene headline: up to 2.6rem, weight 400, balanced. One plain sentence under it at 16px in `--fg-2`. No eyebrows, no all-caps.

## Composition

- **Desktop (≥1100 px):** caption column (4fr) beside the diagram (8fr), vertically centred; player fixed to the bottom edge; a quiet trace line below.
- **700–1099 px:** caption above, diagram full width.
- **Phones (<700 px):** caption, then the portrait diagram, then the fixed player. Works to 320 px (tested).
- **Diagram:** tasks (squares, left) link to candidate models (circles, right). Candidate links are dotted; once forecast they turn solid grey with the value on the link; the selected link draws in white. Below, the compute-budget bar with the budget line. Under it, credits: accounts with signed net change, arcs for transfers, utility.
- **Camera:** the SVG `viewBox` frames the part the scene is about: compute before credits exist; credits after. A 28 px top fade dissolves anything at the frame edge instead of cutting it.
- **Disclosure:** caption → "More detail" (technical caveat) → "Source: event N" (inspector) → **Data** (every known figure with its source event).

## Motion

| Moment | Meaning | Ingredients |
|---|---|---|
| Reservation | Compute is committed to a task on a model | The link draws (700 ms); a block travels from the link's midpoint into the budget bar (720 ms, ease-in-out) |
| Settlement | Real costs replace reservations | Blocks resize in place; the overrun grows in red; the scale widens if needed; the over-budget bracket fades in (600 ms) |
| Transfer | Credits move from payer to payee | One token travels along the arc (900 ms) |
| Scene change | Focus moves | The camera pans/zooms (700 ms); the other part recedes to 30 % opacity |
| Keyboard steps | — | Everything lands instantly |
| Reduced motion | — | No movement, scaling or drawing; brief opacity/colour changes only |

No looping, pulsing, particles or decorative glow.
