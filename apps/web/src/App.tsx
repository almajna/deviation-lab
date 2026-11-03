import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BUNDLED } from './data/fixtures';
import { format, InstantContext, useHashRoute, type Route } from './lib/hooks';
import { Inspector } from './components/Inspector';
import { Narration } from './components/Narration';
import { Stage, type InspectTarget } from './components/Stage';
import { SPEEDS, Timeline } from './components/Timeline';
import { TraceBar } from './components/TraceBar';
import { narrate, narrateOpening } from './trace/narrate';
import { replayAt } from './trace/replay';
import type { TraceBundle } from './trace/types';
import { Evolution, Theater } from './views/Unavailable';

/** Base dwell per event at 1×. Settlement holds longer: it is the turn of the story. */
const DWELL_MS = 2600;

export function App() {
  const [route, setRoute] = useHashRoute();
  const [loaded, setLoaded] = useState<TraceBundle[]>([]);
  const bundles = useMemo(() => [...BUNDLED, ...loaded], [loaded]);
  const bundle = bundles.find((b) => b.id === route.trace) ?? bundles[0];
  const n = bundle.trace.events.length;
  const cursor = Math.max(-1, Math.min(route.t ?? -1, n - 1));

  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [inspect, setInspect] = useState<InspectTarget | null>(null);
  /** Keyboard navigation is repeated rapidly; its state changes land without animation. */
  const [instant, setInstant] = useState(false);

  const go = useCallback((r: Partial<Route>) => setRoute({ ...route, ...r }), [route, setRoute]);
  const seek = useCallback(
    (k: number) => {
      const t = Math.max(-1, Math.min(k, n - 1));
      go({ t: t < 0 ? undefined : t });
    },
    [go, n],
  );

  const state = useMemo(() => replayAt(bundle, cursor), [bundle, cursor]);
  const final = useMemo(() => replayAt(bundle, n - 1), [bundle, n]);
  const event = cursor >= 0 ? bundle.trace.events[cursor] : undefined;
  const narration = event ? narrate(event, state) : narrateOpening(bundle, state);

  // Playback: advance one whole event per dwell; stop at the end.
  useEffect(() => {
    if (!playing || route.view !== 'arena') return;
    if (cursor >= n - 1) {
      setPlaying(false);
      return;
    }
    const next = bundle.trace.events[cursor + 1];
    const hold = next?.type === 'realized_cost_report' ? 1.5 : cursor < 0 ? 0.4 : 1;
    const id = setTimeout(() => seek(cursor + 1), (DWELL_MS * hold) / speed);
    return () => clearTimeout(id);
  }, [playing, cursor, n, speed, seek, bundle, route.view]);

  const toggle = useCallback(() => {
    if (!playing && cursor >= n - 1) seek(-1);
    setPlaying((p) => !p);
  }, [playing, cursor, n, seek]);

  // Keyboard: Space play/pause, ←/→ step, Home/End, I inspect. One listener reads the latest state
  // through a ref, so keys pressed in quick succession (e.g. right after Esc) are never dropped.
  const keys = useRef({ inspect, toggle, seek, cursor, n, event, view: route.view });
  keys.current = { inspect, toggle, seek, cursor, n, event, view: route.view };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const { inspect, toggle, seek, cursor, n, event, view } = keys.current;
      const el = e.target as HTMLElement;
      if (view !== 'arena' || inspect || e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) return;
      const k = e.key;
      if (/^(ArrowLeft|ArrowRight|Home|End)$/.test(k)) setInstant(true);
      if (k === ' ' && el.tagName !== 'BUTTON') { e.preventDefault(); setInstant(false); toggle(); }
      else if (/^(ArrowRight|ArrowLeft|Home|End)$/.test(k)) {
        e.preventDefault();
        setPlaying(false);
        const t = Math.max(-1, Math.min(n - 1, k === 'ArrowRight' ? cursor + 1 : k === 'ArrowLeft' ? cursor - 1 : k === 'Home' ? -1 : n - 1));
        keys.current.cursor = t; // a second key before re-render continues from here
        seek(t);
      }
      else if ((k === 'i' || k === 'I') && event) setInspect({ kind: 'event', seq: event.seq });
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <a className="sr-only" href="#main">Skip to content</a>
      <div className="shell">
        <header className="masthead">
          <a className="wordmark" href={format({ view: 'arena' })}>DEVIATION</a>
          <nav className="nav" aria-label="Views">
            <a href={format({ view: 'arena', trace: route.trace })} aria-current={route.view === 'arena' ? 'page' : undefined}><span className="full">Market Arena</span><span className="short">Arena</span></a>
            <a href={format({ view: 'theater', trace: route.trace })} aria-current={route.view === 'theater' ? 'page' : undefined}><span className="full">Exploit Theater</span><span className="short">Theater</span></a>
            <a href={format({ view: 'evolution', trace: route.trace })} aria-current={route.view === 'evolution' ? 'page' : undefined}><span className="full">Mechanism Evolution</span><span className="short">Evolution</span></a>
          </nav>
          <button type="button" className="provenance" onClick={() => { go({ view: 'arena' }); setInspect({ kind: 'trace' }); }}
            aria-label={`Data provenance: ${bundle.origin === 'SYNTHETIC_FIXTURE' ? 'synthetic fixture, not a result' : 'loaded file'}. Inspect`}>
            <i aria-hidden="true" />
            <strong>{bundle.trace.data_kind === 'SYNTHETIC' ? 'Synthetic' : 'Recorded outcomes'}</strong>
            <span className="long">{bundle.origin === 'SYNTHETIC_FIXTURE' ? <>fixture<span className="rest"> · not a result</span></> : 'loaded file'}</span>
          </button>
        </header>
      </div>

      <main id="main">
        {route.view === 'arena' && (
          <InstantContext.Provider value={instant}>
            <div className="shell arena" onPointerDown={() => setInstant(false)}>
              <Narration narration={narration} event={event} total={n} onInspect={() => event && setInspect({ kind: 'event', seq: event.seq })} />
              <Stage bundle={bundle} state={state} final={final} onInspect={setInspect} />
              <Timeline
                events={bundle.trace.events}
                cursor={cursor}
                playing={playing}
                speed={speed}
                onSeek={(k) => { setPlaying(false); seek(k); }}
                onToggle={toggle}
                onSpeed={(s) => setSpeed(SPEEDS.includes(s) ? s : 1)}
              />
              <TraceBar
                bundles={bundles}
                current={bundle}
                onSelect={(id) => { setPlaying(false); go({ trace: id, t: undefined }); }}
                onLoad={(b) => { setLoaded((l) => [...l.filter((x) => x.id !== b.id), b]); setPlaying(false); go({ trace: b.id, t: undefined }); }}
                onProvenance={() => setInspect({ kind: 'trace' })}
              />
            </div>
          </InstantContext.Provider>
        )}
        {route.view === 'theater' && <Theater />}
        {route.view === 'evolution' && <Evolution />}
      </main>

      <div className="shell">
        <footer className="footer">
          <span>Contract v0.2 completed-trace consumer</span>
          <span>Forecasts are expected judged-preference reward, not probability of correctness</span>
          <span>Costs and credits are separate units and are never combined</span>
        </footer>
      </div>

      <Inspector bundle={bundle} target={inspect} onClose={() => setInspect(null)} onSeek={(k) => { setInspect(null); setPlaying(false); seek(k); }} />
    </>
  );
}
