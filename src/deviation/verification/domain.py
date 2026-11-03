"""Independent actions, transitions, exact objective and finite-state baselines.

No imports from attacks.search, certificate optimizer or their bound routines.
The existing transition engine and certified numeric primitives are trusted.
"""
from copy import deepcopy
from fractions import Fraction
from itertools import product

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from deviation.markets.numeric import prices, transform


class VerificationError(ValueError):
    pass


def encoded(x):
    x = Fraction(x)
    return [x.numerator, x.denominator]


def fraction(x):
    if (not isinstance(x, list) or len(x) != 2 or any(type(n) is not int for n in x)
            or x[1] <= 0):
        raise VerificationError("noncanonical rational")
    value = Fraction(*x)
    if encoded(value) != x:
        raise VerificationError("noncanonical rational")
    return value


def terminal(g):
    return not g.report_slots if g.scope == "reports" else g.engine.turn == len(g.engine.schedule)


def command(g, kind):
    e = g.engine
    a, mid = e.schedule[e.turn]
    return {"schema_version": "0.3", "kind": kind, "stage": e.stage,
            "actor": a, "order_id": f"{a}/order-{e.turn}", "market_id": mid,
            "expected_state_seq": e.books[mid]["seq"]}


def actions(g):
    """Enumerate integer lattice independently, without policies.candidates."""
    if terminal(g):
        return
    e, D = g.engine, g.engine.cfg["report_denominator"]
    if g.scope == "reports":
        a, mid = g.report_slots[0]
        for p in [None] + [[i, j, D-i-j] for i in range(D+1) for j in range(D-i+1)]:
            yield {"stage": "REPORT_COMMIT", "actor": a, "market_id": mid, "counts": p}
        return
    yield command(g, "no_op")
    a, mid = e.schedule[e.turn]
    if e.attempts[a] >= e.cfg["action_limit"]:
        return
    if g.mechanism == "lmsr":
        Q = e.cfg["order_limit"]
        for delta in product(range(-Q, Q+1), repeat=3):
            if not 0 < sum(abs(n) for n in delta) <= Q:
                continue
            try:
                quote = e.inspect_order(a, mid, list(delta))
            except Rejection:
                continue
            req = command(g, "trade_shares")
            req.update(share_delta=list(delta), max_net_debit=quote["receipt"]["charge"] + e.cfg["fee"])
            yield req
    elif g.mechanism == "interactive-pool" and e.balances[e.wallet(a)] >= e.cfg["fee"]:
        for i in range(D+1):
            for j in range(D-i+1):
                req = command(g, "update_distribution")
                req.update(counts=[i, j, D-i-j], denominator=D)
                yield req


def step(g, req):
    """Execute only a member of the independent legal finite alphabet."""
    if digest(req) not in {digest(a) for a in actions(g)}:
        raise VerificationError("command outside finite action space")
    return advance(g, req)


def advance(g, req):
    """Internal transition after caller generated/validated the full alphabet."""
    child = deepcopy(g)
    e = child.engine
    if child.scope == "reports":
        a, mid = child.report_slots.pop(0)
        e.commit(a, mid, req["counts"])
        if not child.report_slots:
            for a, mid in sorted(e.tokens):
                if (a, mid) not in e.commits:
                    e.commit(a, mid, child.announced_reports[a][mid])
            e.reveal()
            while e.turn < len(e.schedule):
                e.apply(command(child, "no_op"), allowed_kinds={"no_op"})
    else:
        allowed = {"no_op", "trade_shares"} if child.mechanism == "lmsr" else {"no_op", "update_distribution"}
        accepted = e.apply(req, allowed_kinds=allowed)
        if not accepted and e.events[-1]["payload"]["reason"] != "ACTION_LIMIT":
            raise VerificationError("engine rejected declared legal action")
    return child


def execute(g, commands):
    child = g
    for req in commands:
        if terminal(child):
            raise VerificationError("commands after terminal state")
        child = step(child, req)
    if not terminal(child):
        raise VerificationError("incomplete incumbent")
    return child


