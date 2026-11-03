"""Independent stdlib resampler; never imports production statistics code."""
import argparse
import hashlib
import json, random, statistics, math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((root/p).read_text())
r=read('artifacts/benchmark/phase5/results.json');cfg=read('experiments/benchmark_protocol.json')
cfg=cfg['statistics']; checked=0; maximum_error=0

def interval(values,weights):
 rng=random.Random(cfg['bootstrap_seed']); n=len(values); draws=[]
 for _ in range(cfg['bootstrap_replicates']):
  selected=[rng.randrange(n) for _ in range(n)]
  draws.append(math.fsum(values[i] for i in selected)/sum(weights[i] for i in selected))
 draws.sort()
 return [math.fsum(values)/sum(weights),draws[int(.025*(len(draws)-1))],draws[int(.975*(len(draws)-1))]]

def compare(got,want):
 global checked,maximum_error
 for a,b in zip(got,[want['estimate'],want['lower'],want['upper']]):
  err=abs(a-b); assert err<2e-14,(a,b);maximum_error=max(maximum_error,err);checked+=1

rows=r['recorded']['rows']
for summary in r['recorded']['summary']:
 chosen=[x for x in rows if x['budget_fraction']==summary['budget_fraction']]
 own=[x for x in chosen if x['mechanism']==summary['mechanism']]
 ref={(x['batch'],x['seed']):x for x in chosen if x['mechanism']=='calibrated-pool'}
 groups=[[x for x in own if x['batch']==batch] for batch in sorted({x['batch'] for x in own})]
 weights=[g[0]['task_count'] for g in groups]
 q=[math.fsum(x['quality'] for x in g)*n/len(g) for g,n in zip(groups,weights)]
 delta=[math.fsum(x['quality']-ref[x['batch'],x['seed']]['quality'] for x in g)*n/len(g) for g,n in zip(groups,weights)]
 brier=[math.fsum(x['brier']*x['task_count'] for x in g)/len(g) for g in groups]
 for values,name in [(q,'quality'),(delta,'difference_vs_calibrated_pool'),(brier,'brier_interval')]:compare(interval(values,weights),summary[name])
for summary in r['synthetic']['summary']:
 chosen=[x for x in r['synthetic']['rows'] if x['profile']==summary['profile'] and x['mechanism']==summary['mechanism']]
 for field in ['utility_gain','gain_vs_no_action','cash_gain','external_gain','welfare_loss','rerouted_fraction','zero_external_gain','quality','brier','fees','maker_cash_pnl','score_paid','accepted','rejected','trades','updates','noops']:
  compare(interval([x[field] for x in chosen],[1]*len(chosen)),summary[field])
def check_timing(folder):
 result=read(folder+'/results.json');timing=read(folder+'/timings.json'); protocol=read('experiments/certificate_benchmark.json')
 assert timing['results_sha256']==result['sha256']
 case={x['case']:x for x in result['rows']}; eligible=[]
 for x in timing['samples']:
  row=case[x['case']]
  denominators=[statistics.median(x[k]) for k in ['exhaustive','dynamic_programming'] if row[k]['status']=='EXACT']
  if denominators and row['root_actions']>=2 and row['certificate']['gap']==[0,1]:
   eligible.append({'case':row['case'],'seed':row['seed'],'ratio':(statistics.median(x['solve'])+statistics.median(x['check']))/min(denominators)})
 seeds=sorted({x['seed'] for x in eligible}); rng=random.Random(protocol['bootstrap_seed']);vals=[]
 for _ in range(protocol['bootstrap_draws']):
  blocks=rng.choices(seeds,k=len(seeds));vals.append(statistics.median([x['ratio'] for s in blocks for x in eligible if x['seed']==s]))
 vals.sort(); med=statistics.median(x['ratio'] for x in eligible); ci=[vals[int(.025*(len(vals)-1))],vals[int(.975*(len(vals)-1))]]
 assert eligible==timing['summary']['eligible'];assert med==timing['summary']['median_ratio'];assert ci==timing['summary']['seed_block_95_interval'];assert (len(eligible)>=10 and med<=.8)==timing['summary']['prespecified_speed_criterion_met']
 return {'eligible':len(eligible),'median_ratio':med,'seed_block_95_interval':ci,'prespecified_speed_criterion_met':len(eligible)>=10 and med<=.8}

official=check_timing('artifacts/verification')
report={'bootstrap_scalars_checked':checked,'maximum_abs_error':maximum_error,
 'certificate_timing_eligible':official['eligible'],'median_ratio':official['median_ratio'],
 'seed_block_95_interval':official['seed_block_95_interval'],
 'prespecified_speed_criterion_met':official['prespecified_speed_criterion_met'],
 'raw_row_counts':{'recorded':len(rows),'synthetic':len(r['synthetic']['rows']),'certificates':len(read('artifacts/verification/results.json')['rows'])},
 'initial_negative_run':check_timing('artifacts/verification/initial_run')}
files=['artifacts/benchmark/phase5/results.json','artifacts/verification/results.json','artifacts/verification/timings.json',
 'artifacts/verification/initial_run/results.json','artifacts/verification/initial_run/timings.json',
 'experiments/benchmark_protocol.json','experiments/certificate_benchmark.json']
report['source_artifacts']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
report['audit_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',type=Path);a=p.parse_args()
if a.verify and report!=json.loads(a.verify.read_text()):raise ValueError('INDEPENDENT_STATISTICS_MISMATCH')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'bootstrap_scalars_checked':checked,'maximum_abs_error':maximum_error,'official_speed_criterion':official['prespecified_speed_criterion_met'],'initial_speed_criterion':report['initial_negative_run']['prespecified_speed_criterion_met']}))
