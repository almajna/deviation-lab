# DEVIATION — status

**Stage:** Phase 1 accepted for limited exploratory development; Gate A shared-contract v0.2 approval/merge pending. Historical audit NO-GO remains unchanged; no broad empirical qualification or completed benchmark/app.
**Release status:** NOT READY.
**Real-world result claims:** NONE.
**Last verified:** 2026-11-02: PRs #3/#4 merged into main and synchronized before this proposal. Approved development assumptions are in `docs/RESEARCH.md`; tested v0.2 proposal and merge-governance investigation are in the Gate A PR. No real-data fit, mechanism run or final evaluation was performed here.

## Milestone tracker
| ID | Milestone | Status | Owner | Required proof |
|---|---|---|---|---|
| M0 | Research design and contracts | Limited assumptions approved; v0.2 exact-head approval/merge pending | Codex integrator | Gate A PR, CI, independent review, explicit owner approval |
| M1 | Real data audit | Accepted exploratory pool: 247 tasks / 988 outcomes; no broad empirical GO | Research worker | Unchanged Phase 1 evidence and approved limitations |
| M2 | Simulator core | Toy scaffold only | Core worker | Hidden-info tests, replay, cost/utility accounting |
| M3 | Markets | Not started | Mechanism worker | Mechanism math + accounting/unit tests |
| M4 | Attacks | Not started | Adversarial worker | Reproducible exploit and exact bounded check |
| M5 | Benchmark | Not started | Research worker | Frozen splits, baselines, confidence intervals |
| M6 | Visualization | Not started | Frontend worker | Event-driven real replay + usability tests |
| M7 | Policy search | Not started | Research worker | Search traces, held-out test, zero-cost default |
| M8 | Red-team review | Not started | Independent reviewer | Signed-off critical issues or blockers |
| M9 | Release | Not started | Integrator + human | `docs/RELEASE_CHECKLIST.md` and external review |

## Human decisions
- Approve the exact v0.2 contract PR head before Phase 2/Phase 6.
- Approve proposed main protections and identify a separate GitHub reviewer before activating them.
- Approve important scope/assumption changes.
- Authorize final release only after independent audit.
