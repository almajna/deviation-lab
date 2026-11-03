// Client-side validation of a v0.2 completed trace and its optional public companions.
// Mirrors deviation.contracts (validate_trace, validate_run_config, validate_ledger) for every check
// a public bundle can support. Any figure the UI displays is either read from a validated event or
// recomputed from events and required to match; contradictory accounting is rejected, not displayed.

import type { CompletedTrace, LedgerReceipt, PublicTask, RunConfig, TraceBundle } from './types';

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
const RESERVED_ROLES = new Set(['allocator', 'system']);
const RUN_CONFIG_KEYS = 'schema_version cost_unit reservation_budget agent_accounts maker_account fee_sink_account initial_balances exogenous_history_actors';
const LEDGER_KEYS = 'schema_version unit initial_balances final_balances transfers agent_utilities maker_account maker_initial_subsidy maker_cash_pnl maker_realized_loss';
const BUNDLE_KEYS = new Set(['trace', 'run_config', 'decision_tasks', 'ledger']);

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

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

function textList(v: unknown, where: string, min = 0): string[] {
  if (!Array.isArray(v) || v.length < min) throw new TraceError(`${where}: expected a list of at least ${min}`);
  const out = v.map((x, i) => text(x, `${where}[${i}]`));
  if (new Set(out).size !== out.length) throw new TraceError(`${where}: duplicate entries`);
  return out;
}

function intMap(v: unknown, where: string, signed = false): Record<string, number> {
  if (!isObj(v)) throw new TraceError(`${where}: expected an object`);
  for (const [k, x] of Object.entries(v)) int(x, `${where}.${k}`, signed);
  return v as Record<string, number>;
}

/** Canonical form: object keys sorted recursively, so equality never depends on key order. */
export function canonical(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
  if (isObj(v)) return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canonical(v[k])}`).join(',')}}`;
  return JSON.stringify(v);
}
const same = (a: unknown, b: unknown) => canonical(a) === canonical(b);

