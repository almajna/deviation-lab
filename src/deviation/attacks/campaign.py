"""All-case exploratory replication; no final empirical data or positive filter."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from .environments import environment
from .evidence import discover, write_bundle


def run_campaign(protocol, destination=None, *, include_pilots=True):
    if type(protocol.get("evaluator_seed")) is not int or protocol["evaluator_seed"]<0:
        raise Rejection("EVALUATOR_SEED_REQUIRED")
    rows=[];manifest={};selected=None;selection_key=None
    phases=[("replication",protocol["replication_seeds"])]
    if include_pilots:phases.insert(0,("known_pilot",protocol["known_pilot_seeds"]))
    if protocol.get("post_review_replication_seeds"):
        phases.append(("post_review_replication",protocol["post_review_replication_seeds"]))
    for phase,seeds in phases:
        for seed in seeds:
            for definition in protocol["profiles"]:
                profile=deepcopy(protocol["base_profile"]);profile.update(definition["overrides"])
                private_realization=int(digest([protocol["evaluator_seed"],seed]),16)
                s,world,announced=environment(profile,seed,realization_seed=private_realization)
                for mechanism in protocol["mechanisms"]:
                    scope="reports" if mechanism in ["pool","score","calibrated-pool"] else "terminal"
                    case=f"{phase}-{seed}-{definition['id']}-{mechanism}"
                    row={"case":case,"phase":phase,"profile":definition["id"],"parameters":profile,
                         "mechanism":mechanism,"seed":seed,"scenario_sha256":digest(s)}
                    settings=protocol["search"]
                    method=definition.get("method","exact");fallback=False
                    try:
                        try:
                            bundle=discover(s,"strategic",mechanism,scope=scope,public_report_model=announced if scope=="reports" else None,
                                method=method,max_nodes=settings["exact_node_cap"] if method=="exact" else settings["heuristic_node_cap"],
                                beam_width=settings["beam_width"],seed=seed,environment_counts=world)
                        except Rejection as error:
                            if str(error)!="EXACT_SEARCH_LIMIT_NO_OPTIMALITY_CLAIM":raise
                            fallback=True
                            bundle=discover(s,"strategic",mechanism,scope=scope,public_report_model=announced if scope=="reports" else None,
                                method="beam",max_nodes=settings["heuristic_node_cap"],beam_width=settings["beam_width"],seed=seed,environment_counts=world)
                        e=bundle["evidence"]
                        row.update(status="EVALUATED",classification=e["classification"],method=e["search"]["method"],
                            exact_attempt_exhausted=fallback,visited_nodes=e["search"]["visited_nodes"],
                            gain_vs_honest=e["gain_vs_signal_following"],gain_vs_noop=e["gain_vs_no_action"],
                            cash_gain=e["incentive_decomposition"]["cash_gain"],external_gain=e["incentive_decomposition"]["external_gain"],
                            expected_welfare_loss=e["environment_expected_welfare_loss"],
                            world_gain=e["environment_gain_vs_signal_following"],realized_proxy_loss=e["realized_proxy_loss"],
                            allocation_redirected=e["allocation_redirected"],evidence_sha256=e["sha256"],
                            incentive_attribution=e["incentive_attribution"],same_plan_gain_without_external=e["same_plan_gain_without_external"],
                            budget_exhausted=e["search"]["budget_exhausted"])
                        if e["classification"]=="VERIFIED_STRATEGIC_ALLOCATION_DEVIATION":
                            if destination is not None:
                                path=Path(destination)/"counterexamples"/case
                                write_bundle(bundle,path)
                                manifest[case]=digest(json.loads((path/"audit_manifest.json").read_text()))
                            harmful=Fraction(*e["environment_expected_welfare_loss"])>0
                            if harmful:
                                preferred=(mechanism=="lmsr" and e["search"]["method"]=="exact" and profile["belief_quality"]==100)
                                key=(not preferred,case)
                                if selected is None or key<selection_key:selected=(case,bundle);selection_key=key
                    except Rejection as error:
                        row.update(status="NOT_EVALUATED",reason=str(error))
                    rows.append(row)
    summary={"version":"attack-campaign-1","protocol_sha256":digest(protocol),"cases":rows,
        "counts":{"total":len(rows),"evaluated":sum(r["status"]=="EVALUATED" for r in rows),
        "verified_redirects":sum(r.get("classification")=="VERIFIED_STRATEGIC_ALLOCATION_DEVIATION" for r in rows),
        "verified_harmful_redirects":sum(r.get("classification")=="VERIFIED_STRATEGIC_ALLOCATION_DEVIATION" and Fraction(*r["expected_welfare_loss"])>0 for r in rows),
        "exact":sum(r.get("method")=="exact" for r in rows),"heuristic":sum(r.get("method")=="beam" for r in rows)},
        "counterexample_manifests":manifest,"selected_counterexample":None if selected is None else selected[0]}
    summary["sha256"]=digest(summary)
    if destination is not None:
        root=Path(destination);root.mkdir(parents=True,exist_ok=True)
        (root/"campaign.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        (root/"protocol.json").write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n")
        if selected is not None:write_bundle(selected[1],root/"selected")
    return summary,selected
