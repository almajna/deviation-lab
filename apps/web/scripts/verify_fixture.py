"""Verify the handoff without installing or claiming a working frontend."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
web = root / "apps/web"
manifest = json.loads((web / "fixtures/manifest.json").read_text())
for name, expected in manifest["approved_files_sha256"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
pack = json.loads((root / "tests/fixtures/contracts_v0_2.json").read_text())
p = web / "fixtures/gate-a.synthetic.json"
assert json.loads(p.read_text()) == pack["trace"]
assert p.read_text() == json.dumps(pack["trace"], indent=2, sort_keys=True) + "\n"
assert hashlib.sha256(p.read_bytes()).hexdigest() == manifest["public_trace_sha256"]
for forbidden in ["private_signal", "sealed_outcomes", "ground_truth", "raw_output"]:
    assert forbidden not in p.read_text(), forbidden
assert pack["trace"]["data_kind"] == "SYNTHETIC"
print("Pinned v0.2 contracts and public SYNTHETIC fixture verified; frontend not implemented")
