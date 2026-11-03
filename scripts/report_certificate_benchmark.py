"""Computed tables/figures; matplotlib==3.10.7 only for report generation."""
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    folder = Path(sys.argv[1])
    results = json.loads((folder/"results.json").read_text())
    timings = json.loads((folder/"timings.json").read_text())
    timing = {r["case"]: r for r in timings["samples"]}
    rows = results["rows"]
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["mechanism"]].append(row)
    def rational(value):
        return Fraction(*value)
    def exact(r):
        return r["certificate"]["gap"] == [0, 1]
    table = ["| Mechanism | Cases | Zero gap | Exhaustive complete | DP complete | Median / max gap |",
             "|---|---:|---:|---:|---:|---:|"]
    for m, values in sorted(grouped.items()):
        gaps = [rational(r["certificate"]["gap"]) for r in values]
        table.append(f"| {m} | {len(values)} | {sum(exact(r) for r in values)} | "
                     f"{sum(r['exhaustive']['status']=='EXACT' for r in values)} | "
                     f"{sum(r['dynamic_programming']['status']=='EXACT' for r in values)} | "
                     f"{median(gaps)} / {max(gaps)} |")
    summary = timings["summary"]
    improvement = sum(rational(r["certificate"]["lower"]) > rational(r["beam"]["lower"]) for r in rows)
    lost = sum(rational(r["certificate"]["lower"]) < rational(r["beam"]["lower"]) for r in rows)
    root_improved = sum(rational(r["root_endpoint_upper"]) < rational(r["root_fallback_upper"]) for r in rows)
    max_bytes = max(r["proof_bytes"] for r in rows)
    ratio_lookup = {r["case"]: r["ratio"] for r in summary["eligible"]}
    cost_table = ["| Mechanism | Eligible cases | Median paired time ratio |",
                  "|---|---:|---:|"]
    for m, values in sorted(grouped.items()):
        ratios = [ratio_lookup[r["case"]] for r in values if r["case"] in ratio_lookup]
        cost_table.append(f"| {m} | {len(ratios)} | {median(ratios):.3f} |")
    ordinary_path = folder/"ordinary_exact.json"
    ordinary_note = "Secondary ordinary-exact diagnostic not supplied."
    if ordinary_path.exists():
        ordinary = json.loads(ordinary_path.read_text())
        row_lookup = {r["case"]: r for r in rows}
        for row in ordinary["rows"]:
            if row["status"] == "EXACT":
                ref = row_lookup[row["case"]]
                assert rational(ref["certificate"]["lower"]) <= rational(row["utility"]) <= rational(ref["certificate"]["upper"])
                if ref["exhaustive"]["status"] == "EXACT":
                    assert ref["exhaustive"]["utility"] == row["utility"]
        n = sum(r["status"] == "EXACT" for r in ordinary["rows"])
        ordinary_note = (f"The separately labeled unchanged ordinary-exact diagnostic completed {n}/{len(rows)} "
                         "cases; all completed values agreed with independent exact results and the certified intervals. "
                         "It was added after the initial protocol at the supervisor's request and does not enter the primary timing criterion.")
    report = f"""# Independent attack-certificate evaluation

All **{len(rows)} cases are synthetic development fixtures**, from the frozen
protocol [{results['protocol_commit']}](https://github.com/almajna/deviation-lab/commit/{results['protocol_commit']}).
No real LLM-agent decisions, recorded outcome rows or final holdout were used.
The producer is unmodified Agent 1 PR #23 at {results['producer_commit']}.
Integrated source fingerprint: `{results['source_sha256']}`.
Results fingerprint: `{results['sha256']}`.

## Correctness and utility of the certificate

The independent checker accepted all {results['counts']['checked']} generated
proofs. There were **{len(results['failures'])} interval/baseline disagreements**.
Every completed independent exhaustive or dynamic-programming result lay within
the certified interval. Zero gap establishes finite-subgame optimality only.
This is executable evidence under a shared trusted engine and numeric library,
not a proof-assistant theorem or an independent audit of those dependencies.

{chr(10).join(table)}

The producer's feasible utility beat ordinary beam search in {improvement} cases,
lost in {lost}, and tied in {len(rows)-improvement-lost}. These algorithms have
different units of work: the configured cap is a state expansion cap for the
producer and a candidate-transition cap for beam. The table is not an equal-time
superiority estimate. Beam supplies no mathematical upper bound.
Work counters use finite-game child transitions, with static-report completion
counted as one child; they are not counts of raw Engine.apply invocations.
The endpoint relaxation improved the root bound over its conservative fallback
in {root_improved}/{len(rows)} cases. Largest proof: {max_bytes:,} serialized bytes.
All rows, including censored baselines and nonzero gaps, appear in results.csv.

The eight-slot LMSR stress cases closed their gaps even where both independent
exact baselines hit their declared state cap. This is useful scoped evidence for
the bound, not an equal-time speedup estimate: a completed exact comparator is
unavailable there. The corresponding eight-slot interactive-pool cases retained
gaps and lost incumbent utility to beam search. The external-reward relaxation
and best-bound exploration do not by themselves guarantee strong feasible search.

{ordinary_note}

## Prespecified practical-value criterion

On {summary['n']} eligible zero-gap cases with at least two legal root actions and
a completed exact comparator, the median paired ratio
`(median generation time + median independent-check time) / faster completed exact baseline time`
was **{summary['median_ratio']:.3f}**. The descriptive 95% seed-block bootstrap
interval was **[{summary['seed_block_95_interval'][0]:.3f}, {summary['seed_block_95_interval'][1]:.3f}]**.
The preregistered threshold (ratio <=0.8 on >=10 cases) was
**{'MET within this finite suite' if summary['prespecified_speed_criterion_met'] else 'NOT MET'}**.
This is a warm-cache measurement, with one warm run and three retained repeats
per method/case; it does not describe first-run latency. There are only three
seed blocks, related grid cells and repeated static-report settings. The interval
is not a real-world population confidence statement.

Descriptive breakdown (no additional success criteria):

{chr(10).join(cost_table)}

## Scientific conclusion

The implemented certificate adds an independently checkable upper bound and
explicit residual uncertainty to executable best-found attacks. Its economic
bound uses known branch-and-bound and proof-checking principles applied to the
engine's rounded LMSR charges. This suite does **not** establish a new economic
vulnerability, literature novelty, a breakthrough, full-game robustness or
generic optimization superiority. Passing a finite suite cannot exclude all
implementation errors. Practical value is conditional on the measured criteria
and the narrow information/action model.

## Limits and reproduction

The public schedule is constructed to leave a controlled terminal suffix. It
does not test unknown future honest actions. Prescribed beliefs are not calibrated
LLM forecasts; no realized welfare or accuracy claim follows. Controller account
partitions keep the registry/funding fixed but do not model free identity creation.
Static pool games search one final commitment in every profile, even when the
profile's terminal horizon is larger. Exact DP merges equivalent future economic
states and its returned commands are rebound/replayed; capped runs have no exact
answer. State/expansion caps are not hard runtime or peak-memory limits. Arbitrary
root histories pre-reserving future canonical order IDs are unsupported.

Independent checker code imports no producer optimizer, action generator, bound
or payoff helpers. Engine transitions, certified quotes/prices, reservation
artifacts, Game serialization and the package digest remain shared dependencies.
The checker computes allocation and Brier/utility arithmetic separately.

```
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python -I -m deviation.verification --out replay/certificates --no-timings --verify artifacts/verification/results.json
python -I -m deviation.verification --out replay/measured
python scripts/certificate_ordinary_exact.py replay/measured
python scripts/check_certificate_archive.py artifacts/verification
python -m pip install matplotlib==3.10.7
MPLCONFIGDIR=replay/mpl python scripts/report_certificate_benchmark.py replay/measured
```

Economic values, proofs, work counts and source bindings reproduce exactly;
wall times vary by hardware/load. The first declared base/seed101 case for each
mechanism is retained as a complete example proof regardless of outcome. The
driver emits all proof files. No monetary spend or final holdout access occurred.
All 81 complete proofs are also retained in a compressed archive directory with
hashes of compressed and original JSON bytes; they can be independently checked
without rerunning any optimizer.

The first complete run, including its negative speed result, is preserved under
artifacts/verification/initial_run/. The official run follows logging-only failed-case persistence and
explicit rejection of unsupported noncanonical roots; settings and mathematical
algorithms were not tuned. These are disclosed infrastructure corrections.
"""
    (folder/"REPORT.md").write_text(report)
    figures = folder/"figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.hashsalt": "deviation-certificate-eval-1"})
    colors = {"lmsr": "#175D91", "interactive-pool": "#B65334", "pool": "#567B45"}
    data = {"gap": [], "runtime": [], "work": []}
    fig, ax = plt.subplots(figsize=(9.5, 4.5), layout="constrained")
    for m, values in sorted(grouped.items()):
        x = [r["horizon"] for r in values]
        y = [float(rational(r["certificate"]["gap"])) for r in values]
        ax.scatter(x, y, label=m, color=colors[m], alpha=.6, s=40)
        data["gap"] += [{"case": r["case"], "horizon": h, "gap": gap} for r, h, gap in zip(values, x, y)]
    ax.set(xlabel="Actually searched controlled horizon (report games: 1)", ylabel="Residual utility gap (virtual units)",
           title="Finite-game certificate tightness — all declared synthetic cases")
    ax.legend(frameon=False)
    fig.savefig(figures/"gaps.svg", metadata={"Date": None})
    fig.savefig(figures/"gaps.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.4, 5), layout="constrained")
    for m, values in sorted(grouped.items()):
        xs, ys = [], []
        for row in values:
            t = timing[row["case"]]
            baseline = [median(t[k]) for k in ["exhaustive", "dynamic_programming"] if row[k]["status"] == "EXACT"]
            if not baseline or not exact(row) or row["root_actions"] < 2:
                continue
            xs.append(min(baseline))
            ys.append(median(t["solve"])+median(t["check"]))
            data["runtime"].append({"case": row["case"], "exact_seconds": xs[-1], "solve_check_seconds": ys[-1]})
        ax.scatter(xs, ys, label=m, color=colors[m], alpha=.65)
    points = data["runtime"]
    lo = min(min(p["exact_seconds"], p["solve_check_seconds"]) for p in points)*.6
    hi = max(max(p["exact_seconds"], p["solve_check_seconds"]) for p in points)*1.7
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="equal time")
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel="Faster completed independent exact baseline (seconds)",
           ylabel="Generation + independent verification (seconds)",
           title="Warm-cache cost; zero-gap eligible cases")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(figures/"cost.svg", metadata={"Date": None})
    fig.savefig(figures/"cost.png", dpi=160)
    plt.close(fig)
    for row in rows:
        data["work"].append({"case": row["case"], "proof_nodes": row["certificate"]["search"]["generated"],
                             "dp_nodes": row["dynamic_programming"]["nodes"], "dp_status": row["dynamic_programming"]["status"]})
    (folder/"plot_data.json").write_text(json.dumps(data, sort_keys=True, indent=2)+"\n")
    for svg in figures.glob("*.svg"):
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    files = [folder/"results.json", folder/"timings.json", folder/"plot_data.json", Path(__file__)]
    manifest = {str(p.name): sha256(p.read_bytes()).hexdigest() for p in files}
    manifest["figures"] = {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(figures.glob("*.svg"))}
    (folder/"figure_manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2)+"\n")
    print(report)


if __name__ == "__main__":
    main()
