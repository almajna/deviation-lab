#!/usr/bin/env python3
"""Prespecified retrospective AgentOps acquisition audit; stdlib only."""
import hashlib
import json
import math
import random
import statistics
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

def digest(*parts):
    return hashlib.sha256('|'.join(str(x) for x in parts).encode()).digest()

def parse_report(obj, rows, condition_counts=None):
    if not isinstance(obj, dict) or not isinstance(obj.get('results'), list):
        raise ValueError('invalid report')
    report_agent=obj.get('agent_id')
    if not isinstance(report_agent,str) or not report_agent:
        raise ValueError('invalid report agent ID')
    if condition_counts is None: condition_counts=Counter()
    for r in obj['results']:
        if not isinstance(r,dict) or r.get('agent_id') != report_agent:
            raise ValueError('report/result agent ID mismatch')
        condition=r.get('condition')
        if condition not in ('clean','noisy','adversarial'):
            raise ValueError('unknown or missing condition')
        condition_counts[condition]+=1
        if condition != 'clean':
            continue
        try:
            task, agent, run = r['task_id'], r['agent_id'], r['run_number']
            if not isinstance(task,str) or not task or not isinstance(agent,str) or not agent:
                raise ValueError('bad IDs')
            if not isinstance(run,int) or isinstance(run,bool):
                raise ValueError('bad run number')
            completion = float(r['scores']['completion'])
            cost = float(r['scores']['cost']['cost_usd'])
        except (KeyError, TypeError, ValueError):
            raise ValueError('invalid clean record') from None
        if not math.isfinite(completion) or not 0 <= completion <= 1 or not math.isfinite(cost) or cost < 0:
            raise ValueError('invalid score or cost')
        key = (task,agent,run)
        if key in rows:
            raise ValueError('duplicate clean task/agent/run')
        rows[key] = (completion,cost)

