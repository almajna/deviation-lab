# Shared contracts v0.2 — proposed for approval

Status: **complete proposal, human contract approval and merge pending**. The owner approved the five development assumptions on 2026-11-02; approval of those assumptions is not approval of this exact interface revision. Phase 2 and Phase 6 work starts only after independent review, explicit owner approval of the current PR head, and verified merge. A merge alone is insufficient. See `GATE_A.md`.

The normative reference is `src/deviation/contracts.py`; `schemas/contracts-v0.2.json` indexes components and validator entry points. Fixtures are synthetic conformance examples, not an implemented simulator or evidence of mechanism performance. Unknown fields are rejected, including nested fields. Cost amounts use integer fixed-point units, credits use separate integer virtual units. JSON serialization and hashes use UTF-8 canonical sorted-key JSON as implemented by `deviation.data.pipeline.digest`.

## Scientific interpretation

- Historical ArenaHard quality is a noisy judged preference proxy: win/tie/loss = 1/0.5/0. It is not objective coding correctness; invalid historical judging may be indistinguishable from a loss.
- Historical reported costs are retrospective measurements of unresolved API-reported/token-priced provenance. They are not verified invoices, deployable dollar savings, or guaranteed resource costs.
- Agents in these contracts are synthetic forecasters/adversaries. Recorded LLM task outcomes plus simulated agents use `RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS`; wholly synthetic fixtures use `SYNTHETIC`. Observed real LLM-agent behavior is unsupported in this revision.
- The 247-task cohort is a development pool. Existing exploratory `test` labels do not create a final holdout. No final evaluation is authorized here.

## Public tasks and sealed outcomes

A public task has exactly `task_id`, original `prompt`, and unique `model_options` (at least two). IDs must be nonempty and unique. Equal NFKC/case/whitespace-normalized prompts share a group even across different IDs. Model names do not imply a fixed cheap/strong ordering.

The runner owns the sealed paired-outcome store: task/model IDs, judged quality, historical cost and provenance. The Phase 1 `OutcomeRecord` remains an internal audit object, not a policy input. Its existing `data-audit-1` artifacts are unchanged. Only settlement/evaluation code receives sealed outcomes after decisions. Counterfactual outcomes are offline historical observations; their availability must not be claimed for deployment. Policies receive deep copies/frozen projections of public fields, not outcome-store references, source paths, or arbitrary metadata. Validators establish structural boundaries, not hostile-code isolation or provenance authenticity; untrusted policy code still requires a sandbox.

## Training-only reservation artifact

The runner supplies a trusted, frozen `run_config` separately from policy messages and receipts. `validate_run_config` checks its version, cost unit, reservation budget, economic `agent_accounts`, maker and fee-sink accounts, initial balances, and `exogenous_history_actors`. Roles are distinct; initial balances cover exactly the economic agents, maker and fee sink. `allocator` and `system` are reserved roles. Persist this configuration with the future reproducible run. A participant cannot replace it with a larger budget or different funding. Validators do not authenticate who supplied the configuration.

`validate_reservations` checks an already-supplied receipt against trusted training rows, split-group registry, source/split hashes and decision task catalog. It is not a fitting service and is not run against the real development cohort in this PR.

Chosen initial estimator: `mean_train_only_v1`. For each model m, use every approved training task/model cost row, require complete model coverage, and compute:

`reservation[m] = ceil(1_000_000_000 * sum(training_cost[m]) / training_count[m])`.

Use decimal strings and exact decimal arithmetic; round upward to integer nanos. Base units are `reported_usd` or `synthetic_units`; public units are `nano_reported_usd` or `nano_synthetic_units`. Zero/missing/nonfinite/negative training costs, booleans, mixed units, duplicate rows, missing arms, unknown estimators, empty training receipts and changed hashes fail. Each admitted reservation is positive. The scale is fixed at 1e9; future realized-cost conversion must retain the original decimal and disclose its rounding (ceil per selected row, less than one nano extra per row).

The receipt contains `schema_version`, `data_kind`, `cost_unit`, `scale`, `method`, source/split manifest SHA-256, sorted `fit_group_ids`, `fit_row_count`, per-model `reservations`, and a canonical `artifact_sha256`. Source/split hashes must match trusted inputs, but hashes alone do not prove that the caller supplied genuine data.

**Exclude all training prompt groups from allocation runs.** Do not allocate training tasks under a receipt containing their own costs. No cross-fitting is authorized by this initial contract. Validation and exploratory test groups must be disjoint from all fit groups; duplicates under different IDs do not bypass this. Missing model estimates cause an error, not a held-out-cost fallback. Freeze the artifact before any decisions. Sensitivity estimators are future protocol choices fitted only on training data.

