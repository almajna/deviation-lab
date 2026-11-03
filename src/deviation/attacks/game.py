"""Outcome-free search games over the actual Phase 3 transition engine.

The trusted observation harness may execute an honest prefix. Optimizers receive
only an Engine containing public/revealed state and a controller's own beliefs.
No scenario, outcome store, or future honest private signal is a Game field.
"""
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction

from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection, counts, score
from deviation.markets.engine import Engine
from deviation.markets.policies import SignalFollowing, base_action, pooled
from deviation.markets.runner import _prepare, _allocation, allowed_actions, packet


@dataclass
class Game:
    engine: Engine
    tasks: list
    artifact: dict
    temperature: str
    training_means: dict
    budget: int
    seed: int
    mechanism: str
    controller: str
    beliefs: dict
    scope: str
    report_slots: list
    announced_reports: dict

    @property
    def members(self):
        return sorted(a for a, v in self.engine.agents.items() if v["controller"] == self.controller)

    def observation(self):
        return {"scope": self.scope, "stage": self.engine.stage, "turn": self.engine.turn,
            "public_schedule": self.engine.schedule, "prefix_events": self.engine.events,
            "books": self.engine.books, "balances": self.engine.balances,
            "initial_balances": self.engine.initial, "public_agents": self.engine.agents,
            "economics": self.engine.cfg, "attempts": self.engine.attempts,
            "used_command_ids": sorted(self.engine.used),
            "reports": [[a,m,p] for (a,m),p in sorted(self.engine.reports.items())],
            "known_commitments": [[a,m,p] for (a,m),p in sorted(self.engine.commits.items())],
            "controllers": self.engine.controllers, "beliefs": self.beliefs,
            "tasks": self.tasks, "reservations": self.artifact, "budget": self.budget,
            "temperature": self.temperature, "training_means": self.training_means,
            "seed": self.seed, "mechanism": self.mechanism,
            "report_slots": self.report_slots, "announced_reports": self.announced_reports}

    def policy_packet(self):
        a, mid = self.engine.schedule[self.engine.turn]
        p = self.engine.snapshot(a, mid)
        c = self.engine.controllers[self.controller]
        p.update(agent_id=a, schema_version="0.3", mechanism=self.mechanism,
            own_signal=deepcopy(self.beliefs[mid]), decline_report=False,
            report_token=self.engine.tokens[(a, mid)], own_last_report=self.engine.reports.get((a, mid)),
            own_group_positions=[sum(self.engine.books[mid]["holdings"][a][k] for a in self.members) for k in range(3)],
            own_group_position_cap=c["position_cap"], own_utility_view=deepcopy(c["external_weights"]),
            reservations=deepcopy(self.artifact["reservations"]), reservation_budget=self.budget,
            public_tasks=deepcopy(self.tasks), remaining_slots=len(self.engine.schedule)-self.engine.turn)
        return p

    def allocation(self):
        return _allocation(self.engine, self.tasks, self.artifact, self.mechanism,
            self.temperature, self.training_means, self.budget, self.seed)[0]

    def expected(self):
        """Absolute controller expected terminal cash/utility; no realized labels."""
        D = self.engine.cfg["report_denominator"]
        cash = sum(Fraction(self.engine.balances[self.engine.wallet(a)] - self.engine.initial[self.engine.wallet(a)]) for a in self.members)
        for mid, book in self.engine.books.items():
            cash += sum(Fraction(self.beliefs[mid][y], D) * sum(book["holdings"][a][y] for a in self.members) for y in range(3))
        # Commitments, not mutable public revisions, earn their fixed score claim.
        for (a, mid), report in self.engine.commits.items():
            if a in self.members and report is not None:
                cash += sum(Fraction(self.beliefs[mid][y], D) * score(report, D, self.engine.cfg["score_scale"], y) for y in range(3))
        plan = self.allocation()
        c = self.engine.controllers[self.controller]
        external = sum(c["external_weights"].get(row["task_id"], {}).get(row["model_id"], 0) for row in plan["allocations"])
        effort = c["effort_per_attempt"] * sum(self.engine.attempts[a] for a in self.members)
        return {"cash": cash, "external": Fraction(external), "effort": Fraction(effort),
                "utility": cash + external - effort, "allocation": plan}

    def complete_reports(self):
        for (a, mid), token in sorted(self.engine.tokens.items()):
            if (a, mid) in self.engine.commits: continue
            self.engine.commit(a, mid, self.announced_reports[a][mid])
        self.engine.reveal()
        while self.engine.turn < len(self.engine.schedule):
            req = base_action(self.policy_packet_any(), "no_op")
            if not self.engine.apply(req, allowed_kinds=allowed_actions(self.mechanism)):
                raise Rejection("INVALID_SEARCH_TRANSITION")

    def policy_packet_any(self):
        a, mid = self.engine.schedule[self.engine.turn]
        # Static report games have no future updates/trades; no-op needs only IDs.
        return {"stage": self.engine.stage, "agent_id": a, "turn": self.engine.turn,
            "market_id": mid, "state_seq": self.engine.books[mid]["seq"]}


