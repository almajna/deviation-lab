"""Transparent train-only categorical router; no outcome-derived target signals."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import re
from deviation.contracts import prompt_group
from deviation.data.pipeline import digest
from deviation.markets.numeric import project_rational


def tokens(prompt):
    return frozenset(re.findall(r'[a-z][a-z0-9_]{1,}', prompt.casefold()))


def fold(prompt, count):
    return int(prompt_group(prompt), 16) % count


class TextForecaster:
    def __init__(self, rows, *, neighbors=5, smoothing=3):
        if not rows:
            raise ValueError('EMPTY_TRAINING_SHARD')
        self.rows = tuple(deepcopy(sorted(rows, key=lambda r: (r['task_id'], r['model_id']))))
        self.neighbors, self.smoothing = neighbors, smoothing
        self.models = sorted({r['model_id'] for r in rows})
        self.groups = {prompt_group(r['prompt']) for r in rows}
        self.priors = {}
        for m in self.models:
            c = Counter(int(2*r['quality']) for r in rows if r['model_id'] == m)
            self.priors[m] = [Fraction(c[k]+1, sum(c.values())+3) for k in range(3)]
        self.features = {r['task_id']: tokens(r['prompt']) for r in rows}
        self.sha256 = digest({'training': self.rows, 'neighbors': neighbors, 'smoothing': smoothing})

    def predict(self, task, D):
        if prompt_group(task['prompt']) in self.groups:
            raise ValueError('TRAIN_TARGET_GROUP_LEAKAGE')
        query = tokens(task['prompt'])
        result = {}
        for m in task['model_options']:
            scored = []
            for row in self.rows:
                if row['model_id'] != m:
                    continue
                feats = self.features[row['task_id']]
                similarity = Fraction(len(query & feats), max(1, len(query | feats)))
                scored.append((similarity, row['task_id'], row))
            scored.sort(key=lambda x: (-x[0], x[1]))
            mass = [self.smoothing*p for p in self.priors[m]]
            for weight, _, row in scored[:self.neighbors]:
                mass[int(2*row['quality'])] += weight
            result[m] = project_rational(mass, D)
        return result


def fit(rows, cfg, D):
    """Group-disjoint shards; training OOF calibration is not decision allocation."""
    n = cfg['agents']
    learners = [TextForecaster([r for r in rows if fold(r['prompt'], n) == j],
                neighbors=cfg['neighbors'], smoothing=cfg['smoothing']) for j in range(n)]
    full = TextForecaster(rows, neighbors=cfg['neighbors'], smoothing=cfg['smoothing'])
    oof = []
    F = cfg['inner_folds']
    for held in range(F):
        # A distinct salt avoids accidentally using the same folds for every shard.
        inner = lambda r: int(digest(['inner', prompt_group(r['prompt'])]),16) % F
        subset = [r for r in rows if inner(r) != held]
        model = TextForecaster(subset, neighbors=cfg['neighbors'], smoothing=cfg['smoothing'])
        tasks = {}
        for r in rows:
            if inner(r) == held:
                tasks[r['task_id']] = {'task_id':r['task_id'], 'prompt':r['prompt'], 'model_options':full.models}
        # Calibrate the pooled forecasting PROCEDURE with group-excluded shard models.
        shards = []
        for j in range(n):
            local = [r for r in subset if fold(r['prompt'],n)==j]
            shards.append(TextForecaster(local,neighbors=cfg['neighbors'],smoothing=cfg['smoothing']) if local else model)
        for task in sorted(tasks.values(),key=lambda t:t['task_id']):
            ps = [s.predict(task,D) for s in shards]
            labels = {r['model_id']:int(2*r['quality']) for r in rows if r['task_id']==task['task_id']}
            for m in full.models:
                counts = project_rational([sum(p[m][k] for p in ps) for k in range(3)],D)
                oof.append({'task_id':task['task_id'],'model_id':m,'counts':counts,'category':labels[m]})
    return learners, full, oof
