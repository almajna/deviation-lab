import type { ReplayState } from '../trace/replay';
import { cohortAccounts } from '../trace/replay';
import { costUnitLabel, fmt } from '../trace/narrate';
import type { TraceBundle } from '../trace/types';
import { useWidth } from '../lib/hooks';
import { Num } from './Num';

export type InspectTarget = { kind: 'event'; seq: number } | { kind: 'account'; id: string } | { kind: 'trace' };

interface Props {
  bundle: TraceBundle;
  state: ReplayState;
  /** State at the final event: fixes scales so nothing reflows while seeking. */
  final: ReplayState;
  onInspect: (t: InspectTarget) => void;
}

type Row = 'tasks' | 'budget' | 'ledger';

/** Which stage row the event at the cursor writes to. */
function focusOf(bundle: TraceBundle, cursor: number): Row | undefined {
  const e = bundle.trace.events[cursor];
  if (!e) return undefined;
  if (e.type === 'public_forecast') return 'tasks';
  if (e.type === 'reservation' || e.type === 'realized_cost_report') return 'budget';
  return 'ledger';
}

export function Stage({ bundle, state, final, onInspect }: Props) {
  const focus = focusOf(bundle, state.cursor);
  const active = (r: Row) => (focus === undefined ? undefined : focus === r || (r === 'tasks' && focus === 'budget'));
  return (
    <section className="stage" aria-label="Replay stage" data-focus={focus}>
      <Tasks state={state} onInspect={onInspect} active={active('tasks')} />
      <div className="stage-pair">
        <Budget bundle={bundle} state={state} final={final} onInspect={onInspect} active={active('budget')} />
        <Ledger state={state} final={final} onInspect={onInspect} active={active('ledger')} />
      </div>
    </section>
  );
}

