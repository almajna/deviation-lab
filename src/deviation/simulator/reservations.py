"""Trusted offline preparation. Never pass these records to decision policies."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from deviation.contracts import ContractError, SCALE, validate_reservations
from deviation.data.pipeline import (decision_view, digest, validate_records,
                                     validate_splits)


def nanos(decimal_string):
    """Ceil each positive decimal to nanos, without decimal-context rounding."""
    if not isinstance(decimal_string, str):
        raise ContractError("cost must be an explicit decimal string")
    try:
        value = Decimal(decimal_string)
    except InvalidOperation as exc:
        raise ContractError("invalid decimal cost") from exc
    if not value.is_finite() or value <= 0:
        raise ContractError("cost must be finite and positive")
    value = Fraction(value) * SCALE
    return -(-value.numerator // value.denominator)


def fit_reservations(training_rows, split_groups, decision_tasks, *,
                     source_manifest_sha256, split_manifest_sha256,
                     data_kind="SYNTHETIC", cost_unit="nano_synthetic_units"):
    totals, counts = defaultdict(Fraction), defaultdict(int)
    for row in training_rows:
        nanos(row["cost_decimal"])  # Validate before Fraction conversion.
        totals[row["model_id"]] += Fraction(Decimal(row["cost_decimal"]))
        counts[row["model_id"]] += 1
    reserves = {}
    for model in sorted(totals):
        mean = totals[model] * SCALE / counts[model]
        reserves[model] = -(-mean.numerator // mean.denominator)
    artifact = {
        "schema_version": "0.2", "data_kind": data_kind, "cost_unit": cost_unit,
        "scale": SCALE, "method": "mean_train_only_v1",
        "source_manifest_sha256": source_manifest_sha256,
        "split_manifest_sha256": split_manifest_sha256,
        "fit_group_ids": sorted(g for g, split in split_groups.items() if split == "train"),
        "fit_row_count": len(training_rows), "reservations": reserves,
    }
    artifact["artifact_sha256"] = digest(artifact)
    validate_reservations(artifact, training_rows, split_groups, decision_tasks,
                          source_manifest_sha256=source_manifest_sha256,
                          split_manifest_sha256=split_manifest_sha256)
    return artifact


def prepare_records(records, split_manifest, *, source_manifest_sha256,
                    decision_split="validation"):
    """Adapt audited paired records into private runner inputs; no downloads.

    Supports only the Phase 1 exploratory split algorithm. This is offline data
    preparation, not access by an economic agent or a final-evaluation entrypoint.
    Float costs in OutcomeRecord retain their loader precision via str(cost).
    """
    validate_records(records)
    validate_splits(records, split_manifest)
    if (split_manifest.get("status") != "EXPLORATORY_NOT_FROZEN"
            or decision_split not in {"validation", "test"}):
        raise ContractError("only explicit exploratory decision splits are supported")
    if records[0].cost_unit not in {"reported_usd", "synthetic_units"}:
        raise ContractError("unapproved historical cost semantics")
    registry = split_manifest["tasks"]
    groups = {v["group_id"]: v["split"] for v in registry.values()}
    training = [r for r in records if registry[r.task_id]["split"] == "train"]
    selected = [r for r in records if registry[r.task_id]["split"] == decision_split]
    tasks = decision_view(selected)
    rows = [{"task_id": r.task_id, "prompt": r.prompt, "model_id": r.model_id,
             "cost_decimal": str(r.cost), "cost_unit": r.cost_unit}
            for r in sorted(training, key=lambda r: (r.task_id, r.model_id))]
    kind = "SYNTHETIC" if records[0].cost_unit == "synthetic_units" else "RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS"
    unit = "nano_" + records[0].cost_unit
    artifact = fit_reservations(rows, groups, tasks,
                                source_manifest_sha256=source_manifest_sha256,
                                split_manifest_sha256=split_manifest["sha256"],
                                data_kind=kind, cost_unit=unit)
    qualities = [{"task_id": r.task_id, "model_id": r.model_id, "quality": r.quality}
                 for r in sorted(training, key=lambda r: (r.task_id, r.model_id))]
    outcomes = [{"task_id": r.task_id, "model_id": r.model_id,
                 "quality": r.quality, "cost_decimal": str(r.cost)}
                for r in sorted(selected, key=lambda r: (r.task_id, r.model_id))]
    return {"training_rows": rows, "split_groups": groups, "decision_tasks": tasks,
            "reservation_artifact": artifact, "training_quality_rows": qualities,
            "sealed_outcomes": outcomes}
