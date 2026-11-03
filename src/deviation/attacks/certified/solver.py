"""Best-bound anytime search. Proof verification never imports this module."""
from copy import deepcopy
import heapq
from fractions import Fraction

from deviation.attacks.search import choices, reference, transition
from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from .model import ACTION_SPACE, VERSION, payoff, rat, source_sha, terminal, upper_bound, validate_game, complete_static_reports


def solve(game, *, max_expansions=1000, vector_limit=5000):
    """Produce executable lower bound and covering proof of an upper bound.

    The cap counts expanded nonterminal states, not engine calls or seconds.
    Generation of a node's entire action family is atomic and always retained.
    """
    validate_game(game)
    if type(max_expansions) is not int or not 0 <= max_expansions <= 100_000:
        raise Rejection('CERT_INVALID_LIMIT')
    if type(vector_limit) is not int or not 0 <= vector_limit <= 100_000:
        raise Rejection('CERT_INVALID_LIMIT')
    def advance(g, command):
        if g.scope != 'reports':
            return transition(g, command)
        child = deepcopy(g)
        a, mid = child.report_slots.pop(0)
        child.engine.commit(a, mid, command['counts'])
        complete_static_reports(child)
        return child

    initial_sha = digest(game.observation())
    incumbents = []
    for strategy in ['no_action', 'signal_following']:
        if game.scope == 'reports':
            a, mid = game.report_slots[0]
            command = dict(stage='REPORT_COMMIT', actor=a, market_id=mid,
                           counts=None if strategy == 'no_action' else game.beliefs[mid])
            state, commands = advance(game, command), [command]
        else:
            state, commands = reference(game, strategy)
        incumbents.append((payoff(state)['utility'], commands))
    lower, best_path = max(incumbents, key=lambda x: x[0])
    nodes, queue, expansions, generated = [], [], 0, 0

    def add(g, path):
        nonlocal lower, best_path, generated
        i = len(nodes)
        if terminal(g):
            bound = payoff(g)['utility']
            if bound > lower:
                lower, best_path = bound, path
            node = dict(kind='terminal', upper=rat(bound))
        else:
            bound = upper_bound(g, vector_limit=vector_limit)
            node = dict(kind='bound', upper=rat(bound))
            heapq.heappush(queue, (-bound, i, g, path))
        nodes.append(node)
        generated += 1
        return i

    add(deepcopy(game), [])
    while queue and expansions < max_expansions:
        negative, index, state, path = heapq.heappop(queue)
        if -negative <= lower:
            continue
        children = []
        for command in choices(state):
            child = advance(state, command)
            if child is not None:
                children.append(dict(command=command, node=add(child, path+[command])))
        if not children:
            raise Rejection('CERT_EMPTY_ACTION_FAMILY')
        nodes[index] = dict(kind='split', children=children)
        expansions += 1
    upper = max([lower] + [Fraction(*n['upper']) for n in nodes if n['kind'] != 'split'])
    result = dict(version=VERSION, scope=game.scope, controller=game.controller, action_space=ACTION_SPACE,
                  observation_sha256=initial_sha, source_sha256=source_sha(),
                  objective='SUBJECTIVE_EXPECTED_CONTROLLER_UTILITY', vector_limit=vector_limit,
                  incumbent_commands=best_path, lower=rat(lower), upper=rat(upper), gap=rat(upper-lower),
                  claim='EXACT_FINITE_SUBGAME' if upper == lower else 'BOUNDED_FINITE_SUBGAME',
                  nodes=nodes, search=dict(max_expansions=max_expansions, expansions=expansions, generated=generated))
    result['sha256'] = digest(result)
    return result
