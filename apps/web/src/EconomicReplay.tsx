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
  return <section aria-labelledby="economic"><h2 id="economic">Recorded model decision and certified alternative</h2>
    <p>Qwen2.5-7B made real recorded decisions in a synthetic allocation game. Reports, signals and utility are expressed in simulated units; credits are not money. The certified report is an independently checked counterfactual best response, not a decision the model made.</p>
    <label>Economic case <select value={caseId} onChange={x => setCase(Number(x.target.value))}>{[0,1,2,3,4,5].map(i => <option key={i} value={i}>{i + 1}</option>)}</select></label>{' '}
    <label>Economic condition <select value={condition} onChange={x => setCondition(x.target.value)}><option value="truthful">Truthful instruction</option><option value="utility_zero">Utility instruction, zero bonus</option><option value="utility_bonus">Utility instruction, 200-credit bonus</option></select></label>
    <div aria-live="polite"><h3>Case {caseId + 1}: {condition.replaceAll('_',' ')}</h3>
      <p>Supplied belief over outcomes: [{format(e.belief)}] out of 10. Recorded rival report: [{format(e.rival_report)}].</p>
      <p>Recorded model report: <strong>[{format(e.model_report)}]</strong>; observed allocation: {e.allocation.join(', ')}. Expected utility under the supplied belief: {rational(e.expected_utility)} credits; realized utility: {e.realized_utility} credits.</p>
      <p>Certified best-response report: <strong>[{format(e.certified_report)}]</strong>; expected utility: {rational(e.optimal_expected_utility)} credits. Expected utility gap from the model’s report: {regret(e)} credits.</p>
      <p>Recorded model expected gain versus signal-following: {e.expected_gain_vs_signal} credits. This is a different comparison from the gap to the certified best response.</p>
      <p>Certificate SHA-256: <code>{e.certificate_sha256}</code></p></div>
    <p>The certificate covers 67 legal decisions (66 reports and decline) for the recorded rival report and stated belief. It does not prove an equilibrium or general model capability. Across the six paired zero- and bonus-condition cases, no focal report or allocation changed; no profitable model manipulation was found under the study’s definition.</p>
    <p><a href={data.source_url}>Recorded inference and certificate archive</a> · <a href={data.protocol_url}>Study and independent verification</a>. Archive SHA-256: <code>{data.source_sha256}</code>.</p>
  </section>;
}
