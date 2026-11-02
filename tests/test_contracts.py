"""Synthetic contract conformance; no real-data fitting or final evaluation."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from deviation.contracts import (ContractError, SCALE, prompt_group, validate_action,
                                validate_allocation, validate_information, validate_ledger,
                                validate_realized_report, validate_reservations, validate_run_config,
                                validate_trace)
from deviation.core import synthetic_demo
from deviation.data.pipeline import digest

FIXTURES = Path(__file__).parent / "fixtures"


def fixture():
    return json.loads((FIXTURES / "contracts_v0_2.json").read_text())


def reservations(pack):
    validate_reservations(pack["reservation_artifact"], pack["training_rows"],
                          pack["split_groups"], pack["decision_tasks"],
                          source_manifest_sha256="a" * 64, split_manifest_sha256="b" * 64)


def rehash(artifact):
    artifact["artifact_sha256"] = digest({k: v for k, v in artifact.items() if k != "artifact_sha256"})


class TestReservations(unittest.TestCase):
    def test_trusted_configuration_rejects_role_overlap_or_missing_funding(self):
        for kind in ["duplicate", "overlap", "system", "funding", "boolean_budget", "metadata"]:
            config = fixture()["run_config"]
            if kind == "duplicate": config["agent_accounts"] *= 2
            if kind == "overlap": config["exogenous_history_actors"] = ["agent-1"]
            if kind == "system": config["fee_sink_account"] = "system"
            if kind == "funding": del config["initial_balances"]["agent-1"]
            if kind == "boolean_budget": config["reservation_budget"] = True
            if kind == "metadata": config["ground_truth"] = "hidden"
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                validate_run_config(config)

    def test_train_only_fixed_mean_receipt(self):
        pack = fixture()
        reservations(pack)
        self.assertEqual(pack["reservation_artifact"]["reservations"], {"a": 200, "b": 300})

    def test_holdout_or_same_prompt_new_id_cannot_enter_training(self):
        for use_decision_prompt in [False, True]:
            pack = fixture()
            row = pack["training_rows"][0]
            if use_decision_prompt:
                row["task_id"] = "different-id-same-hidden-question"
                row["prompt"] = "  SYNTHETIC   EVALUATION PROMPT ONE "
            else:
                pack["split_groups"][prompt_group(row["prompt"])] = "test"
            with self.assertRaises(ContractError):
                reservations(pack)

    def test_training_groups_cannot_be_allocated(self):
        pack = fixture()
        pack["decision_tasks"][0]["prompt"] = pack["training_rows"][0]["prompt"]
        with self.assertRaisesRegex(ContractError, "excluded from training"):
            reservations(pack)

    def test_missing_duplicate_or_incomplete_training(self):
        for rows in [[], fixture()["training_rows"][:-1], fixture()["training_rows"] * 2]:
            pack = fixture()
            pack["training_rows"] = rows
            with self.assertRaises(ContractError):
                reservations(pack)

    def test_training_and_decision_ids_disjoint_even_for_different_prompts(self):
        pack = fixture()
        for row in pack["training_rows"]:
            if row["task_id"] == "train-1":
                row["task_id"] = pack["decision_tasks"][0]["task_id"]
        with self.assertRaisesRegex(ContractError, "task IDs overlap"):
            reservations(pack)

    def test_invalid_costs_units_hashes_and_model_coverage(self):
        for value in ["NaN", "Infinity", "-1", "0", "not-money", True, 0.1]:
            pack = fixture()
            pack["training_rows"][0]["cost_decimal"] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                reservations(pack)
        for change in [{"scale": True}, {"scale": 100}, {"method": "fit_on_all"},
                       {"cost_unit": "virtual_credit"}, {"data_kind": "OBSERVED_LLM_AGENT_INTERACTIONS"},
                       {"source_manifest_sha256": "c" * 64}, {"fit_row_count": True},
                       {"artifact_sha256": "0" * 64}, {"reservations": {"a": 200}}]:
            pack = fixture()
            pack["reservation_artifact"].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                reservations(pack)
        pack = fixture()
        pack["training_rows"][0]["cost_unit"] = "reported_usd"
        with self.assertRaises(ContractError):
            reservations(pack)

    def test_decimal_upward_rounding_and_boolean_amounts(self):
        pack = fixture()
        for row in pack["training_rows"]:
            row["cost_decimal"] = "0.0000000001" if row["task_id"] == "train-1" else "0.0000000002"
        pack["reservation_artifact"]["reservations"] = {"a": 1, "b": 1}
        rehash(pack["reservation_artifact"])
        reservations(pack)  # 0.15 nano rounded upward to one nano, not zero.
        pack["reservation_artifact"]["reservations"]["a"] = True
        rehash(pack["reservation_artifact"])
        with self.assertRaises(ContractError):
            reservations(pack)
        pack = fixture()
        for row in pack["training_rows"]:
            row["cost_decimal"] = "0.1" if row["task_id"] == "train-1" else "0.2"
        pack["reservation_artifact"]["reservations"] = {"a": 150_000_000, "b": 150_000_000}
        rehash(pack["reservation_artifact"])
        reservations(pack)  # Exact decimal arithmetic, not binary-float addition.
        self.assertEqual(pack["reservation_artifact"]["scale"], SCALE)
        for row in pack["training_rows"]:
            row["cost_decimal"] = "0.000000001000000000000000000000000000000000000000001"
        pack["reservation_artifact"]["reservations"] = {"a": 2, "b": 2}
        rehash(pack["reservation_artifact"])
        reservations(pack)  # Arbitrary decimal precision cannot round a value above one down to one.


class TestInformationBoundary(unittest.TestCase):
    def check(self, pack):
        validate_information(pack["information"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_closed_recipient_specific_information_and_action(self):
        pack = fixture()
        self.check(pack)
        validate_action(pack["action"], pack["information"])

    def test_hidden_fields_rejected_at_every_public_nesting_level(self):
        for field in ["quality", "ground_truth", "raw_output", "realized_cost", "completion_tokens", "oracle"]:
            for location in ["root", "task", "signal", "history"]:
                pack = fixture()
                info = pack["information"]
                target = {"root": info, "task": info["task"], "signal": info["private_signal"],
                          "history": info["history"][0]["payload"]}[location]
                target[field] = "SYNTHETIC hidden value"
                with self.subTest(field=field, location=location), self.assertRaises(ContractError):
                    self.check(pack)

    def test_other_agent_signal_future_or_private_history_rejected(self):
        changes = [("owner", "agent-2"), ("seq", 1), ("time_step", 2),
                   ("visibility", "PRIVATE"), ("type", "settlement")]
        for field, value in changes:
            pack = fixture()
            if field == "owner":
                pack["information"]["private_signal"]["owner_agent_id"] = value
            else:
                pack["information"]["history"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.check(pack)
        pack = fixture()
        pack["information"]["history"] *= 2
        with self.assertRaises(ContractError):
            self.check(pack)

    def test_incorrect_semantics_units_or_actions_rejected(self):
        for change in [{"agent_kind": "REAL_LLM_AGENT"}, {"cost_unit": "reported_usd"},
                       {"available_credits": True}, {"action_fee": 21}]:
            pack = fixture()
            pack["information"].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.check(pack)
        for change in [{"agent_id": "agent-2"}, {"forecast_kind": "probability_of_coding_success"},
                       {"action_fee": 0}, {"values": {"a": float("nan"), "b": 0.5}},
                       {"values": {"a": True, "b": 0.5}}]:
            pack = fixture()
            pack["action"].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_action(pack["action"], pack["information"])


    def test_registered_exogenous_history_is_not_an_economic_participant(self):
        pack = fixture()
        self.check(pack)
        self.assertEqual(pack["information"]["history"][0]["actor"], "seed-history")
        self.assertNotIn("seed-history", pack["run_config"]["initial_balances"])
        for target in ["history", "recipient"]:
            bad = deepcopy(pack)
            if target == "history":
                bad["information"]["history"][0]["actor"] = "undeclared-agent"
            else:
                bad["information"]["agent_id"] = "seed-history"
            with self.subTest(target=target), self.assertRaises(ContractError):
                self.check(bad)


class TestBudgetsAndPayoffs(unittest.TestCase):
    def test_plan_cannot_inflate_budget_to_hide_realized_violation(self):
        pack = fixture()
        pack["allocation_plan"]["reservation_budget"] = 900
        pack["realized_report"].update(realized_budget_excess=0, realized_budget_violated=False)
        for check in [
            lambda: validate_allocation(pack["allocation_plan"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"]),
            lambda: validate_realized_report(pack["realized_report"], pack["allocation_plan"], run_config=pack["run_config"]),
            lambda: validate_trace(pack["trace"], pack["reservation_artifact"], pack["allocation_plan"], pack["realized_report"], pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"]),
        ]:
            with self.assertRaisesRegex(ContractError, "trusted reservation budget"):
                check()

    def test_all_participant_utilities_and_typed_containers_required(self):
        for change in [{"agent_utilities": {}}, {"agent_utilities": {"unknown": {}}},
                       {"agent_utilities": None}, {"agent_utilities": []}, {"transfers": {}}]:
            pack = fixture()
            pack["ledger"].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_ledger(pack["ledger"], run_config=pack["run_config"])
        pack = fixture()
        pack["ledger"]["initial_balances"]["agent-1"] += 100
        pack["ledger"]["final_balances"]["agent-1"] += 100
        with self.assertRaisesRegex(ContractError, "trusted initial funding"):
            validate_ledger(pack["ledger"], run_config=pack["run_config"])

    def test_exact_reservation_boundary_and_one_unit_violation(self):
        pack = fixture()
        plan = pack["allocation_plan"]
        plan["reservation_budget"] = 500
        pack["run_config"]["reservation_budget"] = 500
        validate_allocation(plan, pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        plan["reservation_budget"] = 499
        pack["run_config"]["reservation_budget"] = 499
        with self.assertRaisesRegex(ContractError, "budget violation"):
            validate_allocation(plan, pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_abstention_zero_reserve_and_no_realized_refund_during_play(self):
        pack = fixture()
        plan = pack["allocation_plan"]
        plan["allocations"][0].update(model_id=None, reserved_cost=0)
        validate_allocation(plan, pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        plan["allocations"][1]["reserved_cost"] = 200  # Realized cost is 200, fixed reservation is 300.
        with self.assertRaisesRegex(ContractError, "incorrect reservation"):
            validate_allocation(plan, pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_report_realized_violations_without_hiding_them(self):
        pack = fixture()
        validate_allocation(pack["allocation_plan"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        validate_realized_report(pack["realized_report"], pack["allocation_plan"], run_config=pack["run_config"])
        report = pack["realized_report"]
        self.assertEqual((report["positive_task_overruns"], report["net_overrun"],
                          report["realized_budget_excess"]), (500, 400, 300))
        for change in [{"positive_task_overruns": 400}, {"realized_budget_violated": False},
                       {"phase": "DECIDING"}, {"realized_spend": True}]:
            bad = deepcopy(report)
            bad.update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_realized_report(bad, pack["allocation_plan"], run_config=pack["run_config"])

    def test_duplicate_ids_or_hidden_cost_inputs_in_plan_rejected(self):
        pack = fixture()
        pack["allocation_plan"]["allocations"].append(pack["allocation_plan"]["allocations"][0])
        with self.assertRaises(ContractError):
            validate_allocation(pack["allocation_plan"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        pack = fixture()
        pack["allocation_plan"]["realized_costs"] = [700, 200]
        with self.assertRaises(ContractError):
            validate_allocation(pack["allocation_plan"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_virtual_conservation_and_no_double_charged_action_cost(self):
        ledger = fixture()["ledger"]
        validate_ledger(ledger, run_config=fixture()["run_config"])
        self.assertEqual(sum(ledger["initial_balances"].values()), sum(ledger["final_balances"].values()))
        self.assertEqual(ledger["agent_utilities"]["agent-1"]["utility"], 6)
        ledger["agent_utilities"]["agent-1"]["utility"] -= 2
        with self.assertRaisesRegex(ContractError, "double-counted"):
            validate_ledger(ledger, run_config=fixture()["run_config"])

    def test_unfunded_transfers_duplicate_ids_and_subsidy_not_profit(self):
        for kind in ["funding", "duplicate", "subsidy", "unit", "negative"]:
            ledger = fixture()["ledger"]
            if kind == "funding": ledger["final_balances"]["agent-1"] += 1
            if kind == "duplicate": ledger["transfers"].append(deepcopy(ledger["transfers"][0]))
            if kind == "subsidy": ledger["maker_cash_pnl"] += ledger["maker_initial_subsidy"]
            if kind == "unit": ledger["unit"] = "nano_reported_usd"
            if kind == "negative": ledger["transfers"][0]["amount"] = 21
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                validate_ledger(ledger, run_config=fixture()["run_config"])


class TestReplayAndMigration(unittest.TestCase):
    def test_published_contract_index_matches_fixture_and_validator_exports(self):
        from deviation import contracts
        index = json.loads((FIXTURES.parents[1] / "schemas" / "contracts-v0.2.json").read_text())
        pack = fixture()
        self.assertEqual(index["schema_version"], contracts.SCHEMA_VERSION)
        for name, component in index["components"].items():
            self.assertEqual(component["fields"], sorted(pack[name]), name)
            self.assertTrue(callable(getattr(contracts, component["validator"])), name)

    def test_complete_replay_conforms_and_serializes_deterministically(self):
        pack = fixture()
        reservations(pack)
        validate_information(pack["information"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        validate_action(pack["action"], pack["information"])
        validate_allocation(pack["allocation_plan"], pack["reservation_artifact"], pack["decision_tasks"], run_config=pack["run_config"])
        validate_realized_report(pack["realized_report"], pack["allocation_plan"], run_config=pack["run_config"])
        validate_ledger(pack["ledger"], run_config=pack["run_config"])
        validate_trace(pack["trace"], pack["reservation_artifact"], pack["allocation_plan"],
                       pack["realized_report"], pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])
        self.assertEqual(digest(pack), digest(json.loads(json.dumps(pack, sort_keys=True))))

    def test_wrong_version_order_private_payload_or_claims_rejected(self):
        for kind in ["version", "sequence", "visibility", "payload", "quality", "missing_transfer"]:
            pack = fixture()
            trace = pack["trace"]
            if kind == "version": trace["schema_version"] = "0.1"
            if kind == "sequence": trace["events"][0]["seq"] = True
            if kind == "visibility": trace["events"][0]["visibility"] = "PRIVATE"
            if kind == "payload": trace["events"][0]["payload"]["ground_truth"] = "hidden"
            if kind == "quality": trace["quality_semantics"] = "objective_coding_correctness"
            if kind == "missing_transfer": trace["events"].pop(4)
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                validate_trace(trace, pack["reservation_artifact"], pack["allocation_plan"],
                               pack["realized_report"], pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_legacy_demo_is_unchanged_and_cannot_be_silently_relabelled(self):
        migration = json.loads((FIXTURES / "contract_migration.json").read_text())
        self.assertEqual(migration["legacy_artifact"], synthetic_demo())
        self.assertEqual(digest(synthetic_demo()), migration["legacy_artifact_sha256"])
        self.assertFalse(migration["automatic_cost_reinterpretation"])
        pack = fixture()
        with self.assertRaises(ContractError):
            validate_trace(migration["legacy_artifact"], pack["reservation_artifact"],
                           pack["allocation_plan"], pack["realized_report"], pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_forecast_model_coverage_uses_task_options_not_global_universe(self):
        pack = fixture()
        artifact = pack["reservation_artifact"]
        for row in deepcopy(pack["training_rows"]):
            if row["model_id"] == "a":
                row.update(model_id="c", cost_decimal="0.0000004")
                pack["training_rows"].append(row)
        pack["decision_tasks"][1]["model_options"].append("c")
        artifact["fit_row_count"] = 6
        artifact["reservations"]["c"] = 400
        rehash(artifact)
        for target in [pack["trace"], pack["allocation_plan"]]:
            target["reservation_artifact_sha256"] = artifact["artifact_sha256"]
        reservations(pack)
        validate_trace(pack["trace"], artifact, pack["allocation_plan"], pack["realized_report"],
                       pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])
        pack["trace"]["events"][0]["payload"]["values"]["c"] = 0.5
        with self.assertRaisesRegex(ContractError, "forecast model coverage"):
            validate_trace(pack["trace"], artifact, pack["allocation_plan"], pack["realized_report"],
                           pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])
