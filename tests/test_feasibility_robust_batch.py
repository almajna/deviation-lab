import json
from pathlib import Path
import subprocess
import sys
import unittest


class RobustBatchReproductionTest(unittest.TestCase):
    def test_fixture_receipt(self):
        root = Path(__file__).resolve().parents[1]
        output = subprocess.check_output(
            [sys.executable, "-I", str(root / "scripts/reproduce_robust_batch.py")],
            text=True,
        )
        expected = root / "artifacts/feasibility/robust_batch_fixture.json"
        self.assertEqual(json.loads(output), json.loads(expected.read_text()))
