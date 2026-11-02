# COPY INTO CODEX RESEARCH WORKER — Phase 5: rigorous experimental benchmark

Read approved `docs/RESEARCH.md`, dataset audit, mechanism and attack specs. Own `src/deviation/evaluation/`, experiment drivers, and results docs. Do not alter frozen final tests to make outcomes impressive.

Implement grouped task-level train/validation/test splits with stored manifests/hashes, train-only feature normalization/calibration and no direct or indirect hidden-label leakage. All feasible policies share identical tasks, costs, budgets and predecision data. Baselines include budgeted random, cheapest, best fixed affordable, learned cost-aware router, calibrated non-market forecast aggregation, market allocation and oracle analysis-only. Define oracle upper bound carefully under same budget.

Measure quality at fixed budget and quality-cost frontier, regrets, calibration, market-maker subsidy, net attacker utility and welfare loss. Include independent seeds for signals/attacks, uncertainty intervals using paired task-level bootstrap (or justified alternative), and source-level caution if tasks correlate.

Preregister assumptions and plots, then freeze test. Do not optimize final algorithm on test. Export versioned manifests, raw metrics, tables, plot data and a limitations draft. Run multiple information correlation and attacker budget regimes; document if costs are estimated rather than actual.

Deliver one-command reproducible benchmark, tests and report with **actual computed numbers**, including negative or null results. Open a PR with artifact sizes, deterministic seeds and limitations. No fabricated statistical significance or claims.
