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

## D-009 — 2026-11-02 — Owner-approved limited scientific development
Approval source: the owner's Gate A instruction after Phase 1 acceptance. Use ArenaHard win/tie/loss only as a noisy preference proxy; reported historical costs only retrospectively; train-only fixed reservations with separate realized overruns/violations; the 247-task pool only for exploratory engineering; explicitly synthetic agents with sealed outcomes. No correctness, verified billing, deployable dollar savings, real-world hard-budget, observed-agent or broad superiority claims. Preserve an untouched final evaluation after protocol freeze; do not run it now. Details: `RESEARCH.md`. Owner: human research director. Reversible by reviewed scientific amendment. Assumption approval received; exact v0.2 contract approval/merge pending.

## D-010 — 2026-11-02 — Initial reservation and payoff contract choices
Choose exact-decimal train-only arithmetic means, upward rounding at 1e9 scale, fixed reservations and exclusion of training prompt groups from decisions. No cross-fitting, hidden-cost refunds or held-out fallback. Separate reservation feasibility from realized-cost accounting and virtual credits from historical costs. Utility includes cash balance delta once plus modeled external benefit minus distinct noncash effort; maker initial subsidy is separate from cash P&L/loss. Alternatives: hidden dynamic costs, mixed units and duplicated fees; rejected. Evidence: synthetic v0.2 fixtures/adversarial tests. Owner: integrator. Reversible by versioned review. These are proposed contract choices, not a real-data fit or economic engine. Spend $0.

## D-011 — 2026-11-02 — Human-only merges and enforcement proposal
Read-only evidence attributes PR #3/#4 merges to the `almajna` account, not a particular person/client/process. Current auto-merge is off, main is unprotected, no rulesets exist, and neither PR has submitted GitHub reviews. Agent merge/auto-merge/bypass operations are forbidden; CI stays read-only. Proposed main ruleset requires independent review and Actions CI with no bypass actors, force pushes or deletion. Not applied: owner must approve restrictions and identify a separate authorized GitHub reviewer. Evidence: `MERGE_GOVERNANCE.md` and aggregate receipt. Reversible yes. Owner: human for settings/merge; integrator for proposals. No settings changed, no merge performed, $0 spent.
