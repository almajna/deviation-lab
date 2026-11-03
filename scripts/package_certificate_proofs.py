"""Preserve all generated proof JSON exactly in deterministic gzip containers."""
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import sys


def main():
    source, target = map(Path, sys.argv[1:3])
    target.mkdir(parents=True, exist_ok=True)
    (target/"proofs").mkdir(exist_ok=True)
    (target/"examples").mkdir(exist_ok=True)
    for name in ["results.json", "results.csv", "timings.json", "ordinary_exact.json", "ordinary_exact_timings.json"]:
        if (source/name).exists():
            shutil.copyfile(source/name, target/name)
    results = json.loads((source/"results.json").read_text())
    manifest = {"version": "independent-certificate-proof-archive-1",
                "source_sha256": results["source_sha256"], "results_sha256": results["sha256"], "proofs": []}
    compressed_total, raw_total = 0, 0
    for row in results["rows"]:
        case = row["case"]
        raw = (source/"proofs"/(case+".json")).read_bytes()
        certificate = json.loads(raw)
        assert certificate["sha256"] == row["certificate"]["sha256"]
        buf = io.BytesIO()
        with gzip.GzipFile(filename="", fileobj=buf, mode="wb", mtime=0, compresslevel=9) as stream:
            stream.write(raw)
        compressed = buf.getvalue()
        (target/"proofs"/(case+".json.gz")).write_bytes(compressed)
        manifest["proofs"].append({"case": case, "profile": row["profile"], "seed": row["seed"],
            "mechanism": row["mechanism"], "certificate_sha256": certificate["sha256"],
            "uncompressed_bytes": len(raw), "json_sha256": sha256(raw).hexdigest(),
            "gzip_sha256": sha256(compressed).hexdigest()})
        compressed_total += len(compressed)
        raw_total += len(raw)
        if row["profile"] == "base" and row["seed"] == 101:
            (target/"examples"/(case+".json")).write_bytes(raw)
    (target/"proof_manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2)+"\n")
    print(json.dumps({"proofs": len(manifest["proofs"]), "raw_bytes": raw_total, "gzip_bytes": compressed_total}))


if __name__ == "__main__":
    main()
