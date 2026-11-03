"""Gate B mathematical oracles only; no production market/action engine.

Decimal examples check well-separated values, not certified quote enclosures.
Fractions check exact report scoring; fixtures are hand-specified, not run logs.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction
import json
from pathlib import Path
import random
import unittest

from deviation.contracts import ContractError, validate_trace
from deviation.simulator.runner import implementation_sha256

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "tests/fixtures/gate_b_math.json").read_text())


def score(counts, denominator, scale, category):
    """Exact equation oracle on the declared grid, not a settlement handler."""
    if (type(denominator) is not int or denominator <= 0 or type(scale) is not int or scale <= 0
            or not isinstance(counts, list) or len(counts) != 3
            or any(type(n) is not int or n < 0 for n in counts) or sum(counts) != denominator
            or type(category) is not int or category not in range(3)):
        raise ValueError("invalid categorical grid")
    return scale * (2 * denominator ** 2 - sum((n - denominator * (i == category)) ** 2
                                               for i, n in enumerate(counts)))


def potential(q, b):
    """High-precision math oracle; caller owns local Decimal context."""
    q, b = [Decimal(v) for v in q], Decimal(b)
    shift = max(q)
    return shift + b * sum(((v - shift) / b).exp() for v in q).ln()


def prices(q, b):
    q, b = [Decimal(v) for v in q], Decimal(b)
    weights = [((v - max(q)) / b).exp() for v in q]
    return [w / sum(weights) for w in weights]


def ceil(value):
    return int(value.to_integral_value(rounding=ROUND_CEILING))


class TestGateBScoring(unittest.TestCase):
    def test_hand_checked_integer_scores_and_pool_conservation(self):
        ex = fixture()["score_example"]
        values = [score(ex["counts"], ex["denominator"], ex["scale_k"], y) for y in range(3)]
        self.assertEqual(values, ex["scores_by_category"])
        self.assertEqual(ex["K"], 2 * ex["denominator"] ** 2 * ex["scale_k"])
        self.assertEqual(ex["initial_pool"], ex["one_payout"] + ex["final_pool"])
        self.assertEqual(ex["one_payout"], values[2])

    def test_grid_properness_gap_and_unique_representable_optimum(self):
        ex = fixture()["score_example"]
        D, k = ex["denominator"], ex["scale_k"]
        belief = [Fraction(n, D) for n in ex["belief_counts"]]
        expected = lambda n: sum(belief[y] * score(n, D, k, y) for y in range(3))
        truth = expected(ex["belief_counts"])
        self.assertEqual(truth, Fraction(ex["expected_reward"]))
        self.assertEqual(expected(ex["alternative_counts"]), Fraction(ex["alternative_expected_reward"]))
        optimizers = []
        for a in range(D + 1):
            for b in range(D + 1 - a):
                n = [a, b, D - a - b]
                gap = Fraction(ex["K"], 2) * sum((Fraction(n[y], D) - belief[y]) ** 2 for y in range(3))
                self.assertEqual(truth - expected(n), gap)
                if expected(n) == truth: optimizers.append(n)
                for y in range(3): self.assertTrue(0 <= score(n, D, k, y) <= ex["K"])
        self.assertEqual(optimizers, [ex["belief_counts"]])

    def test_off_grid_belief_can_have_two_optima(self):
        D, belief = 10, [Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)]
        rewards = {}
        for a in range(D + 1):
            for b in range(D + 1 - a):
                counts = [a, b, D - a - b]
                rewards[tuple(counts)] = sum(belief[y] * score(counts, D, 1, y) for y in range(3))
        maximum = max(rewards.values())
        self.assertEqual({n for n, value in rewards.items() if value == maximum}, {(2, 3, 5), (3, 2, 5)})

    def test_report_units_shapes_and_boolean_counts_rejected(self):
        for counts, D, k, y in [([True, 4, 5], 10, 1, 2), ([2, 3, 4], 10, 1, 2),
                                 ([-1, 6, 5], 10, 1, 2), ([2, 3, 5], True, 1, 2),
                                 ([0.2, 0.3, 0.5], 1, 1, 2), ([2, 3, 5], 10, 0, 2),
                                 ([2, 3, 5], 10, 1, True)]:
            with self.subTest(counts=counts), self.assertRaises(ValueError): score(counts, D, k, y)

    def test_mean_only_forecast_cannot_identify_category_distribution(self):
        a, b = [Fraction(0), Fraction(1), Fraction(0)], [Fraction(1, 2), Fraction(0), Fraction(1, 2)]
        self.assertEqual(a[1] / 2 + a[2], b[1] / 2 + b[2])
        self.assertNotEqual(a, b)


class TestGateBLMSRMathematics(unittest.TestCase):
    def test_uniform_prices_translation_and_full_set(self):
        with localcontext() as context:
            context.prec = 80
            for p in prices([0, 0, 0], 10): self.assertLess(abs(p - Decimal(1) / 3), Decimal("1e-75"))
            original = [2, 4, 7]
            shifted = [v + 1 for v in original]
            self.assertLess(abs(potential(shifted, 10) - potential(original, 10) - 1), Decimal("1e-75"))
            self.assertEqual(prices(original, 10), prices(shifted, 10))
        # Runtime implementation must special-case exact translation, not ceil a
        # numerically approximate difference on an integer boundary.

    def test_example_cost_prices_and_conservative_charge(self):
        ex = fixture()["market_example"]
        p = ex["accepted_event"]["payload"]
        with localcontext() as context:
            context.prec = 80
            cost = potential(p["q_after"], ex["b"]) - potential(p["q_before"], ex["b"])
            self.assertTrue(Decimal(p["quote_interval"][0]) < cost < Decimal(p["quote_interval"][1]))
            self.assertEqual(ceil(cost), p["signed_maker_charge"])
            self.assertTrue(0 <= Decimal(p["signed_maker_charge"]) - cost < 1)
            actual = prices(p["q_after"], ex["b"])
            P = p["price_denominator"]
            floors = [int((x * P).to_integral_value(rounding=ROUND_FLOOR)) for x in actual]
            order = sorted(range(3), key=lambda i: (-(actual[i] * P - floors[i]), i))
            for i in order[:P - sum(floors)]: floors[i] += 1
            self.assertEqual(floors, p["price_counts_after"])
            self.assertEqual(sum(floors), P)
            mean = actual[1] / 2 + actual[2]
            projected = Decimal(floors[1] + 2 * floors[2]) / (2 * P)
            self.assertLessEqual(abs(projected - mean), Decimal("1.5") / P)
            self.assertGreater(actual[2], actual[0])
            self.assertGreater(mean, Decimal("0.5"))

    def test_trade_and_resolution_cash_conserve_without_subsidy_as_profit(self):
        ex = fixture()["market_example"]
        p = ex["accepted_event"]["payload"]
        self.assertEqual(p["trader_cash_after"], p["trader_cash_before"] - p["signed_maker_charge"] - p["fee"])
        self.assertEqual(p["maker_cash_after"], p["maker_cash_before"] + p["signed_maker_charge"])
        self.assertEqual(p["fee_sink_after"], p["fee_sink_before"] + p["fee"])
        initial = p["trader_cash_before"] + ex["initial_funding"]
        for category, case in [(2, ex["win_resolution"]), (0, ex["zero_resolution"])]:
            payout = p["position_after"][category]
            self.assertEqual(case["agent_final"], p["trader_cash_after"] + payout)
            self.assertEqual(case["maker_final"], p["maker_cash_after"] - payout)
            self.assertEqual(case["maker_pnl"], case["maker_final"] - ex["initial_funding"])
            self.assertEqual(case["maker_realized_loss"], max(-case["maker_pnl"], 0))
            self.assertEqual(sum(case[k] for k in ["agent_final", "maker_final", "sink_final"]), initial)

    def test_signed_ceiling_roundtrip_loses_rounding_and_two_fees(self):
        ex = fixture()["market_example"]
        p, case = ex["accepted_event"]["payload"], ex["roundtrip"]
        with localcontext() as context:
            context.prec = 80
            cost = potential(p["q_after"], ex["b"]) - potential(p["q_before"], ex["b"])
            self.assertEqual(ceil(-cost), -4)
            self.assertEqual(case["sell_signed_charge"], ceil(-cost))
            self.assertGreaterEqual(ceil(cost) + ceil(-cost), 0)
        self.assertEqual(case["agent_final"], p["trader_cash_after"] - case["sell_signed_charge"] - p["fee"])
        self.assertEqual(case["maker_final"], p["maker_cash_after"] + case["sell_signed_charge"])
        self.assertEqual(case["net_agent_profit"], case["agent_final"] - p["trader_cash_before"])
        self.assertEqual(case["agent_final"] + case["maker_final"] + case["sink_final"], 31)

    def test_all_category_solvency_and_loss_bound_over_deterministic_paths(self):
        rng = random.Random(317)
        with localcontext() as context:
            context.prec = 80
            b = Decimal(10)
            c0, q, revenue = potential([0, 0, 0], b), [0, 0, 0], 0
            funding = ceil(c0)
            self.assertEqual(funding, 11)
            for _ in range(80):
                new_q = [rng.randrange(0, 50) for _ in range(3)]
                # Algebra oracle, not an executable order book: these states
                # illustrate nonnegative outstanding liabilities/owned sales.
                delta = potential(new_q, b) - potential(q, b)
                charge = (new_q[0] - q[0]) if len({new_q[i] - q[i] for i in range(3)}) == 1 else ceil(delta)
                revenue += charge
                q = new_q
                cash = funding + revenue
                self.assertGreaterEqual(cash, max(q))
                for y in range(3):
                    self.assertGreaterEqual(cash - q[y], 0)
                    self.assertLessEqual(Decimal(q[y] - revenue), c0 + Decimal("1e-70"))

    def test_trade_admissibility_examples_do_not_allow_free_credit(self):
        p = fixture()["market_example"]["accepted_event"]["payload"]
        self.assertLessEqual(p["signed_maker_charge"] + p["fee"], p["max_net_debit"])
        self.assertGreaterEqual(p["maker_cash_after"], max(p["q_after"]))
        self.assertTrue(all(a - b == d for a, b, d in zip(p["position_after"], p["position_before"], p["share_delta"])))
        self.assertFalse(all(h + d >= 0 for h, d in zip([0, 0, 0], [0, 0, -1])))
        self.assertLess(5, p["signed_maker_charge"] + p["fee"])  # Tight order limit rejects.
        self.assertLess(5 - p["signed_maker_charge"] - p["fee"], 0)  # Insufficient cash rejects.
        self.assertLess(0, max(p["q_after"]))  # Unfunded maker cannot cover claims.


class TestGateBProposalBoundaries(unittest.TestCase):
    def test_empty_pool_uniform_and_one_current_message_per_identity(self):
        # Mathematical aggregation oracle, not a runtime message handler.
        def pool(messages):
            if not messages: return [Fraction(1, 3)] * 3
            return [sum(p[y] for p in messages.values()) / len(messages) for y in range(3)]
        messages = {}
        self.assertEqual(pool(messages), [Fraction(1, 3)] * 3)
        messages["a"] = [Fraction(2, 10), Fraction(3, 10), Fraction(5, 10)]
        before = pool(messages)
        self.assertEqual(pool(messages), before)  # No-op retains the last message.
        messages["b"] = [Fraction(4, 10), Fraction(3, 10), Fraction(3, 10)]
        self.assertEqual(pool(messages), [Fraction(3, 10), Fraction(3, 10), Fraction(4, 10)])
        messages["a"] = [Fraction(0), Fraction(0), Fraction(1)]
        self.assertEqual(len(messages), 2)  # Revision replaces rather than adds weight.
        self.assertEqual(sum(pool(messages)), 1)

    def test_last_slot_expected_cash_value_is_not_realized_lucky_profit(self):
        p = fixture()["market_example"]["accepted_event"]["payload"]
        belief_win = Fraction(1, 2)
        expected_cash_gain = belief_win * 10 - p["signed_maker_charge"] - p["fee"]
        self.assertEqual(expected_cash_gain, -1)
        self.assertEqual(10 - p["signed_maker_charge"] - p["fee"], 4)  # Lucky realization.
        self.assertEqual(expected_cash_gain + 3, 2)  # Declared allocation interest can reverse incentive.

    def test_declared_temperature_control_normalizes_without_new_information(self):
        p = [Fraction(2, 10), Fraction(3, 10), Fraction(5, 10)]
        weights = [v ** 2 for v in p]
        transformed = [v / sum(weights) for v in weights]
        self.assertEqual(transformed, [Fraction(4, 38), Fraction(9, 38), Fraction(25, 38)])
        self.assertEqual(sum(transformed), 1)
        uniform = [Fraction(1, 3)] * 3
        for T in [1, 2]:
            weights = [v ** T for v in uniform]
            self.assertEqual([v / sum(weights) for v in weights], uniform)
        # Uniform forecasts tie across temperatures; the stated selection rule
        # must prefer identity, not claim calibration from this arithmetic.

    def test_index_and_example_explicitly_inactive_closed_fields(self):
        f = fixture()
        index = json.loads((ROOT / "schemas/proposals/markets-v0.3.json").read_text())
        self.assertEqual(index["status"], "PROPOSED_NOT_ACTIVE")
        self.assertIn("NOT_EXECUTED_MARKET", f["fixture_scope"])
        event = f["market_example"]["accepted_event"]
        self.assertEqual(set(event), set(index["components"]["event"]["fields"]))
        self.assertEqual(set(event["payload"]), set(index["components"]["trade_accepted_payload"]["fields"]))
        self.assertEqual(event["visibility"], "PUBLIC")
        self.assertFalse({"ground_truth", "realized_cost", "raw_output", "private_signal"} & set(event["payload"]))

    def test_active_v0_2_rejects_proposed_market_events_and_version(self):
        pack = json.loads((ROOT / "tests/fixtures/contracts_v0_2.json").read_text())
        for kind in ["event", "version"]:
            trace = deepcopy(pack["trace"])
            if kind == "event": trace["events"][0]["type"] = "trade_accepted"
            else: trace["schema_version"] = "0.3"
            with self.assertRaises(ContractError):
                validate_trace(trace, pack["reservation_artifact"], pack["allocation_plan"],
                    pack["realized_report"], pack["ledger"], pack["decision_tasks"], run_config=pack["run_config"])

    def test_gate_b_does_not_change_simulator_source_fingerprint(self):
        receipt = json.loads((ROOT / "artifacts/simulator/two_task/receipts.json").read_text())
        self.assertEqual(implementation_sha256(), receipt["implementation_sha256"])

    def test_external_utility_is_counted_once_per_controller(self):
        ex = fixture()["external_utility_example"]
        self.assertEqual(-ex["cash_loss"] + ex["expected_external_gain"] - ex["additional_effort"], ex["expected_utility_gain"])
        controller_lambda = Fraction(5)
        identity_weights = [Fraction(2), Fraction(3)]
        self.assertEqual(sum(identity_weights), controller_lambda)
        self.assertNotEqual(len(identity_weights) * controller_lambda, controller_lambda)

    def test_score_token_cap_is_fixed_not_multiplied_by_new_alias(self):
        tokens, K = 2, 200
        funded = tokens * K
        split_tokens = {"alias-1": 1, "alias-2": 1}
        self.assertEqual(sum(split_tokens.values()) * K, funded)
        self.assertGreater(2 * tokens * K, funded)