/** Structural and arithmetic validation of the trace alone. */
export function validateTrace(raw: unknown): CompletedTrace {
  const t = exact(raw, TRACE_KEYS, 'trace');
  if (t.schema_version !== '0.2') throw new TraceError(`trace: unsupported schema_version ${String(t.schema_version)}`);
  text(t.experiment_id, 'trace.experiment_id');
  int(t.seed, 'trace.seed');
  if (t.phase !== 'SETTLED') throw new TraceError('trace: replay must be SETTLED');
  if (t.agent_origin !== 'SYNTHETIC') throw new TraceError('trace: agent_origin must be SYNTHETIC in v0.2');
  if (t.data_kind !== 'SYNTHETIC' && t.data_kind !== 'RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS') throw new TraceError('trace: unknown data_kind');
  const expectedQuality = t.data_kind === 'SYNTHETIC' ? 'synthetic_fixture' : 'noisy_preference_proxy';
  if (t.quality_semantics !== expectedQuality) throw new TraceError('trace: unsupported quality claim');
  if (!COST_UNITS.has(t.cost_unit as string)) throw new TraceError('trace: unknown cost_unit');
  text(t.reservation_artifact_sha256, 'trace.reservation_artifact_sha256');
  const p = exact(t.provenance, 'source_manifest_sha256 split_manifest_sha256 code_revision', 'trace.provenance');
  text(p.source_manifest_sha256, 'trace.provenance.source_manifest_sha256');
  text(p.split_manifest_sha256, 'trace.provenance.split_manifest_sha256');
  const rev = p.code_revision;
  if (!(t.data_kind === 'SYNTHETIC' && rev === 'SYNTHETIC_FIXTURE') && !(typeof rev === 'string' && /^[0-9a-f]{40}$/.test(rev))) {
    throw new TraceError('trace.provenance: replay requires a pinned 40-hex code revision');
  }
  if (!Array.isArray(t.events) || t.events.length === 0) throw new TraceError('trace: missing replay events');

  let lastTime = -1;
  let settled = false;
  let summarized = false;
  const reserved = new Map<string, { model_id: unknown; reserved_cost: number }>();
  const transferIds = new Set<string>();
  const netCash = new Map<string, number>();
  const roles = { feeSinks: new Set<string>(), feePayers: new Set<string>(), makers: new Set<string>() };

  t.events.forEach((rawEvent: unknown, i: number) => {
    const where = `event ${i}`;
    const e = exact(rawEvent, EVENT_KEYS, where);
    if (int(e.seq, `${where}.seq`) !== i) throw new TraceError(`${where}: seq must be contiguous from 0`);
    const ts = int(e.time_step, `${where}.time_step`);
    if (ts < lastTime) throw new TraceError(`${where}: time_step decreased`);
    lastTime = ts;
    const actor = text(e.actor, `${where}.actor`);
    const type = e.type as string;
    if (!(type in PAYLOAD_KEYS)) throw new TraceError(`${where}: unsupported event type "${type}"`);
    if (summarized) throw new TraceError(`${where}: ${type} after the utility summary; the summary must be final`);
    const visibility = POST_SETTLEMENT.has(type) ? 'POST_SETTLEMENT' : 'PUBLIC';
    if (e.visibility !== visibility) throw new TraceError(`${where}: ${type} must be ${visibility}`);
    if (POST_SETTLEMENT.has(type) && actor !== 'system') throw new TraceError(`${where}: ${type} must be recorded by "system", not "${actor}"`);
    const keys = PAYLOAD_KEYS[type];
    const pl = keys ? exact(e.payload, keys, `${where}.payload`) : e.payload;

    if (type === 'public_forecast') {
      const f = pl as Record<string, unknown>;
      if (settled) throw new TraceError(`${where}: forecast after settlement`);
      if (RESERVED_ROLES.has(actor)) throw new TraceError(`${where}: forecasts cannot come from "${actor}"`);
      if (f.forecast_kind !== 'expected_preference_proxy') throw new TraceError(`${where}: unsupported forecast_kind`);
      text(f.task_id, `${where}.task_id`);
      if (!isObj(f.values) || Object.keys(f.values).length < 2) throw new TraceError(`${where}: forecast needs per-model values`);
      for (const [m, v] of Object.entries(f.values)) {
        if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1) throw new TraceError(`${where}: forecast value for ${m} must be in [0, 1]`);
      }
    } else if (type === 'reservation') {
      const r = pl as Record<string, unknown>;
      if (settled) throw new TraceError(`${where}: reservation after settlement`);
      if (actor !== 'allocator') throw new TraceError(`${where}: reservations come from the allocator`);
      const task = text(r.task_id, `${where}.task_id`);
      if (reserved.has(task)) throw new TraceError(`${where}: duplicate reservation for ${task}`);
      const cost = int(r.reserved_cost, `${where}.reserved_cost`);
      if (r.model_id === null) {
        if (cost !== 0) throw new TraceError(`${where}: abstention must reserve zero`);
      } else {
        text(r.model_id, `${where}.model_id`);
        if (cost === 0) throw new TraceError(`${where}: a selected model must reserve a positive amount`);
      }
      reserved.set(task, { model_id: r.model_id, reserved_cost: cost });
    } else if (type === 'realized_cost_report') {
      if (settled) throw new TraceError(`${where}: duplicate settlement report`);
      if (reserved.size === 0) throw new TraceError(`${where}: settlement before any reservation`);
      checkReport(pl as Record<string, unknown>, reserved, t.cost_unit as string, where);
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
      if (RESERVED_ROLES.has(payer) || RESERVED_ROLES.has(payee)) throw new TraceError(`${where}: "${RESERVED_ROLES.has(payer) ? payer : payee}" is a reserved role, not an account`);
      const amount = int(x.amount, `${where}.amount`);
      if (amount === 0) throw new TraceError(`${where}: zero transfer`);
      const reason = text(x.reason, `${where}.reason`);
      if (reason === 'action_fee') { roles.feePayers.add(payer); roles.feeSinks.add(payee); }
      if (reason === 'settlement') roles.makers.add(payer);
      netCash.set(payer, (netCash.get(payer) ?? 0) - amount);
      netCash.set(payee, (netCash.get(payee) ?? 0) + amount);
    } else if (type === 'utility_summary') {
      if (!settled) throw new TraceError(`${where}: utilities before settlement`);
      if (!isObj(pl) || Object.keys(pl).length === 0) throw new TraceError(`${where}: utility summary must be a nonempty object`);
      for (const [agent, u] of Object.entries(pl)) {
        if (RESERVED_ROLES.has(agent)) throw new TraceError(`${where}: "${agent}" cannot hold a utility receipt`);
        const c = exact(u, 'cash_delta external_benefit noncash_effort_cost utility', `${where}.${agent}`);
        const cash = int(c.cash_delta, `${where}.${agent}.cash_delta`, true);
        const ext = int(c.external_benefit, `${where}.${agent}.external_benefit`);
        const effort = int(c.noncash_effort_cost, `${where}.${agent}.noncash_effort_cost`);
        if (int(c.utility, `${where}.${agent}.utility`, true) !== cash + ext - effort) {
          throw new TraceError(`${where}: ${agent} utility ≠ cash_delta + external_benefit − noncash_effort_cost`);
        }
        if (cash !== (netCash.get(agent) ?? 0)) throw new TraceError(`${where}: ${agent} cash_delta ${cash} disagrees with its replayed transfers (${netCash.get(agent) ?? 0})`);
      }
      for (const payer of roles.feePayers) {
        if (!(payer in (pl as object))) throw new TraceError(`${where}: ${payer} paid an action fee but has no utility receipt`);
      }
      for (const [account, net] of netCash) {
        if (net !== 0 && !(account in (pl as object)) && !roles.feeSinks.has(account) && !roles.makers.has(account)) {
          throw new TraceError(`${where}: ${account} moved credits but has no utility receipt and is neither fee sink nor maker`);
        }
      }
      summarized = true;
    }
  });
  if (!settled) throw new TraceError('trace: no realized_cost_report; replay is not settled');
  if (!summarized) throw new TraceError('trace: no utility_summary; payoffs cannot be reconciled');
  return raw as CompletedTrace;
}

