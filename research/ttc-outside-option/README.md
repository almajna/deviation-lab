# Outside options in test-time compute games: mathematical audit

This is a theoretical correction candidate for [*Test-Time Compute Games*, arXiv:2601.21839v3, 18 October 2026](https://arxiv.org/html/2601.21839v3). The target is the paper's own model, Equation (7), Theorems 1–3, and Appendices C.1–C.3. This work does not demonstrate harm in a real deployment or invalidate the paper's numerical experiments or auction result. It is not external peer review, and a limited literature search cannot establish publication priority.

## Findings

1. With an explicit user outside option, the perfect-rationality function printed in Equation (7) is not always an ordinal potential. The exact two-provider example in `PROOF.md` has a unilateral utility increase of 1/2 while the printed potential decreases by ln(2), regardless of its coefficient. This only refutes the stated function: it does not refute the existence of another potential.
2. Under the same example, Theorem 2(i) predicts the wrong equilibrium compute level because its comparison omits the outside value. We give a revised necessary-and-sufficient characterization under the explicit conditions in `PROOF.md`, including a blocker condition for other higher-margin actions.
3. We give and prove an alternative generalized ordinal potential that includes the outside option as a fixed dummy participant. It requires finite actions, positive margins, and strict separation of the outside value from every feasible provider value. The dummy's margin is a proof device, not an actual payment.
4. `WELFARE_BOUND.md` gives an independently checked two-provider counterexample to the unexpanded welfare inequality in Appendix C.4, Equation (55), even though each provider has an action offering users positive value. The first-order theorem display carries a higher-order qualification; we do not present it as an unconditional exact bound.
5. `THEOREM3_TIE_NOTE.md` describes a separate sensitivity of Theorem 3 when a provider value equals the outside option. At such a tie the paper's strict indicators fail to sum to one, and the softmax limit differs; other tie rules can change the result. It does not refute a version with a consistent tie rule or no ties with the outside option.

The formal paper allows an abstention threshold and explicitly excludes ties between providers; our Theorems 1–2 example also has no ties with abstention. For the corrected general statements we explicitly impose no outside ties. See `PROOF.md` for the full case proof and assumptions. The claims are about the printed model, not an assertion that the authors intended the unrestricted domain.

## Independent verification and reproducibility

These checks are exact rational arithmetic except `verify_potential.py`, which independently checks a logarithmic form using floating point on a finite grid. Run from the repository root:

```sh
python3 research/ttc-outside-option/verify.py
python3 research/ttc-outside-option/tie_limit.py
python3 research/ttc-outside-option/verify_fraction.py
python3 research/ttc-outside-option/verify_welfare_bound.py
python3 research/ttc-outside-option/exhaustive_general.py
python3 research/ttc-outside-option/verify_potential.py
python3 research/ttc-outside-option/theorem3_exact.py
```

- The focused verifier exhausts the original four profiles and checks the published formula's sign failure.
- An independently specified finite family contains 2,520 legal two-provider games, 10,080 profiles, and 20,160 deviations; all 5,006 profitable deviations increase the corrected potential and the equilibrium characterization matches direct enumeration. `PROTOCOL.md` documents the family; it was frozen before its enumeration but after an exploratory check.
- A second implementation sampled 6,000 valid games covering 2–3 providers and 2–3 actions, then enumerated all 72,000 profiles and 345,000 deviations; the potential and equilibrium characterization passed. Seed: 771892. This is a bounded implementation check, not proof of the universal statements.
- An independent reviewer checked the proof by cases and separately enumerated 35,160 profiles for a logarithmic dummy-inclusive potential. The theorem 3 tie example and the welfare-bound counterexample were independently checked algebraically and using exact rational arithmetic.

See `results.txt` for the 2,520-game output. Run the commands above to regenerate the other summaries. No stochastic significance test, real-world extrapolation, final holdout or model inference is involved.

## Published baseline and limits

The baseline is the printed mathematical formulation, checked directly against the pinned paper version. We did not rerun the full published empirical code or independently obtain all inference traces during this audit. A previous project branch records an execution of its GSM8K notebook and independently checked best-of-N calculations; see [that reproduction report](https://github.com/almajna/deviation-lab/blob/86b41d760f0cd38208743b1d59c0cf3ef38f714f/docs/research/strategic-ttc-reproduction.md). It cannot establish that these edge cases change the published outcomes.

The published main-section numerical simulations use finite β=1000. Released GSM8K/AIME/GPQA plotted value curves were visually inspected and appeared above the outside value; this was not a numeric audit of all source data, versions, and sweeps. Thus applicability to reported results is unestablished. The outside-tie example is nongeneric and does not establish its frequency in real markets.

Repository provenance: GitHub `main` was `88bd78e29ec823b5b5d1dce4d891da7258f2c83b` with tree `43c89bf1172da0aba40fa0623d991418b91fd848`. The local isolated branch began at `630ac8e83566652d4a5dd39549cd6cdacebe21d6`, which has the identical content tree, because the current merge commit was unavailable to local Git over the restricted network.