def load_archive(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            buf=f.read(1024*1024)
            if not buf: break
            h.update(buf)
    rows={}; members=[]; reports=0; size=0; condition_counts=Counter()
    with tarfile.open(path,'r:gz') as archive:
        for m in archive:
            name=PurePosixPath(m.name)
            if name.is_absolute() or '..' in name.parts or m.issym() or m.islnk():
                raise ValueError('unsafe archive member')
            if not (m.isfile() or m.isdir()):
                raise ValueError('unsupported archive member')
            if m.size < 0 or m.size > 50_000_000:
                raise ValueError('archive member too large')
            size += m.size
            if size > 350_000_000 or len(members) >= 15000:
                raise ValueError('archive bounds exceeded')
            members.append({'name':m.name,'size':m.size,'type':'file' if m.isfile() else 'directory'})
            # Ignore optional duplicate _combined copies; read per-agent reports only.
            if m.isfile() and name.name.endswith('_report.json') and '_combined' not in name.parts:
                stream=archive.extractfile(m)
                if stream is None: raise ValueError('failed report read')
                try: data=json.load(stream)
                except (ValueError,UnicodeError): raise ValueError('invalid report JSON') from None
                parse_report(data,rows,condition_counts); reports+=1
    tasks=sorted({t for t,a,r in rows}); agents=sorted({a for t,a,r in rows})
    if reports != 8 or len(tasks)!=100 or len(agents)!=8 or len(rows)!=2400:
        raise ValueError('expected exactly 8 reports and full 100x8x3 clean matrix')
    for t in tasks:
        for a in agents:
            if len([r for tt,aa,r in rows if tt==t and aa==a])!=3:
                raise ValueError('incomplete task/agent repeat cell')
    return rows,tasks,agents,h.hexdigest(),members,condition_counts

def select(observations, agents, lo, hi, task, policy):
    # No held-back records are passed to this function.
    histories={a:[observations[a][0]] for a in agents}
    def value(x): return x[0]-0.05*(x[1]-lo)/(hi-lo)
    def rank(group):
        return sorted(group,key=lambda a:(-statistics.mean(value(x) for x in histories[a]),a))
    if policy=='adaptive':
        extra=rank(agents)[:4]
    elif policy=='uniform':
        extra=sorted(agents,key=lambda a:(digest('AOB-UNIFORM-V1',task,a),a))[:4]
    else: raise ValueError('unknown policy')
    for a in extra: histories[a].append(observations[a][1])
    selected=rank(agents)[0]
    assert sum(len(x) for x in histories.values())==12
    spent=sum(x[1] for history in histories.values() for x in history)
    final=[statistics.mean(value(x) for x in histories[a]) for a in agents]
    return selected,spent,Counter(final)[max(final)]>1

def aggregate(rows,tasks,agents,source_sha):
    ordered=sorted(tasks,key=lambda t:(digest('AOB-QUERY-V1',t),t))
    development,evaluation=ordered[:50],ordered[50:]
    devcost=[c for (t,a,r),(s,c) in rows.items() if t in set(development)]
    lo,hi=min(devcost),max(devcost)
    if hi <= lo: raise ValueError('development cost range must be positive')
    def value(x): return x[0]-0.05*(x[1]-lo)/(hi-lo)
    output={p:{'utility':[],'completion':[],'cost':[],'selection':Counter(),
               'agreement':0,'final_max_ties':0} for p in ('adaptive','uniform')}
    delta=[]; outside=0
    for t in evaluation:
        pools={}; heldkeys={}
        for a in agents:
            nums=sorted((r for tt,aa,r in rows if tt==t and aa==a),
                       key=lambda r:(digest('AOB-REPEAT-V1',t,a,r),r))
            pools[a]=[rows[(t,a,r)] for r in nums[:2]]
            heldkeys[a]=(t,a,nums[2])
        # Lock both decisions before any reference outcomes are retrieved.
        decisions={p:select(pools,agents,lo,hi,t,p) for p in ('adaptive','uniform')}
        held={a:rows[key] for a,key in heldkeys.items()}
        for a in agents:
            outside += held[a][1]<lo or held[a][1]>hi
        oracle=sorted(agents,key=lambda a:(-value(held[a]),a))[0]
        for p in ('adaptive','uniform'):
            chosen,cost,tied=decisions[p]
            o=output[p]; o['selection'][chosen]+=1; o['agreement']+=int(chosen==oracle)
            o['utility'].append(value(held[chosen])); o['completion'].append(held[chosen][0])
            o['cost'].append(cost); o['final_max_ties']+=int(tied)
        delta.append(output['adaptive']['utility'][-1]-output['uniform']['utility'][-1])
    rng=random.Random(26061105)
    boot=sorted(statistics.mean(delta[rng.randrange(50)] for _ in range(50)) for _ in range(5000))
    return {'source_sha256':source_sha,'development_queries':len(development),
            'evaluation_queries':len(evaluation),'development_min_cost':lo,
            'development_max_cost':hi,'heldback_costs_outside_development_range':outside,
            'calls_per_policy_per_query':12,
            'policies':{p:{'mean_heldback_utility':statistics.mean(o['utility']),
                           'mean_heldback_completion':statistics.mean(o['completion']),
                           'total_observed_acquisition_cost_usd':sum(o['cost']),
                           'oracle_agreement':o['agreement'],'final_max_ties':o['final_max_ties'],
                           'agent_selections':dict(o['selection'])} for p,o in output.items()},
            'paired_utility_difference':{'mean':statistics.mean(delta),'median':statistics.median(delta),
                'positive':sum(x>0 for x in delta),'negative':sum(x<0 for x in delta),
                'zero':sum(x==0 for x in delta),'bootstrap_95_percentile':[boot[124],boot[4874]]}}

if __name__=='__main__':
    if len(sys.argv)!=4: raise SystemExit('usage: audit.py INPUT.tar.gz RESULTS.json MEMBERS.json')
    rows,tasks,agents,checksum,members,condition_counts=load_archive(sys.argv[1])
    result=aggregate(rows,tasks,agents,checksum)
    result['condition_counts_in_reports']=dict(condition_counts)
    Path(sys.argv[2]).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    Path(sys.argv[3]).write_text(json.dumps(members,indent=2,sort_keys=True)+'\n')
