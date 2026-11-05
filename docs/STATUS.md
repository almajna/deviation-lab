# Project status

Snapshot based on main `0820563fe772a6706e3420c4762211dea0513b6f` (2026-11-04 Pacific). This is a research release candidate, **not a finished or approved public release**. Earlier plans, protocols and review notes preserve their historical context; their progress statements may be stale.

- Economic simulation, markets, bounded attack search, certificate checking and backend integration are present on main. See [backend integration](BACKEND_INTEGRATION.md), [adversarial lab](ADVERSARIAL_LAB.md) and [certificate evaluation](../artifacts/verification/REPORT.md).
- Recorded open-weight experiments and a controlled LiteLLM study are present. See the [results index](RESULTS.md). LiteLLM's scientific verdict is **INCONCLUSIVE**.
- The data audit identifies 247 complete four-model exploratory tasks and 988 outcomes; important data, cost and license caveats remain. The final holdout has not been evaluated. See [data audit](DATA_AUDIT.md) and [Phase 5](PHASE_5_RESULTS.md).
- A frontend PR exists but is separately owned; this documentation update does not assess its current quality or release readiness.
- The proposed [public introduction](../README_RELEASE_DRAFT.md) remains a draft: replacing the existing README fails the historical research preservation guard in `src/deviation_research_replay/provenance.py`. The guard and original README are unchanged. Full original LiteLLM ZIP preservation, current-head checks, and release approval remain required. Historical agent review is not external peer review.

## Open pull requests at this snapshot

| PR | Classification | Status at inspection |
| --- | --- | --- |
| [#17](https://github.com/almajna/deviation-lab/pull/17) | Frontend implementation; separately owned | Open; requires its own current-head review. |
| [#25](https://github.com/almajna/deviation-lab/pull/25) | Certificate work, previously integrated through backend PR #29 | Open stacked PR; compare current trees and review before any closure. |
| [#31](https://github.com/almajna/deviation-lab/pull/31) | Research feasibility gate | Draft; reported merge conflict and unresolved data eligibility. |
| [#34](https://github.com/almajna/deviation-lab/pull/34) | Agent instruction configuration | Open; independent review pending. |
| [#35](https://github.com/almajna/deviation-lab/pull/35) | Separate reasoning experiment | Draft; reports a negative frozen result; evidence lives on its branch. |
| [#37](https://github.com/almajna/deviation-lab/pull/37) | Frontier sprint research notes | Draft; source-level lead subsequently studied in merged #39; review notes independently. |

No PR is merged or closed by this status update. Open PR status can change; consult GitHub for current state.
