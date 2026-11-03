"""Synthetic-only engineering CLI; never loads policies or executes input code."""
import argparse
import json
from pathlib import Path
from .runner import MECHANISMS, run, replay, write_bundle


def main():
    p = argparse.ArgumentParser(description="DEVIATION v0.3 synthetic market engine")
    p.add_argument("scenario", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mechanism", choices=MECHANISMS, default="lmsr")
    p.add_argument("--verify", type=Path)
    args = p.parse_args()
    scenario = json.loads(args.scenario.read_text())
    result = replay(scenario, json.loads(args.verify.read_text())) if args.verify else run(scenario, args.mechanism)
    write_bundle(result, args.out)
    print(f"SYNTHETIC v0.3 {result['mechanism']} receipt {result['sha256']}; {len(result['trace']['events'])} events")


if __name__ == "__main__": main()
