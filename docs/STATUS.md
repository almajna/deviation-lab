# DEVIATION — status

**Stage:** Phase 1 paired ingestion verified; empirical gate NO-GO. No scientific benchmark or interactive app has been completed.
**Release status:** NOT READY.
**Real-world result claims:** NONE.
**Last verified:** 2026-11-02: bootstrap PR #1 merged; Phase 1 local tests and independent sample reproduction passed. Hosted Phase 1 CI is recorded in its PR. See `docs/DATA_AUDIT.md` and `artifacts/data_audit.json`.

## Milestone tracker
| ID | Milestone | Status | Owner | Required proof |
|---|---|---|---|---|
| M0 | Research design and contracts | Bootstrap draft, approval pending | Codex integrator | Audit PR, passing CI, human approves scientific plan |
| M1 | Real data audit | Technical PASS: 247 four-arm tasks / 988 outcomes; empirical NO-GO | Research worker | Pinned checksums, reproduced aggregates/splits, cost/quality limitations in `docs/DATA_AUDIT.md` |
| M2 | Simulator core | Toy scaffold only | Core worker | Hidden-info tests, replay, cost/utility accounting |
| M3 | Markets | Not started | Mechanism worker | Mechanism math + accounting/unit tests |
| M4 | Attacks | Not started | Adversarial worker | Reproducible exploit and exact bounded check |
| M5 | Benchmark | Not started | Research worker | Frozen splits, baselines, confidence intervals |
| M6 | Visualization | Not started | Frontend worker | Event-driven real replay + usability tests |
| M7 | Policy search | Not started | Research worker | Search traces, held-out test, zero-cost default |
| M8 | Red-team review | Not started | Independent reviewer | Signed-off critical issues or blockers |
| M9 | Release | Not started | Integrator + human | `docs/RELEASE_CHECKLIST.md` and external review |

## Human decisions
- Approve scientific protocol after dataset audit.
- Approve important scope/assumption changes.
- Authorize final release only after independent audit.
