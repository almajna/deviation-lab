"""Read only aggregate data from fixed verified archive; never execute it."""
import hashlib
import json
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

archive_path, output_path = map(Path, sys.argv[1:3])
assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == 'cb6ff8cbcabafac137673825e4e5212f0129768b18c4f912444d00ca99d644c3'
with zipfile.ZipFile(archive_path) as archive:
    members = [x for x in archive.infolist() if x.filename.rsplit('/', 1)[-1] == 'finite-beta-input.json']
    assert len(members) == 1 and members[0].file_size < 1_000_000
    raw = archive.read(members[0])
assert hashlib.sha256(raw).hexdigest() == '1fff54b2020398a74b540d8017c052e16ac5d105e2ef4edb18238f08cc8914df'
x = json.loads(raw)
assert x['beta'] == 1000 and x['outside_value'] == 0
assert x['theta_values'] == [1, 4, 8, 16, 32, 64]
assert len(x['providers']) == 9 and all(len(p['actions']) == 6 for p in x['providers'])
lines = ['9 6 1000 0', ' '.join(map(str, x['market_actions']))]
for provider in x['providers']:
    for a in provider['actions']:
        lines.append(str(Decimal.from_float(a['V'])) + ' ' + str(Decimal.from_float(a['W'])))
output_path.write_text('\n'.join(lines) + '\n')
print('VERIFIED_INPUT_SHA256', hashlib.sha256(raw).hexdigest())
print('NUMERIC_INPUT_SHA256', hashlib.sha256(output_path.read_bytes()).hexdigest())
