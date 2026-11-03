import type { ReplayState } from '../trace/replay';
import { cohortAccounts } from '../trace/replay';
import { costUnitLabel, fmt } from '../trace/narrate';
import type { TraceBundle } from '../trace/types';
import { useWidth } from '../lib/hooks';
import { Num } from './Num';

export type InspectTarget = { kind: 'event'; seq: number } | { kind: 'account'; id: string } | { kind: 'trace' };

interface Props {
  bundle: TraceBundle;
  /** Everything rendered here comes from this state: the known prefix of events only. */
  state: ReplayState;
  onInspect: (t: InspectTarget) => void;
}

type Row = 'tasks' | 'budget' | 'ledger';

/** Which stage row the event at the cursor writes to (none on the opening and closing frames). */
export function focusOf(bundle: TraceBundle, cursor: number): Row | undefined {
  const e = bundle.trace.events[cursor];
  if (!e) return undefined;
  if (e.type === 'public_forecast') return 'tasks';
  if (e.type === 'reservation' || e.type === 'realized_cost_report') return 'budget';
  return 'ledger';
}

export function Stage({ bundle, state, onInspect }: Props) {
  const focus = focusOf(bundle, state.cursor);
  const active = (r: Row) => (focus === undefined ? undefined : focus === r || (r === 'tasks' && focus === 'budget'));
  return (
    <section className="stage" aria-label="Replay stage" data-focus={focus}>
      <Tasks state={state} onInspect={onInspect} active={active('tasks')} />
      <div className="stage-pair">
        <Budget bundle={bundle} state={state} onInspect={onInspect} active={active('budget')} />
        <Ledger state={state} onInspect={onInspect} active={active('ledger')} />
      </div>
    </section>
  );
}

function Seq({ seq, onInspect, children, label }: { seq: number; onInspect: Props['onInspect']; children: React.ReactNode; label: string }) {
  return (
    <button type="button" className="value-btn" onClick={() => onInspect({ kind: 'event', seq })} aria-label={`${label}. Inspect event ${seq + 1}`}>
      {children}
    </button>
  );
}

function Caption({ title, note }: { title: string; note: string }) {
  return (
    <h2 className="caption">
      {title}
      <small>{note}</small>
    </h2>
  );
}

