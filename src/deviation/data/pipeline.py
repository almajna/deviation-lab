"""Strict, stdlib-only adapters and reproducible feasibility diagnostics.

OutcomeRecord is an audit/evaluation object, NEVER an allocator input. The
allowlisted decision_view is the only public projection supplied by this module.
Shared experiment contracts remain unchanged and unapproved.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import re
import unicodedata


class AuditError(ValueError):
    """Explicit invalid data, pairing, provenance, or split boundary."""


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalized_prompt(prompt: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", prompt).casefold().split())


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"missing or invalid {name}")
    return value


def _number(value: object, name: str, *, upper: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuditError(f"missing or invalid {name}")
    if not math.isfinite(value) or value < 0 or (upper is not None and value > upper):
        raise AuditError(f"out-of-range {name}")
    return float(value)


@dataclass(frozen=True)
class OutcomeRecord:
    source: str
    revision: str
    dataset: str
    source_split: str
    task_id: str
    model_id: str
    prompt: str
    formatted_prompt_sha256: str
    ground_truth_sha256: str | None
    quality: float
    cost: float
    cost_unit: str
    cost_basis: str
    metric: str
    data_kind: str

    @property
    def group_id(self) -> str:
        # Deliberately excludes source/task ID: repeated prompts across IDs and
        # sources must be in one split, even if labels/outcomes differ.
        return digest(normalized_prompt(self.prompt))


def load_llmrouterbench(document: dict, *, revision: str, metric: str,
                       cost_unit: str, cost_basis: str,
                       data_kind: str = "RECORDED_LLM_OUTCOMES",
                       collect_invalid: bool = False) -> tuple[list[OutcomeRecord], list[dict]]:
    """Adapt a single pinned result JSON; never coerce missing labels/cost to zero.

    Default is fail-closed. collect_invalid is an explicit audit mode: rejected
    rows are counted/reported and cannot enter a paired research cohort silently.
    Zero reported real USD cost is unknown/free-unverified, not a free model.
    """
    if not isinstance(document, dict) or document.get("demo") is not False:
        raise AuditError("missing demo flag or demo result")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise AuditError("source revision must be a pinned commit SHA")
    if data_kind not in {"RECORDED_LLM_OUTCOMES", "SYNTHETIC_FIXTURE"}:
        raise AuditError("invalid data kind")
    for value, name in [(metric, "metric"), (cost_basis, "cost_basis")]:
        _text(value, name)
    if cost_unit not in {"reported_usd", "estimated_usd", "synthetic_units"}:
        raise AuditError("unknown cost unit")
    if (data_kind == "SYNTHETIC_FIXTURE") != (cost_unit == "synthetic_units"):
        raise AuditError("synthetic/real cost provenance mismatch")
    dataset = _text(document.get("dataset_name"), "dataset_name")
    source_split = _text(document.get("split"), "source split")
    model = _text(document.get("model_name"), "model_name")
    rows = document.get("records")
    if not isinstance(rows, list) or not rows:
        raise AuditError("missing records")
    if (isinstance(document.get("counts"), bool) or not isinstance(document.get("counts"), int)
            or document["counts"] != len(rows)):
        raise AuditError("record count mismatch")
    accepted, rejected, seen = [], [], set()
    for position, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise AuditError("record is not an object")
            index = row.get("index")
            if isinstance(index, bool) or not isinstance(index, (int, str)) or str(index).strip() == "":
                raise AuditError("invalid source index")
            if str(index) in seen:
                # Duplicates are structural ambiguity, not excludable bad outcomes.
                raise AuditError("duplicate source index")
            seen.add(str(index))
            prompt = _text(row.get("origin_query"), "origin_query")
            formatted = _text(row.get("prompt"), "formatted prompt")
            quality = _number(row.get("score"), "score", upper=1)
            cost = _number(row.get("cost"), "cost")
            if data_kind == "RECORDED_LLM_OUTCOMES" and cost == 0:
                raise AuditError("zero real cost has unverified provenance")
            for name in ["prompt_tokens", "completion_tokens"]:
                count = row.get(name)
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise AuditError(f"invalid {name}")
            raw = row.get("raw_output")
            if (not isinstance(raw, str) or not raw.strip()
                    or raw.startswith(("Generation failed:", "Processing failed:", "Unexpected error:"))):
                raise AuditError("missing or failed model output")
            truth = row.get("ground_truth")
            accepted.append(OutcomeRecord(
                source="LLMRouterBench", revision=revision, dataset=dataset,
                source_split=source_split,
                task_id=digest(["LLMRouterBench", revision, dataset, source_split, str(index)]),
                model_id=model, prompt=prompt, formatted_prompt_sha256=digest(formatted),
                ground_truth_sha256=None if truth is None or truth == "" else digest(truth),
                quality=quality, cost=cost, cost_unit=cost_unit, cost_basis=cost_basis,
                metric=metric, data_kind=data_kind,
            ))
        except AuditError as exc:
            if not collect_invalid or str(exc) == "duplicate source index":
                raise
            rejected.append({"model_id": model, "position": position, "reason": str(exc)})
    return accepted, rejected


def validate_records(records: list[OutcomeRecord], *, require_complete: bool = True,
                     required_models: tuple[str, ...] | None = None) -> None:
    if not records:
        raise AuditError("empty dataset")
    tasks = defaultdict(list)
    seen = set()
    for r in records:
        for field in ["source", "revision", "dataset", "source_split", "task_id", "model_id",
                      "cost_unit", "cost_basis", "metric", "data_kind", "formatted_prompt_sha256"]:
            _text(getattr(r, field), field)
        if not re.fullmatch(r"[0-9a-f]{40}", r.revision):
            raise AuditError("source revision must be a pinned commit SHA")
        if r.cost_unit not in {"reported_usd", "estimated_usd", "synthetic_units"}:
            raise AuditError("unknown cost unit")
        if r.data_kind not in {"RECORDED_LLM_OUTCOMES", "SYNTHETIC_FIXTURE"}:
            raise AuditError("invalid data kind")
        if (r.data_kind == "SYNTHETIC_FIXTURE") != (r.cost_unit == "synthetic_units"):
            raise AuditError("synthetic/real cost provenance mismatch")
        _number(r.quality, "score", upper=1)
        _number(r.cost, "cost")
        if r.data_kind == "RECORDED_LLM_OUTCOMES" and r.cost == 0:
            raise AuditError("zero real cost has unverified provenance")
        _text(r.prompt, "prompt")
        key = (r.task_id, r.model_id)
        if key in seen:
            raise AuditError("duplicate task/model outcome")
        seen.add(key)
        tasks[r.task_id].append(r)
    if len({(r.source, r.revision, r.cost_unit, r.cost_basis, r.metric, r.data_kind)
            for r in records}) != 1:
        raise AuditError("mixed source revisions, units, cost basis, metrics, or data kind")
    models = set(required_models) if required_models is not None else {r.model_id for r in records}
    if len(models) < 2:
        raise AuditError("at least two model arms required")
    if {r.model_id for r in records} - models:
        raise AuditError("unexpected model arm")
    for rows in tasks.values():
        if len({(r.dataset, r.source_split, r.prompt, r.ground_truth_sha256) for r in rows}) != 1:
            raise AuditError("task prompts or ground truths do not align across arms")
        if require_complete and {r.model_id for r in rows} != models:
            raise AuditError("missing paired outcomes")


def overlap_report(records: list[OutcomeRecord], *, required_models: tuple[str, ...]) -> dict:
    validate_records(records, require_complete=False, required_models=required_models)
    by_model = {m: {r.task_id for r in records if r.model_id == m} for m in required_models}
    union = set.union(*by_model.values())
    complete = set.intersection(*by_model.values())
    return {
        "valid_records": len(records), "tasks_with_any_valid_outcome": len(union),
        "complete_paired_tasks": len(complete),
        "incomplete_tasks": len(union - complete),
        "model_counts": {m: len(ids) for m, ids in by_model.items()},
        "missing_by_model": {m: len(union - ids) for m, ids in by_model.items()},
        "overlap_matrix": {a: {b: len(by_model[a] & by_model[b]) for b in by_model} for a in by_model},
        "complete_task_ids": sorted(complete),
        "ground_truth_present_records": sum(r.ground_truth_sha256 is not None for r in records),
        "quality_value_counts": dict(sorted(Counter(str(r.quality) for r in records).items())),
    }


def decision_view(records: list[OutcomeRecord]) -> list[dict]:
    """Public prompt + model IDs only; no realized cost, target, score or output.

    Validation is an offline cohort-preparation step. Callers must never use its
    results/errors as a feature, or select future tasks based on held-out outcomes.
    """
    validate_records(records)
    grouped = defaultdict(list)
    for r in records:
        grouped[r.task_id].append(r)
    return [{"task_id": task, "prompt": rows[0].prompt,
             "model_options": sorted(r.model_id for r in rows)}
            for task, rows in sorted(grouped.items())]


def grouped_splits(records: list[OutcomeRecord], *, seed: int = 7) -> dict:
    """Exploratory 70/15/15 split, stable under input order and appended groups.

    NFKC/case/whitespace-identical prompts (even across different task IDs) stay
    together. This is NOT semantic near-duplicate detection or a frozen holdout.
    """
    validate_records(records)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise AuditError("seed must be an integer")
    tasks = {}
    for r in sorted(records, key=lambda x: x.task_id):
        bucket = int(digest([seed, r.group_id]), 16) % 10000
        split = "train" if bucket < 7000 else "validation" if bucket < 8500 else "test"
        tasks[r.task_id] = {"group_id": r.group_id, "split": split}
    result = {"schema_version": "data-audit-1", "seed": seed, "status": "EXPLORATORY_NOT_FROZEN",
              "algorithm": "sha256(seed, normalized_prompt_hash) modulo 10000; 7000/8500 cutoffs",
              "tasks": tasks}
    result["sha256"] = digest(result)
    return result


def validate_splits(records: list[OutcomeRecord], manifest: dict) -> None:
    validate_records(records)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tasks"), dict):
        raise AuditError("invalid split manifest")
    content = {k: v for k, v in manifest.items() if k != "sha256"}
    if manifest.get("sha256") != digest(content):
        raise AuditError("split manifest checksum mismatch")
    tasks = manifest["tasks"]
    if set(tasks) != {r.task_id for r in records}:
        raise AuditError("split manifest must cover exactly the cohort")
    groups = {}
    for r in records:
        entry = tasks[r.task_id]
        if (not isinstance(entry, dict) or entry.get("group_id") != r.group_id
                or entry.get("split") not in {"train", "validation", "test"}):
            raise AuditError("invalid split assignment")
        split = entry["split"]
        if r.group_id in groups and groups[r.group_id] != split:
            raise AuditError("prompt group leaks across splits")
        groups[r.group_id] = split
    if manifest != grouped_splits(records, seed=manifest.get("seed")):
        raise AuditError("split assignments or metadata do not match the declared seed/algorithm")
