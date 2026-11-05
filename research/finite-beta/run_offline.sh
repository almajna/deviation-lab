#!/usr/bin/env bash
set -euo pipefail

# This shell is executed after dropping root and all Linux capabilities in a
# fresh network namespace; the original source is untrusted executable code.
test "$(id -u)" -ne 0
awk '/^CapEff:/ { if ($2 !~ /^0+$/) exit 1; seen=1 } END { if (!seen) exit 1 }' /proc/self/status
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
cd "$TASK_WORKSPACE/baseline/notebooks"
python - <<'PY'
import hashlib, nbformat, pathlib
original = pathlib.Path('GSM8K-demo.ipynb')
notebook = nbformat.read(original, as_version=4)
indices = [0, 2, 3, 6, 11, 22, 24, 26, 27]
selected = [notebook.cells[i] for i in indices]
for i, c in zip(indices, selected):
    print('SELECTED_CELL', i, hashlib.sha256(c.source.encode()).hexdigest())
    if c.cell_type == 'code':
        c.outputs = []
        c.execution_count = None
append = pathlib.Path('../../research/finite-beta/export_cell.py').read_text()
notebook.cells = selected + [nbformat.v4.new_code_cell(append)]
nbformat.write(notebook, 'finite-beta-selected.ipynb')
PY
jupyter nbconvert --to notebook --execute finite-beta-selected.ipynb --output finite-beta-executed.ipynb --ExecutePreprocessor.timeout=600
python - <<'PY'
import nbformat, pathlib
notebook = nbformat.read('finite-beta-executed.ipynb', as_version=4)
text = []
for cell in notebook.cells:
    for output in cell.get('outputs', []):
        if output.get('output_type') == 'stream':
            text.append(output.get('text', ''))
pathlib.Path('../notebook-streams.txt').write_text(''.join(text))
print(''.join(text))
pathlib.Path('../notebook-execution-succeeded.txt').write_text('Selected cells completed in this run; source cell hashes are in the job log.\n')
PY
cd "$TASK_WORKSPACE"
python research/finite-beta/analyze_curves.py --input baseline/finite-beta-input.json --output baseline/finite-beta-results.json
python research/finite-beta/certify_real.py --input baseline/finite-beta-canonical.json --output baseline/finite-beta-certificate.json --precision 80 --tolerance 1e-15
sha256sum baseline/finite-beta-input.json baseline/finite-beta-results.json baseline/finite-beta-canonical.json baseline/finite-beta-certificate.json baseline/notebooks/finite-beta-selected.ipynb baseline/notebooks/finite-beta-executed.ipynb > baseline/output-sha256.txt
