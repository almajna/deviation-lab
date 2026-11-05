import { useEffect, useId, useRef } from 'react';
import type { ReplayState } from '../trace/replay';
import type { TraceBundle } from '../trace/types';
import { costUnitLabel, exact, fmt } from '../trace/narrate';

export type InspectTarget = { kind: 'event'; seq: number } | { kind: 'account'; id: string } | { kind: 'trace' } | { kind: 'figures' };

interface Props {
  bundle: TraceBundle;
  /** The inspector shows only what is known at the current position, exactly like the stage. */
  state: ReplayState;
  target: InspectTarget | null;
  onClose: () => void;
  onSeek: (k: number) => void;
  /** Trace selection, provenance, download and load: shown at the top of the Data panel. */
  traceControls?: React.ReactNode;
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal dialog: focus moves in on open, Tab is contained, Escape and the scrim close it, the page
 * behind is inert, and focus returns to the trigger synchronously on close.
 */
export function Inspector({ bundle, state, target, onClose, onSeek, traceControls }: Props) {
  const open = target !== null;
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement;
    const background = [...document.querySelectorAll<HTMLElement>('[data-page]')];
    background.forEach((el) => el.setAttribute('inert', ''));
    // Focus after the dialog is visible and the background inert (also under reduced motion).
    closeRef.current?.focus({ preventScroll: true });
    requestAnimationFrame(() => {
      if (!dialogRef.current?.contains(document.activeElement)) closeRef.current?.focus({ preventScroll: true });
    });
    return () => background.forEach((el) => el.removeAttribute('inert'));
  }, [open]);

  // Escape closes the dialog wherever focus is (a document-level listener, not only inside the dialog).
  const closeRefFn = useRef<() => void>(() => {});
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        closeRefFn.current();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => document.removeEventListener('keydown', onKey, true);
  }, [open]);

  const close = () => {
    document.querySelectorAll<HTMLElement>('[data-page]').forEach((el) => el.removeAttribute('inert'));
    const back = returnFocus.current;
    if (back instanceof HTMLElement && back !== document.body && back.isConnected) back.focus({ preventScroll: true });
    else (document.activeElement as HTMLElement | null)?.blur();
    onClose();
  };

  closeRefFn.current = close;

  const onKeyDown = (e: React.KeyboardEvent) => {
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
          <button ref={closeRef} type="button" className="pbtn" onClick={close} aria-label="Close inspector">
            <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.4" /></svg>
          </button>
        </header>
        <div className="body">{target && <Body bundle={bundle} state={state} target={target} traceControls={traceControls} onSeek={(k) => { close(); onSeek(k); }} />}</div>
      </div>
    </>
  );
}

function title(t: InspectTarget | null) {
  if (!t) return '';
  if (t.kind === 'event') return `Event ${t.seq + 1}`;
  if (t.kind === 'account') return t.id;
  if (t.kind === 'figures') return 'Data';
  return 'Trace provenance';
}

function Body({ bundle, state, target, onSeek, traceControls }: { bundle: TraceBundle; state: ReplayState; target: InspectTarget; onSeek: (k: number) => void; traceControls?: React.ReactNode }) {
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
          <button type="button" className="pbtn text bordered" onClick={() => onSeek(e.seq)}>Seek here</button>
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
            <><dt>utility</dt><dd><span className="num">{fmt(u.utility, true)}</span> <span className="nowrap">= cash <span className="num">{fmt(u.cash_delta, true)}</span></span> <span className="nowrap">+ modelled benefit <span className="num">{u.external_benefit}</span></span> <span className="nowrap">− effort <span className="num">{u.noncash_effort_cost}</span></span></dd></>
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
  if (target.kind === 'figures') return <>{traceControls}<Figures bundle={bundle} state={state} onSeek={onSeek} /></>;
  return <Provenance bundle={bundle} />;
}

/** Every figure known at the current position, each with the event that establishes it. */
function Figures({ bundle, state, onSeek }: { bundle: TraceBundle; state: ReplayState; onSeek: (k: number) => void }) {
  const unit = costUnitLabel(bundle.trace.cost_unit);
  const Src = ({ seq }: { seq: number }) => (
    <button type="button" className="value-btn row-link num" onClick={() => onSeek(seq)} aria-label={`Seek to event ${seq + 1}`}>event {seq + 1}</button>
  );
  const r = state.report;
  return (
    <>
      <p className="knew">Everything the diagram shows at this position, as recorded. Select an event to jump there.</p>
      <section aria-label="Tasks">
        <h3 className="dh">Tasks</h3>
        {state.tasks.length === 0 && <p className="note">No task has appeared yet.</p>}
        <dl>
          {state.tasks.map((t) => (
            <Row key={t.task_id} k={t.task_id}>
              {t.prompt && <span className="muted">{t.prompt}</span>}
              {t.forecast && <span className="fig">expected reward {Object.entries(t.forecast.values).map(([m, v]) => `${m} ${exact(v)}`).join(', ')} <Src seq={t.forecast.seq} /></span>}
              {t.reservation && <span className="fig">reserved {t.reservation.model_id ? `${fmt(t.reservation.reserved_cost)} on ${t.reservation.model_id}` : 'none (abstained)'} <Src seq={t.reservation.seq} /></span>}
              {t.realized && t.reservation && (
                <span className="fig">realized {fmt(t.realized.realized_cost)} ({fmt(t.realized.realized_cost - t.reservation.reserved_cost, true)} vs reserved) <Src seq={t.realized.seq} /></span>
              )}
              {!t.forecast && !t.reservation && <span className="muted">nothing recorded yet</span>}
            </Row>
          ))}
        </dl>
      </section>
      <section aria-label="Compute">
        <h3 className="dh">Compute <span className="muted">({unit})</span></h3>
        <dl>
          {state.budget !== undefined && <Row k="budget">{fmt(state.budget)} <span className="muted">{state.budgetSource === 'annotation' ? 'fixture annotation, not a trace field' : 'run configuration'}</span></Row>}
          <Row k="reserved">{fmt(state.reservationSpend)}</Row>
          {r ? (
            <>
              <Row k="realized">{fmt(r.realized_spend)} <Src seq={r.seq} /></Row>
              <Row k="vs reserved">{fmt(r.net_overrun, true)} (overruns {fmt(r.positive_task_overruns, true)}, unused {fmt(-r.unused_reservations, true)})</Row>
              {state.budget !== undefined && <Row k="vs budget">{fmt(r.realized_budget_excess, true)}</Row>}
            </>
          ) : (
            <Row k="realized"><span className="muted">sealed until settlement</span></Row>
          )}
        </dl>
      </section>
      <section aria-label="Credits">
        <h3 className="dh">Credits <span className="muted">(virtual)</span></h3>
        {state.transfers.length === 0 && <p className="note">No credits move until settlement.</p>}
        <dl>
          {state.transfers.map((t) => (
            <Row key={t.transfer_id} k={t.transfer_id}>{t.payer} → {t.payee} {fmt(t.amount)} <span className="muted">{t.reason.replace(/_/g, ' ')}</span> <Src seq={t.seq} /></Row>
          ))}
          {Object.entries(state.utilities?.values ?? {}).map(([a, u]) => (
            <Row key={a} k={`${a} utility`}>{fmt(u.utility, true)} = cash {fmt(u.cash_delta, true)} + modelled benefit {u.external_benefit} − effort {u.noncash_effort_cost} <Src seq={state.utilities!.seq} /></Row>
          ))}
        </dl>
      </section>
    </>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="num">{k}</dt>
      <dd className="figs">{children}</dd>
    </>
  );
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
      className="pbtn"
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
