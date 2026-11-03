# Phase 5 findings and limits

The prereviewed exploratory benchmark found **no demonstrated market advantage** in the tested configuration. It also did not establish a generalized profitable harmful market manipulation. These are results of the specified weak forecasting/policy classes and small samples, not proofs of market inferiority or robustness.

Full reproducible tables/report/figures are in `artifacts/benchmark/phase5/`. Result hash `05bd899641a761f14823de984e14f04ae892f6b40b86f9238a042156744c283d`; evaluated package fingerprint `ea6facd88431e7726e395b97b8f9e10c102bb8fd606d925db67883c8dcb86fed`. Protocol `8feebbfcdebc20f18463a068839bd7125b89a5caae5691c5bbd470e83cca5390` was independently reviewed and committed before evaluation. The old protocol checkpoint and both pre-evaluation amendments remain in Git history.

## Recorded outcomes with synthetic forecasts

172 training tasks, 31 validation tasks and four historical model arms; 44 existing exploratory `test` tasks excluded. No final cohort was provisioned, accessed or run. There are 648 aggregate batch/seed/mechanism rows, not 648 independent empirical tasks.

| Budget interpolation | LMSR mean proxy | Calibrated pool | Paired delta [conditional 95% interval] |
|---|---:|---:|---:|
| Cheapest reservation total | 0.7581 | 0.7581 | 0 [0,0] |
| Halfway to most-expensive total | 0.7097 | 0.7581 | -0.0484 [-0.1452,+0.0333] |
| Most-expensive reservation total | 0.7097 | 0.7581 | -0.0484 [-0.1452,+0.0333] |

At the middle/high budgets the interval spans zero; do not call this significant inferiority. LMSR actually traded: mean 66.33 accepted trades over the 31 tasks per schedule seed, not a one-share inactivity artifact. The full-training text router, cheapest and best-fixed references all achieved 0.7581 in this particular cohort; a weak text model did not create an artificial market win. The analysis-only oracle reached 0.9194 at middle/high budgets, demonstrating remaining headroom, not an attainable causal deployment gain.

At the minimum reservation budget, calibrated pooling's realized historical costs exceeded the batch budget in 6/8 batches (75%). This is not spending by this project: it is retrospective reported cost under mean train-only reservations. It demonstrates why reservation feasibility does not imply a guaranteed real-world hard budget. Middle/high-budget violations were zero in this small sample; no guarantee follows. At midpoint, mean total LMSR realized cost was 73,507,206.67 nanos of reported historical USD versus pooling's 35,529,660; these are neither verified invoices nor actual deployable savings. Virtual market fees/subsidies are reported separately.

Brier accuracy at midpoint was 0.64645 for LMSR and 0.61696 for calibrated pooling (lower is better); reliability plots are descriptive with correlated arms and only 31 tasks. Tie/zero ambiguity sensitivities rescore fixed chosen routes without inventing missing judge status. Exact-prompt grouping does not resolve semantic near-duplicates or source-family dependence. The four-arm complete-case cohort remains selected and single-domain.

## Synthetic generalization

Twenty templates per mechanism/reward condition were enumerated on four development worlds; choices were frozen before 168 paired validation cases (56 nature worlds × three mechanisms). Every declared episode executed; no terminal horizon was excluded. Schedule seed 41 was fixed, so this is nature/information/configuration generalization, not evidence across arbitrary orderings.

Development selected the honest reference for LMSR and static calibrated pooling. Therefore their validation zero utility differences show that this finite sample/class selected no stronger policy; they do **not** certify the absence of other attacks. Interactive pooling selected a delayed partial-bias update strategy. With correlated information its mean utility gain was +1 credit-equivalent utility [0,+2.5]; this interval does not establish a strictly positive expected-profit result. Under fees/weak information the same frozen strategy lost exactly 4 utility units in each validation world. Zero-external searches selected honest policies. All negative and null rows are retained.

No profile/mechanism had a strictly positive lower utility interval, and all mean realized preference-proxy loss differences were zero. This does not prove harmlessness: eight worlds/profile, coarse finite policies and fixed belief dynamics give limited power. Delayed updates keep original proper-score rewards and can exploit the approved unscored-revision structure; any future success would need to be interpreted as that familiar weakness with actual fees/payoffs, not novelty.

The normalized one-versus-two-active-account comparison produced no gain difference here. The registry, private observation, report weights, aggregate cash/caps/token/turn resources and sponsor funding were identical by assertion. Account partition can still fragment liquidity, and this does not model free new identities or pooled heterogeneous coalition beliefs. Those limitations remain explicit rather than disguised as solved general mechanism design.

## What this teaches us, and what remains

The benchmark now distinguishes weak forecast aggregation, integer trade friction, participation funding, external incentives and realization noise. Independent review prevented two misleading designs before evaluation: one-share-only honest inactivity and an interactive attack class that could never update. The pipeline can reproduce ordinary comparisons and failed generalization without selecting impressive outcomes.

It does not determine ideal Bayesian market performance, state-of-the-art routing, real strategic LLM-agent behavior, broad population effects or the transfer of synthetic attacks to recorded tasks. The recorded evaluation here covers honest forecast/allocation comparisons; strategic validation is a separate controlled synthetic track. A reviewed richer policy/information model, larger development/world samples, semantic/source-family grouping and an independently sealed final cohort would be needed for stronger claims. Do not run a final holdout or retune on these validation results under the old protocol.
