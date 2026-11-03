# Independent actual implementation review — Phase 3

Issue [#13](https://github.com/almajna/deviation-lab/issues/13). Date: 2026-11-02 Pacific. Reviewer: separate `market_review` agent, read-only; it did not author or modify the feature. After corrections its verdict is **no unresolved implementation blocker**, with **120 tests independently passing**. Exact committed-head clean-export and hosted CI results are recorded in the implementation PR. Human review/merge remain required; this is not a separately authenticated GitHub approval or a scientific-results endorsement.

## Findings and corrections on actual code

| Finding / challenge | Correction and verification |
|---|---|
| Calibration at exact square-root/remainder ties could reject valid inputs | Exact rational-ratio root path cancels common irrational factors. Regressions include normalized (2,8,0)/10 and (1,4,9)/14, one-hot and zero components. |
| Custom no-op/update/commit IDs were not preserved in public replay | Persist authoritative accepted command IDs and reserved rejected IDs, and reconstruct the exact used-ID state. Custom no-op followed by an otherwise colliding-looking trade now reproduces. |
| Pooling controls could accept trades through injected policies | Trusted mechanism capabilities restrict LMSR to trade/no-op, interactive pooling to update/no-op and static controls to no-op. Hostile cross-treatment requests reject without financial mutation. |
| A prefix convention alone could permit overlapping actor namespaces | Strict actor syntax excludes slash; actor/ command namespaces are disjoint. Future report-token IDs cannot be pre-reserved by another report. |
| Snapshot method could disclose settled history after decisions | Snapshot refuses all nondecision stages; original acting packets never receive outcomes or foreign private signals. Independent sealed-input mutations left actual packets and all pre-settlement events unchanged. |
| Funding budget needed complete resources, not maker reserves alone | Overall cap includes initial agent wallets, per-cell makers and segregated scoring reserve. Controller-level cash/token/slot/position caps and a single external utility prevent alias multiplication. |
| Last-slot utility helper could be called at earlier horizons or with forged quotes | Require final optional slot and LMSR, verify membership in certified candidates, and refuse earlier-turn/cross-treatment calls. No hidden-label objective exists. |
| Shallow event key checks were insufficient as a standalone validator | `validate_result` regenerates the complete public economic state machine and compares canonical event bytes, including all nested arithmetic/types. `event_shape` is explicitly only an envelope helper. |
| Initial malformed commitments needed safe slot behavior | Decline only that report token, emit a content-free rejection, retain optional slots and never pay its score. Independent malformed-profile and future-token probes passed. |

The reviewer formally inspected the alternating exp enclosure, dyadic outward operations, log atanh tail bound, max-shift potential, signed ceiling and translation shortcuts. It independently reported 6,238 additional numerical/funding/translation checks, 500 actual engine transitions, 108 parameter-profile/treatment replays, hostile nested receipt mutations and actual packet/hidden-input invariance probes. These are supplementary diagnostics, not a claim of exhaustive numerical or attack coverage. The committed suite provides reproducible checks and the proof obligations are documented in `MARKETS.md`/source.

## Reproduction

Python 3.11+:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/check.sh
PYTHONPATH=src python3 -m deviation.markets tests/fixtures/markets/two_task.json --out market-output --verify artifacts/markets/two_task/receipts.json
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out current-legacy-output --verify artifacts/simulator/v0_3_source/receipts.json
```

CI also installs the wheel, verifies both new source-bound receipts, exports original Phase 2 source at `390e1b7a63cf31306d78815e381f81ec7245f8d6` and verifies immutable original receipts with that source. Original canonical receipt hash remains `9abd80c9628d4f3030522f79904662adc109f23deefc1ec5a6c22e0f4dcf3c83`. No historical artifact is relabeled or overwritten. Existing v0.2 behavior matches exactly apart from new implementation/receipt hashes. Original simulator code, v0.2 contracts/fixture, Phase 1 evidence, frontend, README, license and .gitignore have no implementation diff.

## Limits of this evidence

The runnable scenario and all generated artifacts are explicitly synthetic. The CLI executes no recorded-cohort or final evaluation and supplies no empirical market advantage, exploit or incentive theorem. Numeric ambiguity fails closed at the configured precision limit. Trusted Python policies are not a hostile-code sandbox.

Public transition validation proves internally consistent financial/stage transitions, not source authenticity or the truth of private rejected request bodies. Original-input replay supports trusted built-ins; injected local policies are labeled and refused by built-in source replay, while their public accepted transitions remain validated. Signals are supplied synthetic beliefs; no coherent posterior inference or empirical signal channel is invented. Default interactive pooling can match raw pooling, and score/raw-pool allocation paths coincide by design. Actual attack search, optional bid mechanics, live settlement, final evaluation and frontend integration remain future work. $0; no automatic merge.