function Tasks({ state, onInspect, active }: { state: ReplayState; onInspect: Props['onInspect']; active?: boolean }) {
  return (
    <div className="stage-row" data-row="tasks" data-active={active}>
      <Caption title="Tasks" note="forecasts are expected judged-preference reward" />
      {state.tasks.length === 0 && <p className="empty">No task has appeared yet.</p>}
      <div className="tasks">
        {state.tasks.map((t) => (
          <article className="task" key={t.task_id} aria-label={`Task ${t.task_id}${t.forecast ? '' : ', no public forecast yet'}`}>
            <header>
              <span className="num">{t.task_id}</span>
              {t.prompt && <span title={t.prompt}>{t.prompt}</span>}
            </header>
            <div className="colhead" aria-hidden="true">
              <span>model</span>
              <span>{t.forecast ? '' : 'no public forecast'}</span>
              <span>reward</span>
              <span>reserved</span>
              <span>realized<span className="qual"> · vs reserved</span></span>
            </div>
            {t.models.map((m) => {
              const v = t.forecast?.values[m];
              const chosen = t.reservation?.model_id === m;
              const realized = chosen ? t.realized : undefined;
              const delta = realized ? realized.realized_cost - t.reservation!.reserved_cost : undefined;
              return (
                <div className="model" key={m} data-chosen={chosen}>
                  <span className="name">{m}</span>
                  <span className="track" data-empty={v === undefined} aria-hidden="true">
                    {v !== undefined && <i style={{ '--v': v } as React.CSSProperties} />}
                  </span>
                  <span className="val">
                    {v !== undefined && t.forecast ? (
                      <Seq seq={t.forecast.seq} onInspect={onInspect} label={`Expected reward for model ${m}: ${v.toFixed(2)}`}>
                        <Num value={v} dp={2} />
                      </Seq>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </span>
                  <span className="cost">
                    {chosen && t.reservation ? (
                      <Seq seq={t.reservation.seq} onInspect={onInspect} label={`Reserved ${t.reservation.reserved_cost} for model ${m}`}>
                        <Num value={t.reservation.reserved_cost} />
                      </Seq>
                    ) : null}
                  </span>
                  <span className="cost realized">
                    {chosen && t.reservation ? (
                      realized && delta !== undefined ? (
                        <Seq seq={realized.seq} onInspect={onInspect} label={`Realized ${realized.realized_cost}, ${delta > 0 ? `${delta} over` : delta < 0 ? `${-delta} under` : 'equal to'} the reservation`}>
                          <Num value={realized.realized_cost} />
                          <small className={delta > 0 ? 'loss' : delta < 0 ? 'gain' : 'faint'}>
                            {delta > 0 ? <><Num value={delta} signed /> over</> : delta < 0 ? <><Num value={-delta} /> under</> : 'exact'}
                          </small>
                        </Seq>
                      ) : (
                        <span className="faint">sealed</span>
                      )
                    ) : null}
                  </span>
                </div>
              );
            })}
          </article>
        ))}
      </div>
    </div>
  );
}

function scaleOf(max: number) {
  const raw = max / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const top = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(Math.round(v));
  return { top, ticks };
}

function Budget({ bundle, state, onInspect, active }: Props & { active?: boolean }) {
  const unit = costUnitLabel(bundle.trace.cost_unit);
  const r = state.report;
  const budget = state.budget;
  // The scale is sized from what is known now; it widens at settlement if realized costs require it.
  const { top, ticks } = scaleOf(Math.max(budget ?? 0, state.reservationSpend, r?.realized_spend ?? 0) * 1.05 || 1);
  const pct = (n: number) => `${(n / top) * 100}%`;

  let offset = 0;
  const reservedSegs = state.tasks
    .filter((t) => t.reservation && t.reservation.reserved_cost > 0)
    .map((t) => {
      const seg = { id: t.task_id, left: offset, w: t.reservation!.reserved_cost };
      offset += seg.w;
      return seg;
    });
  let rOffset = 0;
  const realizedSegs = r
    ? state.tasks.filter((t) => t.realized).map((t) => {
        const seg = { id: t.task_id, left: rOffset, w: t.realized!.realized_cost };
        rOffset += seg.w;
        return seg;
      })
    : [];
  const over = r && budget !== undefined && r.realized_spend > budget ? r.realized_spend - budget : 0;

  return (
    <div className="stage-row" data-row="budget" data-active={active}>
      <Caption title="Budget" note={state.budgetSource === 'annotation' ? `${unit} · budget: fixture annotation` : unit} />
      <div className="budget" role="img" aria-label={budgetLabel(state, budget)}>
        {budget !== undefined && (
          <div className="budget-overlay" aria-hidden="true">
            <span />
            <span>
              <span className="budget-line" style={{ left: pct(budget) }}>
                <span>
                  budget <Num value={budget} />
                </span>
              </span>
            </span>
            <span />
          </div>
        )}
        <div className="bar-row">
          <span>Reserved</span>
          <span className="bar">
            {reservedSegs.map((s) => (
              <i key={s.id} className="seg grow" style={{ left: pct(s.left), width: pct(s.w) }} />
            ))}
          </span>
          <span>
            <Num value={state.reservationSpend} />
          </span>
        </div>
        <div className="bar-row">
          <span>Realized</span>
          <span className="bar">
            {!r && <i className="sealed" />}
            {realizedSegs.map((s) => (
              <i key={s.id} className="seg dim grow" style={{ left: pct(s.left), width: pct(s.w) }} />
            ))}
            {over > 0 && (
              <>
                <i className="seg over grow late" style={{ left: pct(budget!), width: pct(over) }} />
                <span className="bar-note num" aria-hidden="true" style={{ left: pct(budget!), width: pct(over) }}>
                  {fmt(over, true)} over budget
                </span>
              </>
            )}
          </span>
          <span>
            {r ? (
              <Seq seq={r.seq} onInspect={onInspect} label={`Realized spend ${r.realized_spend}`}>
                <Num value={r.realized_spend} tone={r.realized_budget_violated && budget !== undefined ? 'loss' : undefined} />
              </Seq>
            ) : (
              <span className="faint">sealed</span>
            )}
          </span>
        </div>
        <div className="axis" aria-hidden="true">
          <span />
          <span className="ticks">
            {ticks.map((t, i) => (
              <span key={t} style={{ left: pct(t) }} data-edge={i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : undefined}>
                {fmt(t)}
              </span>
            ))}
          </span>
          <span />
        </div>
      </div>
      <p className="budget-report">
        {r ? (
          <>
            <span>
              vs reserved <Num value={r.net_overrun} signed tone={r.net_overrun > 0 ? 'loss' : r.net_overrun < 0 ? 'gain' : undefined} />
              <span className="faint">
                {' '}
                (overruns <Num value={r.positive_task_overruns} signed /> · unused <Num value={-r.unused_reservations} signed />)
              </span>
            </span>
            {budget !== undefined && (
              <span>
                vs budget <Num value={r.realized_budget_excess} signed tone={r.realized_budget_violated ? 'loss' : undefined} />
              </span>
            )}
          </>
        ) : budget === undefined ? (
          <span className="faint">No run configuration loaded; budget unknown.</span>
        ) : (
          <span className="faint">Realized costs are sealed until settlement.</span>
        )}
      </p>
    </div>
  );
}

function budgetLabel(s: ReplayState, budget?: number) {
  const parts = [`Reserved ${s.reservationSpend}`];
  if (budget !== undefined) parts.push(`of a ${budget} budget`);
  parts.push(s.report ? `Realized ${s.report.realized_spend}` : 'Realized cost sealed until settlement');
  return parts.join('. ');
}

function Ledger({ state, onInspect, active }: { state: ReplayState; onInspect: Props['onInspect']; active?: boolean }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const groups = cohortAccounts(state.accounts);
  const n = groups.length;
  const col = (id: string) => groups.findIndex((g) => g.members.some((m) => m.id === id));
  const gap = 24;
  const cw = n ? (width - gap * (n - 1)) / n : 0;
  const x = (i: number) => i * (cw + gap) + 8;
  const balances = n > 0 && groups.every((g) => g.members.every((m) => m.initial !== undefined));

  return (
    <div className="stage-row" data-row="ledger" data-active={active}>
      <Caption title="Ledger" note={balances ? 'virtual credits' : 'virtual credits · net change; balances are not in the public trace'} />
      <div className="ledger">
        {n === 0 ? (
          <p className="empty">{state.settled ? 'No credits have moved yet.' : 'No credits move until settlement.'}</p>
        ) : (
          <div ref={ref} className="accounts" style={{ '--n': n, paddingTop: state.transfers.length ? 64 : 0 } as React.CSSProperties}>
            {state.transfers.length > 0 && width > 0 && (
              <svg className="flows" width={width} height={64} style={{ height: 64 }} aria-hidden="true">
                <defs>
                  {['live', 'past'].map((k) => (
                    <marker key={k} id={`arrow-${k}`} viewBox="0 0 6 6" refX="5" refY="3" markerWidth="7" markerHeight="7" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                      <path d="M0 0 L6 3 L0 6 z" fill={k === 'live' ? 'var(--fg)' : 'var(--fg-3)'} stroke="none" />
                    </marker>
                  ))}
                </defs>
                {state.transfers.map((t, i) => {
                  const a = col(t.payer), b = col(t.payee);
                  if (a < 0 || b < 0 || a === b) return null;
                  // Each transfer gets its own lane: distinct endpoints and apex height, label above the apex.
                  const x1 = x(a) + i * 14, x2 = x(b) + i * 14;
                  const h = 18 + i * 28;
                  const y = 62;
                  const d = `M ${x1} ${y} C ${x1} ${y - h * 1.33}, ${x2} ${y - h * 1.33}, ${x2} ${y - 2}`;
                  const live = t.seq === state.cursor;
                  const len = Math.abs(x2 - x1) + h * 2;
                  return (
                    <g key={`${t.transfer_id}:${live}`} className={live ? 'live' : 'past'}>
                      <path d={d} style={{ '--len': len } as React.CSSProperties} markerEnd={`url(#arrow-${live ? 'live' : 'past'})`} />
                      <text x={(x1 + x2) / 2} y={y - h - 5} textAnchor="middle">
                        {t.amount}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
            {groups.map((g) => {
              const delta = g.members.reduce((s, m) => s + m.delta, 0);
              const initial = balances ? g.members.reduce((s, m) => s + (m.initial ?? 0), 0) : undefined;
              const id = g.members.length === 1 ? g.members[0].id : g.key;
              return (
                <button type="button" key={g.key} className="account" onClick={() => onInspect({ kind: 'account', id })} aria-label={`Account ${g.label}: change ${fmt(delta, true)} credits. Inspect`}>
                  <span className="id">{g.label}</span>
                  {initial !== undefined ? (
                    <>
                      <Num value={initial + delta} className="bal" />
                      <span className="delta" data-zero={delta === 0}>
                        <Num value={delta} signed tone="auto" />
                      </span>
                    </>
                  ) : (
                    <Num value={delta} signed tone="auto" className="bal" />
                  )}
                </button>
              );
            })}
          </div>
        )}
        {state.utilities &&
          Object.entries(state.utilities.values).map(([agent, u]) => (
            <p className="utility" key={agent}>
              <span><span className="num">{agent}</span> utility</span>
              <Seq seq={state.utilities!.seq} onInspect={onInspect} label={`${agent} utility ${u.utility}`}>
                <Num value={u.utility} signed tone="auto" className="eq" />
              </Seq>
              <span>
                = cash <Num value={u.cash_delta} signed /> + external <Num value={u.external_benefit} /> − effort <Num value={u.noncash_effort_cost} />
              </span>
            </p>
          ))}
      </div>
    </div>
  );
}
