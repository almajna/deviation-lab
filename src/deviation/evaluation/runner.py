"""Actual economic engine with explicit post-lock outcome-provider boundary.

New benchmark sidecars do not relabel synthetic Phase 3 runner receipts. This
runner uses the same Engine, pricing, funded scores and budget validators.
"""
from copy import deepcopy
from fractions import Fraction
from deviation.contracts import validate_allocation
from deviation.data.pipeline import digest
from deviation.markets.engine import Engine, market_id
from deviation.markets.numeric import prices, transform
from deviation.markets.contracts import mean
from deviation.markets.policies import pooled
from deviation.markets.runner import packet, allowed_actions, allocation_config, summary
from deviation.simulator.policies import optimize, ReferenceAllocator
from deviation.simulator.runner import _selected_report, implementation_sha256
from .policies import policy


def audit_events(events, initial, final):
    """Independent ledger, proper-score and long-only claim verification."""
    balances=deepcopy(initial);seen=set();positions={}
    for i,e in enumerate(events):
        if e['seq']!=i:raise ValueError('EVENT_SEQUENCE')
        p=e['payload']
        if e['type']=='ledger_transfer':
            if p['transfer_id'] in seen:raise ValueError('DUPLICATE_TRANSFER')
            seen.add(p['transfer_id']);balances[p['payer']]-=p['amount'];balances[p['payee']]+=p['amount']
            if min(balances.values())<0:raise ValueError('UNFUNDED_TRANSFER')
        elif e['type']=='trade_accepted':
            key=p['actor'],p['market_id'];old=positions.get(key,[0,0,0])
            if old!=p['position_before']:raise ValueError('POSITION_DISAGREEMENT')
            after=[x+y for x,y in zip(old,p['share_delta'])]
            if after!=p['position_after'] or min(after)<0:raise ValueError('CLAIM_DISAGREEMENT')
            positions[key]=after
        elif e['type']=='market_settled':
            if any(n!=positions.get((a,p['market_id']),[0,0,0])[p['category']] for a,n in p['claims'].items()):raise ValueError('PAYOUT_DISAGREEMENT')
        elif e['type']=='score_settled':
            D=p['denominator'];expected=2*D*D-sum((n-D*int(k==p['category']))**2 for k,n in enumerate(p['counts']))
            if p['score']!=expected:raise ValueError('SCORE_DISAGREEMENT')
    if balances!=final or sum(final.values())!=sum(initial.values()):raise ValueError('CASH_CONSERVATION')
    return True