## Agent information, actions, and histories

`validate_information(info, artifact, decision_tasks, run_config=trusted_config)` accepts exactly:

- `schema_version`, `agent_id`, `agent_kind` (`SYNTHETIC_FORECASTER` or `SYNTHETIC_ADVERSARY`);
- one registered public `task`;
- recipient-specific `private_signal` with `owner_agent_id`, `origin=SYNTHETIC`, `forecast_kind=expected_preference_proxy`, and bounded per-model `values`;
- the fixed reservation artifact hash, per-model reservations, cost unit and remaining reservation budget;
- `available_credits`, configured nonnegative `action_fee`, `action_seq`, `time_step`, and allowed public `history`.

Forecast values represent E[judged preference reward], not probability of coding success. Binary-event forecasts require a separately approved event/threshold contract; this revision makes no scoring-rule truthfulness claim.

A pre-action history event has exactly `seq`, `time_step`, `actor`, `visibility`, `type`, `payload`. Only PUBLIC `public_forecast` events for the current task are admitted. Their payload is exactly `task_id`, `forecast_kind`, `values`. Sequence numbers increase strictly and are less than `action_seq`; time steps cannot be in the future. Earlier sequence numbers within the same time step are allowed; later events in that step are forbidden. Settlement, realized costs, raw signals, outputs, ground truth, another agent's private fields and metadata bags are rejected. Broader market/trade histories need an explicit reviewed contract extension in Phase 3.

A v0.2 action has exactly version, agent/task IDs, `kind=report_preference`, `forecast_kind`, per-model `values`, and `action_fee`. `validate_action` matches identity, task, model coverage and the configured fee. The participant cannot lower its fee or report under another agent's identity. Action permissions and credit state must be enforced by the future runner, not inferred from a schema-valid message alone.

Recipients must be registered economic agents. Public history actors must be registered agents or declared exogenous history sources. The fixture's `seed-history` is a fixed synthetic prior-history source with no economic action, account or payoff; it is not an omitted participant. Remaining budget cannot exceed the trusted budget. The future runner must derive exact remaining budget, available credits and configured fees from authoritative state; schema checks alone do not implement state transitions.

## Allocation and distinct budget semantics

The allocation interface receives public tasks, validated actions, frozen reservations and a reservation budget; **it receives no outcomes or realized cost**. A plan has version, reservation artifact hash, cost unit, `reservation_budget`, and one allocation for every task: `task_id`, `model_id`, `reserved_cost`. Explicit abstention uses null model and zero reserve/cost. Other reserves must exactly match the frozen per-model estimate. Reject duplicates, missing tasks, unknown arms and sum(reservations) greater than the budget. Equality at the budget is allowed.

There are no hidden-cost-dependent reservation releases, refunds or mid-run refits. All decisions complete before historical costs are revealed. Any future online/repeated-round extension needs a reviewed visibility rule. Valid simulated reservation feasibility does **not** imply a real-world hard-budget guarantee.

Allocation and realized-report validators require the separate trusted `run_config` and bind plan budget/unit to it. Increasing a receipt's own budget cannot suppress a reported violation. Training and decision task IDs must also be disjoint, even if their prompt strings differ.

After decisions, a SETTLED realized-cost report contains selected task/model costs and these separate quantities (all cost quantities use the same nano unit):

- `reservation_spend = sum(selected reservations)`;
- `realized_spend = sum(selected historical costs)`;
- `positive_task_overruns = sum(max(realized_i - reserved_i, 0))`;
- `unused_reservations = sum(max(reserved_i - realized_i, 0))`;
- signed `net_overrun = realized_spend - reservation_spend`;
- `realized_budget_excess = max(realized_spend - reservation_budget, 0)`;
- `realized_budget_violated = realized_spend > reservation_budget`.

Report overruns honestly; do not reject a completed retrospective run merely to hide a realized violation. Reservation violations are allocation errors; realized violations are reported retrospective outcomes. They must never be conflated. In the synthetic fixture: reserved 500 <= budget 600, realized 900, positive per-task overruns 500, unused reserves 100, net overrun 400, and realized budget excess 300.

## Payoff and settlement interfaces

All ledger amounts are integer `virtual_credit`, separate from reported historical cost. Never add them to USD or subtract them from judged quality without an explicit, separately reviewed conversion/objective.

