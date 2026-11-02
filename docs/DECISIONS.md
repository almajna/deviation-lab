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

## D-005 — 2026-11-02 — Bounded paired-data audit
Use pinned byte ranges and original prompt provenance instead of full downloads/inference. Evidence: 1,012 rows across four arms; six unverified zero-cost rows explicitly rejected; 247 complete tasks / 988 outcomes. Keep raw data outside Git, commit aggregate evidence/checksums and synthetic fixtures only. Never deserialize RouterBench pickle. Alternative: full downloads/upstream loaders, unnecessary for this gate. Reversible: yes. Owner: Codex integrator. Incremental spend: $0. Human approval required: none for routine audit engineering; scientific Gate A remains pending.

## D-006 — 2026-11-02 — Private realized costs and grouped exploratory splits
Decision projection contains only original prompt, opaque task ID, and model options. Scores, outputs, ground truth and response-dependent costs stay in audit/evaluation records. Seeded splits keep normalized duplicate prompts together across IDs and validate exact algorithm reproduction. They remain exploratory, not frozen. Alternative: expose realized cost or split model rows independently; rejected for leakage. Reversible: yes. Owner: Codex integrator. Human approval required: future scientific choice of pre-decision cost/budget policy, not this safeguard. Shared contracts unchanged.

## D-007 — 2026-11-02 — Preserve unresolved quality/cost semantics
Retained ArenaHard scores cannot distinguish every judged loss from judging failures; historical rows omit per-row API-cost-versus-token-price provenance. Technical pairing passes; empirical/downstream GO remains blocked. Do not convert this into objective coding correctness, observed invoices, statistical power, or deployable budget guarantees. Evidence: `docs/DATA_AUDIT.md`. Reversible if new evidence resolves gaps. Owner: Codex integrator. Human approval required: existing Gate A decisions on permissible proxy claims and cost semantics before downstream research.

## D-008 — 2026-11-02 — Engineering review follow-up without changing empirical scope
Address the owner's three independent-review findings on PR #3: reject `Generation failed:` with regression coverage, correct the complete zero-cost-file count to six, and add synthetic CLI-to-artifact integration coverage. Explicit synthetic manifest labeling keeps test output distinct from real observations; the real manifest's behavior and all three committed evidence files remain unchanged. Evidence and review limitations: `docs/DATA_REVIEW.md`. Alternatives: treating engineering approval as empirical GO or altering the cohort; rejected because the review is engineering-only. Reversible: yes. Owner: Codex integrator. Spend: $0. Human approval required: no new routine-engineering approval; existing scientific/merge gates remain pending.
