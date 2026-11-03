// Views whose evidence does not exist yet. They say what they will show and what is missing,
// and they never draw placeholder data.

const BEATS = ['Before the attack', 'The attacker enters', 'What it changed', 'Where resources went', 'Who gained, who lost', 'Why it worked'];

export function Theater() {
  return (
    <article className="essay shell" aria-labelledby="theater-title">
      <h1 id="theater-title">Exploit Theater</h1>
      <p className="lede">A saved attack will play here as a story, beat by beat, against the same tasks under an honest market. No approved trace contains an attack yet, so nothing is staged.</p>
      <ol className="beats" aria-label="How an exploit will be told">
        {BEATS.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ol>
      <p className="requires">
        <i aria-hidden="true" />
        Waiting for a reviewed, reproducible attack trace.
      </p>
    </article>
  );
}

export function Evolution() {
  return (
    <article className="essay shell" aria-labelledby="evo-title">
      <h1 id="evo-title">Mechanism Evolution</h1>
      <p className="lede">Whether a new mechanism allocates better on held-out tasks, and whether it holds when someone tries to break it. Nothing has been evaluated, so the axes are empty.</p>
      <figure className="plot" aria-label="Empty plot: held-out quality against adversarial welfare loss. No data.">
        <svg viewBox="0 0 1000 420" preserveAspectRatio="none" role="presentation">
          <line className="axisline" x1={0} x2={1000} y1={420} y2={420} />
          <line className="axisline" x1={0} x2={0} y1={0} y2={420} />
        </svg>
        <span className="y-label">↑ held-out quality</span>
        <span className="x-label">adversarial welfare loss →</span>
        <div className="empty-state">
          <b>No mechanisms evaluated</b>
        </div>
      </figure>
      <p className="requires">
        <i aria-hidden="true" />
        Waiting for frozen held-out results with uncertainty.
      </p>
    </article>
  );
}
