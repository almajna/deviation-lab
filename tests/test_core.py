"""Stdlib smoke tests for synthetic reference, run without network or APIs."""
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from deviation.core import Arm, Task, ObservedOutcome, choose_routes, evaluate_selected, synthetic_demo


class TestToyCore(unittest.TestCase):
    def test_demo_is_deterministic_and_labeled(self):
        a, b = synthetic_demo(7), synthetic_demo(7)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a["data_kind"], "SYNTHETIC")
        self.assertIn("NO prediction market", a["warning"])
        self.assertEqual(a["metrics"], {"quality": 2.0, "cost": 4.0, "cheapest_quality": 1.0, "cheapest_cost": 3.0})

    def test_no_outcome_input_to_allocator(self):
        t = [Task("t", Arm("a", 1), Arm("b", 2), 0.1, 0.8)]
        # Algorithm has no outcomes argument; evaluation is a separate post-decision step.
        choice = choose_routes(t, 2)
        self.assertEqual(choice, {"t": "b"})
        first = evaluate_selected(t, choice, [ObservedOutcome("t", "b", 1)])
        second = evaluate_selected(t, choice, [ObservedOutcome("t", "b", 0)])
        self.assertEqual(first[1], second[1])
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(choose_routes(t, 2), choice)

    def test_budget_and_invalid_input(self):
        t = [Task("t", Arm("a", 1), Arm("b", 2), 0.1, 0.8)]
        with self.assertRaises(ValueError):
            choose_routes(t, 0.9)
        with self.assertRaises(ValueError):
            choose_routes(t + t, 4)
        with self.assertRaises(ValueError):
            choose_routes([Task("x", Arm("a", 1), Arm("b", 2), 1.1, 0.4)], 3)

    def test_event_order_and_cost(self):
        x = synthetic_demo(9)
        self.assertEqual([e["seq"] for e in x["events"]], list(range(len(x["events"]))))
        self.assertLessEqual(x["metrics"]["cost"], x["config"]["budget"])


if __name__ == "__main__":
    unittest.main()
