#!/usr/bin/env python3
"""Independent exact-protocol recomputation over the public AgentOps archive.

No upstream code or model outputs are executed. Only aggregate statistics are
emitted. This is the same fixed comparison, not a new significance test.
"""
import collections
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys
import tarfile

EXPECTED = 'e185bfd037fa9fa5727dbae0eb8eba421dfb5011dfec6f4dc60b111d51e7a85f'


def h(*items):
    return hashlib.sha256('|'.join(map(str, items)).encode()).digest()


def read_data(file):
    if hashlib.sha256(pathlib.Path(file).read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('source hash mismatch')
    rows = {}
    report_count = 0
    with tarfile.open(file, 'r:gz') as tf:
        for info in tf:
            path = pathlib.PurePosixPath(info.name)
            if path.is_absolute() or '..' in path.parts or info.islnk():
                raise ValueError('unsafe source')
            if info.issym() or path.name.startswith('._'):
                continue
            if (not info.isfile() or '_combined' in path.parts
                    or not path.name.endswith('_report.json')):
                continue
            report = json.load(tf.extractfile(info))
            report_count += 1
            for item in report['results']:
                if item['agent_id'] != report['agent_id']:
                    raise ValueError('agent mismatch')
                if item['condition'] != 'clean':
                    continue
                key = (item['task_id'], item['agent_id'], item['run_number'])
                score = float(item['scores']['completion'])
                cost = float(item['scores']['cost']['cost_usd'])
                if key in rows or not (math.isfinite(score) and 0 <= score <= 1
                                       and math.isfinite(cost) and cost >= 0):
                    raise ValueError('invalid outcome')
                rows[key] = score, cost
    tasks = sorted({k[0] for k in rows}, key=lambda x: (h('AOB-QUERY-V1', x), x))
    agents = sorted({k[1] for k in rows})
    if report_count != 8 or len(tasks) != 100 or len(agents) != 8 or len(rows) != 2400:
        raise ValueError('incomplete matrix')
    for t in tasks:
        for a in agents:
            if len([k for k in rows if k[0] == t and k[1] == a]) != 3:
                raise ValueError('incomplete repetitions')
    return rows, tasks, agents


def verify(rows, tasks, agents):
    development, evaluation = set(tasks[:50]), tasks[50:]
    available_costs = [v[1] for k, v in rows.items() if k[0] in development]
    low, high = min(available_costs), max(available_costs)
    if low >= high:
        raise ValueError('zero development range')

    def value(r):
        return r[0] - 0.05 * (r[1] - low) / (high - low)

    totals = {p: {'utility': [], 'completion': [], 'cost': [], 'oracle': 0,
                  'selections': collections.Counter()} for p in ('adaptive', 'uniform')}
    difference = []
    for task in evaluation:
        incoming, heldkeys = {}, {}
        for agent in agents:
            indices = sorted((k[2] for k in rows if k[:2] == (task, agent)),
                             key=lambda r: (h('AOB-REPEAT-V1', task, agent, r), r))
            incoming[agent] = [rows[(task, agent, r)] for r in indices[:2]]
            heldkeys[agent] = (task, agent, indices[2])
        rank_key = lambda a: (-value(incoming[a][0]), a)
        adaptive_extra = sorted(agents, key=rank_key)[:4]
        uniform_extra = sorted(agents, key=lambda a: (h('AOB-UNIFORM-V1', task, a), a))[:4]
        selected, spent = {}, {}
        for policy, extras in (('adaptive', adaptive_extra), ('uniform', uniform_extra)):
            utility = {a: statistics.mean(value(r) for r in incoming[a][:1 + (a in extras)])
                       for a in agents}
            chosen = min(agents, key=lambda a: (-utility[a], a))
            assert sum(1 + (a in extras) for a in agents) == 12
            selected[policy] = chosen
            spent[policy] = sum(r[1] for a in agents for r in incoming[a][:1 + (a in extras)])
        # Neither policy may inspect the held-back reference before both select.
        held = {agent: rows[key] for agent, key in heldkeys.items()}
        oracle = min(agents, key=lambda a: (-value(held[a]), a))
        for policy in ('adaptive', 'uniform'):
            chosen = selected[policy]
            out = totals[policy]
            out['utility'].append(value(held[chosen]))
            out['completion'].append(held[chosen][0])
            out['cost'].append(spent[policy])
            out['oracle'] += chosen == oracle
            out['selections'][chosen] += 1
        difference.append(value(held[selected['adaptive']]) - value(held[selected['uniform']]))
    rng = random.Random(26061105)
    boot = sorted(statistics.mean(difference[rng.randrange(50)] for _ in range(50))
                  for _ in range(5000))
    return {
        'source_sha256': EXPECTED,
        'development_min_cost': low,
        'development_max_cost': high,
        'difference_mean': statistics.mean(difference),
        'difference_median': statistics.median(difference),
        'difference_signs': [sum(x > 0 for x in difference), sum(x == 0 for x in difference),
                             sum(x < 0 for x in difference)],
        'bootstrap_95': [boot[124], boot[4874]],
        'policies': {p: {'mean_utility': statistics.mean(o['utility']),
                         'mean_completion': statistics.mean(o['completion']),
                         'total_cost': sum(o['cost']), 'oracle_agreement': o['oracle'],
                         'selections': o['selections']} for p, o in totals.items()},
    }


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: verify.py SOURCE_ARCHIVE OUTPUT_JSON')
    rows, tasks, agents = read_data(sys.argv[1])
    pathlib.Path(sys.argv[2]).write_text(json.dumps(verify(rows, tasks, agents), indent=2,
                                                    sort_keys=True) + '\n')
