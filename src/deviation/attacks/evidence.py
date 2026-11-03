"""Execute searched commands on the real engine and audit counterfactuals."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection
from deviation.markets.policies import SignalFollowing, base_action
from deviation.markets.runner import run as run_market, write_bundle as write_market
from deviation.simulator.runner import implementation_sha256
from .game import prepare_game
from .search import search, reference, metrics
from .verify import recompute, welfare, pair


class CommandPolicy(SignalFollowing):
    """Data-only replay of searched commands; no generated Python/code loading."""
    def __init__(self,commands):
        self.initial={};self.optional={}
        for c in commands:
            if c["stage"]=="REPORT_COMMIT":self.initial[(c["actor"],c["market_id"])]=c["counts"]
            else:
                # The engine assigns globally unique optional-turn IDs.
                turn=int(c["order_id"].rsplit("order-",1)[1])
                self.optional[turn]=c
    def act(self,p):
        if p["stage"]=="REPORT_COMMIT" and (p["agent_id"],p["market_id"]) in self.initial:
            values=self.initial[(p["agent_id"],p["market_id"])]
            if values is None:return None
            out=base_action(p,"report_distribution")
            out.update(counts=deepcopy(values),denominator=p["limits"]["report_denominator"],report_token=p["report_token"])
            return out
        if p["stage"]=="TRADE_OR_UPDATE" and p["turn"] in self.optional:
            out=deepcopy(self.optional[p["turn"]])
            if out["actor"]!=p["agent_id"] or out["market_id"]!=p["market_id"]:raise Rejection("COMMAND_CONTEXT_MISMATCH")
            return out
        return super().act(p)


def execute(scenario,mechanism,commands):
    return run_market(scenario,mechanism,policies={a:CommandPolicy(commands) for a in scenario["agents"]})


def _fraction(value):return Fraction(*value)


def discover(scenario,controller,mechanism,*,scope="terminal",public_report_model=None,
             method="exact",max_nodes=2000,beam_width=6,seed=0,environment_counts=None):
    scenario=deepcopy(scenario);public_report_model=deepcopy(public_report_model);environment_counts=deepcopy(environment_counts)
    game=prepare_game(scenario,controller,mechanism,scope=scope,public_report_model=public_report_model)
    certificate=search(game,method=method,max_nodes=max_nodes,beam_width=beam_width,seed=seed)
    honest,hcommands=reference(game,"signal_following")
    noop,ncommands=reference(game,"no_action")
    receipts={"attack":execute(scenario,mechanism,certificate["commands"]),
              "signal_following":execute(scenario,mechanism,hcommands),
              "no_action":execute(scenario,mechanism,ncommands)}
    shared_config=len({digest(r["public_config"]) for r in receipts.values()})==1
    if not shared_config:raise Rejection("UNMATCHED_RESOURCES_OR_SCHEDULE")
    checks={name:recompute(r,controller,game.beliefs) for name,r in receipts.items()}
    model_matches=True
    accepted_ids={e["payload"]["order_id"] for e in receipts["attack"]["trace"]["events"] if e["type"] in {"trade_accepted","distribution_updated"}}
    accepted_nonnoop=all(c.get("kind") in [None,"no_op"] or c["order_id"] in accepted_ids for c in certificate["commands"])
    if not accepted_nonnoop:model_matches=False
    for name,expected in [("signal_following",metrics(honest)),("no_action",metrics(noop)),("attack",certificate["selected"])]:
        c=checks[name]
        if c["expected_utility"]!=expected["utility"] or receipts[name]["allocation_plan"]!=expected["allocation"]:
            model_matches=False
    if scope=="reports":
        actual={(e["payload"]["actor"],e["payload"]["market_id"]):e["payload"]["counts"] for e in receipts["attack"]["trace"]["events"] if e["type"]=="report_revealed"}
        for a,values in public_report_model.items():
            for mid,p in values.items():
                if actual.get((a,mid))!=p:model_matches=False
    gain=_fraction(checks["attack"]["expected_utility"])-_fraction(checks["signal_following"]["expected_utility"])
    noop_gain=_fraction(checks["attack"]["expected_utility"])-_fraction(checks["no_action"]["expected_utility"])
    redirect=receipts["attack"]["allocation_plan"]!=receipts["signal_following"]["allocation_plan"]
    expected_welfare=None;world_checks=None;world_gain=None;world_noop_gain=None
    if environment_counts is not None:
        expected_welfare={k:welfare(r,environment_counts) for k,r in receipts.items()}
        world_checks={k:recompute(r,controller,environment_counts) for k,r in receipts.items()}
        world_gain=_fraction(world_checks["attack"]["expected_utility"])-_fraction(world_checks["signal_following"]["expected_utility"])
        world_noop_gain=_fraction(world_checks["attack"]["expected_utility"])-_fraction(world_checks["no_action"]["expected_utility"])
    valid=model_matches and gain>0 and noop_gain>0
    external_change=checks["attack"]["external_benefit"]-checks["signal_following"]["external_benefit"]
    cash_change=_fraction(checks["attack"]["expected_cash"])-_fraction(checks["signal_following"]["expected_cash"])
    without_external=gain-external_change
    if valid and redirect and external_change>0 and without_external<=0:
        motive="EXTERNAL_REWARD_REQUIRED_FOR_THIS_SELECTED_PLAN"
    elif valid and redirect and cash_change>0:motive="PROFITABLE_TRADING_WITH_ALLOCATION_EFFECT"
    else:motive="NO_EXTERNAL_MANIPULATION_ATTRIBUTION"
    if not model_matches:classification="PUBLIC_MODEL_MISMATCH_NOT_VERIFIED"
    elif valid and redirect and world_gain is not None and world_gain>0 and world_noop_gain>0:classification="VERIFIED_STRATEGIC_ALLOCATION_DEVIATION"
    elif valid and redirect:classification="SUBJECTIVE_GAIN_REDIRECTION_NOT_WORLD_VERIFIED"
    elif valid:classification="PROFITABLE_DEVIATION_WITHOUT_REDIRECTION"
    elif noop_gain>0:classification="ORDINARY_TRADING_OR_REFERENCE_NOT_BEATEN"
    else:classification="NO_PROFITABLE_DEVIATION_FOUND"
    # Reoptimize under zero allocation reward, not just an accounting subtraction
    # on the selected attack. No outcomes enter this second optimization either.
    zero_game=deepcopy(game)
    zero_game.engine.controllers[controller]["external_weights"]={}
    zero_certificate=search(zero_game,method=method,max_nodes=max_nodes,beam_width=beam_width,seed=seed)
    zero_scenario=deepcopy(scenario)
    zero_scenario["controllers"][controller]["external_weights"]={}
    for name,commands in [("zero_external_attack",zero_certificate["commands"]),
                          ("zero_external_signal_following",hcommands),("zero_external_no_action",ncommands)]:
        receipts[name]=execute(zero_scenario,mechanism,commands)
    zero_checks={name:recompute(receipts[name],controller,game.beliefs) for name in receipts if name.startswith("zero_external")}
    zero_model_matches=(zero_checks["zero_external_attack"]["expected_utility"]==zero_certificate["selected"]["utility"]
        and receipts["zero_external_attack"]["allocation_plan"]==zero_certificate["selected"]["allocation"] and model_matches)
    zero_gain=_fraction(zero_checks["zero_external_attack"]["expected_utility"])-_fraction(zero_checks["zero_external_signal_following"]["expected_utility"])
    causal=[]
    for e in receipts["attack"]["trace"]["events"]:
        if e["type"] in {"trade_accepted","report_revealed","distribution_updated","allocation_locked","economic_summary"}:
            causal.append({"event_seq":e["seq"],"event_type":e["type"],"payload_sha256":digest(e["payload"])})
    evidence={"version":"attack-evidence-1","data_kind":"SYNTHETIC","controller":controller,
        "mechanism":mechanism,"scope":scope,"classification":classification,
        "input_sha256":digest(scenario),"implementation_sha256":implementation_sha256(),
        "search":certificate,"observation_audit":{"access":"POST_RUN_SYNTHETIC_RESEARCH_AUDIT_NOT_POLICY_PACKET",
            "observation_sha256":digest(game.observation()),"declared_belief_counts":game.beliefs,
            "future_information":"NO_FUTURE_HONEST_ACTIONS_IN_TERMINAL_GAME; PUBLIC_ANNOUNCED_MODEL_IN_REPORT_GAME",
            "public_report_model":public_report_model},
        "independent_payoff_checks":checks,"model_matches_real_execution":model_matches,
        "all_selected_nonnoop_commands_accepted":accepted_nonnoop,
        "resource_matching":{"same_registry_config_caps_and_schedule":shared_config,
            "registered_actors":sorted(receipts["attack"]["public_config"]["agents"]),
            "score_reserve":receipts["attack"]["trace"]["events"][-1]["payload"]["score_reserve"]},
        "zero_external_control":{"intervention":"ZERO_CONTROLLER_ALLOCATION_REWARDS_ONLY_REOPTIMIZED",
            "search":zero_certificate,"independent_payoff_checks":zero_checks,"gain_vs_signal_following":pair(zero_gain),"model_matches_real_execution":zero_model_matches},
        "gain_vs_signal_following":pair(gain),"gain_vs_no_action":pair(noop_gain),
        "allocation_redirected":redirect,"environment_expected_welfare":expected_welfare,
        "incentive_attribution":motive,"same_plan_gain_without_external":pair(without_external),
        "environment_expected_welfare_loss":None if expected_welfare is None else pair(_fraction(expected_welfare["signal_following"])-_fraction(expected_welfare["attack"])),
        "realized_proxy_loss":receipts["signal_following"]["trace"]["events"][-1]["payload"]["evaluation"]["total_preference_proxy"]-receipts["attack"]["trace"]["events"][-1]["payload"]["evaluation"]["total_preference_proxy"],
        "incentive_decomposition":{"cash_gain":pair(_fraction(checks["attack"]["expected_cash"])-_fraction(checks["signal_following"]["expected_cash"])),
            "external_gain":checks["attack"]["external_benefit"]-checks["signal_following"]["external_benefit"],
            "effort_change":checks["attack"]["effort"]-checks["signal_following"]["effort"]},
        "environment_payoff_checks":world_checks,"environment_gain_vs_signal_following":None if world_gain is None else pair(world_gain),
        "environment_gain_vs_no_action":None if world_noop_gain is None else pair(world_noop_gain),
        "causal_sequence":causal,"receipt_sha256":{k:r["sha256"] for k,r in receipts.items()}}
    evidence["sha256"]=digest(evidence)
    return {"scenario":deepcopy(scenario),"controller":controller,"mechanism":mechanism,
        "options":{"scope":scope,"public_report_model":public_report_model,"method":method,
            "max_nodes":max_nodes,"beam_width":beam_width,"seed":seed,"environment_counts":environment_counts},
        "evidence":evidence,"receipts":receipts}


def replay(bundle):
    actual=discover(bundle["scenario"],bundle["controller"],bundle["mechanism"],**bundle["options"])
    if digest(actual)!=digest(bundle):raise Rejection("ATTACK_REPLAY_MISMATCH")
    return actual


def write_bundle(bundle,destination):
    p=Path(destination);p.mkdir(parents=True,exist_ok=True)
    for name,r in bundle["receipts"].items():write_market(r,p/name)
    source={k:bundle[k] for k in ["scenario","controller","mechanism","options"]}
    source["receipt_names"]=sorted(bundle["receipts"])
    for name,value in [("experiment.json",source),("evidence.json",bundle["evidence"])]:
        (p/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n")
    paths=sorted(x for x in p.rglob("*") if x.is_file() and x.name!="audit_manifest.json")
    manifest={"version":"attack-evidence-1","files":{x.relative_to(p).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}}
    (p/"audit_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")


def load_bundle(destination):
    p=Path(destination)
    manifest=json.loads((p/"audit_manifest.json").read_text())
    for name,expected in manifest["files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:raise Rejection("INVALID_ARTIFACT_PATH")
        if hashlib.sha256((p/name).read_bytes()).hexdigest()!=expected:raise Rejection("ARTIFACT_HASH_MISMATCH")
    source=json.loads((p/"experiment.json").read_text())
    source["evidence"]=json.loads((p/"evidence.json").read_text())
    names=source.pop("receipt_names")
    if not isinstance(names,list) or any(not isinstance(n,str) or not n.replace('_','').isalpha() for n in names):raise Rejection("INVALID_ARTIFACT_PATH")
    source["receipts"]={name:json.loads((p/name/"receipts.json").read_text()) for name in names}
    return source
