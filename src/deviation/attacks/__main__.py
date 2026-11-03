"""JSON-only attack discovery/replay CLI; no arbitrary code execution."""
import argparse
import json
from pathlib import Path
from .campaign import run_campaign
from .evidence import discover,load_bundle,replay,write_bundle
from .sensitivity import sensitivity


def main():
    p=argparse.ArgumentParser(description="DEVIATION controlled synthetic adversarial laboratory")
    p.add_argument("command",choices=["discover","replay","campaign","sensitivity"])
    p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.command=="campaign":
        summary,selected=run_campaign(json.loads(args.input.read_text()),args.out)
        print(json.dumps(summary["counts"],sort_keys=True));return
    if args.command=="sensitivity":
        result=sensitivity(load_bundle(args.input));args.out.mkdir(parents=True,exist_ok=True)
        (args.out/"sensitivity.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(f"{len(result['cases'])} exploratory interventions");return
    if args.command=="replay":bundle=replay(load_bundle(args.input))
    else:
        request=json.loads(args.input.read_text())
        bundle=discover(request["scenario"],request["controller"],request["mechanism"],**request["options"])
    write_bundle(bundle,args.out)
    print(bundle["evidence"]["classification"],bundle["evidence"]["sha256"])


if __name__=="__main__":main()
