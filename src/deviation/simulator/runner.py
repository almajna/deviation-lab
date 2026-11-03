"""Trusted deterministic runner. Only completed decisions can reveal outcomes.

Policies are trusted in-process Python, not a security sandbox. No dynamic code
loading, model API, network call or final-evaluation runner is provided.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from deviation.contracts import (ContractError, validate_action, validate_allocation,
    validate_information, validate_ledger, validate_realized_report,
    validate_run_config, validate_trace)
from deviation.data.pipeline import digest
from .policies import ReferenceAllocator, ReportSignal
from .reservations import fit_reservations, nanos


def _integer(value):
    if type(value) is not int or value < 0:
        raise ContractError("expected nonnegative integer")


def implementation_sha256():
    # Bind the entire local package, including scientific boundary validators and
    # digest/split helpers. Stable package-relative keys work in wheels/checkouts.
    root = Path(__file__).parent.parent
    return digest({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(root.rglob("*.py"))})


def _validate_scenario(s):
    expected = {"execution_version", "experiment_id", "seed", "policy", "run_config",
                "training_rows", "split_groups", "decision_tasks", "training_quality_rows",
                "source_manifest_sha256", "split_manifest_sha256", "data_kind",
                "code_revision", "agent_specs", "sealed_outcomes", "settlement"}
    if not isinstance(s, dict) or set(s) != expected or s["execution_version"] != "simulator-1":
        raise ContractError("unknown execution input fields/version")
    validate_run_config(s["run_config"])
    _integer(s["seed"])
    if not isinstance(s["experiment_id"], str) or not s["experiment_id"].strip():
        raise ContractError("missing experiment identity")
    if s["data_kind"] not in {"SYNTHETIC", "RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS"}:
        raise ContractError("unsupported provenance")
    if s["data_kind"] != "SYNTHETIC" and not re.fullmatch(r"[0-9a-f]{40}", s["code_revision"]):
        raise ContractError("recorded execution requires pinned code revision")
    specs = s["agent_specs"]
    if not isinstance(specs, dict) or set(specs) != set(s["run_config"]["agent_accounts"]):
        raise ContractError("agent specification coverage mismatch")
    for spec in specs.values():
        if not isinstance(spec, dict) or set(spec) != {"agent_kind", "action_fee", "signals"}:
            raise ContractError("unknown agent specification")
        _integer(spec["action_fee"])
        if not isinstance(spec["signals"], dict) or set(spec["signals"]) != {t["task_id"] for t in s["decision_tasks"]}:
            raise ContractError("synthetic signal task coverage mismatch")
    st = s["settlement"]
    if not isinstance(st, dict) or set(st) != {"transfers", "external_benefits", "noncash_effort_costs", "maker_initial_subsidy"}:
        raise ContractError("unknown settlement accounting inputs")
    if not isinstance(st["transfers"], list):
        raise ContractError("invalid settlement transfer list")
    _integer(st["maker_initial_subsidy"])
    for field in ["external_benefits", "noncash_effort_costs"]:
        if not isinstance(st[field], dict) or set(st[field]) != set(specs):
            raise ContractError("utility parameter coverage mismatch")
        for value in st[field].values():
            _integer(value)


def _selected_report(plan, sealed_outcomes, expected_pairs):
    """Called only after allocation validation; complete paired store required."""
    store = {}
    if not isinstance(sealed_outcomes, list):
        raise ContractError("sealed outcomes must be a list")
    for row in sealed_outcomes:
        if not isinstance(row, dict) or set(row) != {"task_id", "model_id", "quality", "cost_decimal"}:
            raise ContractError("invalid sealed outcome fields")
        if any(not isinstance(row[k], str) or not row[k].strip() for k in ["task_id", "model_id"]):
            raise ContractError("invalid sealed outcome identifier")
        key = (row["task_id"], row["model_id"])
        if key in store:
            raise ContractError("duplicate sealed outcome")
        q = row["quality"]
        if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0 <= q <= 1:
            raise ContractError("invalid quality proxy")
        store[key] = {"quality": q, "cost": nanos(row["cost_decimal"])}
    if set(store) != expected_pairs:
        raise ContractError("complete sealed paired-outcome coverage required")
    selected, actual, positive, unused, quality = [], 0, 0, 0, Fraction(0)
    for choice in plan["allocations"]:
        key = (choice["task_id"], choice["model_id"])
        row = {"quality": 0, "cost": 0} if choice["model_id"] is None else store.get(key)
        if row is None:
            raise ContractError("missing selected paired outcome")
        cost, reserve = row["cost"], choice["reserved_cost"]
        selected.append({"task_id": choice["task_id"], "model_id": choice["model_id"], "realized_cost": cost})
        quality += Fraction(str(row["quality"]))
        actual += cost
        positive += max(cost - reserve, 0)
        unused += max(reserve - cost, 0)
    reserved = sum(c["reserved_cost"] for c in plan["allocations"])
    report = {"schema_version": "0.2", "phase": "SETTLED", "cost_unit": plan["cost_unit"],
              "selected_costs": selected, "reservation_spend": reserved, "realized_spend": actual,
              "positive_task_overruns": positive, "unused_reservations": unused,
              "net_overrun": actual - reserved,
              "realized_budget_excess": max(actual - plan["reservation_budget"], 0),
              "realized_budget_violated": actual > plan["reservation_budget"]}
    return report, {"phase": "POST_SETTLEMENT", "total_preference_proxy": float(quality),
                    "mean_preference_proxy": float(quality / len(selected)),
                    "abstentions": sum(c["model_id"] is None for c in selected)}


def _training_means(s):
    expected = {(r["task_id"], r["model_id"]) for r in s["training_rows"]}
    seen, values = set(), {}
    if not isinstance(s["training_quality_rows"], list):
        raise ContractError("training qualities must be a list")
    for row in s["training_quality_rows"]:
        if not isinstance(row, dict) or set(row) != {"task_id", "model_id", "quality"}:
            raise ContractError("invalid training quality fields")
        pair, q = (row["task_id"], row["model_id"]), row["quality"]
        if pair not in expected or pair in seen:
            raise ContractError("non-training or duplicate baseline quality")
        if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0 <= q <= 1:
            raise ContractError("invalid training quality")
        seen.add(pair)
        values.setdefault(row["model_id"], []).append(Fraction(str(q)))
    if seen != expected:
        raise ContractError("incomplete training baseline quality")
    return {m: float(sum(v) / len(v)) for m, v in values.items()}


def _ledger(config, fees, settlement):
    initial = deepcopy(config["initial_balances"])
    balances = deepcopy(initial)
    transfers = deepcopy(fees)
    for transfer in settlement["transfers"]:
        if not isinstance(transfer, dict) or transfer.get("reason") != "settlement":
            raise ContractError("configured payouts must be labeled settlement")
        transfers.append(deepcopy(transfer))
    ids = set()
    for transfer in transfers:
        if not isinstance(transfer, dict) or set(transfer) != {"transfer_id", "payer", "payee", "amount", "reason"}:
            raise ContractError("invalid transfer fields")
        for key in ["transfer_id", "payer", "payee"]:
            if not isinstance(transfer[key], str) or not transfer[key]:
                raise ContractError("invalid transfer identity")
        _integer(transfer["amount"])
        payer, payee, amount = transfer["payer"], transfer["payee"], transfer["amount"]
        if (transfer["transfer_id"] in ids or payer not in balances or payee not in balances
                or payer == payee or amount <= 0 or balances[payer] < amount):
            raise ContractError("unfunded, duplicate or invalid transfer")
        ids.add(transfer["transfer_id"])
        balances[payer] -= amount
        balances[payee] += amount
    utilities = {}
    for agent in config["agent_accounts"]:
        delta = balances[agent] - initial[agent]
        benefit, effort = settlement["external_benefits"][agent], settlement["noncash_effort_costs"][agent]
        utilities[agent] = {"cash_delta": delta, "external_benefit": benefit,
                            "noncash_effort_cost": effort, "utility": delta + benefit - effort}
    pnl = balances[config["maker_account"]] - initial[config["maker_account"]]
    ledger = {"schema_version": "0.2", "unit": "virtual_credit", "initial_balances": initial,
              "final_balances": balances, "transfers": transfers, "agent_utilities": utilities,
              "maker_account": config["maker_account"], "maker_initial_subsidy": settlement["maker_initial_subsidy"],
              "maker_cash_pnl": pnl, "maker_realized_loss": max(-pnl, 0)}
    validate_ledger(ledger, run_config=config)
    return ledger


def run(scenario, *, policies=None, allocator=None):
    """Execute trusted policies on copied allowlisted packets, then settle.

    Injected policies/allocators are for trusted local engineering tests only.
    They must not be untrusted code. Hidden data is never an interface argument.
    """
    s = deepcopy(scenario)
    _validate_scenario(s)
    custom = {"policies": policies is not None, "allocator": allocator is not None}
    config, tasks = s["run_config"], sorted(s["decision_tasks"], key=lambda t: t["task_id"])
    artifact = fit_reservations(s["training_rows"], s["split_groups"], tasks,
        source_manifest_sha256=s["source_manifest_sha256"], split_manifest_sha256=s["split_manifest_sha256"],
        data_kind=s["data_kind"], cost_unit=config["cost_unit"])
    training_means = _training_means(s)
    actors = sorted(config["agent_accounts"])
    policies = policies if policies is not None else {a: ReportSignal() for a in actors}
    if set(policies) != set(actors):
        raise ContractError("policy identity coverage mismatch")
    credits, fees, actions, events = deepcopy(config["initial_balances"]), [], [], []

    def emit(kind, payload, actor, *, settled=False):
        events.append({"seq": len(events), "time_step": len(events), "actor": actor,
                       "visibility": "POST_SETTLEMENT" if settled else "PUBLIC",
                       "type": kind, "payload": deepcopy(payload)})

    # No outcome-store iteration or selected-cost access occurs in this stage.
    for task in tasks:
        for agent in actors:
            spec = s["agent_specs"][agent]
            info = {"schema_version": "0.2", "agent_id": agent, "agent_kind": spec["agent_kind"],
                    "task": deepcopy(task), "private_signal": {"owner_agent_id": agent,
                    "origin": "SYNTHETIC", "forecast_kind": "expected_preference_proxy",
                    "values": deepcopy(spec["signals"][task["task_id"]])},
                    "reservation_artifact_sha256": artifact["artifact_sha256"],
                    "model_reservations": deepcopy(artifact["reservations"]), "cost_unit": config["cost_unit"],
                    "reservation_budget_remaining": config["reservation_budget"],
                    "available_credits": credits[agent], "action_fee": spec["action_fee"],
                    "action_seq": len(events), "time_step": len(events),
                    "history": [deepcopy(e) for e in events if e["type"] == "public_forecast"
                                and e["payload"]["task_id"] == task["task_id"]]}
            validate_information(info, artifact, tasks, run_config=config)
            action = deepcopy(policies[agent].act(deepcopy(info)))
            validate_action(action, info)
            actions.append(action)
            if action["action_fee"]:
                credits[agent] -= action["action_fee"]
                fees.append({"transfer_id": f"fee-{len(fees)}", "payer": agent,
                             "payee": config["fee_sink_account"], "amount": action["action_fee"], "reason": "action_fee"})
            emit("public_forecast", {"task_id": task["task_id"], "forecast_kind": "expected_preference_proxy",
                                     "values": action["values"]}, agent)
    allocator = allocator if allocator is not None else ReferenceAllocator(s["policy"], seed=s["seed"], training_means=training_means)
    plan = deepcopy(allocator.allocate(deepcopy(tasks), deepcopy(actions), deepcopy(artifact), config["reservation_budget"]))
    validate_allocation(plan, artifact, tasks, run_config=config)
    for choice in plan["allocations"]:
        emit("reservation", choice, "allocator")
    # Settlement barrier: all actions and allocations are now frozen/validated.
    expected_pairs = {(t["task_id"], m) for t in tasks for m in t["model_options"]}
    report, evaluation = _selected_report(plan, s["sealed_outcomes"], expected_pairs)
    validate_realized_report(report, plan, run_config=config)
    ledger = _ledger(config, fees, s["settlement"])
    emit("realized_cost_report", report, "system", settled=True)
    for transfer in ledger["transfers"]:
        emit("ledger_transfer", transfer, "system", settled=True)
    emit("utility_summary", ledger["agent_utilities"], "system", settled=True)
    trace = {"schema_version": "0.2", "experiment_id": s["experiment_id"], "seed": s["seed"],
             "data_kind": s["data_kind"], "agent_origin": "SYNTHETIC",
             "quality_semantics": "synthetic_fixture" if s["data_kind"] == "SYNTHETIC" else "noisy_preference_proxy",
             "phase": "SETTLED", "cost_unit": config["cost_unit"],
             "reservation_artifact_sha256": artifact["artifact_sha256"],
             "provenance": {"source_manifest_sha256": s["source_manifest_sha256"],
                            "split_manifest_sha256": s["split_manifest_sha256"], "code_revision": s["code_revision"]},
             "events": events}
    validate_trace(trace, artifact, plan, report, ledger, tasks, run_config=config)
    result = {"execution_version": "simulator-1", "input_sha256": digest(s),
              "implementation_sha256": implementation_sha256(), "policy": s["policy"],
              "trusted_test_injections": custom,
              "run_config": config, "decision_tasks": tasks, "reservation_artifact": artifact,
              "allocation_plan": plan, "realized_report": report, "ledger": ledger,
              "evaluation": evaluation, "trace": trace}
    result["sha256"] = digest(result)
    return result


def replay(scenario, expected):
    """Re-execute trusted built-ins; reject altered config, code or output bytes."""
    actual = run(scenario)
    if actual != expected or digest(actual) != digest(expected):
        raise ContractError("replay mismatch: input, implementation or output changed")
    return actual


def write_bundle(result, destination):
    """Write public completed trace + receipts/manifest; no private signals/store."""
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    encoded = lambda value: json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (path / "replay.json").write_text(encoded(result["trace"]), encoding="utf-8")
    (path / "receipts.json").write_text(encoded(result), encoding="utf-8")
    (path / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n"
                                                  for e in result["trace"]["events"]), encoding="utf-8")
    files = {name: hashlib.sha256((path / name).read_bytes()).hexdigest()
             for name in ["replay.json", "receipts.json", "events.jsonl"]}
    (path / "manifest.json").write_text(encoded({"execution_version": "simulator-1", "files": files,
        "receipt_sha256": result["sha256"], "implementation_sha256": result["implementation_sha256"]}), encoding="utf-8")
