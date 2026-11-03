import { useEffect, useRef } from 'react';
import type { TraceBundle } from '../trace/types';
import type { InspectTarget } from './Stage';
import { fmt } from '../trace/narrate';

interface Props {
  bundle: TraceBundle;
  target: InspectTarget | null;
  onClose: () => void;
  onSeek: (k: number) => void;
}

export function Inspector({ bundle, target, onClose, onSeek }: Props) {
  const open = target !== null;
  const closeRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<Element | null>(null);

  // Focus moves in on open and returns synchronously on close, so a key pressed immediately after
  // closing never lands on the hidden drawer.
  useEffect(() => {
    if (open) {
      returnFocus.current = document.activeElement;
      closeRef.current?.focus({ preventScroll: true });
    }
  }, [open]);
  const close = () => {
    const back = returnFocus.current;
    if (back instanceof HTMLElement && back !== document.body) back.focus({ preventScroll: true });
    else (document.activeElement as HTMLElement | null)?.blur();
    onClose();
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  });

  return (
    <>
      <div className="scrim" data-open={open} onClick={close} aria-hidden="true" />
      <aside className="inspector" data-open={open} aria-label="Inspector" aria-hidden={!open} {...(open ? {} : { inert: '' })}>
        <header>
          <h2>{title(target)}</h2>
          <button ref={closeRef} type="button" className="tbtn" onClick={close} aria-label="Close inspector">
            <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.4" /></svg>
          </button>
        </header>
        <div className="body">{target && <Body bundle={bundle} target={target} onSeek={(k) => { close(); onSeek(k); }} />}</div>
      </aside>
    </>
  );
}

function title(t: InspectTarget | null) {
  if (!t) return '';
  if (t.kind === 'event') return `Event ${t.seq}`;
  if (t.kind === 'account') return t.id;
  return 'Trace provenance';
}

function Body({ bundle, target, onSeek }: { bundle: TraceBundle; target: InspectTarget; onSeek: (k: number) => void }) {
  const { trace } = bundle;
  if (target.kind === 'event') {
    const e = trace.events[target.seq];
    const isPublic = e.visibility === 'PUBLIC';
    return (
      <>
        <p className="knew">
          {isPublic
            ? 'Public. Participants could see this when they acted.'
            : 'Post-settlement. Revealed only after every decision was final; no participant could act on it.'}
        </p>
        <dl>
          <dt>type</dt><dd className="num">{e.type}</dd>
          <dt>actor</dt><dd className="num">{e.actor}</dd>
          <dt>time step</dt><dd className="num">{e.time_step}</dd>
          <dt>visibility</dt><dd className="num">{e.visibility}</dd>
        </dl>
        <Json value={e} />
        <div className="actions">
          <button type="button" className="tbtn primary" onClick={() => onSeek(e.seq)}>Seek here</button>
          <CopyButton text={JSON.stringify(e, null, 2)} />
        </div>
        <Provenance bundle={bundle} />
      </>
    );
  }
  if (target.kind === 'account') {
    const rows = trace.events.flatMap((e) =>
      e.type === 'ledger_transfer' && (e.payload.payer === target.id || e.payload.payee === target.id)
        ? [{ seq: e.seq, amount: e.payload.payee === target.id ? e.payload.amount : -e.payload.amount, reason: e.payload.reason, other: e.payload.payee === target.id ? e.payload.payer : e.payload.payee }]
        : [],
    );
    const util = trace.events.find((e) => e.type === 'utility_summary');
    const u = util?.type === 'utility_summary' ? util.payload[target.id] : undefined;
    const role = roleOf(bundle, target.id);
    return (
      <>
        <p className="knew">{role}</p>
        <dl>
          {bundle.runConfig?.initial_balances[target.id] !== undefined && (
            <><dt>initial balance</dt><dd className="num">{fmt(bundle.runConfig.initial_balances[target.id])} credits</dd></>
          )}
          {rows.map((r) => (
            <FragmentRow key={r.seq} seq={r.seq} onSeek={onSeek}
              label={r.reason.replace(/_/g, ' ')} value={fmt(r.amount, true)} other={`${r.amount > 0 ? '←' : '→'} ${r.other}`} tone={r.amount > 0 ? 'gain' : 'loss'} />
          ))}
          {u && (
            <><dt>utility</dt><dd><span className="num">{fmt(u.utility, true)}</span> = cash <span className="num">{fmt(u.cash_delta, true)}</span> + external <span className="num">{u.external_benefit}</span> − effort <span className="num">{u.noncash_effort_cost}</span></dd></>
          )}
        </dl>
        {isEconomicAgent(bundle, target.id) && (
          <p className="note">
            This agent's own report and its private signal are not part of the public replay (contract v0.2). Only its post-settlement payoffs are shown. Inspecting private information needs a reviewed viewer-specific extension.
          </p>
        )}
      </>
    );
  }
  return <Provenance bundle={bundle} />;
}

