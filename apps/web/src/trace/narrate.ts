// Scene narration derived only from event payloads and the replay state.
// Each scene has a short chapter name, one plain-language headline, one sentence of explanation and an
// optional technical note shown on request. It states what the record shows and never infers motives.

import type { ReplayState } from './replay';
import type { TraceBundle, TraceEvent } from './types';

export interface Narration {
  /** Chapter name for the scene, e.g. "Forecast", "Reserve", "Settle". */
  chapter: string;
  /** One sentence. Segments let the view colour signed figures. */
  headline: Segment[];
  /** One plain sentence for a first-time viewer. */
  detail: string;
  /** Technical caveat, revealed on request. */
  note?: string;
  /** Closing frame only: evidence-derived statements, each recomputed from the replay state. */
  points?: Segment[][];
}

export type Segment = string | { n: number; tone?: 'gain' | 'loss'; signed?: boolean; exact?: boolean };

export const fmt = (n: number, signed = false) => {
  const s = Math.abs(n).toLocaleString('en-US');
  if (!signed) return n < 0 ? `−${s}` : s;
  return n > 0 ? `+${s}` : n < 0 ? `−${s}` : '0';
};

/** A recorded fractional value exactly as recorded: at least two decimals, never rounded away. */
export const exact = (v: number) => {
  const s = String(v);
  const dp = s.includes('.') ? s.split('.')[1].length : 0;
  return v.toFixed(Math.max(2, Math.min(dp, 12)));
};

export function costUnitLabel(unit: string) {
  return unit === 'nano_reported_usd' ? 'nano reported USD' : 'nano synthetic units';
}

export function narrateOpening(bundle: TraceBundle, s: ReplayState): Narration {
  const tasks = s.tasks.length;
  const models = new Set(s.tasks.flatMap((t) => t.models)).size;
  const headline: Segment[] = [`${cap(words(tasks))} AI ${tasks === 1 ? 'task' : 'tasks'} compete for scarce compute`];
  if (s.budget !== undefined) headline.push(': a budget of ', { n: s.budget }, ' units.');
  else headline.push('.');
  return {
    chapter: 'The setup',
    headline,
    detail: `An allocator must reserve compute and choose among ${words(models).toLowerCase()} candidate models before anyone knows what each run will really cost.`,
    note: `${bundle.trace.events.length} recorded events. Events before settlement were public when decisions were made; later events were revealed only afterwards. Market prices and trades are not part of v0.2 traces.${
      s.budgetSource === 'annotation' ? ' The budget is a labelled fixture annotation, not a field of the trace.' : ''
    }`,
  };
}

