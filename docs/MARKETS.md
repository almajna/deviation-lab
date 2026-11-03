# Working categorical economic engine v0.3

Issue [#13](https://github.com/almajna/deviation-lab/issues/13). The owner approved Gate B at `a8bbcd7cd716b37d529b8f5aa82adb1b83dda7a6`; PR #12 is merged at `ea0c0a327730855e3e230fd2c114b14673f1c5ef`. The implementation is isolated in `deviation.markets`; active v0.2 contracts/runner and historical artifacts are unchanged. This is synthetic engineering, not a scientific result or a completed attack benchmark.

## Run and reproduce

Python 3.11+, standard library runtime only:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation.markets tests/fixtures/markets/two_task.json --out market-output
PYTHONPATH=src python3 -m deviation.markets tests/fixtures/markets/two_task.json --out market-replay --verify market-output/receipts.json
PYTHONPATH=src python3 -m deviation.markets tests/fixtures/markets/two_task.json --mechanism calibrated-pool --out pooled-output
```

An isolated `pip install --no-deps .` also installs the CLI without PYTHONPATH. The CLI reads JSON data only, never loads policy code, and supports only explicitly SYNTHETIC scenarios. No downloader, model API, training job, final-evaluation path or deployment exists. Construction accepts audited training costs and categorical training-report data; no model-fitting claim follows from selecting a three-value calibration parameter.

The scenario is `markets-1`, containing trusted public tasks/economic configuration, synthetic recipient signals, training-only cost/calibration rows and a separately sealed outcome store. Output `replay.json` is v0.3 public/post-settlement events; `receipts.json` adds public configuration, reservation/allocation receipts and canonical receipt hash; `events.jsonl` is the same ordered event stream; `manifest.json` hashes output bytes. Input and complete local Python-package hashes bind built-in reexecution. Run/replay writes byte-identical files across source checkout and installed wheel for the same inputs/code. Private signals and sealed stores are not exported. A public report can intentionally repeat a signal; it is labeled a report, not an exported private packet.

## Certified pricing and projection

`numeric.py` performs integer-directed dyadic interval arithmetic at 64, 128 and 256 bits. No floating-point exp/log or epsilon decides a quote. For exp(-x), halve nonnegative x until ≤1/2, bracket with consecutive exact alternating Taylor sums, round outwards, then square with directed integer rounding. For log, max-shift LMSR makes the summed exponential lie in [1,3]; use `ln x=2 atanh((x-1)/(x+1))`. Positive series terms are enclosed and the omitted tail is bounded geometrically. The implementation permits [1,4] to account for outward rounding. Potential subtraction uses lower-after minus upper-before and upper-after minus lower-before.

Accept signed ceil(ΔC) only when both endpoints have the same ceiling. Common translations/permutations are recognized analytically, including exact zero differences and full sets. Persist exact finite-decimal dyadic endpoints, bit precision and numerical-policy hash. At the precision cap, reject NUMERIC_AMBIGUITY without charging or mutating positions. This can reject very extreme but mathematically valid orders; it cannot silently approximate a debit. Quote domain is bounded integer q/b up to the documented coordinate/b limits.

Project probabilities using certified floor/remainder comparisons and exact equal-coordinate ties. Counts sum P; execution charges come from C, never displayed prices. Rational pooling projects exactly. Square-root calibration encloses roots using integer square roots and has an exact rational-ratio path: common irrational normalization factors cancel, so valid normalized distributions such as (2,8,0)/10 do not reject at exact remainder ties. Policy and component indexes are in `schemas/contracts-v0.3.json`; this is not JSON Schema.

## State, money and permissions

Engine stages follow Gate B: prepared books → private report commitments → common reveal → scheduled optional actions → locked allocation → all-arm settlement. Every actor/market report opportunity must commit or decline before reveal. The runner owns actor/market turns, sequence numbers, report tokens, available cash, numerical policy and limits. Copied packets contain public history/current books and the recipient's own signal/portfolio/controller preferences only. `Engine.snapshot` refuses post-settlement/nondecision access. The runner does not read the outcome store until all allocations lock. Trusted in-process Python policies are not a hostile-code sandbox; no untrusted code execution is supported.

Actor IDs use `[A-Za-z][A-Za-z0-9_-]{0,63}` and command IDs must begin `actor/`. This makes namespaces disjoint and prevents an actor reserving another actor's command identity. Accepted report/no-op/update/trade IDs are recorded; rejected events record an ID only if that typed ID was reserved. Invalid requests consume an assigned slot, not another actor's opportunity; they leave money/positions/prices unchanged. Replayed IDs cannot debit twice. State sequences also advance for public report revisions.

Signed baskets sell owned shares only. Before committing, check all position/quantity/controller limits, exact charge, fee, signed order limit, final trader cash and maker cash≥max(q). Apply maker payment/refund plus fee on a copy, then commit atomically. Fees go to a separate sink. Every cell has its own `ceil(b ln3)` funded maker. Scoring receives N_tokens×2D²k in a separate account; pending rewards cannot finance trading. Overall sponsorship cap conservatively includes initial agent wallets as well as maker/scoring reserves. Fixed controller caps bind aggregate wallets, report tokens, slots and positions; utility preference weights are counted once per controller rather than per alias.

Initial report fees are zero. Optional accepted trades/updates pay the configured fixed fee; rejected/no-op requests pay no cash fee. `effort_per_attempt` is separately declared noncash effort per consumed optional slot, including a no-op; comparisons must state this choice. Original committed reports receive exact integer Brier rewards once. Later revisions never replace the score claim. All eligible market arms settle even when compute allocation abstains. Winning claims pay from their cell and **all** claims then burn. Cash delta includes maker payments, fees, claim payouts and scoring exactly once; external utility and noncash effort remain separate modeled terms. Maker P&L excludes its starting subsidy.

## Allocation and non-market controls

Reuse the existing simulator's training-only reservation fitter, exact multiple-choice allocator, reference policies and selected realized-cost accounting. A trusted v0.2-shaped compute plan is carried inside the v0.3 allocation event by an explicit adapter; economic credits never enter compute-cost units. Public config separately binds reservation budget so changing the plan's own budget cannot hide a violation.

Configured treatments: LMSR price means; raw pool; interactive pool; training-calibrated pool; scored reports; uniform prior; seeded feasible random; cheapest; training-best-fixed. All receive the same initial report opportunities, source signals, wallets, funded reserve caps, schedule, task set and compute budget. Pool/scored-report labels share the same allocation path; scored commitments are common to every treatment to hold report rewards fixed. They are not independent discoveries. The default interactive reference follows its fixed supplied signal and does not invent a Bayesian update; without new messages it can equal raw pooling.

LMSR accepts trade/no-op; interactive pooling accepts distribution-update/no-op; static controls accept no-op only in optional slots. Unavailable actions reject. Equal pooling holds one current message per identity, uniform if empty; late entry requires its existing optional slot and earns no retroactive score. Calibration uses the exact declared training pairs only, selects T∈{1,1/2,2} by Brier loss with identity-first ties, and reports the identity ablation separately. Missing/duplicate/nontraining pairs fail. No hidden labels/realized costs fit predictions or select actions.

## Events, validation and Phase 4 interface

`validate_result` checks closed envelopes then rebuilds the entire public economic state machine: committed/revealed reports, command identities, certified accepted trades, effect-free rejected slots, no-ops, revisions, allocation, claims, scoring, transfers and summary. Comparing canonical regenerated events enforces types/arithmetic and nested fields, including boolean-versus-integer differences. A transfer event projects its linked atomic transition; replay does not apply both twice. Source replay separately reruns the trusted built-ins against original inputs/code.

Public validation cannot prove authenticity of source data or the truth of an unexported rejected request; its permitted reason, reserved ID and effect-free slot transition are checked. Injected local test policies are explicitly labeled. Public transition replay validates their accepted commands, but original-input built-in replay refuses them with INJECTED_POLICY_REPLAY_REQUIRES_COMMANDS; no arbitrary policy serialization or execution is implied. `event_shape` alone is a shallow envelope helper, **not** a full replay validator.

`policies.candidates(packet)` is a finite pure candidate/quote interface over recipient/public state. Caps fail explicitly rather than silently truncating search. `candidate_value` verifies candidate membership and supports only LMSR's last optional slot, using declared belief, public counterfactual allocations, controller utility and explicit added effort. Earlier-turn lookahead is disabled without a future-behavior model. This prepares Phase 4 interfaces; it is not an attack search or a proof of a profitable exploit.

## Historical compatibility and evidence

Old evidence is immutable at its pinned source. The approved Phase 2 whole-package fingerprint necessarily changes when modules are added. Original `artifacts/simulator/two_task` remains unchanged and is verified from commit `390e1b7a63cf31306d78815e381f81ec7245f8d6` by CI. A separately versioned `artifacts/simulator/v0_3_source` reexecutes the unchanged v0.2 behavior under current source. Only implementation/receipt hashes differ; all other v0.2 fields and existing tests are preserved. Fingerprint validation has not been disabled. New market artifacts are under `artifacts/markets/two_task` and explicitly SYNTHETIC.

Independent review challenged the actual code and found/fixed command identity replay, treatment permissions, normalized square-root ties and horizon constraints. Exact-head tests/CI/review evidence are in the PR and `PHASE_3_REVIEW.md`. Mathematical, conservation, private-packet, hidden-outcome mutation, nested tampering, adversarial-order and installed CLI tests exercise actual transitions. No benchmark result or market advantage is claimed from this fixture. No full-game truthfulness, calibration, general Sybil resistance, objective correctness, verified bills/savings, deployment budget or live counterfactual claim. Optional bids, coherent empirical signal/posterior generation, attack search, final holdout and UI integration remain future work. Spend $0; human-only merge.
