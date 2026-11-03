# Backend integration and reproduction

Tracking issue: [#28](https://github.com/almajna/deviation-lab/issues/28).
This combines #19, #23, #25 and #24. It is not a release or a scientific novelty,
market superiority, general speedup or successful LLM-manipulation claim.

## Reproduce

From a full-history checkout of this branch, Python 3.11 or 3.12:

```sh
python -m venv /tmp/deviation-integration-env
. /tmp/deviation-integration-env/bin/activate
python -m pip install --no-deps .
python -m pip install matplotlib==3.10.7
python -m unittest discover -s tests -v
python -I -m deviation.attacks.certified verify artifacts/attacks/certified/scenario.json artifacts/integration/example.certificate.json
python scripts/audit_integration_statistics.py --out /tmp/deviation-statistics.json --verify artifacts/integration/independent_statistics.json
python -I -m deviation_integration \
  --cache /tmp/deviation-audit-cache --download \
  --out /tmp/deviation-combined-reproduction --plots \
  --verify artifacts/integration/manifest.json
```

The output folder must be new/empty. With a populated checksum-verified audit
cache, omit `--download` for offline execution. Omit `--plots` and its dependency
for standard-library numerical reproduction; the numerical manifest is identical
with or without plotting. Local Git history must include all pinned commits
(`fetch-depth: 0` in CI). Missing history is an error, never a source fallback.
The installed entry point operates on the current repository checkout.

No model weights, inference runtime, API key or paid service is needed. The only
optional request is the existing bounded exploratory data download. There is no
final/test-split or inference option. Integration CI has no automatic inference
fallback; missing observed transcripts fail explicitly. Existing local-model
adapters remain available for separately approved experiments.

## Evidence boundaries

- `preservation.json` checks original Git blobs for all upstream artifacts,
  experimental protocols, runtime modules, shared contracts, mathematical
  derivations, README and license. Original observations/proofs are never relabeled.
- Historical simulator/market/attack receipts, all producer proofs, the full
  Phase 5 benchmark, all 81 independent certificate cases, archived proofs,
  ordinary exact comparator, scripted controls, observed pilot, six-row summary
  and publication audit replay at their exact pinned source. Original strict
  verifiers remain unchanged.
- The installed combined package regenerates every research track. Every old
  scientific value, information hash, event, allocation, payoff and proof-tree
  node must match. Only explicitly declared source-dependent digest fields can
  change; `rebindings.json` records every changed path and both values.
- The integrated manifest strictly binds complete deterministic outputs, all
  81 new proof files and the integration implementation. Compatibility comparison
  supplements strict original-source and current-output verification.
- Original LLM calls are verified at original source, then `RecordedPolicy`
  replays exact packet/prompt/action contexts through the combined engine. New
  receipts say `RECORDED_DECISION_REPLAY`, with zero new inference calls. Original
  live evidence and scripted control provenance remain separate and untouched.
- Published timing statistics are recomputed from original measured samples.
  New execution times are diagnostics, not replacements for historical timings.
  Optional figures regenerate with input/script/output bindings; graphical bytes
  can depend on the platform and stay outside the numerical manifest.

Each subprocess writes a log and step receipt. Failure writes `FAILURE.json`;
success writes `SUCCESS.json` with the strict manifest digest. These receipts
qualify reproduction, not release. Regression tests connect certified attack
commands, actual engine transitions, Agent 3 metrics, independent payoff checking
and the evaluation ledger auditor. They also cover sealed information, old-source
rejection, recorded-decision tampering, initial negative results and plot-flag
manifest invariance.

## Recovery and scientific limitations

The earlier Mac workspace disconnected before its integration patch/manifest was
pushed. The existing remote integration branch contained exact #23/#25 history.
This cloud continuation recovered that branch, merged the existing #19/#24 heads,
restored only the missing integration layer from the previous session, and reran
verification. Earlier Mac runs are historical evidence, not final-tree cloud CI.

Phase 5 remains exploratory: 31 recorded validation tasks, 168 paired synthetic
cases, weak predictors and conditional intervals; no demonstrated LMSR advantage.
Retrospective costs can exceed reservations; there is no deployable hard-budget
or verified-dollar-savings guarantee. Certificate evaluation has 81 checked cases,
78 zero gaps and six capped exact baselines. Three deep interactive-pool gaps
remain unresolved. Its frozen general speed criterion fails (published ratio
about 2.191); no general attack-discovery advantage or economic novelty follows.
The actual CPU pilot made 24 calls: two valid chosen no-ops, 22 invalid responses,
zero reports/trades. Replaying it does not resolve capability failure or establish
strategic behavior. Certificates assume canonical prepared roots, controlled
terminal/report opportunities and shared trusted Engine/numerics. This integration
proves compatibility, not a stronger mathematical theorem or real-world validity.

The final cohort is neither provisioned nor accessed. Broader assumptions, richer
inference experiments, final evaluation, frontend readiness, independent human
review and release approval remain separate gates. No merge or paid spending.
