"""Controlled exogenous belief-error environments, not empirical LLM agents.

Beliefs are formed before and independently of sampled outcomes. 'Quality' is
belief calibration/misspecification, not a claimed informative signal channel.
Shared vs independent belief perturbations control correlation of forecast errors.
"""
from copy import deepcopy
from decimal import Decimal
import random
import secrets

from deviation.contracts import prompt_group
from deviation.data.pipeline import digest
from deviation.markets.engine import market_id
from deviation.markets.numeric import project_rational


def environment(profile, seed, *, realization_seed=None):
    # This seed belongs to the evaluator, never the public schedule or policy.
    # A frozen scenario already stores outcomes for replay. Research protocols
    # may disclose this simulation seed after the run; it is not a credential.
    realization_seed=secrets.randbits(128) if realization_seed is None else realization_seed
    rng=random.Random(seed)
    D=profile.get("D",3);N=profile.get("tasks",2);A=profile.get("aliases",1)
    models=["m0","m1"]
    tasks=[{"task_id":f"task-{i}","prompt":f"Synthetic decision prompt {i}","model_options":models} for i in range(N)]
    training=[];calibration=[];groups={}
    for i in range(2):
        prompt=f"Synthetic training prompt {i}";groups[prompt_group(prompt)]="train"
        for j,m in enumerate(models):
            training.append({"task_id":f"train-{i}","prompt":prompt,"model_id":m,
                "cost_decimal":str(Decimal(j+1)/Decimal(10**9)),"cost_unit":"synthetic_units"})
            calibration.append({"task_id":f"train-{i}","model_id":m,"counts":[1,1,D-2],"category":j+1})
    for t in tasks:groups[prompt_group(t["prompt"]) ]="validation"
    def distribution(source=rng):
        a=source.randrange(D+1);b=source.randrange(D-a+1)
        return [a,b,D-a-b]
    theta={market_id(t["task_id"],m):distribution() for t in tasks for m in models}
    # The private controller beliefs may be misspecified. Neither they nor the
    # opponent errors are conditioned on any realized label.
    mix=profile.get("belief_quality",100)
    shared_rng=random.Random(seed+101);own_rng=random.Random(seed+211);honest_rng=random.Random(seed+307)
    common={mid:distribution(shared_rng) for mid in theta}
    own={mid:project_rational([mix*x+(100-mix)*z for x,z in zip(p,common[mid] if profile.get("correlated",True) else distribution(own_rng))],D) for mid,p in theta.items()}
    honest={}
    for mid,p in theta.items():
        noise=common[mid] if profile.get("correlated",True) else distribution(honest_rng)
        honest[mid]=project_rational([mix*x+(100-mix)*z for x,z in zip(p,noise)],D)
    total=profile.get("capital",8)
    agents={"h0":{"controller":"honest","wallet":16,"signals":honest,"decline_report":False}}
    for a in range(A):
        agents[f"z{a}"]={"controller":"strategic","wallet":total//A+int(a<total%A),
            "signals":deepcopy(own),"decline_report":False}
    Q=profile.get("quantity",2);b=profile.get("b",3)
    economics={"b":b,"report_denominator":D,"score_scale":1,"price_denominator":3_000_000,
        "fee":profile.get("fee",0),"order_limit":Q,"agent_position_limit":100,
        "cell_position_limit":1000,"action_limit":100,"candidate_limit":10000,
        "rounds":profile.get("rounds",1),"sponsor_cap":100_000}
    favorite_rng=random.Random(seed+401)
    weights={t["task_id"]:{favorite_rng.choice(models):profile.get("external",6)} for t in tasks}
    C=2*N;slots=C*economics["rounds"]
    controllers={"honest":{"cash_cap":16,"token_cap":C,"action_cap":slots,"position_cap":100,
        "external_weights":{},"effort_per_attempt":0},
        "strategic":{"cash_cap":total,"token_cap":A*C,"action_cap":A*slots,"position_cap":100,
            "external_weights":weights,"effort_per_attempt":profile.get("effort",0)}}
    scenario={"execution_version":"markets-1","experiment_id":f"SYNTHETIC-discovery-{seed}","seed":seed,
        "data_kind":"SYNTHETIC","code_revision":"SYNTHETIC_FIXTURE",
        # Public generator/training provenance, not a hash of sealed outcomes.
        # The full frozen input hash binds the realization only after execution.
        "source_manifest_sha256":digest(["exogenous-synthetic-generator-3",profile,seed]),
        "split_manifest_sha256":digest(groups),"training_rows":training,"split_groups":groups,
        "decision_tasks":tasks,"training_calibration_rows":calibration,
        "reservation_budget":profile.get("budget",2*N),"cost_unit":"nano_synthetic_units",
        "economics":economics,"agents":agents,"controllers":controllers}
    # Independent realization stream. Never consumed by preparation/search.
    realized=random.Random(realization_seed)
    scenario["sealed_outcomes"]=[{"task_id":t["task_id"],"model_id":m,
        "quality":realized.choices([0,0.5,1],weights=theta[market_id(t["task_id"],m)])[0],
        "cost_decimal":str(Decimal(models.index(m)+1)/Decimal(10**9))} for t in tasks for m in models]
    return scenario,theta,{"h0":deepcopy(honest)}