function Seq({ seq, onInspect, children, label }: { seq: number; onInspect: Props['onInspect']; children: React.ReactNode; label: string }) {
  return (
    <button type="button" className="value-btn" onClick={() => onInspect({ kind: 'event', seq })} aria-label={`${label}. Inspect event ${seq}`}>
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
    <div className="stage-row" data-active={active}>
      <Caption title="Tasks" note="forecasts are expected judged-preference reward" />
      <div className="tasks">
        {state.tasks.map((t) => (
          <article className="task" key={t.task_id} aria-label={`Task ${t.task_id}${t.forecast ? '' : ', no public forecast in this trace'}`}>
            <header>
              <span className="num">{t.task_id}</span>
              {t.prompt && <span title={t.prompt}>{t.prompt}</span>}
            </header>
            <div className="colhead" aria-hidden="true">
              <span>model</span>
              <span>{t.forecast ? '' : 'no public forecast'}</span>
              <span>reward</span>
              <span>reserved Δ</span>
            </div>
            {t.models.map((m) => {
              const v = t.forecast?.values[m];
              const chosen = t.reservation?.model_id === m;
              const delta = chosen && t.realized ? t.realized.realized_cost - t.reservation!.reserved_cost : undefined;
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
                    {chosen && t.reservation && (
                      <>
                        <Seq seq={t.reservation.seq} onInspect={onInspect} label={`Reserved ${t.reservation.reserved_cost}`}>
                          <Num value={t.reservation.reserved_cost} />
                        </Seq>
                        {delta !== undefined && t.realized && (
                          <>
                            {' '}
                            <Seq
                              seq={t.realized.seq}
                              onInspect={onInspect}
                              label={`Realized ${t.realized.realized_cost}, ${delta > 0 ? 'over' : 'under'} reservation by ${Math.abs(delta)}`}
                            >
                              <Num value={delta} signed tone={delta > 0 ? 'loss' : delta < 0 ? 'gain' : undefined} />
                            </Seq>
                          </>
                        )}
                      </>
                    )}
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

function Budget({ bundle, state, final, onInspect, active }: Props & { active?: boolean }) {
  const unit = costUnitLabel(bundle.trace.cost_unit);
  const finalRealized = final.report?.realized_spend ?? 0;
  const { top, ticks } = scaleOf(Math.max(state.budget ?? 0, finalRealized, final.reservationSpend) * 1.05 || 1);
  const pct = (n: number) => `${(n / top) * 100}%`;
  const budget = state.budget;
  const r = state.report;

  let offset = 0;
  const reservedSegs = final.tasks
    .filter((t) => t.reservation && t.reservation.reserved_cost > 0)
    .map((t) => {
      const seg = { id: t.task_id, left: offset, w: t.reservation!.reserved_cost, on: !!state.tasks.find((x) => x.task_id === t.task_id)?.reservation };
      offset += seg.w;
      return seg;
    });
  let rOffset = 0;
  const realizedSegs = final.tasks
    .filter((t) => t.realized)
    .map((t) => {
      const seg = { id: t.task_id, left: rOffset, w: t.realized!.realized_cost };
      rOffset += seg.w;
      return seg;
    });
  const over = budget !== undefined && finalRealized > budget;

  return (
    <div className="stage-row" data-active={active}>
      <Caption title="Budget" note={state.budgetSource === 'annotation' ? `${unit} · budget from fixture annotation, not the trace` : unit} />
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
              <i key={s.id} className="seg" style={{ left: pct(s.left), width: pct(s.w), transform: `scaleX(${s.on ? 1 : 0})` }} />
            ))}
          </span>
          <span>
            <Num value={state.reservationSpend} />
          </span>
        </div>
        <div className="bar-row">
          <span>Realized</span>
          <span className="bar">
            <i className="sealed" style={{ opacity: state.settled ? 0 : 1 }} />
            {realizedSegs.map((s) => (
              <i key={s.id} className="seg dim" style={{ left: pct(s.left), width: pct(s.w), transform: `scaleX(${state.settled ? 1 : 0})` }} />
            ))}
            {over && (
              <>
                <i className="seg over" style={{ left: pct(budget!), width: pct(finalRealized - budget!), transform: `scaleX(${state.settled ? 1 : 0})`, transitionDelay: state.settled ? '200ms' : '0ms' }} />
                {state.settled && (
                  <span className="bar-note num" aria-hidden="true" style={{ left: pct(budget!), width: pct(finalRealized - budget!) }}>
                    {fmt(finalRealized - budget!, true)} over budget
                  </span>
                )}
              </>
            )}
          </span>
          <span>
            {r ? (
              <Seq seq={r.seq} onInspect={onInspect} label={`Realized spend ${r.realized_spend}`}>
                <Num value={r.realized_spend} tone={r.realized_budget_violated ? 'loss' : undefined} />
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
      <p className="budget-report" data-hidden={!r}>
        {r ? (
          <>
            <span>
              vs reserved <Num value={r.net_overrun} signed tone={r.net_overrun > 0 ? 'loss' : 'gain'} />
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

function Ledger({ state, final, onInspect, active }: { state: ReplayState; final: ReplayState; onInspect: Props['onInspect']; active?: boolean }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const groups = cohortAccounts(state.accounts);
  const n = groups.length;
  const col = (id: string) => groups.findIndex((g) => g.members.some((m) => m.id === id));
  const gap = 24;
  const cw = n ? (width - gap * (n - 1)) / n : 0;
  const x = (i: number) => i * (cw + gap) + 8;
  const hasTransfers = final.transfers.length > 0;
  const utilityEvent = final.utilities?.seq;

  return (
    <div className="stage-row" data-active={active}>
      <Caption title="Ledger" note={groups.some((g) => g.members.some((m) => m.initial === undefined)) ? 'virtual credits · net change; balances are not in the public trace' : 'virtual credits'} />
      <div className="ledger">
        {!hasTransfers && <p className="faint">This trace records no ledger transfers.</p>}
        <div ref={ref} className="accounts" style={{ '--n': n, paddingTop: hasTransfers ? 44 : 0 } as React.CSSProperties}>
          {hasTransfers && width > 0 && (
            <svg className="flows" width={width} height={44} style={{ height: 44 }} aria-hidden="true">
              <defs>
                {['live', 'past'].map((k) => (
                  <marker key={k} id={`arrow-${k}`} viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                    <path d="M0 0 L6 3 L0 6 z" fill={k === 'live' ? 'var(--fg)' : 'var(--fg-3)'} stroke="none" />
                  </marker>
                ))}
              </defs>
              {state.transfers.map((t, i) => {
                const a = col(t.payer), b = col(t.payee);
                if (a < 0 || b < 0 || a === b) return null;
                const x1 = x(a), x2 = x(b);
                const h = 12 + Math.abs(b - a) * 8 + (i % 2) * 5;
                const y = 42;
                const d = `M ${x1} ${y} C ${x1} ${y - h}, ${x2} ${y - h}, ${x2} ${y - 2}`;
                const live = t.seq === state.cursor;
                const len = Math.abs(x2 - x1) + h * 2;
                return (
                  <g key={`${t.transfer_id}:${live}`} className={live ? 'live' : 'past'}>
                    <path d={d} style={{ '--len': len } as React.CSSProperties} markerEnd={`url(#arrow-${live ? 'live' : 'past'})`} />
                    <text x={(x1 + x2) / 2} y={y - h * 0.75 - 4} textAnchor="middle">
                      {t.amount}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
          {groups.map((g) => {
            const delta = g.members.reduce((s, m) => s + m.delta, 0);
            const initial = g.members.every((m) => m.initial !== undefined) ? g.members.reduce((s, m) => s + (m.initial ?? 0), 0) : undefined;
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
        {final.utilities &&
          Object.keys(final.utilities.values).map((agent) => {
            const u = state.utilities?.values[agent];
            if (!u || !state.utilities) {
              return (
                <p className="utility" key={agent}>
                  <span><span className="num">{agent}</span> utility</span>
                  <span className="muted">revealed at event {utilityEvent}</span>
                </p>
              );
            }
            return (
              <p className="utility" key={agent}>
                <span><span className="num">{agent}</span> utility</span>
                <Seq seq={state.utilities.seq} onInspect={onInspect} label={`${agent} utility ${u.utility}`}>
                  <Num value={u.utility} signed tone="auto" className="eq" />
                </Seq>
                <span>
                  = cash <Num value={u.cash_delta} signed /> + external <Num value={u.external_benefit} /> − effort <Num value={u.noncash_effort_cost} />
                </span>
              </p>
            );
          })}
      </div>
    </div>
  );
}
