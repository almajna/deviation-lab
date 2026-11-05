#!/usr/bin/env python3
"""Execute pinned upstream functions on public preview YAML and synthetic patches.

This runs only inside the no-network unprivileged GitHub Actions environment.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import yaml

root = Path('/tmp/joule-source')

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

harness = load(root / 'harness/run.py', 'joule_harness')
scorer = load(root / 'grading/score.py', 'joule_score')

observed = []
for tid in ('joule-001', 'joule-002', 'joule-004'):
    task = yaml.safe_load((root / 'tasks/preview' / tid / 'task.yaml').read_text())
    with tempfile.TemporaryDirectory() as directory:
        prompt = harness.write_prompt_file(task, Path(directory)).read_text()
    reference = task['ground_truth']['human_reference_pr_url']
    assert reference in prompt
    observed.append({'task':tid, 'reference_url_present':True,
                     'opened_at_utc':str(task['source']['opened_at_utc']),
                     'training_cutoff_utc':str(task['contamination']['training_cutoff_constraint_utc'])})

task = yaml.safe_load((root / 'tasks/preview/joule-001/task.yaml').read_text())
relevant = task['ground_truth']['relevant_files'][0]
scores = []
for replacement in (b'export const outcome: boolean = true;\n', b'export const outcome: boolean = false;\n'):
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        target = workspace / relevant
        target.parent.mkdir(parents=True)
        target.write_bytes(b'original\n')
        other = workspace / 'important-unrelated.py'
        other.write_bytes(b'original\n')
        before = harness.snapshot_file_state(workspace)
        target.write_bytes(replacement)
        other.unlink()
        after = harness.snapshot_file_state(workspace)
        diff = harness.diff_states(before, after)
        attention = scorer.compute_attention({'file_diff':diff}, task)
        assert attention['attention_f1'] == 1.0
        assert 'important-unrelated.py' in diff['removed']
        scores.append({'f1':attention['attention_f1'], 'removed':diff['removed'],
                       'replacement_sha256':hashlib.sha256(replacement).hexdigest()})
assert scores[0]['replacement_sha256'] != scores[1]['replacement_sha256']
print(json.dumps({'prompt_checks':observed, 'synthetic_patch_checks':scores,
                  'actual_agent_behavior_observed':False}, sort_keys=True, indent=2))
