# DEVIATION — status

**Stage:** Gate A approved at exact commit `a0449c9add2ee3aeb1741d48d41e725d5e8db261` and PR #6 merge verified on main `cb4fb585171f4dde371e4dfa4319d21e9ca70bc1`. Phase 2 engineering is active; Phase 6 Claude Code handoff is prepared in a separate worktree. Historical audit NO-GO remains unchanged; no broad empirical qualification or completed benchmark/app.
**Release status:** NOT READY.
**Real-world result claims:** NONE.
**Last verified:** 2026-11-02 Pacific: explicit owner contract approval; approved commit ancestry verified; contract CI run 41549422392 and merged-main CI run 41549521955 passed. Local Phase 2 synthetic conformance/invariant tests pass; hosted implementation CI and final exact-head independent review remain required before merge. No real-data fit, final evaluation or market implementation has run.

## Milestone tracker
| ID | Milestone | Status | Owner | Required proof |
|---|---|---|---|---|
| M0 | Research design and contracts | Gate A v0.2 approved and merged | Codex integrator | PR #6, exact-head owner approval, ancestry and CI verified |
| M1 | Real data audit | Accepted exploratory pool: 247 tasks / 988 outcomes; no broad empirical GO | Research worker | Unchanged Phase 1 evidence and approved limitations |
| M2 | Simulator core | v0.2 implementation under independent review; synthetic tests/replay pass | Codex core worker | Issue #7, implementation PR/CI, hidden-info and accounting invariants |
| M3 | Markets | Not started | Mechanism worker | Mechanism math + accounting/unit tests |
| M4 | Attacks | Not started | Adversarial worker | Reproducible exploit and exact bounded check |
| M5 | Benchmark | Not started | Research worker | Frozen splits, baselines, confidence intervals |
| M6 | Visualization | Separate worktree and pinned Claude Code brief prepared; app not implemented/session not launched | Claude Code frontend worker | Issue #8, frontend PR with build/interaction/screenshots |
| M7 | Policy search | Not started | Research worker | Search traces, held-out test, zero-cost default |
| M8 | Red-team review | Not started | Independent reviewer | Signed-off critical issues or blockers |
| M9 | Release | Not started | Integrator + human | `docs/RELEASE_CHECKLIST.md` and external review |

## Human decisions
- Review Phase 2 implementation and Phase 6 frontend PRs; human merges only. Gate A approval is recorded above.
- Approve proposed main protections and identify a separate GitHub reviewer before activating them.
- Approve important scope/assumption changes.
- Authorize final release only after independent audit.
