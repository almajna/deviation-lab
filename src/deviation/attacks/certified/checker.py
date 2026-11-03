"""Proof checker: does not call/import search, solver, choices or transition.

Trusted base: approved Engine, allocation, certified numerical primitives and
model.py's documented economic relaxation. This is not a proof-assistant kernel.
"""
from copy import deepcopy
from itertools import product

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from deviation.markets.policies import base_action
from deviation.markets.runner import allowed_actions
from .model import ACTION_SPACE, VERSION, payoff, rat, source_sha, terminal, unrat, upper_bound, validate_game, complete_static_reports


def _require(condition, reason='CERT_INVALID_PROOF'):
    if not condition:
        raise Rejection(reason)


def _actions(g):
    """Separate complete finite family using inspect_order, not candidates()."""
    e = g.engine
    D = e.cfg['report_denominator']
    if g.scope == 'reports':
        actor, mid = g.report_slots[0]
        return [dict(stage='REPORT_COMMIT', actor=actor, market_id=mid, counts=p)
                for p in [None]+[[a,b,D-a-b] for a in range(D+1) for b in range(D-a+1)]]
    a, mid = e.schedule[e.turn]
    p = dict(stage=e.stage, agent_id=a, market_id=mid, turn=e.turn, state_seq=e.books[mid]['seq'])
    out = [base_action(p, 'no_op')]
    if e.attempts[a] >= e.cfg['action_limit']:
        return out
    if g.mechanism == 'lmsr':
        Q = e.cfg['order_limit']
        for delta in product(range(-Q,Q+1), repeat=3):
            if not any(delta) or sum(abs(x) for x in delta) > Q:
                continue
            try:
                result = e.inspect_order(a, mid, list(delta))
            except Rejection:
                continue
            cmd = base_action(p, 'trade_shares')
            cmd.update(share_delta=list(delta), max_net_debit=result['receipt']['charge']+e.cfg['fee'])
            out.append(cmd)
    elif g.mechanism == 'interactive-pool' and e.balances[e.wallet(a)] >= e.cfg['fee']:
        for x in range(D+1):
            for y in range(D-x+1):
                cmd = base_action(p, 'update_distribution')
                cmd.update(counts=[x,y,D-x-y], denominator=D)
                out.append(cmd)
    return out


def _step(g, command):
    child = deepcopy(g)
    if child.scope == 'reports':
        a, mid = child.report_slots.pop(0)
        child.engine.commit(a, mid, command['counts'])
        if not child.report_slots:
            complete_static_reports(child)
    else:
        accepted = child.engine.apply(command, allowed_kinds=allowed_actions(child.mechanism))
        _require(accepted or child.engine.events[-1]['payload']['reason'] == 'ACTION_LIMIT')
    return child


