// Deterministic replay: the state at cursor k is a pure fold over events[0..k].
//
// Knowledge rule: nothing in ReplayState depends on events after the cursor. Layout comes only from
// the known prefix plus trusted, pre-run companions (the public task catalog and run configuration).
// The UI renders exclusively from this state, so no future figure can reach the DOM.

import type { LedgerTransferPayload, RealizedCostReportPayload, TraceBundle, TraceEvent, UtilityComponents } from './types';

export interface TaskState {
  task_id: string;
  prompt?: string;
  models: string[];
  /** Latest public forecast per model, with the seq that set it. */
  forecast?: { values: Record<string, number>; seq: number; actor: string };
  /** Every known forecast for this task in order, so repeated forecasts can be drawn as a curve. */
  forecasts: Array<{ values: Record<string, number>; seq: number; actor: string }>;
  reservation?: { model_id: string | null; reserved_cost: number; seq: number };
  realized?: { realized_cost: number; seq: number };
}

export interface AccountState {
  id: string;
  /** Balance after declared initial funding, only when a trusted run configuration supplies it. */
  initial?: number;
  delta: number;
}

export interface ReplayState {
  /** -1 = before the first event; events.length = the closing summary frame. */
  cursor: number;
  /** Index of the last applied event (cursor clamped to the trace). */
  applied: number;
  settled: boolean;
  tasks: TaskState[];
  reservationSpend: number;
  budget?: number;
  /** Where the budget figure came from; it is never a field of the public trace. */
  budgetSource?: 'run_config' | 'annotation';
  report?: RealizedCostReportPayload & { seq: number };
  accounts: AccountState[];
  transfers: Array<LedgerTransferPayload & { seq: number }>;
  utilities?: { values: Record<string, UtilityComponents>; seq: number };
}

/** Index of the first POST_SETTLEMENT event: the knowledge boundary. */
export function settlementIndex(events: TraceEvent[]): number {
  const i = events.findIndex((e) => e.visibility === 'POST_SETTLEMENT');
  return i === -1 ? events.length : i;
}

/** The last cursor position: one frame past the final event, where the replay concludes. */
export const endOf = (bundle: TraceBundle) => bundle.trace.events.length;

export function replayAt(bundle: TraceBundle, cursor: number): ReplayState {
  const { events } = bundle.trace;
  const end = events.length;
  const c = Math.max(-1, Math.min(cursor, end));
  const k = Math.min(c, end - 1);
  const catalog = bundle.tasks ?? bundle.annotation?.tasks;
  const config = bundle.runConfig;

  const tasks: TaskState[] = [];
  const byId = new Map<string, TaskState>();
  const task = (id: string) => {
    let t = byId.get(id);
    if (!t) {
      const entry = catalog?.find((x) => x.task_id === id);
      t = { task_id: id, prompt: entry?.prompt, models: entry ? [...entry.model_options].sort() : [], forecasts: [] };
      byId.set(id, t);
      tasks.push(t);
    }
    return t;
  };
  for (const entry of catalog ?? []) task(entry.task_id);
  const addModel = (t: TaskState, m: string) => !t.models.includes(m) && (t.models.push(m), t.models.sort());

  const accounts: AccountState[] = [];
  const account = (id: string) => {
    let a = accounts.find((x) => x.id === id);
    if (!a) accounts.push((a = { id, initial: config?.initial_balances[id], delta: 0 }));
    return a;
  };
  for (const id of Object.keys(config?.initial_balances ?? {})) account(id);

  const state: ReplayState = {
    cursor: c,
    applied: k,
    settled: false,
    tasks,
    reservationSpend: 0,
    budget: config?.reservation_budget ?? bundle.annotation?.reservation_budget,
    budgetSource: config ? 'run_config' : bundle.annotation?.reservation_budget !== undefined ? 'annotation' : undefined,
    accounts,
    transfers: [],
  };

  for (let i = 0; i <= k; i++) {
    const e = events[i];
    switch (e.type) {
      case 'public_forecast': {
        const t = task(e.payload.task_id);
        Object.keys(e.payload.values).forEach((m) => addModel(t, m));
        t.forecast = { values: e.payload.values, seq: e.seq, actor: e.actor };
        t.forecasts.push(t.forecast);
        break;
      }
      case 'reservation': {
        const t = task(e.payload.task_id);
        if (e.payload.model_id) addModel(t, e.payload.model_id);
        t.reservation = { ...e.payload, seq: e.seq };
        state.reservationSpend += e.payload.reserved_cost;
        break;
      }
      case 'realized_cost_report':
        state.settled = true;
        state.report = { ...e.payload, seq: e.seq };
        for (const sc of e.payload.selected_costs) task(sc.task_id).realized = { realized_cost: sc.realized_cost, seq: e.seq };
        break;
      case 'ledger_transfer':
        state.transfers.push({ ...e.payload, seq: e.seq });
        account(e.payload.payer).delta -= e.payload.amount;
        account(e.payload.payee).delta += e.payload.amount;
        break;
      case 'utility_summary':
        state.utilities = { values: e.payload, seq: e.seq };
        break;
    }
  }
  return state;
}

/** Aggregate accounts into cohorts once there are too many to draw individually. */
export function cohortAccounts(accounts: AccountState[], limit = 8, roleOf: (id: string) => string = defaultRole) {
  if (accounts.length <= limit) return accounts.map((a) => ({ key: a.id, label: a.id, members: [a] }));
  const groups = new Map<string, AccountState[]>();
  for (const a of accounts) {
    const r = roleOf(a.id);
    groups.set(r, [...(groups.get(r) ?? []), a]);
  }
  return [...groups].map(([role, members]) => ({ key: `cohort:${role}`, label: `${role} ×${members.length}`, members }));
}

function defaultRole(id: string) {
  return id.replace(/[-_]?\d+$/, '') || id;
}
