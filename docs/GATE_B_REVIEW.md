# Independent adversarial review — Gate B design

Issue: [#11](https://github.com/almajna/deviation-lab/issues/11). Date: 2026-11-02 Pacific. Reviewer: separate `gate_b_review` agent, read-only and not a feature author. Verdict after corrections: **PASS for design-level proposal**, with no remaining blocking scientific/mathematical finding. Exact published-head clean-export review and hosted CI are recorded in the PR. Owner exact-head approval and human merge remain required; this agent verdict does not provide either.

## Challenges, corrections and evidence

| Adversarial challenge | Resolution |
|---|---|
| Arbitrarily rounded proper-score payouts could cease to be proper | Reports use n/D and K=2D²k, giving exact integer scores. Tests verify the expected-score gap over every D=10 report, unique representable optimum and a two-optimum off-grid case. Propriety is conditional one-shot mathematics, not a full-game theorem. |
| Credits alone did not define equal resources; aliases might multiply rewards | Separate named scoring reserve and per-cell makers; fixed controller-level cash, score tokens/subsidy, action/position limits and aggregate external λ. Report all actual/unused resources and matched-budget sensitivity. No general Sybil-resistance claim. |
| Maker solvency/refunds needed precise signed rounding and state conventions | q is aggregate owned long-only claims, charge is signed ceil(ΔC), fees go elsewhere, and every cell is funded independently. The derivation proves cash≥max(q); tests cover each resolution, reversal, full sets and nonnegative state paths. |
| A supported all-decline action left pooling undefined | Empty cells deterministically use uniform; each identity has one current message, no-op retains it, late entry requires an assigned slot without new score tokens. Added aggregation conformance cases. |
| Source-bound historical receipts cannot match changed future package bytes | Preserve historical evidence at its pinned source; after approval a separate implementation PR must introduce current-source versioned artifacts/CI and replace this design-only source-freeze assertion. Fingerprint checks must never be disabled. |
| Attacker search might choose actions using hidden labels/future signals | Last-slot search uses its own declared belief, public post-trade allocation and fixed controller utility. Earlier-turn search without an allowed future-behavior belief model is disabled; hindsight optima remain oracle analysis. Distinguish expected incentive gain from realized luck. |
| Mean proxy, probability, labels and honest policy were liable to conflation | Three recorded categories preserve zero ambiguity; marginal prices map to expected preference, not correctness. Signal-following is distinct from a posterior conditional on public history; no unique v0.2 mean→distribution migration exists. |
| Proposed action bodies lacked explicit dispatch | The inactive index now names kind/stage discriminators. The trusted runner must reject mismatched dispatch; active v0.2 still rejects proposed events. |

The reviewer independently ran the initial 93-test suite, then the updated 95- and 96-test suites while challenging the draft. It checked hand-specified fixtures, the full Gate B/event documents, proposed index, supporting research/status/decision changes and math tests. Final worktree verdict reported **96 tests passing** and no unresolved blocker, including the explicit training-only temperature control and identity ablation. No runtime, active-contract, frontend, README or license edits were observed. No mechanism, real-data experiment or final holdout was executed by the reviewer.

## Reproduction and preserved behavior

With Python 3.11+ from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p test_gate_b_spec.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/check.sh
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out replay-check --verify artifacts/simulator/two_task/receipts.json
git diff 9899618a72cc5df9cc18980ad58d9bd4381b1bf7 -- src apps/web schemas/contracts-v0.2.json tests/fixtures/contracts_v0_2.json artifacts README.md LICENSE .gitignore
```

The final diff is empty. Existing simulator receipt SHA remains `9abd80c9628d4f3030522f79904662adc109f23deefc1ec5a6c22e0f4dcf3c83`; full-package bytes and all original Phase 1 evidence are unchanged. New fixture `tests/fixtures/gate_b_math.json` is explicitly hand-specified synthetic mathematical cases, not executed market logs or scientific results.

## Scope and remaining limits

This is adversarial agent review, not external peer review, a separately authenticated GitHub approval, a certified numerical implementation or evidence of market value. High-precision example arithmetic does not certify arbitrary quote intervals. Runtime closed validators, stage/privacy boundaries, atomic accounting, numerical enclosures, deterministic full market replay and compatibility dispatch must be implemented and independently tested only after Gate B approval.

The signal generator, coherent posterior corpus, earlier-turn attacker belief model and final evaluation remain later protocol obligations. Long-only positions, finite wealth, quantization, fees, external incentives and artificial sponsorship invalidate unrestricted truthfulness/incentive-compatibility claims. Live selected-only settlement is outside scope. No scientific superiority, correctness, verified billing, deployable savings or hard real-world budget claim is approved. Spend $0; no automatic merge.
