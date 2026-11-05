# Exact and certified global welfare under finite-rationality choice

## Scope and original source

The published [Test-Time Compute Games v3, Eq. 5](https://arxiv.org/html/2601.21839v3) defines welfare for a single type of user, independent finite provider choices, the multinomial-logit market share, and outside option V0. Let v_ia be value, u_ia=q_ia-c_ia be provider welfare contribution, w_ia=exp(βv_ia)>0, w0=exp(βV0)>0. For one action a_i per provider, the exact global welfare objective is

`R(a) = [w0 V0 + Σ_i w_i,a_i u_i,a_i] / [w0 + Σ_i w_i,a_i]`.

Each provider contributes only its selected action. This is a full-information counterfactual optimization over provider action profiles, not an equilibrium, a deployable policy or a proof that providers will cooperate. It is narrower than games with coupled constraints, multiple user classes, endogenous entry, or unknown empirical inputs. A global monetary/utility unit must be consistent across all terms. β=0 is permitted mathematically; β>0 is the paper's finite-rationality case. This reduction applies standard [fractional programming (Dinkelbach 1967)](https://doi.org/10.1287/mnsc.13.7.492) and close related [MNL assortment optimization](https://researchportal.hkust.edu.hk/en/publications/assortment-planning-under-the-multinomial-logit-model-with-totall/); it is not claimed as a novel general algorithm or first application to choice models.

For any target λ, define

`F(λ) = w0(V0−λ) + Σ_i max_a w_ia(u_ia−λ)`.

A profile independently attaining every maximum also maximizes the sum `numerator−λ denominator` among all profiles. Since every feasible denominator is strictly positive, `F(λ)>0` iff some profile has `R(a)>λ`, `F(λ)=0` iff λ equals the global optimum, and `F(λ)<0` iff every profile has lower welfare. Thus bisection on λ between the least and greatest component reward certifies any desired objective tolerance using O(T log((U−L)/ε)) exact arithmetic/comparison operations, where T is total actions. This is not a bit-complexity bound or guarantee on computing exponentials.

Alternatively, start at any feasible profile welfare λ. Select per-provider maximizers in F(λ) and update λ to that selected profile's exact welfare. If F(λ)>0, the new feasible welfare is strictly larger. If F(λ)=0, λ is globally optimal. There are finitely many profiles, so this process terminates with an exact rational answer for exact positive rational weights. The number of iterations may be exponential in provider count; no polynomial iteration bound is asserted. Ties are broken by first action. The solver fails closed if its explicit iteration cap is exceeded.

## Bounding real exponentials for encoded inputs

`certify_real.py` treats input decimal strings as exact numbers; these may exactly encode binary64 if exported with `str(Decimal.from_float(float(x)))`. Choose one fixed shift `S=max(V0, all v_ia)` and represent weights as exp(β(v−S)); common positive scaling preserves R. Compute the exponent as an exact rational, then enclose it with floor/ceiling Decimal division. Python [`Decimal.exp`](https://docs.python.org/3/library/decimal.html#decimal.Decimal.exp) is correctly rounded using ROUND_HALF_EVEN. Monotonicity and one adjacent representable Decimal outward from each endpoint provide weight intervals `[w^-,w^+]`; a nonpositive lower bound or overflow aborts. Convert bounds to exact Fractions.

Take any rational λ and any feasible witness profile, here obtained by exact optimization over nearby rounded weights. For each signed coefficient `(u−λ)`, the maximum allowed weight contribution is `w^+(u−λ)` if nonnegative and `w^-(u−λ)` otherwise. The global residual is at most `F^+`, computed by maximizing these interval upper contributions independently per provider, plus the corresponding outside contribution. Every profile denominator is at least `D_min=w0^-+Σ_i min_a w_ia^- >0`. Hence the true optimum is at most `λ + max(F^+,0)/D_min`.

For the selected witness, compute a residual lower bound G^- by the reverse endpoint selection. Its denominator is at least D_min and at most D_witness_max. If G^-<0 then the witness welfare is at least `λ+G^-/D_min`; if G^-≥0 it is at least `λ+G^-/D_witness_max`. The witness is feasible, so that value lower-bounds the global optimum. All sign decisions and fractions in the certificate are exact. The CLI prints outward-rounded decimal lower/upper values and fails if the rigorous width exceeds its requested tolerance. These bounds cover the mathematical exponentials of the **exactly encoded input values**; they do not cover statistical uncertainty, input fitting, numerical error already incurred upstream, or distribution shift.

## Tests and limitation on originality

`test_welfare.py` checks 4,000 generated rational-weight games, all 358,800 action profiles, exact value and witness, residual zero, certified bisection width, global weight-rescaling invariance, equal-weight beta=0 case, tie behavior and positive-weight rejection. No p-values are reported. For the actual paper's published empirical comparison, see the separate frozen pipeline if its datasets and runner are available; synthetic games alone do not show a real-world effect. The best existing published brute-force routine enumerates all K^N profiles; our mathematical reduction does not by itself establish novelty against historical fractional or MNL optimization literature.
