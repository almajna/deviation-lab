import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CONFORMANCE_FIXTURE } from '../data/fixtures';
import { narrate, narrateOpening } from './narrate';
import { cohortAccounts, replayAt, settlementIndex } from './replay';
import type { CompletedTrace, TraceBundle } from './types';
import { bundleFromJson, TraceError, validateRunConfig, validateTrace } from './validate';

// The source pack is read here, in Node, only to check the public projection. It is never bundled.
const FIXTURE_PATH = new URL('../../../../tests/fixtures/contracts_v0_2.json', import.meta.url);
const PUBLIC_PATH = new URL('../../fixtures/gate-a.synthetic.json', import.meta.url);
const ANNOTATION_PATH = new URL('../../fixtures/gate-a.annotations.json', import.meta.url);
const MANIFEST = JSON.parse(readFileSync(new URL('../../fixtures/manifest.json', import.meta.url), 'utf8'));
const raw = JSON.parse(readFileSync(FIXTURE_PATH, 'utf8'));
const sha = (u: URL) => createHash('sha256').update(readFileSync(u)).digest('hex');
const clone = (): CompletedTrace => structuredClone(raw.trace);

describe('fixture provenance', () => {
  it('bundles the pinned public projection, identical to the approved pack trace', () => {
    expect(sha(FIXTURE_PATH)).toBe(MANIFEST.approved_files_sha256['tests/fixtures/contracts_v0_2.json']);
    expect(sha(PUBLIC_PATH)).toBe(MANIFEST.public_trace_sha256);
    expect(JSON.parse(readFileSync(PUBLIC_PATH, 'utf8'))).toEqual(raw.trace);
    expect(CONFORMANCE_FIXTURE.trace).toEqual(raw.trace);
    expect(CONFORMANCE_FIXTURE.trace.data_kind).toBe('SYNTHETIC');
    expect(CONFORMANCE_FIXTURE.trace.provenance.code_revision).toBe('SYNTHETIC_FIXTURE');
  });

  it('annotation copies only public receipts, exactly, and no private or balance fields', () => {
    const a = JSON.parse(readFileSync(ANNOTATION_PATH, 'utf8'));
    expect(a.kind).toBe('FIXTURE_ANNOTATION');
    expect(a.source.sha256).toBe(sha(FIXTURE_PATH));
    expect(a.annotates_public_trace_sha256).toBe(MANIFEST.public_trace_sha256);
    expect(a.reservation_budget).toBe(raw.allocation_plan.reservation_budget);
    expect(a.tasks).toEqual(raw.decision_tasks);
    const text = JSON.stringify(a) + JSON.stringify(CONFORMANCE_FIXTURE);
    for (const k of ['private_signal', 'owner_agent_id', 'available_credits', 'initial_balances', 'training_rows', '0.7']) {
      expect(text, k).not.toContain(k);
    }
  });
});

describe('validateTrace', () => {
  it('accepts the v0.2 synthetic fixture', () => {
    expect(() => validateTrace(clone())).not.toThrow();
    expect(() => validateRunConfig(raw.run_config, raw.trace)).not.toThrow();
  });

  const reject = (mutate: (t: any) => void, match: RegExp) => {
    const t = clone();
    mutate(t);
    expect(() => validateTrace(t)).toThrowError(match);
  };

  it('rejects unknown and nested hidden fields', () => {
    reject((t) => (t.answer_labels = []), /unknown answer_labels/);
    reject((t) => (t.events[0].payload.ground_truth = 1), /unknown ground_truth/);
    reject((t) => (t.events[1].private_signal = {}), /unknown private_signal/);
  });
  it('rejects non-contiguous sequence and time travel', () => {
    reject((t) => (t.events[2].seq = 5), /contiguous/);
    reject((t) => (t.events[3].time_step = 0), /time_step decreased/);
  });
  it('rejects wrong visibility (post-settlement data marked public)', () => {
    reject((t) => (t.events[3].visibility = 'PUBLIC'), /must be POST_SETTLEMENT/);
    reject((t) => (t.events[0].visibility = 'POST_SETTLEMENT'), /must be PUBLIC/);
  });
  it('rejects events outside the approved v0.2 vocabulary', () => {
    reject((t) => (t.events[0].type = 'market_price'), /unsupported event type/);
  });
  it('rejects transfers before settlement and reservations after it', () => {
    reject((t) => ([t.events[3], t.events[4]] = [t.events[4], t.events[3]]), /seq|before settlement/);
    reject((t) => t.events.push({ ...t.events[1], seq: 7, time_step: 2 }), /after settlement/);
  });
  it('recomputes the realized report from events instead of trusting it', () => {
    reject((t) => (t.events[3].payload.realized_spend = 600), /realized_spend is 600, events imply 900/);
    reject((t) => (t.events[3].payload.realized_budget_violated = false), /violation flag/);
  });
  it('rejects utilities that double count or disagree with transfers', () => {
    reject((t) => (t.events[6].payload['agent-1'].utility = 7), /utility ≠/);
    reject((t) => (t.events[5].payload.amount = 9), /cash_delta disagrees/);
  });
  it('rejects unpinned code revisions for recorded data', () => {
    reject((t) => { t.data_kind = 'RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS'; t.quality_semantics = 'noisy_preference_proxy'; }, /pinned 40-hex/);
  });
  it('rejects a run configuration whose budget hides the reported excess', () => {
    const cfg = { ...raw.run_config, reservation_budget: 900 };
    expect(() => validateRunConfig(cfg, raw.trace)).toThrowError(/inconsistent/);
  });
  it('loads a conformance pack or a bare trace from a file', () => {
    expect(bundleFromJson(raw, 'pack.json').runConfig?.reservation_budget).toBe(600);
    expect(bundleFromJson(raw.trace, 'trace.json').runConfig).toBeUndefined();
    expect(() => bundleFromJson({ nope: 1 }, 'x.json')).toThrow(TraceError);
  });
});

