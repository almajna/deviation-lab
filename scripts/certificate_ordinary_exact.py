"""Secondary diagnostic: unchanged ordinary exact search on the frozen grid.

Added after the initial protocol to satisfy supervisor's comparator request.
It does not enter the prespecified primary speed metric or change any fixture.
"""
import json
from pathlib import Path
import sys
from time import perf_counter

from deviation.attacks.search import search
from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from deviation.verification.checker import source_sha
from deviation.verification.fixtures import fixture


def main():
    protocol = json.loads(Path("experiments/certificate_benchmark.json").read_text())
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    rows, times = [], []
    for p in protocol["profiles"]:
        for seed in protocol["seeds"]:
            for mechanism in protocol["mechanisms"]:
                case = f"{p['id']}-{seed}-{mechanism}"
                game = fixture(p, seed, mechanism)
                start = perf_counter()
                try:
                    r = search(game, max_nodes=protocol["independent_max_nodes"])
                    row = {"case": case, "status": "EXACT", "utility": r["selected"]["utility"],
                           "nodes": r["visited_nodes"], "leaves": r["terminal_evaluations"]}
                except Rejection as error:
                    if error.code != "EXACT_SEARCH_LIMIT_NO_OPTIMALITY_CLAIM":
                        (folder/"ordinary_exact.failure.json").write_text(json.dumps({"case": case, "error": str(error)}))
                        raise
                    row = {"case": case, "status": "CENSORED_STATE_LIMIT", "utility": None,
                           "configured_node_cap": protocol["independent_max_nodes"]}
                rows.append(row)
                times.append({"case": case, "seconds": perf_counter()-start})
    result = {"version": "secondary-ordinary-exact-1", "source_sha256": source_sha(),
              "protocol_sha256": digest(protocol), "rows": rows}
    result["sha256"] = digest(result)
    (folder/"ordinary_exact.json").write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
    (folder/"ordinary_exact_timings.json").write_text(json.dumps(times, sort_keys=True, indent=2)+"\n")
    print(json.dumps({"cases": len(rows), "exact": sum(r["status"] == "EXACT" for r in rows), "sha256": result["sha256"]}))


if __name__ == "__main__":
    main()
