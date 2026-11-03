import { useEffect, useId, useRef } from 'react';
import type { ReplayState } from '../trace/replay';
import type { TraceBundle } from '../trace/types';
import type { InspectTarget } from './Stage';
import { fmt } from '../trace/narrate';

interface Props {
  bundle: TraceBundle;
  /** The inspector shows only what is known at the current position, exactly like the stage. */
  state: ReplayState;
  target: InspectTarget | null;
  onClose: () => void;
  onSeek: (k: number) => void;
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal dialog: focus moves in on open, Tab is contained, Escape and the scrim close it, the page
 * behind is inert, and focus returns to the trigger synchronously on close.
 */
export function Inspector({ bundle, state, target, onClose, onSeek }: Props) {
  const open = target !== null;
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement;
    closeRef.current?.focus({ preventScroll: true });
    const background = [...document.querySelectorAll<HTMLElement>('[data-page]')];
    background.forEach((el) => el.setAttribute('inert', ''));
    return () => background.forEach((el) => el.removeAttribute('inert'));
  }, [open]);

  const close = () => {
    document.querySelectorAll<HTMLElement>('[data-page]').forEach((el) => el.removeAttribute('inert'));
    const back = returnFocus.current;
    if (back instanceof HTMLElement && back !== document.body && back.isConnected) back.focus({ preventScroll: true });
    else (document.activeElement as HTMLElement | null)?.blur();
    onClose();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
      return;
    }
    if (e.key !== 'Tab') return;
    const items = [...(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])];
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };

  return (
    <>
      <div className="scrim" data-open={open} onClick={close} aria-hidden="true" />
      <div
        ref={dialogRef}
        className="inspector"
        data-open={open}
        {...(open ? { role: 'dialog', 'aria-modal': true, 'aria-labelledby': titleId } : { 'aria-hidden': true, inert: '' })}
        onKeyDown={onKeyDown}
      >
        <header>
          <h2 id={titleId}>{title(target)}</h2>
          <button ref={closeRef} type="button" className="tbtn" onClick={close} aria-label="Close inspector">
            <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.4" /></svg>
          </button>
        </header>
        <div className="body">{target && <Body bundle={bundle} state={state} target={target} onSeek={(k) => { close(); onSeek(k); }} />}</div>
      </div>
    </>
  );
}

function title(t: InspectTarget | null) {
  if (!t) return '';
  if (t.kind === 'event') return `Event ${t.seq + 1}`;
  if (t.kind === 'account') return t.id;
  return 'Trace provenance';
}

function Body({ bundle, state, target, onSeek }: { bundle: TraceBundle; state: ReplayState; target: InspectTarget; onSeek: (k: number) => void }) {
  const { trace } = bundle;
  if (target.kind === 'event') {
    // Only events at or before the current position can be shown.
    if (target.seq > state.applied) return <p className="knew">This event has not happened yet at the current position.</p>;
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
          <dt>sequence</dt><dd className="num">{e.seq}</dd>
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
    // Transfers and utility as of the current position; nothing later.
    const rows = state.transfers
      .filter((t) => t.payer === target.id || t.payee === target.id)
      .map((t) => ({ seq: t.seq, amount: t.payee === target.id ? t.amount : -t.amount, reason: t.reason, other: t.payee === target.id ? t.payer : t.payee }));
    const u = state.utilities?.values[target.id];
    const account = state.accounts.find((a) => a.id === target.id);
    const agent = isEconomicAgent(bundle, state, target.id);
    return (
      <>
        <p className="knew">{roleOf(bundle, state, target.id)}</p>
        <dl>
          {account?.initial !== undefined && (
            <><dt>initial balance</dt><dd className="num">{fmt(account.initial)} credits (run configuration)</dd></>
          )}
          {rows.map((r) => (
            <FragmentRow key={r.seq} seq={r.seq} onSeek={onSeek}
              label={r.reason.replace(/_/g, ' ')} value={fmt(r.amount, true)} other={`${r.amount > 0 ? '←' : '→'} ${r.other}`} tone={r.amount > 0 ? 'gain' : 'loss'} />
          ))}
          {account && <><dt>net so far</dt><dd className="num">{fmt(account.delta, true)} credits</dd></>}
          {u && (
            <><dt>utility</dt><dd><span className="num">{fmt(u.utility, true)}</span> <span className="nowrap">= cash <span className="num">{fmt(u.cash_delta, true)}</span></span> <span className="nowrap">+ external <span className="num">{u.external_benefit}</span></span> <span className="nowrap">− effort <span className="num">{u.noncash_effort_cost}</span></span></dd></>
          )}
        </dl>
        {agent && !u && <p className="note">Utility is reported at the end of settlement.</p>}
        {agent && (
          <p className="note">
            This agent's own report and private signal are not part of the public replay (contract v0.2). Inspecting private information needs a reviewed viewer-specific extension.
          </p>
        )}
      </>
    );
  }
  return <Provenance bundle={bundle} />;
}

/** Roles from the trusted configuration, else from what the known events establish. */
function isEconomicAgent(bundle: TraceBundle, state: ReplayState, id: string) {
  if (bundle.runConfig) return bundle.runConfig.agent_accounts.includes(id);
  return !!state.utilities && id in state.utilities.values || state.transfers.some((t) => t.reason === 'action_fee' && t.payer === id);
}

function roleOf(bundle: TraceBundle, state: ReplayState, id: string) {
  const c = bundle.runConfig;
  if (isEconomicAgent(bundle, state, id)) return 'Synthetic economic agent.';
  if (c ? c.maker_account === id : state.transfers.some((t) => t.reason === 'settlement' && t.payer === id)) {
    return 'Market maker: funds settlement payouts from its subsidy.';
  }
  if (c ? c.fee_sink_account === id : state.transfers.some((t) => t.reason === 'action_fee' && t.payee === id)) {
    return 'Fee sink: receives action fees, so nothing is silently burned.';
  }
  return 'Account from the ledger transfers.';
}

function FragmentRow({ seq, label, value, other, tone, onSeek }: { seq: number; label: string; value: string; other: string; tone: string; onSeek: (k: number) => void }) {
  return (
    <>
      <dt><button type="button" className="value-btn row-link num" onClick={() => onSeek(seq)} aria-label={`Seek to event ${seq + 1}`}>event {seq + 1}</button></dt>
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
        <dt>market events</dt><dd>None. Market prices and trades are not part of contract v0.2 traces.</dd>
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
    <pre aria-label="Event JSON" tabIndex={0}>
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
