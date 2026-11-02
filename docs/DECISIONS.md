# Architecture / scientific decision log

Each entry: Date, ID, Decision, Alternatives, Why, Evidence, Reversible?, Owner, Human approval required?

## D-001 — 2026-11-02 — Local-first offline empirical benchmark
Use recorded, paired LLM task outcomes wherever valid, with synthetic economic signals clearly distinguished. Avoid mandatory paid model inference. Rationale: reproducibility, near-zero spend, tractable counterfactual replay.

## D-002 — 2026-11-02 — No unverified scientific claims
The project can guarantee an engineering procedure, not market superiority, scientific novelty, a subjective rating, or fully hands-off completion.

## D-003 — 2026-11-02 — One integrator, isolated implementation branches
Shared contracts are merged first; implementation agents own non-overlapping files and PRs. Rationale: minimize merge conflict and silently diverging APIs.

## D-004 — 2026-11-02 — Bootstrap installation command correction
Remove the nonexistent `examples/` path from the documented staging command and include the packaged `COPY_TO_CODEX.md`. Evidence: the ZIP contains 39 files with no `examples/` directory; the independent bootstrap review identified that the original command would fail. Scope is documentation only; the synthetic reference and draft contracts are unchanged. Reversible: yes. Owner: Codex integrator. Human approval required: routine correction included in the bootstrap PR for review.