describe('replay', () => {
  const b = CONFORMANCE_FIXTURE;

  it('starts empty before the first event', () => {
    const s = replayAt(b, -1);
    expect(s.reservationSpend).toBe(0);
    expect(s.settled).toBe(false);
    expect(s.tasks.every((t) => !t.forecast && !t.reservation && !t.realized)).toBe(true);
  });

  it('matches the documented contract figures at settlement', () => {
    const s = replayAt(b, 6);
    expect(s.reservationSpend).toBe(500);
    expect(s.budget).toBe(600);
    expect(s.budgetSource).toBe('annotation');
    expect(s.report).toMatchObject({ realized_spend: 900, positive_task_overruns: 500, unused_reservations: 100, net_overrun: 400, realized_budget_excess: 300 });
    // Balances are not public: only deltas are replayed, and they match the ledger receipt.
    expect(s.accounts.every((a) => a.initial === undefined)).toBe(true);
    const delta = Object.fromEntries(s.accounts.map((a) => [a.id, a.delta]));
    for (const [id, fin] of Object.entries(raw.ledger.final_balances as Record<string, number>)) {
      expect(delta[id]).toBe(fin - raw.ledger.initial_balances[id]);
    }
    expect(s.utilities?.values['agent-1'].utility).toBe(6);
  });

  it('never reveals post-settlement data before the boundary', () => {
    const k = settlementIndex(b.trace.events);
    expect(k).toBe(3);
    const s = replayAt(b, k - 1);
    expect(s.report).toBeUndefined();
    expect(s.tasks.some((t) => t.realized)).toBe(false);
    expect(s.accounts.every((a) => a.delta === 0)).toBe(true);
  });

  it('is deterministic and seek-order independent', () => {
    const forward = [-1, 0, 1, 2, 3, 4, 5, 6].map((k) => JSON.stringify(replayAt(b, k)));
    const backward = [6, 5, 4, 3, 2, 1, 0, -1].map((k) => JSON.stringify(replayAt(b, k))).reverse();
    expect(forward).toEqual(backward);
    expect(JSON.stringify(replayAt(b, 99))).toBe(forward[7]);
  });

  it('aggregates large account sets into role cohorts', () => {
    const accounts = Array.from({ length: 2000 }, (_, i) => ({ id: `agent-${i}`, delta: i % 3 }));
    const g = cohortAccounts([...accounts, { id: 'maker', delta: -5 }]);
    expect(g.map((x) => x.label)).toEqual(['agent ×2000', 'maker ×1']);
  });

  it('replays a 3,000-event synthetic stress trace quickly', () => {
    const big = stressBundle(3000);
    const t0 = performance.now();
    const s = replayAt(big, 2999);
    expect(s.transfers.length).toBe(3000 - 3);
    expect(performance.now() - t0).toBeLessThan(250);
  });
});

describe('narration', () => {
  const b = CONFORMANCE_FIXTURE;
  const text = (k: number) => {
    const s = replayAt(b, k);
    const n = k < 0 ? narrateOpening(b, s) : narrate(b.trace.events[k], s);
    return n.headline.map((x) => (typeof x === 'string' ? x : String(x.n))).join('') + ' ' + n.detail;
  };
  it('never calls a forecast a probability of success', () => {
    for (let k = -1; k < 7; k++) expect(text(k)).not.toMatch(/probability of (coding )?success|chance of success/i);
    expect(text(0)).toMatch(/not a probability/);
  });
  it('states the overrun honestly and separates it from allocation error', () => {
    expect(text(3)).toMatch(/900.*600.*300 over/);
    expect(text(3)).toMatch(/not an allocation error/);
  });
  it('reports the forecast/choice mismatch without inventing a reason', () => {
    expect(text(1)).toMatch(/does not record why/);
  });
});

function stressBundle(n: number): TraceBundle {
  const events: any[] = [
    { seq: 0, time_step: 0, actor: 'allocator', visibility: 'PUBLIC', type: 'reservation', payload: { task_id: 'x', model_id: 'a', reserved_cost: 1 } },
    { seq: 1, time_step: 1, actor: 'system', visibility: 'POST_SETTLEMENT', type: 'realized_cost_report', payload: { schema_version: '0.2', phase: 'SETTLED', cost_unit: 'nano_synthetic_units', selected_costs: [{ task_id: 'x', model_id: 'a', realized_cost: 1 }], reservation_spend: 1, realized_spend: 1, positive_task_overruns: 0, unused_reservations: 0, net_overrun: 0, realized_budget_excess: 0, realized_budget_violated: false } },
  ];
  for (let i = 2; i < n - 1; i++) {
    events.push({ seq: i, time_step: 1, actor: 'system', visibility: 'POST_SETTLEMENT', type: 'ledger_transfer', payload: { transfer_id: `t${i}`, payer: 'maker', payee: `agent-${i % 500}`, amount: 1, reason: 'settlement' } });
  }
  events.push({ seq: n - 1, time_step: 1, actor: 'system', visibility: 'POST_SETTLEMENT', type: 'utility_summary', payload: {} });
  return { id: 'stress', label: 'stress', origin: 'LOADED_FILE', trace: { ...clone(), events } };
}

