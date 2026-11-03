"""Nature draws outcomes and observations; posterior() never accepts labels."""
from copy import deepcopy
from fractions import Fraction
import random
from deviation.contracts import prompt_group
from deviation.data.pipeline import digest
from deviation.markets.engine import market_id
from deviation.markets.numeric import project_rational
from deviation.simulator.reservations import fit_reservations


def posterior(observation, prior, accuracy, D):
    a=Fraction(*accuracy)
    if not 0<a<1 or observation not in range(3):raise ValueError('INVALID_SIGNAL_CHANNEL')
    return project_rational([Fraction(n,sum(prior))*(a if y==observation else (1-a)/2)
                             for y,n in enumerate(prior)],D)


def economics(D=6, *, b=2, fee=0, order_limit=3):
    return {'b':b,'report_denominator':D,'score_scale':1,'price_denominator':30000,'fee':fee,
        'order_limit':order_limit,'agent_position_limit':8,'cell_position_limit':1000,'action_limit':100000,
        'candidate_limit':100,'rounds':1,'sponsor_cap':10000000}


def controller(cash, tokens, slots, weights=None):
    return {'cash_cap':cash,'token_cap':tokens,'action_cap':slots,'position_cap':8,
            'external_weights':weights or {},'effort_per_attempt':0}


def synthetic(profile, nature_seed, *, schedule_seed=41):
    """Seed is a trusted nature parameter, never part of returned public state."""
    rng=random.Random(nature_seed);yrng=random.Random(nature_seed+701);N=profile['tasks'];D=profile['D'];models=['m0','m1']
    tasks=[{'task_id':f'task-{i}','prompt':f'Synthetic decision {i}','model_options':models} for i in range(N)]
    mids=sorted(market_id(t['task_id'],m) for t in tasks for m in models);C=len(mids)
    observations={a:{} for a in ['h0','h1','z0','z1']};sealed=[];priors={}
    a=Fraction(*profile['accuracy']);rho=Fraction(*profile['correlation'])
    for i,t in enumerate(tasks):
        for j,m in enumerate(models):
            prior=[3,2,1] if (i+j)%2==0 else [1,2,3]
            mid=market_id(t['task_id'],m);priors[mid]=prior
            y=yrng.choices(range(3),weights=prior)[0]
            likelihood=[a if x==y else (1-a)/2 for x in range(3)]
            common=rng.choices(range(3),weights=likelihood)[0]
            shared=rng.random()<rho
            for actor in ['h0','h1','z0']:
                independent=rng.choices(range(3),weights=likelihood)[0]
                x=common if shared else independent
                observations[actor][mid]=posterior(x,prior,profile['accuracy'],D)
            observations['z1'][mid]=list(observations['z0'][mid])
            sealed.append({'task_id':t['task_id'],'model_id':m,'quality':y/2,'cost_decimal':f'{j+1}E-9'})
    agents={a:{'controller':a if a.startswith('h') else 'strategic',
        'wallet':12 if a.startswith('h') else 0,'signals':observations[a],'decline_report':False} for a in observations}
    total=profile['capital'];aliases=profile['active_aliases']
    if aliases not in (1,2):raise ValueError('FIXED_REGISTRY_ALIASES_ONLY')
    agents['z0']['wallet']=total if aliases==1 else (total+1)//2
    agents['z1']['wallet']=0 if aliases==1 else total//2
    schedule=[]
    for h in ['h0','h1']:schedule.extend([[h,m] for m in mids])
    schedule.extend([['z0' if aliases==1 or i%2==0 else 'z1',m] for i,m in enumerate(mids)])
    random.Random(schedule_seed).shuffle(schedule)
    controllers={h:controller(12,C,C) for h in ['h0','h1']}
    controllers['strategic']=controller(total,2*C,C,{t['task_id']:{'m0':profile['external']} for t in tasks})
    groups={prompt_group(t['prompt']):'validation' for t in tasks};training=[]
    for i in range(4):
        prompt=f'Synthetic training {i}';groups[prompt_group(prompt)]='train'
        for j,m in enumerate(models):training.append({'task_id':f'train-{i}','prompt':prompt,'model_id':m,'cost_decimal':f'{j+1}E-9','cost_unit':'synthetic_units'})
    source=digest(['likelihood-world-1',profile])
    artifact=fit_reservations(training,groups,tasks,source_manifest_sha256=source,
        split_manifest_sha256=digest(groups))
    public={'tasks':tasks,'artifact':artifact,'economics':economics(D,b=profile['b'],fee=profile['fee'],order_limit=profile['order_limit']),
        'agents':agents,'controllers':controllers,'schedule':schedule,'budget':N*3//2,
        'temperature':'1','training_means':{'m0':.5,'m1':.5},'data_kind':'SYNTHETIC',
        'source_sha256':source,'split_sha256':digest(groups),'seed':schedule_seed}
    return public,sealed,{'priors':priors,'channel':{'accuracy':profile['accuracy'],'correlation':profile['correlation']}}


def remove_external(public):
    p=deepcopy(public)
    for c in p['controllers'].values():
        for row in c['external_weights'].values():
            for m in row:row[m]=0
    return p


def normalized_resources(public):
    """Exclude intentional account/slot partition, retain total resources."""
    p=public;members=[a for a,s in p['agents'].items() if s['controller']=='strategic']
    c=p['controllers']['strategic']
    return {'registry':sorted(p['agents']),'total_cash':sum(p['agents'][a]['wallet'] for a in members),
        'controller_caps':{k:v for k,v in c.items() if k!='external_weights'},
        'controller_slot_cells':sorted(mid for a,mid in p['schedule'] if a in members),
        'honest_slots':sorted([a,mid] for a,mid in p['schedule'] if a not in members),
        'private_information':{a:p['agents'][a]['signals'] for a in p['agents']},
        'economics':p['economics'],'budget':p['budget'],
        'report_tokens':len(p['agents'])*sum(len(t['model_options']) for t in p['tasks'])}
