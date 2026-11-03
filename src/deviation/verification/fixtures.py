"""Independent synthetic fixtures with declared, outcome-free public schedules."""
from copy import deepcopy
from fractions import Fraction
import random

from deviation.attacks.game import Game
from deviation.contracts import prompt_group
from deviation.data.pipeline import digest
from deviation.markets.engine import Engine, market_id
from deviation.markets.policies import SignalFollowing
from deviation.simulator.reservations import fit_reservations


def fixture(profile, seed, mechanism):
    """Return a Game, never a scenario containing labels or future private signals.

    Registry/funding/tokens/total optional slots stay fixed across alias allocation.
    Common beliefs are prescribed signals, not posteriors or hidden true outcomes.
    """
    rng = random.Random(seed)
    tasks = [{"task_id": f"task-{i}", "prompt": f"Independent synthetic task {i}",
              "model_options": ["m0", "m1"]} for i in range(2)]
    rows, groups = [], {}
    for i in range(2):
        prompt = f"Independent synthetic training {i}"
        groups[prompt_group(prompt)] = "train"
        for m, amount in [("m0", "0.000000001"), ("m1", "0.000000002")]:
            rows.append({"task_id": f"fit-{i}", "prompt": prompt, "model_id": m,
                         "cost_decimal": amount, "cost_unit": "synthetic_units"})
    for t in tasks:
        groups[prompt_group(t["prompt"])] = "validation"
    artifact = fit_reservations(rows, groups, tasks,
        source_manifest_sha256=digest(["independent-certificate-fixtures-1", profile, seed]),
        split_manifest_sha256=digest(groups), data_kind="SYNTHETIC",
        cost_unit="nano_synthetic_units")
    mids = sorted(market_id(t["task_id"], m) for t in tasks for m in t["model_options"])
    def draw():
        a = rng.randrange(4)
        b = rng.randrange(4 - a)
        return [a, b, 3 - a - b]
    beliefs = {m: ([1, 1, 1] if profile["information"] == "uniform" else draw()) for m in mids}
    honest = {m: (list(reversed(p)) if profile["information"] == "conflicting" else draw())
              for m, p in beliefs.items()}
    capital, horizon = profile["capital"], profile["horizon"]
    split = capital // 2 if profile["aliases"] == 2 else 0
    agents = {"h0": {"controller": "honest", "wallet": 16},
              "z0": {"controller": "strategic", "wallet": capital - split},
              "z1": {"controller": "strategic", "wallet": split}}
    controllers = {
        "honest": {"cash_cap": 16, "token_cap": 4, "action_cap": 4,
                   "position_cap": 100, "external_weights": {}, "effort_per_attempt": 0},
        "strategic": {"cash_cap": capital, "token_cap": 8, "action_cap": horizon,
                      "position_cap": 100,
                      "external_weights": {t["task_id"]: {rng.choice(["m0", "m1"]): profile["external"]}
                                           for t in tasks}, "effort_per_attempt": 0}}
    economics = {"b": profile["b"], "report_denominator": 3, "score_scale": 1,
        "price_denominator": 3000000, "fee": profile["fee"],
        "order_limit": profile["quantity"], "agent_position_limit": 100,
        "cell_position_limit": 1000, "action_limit": 100, "candidate_limit": 10000,
        "rounds": 1, "sponsor_cap": 100000}
    order = list(mids)
    rng.shuffle(order)
    schedule = [["h0", m] for m in mids] + [
        ["z" + str(i % profile["aliases"]), order[i % len(order)]] for i in range(horizon)]
    engine = Engine(tasks, economics, agents, controllers, schedule)
    scope = "reports" if mechanism == "pool" else "terminal"
    game = Game(engine, tasks, artifact, "1", {"m0": 0.25, "m1": 0.75}, 3,
                seed, mechanism, "strategic", beliefs, scope, [], {})
    target = sorted(engine.tokens)[-1]
    for a, mid in sorted(engine.tokens):
        if scope == "reports" and (a, mid) == target:
            game.report_slots = [target]
            continue
        engine.commit(a, mid, honest[mid] if a == "h0" else beliefs[mid])
    if scope == "reports":
        game.announced_reports = {"h0": deepcopy(honest)}
        return game
    engine.reveal()
    policy = SignalFollowing()
    while engine.turn < len(mids):
        a, mid = schedule[engine.turn]
        packet = engine.snapshot(a, mid)
        packet.update(schema_version="0.3", agent_id=a, mechanism=mechanism,
            own_signal=honest[mid], decline_report=False, report_token=engine.tokens[a, mid],
            own_last_report=engine.reports.get((a, mid)),
            own_group_positions=engine.books[mid]["holdings"][a],
            own_group_position_cap=100, own_utility_view={},
            reservations=artifact["reservations"], reservation_budget=3,
            public_tasks=tasks, remaining_slots=len(schedule) - engine.turn)
        engine.apply(policy.act(packet), allowed_kinds={"no_op", "trade_shares"}
                     if mechanism == "lmsr" else {"no_op", "update_distribution"})
    return game
