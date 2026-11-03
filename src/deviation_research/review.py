"""Adversarial numerical replay. Does not import or call the producer optimizer.

This is an automated evidence gate, not an independent scientific peer reviewer.
The certificate check is Agent 2's separately authored implementation.
"""
from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_CEILING
from fractions import Fraction
from itertools import product

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
    signed_status = "NOT_REQUESTED"
    unresolved = False
    if result["kind"] == "lmsr_baseline":
        require(len(rows) == 243, "baseline coverage")
        expected_cells = set()
        for b in (1, 3, 8):
            for before in product((0, 1, 4), repeat=3):
                for k in range(3):
                    after = list(before); after[k] += 1
                    expected_cells.add((b, before, tuple(after)))
        actual_cells = [(r["b"], tuple(r["before"]), tuple(r["after"])) for r in rows]
        require(len(set(actual_cells)) == 243 and set(actual_cells) == expected_cells, "baseline exact unique grid")
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
        if plan.get("signed_diagnostic"):
            spec = plan["signed_diagnostic"]
            require(spec["version"] == "signed-lmsr-diagnostic-1" and spec["liquidities"] == [1, 3, 8] and
                    spec["transitions"] == [
                        [[0, 0, 0], [0, 0, 9]], [[0, 0, 9], [0, 0, 0]], [[2, 4, 7], [7, 4, 2]],
                        [[2, 4, 7], [4, 6, 9]], [[3, 3, 3], [1, 1, 1]], [[2, 4, 7], [1, 8, 3]],
                        [[0, 0, 0], [3, 3, 0]]], "signed diagnostic was not preregistered")
            signed_rows = result["signed_rows"]
            cells = [(r["b"], tuple(r["before"]), tuple(r["after"])) for r in signed_rows]
            expected = {(b, tuple(before), tuple(after)) for b in spec["liquidities"] for before, after in spec["transitions"]}
            require(set(cells) == expected and len(cells) == len(expected), "signed diagnostic exact grid")
            with localcontext() as context:
                context.prec = 80
                for row in signed_rows:
                    b = Decimal(row["b"])
                    before, after = sorted(row["before"]), sorted(row["after"])
                    offsets = [a-z for a, z in zip(after, before)]
                    cost = lambda q: b*sum((Decimal(v)/b).exp() for v in q).ln()
                    delta = Decimal(offsets[0]) if min(offsets) == max(offsets) else cost(after)-cost(before)
                    require(abs(Decimal(row["analytic_delta"])-delta) < Decimal("1e-60"), "signed potential mismatch")
                    require(row["engine_charge"] == row["analytic_charge"] == int(delta.to_integral_value(rounding=ROUND_CEILING)), "signed rounded charge mismatch")
                    lo, hi = map(Decimal, row["engine_interval"])
                    require(lo <= delta <= hi, "analytic delta outside certified interval")
            require({-1 if r["engine_charge"] < 0 else int(r["engine_charge"] > 0) for r in signed_rows} == {-1, 0, 1}, "signed coverage missing charge signs")
            signed_status = "PASS_ON_DECLARED_21_TRANSITIONS"
            checks.append("Separately preregistered signed/multi-share diagnostic: 21 potential deltas, charges and certified intervals")
    elif result["kind"] in {"fee_sensitivity", "certificate_ablation"}:
        from deviation.verification.checker import check
        from deviation.verification.domain import encoded, execute, payoff
        from deviation.verification.bounds import upper
        from deviation.verification.fixtures import fixture
        from deviation.attacks.environments import environment
        from deviation.attacks.game import prepare_game
        from deviation.markets.contracts import Rejection
        groups = defaultdict(dict)
        expected = len(plan["seeds"])*(6 if result["kind"] == "fee_sensitivity" else 4)
        require(len(rows) == expected, "certificate experiment coverage")
        unique = set()
        expected_cells = set()
        if result["kind"] == "fee_sensitivity":
            for seed in plan["seeds"]:
                for external in (0, 6):
                    for fee in (0, 2, 4):
                        expected_cells.add(sha([dict(fee=fee, external=external, quantity=2), seed, None]))
        else:
            for seed in plan["seeds"]:
                for horizon in (1, 2):
                    for limit in (0, 5000):
                        expected_cells.add(sha([dict(capital=8, external=8, fee=0, b=3, quantity=1,
                            information="mixed", aliases=1, horizon=horizon), seed, limit]))
        for row in rows:
            profile, seed = row["profile"], row["seed"]
            identity = sha([profile, seed, row.get("vector_limit")])
            require(identity not in unique and identity in expected_cells, "duplicate or nonregistered case")
            unique.add(identity)
            if result["kind"] == "fee_sensitivity":
                scenario, _, _ = environment(profile, seed, realization_seed=987654)
                try:
                    g = prepare_game(scenario, "strategic", "lmsr")
                except Rejection as exc:
                    require(exc.code == "NO_CONTROLLED_TERMINAL_SUFFIX" and
                            row.get("status") == "UNSUPPORTED_NO_CONTROLLED_TERMINAL_SUFFIX", "unexpected unsupported claim")
                    unresolved = True
                    continue
                require(row.get("status") == "EVALUATED", "hidden supported case")
                # Independently recheck information-boundary mutation, not a producer boolean.
                from copy import deepcopy
                mutation = deepcopy(scenario)
                for r in mutation["sealed_outcomes"]:
                    r.update(quality=1-r["quality"], cost_decimal="999")
                require(prepare_game(mutation, "strategic", "lmsr").observation() == g.observation()
                        and row["outcome_mutation_invariant"], "outcome leakage")
            else:
                g = fixture(profile, seed, "lmsr")
            require(row["certificate"]["vector_limit"] == row.get("vector_limit", 5000), "certificate ablation identity")
            require(check(g, row["certificate"]) == row["independent_check"], "independent check mismatch")
            selected = execute(g, row["certificate"]["incumbent_commands"])
            require({k: encoded(payoff(selected)[k]) for k in ("cash", "external", "effort", "utility")} == row["payoff"]
                    and payoff(selected)["allocation"] == row["allocation"], "witness payoff mismatch")
            for mode in ("exhaustive", "dynamic_programming"):
                baseline = row[mode]
                require(baseline["status"] == "EXACT", "censored exact comparator")
                # Independently check the exact comparator's witness; interval equality
                # plus a sound zero-gap proof authenticates its optimum without searching.
                replayed = execute(g, baseline["commands"])
                require(encoded(payoff(replayed)["utility"]) == baseline["utility"], "exact witness mismatch")
                require(baseline["utility"] == row["certificate"]["lower"] == row["certificate"]["upper"], "exact baselines disagree")
            beam = execute(g, row["beam"]["commands"])
            require(encoded(payoff(beam)["utility"]) == row["beam"]["utility"] and
                    Fraction(*row["beam"]["utility"]) <= Fraction(*row["certificate"]["upper"]), "beam witness or bound mismatch")
            require(encoded(upper(g, vector_limit=0)) == row["root_fallback_upper"] and
                    encoded(upper(g, vector_limit=5000)) == row["root_endpoint_upper"], "bound ablation mismatch")
            # Rebuild no-action and signal-following witnesses without producer search routines.
            from deviation.verification.domain import actions, advance, terminal
            no = g
            while not terminal(no):
                no = advance(no, next(actions(no)))
            require(encoded(payoff(no)["utility"]) == row["no_action"], "no-action comparator mismatch")
            honest = execute(g, row["honest_commands"])
            require(encoded(payoff(honest)["utility"]) == row["honest"], "signal-following payoff mismatch")
            from deviation.markets.policies import SignalFollowing
            control, actual_commands = g, []
            while not terminal(control):
                req = SignalFollowing().act(control.policy_packet())
                actual_commands.append(req)
                control = advance(control, req)
            require(actual_commands == row["honest_commands"], "signal-following strategy mismatch")
            if result["kind"] == "fee_sensitivity":
                groups[seed, profile["external"]][profile["fee"]] = Fraction(*row["certificate"]["lower"])-Fraction(*row["no_action"])
        require(unique == expected_cells, "registered exact grid missing cells")
        if result["kind"] == "fee_sensitivity":
            require(all(set(v) == {0, 2, 4} for v in groups.values()), "fee paired grid coverage")
            monotonic = all(v[0] >= v[2] >= v[4] for (s, e), v in groups.items() if e == 6)
            strict = any(v[0] > v[4] for (s, e), v in groups.items() if e == 6)
            null = all(max(v.values()) <= 0 for (s, e), v in groups.items() if e == 0)
            supported = monotonic and strict and null and not unresolved
            checks.append({"monotonic": monotonic, "strict": strict, "zero_external_null": null,
                           "unsupported_cases": sum(r.get("status", "").startswith("UNSUPPORTED") for r in rows),
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
            require(sum(a["reserved_cost"] for a in row["plan"]["allocations"]) <= scenario["reservation_budget"], "reservation budget violation")
            values[s, correlated][mechanism] = Fraction(str(summary["evaluation"]["total_preference_proxy"]))
        require(unique == {(s, c, m) for s in plan["seeds"] for c in (False, True)
                          for m in ("lmsr", "pool", "uniform", "cheapest", "random", "best-fixed")}, "correlation grid mismatch")
        differences = {str(c): sum(values[s, c]["pool"]-values[s, c]["lmsr"] for s in plan["seeds"])/len(plan["seeds"]) for c in (False, True)}
        supported = differences["True"] >= 0 and differences["True"] >= differences["False"]
        checks.append({"mean_total_proxy_pool_minus_market": {k: str(v) for k, v in differences.items()},
                       "uncertainty": "Three seed blocks, two tasks each; descriptive only, no generalization inference"})
    return dict(version="research-review-1", result_sha256=sha(result),
                integrity="PASS", criterion=plan.get("success_rule", "all_analytic_checks"),
                criterion_status="NOT_EVALUABLE_ON_REGISTERED_GRID" if unresolved else
                                 "SUPPORTED_ON_REGISTERED_GRID" if supported else "REJECTED_ON_REGISTERED_GRID",
                narrative_claim_status="SCIENTIFIC_REVIEW_REQUIRED",
                checks=checks, signed_diagnostic_status=signed_status,
                novelty="NOT_ESTABLISHED", independent_scientific_review="PENDING",
                limitation="Automated numerical gate, separately implemented certificate checker, shared trusted engine. No external peer review.")