def allocation(g):
    """Independent dense budget DP, including deterministic engine tie rules."""
    e, values = g.engine, {}
    P, D = e.cfg["price_denominator"], e.cfg["report_denominator"]
    for mid, book in e.books.items():
        if g.mechanism == "lmsr":
            p = prices(book["q"], e.cfg["b"], P)
        else:
            reports = [v for (a, m), v in e.reports.items() if m == mid]
            p = [sum((Fraction(v[k], D) for v in reports), Fraction())/len(reports)
                 if reports else Fraction(1, 3) for k in range(3)]
            p = transform(p, g.temperature if g.mechanism == "calibrated-pool" else "1", P)
        values[book["task_id"], book["model_id"]] = Fraction(p[1]+2*p[2], 2*P)
    states = {0: (Fraction(), [])}
    for t in g.tasks:
        next_states = {}
        for cost in sorted(states):
            score, plan = states[cost]
            for m in [None] + sorted(t["model_options"]):
                spend = cost + (g.artifact["reservations"][m] if m is not None else 0)
                if spend > g.budget:
                    continue
                value = score + (values[t["task_id"], m] if m is not None else 0)
                if spend not in next_states or value > next_states[spend][0]:
                    next_states[spend] = value, plan + [m]
        best = Fraction(-1)
        states = {}
        for cost in sorted(next_states):
            if next_states[cost][0] > best:
                states[cost] = next_states[cost]
                best = next_states[cost][0]
    spend = max(states, key=lambda c: (states[c][0], -c))
    return [{"task_id": t["task_id"], "model_id": m,
             "reserved_cost": g.artifact["reservations"][m] if m is not None else 0}
            for t, m in zip(g.tasks, states[spend][1])]


def payoff(g):
    """Expanded categorical Brier plus cash/claims/external utility minus effort."""
    e, D = g.engine, g.engine.cfg["report_denominator"]
    members = {a for a, cfg in e.agents.items() if cfg["controller"] == g.controller}
    cash = sum((Fraction(e.balances[e.wallet(a)]-e.initial[e.wallet(a)]) for a in members), Fraction())
    claims = sum((Fraction(g.beliefs[mid][k], D)*book["holdings"][a][k]
                  for mid, book in e.books.items() for a in members for k in range(3)), Fraction())
    scores = Fraction()
    for (a, mid), p in e.commits.items():
        if a in members and p is not None:
            for y in range(3):
                reward = e.cfg["score_scale"]*(2*D*D-sum((p[k]-D*int(k == y))**2 for k in range(3)))
                scores += Fraction(g.beliefs[mid][y], D)*reward
    cfg = e.controllers[g.controller]
    plan = allocation(g)
    external = sum(cfg["external_weights"].get(r["task_id"], {}).get(r["model_id"], 0) for r in plan)
    effort = cfg["effort_per_attempt"]*sum(e.attempts[a] for a in members)
    return {"cash": cash+claims+scores, "external": Fraction(external),
            "effort": Fraction(effort), "utility": cash+claims+scores+external-effort,
            "allocation": plan}


def economic_key(g):
    """Sufficient state for future transitions/utility, excluding event history.

    Prefix receipts, command IDs and state-sequence counters do not affect future
    cash or allocation under this fixed single-controller suffix. Command IDs are
    unique by turn and all commands use the freshly observed sequence. Initial
    balances, beliefs, config and tasks stay fixed per solve. Current cash, all
    portfolios, reports, commitments, attempts and turn remain in the key.
    """
    e = g.engine
    return digest({"turn": e.turn, "report_slots": g.report_slots,
        "balances": e.balances, "books": {m: {"q": b["q"], "holdings": b["holdings"]}
        for m, b in e.books.items()}, "attempts": e.attempts,
        "reports": [[a, m, p] for (a, m), p in sorted(e.reports.items())],
        "commits": [[a, m, p] for (a, m), p in sorted(e.commits.items())]})


def exact(g, *, max_nodes=20000, memoize=False):
    """Independent complete enumeration / memoized finite-horizon value iteration.

    If capped, return only a censored status and feasible no-op incumbent; no
    upper-bound/optimality claim is made. Counters measure actual engine children.
    """
    nodes, transitions, leaves, hits = 0, 0, 0, 0
    cache = {}
    def solve(state):
        nonlocal nodes, transitions, leaves, hits
        key = economic_key(state) if memoize else None
        if memoize and key in cache:
            hits += 1
            return cache[key]
        nodes += 1
        if nodes > max_nodes:
            raise OverflowError
        if terminal(state):
            leaves += 1
            value = payoff(state)["utility"], []
        else:
            value = None
            for req in actions(state):
                transitions += 1
                child = advance(state, req)
                score, path = solve(child)
                if value is None or score > value[0]:
                    value = score, [req]+path
        if memoize:
            cache[key] = value
        return value
    try:
        value, path = solve(g)
        status = "EXACT"
        # Cached paths can carry stale sequence numbers after state merging.
        # Rebind IDs/sequences against the actual replay path; commands' economic
        # choices remain identical and must pass the independent legal alphabet.
        child, rebound = g, []
        for req in path:
            req = deepcopy(req)
            if child.scope != "reports":
                req.update(command(child, req["kind"]))
            child = step(child, req)
            rebound.append(req)
        if payoff(child)["utility"] != value:
            raise VerificationError("memoized replay disagrees")
        path = rebound
    except OverflowError:
        value, path, status = None, [], "CENSORED_STATE_LIMIT"
    return {"status": status, "utility": encoded(value) if value is not None else None,
            "commands": path, "nodes": min(nodes, max_nodes), "transitions": transitions,
            "leaves": leaves, "cache_hits": hits}
