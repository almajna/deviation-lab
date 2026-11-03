"""Preregister, rank, execute, review and remember bounded research cycles."""
from pathlib import Path
import json
import time

from .records import Memory, sha, source_hash, write
from .safety import run
from .scout import validate_sources

ALLOWED_RULES = {"lmsr_baseline": "all_analytic_checks", "fee_sensitivity": "fee_monotonic_with_strict_and_null_controls",
                 "certificate_ablation": "endpoint_dominance_with_strict", "forecast_correlation": "pool_correlated_nonnegative_relative"}


def execution_key(direction):
    # Titles, ranks and literature notes do not change executed science. Fixed
    # adapter version binds its hardcoded grid; seeds bind every stochastic input.
    diagnostic = direction.get("signed_diagnostic")
    diagnostic = {k: diagnostic[k] for k in ("version", "liquidities", "transitions")} if diagnostic else None
    return sha({"adapter": direction["runner"], "adapter_version": 1, "seeds": direction["seeds"],
                "scope": direction["scope"], "success_rule": direction["success_rule"],
                "signed_diagnostic": diagnostic})


def validate_plan(plan, source_ids):
    if plan.get("version") != "research-plan-1" or plan.get("max_experiments") != 4 or not 1 <= plan.get("cycle_wall_seconds", 0) <= 240:
        raise ValueError("invalid cycle plan/budget")
    directions = plan["directions"]
    if plan["published_baseline"]["runner"] != "lmsr_baseline":
        raise ValueError("published baseline adapter required")
    spec = plan["published_baseline"].get("signed_diagnostic")
    if spec and (spec["version"] != "signed-lmsr-diagnostic-1" or spec["liquidities"] != [1, 3, 8]
                 or len(spec["transitions"]) != 7):
        raise ValueError("unsupported signed diagnostic")
    if len(directions) != 3 or {d["runner"] for d in directions} != set(ALLOWED_RULES)-{"lmsr_baseline"}:
        raise ValueError("three distinct registered adapters required")
    for d in [plan["published_baseline"]]+directions:
        if (d.get("runner") not in ALLOWED_RULES or d.get("success_rule") != ALLOWED_RULES[d["runner"]]
                or d.get("scope") != "APPROVED_SYNTHETIC_DEVELOPMENT_ONLY" or d.get("assumption_changes") != []
                or d.get("owner_approval_required") is not False or d.get("evidence_kind") != "SYNTHETIC"):
            raise ValueError("unsupported adapter or research assumptions; owner review required")
        if not set(d["sources"]) <= source_ids or not d["sources"]:
            raise ValueError("unknown/unverified citation")
        if any(not d.get(k) for k in ("hypothesis", "baselines", "failure_rule", "information_boundary", "novelty_status")):
            raise ValueError("missing preregistration")
        seeds = d["seeds"]
        if len(seeds) > 3 or len(set(seeds)) != len(seeds) or any(type(s) is not int or not 0 <= s < 2**31 for s in seeds):
            raise ValueError("invalid seeds")
        if d["runner"] != "lmsr_baseline" and not seeds:
            raise ValueError("missing seeds")
        if d["runner"] != "lmsr_baseline":
            scores = d["scores"]
            if set(scores) != {"novelty", "importance", "usefulness", "feasibility", "baseline_strength"} or any(type(n) is not int or not 1 <= n <= 5 for n in scores.values()):
                raise ValueError("invalid gap ranking")
    return [plan["published_baseline"]]+sorted(directions, key=lambda d: (-sum(d["scores"].values()), d["id"]))


