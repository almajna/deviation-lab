"""Trusted reference policies receive public inputs only; no outcome imports."""
from copy import deepcopy
from fractions import Fraction
import random

from deviation.contracts import ContractError


class ReportSignal:
    """Report the supplied synthetic signal; no claim of strategic truthfulness."""
    def act(self, information):
        return {"schema_version": "0.2", "agent_id": information["agent_id"],
                "task_id": information["task"]["task_id"], "kind": "report_preference",
                "forecast_kind": "expected_preference_proxy",
                "values": deepcopy(information["private_signal"]["values"]),
                "action_fee": information["action_fee"]}


def optimize(tasks, reservations, budget, values, *, max_states=100_000):
    """Exact sparse multiple-choice knapsack, stable ties; fail on state limit.

    Objective is total expected proxy, with zero-valued abstention. Dominated
    cost/score states are pruned. This is exact, not a silent greedy fallback.
    """
    states = {0: (Fraction(0), ())}
    for task in tasks:
        next_states = {}
        choices = [None] + sorted(task["model_options"])
        for spent, (score, path) in sorted(states.items()):
            for model in choices:
                cost = 0 if model is None else reservations[model]
                total = spent + cost
                if total > budget:
                    continue
                gain = Fraction(0) if model is None else Fraction(str(values[task["task_id"]][model]))
                candidate = (score + gain, path + (model,))
                # Traversal fixes ties without comparing None against strings.
                if total not in next_states or candidate[0] > next_states[total][0]:
                    next_states[total] = candidate
        states, best = {}, Fraction(-1)
        for spent, item in sorted(next_states.items()):
            if item[0] > best:
                states[spent] = item
                best = item[0]
        if len(states) > max_states:
            raise ContractError("exact allocation state limit exceeded")
    spent, (_, path) = max(states.items(), key=lambda pair: (pair[1][0], -pair[0]))
    return [{"task_id": task["task_id"], "model_id": model,
             "reserved_cost": 0 if model is None else reservations[model]}
            for task, model in zip(tasks, path)]


class ReferenceAllocator:
    def __init__(self, kind="cost-aware", *, seed=7, training_means=None):
        if kind not in {"random", "cheapest", "best-fixed", "cost-aware"}:
            raise ContractError("unknown reference policy")
        self.kind, self.seed = kind, seed
        self.training_means = deepcopy(training_means or {})

    def allocate(self, public_tasks, validated_actions, reservation_artifact, budget):
        tasks = sorted(deepcopy(public_tasks), key=lambda t: t["task_id"])
        reserves = reservation_artifact["reservations"]
        if self.kind == "cost-aware":
            values = {}
            for task in tasks:
                reports = [a["values"] for a in validated_actions if a["task_id"] == task["task_id"]]
                if not reports:
                    raise ContractError("cost-aware allocation requires reports for every task")
                values[task["task_id"]] = {m: sum(Fraction(str(v[m])) for v in reports) / len(reports)
                                           for m in task["model_options"]}
            # Fraction -> exact string accepted by optimize via Fraction(str()).
            allocations = optimize(tasks, reserves, budget, values)
        else:
            rng, remaining, allocations = random.Random(self.seed), budget, []
            fixed = None
            if self.kind == "best-fixed":
                if set(self.training_means) != set(reserves):
                    raise ContractError("best-fixed requires training-only means for every model")
                for value in self.training_means.values():
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                        raise ContractError("invalid training quality mean")
                # Maximize expected total under the same budget, including abstentions.
                fixed = min(reserves, key=lambda m: (
                    -Fraction(str(self.training_means[m])) * min(sum(m in t["model_options"] for t in tasks), budget // reserves[m]),
                    reserves[m], m))
            if self.kind == "random":
                rng.shuffle(tasks)
            for task in tasks:
                options = [m for m in task["model_options"] if reserves[m] <= remaining]
                if self.kind == "best-fixed":
                    model = fixed if fixed in options else None
                elif self.kind == "random":
                    model = rng.choice(sorted(options)) if options else None
                else:
                    model = min(options, key=lambda m: (reserves[m], m)) if options else None
                cost = 0 if model is None else reserves[model]
                allocations.append({"task_id": task["task_id"], "model_id": model, "reserved_cost": cost})
                remaining -= cost
            allocations.sort(key=lambda a: a["task_id"])
        return {"schema_version": "0.2", "reservation_artifact_sha256": reservation_artifact["artifact_sha256"],
                "cost_unit": reservation_artifact["cost_unit"], "reservation_budget": budget,
                "allocations": allocations}
