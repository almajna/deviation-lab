# Abstention correction to Test-Time Compute Games v3, Theorems 1–2

Status: independent mathematical audit of [arXiv:2601.21839v3](https://arxiv.org/html/2601.21839v3), not a claim of measured market harm, of refutation of every result in the paper, or of a peer-reviewed discovery. Version v3 as posted 2026-10-18; the formal model is §2, equations (2)–(4), Table 1, Theorems 1–2 and Appendix C.1–C.2. The failures below concern the printed formulation with its explicit abstention option. These two counterexamples are excluded if, at every feasible profile, some provider strictly beats the outside value.

## Standing assumptions

There are finitely many providers, N>=2, and a common finite totally ordered action set Θ. Each provider has quality q_i(θ)>=0, cost c_i(θ)>=0, price p_i(θ), offered value v_i(θ)=q_i(θ)-p_i(θ), and margin m_i(θ)=p_i(θ)-c_i(θ)>0; q_i weakly increases and p_i, c_i and m_i strictly increase with θ. For distinct providers i≠j, their achievable values never tie, and no achievable value ties the constant abstention value v0. Under perfect rationality, the provider with maximum value serves if this exceeds v0, else nobody serves. An active provider's utility is its margin; all other provider utilities are zero. Positive margins are explicit here because the original printed potential uses their logarithms. We impose the additional no-abstention-ties condition for an unambiguous statement; it is not needed by the counterexample. Weakly increasing quality and strictly increasing cost are stronger than necessary for our correction.

## Exact counterexample

Take Θ=(low,high), v0=0, and the following model inputs:

| provider | q low, high | p low, high | c low, high | v low, high | m low, high |
|---|---|---|---|---|---|
| 1 | 2, 21/10 | 1, 11/5 | 1/2, 6/5 | 1, -1/10 | 1/2, 1 |
| 2 | 1/5, 1/5 | 1, 2 | 1/2, 1 | -4/5, -9/5 | 1/2, 1 |

All stated conditions hold: q is nondecreasing, costs/prices/margins strictly increase, margins are positive, and the achievable values from different participants including v0 are pairwise unequal. Exact rational utilities and unilateral deviation gains:

| (θ1,θ2) | winner | (U1,U2) | ΔU1 from flipping | ΔU2 from flipping | equilibrium |
|---|---|---|---|---|---|
| (low,low) | 1 | (1/2,0) | -1/2 | 0 | yes |
| (low,high) | 1 | (1/2,0) | -1/2 | 0 | yes |
| (high,low) | abstain | (0,0) | +1/2 | 0 | no |
| (high,high) | abstain | (0,0) | +1/2 | 0 | no |

Theorem 2(i), as printed, predicts θ1=high because max(V2)=-4/5 and both values of provider 1 exceed -4/5; in fact both equilibria have θ1=low. The proof of Appendix C.2 implicitly assumes that a provider must win when provider 1 does not; abstention is the missing possibility.

For Theorem 1, use (high,low) -> (low,low). The acting provider's utility rises from 0 to 1/2. Equation (7) ranks *providers*, excluding abstention, so provider 1 is first and provider 2 is second in both profiles. Its printed potential changes from ln(1)+C(-4/5) to ln(1/2)+C(-4/5), a strict decrease independent of C. Thus the specific potential is not a generalized ordinal potential on the paper's full stated domain. This does not by itself establish that an ordinal potential or an equilibrium fails to exist.

## A corrected generalized ordinal potential

Treat abstention as a fixed dummy participant 0 with value v0 and a notional margin m0=1; this margin is a mathematical device, not an economic transfer or provider utility. For each profile x, order all N+1 participant values, let w(x) be the highest-value participant and r(x) the second-highest value. Let mmin,mmax be the minimum and maximum among 1 and all achievable provider margins. Let δ>0 be the minimum absolute gap between the achievable values of distinct participants, including dummy 0. Such δ exists by finiteness and the no-ties assumption. Choose any C>(mmax-mmin)/δ and define

    Φ(x) = m_w(x) + C r(x).

For a strictly profitable unilateral provider deviation, there are only two possibilities:

1. The deviator is the winning provider both before and after. Its margin increases strictly and all other participants' values are unchanged; therefore r is unchanged and Φ strictly increases.
2. The deviator was not the winner and becomes the winner. Its former utility was zero and its new utility is positive. The new second-highest value is the old winner's unchanged value. The old second-highest value was at least δ below the old winner, so r rises by at least δ. The margin term can decrease by at most mmax-mmin, and hence Φ strictly increases by more than zero. This case also covers an old abstention winner.

A winning provider cannot profit by becoming a loser, since its original margin was positive; a losing provider cannot profit while remaining a loser. Therefore Φ is a generalized ordinal potential and finite better-response paths terminate. This proves existence of a pure Nash equilibrium under the specified assumptions; a tie case or nonpositive margins requires a separate result.

## Corrected equilibrium characterization

Let v_i*=max_θ v_i(θ), index the unique provider with largest maximum as d, and let T=max(v0, max_{j≠d} v_j*). By distinctness of cross-participant achievable values, no maximum ties v0 or another provider maximum.

- If v_d*<v0, every possible provider value is below v0; users always abstain and every profile is a Nash equilibrium.
- If v_d*>T, write θsafe=max{θ∈Θ : v_d(θ)>T}. A profile x is a Nash equilibrium **if and only if** (a) x_d=θsafe, and (b) every θ with m_d(θ)>m_d(x_d) has v_d(θ)<max(v0,max_{j≠d}v_j(x_j)).

Necessity: If d is not serving, d can deviate to an action attaining v_d* and obtain a strictly positive margin. If d serves with value below another provider j's maximum, j can deviate to its value-maximizing action and win with positive margin. Thus d's value must exceed both v0 and all other provider maxima. Since margin strictly increases in θ, d must select the largest action whose value still exceeds T; otherwise moving to that action is profitable regardless of rival current actions. Finally, any strictly higher-margin action beating v0 and all current rivals would be profitable, giving (b).

Sufficiency: At x_d=θsafe, d beats v0 and all competitors' maxima, so no competitor can win by deviating. Provider d cannot gain by selecting a lower-margin action; by (b), no higher-margin action wins against v0 and the rivals' current values. Thus no unilateral deviation increases utility. These are exact logical conditions, not a claim that the result applies when values tie or margins are nonpositive.

## Bounded execution

`PROTOCOL.md` specifies the finite family and complete enumeration before its execution; the earlier seeded 20,000-game check was exploratory. `python3 verify_fraction.py` enumerated 2,520 admissible two-provider games, 10,080 profiles, and 20,160 deviations (5,006 strictly profitable), with exact rational arithmetic. The corrected potential increased in all profitable deviations; the characterization agreed with direct equilibrium enumeration on all profiles. It also independently reproduced the four-profile counterexample. This is a finite checker, not the proof of the universal assertions above. Complete raw output is `results.txt`; checker SHA-256 `21b7ce3780ce1c3ad3f2d4fcf8148df88ea2083e4244b8a4cbc46b30c8aaa4fc`.
