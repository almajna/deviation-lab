"""Agent 2 independently tests mathematical bounds, coverage and economic DP."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from itertools import product
import unittest
import tempfile
from unittest.mock import patch

from deviation.attacks.certified import solve
from deviation.data.pipeline import digest
from deviation.verification.bounds import upper
from deviation.verification.checker import check
from deviation.verification.domain import (VerificationError, actions, advance,
    encoded, exact, execute, fraction, payoff, terminal, economic_key)
from deviation.verification.fixtures import fixture

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT/"experiments/certificate_benchmark.json").read_text())["profiles"][0]


def rehash(c):
    c["sha256"] = digest({k: v for k, v in c.items() if k != "sha256"})
    return c


class IndependentCertificateTests(unittest.TestCase):
    def game(self, **changes):
        mechanism = changes.pop("mechanism", "lmsr")
        return fixture(BASE | changes, 101, mechanism)

    def test_published_agent1_proof_checks_without_migrating_source_binding(self):
        from deviation.attacks.game import prepare_game
        folder = ROOT/"artifacts/attacks/certified"
        g = prepare_game(json.loads((folder/"scenario.json").read_text()), "strategic", "lmsr")
        c = json.loads((folder/"small-lmsr.certificate.json").read_text())
        result = check(g, c, expected_source_sha="b016e0178a67cc9834c0c6f6c409568de6df31e4b95baa5e95a61655152aef75")
        self.assertEqual(result["lower"], [203, 3])

    def test_exact_bounds_match_independent_enumeration_across_mechanisms(self):
        for m in ["lmsr", "interactive-pool", "pool"]:
            with self.subTest(m=m):
                g = fixture(BASE | {"horizon": 2}, 101, m)
                c = solve(g, max_expansions=200)
                check(g, c)
                value = exact(g, max_nodes=2000)["utility"]
                self.assertEqual(value, c["lower"])
                self.assertEqual(value, c["upper"])

    def test_checker_does_not_call_solver_model_or_game_payoff(self):
        g = self.game()
        c = solve(g, max_expansions=20)
        with patch("deviation.attacks.certified.model.upper_bound", side_effect=AssertionError), \
             patch("deviation.attacks.certified.model.payoff", side_effect=AssertionError), \
             patch("deviation.attacks.certified.solver.solve", side_effect=AssertionError), \
             patch("deviation.attacks.game.Game.expected", side_effect=AssertionError), \
             patch("deviation.attacks.game.Game.allocation", side_effect=AssertionError), \
             patch("deviation.attacks.search.choices", side_effect=AssertionError):
            self.assertEqual(check(g, c)["lower"], c["lower"])

    def test_all_small_descendants_are_bounded_for_both_relaxations(self):
        for m in ["lmsr", "interactive-pool", "pool"]:
            for fee in [0, 2]:
                g = fixture(BASE | {"horizon": 2, "fee": fee}, 211, m)
                for state in [g] + [advance(g, a) for a in actions(g)]:
                    value = fraction(exact(state, max_nodes=2000)["utility"])
                    for limit in [0, 5000]:
                        self.assertLessEqual(value, upper(state, vector_limit=limit))

    def test_anytime_zero_expansion_certificate(self):
        g = self.game(horizon=4)
        c = solve(g, max_expansions=0)
        v = check(g, c)
        self.assertEqual(v["checked_nodes"], 1)
        optimum = fraction(exact(g, max_nodes=20000)["utility"])
        self.assertLessEqual(fraction(c["lower"]), optimum)
        self.assertGreaterEqual(fraction(c["upper"]), optimum)

    def test_memoized_dp_matches_full_tree_and_replays(self):
        for m in ["lmsr", "interactive-pool", "pool"]:
            g = fixture(BASE | {"horizon": 3, "quantity": 1}, 307, m)
            a = exact(g, max_nodes=20000)
            b = exact(g, max_nodes=20000, memoize=True)
            self.assertEqual(a["utility"], b["utility"])
            self.assertEqual(encoded(payoff(execute(g, b["commands"]))["utility"]), b["utility"])
            self.assertLessEqual(b["nodes"], a["nodes"])

    def test_capped_baseline_is_not_an_exact_answer(self):
        g = self.game(horizon=4)
        r = exact(g, max_nodes=1)
        self.assertEqual(r["status"], "CENSORED_STATE_LIMIT")
        self.assertIsNone(r["utility"])

    def test_independent_cash_and_allocation_match_engine_objective(self):
        for m in ["lmsr", "interactive-pool", "pool"]:
            g = fixture(BASE, 307, m)
            for req in actions(g):
                child = advance(g, req)
                actual, independent = child.expected(), payoff(child)
                for component in ["cash", "effort", "external", "utility"]:
                    self.assertEqual(actual[component], independent[component])
                self.assertEqual(actual["allocation"]["allocations"], independent["allocation"])

    def test_fixed_registry_preserves_pooled_resources_and_slots(self):
        a = self.game(horizon=4, aliases=1)
        b = self.game(horizon=4, aliases=2)
        self.assertEqual(a.engine.initial["scoring_pool"], b.engine.initial["scoring_pool"])
        self.assertEqual(sum(a.engine.initial.values()), sum(b.engine.initial.values()))
        self.assertEqual(a.engine.controllers, b.engine.controllers)
        self.assertEqual(len(a.engine.schedule), len(b.engine.schedule))
        self.assertEqual(a.beliefs, b.beliefs)

    def test_state_key_retains_economic_differences(self):
        g = self.game(horizon=2)
        for mutate in [lambda e: e.balances.__setitem__("fee_sink", 1),
                       lambda e: e.attempts.__setitem__("z0", 9),
                       lambda e: setattr(e, "turn", e.turn+1)]:
            changed = deepcopy(g)
            mutate(changed.engine)
            self.assertNotEqual(economic_key(g), economic_key(changed))

    def test_source_observation_controller_and_scope_bindings(self):
        g = self.game()
        c = solve(g, max_expansions=20)
        for key, value in [("source_sha256", "0"*64), ("observation_sha256", "0"*64),
                           ("controller", "honest"), ("scope", "reports"),
                           ("objective", "REALIZED_UTILITY"), ("action_space", "narrower"),
                           ("version", "attack-certificate-2")]:
            with self.subTest(key=key):
                changed = deepcopy(c)
                changed[key] = value
                with self.assertRaises(VerificationError):
                    check(g, rehash(changed))

    def test_rehashed_payoff_and_bound_forgery(self):
        g = self.game()
        for cap in [0, 20]:
            c = solve(g, max_expansions=cap)
            for key in ["lower", "upper", "gap"]:
                changed = deepcopy(c)
                changed[key] = encoded(fraction(c[key])+1)
                with self.assertRaises(VerificationError):
                    check(g, rehash(changed))
            changed = deepcopy(c)
            leaf = next(n for n in changed["nodes"] if n["kind"] != "split")
            leaf["upper"] = encoded(fraction(leaf["upper"])-1)
            with self.assertRaises(VerificationError):
                check(g, rehash(changed))

    def test_missing_duplicate_cycle_unreachable_branch_rejected(self):
        g = self.game()
        c = solve(g, max_expansions=20)
        self.assertEqual(c["nodes"][0]["kind"], "split")
        for mode in ["missing", "duplicate", "cycle", "shared", "unreachable"]:
            changed = deepcopy(c)
            edges = changed["nodes"][0]["children"]
            if mode == "missing": edges.pop()
            elif mode == "duplicate": edges[0] = deepcopy(edges[-1])
            elif mode == "cycle": edges[0]["node"] = 0
            elif mode == "shared": edges[0]["node"] = edges[1]["node"]
            else: changed["nodes"].append(deepcopy(changed["nodes"][-1]))
            with self.subTest(mode=mode), self.assertRaises(VerificationError):
                check(g, rehash(changed))

    def test_invalid_incomplete_or_extra_witness_rejected(self):
        g = self.game()
        c = solve(g, max_expansions=20)
        for path in [[], c["incumbent_commands"]*2, [{"kind": "fake"}]]:
            changed = deepcopy(c)
            changed["incumbent_commands"] = path
            with self.assertRaises(VerificationError):
                check(g, rehash(changed))

    def test_canonical_rational_rejection(self):
        for value in [[2, 2], [0, 2], [1, -1], [True, 1], [1.0, 1], [1], "1/2"]:
            with self.assertRaises(VerificationError):
                fraction(value)

    def test_changed_game_resources_cannot_reuse_proof(self):
        g = self.game()
        c = solve(g, max_expansions=20)
        changed = deepcopy(g)
        changed.budget += 1
        with self.assertRaises(VerificationError):
            check(changed, c)

    def test_forbidden_future_opponent_is_rejected(self):
        g = self.game()
        g.engine.schedule[-1][0] = "h0"
        with self.assertRaises(VerificationError):
            check(g, {})

    def test_exhausted_slots_and_effort_remain_in_bound(self):
        for m in ["lmsr", "interactive-pool", "pool"]:
            g = fixture(BASE | {"horizon": 2}, 101, m)
            g.engine.cfg["action_limit"] = 0
            g.engine.controllers[g.controller]["effort_per_attempt"] = 3
            c = solve(g, max_expansions=100)
            check(g, c)
            self.assertEqual(c["lower"], exact(g)["utility"])

    def test_existing_holdings_and_owned_resales_are_in_alphabet(self):
        g = self.game(horizon=2)
        actor, mid = g.engine.schedule[g.engine.turn]
        g.engine.schedule[g.engine.turn:] = [[actor, mid], [actor, mid]]
        buy = next(a for a in actions(g) if a["kind"] == "trade_shares")
        owned = advance(g, buy)
        sales = [a for a in actions(owned) if a["kind"] == "trade_shares" and min(a["share_delta"]) < 0]
        self.assertTrue(sales)
        for state in [g, owned]:
            optimum = exact(state)
            c = solve(state, max_expansions=200)
            check(state, c)
            self.assertEqual(c["lower"], optimum["utility"])

    def test_ambiguous_relaxed_endpoints_are_retained_safely(self):
        from deviation.markets.numeric import NumericAmbiguity
        from deviation.verification.bounds import endpoint_cap
        g = self.game(horizon=2)
        optimum = fraction(exact(g)["utility"])
        endpoint_cap.cache_clear()
        with patch("deviation.verification.bounds.quote", side_effect=NumericAmbiguity("probe")):
            self.assertGreaterEqual(upper(g, vector_limit=5000), optimum)
        endpoint_cap.cache_clear()

    def test_ordinary_exact_search_matches_independent_comparators(self):
        from deviation.attacks.search import search
        for mechanism in ["lmsr", "interactive-pool", "pool"]:
            g = fixture(BASE | {"horizon": 2}, 101, mechanism)
            ordinary = search(g, max_nodes=20000)
            self.assertEqual(ordinary["selected"]["utility"], exact(g)["utility"])

    def test_allocation_dp_and_external_bound_match_bruteforce_plans(self):
        from deviation.markets.numeric import prices
        from deviation.markets.engine import market_id
        from deviation.verification.bounds import external_cap
        g = self.game(horizon=1)
        for child in [advance(g, req) for req in actions(g)]:
            P = child.engine.cfg["price_denominator"]
            values = {}
            for t in child.tasks:
                for m in t["model_options"]:
                    p = prices(child.engine.books[market_id(t["task_id"], m)]["q"], child.engine.cfg["b"], P)
                    values[t["task_id"], m] = Fraction(p[1]+2*p[2], 2*P)
            candidates = []
            externals = []
            weights = child.engine.controllers[child.controller]["external_weights"]
            for plan in product(*[[None]+t["model_options"] for t in child.tasks]):
                spent = sum(child.artifact["reservations"][m] if m else 0 for m in plan)
                if spent <= child.budget:
                    value = sum(values[t["task_id"], m] if m else 0 for t, m in zip(child.tasks, plan))
                    candidates.append((value, -spent))
                    externals.append(sum(weights.get(t["task_id"], {}).get(m, 0) for t, m in zip(child.tasks, plan)))
            plan = payoff(child)["allocation"]
            selected_value = sum(values[r["task_id"], r["model_id"]] if r["model_id"] else 0 for r in plan)
            self.assertEqual((selected_value, -sum(r["reserved_cost"] for r in plan)), max(candidates))
            self.assertEqual(external_cap(child), max(externals))

    def test_noncanonical_future_order_id_is_explicitly_unsupported(self):
        g = self.game()
        a, mid = g.engine.schedule[g.engine.turn]
        g.engine.used.add(f"{a}/order-{g.engine.turn}")
        with self.assertRaisesRegex(VerificationError, "noncanonical"):
            check(g, {})

    def test_failed_case_is_preserved_before_abort(self):
        from deviation.verification.benchmark import run
        protocol = json.loads((ROOT/"experiments/certificate_benchmark.json").read_text())
        with tempfile.TemporaryDirectory() as tmp, \
             patch("deviation.attacks.certified.solve", side_effect=VerificationError("injected failure")):
            with self.assertRaisesRegex(VerificationError, "injected failure"):
                run(protocol, tmp, measure=False, progress=lambda text: None)
            failed = json.loads((Path(tmp)/"failure.json").read_text())
            self.assertEqual(failed["current_case"]["case"], "base-101-lmsr")
            self.assertEqual(failed["exception_type"], "VerificationError")
            self.assertEqual(failed["message"], "injected failure")

    def test_false_exact_claim_and_checker_node_cap_rejected(self):
        g = self.game()
        c = solve(g, max_expansions=0)
        self.assertNotEqual(c["gap"], [0, 1])
        changed = deepcopy(c)
        changed["claim"] = "EXACT_FINITE_SUBGAME"
        with self.assertRaises(VerificationError):
            check(g, rehash(changed))
        c = solve(g, max_expansions=20)
        with self.assertRaises(VerificationError):
            check(g, c, max_nodes=1)


if __name__ == "__main__":
    unittest.main()
