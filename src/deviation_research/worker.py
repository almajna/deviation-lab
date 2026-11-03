"""Fixed experiment adapters; imported/executed only inside the OS sandbox."""
from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_CEILING
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import sys


def lmsr_baseline(plan):
    from deviation.markets.numeric import funding, quote
    rows = []
    with localcontext() as context:
        context.prec = 70
        def cost(q, b):
            return Decimal(b)*sum((Decimal(x)/b).exp() for x in q).ln()
        for b in (1, 3, 8):
            for q in product((0, 1, 4), repeat=3):
                for k in range(3):
                    after = list(q); after[k] += 1
                    # Exact translation/permutation cases avoid decimal near-integer ambiguity.
                    analytic = cost(after, b)-cost(q, b)
                    charge = int(analytic.to_integral_value(rounding=ROUND_CEILING))
                    actual = quote(list(q), after, b)["charge"]
                    bound = Decimal(b)*Decimal(3).ln()
                    loss = Decimal(max(q))-(cost(q, b)-cost((0, 0, 0), b))
                    rows.append(dict(b=b, before=list(q), after=after, analytic_charge=charge,
                        engine_charge=actual, loss_le_b_log_n=loss <= bound,
                        funding=funding(b), analytic_funding=int(bound.to_integral_value(rounding=ROUND_CEILING))))
    signed_rows = []
    if plan.get("signed_diagnostic"):
        spec = plan["signed_diagnostic"]
        with localcontext() as context:
            context.prec = 70
            for b in spec["liquidities"]:
                for before, after in spec["transitions"]:
                    shifts = [a-z for a, z in zip(sorted(after), sorted(before))]
                    analytic = Decimal(shifts[0]) if len(set(shifts)) == 1 else cost(sorted(after), b)-cost(sorted(before), b)
                    actual = quote(before, after, b)
                    signed_rows.append(dict(b=b, before=before, after=after, analytic_delta=str(analytic),
                        analytic_charge=int(analytic.to_integral_value(rounding=ROUND_CEILING)),
                        engine_charge=actual["charge"], engine_interval=actual["interval"]))
    return dict(kind="lmsr_baseline", rows=rows, signed_rows=signed_rows, data_kind="SYNTHETIC",
                reproduction="Hanson LMSR cost-function/finite-grid bounded-loss reproduction; not full paper replication")


def _cert_case(g, expansions=20, vector_limit=5000):
    from deviation.attacks.certified.solver import solve
    from deviation.attacks.search import search
    from deviation.verification.checker import check
    from deviation.verification.domain import exact, execute, encoded, payoff
    from deviation.attacks.search import reference
    from deviation.verification.bounds import upper
    certificate = solve(g, max_expansions=expansions, vector_limit=vector_limit)
    checked = check(g, certificate)
    exhaustive = exact(g, max_nodes=4000)
    dp = exact(g, max_nodes=4000, memoize=True)
    beam = search(g, method="beam", max_nodes=100, beam_width=2, seed=g.seed)
    honest, honest_commands = reference(g, "signal_following")
    noop, _ = reference(g, "no_action")
    selected = execute(g, certificate["incumbent_commands"])
    return dict(certificate=certificate, independent_check=checked,
                exhaustive=exhaustive, dynamic_programming=dp,
                beam={"utility": beam["selected"]["utility"], "commands": beam["commands"]},
                honest=encoded(payoff(honest)["utility"]), honest_commands=honest_commands,
                no_action=encoded(payoff(noop)["utility"]),
                payoff={k: encoded(payoff(selected)[k]) for k in ("cash", "external", "effort", "utility")},
                allocation=payoff(selected)["allocation"],
                root_endpoint_upper=encoded(upper(g, vector_limit=5000)),
                root_fallback_upper=encoded(upper(g, vector_limit=0)))


