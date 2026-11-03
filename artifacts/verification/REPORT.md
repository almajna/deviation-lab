# Independent attack-certificate evaluation

All **81 cases are synthetic development fixtures**, from the frozen
protocol [d77e2cd6031b665c082a4412597bf564eab657d1](https://github.com/almajna/deviation-lab/commit/d77e2cd6031b665c082a4412597bf564eab657d1).
No real LLM-agent decisions, recorded outcome rows or final holdout were used.
The producer is unmodified Agent 1 PR #23 at 3151edb463484498a5b686bf607dff4f062d66a4.
Integrated source fingerprint: `7d88cd5dfa1d0bd72f0d7c9796a06206ceb1451228171ad67b1041b8a6049b78`.
Results fingerprint: `40cc53c126cc4510715b5bcd9c0c2b9b7c5868d952f0889c57d1e4a8c9d554ae`.

## Correctness and utility of the certificate

The independent checker accepted all 81 generated
proofs. There were **0 interval/baseline disagreements**.
Every completed independent exhaustive or dynamic-programming result lay within
the certified interval. Zero gap establishes finite-subgame optimality only.
This is executable evidence under a shared trusted engine and numeric library,
not a proof-assistant theorem or an independent audit of those dependencies.

| Mechanism | Cases | Zero gap | Exhaustive complete | DP complete | Median / max gap |
|---|---:|---:|---:|---:|---:|
| interactive-pool | 27 | 24 | 24 | 24 | 0 / 24 |
| lmsr | 27 | 27 | 24 | 24 | 0 / 0 |
| pool | 27 | 27 | 27 | 27 | 0 / 0 |

The producer's feasible utility beat ordinary beam search in 0 cases,
lost in 3, and tied in 78. These algorithms have
different units of work: the configured cap is a state expansion cap for the
producer and a candidate-transition cap for beam. The table is not an equal-time
superiority estimate. Beam supplies no mathematical upper bound.
Work counters use finite-game child transitions, with static-report completion
counted as one child; they are not counts of raw Engine.apply invocations.
The endpoint relaxation improved the root bound over its conservative fallback
in 27/81 cases. Largest proof: 12,839,913 serialized bytes.
All rows, including censored baselines and nonzero gaps, appear in results.csv.

The eight-slot LMSR stress cases closed their gaps even where both independent
exact baselines hit their declared state cap. This is useful scoped evidence for
the bound, not an equal-time speedup estimate: a completed exact comparator is
unavailable there. The corresponding eight-slot interactive-pool cases retained
gaps and lost incumbent utility to beam search. The external-reward relaxation
and best-bound exploration do not by themselves guarantee strong feasible search.

The separately labeled unchanged ordinary-exact diagnostic completed 75/81 cases; all completed values agreed with independent exact results and the certified intervals. It was added after the initial protocol at the supervisor's request and does not enter the primary timing criterion.

## Prespecified practical-value criterion

On 72 eligible zero-gap cases with at least two legal root actions and
a completed exact comparator, the median paired ratio
`(median generation time + median independent-check time) / faster completed exact baseline time`
was **2.191**. The descriptive 95% seed-block bootstrap
interval was **[1.159, 2.382]**.
The preregistered threshold (ratio <=0.8 on >=10 cases) was
**NOT MET**.
This is a warm-cache measurement, with one warm run and three retained repeats
per method/case; it does not describe first-run latency. There are only three
seed blocks, related grid cells and repeated static-report settings. The interval
is not a real-world population confidence statement.

Descriptive breakdown (no additional success criteria):

| Mechanism | Eligible cases | Median paired time ratio |
|---|---:|---:|
| interactive-pool | 24 | 0.589 |
| lmsr | 21 | 0.619 |
| pool | 27 | 3.406 |

## Scientific conclusion

The implemented certificate adds an independently checkable upper bound and
explicit residual uncertainty to executable best-found attacks. Its economic
bound uses known branch-and-bound and proof-checking principles applied to the
engine's rounded LMSR charges. This suite does **not** establish a new economic
vulnerability, literature novelty, a breakthrough, full-game robustness or
generic optimization superiority. Passing a finite suite cannot exclude all
implementation errors. Practical value is conditional on the measured criteria
and the narrow information/action model.

## Limits and reproduction

The public schedule is constructed to leave a controlled terminal suffix. It
does not test unknown future honest actions. Prescribed beliefs are not calibrated
LLM forecasts; no realized welfare or accuracy claim follows. Controller account
partitions keep the registry/funding fixed but do not model free identity creation.
Static pool games search one final commitment in every profile, even when the
profile's terminal horizon is larger. Exact DP merges equivalent future economic
states and its returned commands are rebound/replayed; capped runs have no exact
answer. State/expansion caps are not hard runtime or peak-memory limits. Arbitrary
root histories pre-reserving future canonical order IDs are unsupported.

Independent checker code imports no producer optimizer, action generator, bound
or payoff helpers. Engine transitions, certified quotes/prices, reservation
artifacts, Game serialization and the package digest remain shared dependencies.
The checker computes allocation and Brier/utility arithmetic separately.

```
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python -I -m deviation.verification --out replay/certificates --no-timings --verify artifacts/verification/results.json
python -I -m deviation.verification --out replay/measured
python scripts/certificate_ordinary_exact.py replay/measured
python scripts/check_certificate_archive.py artifacts/verification
python -m pip install matplotlib==3.10.7
MPLCONFIGDIR=replay/mpl python scripts/report_certificate_benchmark.py replay/measured
```

Economic values, proofs, work counts and source bindings reproduce exactly;
wall times vary by hardware/load. The first declared base/seed101 case for each
mechanism is retained as a complete example proof regardless of outcome. The
driver emits all proof files. No fee/spending or holdout access occurred.
All 81 complete proofs are also retained in a compressed archive directory with
hashes of compressed and original JSON bytes; they can be independently checked
without rerunning any optimizer.

The first complete run, including its negative speed result, is preserved under
artifacts/verification/initial_run/. The official run follows logging-only failed-case persistence and
explicit rejection of unsupported noncanonical roots; settings and mathematical
algorithms were not tuned. These are disclosed infrastructure corrections.
