"""Adversarial numerical replay. Does not import or call the producer optimizer.

This is an automated evidence gate, not an independent scientific peer reviewer.
The certificate check is Agent 2's separately authored implementation.
"""
from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_CEILING
from fractions import Fraction

from .records import sha


def require(ok, message):
    if not ok:
        raise ValueError(message)


def review(payload):
    result, plan = payload["result"], payload["plan"]
    require(result["data_kind"] == "SYNTHETIC" and result["kind"] == plan["runner"], "result identity")
    rows = result["rows"]
    require(bool(rows), "empty experiment")
    checks = []
    if result["kind"] == "lmsr_baseline":
        require(len(rows) == 243, "baseline coverage")
        with localcontext() as c:
            c.prec = 80
            for row in rows:
                b = Decimal(row["b"])
                cost = lambda q: b*sum((Decimal(v)/b).exp() for v in q).ln()
                charge = int((cost(row["after"])-cost(row["before"])).to_integral_value(rounding=ROUND_CEILING))
                require(charge == row["engine_charge"] == row["analytic_charge"], "LMSR charge mismatch")
                bound = b*Decimal(3).ln()
                loss = max(row["before"])-(cost(row["before"])-cost([0, 0, 0]))
                require(loss <= bound and row["loss_le_b_log_n"], "maker-loss violation")
                require(row["funding"] == row["analytic_funding"] == int(bound.to_integral_value(rounding=ROUND_CEILING)), "funding mismatch")
        supported = True
        checks.append("243 analytic charge, funding and sampled bounded-loss checks")
    elif result["kind"] in {"fee_sensitivity", "certificate_ablation"}:
        from deviation.verification.checker import check
        from deviation.verification.domain import encoded, execute, payoff
        from deviation.verification.bounds import upper
        from deviation.verification.fixtures import fixture
        from deviation.attacks.environments import environment
        from deviation.attacks.game import prepare_game
        groups = defaultdict(dict)
        expected = len(plan["seeds"])*(6 if result["kind"] == "fee_sensitivity" else 4)
        require(len(rows) == expected, "certificate experiment coverage")
        unique = set()
        for row in rows:
            profile, seed = row["profile"], row["seed"]
            identity = sha([profile, seed, row.get("vector_limit")])
            require(identity not in unique and seed in plan["seeds"], "duplicate or unexpected case")
            unique.add(identity)
            if result["kind"] == "fee_sensitivity":
                scenario, _, _ = environment(profile, seed, realization_seed=987654)
                g = prepare_game(scenario, "strategic", "lmsr")
                # Independently recheck information-boundary mutation, not a producer boolean.
                from copy import deepcopy
                mutation = deepcopy(scenario)
                for r in mutation["sealed_outcomes"]:
                    r.update(quality=1-r["quality"], cost_decimal="999")
                require(prepare_game(mutation, "strategic", "lmsr").observation() == g.observation()
                        and row["outcome_mutation_invariant"], "outcome leakage")
            else:
                g = fixture(profile, seed, "lmsr")
            require(check(g, row["certificate"]) == row["independent_check"], "independent check mismatch")
            selected = execute(g, row["certificate"]["incumbent_commands"])
            require({k: encoded(v) for k, v in payoff(selected).items()} == row["payoff"], "witness payoff mismatch")
            for mode in ("exhaustive", "dynamic_programming"):
                baseline = row[mode]
                require(baseline["status"] == "EXACT", "censored exact comparator")
                # Independently check the exact comparator's witness; interval equality
                # plus a sound zero-gap proof authenticates its optimum without searching.
                replayed = execute(g, baseline["commands"])
                require(encoded(payoff(replayed)["utility"]) == baseline["utility"], "exact witness mismatch")
                require(baseline["utility"] == row["certificate"]["lower"] == row["certificate"]["upper"], "exact baselines disagree")
            require(Fraction(*row["beam"]) <= Fraction(*row["certificate"]["upper"]), "beam exceeds bound")
            require(encoded(upper(g, vector_limit=0)) == row["root_fallback_upper"] and
                    encoded(upper(g, vector_limit=5000)) == row["root_endpoint_upper"], "bound ablation mismatch")
            # Rebuild no-action and signal-following witnesses without producer search routines.
            from deviation.verification.domain import actions, advance, terminal
            no = g
            while not terminal(no):
                no = advance(no, next(actions(no)))
            require(encoded(payoff(no)["utility"]) == row["no_action"], "no-action comparator mismatch")
            if result["kind"] == "fee_sensitivity":
                groups[seed, profile["external"]][profile["fee"]] = Fraction(*row["certificate"]["lower"])-Fraction(*row["no_action"])
        if result["kind"] == "fee_sensitivity":
            require(set(groups) == {(s, e) for s in plan["seeds"] for e in (0, 6)} and
                    all(set(v) == {0, 2, 4} for v in groups.values()), "fee grid coverage")
            monotonic = all(v[0] >= v[2] >= v[4] for (s, e), v in groups.items() if e == 6)
            strict = any(v[0] > v[4] for (s, e), v in groups.items() if e == 6)
            null = all(max(v.values()) <= 0 for (s, e), v in groups.items() if e == 0)
            supported = monotonic and strict and null
            checks.append({"monotonic": monotonic, "strict": strict, "zero_external_null": null,
                           "paired_gains": {f"{s}/{e}": {str(k): str(x) for k, x in v.items()} for (s, e), v in groups.items()}})
        else:
            weak = all(Fraction(*r["root_endpoint_upper"]) <= Fraction(*r["root_fallback_upper"]) for r in rows)
            strict = any(Fraction(*r["root_endpoint_upper"]) < Fraction(*r["root_fallback_upper"]) for r in rows)
            supported = weak and strict
            checks.append({"weak_dominance": weak, "strict_improvement": strict})
        checks.append("Every certificate and exact-baseline witness independently replayed")
    else:
        from deviation.attacks.environments import environment
        from deviation.markets.runner import run
        require(len(rows) == len(plan["seeds"])*12, "correlation coverage")
        values = defaultdict(dict)
        unique = set()
        for row in rows:
            s, correlated, mechanism = row["seed"], row["correlated"], row["mechanism"]
            require((s, correlated, mechanism) not in unique, "duplicate correlation cell")
            unique.add((s, correlated, mechanism))
            scenario, _, _ = environment(dict(external=0, belief_quality=50, correlated=correlated), s, realization_seed=100000+s)
            replay = run(scenario, mechanism)
            summary = replay["trace"]["events"][-1]["payload"]
            require(summary == row["summary"] and replay["sha256"] == row["receipt_sha256"] and
                    replay["allocation_plan"] == row["plan"], "market receipt replay mismatch")
            require(sum(a["reservation"] for a in row["plan"]["allocations"]) <= scenario["reservation_budget"], "reservation budget violation")
            values[s, correlated][mechanism] = Fraction(str(summary["evaluation"]["selected_quality"]))
        require(unique == {(s, c, m) for s in plan["seeds"] for c in (False, True)
                          for m in ("lmsr", "pool", "uniform", "cheapest", "random", "best-fixed")}, "correlation grid mismatch")
        differences = {str(c): sum(values[s, c]["pool"]-values[s, c]["lmsr"] for s in plan["seeds"])/len(plan["seeds"]) for c in (False, True)}
        supported = differences["True"] >= 0 and differences["True"] >= differences["False"]
        checks.append({"mean_total_proxy_pool_minus_market": {k: str(v) for k, v in differences.items()},
                       "uncertainty": "Three seed blocks, two tasks each; descriptive only, no generalization inference"})
    return dict(version="research-review-1", result_sha256=sha(result),
                integrity="PASS", hypothesis_status="SUPPORTED_ON_REGISTERED_GRID" if supported else "REJECTED_ON_REGISTERED_GRID",
                checks=checks, novelty="NOT_ESTABLISHED", independent_scientific_review="PENDING",
                limitation="Automated numerical gate, separately implemented certificate checker, shared trusted engine. No external peer review.")
