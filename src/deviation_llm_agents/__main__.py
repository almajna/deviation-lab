"""No dataset/holdout loading. Live model calls require an explicit subcommand."""
import argparse
import json
from pathlib import Path

from .experiments import campaign, scenario, write_json
from .harness import Budget, LocalPolicy, replay_episode, run_episode
from .local import OllamaLocal
from .availability import inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    controls = sub.add_parser("controls"); controls.add_argument("--out", required=True)
    probe = sub.add_parser("inventory"); probe.add_argument("--out", required=True)
    replay = sub.add_parser("replay"); replay.add_argument("sidecar"); replay.add_argument("--out", required=True)
    live = sub.add_parser("live")
    live.add_argument("--model-manifest", required=True)
    live.add_argument("--out", required=True)
    live.add_argument("--seed", type=int, default=7)
    live.add_argument("--signal", choices=["a_high", "b_high"], default="a_high")
    live.add_argument("--benefit", type=int, choices=[0, 20, 200], default=0)
    live.add_argument("--fee", type=int, choices=[0, 2], default=0)
    live.add_argument("--mechanism", choices=["lmsr", "pool", "cheapest"], default="lmsr")
    live.add_argument("--mode", choices=["truthful", "utility"], default="utility")
    live.add_argument("--max-calls", type=int, default=4)
    args = parser.parse_args()
    if args.command == "controls":
        write_json(args.out, campaign()); return
    if args.command == "inventory":
        write_json(args.out, inventory()); return
    if args.command == "replay":
        bundle = json.loads(Path(args.sidecar).read_text())
        write_json(args.out, replay_episode(bundle["scenario"], bundle["sidecar"])); return
    s = scenario(args.seed, args.signal, args.benefit, args.fee)
    try:
        backend = OllamaLocal(json.loads(Path(args.model_manifest).read_text()))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        write_json(args.out, {"version": "llm-preflight-1", "status": "BLOCKED_BEFORE_INFERENCE",
            "inference_calls_attempted": 0, "valid_llm_decisions": 0,
            "error_type": type(exc).__name__,
            "error_code": str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else "PREFLIGHT_FAILED"})
        raise SystemExit(2)
    policy = LocalPolicy(backend, Budget(max_calls=args.max_calls), seed=args.seed, mode=args.mode)
    sidecar = run_episode(s, "focal", policy, args.mechanism)
    write_json(args.out, {"scenario": s, "sidecar": sidecar})


if __name__ == "__main__": main()
