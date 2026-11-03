# Independent certificate implementation review

Issue #20. Reviewer `certificate_review` was a separate read-only agent and did not author the feature. This is an agent challenge, not external peer review, a distinct GitHub reviewer identity, owner scientific approval or merge authorization. Agent 2's separately implemented checker/benchmark in #22 remains a distinct deliverable.

## Findings and responses

- **Medium: exhausted static report slots.** The inherited `Game.complete_reports` rejected a forced no-op's real `ACTION_LIMIT` result, making a valid action-limit-zero report game fail. The additive certificate harness now consumes those exhausted opportunities with their real rejection events and effort. It never fakes acceptance or changes the existing engine/search. A dedicated regression and the reviewer's separate probe pass.
- **Identity binding.** Existing observation omits the selected `Game.controller` field itself, though much of its state is reflected indirectly. The certificate now binds controller explicitly, and checker compares it with the trusted game.
- **Scalability and novelty.** Full state/event-history copying, atomic action-family expansion and checking costs prevent interpreting an expansion cap as a wall-time/peak-memory cap. Branch and bound/proof logging and outside-incentive attacks are known. Documentation now confines the contribution to the engine-specific endpoint bound and independently checkable finite gap; it reports the larger unresolved gap and cases without pruning improvement.
- **Checker independence wording.** Checker does not invoke search/optimizer payoff; the existing parent package still imports search at initialization. The trusted base includes the common mathematical bound, engine, allocator and numeric primitives. Agent 2 is asked to independently reimplement the bounding logic rather than reuse it.

No remaining material soundness finding was identified at the reviewed package fingerprint below. This is limited assurance, not a universal proof of software correctness.

## Executed evidence

The reviewer independently ran the full source suite on Python 3.12: **162 tests passed**. The reviewer also used separate exhaustive economic probes: 20 supported LMSR/interactive games with 2,496 recursive states, and 120 categorical cells with 167,788 sequential paths including purchases, sales/refunds, fees and round trips. No endpoint/fallback upper-bound violations were found. These were one-off reviewer diagnostics; committed regression tests and the separate Agent 2 benchmark provide the durable repeatable checks. They are not statistical samples or an empirical failure-rate estimate.

Rehashed malformed certificates with missing/duplicate edges, cycles, fake bounds, noncanonical rationals and unreachable nodes were rejected. Source mutation during early review correctly caused `CERT_SOURCE` rejection; this was expected concurrent editing, not waived verification.

Clean snapshot and installed reproduction passed under Python 3.11:

```sh
python -m pip install --no-deps --no-build-isolation /tmp/certificate-review-snapshot
python -I -m deviation.attacks.certified examples \
  --out /tmp/certificate-review-installed \
  --verify /tmp/deviation-certified-attacks/artifacts/attacks/certified
python -I -m deviation.attacks.certified verify \
  /tmp/deviation-certified-attacks/artifacts/attacks/certified/scenario.json \
  /tmp/deviation-certified-attacks/artifacts/attacks/certified/small-lmsr.certificate.json
```

The installed import resolved to the review venv's site-packages. All eleven deterministic files reproduced byte-for-byte; standalone checker returned `[203/3,203/3]`, gap zero. Full installed suite: **162 tests passed**. An initial Python 3.12 build environment lacked setuptools; that failed setup is excluded from successful installation evidence.

Reviewed package source fingerprint: `b016e0178a67cc9834c0c6f6c409568de6df31e4b95baa5e95a61655152aef75`.

Example summary digest: `267bc0f74059ed404f21d6ddd1e023d28d6caba75d7eb22dbf4e53812ddc86f4`.

Published source checkpoint: `9f2844e2f6b63c3d11618fdda9051e0b300578bd`. Final exact-head/hosted-CI evidence is recorded in the PR to avoid a self-referential commit hash.

## Residual limits

Reviewer and implementer share model family and source materials. Probes reuse the certified quote engine, so defects in trusted numerical/transition logic can be shared. Certificates establish subjective utility bounds in the declared finite subgame, not truthful equilibria, actual LLM behavior, harmful held-out transfer or deployable cost savings. The larger fixture remains unresolved. Human review/merge is required; final holdout was not accessed and no money was spent.
