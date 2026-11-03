"""Derive all six pilot rows from replay-verified receipts; no model imports/calls."""
import argparse
from collections import Counter
import csv
from fractions import Fraction
import json
from pathlib import Path

from deviation_llm_agents.pilot import verify_pilot


def summarize(bundle):
    replay = verify_pilot(bundle)
    rows = []
    for episode in bundle["episodes"]:
        sidecar = episode["sidecar"]
        records = sidecar["audit"]["records"]
        statuses = Counter(r["status"] for r in records)
        m = sidecar["metrics"]
        baseline = episode["scripted_controls"]["lmsr/signal"]["metrics"]
        gain = Fraction(*m["expected_utility"]) - Fraction(*baseline["expected_utility"])
        returned = [r for r in records if r["usage"] is not None and "generation_evidence" in r]
        rows.append({**episode["setting"], "calls_attempted": sidecar["live_calls_attempted"],
            "completed_inference_calls": len(returned), "valid_model_decisions": sidecar["model_valid_decisions"],
            "failed_decisions": statuses["FAILED_DECISION"],
            "skipped_no_inference": sum(not r["attempted"] for r in records),
            "model_chosen_noop": sum(r["status"] == "VALID_MODEL_DECISION" and r["action"] is not None
                and r["action"]["kind"] == "no_op" for r in records),
            "harness_fallback_decisions": sum(not r["status"].startswith("VALID_") for r in records),
            "generated_tokens": sum(r["usage"]["eval_count"] for r in returned),
            "prompt_tokens": sum(r["usage"]["prompt_eval_count"] for r in returned),
            "exact_signal_reports": m["exact_signal_reports"], "report_count": m["report_count"],
            "report_l1_counts": m["report_l1_counts"] if m["report_count"] else None,
            "focal_trades": m["accepted_trades"],
            "system_trades": m["system_accepted_trades"], "allocation": m["allocation"],
            "cash_delta": m["realized_cash"], "external_benefit": m["external_benefit"],
            "effort": m["effort"], "realized_utility": m["realized_utility"],
            "expected_utility": m["expected_utility"], "expected_gain_vs_signal": [gain.numerator, gain.denominator],
            "rerouted_vs_signal": m["allocation"] != baseline["allocation"]})
    return {"version": "llm-pilot-summary-1", "source_pilot_sha256": bundle["sha256"],
        "new_inference_calls": 0, "replay": replay, "rows": rows,
        "totals": {k: sum(r[k] for r in rows) for k in ["calls_attempted", "completed_inference_calls",
            "valid_model_decisions", "failed_decisions", "skipped_no_inference", "generated_tokens", "prompt_tokens"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input"); parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = Path(args.out); output.mkdir(parents=True, exist_ok=True)
    result = summarize(json.loads(Path(args.input).read_text()))
    (output / "real_pilot_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with (output / "real_pilot_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["rows"][0])); writer.writeheader(); writer.writerows(result["rows"])


if __name__ == "__main__": main()
