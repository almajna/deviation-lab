// Scene geometry: a pure function from the known replay state to positions and labels.
// It never sees events beyond the cursor, so nothing it returns can reveal the future.
// Two compositions: 'wide' (landscape, desktop) and 'tall' (portrait, phones).

import type { ReplayState } from '../trace/replay';
import { exact, fmt } from '../trace/narrate';
import type { InspectTarget } from '../components/Inspector';

export type Mode = 'wide' | 'tall';

interface Frame {
  W: number; H: number;
  taskX: number; modelX: number; rowTop: number; rowBottom: number; headY: number;
  barY: number; barX0: number; barX1: number;
  ledgerY: number; accX0: number; accX1: number; utilY: number;
  prompts: boolean; modelPrefix: string;
}

const FRAMES: Record<Mode, Frame> = {
  wide: { W: 1000, H: 830, taskX: 230, modelX: 780, rowTop: 110, rowBottom: 320, headY: 52, barY: 460, barX0: 120, barX1: 880, ledgerY: 720, accX0: 200, accX1: 800, utilY: 792, prompts: false, modelPrefix: 'model ' },
  tall: { W: 360, H: 700, taskX: 92, modelX: 262, rowTop: 92, rowBottom: 196, headY: 44, barY: 330, barX0: 20, barX1: 340, ledgerY: 572, accX0: 64, accX1: 296, utilY: 644, prompts: false, modelPrefix: '' },
};

export interface Item { id: string; x: number; y: number; label: string; sub?: string; active: boolean; target?: InspectTarget; aria: string }
export interface Link { id: string; d: string; task: string; model: string; selected: boolean; forecast: boolean; value?: number; target?: InspectTarget }
export interface ValueLabel { id: string; x: number; y: number; text: string; target: InspectTarget; aria: string }
export interface Block {
  id: string; x: number; y: number; h: number;
  base: number; over: number; /** px widths */
  /** where a newly reserved block flies in from (link midpoint) */
  from: { x: number; y: number };
  reserveSeq: number; target: InspectTarget; aria: string;
  label: { x: number; y: number; text: string; delta?: { text: string; tone: 'gain' | 'loss' | 'none' } };
  /** the reservation, drawn as a dashed outline under the bar once costs are known */
  reservedW?: number;
}
export interface Account { id: string; x: number; y: number; delta: number; balance?: number; target: InspectTarget; aria: string }
export interface Arc { id: string; d: string; points: Array<[number, number]>; label: { x: number; y: number; text: string }; live: boolean; seq: number }

export type ViewBox = [number, number, number, number];

export interface SceneLayout {
  mode: Mode; W: number; H: number;
  /** Camera framings: the element keeps one aspect ratio; the camera frames the part in focus. */
  views: { compute: ViewBox; settle: ViewBox; ledger: ViewBox; all: ViewBox };
  heads: Array<{ x: number; y: number; text: string; anchor: 'start' | 'middle' | 'end' }>;
  tasks: Item[]; models: Item[]; links: Link[]; forecasts: ValueLabel[]; forecastCaption?: { x: number; y: number };
  curves: Array<{ id: string; d: string }>;
  bar: { y: number; x0: number; x1: number; h: number; ticksEvery?: number };
  caption: { x: number; y: number; label: string; value: string; tone?: 'loss' };
  budget?: { x: number; label: string; note?: string; target?: InspectTarget };
  /** One-line compute summary shown above the credits when the camera frames them. */
  summary?: { x: number; y: number; text: string; tone?: 'loss' };
  blocks: Block[];
  excess?: { x0: number; x1: number; y: number; text: string; target: InspectTarget };
  sealed: boolean;
  accounts: Account[]; arcs: Arc[];
  utility?: { x: number; y: number; text: string; sub: string; target: InspectTarget; tone: 'gain' | 'loss' };
  ledgerVisible: boolean;
}

const spread = (n: number, a: number, b: number, maxGap: number) => {
  if (n <= 1) return [(a + b) / 2];
  const gap = Math.min((b - a) / (n - 1), maxGap);
  const start = (a + b) / 2 - (gap * (n - 1)) / 2;
  return Array.from({ length: n }, (_, i) => start + i * gap);
};

