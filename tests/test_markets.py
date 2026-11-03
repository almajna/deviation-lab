"""Actual engine mathematics, accounting, privacy and hostile replay tests."""
from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_CEILING
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from deviation.contracts import ContractError
from deviation.data.pipeline import digest
from deviation.markets import Engine, run, replay, validate_result
from deviation.markets.contracts import Rejection, score
from deviation.markets.engine import market_id
from deviation.markets.numeric import (NumericAmbiguity, _potential, funding, prices,
    quote, project_rational, transform)
from deviation.markets.policies import SignalFollowing, base_action, candidates, candidate_value, fit_temperature
from deviation.markets.runner import MECHANISMS, _prepare, packet

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/markets/two_task.json"


def scenario(): return json.loads(FIXTURE.read_text())


def prepared(s=None):
    s = scenario() if s is None else deepcopy(s)
    return _prepare({k: v for k, v in s.items() if k != "sealed_outcomes"})


def opened(s=None):
    tasks, artifact, T, means, e = prepared(s)
    for a, mid in e.tokens: e.commit(a, mid, None)
    e.reveal()
    return e


def request(e, delta, *, ident=None, limit=10**6):
    a, mid = e.schedule[e.turn]
    return {"schema_version": "0.3", "kind": "trade_shares", "stage": "TRADE_OR_UPDATE", "actor": a,
        "order_id": ident or a + f"/test-{e.turn}", "market_id": mid,
        "expected_state_seq": e.books[mid]["seq"], "share_delta": delta, "max_net_debit": limit}


def rehash(result): result["sha256"] = digest({k: v for k, v in result.items() if k != "sha256"})


class TestCertifiedMath(unittest.TestCase):
    def test_intervals_signed_ceil_prices_and_funding_against_independent_decimal(self):
        rng = random.Random(51)
        with localcontext() as context:
            context.prec = 200
            def C(q, b):
                shift = max(q)
                return Decimal(shift) + Decimal(b) * sum((Decimal(n - shift) / b).exp() for n in q).ln()
            for _ in range(80):
                b = rng.randint(1, 40)
                before, after = [[rng.randrange(0, 400) for _ in range(3)] for _ in range(2)]
                r = quote(before, after, b)
                value = C(after, b) - C(before, b)
                self.assertLessEqual(Decimal(r["interval"][0]), value)
                self.assertGreaterEqual(Decimal(r["interval"][1]), value)
                self.assertEqual(r["charge"], int(value.to_integral_value(rounding=ROUND_CEILING)))
                self.assertEqual(funding(b), int(C([0, 0, 0], b).to_integral_value(rounding=ROUND_CEILING)))
                projected = prices(after, b)
                self.assertEqual(sum(projected), 3_000_000)
                shift = max(after)
                w = [(Decimal(n - shift) / b).exp() for n in after]
                for n, value in zip(projected, w):
                    self.assertLess(abs(Decimal(n) / 3_000_000 - value / sum(w)), Decimal(1) / 3_000_000)

    def test_analytic_integer_boundaries_translation_permutation_and_roundtrip(self):
        self.assertEqual(quote([2, 4, 7], [8, 3, 5], 10)["charge"], 1)
        self.assertEqual(quote([0, 0, 0], [1, 1, 1], 10)["interval"], ["1", "1"])
        self.assertEqual(quote([0, 0, 0], [0, 0, 10], 10)["charge"], 5)
        self.assertEqual(quote([0, 0, 10], [0, 0, 0], 10)["charge"], -4)
        self.assertEqual(quote([1, 2, 3], [3, 2, 1], 10)["charge"], 0)

    def test_fail_closed_and_invalid_numeric_domains(self):
        with self.assertRaises(NumericAmbiguity): quote([0, 0, 0], [0, 0, 1], 10, precisions=[])
        for q, b in [([True, 0, 0], 10), ([0, 0, 0], 0), ([-1, 0, 0], 1), ([0, 0, 1_000_001], 1)]:
            with self.assertRaises(ContractError): prices(q, b)

    def test_sqrt_calibration_exact_rational_and_zero_remainder_ties(self):
        for p, expected in [([1, 0, 0], [3_000_000, 0, 0]), ([0, 1, 1], [0, 1_500_000, 1_500_000]),
                            ([1, 4, 9], [500_000, 1_000_000, 1_500_000])]:
            self.assertEqual(transform(p, "1/2", 3_000_000), expected)
        self.assertEqual(transform([1, 1, 1], "1/2", 3_000_000), [1_000_000] * 3)
        self.assertEqual(transform([Fraction(1,14),Fraction(4,14),Fraction(9,14)], "1/2", 3_000_000), [500_000,1_000_000,1_500_000])
        self.assertEqual(transform([Fraction(2,10),Fraction(8,10),0], "1/2", 3_000_000), [1_000_000,2_000_000,0])

    def test_exact_proper_scores_and_off_grid_limits(self):
        self.assertEqual([score([2, 3, 5], 10, 1, y) for y in range(3)], [102, 122, 162])
        truth = sum(Fraction(n, 10) * score([2, 3, 5], 10, 1, y) for y, n in enumerate([2, 3, 5]))
        alt = sum(Fraction(n, 10) * score([3, 3, 4], 10, 1, y) for y, n in enumerate([2, 3, 5]))
        self.assertEqual((truth, alt), (138, 136))
        with self.assertRaises(ContractError): score([True, 4, 5], 10, 1, 0)


