# Outside option and the paper's displayed PoA bound

Exploratory, synthetic counterexample to [Test-Time Compute Games v3](https://arxiv.org/html/2601.21839v3), Appendix C.4 Equation (55), for perfect rationality. This concerns the stated theoretical model, not empirical LLM results, and was independently checked by two reviewers using exact arithmetic. In particular, Theorem 4's main display is qualified by 'up to higher order terms', so the exact contradiction is to the pre-Taylor proof inequality (55); do not silently treat the first-order display as an unqualified exact statement.

For two providers, two ordered actions and outside value V0=0, let

| provider | q(low), q(high) | p(low), p(high) | c(low), c(high) | values | margins | W=q-c |
|---|---|---|---|---|---|
| 1 | 2, 41/10 | 1, 21/5 | 1/2, 6/5 | 1, -1/10 | 1/2, 3 | 3/2, 29/10 |
| 2 | 5/2, 27/10 | 23/10, 43/10 | 13/10, 7/5 | 1/5, -8/5 | 1, 29/10 | 6/5, 13/10 |

All prices and costs are positive and strictly increasing; quality is positive and increasing; margins are strictly positive and increasing. Distinct providers and V0 never tie. Both providers can offer a value greater than V0 by choosing low, but in the independently welfare-maximizing profile θ*=(high,high), both values are negative and users abstain. A stronger assumption requiring an offer above V0 specifically at θ* would exclude this example. Provider 1 is the highest-valued provider in θ*, though it is not selected. Thus W₁(θ₁*)=29/10 must not be substituted for the actual social welfare W(θ*)=0.

At either (low,low) or (low,high), provider 1 wins, welfare is 3/2, and it is a Nash equilibrium. At (high,low), provider 2 wins and welfare is 6/5; at (high,high), users abstain and welfare is 0. Therefore max profile welfare is 3/2 and the exact PoA is 1. In contrast, the provider-only terms substituted in the pre-Taylor equation (55), when β=∞ and its exponentials vanish, give (29/10)/(3/2)=29/15>1. Its intermediate bound is thus false on this game.

A one-parameter family makes the discrepancy occur arbitrarily close to the 'small welfare-gap' regime: keep all quantities fixed except set q₁(high)=27/10+ε, p₁(high)=28/10+ε for ε>0. This preserves value −1/10, the winner in every profile, the same equilibria and true PoA=1, while W₁(θ₁*)=3/2+ε. Equation (55) yields (3/2+ε)/(3/2)>1; the main display's leading expression is 1+ε/(3/2+ε). The verifier below checks the fixed example; the ε-family is an analytic argument, with three rational values separately checked by a reviewer. Actual remainder interpretation depends on constants and the paper's precise asymptotic statement; the exact Eq. (55) contradiction is the primary claim.

Reproduce using `python3 research/ttc-outside-option/verify_welfare_bound.py`; exact Fraction arithmetic checks all assumptions and unilateral deviations. The concrete displayed first-order expression is 43/29, but its stated higher-order qualification prevents calling that first-order display alone an unqualified exact bound. This illustrative case does not establish the false inequality affects the paper's published numerical benchmark.
