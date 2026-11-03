"""Regression cases derived from independently reviewed, actually executed evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from deviation_research.review import review

BASE = Path(__file__).resolve().parents[1]/"artifacts/research/mvp"


@unittest.skipUnless((BASE/"summary.json").exists(), "committed CI evidence is required")
class RetainedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        summary = json.loads((BASE/"summary.json").read_text())
        cls.evidence = {}
        for row in summary["records"]:
            folder = BASE/row["key"]
            cls.evidence[row["id"]] = {"plan": json.loads((folder/"plan.json").read_text()),
                                       "result": json.loads((folder/"result.json").read_text())}

    def test_all_evidence_reviews_without_optimizer_or_game_payoff(self):
        with patch("deviation.attacks.certified.solver.solve", side_effect=AssertionError("producer optimizer forbidden")), \
             patch("deviation.attacks.game.Game.expected", side_effect=AssertionError("producer payoff forbidden")), \
             patch("deviation.attacks.game.Game.allocation", side_effect=AssertionError("producer allocation forbidden")):
            for name, evidence in self.evidence.items():
                if name != "correlation":
                    self.assertEqual(review(evidence)["integrity"], "PASS")

    def test_fee_counterexample_not_hidden_by_unsupported_cells(self):
        receipt = review(self.evidence["fees"])
        self.assertEqual(receipt["criterion_status"], "REJECTED_ON_EVALUATED_CELLS")
        self.assertEqual(receipt["coverage_status"], "PARTIAL_UNSUPPORTED_CASES")
        self.assertFalse(receipt["checks"][0]["monotonic"])

    def test_correlation_null_is_retained(self):
        receipt = review(self.evidence["correlation"])
        self.assertEqual(receipt["criterion_status"], "REJECTED_ON_REGISTERED_GRID")
        self.assertEqual(receipt["checks"][0]["mean_total_proxy_pool_minus_market"], {"False": "0", "True": "-1/6"})

    def test_comparator_payoff_and_profile_forgeries_rejected(self):
        for field in ("honest", "beam", "profile"):
            value = deepcopy(self.evidence["bounds"])
            row = value["result"]["rows"][0]
            if field == "honest": row["honest"][0] -= 1
            elif field == "beam": row["beam"]["utility"][0] -= 1
            else: row["profile"]["capital"] += 1
            with self.assertRaises(ValueError): review(value)

    def test_signed_diagnostic_and_grid_tampering_rejected(self):
        value = deepcopy(self.evidence["lmsr"])
        value["result"]["signed_rows"][0]["engine_charge"] += 1
        with self.assertRaises(ValueError): review(value)
        value = deepcopy(self.evidence["lmsr"])
        value["result"]["signed_rows"][-1] = value["result"]["signed_rows"][0]
        with self.assertRaises(ValueError): review(value)


if __name__ == "__main__":
    unittest.main()
