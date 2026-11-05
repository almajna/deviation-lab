#!/usr/bin/env python3
"""Check public release metadata and stream digest without reading outcomes."""
import hashlib
import json
import sys
from pathlib import Path

if len(sys.argv)!=4:
    raise SystemExit('usage: stage.py RELEASE.json ARCHIVE OUTPUT')
meta=json.loads(Path(sys.argv[1]).read_text())
if meta.get('tag_name')!='v1.0' or meta.get('draft') or meta.get('prerelease'):
    raise SystemExit('unexpected release tag or state')
assets=[x for x in meta.get('assets',[]) if x.get('name')=='agentops-bench-v1.0-pilot-traces.tar.gz']
if len(assets)!=1:
    raise SystemExit('missing/duplicated named release asset')
asset=assets[0]
h=hashlib.sha256()
with Path(sys.argv[2]).open('rb') as f:
    while True:
        b=f.read(1024*1024)
        if not b: break
        h.update(b)
actual=h.hexdigest()
if asset.get('size')!=Path(sys.argv[2]).stat().st_size:
    raise SystemExit('archive length differs from GitHub release metadata')
expected=asset.get('digest')
if not isinstance(expected,str) or not expected.startswith('sha256:'):
    raise SystemExit('upstream sha256 digest absent; stop before reading outcomes')
if expected!='sha256:'+actual:
    raise SystemExit('archive digest differs from GitHub release metadata')
Path(sys.argv[3]).write_text(json.dumps({'release_id':meta.get('id'),
    'tag':meta.get('tag_name'),'target_commitish':meta.get('target_commitish'),
    'published_at':meta.get('published_at'),'asset_id':asset.get('id'),
    'asset_name':asset.get('name'),'asset_size':asset.get('size'),
    'upstream_digest':expected,'computed_sha256':actual},indent=2,sort_keys=True)+'\n')
