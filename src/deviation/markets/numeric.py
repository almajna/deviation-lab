"""Certified dyadic enclosures; no binary floating-point transcendental calls.

Every endpoint is an integer / 2**bits. Multiplication/division round outwards.
exp(-x) uses alternating Taylor bounds after halving to x<=1/2, then squares.
log(x), 1<=x<=4, uses the positive atanh series and a geometric tail bound.
"""
from fractions import Fraction
from functools import lru_cache
from math import isqrt

from deviation.contracts import ContractError
from deviation.data.pipeline import digest

POLICY = {"version": "dyadic-series-1", "bits": [64, 128, 256],
          "max_coordinate": 1_000_000, "categories": 3}
POLICY_SHA256 = digest(POLICY)


class NumericAmbiguity(ContractError):
    pass


def up(n, d):
    return -(-n // d)


def integer(v, low=0, high=1_000_000):
    if type(v) is not int or not low <= v <= high:
        raise ContractError("invalid bounded integer")


def vector(q):
    if not isinstance(q, (list, tuple)) or len(q) != 3:
        raise ContractError("three coordinates required")
    for n in q: integer(n)


def _exp_negative(x, bits):
    """Exact alternating-series bracket, quantized once before squaring."""
    S, halves = 1 << bits, 0
    while x > Fraction(1, 2):
        x /= 2
        halves += 1
    term, total = Fraction(1), Fraction(1)
    for n in range(1, bits + 20):
        term *= -x / n
        previous = total
        total += term
        if abs(term) < Fraction(1, S * 8):
            lo, hi = min(previous, total), max(previous, total)
            a, b = lo.numerator * S // lo.denominator, up(hi.numerator * S, hi.denominator)
            for _ in range(halves):
                a, b = a * a // S, up(b * b, S)
            return a, b
    raise NumericAmbiguity("exp enclosure exhausted")


def _log_point(x, bits):
    """ln(x/S) for fixed integer x>=S, via 2*atanh((x-S)/(x+S))."""
    S = 1 << bits
    if x == S: return 0, 0
    if not S <= x <= 4 * S:
        raise NumericAmbiguity("log enclosure domain")
    tl, th = (x - S) * S // (x + S), up((x - S) * S, x + S)
    square_lo, square_hi = tl * tl // S, up(th * th, S)
    pl, ph, sl, sh = tl, th, 0, 0
    for n in range(bits * 2):
        odd = 2 * n + 1
        sl += pl // odd
        sh += up(ph, odd)
        pl, ph = pl * square_lo // S, up(ph * square_hi, S)
        tail = up(2 * ph * S * S, (odd + 2) * (S * S - th * th))
        if tail <= 4:
            return 2 * sl, 2 * sh + tail
    raise NumericAmbiguity("log enclosure exhausted")


@lru_cache(maxsize=8192)
def _weights(q, b, bits):
    shift = max(q)
    return tuple(_exp_negative(Fraction(shift - n, b), bits) for n in q)


@lru_cache(maxsize=8192)
def _potential(q, b, bits):
    S = 1 << bits
    weights = _weights(q, b, bits)
    lo, hi = sum(x[0] for x in weights), sum(x[1] for x in weights)
    a, _ = _log_point(lo, bits)
    _, z = _log_point(hi, bits)
    return max(q) * S + b * a, max(q) * S + b * z


def _endpoints(lo, hi, bits):
    # Dyadic fractions have a finite decimal representation, exactly.
    def dec(n):
        sign = "-" if n < 0 else ""
        digits = str(abs(n) * 5 ** bits).rjust(bits + 1, "0")
        return sign + digits[:-bits] + "." + digits[-bits:]
    return [dec(lo), dec(hi)]


def quote(before, after, b, *, precisions=None):
    vector(before); vector(after); integer(b, 1)
    shifts = [a - z for a, z in zip(sorted(after), sorted(before))]
    if len(set(shifts)) == 1:
        # Permutations and common translations have exact potential differences.
        return {"charge": shifts[0], "interval": [str(shifts[0])] * 2,
                "bits": 0, "policy_sha256": POLICY_SHA256}
    for bits in (precisions if precisions is not None else POLICY["bits"]):
        if bits not in POLICY["bits"]: raise ContractError("unsupported precision")
        S = 1 << bits
        al, ah = _potential(tuple(after), b, bits)
        bl, bh = _potential(tuple(before), b, bits)
        lo, hi = al - bh, ah - bl
        if up(lo, S) == up(hi, S):
            return {"charge": up(hi, S), "interval": _endpoints(lo, hi, bits),
                    "bits": bits, "policy_sha256": POLICY_SHA256}
    raise NumericAmbiguity("NUMERIC_AMBIGUITY")


def funding(b):
    return _funding(b)


@lru_cache(maxsize=128)
def _funding(b):
    integer(b, 1)
    for bits in POLICY["bits"]:
        lo, hi = _potential((0, 0, 0), b, bits)
        if up(lo, 1 << bits) == up(hi, 1 << bits): return up(hi, 1 << bits)
    raise NumericAmbiguity("funding enclosure ambiguous")


def project_rational(weights, P):
    integer(P, 3, 100_000_000)
    if len(weights) != 3 or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ContractError("invalid probability weights")
    values = [Fraction(w) * P / sum(weights) for w in weights]
    counts = [v.numerator // v.denominator for v in values]
    order = sorted(range(3), key=lambda i: (-(values[i] - counts[i]), i))
    for i in order[:P - sum(counts)]: counts[i] += 1
    return counts


def _project_intervals(weights, equal, P, bits):
    S = 1 << bits
    sl, sh = sum(w[0] for w in weights), sum(w[1] for w in weights)
    if sl <= 0: raise NumericAmbiguity("normalization enclosure")
    intervals = [(w[0] * S // sh, up(w[1] * S, sl)) for w in weights]
    counts = [lo * P // S for lo, hi in intervals]
    if any(hi * P // S != counts[i] for i, (lo, hi) in enumerate(intervals)):
        raise NumericAmbiguity("price floor ambiguous")
    remainders = [(lo * P - counts[i] * S, hi * P - counts[i] * S)
                  for i, (lo, hi) in enumerate(intervals)]
    order = []
    for i in range(3):
        rank = 0
        for j in range(3):
            if i == j: continue
            if equal(i, j): rank += j < i
            elif remainders[j][0] > remainders[i][1]: rank += 1
            elif remainders[i][0] > remainders[j][1]: pass
            else: raise NumericAmbiguity("price remainder ambiguous")
        order.append((rank, i))
    for _, i in sorted(order)[:P - sum(counts)]: counts[i] += 1
    return counts


@lru_cache(maxsize=8192)
def _prices(q, b, P):
    if len(set(q)) == 1: return tuple(project_rational([1, 1, 1], P))
    for bits in POLICY["bits"]:
        try:
            return tuple(_project_intervals(_weights(q, b, bits), lambda i, j: q[i] == q[j], P, bits))
        except NumericAmbiguity: pass
    raise NumericAmbiguity("NUMERIC_AMBIGUITY")


def prices(q, b, P=3_000_000):
    vector(q); integer(b, 1); integer(P, 3, 100_000_000)
    return list(_prices(tuple(q), b, P))


def transform(p, temperature, P):
    """Training-only calibration control, with enclosed sqrt when T=1/2."""
    p = list(map(Fraction, p))
    if len(p) != 3 or any(x < 0 for x in p) or sum(p) <= 0:
        raise ContractError("invalid calibration distribution")
    if temperature in {"1", "2"}:
        return project_rational([x ** int(temperature) for x in p], P)
    if temperature != "1/2": raise ContractError("invalid temperature")
    # A common irrational root cancels on normalization, e.g. counts [2,8,0]
    # divided by D=10. Test rational square *ratios*, not absolute weights.
    reference = next(x for x in p if x)
    ratios = [x / reference for x in p]
    roots = [(isqrt(x.numerator), isqrt(x.denominator)) for x in ratios]
    if all(a * a == x.numerator and b * b == x.denominator for x, (a, b) in zip(ratios, roots)):
        return project_rational([Fraction(a, b) for a, b in roots], P)
    if len({x for x in p if x}) == 1:
        return project_rational([int(x > 0) for x in p], P)
    for bits in POLICY["bits"]:
        S, weights = 1 << bits, []
        for x in p:
            lo = isqrt(x.numerator * S * S // x.denominator)
            hi = lo if lo * lo * x.denominator == x.numerator * S * S else lo + 1
            weights.append((lo, hi))
        try: return _project_intervals(weights, lambda i, j: p[i] == p[j], P, bits)
        except NumericAmbiguity: pass
    raise NumericAmbiguity("NUMERIC_AMBIGUITY")
