import { useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { InspectTarget } from '../components/Inspector';
import { InstantContext, useReducedMotion } from '../lib/hooks';
import type { ReplayState } from '../trace/replay';
import { fmt } from '../trace/narrate';
import { sceneLayout, type Block, type Mode, type ViewBox } from './layout';

interface Props {
  state: ReplayState;
  mode: Mode;
  /** Which part of the diagram the current scene is about; the rest recedes. */
  focus: 'compute' | 'ledger' | 'all';
  onInspect: (t: InspectTarget) => void;
}

/** A diagram element that opens its source record. Keyboard and pointer accessible. */
function Hit({ target, aria, onInspect, children, className }: { target?: InspectTarget; aria: string; onInspect: Props['onInspect']; children: React.ReactNode; className?: string }) {
  if (!target) return <g className={className}>{children}</g>;
  return (
    <g
      className={`hit ${className ?? ''}`}
      role="button"
      tabIndex={0}
      aria-label={`${aria}. Inspect`}
      onClick={() => onInspect(target)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          e.stopPropagation();
          onInspect(target);
        }
      }}
    >
      {children}
    </g>
  );
}

const tx = (x: number, y: number) => ({ transform: `translate(${x}px, ${y}px)` });

export function Scene({ state, mode, focus, onInspect }: Props) {
  const L = useMemo(() => sceneLayout(state, mode), [state, mode]);
  const instant = useContext(InstantContext);
  const reduce = useReducedMotion();
  const animate = !instant && !reduce;
  // Camera: frame the part the scene is about. Before credits exist, compute fills the frame.
  // On phones, the settlement scene frames the budget bar alone so all its labels fit.
  const settling = !!state.report && state.report.seq === state.cursor;
  const wanted: ViewBox = settling ? L.views.settle : !L.ledgerVisible ? L.views.compute : focus === 'compute' ? L.views.compute : L.views.ledger;
  const view = useCamera(wanted, animate);

  return (
    <svg className="scene" data-mode={mode} data-focus={focus} viewBox={view.join(' ')} preserveAspectRatio="xMidYMid meet" role="group" aria-label="Diagram of the replay at the current position">
      <defs>
 <pattern id="over-hatch" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)">
          <rect className="hatch" width="2.5" height="7" />
        </pattern>
        <marker id="tip" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto">
          <path d="M0 0 L8 4 L0 8 z" fill="currentColor" />
        </marker>
      </defs>

      {/* ── Compute: tasks compete for scarce compute ───────────────── */}
      <g className="part compute">
        {L.heads.filter((h) => h.text !== 'credits').map((h) => (
          <text key={h.text} className="head" x={h.x} y={h.y} textAnchor={h.anchor}>{h.text}</text>
        ))}
        {L.links.map((l) => (
          <Hit key={l.id} target={l.target} aria={`Link ${l.task} to model ${l.model}`} onInspect={onInspect} className="link-hit">
            {/* Forecast weight: a wider stroke for a higher expected reward (quality, not cost). */}
            <path className="link" data-selected={l.selected} data-forecast={l.forecast} d={l.d} pathLength={1} style={l.value !== undefined && !l.selected ? { strokeWidth: 1 + l.value * 5 } : undefined} />
          </Hit>
        ))}
        {L.curves.map((c) => <path key={c.id} className="curve" d={c.d} />)}
        {L.forecastCaption && <text className="note" x={L.forecastCaption.x} y={L.forecastCaption.y} textAnchor="middle">expected reward</text>}
        {L.forecasts.map((f) => (
          <Hit key={f.id} target={f.target} aria={f.aria} onInspect={onInspect}>
            <g className="appear">
              {/* A backing plate so the link line never shows through the label. */}
              <rect className="value-bg" x={f.x - (f.text.length * (mode === 'wide' ? 10.4 : 9.2)) / 2 - 6} y={f.y - 12} width={f.text.length * (mode === 'wide' ? 10.4 : 9.2) + 12} height={24} rx={3} />
              <text className="value" x={f.x} y={f.y + 5} textAnchor="middle">{f.text}</text>
            </g>
          </Hit>
        ))}
        {L.tasks.map((t) => (
          <Hit key={t.id} target={t.target} aria={t.aria} onInspect={onInspect}>
            <g className="node task" data-active={t.active} style={tx(t.x, t.y)}>
              <title>{t.aria}</title>
              <rect x={-7} y={-7} width={14} height={14} />
              <text className="label" x={mode === 'wide' ? -22 : -16} y={5} textAnchor="end">{t.label}</text>
              {t.sub && <text className="sub" x={-22} y={24} textAnchor="end">{t.sub}</text>}
            </g>
          </Hit>
        ))}
        {L.models.map((m) => (
          <g key={m.id} className="node model" data-active={m.active} style={tx(m.x, m.y)} aria-label={m.aria}>
            <circle r={8} />
            <text className="label" x={mode === 'wide' ? 22 : 16} y={5}>{m.label}</text>
          </g>
        ))}

        <text className="caption-label" x={L.caption.x} y={L.caption.y}>{L.caption.label}</text>
        <text className={`caption-value ${L.caption.tone ?? ''}`} x={L.caption.x} y={L.caption.y + 32}>{L.caption.value}</text>
        <rect className="track" x={L.bar.x0} y={L.bar.y} width={L.bar.x1 - L.bar.x0} height={L.bar.h} />
        {L.sealed && L.blocks.length > 0 && <text className="note" x={L.bar.x1} y={L.bar.y + L.bar.h + 18} textAnchor="end">real costs sealed until settlement</text>}
        {L.blocks.map((b) => <ComputeBlock key={b.id} b={b} animate={animate} fresh={b.reserveSeq === state.cursor} onInspect={onInspect} />)}
        {L.budget && (
          <g className="budget-mark" data-note={!!L.budget.note} style={tx(L.budget.x, L.bar.y)}>
            <line y1={-26} y2={L.bar.h + 8} />
            <text x={-8} y={-14} textAnchor="end">{L.budget.label}</text>
            {L.budget.note && <text className="sub" x={-8} y={-30} textAnchor="end">{L.budget.note}</text>}
          </g>
        )}
        {L.excess && (
          <Hit target={L.excess.target} aria={L.excess.text} onInspect={onInspect}>
            <g className="excess appear-late">
              {/* Hatched, not filled: the excess belongs to the total, not to any one task. */}
              <rect className="excess-fill" x={L.excess.x0} y={L.bar.y - 3} width={Math.max(L.excess.x1 - L.excess.x0, 0)} height={L.bar.h + 6} fill="url(#over-hatch)" />
              <path d={`M ${L.excess.x0} ${L.excess.y} H ${L.excess.x1} M ${L.excess.x1} ${L.excess.y} v 8`} />
              <text x={L.excess.x0 + 8} y={L.excess.y - 8}>{L.excess.text}</text>
            </g>
          </Hit>
        )}
      </g>

      {/* ── Credits: who paid whom, and what each agent ends with ──── */}
      {L.ledgerVisible && (
        <g className="part ledger">
          {L.summary && <text className={`summary ${L.summary.tone ?? ''}`} x={L.summary.x} y={L.summary.y}>{L.summary.text}</text>}
          {L.heads.filter((h) => h.text === 'credits').map((h) => (
            <text key={h.text} className="head" x={h.x} y={h.y}>{h.text}</text>
          ))}
          {L.arcs.map((a) => (
            <g key={a.id} className="arc" data-live={a.live}>
              <path d={a.d} markerEnd="url(#tip)" />
              <text className="amount" x={a.label.x} y={a.label.y} textAnchor="middle">{a.label.text}</text>
              {a.live && animate && <Token points={a.points} />}
            </g>
          ))}
          {L.accounts.map((a) => (
            <Hit key={a.id} target={a.target} aria={a.aria} onInspect={onInspect}>
              <g className="account-node appear" style={tx(a.x, a.y)}>
                <text className="label" y={-8} textAnchor="middle">{a.id}</text>
                <text className={`delta ${a.delta > 0 ? 'gain' : a.delta < 0 ? 'loss' : ''}`} y={24} textAnchor="middle">{fmt(a.delta, true)}</text>
                {a.balance !== undefined && <text className="sub" y={44} textAnchor="middle">balance {fmt(a.balance)}</text>}
              </g>
            </Hit>
          ))}
          {L.utility && (
            <Hit target={L.utility.target} aria={L.utility.text} onInspect={onInspect}>
              <g className="utility-line appear">
                <text className={L.utility.tone} x={L.utility.x} y={L.utility.y}>{L.utility.text}</text>
                <text className="sub" x={L.utility.x} y={L.utility.y + 18}>{L.utility.sub}</text>
              </g>
            </Hit>
          )}
        </g>
      )}
    </svg>
  );
}

