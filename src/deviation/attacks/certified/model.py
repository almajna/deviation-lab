"""Trusted certificate semantics and rational economic relaxation (see proof)."""
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import product
from pathlib import Path

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection, score
from deviation.markets.numeric import NumericAmbiguity, quote
from deviation.simulator.policies import optimize

VERSION = 'attack-certificate-1'
ACTION_SPACE = 'engine-l1-orders-or-simplex-reports-1'


def rat(x):
    x = Fraction(x)
    return [x.numerator, x.denominator]


def unrat(x):
    if (not isinstance(x, list) or len(x) != 2 or any(type(v) is not int for v in x)
            or x[1] <= 0 or rat(Fraction(*x)) != x):
        raise Rejection('CERT_INVALID_RATIONAL')
    return Fraction(*x)


def source_sha():
    root = Path(__file__).resolve().parents[2]
    return digest({str(p.relative_to(root)): digest(p.read_text()) for p in sorted(root.rglob('*.py'))})


def validate_game(g):
    e = g.engine
    if g.mechanism not in {'lmsr', 'interactive-pool', 'pool', 'score', 'calibrated-pool'}:
        raise Rejection('CERT_UNSUPPORTED_MECHANISM')
    if g.scope == 'terminal':
        if e.stage != 'TRADE_OR_UPDATE' or any(a not in g.members for a, _ in e.schedule[e.turn:]):
            raise Rejection('CERT_FUTURE_UNCONTROLLED')
    elif (g.scope != 'reports' or e.stage != 'REPORT_COMMIT'
          or g.report_slots != [sorted(e.tokens)[-1]] or g.report_slots[0][0] not in g.members
          or g.mechanism not in {'pool', 'score', 'calibrated-pool'}):
        raise Rejection('CERT_INVALID_REPORT_SCOPE')
    horizon = len(e.schedule) - e.turn if g.scope == 'terminal' else 1
    if horizon > 128:
        raise Rejection('CERT_HORIZON_LIMIT')
    # Strictly finite generation, independent of the optimizer's candidate API.
    Q, D = e.cfg['order_limit'], e.cfg['report_denominator']
    count = (4*Q**3 + 6*Q**2 + 8*Q + 3)//3 if g.mechanism == 'lmsr' else (D+1)*(D+2)//2+1
    if count > min(e.cfg['candidate_limit'], 100_000):
        raise Rejection('CERT_ACTION_SPACE_LIMIT')


def terminal(g):
    return not g.report_slots if g.scope == 'reports' else g.engine.turn == len(g.engine.schedule)


def payoff(g):
    """Separate algebra from Game.expected; only allocation uses shared runner."""
    e, D = g.engine, g.engine.cfg['report_denominator']
    cash = sum(Fraction(e.balances[e.wallet(a)]-e.initial[e.wallet(a)]) for a in g.members)
    for mid, book in e.books.items():
        cash += sum(Fraction(g.beliefs[mid][k], D)*sum(book['holdings'][a][k] for a in g.members) for k in range(3))
    for (a, mid), p in e.commits.items():
        if a in g.members and p is not None:
            cash += sum(Fraction(g.beliefs[mid][y], D)*e.cfg['score_scale'] *
                        (2*D*D-sum((p[k]-D*int(k==y))**2 for k in range(3))) for y in range(3))
    c = e.controllers[g.controller]
    external = sum(c['external_weights'].get(r['task_id'], {}).get(r['model_id'], 0)
                   for r in g.allocation()['allocations'])
    effort = c['effort_per_attempt']*sum(e.attempts[a] for a in g.members)
    return dict(cash=cash, external=Fraction(external), effort=Fraction(effort), utility=cash+external-effort)


