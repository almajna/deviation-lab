# Independent certificate evaluation — development protocol

Owner: Agent 2; issue #22, coordinating with Agent 1 in #20. All inputs are
synthetic development fixtures. No recorded cohort or final holdout is loaded.
This document is frozen before numerical evaluation. The protocol commit is
recorded in the result manifest. Later changes must be disclosed separately.

## Questions and success criteria

1. **Correctness (mandatory):** every accepted certificate must contain the
   independently replayed feasible incumbent and an upper bound covering every
   legal continuation in its stated finite subgame. On every completed independent
   exhaustive case, lower <= exact optimum <= upper, in exact rational arithmetic.
   Completed zero-gap certificates must equal that optimum. Any violation fails
   the experiment; do not remove the row.
2. **Adversarial checking (mandatory):** reject wrong game/resource bindings,
   missing or duplicated branches, altered incumbent commands/payoffs, reduced
   upper bounds and inconsistent rational encodings even after rehashing. A
   solver transcript hash alone is insufficient.
3. **Useful certification (contingent):** report the fraction closing the gap,
   absolute gap, proof bytes, visited states, engine transitions and separately
   measured generation/check time. We claim a practical improvement only if the
   paired median end-to-end time (generation + independent check) is at most
   0.8 times a completed exact baseline on the same solved nontrivial cases, with
   at least 10 cases. Timing samples are descriptive, not independent economic
   observations. Fewer cases or a missed threshold is inconclusive/negative.
4. **Search quality (contingent):** compare incumbent utility against ordinary
   beam search with the same configured expansion cap, and against independent
   exhaustive enumeration and exact memoized dynamic programming where complete.
   Report expansions AND work/time; expansion units differ across algorithms.
   Equal quality is not an algorithmic novelty claim.
5. **Stress/generalization:** define base and stress profiles before execution;
   apply identical fixed settings, without fitting or selecting settings using
   stress results. These are synthetic out-of-profile tests, not a sealed final
   holdout or population generalization experiment.

## Frozen experiment

`experiments/certificate_benchmark.json` specifies profiles, seeds, mechanisms,
search caps and timing repetitions. Fixtures are constructed independently of
Agent 1's optimizer and the Phase 4 environment generator. Public schedules have
an explicitly constructed controlled suffix; no seed is searched to find a
supported suffix. This conditions all results on terminal priority. Report games
use one final controlled commitment and a public deterministic opponent model.

The fixture registry has fixed two strategic accounts even when only one acts;
aggregate starting cash, score tokens, controller caps and total optional slots
are unchanged within an identity-allocation comparison. Both accounts share the
same belief. These cases test controlled coalition execution, not free Sybil
registration or heterogeneous information pooling.

Synthetic beliefs are prescribed predecision distributions, independent of any
realized label. Their sharpness and alignment vary; they are not claimed Bayesian
posteriors. All decisions and certificates see only the outcome-free Game.
No welfare or calibration claim is inferred from their subjective utility.

## Comparators and measurement

Independent enumeration builds the integer action lattice itself and executes
the actual engine. Its objective expands Brier rewards directly and independently
solves the budgeted allocation; it never calls Game.expected, the attack objective,
or certificate bounding helpers. Exact dynamic programming merges only states
with identical future economic consequences and uses the same independent
objective. Both have explicit state limits: incomplete runs are censored,
not exact answers. Ordinary beam search is the unchanged merged implementation.

All solvers get the same Game, finite legal action space and objective. Report
absolute controller utility and gain over no-action separately: common funded
scores can dominate absolute levels. Fees enter cash once; external allocation
utility and effort remain separate. Synthetic reservation units and virtual
credits are never combined. The checker trusts the existing deterministic engine
and certified numeric primitives, not the optimizer or its bound routines.
It is a distinct mathematical implementation, not a formally verified theorem.

One warm run plus three timed repeats are planned; retain all raw times, use the
median per case, report min/max and paired case bootstrap intervals with 2,000
draws and seed 991. Fixtures are the unit of comparison. Grid/seed intervals
describe this finite suite, not a sampled real-world population. Deterministic
utilities require exact agreement, not sampling intervals. Timings are excluded
from byte-for-byte result comparison; all economic/proof/count fields are checked.

## Interpretation and limits

Branch-and-bound, anytime bounds, rational proof checking and state memoization
are established techniques. VIPR (Cheung, Gleixner and Steffy, IPCO 2017) explicitly
separates optimization and verification; see
https://arxiv.org/abs/1611.08832 and https://github.com/scipopt/vipr.
No direct VIPR runtime comparison is meaningful without a faithful MILP encoding
of integer-ceiling LMSR charges, certified projected prices and deterministic
allocation tie rules. This suite compares exact finite-engine algorithms, not
state-of-the-art generic MILP performance. Outside-incentive manipulation is also
known: https://projects.iq.harvard.edu/files/yiling/files/manipulation-aaai11.pdf.

A defensible contribution here could be independently verified executable bounds
over these engine-specific finite games. Neither passing tests nor a synthetic
speedup establishes a new optimization algorithm or an economically new attack.
Unsupported scopes, loose bounds, censored search, weak speedups and failure of
transfer beyond these fixtures must be disclosed. Independent scientific review
must challenge this protocol and the implementation before any release claim.
