"""Adversarial source-boundary regressions, independent of migration hash labels."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from unittest.mock import patch
import os

from deviation.data.pipeline import digest
from deviation.attacks.environments import environment
from deviation.attacks.game import prepare_game
from deviation.verification.checker import check, source_sha
from deviation_research.records import sha
from deviation_research_replay.provenance import preservation, historical_review, HISTORICAL_ENGINE_SHA
from deviation_research_replay.bridge import _compare_result, _compare_events

BASE = Path(__file__).resolve().parents[1]/"artifacts/research/mvp"


class RebaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        summary = json.loads((BASE/"summary.json").read_text())
        cls.records = {r["id"]:r for r in summary["records"]}
        row = cls.records["fees"]
        cls.plan = json.loads((BASE/row["key"]/"plan.json").read_text())
        cls.old = json.loads((BASE/row["key"]/"result.json").read_text())

    def adapted(self):
        value = deepcopy(self.old)
        for row in value["rows"]:
            if "certificate" in row:
                c = row["certificate"]; c["source_sha256"] = source_sha()
                c["sha256"] = digest({k:v for k,v in c.items() if k != "sha256"})
        return value

    def test_main_and_original_harness_bytes_preserved(self):
        audit = preservation()
        self.assertEqual(set(audit),{"main","research"})
        self.assertTrue(all(v["files"] for v in audit.values()))

    def test_readme_can_evolve_but_historical_readme_tampering_fails(self):
        from deviation_integration.provenance import preservation_audit
        # Both audits use the versioned historic README, not the current introduction.
        self.assertIn("README.md", preservation()["main"]["files"])
        self.assertTrue(all("README.md" in row["files"] for row in preservation_audit().values()))
        original_read = Path.read_bytes
        def tampered(path):
            data = original_read(path)
            return data + b"tampered" if path.name == "README-8521252.md" else data
        with patch.object(Path, "read_bytes", tampered):
            with self.assertRaises(ValueError): preservation()
            with self.assertRaises(ValueError): preservation_audit()

    def test_other_historical_evidence_tampering_still_fails(self):
        original_read = Path.read_bytes
        def tampered(path):
            data = original_read(path)
            return data + b"tampered" if path.name == "data_audit.json" else data
        with patch.object(Path, "read_bytes", tampered):
            with self.assertRaises(ValueError): preservation()

    def test_changed_provenance_adapter_is_rejected(self):
        from deviation_research_replay import provenance
        original_sha = provenance.file_sha
        def forged(path):
            return "0" * 64 if path.name == "provenance.py" and path.parent.name == "deviation_integration" else original_sha(path)
        with patch.object(provenance, "file_sha", forged):
            with self.assertRaisesRegex(ValueError, "INTEGRATION_PROVENANCE_SUCCESSOR_CHANGED"):
                preservation()

    def test_contract_tampering_still_fails(self):
        from deviation_integration.provenance import preservation_audit
        original_read = Path.read_bytes
        def tampered(path):
            data = original_read(path)
            return data + b"tampered" if path.name == "CONTRACTS.md" else data
        with patch.object(Path, "read_bytes", tampered):
            with self.assertRaises(ValueError): preservation()
            with self.assertRaises(ValueError): preservation_audit()

    def test_original_reviews_reject_forgery_at_exact_original_source(self):
        self.assertEqual(historical_review({"plan":self.plan,"result":self.old})["integrity"],"PASS")
        forged = deepcopy(self.old); forged["rows"][0]["payoff"]["utility"][0] += 1
        with self.assertRaises(ValueError):
            historical_review({"plan":self.plan,"result":forged})

    def test_historical_binding_survives_optimized_environment(self):
        with patch.dict(os.environ,{"PYTHONOPTIMIZE":"2"}), \
             patch("deviation_research_replay.provenance.HISTORICAL_HARNESS_SHA","0"*64):
            with self.assertRaisesRegex(ValueError,"HISTORICAL_HARNESS_SOURCE_MISMATCH"):
                historical_review({"plan":self.plan,"result":self.old})

    def test_current_checker_still_rejects_historical_source(self):
        row = self.old["rows"][0]
        scenario,_,_ = environment(row["profile"],row["seed"],realization_seed=987654)
        game = prepare_game(scenario,"strategic","lmsr")
        with self.assertRaisesRegex(ValueError,"source binding"):
            check(game,row["certificate"])
        # This is an explicitly constructed test fixture, not a new execution receipt.
        current = self.adapted()["rows"][0]["certificate"]
        self.assertEqual(check(game,current),row["independent_check"])

    def test_only_derived_certificate_source_and_digest_can_rebind(self):
        changes = _compare_result(self.old,self.adapted(),HISTORICAL_ENGINE_SHA,source_sha())
        self.assertTrue(changes)
        self.assertTrue(all(c["path"][-1] in {"source_sha256","sha256"} for c in changes))

    def test_numeric_context_scope_and_control_changes_rejected(self):
        for field in ("payoff","observation_sha256","honest","profile"):
            current = self.adapted(); row = current["rows"][0]
            if field == "payoff": row["payoff"]["utility"][0] += 1
            elif field == "honest": row["honest"][0] += 1
            elif field == "profile": row["profile"]["fee"] += 1
            else: row[field] = "a"*64
            with self.assertRaises(ValueError):
                _compare_result(self.old,current,HISTORICAL_ENGINE_SHA,source_sha())

    def test_rehashed_changed_proof_and_wrong_source_rejected(self):
        for field in ("upper","observation_sha256","source_sha256"):
            current = self.adapted(); c = current["rows"][0]["certificate"]
            c[field] = [999,1] if field == "upper" else "a"*64
            c["sha256"] = digest({k:v for k,v in c.items() if k != "sha256"})
            with self.assertRaises(ValueError):
                _compare_result(self.old,current,HISTORICAL_ENGINE_SHA,source_sha())

    def test_event_chain_and_scientific_decision_cannot_be_rebound(self):
        old = [json.loads(x) for x in (BASE/"events.jsonl").read_text().splitlines()]
        _compare_events(old,deepcopy(old),{})
        forged = deepcopy(old)
        target = next(r for r in forged if r["kind"] == "review_recorded")
        target["payload"]["criterion_status"] = "UNSUPPORTED_SUPERIORITY_CLAIM"
        previous = None
        for event in forged:
            event["previous_sha256"] = previous
            event["sha256"] = sha({k:v for k,v in event.items() if k != "sha256"})
            previous = event["sha256"]
        with self.assertRaisesRegex(ValueError,"EVENT_SEMANTICS"):
            _compare_events(old,forged,{})

    def test_hash_format_and_int_float_are_not_scientific_compatibility(self):
        from deviation_research_replay.bridge import strict_equal
        with self.assertRaises(ValueError): strict_equal({"quality":0},{"quality":0.0},"changed")
        current = self.adapted()
        current["rows"][0]["certificate"]["sha256"] = "not-a-digest"
        with self.assertRaises(ValueError):
            _compare_result(self.old,current,HISTORICAL_ENGINE_SHA,source_sha())


if __name__ == "__main__":
    unittest.main()
