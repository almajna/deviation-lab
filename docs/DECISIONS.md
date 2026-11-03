# Architecture / scientific decision log

## Agent 2 — independent certificate evaluation (2026-11-02 Pacific)

Own additive verification package and synthetic fixtures in #22 / PR #25, stacked
on unmodified Agent 1 #23. Freeze criteria publicly before outcomes at d77e2cd;
evaluate only synthetic development subgames. Preserve source-bound historical
artifacts; new integrated proofs bind the new package. Use independent exhaustive
and memoized exact DP baselines, disclose warmed timings and known prior art.
After the first negative speed result, add only failure recording and explicit
canonical-root rejection; retain the original result and regenerate evidence.
Secondary ordinary exact search does not enter the frozen primary criterion.
Routine reversible engineering/evaluation implementation under the user's scope;
no final holdout, assumption change, spend, merge or release. Owner: Agent 2.

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

## D-012 — 2026-11-02 — Activate approved contracts in isolated implementation worktrees
The owner explicitly approved v0.2 at a0449c9add2ee3aeb1741d48d41e725d5e8db261 after PR #6 merged. Verified ancestry on main cb4fb585171f4dde371e4dfa4319d21e9ca70bc1 and both contract/main CI. Phase 2 uses codex/economic-core; Phase 6 Claude Code preparation uses codex/visual-lab. Use src/deviation/simulator/ rather than a core/ package to avoid shadowing the legacy core.py API. Shared contracts/schemas and original Phase 1 evidence stay unchanged. Reversible namespace choice; owner integrator; no new scientific assumption or paid spend.

## D-013 — 2026-11-02 — Reference-policy and accounting execution choices
Choose exact sparse multiple-choice knapsack over mean synthetic reports, with explicit state-limit failure and abstention; deterministic cheapest/train-best-fixed and seeded feasible random references share reservation constraints. Train-best-fixed quality parameters cover validated training pairs only. Post-decision selected costs and quality remain sealed during decisions. Reserve fees in authoritative agent credits and post once to a conserved ledger; configurable fixed funded synthetic payouts test approved payoff accounting only, not a market/scoring rule. No oracle live policy, dynamic code loading, real-data experiment or final holdout CLI. Reversible implementation choices; evidence in simulator tests; owner Codex core worker; $0.

## D-014 — 2026-11-02 — Gate B proposal before economic implementation
Verified PRs #9/#10 merged and synchronized main 9899618; CI passes. Gate B proposes three-state judged-proxy markets, all-arm offline settlement, exact grid-funded scoring, long-only constant-b LMSR with segregated fully funded makers, signed-ceiling charges, explicit resources/nonmarket controls and fixed controller-level attack budgets. Alternatives: threshold binary events lose tie information; live selected-only settlement, naked shorting and adaptive liquidity require additional theory and are excluded. Math/fixtures/tests live outside runtime source and active v0.2 contracts. Codex owns economic backend; frontend untouched. These are proposed scientific choices, not approved changes or implemented market results. Reversible by independent review; owner exact-head Gate B approval required; $0.

## D-015 — 2026-11-02 — Implement approved Gate B with certified integer arithmetic
Owner explicitly approved a8bbcd7; PR #12 merged at ea0c0a3. Implement v0.3 separately under deviation.markets with dyadic interval exp/log enclosures, certified signed ceilings and price grids, exact score arithmetic, funded cell makers/scoring, controller caps and staged copied policy packets. Fixed actor namespaces and recorded IDs preserve public replay and avoid ID theft; action capabilities are treatment-specific. Initial report fee is zero; optional attempt effort includes every consumed slot. Synthetic CLI only; no final/recorded experiment. Reversible engineering choices within approved design; code/tests and independent review provide evidence. $0.

## D-016 — 2026-11-02 — Preserve historical source-bound receipts rather than relabel
New package modules change the Phase 2 fingerprint by design. Keep original artifacts immutable, verify them from 390e1b7 in CI, and generate separately versioned current-source v0.2 and market receipts. Replace the Gate B design-only source-freeze assertion with exact behavior compatibility plus source-version distinction. No fingerprint check is disabled. Injected test policies retain public transition validation but refuse built-in source replay; last-slot candidate value has no earlier-turn belief model. Owner integrator; reversible by reviewed versioned changes; no new scientific approval or spend.

## D-017 — 2026-11-02 — Information-safe finite adversarial discovery
Verified PR #14 merged and 1afe571 ancestor of main 5306ded. Implement Phase 4 in isolated codex/adversarial-discovery using the unchanged approved market engine. Choose exact finite terminal-controlled suffix/final-global-report search plus bounded seeded beam; reject unknown future honest actions and require an explicit public opponent report model for static reports. Share fixed resources across registered aliases, with no causal across-registry Sybil claim. Independent event-level payoff recomputation, actual transition replay, reoptimized zero-external controls and source-bound sidecars preserve v0.3 contracts. Synthetic exogenous belief errors are prescribed subjective models, not Bayesian signals; hidden draws use an evaluator-only seed. An invalid correlation campaign was discarded and regenerated after review. These reversible restrictions narrow the search scope without expanding Gate B assumptions. Owner integrator; evidence in Phase 4 docs/tests/artifacts; $0. Human review/merge remains required; no final empirical holdout or scientific superiority claim.

## D-CERT-001 — 2026-11-02 — Additive finite attack certificates
Owner-requested Agent 1 implementation, tracked in #20 on isolated codex/certified-attack-discovery. Retain approved engine, existing outcome-free terminal/final-report subgames and fixed subjective beliefs; add best-bound search, rounded-charge endpoint relaxation and an independently executable proof checker. Preserve unresolved boundary nodes on truncation. Shared contracts, Agent 2 verification/experiments, Agent 3 harness and final holdout remain unchanged. Alternatives: label beam optima certified, assume unobserved future policies, or solve a continuous-cost surrogate; rejected. The contribution is an engine-specific checkable bound, not new economic manipulation or global robustness. Source-bound historical artifacts stay immutable and CI checks them at base source 8cf8bd3; new sidecars bind current source. Routine reversible engineering within existing approved model; no new scientific assumption or spend. Human review/merge and independent Agent 2 benchmarking remain separate.