def cycle(plan_path, sources_path, memory_path, destination, *, scout_path=None, online=False):
    plan = json.loads(Path(plan_path).read_text())
    registry = json.loads(Path(sources_path).read_text())
    order = validate_plan(plan, validate_sources(registry))
    out = Path(destination)
    if out.exists() and any(out.iterdir()):
        raise ValueError("cycle destination must be empty to preserve earlier evidence")
    out.mkdir(parents=True, exist_ok=True)
    memory = Memory(memory_path)
    started = time.monotonic()
    source = source_hash()
    from deviation.verification.checker import source_sha
    engine_source = source_sha()
    frozen = {"plan": plan, "sources_sha256": sha(registry), "harness_source_sha256": source,
              "engine_source_sha256": engine_source, "execution_order": [d["id"] for d in order]}
    frozen_sha = sha(frozen)
    path = out/("preregistration-"+frozen_sha+".json")
    if path.exists() and json.loads(path.read_text()) != frozen:
        raise ValueError("preregistration changed")
    write(path, frozen)  # Frozen bytes written and event committed before any worker starts.
    write(out/"inputs.plan.json", plan)
    write(out/"inputs.sources.json", registry)
    try:
        from .scout import scout
        if online:
            scouting = scout(out/"scout.json")
        else:
            candidate_path = Path(scout_path) if scout_path else Path(sources_path).with_name("scout.json")
            scouting = json.loads(candidate_path.read_text())
            write(out/"scout.json", scouting)
        if scouting.get("sha256") != sha({k: v for k, v in scouting.items() if k != "sha256"}):
            raise ValueError("scout provenance digest mismatch")
        memory.event("literature_scouted", scouting["sha256"], scouting)
        for request in scouting["requests"]:
            for candidate in request["results"]:
                memory.event("source_discovered", sha(candidate), {"candidate": candidate,
                    "provider": request["provider"], "query": request["query"],
                    "claim_eligibility": "PRIMARY_SOURCE_READING_REQUIRED"}, [scouting["sha256"]])
        for s in registry["sources"]:
            memory.event("source_verified", s["id"], s)
        memory.event("cycle_preregistered", frozen_sha, frozen)
        records = []
        for d in order:
            dsha = sha(d)
            memory.event("hypothesis_ranked", dsha, d, d["sources"])
            # Identity intentionally ignores wall timings and software version; a new
            # session or cosmetic source refresh must not silently retry failed science.
            key = execution_key(d)
            if not memory.reserve(key, {"plan_sha256": frozen_sha, "hypothesis_sha256": dsha,
                                       "harness_source_sha256": source, "engine_source_sha256": engine_source}):
                records.append({"id": d["id"], "status": "duplicate_skipped"})
                continue
            run_dir = out/key
            run_dir.mkdir(exist_ok=True)
            write(run_dir/"plan.json", d)
            try:
                remaining = plan["cycle_wall_seconds"]-(time.monotonic()-started)
                result, receipt = run(d["runner"], d, wall_seconds=remaining)
                write(run_dir/"resources.json", {"execution": receipt})
                if receipt["harness_source_sha256"] != source or receipt["engine_source_sha256"] != engine_source:
                    raise ValueError("executed source differs from frozen preregistration")
                write(run_dir/"result.json", result)
                memory.event("result_recorded", key, {"sha256": sha(result), "artifact": key+"/result.json"}, [key])
                remaining = plan["cycle_wall_seconds"]-(time.monotonic()-started)
                review, review_receipt = run("review", {"plan": d, "result": result}, wall_seconds=remaining)
                write(run_dir/"resources.json", {"execution": receipt, "review": review_receipt})
                if review_receipt["harness_source_sha256"] != source or review_receipt["engine_source_sha256"] != engine_source:
                    raise ValueError("review source differs from frozen preregistration")
                write(run_dir/"review.json", review)
                # Non-deterministic measurements are kept outside reproducible scientific evidence.
                record = {"id": d["id"], "key": key, "status": "completed", "rows": len(result["rows"]),
                          "result_sha256": sha(result), "review": review}
                memory.event("review_recorded", key, review, [sha(result)])
                if review["criterion_status"].startswith("REJECTED"):
                    memory.event("hypothesis_rejected", dsha, review, [key])
                memory.finish(key, "completed", record)
            except Exception as exc:
                record = {"id": d["id"], "key": key, "status": "failed", "error": type(exc).__name__+": "+str(exc)[:3000]}
                if getattr(exc, "receipt", None):
                    write(run_dir/"failure-resources.json", exc.receipt)
                write(run_dir/"failure.json", record)
                memory.finish(key, "failed", record)
            records.append(record)
        summary = {"version": "research-cycle-1", "preregistration_sha256": frozen_sha,
                   "data_kind": "SYNTHETIC", "inference_calls": 0, "paid_spend_usd": 0,
                   "records": records, "novelty": "NOT_ESTABLISHED", "scientific_review": "PENDING"}
        summary["sha256"] = sha(summary)
        write(out/"summary.json", summary)
        memory.event("cycle_finished", frozen_sha, summary)
        memory.export(out/"events.jsonl")
        return summary
    finally:
        memory.close()
