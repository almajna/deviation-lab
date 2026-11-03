"""Hand-computable examples and independent exhaustive/visibility invariants."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

from deviation.contracts import ContractError, prompt_group, validate_trace
from deviation.data.pipeline import OutcomeRecord, digest, grouped_splits
from deviation.simulator import fit_reservations, prepare_records, run, replay, write_bundle
from deviation.simulator.evaluation import offline_oracle
from deviation.simulator.policies import ReportSignal, ReferenceAllocator, optimize

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/simulator/two_task.json"


def scenario():
    return json.loads(FIXTURE.read_text())


def decision_events(result):
    return [e for e in result["trace"]["events"] if e["visibility"] == "PUBLIC"]


class TestExecution(unittest.TestCase):
    def test_hand_computable_budget_overrun_and_funded_payoff(self):
        result = run(scenario())
        self.assertEqual(result["reservation_artifact"]["reservations"], {"a": 200, "b": 300})
        self.assertEqual([(a["model_id"], a["reserved_cost"]) for a in result["allocation_plan"]["allocations"]], [("a", 200), ("b", 300)])
        report = result["realized_report"]
        self.assertEqual([report[k] for k in ["reservation_spend", "realized_spend", "positive_task_overruns", "unused_reservations", "net_overrun", "realized_budget_excess"]], [500, 900, 500, 100, 400, 300])
        self.assertTrue(report["realized_budget_violated"])
        ledger = result["ledger"]
        self.assertEqual(ledger["final_balances"], {"agent-1": 22, "maker": 44, "fee_sink": 4})
        self.assertEqual(ledger["agent_utilities"]["agent-1"], {"cash_delta": 2, "external_benefit": 3, "noncash_effort_cost": 1, "utility": 4})
        self.assertEqual((ledger["maker_initial_subsidy"], ledger["maker_cash_pnl"], ledger["maker_realized_loss"]), (50, -6, 6))
        self.assertEqual(result["evaluation"]["total_preference_proxy"], 1)
        self.assertEqual(result["evaluation"]["mean_preference_proxy"], 0.5)
        validate_trace(result["trace"], result["reservation_artifact"], result["allocation_plan"],
                       report, ledger, result["decision_tasks"], run_config=result["run_config"])

    def test_exact_replay_and_no_caller_mutation(self):
        s = scenario()
        before = deepcopy(s)
        first = run(s)
        self.assertEqual(first, run(s))
        self.assertEqual(first, replay(s, first))
        self.assertEqual(s, before)
        altered = deepcopy(first)
        altered["trace"]["events"][0]["payload"]["values"]["a"] = 0.99
        with self.assertRaisesRegex(ContractError, "replay mismatch"):
            replay(s, altered)
        s["seed"] += 1
        with self.assertRaises(ContractError):
            replay(s, first)

    def test_injected_code_is_labeled_and_not_silently_replayed_as_built_in(self):
        s = scenario()
        injected = run(s, policies={"agent-1": ReportSignal()})
        self.assertEqual(injected["trusted_test_injections"], {"policies": True, "allocator": False})
        with self.assertRaisesRegex(ContractError, "replay mismatch"):
            replay(s, injected)

    def test_zero_and_exact_budget_and_abstentions(self):
        for budget, spent in [(0, 0), (199, 0), (200, 200), (499, 400), (500, 500), (600, 500)]:
            s = scenario()
            s["run_config"]["reservation_budget"] = budget
            result = run(s)
            self.assertEqual(result["realized_report"]["reservation_spend"], spent)
            for choice, cost in zip(result["allocation_plan"]["allocations"], result["realized_report"]["selected_costs"]):
                if choice["model_id"] is None:
                    self.assertEqual((choice["reserved_cost"], cost["realized_cost"]), (0, 0))

    def test_all_reference_policies_obey_identical_budget_artifact_and_units(self):
        hashes = set()
        for policy in ["random", "cheapest", "best-fixed", "cost-aware"]:
            for budget in [0, 199, 200, 499, 500, 600]:
                s = scenario()
                s.update(policy=policy)
                s["run_config"]["reservation_budget"] = budget
                result = run(s)
                hashes.add(result["reservation_artifact"]["artifact_sha256"])
                self.assertLessEqual(result["realized_report"]["reservation_spend"], budget)
                self.assertEqual(result, run(s))
        self.assertEqual(len(hashes), 1)

    def test_seeded_random_changes_without_global_rng_side_effect(self):
        state = random.getstate()
        results = set()
        for seed in range(12):
            s = scenario()
            s.update(seed=seed, policy="random")
            results.add(digest(run(s)["allocation_plan"]))
        self.assertGreater(len(results), 1)
        self.assertEqual(state, random.getstate())

    def test_infeasible_or_forged_allocator_result_rejected(self):
        class BadAllocator:
            def allocate(self, tasks, actions, artifact, budget):
                plan = ReferenceAllocator().allocate(tasks, actions, artifact, budget)
                plan["reservation_budget"] += 100
                return plan
        with self.assertRaisesRegex(ContractError, "trusted reservation budget"):
            run(scenario(), allocator=BadAllocator())

    def test_funding_and_fee_exhaustion_fail_without_silent_agent_drop(self):
        for kind in ["fees", "maker", "utility", "duplicate"]:
            s = scenario()
            if kind == "fees": s["run_config"]["initial_balances"]["agent-1"] = 3
            if kind == "maker": s["settlement"]["transfers"][0]["amount"] = 51
            if kind == "utility": del s["settlement"]["external_benefits"]["agent-1"]
            if kind == "duplicate": s["settlement"]["transfers"] *= 2
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                run(s)

    def test_zero_fee_and_zero_payout_complete_valid_ledger(self):
        s = scenario()
        s["agent_specs"]["agent-1"]["action_fee"] = 0
        s["settlement"].update(transfers=[], external_benefits={"agent-1": 0}, noncash_effort_costs={"agent-1": 0})
        result = run(s)
        self.assertEqual(result["ledger"]["transfers"], [])
        self.assertEqual(result["ledger"]["agent_utilities"]["agent-1"]["utility"], 0)

    def test_incomplete_duplicate_or_invalid_outcomes_fail_at_settlement(self):
        for kind in ["missing", "duplicate", "quality", "cost"]:
            s = scenario()
            if kind == "missing": s["sealed_outcomes"].pop()
            if kind == "duplicate": s["sealed_outcomes"].append(deepcopy(s["sealed_outcomes"][0]))
            if kind == "quality": s["sealed_outcomes"][0]["quality"] = float("nan")
            if kind == "cost": s["sealed_outcomes"][0]["cost_decimal"] = "NaN"
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                run(s)

    def test_malformed_sealed_store_is_a_contract_error(self):
        for value in [None, {}, [None], [{}], [{"task_id": [], "model_id": "a", "quality": 0.5, "cost_decimal": "1"}]]:
            s = scenario()
            s["sealed_outcomes"] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                run(s)

    def test_final_split_unknown_fields_and_oracle_policy_not_supported(self):
        for kind in ["final", "metadata", "oracle"]:
            s = scenario()
            if kind == "final": s["split_groups"][prompt_group(s["decision_tasks"][0]["prompt"])] = "final_holdout"
            if kind == "metadata": s["raw_output"] = "not allowed"
            if kind == "oracle": s["policy"] = "oracle"
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                run(s)


class TestInformationBoundary(unittest.TestCase):
    def test_hidden_quality_and_cost_mutations_leave_all_decisions_unchanged(self):
        for kind in ["quality", "cost", "both"]:
            original = scenario()
            modified = deepcopy(original)
            for row in modified["sealed_outcomes"]:
                if kind in {"quality", "both"}: row["quality"] = 1 - row["quality"]
                if kind in {"cost", "both"}: row["cost_decimal"] = "0.123456789"
            first, second = run(original), run(modified)
            self.assertEqual(first["reservation_artifact"], second["reservation_artifact"])
            self.assertEqual(first["allocation_plan"], second["allocation_plan"])
            self.assertEqual(decision_events(first), decision_events(second))

    def test_own_signal_only_and_copied_information_history(self):
        class RecordingPolicy(ReportSignal):
            def __init__(self): self.packets = []
            def act(self, info):
                self.packets.append(deepcopy(info))
                action = super().act(info)
                info["task"]["prompt"] = "mutated by policy"
                info["model_reservations"]["a"] = 0
                info["history"].clear()
                return action
        s = scenario()
        s["run_config"]["agent_accounts"].append("agent-2")
        s["run_config"]["initial_balances"]["agent-2"] = 20
        s["agent_specs"]["agent-2"] = deepcopy(s["agent_specs"]["agent-1"])
        s["agent_specs"]["agent-2"]["signals"]["eval-1"] = {"a": 0.2, "b": 0.4}
        for field in ["external_benefits", "noncash_effort_costs"]:
            s["settlement"][field]["agent-2"] = 0
        policies = {a: RecordingPolicy() for a in s["run_config"]["agent_accounts"]}
        result = run(s, policies=policies)
        for agent, policy in policies.items():
            for info in policy.packets:
                self.assertEqual(info["private_signal"]["owner_agent_id"], agent)
                self.assertFalse({"sealed_outcomes", "quality", "realized_cost", "ground_truth"} & set(info))
                self.assertEqual(info["model_reservations"], {"a": 200, "b": 300})
                self.assertTrue(all(e["seq"] < info["action_seq"] and e["type"] == "public_forecast" for e in info["history"]))
        self.assertEqual([p["available_credits"] for p in policies["agent-1"].packets], [20, 18])
        self.assertEqual(len(policies["agent-2"].packets[0]["history"]), 1)
        self.assertEqual(result["decision_tasks"], s["decision_tasks"])

    def test_action_cannot_mutate_its_fee_or_report_as_another_agent(self):
        class BadPolicy(ReportSignal):
            def act(self, info):
                action = super().act(info)
                action["action_fee"] = 0
                return action
        with self.assertRaisesRegex(ContractError, "participant-controlled"):
            run(scenario(), policies={"agent-1": BadPolicy()})

    def test_decision_stage_finishes_before_invalid_hidden_cost_is_read(self):
        seen = []
        class WatchAllocator(ReferenceAllocator):
            def allocate(self, *args):
                seen.append("all decisions")
                self_args = json.dumps(args)
                self.assertion = "sealed_outcomes" not in self_args and "realized_cost" not in self_args
                return super().allocate(*args)
        s = scenario()
        s["sealed_outcomes"][0]["cost_decimal"] = "NaN"
        allocator = WatchAllocator()
        with self.assertRaises(ContractError): run(s, allocator=allocator)
        self.assertEqual(seen, ["all decisions"])
        self.assertTrue(allocator.assertion)


class TestOptimizationAndPreparation(unittest.TestCase):
    def test_exact_optimizer_matches_independent_exhaustive_search(self):
        rng = random.Random(91)
        for _ in range(80):
            tasks = [{"task_id": str(i), "model_options": ["a", "b", "c"]} for i in range(rng.randint(1, 4))]
            reserves = {m: rng.randint(1, 7) for m in ["a", "b", "c"]}
            budget = rng.randint(0, 20)
            values = {t["task_id"]: {m: rng.randint(0, 10) / 10 for m in reserves} for t in tasks}
            plan = optimize(tasks, reserves, budget, values)
            actual = sum(Fraction(str(values[c["task_id"]][c["model_id"]])) for c in plan if c["model_id"] is not None)
            feasible = []
            for choices in itertools.product([None, "a", "b", "c"], repeat=len(tasks)):
                if sum(reserves[m] for m in choices if m) <= budget:
                    feasible.append(sum(Fraction(str(values[str(i)][m])) for i, m in enumerate(choices) if m))
            self.assertEqual(actual, max(feasible))

    def test_optimizer_state_limit_is_explicit_failure(self):
        with self.assertRaisesRegex(ContractError, "state limit"):
            optimize([{"task_id": "t", "model_options": ["a", "b"]}], {"a": 1, "b": 2}, 3,
                     {"t": {"a": 0.5, "b": 1}}, max_states=1)

    def test_offline_oracle_has_separate_label_and_never_uses_realized_cost(self):
        s = scenario()
        result = run(s)
        oracle = offline_oracle(s["decision_tasks"], s["sealed_outcomes"], result["reservation_artifact"], s["run_config"])
        self.assertEqual(oracle["visibility"], "OFFLINE_ORACLE_ONLY")
        self.assertEqual([c["model_id"] for c in oracle["allocation_plan"]["allocations"]], ["b", "a"])
        for row in s["sealed_outcomes"]: row["cost_decimal"] = "999"
        self.assertEqual(oracle, offline_oracle(s["decision_tasks"], s["sealed_outcomes"], result["reservation_artifact"], s["run_config"]))

    def test_training_quality_identity_cannot_come_from_decision_tasks(self):
        s = scenario()
        s["training_quality_rows"][0]["task_id"] = "eval-1"
        with self.assertRaisesRegex(ContractError, "non-training"):
            run(s)

    def test_reservation_fit_exact_rounding_and_excludes_training_groups(self):
        s = scenario()
        result = run(s)
        self.assertEqual(result["reservation_artifact"]["reservations"], {"a": 200, "b": 300})
        for row in s["training_rows"]:
            row["cost_decimal"] = "0.00000000100000000000000000000000001"
        self.assertEqual(run(s)["reservation_artifact"]["reservations"], {"a": 2, "b": 2})
        s["decision_tasks"][0]["prompt"] = s["training_rows"][0]["prompt"]
        with self.assertRaises(ContractError): run(s)

    def test_phase1_record_adapter_uses_training_only_and_exploratory_registry(self):
        records = []
        for i in range(100):
            for model in ["a", "b"]:
                records.append(OutcomeRecord("synthetic", "a" * 40, "fixture", "test", str(i), model,
                    f"Synthetic independent prompt {i}", "b" * 64, None, 0.5,
                    0.0000002 if model == "a" else 0.0000003, "synthetic_units", "synthetic", "fixture", "SYNTHETIC_FIXTURE"))
        splits = grouped_splits(records)
        prepared = prepare_records(records, splits, source_manifest_sha256="c" * 64)
        self.assertEqual(prepared["reservation_artifact"]["reservations"], {"a": 200, "b": 300})
        train_ids = {r["task_id"] for r in prepared["training_rows"]}
        self.assertFalse(train_ids & {t["task_id"] for t in prepared["decision_tasks"]})
        mutated = [replace(r, cost=123.0, quality=1) if splits["tasks"][r.task_id]["split"] != "train" else r for r in records]
        again = prepare_records(mutated, splits, source_manifest_sha256="c" * 64)
        self.assertEqual(prepared["reservation_artifact"], again["reservation_artifact"])
        self.assertEqual(prepared["training_quality_rows"], again["training_quality_rows"])
        with self.assertRaises(ContractError): prepare_records(records, splits, source_manifest_sha256="c" * 64, decision_split="final")


class TestArtifactCLI(unittest.TestCase):
    def test_replay_binds_scientific_validator_and_pipeline_dependency_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for dependency in ["contracts.py", "data/pipeline.py"]:
                copy = root / dependency.replace("/", "-")
                shutil.copytree(ROOT / "src/deviation", copy / "deviation", ignore=shutil.ignore_patterns("__pycache__"))
                env = dict(os.environ, PYTHONPATH=str(copy))
                cli = [sys.executable, "-m", "deviation.simulator", str(FIXTURE)]
                subprocess.run(cli + ["--out", str(copy / "before")], env=env, check=True, capture_output=True)
                p = copy / "deviation" / dependency
                p.write_text(p.read_text() + "\n# Reviewed dependency change must invalidate replay.\n")
                attempted = subprocess.run(cli + ["--out", str(copy / "after"), "--verify", str(copy / "before/receipts.json")], env=env, capture_output=True, text=True)
                self.assertNotEqual(attempted.returncode, 0)
                self.assertIn("replay mismatch", attempted.stderr)

    def test_cli_artifacts_replay_hashes_and_public_export(self):
        with tempfile.TemporaryDirectory() as directory:
            out, other = Path(directory) / "one", Path(directory) / "two"
            cli = [sys.executable, "-m", "deviation.simulator", str(FIXTURE)]
            first = subprocess.run(cli + ["--out", str(out)], check=True, capture_output=True, text=True)
            self.assertIn("SYNTHETIC v0.2 replay", first.stdout)
            subprocess.run(cli + ["--out", str(other), "--verify", str(out / "receipts.json")], check=True, capture_output=True)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["events.jsonl", "manifest.json", "receipts.json", "replay.json"])
            for p in out.iterdir():
                self.assertEqual(p.read_bytes(), (other / p.name).read_bytes())
            public = (out / "replay.json").read_text()
            self.assertNotIn("private_signal", public)
            self.assertNotIn("sealed_outcomes", public)
            self.assertNotIn("training_quality_rows", public)
            import hashlib
            manifest = json.loads((out / "manifest.json").read_text())
            for name, sha in manifest["files"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), sha)
            result = json.loads((out / "receipts.json").read_text())
            self.assertEqual(result["sha256"], digest({k: v for k, v in result.items() if k != "sha256"}))

    def test_cli_refuses_recorded_experiment_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            s = scenario()
            s["data_kind"] = "RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS"
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(s))
            completed = subprocess.run([sys.executable, "-m", "deviation.simulator", str(path), "--out", str(Path(directory) / "out")], capture_output=True, text=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("SYNTHETIC scenarios only", completed.stderr)
