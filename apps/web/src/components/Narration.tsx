import { useContext, useEffect, useId, useState } from 'react';
import { InstantContext } from '../lib/hooks';
import type { Narration as N, Segment } from '../trace/narrate';
import { exact, fmt } from '../trace/narrate';
import type { TraceEvent } from '../trace/types';

interface Props {
  narration: N;
  event?: TraceEvent;
  /** 'open' before the first event, 'event' during, 'end' on the closing frame. */
  frame: 'open' | 'event' | 'end';
  onInspect: () => void;
}

/** The caption of the current scene: one idea, in plain language; technical detail on request. */
export function Narration({ narration, event, frame, onInspect }: Props) {
  const key = event ? event.seq : frame;
  const instant = useContext(InstantContext);
  const [more, setMore] = useState(false);
  const noteId = useId();
  useEffect(() => setMore(false), [key]);

  return (
    <section className={`narration${instant ? ' instant' : ''}`} data-frame={frame} aria-live="polite" aria-atomic="true">
      {frame === 'open' ? (
        <>
          <h1 className="title">LLM Prediction Markets</h1>
          <p className="subtitle">An interactive laboratory for the economics of AI compute.</p>
          <p key="lead" className="lead line-enter">{narration.headline.map((s, i) => <Seg key={i} s={s} />)}</p>
        </>
      ) : (
        <>
          <h1 key={`h${key}`} className="line-enter">{narration.headline.map((s, i) => <Seg key={i} s={s} />)}</h1>
        </>
      )}
      {narration.points && (
        <ul key={`l${key}`} className="findings line-enter">
          {narration.points.map((p, i) => <li key={i}>{p.map((s, j) => <Seg key={j} s={s} />)}</li>)}
        </ul>
      )}
      <p key={`p${key}`} className="detail line-enter">{keep(narration.detail)}</p>
      <div className="aside">
        {narration.note && (
          <button type="button" className="disclose" aria-expanded={more} aria-controls={noteId} onClick={() => setMore((m) => !m)}>
            <span>{more ? 'Less detail' : 'More detail'}</span>
          </button>
        )}
        {event && (
          <button type="button" className="disclose" onClick={onInspect}>
            <span>Source: event {event.seq + 1}</span>
          </button>
        )}
      </div>
      {narration.note && (
        <p id={noteId} className="note-text" hidden={!more}>
          {narration.note}
        </p>
      )}
    </section>
  );
}

/** Identifiers such as agent-1 never break across lines (U+2011 non-breaking hyphen). */
const keep = (s: string) => s.replace(/([a-z_])-(\d)/gi, '$1\u2011$2');

function Seg({ s }: { s: Segment }) {
  if (typeof s === 'string') return <>{keep(s)}</>;
  const shown = s.exact || !Number.isInteger(s.n) ? exact(s.n) : fmt(s.n, s.signed);
  return <span className={['num', s.tone].filter(Boolean).join(' ')}>{shown}</span>;
}
