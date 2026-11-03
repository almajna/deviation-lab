import { Component, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { BUNDLED } from './data/fixtures';
import { format, InstantContext, useHashRoute, useMediaQuery, type Route } from './lib/hooks';
import { Inspector, type InspectTarget } from './components/Inspector';
import { Narration } from './components/Narration';
import { Player, SPEEDS } from './components/Player';
import { TraceBar } from './components/TraceBar';
import { Scene } from './scene/Scene';
import { narrate, narrateEnd, narrateOpening } from './trace/narrate';
import { endOf, replayAt } from './trace/replay';
import type { TraceBundle } from './trace/types';
import { Evolution, Theater } from './views/Unavailable';

/** Base dwell per frame at 1×. Settlement and the closing frame hold longer: they are the turns of the story. */
const DWELL_MS = 2600;

export function App() {
  const [route, setRoute] = useHashRoute();
  const [loaded, setLoaded] = useState<TraceBundle[]>([]);
  const bundles = useMemo(() => [...BUNDLED, ...loaded], [loaded]);
  const bundle = bundles.find((b) => b.id === route.trace) ?? bundles[0];
  const n = bundle.trace.events.length;
  const end = endOf(bundle);
  const cursor = Math.max(-1, Math.min(route.t ?? -1, end));
  const wide = useMediaQuery('(min-width: 700px)');

  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [inspect, setInspectRaw] = useState<InspectTarget | null>(null);
  /** Keyboard navigation is repeated rapidly; its state changes land without animation. */
  const [instant, setInstant] = useState(false);
  const setInspect = useCallback((t: InspectTarget | null) => {
    if (t) setPlaying(false); // a modal pauses the film
    setInspectRaw(t);
  }, []);

  // A dialog never outlives the view it was opened on.
  useEffect(() => setInspectRaw(null), [route.view]);

  const go = useCallback((r: Partial<Route>) => setRoute({ ...route, ...r }), [route, setRoute]);
  const seek = useCallback(
    (k: number) => {
      const t = Math.max(-1, Math.min(k, end));
      go({ t: t < 0 ? undefined : t });
    },
    [go, end],
  );

  const state = useMemo(() => replayAt(bundle, cursor), [bundle, cursor]);
  const event = cursor >= 0 && cursor < n ? bundle.trace.events[cursor] : undefined;
  const frame = cursor < 0 ? 'open' : cursor >= end ? 'end' : 'event';
  const narration = event ? narrate(event, state) : frame === 'end' ? narrateEnd(bundle, state) : narrateOpening(bundle, state);
  // The diagram foregrounds the part the current scene is about.
  const focus = !event ? 'all' : event.type === 'ledger_transfer' || event.type === 'utility_summary' ? 'ledger' : 'compute';

  // Playback: advance one frame per dwell; stop on the closing frame.
  useEffect(() => {
    if (!playing || route.view !== 'arena') return;
    if (cursor >= end) {
      setPlaying(false);
      return;
    }
    const next = bundle.trace.events[cursor + 1];
    const hold = next?.type === 'realized_cost_report' || cursor + 1 === end ? 1.5 : cursor < 0 ? 0.4 : 1;
    const id = setTimeout(() => seek(cursor + 1), (DWELL_MS * hold) / speed);
    return () => clearTimeout(id);
  }, [playing, cursor, end, speed, seek, bundle, route.view]);

  const toggle = useCallback(() => {
    if (!playing && cursor >= end) seek(-1);
    setPlaying((p) => !p);
  }, [playing, cursor, end, seek]);

  // Keyboard: Space play/pause, ←/→ step, Home/End, I inspect. One listener reads the latest state
  // through a ref, so keys pressed in quick succession (e.g. right after Esc) are never dropped.
  const keys = useRef({ inspect, toggle, seek, cursor, end, event, view: route.view });
  keys.current = { inspect, toggle, seek, cursor, end, event, view: route.view };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const { inspect, toggle, seek, cursor, end, event, view } = keys.current;
      const el = e.target as HTMLElement;
      if (view !== 'arena' || inspect || e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) return;
      const k = e.key;
      if (k === ' ' && el.tagName !== 'BUTTON' && el.tagName !== 'A') { e.preventDefault(); setInstant(false); toggle(); }
      else if (/^(ArrowRight|ArrowLeft|Home|End)$/.test(k)) {
        e.preventDefault();
        setInstant(true);
        setPlaying(false);
        const t = Math.max(-1, Math.min(end, k === 'ArrowRight' ? cursor + 1 : k === 'ArrowLeft' ? cursor - 1 : k === 'Home' ? -1 : end));
        keys.current.cursor = t; // a second key before re-render continues from here
        seek(t);
      }
      else if ((k === 'i' || k === 'I') && event) setInspect({ kind: 'event', seq: event.seq });
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, [setInspect]);

  const resetToFixture = () => {
    setLoaded([]);
    setPlaying(false);
    go({ view: 'arena', trace: undefined, t: undefined });
  };

  return (
    <>
      {/* Moves focus without touching the URL, so the view and replay position are preserved. */}
      <a
        className="skip-link"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById('main')?.focus();
        }}
      >
        Skip to content
      </a>
      <div className="shell" data-page>
        <header className="masthead">
          <a className="wordmark" href={format({ view: 'arena' })}>LLM Prediction Markets</a>
          <nav className="nav" aria-label="Views">
            <a href={format({ view: 'arena', trace: route.trace })} aria-current={route.view === 'arena' ? 'page' : undefined}><span className="full">Replay</span><span className="short">Replay</span></a>
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

      <main id="main" tabIndex={-1} data-page>
        {route.view === 'arena' && (
          <Recoverable key={bundle.id} onReset={resetToFixture}>
            <InstantContext.Provider value={instant}>
              <div className={`shell arena${instant ? ' instant' : ''}`} onPointerDown={() => setInstant(false)}>
                <div className="film" data-frame={frame}>
                  <Narration narration={narration} event={event} frame={frame} onInspect={() => event && setInspect({ kind: 'event', seq: event.seq })} />
                  <figure className="stage-figure">
                    <Scene state={state} mode={wide ? 'wide' : 'tall'} focus={focus} onInspect={setInspect} />
                    <figcaption className="hint">Select any part of the diagram to see the record behind it.</figcaption>
                  </figure>
                </div>

              </div>
              <Player
                events={bundle.trace.events}
                cursor={cursor}
                playing={playing}
                speed={speed}
                onSeek={(k) => { setPlaying(false); seek(k); }}
                onToggle={toggle}
                onSpeed={(s) => setSpeed(SPEEDS.includes(s) ? s : 1)}
                onInspect={() => event && setInspect({ kind: 'event', seq: event.seq })}
                onData={() => setInspect({ kind: 'figures' })}
              />
            </InstantContext.Provider>
          </Recoverable>
        )}
        {route.view === 'theater' && <Theater />}
        {route.view === 'evolution' && <Evolution />}
      </main>

      <Inspector
        bundle={bundle}
        state={state}
        target={inspect}
        onClose={() => setInspectRaw(null)}
        onSeek={(k) => { setPlaying(false); seek(k); }}
        traceControls={
          <TraceBar
            bundles={bundles}
            current={bundle}
            onSelect={(id) => { setPlaying(false); go({ trace: id, t: undefined }); }}
            onLoad={(b) => { setLoaded((l) => [...l.filter((x) => x.id !== b.id), b]); setPlaying(false); go({ trace: b.id, t: undefined }); }}
            onProvenance={() => setInspect({ kind: 'trace' })}
          />
        }
      />
    </>
  );
}

/** A render failure in a loaded trace leaves the app usable and explains how to recover. */
class Recoverable extends Component<{ children: ReactNode; onReset: () => void }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="shell essay" role="alert">
        <h1>This trace could not be displayed</h1>
        <p className="lede">{this.state.error.message}</p>
        <p style={{ marginTop: 32 }}>
          <button type="button" className="pbtn text bordered" onClick={this.props.onReset}>Return to the bundled fixture</button>
        </p>
      </div>
    );
  }
}
