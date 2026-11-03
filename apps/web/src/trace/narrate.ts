// Plain-language narration derived only from event payloads and the replay state.
// Narration states what the record shows; it never infers motives the trace does not record.

import type { ReplayState } from './replay';
import type { TraceBundle, TraceEvent } from './types';

export interface Narration {
  /** One sentence for the headline. Segments let the view colour signed figures. */
  headline: Segment[];
  detail: string;
  /** Closing frame only: evidence-derived statements, each recomputed from the replay state. */
  points?: Segment[][];
}

export type Segment = string | { n: number; tone?: 'gain' | 'loss'; signed?: boolean; unit?: string };

export const fmt = (n: number, signed = false) => {
  const s = Math.abs(n).toLocaleString('en-US');
  if (!signed) return n < 0 ? `−${s}` : s;
  return n > 0 ? `+${s}` : n < 0 ? `−${s}` : '0';
};

export function costUnitLabel(unit: string) {
  return unit === 'nano_reported_usd' ? 'nano reported USD' : 'nano synthetic units';
}

export function narrateOpening(bundle: TraceBundle, s: ReplayState): Narration {
  const tasks = s.tasks.length;
  const models = new Set(s.tasks.flatMap((t) => t.models)).size;
  const headline: Segment[] = [
    `${words(tasks)} ${tasks === 1 ? 'task' : 'tasks'}. ${cap(words(models))} candidate models. `,
  ];
  if (s.budget !== undefined) headline.push('A budget of ', { n: s.budget }, '. ');
  headline.push('Watch an allocator commit before it knows what anything costs.');
  return {
    headline,
    detail: `${bundle.trace.events.length} recorded events. Left of the settlement line was public when decisions were made; right of it was revealed only afterwards. Market prices and trades are not part of v0.2 traces.`,
  };
}

export function narrate(e: TraceEvent, s: ReplayState): Narration {
  switch (e.type) {
    case 'public_forecast': {
      const entries = Object.entries(e.payload.values).sort((a, b) => b[1] - a[1]);
      const [top, second] = entries;
      return {
        headline: [
          `A public forecast for ${e.payload.task_id}: model ${top[0]} is expected to score `,
          { n: top[1] },
          `, model ${second[0]} `,
          { n: second[1] },
          '.',
        ],
        detail: `From ${e.actor}. Values are expected judged-preference reward (a noisy proxy), not a probability that the code is correct.`,
      };
    }
    case 'reservation': {
      const { task_id, model_id, reserved_cost } = e.payload;
      const t = s.tasks.find((x) => x.task_id === task_id);
      const headline: Segment[] =
        model_id === null
          ? [`The allocator abstains on ${task_id}.`]
          : [`The allocator reserves `, { n: reserved_cost }, ` to run ${task_id} on model ${model_id}.`];
      const parts = ['Committed before any cost is revealed.'];
      if (s.budget !== undefined) parts.push(`Reserved so far: ${fmt(s.reservationSpend)} of ${fmt(s.budget)}.`);
      const f = t?.forecast;
      if (f && model_id && f.seq < e.seq) {
        const best = Object.entries(f.values).sort((a, b) => b[1] - a[1])[0][0];
        if (best !== model_id) parts.push(`The public forecast favoured model ${best}; the trace does not record why the allocator chose ${model_id}.`);
      }
      return { headline, detail: parts.join(' ') };
    }
    case 'realized_cost_report': {
      const r = e.payload;
      const headline: Segment[] = ['Settlement. Realized costs total ', { n: r.realized_spend }];
      if (s.budget !== undefined) {
        headline.push(' against a budget of ', { n: s.budget });
        headline.push(
          r.realized_budget_violated ? ': ' : '.',
          ...(r.realized_budget_violated ? [{ n: r.realized_budget_excess, tone: 'loss' as const, signed: true }, ' over budget.'] : []),
        );
      } else {
        headline.push('.');
      }
      const reservedOk = s.budget === undefined || r.reservation_spend <= s.budget;
      return {
        headline,
        detail: `Against its own reservations of ${fmt(r.reservation_spend)}, spending ran ${fmt(r.net_overrun, true)}${
          s.budget !== undefined ? `; against the budget, ${fmt(r.realized_budget_excess, true)}` : ''
        }. ${reservedOk ? 'The plan itself stayed within budget, so this is a reported retrospective outcome, not an allocation error.' : ''}`.trim(),
      };
    }
    case 'ledger_transfer': {
      const { payer, payee, amount, reason } = e.payload;
      const what = reason === 'action_fee' ? 'an action fee' : reason === 'settlement' ? 'a settlement payment' : reason.replace(/_/g, ' ');
      return {
        headline: [`${cap(payer)} pays ${payee} `, { n: amount }, ` credits: ${what}.`],
        detail: 'Virtual credits. They are never added to, or converted into, cost units.',
      };
    }
    case 'utility_summary': {
      const entries = Object.entries(e.payload);
      if (entries.length !== 1) {
        return { headline: [`Utilities settle for ${entries.length} agents.`], detail: 'utility = cash change + external benefit − effort.' };
      }
      const [agent, u] = entries[0];
      return {
        headline: [
          `${cap(agent)} ends with utility `,
          { n: u.utility, tone: u.utility >= 0 ? 'gain' : 'loss', signed: true },
          '.',
        ],
        detail: `Cash ${fmt(u.cash_delta, true)}, external benefit ${fmt(u.external_benefit, true)}, effort ${fmt(-u.noncash_effort_cost, true)}. External benefit is a modelled utility term, not a funded transfer.`,
      };
    }
  }
}

