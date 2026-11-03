"""Immutable Git sources; no network, inference or expected-source overrides."""
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

HISTORICAL_PIN = "b67bf93b7a23c5c5d62e9d7f04ddfb614cfb0d81"
BASE_MAIN = "8521252fceb8eb9cb3877badc9fbbd29bf995e1a"
HISTORICAL_HARNESS_SHA = "e0dc9e86f27be854f560e186edad318f8e6ec4ff5819b3c4ab1419a63606dd64"
HISTORICAL_ENGINE_SHA = "7d88cd5dfa1d0bd72f0d7c9796a06206ceb1451228171ad67b1041b8a6049b78"


def root():
    return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+"\n")


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preservation():
    """Check all main runtime/evidence and original harness evidence byte-for-byte."""
    result = {}
    for name, pin, prefixes, exact in [
        ("main", BASE_MAIN, ("src/", "artifacts/", "experiments/"), {"README.md", "LICENSE", "docs/CONTRACTS.md"}),
        ("research", HISTORICAL_PIN, ("src/deviation_research/", "research/", "artifacts/research/"), set()),
    ]:
        protected = {}
        entries = subprocess.check_output(["git", "ls-tree", "-rz", pin], cwd=root()).split(b"\0")
        for entry in entries:
            if not entry: continue
            meta, raw_path = entry.split(b"\t"); path = raw_path.decode()
            if not path.startswith(prefixes) and path not in exact: continue
            mode, kind, expected = meta.decode().split()
            data = (root()/path).read_bytes()
            actual = hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
            if kind != "blob" or actual != expected:
                raise ValueError("PROTECTED_SOURCE_OR_EVIDENCE_CHANGED: "+name+":"+path)
            protected[path] = expected
        result[name] = {"commit":pin, "files":protected}
    return result


@lru_cache(maxsize=1)
def historical_source():
    actual = subprocess.check_output(["git","rev-parse",HISTORICAL_PIN+"^{commit}"], cwd=root(), text=True).strip()
    if actual != HISTORICAL_PIN: raise ValueError("HISTORICAL_COMMIT_IDENTITY")
    temporary = tempfile.TemporaryDirectory(prefix="deviation-harness-original-")
    data = subprocess.check_output(["git","archive",HISTORICAL_PIN], cwd=root())
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for m in archive.getmembers():
            p = Path(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise ValueError("UNSAFE_HISTORICAL_ARCHIVE")
        archive.extractall(temporary.name, filter="data")
    return temporary


def historical_environment():
    env = os.environ.copy(); env.pop("PYTHONHOME",None)
    env["PYTHONPATH"] = str(Path(historical_source().name)/"src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def historical_review(payload):
    """Run the original numerical reviewer at its literal source and package hashes.

    This is pure verification of supplied synthetic records. Producer routines
    are disabled INSIDE the child, so migrated legacy tests retain their force.
    No caller-supplied source override or arbitrary command is accepted.
    """
    code = '''import json,sys
from unittest.mock import patch
from deviation_research.records import source_hash
from deviation.verification.checker import source_sha
from deviation_research.review import review
assert source_hash() == %r
assert source_sha() == %r
with patch('deviation.attacks.certified.solver.solve',side_effect=AssertionError('optimizer forbidden')), patch('deviation.attacks.game.Game.expected',side_effect=AssertionError('producer payoff forbidden')), patch('deviation.attacks.game.Game.allocation',side_effect=AssertionError('producer allocation forbidden')):
 print(json.dumps(review(json.load(sys.stdin)),allow_nan=False))
''' % (HISTORICAL_HARNESS_SHA,HISTORICAL_ENGINE_SHA)
    result = subprocess.run([sys.executable,"-B","-s","-c",code],
        input=json.dumps(payload,allow_nan=False), cwd=historical_source().name,
        env=historical_environment(), text=True, capture_output=True, timeout=45)
    if result.returncode:
        raise ValueError("HISTORICAL_REVIEW_REJECTED: "+result.stderr[-2000:])
    return json.loads(result.stdout)
