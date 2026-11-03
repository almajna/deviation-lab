# Independent evaluation review record

Issue #22 / PR #25. This record distinguishes the independent review of the
evaluation feature from Agent 2's independently authored check of Agent 1.
Neither is external scientific peer review or human release approval.

## Before broad execution

A separate read-only reviewer, with no feature authorship, read the protocol and
existing engine. The initial protocol was published at a3ad273050e12079cc2da5f92e9e755fffedf60d.
The reviewer challenged two ambiguous criteria: which exact comparator to use,
and whether the threshold used a ratio of medians or median of paired ratios.
Clarifications were published at d77e2cd6031b665c082a4412597bf564eab657d1 before
numerical execution: use the faster completed exhaustive/DP baseline per case,
require zero certificate gap and >=2 legal root actions, then take the median
of paired per-case ratios. Timing intervals resample entire seed blocks.

The reviewer also required actual searched horizons for static report games,
fixed-belief caveats and an explicit argument for DP state equivalence.

## Read-only implementation challenge

The reviewer inspected the independent action lattice, economic objective,
allocation DP, endpoint bound, tree checker, fixtures and benchmark code. It
independently repeated a market over two controlled turns to exercise owned
sales and coalition execution. Full enumeration and memoized DP agreed;
both endpoint/fallback upper bounds covered every checked one-step descendant.
It found no mathematical blocker within the supported canonical fixtures.

Two limitations were raised:

1. Arbitrary root histories can reserve future canonical order IDs. Document and
   enforce the trusted canonical-prefix root assumption; hashes are not root
   authentication. This does not extend the checker to arbitrary hostile states.
2. Failure/checker rejection must retain the active case and exception before
   aborting. Earlier checkpoint code recorded only completed cases. Infrastructure
   hardening now writes current_case.json before work and failure.json before
   propagating any failure/interruption. An injected failure regression checks
   the active case and exact error. Canonical-root validation now explicitly
   rejects pre-reserved future order IDs. Neither correction changes legal
   canonical fixtures, optimizer/bound arithmetic, settings or criteria.

The initial complete run is retained under artifacts/verification/initial_run/.
It found no bound violations, 78 zero-gap proofs of 81 and a negative speed result
(median ratio approximately 2.17). This is not discarded or tuned away. Official
integrated evidence is regenerated after the infrastructure corrections. A
secondary ordinary-exact diagnostic requested by Agent 4 is explicitly outside
the original primary speed comparison. All fixture settings remain frozen.

The reviewer agreed the documented telescoping charge lower bound, pooled
endpoint enlargement, minimum fee count, pending-score maximum and future-slot
effort deductions are sound under the stated finite common-belief model.

## Final evidence review

The read-only reviewer independently recomputed the official results without
importing the benchmark summary helpers: 81 unique rows, 78 zero-gap certificates,
75 complete exhaustive and 75 complete DP answers. Every complete exact answer
lay in its certificate interval. All economic/work/check rows match the initial
run after normalizing only source-bound certificate digests.

It independently reproduced all 72 eligible timing ratios, the median
2.1907801380731162, and the 2,000-draw seed-block interval
[1.158893535310708, 2.3821130206129135]. The frozen speed criterion fails. No
certificate incumbent beats beam; 78 tie and three deep interactive cases lose.

In a fresh Python process, it rebuilt all 81 roots and checked/replayed every
official full proof without calling the producer optimizer. Every check receipt
exactly matched the saved independent_check row. It reviewed the failure-recording
and canonical-root changes and found no mathematical blocker within this scope.

Author validation: all 187 tests pass under native Python 3.11.18 and 3.12.15.
A clean wheel installation under isolated Python 3.12 reproduces all deterministic
81-case results exactly; all 81 compressed proof files independently check.
The 20 imported producer code/test/document/artifact blobs were compared with
actual GitHub blob SHAs at producer head 3151edb, all equal; evidence is
artifacts/verification/producer_dependency.json. CI and the decision log are the
only intentionally modified producer-owned files.

## Certificate replay CI correction

Initial draft head a3d85c6 failed run 41596235352 at historical certificate replay:
`Example replay mismatch: small-lmsr.certificate.json`. Adding the independent
package changes the whole-package source hash, so replaying old producer proofs
with the new installed package correctly fails strict byte/source comparison.
No proof is relabeled and no source check is relaxed. CI now archives producer
commit 3151edb for the immutable historical proofs and verifies the new integrated
proofs/results against their current package fingerprint. Rehashed wrong-source
proof rejection remains tested. Final hosted CI and exact-head review are recorded
in the PR once those checks complete.
