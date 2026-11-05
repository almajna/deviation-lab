"""Exact optimization for rational choice weights; see PROTOCOL.md.

The optional CLI computes rounded Decimal exponential weights. Exact
certificates then apply to those rounded weights, not to real exponentials.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import product
import argparse
import json
from pathlib import Path

F = Fraction


def welfare(rows, outside_weight, outside_welfare, choices):
    denom = outside_weight + sum(rows[i][a][0] for i, a in enumerate(choices))
    numer = outside_weight * outside_welfare + sum(rows[i][a][0] * rows[i][a][1] for i, a in enumerate(choices))
    return numer / denom


def validate(rows, outside_weight):
    if outside_weight <= 0 or not rows or any(not row for row in rows):
        raise ValueError('outside weight must be positive; providers and actions must be nonempty')
    if any(w <= 0 for row in rows for w, _ in row):
        raise ValueError('every action weight must be positive')


def residual(rows, outside_weight, outside_welfare, target):
    choices = []
    total = outside_weight * (outside_welfare - target)
    for row in rows:
        # max() of (score,-index) makes tie-breaking deterministic.
        score, neg_index = max((w * (value - target), -index) for index, (w, value) in enumerate(row))
        choices.append(-neg_index)
        total += score
    return total, tuple(choices)


def solve_exact(rows, outside_weight, outside_welfare, max_iterations=10000):
    """Return exact rational optimum, maximizing witness, and iteration count."""
    validate(rows, outside_weight)
    target = welfare(rows, outside_weight, outside_welfare, (0,) * len(rows))
    for iteration in range(1, max_iterations + 1):
        gap, chosen = residual(rows, outside_weight, outside_welfare, target)
        if gap == 0:
            return target, chosen, iteration
        if gap < 0:
            raise ArithmeticError('negative residual at feasible welfare')
        updated = welfare(rows, outside_weight, outside_welfare, chosen)
        if updated <= target:
            raise ArithmeticError('objective failed to increase')
        target = updated
    raise RuntimeError('iteration cap reached without exact certificate')


def bracket(rows, outside_weight, outside_welfare, epsilon):
    """Exact certified bracket for the supplied positive rational weights."""
    validate(rows, outside_weight)
    if epsilon <= 0:
        raise ValueError('epsilon must be positive')
    all_outcomes = [outside_welfare] + [u for row in rows for _, u in row]
    low, high = min(all_outcomes), max(all_outcomes)
    while high - low > epsilon:
        mid = (low + high) / 2
        gap, _ = residual(rows, outside_weight, outside_welfare, mid)
        if gap > 0:
            low = mid
        elif gap < 0:
            high = mid
        else:
            return mid, mid
    return low, high


def rounded_weights(data, precision):
    """Interpret decimal inputs; independently round exp weights to precision."""
    if precision < 20:
        raise ValueError('precision must be at least 20 decimal digits')
    beta = Decimal(str(data['beta']))
    outside = Decimal(str(data['outside']))
    providers = data['providers']
    if not beta.is_finite() or beta < 0 or not outside.is_finite() or not providers:
        raise ValueError('beta must be finite/nonnegative and outside finite')
    entries = [[(Decimal(str(a['value'])), Decimal(str(a['welfare']))) for a in p['actions']] for p in providers]
    if any(not row for row in entries) or any(not v.is_finite() or not w.is_finite() for row in entries for v, w in row):
        raise ValueError('all actions must have finite values and welfare')
    shift = max([outside] + [v for row in entries for v, _ in row])
    with localcontext() as ctx:
        ctx.prec = precision
        w0 = (beta * (outside - shift)).exp()
        rows = [[(F((beta * (v - shift)).exp()), F(u)) for v, u in row] for row in entries]
    if w0 == 0 or any(w == 0 for row in rows for w, _ in row):
        raise ArithmeticError('weight underflow; do not interpret result as exact')
    return rows, F(w0), F(outside)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--precision', type=int, default=80)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    rows, w0, v0 = rounded_weights(data, args.precision)
    optimum, choices, iterations = solve_exact(rows, w0, v0)
    gap, _ = residual(rows, w0, v0, optimum)
    with localcontext() as ctx:
        ctx.prec = args.precision
        decimal_result = str(Decimal(optimum.numerator) / Decimal(optimum.denominator))
    output = {'precision': args.precision, 'beta': str(data['beta']), 'outside': str(data['outside']),
              'provider_names': [p.get('name', str(i)) for i, p in enumerate(data['providers'])],
              'action_indices': list(choices), 'welfare_decimal': decimal_result,
              'iterations': iterations, 'exact_rounded_weight_residual_zero': gap == 0,
              'scope': 'exact for independently rounded decimal weights, not certified exact real exponentials'}
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps(output, sort_keys=True))


if __name__ == '__main__':
    main()

# Rigorous interval helpers are imported by certify_real.py. The arithmetic
# uses Decimal's documented correctly rounded exp and outward adjacent values.
def _decimal_exponential_interval(exponent, precision):
    from decimal import ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN
    if precision < 20:
        raise ValueError('precision must be at least 20 decimal digits')
    with localcontext() as ctx:
        ctx.prec = precision
        ctx.rounding = ROUND_FLOOR
        x_lo = Decimal(exponent.numerator) / Decimal(exponent.denominator)
        ctx.rounding = ROUND_CEILING
        x_hi = Decimal(exponent.numerator) / Decimal(exponent.denominator)
        ctx.rounding = ROUND_HALF_EVEN
        y_lo = x_lo.exp().next_minus()
        y_hi = x_hi.exp().next_plus()
        if y_lo <= 0 or not y_hi.is_finite():
            raise ArithmeticError('exponential bounds underflow or overflow')
        return F(y_lo), F(y_hi)


def exponential_intervals(data, precision):
    """Exact Fraction intervals enclosing exp(beta*(value-shift))."""
    beta = F(Decimal(str(data['beta'])))
    outside = F(Decimal(str(data['outside'])))
    if beta < 0 or not data['providers']:
        raise ValueError('beta must be nonnegative with providers')
    values = [[(F(Decimal(str(a['value']))), F(Decimal(str(a['welfare']))))
               for a in p['actions']] for p in data['providers']]
    if any(not row for row in values):
        raise ValueError('provider with no actions')
    shift = max([outside] + [v for row in values for v, _ in row])
    w0 = _decimal_exponential_interval(beta * (outside - shift), precision)
    rows = [[(*_decimal_exponential_interval(beta * (v - shift), precision), u)
             for v, u in row] for row in values]
    return rows, w0, outside


def certificate(rows, outside_weight, outside_welfare, chosen, target):
    """Enclose ideal-exponential global optimum using exact rational bounds.

    Each action is (weight lower, weight upper, welfare). Positive lower
    bounds required. A global residual upper bound establishes the upper end;
    the feasible chosen profile establishes the lower end.
    """
    w0_lo, w0_hi = outside_weight
    if w0_lo <= 0 or w0_lo > w0_hi or len(rows) != len(chosen):
        raise ValueError('invalid outside bounds or witness length')
    if any(not row or any(lo <= 0 or hi < lo for lo, hi, _ in row) for row in rows):
        raise ValueError('invalid provider bounds')
    denominator_min = w0_lo + sum(min(lo for lo, _, _ in row) for row in rows)
    dmax = w0_hi + sum(rows[i][a][1] for i, a in enumerate(chosen))
    def low_term(lo, hi, gap):
        return (lo if gap >= 0 else hi) * gap
    def high_term(lo, hi, gap):
        return (hi if gap >= 0 else lo) * gap
    outside_gap = outside_welfare - target
    witness_low = low_term(w0_lo, w0_hi, outside_gap)
    global_high = high_term(w0_lo, w0_hi, outside_gap)
    for i, row in enumerate(rows):
        lo, hi, value = row[chosen[i]]
        witness_low += low_term(lo, hi, value - target)
        global_high += max(high_term(a, b, value - target) for a, b, value in row)
    lower = target + witness_low / (dmax if witness_low >= 0 else denominator_min)
    upper = target + max(F(0), global_high) / denominator_min
    if lower > upper:
        raise ArithmeticError('certificate endpoints inconsistent')
    return lower, upper
