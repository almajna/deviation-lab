"""Offline checks. A fabricated transport envelope is strictly a test input."""
from copy import deepcopy
from fractions import Fraction
import json
import unittest

from scripts.check_autonomous_economy import check

from scripts.run_autonomous_economy import (
    MODEL, REPORTS, RIVAL_B, SIGNALS, decode_call, evaluate, fixture, request_for, settle,
)


class AutonomousEconomyTests(unittest.TestCase):
    def setUp(self):
        self.request = request_for(SIGNALS[0], "utility_bonus", 7)

    def envelope(self, content):
        body = {"model": MODEL, "done": True, "done_reason": "stop", "eval_count": 12,
                "prompt_eval_count": 250, "message": {"role": "assistant", "content": content}}
        return {"request": self.request, "response": {"http_body": json.dumps(body),
                "read_limit_exceeded": False}, "error": None}

    def test_independent_checker_rejects_incomplete_or_duplicate_coverage(self):
        row = {"case": 0, "condition": "truthful", "belief": [6, 3, 1]}
        for rows in ([], [row], [row] * 18):
            with self.subTest(rows=len(rows)):
                with self.assertRaisesRegex(ValueError, "frozen episode coverage"):
                    check({"summary": {"episodes": rows}})

    def test_grammar_covers_full_action_space(self):
        self.assertEqual(len(REPORTS), 67)
        self.assertEqual(set(self.request["format"]["properties"]["choice"]["enum"]), REPORTS.keys())
        for key, counts in REPORTS.items():
            call = self.envelope(json.dumps({"choice": key}))
            self.assertEqual(decode_call(call, self.request), (True, counts))

    def test_invalid_action_does_not_become_valid_decline(self):
        for raw in ('{"choice":"2,2,2"}', '{"choice":1}', '{"choice":" 0,0,10"}',
                    '{"choice":"decline","choice":"decline"}', '{"choice":"decline","extra":0}'):
            self.assertEqual(decode_call(self.envelope(raw), self.request), (False, None))
        self.assertEqual(decode_call(self.envelope('{"choice":"decline"}'), self.request), (True, None))
        failure = self.envelope('{"choice":"decline"}')
        failure["error"] = "TimeoutError"
        self.assertEqual(decode_call(failure, self.request), (False, None))
        with self.assertRaisesRegex(ValueError, "REQUEST_MISMATCH"):
            decode_call(failure, request_for(SIGNALS[0], "utility_zero", 7))

    def test_exact_optimum_matches_all_engine_replays(self):
        s = fixture(SIGNALS[0], 200, 7)
        analysis = evaluate(s, [0, 0, 10], RIVAL_B)
        optimum = max(Fraction(*settle(s, r, RIVAL_B)["metrics"]["expected_utility"])
                      for r in REPORTS.values())
        self.assertEqual(optimum, Fraction(*analysis["certificate"]["lower"]))
        self.assertEqual(analysis["expected_gain_vs_signal"], "74")
        self.assertEqual(analysis["regret"], "84")
        self.assertTrue(analysis["allocation_changed_vs_signal"])
        altered_outcomes = deepcopy(s)
        for outcome in altered_outcomes["sealed_outcomes"]:
            outcome["quality"] = 1 - outcome["quality"]
        replay = evaluate(altered_outcomes, [0, 0, 10], RIVAL_B, analysis["certificate"])
        self.assertEqual(replay["expected_gain_vs_signal"], analysis["expected_gain_vs_signal"])
        self.assertNotEqual(replay["realized_gain_vs_signal"], analysis["realized_gain_vs_signal"])


if __name__ == "__main__":
    unittest.main()
