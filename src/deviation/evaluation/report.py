"""Aggregate tables and an evidence-bound technical report; raw data excluded."""
import csv
import json


def render(result, path):
    recorded=result['recorded'];synthetic=result['synthetic']
    table=[]
    if recorded:
        for r in recorded['summary']:
            q=r['quality'];d=r['difference_vs_calibrated_pool']
            table.append({'track':'RECORDED_OUTCOMES_SYNTHETIC_FORECASTERS','condition':r['budget_fraction'],
                'mechanism':r['mechanism'],'mean_quality':q['estimate'],'quality_lower':q['lower'],'quality_upper':q['upper'],
                'difference_vs_calibrated_pool':d['estimate'],'difference_lower':d['lower'],'difference_upper':d['upper'],
                'regret':r['regret'],'brier':r['brier'],'reservation_spend':r['reservation_spend'],
                'realized_historical_spend':r['realized_spend'],'batch_violation_fraction':r['batch_budget_violation_fraction'],
                'clusters':q['clusters'],'reliability_bins':r['reliability_bins'],'mean_batch_calibration_abs_error':r['calibration_abs_error']})
        with (path/'recorded_table.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    st=[]
    for r in synthetic['summary']:
        st.append({'track':'WHOLLY_SYNTHETIC','profile':r['profile'],'mechanism':r['mechanism'],
            'mean_utility_gain':r['utility_gain']['estimate'],'lower':r['utility_gain']['lower'],'upper':r['utility_gain']['upper'],
            'cash_gain':r['cash_gain']['estimate'],'external_gain':r['external_gain']['estimate'],
            'mean_proxy_loss':r['welfare_loss']['estimate'],'rerouted_fraction':r['rerouted_fraction']['estimate'],
            'zero_external_gain':r['zero_external_gain']['estimate'],'worlds':r['worlds'],
            'interpretation':r['profitability_interpretation']})
    with (path/'synthetic_table.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(st[0]));w.writeheader();w.writerows(st)
    lines=['# Phase 5 exploratory research report','',
        '**Exploratory validation, not final evaluation or evidence of general superiority.**',
        'Recorded LLM judged outcomes are distinct from synthetic forecasting/trading behavior. Quality is a noisy preference proxy; historical costs are not bills or deployable savings.', '',
        f"Protocol `{result['protocol_sha256']}`; source `{result['implementation_sha256']}`; result `{result['sha256']}`.",
        'Independent protocol review preceded evaluation; frozen selection uses separate development worlds. No final cohort was provisioned or accessed; existing exploratory test split was excluded.','']
    if recorded:
        lines+=['## Recorded-outcome validation','',
            f"Train {recorded['provenance']['training_tasks']} tasks; validation {recorded['provenance']['validation_tasks']} tasks; excluded exploratory test {recorded['provenance']['excluded_exploratory_test_tasks']}. Four historical model arms, one selected coding-domain cohort. OOF training temperature: {recorded['temperature_train_oof']}.",
            'No current-task outcome/cost generated a forecast. Four training-shard forecasters and the union-information text-router use public prompts and training rows only. All ordinary plans lock before any current outcomes are read. Oracle is a separate analysis-only invocation.','',
            '| Budget fraction | Mechanism | Mean proxy | Delta vs calibrated pool [95% interval] | Oracle regret |',
            '|---|---|---:|---:|---:|']
        for r in recorded['summary']:
            d=r['difference_vs_calibrated_pool']
            lines.append(f"| {r['budget_fraction']} | {r['mechanism']} | {r['quality']['estimate']:.4f} | {d['estimate']:+.4f} [{d['lower']:+.4f}, {d['upper']:+.4f}] | {r['regret']:.4f} |")
        lines+=['','Intervals resample eight fixed budget batches after averaging schedule seeds, using task-count weighted ratios. They describe conditional batch variation, not population/source-family generalization or globally reoptimized bootstrap budgets. Thirty-one tasks and eight clusters are weak evidence; exact prompt grouping does not resolve semantic duplicates. All contrasts are exploratory, no p-values or multiplicity-adjusted winner claim.',
            '','`recorded_table.csv` and results.json retain reported historical spend, overruns, unused reservations, budget violations, reservation utilization, fees, maker funding/P&L, score reserve/payout and calibration. Reliability bins and mean per-batch bin absolute error are descriptive calibration diagnostics, distinct from Brier accuracy. Calibration for cheapest/random/best-fixed/oracle is the common pooled-report diagnostic, not a probabilistic forecast produced by those route rules. Fixed-route tie/zero rescoring is a descriptive ambiguity sensitivity, not recovered judge status or a different optimized objective.','']
    lines+=['## Synthetic generalization and strategic controls','',
        f"{len(synthetic['rows'])} paired validation world/mechanism cases; every schedule supported. Twenty finite policy templates were enumerated on four separate development worlds per mechanism/incentive condition, then frozen for seven unseen-profile conditions and eight validation worlds each. No validation strategy reselection or negative-gain clamping.",
        '','| Profile | Mechanism | Utility gain [95% MC interval] | Cash gain | External gain | Proxy loss | Zero-external gain |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in synthetic['summary']:
        g=r['utility_gain']
        lines.append(f"| {r['profile']} | {r['mechanism']} | {g['estimate']:+.3f} [{g['lower']:+.3f}, {g['upper']:+.3f}] | {r['cash_gain']['estimate']:+.3f} | {r['external_gain']['estimate']:+.3f} | {r['welfare_loss']['estimate']:+.3f} | {r['zero_external_gain']['estimate']:+.3f} |")
    positive=sum(r['utility_gain']['lower']>0 for r in synthetic['summary'])
    lines+=['',f'{positive} of {len(synthetic["summary"])} profile/mechanism intervals have a positive lower endpoint. These are unadjusted exploratory Monte Carlo intervals, not global-optimum certificates, validated real-world exploits or a population failure rate.',
        '','The likelihood generator gives initial own-observation Bayes forecasts; after report reveal, references are fixed-belief myopic policies, not Bayesian equilibrium traders. Nature outcomes are never given to posterior formation or policy packets. The optimizer sees development completed payoffs; validation seeds/outcomes do not enter selection. Sample-average winner selection can overfit four development worlds. No full-game optimality or expected-profit proof follows.',
        '','The fixed h0/h1/z0/z1 registry preserves all report weights, information, sponsor funding, controller cash/caps and controller turn-cell opportunities when splitting one versus two active accounts. Capital/slot partition changes; new unrestricted identities are not created. This eliminates the earlier funding/turn confound for the specified comparison, but does not establish a general Sybil theorem or heterogeneous-information coalition behavior.',
        '','## Reproduction and review','',
        'Run the reviewed evaluation CLI with the pinned source/split manifests and a local cache, then scripts/plot_benchmark.py for scientific figures. Raw data is not redistributed. results.json contains aggregate recorded batches, every synthetic case, development candidate objectives, code/config/source hashes and a complete first-declared synthetic sample chosen regardless of outcome. All cash/payoff receipts are checked against an independent event-ledger reconstruction. Independent skeptical actual-code review and hosted CI are linked in the PR.',
        '','## Remaining research limitations','',
        'Small single-source selected development cohort; historical judging failures mixed with zero; unresolved reported-cost provenance; complete-case selection; weak fixed text forecasters; intrinsic differences between trade/update action spaces; fixed-belief post-reveal policies; narrow finite attack class and small Monte Carlo sample; conditional rather than deployment uncertainty; no semantic-family holdout or final untouched cohort. Negative/null results are retained. These limit claims rather than justify manufacturing improvements. $0 paid spend; no frontend or shared-contract edits. Human review and merge remain required.']
    (path/'REPORT.md').write_text('\n'.join(lines)+'\n')
    (path/'plot_data.json').write_text(json.dumps({'recorded':table,'synthetic':st},indent=2,sort_keys=True)+'\n')
