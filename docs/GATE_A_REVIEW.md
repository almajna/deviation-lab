# Independent Gate A engineering review

Issue: [#5](https://github.com/almajna/deviation-lab/issues/5). Date: 2026-11-02. Verdict: **APPROVE — engineering proposal only**, after corrections. Owner contract approval, repository-settings approval and human merge remain pending.

## Scope and independence

The separate `data_scientific_review` agent inspected actual source, synthetic fixtures, tests and scientific/governance documents, ran checks, and returned findings without authoring or modifying the feature. The integrator implemented the corrections. Review used the existing worktree, not an independent cold installation, external scientific peer review or separately authenticated GitHub approval. This review cannot approve the human scientific gate or activate downstream work.

Reviewed `src/deviation/contracts.py` SHA-256: `dcd175fd35452cff07380eaca85dd7cbc5b6257709892d50356175e551bbe000`.

## Challenges and corrections

| Finding | Correction and reproduction evidence |
|---|---|
| A plan could inflate its own budget from 600 to 900 and suppress a realized violation | Separate trusted `run_config` binds budget/unit in allocation, realized reporting and completed replay. `test_plan_cannot_inflate_budget_to_hide_realized_violation` rejects all three paths. |
| Empty participant utility receipts could omit economic payoffs | Trusted agent registry requires exactly one utility receipt per economic agent. Missing/extra participants and malformed containers fail `test_all_participant_utilities_and_typed_containers_required`. |
| Training and decision IDs could collide despite different prompts | Both task IDs and normalized prompt groups must be disjoint; `test_training_and_decision_ids_disjoint_even_for_different_prompts` rejects the collision. |
| Dictionary-shaped transfers could bypass an empty-transfer loop | Transfers require list shape; utilities require object shape. Initial funding is separately bound to trusted configuration. |
| Prior-history actor looked like an undeclared economic participant | `seed-history` is a declared exogenous synthetic history source with no account, action or payoff. Unregistered actors and exogenous recipients fail `test_registered_exogenous_history_is_not_an_economic_participant`. |
| Historical audit wording implied contracts were still unchanged | `DATA_AUDIT.md` now identifies the historical checkpoint and separately pending v0.2 proposal. Original Phase 1 evidence remains unchanged. |

The reviewer independently reported **50 tests passing** after these fixes, confirmed exact decimal/nano rounding, training exclusion, reservation/realized accounting, ledger conservation and migration checks, and found no remaining actionable blocker. Two subsequent integrator tests check trusted-role/funding configuration rejection and published contract-index consistency; the complete suite now has **52 passing tests**. Those test additions do not change the reviewed validator source hash. Hosted CI and exact published head are recorded in the PR.

## Reproduction

Use Python 3.11 or newer from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/check.sh
git diff 5b97cc7e7cc51f0194b1345fa0b4707e8be9c72d -- artifacts/data_audit.json artifacts/data_manifest.json artifacts/splits.json src/deviation/core.py
```

The last command produces no differences. The existing starter trace remains visibly synthetic and within its legacy demo budget. This is not a v0.2 simulator run. New fixtures are hand-specified synthetic conformance receipts, including a reservation-feasible plan with a reported realized-cost violation. No raw third-party data is included.

Unchanged Phase 1 SHA-256 evidence:

| Artifact | SHA-256 |
|---|---|
| `artifacts/data_audit.json` | `2ef3bfeb70d821c9c63588c7b7d824b94fb496b44059b422365e80c5217c2a95` |
| `artifacts/data_manifest.json` | `111a07dfe4fe7abed39af5cdca230a9efcbf11a5aab4e93b676f3dc0d3d71ac3` |
| `artifacts/splits.json` | `4a3b1d1f5627cb87a392ab377089e9cd6948c1ec5a60feee138e4f20f693c88f` |

## Limits of this approval

Validators establish supplied-receipt shape, boundaries and arithmetic. They do not authenticate provenance, implement runtime credit/fee state, isolate hostile code, measure estimator performance or prove incentive compatibility. The future runner must own trusted configuration, frozen reservations, authoritative state and sealed outcomes. Synthetic signals and utilities remain modeling assumptions. ArenaHard quality, historical costs and the 247-task exploratory scope retain all approved limitations.

No simulator, market or frontend was implemented; no real-data reservation fit, mechanism comparison or final evaluation was run. The merge investigation establishes account attribution and current missing protections, not the person/client responsible or historical settings. The ruleset proposal remains unapplied. Incremental spend: **$0**.
