"""Independent mathematical checking and reproducible synthetic evaluation."""
import argparse
import json
from pathlib import Path

from .benchmark import run
from .checker import check
from .fixtures import fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=Path("experiments/certificate_benchmark.json"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--no-timings", action="store_true")
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--profile", default="base")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--mechanism", default="lmsr")
    parser.add_argument("--expected-source")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    if args.certificate:
        profile = next(p for p in protocol["profiles"] if p["id"] == args.profile)
        checked = check(fixture(profile, args.seed, args.mechanism), json.loads(args.certificate.read_text()),
                        expected_source_sha=args.expected_source)
        print(json.dumps(checked, sort_keys=True))
        return
    if args.out is None:
        parser.error("--out is required for a benchmark")
    result = run(protocol, args.out, measure=not args.no_timings)
    if args.verify and result != json.loads(args.verify.read_text()):
        raise ValueError("deterministic benchmark reproduction mismatch")
    print(json.dumps({"counts": result["counts"], "sha256": result["sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
