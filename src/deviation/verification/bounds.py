"""Independent derivation of the published pooled-endpoint upper bound.

This module imports neither the producer nor its model/bound/payoff helpers.
For each reachable final aggregate holding H, telescope potential changes, bound
the rounded total charge from below, and subtract a lower bound on trade fees.
Capital, intermediate solvency and per-account paths are relaxed. External
allocation value is separately optimized over the same reservation budget.
"""
from fractions import Fraction
from functools import lru_cache
from itertools import product

from deviation.markets.numeric import NumericAmbiguity, quote
from .domain import payoff, terminal


def external_cap(g):
    weights = g.engine.controllers[g.controller]["external_weights"]
    values = {0: 0}
    for task in g.tasks:
        updated = {}
        for spend, value in values.items():
            for m in [None] + task["model_options"]:
                total = spend + (0 if m is None else g.artifact["reservations"][m])
                if total <= g.budget:
                    candidate = value + weights.get(task["task_id"], {}).get(m, 0)
                    updated[total] = max(updated.get(total, candidate), candidate)
        values = updated
    return max(values.values())


@lru_cache(maxsize=8192)
def endpoint_cap(q, h, caps, belief, denominator, liquidity, quantity, fee, opportunities, limit):
    if opportunities == 0:
        return Fraction()
    distance_cap = quantity*opportunities
    # Enumerate final holdings, a different parameterization from producer delta.
    lo = [max(0, n-distance_cap) for n in h]
    hi = [min(cap, n+distance_cap) for n, cap in zip(h, caps)]
    box_size = (hi[0]-lo[0]+1)*(hi[1]-lo[1]+1)*(hi[2]-lo[2]+1)
    if box_size > limit:
        return Fraction(distance_cap)
    result = Fraction()
    for H in product(*(range(a, b+1) for a, b in zip(lo, hi))):
        delta = tuple(end-start for end, start in zip(H, h))
        distance = sum(abs(n) for n in delta)
        if distance > distance_cap:
            continue
        after = [a+b for a, b in zip(q, delta)]
        try:
            charge_lower = quote(list(q), after, liquidity)["charge"]
        except NumericAmbiguity:
            # Smooth log-sum-exp potential difference >= minimum coordinate delta.
            # An ambiguous endpoint is retained with a weaker safe lower charge.
            charge_lower = min(delta)
        minimum_trades = (distance+quantity-1)//quantity
        improvement = sum((Fraction(n, denominator)*d for n, d in zip(belief, delta)), Fraction())
        result = max(result, improvement-charge_lower-minimum_trades*fee)
    return result


def upper(g, *, vector_limit):
    if terminal(g):
        return payoff(g)["utility"]
    e = g.engine
    cfg = e.controllers[g.controller]
    members = {a for a in e.agents if e.agents[a]["controller"] == g.controller}
    current = payoff(g)
    extra_cash = Fraction()
    remaining = e.schedule[e.turn:]
    future_attempts = sum(a in members for a, m in remaining)
    if g.scope == "reports":
        _, mid = g.report_slots[0]
        D = e.cfg["report_denominator"]
        p = g.beliefs[mid]
        # Expected proper score at p: scale*(D^2 + sum(p_k^2)).
        extra_cash = Fraction(e.cfg["score_scale"]*(D*D+sum(n*n for n in p)))
    elif g.mechanism == "lmsr":
        used = dict(e.attempts)
        opportunities = {}
        for a, mid in remaining:
            used[a] += 1
            if used[a] <= e.cfg["action_limit"]:
                opportunities[mid] = opportunities.get(mid, 0)+1
        for mid, count in opportunities.items():
            book = e.books[mid]
            holding = tuple(sum(book["holdings"][a][k] for a in members) for k in range(3))
            limits = tuple(min(cfg["position_cap"], len(members)*e.cfg["agent_position_limit"],
                               e.cfg["cell_position_limit"]-(book["q"][k]-holding[k])) for k in range(3))
            extra_cash += endpoint_cap(tuple(book["q"]), holding, limits, tuple(g.beliefs[mid]),
                e.cfg["report_denominator"], e.cfg["b"], e.cfg["order_limit"], e.cfg["fee"], count, vector_limit)
    return (current["cash"]+extra_cash+external_cap(g)-current["effort"]
            -cfg["effort_per_attempt"]*future_attempts)
