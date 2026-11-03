"""Independent certificate checker with independently rebuilt proof semantics."""
from copy import deepcopy
from pathlib import Path

from deviation.data.pipeline import digest
from .bounds import upper
from .domain import VerificationError, actions, advance, encoded, execute, fraction, payoff, terminal


def source_sha():
    root = Path(__file__).resolve().parents[1]
    return digest({str(p.relative_to(root)): digest(p.read_text()) for p in sorted(root.rglob("*.py"))})


def require(ok, message):
    if not ok:
        raise VerificationError(message)


def validate_game(g):
    e = g.engine
    require(g.mechanism in {"lmsr", "interactive-pool", "pool", "score", "calibrated-pool"}, "unsupported mechanism")
    require(g.controller in e.controllers and g.members, "missing controlled accounts")
    require(set(g.beliefs) == set(e.books), "belief market coverage")
    D = e.cfg["report_denominator"]
    for p in g.beliefs.values():
        require(isinstance(p, list) and len(p) == 3 and all(type(n) is int and n >= 0 for n in p)
                and sum(p) == D, "invalid beliefs")
    if g.scope == "terminal":
        require(e.stage == "TRADE_OR_UPDATE" and 0 <= e.turn <= len(e.schedule), "wrong stage")
        require(all(a in g.members for a, m in e.schedule[e.turn:]), "future uncontrolled action")
        require(len(e.schedule)-e.turn <= 128, "unsupported horizon")
    else:
        require(g.scope == "reports" and e.stage == "REPORT_COMMIT" and
                g.report_slots == [sorted(e.tokens)[-1]] and g.report_slots[0][0] in g.members
                and g.mechanism in {"pool", "score", "calibrated-pool"}, "unsupported report scope")
    Q = e.cfg["order_limit"]
    alphabet_bound = (4*Q**3+6*Q**2+8*Q+3)//3 if g.mechanism == "lmsr" else (D+1)*(D+2)//2+1
    require(alphabet_bound <= min(100000, e.cfg["candidate_limit"]), "oversized alphabet")


def check(game, certificate, *, expected_source_sha=None, max_nodes=1000000):
    """Replay incumbent, check complete tree coverage and every frontier bound.

    Trusted caller supplies the outcome-free root Game. source_sha/observation
    bind identity, not provenance authenticity. The expected producer-source hash
    defaults to this integrated package. An explicit hash permits historical proof
    checking without pretending a different current package produced it.
    """
    validate_game(game)
    c = certificate
    keys = set("version scope controller action_space observation_sha256 source_sha256 objective vector_limit incumbent_commands lower upper gap claim nodes search sha256".split())
    require(type(max_nodes) is int and max_nodes >= 1, "invalid checker cap")
    require(isinstance(c, dict) and set(c) == keys, "certificate fields")
    require(c["sha256"] == digest({k: v for k, v in c.items() if k != "sha256"}), "certificate digest")
    require(c["version"] == "attack-certificate-1" and c["action_space"] == "engine-l1-orders-or-simplex-reports-1"
            and c["objective"] == "SUBJECTIVE_EXPECTED_CONTROLLER_UTILITY", "certificate semantics")
    require(c["scope"] == game.scope and c["controller"] == game.controller, "controller/scope binding")
    require(c["observation_sha256"] == digest(game.observation()), "observation binding")
    require(c["source_sha256"] == (source_sha() if expected_source_sha is None else expected_source_sha), "source binding")
    require(type(c["vector_limit"]) is int and 0 <= c["vector_limit"] <= 100000, "invalid vector limit")
    require(isinstance(c["nodes"], list) and 1 <= len(c["nodes"]) <= max_nodes, "node count")
    require(isinstance(c["incumbent_commands"], list), "incumbent commands")
    lower, claimed_upper, gap = [fraction(c[k]) for k in ["lower", "upper", "gap"]]
    witness = execute(game, c["incumbent_commands"])
    components = payoff(witness)
    require(components["utility"] == lower, "incorrect incumbent value")
    visited, pending, bounds = set(), [(0, deepcopy(game))], []
    transitions, splits = 0, 0
    while pending:
        i, state = pending.pop()
        require(type(i) is int and 0 <= i < len(c["nodes"]) and i not in visited, "cycle/shared/invalid node")
        visited.add(i)
        node = c["nodes"][i]
        require(isinstance(node, dict) and "kind" in node, "node fields")
        if node["kind"] == "split":
            require(set(node) == {"kind", "children"} and not terminal(state), "split fields/stage")
            require(isinstance(node["children"], list), "children type")
            legal = {digest(a): a for a in actions(state)}
            require(len(node["children"]) == len(legal), "missing/extra action coverage")
            seen = set()
            for edge in node["children"]:
                require(isinstance(edge, dict) and set(edge) == {"command", "node"}, "edge fields")
                key = digest(edge["command"])
                require(key in legal and key not in seen, "missing/duplicate/illegal branch")
                seen.add(key)
                pending.append((edge["node"], advance(state, legal[key])))
                transitions += 1
            splits += 1
        else:
            require(set(node) == {"kind", "upper"}, "leaf fields")
            if node["kind"] == "terminal":
                require(terminal(state), "nonterminal terminal leaf")
                value = payoff(state)["utility"]
            else:
                require(node["kind"] == "bound" and not terminal(state), "invalid bound leaf")
                value = upper(state, vector_limit=c["vector_limit"])
            require(fraction(node["upper"]) == value, "incorrect leaf bound")
            bounds.append(value)
    require(len(visited) == len(c["nodes"]), "unreachable node")
    search = c["search"]
    require(isinstance(search, dict) and set(search) == {"max_expansions", "expansions", "generated"}, "search fields")
    require(all(type(n) is int and n >= 0 for n in search.values()), "search count type")
    require(search["generated"] == len(visited) and search["expansions"] == splits
            and splits <= search["max_expansions"] <= 100000, "search counts")
    actual_upper = max([lower] + bounds)
    require(claimed_upper == actual_upper and gap == actual_upper-lower and gap >= 0, "incorrect interval")
    require(c["claim"] == ("EXACT_FINITE_SUBGAME" if gap == 0 else "BOUNDED_FINITE_SUBGAME"), "incorrect claim")
    return {"version": "independent-certificate-check-1", "lower": encoded(lower),
            "upper": encoded(actual_upper), "gap": encoded(gap), "checked_nodes": len(visited),
            "engine_transitions": transitions+len(c["incumbent_commands"]),
            "payoff": {k: encoded(v) for k, v in components.items() if k != "allocation"},
            "allocation": components["allocation"]}