/**
 * The closing frame. Every statement is computed from the final replay state; nothing is authored
 * per fixture. Claims are limited to accounting the events establish.
 */
export function narrateEnd(bundle: TraceBundle, s: ReplayState): Narration {
  const r = s.report;
  const b = s.budget;
  const points: Segment[][] = [];
  const headline: Segment[] = [];
  if (r && b !== undefined) {
    const fitted = r.reservation_spend <= b;
    if (fitted && r.realized_budget_violated) {
      headline.push('Within budget on paper. ', { n: r.realized_budget_excess, tone: 'loss', signed: true }, ' over once costs were known.');
    } else if (fitted) {
      headline.push('Committed within budget, and stayed there: ', { n: b - r.realized_spend }, ' to spare.');
    } else {
      headline.push('Reservations exceeded the budget before any cost was known.');
    }
    points.push(['Reserved ', { n: r.reservation_spend }, ' of a ', { n: b }, ' budget before any cost was revealed.']);
  } else if (r) {
    headline.push('Settled: realized ', { n: r.realized_spend }, ' against ', { n: r.reservation_spend }, ' reserved.');
  } else {
    headline.push('The replay ends without a settlement report.');
  }
  const deltas = s.tasks.filter((t) => t.reservation?.model_id && t.realized).map((t) => ({ id: t.task_id, d: t.realized!.realized_cost - t.reservation!.reserved_cost }));
  if (deltas.length) {
    const parts: Segment[] = [];
    deltas.forEach(({ id, d }, i) => {
      if (i) parts.push(i === deltas.length - 1 ? '; ' : ', ');
      if (d > 0) parts.push(`${id} ran `, { n: d, tone: 'loss', signed: true }, ' over its reservation');
      else if (d < 0) parts.push(`${id} came in `, { n: -d, tone: 'gain' }, ' under');
      else parts.push(`${id} cost exactly its reservation`);
    });
    parts.push('.');
    points.push(parts);
  }
  const moved = s.accounts.filter((a) => a.delta !== 0);
  if (moved.length) {
    const parts: Segment[] = ['Credits moved: '];
    moved.forEach((a, i) => {
      if (i) parts.push(', ');
      parts.push(`${a.id} `, { n: a.delta, tone: a.delta > 0 ? 'gain' : 'loss', signed: true });
    });
    const net = moved.reduce((x, a) => x + a.delta, 0);
    parts.push(net === 0 ? '. They sum to zero: nothing was created or burned.' : '.');
    points.push(parts);
  }
  for (const [agent, u] of Object.entries(s.utilities?.values ?? {})) {
    points.push([`${cap(agent)} ends with utility `, { n: u.utility, tone: u.utility >= 0 ? 'gain' : 'loss', signed: true }, ' from cash ', { n: u.cash_delta, signed: true }, '.']);
  }
  return {
    headline,
    detail:
      bundle.origin === 'SYNTHETIC_FIXTURE'
        ? 'A hand-authored synthetic fixture: this shows the replay’s accounting, not a mechanism result.'
        : `Recomputed from ${bundle.trace.events.length} validated events.`,
    points,
  };
}

const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
function words(n: number) {
  return WORDS[n] ?? n.toLocaleString('en-US');
}
function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
