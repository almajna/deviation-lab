"""Reproduce Phase 1 sample evidence with explicit bounded downloads."""
from collections import Counter
import argparse
import json
from pathlib import Path

from .acquire import cached_input, read_json, result_members, sha256
from .pipeline import (AuditError, decision_view, digest, grouped_splits,
                       load_llmrouterbench, overlap_report, validate_records, validate_splits)


def audit(manifest: dict, cache: Path, *, download: bool = False) -> dict:
    # Explicitly marked synthetic manifests exercise the same acquisition and
    # validation path without mislabeling generated fixtures as real observations.
    data_kind = manifest.get("data_kind", "RECORDED_LLM_OUTCOMES")
    if data_kind not in {"RECORDED_LLM_OUTCOMES", "SYNTHETIC_FIXTURE"}:
        raise AuditError("invalid data kind")
    synthetic = data_kind == "SYNTHETIC_FIXTURE"
    cost_unit = "synthetic_units" if synthetic else "reported_usd"
    cost_basis = "synthetic_fixture" if synthetic else "api_usage_cost_or_token_pricing_unresolved"
    inputs = {name: cached_input(spec, cache, download=download)
              for name, spec in manifest["inputs"].items()}
    members = result_members(inputs["llm_archive_prefix"], manifest["llm_sample"]["members"])
    # Recheck query provenance against a separately pinned original task source.
    questions = [json.loads(line) for line in inputs["arena_questions"].split(b"\n") if line.strip()]
    original_prompts = {q["prompt"] for q in questions}
    records, rejected, source_counts, formatted_mismatches = [], [], {}, 0
    raw_task_prompts = {}
    for spec, doc in members:
        for row in doc["records"]:
            if row["origin_query"] not in original_prompts:
                raise AuditError("query not found in pinned original task source")
            key = str(row["index"])
            if key in raw_task_prompts and raw_task_prompts[key] != row["origin_query"]:
                raise AuditError("raw task prompts do not align")
            raw_task_prompts[key] = row["origin_query"]
        source_counts[spec["model_id"]] = len(doc["records"])
        accepted, invalid = load_llmrouterbench(
            doc, revision=manifest["llm_sample"]["revision"],
            metric="synthetic_fixture_quality" if synthetic else "arena_hard_judged_win_tie_loss",
            cost_unit=cost_unit, cost_basis=cost_basis, data_kind=data_kind, collect_invalid=True)
        records.extend(accepted)
        rejected.extend(invalid)
    models = tuple(sorted(source_counts))
    overlap = overlap_report(records, required_models=models)
    complete_ids = set(overlap.pop("complete_task_ids"))
    cohort = [r for r in records if r.task_id in complete_ids]
    validate_records(cohort, required_models=models)
    # This is verification of projection shape, not a deployable experiment.
    public = decision_view(cohort)
    if any(set(t) != {"task_id", "prompt", "model_options"} for t in public):
        raise AuditError("unexpected decision field")
    for task in complete_ids:
        formatted_mismatches += len({r.formatted_prompt_sha256 for r in cohort if r.task_id == task}) > 1
    splits = grouped_splits(cohort, seed=7)
    validate_splits(cohort, splits)
    split_counts = dict(sorted(Counter(e["split"] for e in splits["tasks"].values()).items()))
    report = {
        "schema_version": "data-audit-1", "data_kind": data_kind,
        "scope": ("synthetic integration fixture; no real model observations" if synthetic
                  else "bounded arenahard_coding subset; not representative of all benchmark domains"),
        "technical_pairing": "PASS", "empirical_gate": "NO_GO",
        "blockers": manifest["empirical_gate_blockers"],
        "llmrouterbench": {
            "source_records": sum(source_counts.values()), "source_model_counts": source_counts,
            "raw_aligned_tasks": len(raw_task_prompts),
            "original_prompt_matches": len(raw_task_prompts), "original_source_rows": len(questions),
            "zero_or_invalid_cost_and_outcome_rows": len(rejected),
            "rejection_counts": dict(sorted(Counter(r["reason"] for r in rejected).items())),
            "rejections_by_model": dict(sorted(Counter(r["model_id"] for r in rejected).items())),
            **overlap,
            "complete_cohort_records": len(cohort),
            "complete_tasks_with_model_specific_prompt_templates": formatted_mismatches,
            "selection_warning": "Complete-case exclusions depend on realized cost validity; audit cohort only, not a frozen evaluation set.",
            "score_semantics": ("synthetic fixture quality" if synthetic else
                                "judged baseline win=1, tie=0.5, loss=0; invalid judging can also become 0"),
            "cost_unit": cost_unit,
            "cost_basis": cost_basis,
            "cost_available_before_decision": False,
        },
        "routerbench": {
            "revision": manifest["routerbench"]["revision"],
            "prefix_bytes": len(inputs["router_pickle_prefix"]),
            "pickle_protocol": inputs["router_pickle_prefix"][1],
            "ingestion": "NOT_DESERIALIZED; upstream pickle is not a safe interchange format",
            "paired_task_count": None,
            "dataset_license": "synthetic fixture" if synthetic else "not declared at pinned HF revision",
            "cost_basis": ("synthetic fixture only" if synthetic else
                           "estimated from API/reference pricing; not observed invoices"),
        },
        "decision_fields": ["task_id", "prompt", "model_options"],
        "split_status": splits["status"], "split_counts": split_counts,
        "split_manifest_sha256": splits["sha256"],
        "incremental_spend_usd": 0,
    }
    input_manifest = {
        "schema_version": "data-audit-1", "source_manifest_sha256": digest(manifest),
        "sources": manifest["sources"],
        "inputs": {name: {**spec, "actual_sha256": sha256(inputs[name])}
                   for name, spec in manifest["inputs"].items()},
        "selected_members": manifest["llm_sample"]["members"],
        "raw_data_redistributed": False,
    }
    return {"data_audit.json": report, "data_manifest.json": input_manifest, "splits.json": splits}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/source_manifest.json"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--download", action="store_true", help="permit bounded public downloads; no inference")
    args = parser.parse_args()
    try:
        artifacts = audit(read_json(args.manifest), args.cache, download=args.download)
        args.out.mkdir(parents=True, exist_ok=True)
        for name, data in artifacts.items():
            (args.out / name).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")
    except (AuditError, KeyError, ValueError, OSError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")
    report = artifacts["data_audit.json"]
    print(f"Technical pairing: {report['technical_pairing']}; empirical gate: {report['empirical_gate']}")
    print(f"Complete sample: {report['llmrouterbench']['complete_paired_tasks']} tasks; {report['llmrouterbench']['complete_cohort_records']} outcomes")
    print("Evidence generated; NO_GO is a scientific finding, not a successful empirical benchmark.")


if __name__ == "__main__":
    main()
