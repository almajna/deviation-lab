"""Exact finite-game enumeration and explicitly bounded heuristic beam search.

Only Game reaches these routines: no sealed outcome store or future honest
signals. Every optional child is executed by Engine.apply before it is ranked.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
import random

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection, integer
from deviation.markets.policies import SignalFollowing, base_action, candidates
from deviation.markets.runner import allowed_actions


def rational(x):
    x = Fraction(x)
    return [x.numerator, x.denominator]


def metrics(game):
    value = game.expected()
    return {k: rational(value[k]) for k in ["cash", "external", "effort", "utility"]} | {"allocation": value["allocation"]}


def done(g):
    return len(g.report_slots) == 0 if g.scope == "reports" else g.engine.turn == len(g.engine.schedule)


def distributions(D):
    for a in range(D+1):
        for b in range(D+1-a): yield [a, b, D-a-b]


def choices(g):
    D = g.engine.cfg["report_denominator"]
    if (g.scope == "reports" or g.mechanism == "interactive-pool") and (D+1)*(D+2)//2+1 > g.engine.cfg["candidate_limit"]:
        raise Rejection("REPORT_CANDIDATE_LIMIT")
    if g.scope == "reports":
        a, mid = g.report_slots[0]
        for p in [None, *distributions(g.engine.cfg["report_denominator"])]:
            yield {"stage": "REPORT_COMMIT", "actor": a, "market_id": mid, "counts": p}
        return
    p = g.policy_packet()
    yield base_action(p, "no_op")
    if g.engine.attempts[p["agent_id"]] >= g.engine.cfg["action_limit"]:return
    if g.mechanism == "lmsr":
        for c in candidates(p):
            out = base_action(p, "trade_shares")
            out.update(share_delta=c["share_delta"], max_net_debit=c["max_net_debit"])
            yield out
    elif g.mechanism == "interactive-pool":
        for values in distributions(g.engine.cfg["report_denominator"]):
            if g.engine.balances[g.engine.wallet(p["agent_id"])] < g.engine.cfg["fee"]: continue
            out = base_action(p, "update_distribution")
            out.update(counts=values, denominator=g.engine.cfg["report_denominator"])
            yield out


def transition(g, command):
    child = deepcopy(g)
    if child.scope == "reports":
        a, mid = child.report_slots.pop(0)
        child.engine.commit(a, mid, command["counts"])
        if not child.report_slots: child.complete_reports()
    else:
        accepted=child.engine.apply(command, allowed_kinds=allowed_actions(child.mechanism))
        if not accepted and child.engine.events[-1]["payload"]["reason"]!="ACTION_LIMIT":return None
    return child


def reference(g, strategy):
    child, commands = deepcopy(g), []
    while not done(child):
        if child.scope == "reports":
            a, mid = child.report_slots[0]
            command = {"stage":"REPORT_COMMIT", "actor":a, "market_id":mid,
                       "counts":None if strategy == "no_action" else child.beliefs[mid]}
        else:
            p = child.policy_packet()
            exhausted=child.engine.attempts[p["agent_id"]]>=child.engine.cfg["action_limit"]
            command = base_action(p, "no_op") if strategy == "no_action" or exhausted else SignalFollowing().act(p)
        child = transition(child, command)
        if child is None: raise Rejection("REFERENCE_NOT_ADMISSIBLE")
        commands.append(command)
    return child, commands


def search(game, *, method="exact", max_nodes=20_000, beam_width=12, seed=0):
    if method not in ["exact", "beam"]: raise Rejection("INVALID_SEARCH_METHOD")
    integer(max_nodes,1,10_000_000);integer(beam_width,1,10_000)
    integer(seed)
    if game.scope=="terminal":
        if game.engine.stage!="TRADE_OR_UPDATE" or any(a not in game.members for a,m in game.engine.schedule[game.engine.turn:]):
            raise Rejection("FUTURE_UNCONTROLLED_ACTIONS_FORBIDDEN")
        if method=="exact" and len(game.engine.schedule)-game.engine.turn>64:raise Rejection("EXACT_HORIZON_LIMIT")
    elif game.scope!="reports" or game.engine.stage!="REPORT_COMMIT" or game.report_slots!=[sorted(game.engine.tokens)[-1]]:
        raise Rejection("INVALID_REPORT_HORIZON")
    observation_sha = digest(game.observation())
    honest, hcommands = reference(game, "signal_following")
    noop, ncommands = reference(game, "no_action")
    best, commands = (honest, hcommands) if honest.expected()["utility"] >= noop.expected()["utility"] else (noop, ncommands)
    visits, leaves, considered, truncated = 0, 0, 0, False
    transcript = sha256()
    improvements = []

    def record(g, path):
        nonlocal best, commands, leaves
        leaves += 1
        m = metrics(g)
        transcript.update((digest({"commands":path,"metrics":m})+"\n").encode())
        if g.expected()["utility"] > best.expected()["utility"]:
            best, commands = g, path
            improvements.append({"leaf":leaves,"utility":m["utility"],"command_sha256":digest(path)})

    if method == "exact":
        def dfs(g, path):
            nonlocal visits, considered
            visits += 1
            if visits > max_nodes: raise Rejection("EXACT_SEARCH_LIMIT_NO_OPTIMALITY_CLAIM")
            if done(g): record(g,path);return
            for command in choices(g):
                considered += 1
                child = transition(g,command)
                if child is not None: dfs(child,path+[command])
        dfs(game,[])
    else:
        # Seeded randomized tie order; deterministic bounded search, not a
        # genetic/global-optimality claim. Rank partial states after no-op fill.
        rng = random.Random(seed)
        frontier = [(deepcopy(game),[])]
        while frontier:
            expanded = []
            for g,path in frontier:
                if done(g): record(g,path);continue
                options = list(choices(g));rng.shuffle(options)
                for command in options:
                    if visits >= max_nodes: truncated=True;break
                    visits += 1;considered += 1
                    child=transition(g,command)
                    if child is None:continue
                    if done(child):record(child,path+[command])
                    else:
                        filled,filled_commands=reference(child,"no_action")
                        # This complete admissible plan is a real incumbent,
                        # even if the beam budget stops before this depth ends.
                        record(filled,path+[command]+filled_commands)
                        expanded.append((child,path+[command],filled.expected()["utility"]))
                if truncated:break
            if truncated:break
            expanded.sort(key=lambda row:row[2],reverse=True)
            frontier=[(g,path) for g,path,v in expanded[:beam_width]]
    result={"version":"attack-search-1","method":method,
        "claim":"EXACT_DECLARED_FINITE_SUBGAME" if method=="exact" else "BEST_FOUND_BOUNDED_HEURISTIC",
        "scope":game.scope,"observation_sha256":observation_sha,
        "max_nodes":max_nodes,"beam_width":beam_width,"seed":seed,"budget_exhausted":truncated,
        "visited_nodes":visits,"terminal_evaluations":leaves,"considered_actions":considered,
        "evaluation_transcript_sha256":transcript.hexdigest(),"improvements":improvements,
        "commands":commands,"selected":metrics(best),"signal_following":metrics(honest),"no_action":metrics(noop),
        "gain_vs_signal_following":rational(best.expected()["utility"]-honest.expected()["utility"]),
        "gain_vs_no_action":rational(best.expected()["utility"]-noop.expected()["utility"])}
    result["sha256"]=digest(result)
    return result