def prepare_game(scenario, controller, mechanism, *, scope="terminal", public_report_model=None):
    """Trusted harness. Private data is stripped before constructing a Game."""
    public = deepcopy({k: v for k, v in scenario.items() if k != "sealed_outcomes"})
    tasks, artifact, T, quality, engine = _prepare(public)
    if controller not in engine.controllers: raise Rejection("UNKNOWN_CONTROLLER")
    members = sorted(a for a, v in engine.agents.items() if v["controller"] == controller)
    if not members: raise Rejection("EMPTY_CONTROLLER")
    beliefs = deepcopy(public["agents"][members[0]]["signals"])
    if any(public["agents"][a]["signals"] != beliefs for a in members):
        raise Rejection("COMMON_CONTROLLER_BELIEF_REQUIRED")
    for c, definition in engine.controllers.items():
        if c != controller: definition["external_weights"] = {}  # Not an observation.
    g = Game(engine, tasks, artifact, T, quality, public["reservation_budget"], public["seed"],
             mechanism, controller, beliefs, scope, [], {})
    if scope == "reports":
        if mechanism not in ["pool", "score", "calibrated-pool"]: raise Rejection("UNSUPPORTED_REPORT_GAME")
        opponents = set(engine.agents) - set(members)
        if not isinstance(public_report_model, dict) or set(public_report_model) != opponents:
            raise Rejection("PUBLIC_REPORT_MODEL_REQUIRED")
        for a, values in public_report_model.items():
            if set(values) != set(engine.books): raise Rejection("PUBLIC_REPORT_MODEL_REQUIRED")
            for p in values.values():
                if p is not None: counts(p, engine.cfg["report_denominator"])
        # A single last-global commitment: every own signal has actually been
        # observed in earlier own report opportunities or this current packet.
        # Opponent commitments are NOT read; only the imposed public model is.
        target = sorted(engine.tokens)[-1]
        if target[0] not in members: raise Rejection("LAST_COMMIT_NOT_CONTROLLED")
        g.announced_reports = deepcopy(public_report_model)
        g.report_slots = [target]
        for a, mid in sorted(engine.tokens):
            if (a, mid) == target: continue
            values = (None if public["agents"][a]["decline_report"] else beliefs[mid]) if a in members else public_report_model[a][mid]
            engine.commit(a, mid, values)
        return g
    if scope != "terminal": raise Rejection("INVALID_SEARCH_SCOPE")
    policy = SignalFollowing()
    for a, mid in sorted(engine.tokens):
        info = packet(engine, public, a, mid, mechanism, artifact)
        command = policy.act(info)
        engine.commit(a, mid, None if command is None else command["counts"])
    engine.reveal()
    # Schedule is a preannounced protocol parameter, not a future event trace.
    start = len(engine.schedule)
    while start and engine.schedule[start-1][0] in members: start -= 1
    if start == len(engine.schedule): raise Rejection("NO_CONTROLLED_TERMINAL_SUFFIX")
    while engine.turn < start:
        a, mid = engine.schedule[engine.turn]
        command = policy.act(packet(engine, public, a, mid, mechanism, artifact))
        engine.apply(command, allowed_kinds=allowed_actions(mechanism))
    return g
