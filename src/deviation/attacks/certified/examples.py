"""Small exact checks and bounded larger fixtures, never holdout experiments."""
from fractions import Fraction
from pathlib import Path
import json
from time import perf_counter

from deviation.attacks.environments import environment
from deviation.attacks.game import prepare_game
from deviation.attacks.search import reference, search
from deviation.attacks.evidence import execute
from deviation.attacks.verify import recompute
from deviation.data.pipeline import digest
from .checker import verify
from .model import payoff, rat, upper_bound
from .solver import solve


def dumps(value):
    return json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n'


def run_examples(out, *, verify_dir=None):
    """All declared fixtures retained; work counters are not equal time budgets."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[];timings=[];files={}
    profiles=[('small',{'fee':2},7,100),('two-slot',{'fee':2},17,100),
              ('zero-external',{'fee':2,'external':0},7,100),
              ('larger',{'aliases':3,'rounds':2,'quantity':3,'capital':24},17,2)]
    for name,profile,seed,expansions in profiles:
        for mechanism in (['lmsr','interactive-pool','pool'] if name=='small' else ['lmsr']):
            case=name+'-'+mechanism
            s,world,model=environment(profile,seed,realization_seed=12345+seed)
            kwargs=dict(scope='reports',public_report_model=model) if mechanism=='pool' else {}
            g=prepare_game(s,'strategic',mechanism,**kwargs)
            started=perf_counter();c=solve(g,max_expansions=expansions)
            solve_seconds=perf_counter()-started
            started=perf_counter();checked=verify(g,c)
            verify_seconds=perf_counter()-started
            # Ordinary beam uses an explicit, separately reported transition cap.
            beam_cap=max(1,c['search']['generated']-1)
            started=perf_counter();beam=search(g,method='beam',max_nodes=beam_cap,beam_width=2,seed=0)
            beam_seconds=perf_counter()-started
            exact=None
            if name!='larger':
                started=perf_counter();exact=search(g,max_nodes=20_000)
                exact_seconds=perf_counter()-started
                assert exact['selected']['utility']==c['lower']==c['upper']
            else:
                exact_seconds=None
            honest,hcommands=reference(g,'signal_following')
            noop,ncommands=reference(g,'no_action')
            rows.append(dict(case=case,data_kind='SYNTHETIC',scope=g.scope,
                remaining_slots=1 if g.scope=='reports' else len(g.engine.schedule)-g.engine.turn,
                certified={k:c[k] for k in ['lower','upper','gap','claim','search']},
                checker_nodes=checked['checked_nodes'],
                ordinary_beam=dict(lower=beam['selected']['utility'],upper=None,
                                   visited_nodes=beam['visited_nodes'],transition_cap=beam_cap,beam_width=2),
                ordinary_exact=None if exact is None else dict(lower=exact['selected']['utility'],visited_nodes=exact['visited_nodes']),
                root_endpoint_upper=rat(upper_bound(g)),root_lipschitz_upper=rat(upper_bound(g,vector_limit=0)),
                gain_vs_honest=rat(Fraction(*c['lower'])-payoff(honest)['utility']),
                gain_vs_noop=rat(Fraction(*c['lower'])-payoff(noop)['utility']),
                certificate_sha256=c['sha256']))
            files[case+'.certificate.json']=c
            timings.append(dict(case=case,solve_seconds=solve_seconds,verify_seconds=verify_seconds,
                                beam_seconds=beam_seconds,exact_seconds=exact_seconds))
            if case=='small-lmsr':
                files['scenario.json']=s
                selected=execute(s,'lmsr',c['incumbent_commands'])
                reference_receipt=execute(s,'lmsr',hcommands)
                files['selected.receipt.json']=selected
                files['honest.receipt.json']=reference_receipt
                files['independent-payoffs.json']=dict(selected=recompute(selected,'strategic',g.beliefs),
                                                     honest=recompute(reference_receipt,'strategic',g.beliefs))
    summary=dict(version='certified-examples-1',data_kind='SYNTHETIC',cases=rows,
                 interpretation='Implementation fixtures; known economic failure, no empirical or novelty claim.',
                 comparison='State expansions, transitions and wall time differ; no general speedup claim.')
    summary['sha256']=digest(summary)
    files['summary.json']=summary
    for name,value in files.items():
        data=dumps(value)
        if verify_dir is not None and data != (Path(verify_dir)/name).read_text():
            raise ValueError('Example replay mismatch: '+name)
        (out/name).write_text(data)
    # Timing is deliberately outside deterministic evidence and --verify output.
    return summary,timings
