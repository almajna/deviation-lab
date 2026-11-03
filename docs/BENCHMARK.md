# Exploratory scientific benchmark

Issue #18; backend ownership `src/deviation/evaluation`, tests, experiments, scientific artifacts/docs and CI. The approved simulator/market/attack implementation and shared contracts are unchanged. Claude's frontend is untouched.

## Reproduce

Python 3.11+ and standard library run the benchmark; matplotlib 3.10.7 is a free optional plotting dependency. No model calls, generated benchmark solution execution or paid services.

```sh
python -m pip install --no-deps .
python -m unittest discover -s tests -v
benchmark_cache="$(mktemp -d)"
python -I -m deviation.evaluation --cache "$benchmark_cache" --download \
  --out replay/phase5 --verify artifacts/benchmark/phase5/results.json
python -m pip install matplotlib==3.10.7
MPLCONFIGDIR=replay/mpl python scripts/plot_benchmark.py replay/phase5
```

The bounded download reads the pinned 8 MiB public LLMRouterBench archive prefix, whitelists/checksums the same four audited JSON members and reuses Phase 1 complete-case/group split validation. No RouterBench pickle is downloaded or deserialized. Reuse the cache without `--download` for offline reproduction. Raw cache bytes stay outside Git. No raw prompts/responses/per-task real labels or costs are redistributed; recorded rows in results.json are **batch-level aggregate diagnostics** plus irreversible receipt hashes.

`--synthetic-only` runs only the controlled worlds; it deliberately produces a different result object. There is no final/test evaluation option. Protocol status/guardrails, review digest, source/split provenance and the validation-only loader boundary reject unsupported scopes. Inputs are trusted research configuration: a user who edits source/manifests or fabricates a review receipt can violate the process; this is not a hostile-code/data security sandbox. Final evaluation requires a new explicitly approved frozen protocol and independently sealed cohort. No such final cohort is provisioned here.

## Implementation and information

The benchmark uses the actual approved Engine, certified LMSR quotes, funded scores, controller resources, exact allocator and reservation validators. It does not relabel recorded outcomes as synthetic to bypass the Phase 3 synthetic-only runner. `benchmark-episode-1` is a separate backend research receipt containing existing v0.3 event shapes, provenance, actual allocation, accounting, metrics and pre-decision hashes. It is not a changed frontend/shared contract.

`execute(..., defer_settlement=True)` returns a settlement callback only after all report/trade/allocation work locks. The benchmark locks every ordinary treatment before invoking any current-outcome provider. Oracle is then a separately privileged post-lock analysis. Mutating target quality/costs while holding actual permitted observations fixed leaves decisions and pre-decision hashes unchanged. For synthetic channels, changing the observation legitimately can change decisions; labels themselves never enter posterior() or policies.

Real forecasts use train-only hashed shards/text neighbors and group-excluded inner training calibration. No current validation label/cost generates a signal, funds an order, selects a strategy or fits a reservation. The full-training text router uses the same union training information. These are transparent weak predictors, not a state-of-the-art routing claim.

Synthetic nature uses a declared nondegenerate likelihood and a separate hidden RNG for outcomes. Marginal Bayes forecasts apply only at initial own observation; trading thereafter is fixed-belief myopic. Development search enumerates twenty contingent policy templates on four worlds per mechanism/reward condition; winners freeze before 56 validation worlds (seven profiles × eight draws). Every full schedule executes. This is a finite policy-class sample optimum, not a global dynamic-game optimum or expected-profit proof.

The synthetic schedule seed is fixed at **41** across worlds; nature seeds vary outcomes/observations. Unit tests cover other schedules, but the result does not establish schedule generalization. No claim of robust behavior across arbitrary orders is supported by `all_schedules_supported`; that field means every declared episode was executable without the old terminal-suffix restriction.

Immediate and delayed report biases allow actual interactive revisions. Original reports remain properly scored; subsequent revisions are not scored by the approved engine, though fees/caps apply. This can create a familiar structural manipulation opportunity, not evidence of novelty. Honest fixed-signal interactive agents normally have no reason to revise, so this is not an ideal Bayesian interactive control. Synthetic calibrated-pool uses the identity temperature on already specified marginal posteriors; recorded calibrated-pool fits its temperature from OOF training only.

Normalized alias comparisons always register h0,h1,z0,z1. Controlled aliases share the same private observation, two report weights and fixed aggregate money/caps/tokens/slots/subsidies in both conditions. Only capital and turn assignment are partitioned. This controls the previous funding/opportunity confound for account splitting, not unrestricted Sybil creation or heterogeneous-information coalition inference.

## Artifacts, units and uncertainty

`artifacts/benchmark/phase5/results.json` contains source/protocol/review hashes, development candidate tables, every recorded aggregate and synthetic row, primary contrasts/intervals and a full first-declared synthetic receipt selected regardless of success. Six data/report files are bound by manifest.json. SVGs are separately bound to exact aggregate plot data, plot-script hash and pinned matplotlib by plot_manifest.json. Numerical outputs reproduce byte-for-byte across tested Python 3.11/3.12; SVG byte encoding may depend on the graphics platform, so CI binds regenerated figure bytes to their inputs/script instead of claiming cross-platform byte identity.

**All historical reservation/cost columns are integer nanos or averages of integer nanos, unit `nano_reported_usd` (1e9 nanos per reported historical USD).** They are not new expenditure, verified bills or deployment savings. Fees, funded scoring, capital and maker P&L are separate virtual credits. External benefit is utility-only; preference quality has its own proxy units. No table converts between these units. The result's reservation artifact records the cost unit and estimator. Per-selected-row ceiling contributes less than one nano of rounding.

The primary recorded estimand is task-weighted quality over 31 validation tasks. Bootstrap resamples eight fixed budget batches after averaging three schedule seeds, retaining batch sizes 4×7+3; it is conditional batch variation, not population uncertainty or a globally reoptimized budget bootstrap. Categorical Brier evaluates forecast accuracy; descriptive reliability bins and mean batch bin absolute error diagnose calibration without a significance claim. Cheapest/random/best-fixed/oracle calibration columns describe common pooled reports, not probability forecasts produced by those routing rules.

Synthetic intervals resample eight paired nature worlds within each profile. They estimate Monte Carlo uncertainty within this generator. No winner is chosen on validation and no negative gain is clamped. Degenerate zero intervals can reflect an identical selected policy, not proof that no other strategy is profitable. Full-engine exact terminal search and its old claims remain separately available.

See `PHASE_5_RESULTS.md` for conclusions, `PHASE_5_REVIEW.md` for skeptical evidence, and the prereviewed `PHASE_5_PROTOCOL.md` for the design. No final holdout, broad superiority, release or automatic merge is authorized.
