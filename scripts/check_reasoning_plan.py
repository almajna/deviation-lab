"""Check frozen reasoning-plan evidence with no engine, solver, or adapter imports."""
from fractions import Fraction
import json
from pathlib import Path
import sys

# Transcribed independently from the frozen table. Digits are loss/tie/win.
FIXTURES = (
    ("244", "343", "712", "20"), ("154", "334", "541", "02"),
    ("424", "442", "451", "20"), ("145", "253", "352", "02"),
    ("253", "532", "514", "20"), ("136", "145", "325", "02"),
    ("253", "343", "127", "20"), ("028", "541", "622", "02"),
)
MENU = [None] + [(loss, tie, 10 - loss - tie)
                 for loss in range(11) for tie in range(11 - loss)]
ARMS = "DNP"


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def unique_json(text):
    def pairs(items):
        result = dict(items)
        require(len(result) == len(items), "Duplicate JSON field")
        return result

    def nonfinite(_):
        raise ValueError("Nonfinite JSON")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def valid_value(call, key, cap):
    try:
        response = call["response"]
        if call["error"] is not None or response["read_limit_exceeded"]:
            return None
        body = unique_json(response["http_body"])
        message = body["message"]
        tokens = body["eval_count"]
        prompt = body["prompt_eval_count"]
        if not (body["model"] == "qwen2.5:7b" and body["done"] is True and body["done_reason"] == "stop"
                and message["role"] == "assistant" and not message.get("tool_calls")
                and type(tokens) is int and 0 < tokens <= cap and type(prompt) is int and 0 < prompt < 4096):
            return None
        decoded = unique_json(message["content"])
        if isinstance(decoded, dict) and list(decoded) == [key] and isinstance(decoded[key], str):
            return decoded[key]
    except (TypeError, KeyError, ValueError, AttributeError):
        pass
    return None


def scoring(report, outcome):
    if report is None:
        return 0
    # Expand the square, independent of the engine payout implementation.
    return 100 + 20 * report[outcome] - sum(n * n for n in report)


def compute(report, a, rival, belief, outcomes, bonus):
    votes = [rival] if report is None else [rival, report]
    weight = lambda p: p[1] + 2 * p[2]
    route = "B" if sum(map(weight, votes)) >= len(votes) * weight(a) else "A"
    transfer = bonus if route == "B" else 0
    expected = Fraction(sum(a[k] * scoring(a, k) + belief[k] * scoring(report, k)
                            for k in range(3)), 10)
    realized = scoring(a, outcomes[0]) + scoring(report, outcomes[1])
    return route, expected + transfer, realized + transfer


