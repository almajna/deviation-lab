# DEVIATION — visual direction and interactive specification

## Creative brief
Create a credible instrument for **economics of autonomous AI**, with the polish of a financial terminal and the clarity of a scientific notebook. Target aesthetic: dark ink backgrounds, fine typography, subtle lattice/network grid, restrained cyan-teal for honest activity, amber for uncertain strategic signals, red only for confirmed attacks. High-density information, deliberate whitespace, no generic AI gradient blobs or meaningless particles.

**Main interaction promise**: Any apparent result can be clicked to reveal its exact observed/simulated provenance, input assumptions, decision history and replay ID.

## View 1: Market Arena
- Animated event timeline of predictions, bids and budget assignments; graph/layout groups agents by role or coalition, not random floating dots.
- Controls: play/pause/step, speed, mechanism selection, budget slider (only if simulation is recomputed), seed/scenario selector.
- Agent detail drawer: actual information set at time of action, report/trade, prior credits, external payoff, realized outcome at settlement.
- Price charts, selected allocation and resource flow graph; visual encodings with legend/accessible descriptions.

## View 2: Exploit Theater — flagship
- A saved attack is a story with exact stages: normal equilibrium/baseline, adversarial entry, changed forecast/price, redirected allocation, payoff and welfare consequences, independent replay verification.
- Split-screen: attacked and honest or alternative-mechanism scenario with **same task set and conditions**. Show price shift and allocation delta; offer JSON event log / reproduction command.
- Timeline scrubber should seek deterministically, not rely on rendering-side randomness.
- Use generated trace cases to build a carousel of reproductions; clearly mark any synthetic fixture as a demonstration not a discovery.

## View 3: Mechanism Evolution
- Scatter plot of budget-adjusted quality versus adversarial welfare loss; show uncertainty and held-out vs training indicators.
- Inspect candidate policy parameters, version and source commit; compare leaderboard entries without leaking test data into optimization.
- If SkyDiscover is not used, title 'Policy Search', not 'AI-discovered mechanisms'.

## Implementation and performance
- Vite + React + TypeScript recommended for a static site; simple canvas/SVG with React components and a charting library; avoid stacking 5 animation frameworks.
- Versioned replay JSON contract in `docs/CONTRACTS.md`.
- Start with tiny **SYNTHETIC_FIXTURE** traced examples; swap in genuine verified experiment artifacts for publication.
- Aim for accessible keyboard interactions, contrast, tab order, mobile layout and reduced motion.
- Avoid costly WebGL for tiny networks; aggregate thousands of agents into cohorts and render detail upon selection.
- Use zero external secrets or cloud services in public bundle.

## Design acceptance
At least three task-focused usability flows should work without guidance: (a) compare policy performance, (b) find and replay a valid exploit, (c) inspect why a particular agent received resources. Browser tests should cover all three; screenshots and video are presentation evidence but don't replace functionality.
