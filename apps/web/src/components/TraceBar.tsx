import { useRef, useState } from 'react';
import type { TraceBundle } from '../trace/types';
import { bundleFromJson, TraceError } from '../trace/validate';

interface Props {
  bundles: TraceBundle[];
  current: TraceBundle;
  onSelect: (id: string) => void;
  onLoad: (b: TraceBundle) => void;
  onProvenance: () => void;
}

export function TraceBar({ bundles, current, onSelect, onLoad, onProvenance }: Props) {
  const file = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const download = () => {
    const blob = new Blob([JSON.stringify(current.trace, null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${current.trace.experiment_id}.seed-${current.trace.seed}.trace.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="tracebar" aria-label="Trace">
      <label>
        <span className="sr-only">Trace</span>
        <select value={current.id} onChange={(e) => onSelect(e.target.value)} aria-label="Select trace">
          {bundles.map((b) => (
            <option key={b.id} value={b.id}>
              {b.label}
            </option>
          ))}
        </select>
      </label>
      <span className="num faint">seed {current.trace.seed}</span>
      <span className="spacer" />
      <button type="button" className="link" onClick={onProvenance}>Provenance</button>
      <button type="button" className="link" onClick={download} title="The complete audit record, including post-settlement events">Download complete trace</button>
      <button type="button" className="link" onClick={() => file.current?.click()}>Load trace</button>
      <input
        ref={file}
        type="file"
        accept="application/json,.json"
        hidden
        aria-label="Load a v0.2 completed trace JSON file"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          e.target.value = '';
          if (!f) return;
          try {
            onLoad(bundleFromJson(JSON.parse(await f.text()), f.name));
            setError(null);
          } catch (err) {
            const msg = err instanceof TraceError ? err.message : err instanceof SyntaxError ? 'not valid JSON' : String(err);
            setError(`${f.name} was not loaded: ${msg}. Only contract v0.2 completed traces are supported.`);
          }
        }}
      />
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
