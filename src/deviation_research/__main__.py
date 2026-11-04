import argparse
import json
from pathlib import Path

from .records import Memory


def main():
    p = argparse.ArgumentParser(description="Bounded DEVIATION research; zero inference, synthetic development only")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("cycle")
    c.add_argument("--plan", default="research/plan.json")
    c.add_argument("--sources", default="research/sources.json")
    c.add_argument("--memory", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--scout-receipt", default=None)
    c.add_argument("--online", action="store_true", help="Run the bounded scout before the cycle; otherwise replay captured metadata")
    s = sub.add_parser("scout")
    s.add_argument("--out", required=True)
    s.add_argument("--max-requests", type=int, default=12)
    s.add_argument("--wall-seconds", type=float, default=65)
    e = sub.add_parser("export")
    e.add_argument("--memory", required=True); e.add_argument("--out", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("--memory", required=True)
    r = sub.add_parser("reproduce")
    r.add_argument("--evidence", required=True); r.add_argument("--out", required=True)
    args = p.parse_args()
    if args.command == "scout":
        from .scout import scout
        result = scout(args.out, max_requests=args.max_requests, wall_seconds=args.wall_seconds)
        print(json.dumps({"requests": len(result["requests"]), "ok": sum(r["status"] == "ok" for r in result["requests"])}))
    elif args.command == "cycle":
        from .orchestrator import cycle
        result = cycle(args.plan, args.sources, args.memory, args.out, scout_path=args.scout_receipt, online=args.online)
        print(json.dumps({"records": [{"id": r["id"], "status": r["status"]} for r in result["records"]]}))
        if any(r["status"] == "failed" for r in result["records"]):
            raise SystemExit(1)
    elif args.command == "reproduce":
        from .orchestrator import cycle
        out = Path(args.out)
        if out.exists():
            raise ValueError("reproduction destination must be fresh")
        evidence = Path(args.evidence)
        result = cycle(evidence/"inputs.plan.json", evidence/"inputs.sources.json", out/"memory.sqlite", out, scout_path=evidence/"scout.json")
        expected = json.loads((Path(args.evidence)/"summary.json").read_text())
        if result != expected:
            raise ValueError("scientific evidence reproduction mismatch")
        for r in result["records"]:
            for name in ("plan.json", "result.json", "review.json"):
                if (out/r["key"]/name).read_bytes() != (Path(args.evidence)/r["key"]/name).read_bytes():
                    raise ValueError("artifact mismatch: "+name)
        if (out/"events.jsonl").read_bytes() != (Path(args.evidence)/"events.jsonl").read_bytes():
            raise ValueError("event replay mismatch")
        print("Every scientific result, review and research event reproduced byte-for-byte")
    else:
        memory = Memory(args.memory)
        try:
            if args.command == "inspect":
                print(json.dumps(memory.inspect(), sort_keys=True, indent=2))
            else:
                memory.export(args.out)
        finally:
            memory.close()


if __name__ == "__main__":
    main()
