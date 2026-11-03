# Phase 4 technical research note

## Result and scope

The implemented instrument searches the actual approved Phase 3 engine and reproduces a conditional externally rewarded allocation distortion. It does not establish a new economic theorem, novel vulnerability, market inferiority, empirical superiority or an autonomous LLM exploit. All tasks, participants, beliefs and outcomes here are synthetic. The empirical 247-task / 988-outcome cohort and untouched final holdout were neither read nor evaluated.

Protocol: `experiments/adversarial_protocol.json`. Results: `artifacts/attacks/phase4/campaign.json`; complete selected counterexample: `artifacts/attacks/phase4/selected/`. Source fingerprint: `368485d0af592ea1c0359ffba5c9f6de0710e6342142208d91d778983a7c3e30`. Selected evidence: `73f2f744c933d7e6bacace603758ab3d06646ca551b9f20ff1f327829a77a34b`.

## All-case accounting

The declared grid contains 216 cases: eight schedule seeds, nine resource/belief profiles, three mechanisms. Of these, 148 have a supported information-safe horizon; 68 are explicitly `NO_CONTROLLED_TERMINAL_SUFFIX`, not successes or nulls. There are 128 completed exact finite-subgame searches and 20 bounded beam results. Twenty-one evaluated cases meet the neutral verified-redirect criterion; four also reduce environment-expected preference quality.

| Phase | Declared | Evaluated | Verified redirects | Harmful verified redirects |
|---|---:|---:|---:|---:|
| Known pilots (7,17,31) | 81 | 63 | 20 | 4 |
| Replication (401,503,607) | 81 | 49 | 0 | 0 |
| Post-review replication (811,907) | 54 | 36 | 1 | 0 |

All four harmful cases occur at known-pilot seed 7. There is **no harmful replication in the fresh configuration grid**. Shared-error pool/interactive-pool and independent-error pool account for the other three harmful pilot cases. Sixty-six evaluated cases are ordinary-trading/reference-not-beaten; 61 are no-profitable-deviation-found. Report every row and method; do not present 4/148 as a population failure rate, and do not treat the grid as independent statistical samples. The fresh seeds are exploratory synthetic replication, not the project's final empirical holdout.

## Hand-checkable searched counterexample

Selected case: `known_pilot-7-costly-lmsr`. Two tasks, two models; categorical denominator 3; liquidity b=3; fee=2; maximum order coordinate 2; attacker initial capital 8; reservation budget 4; one remaining controlled trading slot. All 10 admissible finite actions were evaluated (11 visited nodes). The selected command buys `[0,0,2]` shares in the task-1/m1 market, with maximum net debit 3. The actual engine accepts it, transfers charge 1 to the maker and fee 2 to the fee account, then freezes allocation. Two shares have expected payout 2/3 under the calibrated attacker/environment belief.

Both honest and no-action references allocate `(task-0:m0, task-1:m0)`, reserved cost 2. The selected trade changes task 1 to m1, reserved cost 3, within the same pre-decision budget. The controller values that selection at 6 utility units; this is a declared private external preference, not a cash transfer or observed real-world benefit.

| Quantity | Honest/no-action | Selected | Difference |
|---|---:|---:|---:|
| Expected net cash profit | 64 | 185/3 | -7/3 |
| External allocation utility | 0 | 6 | +6 |
| Expected total utility | 64 | 203/3 | +11/3 |
| Environment-expected summed preference proxy | 4/3 | 2/3 | -2/3 |
| Realized net cash profit | 56 | 55 | -1 |
| Realized total utility | 56 | 61 | +5 |

The common expected funded score of 64 cancels; it is not attack profit. Fees are included once. Therefore expected incremental utility is `-3 + 2/3 + 6 = 11/3`. Expected quality loss is `2/3`, while **realized proxy loss is zero** in this frozen realization. This distinguishes ex-ante incentive from realized luck and identifies an externally incentivized distortion rather than profitable cash-only trading. Exact search with the external reward removed selects no action and gains zero. Maker/scoring funding and cash conservation hold in all six receipts.

The mechanism is not deliberately disabled: certified charges, honest competitors, proper funded scoring, real fees and caps are active. The weakness is the familiar dependency of decision-relevant prices on an agent with an external allocation preference, under discrete prices/orders and terminal priority. It is not evidence of novelty or a generic failure of prediction markets. The opportunity depends on a marginal allocation, sufficient spendable capital, an accessible terminal slot and enough external benefit.

## Exploratory conditions where it disappears

`artifacts/attacks/phase4/sensitivity.json` reoptimizes 21 one-variable interventions on the selected case; these are post-selection analyses, not replication. Reward 0,1,2 yields no profitable redirect; 3,6,12 permits one. Capital 0,1,2 yields none; 3 and 8 permit one. Global action caps 0 and 1 eliminate the optional opportunity. At zero fee the honest prefix changes and there is no additional profitable deviation; fee effects are not monotone because the prefix and integer rounding change. b=1,3,20 all retain a redirect in this selected family, so liquidity alone is not demonstrated as a cure. The same selected plan without the reward loses 7/3 expected cash; broader search does not return negative gain because no-action is an incumbent.

## Limits and confounders

Exactness applies only to the declared terminal suffix/final-report subgame and finite action bounds. Beam outcomes are lower bounds on best attainable utility, never global certificates; search caps and unsupported horizons restrict discovery power. The game does not solve strategic unknown future honest behavior. Static report controls assume a publicly announced report model and have a different horizon/action space from markets. Calibration assumptions are explicit; exogenous correlated errors are not a likelihood-based signal channel. Synthetic public generator seeds are not secret; the misspecified regimes model prescribed subjective beliefs, not full Bayesian conditioning.

Aliases share fixed controller resources and coordinate, but each comparison keeps a pre-registered registry. Across registry sizes, sponsor reserve and turn opportunities can change. No causal claim of profitable identity proliferation is established. Coalition belief pooling, endogenous identity creation, richer opponent uncertainty, multi-round learning and repeated-game reputation remain future work. Sponsor payouts can dominate absolute utility but cancel in matched comparisons. The independent environment law supplies expected welfare/payoffs after strategy selection; it is not supplied to the attacker. The selected calibrated case has equal actor/environment beliefs, avoiding a subjective-profit-only claim.

An early campaign was invalidated after independent review found that the correlation flag did not correlate honest/controller errors. The generator was corrected with shared and separate RNG streams and regression tests; those discarded receipts are not committed or counted. A separate hidden-realization RNG and outcome-free public provenance closed a potential seed-reconstruction leak. The final campaign was regenerated after source freeze. The retained pilot/replication labels do not erase model-development or case-selection bias.

See `ADVERSARIAL_LAB.md` for commands and `PHASE_4_REVIEW.md` for independent challenge evidence. The next scientific step is a reviewed broader information/opponent model with normalized registry/funding comparisons; no final holdout or superiority experiment is authorized by this implementation.
