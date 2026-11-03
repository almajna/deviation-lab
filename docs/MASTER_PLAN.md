# DEVIATION — master plan and critical path

**Project**: adversarial laboratory for AI resource markets. **Repository**: https://github.com/almajna/deviation-lab. **North star**: credible mechanisms research plus a beautiful, interactive, reproducible *exploit theater*. **Release policy**: internal >=90/100 and all scientific blockers closed; external perceived impressiveness cannot be guaranteed.

## The one-sentence demo
A market forecasts where a limited AI inference budget would help most; strategic participants try to corrupt the allocation; DEVIATION automatically finds an attack, measures its effect on real recorded AI task outcomes where possible, and plays back exactly why the market failed. Viewers can compare an alternative mechanism on the same scenario.

## Scope

### Empirical track: offline model routing
Use recorded judged preference proxy q(i,m) and reported historical cost c(i,m) where paired observations are verified. The allocator sees permitted pre-decision information and fixed training-only reservations r(m), choosing routes under reservation budget B. Report realized costs, overruns and violations after decisions. The approved 247-task pool is exploratory only. This is not objective coding correctness, verified billing, guaranteed deployment budgets, real-time savings or live market truthfulness. Forecasters and adversaries are synthetic. See `docs/RESEARCH.md` and the shared-contract gate.

### Economic track: controlled mechanisms and adversaries
A finite information game where agents receive private noisy signals about model outcomes/uplift; their beliefs, reports, trades and payoffs are explicit. Compare direct reports, proper scoring, LMSR-style virtual market and a simple bid mechanism; include an unambiguous non-market average/aggregator. Have strategic agents with stated external interests (e.g. routing to their favored model). Search for manipulations, compare honest vs adversarial welfare, record a reproducible attack. Separate observed versus modeled events in UI.

### Mechanism discovery track
Use fixed program templates and bounded parameter search to optimize for quality, efficiency, and robustness under held-out attack settings. Optional AI-assisted SkyDiscover search is nice-to-have, not required for release. No inference budget or novelty claim required.

### Visual experience track
A responsive static website with three event-driven interactive views: Market Arena, Exploit Theater, and Mechanism Evolution. The first hero demo is a **true reproduced counterexample against an explicitly vulnerable reference rule**, never fictionalized. Charts/animations must reflect stored experiment traces. Public site works entirely without secrets or backend APIs.

## Work breakdown and precise gates

| Phase | Agent | Dependency | Deliverable | Gate |
|---|---|---|---|---|
| 0 — Foundation | Codex lead | Current repo | Contracts, issue backlog, CI, dependency map | Human approves key research assumptions |
| 1 — Dataset audit | Research agent | 0 | Candidate inspection, paired-outcome schema, license/provenance audit | A sample truly has matched model outcomes/costs |
| 2 — Core | Core agent | 0+1 | Deterministic simulation, payoff/budget engine, event log, oracle test-only | Tests for no leakage, budget invariants, replay |
| 3 — Markets | Claude market agent | 2 | Market and non-market allocators with explicit payoffs | Unit/invariant tests and settlement specification |
| 4 — Attacks | Claude attack agent | 3 | Bounded exact attack search + heuristic searches | Counterexample independently replayed and verified |
| 5 — Evaluation | Research agent | 3+4 | Train/val/test, baselines, uncertainty, full results | No hidden labels; frozen test only after model selection |
| 6 — Visual | Claude frontend agent | Contracts; integration later | Three cinematic views, trace-driven playback | Visual/interaction tests, no invented data |
| 7 — Discovery | Research agent | 5 | Deterministic optimization + optional SkyDiscover | Held-out improvement properly evaluated or honest null |
| 8 — Red team | Independent fresh agent | 2–7 | Methods and code audit, reproduction report | Zero outstanding critical blockers |
| 9 — Release | Codex lead + human | All | One-command reproduction, report, public demo | Score >=90 plus independent review |

## Parallelism and development sequencing

- Start **Phase 1** immediately after shared contract review. Dataset suitability is a stop/go gate.
- Frontend worker may build layout and interactions against versioned, explicitly **SYNTHETIC** fixture trace once `docs/CONTRACTS.md` is frozen; not against invented experimental claims.
- Core simulator starts as soon as data signal fields/cost semantics are resolved; market modules follow core ABI.
- Adversarial engine starts only after market contracts and payoff accounting are stable.
- Scientific evaluation can prepare split framework and CI independently but cannot claim benchmark results until mechanism code exists.
- Algorithm discovery is last: optimization needs a trustworthy objective and frozen train/test separation.
- Two coding agents should never share a checkout, branch or ownership area.

## Simplest initial configuration
Python 3.11+, standard library for starter, optional NumPy/Pandas/Optuna for scaled experiments. TypeScript/React + Vite for a deployable static web app when Phase 6 starts. Avoid choosing both Vite and Next.js; prefer Vite for static-hosting simplicity. Use JSONL traces and CSV/Parquet metrics with versioned schema. Start with no server, database, Docker daemon, or login.

## Research-grade benchmark goals (minimum meaningful comparison)
- At least two or more candidate models with paired recorded outcomes for a validated set of tasks; scale size based on real data quality rather than an arbitrary number.
- Strong baselines: random with budget, cheapest, best fixed affordable, cost-aware predictor, calibrated non-market aggregator, and oracle for offline interpretation only.
- At least two forecasting signal quality regimes, two information-correlation regimes, and three attack budgets in economic track.
- At least four families of adversarial strategies: report manipulation, coalition, Sybil under permissive identity policy, repeated-game reputation/sandbagging; not every attack must succeed.
- Exact attack search on small games and heuristic search on larger games; don't conflate proven optimality with best-found.
- Held-out benchmark tasks and *held-out attacker classes/settings*; balanced evaluation and uncertainty intervals.
- At least one attack trace that reproduces under a clean install and appears faithfully in UI.

## Failure paths and fallbacks
1. **Paired data missing**: use RouterBench or another independently verified source; postpone empirical claims until audited. Synthetic demonstrations remain labeled.
2. **Market offers no improvement**: publish the null/negative result alongside a benchmark and attack findings, if rigorously established.
3. **SkyDiscover local backend weak/incompatible**: replace with deterministic policy search; don't list AI discovery as accomplished.
4. **No new exploit emerges**: guarantee the *testable ability to reproduce a known theoretical attack against a deliberately vulnerable rule*. Describe it accurately, not as discovery.
5. **Graphics too slow**: Canvas with capped visible nodes, aggregation and reduced-motion mode; never sacrifice correctness of the event log.
6. **Unable to secure independent review**: do not claim independently audited; keep release as candidate.

## Suggested timeline (not a promise)
Accelerated well-resourced coding-agent run: 4–8 calendar weeks for meaningful integration, possibly longer for data auditing, statistical debugging, design polish, and external review. Agents cannot run autonomously merely because a prompt requests it; actual sessions, tools and CI must be configured and kept active.

## What the human must decide
- Approve data source and what empirical claims are supported.
- Approve economic utility model and what participants can observe.
- Decide whether discovered failure matters beyond the synthetic model.
- Review critical security and license findings.
- Review final report, visual quality, and public release.

## Current implementation reality
The repository contains a verified Phase 1 loader/audit, documentation, CI and a tiny synthetic reference. Shared v0.2 contracts at a0449c9 are approved and merged. Phase 2 implementation and Phase 6 handoff PRs #9/#10 are merged. Gate B is approved/merged; a working v0.3 economic engine is under implementation review. The benchmark, market, attacks, evolution system and website are not complete. See `docs/STATUS.md`.
