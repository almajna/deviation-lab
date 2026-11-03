"""Actual search, independent small-game enumeration and research validity."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from deviation.markets.policies import base_action
from deviation.markets.runner import allowed_actions
from deviation.attacks.game import prepare_game
from deviation.attacks.search import search
from deviation.attacks.environments import environment
from deviation.attacks.evidence import discover,execute,write_bundle,load_bundle,replay
from deviation.attacks.verify import recompute
from deviation.attacks.campaign import run_campaign


def data(profile=None,seed=17):return environment(profile or {},seed,realization_seed=12345+seed)


def independent_value(g,engine):
    """Different payoff implementation, sharing only actual allocation routine."""
    from deviation.markets.runner import _allocation
    members=g.members;D=engine.cfg["report_denominator"]
    result=sum(Fraction(engine.balances[engine.wallet(a)]-engine.initial[engine.wallet(a)]) for a in members)
    for mid,book in engine.books.items():
        result+=sum(Fraction(g.beliefs[mid][k],D)*sum(book["holdings"][a][k] for a in members) for k in range(3))
    for (a,mid),p in engine.commits.items():
        if a in members and p is not None:
            for y in range(3):result+=Fraction(g.beliefs[mid][y],D)*engine.cfg["score_scale"]*(2*D*D-sum((v-D*int(k==y))**2 for k,v in enumerate(p)))
    plan=_allocation(engine,g.tasks,g.artifact,g.mechanism,g.temperature,g.training_means,g.budget,g.seed)[0]
    c=engine.controllers[g.controller]
    result+=sum(c["external_weights"].get(r["task_id"],{}).get(r["model_id"],0) for r in plan["allocations"])
    return result-c["effort_per_attempt"]*sum(engine.attempts[a] for a in members)


class TestActualSearch(unittest.TestCase):
    def test_exact_matches_separate_cartesian_order_enumeration(self):
        s,world,m=data();g=prepare_game(s,"strategic","lmsr")
        results=[]
        def enumerate_engine(e):
            if e.turn==len(e.schedule):results.append(independent_value(g,e));return
            a,mid=e.schedule[e.turn];Q=e.cfg["order_limit"]
            p={"agent_id":a,"stage":e.stage,"turn":e.turn,"market_id":mid,"state_seq":e.books[mid]["seq"]}
            actions=[base_action(p,"no_op")]
            for d in product(range(-Q,Q+1),repeat=3):
                if not any(d) or sum(abs(v) for v in d)>Q:continue
                try:r=e.inspect_order(a,mid,list(d))
                except Rejection:continue
                command=base_action(p,"trade_shares")
                command.update(share_delta=list(d),max_net_debit=r["receipt"]["charge"]+e.cfg["fee"])
                actions.append(command)
            for command in actions:
                child=deepcopy(e)
                if child.apply(command,allowed_kinds=allowed_actions("lmsr")):enumerate_engine(child)
        enumerate_engine(deepcopy(g.engine))
        certificate=search(g,max_nodes=500)
        self.assertEqual(Fraction(*certificate["selected"]["utility"]),max(results))
        self.assertEqual(certificate["terminal_evaluations"],len(results))
        self.assertEqual(certificate["claim"],"EXACT_DECLARED_FINITE_SUBGAME")

    def test_exact_limit_never_returns_partial_optimality(self):
        s,w,m=data();g=prepare_game(s,"strategic","lmsr")
        with self.assertRaisesRegex(Rejection,"EXACT_SEARCH_LIMIT"):search(g,max_nodes=1)

    def test_beam_is_bounded_deterministic_and_includes_reference_incumbents(self):
        s,w,m=data();g=prepare_game(s,"strategic","lmsr")
        a=search(g,method="beam",max_nodes=3,beam_width=1,seed=8)
        self.assertEqual(a,search(g,method="beam",max_nodes=3,beam_width=1,seed=8))
        self.assertLessEqual(a["visited_nodes"],3)
        self.assertEqual(a["claim"],"BEST_FOUND_BOUNDED_HEURISTIC")
        self.assertGreaterEqual(Fraction(*a["gain_vs_signal_following"]),0)
        self.assertGreaterEqual(Fraction(*a["gain_vs_no_action"]),0)

    def test_multiple_controller_aliases_and_true_multiple_actions(self):
        found=False
        for seed in range(1,12):
            s,w,m=data({"aliases":2},seed)
            try:g=prepare_game(s,"strategic","lmsr")
            except Rejection:continue
            actors={a for a,mid in g.engine.schedule[g.engine.turn:]}
            if len(actors)<2:continue
            c=search(g,method="beam",max_nodes=30,beam_width=2)
            actual=execute(s,"lmsr",c["commands"])
            self.assertTrue(actual["injected_policies"])
            self.assertTrue(all(a in g.members for a in actors));found=True;break
        self.assertTrue(found)

    def test_no_future_honest_action_model_is_silently_used(self):
        s,w,m=data(seed=31)
        with self.assertRaisesRegex(Rejection,"NO_CONTROLLED_TERMINAL_SUFFIX"):
            prepare_game(s,"strategic","lmsr")


class TestInformationAndEconomics(unittest.TestCase):
    def test_sealed_quality_cost_mutation_cannot_change_search(self):
        s,w,m=data();changed=deepcopy(s)
        for row in changed["sealed_outcomes"]:row.update(quality=1-row["quality"],cost_decimal="999")
        first=prepare_game(s,"strategic","lmsr");second=prepare_game(changed,"strategic","lmsr")
        self.assertEqual(first.observation(),second.observation())
        self.assertEqual(search(first,max_nodes=500),search(second,max_nodes=500))
        self.assertNotIn("sealed_outcomes",str(first.observation()))

    def test_report_search_uses_public_model_not_actual_hidden_commitments(self):
        s,w,m=data();changed=deepcopy(s)
        for mid in changed["agents"]["h0"]["signals"]:changed["agents"]["h0"]["signals"][mid]=[3,0,0]
        g1=prepare_game(s,"strategic","pool",scope="reports",public_report_model=m)
        g2=prepare_game(changed,"strategic","pool",scope="reports",public_report_model=m)
        self.assertEqual(g1.observation(),g2.observation())
        self.assertEqual(search(g1),search(g2))
        b=discover(changed,"strategic","pool",scope="reports",public_report_model=m,environment_counts=w)
        self.assertFalse(b["evidence"]["model_matches_real_execution"])
        self.assertEqual(b["evidence"]["classification"],"PUBLIC_MODEL_MISMATCH_NOT_VERIFIED")

    def test_foreign_private_preferences_not_an_observation(self):
        s,w,m=data();changed=deepcopy(s)
        changed["controllers"]["honest"]["external_weights"]={"task-0":{"m0":1000}}
        self.assertEqual(prepare_game(s,"strategic","lmsr").observation(),prepare_game(changed,"strategic","lmsr").observation())

    def test_report_game_requires_public_model_and_last_commit(self):
        s,w,m=data()
        with self.assertRaisesRegex(Rejection,"PUBLIC_REPORT_MODEL_REQUIRED"):prepare_game(s,"strategic","pool",scope="reports")
        with self.assertRaisesRegex(Rejection,"UNSUPPORTED_REPORT_GAME"):prepare_game(s,"strategic","lmsr",scope="reports",public_report_model=m)

    def test_zero_external_report_proper_scoring_negative_control(self):
        s,w,m=data({"external":0})
        b=discover(s,"strategic","pool",scope="reports",public_report_model=m,environment_counts=w)
        self.assertEqual(b["evidence"]["gain_vs_signal_following"],[0,1])
        self.assertEqual(b["evidence"]["zero_external_control"]["gain_vs_signal_following"],[0,1])

    def test_scoring_opportunity_cost_no_free_alias_reward(self):
        s,w,m=data({"aliases":2,"external":0})
        b=discover(s,"strategic","pool",scope="reports",public_report_model=m,environment_counts=w)
        self.assertEqual(b["evidence"]["gain_vs_signal_following"],[0,1])
        self.assertTrue(b["evidence"]["resource_matching"]["same_registry_config_caps_and_schedule"])
        self.assertEqual(len(b["evidence"]["resource_matching"]["registered_actors"]),3)

    def test_capital_fees_and_exhausted_slots_are_real_engine_constraints(self):
        for profile in [{"capital":0},{"fee":20},{"action_limit":0}]:
            s,w,m=data(profile)
            if "action_limit" in profile:s["economics"]["action_limit"]=0
            b=discover(s,"strategic","lmsr",environment_counts=w,max_nodes=500)
            self.assertEqual(b["evidence"]["gain_vs_signal_following"],[0,1])

    def test_selected_searched_case_independent_event_profit_and_null_controls(self):
        s,w,m=data({"fee":2},seed=7)
        b=discover(s,"strategic","lmsr",environment_counts=w,max_nodes=500)
        e=b["evidence"]
        self.assertEqual(e["classification"],"VERIFIED_STRATEGIC_ALLOCATION_DEVIATION")
        self.assertEqual(e["gain_vs_signal_following"],[11,3])
        self.assertEqual(e["incentive_decomposition"]["cash_gain"],[-7,3])
        self.assertEqual(e["incentive_decomposition"]["external_gain"],6)
        self.assertEqual(e["environment_expected_welfare_loss"],[2,3])
        self.assertEqual(e["zero_external_control"]["gain_vs_signal_following"],[0,1])
        for name,r in b["receipts"].items():
            p=recompute(r,"strategic",w)
            expected=e["independent_payoff_checks"].get(name,e["zero_external_control"]["independent_payoff_checks"].get(name))
            self.assertEqual(p,expected)

    def test_expected_gain_is_not_realized_luck_or_monetary_welfare(self):
        s,w,m=data({"fee":2},seed=7)
        first=discover(s,"strategic","lmsr",environment_counts=w)
        for row in s["sealed_outcomes"]:row["quality"]=1-row["quality"]
        second=discover(s,"strategic","lmsr",environment_counts=w)
        self.assertEqual(first["evidence"]["search"],second["evidence"]["search"])
        self.assertEqual(first["evidence"]["gain_vs_signal_following"],second["evidence"]["gain_vs_signal_following"])
        self.assertEqual(first["evidence"]["environment_expected_welfare_loss"],second["evidence"]["environment_expected_welfare_loss"])


class TestResearchProtocolAndReplay(unittest.TestCase):
    def test_evaluator_realization_seed_is_not_public_schedule_seed(self):
        s,w,m=environment({},17,realization_seed=100)
        t,v,n=environment({},17,realization_seed=200)
        self.assertEqual(w,v);self.assertEqual(s["agents"],t["agents"])
        self.assertNotEqual(s["sealed_outcomes"],t["sealed_outcomes"])
        a=search(prepare_game(s,"strategic","lmsr"),max_nodes=500)
        b=search(prepare_game(t,"strategic","lmsr"),max_nodes=500)
        self.assertEqual(a["commands"],b["commands"])
        self.assertEqual(a["selected"],b["selected"])
        self.assertNotIn("realization_seed",str(prepare_game(s,"strategic","lmsr").observation()))

    def test_guard_rejects_future_uncontrolled_action_in_search_game(self):
        s,w,m=data();g=prepare_game(s,"strategic","lmsr")
        g.engine.schedule.append(["h0",g.engine.schedule[-1][1]])
        with self.assertRaisesRegex(Rejection,"FUTURE_UNCONTROLLED"):search(g)

    def test_genuine_error_correlation_and_other_stream_invariance(self):
        s,w,m=data({"belief_quality":50,"correlated":True},seed=17)
        t,v,n=data({"belief_quality":50,"correlated":False},seed=17)
        self.assertEqual(s["agents"]["h0"]["signals"],s["agents"]["z0"]["signals"])
        self.assertNotEqual(t["agents"]["h0"]["signals"],t["agents"]["z0"]["signals"])
        self.assertEqual(w,v);self.assertEqual(s["sealed_outcomes"],t["sealed_outcomes"])
        self.assertEqual(s["controllers"],t["controllers"])

    def test_outcome_realization_independent_of_belief_regime(self):
        s,w,m=data({"belief_quality":100},seed=211)
        t,v,n=data({"belief_quality":0},seed=211)
        self.assertEqual(s["sealed_outcomes"],t["sealed_outcomes"])
        self.assertEqual(w,v)

    def test_bundle_replay_tamper_detection_and_all_six_receipts(self):
        s,w,m=data({"fee":2},seed=7)
        b=discover(s,"strategic","lmsr",environment_counts=w)
        with tempfile.TemporaryDirectory() as d:
            write_bundle(b,d);loaded=load_bundle(d)
            self.assertEqual(replay(loaded),b)
            self.assertEqual(len(loaded["receipts"]),6)
            p=Path(d)/"evidence.json";e=json.loads(p.read_text());e["gain_vs_signal_following"]=[1000,1];p.write_text(json.dumps(e))
            with self.assertRaisesRegex(Rejection,"ARTIFACT_HASH"):load_bundle(d)
        changed=deepcopy(b);changed["evidence"]["classification"]="FAKE"
        with self.assertRaisesRegex(Rejection,"ATTACK_REPLAY"):replay(changed)

    def test_small_campaign_reports_nulls_and_unsupported_without_filtering(self):
        protocol={"known_pilot_seeds":[7],"replication_seeds":[31],"mechanisms":["lmsr","pool"],
            "evaluator_seed":42,
            "base_profile":{"external":0},"profiles":[{"id":"null","overrides":{}}],
            "search":{"exact_node_cap":200,"heuristic_node_cap":20,"beam_width":2}}
        summary,selected=run_campaign(protocol)
        self.assertEqual(summary["counts"]["total"],4)
        self.assertTrue(any(r["status"]=="NOT_EVALUATED" for r in summary["cases"]))
        self.assertIsNone(selected)
