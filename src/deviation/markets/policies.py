"""Pure decision interfaces: copied packets contain no realized outcomes."""
from fractions import Fraction
from itertools import product

from .contracts import Rejection, counts
from .numeric import NumericAmbiguity, prices, project_rational, quote, transform


def base_action(packet, kind):
    return {"schema_version": "0.3", "kind": kind, "stage": packet["stage"],
            "actor": packet["agent_id"], "order_id": packet["agent_id"] + "/" + ("report-" + packet["report_token"] if packet["stage"] == "REPORT_COMMIT" else f"order-{packet['turn']}"),
            "market_id": packet["market_id"], "expected_state_seq": packet["state_seq"]}


def candidates(packet):
    """Finite pure Phase 4 interface, using public state + own portfolio only."""
    cfg, mid = packet["limits"], packet["market_id"]
    Q = cfg["order_limit"]
    if (4 * Q ** 3 + 6 * Q ** 2 + 8 * Q + 3) // 3 > cfg["candidate_limit"]:
        raise Rejection("CANDIDATE_LIMIT")
    q = packet["markets"][mid]["q"]
    output = []
    for d in product(range(-Q, Q + 1), repeat=3):
        if not any(d) or sum(abs(n) for n in d) > Q: continue
        pos = [h + x for h, x in zip(packet["own_positions"], d)]
        after = [h + x for h, x in zip(q, d)]
        group = [h + x for h, x in zip(packet["own_group_positions"], d)]
        if (min(pos) < 0 or max(pos) > cfg["agent_position_limit"]
                or max(after) > cfg["cell_position_limit"] or max(group) > packet["own_group_position_cap"]): continue
        try:
            receipt = quote(q, after, cfg["b"])
            projected = prices(after, cfg["b"], cfg["price_denominator"])
        except NumericAmbiguity: continue  # Numeric-ambiguous orders are inadmissible.
        debit = receipt["charge"] + cfg["fee"]
        if debit > packet["own_cash"]: continue
        output.append({"share_delta": list(d), "charge": receipt["charge"], "fee": cfg["fee"],
                       "max_net_debit": debit, "price_counts_after": projected})
    return output


class SignalFollowing:
    """Fixed supplied belief, not a Bayesian posterior or equilibrium policy."""
    def act(self, packet):
        if packet["stage"] == "REPORT_COMMIT":
            if packet["decline_report"]: return None
            out = base_action(packet, "report_distribution")
            out.update(counts=list(packet["own_signal"]), denominator=packet["limits"]["report_denominator"],
                       report_token=packet["report_token"])
            return out
        noop = base_action(packet, "no_op")
        if packet["mechanism"] == "interactive-pool":
            if packet["own_last_report"] == packet["own_signal"]: return noop
            out = base_action(packet, "update_distribution")
            out.update(counts=list(packet["own_signal"]), denominator=packet["limits"]["report_denominator"])
            return out
        if packet["mechanism"] != "lmsr": return noop
        belief = [Fraction(n, packet["limits"]["report_denominator"]) for n in packet["own_signal"]]
        best, best_key = None, (Fraction(0), 0, (0, 0, 0))
        for candidate in candidates(packet):
            d = candidate["share_delta"]
            gain = sum(r * x for r, x in zip(belief, d)) - candidate["charge"] - candidate["fee"]
            # Explicit no-op wins all zero-gain ties; smaller/lex delta thereafter.
            key = (gain, -sum(abs(x) for x in d), tuple(-x for x in d))
            if key > best_key: best, best_key = candidate, key
        if best is None: return noop
        out = base_action(packet, "trade_shares")
        out.update(share_delta=best["share_delta"], max_net_debit=best["max_net_debit"])
        return out


def pooled(reports, mid, D):
    values = [p for (a, m), p in reports.items() if m == mid]
    if not values: return [Fraction(1, 3)] * 3
    return [sum(Fraction(v[k], D) for v in values) / len(values) for k in range(3)]


def fit_temperature(rows, training_rows, D, P):
    """Frozen global T selected from training pairs only, exact Brier comparison."""
    expected = {(r["task_id"], r["model_id"]) for r in training_rows}
    seen = set()
    from .contracts import closed, integer
    if not isinstance(rows, list) or not rows: raise Rejection("MISSING_TRAINING_REPORTS")
    for row in rows:
        closed(row, "task_id model_id counts category")
        counts(row["counts"], D); integer(row["category"], 0, 2)
        pair = row["task_id"], row["model_id"]
        if pair in seen or pair not in expected: raise Rejection("TRAINING_LEAKAGE")
        seen.add(pair)
    if seen != expected: raise Rejection("MISSING_TRAINING_REPORTS")
    losses = []
    for T in ["1", "1/2", "2"]:
        loss = Fraction(0)
        for row in rows:
            p = transform([Fraction(n, D) for n in row["counts"]], T, P)
            loss += sum((Fraction(n, P) - (i == row["category"])) ** 2 for i, n in enumerate(p))
        losses.append(loss)
    return ["1", "1/2", "2"][min(range(3), key=lambda i: (losses[i], i))]


def candidate_value(packet, candidate, *, additional_effort=0):
    """Last-slot expected-utility interface, never a hindsight outcome oracle."""
    from .contracts import integer
    from deviation.simulator.policies import optimize
    from deviation.data.pipeline import digest
    if packet["stage"] != "TRADE_OR_UPDATE" or packet["mechanism"] != "lmsr" or packet["remaining_slots"] != 1:
        raise Rejection("UNSUPPORTED_HORIZON")
    if digest(candidate) not in {digest(c) for c in candidates(packet)}: raise Rejection("INVALID_CANDIDATE")
    integer(additional_effort)
    D, P = packet["limits"]["report_denominator"], packet["limits"]["price_denominator"]
    belief = [Fraction(n, D) for n in packet["own_signal"]]
    cash = sum(r * d for r, d in zip(belief, candidate["share_delta"])) - candidate["charge"] - candidate["fee"]
    def external(override):
        values = {t["task_id"]: {} for t in packet["public_tasks"]}
        for mid, book in packet["markets"].items():
            p = override if mid == packet["market_id"] and override is not None else book["price_counts"]
            values[book["task_id"]][book["model_id"]] = Fraction(p[1] + 2 * p[2], 2 * P)
        allocation = optimize(sorted(packet["public_tasks"], key=lambda t: t["task_id"]), packet["reservations"], packet["reservation_budget"], values)
        return sum(packet["own_utility_view"].get(c["task_id"], {}).get(c["model_id"], 0) for c in allocation)
    delta = external(candidate["price_counts_after"]) - external(None)
    utility = cash + delta - additional_effort
    return {"basis": "DECLARED_BELIEF_AND_PUBLIC_STATE_ONLY", "expected_cash_gain": [cash.numerator, cash.denominator],
            "external_benefit_delta": delta, "additional_effort": additional_effort,
            "expected_utility_gain": [utility.numerator, utility.denominator]}
