"""Offline comparison of exported published curves; see PROTOCOL.md."""
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations, product
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from welfare_solver import rounded_weights, solve_exact, residual, welfare


def decimal_string(fraction, precision=40):
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(fraction.numerator) / Decimal(fraction.denominator))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    raw_bytes = Path(args.input).read_bytes()
    raw = json.loads(raw_bytes)
    assert raw['beta'] == 1000 and raw['outside_value'] == 0
    assert raw['theta_values'] == [1, 4, 8, 16, 32, 64]
    assert len(raw['providers']) == 9 and all(len(p['actions']) == 6 for p in raw['providers'])
    data = {'beta': '1000', 'outside': '0', 'providers': [
        {'name': p['name'], 'actions': [{'value': str(Decimal.from_float(a['V'])),
                                          'welfare': str(Decimal.from_float(a['W']))}
                                         for a in p['actions']]}
        for p in raw['providers']]}
    canonical_path = Path(args.output).with_name('finite-beta-canonical.json')
    canonical_path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    # Precision applies to independently rounded exponentials; exact rational
    # certificates are only for those weights, not transcendental reals.
    solved = {}
    for precision in (80, 120):
        start = time.perf_counter()
        rows, outside_weight, outside = rounded_weights(data, precision)
        optimum, choices, iterations = solve_exact(rows, outside_weight, outside)
        gap, _ = residual(rows, outside_weight, outside, optimum)
        assert gap == 0 and welfare(rows, outside_weight, outside, choices) == optimum
        solved[precision] = (rows, outside_weight, outside, optimum, choices, iterations,
                             time.perf_counter() - start)
    rows, outside_weight, outside, optimum, choices, iterations, seconds = solved[120]
    market_profile = tuple(int(x) for x in raw['market_actions'])
    component_profile = tuple(max(range(6), key=lambda a: (rows[i][a][1], -a)) for i in range(9))
    market_value = welfare(rows, outside_weight, outside, market_profile)
    component_value = welfare(rows, outside_weight, outside, component_profile)
    assert abs(float(market_value) - raw['market_welfare']) <= 1e-10
    assert abs(float(optimum) - raw['notebook_official_global_welfare']) <= 1e-8
    assert abs(float(optimum) - raw['rerun_official_global_welfare']) <= 1e-8
    assert abs(float(solved[80][3] - optimum)) <= 1e-30
    # Independent direct float64 enumeration, not the fractional solver.
    max_subset_gap = 0.0
    subsets_checked = 0
    for subset in combinations(range(9), 3):
        subrows = [rows[i] for i in subset]
        local_optimum, _, _ = solve_exact(subrows, outside_weight, outside)
        weights = [[float(w) for w, _ in row] for row in subrows]
        outcomes = [[float(w) for _, w in row] for row in subrows]
        outside_float = float(outside_weight)
        outside_value = float(outside)
        direct = -math.inf
        for profile in product(range(6), repeat=3):
            denominator = outside_float + sum(weights[i][a] for i, a in enumerate(profile))
            numerator = outside_float * outside_value + sum(weights[i][a] * outcomes[i][a] for i, a in enumerate(profile))
            direct = max(direct, numerator / denominator)
        difference = abs(float(local_optimum) - direct)
        assert difference <= 1e-11, (subset, difference)
        max_subset_gap = max(max_subset_gap, difference)
        subsets_checked += 1
    assert subsets_checked == 84
    report = {
        'input_sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'scope': 'retrospective same-data GSM8K fitted means; no deployability claim',
        'beta': 1000, 'outside': '0', 'thetas': raw['theta_values'],
        'provider_names': [p['name'] for p in raw['providers']],
        'published_market': {'actions': list(market_profile), 'welfare_decimal': decimal_string(market_value),
                             'notebook_reported_welfare': raw['market_welfare']},
        'published_global_enumeration': {'notebook_float32': raw['notebook_official_global_welfare'],
                                         'rerun_float32': raw['rerun_official_global_welfare'],
                                         'rerun_seconds': raw['rerun_official_seconds'],
                                         'absolute_difference_from_rounded_weight_solver': abs(float(optimum)-raw['rerun_official_global_welfare'])},
        'componentwise_individual_optimum': {'actions': list(component_profile), 'welfare_decimal': decimal_string(component_value)},
        'fractional_global_optimum': {'actions': list(choices), 'theta_values': [raw['theta_values'][a] for a in choices],
                                       'welfare_decimal': decimal_string(optimum), 'precision': 120,
                                       'rounded_weight_exact_residual_zero': True, 'iterations': iterations,
                                       'seconds': seconds, 'precision_80_actions': list(solved[80][4]),
                                       'precision_80_welfare_decimal': decimal_string(solved[80][3]),
                                       'scope': 'exact for independently rounded Decimal weights, not proof of exact real-exponential weights'},
        'validation': {'three_provider_subsets': subsets_checked, 'profiles_per_subset': 216,
                       'maximum_abs_gap_float64': max_subset_gap, 'tolerance': 1e-11,
                       'market_abs_gap': abs(float(market_value)-raw['market_welfare']),
                       'official_global_tolerance': 1e-8}}
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('FINITE_BETA_AUDIT_JSON ' + json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