/** Contract v0.2 guarantees a utility receipt for every economic agent and routes fees to the fee sink. */
export function isEconomicAgent(bundle: TraceBundle, id: string) {
  if (bundle.runConfig) return bundle.runConfig.agent_accounts.includes(id);
  return bundle.trace.events.some((e) => e.type === 'utility_summary' && id in e.payload);
}

function roleOf(bundle: TraceBundle, id: string) {
  const c = bundle.runConfig;
  const ev = bundle.trace.events;
  if (isEconomicAgent(bundle, id)) return 'Synthetic economic agent.';
  if (c ? c.maker_account === id : ev.some((e) => e.type === 'ledger_transfer' && e.payload.reason === 'settlement' && e.payload.payer === id)) {
    return 'Market maker: funds settlement payouts from its subsidy.';
  }
  if (c ? c.fee_sink_account === id : ev.some((e) => e.type === 'ledger_transfer' && e.payload.reason === 'action_fee' && e.payload.payee === id)) {
    return 'Fee sink: receives action fees, so nothing is silently burned.';
  }
  return 'Account from the ledger transfers.';
}

function FragmentRow({ seq, label, value, other, tone, onSeek }: { seq: number; label: string; value: string; other: string; tone: string; onSeek: (k: number) => void }) {
  return (
    <>
      <dt><button type="button" className="value-btn num" onClick={() => onSeek(seq)} aria-label={`Seek to event ${seq}`}>event {seq}</button></dt>
      <dd><span className={`num ${tone}`}>{value}</span> <span className="num">{other}</span> <span className="muted">{label}</span></dd>
    </>
  );
}

export function Provenance({ bundle }: { bundle: TraceBundle }) {
  const { trace, annotation } = bundle;
  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <p className="note" style={{ marginTop: 0 }}>
        {bundle.origin === 'SYNTHETIC_FIXTURE'
          ? 'Hand-authored synthetic conformance fixture: the public projection of the approved v0.2 pack. It demonstrates the replay format and accounting identities. It is not simulator output, a mechanism result or a discovered exploit.'
          : 'Loaded from a local file and validated against contract v0.2 in this browser. Provenance hashes are shown as supplied; they are not authenticated here.'}
      </p>
      <dl>
        {bundle.file && (
          <>
            <dt>public file</dt><dd className="num">{bundle.file.path}</dd>
            <dt>file sha256</dt><dd className="num hash">{bundle.file.sha256}</dd>
            <dt>projection of</dt><dd className="num">{bundle.file.source}</dd>
          </>
        )}
        <dt>experiment</dt><dd className="num">{trace.experiment_id}</dd>
        <dt>seed</dt><dd className="num">{trace.seed}</dd>
        <dt>data kind</dt><dd className="num">{trace.data_kind}</dd>
        <dt>agents</dt><dd className="num">{trace.agent_origin}</dd>
        <dt>quality</dt><dd className="num">{trace.quality_semantics}</dd>
        <dt>code revision</dt><dd className="num hash">{trace.provenance.code_revision}</dd>
        <dt>source manifest</dt><dd className="num hash">{trace.provenance.source_manifest_sha256}</dd>
        <dt>split manifest</dt><dd className="num hash">{trace.provenance.split_manifest_sha256}</dd>
        <dt>reservations</dt><dd className="num hash">{trace.reservation_artifact_sha256}</dd>
      </dl>
      {annotation && (
        <div>
          <p className="note" style={{ marginTop: 0 }}>
            Fixture annotation. The budget and task prompts are not fields of the public trace; they are copied from separate public receipts and labelled wherever they appear.
          </p>
          <dl>
            <dt>source</dt><dd className="num">{annotation.source.path}</dd>
            <dt>fields</dt><dd className="num">{annotation.source.fields.join(', ')}</dd>
            <dt>source sha256</dt><dd className="num hash">{annotation.source.sha256}</dd>
          </dl>
        </div>
      )}
    </div>
  );
}

function Json({ value }: { value: unknown }) {
  const text = JSON.stringify(value, null, 2);
  const parts = text.split(/("(?:[^"\\]|\\.)*")(?=:)/g);
  return (
    <pre aria-label="Event JSON">
      {parts.map((p, i) => (i % 2 ? <span key={i} className="k">{p}</span> : p))}
    </pre>
  );
}

function CopyButton({ text }: { text: string }) {
  return (
    <button
      type="button"
      className="tbtn"
      onClick={async (e) => {
        const b = e.currentTarget;
        try {
          await navigator.clipboard.writeText(text);
          b.textContent = 'Copied';
        } catch {
          b.textContent = 'Copy unavailable';
        }
        setTimeout(() => (b.textContent = 'Copy JSON'), 1400);
      }}
    >
      Copy JSON
    </button>
  );
}