def verify(game, certificate, *, max_nodes=1_000_000):
    """Return verified bounds or raise Rejection. Optimizer metadata is advisory.

    Caller supplies a trusted outcome-free Game; a hash is not authentication.
    All boundary values are recomputed, not accepted from a producer's digest.
    """
    validate_game(game)
    _require(type(max_nodes) is int and max_nodes >= 1)
    c = certificate
    expected = set('version scope controller action_space observation_sha256 source_sha256 objective vector_limit incumbent_commands lower upper gap claim nodes search sha256'.split())
    _require(isinstance(c, dict) and set(c) == expected)
    _require(c['sha256'] == digest({k:v for k,v in c.items() if k != 'sha256'}), 'CERT_HASH')
    _require((c['version'],c['scope'],c['action_space'],c['objective']) ==
             (VERSION,game.scope,ACTION_SPACE,'SUBJECTIVE_EXPECTED_CONTROLLER_UTILITY'))
    _require(c['controller'] == game.controller, 'CERT_CONTROLLER')
    _require(c['source_sha256'] == source_sha(), 'CERT_SOURCE')
    _require(c['observation_sha256'] == digest(game.observation()), 'CERT_OBSERVATION')
    _require(type(c['vector_limit']) is int and 0 <= c['vector_limit'] <= 100_000)
    _require(isinstance(c['nodes'], list) and 1 <= len(c['nodes']) <= max_nodes)
    lower, claimed_upper, gap = (unrat(c[k]) for k in ['lower','upper','gap'])
    # Replay the witness separately, validating each command against checker family.
    witness = deepcopy(game)
    _require(isinstance(c['incumbent_commands'], list))
    for command in c['incumbent_commands']:
        _require(not terminal(witness))
        _require(command in _actions(witness), 'CERT_INADMISSIBLE_WITNESS')
        witness = _step(witness, command)
    _require(terminal(witness) and payoff(witness)['utility'] == lower, 'CERT_LOWER')
    visited, boundary = set(), []
    pending = [(0,deepcopy(game))]
    while pending:
        i, state = pending.pop()
        _require(type(i) is int and 0 <= i < len(c['nodes']) and i not in visited)
        visited.add(i)
        node = c['nodes'][i]
        _require(isinstance(node, dict) and 'kind' in node)
        if node['kind'] == 'split':
            _require(set(node) == {'kind','children'} and not terminal(state))
            actions = _actions(state)
            children = node['children']
            _require(isinstance(children,list) and len(children) == len(actions), 'CERT_COVERAGE')
            observed = []
            for edge in children:
                _require(isinstance(edge,dict) and set(edge) == {'command','node'})
                _require(edge['command'] in actions, 'CERT_COVERAGE')
                observed.append(digest(edge['command']))
                pending.append((edge['node'],_step(state,edge['command'])))
            _require(len(set(observed)) == len(actions), 'CERT_COVERAGE')
        else:
            _require(set(node) == {'kind','upper'})
            if node['kind'] == 'terminal':
                _require(terminal(state))
                bound = payoff(state)['utility']
            else:
                _require(node['kind'] == 'bound' and not terminal(state))
                bound = upper_bound(state, vector_limit=c['vector_limit'])
            _require(unrat(node['upper']) == bound, 'CERT_BOUND')
            boundary.append(bound)
    _require(len(visited) == len(c['nodes']), 'CERT_UNREACHABLE_NODE')
    stats = c['search']
    _require(isinstance(stats,dict) and set(stats) == {'max_expansions','expansions','generated'})
    _require(all(type(v) is int and v >= 0 for v in stats.values()))
    _require(stats['generated'] == len(visited))
    _require(stats['expansions'] == sum(n['kind'] == 'split' for n in c['nodes']))
    _require(stats['expansions'] <= stats['max_expansions'] <= 100_000)
    upper = max([lower]+boundary)
    _require(claimed_upper == upper and gap == upper-lower and gap >= 0, 'CERT_UPPER')
    _require(c['claim'] == ('EXACT_FINITE_SUBGAME' if gap == 0 else 'BOUNDED_FINITE_SUBGAME'))
    # Independently reconstruct ordinary reference commands, without search.py.
    from deviation.markets.policies import SignalFollowing
    references = {}
    for strategy in ['no_action','signal_following']:
        ref = deepcopy(game)
        while not terminal(ref):
            if ref.scope == 'reports':
                a, mid = ref.report_slots[0]
                cmd = dict(stage='REPORT_COMMIT', actor=a, market_id=mid,
                           counts=None if strategy == 'no_action' else ref.beliefs[mid])
            else:
                options = _actions(ref)
                a, _ = ref.engine.schedule[ref.engine.turn]
                cmd = options[0] if strategy == 'no_action' or ref.engine.attempts[a] >= ref.engine.cfg['action_limit'] else SignalFollowing().act(ref.policy_packet())
                _require(cmd in options)
            ref = _step(ref,cmd)
        references[strategy] = payoff(ref)['utility']
    return dict(version=VERSION, lower=rat(lower), upper=rat(upper), gap=rat(gap), claim=c['claim'],
                checked_nodes=len(visited), payoff={k:rat(v) for k,v in payoff(witness).items()},
                incumbent_commands=deepcopy(c['incumbent_commands']),
                reference_utilities={k:rat(v) for k,v in references.items()},
                gain_bounds={k:dict(lower=rat(lower-v),upper=rat(upper-v)) for k,v in references.items()})