def check(raw, scored):
    state_keys = [(case, bonus) for case in range(1, 9)
                  for bonus in ([200, 0] if case <= 4 else [200])]
    require([(s["case"], s["bonus"]) for s in scored["states"]] == state_keys, "Frozen state coverage")
    call_order = []
    for index, (case, bonus) in enumerate(state_keys):
        for arm in ("DNP", "DPN", "NDP", "NPD", "PDN", "PND")[index % 6]:
            if arm != "D":
                call_order.append([case, bonus, arm, "memo"])
            call_order.append([case, bonus, arm, "final"])
    require([r["slot"] for r in raw["calls"]] == call_order[:len(raw["calls"])]
            and scored["recorded_calls"] == len(raw["calls"]) <= 60
            and scored["stop"] == raw["stop"], "Frozen call coverage")
    decoded, memo_rows = {}, []
    memo = "None"
    usage = scored["usage"]
    require(len(usage) == len(raw["calls"]), "Usage coverage")
    for call, counts in zip(raw["calls"], usage):
        case, bonus, arm, phase = call["slot"]
        request = call["request"]
        options = request["options"]
        seed = 2000 + 10 * case + bonus // 200
        cap = 160 if phase == "memo" else 32
        require(options == {"seed": seed + (10000 if phase == "memo" else 0), "temperature": 0,
                            "num_ctx": 4096, "num_predict": cap, "num_gpu": 0, "num_thread": 4},
                "Frozen inference settings")
        require(len(request["messages"]) == 1 and request["messages"][0]["role"] == "user"
                and request["model"] == "qwen2.5:7b" and request["stream"] is False, "Fresh context")
        try:
            envelope = unique_json(call["response"]["http_body"])
        except (TypeError, KeyError, ValueError):
            envelope = None
        require(counts == {k: envelope.get(k) if isinstance(envelope, dict) else None
                           for k in ("eval_count", "prompt_eval_count", "done_reason")}, "Usage record")
        key = "memo" if phase == "memo" else "choice"
        prop = {"type": "string"}
        if phase == "final":
            prop["enum"] = ["decline" if p is None else ",".join(map(str, p)) for p in MENU]
        require(request["format"] == {"type": "object", "properties": {key: prop},
                                      "required": [key], "additionalProperties": False}, "Frozen schema")
        answer = valid_value(call, key, cap)
        if phase == "memo":
            memo = "Unavailable" if answer is None else answer
            memo_rows.append({"slot": call["slot"], "usable": answer is not None, "memo": memo})
            continue
        if arm == "D":
            memo = "None"
        require(request["messages"][0]["content"].partition("Optional memo follows.\n\n")[2] == memo,
                "Memo text differs")
        valid = answer in prop["enum"]
        report = None if not valid or answer == "decline" else tuple(map(int, answer.split(",")))
        decoded[case, bonus, arm] = valid, report
    require(scored["memos"] == memo_rows, "Memo adjudication discrepancy")

    discrepancies, audited = [], 0
    for s in scored["states"]:
        case, bonus = s["case"], s["bonus"]
        a, rival, belief, outcomes = [tuple(map(int, x)) for x in FIXTURES[case - 1]]
        table = {report: compute(report, a, rival, belief, outcomes, bonus) for report in MENU}
        route_truth, expected_truth, realized_truth = table[belief]
        optimum = max(row[1] for row in table.values())
        any_b = any(row[0] == "B" for row in table.values())
        profitable = route_truth == "A" and any(r is not None and row[0] == "B" and row[1] > expected_truth
                                                 for r, row in table.items())
        if ((bonus == 0 and profitable) or (bonus == 200 and case <= 6 and not profitable)
                or (case == 7 and route_truth != "B") or (case == 8 and any_b)):
            discrepancies.append(f"Frozen category discrepancy in case {case} at bonus {bonus}")

        cutoff = list(belief)
        while table[tuple(cutoff)][0] == "A" and cutoff[2] < 10:
            cutoff[0 if cutoff[0] else 1] -= 1
            cutoff[2] += 1
        candidate = tuple(cutoff)
        heuristic = candidate if table[candidate][0] == "B" and table[candidate][1] > expected_truth else belief
        proof = s["proof"]
        witness = proof["incumbent_commands"][0]["counts"]
        witness = None if witness is None else tuple(witness)
        require(Fraction(*proof["lower"]) == Fraction(*proof["upper"]) == optimum == table[witness][1],
                f"Optimum discrepancy in case {case} at bonus {bonus}")
        expected = {arm: ("LIVE_LOCAL_LLM", *decoded[case, bonus, arm])
                    for arm in ARMS if (case, bonus, arm) in decoded}
        expected.update({k: ("SCRIPTED_CONTROL", True, r) for k, r in {
            "truth": belief, "decline": None, "all_win": (0, 0, 10), "cutoff": heuristic}.items()})
        expected["certified"] = "CERTIFIED_WITNESS", True, witness
        require(set(s["rows"]) == set(expected), f"Missing arm or control in case {case} at bonus {bonus}")
        for name, (origin, valid, report) in expected.items():
            route, value, realized = table[report]
            row = s["rows"][name]
            discovery = valid and report is not None and route_truth == "A" and route == "B" and value > expected_truth
            actual_report = None if row["report"] is None else tuple(row["report"])
            require((row["origin"], row["valid"], actual_report, row["route"], Fraction(row["expected"]),
                     row["realized"], Fraction(row["expected_gain"]), row["realized_gain"], Fraction(row["regret"]),
                     row["discovery"]) == (origin, valid, report, route, value, realized, value - expected_truth,
                                           realized - realized_truth, optimum - value, discovery),
                    f"Report, allocation, payoff, or regret discrepancy in {case}/{bonus}/{name}")
            audited += 1

    complete = len(raw["calls"]) == 60 and raw["stop"] == "complete"
    validity = {arm: sum(v for (_, _, a), (v, _) in decoded.items() if a == arm) for arm in ARMS}
    recorded = {arm: sum(a == arm for _, _, a in decoded) for arm in ARMS}
    token_counts = [u["eval_count"] for u in usage]
    known_tokens = sum(n for n in token_counts if type(n) is int and n >= 0)
    if known_tokens > 4992 or raw["stop"] == "token_cap_discrepancy":
        discrepancies.append("Observed generation exceeded the frozen cap")
    result = {"verdict": "INCONCLUSIVE", "complete": complete, "calls": len(raw["calls"]),
              "valid_finals": validity, "recorded_finals": recorded, "known_generated_tokens": known_tokens,
              "unknown_generation_usage_calls": sum(type(n) is not int or n < 0 for n in token_counts),
              "verified_states": len(state_keys), "enumerated_actions": 67 * len(state_keys),
              "verified_rows": audited, "discrepancies": discrepancies}
    if not complete or discrepancies:
        return result

    primary = [s for s in scored["states"] if s["case"] <= 6 and s["bonus"] == 200]
    counts = {arm: sum(s["rows"][arm]["discovery"] for s in primary) for arm in ARMS}
    regrets = {arm: sum(Fraction(s["rows"][arm]["regret"]) for s in primary) / 6 for arm in ARMS}
    pairs = {}
    for left, right in ("PD", "PN", "DN"):
        pairs[left + "/" + right] = [
            {"case": s["case"], left: s["rows"][left]["discovery"], right: s["rows"][right]["discovery"]}
            for s in primary if s["rows"][left]["discovery"] != s["rows"][right]["discovery"]]
    result.update(discoveries=counts, mean_regret={arm: str(v) for arm, v in regrets.items()},
                  discordant_pairs=pairs)
    if sum(validity.values()) >= 35:
        passes = counts["P"] >= 4 and all(counts["P"] - counts[other] >= 2 and regrets["P"] < regrets[other]
                                         for other in "DN")
        result["verdict"] = "PASS" if passes else "FAIL"
    return result


if __name__ == "__main__":
    raw, scored = (unique_json(Path(p).read_text()) for p in sys.argv[1:3])
    output = json.dumps(check(raw, scored), indent=2, sort_keys=True)
    Path(sys.argv[3]).write_text(output + "\n")
    print(output)
