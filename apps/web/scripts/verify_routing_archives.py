#!/usr/bin/env python3
"""Rebuild the routing fixture from the original, hash-pinned Actions ZIPs."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import build_routing_fixture as fixture

ARCHIVES = (
    ('attempt-1-original.zip', '038bf0657b440fcab1c417cf187168755019e0c67fdd855656809facb3f4333c'),
    ('attempt-2-original.zip', '4a86895bc765e62e383bf3b370f40394fb6ead384728592a85c8d25db3fb936e'),
)
ROOT = Path(__file__).resolve().parents[3]


def read_archive(path, expected_sha):
    raw = path.read_bytes()  # Missing evidence must fail.
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f'archive SHA256 mismatch: {path}')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError(f'corrupt archive: {path}')
        if archive.namelist().count('results.json') != 1:
            raise ValueError(f'expected exactly one results.json: {path}')
        return archive.read('results.json')


def verify(directory):
    runs = [fixture.transform(read_archive(directory / name, digest), job)
            for (name, digest), job in zip(ARCHIVES, fixture.JOBS)]
    result = {'schema_version': 'routing-replay-v1', 'runs': runs}
    rebuilt = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if rebuilt != fixture.OUTPUT.read_bytes():
        raise ValueError('routing fixture differs from original archives')
    print('Both original archives verified; routing fixture matches exactly.')


if __name__ == '__main__':
    verify(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'artifacts/litellm-reality')
