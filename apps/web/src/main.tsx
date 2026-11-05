import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EconomicReplay } from './EconomicReplay';
import raw from './data/routing.json';
import { conditions, findCase, measured, replayAt, type Fixture } from './replay';

const data = raw as Fixture;
function App() {
  const [runIndex, setRun] = useState(0);
  const [seed, setSeed] = useState(7);
  const [condition, setCondition] = useState<string>('honest');
  const [cursor, setCursor] = useState(0);
  const run = data.runs[runIndex];
  const chosen = findCase(run, 'latency', seed, condition);
  const { row, priorCache, counts } = replayAt(chosen, cursor);
  const comparisons = conditions.map(c => ({ condition: c, stats: measured(findCase(run, 'latency', seed, c)) }));
  const honest = comparisons[0].stats;
  return <main style={{overflowWrap: 'anywhere'}}>
    <h1>Inside an AI Routing Manipulation</h1>
    <p><strong>Scientific verdict: INCONCLUSIVE.</strong> The original run missed the prespecified allocation threshold across seeds; the independent rerun met that threshold but failed a streaming control. These are controlled offline fixture providers, not production traffic or real LLM responses.</p>
    <section aria-labelledby="choices"><h2 id="choices">Select evidence</h2>
      <label>Execution <select value={runIndex} onChange={e => { setRun(Number(e.target.value)); setCursor(0); }}><option value={0}>Original execution</option><option value={1}>Independent rerun</option></select></label>{' '}
      <label>Seed <select value={seed} onChange={e => { setSeed(Number(e.target.value)); setCursor(0); }}><option>7</option><option>11</option><option>23</option></select></label>{' '}
      <label>Condition <select value={condition} onChange={e => { setCondition(e.target.value); setCursor(0); }}><option value="honest">Honest</option><option value="inflated">Inflated</option><option value="defended">Corrected by gateway (defended)</option></select></label>
      <p>For nonstream requests the pinned router records elapsed response time divided by reported completion tokens as a latency sample. Inflating the denominator can lower B’s recorded per-token sample, affecting later ranking when history is used. Selection also depends on exploration, random choices and prior observations.</p><p>Each condition has its own process and routing history. The same request number across conditions does not imply the router had the same prior history.</p>
    </section>
    <section aria-labelledby="replay"><h2 id="replay">Recorded latency-routing decisions</h2>
      <button type="button" onClick={() => setCursor(0)} disabled={cursor === 0}>First</button>{' '}
      <button type="button" onClick={() => setCursor(cursor - 1)} disabled={cursor === 0}>Previous request</button>{' '}
      <button type="button" onClick={() => setCursor(cursor + 1)} disabled={cursor === chosen.rows.length - 1}>Next request</button>{' '}
      <label>Request <input type="range" min="1" max="24" value={cursor + 1} onChange={e => setCursor(Number(e.target.value) - 1)} /></label>
      <div aria-live="polite"><h3>Request {cursor + 1} of 24 — {row.phase}</h3>
      <p>Selected provider: {row.provider}; client time: {(row.client_seconds * 1000).toFixed(2)} ms. Prior allocations (including warmup): A {counts.A}, B {counts.B}.</p>
      <p>Provider-reported usage: {row.endpoint ? JSON.stringify(row.endpoint.raw_usage) : 'not recorded'}. Forwarded to router: {row.endpoint ? JSON.stringify(row.endpoint.forwarded_usage) : 'not recorded'}.</p>
      <h4>Recorded cache after previous request</h4><pre style={{whiteSpace:'pre-wrap', overflowWrap:'anywhere'}}>{priorCache ? JSON.stringify(priorCache, null, 2) : 'No earlier snapshot recorded.'}</pre>
      <p>These are observed history snapshots, not captured selector scores. Selection-time random draws and the exact candidate scores were not recorded.</p>
      <details><summary>Cache recorded after this request</summary><pre style={{whiteSpace:'pre-wrap', overflowWrap:'anywhere'}}>{JSON.stringify(row.latency_cache, null, 2)}</pre></details></div>
    </section>
    <section aria-labelledby="comparison"><h2 id="comparison">Completed-case comparison</h2><p>Retrospective statistics from all 20 measured requests; these are outcomes, not information available at the selected decision.</p>
      <div style={{overflowX:"auto"}}><table><caption>Seed {seed}, measured requests only</caption><thead><tr><th scope="col">Condition</th><th scope="col">A</th><th scope="col">B</th><th scope="col">B share change from honest</th><th scope="col">Mean client latency</th><th scope="col">Change from honest</th></tr></thead><tbody>{comparisons.map(({condition: c, stats: s}) => <tr key={c}><th scope="row">{c === 'defended' ? 'corrected (defended)' : c}</th><td>{s.A}</td><td>{s.B}</td><td>{((s.B - honest.B) * 5).toFixed(0)} pp</td><td>{(s.mean * 1000).toFixed(2)} ms</td><td>{((s.mean - honest.mean) * 1000).toFixed(2)} ms</td></tr>)}</tbody></table></div>
    </section>
    <section aria-labelledby="limits"><h2 id="limits">Why the result is inconclusive</h2><p>Original inflated-minus-honest B allocation changes for seeds 7, 11, 23 were 0, 0, and 100 percentage points. Rerun changes were 65, 65, and 100. The frozen threshold was at least 50 points for every seed, with controls within 10 points.</p><p>In the rerun's seed 7 streaming control, honest and inflated routed 0 of 20 measured requests to B, while corrected routed 20 of 20. First time-to-first-token samples and subsequent history differed. This is startup timing sensitivity, not proof of a general production effect. The nonstream gateway matched honest allocation in all three seeds in both runs.</p>
    <p>No provider profit, deployment prevalence, or billing impact was measured. The gateway assumes visible output and a known tokenizer.</p></section>
    <EconomicReplay />
    <section aria-labelledby="sources"><h2 id="sources">Evidence and source</h2><ul><li><a href={run.job_url}>Selected execution: original Actions job and preserved receipt logs</a></li><li>Raw results.json SHA-256: <code>{run.raw_sha256}</code></li><li><a href={run.source_url}>Pinned LiteLLM source</a></li><li><a href="https://github.com/almajna/deviation-lab/pull/39">Research closeout and both artifact links</a></li><li><a href="https://github.com/almajna/deviation-lab/blob/0820563fe772a6706e3420c4762211dea0513b6f/docs/LITELLM_REALITY_PROTOCOL.md">Frozen protocol</a></li></ul></section>
  </main>;
}

createRoot(document.getElementById('root')!).render(<App />);
