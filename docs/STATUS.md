# DEVIATION — status

**Stage:** Phase 2 simulator and Phase 6 handoff PRs #9/#10 are merged. Gate B economic-design proposal is under independent adversarial review; human exact-head approval and merge are pending. No runtime market, attack or final evaluation is authorized by this design PR.
**Release status:** NOT READY.
**Real-world result claims:** NONE.
**Last verified:** 2026-11-02 Pacific: PR #9 merge 5d27b36892562dda412a406a7566c6ed91e88c7f and PR #10 merge 9899618a72cc5df9cc18980ad58d9bd4381b1bf7 verified; approved implementation heads are ancestors of synchronized main. Main CI run 41552305655 passed. Gate B tests/evidence are recorded in its PR. No recorded-cohort or final holdout experiment ran.

## Milestone tracker
| ID | Milestone | Status | Owner | Required proof |
|---|---|---|---|---|
| M0 | Research design and contracts | Gate A v0.2 approved and merged | Codex integrator | PR #6, exact-head owner approval, ancestry and CI verified |
| M1 | Real data audit | Accepted exploratory pool: 247 tasks / 988 outcomes; no broad empirical GO | Research worker | Unchanged Phase 1 evidence and approved limitations |
| M2 | Simulator core | v0.2 merged in PR #9; 77 implementation tests/replay and CI passed | Codex core worker | Issue #7, implementation PR/CI, hidden-info and accounting invariants |
| M3 | Markets | Gate B design/math/examples only; approval pending, runtime not implemented | Codex economic backend owner | Issue #11, adversarial review, math tests/CI, human exact-head approval |
| M4 | Attacks | Not started | Adversarial worker | Reproducible exploit and exact bounded check |
| M5 | Benchmark | Not started | Research worker | Frozen splits, baselines, confidence intervals |
| M6 | Visualization | Preparation PR #10 merged; app implementation/visual quality not verified by backend owner | Claude Code frontend worker | Issue #8, frontend PR with build/interaction/screenshots |
| M7 | Policy search | Not started | Research worker | Search traces, held-out test, zero-cost default |
| M8 | Red-team review | Not started | Independent reviewer | Signed-off critical issues or blockers |
| M9 | Release | Not started | Integrator + human | `docs/RELEASE_CHECKLIST.md` and external review |

## Human decisions
- Approve the exact Gate B design head before economic-mechanism implementation on a separate branch. Gate A remains approved; later evaluation/release gates remain open.
- Approve proposed main protections and identify a separate GitHub reviewer before activating them.
- Approve important scope/assumption changes.
- Authorize final release only after independent audit.