def execute(public, outcomes, mechanism, *, strategy=None, full_predictions=None, oracle_values=None, defer_settlement=False):
    """outcomes is a trusted callback; invoked for the first time after lock."""
    public=deepcopy(public)
    if set(public)!={'tasks','artifact','economics','agents','controllers','schedule','budget','temperature','training_means','data_kind','source_sha256','split_sha256','seed'}:
        raise ValueError('UNKNOWN_OR_HIDDEN_PUBLIC_FIELDS')
    if public['data_kind'] not in {'SYNTHETIC','RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS'}:raise ValueError('DATA_KIND')
    tasks=sorted(public['tasks'],key=lambda t:t['task_id']);artifact=public['artifact'];budget=public['budget']
    definitions={a:{'controller':s['controller'],'wallet':s['wallet']} for a,s in public['agents'].items()}
    e=Engine(tasks,public['economics'],definitions,public['controllers'],public['schedule'])
    s={'agents':public['agents'],'decision_tasks':tasks,'reservation_budget':budget}
    policies={a:policy(strategy if strategy and d['controller']=='strategic' else {'kind':'honest'}) for a,d in definitions.items()}
    for a,mid in sorted(e.tokens):
        p=packet(e,s,a,mid,mechanism,artifact);request=policies[a].act(p)
        e.commit(a,mid,None if request is None else request['counts'])
    e.reveal()
    while e.turn<len(e.schedule):
        a,mid=e.schedule[e.turn];p=packet(e,s,a,mid,mechanism,artifact)
        e.apply(policies[a].act(p),allowed_kinds=allowed_actions(mechanism))
    D=public['economics']['report_denominator'];P=public['economics']['price_denominator']
    values={t['task_id']:{} for t in tasks};distributions={}
    for t in tasks:
        for m in t['model_options']:
            mid=market_id(t['task_id'],m)
            if mechanism=='lmsr':dist=prices(e.books[mid]['q'],e.cfg['b'],P)
            elif mechanism=='text-router':dist=transform([Fraction(n,D) for n in full_predictions[t['task_id']][m]],'1',P)
            else:dist=transform(pooled(e.reports,mid,D),public['temperature'] if mechanism=='calibrated-pool' else '1',P)
            distributions[mid]=[Fraction(n,P) for n in dist]
            values[t['task_id']][m]=mean(dist,P)
    if mechanism in {'random','cheapest','best-fixed'}:
        plan=ReferenceAllocator(mechanism,seed=public['seed'],training_means=public['training_means']).allocate(tasks,[],artifact,budget)
    else:
        if oracle_values is not None:
            if mechanism!='oracle-analysis-only':raise ValueError('ORACLE_LEAKAGE')
            values=oracle_values
        elif mechanism=='oracle-analysis-only':raise ValueError('ORACLE_ANALYSIS_ONLY')
        plan={'schema_version':'0.2','reservation_artifact_sha256':artifact['artifact_sha256'],
            'cost_unit':artifact['cost_unit'],'reservation_budget':budget,
            'allocations':optimize(tasks,artifact['reservations'],budget,values)}
    validate_allocation(plan,artifact,tasks,run_config=allocation_config(budget,artifact['cost_unit']))
    encoded={t:{m:{'numerator':v.numerator,'denominator':v.denominator} for m,v in row.items()} for t,row in values.items()}
    e.lock(plan,encoded,artifact['artifact_sha256'])
    predecision_sha=digest(e.events)
    # No current outcome/cost access occurs above this barrier. Oracle analysis
    # is a separate explicitly privileged invocation after ordinary plans finish.
    def finish():
        sealed=deepcopy(outcomes())
        pairs={(t['task_id'],m) for t in tasks for m in t['model_options']}
        realized,evaluation=_selected_report(plan,sealed,pairs)
        categories={market_id(r['task_id'],r['model_id']):int(2*r['quality']) for r in sealed}
        if any(r['quality'] not in [0,.5,1] for r in sealed):raise ValueError('INVALID_CATEGORY')
        e.settle(categories);metrics=summary(e,plan,realized,evaluation);e.emit('economic_summary',metrics)
        audit_events(e.events,e.initial,e.balances)
        brier=sum(sum((p[k]-int(k==categories[mid]))**2 for k in range(3)) for mid,p in distributions.items())/len(distributions)
        squared=sum((sum(Fraction(k,2)*x for k,x in enumerate(p))-Fraction(categories[mid],2))**2 for mid,p in distributions.items())/len(distributions)
        bins=[{'count':0,'prediction_sum':0.,'outcome_sum':0.} for _ in range(5)]
        for mid,dist in distributions.items():
            v=sum(Fraction(k,2)*n for k,n in enumerate(dist));b=bins[min(4,int(5*v))]
            b['count']+=1;b['prediction_sum']+=float(v);b['outcome_sum']+=categories[mid]/2
        metrics['calibration_bins']=bins
        metrics['calibration_abs_error']=sum(abs(b['prediction_sum']-b['outcome_sum']) for b in bins)/len(distributions)
        bypair={(r['task_id'],r['model_id']):r['quality'] for r in sealed}
        chosen=[bypair.get((c['task_id'],c['model_id']),0) for c in plan['allocations']]
        metrics.update(trades=sum(event['type']=='trade_accepted' for event in e.events),
            updates=sum(event['type']=='distribution_updated' for event in e.events),
            noops=sum(event['type']=='action_noop' for event in e.events),brier=float(brier),proxy_squared_error=float(squared),task_count=len(tasks),
            tie_zero_quality=sum(0 if x==.5 else x for x in chosen)/len(tasks),
            tie_one_quality=sum(1 if x==.5 else x for x in chosen)/len(tasks),
            zero_as_one_quality=sum(1 if x==0 and c['model_id'] is not None else x for x,c in zip(chosen,plan['allocations']))/len(tasks),
            maker_initial_funding=sum(b['funding'] for b in e.books.values()),
            maker_cash_pnl=sum(e.balances[e.maker(mid)]-b['funding'] for mid,b in e.books.items()),
            optional_slots=len(e.schedule),registered_agents=len(e.agents))
        result={'version':'benchmark-episode-1','data_kind':public['data_kind'],'mechanism':mechanism,
            'implementation_sha256':implementation_sha256(),'public_sha256':digest(public),
            'predecision_sha256':predecision_sha,'allocation':plan,'metrics':metrics,
            'events':e.events,'resource_signature':digest({'agents':definitions,'controllers':public['controllers'],
                'schedule':e.schedule,'score_reserve':e.score_reserve,'maker_funding':metrics['maker_initial_funding'],
                'economics':e.cfg,'reservation_budget':budget,'artifact':artifact['artifact_sha256']})}
        result['sha256']=digest(result)
        return result
    return finish if defer_settlement else finish()
