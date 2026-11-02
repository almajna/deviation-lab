#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation demo --out /tmp/deviation_bootstrap_trace.json
python3 - <<'PY'
import json
p = '/tmp/deviation_bootstrap_trace.json'
d = json.load(open(p, encoding='utf-8'))
assert d['data_kind'] == 'SYNTHETIC'
assert d['metrics']['cost'] <= d['config']['budget']
print(f'Validated synthetic starter trace: {p}')
PY
