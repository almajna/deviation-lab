# DEVIATION — status

**Stage:** Phase 4 PR #16 merged, synchronized main 8cf8bd3 verified. Phase 5 prereviewed exploratory benchmark implemented; 31 recorded validation tasks and 168 synthetic cases evaluated. No demonstrated market superiority or final evaluation.
**Release status:** NOT READY.
**Real-world result claims:** NONE.
**Last verified:** 2026-11-02 Pacific: independent protocol review preceded evaluation; source and clean-installed numerical reproduction passed. Final exact-head review/test count/hosted CI are recorded in the Phase 5 PR. All earlier artifacts remain immutable.

## Milestone tracker
| ID | Milestone | Status | Owner | Required proof |
|---|---|---|---|---|
| M0 | Research design and contracts | Gate A v0.2 approved and merged | Codex integrator | PR #6, exact-head owner approval, ancestry and CI verified |
| M1 | Real data audit | Accepted exploratory pool: 247 tasks / 988 outcomes; no broad empirical GO | Research worker | Unchanged Phase 1 evidence and approved limitations |
| M2 | Simulator core | v0.2 merged in PR #9; 77 implementation tests/replay and CI passed | Codex core worker | Issue #7, implementation PR/CI, hidden-info and accounting invariants |
| M3 | Markets | v0.3 engine merged in PR #14; approved source ancestry verified | Codex economic backend owner | Issue #13, actual engine tests, independent review, installed/historical replay, green CI |
| M4 | Attacks | Merged PR #16; finite exact/bounded search and conditional synthetic counterexample independently verified | Adversarial worker | Issue #15, source-bound receipts, independent payoff challenge and CI |
| M5 | Benchmark | Working exploratory benchmark; reviewed protocol, paired baselines/uncertainty, negative/null results; under PR review | Research worker | Issue #18, source-bound tables/plots, clean installed reproduction and CI; final holdout disabled |
| M6 | Visualization | Preparation PR #10 merged; app implementation/visual quality not verified by backend owner | Claude Code frontend worker | Issue #8, frontend PR with build/interaction/screenshots |
| M7 | Policy search | Not started | Research worker | Search traces, held-out test, zero-cost default |
| M8 | Red-team review | Not started | Independent reviewer | Signed-off critical issues or blockers |
| M9 | Release | Not started | Integrator + human | `docs/RELEASE_CHECKLIST.md` and external review |

## Human decisions
- Review the Phase 5 implementation PR before human merge. Gate A/B are approved; evaluation/release gates remain open.
- Approve proposed main protections and identify a separate GitHub reviewer before activating them.
- Approve important scope/assumption changes.
- Authorize final release only after independent audit.
