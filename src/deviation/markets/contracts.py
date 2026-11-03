"""Closed v0.3 boundaries; active v0.2 contracts are not modified."""
from fractions import Fraction
import re
from deviation.contracts import ContractError


class Rejection(ContractError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def closed(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise Rejection("INVALID_FIELDS")


def integer(value, low=0, high=10**15):
    if type(value) is not int or not low <= value <= high:
        raise Rejection("INVALID_TYPE")


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise Rejection("INVALID_TYPE")


def counts(values, denominator):
    integer(denominator, 1, 100_000_000)
    if not isinstance(values, list) or len(values) != 3:
        raise Rejection("INVALID_DISTRIBUTION")
    for n in values: integer(n, 0, denominator)
    if sum(values) != denominator: raise Rejection("INVALID_DISTRIBUTION")


def vector(values, *, signed=False):
    if not isinstance(values, list) or len(values) != 3: raise Rejection("INVALID_TYPE")
    for n in values: integer(n, -1_000_000 if signed else 0, 1_000_000)


def action(value):
    if not isinstance(value, dict): raise Rejection("INVALID_FIELDS")
    kind = value.get("kind")
    common = "schema_version kind stage actor order_id market_id expected_state_seq"
    extra = {"trade_shares": " share_delta max_net_debit", "report_distribution": " counts denominator report_token",
             "update_distribution": " counts denominator", "no_op": ""}
    if not isinstance(kind, str) or kind not in extra: raise Rejection("INVALID_TYPE")
    closed(value, common + extra[kind])
    if value["schema_version"] != "0.3": raise Rejection("INVALID_VERSION")
    for key in ["actor", "order_id", "market_id"]: text(value[key])
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value["actor"]): raise Rejection("INVALID_TYPE")
    if not value["order_id"].startswith(value["actor"] + "/"): raise Rejection("INVALID_ID_NAMESPACE")
    integer(value["expected_state_seq"])
    if value["stage"] not in ["REPORT_COMMIT", "TRADE_OR_UPDATE"]: raise Rejection("WRONG_STAGE")
    if kind == "trade_shares":
        vector(value["share_delta"], signed=True)
        integer(value["max_net_debit"], -10**15)
    elif kind in {"report_distribution", "update_distribution"}:
        counts(value["counts"], value["denominator"])
        if kind == "report_distribution": text(value["report_token"])


def score(n, D, k, y):
    counts(n, D); integer(k, 1, 1_000_000); integer(y, 0, 2)
    return k * (2 * D * D - sum((v - D * (i == y)) ** 2 for i, v in enumerate(n)))


EVENTS = {
    "market_opened": "market_id task_id model_id b funding maker_account q price_counts price_denominator",
    "stage_changed": "previous current",
    "report_revealed": "actor order_id market_id report_token counts denominator",
    "distribution_updated": "actor order_id market_id state_seq_before state_seq_after counts denominator fee transfer_ids",
    "action_rejected": "actor slot reason reserved_order_id",
    "action_noop": "actor order_id market_id slot",
    "trade_accepted": "actor order_id market_id state_seq_before state_seq_after q_before q_after position_before position_after price_counts_before price_counts_after price_denominator share_delta signed_maker_charge fee quote_interval quote_bits quote_policy_sha256 max_net_debit trader_cash_before trader_cash_after maker_cash_before maker_cash_after fee_sink_before fee_sink_after transfer_ids",
    "ledger_transfer": "transfer_id payer payee amount reason scope",
    "allocation_locked": "plan expected_values reservation_artifact_sha256",
    "market_settled": "market_id category q_before claims revenue payout funding final_cash pnl loss",
    "score_settled": "actor market_id report_token counts denominator category score remaining_pool transfer_ids",
    "economic_summary": "initial_balances final_balances controllers maker_losses score_reserve score_paid fees accepted rejected realized_report evaluation",
}
STAGES = ["PREPARED", "REPORT_COMMIT", "REPORT_REVEAL", "TRADE_OR_UPDATE", "ALLOCATION_LOCKED", "SETTLED"]


def event_shape(e):
    closed(e, "seq time_step stage actor visibility type payload")
    integer(e["seq"]); integer(e["time_step"]); text(e["actor"])
    if e["stage"] not in STAGES or e["visibility"] not in ["PUBLIC", "POST_SETTLEMENT"]:
        raise Rejection("INVALID_TYPE")
    if not isinstance(e["type"], str) or e["type"] not in EVENTS: raise Rejection("INVALID_TYPE")
    closed(e["payload"], EVENTS[e["type"]])
    post = e["type"] in ["market_settled", "score_settled", "economic_summary"]
    if post and (e["stage"] != "SETTLED" or e["visibility"] != "POST_SETTLEMENT"):
        raise Rejection("OUTCOME_LEAKAGE")
    if e["stage"] != "SETTLED" and e["visibility"] != "PUBLIC": raise Rejection("OUTCOME_LEAKAGE")


def mean(values, denominator):
    counts(values, denominator)
    return Fraction(values[1] + 2 * values[2], 2 * denominator)
