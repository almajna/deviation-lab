// Client-side structural validation of a v0.2 completed trace.
// Mirrors the self-contained parts of deviation.contracts.validate_trace. Cross-receipt checks
// (plan, ledger, reservation artifact) need receipts the public trace does not carry; the UI
// instead recomputes every derived figure from the events and rejects internal inconsistency.

import type { CompletedTrace, PublicTask, RunConfig, TraceBundle } from './types';

export class TraceError extends Error {}

const TRACE_KEYS = 'schema_version experiment_id seed data_kind agent_origin quality_semantics phase cost_unit reservation_artifact_sha256 provenance events';
const EVENT_KEYS = 'seq time_step actor visibility type payload';
const PAYLOAD_KEYS: Record<string, string | null> = {
  public_forecast: 'task_id forecast_kind values',
  reservation: 'task_id model_id reserved_cost',
  realized_cost_report:
    'schema_version phase cost_unit selected_costs reservation_spend realized_spend positive_task_overruns unused_reservations net_overrun realized_budget_excess realized_budget_violated',
  ledger_transfer: 'transfer_id payer payee amount reason',
  utility_summary: null,
};
const POST_SETTLEMENT = new Set(['realized_cost_report', 'ledger_transfer', 'utility_summary']);
const COST_UNITS = new Set(['nano_reported_usd', 'nano_synthetic_units']);
const RUN_CONFIG_KEYS = 'schema_version cost_unit reservation_budget agent_accounts maker_account fee_sink_account initial_balances exogenous_history_actors';

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

function exact(v: unknown, keys: string, where: string): Record<string, unknown> {
  if (!isObj(v)) throw new TraceError(`${where}: expected an object`);
  const want = keys.split(' ').sort();
  const got = Object.keys(v).sort();
  const extra = got.filter((k) => !want.includes(k));
  const missing = want.filter((k) => !got.includes(k));
  if (extra.length || missing.length) {
    const parts = [];
    if (missing.length) parts.push(`missing ${missing.join(', ')}`);
    if (extra.length) parts.push(`unknown ${extra.join(', ')}`);
    throw new TraceError(`${where}: ${parts.join('; ')}`);
  }
  return v;
}

function int(v: unknown, where: string, signed = false): number {
  if (typeof v !== 'number' || !Number.isSafeInteger(v) || (!signed && v < 0)) {
    throw new TraceError(`${where}: expected ${signed ? 'an' : 'a nonnegative'} integer`);
  }
  return v;
}

function text(v: unknown, where: string): string {
  if (typeof v !== 'string' || !v.trim()) throw new TraceError(`${where}: expected nonempty text`);
  return v;
}

