# Phase 5 exploratory research report

**Exploratory validation, not final evaluation or evidence of general superiority.**
Recorded LLM judged outcomes are distinct from synthetic forecasting/trading behavior. Quality is a noisy preference proxy; historical costs are not bills or deployable savings.

Protocol `8feebbfcdebc20f18463a068839bd7125b89a5caae5691c5bbd470e83cca5390`; source `ea6facd88431e7726e395b97b8f9e10c102bb8fd606d925db67883c8dcb86fed`; result `05bd899641a761f14823de984e14f04ae892f6b40b86f9238a042156744c283d`.
Independent protocol review preceded evaluation; frozen selection uses separate development worlds. No final cohort was provisioned or accessed; existing exploratory test split was excluded.

## Recorded-outcome validation

Train 172 tasks; validation 31 tasks; excluded exploratory test 44. Four historical model arms, one selected coding-domain cohort. OOF training temperature: 1.
No current-task outcome/cost generated a forecast. Four training-shard forecasters and the union-information text-router use public prompts and training rows only. All ordinary plans lock before any current outcomes are read. Oracle is a separate analysis-only invocation.

| Budget fraction | Mechanism | Mean proxy | Delta vs calibrated pool [95% interval] | Oracle regret |
|---|---|---:|---:|---:|
| 0/1 | lmsr | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | interactive-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | calibrated-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | random | 0.5430 | -0.2151 [-0.3167, -0.1290] | 0.2473 |
| 0/1 | cheapest | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | best-fixed | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | text-router | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.0323 |
| 0/1 | oracle-analysis-only | 0.7903 | +0.0323 [+0.0000, +0.0781] | 0.0000 |
| 1/1 | lmsr | 0.7097 | -0.0484 [-0.1452, +0.0333] | 0.2097 |
| 1/1 | pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | interactive-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | calibrated-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | random | 0.6237 | -0.1344 [-0.3011, -0.0054] | 0.2957 |
| 1/1 | cheapest | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | best-fixed | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | text-router | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/1 | oracle-analysis-only | 0.9194 | +0.1613 [+0.0968, +0.2321] | 0.0000 |
| 1/2 | lmsr | 0.7097 | -0.0484 [-0.1452, +0.0333] | 0.2097 |
| 1/2 | pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | interactive-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | calibrated-pool | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | random | 0.6237 | -0.1344 [-0.3011, -0.0054] | 0.2957 |
| 1/2 | cheapest | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | best-fixed | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | text-router | 0.7581 | +0.0000 [+0.0000, +0.0000] | 0.1613 |
| 1/2 | oracle-analysis-only | 0.9194 | +0.1613 [+0.0968, +0.2321] | 0.0000 |

Intervals resample eight fixed budget batches after averaging schedule seeds, using task-count weighted ratios. They describe conditional batch variation, not population/source-family generalization or globally reoptimized bootstrap budgets. Thirty-one tasks and eight clusters are weak evidence; exact prompt grouping does not resolve semantic duplicates. All contrasts are exploratory, no p-values or multiplicity-adjusted winner claim.

`recorded_table.csv` and results.json retain reported historical spend, overruns, unused reservations, budget violations, reservation utilization, fees, maker funding/P&L, score reserve/payout and calibration. Reliability bins and mean per-batch bin absolute error are descriptive calibration diagnostics, distinct from Brier accuracy. Calibration for cheapest/random/best-fixed/oracle is the common pooled-report diagnostic, not a probabilistic forecast produced by those route rules. Fixed-route tie/zero rescoring is a descriptive ambiguity sensitivity, not recovered judge status or a different optimized objective.

## Synthetic generalization and strategic controls

168 paired validation world/mechanism cases; every schedule supported. Twenty finite policy templates were enumerated on four separate development worlds per mechanism/incentive condition, then frozen for seven unseen-profile conditions and eight validation worlds each. No validation strategy reselection or negative-gain clamping.

| Profile | Mechanism | Utility gain [95% MC interval] | Cash gain | External gain | Proxy loss | Zero-external gain |
|---|---|---:|---:|---:|---:|---:|
| base-unseen-seeds | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| base-unseen-seeds | interactive-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| base-unseen-seeds | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| correlated-information | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| correlated-information | interactive-pool | +1.000 [+0.000, +2.500] | +0.000 | +1.000 | +0.000 | +0.000 |
| correlated-information | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| friction-and-weak-information | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| friction-and-weak-information | interactive-pool | -4.000 [-4.000, -4.000] | -4.000 | +0.000 | +0.000 | +0.000 |
| friction-and-weak-information | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| high-incentive-liquid | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| high-incentive-liquid | interactive-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| high-incentive-liquid | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| integer-friction-control | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| integer-friction-control | interactive-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| integer-friction-control | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| low-incentive | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| low-incentive | interactive-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| low-incentive | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| split-controller | calibrated-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| split-controller | interactive-pool | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |
| split-controller | lmsr | +0.000 [+0.000, +0.000] | +0.000 | +0.000 | +0.000 | +0.000 |

0 of 21 profile/mechanism intervals have a positive lower endpoint. These are unadjusted exploratory Monte Carlo intervals, not global-optimum certificates, validated real-world exploits or a population failure rate.

The likelihood generator gives initial own-observation Bayes forecasts; after report reveal, references are fixed-belief myopic policies, not Bayesian equilibrium traders. Nature outcomes are never given to posterior formation or policy packets. The optimizer sees development completed payoffs; validation seeds/outcomes do not enter selection. Sample-average winner selection can overfit four development worlds. No full-game optimality or expected-profit proof follows.

The fixed h0/h1/z0/z1 registry preserves all report weights, information, sponsor funding, controller cash/caps and controller turn-cell opportunities when splitting one versus two active accounts. Capital/slot partition changes; new unrestricted identities are not created. This eliminates the earlier funding/turn confound for the specified comparison, but does not establish a general Sybil theorem or heterogeneous-information coalition behavior.

## Reproduction and review

Run the reviewed evaluation CLI with the pinned source/split manifests and a local cache, then scripts/plot_benchmark.py for scientific figures. Raw data is not redistributed. results.json contains aggregate recorded batches, every synthetic case, development candidate objectives, code/config/source hashes and a complete first-declared synthetic sample chosen regardless of outcome. All cash/payoff receipts are checked against an independent event-ledger reconstruction. Independent skeptical actual-code review and hosted CI are linked in the PR.

## Remaining research limitations

Small single-source selected development cohort; historical judging failures mixed with zero; unresolved reported-cost provenance; complete-case selection; weak fixed text forecasters; intrinsic differences between trade/update action spaces; fixed-belief post-reveal policies; narrow finite attack class and small Monte Carlo sample; conditional rather than deployment uncertainty; no semantic-family holdout or final untouched cohort. Negative/null results are retained. These limit claims rather than justify manufacturing improvements. $0 paid spend; no frontend or shared-contract edits. Human review and merge remain required.
