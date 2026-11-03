# Proposed v0.3 economic interface — inactive

Approval target: `GATE_B.md`, issue #11. This is an explicit proposal, **not a change to the active v0.2 contract**. `schemas/proposals/markets-v0.3.json` is a component/field index, not JSON Schema or a running validator. Hand-specified examples in `tests/fixtures/gate_b_math.json` are mathematical conformance data, not produced market logs. The frontend is untouched and must continue rejecting unsupported versions until a separately reviewed adapter exists.

## Execution and numeric envelope

The future manifest pins source/split/config/code and numerical-policy hashes, seed, stage schedule, category order `[zero,half,one]`/rewards `[0,1/2,1]`, report denominator D and exact score multiplier k, price denominator P, share/position caps, b and segregated maker funds per task/model, score-token registry/funding, fee sink, wallets, controller/identity mapping, fixed aggregate external utilities, action limits and attack-information policy. Integers reject booleans. No nonfinite numerical values, arbitrary metadata, raw source paths or executable objects. Signed share deltas, maker charges and order limits are the only signed cash/action quantities; balances, fees, holdings and funds are nonnegative.

The market manifest and source/split hashes are held by the runner. No policy-supplied copies can change them. Every hash uses canonical sorted-key UTF-8 JSON; use a fixed serializer for decimal interval endpoints (base-10 strings, never binary JSON NaN/Infinity). Numeric comparisons/rounding must follow the certified policy in Gate B. Exact quote/price certification is an implementation obligation, not established by this index.

## Information and actions

Proposed packet fields appear in the index. A packet is recipient-specific: synthetic categorical signal, own cash/positions/limits, trusted stage/turn/sequence, public market definitions/state/prices, reservations/B and permitted previous public history. It excludes sealed outcomes, foreign private signals, raw outputs, future orders and pending/revealed payouts. A controller's modeled decision preferences may appear only in its own authorized utility view. Private controller linkage is not automatically public; identity policy must declare what is known.

Actions:

Each indexed action has a closed `kind` discriminator and a trusted `stage`; dispatch rejects a kind/stage mismatch before reading its body. A client cannot advance the stage by declaring it. Separate `report_distribution`, `update_distribution` and `trade_shares` bodies are not interchangeable.

- `report_distribution`: one registered report token, task/model identity, integer probability counts summing to D, stage and expected state sequence. Commit before reveal; no arbitrary token creation or categorical reinterpretation of a v0.2 mean. Optional updates have explicit `update_distribution` type, no score token and no extra reward.
- `trade_shares`: market/actor/order IDs, expected sequence, three signed integer share deltas, signed `max_net_debit`. Fee, available cash/holdings, b and q are server state. Validate and commit maker payment, fee, share ownership and state changes atomically.
- `no_op`: consumes an available slot, no cash movement. Rejected requests also consume a slot with no cash mutation, and have one of the finite rejection reasons in the index.

Report tokens, trade order IDs and event IDs are globally unique per run. Duplicate/replayed commands cannot debit twice. Honest and adversarial policies receive the same typed boundary; oracle analysis is a separate evaluator API with no decision action handler. Fixed schedules cannot reveal outcomes or let a malicious actor steal another actor's slot. Commit/reveal content is private until its designated reveal stage, including in error messages and actor-visible history.

## Reproducible event envelope

Proposed full trace root: version 0.3, experiment/seed/data-kind, synthetic agent origin, noisy-proxy or synthetic quality semantics, stage SETTLED, market/config/source/split/code/numerical-policy hashes, and events. This proposal does not relabel an old v0.2 artifact. Source events/receipts are immutable inputs to future playback; no UI randomness, inferred missing prices or fabricated fills.

