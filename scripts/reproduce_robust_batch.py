"""Offline fixture reproduction of Markovic-Voronov et al., equations (2)-(4)."""

import json
from itertools import product
from random import Random

SCALE = 10_000


def allocate(scores, costs, budget, capacity):
    """Exactly solve the two-route assignment with integer scores and costs.

    All inputs are pre-decision. Ties prefer the lexicographically first
    route vector. An infeasible problem raises ValueError.
    """
    n = len(scores)
    if not n or len(costs) != n or len(capacity) != 2:
        raise ValueError("expected a nonempty two-route batch")
    if any(len(row) != 2 for matrix in (scores, costs) for row in matrix):
        raise ValueError("expected two entries per task")
    if any(type(x) is not int or x < 0 for x in (budget, *capacity)):
        raise ValueError("budget and capacity must be nonnegative integers")
    if any(type(x) is not int or x < 0 for row in costs for x in row):
        raise ValueError("costs must be nonnegative integers")
    if any(type(x) is not int or not 0 <= x <= SCALE for row in scores for x in row):
        raise ValueError("scores must be integers in [0, 10000]")

    # At a fixed prefix length, route 0 use is determined by route 1 use.
    # For equal resource states only the best prefix can improve a suffix.
    states = {(0, 0): (0, ())}
    for i, (task_scores, task_costs) in enumerate(zip(scores, costs)):
        next_states = {}
        for (spent, used_1), (value, prefix) in states.items():
            for route in (0, 1):
                new_spent = spent + task_costs[route]
                new_used_1 = used_1 + route
                if (new_spent > budget or new_used_1 > capacity[1]
                        or i + 1 - new_used_1 > capacity[0]):
                    continue
                key = (new_spent, new_used_1)
                candidate = (-(value + task_scores[route]), prefix + (route,))
                old = next_states.get(key)
                if old is None or candidate < (-old[0], old[1]):
                    next_states[key] = (-candidate[0], candidate[1])
        states = next_states

    if not states:
        raise ValueError("no budget- and capacity-feasible allocation")
    (spent, _), (value, routes) = min(
        states.items(), key=lambda item: (-item[1][0], item[1][1])
    )
    return {"assignment": routes, "cost": spent, "score_sum": value}


def bootstrap_knn(ranks, training_scores, *, k=5, seed=0):
    """Return nominal and Q10 forecasts from per-query training-neighbor ranks.

    Training scores contain paired model outcomes on other tasks only.
    Distances are caller-supplied rankings, closest first.
    """
    n = len(training_scores)
    if not 1 <= k <= n or any(set(rank) != set(range(n)) or len(rank) != n for rank in ranks):
        raise ValueError("expected complete training ranks and 1 <= k <= training size")
    if any(len(row) != 2 or any(type(x) is not int or not 0 <= x <= SCALE for x in row)
           for row in training_scores):
        raise ValueError("expected paired training scores in [0, 10000]")

    def predict(rank, counts):
        neighbors = []
        for index in rank:
            neighbors.extend([index] * min(counts[index], k - len(neighbors)))
            if len(neighbors) == k:
                break
        return tuple(sum(training_scores[i][m] for i in neighbors) // k for m in (0, 1))

    rng = Random(seed)
    draws = []
    for _ in range(100):
        counts = [0] * n
        for _ in range(n):
            counts[rng.randrange(n)] += 1
        draws.append(counts)
    point = [predict(rank, [1] * n) for rank in ranks]
    lower = []
    for rank in ranks:
        by_model = zip(*(predict(rank, draw) for draw in draws))
        lower.append(tuple(sorted(predictions)[9] for predictions in by_model))
    return point, lower


def fixture():
    """Check known answers and independently enumerate all feasible assignments."""
    if not __debug__:
        raise RuntimeError("fixture checks require assertions enabled")

    costs = [(1, 3), (1, 3), (1, 3)]
    point = [(6000, 9000), (4000, 8000), (6000, 7000)]
    lower = [(5500, 8500), (3800, 5500), (5000, 6000)]
    nominal = allocate(point, costs, 5, (3, 1))
    robust = allocate(lower, costs, 5, (3, 1))
    assert nominal == {"assignment": (0, 1, 0), "cost": 5, "score_sum": 20000}
    assert robust == {"assignment": (1, 0, 0), "cost": 5, "score_sum": 17300}
    rankings = [tuple(range(5))]
    estimates = bootstrap_knn(rankings, [(2000, 8000)] * 5)
    assert estimates == ([(2000, 8000)], [(2000, 8000)])
    assert bootstrap_knn([(0, 1)], [(0, SCALE), (SCALE, 0)], k=1) == (
        [(0, SCALE)], [(0, 0)]
    )

    checked = 0
    for scores in (point, lower, [(5000, 5000)] * 3):
        for model_costs in (costs, [(0, 3), (2, 1), (3, 0)]):
            for budget, cap0, cap1 in product(range(10), range(4), range(4)):
                options = []
                for routes in product(range(2), repeat=3):
                    cost = sum(model_costs[i][m] for i, m in enumerate(routes))
                    score = sum(scores[i][m] for i, m in enumerate(routes))
                    if cost <= budget and routes.count(0) <= cap0 and routes.count(1) <= cap1:
                        options.append((-score, routes, cost))
                try:
                    result = allocate(scores, model_costs, budget, (cap0, cap1))
                except ValueError:
                    assert not options
                else:
                    score, routes, cost = min(options)
                    assert result == {"assignment": routes, "cost": cost, "score_sum": -score}
                checked += 1
    return {"data_kind": "SYNTHETIC_FIXTURE", "allocation_checks": checked,
            "budget": 5, "capacity": [3, 1], "score_scale": SCALE,
            "nominal": nominal, "robust": robust}


if __name__ == "__main__":
    print(json.dumps(fixture(), indent=2, sort_keys=True))
