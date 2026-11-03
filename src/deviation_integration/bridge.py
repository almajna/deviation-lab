"""Explicit source migration receipts; never relabel observed live evidence."""
from copy import deepcopy
import re

from deviation.data.pipeline import digest
from deviation.markets.policies import SignalFollowing
from deviation.markets.runner import run
from deviation.simulator.runner import implementation_sha256
from deviation_llm_agents.experiments import metrics, Control
from deviation_llm_agents.harness import RecordedPolicy, source_hash, validate_audit
from .provenance import source_call

# Only declared source-dependent digests may rebind. All changes are retained.
# Packet/prompt/action/observation/protocol/split/data/predecision hashes cannot.
REBIND_SCALARS = {'sha256', 'implementation_sha256', 'receipt_sha256',
                  'engine_receipt_sha256', 'certificate_sha256'}


def rebind_path(path):
    if not path: return False
    if path[-1] in REBIND_SCALARS: return True
    if path in {('source_sha256',), ('basis_case',), ('trace', 'code_sha256')}: return True
    if len(path)==2 and path[0]=='counterexample_manifests': return True
    if len(path)==3 and path[0]=='cases' and type(path[1]) is int and path[2]=='evidence_sha256': return True
    return len(path) >= 2 and path[-2] in {'receipt_hashes', 'receipt_sha256'}


def same_science(old, new, path=(), changes=None):
    """Additional compatibility evidence, alongside separate strict replays."""
    if changes is None: changes = []
    if type(old) is not type(new): raise ValueError('TYPE_CHANGED: '+str(path))
    if isinstance(old, dict):
        if old.keys() != new.keys(): raise ValueError('FIELDS_CHANGED: '+str(path))
        for key in old: same_science(old[key], new[key], path+(key,), changes)
    elif isinstance(old, list):
        if len(old) != len(new): raise ValueError('LENGTH_CHANGED: '+str(path))
        for i, (a, b) in enumerate(zip(old, new)): same_science(a, b, path+(i,), changes)
    elif old != new:
        if not (isinstance(old, str) and re.fullmatch('[a-f0-9]{64}', old)
                and re.fullmatch('[a-f0-9]{64}', new) and rebind_path(path)):
            raise ValueError('SCIENTIFIC_VALUE_CHANGED: '+str(path))
        changes.append({'path': list(path), 'historical': old, 'integrated': new})
    return changes


def verify_source_episode(scenario, sidecar):
    return source_call('agents',
        'import json,sys; from deviation_llm_agents.harness import replay_episode; '
        'x=json.load(sys.stdin); print(json.dumps(replay_episode(x["scenario"],x["sidecar"])))',
        {'scenario': scenario, 'sidecar': sidecar})


def verify_source_pilot(bundle):
    return source_call('agents',
        'import json,sys; from deviation_llm_agents.pilot import verify_pilot; '
        'print(json.dumps(verify_pilot(json.load(sys.stdin))))', bundle)


def replay_recorded(scenario, sidecar):
    """Current engine checks exact original packet/prompt/action at each turn."""
    if sidecar['adapter_source_sha256'] != source_hash(): raise ValueError('ADAPTER_SOURCE_MISMATCH')
    if sidecar['sha256'] != digest({k:v for k,v in sidecar.items() if k != 'sha256'}):
        raise ValueError('SIDECAR_HASH_MISMATCH')
    if digest(scenario) != sidecar['scenario_sha256']: raise ValueError('SCENARIO_MISMATCH')
    validate_audit(sidecar['audit'])
    policy = RecordedPolicy(sidecar['audit'])
    policies = {a:SignalFollowing() for a in scenario['agents']}
    policies[sidecar['focal_agent']] = policy
    receipt = run(deepcopy(scenario), sidecar['engine_result']['mechanism'], policies=policies)
    if policy.cursor != len(sidecar['audit']['records']): raise ValueError('UNUSED_DECISIONS')
    changes = same_science(sidecar['engine_result'], receipt)
    if metrics(receipt, scenario, sidecar['focal_agent']) != sidecar['metrics']:
        raise ValueError('AGENT_METRICS_CHANGED')
    return {'execution_origin':'RECORDED_DECISION_REPLAY', 'new_inference_calls':0,
        'original_sidecar_sha256':sidecar['sha256'], 'audit_sha256':digest(sidecar['audit']),
        'engine_source_sha256':implementation_sha256(), 'receipt':receipt, 'rebindings':changes}


def replay_pilot(bundle):
    original = verify_source_pilot(bundle)
    episodes = []
    for episode in bundle['episodes']:
        result = replay_recorded(episode['scenario'], episode['sidecar'])
        controls = {}
        for key, old in episode['scripted_controls'].items():
            mechanism, control = key.split('/')
            actual = run(episode['scenario'], mechanism, policies={'focal':Control(control)})
            changes = same_science(old['receipt'], actual)
            if metrics(actual, episode['scenario']) != old['metrics']: raise ValueError('CONTROL_METRICS_CHANGED')
            controls[key] = {'receipt':actual, 'rebindings':changes}
        episodes.append({'setting':episode['setting'], 'recorded':result, 'scripted_controls':controls})
    return {'version':'integration-recorded-pilot-1', 'execution_origin':'RECORDED_DECISION_REPLAY',
        'new_inference_calls':0, 'original_pilot_sha256':bundle['sha256'],
        'original_strict_verification':original, 'episodes':episodes}


def compare_attack_bundle(old, new):
    changes={'bundle':same_science({k:v for k,v in old.items() if k!='receipts'},
                                  {k:v for k,v in new.items() if k!='receipts'})}
    if old['receipts'].keys()!=new['receipts'].keys(): raise ValueError('RECEIPT_COVERAGE_CHANGED')
    for name in old['receipts']:
        changes[name]=same_science(old['receipts'][name],new['receipts'][name])
    return changes