function checkReport(r: Record<string, unknown>, reserved: Map<string, { model_id: unknown; reserved_cost: number }>, unit: string, where: string) {
  if (r.schema_version !== '0.2' || r.phase !== 'SETTLED') throw new TraceError(`${where}: report must be v0.2 SETTLED`);
  if (r.cost_unit !== unit) throw new TraceError(`${where}: report unit differs from trace unit`);
  if (!Array.isArray(r.selected_costs)) throw new TraceError(`${where}: selected_costs must be a list`);
  let reservation = 0, realized = 0, over = 0, unused = 0;
  const seen = new Set<string>();
  for (const [i, raw] of r.selected_costs.entries()) {
    const c = exact(raw, 'task_id model_id realized_cost', `${where}.selected_costs[${i}]`);
    const task = text(c.task_id, `${where}.selected_costs[${i}].task_id`);
    const res = reserved.get(task);
    if (!res || seen.has(task) || res.model_id !== c.model_id || res.model_id === null) {
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
  if (r.realized_budget_violated !== ((r.realized_budget_excess as number) > 0)) throw new TraceError(`${where}: violation flag disagrees with budget excess`);
  // A valid plan never reserves more than its budget, so the excess can be at most realized − reserved.
  if ((r.realized_budget_excess as number) > Math.max(realized - reservation, 0)) {
    throw new TraceError(`${where}: budget excess ${String(r.realized_budget_excess)} is impossible: it implies a budget below the ${reservation} already reserved`);
  }
}

const events = (t: CompletedTrace) => t.events;
const reportOf = (t: CompletedTrace) => events(t).find((e) => e.type === 'realized_cost_report');
const summaryOf = (t: CompletedTrace) => events(t).find((e) => e.type === 'utility_summary');
const transfersOf = (t: CompletedTrace) => events(t).flatMap((e) => (e.type === 'ledger_transfer' ? [e.payload] : []));

/** A budget from any source must agree with the reported excess and cover the reservations. */
export function checkBudget(budget: number, trace: CompletedTrace, where: string) {
  const r = reportOf(trace);
  if (!r || r.type !== 'realized_cost_report') return;
  if (r.payload.reservation_spend > budget) throw new TraceError(`${where}: reservations ${r.payload.reservation_spend} exceed the budget ${budget}`);
  if (Math.max(r.payload.realized_spend - budget, 0) !== r.payload.realized_budget_excess) {
    throw new TraceError(`${where}: budget ${budget} is inconsistent with the reported budget excess ${r.payload.realized_budget_excess}`);
  }
}

export function validateRunConfig(raw: unknown, trace: CompletedTrace): RunConfig {
  const c = exact(raw, RUN_CONFIG_KEYS, 'run_config');
  if (c.schema_version !== '0.2') throw new TraceError('run_config: unsupported schema_version');
  if (c.cost_unit !== trace.cost_unit) throw new TraceError('run_config: cost unit differs from trace');
  const budget = int(c.reservation_budget, 'run_config.reservation_budget');
  const agents = textList(c.agent_accounts, 'run_config.agent_accounts', 1);
  const maker = text(c.maker_account, 'run_config.maker_account');
  const sink = text(c.fee_sink_account, 'run_config.fee_sink_account');
  const exo = textList(c.exogenous_history_actors, 'run_config.exogenous_history_actors');
  const balances = intMap(c.initial_balances, 'run_config.initial_balances');
  const roles = [...agents, maker, sink];
  if (new Set(roles).size !== roles.length) throw new TraceError('run_config: agent, maker and fee-sink accounts must be distinct');
  for (const r of [...roles, ...exo]) if (RESERVED_ROLES.has(r)) throw new TraceError(`run_config: "${r}" is a reserved role`);
  if (exo.some((x) => roles.includes(x))) throw new TraceError('run_config: exogenous history actors cannot hold accounts');
  if (!same(Object.keys(balances).sort(), [...roles].sort())) throw new TraceError('run_config: initial_balances must cover exactly the agents, maker and fee sink');
  checkBudget(budget, trace, 'run_config');

  // Bind the trace to this configuration.
  const running = { ...balances };
  for (const e of events(trace)) {
    if (e.type === 'public_forecast' && !agents.includes(e.actor) && !exo.includes(e.actor)) {
      throw new TraceError(`run_config: forecast actor "${e.actor}" is neither an agent nor a declared history source`);
    }
    if (e.type !== 'ledger_transfer') continue;
    const { payer, payee, amount, reason, transfer_id } = e.payload;
    if (!(payer in running) || !(payee in running)) throw new TraceError(`run_config: transfer ${transfer_id} moves credits outside the configured accounts`);
    if (reason === 'action_fee' && (payee !== sink || !agents.includes(payer))) throw new TraceError(`run_config: fee ${transfer_id} must go from an agent to the fee sink`);
    running[payer] -= amount;
    running[payee] += amount;
    if (running[payer] < 0) throw new TraceError(`run_config: transfer ${transfer_id} overdraws ${payer} (unfunded payout)`);
  }
  const s = summaryOf(trace);
  if (s?.type === 'utility_summary' && !same(Object.keys(s.payload).sort(), [...agents].sort())) {
    throw new TraceError('run_config: the utility summary must cover exactly the configured agents');
  }
  return raw as RunConfig;
}

export function validateTasks(raw: unknown, trace: CompletedTrace): PublicTask[] {
  if (!Array.isArray(raw) || raw.length === 0) throw new TraceError('decision_tasks: expected a nonempty list');
  const ids = new Set<string>();
  const tasks = raw.map((x, i) => {
    const t = exact(x, 'task_id prompt model_options', `decision_tasks[${i}]`);
    const id = text(t.task_id, `decision_tasks[${i}].task_id`);
    if (ids.has(id)) throw new TraceError(`decision_tasks: duplicate task ${id}`);
    ids.add(id);
    text(t.prompt, `decision_tasks[${i}].prompt`);
    textList(t.model_options, `decision_tasks[${i}].model_options`, 2);
    return t as unknown as PublicTask;
  });
  const byId = new Map(tasks.map((t) => [t.task_id, t]));
  const reservedTasks = new Set<string>();
  for (const e of events(trace)) {
    if (e.type === 'public_forecast') {
      const t = byId.get(e.payload.task_id);
      if (!t) throw new TraceError(`decision_tasks: forecast for unknown task ${e.payload.task_id}`);
      if (!same(Object.keys(e.payload.values).sort(), [...t.model_options].sort())) throw new TraceError(`decision_tasks: forecast for ${t.task_id} does not cover exactly its model options`);
    }
    if (e.type === 'reservation') {
      const t = byId.get(e.payload.task_id);
      if (!t) throw new TraceError(`decision_tasks: reservation for unknown task ${e.payload.task_id}`);
      if (e.payload.model_id !== null && !t.model_options.includes(e.payload.model_id)) throw new TraceError(`decision_tasks: ${e.payload.model_id} is not an option for ${t.task_id}`);
      reservedTasks.add(t.task_id);
    }
  }
  if (!same([...reservedTasks].sort(), [...ids].sort())) throw new TraceError('decision_tasks: every task needs exactly one reservation or abstention');
  return tasks;
}

export function validateLedger(raw: unknown, trace: CompletedTrace, config: RunConfig | undefined): LedgerReceipt {
  if (!config) throw new TraceError('ledger: a ledger receipt requires the trusted run_config it settles against');
  const l = exact(raw, LEDGER_KEYS, 'ledger');
  if (l.schema_version !== '0.2' || l.unit !== 'virtual_credit') throw new TraceError('ledger: expected v0.2 virtual_credit');
  const initial = intMap(l.initial_balances, 'ledger.initial_balances');
  const final = intMap(l.final_balances, 'ledger.final_balances');
  if (!same(initial, config.initial_balances)) throw new TraceError('ledger: initial balances differ from the run configuration');
  if (l.maker_account !== config.maker_account) throw new TraceError('ledger: maker account differs from the run configuration');
  if (!Array.isArray(l.transfers) || !same(l.transfers, transfersOf(trace))) throw new TraceError('ledger: transfers differ from the replayed ledger events');
  const expected: Record<string, number> = { ...initial };
  for (const t of transfersOf(trace)) {
    expected[t.payer] -= t.amount;
    expected[t.payee] += t.amount;
  }
  if (!same(Object.keys(final).sort(), Object.keys(expected).sort())) throw new TraceError('ledger: final balances must cover exactly the configured accounts');
  for (const [k, v] of Object.entries(expected)) {
    if (final[k] !== v) throw new TraceError(`ledger: final balance for ${k} is ${final[k]}, transfers imply ${v}`);
  }
  const s = summaryOf(trace);
  if (!s || s.type !== 'utility_summary' || !same(l.agent_utilities, s.payload)) throw new TraceError('ledger: agent utilities differ from the replayed utility summary');
  const maker = config.maker_account;
  const subsidy = int(l.maker_initial_subsidy, 'ledger.maker_initial_subsidy');
  const pnl = int(l.maker_cash_pnl, 'ledger.maker_cash_pnl', true);
  const loss = int(l.maker_realized_loss, 'ledger.maker_realized_loss');
  if (subsidy > initial[maker] || pnl !== final[maker] - initial[maker] || loss !== Math.max(-pnl, 0)) throw new TraceError('ledger: maker subsidy, cash P&L or realized loss is inconsistent');
  return raw as LedgerReceipt;
}

/**
 * Parse a user-supplied JSON file: either a bare trace, or a public replay bundle with only
 * `trace`, `run_config`, `decision_tasks` and `ledger`. Anything else (for example a conformance
 * pack with private information sets) is rejected rather than silently ignored.
 */
export function bundleFromJson(raw: unknown, name: string): TraceBundle {
  const base = { id: `file:${name}`, label: name, origin: 'LOADED_FILE' as const };
  if (isObj(raw) && 'trace' in raw) {
    const extra = Object.keys(raw).filter((k) => !BUNDLE_KEYS.has(k));
    if (extra.length) {
      throw new TraceError(`the file contains fields outside a public replay bundle (${extra.join(', ')}); load a bare trace or a bundle of trace, run_config, decision_tasks and ledger`);
    }
    const trace = validateTrace(raw.trace);
    const runConfig = raw.run_config === undefined ? undefined : validateRunConfig(raw.run_config, trace);
    const tasks = raw.decision_tasks === undefined ? undefined : validateTasks(raw.decision_tasks, trace);
    const ledger = raw.ledger === undefined ? undefined : validateLedger(raw.ledger, trace, runConfig);
    return { ...base, trace, runConfig, tasks, ledger };
  }
  return { ...base, trace: validateTrace(raw) };
}
