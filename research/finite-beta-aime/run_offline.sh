#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -ne 0
awk '/^CapEff:/ { if ($2 !~ /^0+$/) exit 1; seen=1 } END { if (!seen) exit 1 }' /proc/self/status
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
cd "$TASK_WORKSPACE"
# Fail before upstream loader could print an offending raw line on bad JSON.
python - <<'PY'
import json, pathlib, sys
files = sorted(pathlib.Path('baseline/final_runs/AIME').glob('*.jsonl'))
if len(files) != 12:
    raise SystemExit('unexpected number of input traces')
for path in files:
    count = 0
    with path.open(encoding='utf-8') as source:
        for index, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except (ValueError, UnicodeError):
                print('INVALID_JSON file', path.name, 'line', index)
                sys.exit(1)
            count += 1
    print('JSON_PREFLIGHT', path.name, 'records', count)
PY
cd "$TASK_WORKSPACE/baseline/notebooks"
python - <<'PY'
import hashlib, nbformat, pathlib
notebook = nbformat.read('AIME-demo.ipynb', as_version=4)
indices = [0, 2, 3, 6, 11, 22, 24, 26, 27]
selected = [notebook.cells[i] for i in indices]
for i, c in zip(indices, selected):
    print('SELECTED_CELL', i, hashlib.sha256(c.source.encode()).hexdigest())
    if c.cell_type == 'code':
        c.outputs = []
        c.execution_count = None
append = pathlib.Path('../../research/finite-beta-aime/export_cell.py').read_text()
notebook.cells = selected + [nbformat.v4.new_code_cell(append)]
nbformat.write(notebook, 'aime-selected.ipynb')
PY
# Never upload/print notebook streams or raw exceptions: benchmark-derived text
# is restricted to the ephemeral sandbox. Only aggregate receipt is retained.
if ! jupyter nbconvert --to notebook --execute aime-selected.ipynb --output aime-executed.ipynb --ExecutePreprocessor.timeout=600 > /tmp/aime-nbconvert-log.txt 2>&1; then
  echo 'AIME notebook execution failed; raw diagnostics intentionally withheld.' >&2
  exit 1
fi
test -f ../finite-beta-input.json
printf '%s\n' 'Selected source cells completed; aggregate output only.' > ../aime-notebook-success.txt
cd "$TASK_WORKSPACE"
python research/finite-beta-aime/analyze_curves.py --input baseline/finite-beta-input.json --output baseline/finite-beta-results.json
python research/finite-beta-aime/certify_real.py --input baseline/finite-beta-canonical.json --output baseline/finite-beta-certificate.json --precision 80 --tolerance 1e-15
sha256sum baseline/finite-beta-input.json baseline/finite-beta-results.json baseline/finite-beta-canonical.json baseline/finite-beta-certificate.json > baseline/output-sha256.txt
