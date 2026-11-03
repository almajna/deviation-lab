"""Reproduce committed instrument evidence without a model or network."""
import json
from pathlib import Path
import unittest

from deviation_llm_agents.experiments import campaign
from deviation_integration.bridge import verify_source_episode
from deviation_integration.bridge import verify_source_pilot

ROOT = Path(__file__).resolve().parents[1] / "artifacts/llm_agents"


class EvidenceTests(unittest.TestCase):
    def test_all_scripted_cases_reproduce_exactly(self):
        expected = json.loads((ROOT / "controls.json").read_text())
        self.assertEqual(campaign(), expected)
        self.assertEqual(len(expected["rows"]), 324)
        self.assertEqual(expected["real_llm_decisions"], 0)

    def test_recorded_test_transport_replays_without_inference(self):
        b = json.loads((ROOT / "test_transport_episode.json").read_text())
        expected = json.loads((ROOT / "test_transport_replay.json").read_text())
        self.assertEqual(verify_source_episode(b["scenario"], b["sidecar"]), expected)
        self.assertEqual(b["sidecar"]["decision_origin"], "SCRIPTED_TRANSPORT_TEST")

    def test_actual_pilot_replays_with_zero_new_model_calls(self):
        bundle = json.loads((ROOT / "real_pilot.json").read_text())
        expected = json.loads((ROOT / "real_pilot_replay.json").read_text())
        self.assertEqual(verify_source_pilot(bundle), expected)
        self.assertEqual(bundle["calls_attempted"], 24)
        self.assertEqual(bundle["valid_model_decisions"], 2)
        rows = [r for e in bundle["episodes"] for r in e["sidecar"]["audit"]["records"]]
        self.assertEqual(sum(r["status"] == "FAILED_DECISION" for r in rows), 22)
        self.assertTrue(all(e["sidecar"]["metrics"]["accepted_trades"] == 0 for e in bundle["episodes"]))


if __name__ == "__main__": unittest.main()
