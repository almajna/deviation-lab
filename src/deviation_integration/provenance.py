"""Immutable source retrieval from local Git objects; no network or inference."""
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

PINS = {
    'phase2': '390e1b7a63cf31306d78815e381f81ec7245f8d6',
    'phase3': '1afe571d84831d9d0868dbdef5ae46df1c4c0b2d',
    'phase4': '8cf8bd318c1a28533aeb88c52c6ad4092aec119e',
    'benchmark': 'fd0b412039639cbf53d32960bc18d60cafcbb9d9',
    'producer': '3151edb463484498a5b686bf607dff4f062d66a4',
    'verification': 'f199007eca28097f70115c5f9a20276b046fe95c',
    'agents': 'cb9347fe5580bf4e3a83bc81cc99fe620098da3d',
}


def repository():
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    if not (root/'experiments/certificate_benchmark.json').is_file():
        raise ValueError('RUN_FROM_INTEGRATION_REPOSITORY')
    return root


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def source(name):
    root = repository()
    temporary = tempfile.TemporaryDirectory(prefix='deviation-source-'+name+'-')
    data = subprocess.check_output(['git', 'archive', PINS[name]], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            p = Path(member.name)
            if p.is_absolute() or '..' in p.parts or not (member.isfile() or member.isdir()):
                raise ValueError('UNSAFE_SOURCE_ARCHIVE')
        archive.extractall(temporary.name, filter='data')
    return temporary


def environment(name=None):
    env = os.environ.copy()
    env.pop('PYTHONHOME', None)
    if name:
        env['PYTHONPATH'] = str(Path(source(name).name)/'src')
    else:
        env.pop('PYTHONPATH', None)
    return env


def source_call(name, code, value):
    response = subprocess.run([sys.executable, '-c', code], input=json.dumps(value), text=True,
        capture_output=True, check=True, cwd=source(name).name, env=environment(name))
    return json.loads(response.stdout)


def preservation_audit():
    """Check every upstream artifact, protocol, runtime file and math document."""
    root = repository(); checks = {}
    for name in ['phase4', 'benchmark', 'producer', 'verification', 'agents']:
        listing = subprocess.check_output(['git', 'ls-tree', '-r', '-z', PINS[name]], cwd=root)
        files = {}
        for entry in listing.split(b'\0'):
            if not entry: continue
            metadata, raw_path = entry.split(b'\t'); path = raw_path.decode()
            protected = path.startswith(('artifacts/', 'experiments/', 'src/')) or path in {
                'README.md', 'LICENSE', 'docs/CONTRACTS.md', 'docs/CONTRACTS_V0_3.md',
                'docs/CERTIFIED_ATTACKS.md', 'docs/INDEPENDENT_CERTIFICATE_CHECKER.md',
                'docs/PHASE_5_PROTOCOL.md'}
            if not protected: continue
            mode, kind, expected = metadata.decode().split()
            # All five pinned READMEs are identical; retain and check their
            # historical bytes without freezing the present-day introduction.
            retained = root/'docs/history/README-8521252.md' if path == 'README.md' else root/path
            data = retained.read_bytes()
            actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if kind != 'blob' or actual != expected:
                raise ValueError('UPSTREAM_BYTES_CHANGED: '+name+':'+path)
            files[path] = expected
        checks[name] = {'commit': PINS[name], 'files': files}
    return checks
