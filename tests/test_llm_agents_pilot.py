"""Pilot protocol/receipt checks use a labeled test transport, never fake live inference."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import unittest

from deviation.data.pipeline import digest
from deviation_llm_agents.pilot import run_pilot, validate_protocol, verify_pilot
from test_llm_agents import TestBackend

CONFIG = Path(__file__).resolve().parents[1] / "experiments/llm_real_pilot.json"


class PilotTests(unittest.TestCase):
    def test_unreviewed_protocol_is_rejected_before_model_execution(self):
        config = json.loads(CONFIG.read_text())
        validate_protocol(config)
        config["max_new_tokens"] = 128
        with self.assertRaisesRegex(ValueError, "UNREVIEWED_PILOT_PROTOCOL"): validate_protocol(config)

    def test_six_test_episodes_replay_without_becoming_live_model_evidence(self):
        with redirect_stdout(io.StringIO()):
            bundle = run_pilot(json.loads(CONFIG.read_text()), TestBackend(), execution={"host": "SCRIPTED_TEST"})
        self.assertEqual(bundle["calls_attempted"], 0)
        self.assertEqual(bundle["valid_model_decisions"], 0)
        self.assertEqual(verify_pilot(bundle)["episodes_reproduced"], 6)
        bad = deepcopy(bundle); bad["episodes"].pop()
        bad["sha256"] = digest({k: v for k,v in bad.items() if k != "sha256"})
        with self.assertRaisesRegex(ValueError, "PILOT_SETTING_COVERAGE"): verify_pilot(bad)
        bad = deepcopy(bundle); bad["episodes"][0]["scripted_controls"].pop("pool/signal")
        bad["sha256"] = digest({k: v for k,v in bad.items() if k != "sha256"})
        with self.assertRaisesRegex(ValueError, "PILOT_CONTROL_COVERAGE"): verify_pilot(bad)
