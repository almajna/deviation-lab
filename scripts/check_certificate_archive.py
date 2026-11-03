"""Check every retained compressed proof without calling any optimizer."""
from hashlib import sha256
import gzip
import json
from pathlib import Path
import sys

from deviation.verification.checker import check
from deviation.verification.fixtures import fixture


def main():
    folder = Path(sys.argv[1])
    protocol = json.loads(Path("experiments/certificate_benchmark.json").read_text())
    manifest = json.loads((folder/"proof_manifest.json").read_text())
    profiles = {p["id"]: p for p in protocol["profiles"]}
    count = 0
    for entry in manifest["proofs"]:
        case = entry["case"]
        path = folder/"proofs"/(case+".json.gz")
        data = path.read_bytes()
        assert sha256(data).hexdigest() == entry["gzip_sha256"]
        expanded = gzip.decompress(data)
        assert len(expanded) == entry["uncompressed_bytes"]
        assert sha256(expanded).hexdigest() == entry["json_sha256"]
        certificate = json.loads(expanded)
        assert certificate["sha256"] == entry["certificate_sha256"]
        game = fixture(profiles[entry["profile"]], entry["seed"], entry["mechanism"])
        check(game, certificate)
        count += 1
    print(json.dumps({"independently_checked": count, "source_sha256": manifest["source_sha256"]}))


if __name__ == "__main__":
    main()
