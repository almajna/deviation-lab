# Independent certificate semantics and reproduction

Issue #22, Agent 2. Producer dependency: Agent 1 PR #23, exact source commit
3151edb463484498a5b686bf607dff4f062d66a4. Its files are imported unchanged. This
branch is stacked on that implementation; review the Agent 2 diff separately.

## What is independently implemented

`src/deviation/verification/` rebuilds the finite action alphabet from integer
lattice/simplex enumeration, transitions via the real engine, Brier expectations,
controller cash/claims/effort/external utility, budgeted allocation, endpoint
upper bounds and complete proof-tree checking. It imports no producer action,
optimizer, payoff or bounding helper. The benchmark driver imports the producer
only to obtain the certificates it tests. Tests disable producer helpers and
Game.expected/Game.allocation while independent checking continues to work.

Shared trusted dependencies are the existing Engine, certified numeric quote and
projected-price routines, probability transform, reservation receipt and canonical
hash serialization. Those dependencies are disclosed; independence is neither
hostile-code sandboxing nor a formally verified numerical kernel. The fixture
builder uses Game as a data carrier and constructs valid Engine states directly,
with public schedules and predecision synthetic beliefs. It loads no outcome file.

## Bound derivation

For a cell, let current total shares be q and controlled shares h; outsider
shares q-h are fixed throughout the declared suffix. If R non-exhausted slots
remain and each order has L1 norm at most Q, every reachable final holding H has
L1 distance at most RQ from h. Its coordinate bounds include nonnegativity,
aggregate controller positions, pooled account limits and the cell total limit.
Dropping intermediate solvency and identity-specific paths enlarges the set.

The engine charges ceil(C(q_next)-C(q_now)) per accepted trade. Summing and
telescoping gives a charge at least ceil(C(q_final)-C(q_initial)). At least
ceil(norm(H-h,1)/Q) fee-paying trades are required. Thus, at the controller's
fixed belief p, the relaxed cash gain is bounded above by the maximum of

`p dot (H-h) - ceil(C(q+H-h)-C(q)) - fee*ceil(norm(H-h,1)/Q)`.

The independent code enumerates final holdings H, rather than the producer's
delta parameterization. A numerically ambiguous relaxed quote uses min(H-h)
as a weaker lower bound on the potential change; it never omits the endpoint.
If its bounding box exceeds the published enumeration limit, each actual order
has expected payoff less than or equal to Q before nonnegative fees, yielding
the safe RQ fallback. Bounds sum over cells. A separate exact integer-budget DP
maximizes the controller's external allocation reward, allowing any reservation-
feasible allocation. This ignores price reachability and is therefore a relaxation.

Current cash includes prior wallet deltas, existing expected claims and the
fixed original scoring obligations. Mutable report revisions never earn a second
score. A final report's maximum expected quadratic score is attained at the
controller's integer belief: scale*(D^2+sum(p_k^2)). Future mandatory consumed
slots incur effort even when exhausted no-ops are rejected. Fees enter cash once.
Weights and fees are nonnegative under the approved engine contract.

## Why a checked tree implies its interval

Each split independently covers every admissible canonical command exactly once.
Leaves either independently recompute terminal utility or the safe relaxed upper
bound above. Induction from those leaves bounds every legal continuation from
the trusted root. Repeated/shared/cyclic/unreachable nodes are rejected. The
maximum leaf bound is an upper bound. Independently replayed complete incumbent
commands provide an attainable lower bound. A zero gap therefore proves the
optimum of this finite subjective-utility subgame, under the stated trusted base.

The scope is a common-belief controlled terminal suffix or final static report,
not a full dynamic game, unknown opponent policy or equilibrium. Root states are
trusted, canonical generated-prefix Games. Arbitrary histories pre-reserving a
future generated order ID are unsupported; Game identity hashes do not certify
valid source data or authenticate a submitted root. A command-ID collision causes
rejection rather than an invented successful action.

## Independent exact dynamic programming

The memo key retains turn, pending report slots, all wallets/maker balances,
aggregate q and per-account holdings, attempts, mutable reports and original
commitments. Per-solve config, beliefs, tasks, schedule and initial balances are
fixed. Canonical command IDs depend on turn; sequence numbers and receipts are
rebound to the actual replay path. Revenue/history do not affect future acceptance
or utility beyond retained balances/portfolios under this canonical suffix.
Returned plans are independently replayed and their values checked. The test
suite compares this state merging against the full unmerged tree, including
repeated markets and owned sales. A state cap produces a censored status, never
an optimality claim. This is standard finite-horizon DP, not a new algorithm.

## Source-bound artifacts and review limits

Adding an independent package changes the producer's whole-package source hash.
New proofs/results deliberately bind the integrated source. Old receipts/proofs
are preserved byte-for-byte and reproduced at their historical source; they are
never silently relabeled. The checker can check a known historical proof with an
explicit expected historical source hash supplied by a trusted caller. Defaults
require the current package hash. The published pilot proof is checked with the
pinned producer source b016e0178a67cc9834c0c6f6c409568de6df31e4b95baa5e95a61655152aef75.

The frozen development protocol specifies the scientific criteria and exact grid.
State caps are not wall-time or memory caps. Failure checkpoints and stderr are
evidence, not permission to omit cases. Timing variation is retained separately
from deterministic mathematical values/proofs. Neither passing tests nor the
agent review is external peer review or a human release approval.
