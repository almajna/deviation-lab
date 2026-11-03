// Deterministic replay: the state at cursor k is a pure fold over events[0..k].
// No timers, randomness or rendering state participate, so seeking is exact.

import type { LedgerTransferPayload, RealizedCostReportPayload, TraceBundle, TraceEvent, UtilityComponents } from './types';

export interface TaskState {
  task_id: string;
  prompt?: string;
  models: string[];
  /** Latest public forecast per model, with the seq that set it. */
  forecast?: { values: Record<string, number>; seq: number; actor: string };
  reservation?: { model_id: string | null; reserved_cost: number; seq: number };
  realized?: { realized_cost: number; seq: number };
}

export interface AccountState {
  id: string;
  /** Balance after declared initial funding, if a run configuration supplies it. */
  initial?: number;
  delta: number;
}

export interface ReplayState {
  /** -1 = before the first event. */
  cursor: number;
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

/** Stable task and account ordering derived from the whole trace (layout never reflows on seek). */
export function layoutOf(bundle: TraceBundle) {
  const taskIds: string[] = [];
  const models = new Map<string, Set<string>>();
  const accounts: string[] = [];
  const addTask = (id: string) => {
    if (!models.has(id)) {
      taskIds.push(id);
      models.set(id, new Set());
    }
    return models.get(id)!;
  };
  for (const t of bundle.tasks ?? bundle.annotation?.tasks ?? []) t.model_options.forEach((m) => addTask(t.task_id).add(m));
  const addAccount = (a: string) => !accounts.includes(a) && accounts.push(a);
  for (const a of Object.keys(bundle.runConfig?.initial_balances ?? {})) addAccount(a);
  for (const e of bundle.trace.events) {
    if (e.type === 'public_forecast') Object.keys(e.payload.values).forEach((m) => addTask(e.payload.task_id).add(m));
    if (e.type === 'reservation') {
      const s = addTask(e.payload.task_id);
      if (e.payload.model_id) s.add(e.payload.model_id);
    }
    if (e.type === 'ledger_transfer') {
      addAccount(e.payload.payer);
      addAccount(e.payload.payee);
    }
  }
  return {
    tasks: taskIds.map((id) => ({
      task_id: id,
      prompt: (bundle.tasks ?? bundle.annotation?.tasks)?.find((t) => t.task_id === id)?.prompt,
      models: [...models.get(id)!].sort(),
    })),
    accounts,
  };
}

export function replayAt(bundle: TraceBundle, cursor: number): ReplayState {
  const { events } = bundle.trace;
  const k = Math.max(-1, Math.min(cursor, events.length - 1));
  const layout = layoutOf(bundle);
  const tasks: TaskState[] = layout.tasks.map((t) => ({ ...t }));
  const byId = new Map(tasks.map((t) => [t.task_id, t]));
  const init = bundle.runConfig?.initial_balances ?? {};
  const accounts: AccountState[] = layout.accounts.map((id) => ({ id, initial: init[id], delta: 0 }));
  const accountById = new Map(accounts.map((a) => [a.id, a]));
  const state: ReplayState = {
    cursor: k,
    settled: false,
    tasks,
    reservationSpend: 0,
    budget: bundle.runConfig?.reservation_budget ?? bundle.annotation?.reservation_budget,
    budgetSource: bundle.runConfig ? 'run_config' : bundle.annotation?.reservation_budget !== undefined ? 'annotation' : undefined,
    accounts,
    transfers: [],
  };

  for (let i = 0; i <= k; i++) {
    const e = events[i];
    switch (e.type) {
      case 'public_forecast':
        byId.get(e.payload.task_id)!.forecast = { values: e.payload.values, seq: e.seq, actor: e.actor };
        break;
      case 'reservation':
        byId.get(e.payload.task_id)!.reservation = { ...e.payload, seq: e.seq };
        state.reservationSpend += e.payload.reserved_cost;
        break;
      case 'realized_cost_report':
        state.settled = true;
        state.report = { ...e.payload, seq: e.seq };
        for (const c of e.payload.selected_costs) {
          const t = byId.get(c.task_id);
          if (t) t.realized = { realized_cost: c.realized_cost, seq: e.seq };
        }
        break;
      case 'ledger_transfer':
        state.transfers.push({ ...e.payload, seq: e.seq });
        accountById.get(e.payload.payer)!.delta -= e.payload.amount;
        accountById.get(e.payload.payee)!.delta += e.payload.amount;
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
