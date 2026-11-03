from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
import signal

from deviation_research.safety import run, SandboxError


class ResearchSandbox(unittest.TestCase):
    def test_interruption_kills_and_reaps_detached_worker(self):
        with patch("deviation_research.safety.backend", return_value="seatbelt"), \
             patch("deviation_research.safety.subprocess.Popen") as spawn, \
             patch("deviation_research.safety.os.killpg") as kill:
            child = spawn.return_value
            child.pid = 123456
            child.poll.return_value = None
            child.wait.side_effect = [KeyboardInterrupt, -9]
            with self.assertRaises(KeyboardInterrupt): run("isolation_probe", {})
            kill.assert_called_once_with(123456, signal.SIGKILL)
            self.assertEqual(child.wait.call_count, 2)

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
        value, resources = run("lmsr_baseline", {})
        self.assertGreater(resources["worker_cpu_seconds"], 0)
        self.assertGreater(resources["worker_peak_rss_kib"], 0)
        review, _ = run("review", {"plan": {"runner": "lmsr_baseline"}, "result": value})
        self.assertEqual(review["integrity"], "PASS")
        value["rows"][0]["engine_charge"] += 1
        with self.assertRaises(SandboxError) as caught:
            run("review", {"plan": {"runner": "lmsr_baseline"}, "result": value})
        self.assertGreater(caught.exception.receipt["worker_cpu_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
