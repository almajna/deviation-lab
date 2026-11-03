"""Reviewed exploratory evaluation; strategies are frozen before validation."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random
from deviation.contracts import prompt_group
from deviation.data.pipeline import digest
from deviation.markets.engine import market_id
from deviation.markets.policies import fit_temperature
from deviation.markets.numeric import project_rational
from deviation.simulator.runner import implementation_sha256
from .data import load
from .forecast import fit
from .protocol import check
from .runner import execute
from .statistics import recorded_summary, synthetic_summary
from .worlds import synthetic, remove_external, normalized_resources, economics, controller


def compact(receipt):
    m=receipt['metrics'];r=m['realized_report']
    result={k:deepcopy(m[k]) for k in ['brier','proxy_squared_error','tie_zero_quality','tie_one_quality',
        'zero_as_one_quality','maker_initial_funding','maker_cash_pnl','fees','score_reserve','score_paid',
        'accepted','rejected','trades','updates','noops','optional_slots','task_count','calibration_bins','calibration_abs_error']}
    result.update({k:deepcopy(v) for k,v in r.items() if k not in {'selected_costs','schema_version','phase','cost_unit'}})
    result['quality']=m['evaluation']['mean_preference_proxy']
    result['reservation_utilization']=r['reservation_spend']/receipt['allocation']['reservation_budget'] if receipt['allocation']['reservation_budget'] else 0
    result['receipt_sha256']=receipt['sha256'];result['predecision_sha256']=receipt['predecision_sha256']
    return result


def recorded(protocol, manifest, splits, cache, *, download=False):
    cfg=protocol['recorded'];prepared,training,provenance=load(manifest,splits,cache,download=download)
    D=6;learners,full,oof=fit(training,cfg,D)
    T=fit_temperature(oof,prepared['training_rows'],D,30000)
    tasks=sorted(prepared['decision_tasks'],key=lambda t:(prompt_group(t['prompt']),t['task_id']))
    predictions={t['task_id']:[l.predict(t,D) for l in learners] for t in tasks}
    fullpred={t['task_id']:full.predict(t,D) for t in tasks}
    means={m:sum(r['quality'] for r in training if r['model_id']==m)/sum(r['model_id']==m for r in training) for m in full.models}
    source=digest(manifest);rows=[];decision_hashes=[]
    # Group-equivalent task IDs stay in one batch, never split at an arbitrary index.
    groups={}
    for t in tasks:groups.setdefault(prompt_group(t['prompt']),[]).append(t)
    batches=[];batch=[]
    for g,ts in sorted(groups.items()):
        if batch and len(batch)+len(ts)>cfg['batch_size']:batches.append(batch);batch=[]
        batch.extend(ts)
    if batch:batches.append(batch)
    for i,batch in enumerate(batches):
        batch=sorted(batch,key=lambda t:t['task_id']);ids={t['task_id'] for t in batch};C=sum(len(t['model_options']) for t in batch)
        sealed=[r for r in prepared['sealed_outcomes'] if r['task_id'] in ids]
        outcome_callback=lambda:deepcopy(sealed)
        for fraction in cfg['budget_fractions']:
            lo=sum(min(prepared['reservation_artifact']['reservations'][m] for m in t['model_options']) for t in batch)
            hi=sum(max(prepared['reservation_artifact']['reservations'][m] for m in t['model_options']) for t in batch)
            budget=lo+(hi-lo)*fraction[0]//fraction[1]
            for seed in cfg['seeds']:
                agents={f'a{j}':{'controller':f'a{j}','wallet':32,'signals':{market_id(t['task_id'],m):predictions[t['task_id']][j][m]
                    for t in batch for m in t['model_options']},'decline_report':False} for j in range(cfg['agents'])}
                schedule=[[a,market_id(t['task_id'],m)] for a in sorted(agents) for t in batch for m in t['model_options']]
                random.Random(seed).shuffle(schedule)
                public={'tasks':batch,'artifact':prepared['reservation_artifact'],'budget':budget,'economics':economics(D,order_limit=cfg['order_limit']),
                    'agents':agents,'controllers':{a:controller(32,C,C) for a in agents},'schedule':schedule,
                    'temperature':T,'training_means':means,'data_kind':provenance['data_kind'],
                    'source_sha256':source,'split_sha256':splits['sha256'],'seed':seed}
                # Lock EVERY ordinary treatment before ANY current outcomes are read.
                pending={m:execute(public,outcome_callback,m,full_predictions=fullpred,defer_settlement=True)
                    for m in cfg['mechanisms'] if m!='oracle-analysis-only'}
                receipts={m:finish() for m,finish in pending.items()}
                signatures={r['resource_signature'] for r in receipts.values()}
                if len(signatures)!=1:raise ValueError('UNMATCHED_RECORDED_RESOURCES')
                oraclevals={t['task_id']:{m:Fraction(str(next(r['quality'] for r in sealed if r['task_id']==t['task_id'] and r['model_id']==m))) for m in t['model_options']} for t in batch}
                oracle=execute(public,outcome_callback,'oracle-analysis-only',oracle_values=oraclevals)
                receipts['oracle-analysis-only']=oracle
                for m,r in receipts.items():
                    row=compact(r);row.update(batch=i,budget_fraction=f'{fraction[0]}/{fraction[1]}',seed=seed,mechanism=m,
                        regret=oracle['metrics']['evaluation']['mean_preference_proxy']-r['metrics']['evaluation']['mean_preference_proxy'],
                        rerouted_fraction=sum(a['model_id']!=b['model_id'] for a,b in zip(r['allocation']['allocations'],receipts['calibrated-pool']['allocation']['allocations']))/len(batch))
                    rows.append(row)
                decision_hashes.append(digest({m:r['predecision_sha256'] for m,r in receipts.items() if m!='oracle-analysis-only'}))
    return {'provenance':provenance,'temperature_train_oof':T,'forecaster_training_hashes':[l.sha256 for l in learners],
        'full_training_hash':full.sha256,'reservation_artifact':prepared['reservation_artifact'],
        'decision_hashes':decision_hashes,'rows':rows,'summary':recorded_summary(rows,cfg['mechanisms'],protocol['statistics'])}


def candidates(protocol):
    p=protocol['synthetic']
    return [{'kind':'honest'},{'kind':'no-action'}]+[
        {'kind':'template','bias':bias,'trade_weight':weight,'report_timing':timing}
        for bias in p['bias_grid'] for weight in p['trade_weight_grid'] for timing in p['report_timing']]


def optimize_templates(protocol):
    cfg=protocol['synthetic'];catalog=candidates(protocol);all_tables=[];winners={}
    for zero in [False,True]:
        for mechanism in cfg['mechanisms']:
            table=[]
            for spec in catalog:
                utilities=[];hashes=[]
                for definition in cfg['development_profiles']:
                    profile=deepcopy(cfg['base']);profile.update(definition['overrides'])
                    for seed in cfg['development_seeds']:
                        p,y,_=synthetic(profile,seed)
                        if zero:p=remove_external(p)
                        r=execute(p,lambda:deepcopy(y),mechanism,strategy=spec)
                        utilities.append(r['metrics']['controllers']['strategic']['utility']);hashes.append(r['sha256'])
                table.append({'strategy':spec,'mean_development_utility':sum(utilities)/len(utilities),'world_utilities':utilities,'receipt_hashes':hashes})
            winner=max(range(len(table)),key=lambda i:(table[i]['mean_development_utility'],-i))
            key=f'{mechanism}:zero={zero}'
            winners[key]=deepcopy(table[winner]['strategy'])
            all_tables.append({'condition':key,'selected_index':winner,'candidates':table,
                'optimality_scope':'EXACT_FINITE_TEMPLATE_CLASS_ON_DEVELOPMENT_SAMPLE_ONLY_NOT_EXPECTED_OR_FULL_GAME'})
    result={'version':'frozen-template-selection-1','development_seeds':cfg['development_seeds'],
        'winners':winners,'tables':all_tables,'protocol_sha256':digest(protocol)}
    result['sha256']=digest(result);return result


def synthetic_validation(protocol,selection):
    cfg=protocol['synthetic'];rows=[];sample=None
    if selection['protocol_sha256']!=digest(protocol):raise ValueError('SELECTION_PROTOCOL_MISMATCH')
    for definition in cfg['validation_profiles']:
        profile=deepcopy(cfg['base']);profile.update(definition['overrides'])
        for seed in cfg['validation_seeds']:
            p,y,nature=synthetic(profile,seed)
            # Same nature draws/resource totals under normalized account partition.
            twin=deepcopy(profile);twin['active_aliases']=3-profile['active_aliases']
            other,other_y,_=synthetic(twin,seed)
            if normalized_resources(p)!=normalized_resources(other) or y!=other_y:raise ValueError('ALIAS_RESOURCE_MISMATCH')
            z=remove_external(p)
            pending={}
            for m in cfg['mechanisms']:
                for condition,spec,pub in [('attack',selection['winners'][f'{m}:zero=False'],p),
                    ('honest',{'kind':'honest'},p),('no-action',{'kind':'no-action'},p),
                    ('zero-attack',selection['winners'][f'{m}:zero=True'],z),('zero-honest',{'kind':'honest'},z)]:
                    pending[m,condition]=execute(pub,lambda:deepcopy(y),m,strategy=spec,defer_settlement=True)
            receipts={k:f() for k,f in pending.items()}
            for m in cfg['mechanisms']:
                attack=receipts[m,'attack'];honest=receipts[m,'honest'];noop=receipts[m,'no-action']
                if len({r['resource_signature'] for r in [attack,honest,noop]})!=1:raise ValueError('UNMATCHED_ATTACK_RESOURCES')
                metrics=attack['metrics'];a=metrics['controllers']['strategic'];h=honest['metrics']['controllers']['strategic'];n=noop['metrics']['controllers']['strategic']
                za=receipts[m,'zero-attack']['metrics']['controllers']['strategic'];zh=receipts[m,'zero-honest']['metrics']['controllers']['strategic']
                alloc=lambda r:[c['model_id'] for c in r['allocation']['allocations']]
                row={'profile':definition['id'],'world_seed':seed,'mechanism':m,'parameters':profile,
                    'utility_gain':a['utility']-h['utility'],'gain_vs_no_action':a['utility']-n['utility'],
                    'cash_gain':a['cash_delta']-h['cash_delta'],'external_gain':a['external_benefit']-h['external_benefit'],
                    'welfare_loss':honest['metrics']['evaluation']['mean_preference_proxy']-metrics['evaluation']['mean_preference_proxy'],
                    'quality':metrics['evaluation']['mean_preference_proxy'],'brier':metrics['brier'],
                    'zero_external_gain':za['utility']-zh['utility'],
                    'rerouted_fraction':sum(x!=y for x,y in zip(alloc(attack),alloc(honest)))/len(p['tasks']),
                    'receipt_hashes':{c:r['sha256'] for (mm,c),r in receipts.items() if mm==m},
                    'all_schedules_supported':True,'alias_normalization_checked':True,
                    **{k:metrics[k] for k in ['fees','maker_cash_pnl','score_paid','accepted','rejected','trades','updates','noops']}}
                if row['utility_gain']!=row['cash_gain']+row['external_gain']:raise ValueError('UTILITY_DECOMPOSITION')
                rows.append(row)
                # First predeclared case regardless of outcome; no success selection.
                if sample is None:sample={'public':p,'sealed_synthetic_outcomes':y,'nature':nature,
                    'strategy':selection['winners'][f'{m}:zero=False'],'mechanism':m,'receipt':attack}
    return {'rows':rows,'summary':synthetic_summary(rows,protocol['statistics']),'sample':sample}


def evaluate(protocol, review, *, manifest=None, splits=None, cache=None, download=False, synthetic_only=False):
    protocol=check(protocol,review)
    selection=optimize_templates(protocol)  # No validation outcomes generated yet.
    selection_sha=selection['sha256']
    synthetic_result=synthetic_validation(protocol,selection)
    if selection['sha256']!=selection_sha or digest({k:v for k,v in selection.items() if k!='sha256'})!=selection_sha:
        raise ValueError('VALIDATION_CHANGED_SELECTION')
    recorded_result=None if synthetic_only else recorded(protocol,manifest,splits,cache,download=download)
    result={'version':'exploratory-benchmark-1','status':'EXPLORATORY_VALIDATION_NOT_FINAL',
        'protocol_sha256':digest(protocol),'review':review,'implementation_sha256':implementation_sha256(),
        'incremental_spend_usd':0,'final_holdout_accessed':False,'existing_test_split_evaluated':False,
        'selection':selection,'synthetic':synthetic_result,'recorded':recorded_result}
    result['sha256']=digest(result);return result


def save(result, destination):
    path=Path(destination);path.mkdir(parents=True,exist_ok=True)
    encode=lambda x:json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n'
    (path/'results.json').write_text(encode(result))
    from .report import render
    render(result,path)
    manifest={'version':'benchmark-artifacts-1','result_sha256':result['sha256'],
        'files':{p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir()) if p.is_file() and p.name!='manifest.json'}}
    (path/'manifest.json').write_text(encode(manifest))
