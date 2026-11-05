"""Certify ideal-exponential welfare optimum for the exact decimal inputs.

Uses Python Decimal.exp's correctly rounded HALF_EVEN guarantee. It brackets
exact rational exponents using directed division, widens the exp outputs by
one adjacent Decimal in each direction, then derives exact Fraction bounds.
The numerical-model certificate excludes statistical, fitted-curve and
upstream floating-point uncertainty. See CERTIFICATE_PROTOCOL.md.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from welfare_solver import rounded_weights, solve_exact, exponential_intervals, certificate


def decimal_bound(x, prec, mode):
    with localcontext() as ctx:
        ctx.prec = prec
        ctx.rounding = mode
        return str(Decimal(x.numerator) / Decimal(x.denominator))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--precision', type=int, default=80)
    parser.add_argument('--tolerance', default='1e-15')
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    data = json.loads(raw)
    rows, w0, v0 = rounded_weights(data, args.precision)
    target, chosen, iterations = solve_exact(rows, w0, v0)
    irows, iw0, outside = exponential_intervals(data, args.precision)
    lower, upper = certificate(irows, iw0, outside, chosen, target)
    width = upper - lower
    tol = Fraction(Decimal(args.tolerance))
    if tol <= 0:
        raise ValueError('tolerance must be positive')
    if width > tol:
        raise ArithmeticError('interval certificate wider than requested tolerance; raise precision')
    result = {
        'input_sha256': sha256(raw).hexdigest(), 'precision_digits': args.precision,
        'beta': str(data['beta']), 'outside': str(data['outside']),
        'action_indices': list(chosen), 'dinkelbach_iterations': iterations,
        'welfare_lower': decimal_bound(lower, args.precision, ROUND_FLOOR),
        'welfare_upper': decimal_bound(upper, args.precision, ROUND_CEILING),
        'certificate_width_upper': decimal_bound(width, args.precision, ROUND_CEILING),
        'tolerance': str(args.tolerance),
        'meaning': 'global welfare optimum for mathematical exp of exactly encoded decimal inputs; excludes upstream/statistical uncertainty',
    }
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
