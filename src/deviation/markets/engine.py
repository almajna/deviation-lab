"""Outcome-free state machine. Only settle() accepts labels, after lock()."""
from copy import deepcopy
from fractions import Fraction
import re

from deviation.data.pipeline import digest
from .contracts import Rejection, action, closed, counts, event_shape, integer, score, text
from .numeric import NumericAmbiguity, POLICY_SHA256, funding, prices, quote

ECON_FIELDS = "b report_denominator score_scale price_denominator fee order_limit agent_position_limit cell_position_limit action_limit candidate_limit rounds sponsor_cap"


def market_id(task, model):
    return digest(["market", task, model])


class Engine:
    def __init__(self, tasks, economics, agents, controllers, schedule):
        closed(economics, ECON_FIELDS)
        for name, value in economics.items(): integer(value, 0, 10**12)
        for name in ["b", "report_denominator", "score_scale", "order_limit", "agent_position_limit", "cell_position_limit", "candidate_limit"]:
            integer(economics[name], 1, 1_000_000)
        integer(economics["price_denominator"], 3, 100_000_000)
        if not agents or not controllers: raise Rejection("INVALID_CONFIG")
        self.cfg, self.agents, self.controllers = deepcopy(economics), deepcopy(agents), deepcopy(controllers)
        self.stage, self.events, self.transfers = "PREPARED", [], []
        self.schedule, self.turn, self.used = deepcopy(schedule), 0, set()
        self.books, self.reports, self.commits, self.attempts = {}, {}, {}, {a: 0 for a in agents}
        self.commit_ids = {}
        self.tokens, self.balances = {}, {"fee_sink": 0}
        catalog = {t["task_id"]: set(t["model_options"]) for t in tasks}
        self.accepted, self.rejected = 0, 0
        for agent, definition in agents.items():
            text(agent)
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", agent): raise Rejection("INVALID_TYPE")
            closed(definition, "controller wallet")
            text(definition["controller"]); integer(definition["wallet"])
            if definition["controller"] not in controllers: raise Rejection("INVALID_CONFIG")
            self.balances[self.wallet(agent)] = definition["wallet"]
        for controller, definition in controllers.items():
            text(controller)
            closed(definition, "cash_cap token_cap action_cap position_cap external_weights effort_per_attempt")
            for name in ["cash_cap", "token_cap", "action_cap", "position_cap", "effort_per_attempt"]: integer(definition[name])
            if not isinstance(definition["external_weights"], dict): raise Rejection("INVALID_CONFIG")
            for task, weights in definition["external_weights"].items():
                text(task)
                if not isinstance(weights, dict): raise Rejection("INVALID_CONFIG")
                if task not in catalog or set(weights) - catalog[task]: raise Rejection("INVALID_PREFERENCES")
                for model, weight in weights.items(): text(model); integer(weight)
        for task in tasks:
            for model in sorted(task["model_options"]):
                mid = market_id(task["task_id"], model)
                F = funding(economics["b"])
                self.balances[self.maker(mid)] = F
                self.books[mid] = {"task_id": task["task_id"], "model_id": model,
                    "q": [0, 0, 0], "seq": 0, "funding": F, "revenue": 0,
                    "holdings": {a: [0, 0, 0] for a in agents}}
                for a in sorted(agents): self.tokens[(a, mid)] = digest(["report", a, mid])
        for actor, mid in schedule:
            if actor not in agents or mid not in self.books: raise Rejection("INVALID_CONFIG")
        for controller, limits in controllers.items():
            members = [a for a in agents if agents[a]["controller"] == controller]
            if (sum(agents[a]["wallet"] for a in members) > limits["cash_cap"]
                    or len(members) * len(self.books) > limits["token_cap"]
                    or sum(actor in members for actor, _ in schedule) > limits["action_cap"]):
                raise Rejection("CONTROLLER_BUDGET")
        K = 2 * economics["report_denominator"] ** 2 * economics["score_scale"]
        self.score_reserve = len(self.tokens) * K
        self.balances["scoring_pool"] = self.score_reserve
        sponsorship = sum(self.balances.values())
        if sponsorship > economics["sponsor_cap"]: raise Rejection("SPONSOR_BUDGET")
        self.initial = deepcopy(self.balances)
        for mid, book in sorted(self.books.items()):
            self.emit("market_opened", {"market_id": mid, "task_id": book["task_id"], "model_id": book["model_id"],
                "b": self.cfg["b"], "funding": book["funding"], "maker_account": self.maker(mid),
                "q": [0, 0, 0], "price_counts": prices([0, 0, 0], self.cfg["b"], self.cfg["price_denominator"]),
                "price_denominator": self.cfg["price_denominator"]})
        self.advance("REPORT_COMMIT")

    @staticmethod
    def wallet(actor): return "agent/" + actor

    @staticmethod
    def maker(mid): return "maker/" + mid

    def emit(self, kind, payload, actor="system"):
        e = {"seq": len(self.events), "time_step": len(self.events), "stage": self.stage,
             "actor": actor, "visibility": "POST_SETTLEMENT" if self.stage == "SETTLED" else "PUBLIC",
             "type": kind, "payload": deepcopy(payload)}
        event_shape(e)
        self.events.append(e)

    def advance(self, stage):
        old = self.stage
        self.stage = stage
        self.emit("stage_changed", {"previous": old, "current": stage})

    def _transact(self, transfers):
        """Check the full batch on a copy, then commit once; no partial debit."""
        balances = deepcopy(self.balances)
        rows = []
        for payer, payee, amount, reason, scope in transfers:
            integer(amount)
            if amount == 0: continue
            if payer not in balances or payee not in balances or payer == payee or balances[payer] < amount:
                raise Rejection("INSUFFICIENT_CASH")
            balances[payer] -= amount
            balances[payee] += amount
            rows.append({"transfer_id": f"transfer-{len(self.transfers) + len(rows)}", "payer": payer,
                         "payee": payee, "amount": amount, "reason": reason, "scope": scope})
        self.balances = balances
        self.transfers.extend(rows)
        return rows

    def _project_transfers(self, rows):
        for row in rows: self.emit("ledger_transfer", row)

    def commit(self, actor, mid, submitted, order_id=None):
        if self.stage != "REPORT_COMMIT": raise Rejection("WRONG_STAGE")
        if (actor, mid) not in self.tokens: raise Rejection("INVALID_TOKEN")
        if (actor, mid) in self.commits: raise Rejection("DUPLICATE_ID")
        if submitted is not None: counts(submitted, self.cfg["report_denominator"])
        order_id = order_id if order_id is not None else actor + "/report-" + self.tokens[(actor, mid)]
        text(order_id)
        if not order_id.startswith(actor + "/"): raise Rejection("INVALID_ID_NAMESPACE")
        if order_id.startswith(actor + "/report-") and order_id != actor + "/report-" + self.tokens[(actor, mid)]:
            raise Rejection("INVALID_ID_NAMESPACE")
        if order_id in self.used: raise Rejection("DUPLICATE_ID")
        self.used.add(order_id)
        self.commit_ids[(actor, mid)] = order_id
        self.commits[(actor, mid)] = deepcopy(submitted)

    def reveal(self):
        if self.stage != "REPORT_COMMIT" or set(self.commits) != set(self.tokens): raise Rejection("WRONG_STAGE")
        self.advance("REPORT_REVEAL")
        for (a, mid), values in sorted(self.commits.items()):
            if values is not None:
                self.reports[(a, mid)] = deepcopy(values)
                self.emit("report_revealed", {"actor": a, "order_id": self.commit_ids[(a, mid)], "market_id": mid, "report_token": self.tokens[(a, mid)],
                    "counts": values, "denominator": self.cfg["report_denominator"]}, a)
        self.advance("TRADE_OR_UPDATE")

    def inspect_order(self, actor, mid, delta, limit=10**15):
        """Pure candidate interface: no outcome store, transfer or slot mutation."""
        if self.stage != "TRADE_OR_UPDATE": raise Rejection("WRONG_STAGE")
        if actor not in self.agents or mid not in self.books: raise Rejection("WRONG_ACTOR")
        from .contracts import vector
        vector(delta, signed=True); integer(limit, -10**15)
        if not any(delta): raise Rejection("ZERO_ORDER")
        c, book = self.cfg, self.books[mid]
        if sum(abs(n) for n in delta) > c["order_limit"]: raise Rejection("QUANTITY_LIMIT")
        position = [x + d for x, d in zip(book["holdings"][actor], delta)]
        q = [x + d for x, d in zip(book["q"], delta)]
        if min(position) < 0: raise Rejection("UNOWNED_SALE")
        members = [a for a in self.agents if self.agents[a]["controller"] == self.agents[actor]["controller"]]
        group = [sum(book["holdings"][a][k] for a in members) + delta[k] for k in range(3)]
        if (max(position) > c["agent_position_limit"] or max(q) > c["cell_position_limit"]
                or max(group) > self.controllers[self.agents[actor]["controller"]]["position_cap"]):
            raise Rejection("POSITION_LIMIT")
        try:
            receipt = quote(book["q"], q, c["b"])
            before_prices = prices(book["q"], c["b"], c["price_denominator"])
            after_prices = prices(q, c["b"], c["price_denominator"])
        except NumericAmbiguity as exc: raise Rejection("NUMERIC_AMBIGUITY") from exc
        charge = receipt["charge"]
        if charge + c["fee"] > limit: raise Rejection("ORDER_LIMIT")
        if self.balances[self.wallet(actor)] - charge - c["fee"] < 0: raise Rejection("INSUFFICIENT_CASH")
        if self.balances[self.maker(mid)] + charge < max(q): raise Rejection("MAKER_INSOLVENT")
        return {"receipt": receipt, "position": position, "q": q,
                "before_prices": before_prices, "after_prices": after_prices}

    def apply(self, request, *, allowed_kinds=None):
        if self.stage != "TRADE_OR_UPDATE" or self.turn >= len(self.schedule): raise Rejection("WRONG_STAGE")
        actor, mid = self.schedule[self.turn]
        slot = self.turn
        self.turn += 1  # Invalid requests consume their assigned opportunity.
        self.attempts[actor] += 1
        reserved_order_id = None
        try:
            if self.attempts[actor] > self.cfg["action_limit"]: raise Rejection("ACTION_LIMIT")
            action(request)
            if request["actor"] != actor or request["market_id"] != mid: raise Rejection("WRONG_ACTOR")
            if request["stage"] != self.stage: raise Rejection("WRONG_STAGE")
            if allowed_kinds is not None and request["kind"] not in allowed_kinds: raise Rejection("DISALLOWED_ACTION")
            if request["order_id"] in self.used: raise Rejection("DUPLICATE_ID")
            self.used.add(request["order_id"])
            reserved_order_id = request["order_id"]
            book = self.books[mid]
            if request["expected_state_seq"] != book["seq"]: raise Rejection("STALE_STATE")
            kind = request["kind"]
            if kind == "no_op":
                self.emit("action_noop", {"actor": actor, "order_id": request["order_id"], "market_id": mid, "slot": slot}, actor)
                return True
            if kind == "update_distribution":
                if request["denominator"] != self.cfg["report_denominator"]: raise Rejection("INVALID_DISTRIBUTION")
                rows = self._transact([(self.wallet(actor), "fee_sink", self.cfg["fee"], "fee", mid)])
                self.reports[(actor, mid)] = deepcopy(request["counts"])
                self.emit("distribution_updated", {"actor": actor, "order_id": request["order_id"], "market_id": mid,
                    "state_seq_before": book["seq"], "state_seq_after": book["seq"] + 1, "counts": request["counts"],
                    "denominator": request["denominator"], "fee": self.cfg["fee"], "transfer_ids": [r["transfer_id"] for r in rows]}, actor)
                self._project_transfers(rows)
                book["seq"] += 1
                self.accepted += 1
                return True
            if kind != "trade_shares": raise Rejection("WRONG_STAGE")
            result = self.inspect_order(actor, mid, request["share_delta"], request["max_net_debit"])
            charge, fee = result["receipt"]["charge"], self.cfg["fee"]
            before_cash = [self.balances[self.wallet(actor)], self.balances[self.maker(mid)], self.balances["fee_sink"]]
            transfers = [(self.wallet(actor), self.maker(mid), charge, "trade_charge", mid)] if charge >= 0 else [(self.maker(mid), self.wallet(actor), -charge, "trade_refund", mid)]
            transfers.append((self.wallet(actor), "fee_sink", fee, "fee", mid))
            rows = self._transact(transfers)
            payload = {"actor": actor, "order_id": request["order_id"], "market_id": mid,
                "state_seq_before": book["seq"], "state_seq_after": book["seq"] + 1,
                "q_before": book["q"], "q_after": result["q"], "position_before": book["holdings"][actor],
                "position_after": result["position"], "price_counts_before": result["before_prices"],
                "price_counts_after": result["after_prices"], "price_denominator": self.cfg["price_denominator"],
                "share_delta": request["share_delta"], "signed_maker_charge": charge, "fee": fee,
                "quote_interval": result["receipt"]["interval"], "quote_bits": result["receipt"]["bits"],
                "quote_policy_sha256": POLICY_SHA256, "max_net_debit": request["max_net_debit"],
                "trader_cash_before": before_cash[0], "trader_cash_after": self.balances[self.wallet(actor)],
                "maker_cash_before": before_cash[1], "maker_cash_after": self.balances[self.maker(mid)],
                "fee_sink_before": before_cash[2], "fee_sink_after": self.balances["fee_sink"],
                "transfer_ids": [r["transfer_id"] for r in rows]}
            book["q"], book["holdings"][actor] = result["q"], result["position"]
            book["seq"] += 1
            book["revenue"] += charge
            self.emit("trade_accepted", payload, actor)
            self._project_transfers(rows)
            self.accepted += 1
            self.invariants()
            return True
        except Rejection as exc:
            self.rejected += 1
            self.emit("action_rejected", {"actor": actor, "slot": slot, "reason": exc.code,
                                          "reserved_order_id": reserved_order_id}, actor)
            return False

    def lock(self, plan, expected_values, artifact_sha):
        if self.stage != "TRADE_OR_UPDATE" or self.turn != len(self.schedule): raise Rejection("WRONG_STAGE")
        self.advance("ALLOCATION_LOCKED")
        self.emit("allocation_locked", {"plan": plan, "expected_values": expected_values,
                                      "reservation_artifact_sha256": artifact_sha})

    def settle(self, categories):
        if self.stage != "ALLOCATION_LOCKED": raise Rejection("WRONG_STAGE")
        if not isinstance(categories, dict) or set(categories) != set(self.books): raise Rejection("INVALID_OUTCOMES")
        for y in categories.values(): integer(y, 0, 2)
        self.advance("SETTLED")
        for mid, book in sorted(self.books.items()):
            y, before = categories[mid], deepcopy(book["q"])
            claims = {a: book["holdings"][a][y] for a in sorted(self.agents)}
            rows = self._transact([(self.maker(mid), self.wallet(a), n, "claim_redemption", mid) for a, n in claims.items()])
            payout = sum(claims.values())
            final = self.balances[self.maker(mid)]
            self.emit("market_settled", {"market_id": mid, "category": y, "q_before": before,
                "claims": claims, "revenue": book["revenue"], "payout": payout, "funding": book["funding"],
                "final_cash": final, "pnl": final - book["funding"], "loss": max(book["funding"] - final, 0)})
            self._project_transfers(rows)
            book["q"] = [0, 0, 0]
            book["holdings"] = {a: [0, 0, 0] for a in self.agents}
        # Score original committed reports, never later public revisions.
        for (a, mid), values in sorted(self.commits.items()):
            if values is None: continue
            reward = score(values, self.cfg["report_denominator"], self.cfg["score_scale"], categories[mid])
            rows = self._transact([("scoring_pool", self.wallet(a), reward, "score_reward", mid)])
            self.emit("score_settled", {"actor": a, "market_id": mid, "report_token": self.tokens[(a, mid)],
                "counts": values, "denominator": self.cfg["report_denominator"], "category": categories[mid],
                "score": reward, "remaining_pool": self.balances["scoring_pool"], "transfer_ids": [r["transfer_id"] for r in rows]})
            self._project_transfers(rows)
        self.invariants()

    def invariants(self):
        if sum(self.balances.values()) != sum(self.initial.values()) or min(self.balances.values()) < 0:
            raise RuntimeError("cash conservation failure")
        for mid, book in self.books.items():
            if any(book["q"][k] != sum(h[k] for h in book["holdings"].values()) for k in range(3)):
                raise RuntimeError("claim conservation failure")
            if self.balances[self.maker(mid)] < max(book["q"]): raise RuntimeError("maker insolvency")

    def snapshot(self, actor, mid):
        """Public + recipient-owned economic state; no outcomes or commits."""
        if self.stage not in ["REPORT_COMMIT", "TRADE_OR_UPDATE"]: raise Rejection("WRONG_STAGE")
        if actor not in self.agents or mid not in self.books: raise Rejection("WRONG_ACTOR")
        return deepcopy({"stage": self.stage, "turn": self.turn, "seq": len(self.events),
            "market_id": mid, "state_seq": self.books[mid]["seq"], "own_cash": self.balances[self.wallet(actor)],
            "own_positions": self.books[mid]["holdings"][actor], "limits": self.cfg,
            "markets": {m: {"task_id": b["task_id"], "model_id": b["model_id"], "q": b["q"],
                           "price_counts": prices(b["q"], self.cfg["b"], self.cfg["price_denominator"])} for m, b in self.books.items()},
            "history": self.events})
