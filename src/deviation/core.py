"""Minimal, dependency-free and fully SYNTHETIC budget-routing reference.

This is intentionally *not* a prediction market, real-data benchmark, attacker,
or scientific result. It establishes a reproducible event-log/API smoke test.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import math


@dataclass(frozen=True)
class Arm:
    model_id: str
    cost: float


@dataclass(frozen=True)
class Task:
    task_id: str
    cheap: Arm
    strong: Arm
    forecast_cheap: float
    forecast_strong: float


@dataclass(frozen=True)
class ObservedOutcome:
    """Post-decision held-out result; never an input to choose_routes."""
    task_id: str
    model_id: str
    quality: float


def choose_routes(tasks: list[Task], budget: float) -> dict[str, str]:
    """Select cheapest arm for each task; greedily upgrade by estimated gain/cost.

    This is a toy two-arm baseline, not a generally optimal knapsack solver.
    Strict input validation prevents silent budget or unit errors.
    """
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("budget must be a finite, nonnegative number")
    if len({t.task_id for t in tasks}) != len(tasks):
        raise ValueError("duplicate task IDs")
    for t in tasks:
        if t.cheap.model_id == t.strong.model_id:
            raise ValueError("task arms must be distinct")
        if any(not math.isfinite(v) for v in (t.cheap.cost, t.strong.cost, t.forecast_cheap, t.forecast_strong)):
            raise ValueError("non-finite costs or forecasts")
        if t.cheap.cost < 0 or t.strong.cost <= t.cheap.cost:
            raise ValueError("strong arm must cost more than nonnegative cheap arm")
        if not all(0 <= p <= 1 for p in (t.forecast_cheap, t.forecast_strong)):
            raise ValueError("forecast must be in [0,1]")
    min_cost = sum(t.cheap.cost for t in tasks)
    if min_cost > budget + 1e-9:
        raise ValueError("budget cannot fund cheap arm for every task")
    choices = {t.task_id: t.cheap.model_id for t in tasks}
    remaining = budget - min_cost
    upgrades = []
    for t in tasks:
        delta_cost = t.strong.cost - t.cheap.cost
        delta_value = t.forecast_strong - t.forecast_cheap
        upgrades.append((delta_value / delta_cost, t.task_id, delta_cost, delta_value, t.strong.model_id))
    upgrades.sort(key=lambda x: (-x[0], x[1]))
    for _, task_id, delta_cost, delta_value, model_id in upgrades:
        if delta_value > 0 and delta_cost <= remaining + 1e-9:
            choices[task_id] = model_id
            remaining -= delta_cost
    return choices


def evaluate_selected(tasks: list[Task], choices: Mapping[str, str], outcomes: list[ObservedOutcome]) -> tuple[float, float]:
    """Evaluate *after* decisions. Enforces complete matched result records."""
    if set(choices) != {t.task_id for t in tasks}:
        raise ValueError("choices must cover exactly all tasks")
    observed = {(o.task_id, o.model_id): o.quality for o in outcomes}
    if len(observed) != len(outcomes):
        raise ValueError("duplicate outcomes")
    if any(not (math.isfinite(o.quality) and 0 <= o.quality <= 1) for o in outcomes):
        raise ValueError("invalid outcome quality")
    cost = 0.0
    quality = 0.0
    for t in tasks:
        allowed = {t.cheap.model_id: t.cheap.cost, t.strong.model_id: t.strong.cost}
        model = choices[t.task_id]
        if model not in allowed:
            raise ValueError("unknown choice")
        if (t.task_id, model) not in observed:
            raise ValueError("missing selected outcome")
        cost += allowed[model]
        quality += observed[(t.task_id, model)]
    return round(quality, 12), round(cost, 12)


def synthetic_demo(seed: int = 7) -> dict:
    """Create a deterministic event trace; no actual LLM calls or market behavior."""
    tasks = [
        Task("task-001", Arm("cheap", 1.0), Arm("strong", 2.0), 0.2, 0.9),
        Task("task-002", Arm("cheap", 1.0), Arm("strong", 2.0), 0.8, 0.9),
        Task("task-003", Arm("cheap", 1.0), Arm("strong", 2.0), 0.3, 0.7),
    ]
    outcomes = [
        ObservedOutcome("task-001", "cheap", 0.0), ObservedOutcome("task-001", "strong", 1.0),
        ObservedOutcome("task-002", "cheap", 1.0), ObservedOutcome("task-002", "strong", 1.0),
        ObservedOutcome("task-003", "cheap", 0.0), ObservedOutcome("task-003", "strong", 1.0),
    ]
    budget = 4.0
    decisions = choose_routes(tasks, budget)
    quality, cost = evaluate_selected(tasks, decisions, outcomes)
    baseline_choices = {t.task_id: t.cheap.model_id for t in tasks}
    baseline_quality, baseline_cost = evaluate_selected(tasks, baseline_choices, outcomes)
    events = []
    for i, t in enumerate(tasks):
        events.append({"seq": i, "type": "allocation", "time_step": i, "actor": "toy_allocator", "payload": {"task_id": t.task_id, "model_id": decisions[t.task_id]}})
    events.append({"seq": len(events), "type": "settlement", "time_step": len(events), "actor": "system", "payload": {"quality": quality, "cost": cost}})
    return {
        "schema_version": "0.1", "experiment_id": f"toy-seed-{seed}", "data_kind": "SYNTHETIC", "seed": seed,
        "config": {"budget": budget, "cost_unit": "synthetic_units", "mechanism": "greedy-forecast-upgrade"},
        "events": events,
        "metrics": {"quality": quality, "cost": cost, "cheapest_quality": baseline_quality, "cheapest_cost": baseline_cost},
        "provenance": {"source": "DEVIATION synthetic example", "code_revision": "bootstrap"},
        "warning": "NO real AI data, NO prediction market, NO adversarial results in this synthetic bootstrap example.",
    }
