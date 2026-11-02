"""Synthetic CLI integration: real cache/archive/validator/output path, no network."""
from contextlib import redirect_stdout
import gzip
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch

from deviation.data.__main__ import main
from deviation.data.acquire import sha256
from deviation.data.pipeline import digest


class TestAuditIntegration(unittest.TestCase):
    def test_synthetic_cli_writes_reproducible_audit_artifacts(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "llmrouterbench_mock.json").read_text())
        self.assertEqual(fixture["data_kind"], "SYNTHETIC_FIXTURE")
        docs = fixture["documents"]
        # One valid-looking upstream failure tests rejection -> overlap -> cohort.
        docs[1]["records"][3]["raw_output"] = "Generation failed: synthetic integration failure"
        members = []
        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
            for doc in docs:
                raw = json.dumps(doc, sort_keys=True).encode()
                path = f"synthetic/{doc['model_name']}.json"
                entry = tarfile.TarInfo(path)
                entry.size = len(raw)
                archive.addfile(entry, io.BytesIO(raw))
                members.append({"path": path, "sha256": sha256(raw),
                                "model_id": doc["model_name"], "records": 4})
        archive_bytes = gzip.compress(tar_bytes.getvalue(), mtime=0)
        questions = b"\n".join(json.dumps({"prompt": row["origin_query"]}).encode()
                                 for row in docs[0]["records"]) + b"\n"
        # Marker bytes only: no pickle object or deserialization is involved.
        payloads = {"llm_archive_prefix": archive_bytes,
                    "arena_questions": questions, "router_pickle_prefix": b"\x80\x05"}
        manifest = {
            "data_kind": "SYNTHETIC_FIXTURE", "sources": [{"name": "SYNTHETIC_FIXTURE"}],
            "llm_sample": {"revision": "a" * 40, "members": members},
            "routerbench": {"revision": "b" * 40},
            "empirical_gate_blockers": ["Synthetic integration test cannot approve empirical research."],
            "inputs": {name: {"bytes": len(raw), "sha256": sha256(raw)}
                       for name, raw in payloads.items()},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "cache"
            cache.mkdir()
            for raw in payloads.values():
                (cache / (sha256(raw) + ".bin")).write_bytes(raw)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            snapshots = []
            for run in ["first", "second"]:
                out = root / run
                args = ["deviation.data", "--manifest", str(manifest_path),
                        "--cache", str(cache), "--out", str(out)]
                stdout = io.StringIO()
                with patch("sys.argv", args), redirect_stdout(stdout), \
                        patch("socket.socket", side_effect=AssertionError("network forbidden in integration test")):
                    main()
                self.assertIn("empirical gate: NO_GO", stdout.getvalue())
                self.assertEqual({p.name for p in out.iterdir()},
                                 {"data_audit.json", "data_manifest.json", "splits.json"})
                snapshots.append({p.name: p.read_bytes() for p in out.iterdir()})
                report = json.loads(snapshots[-1]["data_audit.json"])
                receipt = json.loads(snapshots[-1]["data_manifest.json"])
                splits = json.loads(snapshots[-1]["splits.json"])
                self.assertEqual(report["data_kind"], "SYNTHETIC_FIXTURE")
                self.assertEqual(report["technical_pairing"], "PASS")
                self.assertEqual(report["empirical_gate"], "NO_GO")
                self.assertEqual(report["blockers"], manifest["empirical_gate_blockers"])
                sample = report["llmrouterbench"]
                self.assertEqual(sample["source_records"], 8)
                self.assertEqual(sample["raw_aligned_tasks"], 4)
                self.assertEqual(sample["original_prompt_matches"], 4)
                self.assertEqual(sample["valid_records"], 7)
                self.assertEqual(sample["complete_paired_tasks"], 3)
                self.assertEqual(sample["complete_cohort_records"], 6)
                self.assertEqual(sample["incomplete_tasks"], 1)
                self.assertEqual(sample["rejection_counts"], {"missing or failed model output": 1})
                self.assertEqual(sample["missing_by_model"], {"mock-A": 0, "mock-B": 1})
                self.assertEqual(sample["overlap_matrix"],
                                 {"mock-A": {"mock-A": 4, "mock-B": 3},
                                  "mock-B": {"mock-A": 3, "mock-B": 3}})
                self.assertEqual(sample["cost_unit"], "synthetic_units")
                self.assertEqual(sample["cost_basis"], "synthetic_fixture")
                self.assertFalse(sample["cost_available_before_decision"])
                self.assertEqual(report["decision_fields"], ["task_id", "prompt", "model_options"])
                self.assertEqual(receipt["source_manifest_sha256"], digest(manifest))
                self.assertEqual(receipt["selected_members"], members)
                self.assertFalse(receipt["raw_data_redistributed"])
                for name, spec in receipt["inputs"].items():
                    self.assertEqual(spec["actual_sha256"], sha256(payloads[name]))
                self.assertEqual(splits["status"], "EXPLORATORY_NOT_FROZEN")
                self.assertEqual(len(splits["tasks"]), 3)
                split_digest = digest({k: v for k, v in splits.items() if k != "sha256"})
                self.assertEqual(splits["sha256"], split_digest)
                self.assertEqual(report["split_manifest_sha256"], split_digest)
                self.assertEqual(sum(report["split_counts"].values()), 3)
                groups = {}
                for assignment in splits["tasks"].values():
                    groups.setdefault(assignment["group_id"], set()).add(assignment["split"])
                self.assertEqual(sorted(len(values) for values in groups.values()), [1, 1])
                serialized = b"".join(snapshots[-1].values())
                self.assertNotIn(str(root).encode(), serialized)
                self.assertNotIn(b"Mock question", serialized)
            self.assertEqual(snapshots[0], snapshots[1])
