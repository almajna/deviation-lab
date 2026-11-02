# Shared interface and event-log contracts (v0.1 DRAFT)

Do not silently modify schemas. Proposed change requires integrator review, version bump, migration fixture, and CI updates. Semantic boundaries matter more than any specific serialization library.

## Task-outcome record
```json
{
  "schema_version": "0.1",
  "task_id": "example-001",
  "features": {"topic": "coding"},
  "model_id": "example-model-A",
  "quality": 1.0,
  "cost": 0.002,
  "cost_unit": "estimated_usd",
  "split": "test",
  "source": "SYNTHETIC_FIXTURE"
}
```
Repeated task_id with different model_id represents potential paired counterfactual outcomes. `quality` and `cost` must originate from audited sources or be explicitly marked synthetic. Task features must represent pre-decision information.

## Agent decision information
```json
{
  "agent_id": "reporter-3",
  "task_id": "example-001",
  "model_options": ["example-model-A", "example-model-B"],
  "public_features": {"topic": "coding"},
  "private_signal": {"forecast_success_B": 0.71},
  "market_history_before_action": [],
  "available_credits": 100.0
}
```
Prohibited in a decision information object: target outcome, current-task correctness, future market records or post-settlement payoff. An explicit verifier must assert this boundary.

## Versioned replay log
A simulation output should be one JSON object with this envelope:
```json
{
  "schema_version": "0.1",
  "experiment_id": "toy-seed-7",
  "data_kind": "SYNTHETIC",
  "seed": 7,
  "config": {"budget": 3.0, "cost_unit": "synthetic_units"},
  "events": [
    {"seq": 0, "type": "agent_signal", "time_step": 0, "actor": "forecaster-1", "payload": {"arm": "B", "p": 0.6}},
    {"seq": 1, "type": "allocation", "time_step": 1, "actor": "allocator", "payload": {"task_id": "toy-1", "model_id": "B", "cost": 2.0}},
    {"seq": 2, "type": "settlement", "time_step": 2, "actor": "system", "payload": {"quality": 1.0}}
  ],
  "metrics": {"quality": 1.0, "cost": 2.0},
  "provenance": {"source": "local fixture", "code_revision": "dev"}
}
```
`seq` monotone; events never mutated after emission; every UI number must be derivable from events or computed post-run metrics with provenance. `data_kind` is `SYNTHETIC`, `RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS`, or `OBSERVED_LLM_AGENT_INTERACTIONS`, and the last is used only with separately recorded real interaction evidence.

## Mechanism conceptual API
- Accepts `PublicState`, sealed per-agent information and validated actions; no outcome oracle during play.
- `allocate(actions, budget) -> decisions`: deterministic under seed.
- `settle(decisions, observed_outcomes) -> ledger`: auditable accounting.
- `trace() -> events`: ordered replay events with public/private markings. Public replay redacts actual private signals until explicitly disclosed after experiment.

## Stable error conditions
Invalid cost units, incomplete paired outcomes, budget overrun, missing schema version, unknown event type, negative credits (when prohibited), or forbidden future-label access should fail explicitly, not silently fall back.

## Initial scaffold
`src/deviation/core.py` contains a minimal synthetic example following the envelope shape. This is a starter reference and will need contract expansion as the real engine is developed.
