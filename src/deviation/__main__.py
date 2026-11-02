"""Bootstrap CLI: python -m deviation demo [--out path]."""
import argparse
import json
from pathlib import Path
from .core import synthetic_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="DEVIATION synthetic reference CLI (not full research system)")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--out", type=Path, help="Write JSON trace to path; otherwise print to stdout")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    data = synthetic_demo(seed=args.seed)
    encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
        print(f"Wrote SYNTHETIC reference trace to {args.out}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
