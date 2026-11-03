"""Validate closed public receipts by regenerating all economic transitions.

Original-input replay additionally authenticates a run against private inputs.
Rejected request bodies remain private; only their effect-free slot use/reason
can be checked from public events, not the truth of that unexported request.
"""
from copy import deepcopy
from fractions import Fraction
import re

from deviation.contracts import ContractError, validate_realized_report
from deviation.data.pipeline import digest
from .contracts import Rejection, closed, event_shape, integer
from .engine import Engine
from .numeric import POLICY_SHA256


REASONS = {"INVALID_FIELDS", "INVALID_TYPE", "INVALID_DISTRIBUTION", "INVALID_VERSION", "WRONG_STAGE",
    "WRONG_ACTOR", "DUPLICATE_ID", "STALE_STATE", "ZERO_ORDER", "UNOWNED_SALE", "QUANTITY_LIMIT",
    "POSITION_LIMIT", "ACTION_LIMIT", "INSUFFICIENT_CASH", "ORDER_LIMIT", "MAKER_INSOLVENT", "NUMERIC_AMBIGUITY", "DISALLOWED_ACTION", "INVALID_ID_NAMESPACE", "INVALID_COMMIT"}


def validate_result(result):
    try: _validate(result)
    except (KeyError, TypeError, ValueError, IndexError, ArithmeticError) as exc:
        if isinstance(exc, ContractError): raise
        raise Rejection("INVALID_RECEIPT") from exc