export function validateTrace(raw: unknown): CompletedTrace {
  const t = exact(raw, TRACE_KEYS, 'trace');
  if (t.schema_version !== '0.2') throw new TraceError(`trace: unsupported schema_version ${String(t.schema_version)}`);
  text(t.experiment_id, 'trace.experiment_id');
  int(t.seed, 'trace.seed');
  if (t.phase !== 'SETTLED') throw new TraceError('trace: replay must be SETTLED');
  if (t.agent_origin !== 'SYNTHETIC') throw new TraceError('trace: agent_origin must be SYNTHETIC in v0.2');
  if (t.data_kind !== 'SYNTHETIC' && t.data_kind !== 'RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS') {
    throw new TraceError('trace: unknown data_kind');
  }
  const expectedQuality = t.data_kind === 'SYNTHETIC' ? 'synthetic_fixture' : 'noisy_preference_proxy';
  if (t.quality_semantics !== expectedQuality) throw new TraceError('trace: unsupported quality claim');
  if (!COST_UNITS.has(t.cost_unit as string)) throw new TraceError('trace: unknown cost_unit');
  text(t.reservation_artifact_sha256, 'trace.reservation_artifact_sha256');
  const p = exact(t.provenance, 'source_manifest_sha256 split_manifest_sha256 code_revision', 'trace.provenance');
  const rev = p.code_revision;
  if (!(t.data_kind === 'SYNTHETIC' && rev === 'SYNTHETIC_FIXTURE') && !(typeof rev === 'string' && /^[0-9a-f]{40}$/.test(rev))) {
    throw new TraceError('trace.provenance: replay requires a pinned 40-hex code revision');
  }
  if (!Array.isArray(t.events) || t.events.length === 0) throw new TraceError('trace: missing replay events');

  let lastTime = -1;
  let settled = false;
  let report: Record<string, unknown> | null = null;
  const reserved = new Map<string, { model_id: unknown; reserved_cost: number }>();
  const transferIds = new Set<string>();
  const netCash = new Map<string, number>();

  t.events.forEach((rawEvent: unknown, i: number) => {
    const where = `event ${i}`;
    const e = exact(rawEvent, EVENT_KEYS, where);
    if (int(e.seq, `${where}.seq`) !== i) throw new TraceError(`${where}: seq must be contiguous from 0`);
    const ts = int(e.time_step, `${where}.time_step`);
    if (ts < lastTime) throw new TraceError(`${where}: time_step decreased`);
    lastTime = ts;
    text(e.actor, `${where}.actor`);
    const type = e.type as string;
    if (!(type in PAYLOAD_KEYS)) throw new TraceError(`${where}: unsupported event type "${type}"`);
    const visibility = POST_SETTLEMENT.has(type) ? 'POST_SETTLEMENT' : 'PUBLIC';
    if (e.visibility !== visibility) throw new TraceError(`${where}: ${type} must be ${visibility}`);
    const keys = PAYLOAD_KEYS[type];
    const pl = keys ? exact(e.payload, keys, `${where}.payload`) : e.payload;

    if (type === 'public_forecast') {
      const f = pl as Record<string, unknown>;
      if (settled) throw new TraceError(`${where}: forecast after settlement`);
      if (f.forecast_kind !== 'expected_preference_proxy') throw new TraceError(`${where}: unsupported forecast_kind`);
      text(f.task_id, `${where}.task_id`);
      if (!isObj(f.values) || Object.keys(f.values).length < 2) throw new TraceError(`${where}: forecast needs per-model values`);
      for (const [m, v] of Object.entries(f.values)) {
        if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1) {
          throw new TraceError(`${where}: forecast value for ${m} must be in [0, 1]`);
        }
      }
    } else if (type === 'reservation') {
      const r = pl as Record<string, unknown>;
      if (settled) throw new TraceError(`${where}: reservation after settlement`);
      if (e.actor !== 'allocator') throw new TraceError(`${where}: reservations come from the allocator`);
      const task = text(r.task_id, `${where}.task_id`);
      if (reserved.has(task)) throw new TraceError(`${where}: duplicate reservation for ${task}`);
      const cost = int(r.reserved_cost, `${where}.reserved_cost`);
      if (r.model_id === null) {
        if (cost !== 0) throw new TraceError(`${where}: abstention must reserve zero`);
      } else {
        text(r.model_id, `${where}.model_id`);
      }
      reserved.set(task, { model_id: r.model_id, reserved_cost: cost });
    } else if (type === 'realized_cost_report') {
      if (settled) throw new TraceError(`${where}: duplicate settlement report`);
      report = pl as Record<string, unknown>;
      checkReport(report, reserved, t.cost_unit as string, where);
      settled = true;
    } else if (type === 'ledger_transfer') {
      const x = pl as Record<string, unknown>;
      if (!settled) throw new TraceError(`${where}: transfer before settlement`);
      const id = text(x.transfer_id, `${where}.transfer_id`);
      if (transferIds.has(id)) throw new TraceError(`${where}: duplicate transfer ${id}`);
      transferIds.add(id);
      const payer = text(x.payer, `${where}.payer`);
      const payee = text(x.payee, `${where}.payee`);
      if (payer === payee) throw new TraceError(`${where}: self-transfer`);
      const amount = int(x.amount, `${where}.amount`);
      if (amount === 0) throw new TraceError(`${where}: zero transfer`);
      text(x.reason, `${where}.reason`);
      netCash.set(payer, (netCash.get(payer) ?? 0) - amount);
      netCash.set(payee, (netCash.get(payee) ?? 0) + amount);
    } else if (type === 'utility_summary') {
      if (!settled) throw new TraceError(`${where}: utilities before settlement`);
      if (!isObj(pl) || Object.keys(pl).length === 0) throw new TraceError(`${where}: utility summary must be a nonempty object`);
      for (const [agent, u] of Object.entries(pl)) {
        const c = exact(u, 'cash_delta external_benefit noncash_effort_cost utility', `${where}.${agent}`);
        const cash = int(c.cash_delta, `${where}.${agent}.cash_delta`, true);
        const ext = int(c.external_benefit, `${where}.${agent}.external_benefit`);
        const effort = int(c.noncash_effort_cost, `${where}.${agent}.noncash_effort_cost`);
        if (int(c.utility, `${where}.${agent}.utility`, true) !== cash + ext - effort) {
          throw new TraceError(`${where}: ${agent} utility ≠ cash_delta + external_benefit − noncash_effort_cost`);
        }
        if (cash !== (netCash.get(agent) ?? 0)) {
          throw new TraceError(`${where}: ${agent} cash_delta disagrees with the replayed transfers`);
        }
      }
    }
  });
  if (!settled) throw new TraceError('trace: no realized_cost_report; replay is not settled');
  return raw as CompletedTrace;
}