Each event has exactly `seq`, `time_step`, `stage`, `actor`, `visibility`, `type`, `payload`. Contiguous global seq and monotone deterministic time_step are runner-owned; state sequences bind each market quote to its last accepted transition. No quote event can refer to later state. Public trade/report histories are filtered by current global seq and stage; even a completed audit trace cannot be passed wholesale to a policy. Private signal packets are not exported by default. Committed report contents are not emitted publicly until reveal.

| Event | Visibility / stage | What is recorded |
|---|---|---|
| `market_opened` | PUBLIC / PREPARED | task/model market definition, uniform q/price counts, maker cash/funding, numerical policy |
| `report_revealed` | PUBLIC / REPORT_REVEAL | report/token/actor identity, counts/denominator; no private signal or invented posterior label |
| `distribution_updated` | PUBLIC / TRADE_OR_UPDATE | old/new public counts and their sequence; no new funded score token |
| `trade_accepted` | PUBLIC / TRADE_OR_UPDATE | order/actor, q and price counts before/after, own position before/after, signed maker charge, fee, certified interval/precision, market state seq, cash movement IDs and post-transition solvency |
| `action_rejected` | PUBLIC / decision stages | actor/order/slot and finite reason; no hidden input/quote diagnostics that expose outcomes/private reports |
| `allocation_locked` | PUBLIC / ALLOCATION_LOCKED | frozen reservation artifact, budget/unit, exact mean numerators/denominator, allocations/abstentions and reserved total; no realized costs |
| `market_settled` | POST_SETTLEMENT / SETTLED | category y, outstanding claims and per-agent claim payments/burns, cell initial funding/revenue/payout/P&L/loss/final cash |
| `score_settled` | POST_SETTLEMENT / SETTLED | report token/counts/y, integer score, named funded payer/payee, remaining pool |
| `ledger_transfer` | PUBLIC when allowed or POST_SETTLEMENT | uniquely identified payer/payee/amount/reason, scope/cell; reason distinguishes trade charge/refund, fee, claim redemption and score reward |
| `economic_summary` | POST_SETTLEMENT / SETTLED | initial/final cash, conserved transfers, controller utility components, per-cell losses, scoring/fee/subsidy accounting and realized historical-cost diagnostics |

Initial report fees, if nonzero, must not reveal committed counts before reveal. Their public timing/identity policy is frozen. Mandatory public cash/price payloads concern accepted economic actions only; the policy must not expose secret reports by reflecting their score before settlement.

`trade_accepted` is the authoritative atomic transition record. Its linked `ledger_transfer` entries are accounting projections, **not another debit**. Likewise settlement receipts link to transfers rather than applying money twice. The index specifies the trade fields; other table entries require full closed payload validators/fixtures in the implementation PR before they are admitted. This is a deliberately explicit remaining obligation, not a claim that an incomplete index validates a full replay.

Balances are initially funded credits, not P&L. Price counts sum P; projected expected proxy is rational and independent of credit units. Market cash must cover max(q) after every transition. All-arm payouts, including unselected cells, occur only after every allocation is locked. Post-settlement reports cannot retroactively change quotes, outcomes, reservations, agent credit limits or accepted actions.

## Compatibility and implementation prerequisites

Preserve `deviation.contracts` v0.2, `simulator-1`, old source-bound artifacts and the frontend fixture guard. New v0.3 code lives behind explicit dispatch in a separate module/path. Mean-only v0.2 signals lack categorical information; do not synthesize a distribution and call it an equivalent migration. The implementation PR must include closed validators for every new message/event, valid/invalid fixtures at every nesting level, privacy/stage/order mutation tests, directed numerical enclosures, all-account conservation and source-bound byte-exact replay. No frontend change is required or authorized by this Gate B proposal.

The optional first-price control in Gate B uses separate bid commit/reveal/escrow/payment events if implemented; it is not implicitly covered by these trade fields. Any omitted feature remains disabled until its explicit fields/tests are reviewed. Further private-signal viewer exports, live selected-only settlement, loans, shorting, adaptive liquidity, learned priors and external cash conversion are out of scope.
