"""Frozen, all-case independent certificate evaluation with no data downloads."""
from collections import defaultdict
from fractions import Fraction
import csv
import io
import json
from pathlib import Path
import platform
import random
from statistics import median
from time import perf_counter

from deviation.data.pipeline import digest
from .bounds import upper
from .checker import check, source_sha
from .domain import actions, advance, encoded, exact, fraction, payoff, terminal
from .fixtures import fixture

PROTOCOL_COMMIT = "d77e2cd6031b665c082a4412597bf564eab657d1"
PRODUCER_COMMIT = "3151edb463484498a5b686bf607dff4f062d66a4"


def dumps(v):
    return json.dumps(v, sort_keys=True, indent=2, allow_nan=False) + "\n"


def sample(call, repeats):
    result = call()  # Warm run also checks deterministic outputs on repeats.
    elapsed = []
    for _ in range(repeats):
        start = perf_counter()
        again = call()
        elapsed.append(perf_counter()-start)
        if again != result:
            raise ValueError("nondeterministic solver/check output")
    return result, elapsed


def no_action(g):
    child = g
    while not terminal(child):
        child = advance(child, next(actions(child)))
    return payoff(child)["utility"]


def interval_by_seed(items, draws, seed):
    """Descriptive paired bootstrap; related profile/mechanism rows stay together."""
    by_seed = defaultdict(list)
    for item in items:
        by_seed[item["seed"]].append(item["ratio"])
    seeds = sorted(by_seed)
    if not seeds:
        return None
    rng = random.Random(seed)
    values = sorted(median([r for s in rng.choices(seeds, k=len(seeds)) for r in by_seed[s]])
                    for _ in range(draws))
    return [values[int(0.025*(draws-1))], values[int(0.975*(draws-1))]]


def timing_summary(rows, timings, protocol):
    lookup = {r["case"]: r for r in rows}
    eligible = []
    for record in timings:
        row = lookup[record["case"]]
        candidates = [median(record[k]) for k in ["exhaustive", "dynamic_programming"]
                      if row[k]["status"] == "EXACT"]
        if candidates and row["root_actions"] >= 2 and row["certificate"]["gap"] == [0, 1]:
            ratio = (median(record["solve"])+median(record["check"]))/min(candidates)
            eligible.append({"case": row["case"], "seed": row["seed"], "ratio": ratio})
    ratios = [r["ratio"] for r in eligible]
    return {"eligible": eligible, "n": len(ratios), "median_ratio": median(ratios) if ratios else None,
            "seed_block_95_interval": interval_by_seed(eligible, protocol["bootstrap_draws"], protocol["bootstrap_seed"]),
            "prespecified_speed_criterion_met": len(ratios) >= 10 and median(ratios) <= 0.8,
            "interpretation": "Descriptive finite synthetic suite; only three seed blocks; no population inference."}


