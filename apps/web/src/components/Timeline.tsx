import { useLayoutEffect, useRef } from 'react';
import type { TraceEvent } from '../trace/types';
import { settlementIndex } from '../trace/replay';

interface Props {
  events: TraceEvent[];
  cursor: number;
  playing: boolean;
  speed: number;
  onSeek: (k: number) => void;
  onToggle: () => void;
  onSpeed: (s: number) => void;
}

export const SPEEDS = [0.5, 1, 2];

/** Event-pitched timeline: one lane per actor, the playhead lands only on whole events. */
export function Timeline({ events, cursor, playing, speed, onSeek, onToggle, onSpeed }: Props) {
  const n = events.length;
  const lanes = [...new Set(events.map((e) => e.actor))];
  const boundary = settlementIndex(events);
  const x = (i: number) => `${((i + 0.5) / n) * 100}%`;
  const trackRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  // Publish the docked player's height so the page can reserve space beneath its content.
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
  const dragging = useRef(false);

  const seekFromPointer = (clientX: number) => {
    const el = trackRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const k = Math.round(((clientX - r.left) / r.width) * n - 0.5);
    onSeek(Math.max(0, Math.min(n - 1, k)));
  };
  const firstOfStep = events.filter((e, i) => i === 0 || events[i - 1].time_step !== e.time_step);
  const at = cursor >= 0 ? events[cursor] : undefined;

  return (
    <section ref={sectionRef} className="timeline docked" aria-label="Replay timeline">
      <div className="transport" role="toolbar" aria-label="Playback">
        <button type="button" className="tbtn primary" onClick={onToggle} aria-label={playing ? 'Pause' : cursor >= n - 1 ? 'Replay from start' : 'Play'}>
          {playing ? <PauseIcon /> : <PlayIcon />}
          <span>{playing ? 'Pause' : cursor >= n - 1 ? 'Replay' : 'Play'}</span>
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(-1)} disabled={cursor < 0} aria-label="Rewind to start">
          <StartIcon />
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(cursor - 1)} disabled={cursor < 0} aria-label="Step back">
          <StepIcon back />
        </button>
        <button type="button" className="tbtn" onClick={() => onSeek(cursor + 1)} disabled={cursor >= n - 1} aria-label="Step forward">
          <StepIcon />
        </button>
        <span className="sep" aria-hidden="true" />
        <span role="group" aria-label="Speed" style={{ display: 'inline-flex' }}>
          {SPEEDS.map((s) => (
            <button key={s} type="button" className="tbtn speed num" aria-pressed={speed === s} onClick={() => onSpeed(s)}>
              {s}×
            </button>
          ))}
        </span>
        <div className="legend" aria-hidden="true">
          <span><i className="seen" />seen</span>
          <span><i />upcoming</span>
          <span><i className="dash" />settlement: left was public at decision time, right was revealed afterwards</span>
        </div>
      </div>

      <div className="lanes-ruler" aria-hidden="true">
        <span />
        <span className="ruler">
          {firstOfStep.map((e) => (
            <span key={e.seq} style={{ left: x(e.seq) }}>
              t{e.time_step}
            </span>
          ))}
        </span>
      </div>
      <div className="lanes">
        {lanes.map((actor) => (
          <div className="lane" key={actor}>
            <span title={actor}>{actor}</span>
            <span className="lane-track">
              {events.map((e, i) =>
                e.actor === actor ? (
                  <i
                    key={i}
                    className="frame"
                    style={{ left: x(i) }}
                    data-seen={i <= cursor}
                    data-current={i === cursor}
                    data-tone={e.type === 'realized_cost_report' && e.payload.realized_budget_violated ? 'loss' : undefined}
                  />
                ) : null,
              )}
            </span>
          </div>
        ))}
        <div style={{ position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: 'var(--lane-label, 168px) 1fr', columnGap: 'var(--lane-gap, 24px)' }} className="lanes-overlay">
          <span />
          <div
            ref={trackRef}
            style={{ position: 'relative' }}
            role="slider"
            tabIndex={0}
            aria-label="Replay position"
            aria-valuemin={0}
            aria-valuemax={n}
            aria-valuenow={cursor + 1}
            aria-valuetext={at ? `Event ${at.seq} of ${n}: ${at.type.replace(/_/g, ' ')}` : 'Before the first event'}
            onKeyDown={(e) => {
              const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
              if (step) {
                e.preventDefault();
                e.stopPropagation();
                onSeek(Math.max(-1, Math.min(n - 1, cursor + step)));
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
              <span className="boundary" style={{ left: `${(boundary / n) * 100}%` }}>
                <span>settlement</span>
              </span>
            )}
            <span
              className="playhead"
              style={{ transform: `translateX(${cursor < 0 ? 0 : ((cursor + 0.5) / n) * 100}%)` }}
            />
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
const StartIcon = () => (
  <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2.5v9" stroke="currentColor" strokeWidth="1.4" /><path d="M11.5 2.5v9L5 7z" fill="currentColor" /></svg>
);
const StepIcon = ({ back }: { back?: boolean }) => (
  <svg viewBox="0 0 14 14" aria-hidden="true" style={back ? { transform: 'scaleX(-1)' } : undefined}>
    <path d="M3 2.5v9L9 7z" fill="currentColor" /><path d="M11 2.5v9" stroke="currentColor" strokeWidth="1.4" />
  </svg>
);