/** A reserved block of compute. When newly reserved it travels from its link into the bar. */
function ComputeBlock({ b, animate, fresh, onInspect }: { b: Block; animate: boolean; fresh: boolean; onInspect: Props['onInspect'] }) {
  const ref = useRef<SVGGElement>(null);
  useLayoutEffect(() => {
    if (!animate || !fresh || !ref.current) return;
    const dx = b.from.x - b.x - b.base / 2, dy = b.from.y - b.y;
    ref.current.animate(
      [{ transform: `translate(${dx}px, ${dy}px) scale(0.35, 1)`, opacity: 0.2 }, { transform: 'translate(0px, 0px) scale(1, 1)', opacity: 1 }],
      { duration: 720, easing: 'cubic-bezier(0.77, 0, 0.175, 1)' },
    );
    // Only on the frame the reservation happens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fresh]);
  const d = b.label.delta;
  return (
    <Hit target={b.target} aria={b.aria} onInspect={onInspect}>
      <g className="block">
        <g ref={ref} className="block-body" style={{ transformOrigin: `${b.x}px ${b.y}px` }}>
          <rect className="base" x={0} y={b.y} width={1} height={b.h} style={{ transform: `translateX(${b.x}px) scaleX(${Math.max(b.base - 4, 1)})` }} />
          <rect className="over" x={0} y={b.y} width={1} height={b.h} style={{ transform: `translateX(${b.x + b.base}px) scaleX(${b.over})` }} />
        </g>
        {b.reservedW !== undefined && (
          <rect className="reserved-outline" x={b.x} y={b.y - 4} width={Math.max(b.reservedW - 4, 1)} height={b.h + 8} />
        )}
        {b.label.y > b.y + b.h + 30 && <line className="leader" x1={b.label.x} x2={b.label.x} y1={b.y + b.h + 10} y2={b.label.y - 14} />}
        <text className="block-label" style={tx(b.label.x, b.label.y)} textAnchor="middle">{b.label.text}</text>
        {d && <text className={`block-delta ${d.tone}`} style={tx(b.label.x, b.label.y + 16)} textAnchor="middle">{d.text}</text>}
      </g>
    </Hit>
  );
}

/** One token per transfer, carried along the arc from payer to payee. */
function Token({ points }: { points: Array<[number, number]> }) {
  const ref = useRef<SVGCircleElement>(null);
  useLayoutEffect(() => {
    ref.current?.animate(points.map(([x, y]) => ({ transform: `translate(${x}px, ${y}px)` })), { duration: 900, easing: 'cubic-bezier(0.77, 0, 0.175, 1)', fill: 'forwards' });
  }, [points]);
  const [x, y] = points[points.length - 1];
  return <circle ref={ref} className="token" r={5} style={{ transform: `translate(${x}px, ${y}px)` }} />;
}

/** Tween the viewBox between framings (a camera move). Instant under reduced motion or keyboard steps. */
function useCamera(target: ViewBox, animate: boolean): ViewBox {
  const [view, setView] = useState<ViewBox>(target);
  const from = useRef<ViewBox>(target);
  const key = target.join(' ');
  useEffect(() => {
    const start = from.current;
    if (!animate || start.join(' ') === key) {
      from.current = target;
      setView(target);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / 700);
      const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
      const v = start.map((s, i) => s + (target[i] - s) * e) as ViewBox;
      from.current = v;
      setView(v);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, animate]);
  return view;
}
