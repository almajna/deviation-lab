#!/usr/bin/env python3
"""Project the immutable real-model economic receipt into a static replay."""
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'src/data/economic.json'
SOURCE = ROOT / 'artifacts/llm_agents/autonomous_pool.json.gz'
EXPECTED_SHA = 'bbd599423a88c36f3549e5bb80da72083e0a8797f373cb3beb66faee8caaac5c'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def build(raw):
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA, 'source archive hash mismatch')
    data = json.loads(gzip.decompress(raw))
    require(data['version'] == 'autonomous-pool-1' and len(data['episodes']) == 18, 'invalid source')
    summary = {(s['case'], s['condition']): s for s in data['summary']['episodes']}
    require(len(summary) == 18, 'duplicate or incomplete cases')
    episodes = []
    for ep in data['episodes']:
        key = (ep['case'], ep['condition'])
        s, a = summary[key], ep['analysis']
        require(ep['call']['error'] is None and s['focal_valid'] and s['rival_valid'], 'invalid inference')
        response = json.loads(ep['call']['response']['http_body'])
        choice = json.loads(response['message']['content'])['choice']
        report = [int(n) for n in choice.split(',')]
        require(report == s['focal_report'], 'response and summary disagree')
        require(a['checked']['claim'] == 'EXACT_FINITE_SUBGAME' and a['checked']['gap'] == [0, 1], 'uncertified optimum')
        require(a['certified_report'] == a['checked']['incumbent_commands'][0]['counts'], 'certificate action mismatch')
        require(a['checked']['lower'] == a['checked']['upper'] == s['optimal_expected_utility'], 'optimum mismatch')
        expected = s['expected_utility']
        optimal = s['optimal_expected_utility']
        require(Fraction(*optimal) - Fraction(*expected) == Fraction(a['regret']) == Fraction(s['regret']), 'regret mismatch')
        episodes.append({'case': key[0], 'condition': key[1], 'belief': s['belief'],
            'model_report': report, 'rival_report': s['rival_report'],
            'certified_report': a['certified_report'], 'allocation': s['allocation'],
            'expected_utility': expected, 'optimal_expected_utility': optimal,
            'realized_utility': s['realized_utility'], 'recorded_regret': float(Fraction(s['regret'])),
            'expected_gain_vs_signal': s['expected_gain_vs_signal'], 'certificate_sha256': a['certificate']['sha256']})
    require(set(summary) == {(i,c) for i in range(6) for c in ('truthful','utility_zero','utility_bonus')}, 'case coverage mismatch')
    return {'schema_version':'economic-replay-v1', 'source_sha256': EXPECTED_SHA,
        'source_url':'https://github.com/almajna/deviation-lab/blob/f940faef2b46c7f9f51b4c636963b58c8c751153/artifacts/llm_agents/autonomous_pool.json.gz',
        'protocol_url':'https://github.com/almajna/deviation-lab/blob/f940faef2b46c7f9f51b4c636963b58c8c751153/docs/AUTONOMOUS_ECONOMY.md',
        'episodes': episodes}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source', nargs='?', type=Path, default=SOURCE)
    p.add_argument('--check', action='store_true')
    args=p.parse_args()
    text=json.dumps(build(args.source.read_bytes()), indent=2, allow_nan=False)+'\n'
    if args.check:
        require(OUT.read_text() == text, 'fixture differs from source')
        print('Economic replay fixture matches archived receipt')
    else:
        OUT.write_text(text)
        print('Wrote', OUT)
if __name__ == '__main__':
    main()
