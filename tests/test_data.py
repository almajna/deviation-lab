"""Offline adversarial validation tests; every fixture here is SYNTHETIC."""
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from deviation.data import (AuditError, decision_view, grouped_splits,
                            load_llmrouterbench, overlap_report,
                            validate_records, validate_splits)
from deviation.data.acquire import cached_input, read_json, result_members, sha256
from deviation.data.pipeline import digest

FIXTURE = Path(__file__).parent / "fixtures" / "llmrouterbench_mock.json"


def documents():
    data = json.loads(FIXTURE.read_text())
    assert data["data_kind"] == "SYNTHETIC_FIXTURE"
    return data["documents"]


def load(doc, **options):
    return load_llmrouterbench(doc, revision="a" * 40, metric="mock_fractional_quality",
                              cost_unit="synthetic_units", cost_basis="synthetic_fixture",
                              data_kind="SYNTHETIC_FIXTURE", **options)


def records():
    return [row for doc in documents() for row in load(doc)[0]]


class TestDataValidation(unittest.TestCase):
    def test_mock_pairs_and_fractional_scores(self):
        rows = records()
        validate_records(rows)
        report = overlap_report(rows, required_models=("mock-A", "mock-B"))
        self.assertEqual(report["complete_paired_tasks"], 4)
        self.assertEqual(report["incomplete_tasks"], 0)
        self.assertEqual(report["overlap_matrix"]["mock-A"]["mock-B"], 4)
        self.assertIn(0.5, {r.quality for r in rows})

    def test_missing_or_invalid_scores_never_become_zero(self):
        for value in [None, True, "0", float("nan"), float("inf"), -1, 1.01]:
            with self.subTest(value=value):
                doc = documents()[0]
                doc["records"][0]["score"] = value
                with self.assertRaises(AuditError):
                    load(doc)

    def test_missing_and_invalid_costs(self):
        for value in [None, True, "1", float("nan"), float("inf"), -1]:
            with self.subTest(value=value):
                doc = documents()[0]
                doc["records"][0]["cost"] = value
                with self.assertRaises(AuditError):
                    load(doc)

    def test_zero_real_cost_is_not_a_free_model(self):
        doc = documents()[0]
        doc["records"][0]["cost"] = 0
        with self.assertRaisesRegex(AuditError, "zero real cost"):
            load_llmrouterbench(doc, revision="a" * 40, metric="judged",
                               cost_unit="reported_usd", cost_basis="unresolved")

    def test_explicit_audit_rejections_remain_incomplete(self):
        docs = documents()
        docs[0]["records"][0]["score"] = None
        accepted, rejected = load(docs[0], collect_invalid=True)
        self.assertEqual(len(rejected), 1)
        self.assertIn("score", rejected[0]["reason"])
        rows = accepted + load(docs[1])[0]
        report = overlap_report(rows, required_models=("mock-A", "mock-B"))
        self.assertEqual(report["incomplete_tasks"], 1)
        with self.assertRaisesRegex(AuditError, "missing paired"):
            validate_records(rows)

    def test_duplicate_source_index_always_fails(self):
        doc = documents()[0]
        doc["records"].append(deepcopy(doc["records"][0]))
        doc["counts"] += 1
        with self.assertRaisesRegex(AuditError, "duplicate"):
            load(doc, collect_invalid=True)

    def test_duplicate_outcomes_and_single_arm(self):
        rows = records()
        with self.assertRaisesRegex(AuditError, "duplicate"):
            validate_records(rows + [rows[0]])
        with self.assertRaisesRegex(AuditError, "two model arms"):
            validate_records(load(documents()[0])[0])

    def test_mismatched_prompt_or_ground_truth(self):
        for change in [{"prompt": "different question"}, {"ground_truth_sha256": digest("other answer")}]:
            with self.subTest(change=change):
                rows = records()
                rows[0] = replace(rows[0], **change)
                with self.assertRaisesRegex(AuditError, "do not align"):
                    validate_records(rows)

    def test_units_provenance_and_metric_may_not_mix(self):
        for change in [{"cost_unit": "estimated_usd"}, {"revision": "b" * 40},
                       {"metric": "another_metric"}, {"data_kind": "RECORDED_LLM_OUTCOMES"},
                       {"cost_basis": "unknown"}]:
            with self.subTest(change=change):
                rows = records()
                rows[0] = replace(rows[0], **change)
                with self.assertRaises(AuditError):
                    validate_records(rows)

    def test_missing_metadata_or_failed_output(self):
        for change in [{"demo": True}, {"demo": None}, {"counts": 999}]:
            doc = documents()[0]
            doc.update(change)
            with self.assertRaises(AuditError):
                load(doc)
        doc = documents()[0]
        doc["records"][0]["raw_output"] = "Processing failed: fixture failure"
        with self.assertRaisesRegex(AuditError, "failed model"):
            load(doc)

    def test_uniformly_invalid_records_do_not_bypass_public_validator(self):
        for change in [{"cost_unit": "bananas"}, {"revision": "main"},
                       {"source": ""}, {"model_id": ""}, {"task_id": ""},
                       {"data_kind": "unknown"}, {"cost_basis": ""},
                       {"cost": 0, "cost_unit": "reported_usd", "data_kind": "RECORDED_LLM_OUTCOMES"}]:
            with self.subTest(change=change):
                with self.assertRaises(AuditError):
                    validate_records([replace(r, **change) for r in records()])

    def test_decision_projection_does_not_depend_on_hidden_values(self):
        rows = records()
        before = decision_view(rows)
        after = decision_view([replace(r, quality=1-r.quality, cost=r.cost + 500,
                                       ground_truth_sha256=digest("hidden replacement")) for r in rows])
        self.assertEqual(before, after)
        self.assertEqual(set(before[0]), {"task_id", "prompt", "model_options"})
        encoded = json.dumps(before)
        for field in ["cost", "score", "quality", "ground_truth", "completion_tokens", "raw_output", "oracle"]:
            self.assertNotIn('"' + field + '"', encoded)