def fee_sensitivity(plan):
    from deviation.attacks.environments import environment
    from deviation.attacks.game import prepare_game
    from deviation.data.pipeline import digest
    from deviation.markets.contracts import Rejection
    rows = []
    for seed in plan["seeds"]:
        for external in (0, 6):
            for fee in (0, 2, 4):
                profile = dict(fee=fee, external=external, quantity=2)
                scenario, _, _ = environment(profile, seed, realization_seed=987654)
                try:
                    game = prepare_game(scenario, "strategic", "lmsr")
                except Rejection as exc:
                    if exc.code != "NO_CONTROLLED_TERMINAL_SUFFIX":
                        raise
                    rows.append(dict(seed=seed, profile=profile, status="UNSUPPORTED_NO_CONTROLLED_TERMINAL_SUFFIX"))
                    continue
                # Mutation control demonstrates no realized-outcome access in preparation/search.
                mutated = deepcopy(scenario)
                for row in mutated["sealed_outcomes"]:
                    row.update(quality=1-row["quality"], cost_decimal="999")
                other = prepare_game(mutated, "strategic", "lmsr")
                rows.append(dict(seed=seed, profile=profile, status="EVALUATED", observation_sha256=digest(game.observation()),
                    outcome_mutation_invariant=game.observation() == other.observation(), **_cert_case(game)))
    return dict(kind="fee_sensitivity", rows=rows, data_kind="SYNTHETIC")


def certificate_ablation(plan):
    from deviation.verification.fixtures import fixture
    rows = []
    for seed in plan["seeds"]:
        for horizon in (1, 2):
            profile = dict(capital=8, external=8, fee=0, b=3, quantity=1,
                           information="mixed", aliases=1, horizon=horizon)
            game = fixture(profile, seed, "lmsr")
            for limit in (0, 5000):
                rows.append(dict(seed=seed, profile=profile, vector_limit=limit, **_cert_case(game, vector_limit=limit)))
    return dict(kind="certificate_ablation", rows=rows, data_kind="SYNTHETIC")


def forecast_correlation(plan):
    from deviation.attacks.environments import environment
    from deviation.markets.runner import run
    rows = []
    for seed in plan["seeds"]:
        for correlated in (False, True):
            profile = dict(external=0, belief_quality=50, correlated=correlated)
            scenario, _, _ = environment(profile, seed, realization_seed=100000+seed)
            # Same tasks, generated signals, costs, outcome realization and funding for every rule.
            for mechanism in ("lmsr", "pool", "uniform", "cheapest", "random", "best-fixed"):
                result = run(scenario, mechanism)
                summary = result["trace"]["events"][-1]["payload"]
                rows.append(dict(seed=seed, correlated=correlated, mechanism=mechanism,
                    plan=result["allocation_plan"], summary=summary, receipt_sha256=result["sha256"]))
    return dict(kind="forecast_correlation", rows=rows, data_kind="SYNTHETIC",
                warning="Two-agent prescribed belief perturbations; no posterior-optimality or general correlation claim")


def isolation_probe(plan):
    import socket
    blocked = {}
    for label, path in [("read", plan["read_path"]), ("write", plan["write_path"])]:
        try:
            if label == "read":
                Path(path).read_bytes()
            else:
                Path(path).write_text("must be blocked")
            blocked[label] = False
        except OSError:
            blocked[label] = True
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=0.3).close()
        blocked["network"] = False
    except OSError:
        blocked["network"] = True
    return blocked


def main():
    runner, input_path, output_path = sys.argv[1:]
    payload = json.loads(Path(input_path).read_text())
    if runner == "review":
        from .review import review
        result = review(payload)
    else:
        result = {"lmsr_baseline": lmsr_baseline, "fee_sensitivity": fee_sensitivity,
                  "certificate_ablation": certificate_ablation, "forecast_correlation": forecast_correlation,
                  "isolation_probe": isolation_probe}[runner](payload)
    from .records import source_hash
    from deviation.verification.checker import source_sha
    result = {"value": result, "harness_source_sha256": source_hash(), "engine_source_sha256": source_sha()}
    Path(output_path).write_text(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
