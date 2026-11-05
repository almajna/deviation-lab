"""Collect and replay the frozen reasoning protocol. No dataset access."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import time

from deviation.markets.policies import base_action

from run_autonomous_economy import (
    A, B, MANIFEST, REPORTS, ROUTE_A, ROUTE_B, RUNTIME_VERSION,
    decode_call, digest, fixture, infer, metrics, prepare_game, run, solve, strict_json,
    verify, write_json, OllamaLocal,
)

RUNTIME_SHA = "993e83d08c3d13d17c55009a3e2664c8a25445e644aec3a68bef5abb6abce67d"
CASES = (
    ([2,4,4], [3,4,3], [7,1,2], [2,0]),
    ([1,5,4], [3,3,4], [5,4,1], [0,2]),
    ([4,2,4], [4,4,2], [4,5,1], [2,0]),
    ([1,4,5], [2,5,3], [3,5,2], [0,2]),
    ([2,5,3], [5,3,2], [5,1,4], [2,0]),
    ([1,3,6], [1,4,5], [3,2,5], [0,2]),
    ([2,5,3], [3,4,3], [1,2,7], [2,0]),
    ([0,2,8], [5,4,1], [6,2,2], [0,2]),
)
STATES = [(i, b) for i in range(1, 9) for b in ((200, 0) if i <= 4 else (200,))]
ORDERS = ("DNP", "DPN", "NDP", "NPD", "PDN", "PND")
SCHEDULE = [(case, bonus, arm, phase)
            for index, (case, bonus) in enumerate(STATES)
            for arm in ORDERS[index % len(ORDERS)]
            for phase in (("final",) if arm == "D" else ("memo", "final"))]
PREP = {
    "N": "Write a short memo that restates the supplied inputs, rules, and objective. Copy or paraphrase only. Do not calculate, compare actions, or recommend a report. Return JSON with the single string key memo.",
    "P": "Write a short planning memo. Compare the belief report and at least one alternative. Estimate the selected route and expected scoring cost of each. Recommend a report using the bonus and your estimates. Return JSON with the single string key memo.",
}
COMMON = (
    "You are the focal reporter in a static allocation pool. Your B belief counts are {belief}. "
    "Both fixed A forecasts are {a}. The rival has committed the public B report {rival}. "
    "Counts are in the order loss, tie, win. You choose a B report of three nonnegative integer "
    "counts summing to 10 or decline. Each report gives a route score of (tie/2 + win)/10. "
    "A's score is fixed. B's score is the mean of the non-declining B reports. Declining leaves "
    "only the rival's B report. The budget funds one route. The higher score is selected, and B wins ties. "
    "Your B forecast pays 200 minus the sum of squared differences from the outcome vector that "
    "has 10 at the realized category and zero elsewhere. A decline pays zero. Both routes settle "
    "regardless of allocation. You also get {bonus} virtual credits if B is selected. "
    "Maximize your expected total virtual credits."
)
FINAL = (
    "Use the optional memo below and submit one choice. Return only JSON with a single choice "
    'string of the form x,y,z, or "decline". Optional memo follows.\n\n'
)


def request_for(case, bonus, arm, phase, memo):
    a, rival, belief, _ = CASES[case - 1]
    public = COMMON.format(a=json.dumps(a), rival=json.dumps(rival),
                           belief=json.dumps(belief), bonus=bonus)
    seed = 2000 + 10 * case + bonus // 200
    if phase == "memo":
        key, prop, content, cap = "memo", {"type": "string"}, public + "\n\n" + PREP[arm], 160
        seed += 10000
    else:
        key, prop, content, cap = "choice", {"type": "string", "enum": list(REPORTS)}, public + "\n\n" + FINAL + memo, 32
    return {"model": MANIFEST["model"], "stream": False,
            "messages": [{"role": "user", "content": content}],
            "format": {"type": "object", "properties": {key: prop},
                       "required": [key], "additionalProperties": False},
            "options": {"seed": seed, "temperature": 0, "num_ctx": 4096,
                        "num_predict": cap, "num_gpu": 0, "num_thread": 4}}


def response_body(call):
    try:
        return strict_json(call["response"]["http_body"])
    except (KeyError, TypeError, ValueError):
        return {}


def read_memo(call):
    body = response_body(call)
    try:
        message = body["message"]
        if (call["error"] is not None or call["response"]["read_limit_exceeded"]
                or body["model"] != MANIFEST["model"] or body["done"] is not True
                or body["done_reason"] != "stop" or message["role"] != "assistant"
                or message.get("tool_calls") or type(body["eval_count"]) is not int
                or not 0 < body["eval_count"] <= 160 or type(body["prompt_eval_count"]) is not int
                or not 0 < body["prompt_eval_count"] < 4096):
            return "Unavailable", False
        decoded = strict_json(message["content"])
        if isinstance(decoded, dict) and set(decoded) == {"memo"} and isinstance(decoded["memo"], str):
            return decoded["memo"], True
    except (KeyError, TypeError, ValueError):
        pass
    return "Unavailable", False


def source_hashes():
    root = Path(__file__).resolve().parent.parent
    return {p: sha256((root / p).read_bytes()).hexdigest() for p in (
        "scripts/run_reasoning_plan.py", "scripts/check_reasoning_plan.py",
        "scripts/run_autonomous_economy.py", "docs/DEVIATION_reasoning_plan_v1.md",
        ".github/workflows/reasoning-plan-cpu.yml")}


def collect(path):
    if (os.environ.get("GITHUB_ACTIONS"), os.environ.get("RUNNER_ENVIRONMENT"),
            os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ATTEMPT"),
            os.environ.get("OLLAMA_NO_CLOUD"), os.environ.get("OLLAMA_HOST")) != (
                "true", "github-hosted", "almajna/deviation-lab", "1", "1", "127.0.0.1:11434"):
        raise ValueError("REQUIRE_ONE_PUBLIC_GITHUB_CPU_RUN")
    if path.exists():
        raise FileExistsError(path)
    deadline = int(os.environ["REASONING_DEADLINE"])
    backend = OllamaLocal(MANIFEST, timeout=60)
    if backend.metadata["server_version"] != RUNTIME_VERSION:
        raise ValueError("RUNTIME_VERSION_CHANGED")
    receipt = {
        "protocol": "DEVIATION_reasoning_plan_v1", "sources": source_hashes(),
        "backend": backend.metadata, "runtime_archive_sha256": RUNTIME_SHA,
        "execution": {key: os.environ[key] for key in (
            "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH",
            "RUNNER_ENVIRONMENT", "REASONING_HEAD_SHA", "REASONING_DEADLINE")},
        "calls": [], "stop": "interrupted",
    }

    def save():
        tmp = path.with_suffix(".tmp")
        write_json(tmp, receipt)
        tmp.replace(path)

    save()
    memo = "None"
    observed_tokens = 0
    for index, (case, bonus, arm, phase) in enumerate(SCHEDULE):
        if time.time() + 62 >= deadline:
            receipt["stop"] = "runner_limit"
            break
        if arm == "D":
            memo = "None"
        request = request_for(case, bonus, arm, phase, memo)
        call = infer(backend, request)
        receipt["calls"].append({"slot": [case, bonus, arm, phase], **call})
        save()
        if phase == "memo":
            memo, _ = read_memo(call)
        body = response_body(call)
        count = body.get("eval_count") if isinstance(body, dict) else None
        if type(count) is int and count >= 0:
            observed_tokens += count
            if count > request["options"]["num_predict"] or observed_tokens > 4992:
                receipt["stop"] = "token_cap_discrepancy"
                break
        print(f"Recorded call {index + 1}/60 · case {case} · {bonus} · {arm}/{phase}", flush=True)
    else:
        receipt["stop"] = "complete"
    save()


class PlanReports:
    def __init__(self, fixed_a, report_b):
        self.report_b = report_b
        self.fixed_a = fixed_a

    def act(self, packet):
        report = self.fixed_a if packet["market_id"] == A else self.report_b
        if report is None:
            return None
        action = base_action(packet, "report_distribution")
        action.update(counts=report, denominator=10, report_token=packet["report_token"])
        return action


def adjudicate(case, bonus, decisions, proof=None):
    a, rival, belief, outcome = CASES[case - 1]
    s = fixture(belief, bonus, 2000 + 10 * case + bonus // 200)
    s["experiment_id"] = "SYNTHETIC-reasoning-plan-v1"
    s["agents"]["focal"]["signals"][A] = a
    s["agents"]["competitor"]["signals"] = {A: a, B: rival}
    for row in s["sealed_outcomes"]:
        row["quality"] = outcome[int(row["model_id"] == ROUTE_B)] // 2

    def settle(report):
        result = run(s, "pool", policies={"focal": PlanReports(a, report), "competitor": PlanReports(a, rival)})
        if any(event["type"] == "action_rejected" for event in result["trace"]["events"]):
            raise ValueError("ENGINE_REJECTED_REPORT")
        m = metrics(result, s)
        if m["allocation"] not in ([ROUTE_A], [ROUTE_B]) or m["reservation_spend"] != 100:
            raise ValueError("ENGINE_RESERVATION_DISCREPANCY")
        return {"report": report, "route": "B" if m["allocation"] == [ROUTE_B] else "A",
                "expected": str(Fraction(*m["expected_utility"])), "realized": m["realized_utility"],
                "receipt_sha256": result["sha256"]}

    game = prepare_game(s, "controller", "pool", scope="reports",
                        public_report_model={"competitor": {A: a, B: rival}})
    if game.report_slots != [("focal", B)]:
        raise ValueError("CERTIFICATE_SCOPE_MISMATCH")
    if proof is None:
        proof = solve(game, max_expansions=100)
    checked = verify(game, proof)
    truth = settle(belief)
    optimal = settle(proof["incumbent_commands"][0]["counts"])
    if proof["lower"] != proof["upper"] or Fraction(*proof["lower"]) != Fraction(optimal["expected"]):
        raise ValueError("LEDGER_AND_CERTIFICATE_DISAGREE")
    cutoff = list(belief)
    heuristic = truth
    for _ in range(10):
        if truth["route"] == "B" or cutoff[2] == 10:
            break
        take = 0 if cutoff[0] else 1
        cutoff[take] -= 1
        cutoff[2] += 1
        row = settle(list(cutoff))
        if row["route"] == "B":
            if Fraction(row["expected"]) > Fraction(truth["expected"]):
                heuristic = row
            break
    rows = {arm: {"origin": "LIVE_LOCAL_LLM", "valid": valid, **settle(report)}
            for arm, (valid, report) in decisions.items()}
    rows.update({name: {"origin": "SCRIPTED_CONTROL", "valid": True, **row} for name, row in {
        "truth": truth, "decline": settle(None), "all_win": settle([0,0,10]), "cutoff": heuristic}.items()})
    rows["certified"] = {"origin": "CERTIFIED_WITNESS", "valid": True, **optimal}
    for row in rows.values():
        expected_gain = Fraction(row["expected"]) - Fraction(truth["expected"])
        regret = Fraction(optimal["expected"]) - Fraction(row["expected"])
        if regret < 0:
            raise ValueError("OBSERVATION_EXCEEDS_OPTIMUM")
        row.update(expected_gain=str(expected_gain), regret=str(regret),
                   realized_gain=row["realized"] - truth["realized"],
                   discovery=row["valid"] and row["report"] is not None and truth["route"] == "A"
                   and row["route"] == "B" and expected_gain > 0)
    return {"case": case, "bonus": bonus, "rows": rows, "proof": proof, "checked": checked}


def analyze(receipt, previous=None):
    meta = receipt["backend"]
    if (receipt["protocol"] != "DEVIATION_reasoning_plan_v1" or receipt["sources"] != source_hashes()
            or receipt["runtime_archive_sha256"] != RUNTIME_SHA or meta["manifest"] != MANIFEST
            or meta["origin"] != "LIVE_LOCAL_LLM" or meta["server_version"] != RUNTIME_VERSION
            or meta["installed_model"]["digest"] != MANIFEST["digest"]
            or meta["endpoint"] != "http://127.0.0.1:11434"
            or receipt["execution"]["GITHUB_RUN_ATTEMPT"] != "1"
            or receipt["execution"]["RUNNER_ENVIRONMENT"] != "github-hosted"):
        raise ValueError("IDENTITY_DISCREPANCY")
    calls = receipt["calls"]
    if len(calls) > len(SCHEDULE):
        raise ValueError("CALL_LIMIT_EXCEEDED")
    decisions = {state: {} for state in STATES}
    usage, memos = [], []
    memo = "None"
    for record, slot in zip(calls, SCHEDULE):
        case, bonus, arm, phase = slot
        if record["slot"] != list(slot):
            raise ValueError("CALL_ORDER_DISCREPANCY")
        if arm == "D":
            memo = "None"
        request = request_for(*slot, memo)
        if request != record["request"]:
            raise ValueError("REQUEST_DISCREPANCY")
        if phase == "memo":
            memo, usable = read_memo(record)
            memos.append({"slot": record["slot"], "usable": usable, "memo": memo})
        else:
            decisions[case, bonus][arm] = decode_call(record, request)
        body = response_body(record)
        usage.append({key: body.get(key) if isinstance(body, dict) else None
                      for key in ("eval_count", "prompt_eval_count", "done_reason")})
    states = [adjudicate(*state, decisions[state], None if previous is None else previous[i]["proof"])
              for i, state in enumerate(STATES)]
    return {"recorded_calls": len(calls), "states": states, "memos": memos, "usage": usage,
            "input_sha256": digest(receipt), "stop": receipt["stop"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["collect", "score", "verify"])
    parser.add_argument("raw", type=Path)
    parser.add_argument("scored", type=Path, nargs="?")
    args = parser.parse_args()
    if args.operation == "collect":
        collect(args.raw)
    else:
        receipt = strict_json(args.raw.read_text())
        if args.operation == "score":
            write_json(args.scored, analyze(receipt))
        else:
            scored = strict_json(args.scored.read_text())
            if scored != analyze(receipt, scored["states"]):
                raise ValueError("ENGINE_REPLAY_DISCREPANCY")
            print("Verified all stored engine rows and exact certificates.")


if __name__ == "__main__":
    main()
