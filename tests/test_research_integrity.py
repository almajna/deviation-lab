"""Adversarial tests target independent boundaries, not just happy-path output."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from deviation_research.records import Memory, sha
from deviation_research.scout import scout, normalize, validate_sources, request
from deviation_research.orchestrator import validate_plan, cycle, execution_key
from deviation_research.review import review

ROOT = Path(__file__).resolve().parents[1]


class ResearchIntegrity(unittest.TestCase):
    def test_citations_and_three_predeclared_directions(self):
        sources = json.loads((ROOT/"research/sources.json").read_text())
        plan = json.loads((ROOT/"research/plan.json").read_text())
        self.assertEqual(len(validate_plan(plan, validate_sources(sources))), 4)
        bad = deepcopy(sources); bad["sources"][0]["title"] = "Invented paper"
        with self.assertRaises(ValueError): validate_sources(bad)
        bad = deepcopy(plan); bad["directions"][0]["sources"] += ["imaginary-source"]
        with self.assertRaises(ValueError): validate_plan(bad, validate_sources(sources))
        bad = deepcopy(plan); bad["directions"][0]["assumption_changes"] = ["use final holdout"]
        with self.assertRaises(ValueError): validate_plan(bad, validate_sources(sources))
        bad = deepcopy(plan); bad["directions"][0]["success_rule"] = "retuned_after_failure"
        with self.assertRaises(ValueError): validate_plan(bad, validate_sources(sources))
        bad = deepcopy(plan); bad["directions"][0]["runner"] = "shell"
        with self.assertRaises(ValueError): validate_plan(bad, validate_sources(sources))

    def test_memory_atomic_dedup_failure_retention_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"memory.sqlite"
            a, b = Memory(path), Memory(path)
            record = {"plan_sha256": "plan"}
            self.assertTrue(a.reserve("hypothesis", record))
            self.assertFalse(b.reserve("hypothesis", record))
            a.finish("hypothesis", "failed", {"error": "timeout"})
            self.assertFalse(b.reserve("hypothesis", record))
            a.verify(); b.verify()
            with self.assertRaises(sqlite3.IntegrityError): a.db.execute("DELETE FROM events")
            a.export(Path(temp)/"events.jsonl")
            events = [json.loads(x) for x in (Path(temp)/"events.jsonl").read_text().splitlines()]
            self.assertEqual(events[-1]["payload"]["previous_state"], "failed")
            a.close(); b.close()

    def test_scout_budget_errors_are_kept_and_content_never_executed(self):
        calls = []
        def failure(url, timeout):
            calls.append((url, timeout))
            raise OSError("offline / rate limit")
        with tempfile.TemporaryDirectory() as temp:
            value = scout(Path(temp)/"scout.json", max_requests=4, fetch=failure)
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(r["status"] == "failed" for r in value["requests"]))
            self.assertEqual({r["provider"] for r in value["requests"]}, {"arxiv", "semantic_scholar", "conference", "github"})
        for url in ("http://api.github.com/x", "https://127.0.0.1/", "https://user@api.github.com/x", "https://api.github.com:444/x"):
            with self.assertRaises(ValueError): request(url, 1)
        with self.assertRaises(ValueError): normalize("arxiv", b'<!DOCTYPE x [<!ENTITY x "boom">]><x/>')

    def test_foreign_result_and_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):
            review({"plan": {"runner": "lmsr_baseline"}, "result": {"kind": "lmsr_baseline", "data_kind": "OBSERVED_LLM_AGENT_INTERACTIONS", "rows": []}})
        with self.assertRaises(ValueError):
            review({"plan": {"runner": "lmsr_baseline"}, "result": {"kind": "lmsr_baseline", "data_kind": "SYNTHETIC", "rows": []}})

    def test_forged_repeated_baseline_and_nonregistered_profile_rejected(self):
        repeated = {"b": 1, "before": [0, 0, 0], "after": [1, 0, 0]}
        with self.assertRaisesRegex(ValueError, "exact unique grid"):
            review({"plan": {"runner": "lmsr_baseline"}, "result": {"kind": "lmsr_baseline", "data_kind": "SYNTHETIC", "rows": [repeated]*243}})
        foreign = {"profile": {"capital": 999}, "seed": 13}
        with self.assertRaisesRegex(ValueError, "nonregistered"):
            review({"plan": {"runner": "fee_sensitivity", "seeds": [13]}, "result": {"kind": "fee_sensitivity", "data_kind": "SYNTHETIC", "rows": [foreign]*6}})

    def test_rank_and_claim_rewording_do_not_retry_same_science(self):
        plan = json.loads((ROOT/"research/plan.json").read_text())["directions"][0]
        modified = deepcopy(plan)
        modified.update(title="New title", overlap="New survey", hypothesis="Unsupported grand claim")
        modified["scores"]["novelty"] = 5
        self.assertEqual(execution_key(plan), execution_key(modified))
        modified["seeds"][0] += 1
        self.assertNotEqual(execution_key(plan), execution_key(modified))

    def test_memory_index_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = Memory(Path(temp)/"m.sqlite")
            memory.reserve("key", {"plan_sha256": "plan"})
            memory.db.execute("UPDATE runs SET state='completed'")
            with self.assertRaisesRegex(ValueError, "run index"):
                memory.verify()
            memory.close()

    def test_failed_cycle_is_persisted_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/"first"
            with patch("deviation_research.orchestrator.run", side_effect=RuntimeError("sandbox unavailable")) as run:
                value = cycle(ROOT/"research/plan.json", ROOT/"research/sources.json", Path(temp)/"memory.sqlite", out)
                self.assertEqual(run.call_count, 4)
                self.assertTrue(all(r["status"] == "failed" for r in value["records"]))
            with patch("deviation_research.orchestrator.run", side_effect=AssertionError("must not execute")):
                second = cycle(ROOT/"research/plan.json", ROOT/"research/sources.json", Path(temp)/"memory.sqlite", Path(temp)/"second")
                self.assertTrue(all(r["status"] == "duplicate_skipped" for r in second["records"]))
            for row in value["records"]:
                self.assertTrue((out/row["key"]/"failure.json").exists())


if __name__ == "__main__":
    unittest.main()