@lru_cache(maxsize=8192)
def cell_gain(q, holding, belief, D, b, Q, fee, slots, caps, vector_limit):
    """Upper bound after pooling identities and dropping intermediate solvency.

    Sum ceil(C(q_t+1)-C(q_t)) >= ceil(C(q_final)-C(q_now)).
    Endpoint L1 distance <= Q*slots; fees >= ceil(distance/Q)*fee.
    Ambiguous relaxed endpoint quotes fall back to C(q+d)-C(q)>=min(d).
    """
    if not slots:
        return Fraction(0), 'fixed'
    radius = Q*slots
    ranges = [range(max(-h, -radius), min(cap-h, radius)+1) for h, cap in zip(holding, caps)]
    box = 1
    for r in ranges:
        box *= len(r)
    if box > vector_limit:
        # E[d]-min(d) <= ||d||_1 <= Q for each actual order.
        return Fraction(radius), 'lipschitz'
    best = Fraction(0)
    for delta in product(*ranges):
        distance = sum(abs(d) for d in delta)
        if distance > radius:
            continue
        after = [v+d for v, d in zip(q, delta)]
        try:
            charge = quote(list(q), after, b)['charge']
        except NumericAmbiguity:
            charge = min(delta)  # Never drop an uncertain relaxed endpoint.
        gain = sum(Fraction(p, D)*d for p, d in zip(belief, delta)) - charge
        gain -= ((distance+Q-1)//Q)*fee
        best = max(best, gain)
    return best, 'endpoint'


def upper_bound(g, *, vector_limit=5000):
    """Admissible terminal-utility bound, exact rationals; no sealed outcomes."""
    e, c, D = g.engine, g.engine.controllers[g.controller], g.engine.cfg['report_denominator']
    if terminal(g):
        return payoff(g)['utility']
    current = payoff(g)
    values = {t['task_id']: {m: c['external_weights'].get(t['task_id'], {}).get(m, 0)
                            for m in t['model_options']} for t in g.tasks}
    plan = optimize(sorted(g.tasks, key=lambda t: t['task_id']), g.artifact['reservations'], g.budget, values)
    external = sum(values[r['task_id']].get(r['model_id'], 0) for r in plan)
    cash, future_gain = current['cash'], Fraction(0)
    if g.scope == 'reports':
        # Strictly proper quadratic score is maximized at the integer own belief.
        a, mid = g.report_slots[0]
        p = g.beliefs[mid]
        cash += sum(Fraction(p[y], D)*score(p, D, e.cfg['score_scale'], y) for y in range(3))
        future_attempts = sum(a in g.members for a, _ in e.schedule[e.turn:])
    else:
        future_attempts = len(e.schedule)-e.turn
        if g.mechanism == 'lmsr':
            used = dict(e.attempts)
            active = Counter()
            for a, mid in e.schedule[e.turn:]:
                used[a] += 1
                if used[a] <= e.cfg['action_limit']:
                    active[mid] += 1
            for mid, slots in active.items():
                book = e.books[mid]
                h = tuple(sum(book['holdings'][a][k] for a in g.members) for k in range(3))
                caps = tuple(min(c['position_cap'], len(g.members)*e.cfg['agent_position_limit'],
                                 e.cfg['cell_position_limit']-book['q'][k]+h[k]) for k in range(3))
                gain, _ = cell_gain(tuple(book['q']), h, tuple(g.beliefs[mid]), D, e.cfg['b'],
                                    e.cfg['order_limit'], e.cfg['fee'], slots, caps, vector_limit)
                future_gain += gain
    return cash + future_gain + external - current['effort'] - c['effort_per_attempt']*future_attempts


def complete_static_reports(g):
    """Finish the declared static game, including forced exhausted slots.

    The old search helper rejects ACTION_LIMIT even on mandatory no-op slots;
    here those engine rejections consume the opportunity and its effort, exactly
    as in the terminal game. No accepted action is fabricated.
    """
    from deviation.markets.policies import base_action
    from deviation.markets.runner import allowed_actions
    for a, mid in sorted(g.engine.tokens):
        if (a, mid) not in g.engine.commits:
            g.engine.commit(a, mid, g.announced_reports[a][mid])
    g.engine.reveal()
    while g.engine.turn < len(g.engine.schedule):
        cmd = base_action(g.policy_packet_any(), 'no_op')
        accepted = g.engine.apply(cmd, allowed_kinds=allowed_actions(g.mechanism))
        if not accepted and g.engine.events[-1]['payload']['reason'] != 'ACTION_LIMIT':
            raise Rejection('CERT_STATIC_COMPLETION')
