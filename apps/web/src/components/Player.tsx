import { useLayoutEffect, useRef } from 'react';
import type { TraceEvent } from '../trace/types';
import { settlementIndex } from '../trace/replay';
import { chapterOf } from '../trace/narrate';

interface Props {
  events: TraceEvent[];
  /** -1 before the first event, events.length on the closing frame. */
  cursor: number;
  playing: boolean;
  speed: number;
  onSeek: (k: number) => void;
  onToggle: () => void;
  onSpeed: (s: number) => void;
  onInspect: () => void;
  onData: () => void;
}

export const SPEEDS = [0.5, 1, 2];

/**
 * A compact video-player bar fixed to the bottom edge. One scrubber with a tick per scene (each event
 * plus the opening and closing frames); the dashed tick marks settlement. Ticks reveal only that a
 * scene exists, never its content.
 */
export function Player({ events, cursor, playing, speed, onSeek, onToggle, onSpeed, onInspect, onData }: Props) {
  const n = events.length;
  const frames = n + 2; // opening, events, closing
  const pos = cursor + 1; // 0..n+1
  const atEnd = cursor >= n;
  const boundary = settlementIndex(events) + 1;
  const ref = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  // Publish the bar's height so the page reserves space beneath its content.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const root = document.documentElement;
    const ro = new ResizeObserver(() => root.style.setProperty('--dock-h', `${el.offsetHeight}px`));
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.style.removeProperty('--dock-h');
    };
  }, []);

  const x = (i: number) => `${(i / (frames - 1)) * 100}%`;
  const seekFrom = (clientX: number) => {
    const r = track.current!.getBoundingClientRect();
    onSeek(Math.round(((clientX - r.left) / r.width) * (frames - 1)) - 1);
  };
  const event = cursor >= 0 && cursor < n ? events[cursor] : undefined;
  const frame = cursor < 0 ? 'open' : atEnd ? 'end' : 'event';
  const nextSpeed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];

  return (
    <section ref={ref} className="player" aria-label="Playback">
      <div
        ref={track}
        className="scrubber"
        role="slider"
        tabIndex={0}
        aria-label="Scene"
        aria-valuemin={1}
        aria-valuemax={frames}
        aria-valuenow={pos + 1}
        aria-valuetext={`Scene ${pos + 1} of ${frames}: ${chapterOf(event, frame)}`}
        onKeyDown={(e) => {
          const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
          if (step) {
            e.preventDefault();
            e.stopPropagation();
            onSeek(Math.max(-1, Math.min(n, cursor + step)));
          }
        }}
        onPointerDown={(e) => {
          dragging.current = true;
          e.currentTarget.setPointerCapture(e.pointerId);
          seekFrom(e.clientX);
        }}
        onPointerMove={(e) => dragging.current && seekFrom(e.clientX)}
        onPointerUp={() => (dragging.current = false)}
        onPointerCancel={() => (dragging.current = false)}
      >
        <span className="rail" />
        <span className="fill" style={{ transform: `scaleX(${pos / (frames - 1)})` }} />
        {Array.from({ length: frames }, (_, i) => (
          <i key={i} className="tick" style={{ left: x(i) }} data-seen={i <= pos} data-boundary={i === boundary} />
        ))}
        {boundary > 0 && boundary <= n && (
          <span className="tick-label" style={{ left: x(boundary) }} aria-hidden="true">costs revealed</span>
        )}
        <span className="knob" style={{ left: x(pos) }} />
        <span className="chapter-top" aria-hidden="true">
          <span className="num">{String(pos + 1).padStart(2, '0')}/{String(frames).padStart(2, '0')}</span> {chapterOf(event, frame)}
        </span>
      </div>
      <div className="controls">
        <button type="button" className="pbtn play" onClick={onToggle} aria-label={playing ? 'Pause' : atEnd ? 'Replay from start' : 'Play'}>
          {playing ? <Pause /> : <Play />}
        </button>
        <button type="button" className="pbtn" onClick={() => onSeek(cursor - 1)} disabled={cursor < 0} aria-label="Previous scene">
          <Step back />
        </button>
        <button type="button" className="pbtn" onClick={() => onSeek(cursor + 1)} disabled={atEnd} aria-label="Next scene">
          <Step />
        </button>
        <span className="where">
          <span className="num">{String(pos + 1).padStart(2, '0')}</span>
          <span className="faint"> / {String(frames).padStart(2, '0')}</span>
          <span className="chapter">{chapterOf(event, frame)}</span>
        </span>
        <span className="right">
          <button type="button" className="pbtn text num" onClick={() => onSpeed(nextSpeed)} aria-label={`Speed ${speed}×, change to ${nextSpeed}×`}>
            {speed}×
          </button>
          <button type="button" className="pbtn text" onClick={onData} aria-label="Data: every figure and its source">
            Data
          </button>
          <button type="button" className="pbtn text" onClick={onInspect} disabled={!event} aria-label="Inspect the current event">
            Inspect
          </button>
        </span>
      </div>
    </section>
  );
}

const Play = () => <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.5 2.5v11l9-5.5z" fill="currentColor" /></svg>;
const Pause = () => <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h2.6v10H4zM9.4 3H12v10H9.4z" fill="currentColor" /></svg>;
const Step = ({ back }: { back?: boolean }) => (
  <svg viewBox="0 0 16 16" aria-hidden="true" style={back ? { transform: 'scaleX(-1)' } : undefined}>
    <path d="M4 3v10l7-5z" fill="currentColor" />
    <path d="M12.5 3v10" stroke="currentColor" strokeWidth="1.5" />
  </svg>
);
