"""Scientific boundary, paired-design and actual-engine regression evidence."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deviation.data.pipeline import digest
from deviation.contracts import prompt_group
from deviation.evaluation.protocol import check, ProtocolError
from deviation.evaluation.forecast import TextForecaster, fit, fold
from deviation.evaluation.worlds import posterior, synthetic, normalized_resources
from deviation.evaluation.runner import execute, audit_events
from deviation.evaluation.benchmark import optimize_templates, synthetic_validation, save
from deviation.evaluation.statistics import interval, recorded_summary
from deviation.evaluation.data import load
from deviation.evaluation.policies import Template

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=json.loads((ROOT/'experiments/benchmark_protocol.json').read_text())
REVIEW=json.loads((ROOT/'experiments/benchmark_review.json').read_text())


class TestProtocolAndForecast(unittest.TestCase):
    def test_exact_review_and_no_final_or_test_paths(self):
        check(PROTOCOL,REVIEW)
        for field,value in [('final_evaluation_enabled',True),('recorded_test_split_enabled',True),('paid_spend_usd',1)]:
            p=deepcopy(PROTOCOL);p['guardrails'][field]=value
            with self.assertRaises(ProtocolError):check(p,REVIEW)
        p=deepcopy(PROTOCOL);p['recorded']['allowed_decision_split']='test'
        r=deepcopy(REVIEW);r['protocol_sha256']=digest(p)
        with self.assertRaises(ProtocolError):check(p,r)
        p=deepcopy(PROTOCOL);p['recorded']['neighbors']=100
        with self.assertRaises(ProtocolError):check(p,REVIEW)
        for s in ['test','final','holdout','unknown']:
            with self.assertRaisesRegex(ValueError,'FORBIDDEN'):load({}, {}, Path('.'),decision_split=s)

    def test_disjoint_world_seeds_required(self):
        p=deepcopy(PROTOCOL);p['synthetic']['validation_seeds']=p['synthetic']['development_seeds']
        r=deepcopy(REVIEW);r['protocol_sha256']=digest(p)
        with self.assertRaisesRegex(ProtocolError,'OVERLAP'):check(p,r)

    def test_posterior_uses_observation_likelihood_not_label(self):
        self.assertEqual(posterior(2,[1,1,1],[2,3],6),[1,1,4])
        self.assertEqual(sum(posterior(0,[3,2,1],[1,2],6)),6)
        with self.assertRaises(ValueError):posterior(0,[1,1,1],[1,1],6)

    def test_forecaster_training_only_group_guard_and_public_features(self):
        rows=[{'task_id':'train','prompt':'Python list iteration','model_id':'m0','quality':1}]
        f=TextForecaster(rows);task={'task_id':'new','prompt':'new Python iteration','model_options':['m0']}
        prediction=f.predict(task,6)
        self.assertEqual(set(prediction),{'m0'})
        self.assertEqual(sum(prediction['m0']),6)
        with self.assertRaisesRegex(ValueError,'LEAKAGE'):f.predict({**task,'prompt':' PYTHON  LIST iteration '},6)
        rows[0]['quality']=0
        self.assertEqual(prediction,f.predict(task,6))  # frozen copied scalar rows

    def test_inner_oof_coverage_and_excluded_training_groups(self):
        rows=[]
        for i in range(64):
            for m in ['m0','m1']:
                rows.append({'task_id':f'train-{i}','prompt':f'Synthetic training text {i}','model_id':m,'quality':(i%3)/2})
        cfg=PROTOCOL['recorded']
        learners,full,oof=fit(rows,cfg,6)
        self.assertEqual(len(oof),len(rows));self.assertEqual(len({(r['task_id'],r['model_id']) for r in oof}),len(rows))
        self.assertTrue(all(not(learners[i].groups&learners[j].groups) for i in range(4) for j in range(i)))
        self.assertEqual(set.union(*(x.groups for x in learners)),full.groups)


class TestEngineAndInformation(unittest.TestCase):
    def setUp(self):
        self.profile=deepcopy(PROTOCOL['synthetic']['base'])
        self.public,self.labels,_=synthetic(self.profile,99991)

    def test_all_schedules_execute_no_terminal_horizon_filter(self):
        for schedule_seed in [1,2,3,4]:
            p,y,_=synthetic(self.profile,99991,schedule_seed=schedule_seed)
            r=execute(p,lambda:y,'lmsr')
            self.assertEqual(r['metrics']['optional_slots'],len(p['schedule']))
            self.assertEqual(r['events'][-1]['type'],'economic_summary')
            self.assertEqual(r['metrics']['rejected'],0)

    def test_informative_order_size_avoids_integer_inactivity_floor(self):
        from deviation.markets.engine import Engine
        from deviation.markets.runner import packet
        from deviation.markets.policies import SignalFollowing
        for Q,expected in [(1,'no_op'),(3,'trade_shares')]:
            p=deepcopy(self.public);p['economics']['order_limit']=Q
            definitions={a:{'controller':v['controller'],'wallet':v['wallet']} for a,v in p['agents'].items()}
            e=Engine(p['tasks'],p['economics'],definitions,p['controllers'],p['schedule'])
            for a,mid in sorted(e.tokens):e.commit(a,mid,[1,0,5])
            e.reveal();a,mid=e.schedule[0]
            scenario={'agents':p['agents'],'decision_tasks':p['tasks'],'reservation_budget':p['budget']}
            info=packet(e,scenario,a,mid,'lmsr',p['artifact']);info['own_signal']=[1,0,5]
            request=SignalFollowing().act(info)
            self.assertEqual(request['kind'],expected)
            if Q==3:
                receipt=e.inspect_order(a,mid,request['share_delta'],request['max_net_debit'])
                gain=sum(Fraction(n,6)*x for n,x in zip(info['own_signal'],request['share_delta']))-receipt['receipt']['charge']-p['economics']['fee']
                self.assertGreater(gain,0)
                self.assertTrue(e.apply(request,allowed_kinds={'no_op','trade_shares'}))

    def test_allocation_lock_precedes_sealed_callback(self):
        calls=[]
        pending=[execute(self.public,lambda:(calls.append('read') or self.labels),m,defer_settlement=True)
                 for m in ['lmsr','pool','calibrated-pool']]
        self.assertEqual(calls,[])
        rs=[f() for f in pending]
        self.assertEqual(len(calls),3)
        self.assertEqual(len({r['resource_signature'] for r in rs}),1)
        for r in rs:
            lock=next(e['seq'] for e in r['events'] if e['type']=='allocation_locked')
            settled=next(e['seq'] for e in r['events'] if e['type']=='market_settled')
            self.assertLess(lock,settled)

    def test_hidden_quality_and_cost_mutation_does_not_change_decisions(self):
        mutated=deepcopy(self.labels)
        for row in mutated:row['quality']=1-row['quality'];row['cost_decimal']='999E-9'
        for m in ['lmsr','pool','interactive-pool','calibrated-pool']:
            a=execute(self.public,lambda:self.labels,m,strategy={'kind':'template','bias':3,'trade_weight':3})
            b=execute(self.public,lambda:mutated,m,strategy={'kind':'template','bias':3,'trade_weight':3})
            self.assertEqual(a['allocation'],b['allocation']);self.assertEqual(a['predecision_sha256'],b['predecision_sha256'])
            self.assertNotEqual(a['metrics']['realized_report'],b['metrics']['realized_report'])

    def test_correlated_channel_and_normalized_aliases(self):
        p1=deepcopy(self.profile);p1['correlation']=[1,1]
        p,y,_=synthetic(p1,99991)
        self.assertEqual(p['agents']['h0']['signals'],p['agents']['h1']['signals'])
        p2=deepcopy(self.profile);p2['active_aliases']=2
        q,z,_=synthetic(p2,99991)
        self.assertEqual(self.labels,z);self.assertEqual(normalized_resources(self.public),normalized_resources(q))
        self.assertEqual(y,z)  # Changing correlation preserves outcome draws.
        self.assertEqual(sum(a['wallet'] for a in self.public['agents'].values()),sum(a['wallet'] for a in q['agents'].values()))
        self.assertEqual(len(self.public['schedule']),len(q['schedule']))

    def test_no_action_retains_identical_original_report_rewards(self):
        h=execute(self.public,lambda:self.labels,'lmsr',strategy={'kind':'honest'})
        n=execute(self.public,lambda:self.labels,'lmsr',strategy={'kind':'no-action'})
        reports=lambda r:[e for e in r['events'] if e['type']=='report_revealed']
        self.assertEqual(reports(h),reports(n))
        scores=lambda r:[e['payload']['score'] for e in r['events'] if e['type']=='score_settled']
        self.assertEqual(scores(h),scores(n))

    def test_delayed_bias_executes_real_interactive_updates(self):
        spec={'kind':'template','bias':6,'trade_weight':0,'report_timing':'delayed'}
        r=execute(self.public,lambda:self.labels,'interactive-pool',strategy=spec)
        updates=[e for e in r['events'] if e['type']=='distribution_updated']
        self.assertTrue(updates)
        h=execute(self.public,lambda:self.labels,'interactive-pool',strategy={'kind':'honest'})
        original=lambda r:[e for e in r['events'] if e['type']=='report_revealed']
        self.assertEqual(original(r),original(h))

    def test_independent_ledger_score_and_claim_checks(self):
        r=execute(self.public,lambda:self.labels,'lmsr')
        last=r['events'][-1]['payload'];events=deepcopy(r['events'])
        event=next(e for e in events if e['type']=='score_settled');event['payload']['score']+=1
        with self.assertRaisesRegex(ValueError,'SCORE'):audit_events(events,last['initial_balances'],last['final_balances'])
        with self.assertRaises(ValueError):audit_events(r['events'],last['initial_balances'],{**last['final_balances'],'fee_sink':999})

    def test_no_private_nature_seed_or_sealed_fields_in_policy_packets(self):
        from deviation.evaluation.policies import policy
        seen=[]
        class Spy:
            def act(self,p):
                seen.append(deepcopy(p));return policy({'kind':'honest'}).act(p)
        with patch('deviation.evaluation.runner.policy',return_value=Spy()):execute(self.public,lambda:self.labels,'lmsr')
        encoded=json.dumps(seen)
        self.assertNotIn('nature_seed',encoded);self.assertNotIn('sealed',encoded);self.assertNotIn('99991',encoded)
        self.assertTrue(all('own_signal' in p and 'signals' not in p for p in seen))
        p=deepcopy(self.public);p['sealed_outcomes']=self.labels
        with self.assertRaisesRegex(ValueError,'HIDDEN'):execute(p,lambda:self.labels,'lmsr')

    def test_oracle_rejected_as_ordinary_input_and_budget_bound(self):
        with self.assertRaisesRegex(ValueError,'ORACLE'):execute(self.public,lambda:self.labels,'pool',oracle_values={})
        r=execute(self.public,lambda:self.labels,'cheapest')
        self.assertLessEqual(sum(c['reserved_cost'] for c in r['allocation']['allocations']),self.public['budget'])


class TestSearchAndStatistics(unittest.TestCase):
    def test_full_policy_selection_does_not_depend_on_validation_worlds(self):
        p=deepcopy(PROTOCOL);p['synthetic'].update(development_seeds=[99991],mechanisms=['pool'],bias_grid=[0],trade_weight_grid=[0],report_timing=['immediate'])
        a=optimize_templates(p);p['synthetic']['validation_seeds']=[99999]
        b=optimize_templates(p)
        self.assertEqual(a['winners'],b['winners']);self.assertEqual(a['tables'],b['tables'])
        self.assertEqual(len(a['tables'][0]['candidates']),3)

    def test_frozen_policies_validate_every_world_and_retain_negative_results(self):
        p=deepcopy(PROTOCOL);p['synthetic'].update(development_seeds=[99991],validation_seeds=[99999],mechanisms=['pool'],bias_grid=[0],trade_weight_grid=[0],report_timing=['immediate'],validation_profiles=[{'id':'unit','overrides':{}}])
        a=optimize_templates(p);snapshot=deepcopy(a)
        r=synthetic_validation(p,a)
        self.assertEqual(a,snapshot);self.assertEqual(len(r['rows']),1)
        self.assertTrue(r['rows'][0]['all_schedules_supported'])
        # Statistics must not clamp negative generalization gains to the honest incumbent.
        rs=[{**r['rows'][0],'utility_gain':-5}]
        from deviation.evaluation.statistics import synthetic_summary
        self.assertEqual(synthetic_summary(rs,p['statistics'])[0]['utility_gain']['estimate'],-5)

    def test_synthetic_end_to_end_artifacts_are_reproducible(self):
        from deviation.evaluation.benchmark import evaluate
        p=deepcopy(PROTOCOL)
        p['synthetic'].update(development_seeds=[99991],validation_seeds=[99999],mechanisms=['pool'],
            bias_grid=[0],trade_weight_grid=[0],report_timing=['immediate'],validation_profiles=[{'id':'unit','overrides':{}}])
        review={**REVIEW,'protocol_sha256':digest(p)}
        result=evaluate(p,review,synthetic_only=True)
        self.assertEqual(result,evaluate(p,review,synthetic_only=True))
        with tempfile.TemporaryDirectory() as d:
            save(result,d)
            files={p.name for p in Path(d).iterdir()}
            self.assertTrue({'results.json','REPORT.md','synthetic_table.csv','plot_data.json','manifest.json'}<=files)
            manifest=json.loads((Path(d)/'manifest.json').read_text())
            import hashlib
            for path,sha in manifest['files'].items():self.assertEqual(hashlib.sha256((Path(d)/path).read_bytes()).hexdigest(),sha)

    def test_float_reductions_do_not_depend_on_builtin_sum_version(self):
        # Python3.11 sum lost this unit; Python3.12 changed its float algorithm.
        r=interval([1e16,1.,-1e16],[1,1,1],replicates=100,seed=3)
        self.assertEqual(r['estimate'],1/3)
        p,y,_=synthetic(PROTOCOL['synthetic']['base'],99991)
        baseline=execute(p,lambda:y,'lmsr')
        def legacy_sum(values,start=0):
            total=start
            for value in values:total+=value
            return total
        with patch('deviation.evaluation.runner.sum',legacy_sum,create=True):
            actual=execute(p,lambda:y,'lmsr')
        self.assertEqual(actual,baseline)

    def test_ratio_bootstrap_retains_unequal_cluster_sizes(self):
        r=interval([4,0],[4,1],replicates=100,seed=3)
        self.assertAlmostEqual(r['estimate'],.8)
        self.assertEqual(r,interval([4,0],[4,1],replicates=100,seed=3))
        self.assertEqual(interval([0,0],[4,3],replicates=100)['upper'],0)


if __name__=='__main__':unittest.main()