def run(protocol, destination, *, measure=True, progress=print):
    # Import producer only in driver, never checker/domain/bound implementation.
    from deviation.attacks.certified import solve
    from deviation.attacks.search import search
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=True)
    proofs = out/"proofs"
    proofs.mkdir(exist_ok=True)
    rows, timings, failures = [], [], []
    repeats = protocol["timing_repeats"] if measure else 0
    for profile in protocol["profiles"]:
        for seed in protocol["seeds"]:
            for mechanism in protocol["mechanisms"]:
                case = f"{profile['id']}-{seed}-{mechanism}"
                g = fixture(profile, seed, mechanism)
                c, solve_times = sample(lambda: solve(g, max_expansions=protocol["max_nodes"], vector_limit=5000), repeats)
                checked, check_times = sample(lambda: check(g, c), repeats)
                exhaustive, exhaustive_times = sample(lambda: exact(g, max_nodes=protocol["independent_max_nodes"]), repeats)
                dp, dp_times = sample(lambda: exact(g, max_nodes=protocol["independent_max_nodes"], memoize=True), repeats)
                beam, beam_times = sample(lambda: search(g, method="beam", max_nodes=protocol["max_nodes"],
                    beam_width=protocol["beam_width"], seed=seed), repeats)
                lower, bound = fraction(c["lower"]), fraction(c["upper"])
                for name, result in [("exhaustive", exhaustive), ("dynamic_programming", dp)]:
                    if result["status"] == "EXACT" and not lower <= fraction(result["utility"]) <= bound:
                        failures.append({"case": case, "comparator": name, "reason": "INCORRECT_CERTIFICATE_INTERVAL"})
                if exhaustive["status"] == dp["status"] == "EXACT" and exhaustive["utility"] != dp["utility"]:
                    failures.append({"case": case, "reason": "INDEPENDENT_BASELINES_DISAGREE"})
                if fraction(beam["selected"]["utility"]) > bound:
                    failures.append({"case": case, "reason": "BEAM_EXCEEDS_CERTIFIED_UPPER"})
                noop = no_action(g)
                row = {"case": case, "profile": profile["id"], "group": profile["group"], "seed": seed,
                    "mechanism": mechanism, "scope": g.scope,
                    "horizon": 1 if g.scope == "reports" else len(g.engine.schedule)-g.engine.turn,
                    "root_actions": len(list(actions(g))), "observation_sha256": digest(g.observation()),
                    "certificate": {k: c[k] for k in ["lower", "upper", "gap", "claim", "search", "sha256"]},
                    "proof_bytes": len(dumps(c).encode()), "independent_check": checked,
                    "root_endpoint_upper": encoded(upper(g, vector_limit=5000)),
                    "root_fallback_upper": encoded(upper(g, vector_limit=0)),
                    "no_action_utility": encoded(noop), "gain_vs_no_action": encoded(lower-noop),
                    "exhaustive": {k: v for k, v in exhaustive.items() if k != "commands"},
                    "dynamic_programming": {k: v for k, v in dp.items() if k != "commands"},
                    "beam": {"lower": beam["selected"]["utility"], "upper": None,
                             "visits": beam["visited_nodes"], "considered_actions": beam["considered_actions"],
                             "configured_cap": protocol["max_nodes"], "width": protocol["beam_width"]}}
                rows.append(row)
                (proofs/(case+".json")).write_text(dumps(c))
                if measure:
                    timings.append({"case": case, "solve": solve_times, "check": check_times,
                        "exhaustive": exhaustive_times, "dynamic_programming": dp_times, "beam": beam_times})
                progress(f"{case}: [{lower},{bound}], proof={len(c['nodes'])}, exhaustive={exhaustive['status']}, DP={dp['status']}")
                # Checkpoint everything already completed; never select only positive rows.
                (out/"progress.json").write_text(dumps({"rows": rows, "failures": failures}))
                if measure:
                    (out/"timings.partial.json").write_text(dumps(timings))
    result = {"version": "independent-certificate-benchmark-1", "data_kind": "SYNTHETIC",
        "scope": "DEVELOPMENT_ONLY_NO_FINAL_HOLDOUT", "protocol_commit": PROTOCOL_COMMIT,
        "producer_commit": PRODUCER_COMMIT, "protocol_sha256": digest(protocol),
        "source_sha256": source_sha(), "rows": rows, "failures": failures,
        "counts": {"declared": len(rows), "checked": len(rows),
            "exact_certificates": sum(r["certificate"]["gap"] == [0, 1] for r in rows),
            "complete_exhaustive": sum(r["exhaustive"]["status"] == "EXACT" for r in rows),
            "complete_dp": sum(r["dynamic_programming"]["status"] == "EXACT" for r in rows)}}
    result["sha256"] = digest(result)
    (out/"results.json").write_text(dumps(result))
    fields = ["case", "group", "scope", "horizon", "root_actions", "lower", "upper", "gap", "proof_nodes",
              "proof_bytes", "exhaustive_status", "dp_status", "beam_lower", "gain_vs_no_action"]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fields, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in fields if k in r} | {
            "lower": str(fraction(r["certificate"]["lower"])), "upper": str(fraction(r["certificate"]["upper"])),
            "gap": str(fraction(r["certificate"]["gap"])), "proof_nodes": r["certificate"]["search"]["generated"],
            "exhaustive_status": r["exhaustive"]["status"], "dp_status": r["dynamic_programming"]["status"],
            "beam_lower": str(fraction(r["beam"]["lower"])), "gain_vs_no_action": str(fraction(r["gain_vs_no_action"]))})
    (out/"results.csv").write_text(buf.getvalue())
    if measure:
        timing = {"version": "certificate-benchmark-timings-1", "source_sha256": source_sha(),
                  "results_sha256": result["sha256"], "platform": platform.platform(),
                  "python": platform.python_version(), "samples": timings,
                  "summary": timing_summary(rows, timings, protocol)}
        (out/"timings.json").write_text(dumps(timing))
    if failures:
        raise ValueError(f"{len(failures)} scientific correctness failures; see results.json")
    return result