class TestAtomicEngine(unittest.TestCase):
    def test_actual_owned_roundtrip_and_fees(self):
        s=scenario();s["economics"].update(order_limit=10,fee=1)
        actor="agent-1";mid=market_id("eval-1","a")
        defs={a:{"controller":v["controller"],"wallet":v["wallet"]} for a,v in s["agents"].items()}
        e=Engine(s["decision_tasks"],s["economics"],defs,s["controllers"],[[actor,mid]]*2)
        for a,m in e.tokens:e.commit(a,m,None)
        e.reveal();start=e.balances[e.wallet(actor)]
        self.assertTrue(e.apply(request(e,[0,0,10])))
        self.assertTrue(e.apply(request(e,[0,0,-10])))
        self.assertEqual(e.balances[e.wallet(actor)],start-3)
        self.assertEqual(e.balances[e.maker(mid)],12)
        self.assertEqual(e.balances["fee_sink"],2)
        self.assertEqual(e.books[mid]["q"],[0,0,0]);e.invariants()

    def test_seeded_adversarial_orders_never_break_solvency_or_conservation(self):
        s=scenario();s["economics"].update(order_limit=12,action_limit=100)
        s["controllers"]["c1"]["action_cap"]=100
        actor="agent-1";mid=market_id("eval-1","a")
        defs={a:{"controller":v["controller"],"wallet":v["wallet"]} for a,v in s["agents"].items()}
        e=Engine(s["decision_tasks"],s["economics"],defs,s["controllers"],[[actor,mid]]*80)
        for a,m in e.tokens:e.commit(a,m,None)
        e.reveal();rng=random.Random(111)
        for _ in range(80):
            e.apply(request(e,[rng.randrange(-4,5) for _ in range(3)]));e.invariants()
        e.lock({}, {}, "a"*64);e.settle({m:2 for m in e.books});e.invariants()
        self.assertTrue(all(e.balances[e.maker(m)]>=0 for m in e.books))

    def test_owned_claims_fees_redemption_and_funded_scores(self):
        s = scenario(); s["economics"].update(order_limit=10, fee=1)
        e = opened(s)
        a, mid = e.schedule[0]
        initial = e.balances[e.wallet(a)]
        self.assertTrue(e.apply(request(e, [0, 0, 10])))
        self.assertEqual(e.balances[e.wallet(a)], initial - 6)
        self.assertEqual(e.balances[e.maker(mid)], 16)
        self.assertEqual(e.books[mid]["holdings"][a], [0, 0, 10])
        for _ in range(len(e.schedule) - 1):
            req = request(e, [0, 0, 0]); req.pop("share_delta");req.pop("max_net_debit");req["kind"]="no_op";e.apply(req)
        e.lock({}, {}, "a" * 64)
        e.settle({m: 2 for m in e.books})
        self.assertEqual(e.balances[e.wallet(a)], initial + 4)
        self.assertEqual(e.balances[e.maker(mid)], 6)
        self.assertEqual(e.balances["fee_sink"], 1)
        self.assertTrue(all(b["q"] == [0, 0, 0] for b in e.books.values()))
        e.invariants()
        with self.assertRaises(Rejection): e.settle({m: 2 for m in e.books})
        with self.assertRaises(Rejection): e.snapshot(a, mid)

    def test_all_rejections_preserve_cash_and_positions_consume_only_slot_id(self):
        variants = ["sale", "quantity", "cash", "limit", "stale", "type", "identity", "fields", "namespace"]
        for variant in variants:
            e = opened(); req = request(e, [0, 0, 1])
            if variant == "sale": req["share_delta"] = [-1, 0, 0]
            if variant == "quantity": req["share_delta"] = [10, 0, 0]
            if variant == "cash": e.balances[e.wallet(req["actor"])] = 0
            if variant == "limit": req["max_net_debit"] = -100
            if variant == "stale": req["expected_state_seq"] = 100
            if variant == "type": req["share_delta"] = [True, 0, 0]
            if variant == "identity": req["actor"] = "foreign"
            if variant == "fields": req["ground_truth"] = 1
            if variant == "namespace": req["order_id"] = "someone-else/order"
            before = deepcopy((e.balances, e.books, e.transfers))
            self.assertFalse(e.apply(req), variant)
            self.assertEqual(before, (e.balances, e.books, e.transfers), variant)
            self.assertEqual(e.turn, 1)

    def test_report_secrecy_token_reuse_and_revisions_do_not_rescore(self):
        tasks, artifact, T, means, e = prepared()
        a, mid = next(iter(e.tokens))
        e.commit(a, mid, [0, 0, 10])
        snap = e.snapshot(a, mid)
        self.assertNotIn("commits", snap)
        self.assertFalse(any(x["type"] == "report_revealed" for x in snap["history"]))
        with self.assertRaises(Rejection): e.commit(a, mid, [0, 0, 10])
        with self.assertRaises(Rejection): e.reveal()
        for actor, cell in e.tokens:
            if (actor, cell) != (a, mid): e.commit(actor, cell, None)
        e.reveal()
        self.assertEqual(len([x for x in e.events if x["type"] == "report_revealed"]), 1)
        while e.turn < len(e.schedule):
            req = request(e, [0, 0, 0]); req.pop("share_delta");req.pop("max_net_debit");req["kind"]="no_op";e.apply(req)
        e.reports[(a, mid)] = [10, 0, 0]  # Allocation-only revision cannot alter original score claim.
        e.lock({}, {}, "a" * 64); e.settle({m: 2 for m in e.books})
        rows = [x["payload"] for x in e.events if x["type"] == "score_settled"]
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]["score"], 200)

    def test_controller_sponsor_and_namespace_caps(self):
        for kind in ["cash", "tokens", "actions", "sponsor", "namespace", "preferences"]:
            s = scenario()
            if kind == "cash": s["controllers"]["c1"]["cash_cap"] = 1
            if kind == "tokens": s["controllers"]["c1"]["token_cap"] = 1
            if kind == "actions": s["controllers"]["c1"]["action_cap"] = 1
            if kind == "sponsor": s["economics"]["sponsor_cap"] = 1
            if kind == "namespace": s["agents"]["agent/alias"] = s["agents"].pop("agent-1")
            if kind == "preferences": s["controllers"]["c1"]["external_weights"]={"unknown-task":{"hidden-outcome":1}}
            with self.subTest(kind=kind), self.assertRaises(ContractError): prepared(s)

    def test_settle_and_lock_cannot_skip_turns(self):
        e = opened()
        with self.assertRaises(Rejection): e.settle({m: 2 for m in e.books})
        with self.assertRaises(Rejection): e.lock({}, {}, "a" * 64)


