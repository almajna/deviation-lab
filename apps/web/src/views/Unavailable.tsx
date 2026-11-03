// Views whose evidence does not exist yet. They describe exactly what would populate them
// and which approved event types are missing. They never draw placeholder data.

interface Chapter {
  title: string;
  body: string;
  needs: string;
  have?: string;
}

const THEATER: Chapter[] = [
  {
    title: 'Before the attack',
    body: 'The honest baseline: forecasts, prices and allocations with every participant behaving as modelled.',
    needs: 'A verified baseline trace with market-price events',
  },
  {
    title: 'The attacker enters',
    body: 'An adversarial agent joins and acts. Its information set at that moment, and nothing more.',
    needs: 'SYNTHETIC_ADVERSARY actions in an approved event extension',
  },
  {
    title: 'What it changed',
    body: 'The forecast or price it moved, frame by frame, against the honest counterfactual.',
    needs: 'Market-price and trade events (Phase 3)',
  },
  {
    title: 'Where resources went',
    body: 'Allocations redirected by the distortion, set against the same tasks under the baseline.',
    needs: 'Paired attacked and baseline traces on an identical task set',
  },
  {
    title: 'Who gained, who lost',
    body: 'Payoffs, maker losses and welfare consequences, settled from the ledger.',
    needs: 'Attack-run ledger and utility receipts',
    have: 'Ledger and utility accounting already replay in the Arena',
  },
  {
    title: 'Why it worked',
    body: 'An independent replay that reproduces the exploit bit for bit, plus the mechanism rule it exploited.',
    needs: 'A reproducible counterexample with a bounded check (Phase 4)',
    have: 'Deterministic seek and client-side trace validation exist in this build',
  },
];

const EVOLUTION: Chapter[] = [
  {
    title: 'Held-out quality versus robustness',
    body: 'Each mechanism plotted by budget-adjusted quality on frozen held-out tasks against adversarial welfare loss.',
    needs: 'Frozen evaluation protocol and an authorised held-out run (Gate D)',
  },
  {
    title: 'Uncertainty',
    body: 'Intervals on both axes, so that a mechanism is never declared better on noise alone.',
    needs: 'Bootstrap or equivalent uncertainty summaries',
  },
  {
    title: 'Baselines',
    body: 'Non-market baselines plotted on the same axes, under the same budget.',
    needs: 'Baseline results with parity checks',
  },
  {
    title: 'Lineage',
    body: 'Every candidate’s parameters, version and source commit, with training and held-out indicators kept apart.',
    needs: 'Policy-search traces (Phase 7)',
  },
];

export function Theater() {
  return (
    <article className="essay shell" aria-labelledby="theater-title">
      <h1 id="theater-title">Exploit Theater</h1>
      <p className="lede">
        This is where a saved attack will play as a story: the market before, the move the attacker made, the allocation it bent and who paid for it. No approved trace contains an attack yet, so nothing is staged here.
      </p>
      <p className="status"><i aria-hidden="true" />No attack traces exist</p>
      <Chapters items={THEATER} label="How an exploit will be told" />
      <div className="compare" aria-label="Side-by-side comparison, unavailable">
        <div>
          <h3>Attacked run</h3>
          <p>Empty. Requires an attack trace.</p>
        </div>
        <div>
          <h3>Same tasks, alternative mechanism</h3>
          <p>Empty. Requires a paired trace with the same task set, budget and seed.</p>
        </div>
      </div>
    </article>
  );
}

export function Evolution() {
  return (
    <article className="essay shell" aria-labelledby="evo-title">
      <h1 id="evo-title">Mechanism Evolution</h1>
      <p className="lede">
        Whether a new mechanism actually allocates better, and whether it holds up when someone tries to break it. No mechanism has been evaluated yet; the axes below are drawn empty on purpose.
      </p>
      <p className="status"><i aria-hidden="true" />No evaluation results exist</p>
      <figure className="plot" aria-label="Empty plot: held-out quality against adversarial welfare loss. No data." style={{ margin: '64px 0 0', paddingTop: 24 }}>
        <EmptyPlot />
      </figure>
      <Chapters items={EVOLUTION} label="What will populate this view" />
    </article>
  );
}

function Chapters({ items, label }: { items: Chapter[]; label: string }) {
  return (
    <ol className="chapters" aria-label={label}>
      {items.map((c) => (
        <li key={c.title}>
          <div>
            <h3>{c.title}</h3>
            <p>{c.body}</p>
          </div>
          <div className="needs">
            <b>Needs</b> {c.needs}
            {c.have && (
              <>
                <br />
                <span className="have">Ready</span> {c.have}
              </>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function EmptyPlot() {
  const W = 1000, H = 420;
  const f = [0, 0.25, 0.5, 0.75, 1];
  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="presentation">
        {f.map((t) => (
          <g key={t}>
            <line className="grid" x1={t * W} x2={t * W} y1={0} y2={H} />
            <line className="grid" x1={0} x2={W} y1={t * H} y2={t * H} />
          </g>
        ))}
        <line className="axisline" x1={0} x2={W} y1={H} y2={H} />
        <line className="axisline" x1={0} x2={0} y1={0} y2={H} />
      </svg>
      <span className="y-label">↑ held-out quality, budget-adjusted</span>
      <span className="x-label">adversarial welfare loss →</span>
      <div className="empty-state">
        <b>No mechanisms evaluated</b>
        <span>awaiting frozen held-out results</span>
      </div>
    </>
  );
}
