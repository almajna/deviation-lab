"""Offline engineering CLI. JSON inputs only; no code loading or downloads."""
import argparse
import json
from pathlib import Path
from .runner import run, replay, write_bundle


def main():
    parser = argparse.ArgumentParser(description="DEVIATION v0.2 exploratory simulator; no final evaluation")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify", type=Path, help="Re-execute and compare a prior receipts.json")
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    if scenario.get("data_kind") != "SYNTHETIC":
        parser.error("this engineering CLI permits SYNTHETIC scenarios only; no empirical/final runs")
    result = replay(scenario, json.loads(args.verify.read_text())) if args.verify else run(scenario)
    write_bundle(result, args.out)
    print(f"SYNTHETIC v0.2 replay {result['sha256']}; {len(result['trace']['events'])} events")


if __name__ == "__main__":
    main()