A ledger receipt has explicit initial/final balances, uniquely identified payer/payee transfers, per-agent utility components, maker account, initial maker subsidy, maker cash P&L and realized loss. Initial balances are measured **after declared initial funding**. Transfers debit a payer and credit a payee equally; fees go to a named fee sink, not an invisible burn. No negative balances, duplicate transfers, self-transfers, unfunded payouts or account creation during settlement. Initial subsidy is not rebooked as settlement income.

`validate_ledger(..., run_config=trusted_config)` binds initial balances and maker identity to trusted configuration. Utility receipts cover every registered economic agent exactly once, including zero-activity agents. Transfers must be a list and utilities an object. Action-fee transfers debit an economic agent and credit the configured fee sink. Exogenous history sources have no economic account or utility receipt.

`cash_delta = final_balance - initial_balance` already includes action fees and settlement transfers. `utility = cash_delta + external_benefit - noncash_effort_cost`. Do not subtract a cash action cost twice. External benefit is an explicitly modeled utility-only reward, not a funded cash transfer; noncash effort is distinct from ledger fees. Cash-funded external rewards instead require an ordinary funded ledger transfer and must not also appear as utility-only benefit.

`maker_cash_pnl = maker_final - maker_initial`; `maker_realized_loss = max(-maker_cash_pnl, 0)`. Report initial subsidy/bankroll separately. The fixture's agent pays 2, receives 6, has cash delta 4, external utility 3 and noncash effort 1, so utility is 6. Maker initial funding is 50, ending balance 44, cash P&L -6 and loss 6. This is an accounting illustration, not a market or attack result.

Python Protocol signatures separate `DecisionPolicy.act`, `AllocationMechanism.allocate`, and `Settlement.settle`. Implementations do not exist in this PR. Settlement may receive the runner's sealed outcomes only after allocation. Choice of actual reward/scoring/market settlement rules, external-interest parameters and economic validity remains Gate B/Phase 3 review; conformance to a ledger does not prove incentive compatibility.

## Completed replay and visual handoff

A v0.2 completed trace has version, experiment ID, seed, `data_kind`, `agent_origin=SYNTHETIC`, quality semantics, phase SETTLED, cost unit, reservation artifact hash, source/split/code provenance, and ordered events. Real-outcome traces require a pinned code revision; the wholly synthetic fixture uses `SYNTHETIC_FIXTURE` as its explicit code provenance marker.

Events have contiguous zero-based `seq`, nondecreasing `time_step`, actor, visibility, type, payload. Allowed initial types: public forecast, reservation, realized-cost report, ledger transfer, utility summary. Forecast/reservation visibility is PUBLIC; realized reports and payoffs are POST_SETTLEMENT. All reservation rows, actual-cost summary, transfers and utilities must match the separately validated receipts. This is an **audit replay after completion**, never the information object passed to a policy. Agent-private signals are not exported in the public trace; any later private-signal disclosure needs a reviewed viewer-specific extension.

The frontend consumes public events and explicitly post-settlement receipts, labels synthetic versus recorded provenance, and renders separate reservation/realized-cost/virtual-credit figures. It must not reinterpret a forecast as correctness probability or present the synthetic fixture as a discovered exploit. Unsupported market-price/attack/evolution results stay empty until backed by later validated event types.

## Migration, verification and approval

`tests/fixtures/contracts_v0_2.json` is a synthetic conformance pack; `tests/fixtures/contract_migration.json` preserves the exact legacy v0.1 demo and declares explicit new training/settlement receipts necessary for v0.2. **No automatic relabeling of legacy costs as pre-decision reservations is valid.** The old CLI/core stays v0.1 and unchanged. Phase 2 will add a separate v0.2 path while maintaining that regression test.

Validation order: trusted run configuration -> reservation receipt -> information -> action -> allocation -> realized report -> ledger -> completed trace. Validators receive previously validated dependencies. The conformance pack is illustrative supplied data, not output of an implemented simulation. Tests reject unknown/nested hidden fields, foreign private signals, future history, wrong units/version, training-group leakage, nonfinite/boolean amounts, budget violations, duplicate IDs, double-counted costs and silent migration. CI runs all existing and contract tests under Python 3.11.

Approval requires independent review, owner approval of the exact contract PR head and explicit human merge; no agent can approve its own scientific gate or infer approval from an unrelated merge. After that gate, use the isolated Phase 2 and Phase 6 work described in `IMPLEMENTATION_HANDOFF.md`. No final holdout run, market implementation or superiority claim is authorized by this proposal.