function checkReport(
  r: Record<string, unknown>,
  reserved: Map<string, { model_id: unknown; reserved_cost: number }>,
  unit: string,
  where: string,
) {
  if (r.schema_version !== '0.2' || r.phase !== 'SETTLED') throw new TraceError(`${where}: report must be v0.2 SETTLED`);
  if (r.cost_unit !== unit) throw new TraceError(`${where}: report unit differs from trace unit`);
  if (!Array.isArray(r.selected_costs)) throw new TraceError(`${where}: selected_costs must be a list`);
  let reservation = 0, realized = 0, over = 0, unused = 0;
  const seen = new Set<string>();
  for (const [i, raw] of r.selected_costs.entries()) {
    const c = exact(raw, 'task_id model_id realized_cost', `${where}.selected_costs[${i}]`);
    const task = text(c.task_id, `${where}.selected_costs[${i}].task_id`);
    const res = reserved.get(task);
    if (!res || seen.has(task) || res.model_id !== c.model_id) {
      throw new TraceError(`${where}: selected cost for ${task} does not match a single prior reservation`);
    }
    seen.add(task);
    const cost = int(c.realized_cost, `${where}.selected_costs[${i}].realized_cost`);
    reservation += res.reserved_cost;
    realized += cost;
    over += Math.max(cost - res.reserved_cost, 0);
    unused += Math.max(res.reserved_cost - cost, 0);
  }
  for (const [task, res] of reserved) {
    if (!seen.has(task) && res.model_id !== null) throw new TraceError(`${where}: no realized cost for reserved task ${task}`);
  }
  const expect: Array<[string, number]> = [
    ['reservation_spend', reservation],
    ['realized_spend', realized],
    ['positive_task_overruns', over],
    ['unused_reservations', unused],
    ['net_overrun', realized - reservation],
  ];
  for (const [k, v] of expect) {
    if (r[k] !== v) throw new TraceError(`${where}: ${k} is ${String(r[k])}, events imply ${v}`);
  }
  int(r.realized_budget_excess, `${where}.realized_budget_excess`);
  if (typeof r.realized_budget_violated !== 'boolean') throw new TraceError(`${where}: realized_budget_violated must be boolean`);
  if (r.realized_budget_violated !== ((r.realized_budget_excess as number) > 0)) {
    throw new TraceError(`${where}: violation flag disagrees with budget excess`);
  }
}

export function validateRunConfig(raw: unknown, trace: CompletedTrace): RunConfig {
  const c = exact(raw, RUN_CONFIG_KEYS, 'run_config');
  if (c.schema_version !== '0.2') throw new TraceError('run_config: unsupported schema_version');
  if (c.cost_unit !== trace.cost_unit) throw new TraceError('run_config: cost unit differs from trace');
  int(c.reservation_budget, 'run_config.reservation_budget');
  if (!isObj(c.initial_balances)) throw new TraceError('run_config.initial_balances: expected an object');
  for (const [k, v] of Object.entries(c.initial_balances)) int(v, `run_config.initial_balances.${k}`);
  const cfg = raw as RunConfig;
  const report = trace.events.find((e) => e.type === 'realized_cost_report');
  if (report && report.type === 'realized_cost_report') {
    const excess = Math.max(report.payload.realized_spend - cfg.reservation_budget, 0);
    if (excess !== report.payload.realized_budget_excess) {
      throw new TraceError('run_config: reservation_budget is inconsistent with the reported budget excess');
    }
  }
  return cfg;
}

/** Parse a user-supplied JSON file: either a bare trace or a conformance pack containing one. */
export function bundleFromJson(raw: unknown, name: string): TraceBundle {
  if (isObj(raw) && 'trace' in raw && 'events' in (isObj(raw.trace) ? raw.trace : {})) {
    const trace = validateTrace(raw.trace);
    return {
      id: `file:${name}`,
      label: name,
      origin: 'LOADED_FILE',
      trace,
      runConfig: raw.run_config === undefined ? undefined : validateRunConfig(raw.run_config, trace),
      tasks: Array.isArray(raw.decision_tasks) ? (raw.decision_tasks as PublicTask[]) : undefined,
    };
  }
  return { id: `file:${name}`, label: name, origin: 'LOADED_FILE', trace: validateTrace(raw) };
}