const cubic = (p0: number, p1: number, p2: number, p3: number, t: number) =>
  (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3;

function niceTop(max: number) {
  const raw = max / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  return Math.ceil(max / step) * step;
}

export function sceneLayout(state: ReplayState, mode: Mode): SceneLayout {
  const F = FRAMES[mode];
  const ev = (seq: number): InspectTarget => ({ kind: 'event', seq });

  // ── Tasks and models ────────────────────────────────────────────
  const taskYs = spread(state.tasks.length, F.rowTop, F.rowBottom, 110);
  const modelIds = [...new Set(state.tasks.flatMap((t) => t.models))].sort();
  const modelYs = spread(modelIds.length, F.rowTop, F.rowBottom, 110);
  const modelY = new Map(modelIds.map((m, i) => [m, modelYs[i]]));
  const chosenModels = new Set(state.tasks.map((t) => t.reservation?.model_id).filter(Boolean) as string[]);

  const tasks: Item[] = state.tasks.map((t, i) => ({
    id: t.task_id, x: F.taskX, y: taskYs[i], label: t.task_id, sub: F.prompts ? t.prompt : undefined,
    active: !!t.reservation?.model_id,
    target: t.reservation ? ev(t.reservation.seq) : t.forecast ? ev(t.forecast.seq) : undefined,
    aria: `Task ${t.task_id}${t.prompt ? `: ${t.prompt}` : ''}${t.reservation?.model_id ? `, reserved on model ${t.reservation.model_id}` : ''}`,
  }));
  const models: Item[] = modelIds.map((m) => ({
    id: m, x: F.modelX, y: modelY.get(m)!, label: `${F.modelPrefix}${m}`, active: chosenModels.has(m), aria: `Model ${m}${chosenModels.has(m) ? ', selected' : ''}`,
  }));

  const linkGeom = (ty: number, my: number) => {
    const x0 = F.taskX + 10, x3 = F.modelX - 10, mx = (x0 + x3) / 2;
    return { d: `M ${x0} ${ty} C ${mx} ${ty}, ${mx} ${my}, ${x3} ${my}`, at: (t: number) => [cubic(x0, mx, mx, x3, t), cubic(ty, ty, my, my, t)] as [number, number] };
  };
  const links: Link[] = [];
  const forecasts: ValueLabel[] = [];
  const curves: Array<{ id: string; d: string }> = [];
  let forecastCaption: { x: number; y: number } | undefined;
  state.tasks.forEach((t, i) => {
    for (const m of t.models) {
      const g = linkGeom(taskYs[i], modelY.get(m)!);
      const selected = t.reservation?.model_id === m;
      links.push({ id: `${t.task_id}→${m}`, d: g.d, task: t.task_id, model: m, selected, forecast: !!t.forecast, value: t.forecast?.values[m], target: selected ? ev(t.reservation!.seq) : t.forecast ? ev(t.forecast.seq) : undefined });
      const v = t.forecast?.values[m];
      if (v !== undefined && t.forecast) {
        const [x, y] = g.at(0.3);
        forecasts.push({ id: `${t.task_id}:${m}`, x, y, text: `${m} ${exact(v)}`, target: ev(t.forecast.seq), aria: `Expected reward for ${t.task_id} on model ${m}: ${exact(v)}` });
        forecastCaption ??= { x: g.at(0.3)[0], y: Math.min(...t.models.map((mm) => linkGeom(taskYs[i], modelY.get(mm)!).at(0.3)[1])) - 22 };
      }
    }
    // Repeated forecasts become a small curve per model (only when the trace has more than one).
    if (t.forecasts.length > 1) {
      for (const m of t.models) {
        const pts = t.forecasts.map((f, k) => [F.taskX - 150 + (k / (t.forecasts.length - 1)) * 110, taskYs[i] + 26 - (f.values[m] ?? 0) * 18]);
        curves.push({ id: `${t.task_id}:${m}`, d: pts.map(([x, y], k) => `${k ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ') });
      }
    }
  });

  // ── Compute budget bar ─────────────────────────────────────────
  const r = state.report;
  const budget = state.budget;
  const top = niceTop(Math.max(budget ?? 0, state.reservationSpend, r?.realized_spend ?? 0) * 1.08 || 1);
  const span = F.barX1 - F.barX0;
  const px = (v: number) => (v / top) * span;
  const barH = mode === 'wide' ? 16 : 14;
  const reserved = state.tasks.filter((t) => t.reservation && t.reservation.model_id && t.reservation.reserved_cost > 0).sort((a, b) => a.reservation!.seq - b.reservation!.seq);
  let off = 0;
  const blocks: Block[] = reserved.map((t, i) => {
    const res = t.reservation!;
    const real = t.realized?.realized_cost;
    const width = real ?? res.reserved_cost;
    const base = Math.min(res.reserved_cost, width);
    const over = Math.max(width - res.reserved_cost, 0);
    const x = F.barX0 + px(off) + (i ? 4 : 0);
    off += width;
    const g = linkGeom(taskYs[state.tasks.indexOf(t)], modelY.get(res.model_id!)!);
    const [fx, fy] = g.at(0.5);
    const d = real !== undefined ? real - res.reserved_cost : undefined;
    const row = i % 2;
    // Keep each label (and its delta line) fully inside the bar's span: monospace width estimate.
    const deltaText = d === undefined ? '' : d > 0 ? `reserved ${fmt(res.reserved_cost)} · +${fmt(d)}` : d < 0 ? `reserved ${fmt(res.reserved_cost)} · ${fmt(-d)} unused` : 'as reserved';
    const half = (Math.max(`${t.task_id} ${fmt(width)}`.length, deltaText.length) * (mode === 'wide' ? 9.1 : 7.9)) / 2;
    const cx = Math.min(Math.max(x + px(width) / 2, F.barX0 + half), F.barX1 - half);
    return {
      // One white bar per task: its real width once known. Red is reserved for the over-budget region.
      id: t.task_id, x, y: F.barY, h: barH, base: px(base + over), over: 0, from: { x: fx, y: fy }, reserveSeq: res.seq,
      // The reservation stays drawn as an outline on the bar, so expected vs realized is literal.
      reservedW: px(res.reserved_cost),
      target: ev(real !== undefined ? t.realized!.seq : res.seq),
      aria: real !== undefined
        ? `${t.task_id}: reserved ${res.reserved_cost}, realized ${real}${d! > 0 ? `, ${d} over` : d! < 0 ? `, ${-d!} under` : ''}`
        : `${t.task_id}: reserved ${res.reserved_cost} on model ${res.model_id}`,
      label: {
        x: cx, y: F.barY + barH + 18 + row * (mode === 'wide' ? 34 : 32),
        text: `${t.task_id} ${fmt(width)}`,
        delta: d === undefined ? undefined : { text: d > 0 ? `reserved ${fmt(res.reserved_cost)} · +${fmt(d)}` : d < 0 ? `reserved ${fmt(res.reserved_cost)} · ${fmt(-d)} unused` : 'as reserved', tone: 'none' },
      },
    };
  });
  const used = r ? r.realized_spend : state.reservationSpend;
  const caption = r
    ? { x: F.barX0, y: F.barY - 52, label: 'compute used', value: fmt(r.realized_spend), tone: budget !== undefined && r.realized_budget_violated ? ('loss' as const) : undefined }
    : { x: F.barX0, y: F.barY - 52, label: 'compute reserved', value: fmt(state.reservationSpend) };
  const budgetMark = budget !== undefined
    ? { x: F.barX0 + px(budget), label: `budget ${fmt(budget)}`, note: state.budgetSource === 'annotation' ? 'fixture note' : undefined }
    : undefined;
  const excess = r && budget !== undefined && used > budget
    ? { x0: F.barX0 + px(budget), x1: F.barX0 + px(used), y: F.barY - 14, text: `+${fmt(used - budget)} over budget`, target: ev(r.seq) }
    : undefined;

  // ── Ledger ──────────────────────────────────────────────────────
  const accXs = spread(state.accounts.length, F.accX0, F.accX1, mode === 'wide' ? 260 : 120);
  const accounts: Account[] = state.accounts.map((a, i) => ({
    id: a.id, x: accXs[i], y: F.ledgerY, delta: a.delta, balance: a.initial !== undefined ? a.initial + a.delta : undefined,
    target: { kind: 'account', id: a.id }, aria: `Account ${a.id}: change ${fmt(a.delta, true)} credits. Inspect`,
  }));
  const ax = new Map(accounts.map((a) => [a.id, a.x]));
  const arcs: Arc[] = state.transfers.map((t, i) => {
    const x1 = ax.get(t.payer)!, x2 = ax.get(t.payee)!;
    const h = (mode === 'wide' ? 30 : 26) + i * (mode === 'wide' ? 26 : 22);
    const y = F.ledgerY - 34;
    const off2 = (i % 3) * 6;
    const a0 = x1 + off2, a3 = x2 - off2;
    const d = `M ${a0} ${y} C ${a0} ${y - h * 1.33}, ${a3} ${y - h * 1.33}, ${a3} ${y}`;
    const points = Array.from({ length: 24 }, (_, k) => {
      const tt = k / 23;
      return [cubic(a0, a0, a3, a3, tt), cubic(y, y - h * 1.33, y - h * 1.33, y, tt)] as [number, number];
    });
    return { id: t.transfer_id, d, points, label: { x: (a0 + a3) / 2, y: y - h - 6, text: fmt(t.amount) }, live: t.seq === state.cursor, seq: t.seq };
  });
  const u = state.utilities;
  const agentEntry = u ? Object.entries(u.values)[0] : undefined;
  const utility = u && agentEntry
    ? {
        x: mode === 'wide' ? F.accX0 - 80 : F.barX0, y: F.utilY,
        text: `${agentEntry[0]} utility ${fmt(agentEntry[1].utility, true)}`,
        sub: `cash ${fmt(agentEntry[1].cash_delta, true)} · modelled benefit ${fmt(agentEntry[1].external_benefit, true)} · effort ${fmt(-agentEntry[1].noncash_effort_cost, true)}`,
        target: ev(u.seq), tone: agentEntry[1].utility >= 0 ? ('gain' as const) : ('loss' as const),
      }
    : undefined;

  const heads: SceneLayout['heads'] = [
    { x: F.taskX, y: F.headY, text: 'tasks', anchor: mode === 'wide' ? 'end' : 'middle' },
    { x: F.modelX, y: F.headY, text: 'models', anchor: mode === 'wide' ? 'start' : 'middle' },
  ];
  if (accounts.length) heads.push({ x: F.barX0, y: F.ledgerY - (mode === 'wide' ? 126 : 94), text: 'credits', anchor: 'start' });

  const views = mode === 'wide'
    ? { compute: [70, 20, 880, 600] as ViewBox, settle: [70, 20, 880, 600] as ViewBox, ledger: [70, 360, 880, 600] as ViewBox, all: [0, 0, 1000, 830] as ViewBox }
    : { compute: [0, 20, 360, 420] as ViewBox, settle: [0, 232, 360, 420] as ViewBox, ledger: [0, 420, 360, 420] as ViewBox, all: [0, 0, 360, 700] as ViewBox };
  // On phones the credits frame carries a one-line memory of the compute outcome.
  const summary = mode === 'tall' && accounts.length
    ? { x: F.barX0, y: F.ledgerY - 120, text: r ? `compute used ${fmt(r.realized_spend)}${excess ? ` · ${excess.text}` : ''}` : `compute reserved ${fmt(state.reservationSpend)}`, tone: excess ? ('loss' as const) : undefined }
    : undefined;

  return {
    mode, W: F.W, H: F.H, views, heads, tasks, models, links, forecasts, forecastCaption, curves,
    bar: { y: F.barY, x0: F.barX0, x1: F.barX1, h: barH },
    caption, budget: budgetMark, blocks, excess, sealed: !r, summary,
    accounts, arcs, utility, ledgerVisible: accounts.length > 0,
  };
}
