"""Independent read-only challenge of actual CI outputs; no experiment adapters."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import json

from deviation.data.pipeline import digest
from deviation_research.records import sha, source_hash
from deviation.verification.checker import source_sha
from deviation_research.review import review
from deviation_research_replay.provenance import historical_review, HISTORICAL_ENGINE_SHA
from deviation_research_replay.bridge import _compare_result, _compare_events

ROOT=Path('/tmp/harness-rebase-independent')
EVIDENCE=ROOT/'evidence/research-rebase'
read=lambda p:json.loads(p.read_text())
manifest=read(ROOT/'expected-manifest.json')
comparison=read(ROOT/'comparison.json')
assert source_sha()==manifest['current_engine_source_sha256']
assert source_hash()==manifest['harness_source_sha256']
old,new=[read(EVIDENCE/f/'summary.json') for f in ('historical','current')]
mapping={HISTORICAL_ENGINE_SHA:source_sha(),old['preregistration_sha256']:new['preregistration_sha256'],old['sha256']:new['sha256']}
current_by_id={}
with patch('deviation.attacks.certified.solver.solve',side_effect=AssertionError('producer optimizer disabled')), \
     patch('deviation.attacks.game.Game.expected',side_effect=AssertionError('producer payoff disabled')), \
     patch('deviation.attacks.game.Game.allocation',side_effect=AssertionError('producer allocation disabled')):
    for a,b in zip(old['records'],new['records']):
        assert a['id']==b['id'] and a['key']==b['key']
        before,after=EVIDENCE/'historical'/a['key'],EVIDENCE/'current'/b['key']
        plan=read(before/'plan.json')
        prior,current=read(before/'result.json'),read(after/'result.json')
        assert sha(prior)==a['result_sha256'] and sha(current)==b['result_sha256']
        assert historical_review(dict(plan=plan,result=prior))==read(before/'review.json')
        actual=review(dict(plan=plan,result=current))
        assert actual==read(after/'review.json')==b['review']
        _compare_result(prior,current,HISTORICAL_ENGINE_SHA,source_sha())
        mapping[sha(prior)]=sha(current)
        current_by_id[b['id']]=(plan,prior,current)
        for folder,engine in ((before,HISTORICAL_ENGINE_SHA),(after,source_sha())):
            for receipt in read(folder/'resources.json').values():
                assert receipt['engine_source_sha256']==engine
                assert receipt['harness_source_sha256']==source_hash()
                assert receipt['wall_seconds']<=35 and 0<receipt['worker_cpu_seconds']<=25
                assert 0<receipt['worker_peak_rss_kib']<=768*1024
assert mapping==comparison['verified_derived_digest_map']

plan,prior,current=current_by_id['fees']
rejected=0
for field in ('scope','incumbent_commands','nodes'):
    forged=deepcopy(current)
    cert=next(r['certificate'] for r in forged['rows'] if 'certificate' in r)
    if field=='scope':cert['scope']='FORGED_SCOPE'
    elif field=='incumbent_commands':cert[field].append({'forged':True})
    else:cert[field].append(deepcopy(cert[field][0]))
    cert['sha256']=digest({k:v for k,v in cert.items() if k!='sha256'})
    try:_compare_result(prior,forged,HISTORICAL_ENGINE_SHA,source_sha())
    except ValueError:rejected+=1
    else:raise AssertionError(field+' escaped narrow comparison')
    try:review(dict(plan=plan,result=forged))
    except ValueError:rejected+=1
    else:raise AssertionError(field+' escaped independent numerical review')
events=[]
for folder in ('historical','current'):
    events.append([json.loads(line) for line in (EVIDENCE/folder/'events.jsonl').read_text().splitlines()])
_compare_events(*events,mapping)
forged=deepcopy(events[1]);forged[20]['parents'].append('f'*64)
previous=None
for event in forged:
    event['previous_sha256']=previous
    event['sha256']=sha({k:v for k,v in event.items() if k!='sha256'})
    previous=event['sha256']
try:_compare_events(events[0],forged,mapping)
except ValueError:rejected+=1
else:raise AssertionError('rehashed changed event parent escaped')
print(json.dumps({'all_four_historical_and_current_reviews':'PASS','producer_functions':'DISABLED',
                  'source_and_all_resource_bindings':'PASS','derived_digest_map':'INDEPENDENTLY_RECOMPUTED',
                  'additional_forgery_rejections':rejected,'event_count':len(events[0]),
                  'findings':comparison['findings']},indent=2))
