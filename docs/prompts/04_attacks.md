# COPY INTO CLAUDE CODE ATTACK WORKER — Phase 4: reproducible exploit discovery

Read canonical project docs and approved mechanism math. Work in `feat/attacks` and own `src/deviation/attacks/` and tests. Do not use hidden ground-truth outcomes in attackers' information unless an explicit known-information scenario permits it.

Implement attacker utility net of all payments/trading costs plus documented external payoff. Baseline honest/reference strategy must be explicit. Include bounded report misrepresentation, coalition/collusion, Sybil under permissive identities, and repeated reputation/sandbagging in a separately modeled repeated game. Test feasibility constraints and budgets.

Small game: exhaustive search over a declared finite action space; produce exact best-response payoff and verify the discovered counterexample by independent arithmetic. Large game: reproducible random/local/Optuna search, marked 'best found' not optimal. Add at least one vulnerable reference mechanism with a *known constructed* attack so the demo has a guaranteed valid replay; add hard/no-exploit controls to catch false positives.

For each discovery export full configuration, allowed information, attacker action, baseline and attack payoffs, system welfare delta, seed, cost/subsidy ledger and event log. A counterexample is invalid if its attacker uses unrealizable actions or if savings are illusory.

Open a PR with reproducible tests and a one-command attack replay. If none of the realistic mechanisms are exploitable under tested constraints, report that honestly rather than inventing a breakthrough.
