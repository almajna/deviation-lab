# Evidence-based release acceptance

**Ship threshold**: at least 90/100 on the objective rubric AND no critical blockers AND human release approval. The number is an **internal quality audit**, not a guarantee of an external 8.5/10 reputation score, academic novelty or publication.

## Scoring (reviewer must link proof; no self-assigned credit)

| Category | Max | Evidence required for full points |
|---|---:|---|
| Empirical grounding | 20 | Audited paired LLM outcomes, provenance/cost semantics, clean splits, exact task/model overlap, credible data loader |
| Economic correctness | 15 | Formal incentives, payments, finite liquidity, settlement tests, feasibility, information barrier, baseline parity |
| Adversarial testing | 20 | Four documented attacker families, exhaustive small-game check, heuristic larger search, counterexample replay, negative controls |
| Evaluation integrity | 20 | Prespecified metrics, strong market/non-market baselines, clean holdout, intervals, real-vs-synthetic labels, no oracle leakage |
| Visual laboratory | 15 | Three interactive views using actual logs, pause/step/compare, truthful figures, accessible and responsive, performance checks |
| Reproducibility & OSS | 10 | Clean setup on new machine, passing CI, pinned environments/seeds, licensed dependencies, research report, public docs |
| **Total** | **100** | **Target >=90 and all critical gates** |

## Mandatory critical gates (failure blocks release even at 100)
1. No outcome leakage or unfair baseline comparison.
2. Real recorded outcomes actually verified; any unverified experiment prominently SYNTHETIC.
3. At least one reproducible nontrivial strategic deviation with valid payoff accounting (can be known/constructed vulnerable reference mechanism; must say so).
4. Frozen held-out testing for headline mechanism-search claims.
5. No fake visual data, undisclosed substitutions, or invented scientific result.
6. No critical security issue: no secrets, no unsafe code execution, no unauthorized cloud spending.
7. Independent cold-install reproducibility and independent scientific review; issues addressed.
8. Explicit human approval of final publication.

## Proof artifacts required in release candidate
- `artifacts/data_audit.json`, `artifacts/data_manifest.json`, `artifacts/splits.json` (paths may differ; documented manifest mandatory)
- `artifacts/reproduction_commands.txt` and experiment config/seed/code hashes.
- `artifacts/replays/*.json` with a hand-checkable counterexample and source mechanism.
- `artifacts/results/` tables plus bootstrap or appropriate uncertainty summary.
- Browser screenshots, accessibility report and build/test logs.
- Independent reviewer report with labeled severity and responses.
- `docs/REPORT.md` with conclusion, null results and limitations.

## External 8.5+ calibration (cannot be guaranteed)
Before calling the release 'flagship quality', ask 2–3 technically literate outsiders to independently rate: research trustworthiness, usability, visual quality, clarity and genuine usefulness. Record strengths and weaknesses without filtering negative responses. Improve the artifact if ratings are low; don't change the grading rubric midstream merely to pass.