class TestGroupedSplits(unittest.TestCase):
    def test_deterministic_grouping_across_ids_and_order(self):
        rows = records()
        split = grouped_splits(rows, seed=7)
        self.assertEqual(split, grouped_splits(list(reversed(rows)), seed=7))
        # Fixture tasks 1 and 2 have case/whitespace-equivalent queries.
        tasks = load(documents()[0])[0]
        self.assertNotEqual(tasks[0].task_id, tasks[1].task_id)
        self.assertEqual(tasks[0].group_id, tasks[1].group_id)
        self.assertEqual(split["tasks"][tasks[0].task_id]["split"],
                         split["tasks"][tasks[1].task_id]["split"])
        self.assertEqual(split["status"], "EXPLORATORY_NOT_FROZEN")
        validate_splits(rows, split)

    def test_split_contamination_is_rejected_even_with_updated_checksum(self):
        rows = records()
        split = grouped_splits(rows)
        task = rows[0].task_id
        previous = split["tasks"][task]["split"]
        split["tasks"][task]["split"] = "test" if previous != "test" else "train"
        split["sha256"] = digest({k: v for k, v in split.items() if k != "sha256"})
        with self.assertRaisesRegex(AuditError, "leaks across splits"):
            validate_splits(rows, split)

    def test_manifest_tampering_and_missing_task(self):
        rows = records()
        split = grouped_splits(rows)
        split["seed"] += 1
        with self.assertRaisesRegex(AuditError, "checksum"):
            validate_splits(rows, split)
        split = grouped_splits(rows)
        split["tasks"].pop(rows[0].task_id)
        split["sha256"] = digest({k: v for k, v in split.items() if k != "sha256"})
        with self.assertRaisesRegex(AuditError, "cover exactly"):
            validate_splits(rows, split)

    def test_split_seed_and_algorithm_must_reproduce_assignments(self):
        rows = records()
        for change in [{"seed": 999999}, {"algorithm": "unreviewed algorithm"}]:
            split = grouped_splits(rows)
            split.update(change)
            split["sha256"] = digest({k: v for k, v in split.items() if k != "sha256"})
            with self.assertRaisesRegex(AuditError, "declared seed/algorithm"):
                validate_splits(rows, split)


class TestSafeAcquisition(unittest.TestCase):
    def test_pickle_is_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "untrusted.pkl"
            path.write_bytes(b"\x80\x05cos\nsystem\n")
            with self.assertRaisesRegex(AuditError, "pickle is never"):
                read_json(path)

    def test_corrupt_cache_fails_closed(self):
        spec = {"bytes": 3, "sha256": sha256(b"abc")}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/(spec["sha256"]+".bin")).write_bytes(b"xyz")
            with self.assertRaisesRegex(AuditError, "SHA-256 mismatch"):
                cached_input(spec, Path(tmp))

    def test_range_refusal_never_reads_full_response(self):
        class Response:
            status = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, count): raise AssertionError("must not read unbounded response")
        spec = {"bytes": 3, "sha256": sha256(b"abc"), "range_prefix": True,
                "full_file_bytes": 100, "url": "https://huggingface.co/datasets/mock/resolve/commit/file"}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AuditError, "bounded byte range"):
                cached_input(spec, Path(tmp), download=True, opener=lambda *args, **kwargs: Response())

    def test_exact_tar_member_and_checksum(self):
        doc = documents()[0]
        raw = json.dumps(doc).encode()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            member = tarfile.TarInfo("bench/mock.json")
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        specs = [{"path": "bench/mock.json", "sha256": sha256(raw), "model_id": "mock-A", "records": 4}]
        self.assertEqual(result_members(buffer.getvalue(), specs)[0][1], doc)
        bad = deepcopy(specs)
        bad[0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AuditError, "checksum"):
            result_members(buffer.getvalue(), bad)
        bad[0]["path"] = "../escape.json"
        with self.assertRaisesRegex(AuditError, "unsafe"):
            result_members(buffer.getvalue(), bad)
        with self.assertRaises(AuditError):
            result_members(buffer.getvalue()[:20], specs)
