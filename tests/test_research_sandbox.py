from pathlib import Path
import os
import tempfile
import unittest

from deviation_research.safety import run, SandboxError


class ResearchSandbox(unittest.TestCase):
    def test_arbitrary_entry_point_refused(self):
        with self.assertRaises(SandboxError): run("sh", {})
        with self.assertRaisesRegex(SandboxError, "wall budget"):
            run("isolation_probe", {}, wall_seconds=0)

    @unittest.skipUnless(os.environ.get("DEVIATION_REQUIRE_SANDBOX") == "1", "OS isolation integration runs in required CI job")
    def test_real_os_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            secret = Path(temp)/"sealed-holdout-canary"
            secret.write_text("not a real dataset")
            outside = Path(temp)/"outside"
            value, receipt = run("isolation_probe", {"read_path": str(secret), "write_path": str(outside)})
            self.assertEqual(value, {"read": True, "write": True, "network": True})
            self.assertFalse(outside.exists())
            self.assertEqual(receipt["paid_spend_usd"], 0)

    @unittest.skipUnless(os.environ.get("DEVIATION_REQUIRE_SANDBOX") == "1", "OS isolation integration runs in required CI job")
    def test_sandboxed_baseline_and_forged_result(self):
        value, _ = run("lmsr_baseline", {})
        review, _ = run("review", {"plan": {"runner": "lmsr_baseline"}, "result": value})
        self.assertEqual(review["integrity"], "PASS")
        value["rows"][0]["engine_charge"] += 1
        with self.assertRaises(SandboxError): run("review", {"plan": {"runner": "lmsr_baseline"}, "result": value})


if __name__ == "__main__":
    unittest.main()
