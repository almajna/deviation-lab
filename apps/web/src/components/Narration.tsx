import { useContext } from 'react';
import { InstantContext } from '../lib/hooks';
import type { Narration as N, Segment } from '../trace/narrate';
import { fmt } from '../trace/narrate';
import type { TraceEvent } from '../trace/types';

interface Props {
  narration: N;
  event?: TraceEvent;
  total: number;
  onInspect: () => void;
}

export function Narration({ narration, event, total, onInspect }: Props) {
  const key = event ? event.seq : 'open';
  const instant = useContext(InstantContext);
  return (
    <section className={`narration${instant ? ' instant' : ''}`} aria-live="polite" aria-atomic="true">
      <div className="meta">
        {event ? (
          <>
            <span>
              <b>{String(event.seq + 1).padStart(2, '0')}</b> / {String(total).padStart(2, '0')}
            </span>
            <span>t{event.time_step}</span>
            <span>{event.actor}</span>
            <span>{event.visibility === 'PUBLIC' ? 'public at the time' : 'revealed after settlement'}</span>
          </>
        ) : (
          <span>
            <b>00</b> / {String(total).padStart(2, '0')}
          </span>
        )}
      </div>
      <h1 key={`h${key}`} className="line-enter">
        {narration.headline.map((s, i) => <Seg key={i} s={s} />)}
      </h1>
      <p key={`p${key}`} className="line-enter" style={{ animationDelay: '60ms' }}>
        {narration.detail}
      </p>
      {event && (
        <button type="button" className="source" onClick={onInspect}>
          View source event {event.seq}
        </button>
      )}
    </section>
  );
}

function Seg({ s }: { s: Segment }) {
  if (typeof s === 'string') return <>{s}</>;
  const shown = Number.isInteger(s.n) ? fmt(s.n, s.signed) : s.n.toFixed(2);
  return <span className={['num', s.tone].filter(Boolean).join(' ')}>{shown}</span>;
}
