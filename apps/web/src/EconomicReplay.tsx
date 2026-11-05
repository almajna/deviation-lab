import { useState } from 'react';
import raw from './data/economic.json';
import { economicCase, regret, type EconomicFixture } from './economic';
const data = raw as EconomicFixture;
const format = (x: number[]) => x.join(', ');
const rational = (x: number[]) => x[1] === 1 ? String(x[0]) : `${x[0]}/${x[1]}`;
export function EconomicReplay() {
  const [caseId, setCase] = useState(0);
  const [condition, setCondition] = useState('utility_bonus');
  const e = economicCase(data, caseId, condition);
  return <section aria-labelledby="economic"><h2 id="economic">Recorded model decision and retrospective conditional benchmark</h2>
    <p>Qwen2.5-7B made genuine recorded decisions in a synthetic allocation game with virtual credits, supplied beliefs and controlled counterparties. Credits are not money. Qwen did not observe the rival’s realized report when it decided. The certified alternative is calculated retrospectively, holding that observed report and the supplied belief fixed; it was not selected by the model.</p>
    <label>Economic case <select value={caseId} onChange={x => setCase(Number(x.target.value))}>{[0,1,2,3,4,5].map(i => <option key={i} value={i}>{i + 1}</option>)}</select></label>{' '}
    <label>Economic condition <select value={condition} onChange={x => setCondition(x.target.value)}><option value="truthful">Truthful instruction</option><option value="utility_zero">Utility instruction, zero bonus</option><option value="utility_bonus">Utility instruction, 200-credit bonus</option></select></label>
    <p><button type="button" onClick={() => setCase(caseId - 1)} disabled={caseId === 0}>Previous economic case</button>{' '}<button type="button" onClick={() => setCase(caseId + 1)} disabled={caseId === 5}>Next economic case</button></p>
    <div aria-live="polite"><h3>Case {caseId + 1}: {condition.replaceAll('_',' ')}</h3>
      <p>Supplied belief over outcomes: [{format(e.belief)}] out of 10. Rival report observed after the decision: [{format(e.rival_report)}].</p>
      <p>Recorded model report: <strong>[{format(e.model_report)}]</strong>; observed allocation: {e.allocation.join(', ')}. Expected utility under the supplied belief: {rational(e.expected_utility)} credits; realized utility: {e.realized_utility} credits.</p>
      <p>Retrospective conditional optimal report: <strong>[{format(e.certified_report)}]</strong>; expected utility: {rational(e.optimal_expected_utility)} credits. Retrospective expected utility difference from the model’s report: {regret(e)} credits.</p>
      <p>Recorded model expected gain versus signal-following: {e.expected_gain_vs_signal} credits. This is a different comparison from the retrospective difference to the conditional optimum.</p>
      <p>Certificate SHA-256: <code>{e.certificate_sha256}</code></p></div>
    <p>The certificate covers 67 legal decisions (66 reports and decline) for the recorded rival report and stated belief. This comparison does not establish that Qwen failed to choose an optimum it could have known at decision time. It does not establish general optimality, an equilibrium, real-world provider profit or a novel scientific discovery. Across the six paired zero- and bonus-condition cases, no focal report or allocation changed; no profitable model manipulation was found under the study’s definition.</p>
    <p><a href={data.source_url}>Recorded inference and certificate archive</a> · <a href={data.protocol_url}>Study and independent verification</a>. Archive SHA-256: <code>{data.source_sha256}</code>.</p>
  </section>;
}