class TestSimulatorMarkets(unittest.TestCase):
    def test_malformed_report_consumes_own_token_without_content_leak(self):
        class Invalid(SignalFollowing):
            def act(self,p):
                if p["stage"]=="REPORT_COMMIT":
                    out=super().act(p);out["counts"]=[True,4,5];return out
                return super().act(p)
        r=run(scenario(),"pool",policies={a:Invalid() for a in scenario()["agents"]})
        validate_result(r)
        rejects=[e for e in r["trace"]["events"] if e["type"]=="action_rejected"]
        self.assertEqual(len(rejects),8)
        self.assertTrue(all(e["stage"]=="REPORT_COMMIT" and 'counts' not in e["payload"] for e in rejects))
        self.assertEqual(r["trace"]["events"][-1]["payload"]["score_paid"],0)

    def test_all_controls_replay_same_constraints_no_global_rng_mutation(self):
        state = random.getstate()
        for mechanism in MECHANISMS:
            r = run(scenario(), mechanism)
            self.assertEqual(replay(scenario(), r), r)
            validate_result(r)
            summary = r["trace"]["events"][-1]["payload"]
            self.assertLessEqual(summary["realized_report"]["reservation_spend"], 600)
            self.assertEqual(sum(summary["initial_balances"].values()), sum(summary["final_balances"].values()))
            self.assertEqual(summary["score_reserve"], 1600)
        self.assertEqual(state, random.getstate())

    def test_hidden_mutation_invariance(self):
        original = scenario(); changed = deepcopy(original)
        for row in changed["sealed_outcomes"]: row.update(quality=1-row["quality"], cost_decimal="0.0123456789")
        a, b = run(original), run(changed)
        decision = lambda r: [e for e in r["trace"]["events"] if e["stage"] != "SETTLED"]
        self.assertEqual(decision(a), decision(b))
        self.assertEqual(a["allocation_plan"], b["allocation_plan"])
        self.assertEqual(a["reservation_artifact"], b["reservation_artifact"])
        self.assertNotEqual(a["trace"]["events"][-1]["payload"]["realized_report"], b["trace"]["events"][-1]["payload"]["realized_report"])

    def test_packets_recipient_specific_deep_copies_no_commit_or_future(self):
        class Observe(SignalFollowing):
            def __init__(self): self.packets=[]
            def act(self, p):
                self.packets.append(deepcopy(p));out=super().act(p)
                p["markets"].clear();p["history"].clear();p["limits"]["b"]=999
                return out
        agents={a:Observe() for a in scenario()["agents"]}
        r=run(scenario(), policies=agents)
        for actor, policy in agents.items():
            for p in policy.packets:
                self.assertNotIn("sealed_outcomes", p)
                self.assertNotIn("signals", p)
                self.assertEqual(p["agent_id"], actor)
                self.assertEqual(p["limits"]["b"], 10)
                self.assertTrue(all(e["seq"] < p["seq"] and e["visibility"]=="PUBLIC" for e in p["history"]))
                if p["stage"]=="REPORT_COMMIT": self.assertFalse(any(e["type"]=="report_revealed" for e in p["history"]))
        self.assertTrue(r["injected_policies"])
        with self.assertRaisesRegex(Rejection,"INJECTED_POLICY"):replay(scenario(),r)

    def test_mechanism_action_capabilities_and_public_rejected_ids(self):
        class Bad(SignalFollowing):
            def act(self,p):
                if p["stage"]=="REPORT_COMMIT":return super().act(p)
                out=base_action(p,"trade_shares");out.update(share_delta=[0,0,1],max_net_debit=10);return out
        r=run(scenario(),"pool",policies={a:Bad() for a in scenario()["agents"]})
        rejects=[e for e in r["trace"]["events"] if e["type"]=="action_rejected"]
        self.assertEqual(len(rejects),8)
        self.assertTrue(all(e["payload"]["reason"]=="DISALLOWED_ACTION" for e in rejects))
        validate_result(r)

    def test_custom_noop_ids_and_rejected_reserved_ids_reconstruct(self):
        class Custom(SignalFollowing):
            def __init__(self):self.n=0
            def act(self,p):
                if p["stage"]=="REPORT_COMMIT":return super().act(p)
                self.n+=1
                out=base_action(p,"no_op");out["order_id"]=p["agent_id"]+"/custom-"+str(self.n)
                if self.n==2:
                    out.update(kind="trade_shares",share_delta=[1,1,1],max_net_debit=10)
                    out["order_id"]=p["agent_id"]+"/order-0"
                return out
        r=run(scenario(),policies={a:Custom() for a in scenario()["agents"]});validate_result(r)
        self.assertEqual(len([e for e in r["trace"]["events"] if e["type"]=="trade_accepted"]),2)
        class Stale(SignalFollowing):
            def act(self,p):
                if p["stage"]=="REPORT_COMMIT":return super().act(p)
                out=base_action(p,"no_op");out.update(order_id=p["agent_id"]+"/repeat",expected_state_seq=100);return out
        r=run(scenario(),policies={a:Stale() for a in scenario()["agents"]});validate_result(r)
        self.assertEqual(len([e for e in r["trace"]["events"] if e["type"]=="action_rejected"]),8)

    def test_nested_rehashed_receipt_mutations_fail(self):
        good=run(scenario())
        for key in ["q_after","position_after","price_counts_after","trader_cash_after","quote_interval","signed_maker_charge","transfer_ids"]:
            bad=deepcopy(good);e=next(e for e in bad["trace"]["events"] if e["type"]=="trade_accepted")
            if isinstance(e["payload"][key],list):e["payload"][key]=["hidden"]
            else:e["payload"][key]+=1
            rehash(bad)
            with self.subTest(key=key),self.assertRaises(ContractError):validate_result(bad)
        for kind in ["stage","visibility","hidden","budget","bool"]:
            bad=deepcopy(good)
            if kind=="stage":bad["trace"]["events"][0]["stage"]="SETTLED"
            if kind=="visibility":bad["trace"]["events"][0]["visibility"]="PRIVATE"
            if kind=="hidden":bad["trace"]["events"][0]["payload"]["ground_truth"]=1
            if kind=="budget":bad["allocation_plan"]["reservation_budget"]=9999
            if kind=="bool":bad["trace"]["seed"]=True
            rehash(bad)
            with self.subTest(kind=kind),self.assertRaises(ContractError):validate_result(bad)

    def test_all_arm_settlement_even_when_compute_budget_zero(self):
        s=scenario();s["reservation_budget"]=0
        r=run(s);es=r["trace"]["events"]
        self.assertTrue(all(c["model_id"] is None for c in r["allocation_plan"]["allocations"]))
        self.assertEqual(len([e for e in es if e["type"]=="market_settled"]),4)
        self.assertEqual(len([e for e in es if e["type"]=="score_settled"]),8)

    def test_training_calibration_no_decision_ids_or_duplicates(self):
        for kind in ["target","duplicate","missing"]:
            s=scenario()
            if kind=="target":s["training_calibration_rows"][0]["task_id"]="eval-1"
            if kind=="duplicate":s["training_calibration_rows"]*=2
            if kind=="missing":s["training_calibration_rows"].pop()
            with self.subTest(kind=kind),self.assertRaises(ContractError):run(s)

    def test_empty_pool_late_entry_and_update_does_not_rescore(self):
        s=scenario()
        for a in s["agents"].values():a["decline_report"]=True
        r=run(s,"pool")
        self.assertEqual(r["trace"]["events"][-1]["payload"]["score_paid"],0)
        self.assertFalse(any(e["type"]=="report_revealed" for e in r["trace"]["events"]))
        r=run(s,"interactive-pool")
        self.assertEqual(len([e for e in r["trace"]["events"] if e["type"]=="distribution_updated"]),8)
        self.assertEqual(r["trace"]["events"][-1]["payload"]["score_paid"],0)

    def test_phase4_candidate_interface_is_pure_and_expected_not_hindsight(self):
        s=scenario();tasks,artifact,T,quality,e=prepared(s)
        for a,mid in e.tokens:e.commit(a,mid,None)
        e.reveal();a,mid=e.schedule[0]
        p=packet(e,s,a,mid,"lmsr",artifact);before=deepcopy((e.books,e.balances,e.turn))
        with self.assertRaisesRegex(Rejection,"UNSUPPORTED_HORIZON"):candidate_value(p,candidates(p)[0])
        p["remaining_slots"]=1  # Explicit last-slot fixture; earlier-turn model is disabled.
        choices=candidates(p);self.assertTrue(choices)
        value=candidate_value(p,choices[0]);self.assertIn("expected_utility_gain",value)
        self.assertEqual(value["basis"],"DECLARED_BELIEF_AND_PUBLIC_STATE_ONLY")
        self.assertEqual(before,(e.books,e.balances,e.turn))
        p["limits"]["candidate_limit"]=1
        with self.assertRaisesRegex(Rejection,"CANDIDATE_LIMIT"):candidates(p)

    def test_cli_export_and_reexecution_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            one,two=Path(d)/"one",Path(d)/"two"
            cli=[sys.executable,"-m","deviation.markets",str(FIXTURE)]
            subprocess.run(cli+["--out",str(one)],check=True,capture_output=True)
            subprocess.run(cli+["--out",str(two),"--verify",str(one/"receipts.json")],check=True,capture_output=True)
            for p in one.iterdir():self.assertEqual(p.read_bytes(),(two/p.name).read_bytes())
            text=(one/"replay.json").read_text()
            self.assertNotIn('"own_signal"',text);self.assertNotIn('"sealed_outcomes"',text)
            self.assertIn('"schema_version": "0.3"',text)

