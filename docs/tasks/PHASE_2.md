# Phase 2 — Codex execution brief

Issue: [#7](https://github.com/almajna/deviation-lab/issues/7). Branch: `codex/economic-core`, isolated worktree. Owner: Codex core worker; independent reviewer does not author code.

## Authorization and pinned inputs

The owner explicitly approved v0.2 commit `a0449c9add2ee3aeb1741d48d41e725d5e8db261` for limited engineering development. PR #6 is merged; that commit is an ancestor of synchronized main `cb4fb585171f4dde371e4dfa4319d21e9ca70bc1`. Approved-head CI run `41549422392` and merged-main CI run `41549521955` passed. This satisfies Gate A, not the later scientific or release gates.

Read `AGENTS.md`, `docs/prompts/02_core.md`, `docs/IMPLEMENTATION_HANDOFF.md` and the approved contracts. Shared files remain read-only:

| File | SHA-256 |
|---|---|
| `src/deviation/contracts.py` | `dcd175fd35452cff07380eaca85dd7cbc5b6257709892d50356175e551bbe000` |
| `schemas/contracts-v0.2.json` | `15424b8232b455fd903dfffbbdac81ca3d189c1e766f2d728eb799df9fafcf06` |
| `tests/fixtures/contracts_v0_2.json` | `8aae9c65a592f1e3d0c80ca27accf78eefad5efd8f04705310dc50111ab03a5e` |

## Ownership and implementation

Own `src/deviation/simulator/`, focused simulator tests/fixtures/artifacts and implementation/status/decision documents. Use a separate `simulator` namespace because a `core/` package would shadow the legacy `core.py`; preserve that file and its CLI exactly. Do not modify approved shared contracts, schemas, the frontend branch or original Phase 1 artifacts.

Implement deterministic train-only reservation fitting, paired-record preparation, allowlisted copied per-agent information, synthetic signal reporting, public histories, seeded reference allocations, explicit abstention, settlement barrier, realized diagnostics and virtual-credit accounting. Fees are reserved in authoritative credit state at each action and posted exactly once to the completed ledger. Fixed funded illustrative payouts/utility parameters test accounting only; actual market/proper-scoring settlement remains Gate B.

Baseline definitions, limitations and artifact commands are in `docs/SIMULATOR.md`. No oracle may be registered as a live allocation policy. No cross-fitting, hidden-cost refunds, training-group decisions, final holdout experiment, training run, paid inference, merge or publication.

## Required proof

Full suite/CI, independent exhaustive small-case allocation comparisons, hidden-quality/cost mutation invariance, recipient-specific private signals/history, copied state, exact budget/abstention/rounding, training-only receipt and baseline parameters, action permissions, funded conserved ledger and no double fees. CLI must work after isolated installation. Repeat execution must write byte-identical public trace, JSONL, receipts and manifest. Independent reviewer must challenge the exact PR head before human review/merge.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out artifacts/simulator/two_task
PYTHONPATH=src python3 -m deviation.simulator tests/fixtures/simulator/two_task.json --out replay-check --verify artifacts/simulator/two_task/receipts.json
```

Keep reproduction output out of unrelated directories in Git; only intentional synthetic sample artifacts are committed. The CLI is synthetic-only. Data adapter support is engineering capability, not evidence of an empirical experiment. $0; human merges only.
