# First bounded research cycle

Issue [#26](https://github.com/almajna/deviation-lab/issues/26), implementation [PR #27](https://github.com/almajna/deviation-lab/pull/27). All cases are **SYNTHETIC DEVELOPMENT**, with prescribed beliefs and simulated strategic actions. No live LLM-agent decisions, recorded benchmark task rows, final holdout or paid inference are used.

## Registration and original failures

Original questions, success/failure criteria, seeds and baseline grid were published before execution at `ce59d6d4074f93b51ed27207144343594d68650d`. The first isolated run exposed adapter schema errors; its full bounded capture and summary remain in `artifacts/research/initial/`. The second run reproduced bound/aggregation results but stopped the fee job on an unsupported terminal horizon; that capture and summary remain in `artifacts/research/second/`. Infrastructure fixes did not change the frozen seeds or scientific criteria.

Independent review identified that integer rounding made the original unit-buy charges all equal one. The separate, stronger 21-transition signed diagnostic was published before its execution at `833df7748f7601df4d182375d9c6c3a960057bb3`; the original 243 cells and all three directional criteria remain intact. Later classification fixes preserve an observed counterexample even when other declared cells are unsupported.

## Actual findings

| Investigation | Executed scope | Finding | Interpretation |
|---|---|---|---|
| Published LMSR mathematics | 243 original unit-buy cells and 21 separately preregistered signed/multi-share transitions | High-precision cost differences, signed-ceiling charges, subsidy arithmetic and certified intervals agree; signed charges include negative, zero and positive values | Scoped standard-method reproduction, not full-paper replication or novelty |
| Fee sensitivity | All 18 cells attempted; 12 supported, six independently confirmed unsupported seed-29 horizons | Seed 13/external reward 6 has optimal gain over no action of 0, 13/3, 7/3 at fees 0, 2, 4. Evaluated zero-external controls have zero gain | Monotonic suppression criterion **rejected on evaluated cells**, with partial coverage. Fees also change the honest prefix; no isolated causal claim |
| Bound ablation | 12 solver configurations across six unique games | Endpoint root bounds strictly improve fallback bounds in all six games; every complete certificate agrees with independent exhaustive and memoized-DP optima | Known relaxation behavior reproduced; no speed, scaling or algorithmic-novelty claim |
| Correlated forecast errors | 36 matched runs: three seeds × two perturbation settings × six mechanisms | Mean total selected proxy for pool minus LMSR is 0 under independent perturbations and −1/6 under shared perturbations; shared paired differences are 0, 0, −1/2 | Registered pooling criterion **rejected** on this tiny fixture; no population or deployment inference |

All 24 supported fee/bound certificates are checked by Agent 2's separately implemented checker. Exact/DP and beam command witnesses are replayed; signal-following and no-action controls are verified independently of the producer optimizer. Rational subjective utility, cash, external benefits, effort, allocation, fees, maker/scoring subsidies, reservations and realized synthetic proxy remain inspectable. Unsupported cells have no invented numerical result.

## Evidence and replay

The sample in `artifacts/research/mvp/` was executed at source `397bdcc273c143c4b5991d2f900aa6ed0dd51453` in [CI run 41695709909](https://github.com/almajna/deviation-lab/actions/runs/41695709909), job `126125547763`. All three source-head workflows passed. The research workflow passed real network/filesystem isolation tests, the four-job cycle and fresh-process byte-for-byte reproduction of every scientific result, review and event.

The 22 actual sample files include frozen full inputs, preregistration, original online scout receipts, per-experiment plans/results/reviews, measured worker/reviewer resource receipts, summary and the 54-event hash chain. `artifacts/research/PROVENANCE.json` binds every retained capture, input, result, review and resource receipt. Timings are observed measurements outside deterministic equality checks. Original evidence was recovered directly from CI after the previous workspace went offline; an independent reviewer recovered a separate copy and compared every sample byte.

The online capture made 12 public metadata requests: nine succeeded and three Semantic Scholar requests returned HTTP 429. Failures remain visible. The eight source-registry bibliography identities were checked against primary sources again on 2026-11-03; `citation_review.json` records those links and the distinction between an abstract/identity check, an algorithm reproduction and semantic novelty assessment.

```sh
python -m pip install --no-deps .
DEVIATION_REQUIRE_SANDBOX=1 python -m unittest discover -s tests -p 'test_research*.py' -v
python -I -m deviation_research reproduce --evidence artifacts/research/mvp --out /tmp/research-reproduction
python -I -m deviation_research cycle --online --memory /tmp/research-memory.sqlite --out /tmp/new-research-cycle
python -I -m deviation_research inspect --memory /tmp/research-memory.sqlite
```

Linux execution needs working bubblewrap user/network namespaces. Both previous local nested-sandbox setup and this resumed container's extra network namespace are denied by their hosts. No unsafe fallback was used; real isolated experiments and reproduction run in the passing GitHub Ubuntu 22.04 job. Unit/independent numerical checks can run separately. Worker receipts distinguish self CPU/peak RSS from reaped-supervisor CPU; unavailable measurements after a hard kill remain null. CPU, wall, address-space, file and output limits remain unchanged.

## Independent challenge and scope

See `docs/RESEARCH_HARNESS_REVIEW.md`. A separate read-only reviewer authored no feature code, verified published Git trees and original CI bytes, recalculated 243+21 LMSR checks at 100-digit precision, verified all 24 certificates with producer optimizer/Game payoff/allocation disabled, confirmed six unsupported cases and independently recomputed negative fee/correlation arithmetic and the 54-event chain. Their challenges produced regression tests for forged/duplicate grids, altered profiles/comparators, cosmetic and seed-order retries, interrupted workers, source binding, failure retention and incorrect incomplete-grid classification.

The MVP ranks and validates authored research templates. Newly retrieved metadata is remembered; it does not automatically produce new semantic hypotheses, prove prior-art absence or authorize arbitrary downloaded/generated-code execution. Supporting a new experimental family requires a reviewed adapter and preregistration. Reusing memory skips already-reserved identities, including failures. Changing a title, rank or seed order cannot silently repeat the same science.

These are reproducible infrastructure and small synthetic findings. They establish no breakthrough, general market advantage, actual LLM economic behavior, full-game incentive compatibility or deployment savings. Independent agent review is not external peer review or a separate human GitHub approval. Next action: owner review of this bounded harness and a deliberately selected new adapter/question, preserving all negative findings and information boundaries.