def _validate(r):
    closed(r, "execution_version input_sha256 injected_policies implementation_sha256 mechanism public_config reservation_artifact allocation_plan trace sha256")
    if r["execution_version"] != "markets-1" or type(r["injected_policies"]) is not bool: raise Rejection("INVALID_VERSION")
    if r["sha256"] != digest({k: v for k, v in r.items() if k != "sha256"}): raise Rejection("RECEIPT_HASH")
    cfg, trace, artifact = r["public_config"], r["trace"], r["reservation_artifact"]
    closed(cfg, "economics agents controllers schedule tasks temperature training_means reservation_budget")
    if cfg["temperature"] not in ["1", "1/2", "2"]: raise Rejection("INVALID_TYPE")
    from .runner import MECHANISMS
    if r["mechanism"] not in MECHANISMS: raise Rejection("INVALID_MECHANISM")
    integer(cfg["reservation_budget"])
    closed(trace, "schema_version experiment_id seed data_kind agent_origin quality_semantics stage mechanism numeric_policy_sha256 config_sha256 source_manifest_sha256 split_manifest_sha256 code_sha256 events")
    if (trace["schema_version"] != "0.3" or trace["data_kind"] != "SYNTHETIC" or trace["agent_origin"] != "SYNTHETIC"
            or trace["stage"] != "SETTLED" or trace["quality_semantics"] != "synthetic_fixture"
            or trace["mechanism"] != r["mechanism"] or trace["numeric_policy_sha256"] != POLICY_SHA256
            or trace["code_sha256"] != r["implementation_sha256"]): raise Rejection("INVALID_VERSION")
    for value in [r["input_sha256"], r["implementation_sha256"], trace["config_sha256"], trace["source_manifest_sha256"], trace["split_manifest_sha256"]]:
        if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value): raise Rejection("INVALID_HASH")
    if not isinstance(trace["events"], list): raise Rejection("INVALID_FIELDS")
    from .contracts import text
    integer(trace["seed"]); text(trace["experiment_id"])
    for i, e in enumerate(trace["events"]):
        event_shape(e)
        if e["seq"] != i or e["time_step"] != i: raise Rejection("INVALID_SEQUENCE")
    engine = Engine(cfg["tasks"], cfg["economics"], cfg["agents"], cfg["controllers"], cfg["schedule"])
    reports = {}
    for e in trace["events"]:
        if e["type"] == "report_revealed":
            p = e["payload"]
            pair = p["actor"], p["market_id"]
            if pair in reports: raise Rejection("DUPLICATE_ID")
            reports[pair] = (p["counts"], p["order_id"])
    if set(reports) - set(engine.tokens): raise Rejection("INVALID_TOKEN")
    rejected_commits = {}
    for e in trace["events"]:
        if e["type"] == "action_rejected" and e["stage"] == "REPORT_COMMIT":
            p = e["payload"]
            if p["slot"] in rejected_commits: raise Rejection("DUPLICATE_ID")
            rejected_commits[p["slot"]] = p
    for slot, (a, mid) in enumerate(sorted(engine.tokens)):
        values, order_id = reports.get((a, mid), (None, None))
        engine.commit(a, mid, values, order_id)
        if slot in rejected_commits:
            p = rejected_commits.pop(slot)
            if values is not None or p["actor"] != a or p["reason"] not in REASONS or p["reserved_order_id"] is not None:
                raise Rejection("INVALID_COMMIT")
            engine.rejected += 1
            engine.emit("action_rejected", p, a)
    if rejected_commits: raise Rejection("INVALID_COMMIT")
    engine.reveal()
    decision_types = {"trade_accepted", "distribution_updated", "action_noop", "action_rejected"}
    for e in trace["events"]:
        if e["type"] not in decision_types: continue
        if e["stage"] == "REPORT_COMMIT": continue
        if engine.turn >= len(engine.schedule): raise Rejection("INVALID_SEQUENCE")
        a, mid = engine.schedule[engine.turn]
        p, kind = e["payload"], e["type"]
        if p["actor"] != a: raise Rejection("WRONG_ACTOR")
        if kind == "action_rejected":
            if p["slot"] != engine.turn or p["reason"] not in REASONS: raise Rejection("INVALID_TYPE")
            engine.turn += 1; engine.attempts[a] += 1; engine.rejected += 1
            if p["reserved_order_id"] is not None:
                from .contracts import text
                text(p["reserved_order_id"])
                if not p["reserved_order_id"].startswith(a + "/") or p["reserved_order_id"] in engine.used: raise Rejection("DUPLICATE_ID")
                engine.used.add(p["reserved_order_id"])
            engine.emit("action_rejected", p, a)
            continue
        request = {"schema_version": "0.3", "actor": a, "market_id": mid, "stage": "TRADE_OR_UPDATE",
            "order_id": p["order_id"],
            "expected_state_seq": engine.books[mid]["seq"]}
        if kind == "trade_accepted": request.update(kind="trade_shares", share_delta=p["share_delta"], max_net_debit=p["max_net_debit"])
        elif kind == "distribution_updated": request.update(kind="update_distribution", counts=p["counts"], denominator=p["denominator"])
        else: request["kind"] = "no_op"
        from .runner import allowed_actions
        if not engine.apply(request, allowed_kinds=allowed_actions(r["mechanism"])): raise Rejection("INVALID_TRANSITION")
    # Source authentication is separate; here verify every nested arithmetic field
    # against generated transitions, not a permissive metadata schema.
    closed(artifact, "schema_version data_kind cost_unit scale method source_manifest_sha256 split_manifest_sha256 fit_group_ids fit_row_count reservations artifact_sha256")
    if (artifact["schema_version"] != "0.2" or artifact["data_kind"] != "SYNTHETIC"
            or type(artifact["scale"]) is not int or artifact["scale"] != 1_000_000_000
            or artifact["method"] != "mean_train_only_v1"): raise Rejection("INVALID_VERSION")
    integer(artifact["fit_row_count"], 1)
    if not isinstance(artifact["fit_group_ids"], list) or not artifact["fit_group_ids"]:
        raise Rejection("INVALID_FIELDS")
    for group in artifact["fit_group_ids"]:
        if not isinstance(group, str) or not re.fullmatch("[0-9a-f]{64}", group): raise Rejection("INVALID_HASH")
    if artifact["fit_group_ids"] != sorted(set(artifact["fit_group_ids"])): raise Rejection("INVALID_FIELDS")
    if not isinstance(artifact["reservations"], dict) or set(artifact["reservations"]) != set().union(*(set(t["model_options"]) for t in cfg["tasks"])):
        raise Rejection("INVALID_FIELDS")
    for n in artifact["reservations"].values(): integer(n, 1)
    if artifact["artifact_sha256"] != digest({k: v for k, v in artifact.items() if k != "artifact_sha256"}): raise Rejection("INVALID_HASH")
    if (trace["source_manifest_sha256"] != artifact["source_manifest_sha256"]
            or trace["split_manifest_sha256"] != artifact["split_manifest_sha256"]): raise Rejection("INVALID_HASH")
    from .runner import _allocation, allocation_config, summary
    plan = r["allocation_plan"]
    computed, values = _allocation(engine, cfg["tasks"], artifact, r["mechanism"], cfg["temperature"], cfg["training_means"], cfg["reservation_budget"], trace["seed"])
    if digest(plan) != digest(computed): raise Rejection("INVALID_ALLOCATION")
    engine.lock(plan, values, artifact["artifact_sha256"])
    categories = {}
    for e in trace["events"]:
        if e["type"] == "market_settled":
            p = e["payload"]
            if p["market_id"] in categories: raise Rejection("DUPLICATE_ID")
            categories[p["market_id"]] = p["category"]
    engine.settle(categories)
    summaries = [e["payload"] for e in trace["events"] if e["type"] == "economic_summary"]
    if len(summaries) != 1: raise Rejection("INVALID_FIELDS")
    realized = summaries[0]["realized_report"]
    validate_realized_report(realized, plan, run_config=allocation_config(cfg["reservation_budget"], artifact["cost_unit"]))
    quality = sum(Fraction(categories[next(mid for mid, b in engine.books.items() if b["task_id"] == c["task_id"] and b["model_id"] == c["model_id"])], 2)
                  for c in plan["allocations"] if c["model_id"] is not None)
    evaluation = {"phase": "POST_SETTLEMENT", "total_preference_proxy": float(quality),
        "mean_preference_proxy": float(quality / len(plan["allocations"])), "abstentions": sum(c["model_id"] is None for c in plan["allocations"])}
    engine.emit("economic_summary", summary(engine, plan, realized, evaluation))
    if digest(engine.events) != digest(trace["events"]): raise Rejection("INVALID_TRANSITION")
