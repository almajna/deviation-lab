"""Independent payoff recomputation from public economic events.

Does not call Game.expected or the optimizer. Expected settlement uses declared
probabilities, never realized labels. Realized cash is independently ledgered.
"""
from fractions import Fraction
from deviation.markets.contracts import Rejection, counts
from deviation.markets.validation import validate_result


def pair(x):
    x=Fraction(x);return [x.numerator,x.denominator]


def recompute(receipt, controller, beliefs):
    validate_result(receipt)
    cfg=receipt["public_config"]
    D=cfg["economics"]["report_denominator"]
    members={a for a,v in cfg["agents"].items() if v["controller"]==controller}
    markets={e["payload"]["market_id"] for e in receipt["trace"]["events"] if e["type"]=="market_opened"}
    if not isinstance(beliefs,dict) or set(beliefs)!=markets:raise Rejection("BELIEF_COVERAGE")
    for p in beliefs.values():counts(p,D)
    wallets={"agent/"+a for a in members}
    events=receipt["trace"]["events"]
    initial=events[-1]["payload"]["initial_balances"]
    balances=dict(initial)
    pre_cash=Fraction(0);realized_cash=0;fees=0;claims={};reports={};attempts=0
    ids=set()
    for e in events:
        p=e["payload"]
        if e["type"]=="ledger_transfer":
            if p["transfer_id"] in ids:raise Rejection("DOUBLE_TRANSFER")
            ids.add(p["transfer_id"])
            balances[p["payer"]]-=p["amount"];balances[p["payee"]]+=p["amount"]
            if min(balances.values())<0:raise Rejection("UNFUNDED_TRANSFER")
            delta=(int(p["payee"] in wallets)-int(p["payer"] in wallets))*p["amount"]
            realized_cash+=delta
            if e["stage"]!="SETTLED":pre_cash+=delta
            if p["reason"]=="fee" and p["payer"] in wallets:fees+=p["amount"]
        elif e["type"]=="trade_accepted" and p["actor"] in members:
            claims[(p["actor"],p["market_id"])]=p["position_after"]
        elif e["type"]=="report_revealed" and p["actor"] in members:
            reports[(p["actor"],p["market_id"])]=p["counts"]
        if e["stage"]=="TRADE_OR_UPDATE" and e["type"] in {"trade_accepted","distribution_updated","action_noop","action_rejected"} and p["actor"] in members:
            attempts+=1
    if balances!=events[-1]["payload"]["final_balances"] or sum(balances.values())!=sum(initial.values()):
        raise Rejection("LEDGER_DISAGREEMENT")
    expected_claims=Fraction(0);expected_scores=Fraction(0)
    for (a,mid),holdings in claims.items():
        counts(beliefs[mid],D)
        expected_claims+=sum(Fraction(beliefs[mid][y],D)*holdings[y] for y in range(3))
    for (a,mid),reported in reports.items():
        counts(beliefs[mid],D)
        # Expanded Brier expression, independently of the engine score helper.
        for y in range(3):
            reward=cfg["economics"]["score_scale"]*(2*D*D-sum((n-D*int(y==k))**2 for k,n in enumerate(reported)))
            expected_scores+=Fraction(beliefs[mid][y],D)*reward
    weights=cfg["controllers"][controller]["external_weights"]
    external=sum(weights.get(c["task_id"],{}).get(c["model_id"],0) for c in receipt["allocation_plan"]["allocations"])
    effort=attempts*cfg["controllers"][controller]["effort_per_attempt"]
    expected_cash=pre_cash+expected_claims+expected_scores
    if realized_cash!=sum(balances[w]-initial[w] for w in wallets):raise Rejection("CASH_DISAGREEMENT")
    return {"expected_cash":pair(expected_cash),"expected_claims":pair(expected_claims),
        "expected_scores":pair(expected_scores),"pre_settlement_cash":pair(pre_cash),
        "fees":fees,"external_benefit":external,"effort":effort,
        "expected_utility":pair(expected_cash+external-effort),"realized_cash":realized_cash,
        "realized_utility":realized_cash+external-effort,"cash_conserved":True}


def welfare(receipt, probabilities):
    """Evaluator-only expected proxy, not a decision input or monetary welfare."""
    from deviation.markets.engine import market_id
    value=Fraction(0)
    for row in receipt["allocation_plan"]["allocations"]:
        if row["model_id"] is None:continue
        p=probabilities[market_id(row["task_id"],row["model_id"])]
        value+=Fraction(p[1]+2*p[2],2*sum(p))
    return pair(value)
