# Deterministic economic simulator v0.2

This Phase 2 engine implements the owner-approved interfaces, not a market or an empirical result. Issue [#7](https://github.com/almajna/deviation-lab/issues/7); authorization/pins in `tasks/PHASE_2.md`. Legacy `deviation.core` and its demo are unchanged. New runtime code uses the standard library only.

## Execution and reproduction

From a Python 3.11+ checkout:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out artifacts/simulator/two_task
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out replay-check --verify artifacts/simulator/two_task/receipts.json
```

Or install into an isolated environment with `python3 -m pip install --no-deps .`, then run `python3 -m deviation.simulator ...` without `PYTHONPATH`. Build isolation may fetch the existing free setuptools build requirement; there are no paid APIs or runtime dependencies. The CLI accepts only explicitly SYNTHETIC inputs. No final-evaluation path is provided.

Outputs: `replay.json` conforms to unchanged shared v0.2; `events.jsonl` contains the same ordered events; `receipts.json` contains public configuration/tasks, validated reservation/realized/ledger receipts and post-settlement quality summary; `manifest.json` hashes all three files. The separate `simulator-1` execution envelope is a local reproducibility format, not a revision of the shared replay contract. It hashes the full input and all local Python package bytes, including contracts and data helpers. Replay recomputes with the trusted built-ins and compares all receipts; trusted injected test policies/allocators are explicitly labeled in receipts and are not serialized, loadable from JSON or silently replayed as built-ins.

Private signals and sealed paired stores are not exported. The synthetic scenario input intentionally contains both for trusted offline test construction; it is never a policy packet. Do not package recorded source rows or private signals into a public frontend. Public traces contain no private-signal export extension.

## State, reservations and boundaries

1. Freeze trusted run configuration; fit exact train-only means, ceil at 1e9 scale, then validate the reservation artifact against the approved groups/source/split hashes. Exclude training task IDs and normalized prompt groups from allocation. No held-out fallback or refit.
2. Derive best-fixed quality means from separately supplied quality rows covering exactly the validated training task/model pairs. Input provenance is trusted, not authenticated by hashes.
3. Sort tasks/agents by ID. Give each agent a fresh deep copy of the allowlisted task, own synthetic signal, fixed reservations, current credit balance, configured fee and earlier public forecasts for this task only. All reports precede allocation; budget remaining is therefore the full unchanged reservation budget during reporting. No outcome or foreign private-signal argument enters a policy or allocator.
4. Validate each action against its original packet. Reserve each fee in authoritative credits immediately; insufficient credits fail the run rather than silently dropping agents. Frozen reports and reservations feed the allocator. Validate the complete allocation before emitting reservation events.
5. Only after that barrier validate/access the complete sealed paired store. Reveal selected historical costs, rounding each positive decimal upward to nanos, and selected quality. Retrospective violations are reported, never hidden by rejecting an expensive completed allocation.
6. Post the already-reserved fees once, followed by explicitly configured funded illustrative settlement transfers. Validate all balances/utilities and emit post-settlement receipts. No outcome-dependent scoring rule, market-price dynamics, attack search or incentive claim is implemented.

In-process policies are trusted local code. Deep copies prevent ordinary state aliasing; they do not sandbox malicious Python, prevent file/global access or authenticate source data. Untrusted policies require a separately reviewed isolation layer. Synthetic signals are exogenous hand-authored imperfect forecasts; the engine does not derive them from current-task truth. Future signal generators need explicit reviewed noise/correlation assumptions.

`prepare_records` integrates the existing paired `OutcomeRecord` loader and validated Phase 1 exploratory split manifest. It derives training cost/quality rows and sealed decision rows without downloads. It rejects final split names and unsupported estimated-cost semantics. Float costs already parsed by Phase 1 retain that precision via `str(cost)`; the adapter cannot recover original source decimal bytes. No real-data fit/run is performed in this PR.

## Reference allocations and oracle

All references use identical tasks, fixed reservations, budget and units; unallocated tasks explicitly abstain at zero cost/score. They differ in allowed decision strategy, never hidden outcomes:

- `random`: a local seeded RNG shuffles tasks, then picks uniformly among currently reservation-feasible arms. This is not uniform over all feasible allocations; it never alters global RNG state.
- `cheapest`: sorted tasks, cheapest feasible arm; deterministic model-ID ties.
- `best-fixed`: training-only mean quality times the affordable number of eligible tasks selects one fixed arm; ties favor lower reservation then model ID. Fill eligible tasks in ID order, abstaining when unaffordable/unavailable. It is a trained fixed-arm reference, not a hindsight best model.
- `cost-aware`: arithmetic mean of each task's validated synthetic reports, then exact sparse multiple-choice knapsack maximizing expected preference proxy with abstention. Score ties favor lower total reservation; remaining ties use deterministic traversal. A 100,000-frontier-state limit fails explicitly, without a silent approximation.

`evaluation.offline_oracle` accepts sealed quality only in separate offline small-case analysis, at most 12 tasks. It uses the same reservation constraint, never realized costs as decision weights, and labels output `OFFLINE_ORACLE_ONLY`. It is not a registered live policy and is not automatically executed. An independent product enumeration in tests checks the optimizer across seeded small cases; the oracle is not the sole reference for testing its own optimizer.

## Hand-computable synthetic sample

Training means reserve model a=200 and b=300 nanos. Task forecasts (a,b) are (0.8,0.6) and (0.3,0.9), budget 600. Cost-aware chooses a then b, reserve 500. This choice maximizes forecast sum 1.7; choosing b/b scores 1.5. Selected synthetic realized costs are 700 and 200: total 900, positive overruns 500, unused reservations 100, net overrun 400, budget excess 300. Realized proxy scores are 0.5 and 0.5; the imperfect reports do not equal outcomes.

One synthetic agent starts with 20 virtual credits and pays two fees of 2; a declared illustrative transfer of 6 from maker gives final credits 22. Cash delta 2 plus external utility 3 minus noncash effort 1 gives utility 4. Fee sink ends at 4; maker starts at 50, ends 44, P&L -6/loss 6. Total credits remain 70. These are separate from nano-cost quantities and are not market performance.

The generated sample is distinct from the original hand-authored Gate A conformance fixture, which has one fee and a different declared utility. Both validate under the same unchanged contract. No sample establishes superiority, objective coding correctness, verified bills, actual savings, deployment hard budgets or real autonomous economic agents. The 247-task pool remains exploratory; all original Phase 1 evidence remains unchanged.
