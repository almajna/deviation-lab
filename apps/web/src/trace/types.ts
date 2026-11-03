// Contract v0.2 completed replay (docs/CONTRACTS.md, "Completed replay and visual handoff").
// The frontend is a read-only consumer: these types mirror src/deviation/contracts.py.

export type Visibility = 'PUBLIC' | 'POST_SETTLEMENT';
export type DataKind = 'SYNTHETIC' | 'RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS';

export interface PublicForecastPayload {
  task_id: string;
  forecast_kind: 'expected_preference_proxy';
  values: Record<string, number>;
}

export interface ReservationPayload {
  task_id: string;
  model_id: string | null;
  reserved_cost: number;
}

export interface SelectedCost {
  task_id: string;
  model_id: string | null;
  realized_cost: number;
}

export interface RealizedCostReportPayload {
  schema_version: string;
  phase: 'SETTLED';
  cost_unit: string;
  selected_costs: SelectedCost[];
  reservation_spend: number;
  realized_spend: number;
  positive_task_overruns: number;
  unused_reservations: number;
  net_overrun: number;
  realized_budget_excess: number;
  realized_budget_violated: boolean;
}

export interface LedgerTransferPayload {
  transfer_id: string;
  payer: string;
  payee: string;
  amount: number;
  reason: string;
}

export interface UtilityComponents {
  cash_delta: number;
  external_benefit: number;
  noncash_effort_cost: number;
  utility: number;
}

export type UtilitySummaryPayload = Record<string, UtilityComponents>;

interface EventBase<T extends string, V extends Visibility, P> {
  seq: number;
  time_step: number;
  actor: string;
  visibility: V;
  type: T;
  payload: P;
}

export type TraceEvent =
  | EventBase<'public_forecast', 'PUBLIC', PublicForecastPayload>
  | EventBase<'reservation', 'PUBLIC', ReservationPayload>
  | EventBase<'realized_cost_report', 'POST_SETTLEMENT', RealizedCostReportPayload>
  | EventBase<'ledger_transfer', 'POST_SETTLEMENT', LedgerTransferPayload>
  | EventBase<'utility_summary', 'POST_SETTLEMENT', UtilitySummaryPayload>;

export type EventType = TraceEvent['type'];

export interface CompletedTrace {
  schema_version: '0.2';
  experiment_id: string;
  seed: number;
  data_kind: DataKind;
  agent_origin: 'SYNTHETIC';
  quality_semantics: 'synthetic_fixture' | 'noisy_preference_proxy';
  phase: 'SETTLED';
  cost_unit: string;
  reservation_artifact_sha256: string;
  provenance: {
    source_manifest_sha256: string;
    split_manifest_sha256: string;
    code_revision: string;
  };
  events: TraceEvent[];
}

/** Trusted run configuration (validate_run_config). Optional companion to a trace. */
export interface RunConfig {
  schema_version: '0.2';
  cost_unit: string;
  reservation_budget: number;
  agent_accounts: string[];
  maker_account: string;
  fee_sink_account: string;
  initial_balances: Record<string, number>;
  exogenous_history_actors: string[];
}

export interface PublicTask {
  task_id: string;
  prompt: string;
  model_options: string[];
}

/** Ledger receipt (validate_ledger). Optional companion; requires run_config. */
export interface LedgerReceipt {
  schema_version: '0.2';
  unit: 'virtual_credit';
  initial_balances: Record<string, number>;
  final_balances: Record<string, number>;
  transfers: LedgerTransferPayload[];
  agent_utilities: Record<string, UtilityComponents>;
  maker_account: string;
  maker_initial_subsidy: number;
  maker_cash_pnl: number;
  maker_realized_loss: number;
}

/**
 * Display context that is not part of the public replay (e.g. the budget from the allocation receipt).
 * Always labelled in the UI as an annotation, never merged into events.
 */
export interface FixtureAnnotation {
  kind: 'FIXTURE_ANNOTATION';
  note: string;
  annotates_public_trace_sha256: string;
  source: { path: string; sha256: string; fields: string[] };
  reservation_budget?: number;
  tasks?: PublicTask[];
}

/** What the lab loads: a trace plus optional trusted companions, with a provenance label. */
export interface TraceBundle {
  id: string;
  label: string;
  /** Human-facing provenance class, shown at all times. */
  origin: 'SYNTHETIC_FIXTURE' | 'LOADED_FILE';
  trace: CompletedTrace;
  runConfig?: RunConfig;
  tasks?: PublicTask[];
  ledger?: LedgerReceipt;
  annotation?: FixtureAnnotation;
  /** The bundled public file and its pinned hash, when the trace ships with the app. */
  file?: { path: string; sha256: string; source: string };
}
