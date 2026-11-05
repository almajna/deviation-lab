#!/usr/bin/env python3
"""Build the replay fixture from the two byte-pinned recovered job receipts.

Usage: python3 apps/web/scripts/build_routing_fixture.py [receipt1 receipt2]
The default receipt locations are in /tmp; output is always the adjacent web fixture.
"""
import hashlib
import json
from pathlib import Path
import sys

JOBS = {
    '126972599498': '5c7be87debfcbbebf64ba8c96a78d038dcbeae43a5d1a367bf4ba57af94e8df3',
    '127013368999': '79c7773ace3f0db8d1de7d9adcce5864b75b428011ecd832dd52683719b58b04',
}
COMMIT = '44b85d0c5c3093543b1f911c6808836f16dd3a58'
RUN = '41944311832'
REPO = 'https://github.com/almajna/deviation-lab'
OUTPUT = Path(__file__).resolve().parents[1] / 'src/data/routing.json'
ROW_FIELDS = ('index', 'phase', 'provider', 'response_id', 'endpoint', 'latency_cache',
              'client_seconds', 'stream', 'ttft_seconds', 'error')
ENDPOINT_FIELDS = ('id', 'provider', 'raw_usage', 'forwarded_usage', 'configured_delay_seconds',
                   'server_elapsed_seconds', 'status')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def transform_case(case):
    rows = case['rows']
    require(len(rows) == 24, 'expected 24 rows')
    for index, row in enumerate(rows):
        require(row['index'] == index, 'row index mismatch')
        require(row['phase'] == ('warmup' if index < 4 else 'measured'), 'phase mismatch')
        endpoint = row['endpoint']
        require(row['provider'] == endpoint['provider'] and row['provider'] in ('A', 'B'), 'provider binding mismatch')
        if row['error'] is None:
            require(row['response_id'] == endpoint['id'] and endpoint['status'] == 200, 'response binding mismatch')
        else:
            require(row['response_id'] is None and endpoint['status'] != 200, 'error binding mismatch')
    measured = rows[4:]
    summary = case['summary']
    counts = {p: sum(r['provider'] == p and r['error'] is None for r in measured) for p in ('A', 'B')}
    errors = sum(r['error'] is not None for r in measured)
    require(summary['requests'] == 20 and summary['errors'] == errors, 'measured count mismatch')
    require(all(summary[p] == counts[p] for p in counts), 'measured provider count mismatch')
    require(summary['B_share'] == counts['B'] / 20, 'measured B share mismatch')
    clean_rows = []
    for row in rows:
        clean = {field: row[field] for field in ROW_FIELDS}
        clean['endpoint'] = {field: row['endpoint'][field] for field in ENDPOINT_FIELDS}
        clean_rows.append(clean)
    return {key: case[key] for key in ('mode', 'condition', 'seed', 'summary')} | {'rows': clean_rows}


def transform(raw, job_id):
    require(hashlib.sha256(raw).hexdigest() == JOBS[job_id], 'receipt SHA256 mismatch')
    data = json.loads(raw)
    require(data['source_commit'] == COMMIT and data['run_id'] == RUN, 'source binding mismatch')
    require(len(data['cases']) == 39 and data['checked']['cases_checked'] == 39
            and data['checked']['requests_checked'] == 936, 'receipt count mismatch')
    expected = {(mode, condition, seed)
                for mode in ('latency', 'shuffle', 'stream')
                for condition in ('honest', 'inflated', 'defended') for seed in (7, 11, 23)}
    expected |= {(mode, condition, 7)
                 for mode in ('tpm', 'rpm', 'cooldown', 'cold_stream')
                 for condition in ('honest', 'inflated', 'defended')}
    actual = [(c['mode'], c['condition'], c['seed']) for c in data['cases']]
    require(len(set(actual)) == 39 and set(actual) == expected, 'case matrix mismatch')
    return {'job_id': job_id, 'run_id': RUN, 'source_commit': COMMIT,
            'source_url': f'https://github.com/BerriAI/litellm/blob/{COMMIT}/litellm/router_strategy/lowest_latency.py#L312-L527',
            'job_url': f'{REPO}/actions/runs/{RUN}/job/{job_id}',
            'raw_sha256': JOBS[job_id], 'checked': data['checked'],
            'cases': [transform_case(c) for c in data['cases']]}


def build(paths):
    require(len(paths) == len(JOBS), 'expected both job receipts')
    return {'schema_version': 'routing-replay-v1', 'runs': [
        transform(Path(path).read_bytes(), job) for path, job in zip(paths, JOBS)]}


def main():
    paths = sys.argv[1:] or [f'/tmp/deviation-{job}-results.json' for job in JOBS]
    output = json.dumps(build(paths), indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    OUTPUT.write_text(output, encoding='utf-8')
    print(f'Wrote {OUTPUT}')


if __name__ == '__main__':
    main()
