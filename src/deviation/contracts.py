"""v0.2 conformance checks only: no simulator, fitting service, policy or market.

These checks validate supplied receipts/fixtures. They neither authenticate input
provenance nor isolate malicious Python code; the runner must own sealed outcomes.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math
import re
from typing import Mapping, Protocol, Sequence

from .data.pipeline import digest, normalized_prompt

SCHEMA_VERSION = "0.2"
SCALE = 1_000_000_000


class ContractError(ValueError):
    pass


def _object(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ContractError("missing or unknown fields")


def _integer(value, *, signed=False):
    if isinstance(value, bool) or not isinstance(value, int) or (not signed and value < 0):
        raise ContractError("invalid integer or unit amount")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ContractError("empty or invalid identifier")


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ContractError("invalid provenance hash")


def _version(value):
    if value != SCHEMA_VERSION:
        raise ContractError("unsupported contract version; explicit migration inputs required")


def _unit(value):
    if value not in {"nano_reported_usd", "nano_synthetic_units"}:
        raise ContractError("invalid cost unit")


def _bounded(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= 1):
        raise ContractError("invalid expected preference or quality proxy")


def validate_run_config(config):
    """Validate trusted configuration supplied by the runner, never by a policy."""
    _object(config, "schema_version reservation_budget cost_unit agent_accounts maker_account fee_sink_account initial_balances exogenous_history_actors")
    _version(config["schema_version"])
    _unit(config["cost_unit"])
    _integer(config["reservation_budget"])
    agents, exogenous = config["agent_accounts"], config["exogenous_history_actors"]
    if not isinstance(agents, list) or not agents or not isinstance(exogenous, list):
        raise ContractError("invalid trusted agent/actor registry")
    for name in agents + exogenous + [config["maker_account"], config["fee_sink_account"]]:
        _text(name)
    roles = agents + exogenous + [config["maker_account"], config["fee_sink_account"], "allocator", "system"]
    if len(set(roles)) != len(roles):
        raise ContractError("overlapping or duplicate trusted roles")
    balances = config["initial_balances"]
    if not isinstance(balances, dict) or set(balances) != set(agents + [config["maker_account"], config["fee_sink_account"]]):
        raise ContractError("trusted initial account coverage mismatch")
    for balance in balances.values():
        _integer(balance)


def prompt_group(prompt):
    _text(prompt)
    return digest(normalized_prompt(prompt))


def _tasks(tasks):
    if not isinstance(tasks, list) or not tasks:
        raise ContractError("empty task catalog")
    catalog = {}
    for task in tasks:
        _object(task, "task_id prompt model_options")
        _text(task["task_id"])
        prompt_group(task["prompt"])
        options = task["model_options"]
        if not isinstance(options, list) or len(options) < 2:
            raise ContractError("at least two model options required")
        for option in options:
            _text(option)
        if len(set(options)) != len(options) or task["task_id"] in catalog:
            raise ContractError("duplicate task or model identifier")
        catalog[task["task_id"]] = task
    return catalog


def validate_reservations(artifact, training_rows, split_groups, decision_tasks,
                          *, source_manifest_sha256, split_manifest_sha256):
    """Check an already-built train-only mean receipt; never fit on the pilot here."""
    _object(artifact, "schema_version data_kind cost_unit scale method source_manifest_sha256 split_manifest_sha256 fit_group_ids fit_row_count reservations artifact_sha256")
    _version(artifact["schema_version"])
    _unit(artifact["cost_unit"])
    expected_kind = ("SYNTHETIC" if artifact["cost_unit"] == "nano_synthetic_units"
                     else "RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS")
    if artifact["data_kind"] != expected_kind:
        raise ContractError("data kind and cost unit mismatch")
    _integer(artifact["scale"])
    if artifact["scale"] != SCALE or artifact["method"] != "mean_train_only_v1":
        raise ContractError("unknown estimator or precision")
    for name, expected in [("source_manifest_sha256", source_manifest_sha256),
                           ("split_manifest_sha256", split_manifest_sha256)]:
        _hash(expected)
        if artifact[name] != expected:
            raise ContractError("provenance mismatch")
    if not isinstance(split_groups, dict) or not split_groups:
        raise ContractError("missing trusted split registry")
    for group, split in split_groups.items():
        _hash(group)
        if split not in {"train", "validation", "test"}:
            raise ContractError("unsupported or final holdout split")
    tasks = _tasks(decision_tasks)
    decisions = {prompt_group(t["prompt"]) for t in tasks.values()}
    if any(g not in split_groups or split_groups[g] == "train" for g in decisions):
        raise ContractError("decision groups must be registered and excluded from training")
    if not isinstance(training_rows, list) or not training_rows:
        raise ContractError("empty training receipt")
    totals, counts, pairs, group_ids, identities = defaultdict(Fraction), Counter(), set(), set(), {}
    base_unit = "synthetic_units" if expected_kind == "SYNTHETIC" else "reported_usd"
    for row in training_rows:
        _object(row, "task_id prompt model_id cost_decimal cost_unit")
        _text(row["task_id"])
        _text(row["model_id"])
        group = prompt_group(row["prompt"])
        if split_groups.get(group) != "train" or group in decisions:
            raise ContractError("non-training or decision-group leakage")
        if row["task_id"] in identities and identities[row["task_id"]] != group:
            raise ContractError("mismatched training identity")
        identities[row["task_id"]] = group
        pair = (row["task_id"], row["model_id"])
        if pair in pairs:
            raise ContractError("duplicate training outcome")
        pairs.add(pair)
        group_ids.add(group)
        if row["cost_unit"] != base_unit or not isinstance(row["cost_decimal"], str):
            raise ContractError("mixed training units or non-decimal cost")
        try:
            cost = Decimal(row["cost_decimal"])
        except InvalidOperation as exc:
            raise ContractError("invalid decimal cost") from exc
        if not cost.is_finite() or cost <= 0:
            raise ContractError("invalid training cost")
        totals[row["model_id"]] += Fraction(cost)
        counts[row["model_id"]] += 1
    models = set().union(*(set(t["model_options"]) for t in tasks.values()))
    if set(identities) & set(tasks):
        raise ContractError("training and decision task IDs overlap")
    if set(totals) != models or pairs != {(t, m) for t in identities for m in models}:
        raise ContractError("missing or unexpected training model coverage")
    if group_ids != {g for g, split in split_groups.items() if split == "train"}:
        raise ContractError("training receipt does not cover approved training groups")
    if artifact["fit_group_ids"] != sorted(group_ids):
        raise ContractError("training groups mismatch")
    _integer(artifact["fit_row_count"])
    if artifact["fit_row_count"] != len(training_rows):
        raise ContractError("training row count mismatch")
    reservations = artifact["reservations"]
    if not isinstance(reservations, dict) or set(reservations) != models:
        raise ContractError("reservation model coverage mismatch")
    for model in models:
        _integer(reservations[model])
        scaled_mean = totals[model] * SCALE / counts[model]
        expected = -(-scaled_mean.numerator // scaled_mean.denominator)
        if reservations[model] != expected or expected <= 0:
            raise ContractError("reservation differs from upward-rounded training-only mean")
    _hash(artifact["artifact_sha256"])
    if artifact["artifact_sha256"] != digest({k: v for k, v in artifact.items() if k != "artifact_sha256"}):
        raise ContractError("reservation receipt checksum mismatch")


def validate_information(info, artifact, decision_tasks, *, run_config):
    validate_run_config(run_config)
    _object(info, "schema_version agent_id agent_kind task private_signal reservation_artifact_sha256 model_reservations cost_unit reservation_budget_remaining available_credits action_fee action_seq time_step history")
    _version(info["schema_version"])
    _unit(info["cost_unit"])
    _text(info["agent_id"])
    if info["agent_id"] not in run_config["agent_accounts"]:
        raise ContractError("unregistered economic agent")
    if info["agent_kind"] not in {"SYNTHETIC_FORECASTER", "SYNTHETIC_ADVERSARY"}:
        raise ContractError("unsupported agent provenance")
    _tasks([info["task"]])
    catalog = _tasks(decision_tasks)
    if info["task"] != catalog.get(info["task"]["task_id"]):
        raise ContractError("information task is not the registered public task")
    if not isinstance(info["model_reservations"], dict):
        raise ContractError("invalid public reservations")
    for value in info["model_reservations"].values():
        _integer(value)
    if (info["reservation_artifact_sha256"] != artifact["artifact_sha256"]
            or info["cost_unit"] != artifact["cost_unit"]
            or info["model_reservations"] != artifact["reservations"]):
        raise ContractError("public reservation artifact mismatch")
    for name in ["reservation_budget_remaining", "available_credits", "action_fee", "action_seq", "time_step"]:
        _integer(info[name])
    if info["action_fee"] > info["available_credits"]:
        raise ContractError("unfunded action fee")
    if info["cost_unit"] != run_config["cost_unit"] or info["reservation_budget_remaining"] > run_config["reservation_budget"]:
        raise ContractError("information budget or unit differs from trusted config")
    signal = info["private_signal"]
    _object(signal, "owner_agent_id origin forecast_kind values")
    if (signal["owner_agent_id"] != info["agent_id"] or signal["origin"] != "SYNTHETIC"
            or signal["forecast_kind"] != "expected_preference_proxy"):
        raise ContractError("cross-agent signal or unsupported forecast semantics")
    _forecasts(signal["values"], info["task"]["model_options"])
    if not isinstance(info["history"], list):
        raise ContractError("invalid history")
    previous = -1
    for event in info["history"]:
        _object(event, "seq time_step actor visibility type payload")
        for name in ["seq", "time_step"]:
            _integer(event[name])
        _text(event["actor"])
        if event["actor"] not in run_config["agent_accounts"] + run_config["exogenous_history_actors"]:
            raise ContractError("unknown public history actor")
        if (not previous < event["seq"] < info["action_seq"]
                or event["time_step"] > info["time_step"] or event["visibility"] != "PUBLIC"):
            raise ContractError("private, duplicate or future history")
        previous = event["seq"]
        if event["type"] != "public_forecast":
            raise ContractError("unsupported pre-decision history type")
        payload = event["payload"]
        _object(payload, "task_id forecast_kind values")
        if payload["task_id"] != info["task"]["task_id"] or payload["forecast_kind"] != "expected_preference_proxy":
            raise ContractError("invalid public forecast context")
        _forecasts(payload["values"], info["task"]["model_options"])


def _forecasts(values, models):
    if not isinstance(values, dict) or set(values) != set(models):
        raise ContractError("forecast model coverage mismatch")
    for value in values.values():
        _bounded(value)


def validate_action(action, information):
    _object(action, "schema_version agent_id task_id kind forecast_kind values action_fee")
    _version(action["schema_version"])
    if (action["agent_id"] != information["agent_id"]
            or action["task_id"] != information["task"]["task_id"]
            or action["kind"] != "report_preference"
            or action["forecast_kind"] != "expected_preference_proxy"):
        raise ContractError("unauthorized action or scoring semantics")
    _integer(action["action_fee"])
    if action["action_fee"] != information["action_fee"]:
        raise ContractError("action fee is not participant-controlled")
    _forecasts(action["values"], information["task"]["model_options"])


def validate_allocation(plan, artifact, decision_tasks, *, run_config):
    validate_run_config(run_config)
    _object(plan, "schema_version reservation_artifact_sha256 cost_unit reservation_budget allocations")
    _version(plan["schema_version"])
    _unit(plan["cost_unit"])
    _integer(plan["reservation_budget"])
    if plan["reservation_budget"] != run_config["reservation_budget"] or plan["cost_unit"] != run_config["cost_unit"]:
        raise ContractError("plan differs from trusted reservation budget or unit")
    if plan["cost_unit"] != artifact["cost_unit"] or plan["reservation_artifact_sha256"] != artifact["artifact_sha256"]:
        raise ContractError("allocation reservation provenance mismatch")
    catalog = _tasks(decision_tasks)
    if not isinstance(plan["allocations"], list):
        raise ContractError("invalid allocations")
    seen, reserved = set(), 0
    for choice in plan["allocations"]:
        _object(choice, "task_id model_id reserved_cost")
        task = choice["task_id"]
        _text(task)
        if task not in catalog or task in seen:
            raise ContractError("unknown or duplicate allocation")
        seen.add(task)
        _integer(choice["reserved_cost"])
        model = choice["model_id"]
        if model is None:
            expected = 0  # Explicit abstention; no hidden-cost-dependent refunds.
        elif model in catalog[task]["model_options"]:
            expected = artifact["reservations"][model]
            _integer(expected)
            if expected <= 0:
                raise ContractError("invalid fixed reservation")
        else:
            raise ContractError("unknown model choice")
        if choice["reserved_cost"] != expected:
            raise ContractError("mutable or incorrect reservation")
        reserved += expected
    if seen != set(catalog) or reserved > plan["reservation_budget"]:
        raise ContractError("incomplete plan or reservation budget violation")


def validate_realized_report(report, plan, *, run_config):
    validate_run_config(run_config)
    _object(report, "schema_version phase cost_unit selected_costs reservation_spend realized_spend positive_task_overruns unused_reservations net_overrun realized_budget_excess realized_budget_violated")
    _version(report["schema_version"])
    _unit(report["cost_unit"])
    if plan["reservation_budget"] != run_config["reservation_budget"] or plan["cost_unit"] != run_config["cost_unit"]:
        raise ContractError("plan differs from trusted reservation budget or unit")
    if report["phase"] != "SETTLED" or report["cost_unit"] != plan["cost_unit"]:
        raise ContractError("realized data exposed before settlement or mixed units")
    choices = {a["task_id"]: a for a in plan["allocations"]}
    if not isinstance(report["selected_costs"], list):
        raise ContractError("selected costs must be a list")
    seen, actual, positive, unused = set(), 0, 0, 0
    for outcome in report["selected_costs"]:
        _object(outcome, "task_id model_id realized_cost")
        _integer(outcome["realized_cost"])
        task = outcome["task_id"]
        _text(task)
        if task not in choices or task in seen or outcome["model_id"] != choices[task]["model_id"]:
            raise ContractError("unexpected or duplicate realized outcome")
        seen.add(task)
        cost, reserved = outcome["realized_cost"], choices[task]["reserved_cost"]
        if outcome["model_id"] is None and cost != 0:
            raise ContractError("abstention must have zero realized cost")
        actual += cost
        positive += max(cost - reserved, 0)
        unused += max(reserved - cost, 0)
    reserved = sum(a["reserved_cost"] for a in choices.values())
    expected = {"reservation_spend": reserved, "realized_spend": actual,
                "positive_task_overruns": positive, "unused_reservations": unused,
                "net_overrun": actual - reserved,
                "realized_budget_excess": max(actual - plan["reservation_budget"], 0)}
    if seen != set(choices):
        raise ContractError("missing selected realized costs")
    for name, value in expected.items():
        _integer(report[name], signed=name == "net_overrun")
        if report[name] != value:
            raise ContractError("realized-cost accounting mismatch")
    if type(report["realized_budget_violated"]) is not bool or report["realized_budget_violated"] != (actual > plan["reservation_budget"]):
        raise ContractError("realized budget violation flag mismatch")


def validate_ledger(ledger, *, run_config):
    validate_run_config(run_config)
    _object(ledger, "schema_version unit initial_balances final_balances transfers agent_utilities maker_account maker_initial_subsidy maker_cash_pnl maker_realized_loss")
    _version(ledger["schema_version"])
    if ledger["unit"] != "virtual_credit":
        raise ContractError("ledger may not mix historical cost and virtual utility units")
    if ledger["initial_balances"] != run_config["initial_balances"] or ledger["maker_account"] != run_config["maker_account"]:
        raise ContractError("ledger changes trusted initial funding or maker")
    if not isinstance(ledger["transfers"], list) or not isinstance(ledger["agent_utilities"], dict):
        raise ContractError("invalid ledger containers")
    if set(ledger["agent_utilities"]) != set(run_config["agent_accounts"]):
        raise ContractError("missing or unexpected participant utility")
    for name in ["initial_balances", "final_balances"]:
        if not isinstance(ledger[name], dict) or not ledger[name]:
            raise ContractError("missing accounts")
        for account, balance in ledger[name].items():
            _text(account)
            _integer(balance)
    if set(ledger["initial_balances"]) != set(ledger["final_balances"]):
        raise ContractError("account set mismatch")
    balances, ids = deepcopy(ledger["initial_balances"]), set()
    for transfer in ledger["transfers"]:
        _object(transfer, "transfer_id payer payee amount reason")
        _text(transfer["transfer_id"])
        _text(transfer["payer"])
        _text(transfer["payee"])
        if (transfer["transfer_id"] in ids or transfer["payer"] == transfer["payee"]
                or transfer["payer"] not in balances or transfer["payee"] not in balances
                or transfer["reason"] not in {"action_fee", "settlement", "refund"}):
            raise ContractError("invalid or duplicate ledger transfer")
        if transfer["reason"] == "action_fee" and (transfer["payer"] not in run_config["agent_accounts"]
                                                   or transfer["payee"] != run_config["fee_sink_account"]):
            raise ContractError("invalid action fee account roles")
        ids.add(transfer["transfer_id"])
        _integer(transfer["amount"])
        if transfer["amount"] <= 0 or balances[transfer["payer"]] < transfer["amount"]:
            raise ContractError("negative-credit or zero transfer")
        balances[transfer["payer"]] -= transfer["amount"]
        balances[transfer["payee"]] += transfer["amount"]
    if balances != ledger["final_balances"]:
        raise ContractError("unfunded or inconsistent final balances")
    for agent, payoff in ledger["agent_utilities"].items():
        _object(payoff, "cash_delta external_benefit noncash_effort_cost utility")
        if agent not in balances:
            raise ContractError("unknown utility account")
        for name, value in payoff.items():
            _integer(value, signed=name in {"cash_delta", "utility"})
        delta = balances[agent] - ledger["initial_balances"][agent]
        if payoff["cash_delta"] != delta or payoff["utility"] != delta + payoff["external_benefit"] - payoff["noncash_effort_cost"]:
            raise ContractError("utility mismatch or double-counted cash costs")
    maker = ledger["maker_account"]
    if maker not in balances:
        raise ContractError("unknown maker account")
    _integer(ledger["maker_initial_subsidy"])
    _integer(ledger["maker_cash_pnl"], signed=True)
    _integer(ledger["maker_realized_loss"])
    pnl = balances[maker] - ledger["initial_balances"][maker]
    if (ledger["maker_initial_subsidy"] > ledger["initial_balances"][maker]
            or ledger["maker_cash_pnl"] != pnl or ledger["maker_realized_loss"] != max(-pnl, 0)):
        raise ContractError("maker subsidy/profit/loss mismatch")


def validate_trace(trace, artifact, plan, report, ledger, decision_tasks, *, run_config):
    """Validate a completed audit replay, never an agent decision information set."""
    validate_allocation(plan, artifact, decision_tasks, run_config=run_config)
    validate_realized_report(report, plan, run_config=run_config)
    validate_ledger(ledger, run_config=run_config)
    _object(trace, "schema_version experiment_id seed data_kind agent_origin quality_semantics phase cost_unit reservation_artifact_sha256 provenance events")
    _version(trace["schema_version"])
    _unit(trace["cost_unit"])
    _text(trace["experiment_id"])
    _integer(trace["seed"])
    if (trace["phase"] != "SETTLED" or trace["agent_origin"] != "SYNTHETIC"
            or trace["data_kind"] != artifact["data_kind"]
            or trace["cost_unit"] != artifact["cost_unit"]
            or trace["reservation_artifact_sha256"] != artifact["artifact_sha256"]):
        raise ContractError("invalid replay phase, origin, unit or reservation provenance")
    expected_quality = "synthetic_fixture" if trace["data_kind"] == "SYNTHETIC" else "noisy_preference_proxy"
    if trace["quality_semantics"] != expected_quality:
        raise ContractError("unsupported quality claim")
    provenance = trace["provenance"]
    _object(provenance, "source_manifest_sha256 split_manifest_sha256 code_revision")
    if (provenance["source_manifest_sha256"] != artifact["source_manifest_sha256"]
            or provenance["split_manifest_sha256"] != artifact["split_manifest_sha256"]):
        raise ContractError("replay provenance mismatch")
    revision = provenance["code_revision"]
    if not (trace["data_kind"] == "SYNTHETIC" and revision == "SYNTHETIC_FIXTURE"):
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ContractError("replay requires pinned code revision")
    if not isinstance(trace["events"], list) or not trace["events"]:
        raise ContractError("missing replay events")
    last_time, settled, reserved_tasks, transfer_ids, utilities_seen = -1, False, set(), set(), False
    choices = {c["task_id"]: c for c in plan["allocations"]}
    catalog = _tasks(decision_tasks)
    if set(choices) != set(catalog):
        raise ContractError("replay task catalog mismatch")
    transfers = {t["transfer_id"]: t for t in ledger["transfers"]}
    for seq, event in enumerate(trace["events"]):
        _object(event, "seq time_step actor visibility type payload")
        _integer(event["seq"])
        _integer(event["time_step"])
        _text(event["actor"])
        if event["seq"] != seq or event["time_step"] < last_time:
            raise ContractError("non-monotone replay")
        last_time = event["time_step"]
        kind, payload = event["type"], event["payload"]
        visibility = "POST_SETTLEMENT" if kind in {"realized_cost_report", "ledger_transfer", "utility_summary"} else "PUBLIC"
        if event["visibility"] != visibility:
            raise ContractError("incorrect replay visibility")
        if kind == "public_forecast":
            _object(payload, "task_id forecast_kind values")
            if settled or payload["task_id"] not in choices or payload["forecast_kind"] != "expected_preference_proxy":
                raise ContractError("invalid replay forecast")
            _forecasts(payload["values"], catalog[payload["task_id"]]["model_options"])
            if event["actor"] not in run_config["agent_accounts"] + run_config["exogenous_history_actors"]:
                raise ContractError("unknown public replay actor")
        elif kind == "reservation":
            _object(payload, "task_id model_id reserved_cost")
            _integer(payload["reserved_cost"])
            task = payload["task_id"]
            if settled or task in reserved_tasks or payload != choices.get(task) or event["actor"] != "allocator":
                raise ContractError("invalid replay reservation")
            reserved_tasks.add(task)
        elif kind == "realized_cost_report":
            validate_realized_report(payload, plan, run_config=run_config)
            if settled or payload != report or reserved_tasks != set(choices):
                raise ContractError("invalid or early settlement report")
            settled = True
        elif kind == "ledger_transfer":
            _object(payload, "transfer_id payer payee amount reason")
            _integer(payload["amount"])
            transfer = payload["transfer_id"]
            if not settled or transfer in transfer_ids or payload != transfers.get(transfer):
                raise ContractError("invalid replay ledger transfer")
            transfer_ids.add(transfer)
        elif kind == "utility_summary":
            if not settled or utilities_seen or payload != ledger["agent_utilities"]:
                raise ContractError("invalid replay utility summary")
            utilities_seen = True
            for payoff in payload.values():
                _object(payoff, "cash_delta external_benefit noncash_effort_cost utility")
                for name, value in payoff.items():
                    _integer(value, signed=name in {"cash_delta", "utility"})
        else:
            raise ContractError("unsupported replay event type")
        if visibility == "POST_SETTLEMENT" and event["actor"] != "system":
            raise ContractError("invalid settlement replay actor")
    if not settled or not utilities_seen or transfer_ids != set(transfers):
        raise ContractError("incomplete completed replay")


class DecisionPolicy(Protocol):
    def act(self, information: Mapping[str, object]) -> Mapping[str, object]: ...


class AllocationMechanism(Protocol):
    def allocate(self, public_tasks: Sequence[Mapping[str, object]],
                 validated_actions: Sequence[Mapping[str, object]],
                 reservation_artifact: Mapping[str, object], budget: int) -> Mapping[str, object]: ...


class Settlement(Protocol):
    def settle(self, sealed_outcomes: Mapping[str, object], plan: Mapping[str, object],
               ledger_config: Mapping[str, object]) -> Mapping[str, object]: ...
