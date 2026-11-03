"""v0.3 deterministic market simulator; sealed data enters only after lock."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

from deviation.contracts import validate_allocation
from deviation.data.pipeline import digest
from deviation.simulator.policies import ReferenceAllocator, optimize
from deviation.simulator.reservations import fit_reservations
from deviation.simulator.runner import _selected_report, implementation_sha256
from .contracts import Rejection, action, closed, counts, integer, mean, text
from .engine import Engine, market_id
from .numeric import POLICY_SHA256, prices, project_rational, transform
from .policies import SignalFollowing, fit_temperature, pooled

MECHANISMS = ["lmsr", "pool", "interactive-pool", "calibrated-pool", "score", "uniform", "random", "cheapest", "best-fixed"]


def allowed_actions(mechanism):
    return {"no_op", "trade_shares"} if mechanism == "lmsr" else ({"no_op", "update_distribution"} if mechanism == "interactive-pool" else {"no_op"})


def allocation_config(budget, unit):
    return {"schema_version": "0.2", "reservation_budget": budget, "cost_unit": unit,
        "agent_accounts": ["reference"], "maker_account": "reference_maker", "fee_sink_account": "reference_sink",
        "initial_balances": {"reference": 0, "reference_maker": 0, "reference_sink": 0}, "exogenous_history_actors": []}


def _prepare(s):
    closed(s, "execution_version experiment_id seed data_kind source_manifest_sha256 split_manifest_sha256 code_revision training_rows split_groups decision_tasks training_calibration_rows reservation_budget cost_unit economics agents controllers")
    # Sealed outcomes are deliberately absent from this preparation projection.
    if s["execution_version"] != "markets-1": raise Rejection("INVALID_VERSION")
    integer(s["seed"]); integer(s["reservation_budget"]); text(s["experiment_id"])
    if s["data_kind"] != "SYNTHETIC": raise Rejection("SYNTHETIC_ONLY")
    if s["code_revision"] != "SYNTHETIC_FIXTURE": raise Rejection("INVALID_PROVENANCE")
    artifact = fit_reservations(s["training_rows"], s["split_groups"], s["decision_tasks"],
        source_manifest_sha256=s["source_manifest_sha256"], split_manifest_sha256=s["split_manifest_sha256"],
        data_kind=s["data_kind"], cost_unit=s["cost_unit"])
    tasks = sorted(deepcopy(s["decision_tasks"]), key=lambda t: t["task_id"])
    mids = sorted(market_id(t["task_id"], m) for t in tasks for m in t["model_options"])
    if not isinstance(s["agents"], dict) or not s["agents"]: raise Rejection("INVALID_CONFIG")
    definitions = {}
    for a, spec in s["agents"].items():
        closed(spec, "controller wallet signals decline_report")
        if type(spec["decline_report"]) is not bool: raise Rejection("INVALID_TYPE")
        if not isinstance(spec["signals"], dict) or set(spec["signals"]) != set(mids): raise Rejection("SIGNAL_COVERAGE")
        for values in spec["signals"].values(): counts(values, s["economics"]["report_denominator"])
        definitions[a] = {"controller": spec["controller"], "wallet": spec["wallet"]}
    # Validate calibration identity/provenance even in non-calibrated treatments.
    T = fit_temperature(s["training_calibration_rows"], s["training_rows"],
                        s["economics"]["report_denominator"], s["economics"]["price_denominator"])
    quality = {}
    for m in artifact["reservations"]:
        values = [Fraction(r["category"], 2) for r in s["training_calibration_rows"] if r["model_id"] == m]
        quality[m] = float(sum(values) / len(values))
    schedule = []
    integer(s["economics"]["rounds"], 0, 100)
    for _ in range(s["economics"]["rounds"]):
        round_slots = [[a, m] for a in sorted(definitions) for m in mids]
        schedule.extend(round_slots)
    random.Random(s["seed"]).shuffle(schedule)
    engine = Engine(tasks, s["economics"], definitions, s["controllers"], schedule)
    # External preferences may name only public eligible task/model pairs.
    catalog = {t["task_id"]: set(t["model_options"]) for t in tasks}
    for controller in s["controllers"].values():
        for task, weights in controller["external_weights"].items():
            if task not in catalog or set(weights) - catalog[task]: raise Rejection("INVALID_PREFERENCES")
    return tasks, artifact, T, quality, engine


def packet(engine, scenario, actor, mid, mechanism, artifact):
    p = engine.snapshot(actor, mid)
    group = engine.agents[actor]["controller"]
    members = [a for a in engine.agents if engine.agents[a]["controller"] == group]
    p.update(schema_version="0.3", agent_id=actor, mechanism=mechanism,
        own_signal=deepcopy(scenario["agents"][actor]["signals"][mid]),
        decline_report=scenario["agents"][actor]["decline_report"],
        report_token=engine.tokens[(actor, mid)], own_last_report=deepcopy(engine.reports.get((actor, mid))),
        own_group_positions=[sum(engine.books[mid]["holdings"][a][k] for a in members) for k in range(3)],
        own_group_position_cap=engine.controllers[group]["position_cap"],
        own_utility_view=deepcopy(engine.controllers[group]["external_weights"]),
        reservations=deepcopy(artifact["reservations"]), reservation_budget=scenario["reservation_budget"],
        public_tasks=deepcopy(scenario["decision_tasks"]))
    p["remaining_slots"] = len(engine.schedule) - engine.turn
    return p


def _allocation(engine, tasks, artifact, mechanism, T, quality, budget, seed):
    P, D = engine.cfg["price_denominator"], engine.cfg["report_denominator"]
    values = {}
    for t in tasks:
        values[t["task_id"]] = {}
        for m in t["model_options"]:
            mid = market_id(t["task_id"], m)
            if mechanism == "lmsr": p = prices(engine.books[mid]["q"], engine.cfg["b"], P)
            elif mechanism == "uniform": p = project_rational([1, 1, 1], P)
            else: p = transform(pooled(engine.reports, mid, D), T if mechanism == "calibrated-pool" else "1", P)
            values[t["task_id"]][m] = mean(p, P)
    if mechanism in {"random", "cheapest", "best-fixed"}:
        plan = ReferenceAllocator(mechanism, seed=seed, training_means=quality).allocate(tasks, [], artifact, budget)
    else:
        plan = {"schema_version": "0.2", "reservation_budget": budget, "cost_unit": artifact["cost_unit"],
                "reservation_artifact_sha256": artifact["artifact_sha256"],
                "allocations": optimize(tasks, artifact["reservations"], budget, values)}
    validate_allocation(plan, artifact, tasks, run_config=allocation_config(budget, artifact["cost_unit"]))
    encoded = {t: {m: {"numerator": v.numerator, "denominator": v.denominator} for m, v in row.items()} for t, row in values.items()}
    return plan, encoded


def run(scenario, mechanism="lmsr", *, policies=None):
    if mechanism not in MECHANISMS: raise Rejection("INVALID_MECHANISM")
    if not isinstance(scenario, dict) or "sealed_outcomes" not in scenario: raise Rejection("INVALID_FIELDS")
    # Preparation/reporting/trading functions receive no outcome-store argument.
    public = deepcopy({k: v for k, v in scenario.items() if k != "sealed_outcomes"})
    tasks, artifact, T, quality, engine = _prepare(public)
    identities = sorted(engine.agents)
    injected = policies is not None
    policies = policies if policies is not None else {a: SignalFollowing() for a in identities}
    if set(policies) != set(identities): raise Rejection("POLICY_COVERAGE")
    for slot, (actor, mid) in enumerate(sorted(engine.tokens)):
        info = packet(engine, public, actor, mid, mechanism, artifact)
        request = deepcopy(policies[actor].act(deepcopy(info)))
        if request is None:
            engine.commit(actor, mid, None)
            continue
        try:
            action(request)
            if (request["kind"] != "report_distribution" or request["actor"] != actor
                    or request["market_id"] != mid or request["report_token"] != engine.tokens[(actor, mid)]
                    or request["stage"] != "REPORT_COMMIT" or request["expected_state_seq"] != 0
                    or request["denominator"] != engine.cfg["report_denominator"]): raise Rejection("INVALID_COMMIT")
            engine.commit(actor, mid, request["counts"], request["order_id"])
        except Rejection as exc:
            engine.commit(actor, mid, None)  # Consume this report token as a decline.
            engine.rejected += 1
            engine.emit("action_rejected", {"actor": actor, "slot": slot, "reason": exc.code,
                                          "reserved_order_id": None}, actor)
    engine.reveal()
    while engine.turn < len(engine.schedule):
        actor, mid = engine.schedule[engine.turn]
        info = packet(engine, public, actor, mid, mechanism, artifact)
        engine.apply(deepcopy(policies[actor].act(deepcopy(info))), allowed_kinds=allowed_actions(mechanism))
    plan, values = _allocation(engine, tasks, artifact, mechanism, T, quality, public["reservation_budget"], public["seed"])
    engine.lock(plan, values, artifact["artifact_sha256"])
    # Hard barrier: no label/cost access above this line.
    sealed = deepcopy(scenario["sealed_outcomes"])
    pairs = {(t["task_id"], m) for t in tasks for m in t["model_options"]}
    realized, evaluation = _selected_report(plan, sealed, pairs)
    categories = {}
    for row in sealed:
        if row["quality"] not in [0, 0.5, 1]: raise Rejection("INVALID_CATEGORY")
        categories[market_id(row["task_id"], row["model_id"])] = int(row["quality"] * 2)
    engine.settle(categories)
    engine.emit("economic_summary", summary(engine, plan, realized, evaluation))
    trace = {"schema_version": "0.3", "experiment_id": public["experiment_id"], "seed": public["seed"],
        "data_kind": "SYNTHETIC", "agent_origin": "SYNTHETIC", "quality_semantics": "synthetic_fixture",
        "stage": "SETTLED", "mechanism": mechanism, "numeric_policy_sha256": POLICY_SHA256,
        "config_sha256": digest(public), "source_manifest_sha256": public["source_manifest_sha256"],
        "split_manifest_sha256": public["split_manifest_sha256"], "code_sha256": implementation_sha256(),
        "events": engine.events}
    result = {"execution_version": "markets-1", "input_sha256": digest(scenario), "injected_policies": injected,
        "implementation_sha256": implementation_sha256(), "mechanism": mechanism,
        "public_config": {"economics": engine.cfg, "agents": engine.agents, "controllers": engine.controllers,
                          "schedule": engine.schedule, "tasks": tasks, "temperature": T, "training_means": quality,
                          "reservation_budget": public["reservation_budget"]},
        "reservation_artifact": artifact, "allocation_plan": plan, "trace": trace}
    result["sha256"] = digest(result)
    from .validation import validate_result
    validate_result(result)
    return result


def summary(engine, plan, realized, evaluation):
    controller_utilities = {}
    for cid, config in engine.controllers.items():
        members = [a for a in engine.agents if engine.agents[a]["controller"] == cid]
        delta = sum(engine.balances[engine.wallet(a)] - engine.initial[engine.wallet(a)] for a in members)
        external = sum(config["external_weights"].get(c["task_id"], {}).get(c["model_id"], 0) for c in plan["allocations"])
        effort = config["effort_per_attempt"] * sum(engine.attempts[a] for a in members)
        controller_utilities[cid] = {"cash_delta": delta, "external_benefit": external,
                                     "noncash_effort_cost": effort, "utility": delta + external - effort}
    losses = {m: max(b["funding"] - engine.balances[engine.maker(m)], 0) for m, b in engine.books.items()}
    return {"initial_balances": engine.initial, "final_balances": engine.balances,
        "controllers": controller_utilities, "maker_losses": losses, "score_reserve": engine.score_reserve,
        "score_paid": engine.score_reserve - engine.balances["scoring_pool"], "fees": engine.balances["fee_sink"],
        "accepted": engine.accepted, "rejected": engine.rejected, "realized_report": realized, "evaluation": evaluation}


def replay(scenario, expected):
    if expected["injected_policies"]: raise Rejection("INJECTED_POLICY_REPLAY_REQUIRES_COMMANDS")
    actual = run(scenario, expected["mechanism"])
    if actual != expected: raise Rejection("REPLAY_MISMATCH")
    return actual


def write_bundle(result, destination):
    path = Path(destination); path.mkdir(parents=True, exist_ok=True)
    encode = lambda x: json.dumps(x, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (path / "replay.json").write_text(encode(result["trace"]), encoding="utf-8")
    (path / "receipts.json").write_text(encode(result), encoding="utf-8")
    (path / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in result["trace"]["events"]), encoding="utf-8")
    import hashlib
    (path / "manifest.json").write_text(encode({"execution_version": "markets-1", "receipt_sha256": result["sha256"],
        "files": {p: hashlib.sha256((path / p).read_bytes()).hexdigest() for p in ["replay.json", "receipts.json", "events.jsonl"]}}), encoding="utf-8")
