"""Execute the original pinned research code at two outside values.

See OFFICIAL_NONZERO_PROTOCOL.md. Run only in an unprivileged, network-disabled
sandbox after staging the separately pinned source and dependencies.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from welfare_solver import rounded_weights, solve_exact, welfare
from fractions import Fraction

SOURCE='ed675a2dda0581af449a50aaafdeef72b05f03bf'
RAW='0b250d5f432bda276525fed3f046f6abbf3dd68f69e041c18fef95558d30ce54'
CAN='9b9b99c8ceeef5022ef4a1f55a469cda5b6396fe685f7102be10684dd7e7635b'
TOLERANCE=1e-8

def load_source(path):
    content=Path(path).read_bytes()
    digest=hashlib.sha1(f'blob {len(content)}\0'.encode()+content).hexdigest()
    if digest!=SOURCE:raise ValueError('unrecognized original source blob')
    spec=importlib.util.spec_from_file_location('pinned_ttc_game_dynamics',path)
    if spec is None or spec.loader is None:raise RuntimeError('unable to load pinned source')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module,digest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--input',required=True);ap.add_argument('--canonical',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    raw_bytes=Path(args.input).read_bytes();canonical_bytes=Path(args.canonical).read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest()!=RAW or hashlib.sha256(canonical_bytes).hexdigest()!=CAN:raise ValueError('input provenance mismatch')
    data=json.loads(raw_bytes);canonical=json.loads(canonical_bytes)
    if not(data['alpha']==.008 and data['baseline_frac']==.1 and data['beta']==1000 and data['outside_value']==0 and data['theta_values']==[1,4,8,16,32,64] and len(data['providers'])==9):raise ValueError('unexpected pinned experiment config')
    gm,source=load_source(args.source)
    config=gm.MarketConfig(alpha=.008,beta=1000,default_margin=.25,value_curve='linear',baseline_frac=.1)
    providers=[]
    for index,p in enumerate(data['providers']):
        if p['name']!=canonical['providers'][index]['name'] or len(p['actions'])!=6 or len(p['token_curve'])!=6:raise ValueError('provider alignment mismatch')
        accuracy=np.asarray([a['raw_acc'] for a in p['actions']],dtype=np.float64)
        token=np.asarray(p['token_curve'],dtype=np.float64)
        provider=gm.Provider(name=p['name'],base_model_key=p['name'],accuracy_curve=accuracy,token_curve=token,margin=.25)
        if provider.price_per_token!=p['price_per_token']:raise AssertionError('source pricing differs')
        for action,expected in enumerate(p['actions']):
            got=provider.get_economics(action,config)
            if any(float(got[key])!=expected[key] for key in ('q','p','c','V','raw_acc')) or got['q']-got['c']!=expected['W']:
                raise AssertionError(('source action mismatch',index,action))
        providers.append(provider)
    results={}
    for outside in ('0','0.006'):
        start=time.perf_counter()
        official=float(gm.get_global_max_welfare_brute_force_fast(providers,config,v0=float(outside)))
        official_seconds=time.perf_counter()-start
        canonical['outside']=outside
        rows,w0,v0=rounded_weights(canonical,80)
        omitted,witness,_=solve_exact(rows,w0,Fraction(0))
        proper,proper_witness,_=solve_exact(rows,w0,v0)
        if abs(official-float(omitted))>TOLERANCE:raise AssertionError(('source brute differs',outside,official,float(omitted)))
        strategies=np.asarray(witness,dtype=int)
        values=np.asarray([p.get_economics(witness[i],config)['V'] for i,p in enumerate(providers)])
        shares=gm.get_market_shares(values,config.beta,float(outside))
        source_eval=float(gm.calculate_current_welfare(providers,strategies,shares,config))
        actual=float(welfare(rows,w0,v0,witness));estimated_outside=float(outside)*(1-float(np.sum(shares)))
        if abs(source_eval+estimated_outside-actual)>1e-12:raise AssertionError(('witness welfare mismatch',outside))
        results[outside]={'source_brute_omitted_objective':official,'source_brute_seconds':official_seconds,
          'independent_omitted_objective':float(omitted),'independent_witness':witness,
          'source_welfare_at_independent_witness':source_eval,'outside_share_estimate':1-float(np.sum(shares)),
          'equation5_welfare_at_independent_witness':actual,'independent_eq5_optimum':float(proper),
          'independent_eq5_witness':proper_witness,'eq5_optimality_gap':float(proper)-actual}
    if abs(results['0']['source_brute_omitted_objective']-data['rerun_official_global_welfare'])>TOLERANCE:raise AssertionError('reported V0=0 control mismatch')
    out={'scope':'post-hoc model sensitivity; author function returns scalar, not actions; no claim reported V0=0 results change',
      'source_blob_sha1':source,'raw_input_sha256':RAW,'canonical_input_sha256':CAN,
      'numpy_version':np.__version__,'python_version':sys.version,'results':results}
    Path(args.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
