"""Cross-track checks of actual transitions, source identity and scientific values."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deviation.attacks.certified import solve
from deviation.attacks.environments import environment
from deviation.attacks.evidence import execute as execute_commands
from deviation.attacks.game import prepare_game
from deviation.attacks.verify import recompute
from deviation.data.pipeline import digest
from deviation.evaluation.runner import audit_events
from deviation.verification.checker import check
from deviation_integration.bridge import same_science, replay_recorded, replay_pilot, compare_attack_bundle
from deviation_integration.provenance import preservation_audit, read
from deviation_integration.reproduce import Reproduction
from deviation_llm_agents.harness import replay_episode
from deviation_llm_agents.pilot import verify_pilot

ROOT=Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def test_every_upstream_artifact_protocol_and_runtime_file_preserved(self):
        audit=preservation_audit()
        self.assertEqual(set(audit),{'phase4','benchmark','producer','verification','agents'})
        self.assertTrue(all(x['files'] for x in audit.values()))

    def test_current_certificate_executes_and_all_three_payoff_audits_agree(self):
        s,_,_=environment({'fee':2},7,realization_seed=12352)
        game=prepare_game(s,'strategic','lmsr')
        certificate=solve(game,max_expansions=100)
        checked=check(game,certificate)
        receipt=execute_commands(s,'lmsr',certificate['incumbent_commands'])
        payoff=recompute(receipt,'strategic',game.beliefs)
        self.assertEqual(checked['lower'],payoff['expected_utility'])
        from deviation_llm_agents.experiments import metrics as agent_metrics
        self.assertEqual(agent_metrics(receipt,s,sorted(game.members)[0])['expected_utility'],checked['lower'])
        self.assertEqual(checked['lower'],certificate['upper'])
        self.assertEqual(checked['allocation'],receipt['allocation_plan']['allocations'])
        summary=receipt['trace']['events'][-1]['payload']
        self.assertTrue(audit_events(receipt['trace']['events'],summary['initial_balances'],summary['final_balances']))
        forged=deepcopy(certificate);forged['source_sha256']='0'*64
        forged['sha256']=digest({k:v for k,v in forged.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'source binding'):check(game,forged)

    def test_actual_selected_attack_bundle_and_sensitivity_rebind_only_metadata(self):
        from deviation.attacks.evidence import load_bundle,discover
        from deviation.attacks.sensitivity import sensitivity
        old=load_bundle(ROOT/'artifacts/attacks/phase4/selected')
        actual=discover(old['scenario'],old['controller'],old['mechanism'],**old['options'])
        changes=compare_attack_bundle(old,actual)
        self.assertTrue(changes['attack'])
        same_science(read(ROOT/'artifacts/attacks/phase4/sensitivity.json'),sensitivity(actual))
        actual['receipts']['attack']['trace']['events'][-1]['payload']['accepted']+=1
        with self.assertRaises(ValueError):compare_attack_bundle(old,actual)

    def test_campaign_case_and_bundle_manifests_rebind_without_changing_results(self):
        from deviation.attacks.campaign import run_campaign
        protocol=read(ROOT/'experiments/adversarial_protocol.json')
        protocol['known_pilot_seeds']=[7];protocol['replication_seeds']=[]
        protocol['post_review_replication_seeds']=[];protocol['mechanisms']=['lmsr']
        protocol['profiles']=[p for p in protocol['profiles'] if p['id']=='costly']
        with tempfile.TemporaryDirectory() as folder:
            current,_=run_campaign(protocol,folder)
        original=read(ROOT/'artifacts/attacks/phase4/campaign.json');case=current['cases'][0]['case']
        oldrow=next(r for r in original['cases'] if r['case']==case)
        changes=same_science({'cases':[oldrow],'counterexample_manifests':{case:original['counterexample_manifests'][case]}},
                            {'cases':current['cases'],'counterexample_manifests':current['counterexample_manifests']})
        self.assertTrue(changes)
        self.assertEqual(current['cases'][0]['status'],'EVALUATED')
        bad=deepcopy(current['cases']);bad[0]['gain_vs_honest']=[999,1]
        with self.assertRaises(ValueError):same_science({'cases':[oldrow]},{'cases':bad})

    def test_labels_costs_and_hidden_realization_cannot_change_certificate_or_commands(self):
        s,_,_=environment({'fee':2},7,realization_seed=12352)
        original=solve(prepare_game(s,'strategic','lmsr'),max_expansions=100)
        changed=deepcopy(s)
        for row in changed['sealed_outcomes']:
            row['quality']=1-row['quality'];row['cost_decimal']='99'
        other=solve(prepare_game(changed,'strategic','lmsr'),max_expansions=100)
        self.assertEqual(original,other)

    def test_original_strict_source_rejection_remains_active(self):
        pilot=read(ROOT/'artifacts/llm_agents/real_pilot.json')
        with self.assertRaisesRegex(ValueError,'ECONOMIC_REPLAY_MISMATCH'):verify_pilot(pilot)
        e=pilot['episodes'][0]
        with self.assertRaisesRegex(ValueError,'ECONOMIC_REPLAY_MISMATCH'):replay_episode(e['scenario'],e['sidecar'])

    def test_recorded_pilot_uses_current_engine_without_inference_or_relabeling(self):
        pilot=read(ROOT/'artifacts/llm_agents/real_pilot.json');before=deepcopy(pilot)
        with patch('deviation_llm_agents.transformers_cpu.TransformersCPU',side_effect=AssertionError('NO INFERENCE')):
            actual=replay_pilot(pilot)
        self.assertEqual(pilot,before)
        self.assertEqual(actual['execution_origin'],'RECORDED_DECISION_REPLAY')
        self.assertEqual(actual['new_inference_calls'],0)
        self.assertEqual(len(actual['episodes']),6)
        for old,new in zip(pilot['episodes'],actual['episodes']):
            self.assertEqual(new['recorded']['audit_sha256'],digest(old['sidecar']['audit']))
            self.assertEqual(new['recorded']['receipt']['allocation_plan'],old['sidecar']['engine_result']['allocation_plan'])
            self.assertEqual(new['recorded']['receipt']['trace']['events'],old['sidecar']['engine_result']['trace']['events'])
        self.assertEqual((pilot['calls_attempted'],pilot['valid_model_decisions']),(24,2))
        self.assertEqual(sum(r['status']=='FAILED_DECISION' for e in pilot['episodes'] for r in e['sidecar']['audit']['records']),22)

    def test_recorded_context_action_and_summary_corruption_rejected(self):
        e=read(ROOT/'artifacts/llm_agents/real_pilot.json')['episodes'][0]
        for field in ['packet_sha256','prompt_sha256']:
            bad=deepcopy(e['sidecar']);r=bad['audit']['records'][0];r[field]='0'*64
            r['sha256']=digest({k:v for k,v in r.items() if k!='sha256'})
            bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'})
            with self.assertRaises(ValueError):replay_recorded(e['scenario'],bad)
        bad=deepcopy(e['sidecar']);bad['metrics']['accepted_trades']=1
        bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'METRICS_CHANGED'):replay_recorded(e['scenario'],bad)

    def test_numeric_string_scope_and_private_hash_changes_are_never_rebindings(self):
        for key,a,b in [('quality',0,1),('quality',0,0.),('gap',[0,1],[1,1]),
                        ('claim','EXACT_FINITE_SUBGAME','BOUNDED_FINITE_SUBGAME')]:
            with self.subTest(key=key),self.assertRaises(ValueError):same_science({key:a},{key:b})
        for key in ['packet_sha256','prompt_sha256','observation_sha256','protocol_sha256',
                    'split_sha256','source_manifest_sha256','predecision_sha256']:
            for wrapper in [lambda x:x,lambda x:{'sha256':x},lambda x:{'source_sha256':x}]:
                with self.subTest(key=key),self.assertRaises(ValueError):
                    same_science(wrapper({key:'a'*64}),wrapper({key:'b'*64}))
        self.assertEqual(same_science({'sha256':'a'*64},{'sha256':'b'*64})[0]['path'],['sha256'])
        with self.assertRaises(ValueError):same_science({'x':{'source_sha256':'a'*64}},{'x':{'source_sha256':'b'*64}})

    def test_original_negative_certificate_run_and_timing_statistic_preserved(self):
        from deviation.verification.benchmark import timing_summary
        base=ROOT/'artifacts/verification'
        initial=read(base/'initial_run/results.json');official=read(base/'results.json')
        self.assertTrue(same_science(initial,official))
        self.assertEqual(len(initial['rows']),81)
        times=read(base/'initial_run/timings.json')
        self.assertEqual(times['results_sha256'],initial['sha256'])
        computed=timing_summary(initial['rows'],times['samples'],read(ROOT/'experiments/certificate_benchmark.json'))
        self.assertEqual(computed,times['summary'])
        self.assertFalse(computed['prespecified_speed_criterion_met'])

    def test_optional_plots_do_not_change_numerical_manifest_file_set(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            runner=Reproduction(Path(folder)/'out',folder)
            shutil.copytree(ROOT/'artifacts/benchmark/phase5',runner.out/'historical/benchmark')
            shutil.copytree(ROOT/'artifacts/verification',runner.out/'historical/verification')
            before=deepcopy(runner.files)
            with patch.object(runner,'call'):runner.plots()
            self.assertEqual(runner.files,before)

    def test_reproduction_refuses_nonempty_and_evidence_output_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'keep').write_text('keep')
            with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_EMPTY'):Reproduction(folder,folder)
        with self.assertRaisesRegex(ValueError,'OVERWRITE'):Reproduction(ROOT/'artifacts/integration',ROOT)


if __name__=='__main__':unittest.main()
