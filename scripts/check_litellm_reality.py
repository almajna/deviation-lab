"""Check offline routing receipts without importing LiteLLM or the runner."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean


def allocation_summary(rows):
    selected = []
    elapsed = []
    errors = 0
    for row in rows:
        endpoint = row.get("endpoint")
        if endpoint is not None:
            if endpoint["provider"] != row["provider"]:
                raise ValueError("PROVIDER_BINDING")
            if not row["error"] and row["response_id"] != endpoint["id"]:
                raise ValueError("RESPONSE_BINDING")
        elif not row["error"]:
            raise ValueError("MISSING_ENDPOINT")
        if row["phase"] != "measured":
            continue
        errors += bool(row["error"])
        if endpoint is not None:
            selected.append(endpoint["provider"])
        elapsed.append(row["client_seconds"])
    count = len(elapsed)
    return {"requests": count, "A": selected.count("A"), "B": selected.count("B"),
            "B_share": selected.count("B") / count if count else 0,
            "errors": errors, "mean_client_seconds": mean(elapsed) if elapsed else 0}


def check(bundle, config):
    expected = {(mode, condition, seed) for mode in config["primary_modes"]
                for condition in config["conditions"] for seed in config["seeds"]}
    expected |= {(mode, condition, config["diagnostic_seed"])
                 for mode in config["diagnostic_modes"] for condition in config["conditions"]}
    cases = bundle["cases"]
    actual = [(c["mode"], c["condition"], c["seed"]) for c in cases]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("CASE_COVERAGE")
    summaries = {}
    for case in cases:
        if case.get("failure"):
            raise ValueError("CASE_EXECUTION_FAILED")
        rows = case["rows"]
        if len(rows) != config["warmup_requests"] + config["measured_requests"]:
            raise ValueError("REQUEST_COVERAGE")
        if [r["phase"] for r in rows] != ["warmup"] * config["warmup_requests"] + ["measured"] * config["measured_requests"]:
            raise ValueError("PHASE_COVERAGE")
        for row in rows:
            endpoint = row.get("endpoint")
            if endpoint is None or endpoint["status"] != 200:
                continue
            raw, forwarded = endpoint["raw_usage"], endpoint["forwarded_usage"]
            for usage in (raw, forwarded):
                if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
                    raise ValueError("INCONSISTENT_USAGE")
            factor = config["inflation_factor"] if case["condition"] != "honest" and endpoint["provider"] == "B" else 1
            if raw["completion_tokens"] != case["actual_completion_tokens"] * factor:
                raise ValueError("PROVIDER_CONTROL")
            effective = 1 if case["condition"] == "defended" else factor
            if forwarded["completion_tokens"] != case["actual_completion_tokens"] * effective:
                raise ValueError("DEFENSE_CONTROL")
            if row["content_sha256"] != hashlib.sha256(config["response_text"].encode()).hexdigest():
                raise ValueError("CONTENT_CHANGED")
        summary = allocation_summary(rows)
        if case["summary"] != summary:
            raise ValueError("SUMMARY_MISMATCH")
        summaries[(case["mode"], case["condition"], case["seed"])] = summary
    primary = []
    controls = []
    for seed in config["seeds"]:
        honest = summaries[("latency", "honest", seed)]
        inflated = summaries[("latency", "inflated", seed)]
        defended = summaries[("latency", "defended", seed)]
        primary.append({"seed": seed, "B_share_gain": inflated["B_share"] - honest["B_share"],
                        "client_seconds_change": inflated["mean_client_seconds"] - honest["mean_client_seconds"]})
        controls.append(abs(defended["B_share"] - honest["B_share"]) <= config["control_allocation_difference_max"])
        for mode in ("shuffle", "stream"):
            base = summaries[(mode, "honest", seed)]["B_share"]
            controls.extend(abs(summaries[(mode, cond, seed)]["B_share"] - base) <= config["control_allocation_difference_max"]
                            for cond in ("inflated", "defended"))
    effect = all(p["B_share_gain"] >= config["primary_allocation_gain_min"] for p in primary)
    return {"allocation_effect": effect, "primary": primary, "comparative_controls_pass": all(controls),
            "cases_checked": len(cases), "requests_checked": sum(len(c["rows"]) for c in cases),
            "verdict": "INCONCLUSIVE_PENDING_SAFEGUARD_AND_SOURCE_REVIEW"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--config", type=Path, default=Path("experiments/litellm_reality_v1.json"))
    args = parser.parse_args()
    print(json.dumps(check(json.loads(args.evidence.read_text()), json.loads(args.config.read_text())), indent=2, sort_keys=True))
