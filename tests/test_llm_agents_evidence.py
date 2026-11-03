"""Reproduce committed instrument evidence without a model or network."""
import json
from pathlib import Path
import unittest

from deviation_llm_agents.experiments import campaign
from deviation_llm_agents.harness import replay_episode

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
        self.assertEqual(replay_episode(b["scenario"], b["sidecar"]), expected)
        self.assertEqual(b["sidecar"]["decision_origin"], "SCRIPTED_TRANSPORT_TEST")


if __name__ == "__main__": unittest.main()
