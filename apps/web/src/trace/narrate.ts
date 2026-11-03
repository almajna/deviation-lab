// Plain-language narration derived only from event payloads and the replay state.
// Narration states what the record shows; it never infers motives the trace does not record.

import type { ReplayState } from './replay';
import type { TraceBundle, TraceEvent } from './types';

export interface Narration {
  /** One sentence for the headline. Segments let the view colour signed figures. */
  headline: Segment[];
  detail: string;
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
    detail: `${bundle.trace.events.length} recorded events. Everything to the left of the settlement line was public when decisions were made; everything to its right was revealed only afterwards.`,
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

const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
function words(n: number) {
  return WORDS[n] ?? n.toLocaleString('en-US');
}
function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
