# Certified attack discovery

Issue [#20](https://github.com/almajna/deviation-lab/issues/20). Additive research implementation on the approved Phase 3 engine and Phase 4 outcome-free `Game`. This delivers checkable finite-subgame intervals, not a new market manipulation phenomenon or a full-game security theorem. All included examples are **SYNTHETIC**. No recorded development cohort, final holdout, live LLM or paid API is used.

## Reproduce

Python 3.11+; standard library only. From the repository root:

```sh
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python -I -m deviation.attacks.certified examples \
  --out /tmp/deviation-certified-reproduction \
  --verify artifacts/attacks/certified
python -I -m deviation.attacks.certified verify \
  artifacts/attacks/certified/scenario.json \
  artifacts/attacks/certified/small-lmsr.certificate.json
python -I -m deviation.attacks.certified solve \
  artifacts/attacks/certified/scenario.json \
  --out /tmp/deviation-certificate.json --max-expansions 1000
```

For new scenarios the CLI uses the same trusted `prepare_game` harness as the existing attacks. Static report games require `--scope reports --mechanism pool` (or `score` / `calibrated-pool`) and `--public-reports file.json`: the declared public opponent report model, never hidden actual opponent reports. For library use:

```python
from deviation.attacks.game import prepare_game
from deviation.attacks.certified import solve, verify

game = prepare_game(scenario, "strategic", "lmsr")
certificate = solve(game, max_expansions=1000, vector_limit=5000)
checked = verify(game, certificate)
# checked['gain_bounds']['signal_following'] gives verified incremental bounds.
```

`max_expansions=0` returns the initial feasible incumbent and an unresolved root bound. Partial searches retain all unresolved branches. They never label an unclosed gap optimal. Timings can be measured with `examples --timings /tmp/certified-timings.json`; machine-dependent timing is outside deterministic artifacts and strict replay comparison.

## What is certified

The objective is **subjective expected controller utility**, not realized quality or deployment profit. It is cash balance change plus expected redemption of current long positions plus the original committed report scores plus declared external allocation reward minus noncash attempt effort. Fees are already in wallet changes and are not subtracted twice. Sponsor scores are counted in absolute utility; matched reference differences remove their common component. Existing `attacks.verify.recompute` independently checks sample engine receipts after execution.

Only two existing information-safe subgames are supported:

- A terminal suffix where every future scheduled actor belongs to the controller. Unknown future honest behavior is rejected. Beliefs are fixed during this suffix, and controlled identities share the existing common-belief assumption.
- The last global initial-report opportunity, with the existing explicit public opponent report model. Subsequent static-mechanism slots are forced no-ops. Exhausted slots retain the engine's real `ACTION_LIMIT` rejection and effort rather than fabricating acceptance.

The finite action family contains canonical no-ops and all accepted integer LMSR orders with L1 norm at most Q, or all denominator-D simplex report vectors (and optional decline for the initial report). Order IDs/max-debit values are canonical representatives, not strategic degrees of freedom. Orders rejected for numeric ambiguity are inadmissible under the actual engine. Other invalid messages cannot create a distinct beneficial state here: accepted no-op consumes the same scheduled opportunity/effort without changing portfolio/report. Exhausted opportunities have a canonical forced no-op rejection. This is not a claim about protocols where rejection itself conveys new private information.

Limits fail explicitly: horizon 128, action family at most the engine candidate limit and 100,000, producer expansions at most 100,000, endpoint box limit at most 100,000. Public allocation uses the existing exact knapsack's explicit state limit. Caller supplies a trusted `Game` produced by `prepare_game`; shallow horizon checks do not authenticate arbitrary hand-constructed engine objects. No outcomes, evaluator law, future private signals or source scenario are optimizer fields.

## Rounded-charge endpoint bound

For a market let q be total current shares, h the controller's aggregate long holdings, p its categorical belief, b the existing LMSR liquidity, Q the order L1 cap, f the nonnegative fee, and R the number of remaining opportunities before account action exhaustion. Other holders are fixed throughout this controlled suffix.

Let `C(q) = b log(sum_y exp(q_y/b))`. If future accepted orders have net change delta and charges `ceil(C(q_next)-C(q_prev))`, then

`sum charges >= ceil(C(q + delta) - C(q))`.

This follows from `sum ceil(x_t) >= ceil(sum x_t)` and telescoping, including sales/refunds. There is no continuous-cost substitution for rounded actual payments.

Every executable endpoint satisfies `||delta||_1 <= R Q`, and coordinatewise

`0 <= h + delta <= min(controller_cap, number_of_members * agent_cap, cell_cap - q + h)`.

At least `ceil(||delta||_1 / Q)` nonzero trades are necessary. Consequently an upper bound on future expected cash gain in this cell is

`max_delta {p dot delta - ceil(C(q+delta)-C(q)) - f ceil(||delta||_1/Q)}`

on that relaxed endpoint set. Include delta=0. Pooling identities and dropping intermediate cash/position/funding constraints enlarges the feasible set; it can weaken the bound, not invalidate it. Taking per-cell maxima independently likewise relaxes shared cash. Existing per-identity cash constraints remain mandatory for the executable lower-bound witness.

The implementation enumerates the endpoint box only below `vector_limit`. It uses the existing certified signed-ceiling quote primitive. If a *relaxed* endpoint's quote is ambiguous, it substitutes the safe lower charge `min(delta)`; it never removes a potentially feasible endpoint. The lower charge follows because the gradient of C is a probability vector. For larger boxes it uses the safe bound RQ: for any one trade, `p dot d - ceil(Delta C) <= p dot d - min(d) <= ||d||_1 <= Q`. Ignoring fees only increases this upper bound. This yields a bounded-cost fallback without an exponential enumeration of order sequences.

For the full bound, add current expected cash and sum of cell upper gains; add the maximum external reward under the **same** task choices, reservations, abstention and allocation budget; subtract effort for existing attempts and **every** future consumed slot. The external relaxation ignores market-price reachability and may therefore be loose. Static/interactive report changes cannot change fixed original score claims. For the pending initial report, expected quadratic reward is maximized exactly at the integer belief p, which belongs to the denominator-D simplex; decline is also covered because scores are nonnegative.

These inequalities prove an admissible bound under the stated engine/model. Tests challenge the implementation; neither tests nor this derivation constitute formal verification of the Python interpreter, engine or numerical kernel.

## Search and certificate proof

`solver.py` runs ordinary best-bound branch and bound. Honest and no-action complete plans initialize the incumbent. Expanding a node materializes its complete finite child family atomically. A branch with upper bound at most the incumbent need not be expanded. When the expansion cap is reached all other boundary nodes remain in the proof. Global upper is the maximum of the incumbent and all boundary values; global lower is the executable incumbent's independently recomputed utility. Equality certifies the finite-subgame optimum, including possible ties.

`checker.py` does not invoke solver/search/`Game.expected`. It separately constructs order actions with `Engine.inspect_order`, replays `Engine.apply`, recomputes utility algebra, and verifies every split's complete action partition. It rejects missing/duplicate edges, forged leaves, cycles, shared children, unreachable nodes, changed source/observation/controller/scope, infeasible or partial witnesses and noncanonical rationals, even when the producer recalculates the content digest. The existing parent attacks package imports search on package initialization; independence here means search is never **invoked** by checking. A regression disables the optimizer's routines during verification.

The checker deliberately trusts `model.py`'s economic bounding lemma, approved engine, allocator and certified numerical primitives. Agent 2 owns the independent reimplementation/check and separate benchmarks tracked in [#22](https://github.com/almajna/deviation-lab/issues/22). The internal checker is not a substitute for that independent implementation.

## Certificate interface for Agent 2

Sidecar version `attack-certificate-1`; shared v0.3 events/contracts are unchanged. Top-level fields are closed:

| Field | Meaning |
|---|---|
| `version`, `action_space`, `objective` | `attack-certificate-1`, `engine-l1-orders-or-simplex-reports-1`, `SUBJECTIVE_EXPECTED_CONTROLLER_UTILITY` |
| `scope`, `controller` | Trusted finite horizon kind and controller identity |
| `observation_sha256` | Existing `digest(game.observation())`, including resources, identities, schedule and economic state |
| `source_sha256` | `digest({relative_py_path: digest(file.read_text())})` for all sorted Python files inside `deviation` |
| `vector_limit` | Recomputable endpoint-box threshold, integer 0..100,000 |
| `incumbent_commands` | Complete canonical executable command sequence |
| `lower`, `upper`, `gap` | Reduced `[numerator, positive_denominator]`; absolute utility bounds and their difference |
| `claim` | `EXACT_FINITE_SUBGAME` iff gap=0, otherwise `BOUNDED_FINITE_SUBGAME` |
| `nodes` | Flat proof tree, root index 0; node indices are integers |
| `search` | Checked `{max_expansions, expansions, generated}` work counters |
| `sha256` | Existing `digest` of all other fields |

A split is `{"kind":"split","children":[{"command":...,"node":1},...]}`. An exact terminal is `{"kind":"terminal","upper":[n,d]}`. An unresolved/pruned boundary is `{"kind":"bound","upper":[n,d]}`. Terminal values and unresolved bounds are recomputed at their replayed states. All nodes must be reachable exactly once. There is no trusted pruning bit or producer-supplied action count.

`verify` returns verified bounds, checked-node count, incumbent payoff decomposition/commands, independently reconstructed honest/no-action utilities and gain intervals. A source digest is identity binding, not provenance authentication. Any added Python module changes it: integration with Agent 2 requires regenerating integrated-source certificates or explicitly verifying historical artifacts at their pinned source, never disabling source checks.

## Prior art and contribution boundary

- Land and Doig, [An Automatic Method of Solving Discrete Programming Problems](https://sites.math.washington.edu/~thomas/teaching/m514_web/50YearsIP.pdf), Econometrica 1960: branch and bound is established methodology.
- Cheung, Gleixner and Steffy, [Verifying Integer Programming Results](https://optimization-online.org/wp-content/uploads/2016/11/5740.pdf), IPCO 2017; [VIPR](https://github.com/scipopt/vipr): independently checkable rational optimization certificates are established. This implementation is not a general ILP solver or VIPR implementation.
- Chen, Gao, Goldstein and Kash, [Market Manipulation with Outside Incentives](https://econcs.seas.harvard.edu/sites/g/files/omnuum6346/files/econcs/files/chen_aaai11.pdf), AAAI 2011: outside allocation preferences can create manipulation incentives; success/failure depends on assumptions.
- Othman and Sandholm, [Decision Rules and Decision Markets](https://www.cs.cmu.edu/~sandholm/www/decision%20rules%20and%20decision%20markets.AAMAS10.pdf), AAMAS 2010: decision rules and contingent scoring alter incentives. Their setting/theorems must not be equated with our all-arm offline settlement model.

The defensible incremental contribution is applying a rounded-charge, fee-aware pooled-endpoint bound and explicit allocation-budget relaxation to this executable engine, with a proof partition that preserves upper bounds after early stopping. No literature novelty, new economic attack, asymptotic breakthrough or full-game robustness is claimed. Prior-art survey is targeted, not exhaustive.

## Evidence and limitations

`artifacts/attacks/certified/summary.json` retains all six declared implementation fixtures, plus individual certificates, the selected synthetic scenario, actual attacked/honest engine receipts and event-based independent payoff checks. These reuse known pilots and deliberately small fixtures; they are not a preregistered scientific benchmark or held-out replication. Agent 2 owns broader independent benchmarking.

| Fixture | Certified absolute utility interval | Ordinary search comparison |
|---|---:|---|
| One-slot LMSR, known pilot | [203/3, 203/3] | Exact/beam find same; incremental gain 11/3 |
| One-slot interactive pool | [64, 64] | Exact/beam agree; null gain |
| Final static report | [64, 64] | Exact/beam agree; null gain |
| Two-slot LMSR | [65, 65] | Exact agrees; width-2 beam finds 190/3 |
| Zero external reward | [64, 64] | Endpoint closes at root, 1 proof node vs 11 exhaustive nodes |
| Nine-slot, three controlled identities | [562/3, 194] | Two expansions, 50 proof nodes; beam matches lower bound, has no upper |

For the nine-slot fixture the endpoint root upper is 194 versus the fallback root upper 661/3; remaining certified gap is 20/3. This is a useful early-stopping bound, **not** an exact solution of the larger game. For the two-slot case both certified and ordinary exact search visit 111 nodes; no pruning improvement there. Width-2 beam visits only 30 nodes despite a transition cap of 110 because its frontier is narrow. Producer expansions, generated nodes, beam transitions and total runtime are different quantities; no equal-time or general speedup claim is justified. Verification can be as costly as producing a proof. Optional timings report solving and checking separately.

The known pilot's same executable trade loses 7/3 expected cash and earns 6 modeled external utility, for net 11/3. Funded common scores of 64 cancel. It is a known externally rewarded allocation distortion, not profitable cash-only arbitrage or an empirical discovery. The zero-external fixture certifies no profitable deviation **only within its frozen terminal suffix**, not global truthfulness. Realized luck is not the certified objective.

Resource limits bound work components, not wall time or peak memory: full engine/event histories are copied per retained state, action families expand atomically, and external knapsack has its own state limit. Endpoint enumeration is cubic in radius before the explicit box cutoff; fallback may be loose. There is no scalable polynomial exact algorithm claim. Cash/identity/price reachability relaxations, fixed subjective beliefs, existing synthetic signal limitations and conditional terminal priority constrain scientific interpretation. No unrestricted identity creation, unknown-opponent policy, repeated-game learning, welfare upper bound, live deployment forecast or final-holdout result is certified.
