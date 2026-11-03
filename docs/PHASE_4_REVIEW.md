# Phase 4 independent implementation challenge

Issue #15. A separate read-only agent (`phase4_redteam`) reviewed the implementation without authoring it. This is independent agent challenge evidence, not external peer review, a distinct GitHub reviewer identity, owner scientific approval or merge authorization. Exact final-head review and hosted CI links are recorded in the PR to avoid a self-referential commit hash.

## Findings and corrections

- Correlation treatment initially did not share errors across controller and honest forecasts. Reviewer reproduced the defect; generator now uses shared errors in the correlated treatment and separate streams otherwise. Other configuration/outcome streams are invariant to this switch. The initial campaign was invalidated and excluded.
- A public seed could reconstruct hidden synthetic draws. Realizations now use a separate evaluator-only seed; public source provenance excludes that seed and hidden labels. The full frozen input is bound for post-run replay only. Tests and reviewer compare the entire search certificate across distinct realization seeds, not merely the selected action.
- Prevented uncertain-future leakage by enforcing an all-controlled terminal suffix and a publicly announced opponent model for the final-report game. Incorrect report models are executed but cannot receive verified status. Other controllers' private external preferences are masked.
- Clarified incentive attribution, realized versus expected harm, prescribed belief-error semantics, fixed-registry alias limits and nonidentical market/aggregation action opportunities. Harmful cases occur only in known pilots; fresh configurations provide no harmful replication.

## Independently executed checks

The reviewer ran all 140 tests under Python 3.12, replayed the final selected bundle, independently enumerated admissible terminal trades with `inspect_order`/`Engine.apply`, and independently recomputed payoffs for all six receipts with separate algebra rather than trusting `Game.expected` or the search certificate. The final selected finite game has 10 actions and optimum expected gain 11/3; an earlier two-slot check independently enumerated 100 leaves. Recomputed expected cash loss 7/3 plus external gain 6, expected preference loss 2/3, realized gain 5 and realized preference loss zero. Cash conservation held.

Reviewer probes changed sealed labels/costs, varied the private realization seed, checked correlation and invariance, supplied a false public report model, inspected private preferences and future-action boundaries, and challenged whether ordinary trading/registration funding could explain the claims. The final-source replay matched evidence `73f2f744c933d7e6bacace603758ab3d06646ca551b9f20ff1f327829a77a34b` and implementation `368485d0af592ea1c0359ffba5c9f6de0710e6342142208d91d778983a7c3e30`.

A clean independent Python 3.12 installation from a separate source snapshot passed: the reviewer imported site-packages under isolated mode and reproduced all 27 selected artifact files byte-for-byte. Final committed-head review is required before the delivery PR is called complete. Commands are in `ADVERSARIAL_LAB.md`; the PR records the actually verified head, results and CI run. An obsolete Python 3.9/setuptools environment produced an invalid empty UNKNOWN wheel during reviewer setup; that attempt is discarded, never counted as installed evidence. Python 3.11+ and a modern build backend are required by pyproject.toml.

## Residual limitations

This reviewer shares the same model family and source materials as the implementer; it is not an independent laboratory. Exhaustive optimality is local to finite declared subgames. Shared code in transition execution can share bugs even when payoff algebra is separate. Synthetic priors, objective choices, known-pilot selection, coarse grids, bounded beam search, unsupported terminal horizons and public opponent-model assumptions limit inference. No external economic novelty, real-agent behavior, empirical holdout performance or research superiority is established. Human review remains required; agents must not merge.
