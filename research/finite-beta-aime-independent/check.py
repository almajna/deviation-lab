"""Check independently enumerated totals against original frozen receipt."""
from decimal import Decimal
from pathlib import Path
import json
import sys
import zipfile

archive_path, output_path = map(Path, sys.argv[1:3])
with zipfile.ZipFile(archive_path) as archive:
    matches = [x for x in archive.namelist() if x.rsplit('/', 1)[-1] == 'finite-beta-results.json']
    assert len(matches) == 1
    expected = json.loads(archive.read(matches[0]))
lines = {line.split()[0]: line.split()[1:] for line in output_path.read_text().splitlines()}
assert int(lines['profiles'][0]) == 6**9
best = Decimal(lines['best'][0])
market = Decimal(lines['market'][0])
comp = Decimal(lines['componentwise'][0])
assert abs(best - Decimal(expected['fractional_global_optimum']['welfare_decimal'])) < Decimal('1e-15')
assert abs(best - Decimal(str(expected['published_global_enumeration']['rerun_float32']))) < Decimal('1e-8')
assert abs(market - Decimal(expected['published_market']['welfare_decimal'])) < Decimal('1e-15')
assert abs(comp - Decimal(expected['componentwise_individual_optimum']['welfare_decimal'])) < Decimal('1e-15')
assert [int(x) for x in lines['best_actions']] == expected['fractional_global_optimum']['actions']
print('INDEPENDENT_FULL_ENUMERATION_PASS', json.dumps(lines, sort_keys=True))