export function narrate(e: TraceEvent, s: ReplayState): Narration {
  switch (e.type) {
    case 'public_forecast': {
      const entries = Object.entries(e.payload.values).sort((a, b) => b[1] - a[1]);
      const [top, second] = entries;
      return {
        chapter: 'Forecast',
        headline: [`A forecast for ${e.payload.task_id}: model ${top[0]} is expected to do better, `, { n: top[1], exact: true }, ' against ', { n: second[1], exact: true }, '.'],
        detail: 'Expected reward is about quality, not cost. Forecasts are public: every participant could see this one before acting.',
        note: `From ${e.actor}. Values are expected judged-preference reward (a noisy proxy), not a probability that the code is correct.`,
      };
    }
    case 'reservation': {
      const { task_id, model_id, reserved_cost } = e.payload;
      const t = s.tasks.find((x) => x.task_id === task_id);
      const headline: Segment[] =
        model_id === null ? [`The allocator declines to run ${task_id}.`] : ['The allocator reserves ', { n: reserved_cost }, ` units to run ${task_id} on model ${model_id}.`];
      const parts: string[] = [];
      if (s.budget !== undefined) {
        parts.push(`${fmt(s.reservationSpend)} of ${fmt(s.budget)} now reserved, committed before any cost is known.`);
      } else {
        parts.push(`${fmt(s.reservationSpend)} reserved so far, committed before any cost is known.`);
      }
      let note: string | undefined;
      const f = t?.forecast;
      if (f && model_id && f.seq < e.seq) {
        const best = Object.entries(f.values).sort((a, b) => b[1] - a[1])[0][0];
        if (best !== model_id) {
          // Stated as a fact from the record, with no claim about why.
          parts.unshift(`The public forecast favoured model ${best}.`);
          note = `The trace does not record why the allocator chose ${model_id}. Forecasts are about expected reward (quality); reservations and realized costs are about compute.`;
        }
      }
      return { chapter: `Reserve ${task_id}`, headline, detail: parts.join(' '), note };
    }
    case 'realized_cost_report': {
      const r = e.payload;
      const headline: Segment[] = ['Then the real costs arrive: ', { n: r.realized_spend }];
      if (s.budget !== undefined && r.realized_budget_violated) headline.push(', ', { n: r.realized_budget_excess, tone: 'loss', signed: true }, ' over budget.');
      else if (s.budget !== undefined) headline.push(', within the budget of ', { n: s.budget }, '.');
      else headline.push(' units.');
      const deltas = s.tasks
        .filter((t) => t.reservation?.model_id && t.realized)
        .map((t) => {
          const d = t.realized!.realized_cost - t.reservation!.reserved_cost;
          return d > 0 ? `${t.task_id} cost ${fmt(t.realized!.realized_cost)}, ${fmt(d)} more than reserved` : d < 0 ? `${t.task_id} used ${fmt(-d)} less than reserved` : `${t.task_id} cost exactly what was reserved`;
        });
      // Budget claims only when a budget is actually known (run configuration or labelled annotation).
      const reservedOk = s.budget !== undefined && r.reservation_spend <= s.budget;
      return {
        chapter: 'Settle',
        headline,
        detail: deltas.length ? `${deltas.join('; ')}.` : 'No model was run.',
        note: `Against its own reservations of ${fmt(r.reservation_spend)}, spending ran ${fmt(r.net_overrun, true)}${
          s.budget !== undefined ? `; against the budget, ${fmt(r.realized_budget_excess, true)}` : ''
        }. ${reservedOk ? 'The plan itself stayed within budget, so this is a reported retrospective outcome, not an allocation error.' : ''}`.trim(),
      };
    }
    case 'ledger_transfer': {
      const { payer, payee, amount, reason } = e.payload;
      const what = reason === 'action_fee' ? 'an action fee' : reason === 'settlement' ? 'a settlement payment' : reason.replace(/_/g, ' ');
      return {
        chapter: reason === 'action_fee' ? 'Fee' : reason === 'settlement' ? 'Payout' : 'Transfer',
        headline: [`${cap(payer === 'maker' ? 'the maker' : payer)} pays `, { n: amount }, ` credits to ${payee}: ${what}.`],
        detail: 'Credits are a separate, virtual currency for the agents. They are never mixed with compute.',
        note: 'Every transfer debits one account and credits another by the same amount; fees go to a named fee sink, never an invisible burn.',
      };
    }
    case 'utility_summary': {
      const entries = Object.entries(e.payload);
      if (entries.length !== 1) {
        return { chapter: 'Outcome', headline: [`Utilities settle for ${entries.length} agents.`], detail: 'Utility is the change in cash, plus any modelled benefit, minus effort.' };
      }
      const [agent, u] = entries[0];
      return {
        chapter: 'Outcome',
        headline: [`${cap(agent)} ends `, { n: u.utility, tone: u.utility >= 0 ? 'gain' : 'loss', signed: true }, ' in utility.'],
        detail: `Cash ${fmt(u.cash_delta, true)}, modelled benefit ${fmt(u.external_benefit, true)}, effort ${fmt(-u.noncash_effort_cost, true)}.`,
        note: 'External benefit is a modelled utility term, not a funded transfer. utility = cash change + external benefit − noncash effort.',
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
    // Lead with what the trace itself records; the budget comparison follows, labelled by source.
    headline.push('Reserved ', { n: r.reservation_spend }, '. Used ', { n: r.realized_spend }, '.');
    const src = s.budgetSource === 'annotation' ? ' (fixture annotation)' : '';
    if (fitted && r.realized_budget_violated) {
      points.push(['The plan fit the ', { n: b }, ` budget${src}; the real costs ran `, { n: r.realized_budget_excess, tone: 'loss', signed: true }, ' over it.']);
    } else if (fitted) {
      points.push(['The plan fit the ', { n: b }, ` budget${src}, and the real costs stayed within it.`]);
    } else {
      points.push(['The reservations already exceeded the ', { n: b }, ` budget${src}.`]);
    }
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
      if (d > 0) parts.push(`${id} used `, { n: d }, ' more than reserved');
      else if (d < 0) parts.push(`${id} used `, { n: -d }, ' less');
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
    chapter: 'What the record shows',
    headline,
    detail:
      bundle.origin === 'SYNTHETIC_FIXTURE'
        ? 'A hand-authored synthetic fixture: this shows the replay’s accounting, not a mechanism result.'
        : `Recomputed from ${bundle.trace.events.length} validated events.`,
    points,
  };
}

/** Short chapter label for a frame, used by the player. */
export function chapterOf(e: TraceEvent | undefined, frame: 'open' | 'event' | 'end') {
  if (frame === 'open') return 'The setup';
  if (frame === 'end') return 'Conclusion';
  switch (e?.type) {
    case 'public_forecast': return 'Forecast';
    case 'reservation': return `Reserve ${e.payload.task_id}`;
    case 'realized_cost_report': return 'Settle';
    case 'ledger_transfer': return e.payload.reason === 'action_fee' ? 'Fee' : e.payload.reason === 'settlement' ? 'Payout' : 'Transfer';
    default: return 'Outcome';
  }
}

const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
function words(n: number) {
  return WORDS[n] ?? n.toLocaleString('en-US');
}
function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
