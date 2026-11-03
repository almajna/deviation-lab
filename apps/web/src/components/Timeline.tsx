import { useLayoutEffect, useRef } from 'react';
import type { TraceEvent } from '../trace/types';
import { settlementIndex } from '../trace/replay';

interface Props {
  events: TraceEvent[];
  /** -1 before the first event, events.length on the closing frame. */
  cursor: number;
  playing: boolean;
  speed: number;
  /** Phones: one strip instead of actor lanes, larger targets, speed as a single cycling control. */
  compact: boolean;
  onSeek: (k: number) => void;
  onToggle: () => void;
  onSpeed: (s: number) => void;
}

export const SPEEDS = [0.5, 1, 2];

/**
 * Event-pitched timeline. Positions are whole frames: events plus a closing frame. Marks reveal only
 * that an event exists (actor and time step), never its content, until the playhead reaches it.
 */
export function Timeline({ events, cursor, playing, speed, compact, onSeek, onToggle, onSpeed }: Props) {
  const n = events.length;
  const frames = n + 1;
  const end = n;
  const lanes = compact ? ['all'] : [...new Set(events.map((e) => e.actor))];
  const boundary = settlementIndex(events);
  const x = (i: number) => `${((i + 0.5) / frames) * 100}%`;
  const trackRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const dragging = useRef(false);

  // Publish the docked player's height so the page reserves space beneath its content.
  useLayoutEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const root = document.documentElement;
    const ro = new ResizeObserver(() => root.style.setProperty('--dock-h', `${el.offsetHeight}px`));
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.style.removeProperty('--dock-h');
    };
  }, []);

  const seekFromPointer = (clientX: number) => {
    const el = trackRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const k = Math.round(((clientX - r.left) / r.width) * frames - 0.5);
    onSeek(Math.max(0, Math.min(end, k)));
  };
  const firstOfStep = events.filter((e, i) => i === 0 || events[i - 1].time_step !== e.time_step);
  const at = cursor >= 0 && cursor < n ? events[cursor] : undefined;
  const atEnd = cursor >= end;
  const label = playing ? 'Pause' : atEnd ? 'Replay' : 'Play';
  const nextSpeed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];

  return (
    <section ref={sectionRef} className="timeline docked" data-compact={compact} aria-label="Replay timeline">
      <div className="transport" role="toolbar" aria-label="Playback">
        <button type="button" className="tbtn primary" onClick={onToggle} aria-label={playing ? 'Pause' : atEnd ? 'Replay from start' : 'Play'}>
          {playing ? <PauseIcon /> : <PlayIcon />}
          <span>{label}</span>
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(-1)} disabled={cursor < 0} aria-label="Rewind to start">
          <StartIcon />
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(cursor - 1)} disabled={cursor < 0} aria-label="Step back">
          <StepIcon back />
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(cursor + 1)} disabled={atEnd} aria-label="Step forward">
          <StepIcon />
        </button>
        <span className="sep" aria-hidden="true" />
        {compact ? (
          <button type="button" className="tbtn speed num" onClick={() => onSpeed(nextSpeed)} aria-label={`Speed ${speed}×, change to ${nextSpeed}×`}>
            {speed}×
          </button>
        ) : (
          <span role="group" aria-label="Speed" style={{ display: 'inline-flex' }}>
            {SPEEDS.map((s) => (
              <button key={s} type="button" className="tbtn speed num" aria-pressed={speed === s} onClick={() => onSpeed(s)}>
                {s}×
              </button>
            ))}
          </span>
        )}
        <span className="position num" aria-hidden="true">
          {cursor < 0 ? 'start' : atEnd ? 'end' : `${String(cursor + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}`}
        </span>
        {!compact && (
          <div className="legend" aria-hidden="true">
            <span><i className="seen" />seen</span>
            <span><i />upcoming</span>
            <span><i className="dash" />public | revealed</span>
          </div>
        )}
      </div>

      {!compact && (
        <div className="lanes-ruler" aria-hidden="true">
          <span />
          <span className="ruler">
            {firstOfStep.map((e) => (
              <span key={e.seq} style={{ left: x(e.seq) }}>
                t{e.time_step}
              </span>
            ))}
            <span style={{ left: x(end) }}>end</span>
          </span>
        </div>
      )}
      <div className="lanes">
        {lanes.map((actor) => (
          <div className="lane" key={actor}>
            {!compact && <span title={actor}>{actor}</span>}
            <span className="lane-track">
              {events.map((e, i) =>
                compact || e.actor === actor ? (
                  <i
                    key={i}
                    className="frame"
                    style={{ left: x(i) }}
                    data-seen={i <= cursor}
                    data-current={i === cursor}
                    data-tone={i <= cursor && e.type === 'realized_cost_report' && e.payload.realized_budget_violated ? 'loss' : undefined}
                  />
                ) : null,
              )}
              {(compact || actor === lanes[lanes.length - 1]) && (
                <i className="frame end" style={{ left: x(end) }} data-seen={atEnd} data-current={atEnd} />
              )}
            </span>
          </div>
        ))}
        <div className="lanes-overlay">
          {!compact && <span />}
          <div
            ref={trackRef}
            role="slider"
            tabIndex={0}
            aria-label="Replay position"
            aria-valuemin={0}
            aria-valuemax={frames}
            aria-valuenow={cursor + 1}
            aria-valuetext={at ? `Event ${at.seq + 1} of ${n}: ${at.type.replace(/_/g, ' ')}` : atEnd ? 'Closing summary' : 'Before the first event'}
            onKeyDown={(e) => {
              const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
              if (step) {
                e.preventDefault();
                e.stopPropagation();
                onSeek(Math.max(-1, Math.min(end, cursor + step)));
              }
            }}
            onPointerDown={(e) => {
              dragging.current = true;
              e.currentTarget.setPointerCapture(e.pointerId);
              seekFromPointer(e.clientX);
            }}
            onPointerMove={(e) => dragging.current && seekFromPointer(e.clientX)}
            onPointerUp={() => (dragging.current = false)}
            onPointerCancel={() => (dragging.current = false)}
            className="scrub-area"
          >
            {boundary > 0 && boundary < n && (
              <span className="boundary" style={{ left: `${(boundary / frames) * 100}%` }}>
                <span>settlement</span>
              </span>
            )}
            <span className="playhead" style={{ transform: `translateX(${cursor < 0 ? 0 : ((cursor + 0.5) / frames) * 100}%)` }} />
          </div>
        </div>
      </div>
    </section>
  );
}

const PlayIcon = () => (
  <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 2.2v9.6L11.5 7z" fill="currentColor" /></svg>
);
const PauseIcon = () => (
  <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 2.5h2.2v9H3.5zM8.3 2.5h2.2v9H8.3z" fill="currentColor" /></svg>
);
/** Rewind: a bar and two triangles, so it never reads as a single step. */
const StartIcon = () => (
  <svg viewBox="0 0 16 14" aria-hidden="true" style={{ width: 16 }}><path d="M2 2.5v9" stroke="currentColor" strokeWidth="1.4" /><path d="M8.5 2.5v9L3.5 7zM14 2.5v9L9 7z" fill="currentColor" /></svg>
);
const StepIcon = ({ back }: { back?: boolean }) => (
  <svg viewBox="0 0 14 14" aria-hidden="true" style={back ? { transform: 'scaleX(-1)' } : undefined}>
    <path d="M3 2.5v9L9 7z" fill="currentColor" /><path d="M11 2.5v9" stroke="currentColor" strokeWidth="1.4" />
  </svg>
);
