"""$0 local solve/check/examples commands; Python >=3.11, stdlib only."""
import argparse
import json
from pathlib import Path

from deviation.attacks.game import prepare_game
from .checker import verify
from .solver import solve


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['solve','verify']:
        q=sub.add_parser(name)
        q.add_argument('scenario',type=Path)
        if name=='verify':q.add_argument('certificate',type=Path)
        q.add_argument('--controller',default='strategic')
        q.add_argument('--mechanism',default='lmsr')
        q.add_argument('--scope',choices=['terminal','reports'],default='terminal')
        q.add_argument('--public-reports',type=Path)
        if name=='solve':
            q.add_argument('--out',type=Path,required=True)
            q.add_argument('--max-expansions',type=int,default=1000)
            q.add_argument('--vector-limit',type=int,default=5000)
    q=sub.add_parser('examples')
    q.add_argument('--out',type=Path,required=True)
    q.add_argument('--verify',type=Path)
    q.add_argument('--timings',type=Path)
    args=p.parse_args()
    if args.command=='examples':
        from .examples import dumps,run_examples
        summary,timings=run_examples(args.out,verify_dir=args.verify)
        if args.timings:args.timings.write_text(dumps(timings))
        print(json.dumps({'cases':len(summary['cases']),'sha256':summary['sha256']},sort_keys=True))
        return
    scenario=json.loads(args.scenario.read_text())
    reports=json.loads(args.public_reports.read_text()) if args.public_reports else None
    g=prepare_game(scenario,args.controller,args.mechanism,scope=args.scope,public_report_model=reports)
    if args.command=='verify':
        result=verify(g,json.loads(args.certificate.read_text()))
    else:
        result=solve(g,max_expansions=args.max_expansions,vector_limit=args.vector_limit)
        verify(g,result)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['claim','lower','upper','gap']},sort_keys=True))


if __name__=='__main__':main()
