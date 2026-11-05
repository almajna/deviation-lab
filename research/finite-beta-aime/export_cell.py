"""Append after unchanged published best-of-N notebook cells. Offline export only."""
import copy
import json
import math
import pathlib
import time

assert len(unreasoning_providers) == 9
assert list(thetas_unreasoning) == [1, 4, 8, 16, 32, 64]
assert config.alpha == 0.05 and config.value_curve == 'linear'
assert config.baseline_frac == 0.1
assert all(len(p.accuracy_curve) == 6 and len(p.token_curve) == 6 for p in unreasoning_providers)
analysis_config = copy.copy(config)
analysis_config.beta = 1000
hist, poa, potentials, recorded_shares, welfare_history = market_dynamics_unreasoning[1000]
providers_out = []
actions = []
for provider in unreasoning_providers:
    econ = [provider.get_economics(a, analysis_config) for a in range(6)]
    rows = [{key: float(z[key]) for key in ('q', 'p', 'c', 'V', 'raw_acc')} for z in econ]
    for row in rows:
        row['W'] = row['q'] - row['c']
        assert all(math.isfinite(v) for v in row.values())
    providers_out.append({'name': provider.name, 'price_per_token': float(provider.price_per_token),
                          'margin': float(provider.margin),
                          'token_curve': [float(x) for x in provider.token_curve],
                          'actions': rows})
    actions.append(int(hist[provider.name][-1]))
started = time.perf_counter()
official_recheck = gm.get_global_max_welfare_brute_force_fast(unreasoning_providers, analysis_config, v0=0.0)
official_seconds = time.perf_counter() - started
receipt = {'protocol': 'AIME-best-of-n-published-code', 'beta': 1000,
           'outside_value': 0, 'alpha': float(config.alpha),
           'baseline_frac': float(config.baseline_frac), 'profit_margin': 0.25,
           'theta_values': [int(x) for x in thetas_unreasoning],
           'providers': providers_out, 'market_actions': actions,
           'market_final_shares': [float(x) for x in recorded_shares[-1]],
           'market_welfare': float(welfare_history[-1][1]),
           'notebook_official_global_welfare': float(welfare_history[-1][0]),
           'rerun_official_global_welfare': float(official_recheck),
           'rerun_official_seconds': official_seconds,
           'run_note': 'retrospective fitted curves, randomized better-response order'}
assert all(0 <= a < 6 for a in actions)
assert len({p['name'] for p in providers_out}) == 9
pathlib.Path('../finite-beta-input.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print('PUBLISHED_BASELINE_EXPORT_COMPLETE official_welfare', official_recheck,
      'market_welfare', receipt['market_welfare'], 'official_seconds', official_seconds)
