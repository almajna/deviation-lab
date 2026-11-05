import { useEffect, useMemo, useState } from 'react';
import recorded from './data/economic.json';
import './laboratory.css';

type Report = [number, number, number];
type Result = { report: Report | null; score: number; route: 'A' | 'B'; bonus: number; utility: number; pooled: number };
const episodes = recorded.episodes.filter(e => e.condition === 'utility_bonus').sort((a, b) => a.case - b.case);
if (episodes.length !== 6) throw new Error('Missing recorded economic cases');
export const reports: Report[] = [];
for (let low = 0; low <= 10; low++) for (let middle = 0; middle <= 10 - low; middle++) reports.push([low, middle, 10 - low - middle]);
const label = (r: Report | null) => r ? `[${r.join(', ')}]` : 'Decline';
const reportIndexOf = (report: number[]) => reports.findIndex(r => r.every((x, i) => x === report[i]));
/** This compact case is retrospective: fixed route-A score, belief and rival receipt are from case 0. */
export function evaluateCase(report: Report | null, bonus: number, caseId: number): Result {
  const episode = episodes[caseId];
  if (!episode) throw new Error('Unknown economic case');
  const belief = episode.belief; const rival = episode.rival_report;
  // The separate route-A market gives the focal forecaster 136 expected credits for each of these six cases.
  // The route-B quadratic score is paid only when a report is submitted.
  const score = report ? 100 - report.reduce((s, n) => s + n * n, 0) + 2 * report.reduce((s, n, i) => s + n * belief[i], 0) : 0;
  const rivalValue = (rival[1] + 2 * rival[2]) / 20;
  const ownValue = report ? (report[1] + 2 * report[2]) / 20 : rivalValue;
  const pooled = report ? (ownValue + rivalValue) / 2 : rivalValue;
  // Compare integers: pooled >= 0.6, with B winning ties.
  const route: 'A' | 'B' = (report ? report[1] + 2 * report[2] + rival[1] + 2 * rival[2] >= 24 : rival[1] + 2 * rival[2] >= 12) ? 'B' : 'A';
  const paid = route === 'B' ? bonus : 0;
  return { report, score, route, bonus: paid, utility: 136 + score + paid, pooled };
}
export function parseLaboratoryState(search: string) {
  const p = new URLSearchParams(search);
  const r = p.get('lab_report'); const b = p.get('lab_bonus'); const c = p.get('lab_case');
  const caseId = c !== null && /^\d+$/.test(c) && Number(c) < episodes.length ? Number(c) : 0;
  return {
    caseId, report: r !== null && /^\d+$/.test(r) && Number(r) <= 66 ? Number(r) : reportIndexOf(episodes[caseId].model_report),
    bonus: b !== null && /^\d+$/.test(b) && Number(b) <= 300 ? Number(b) : 200,
  };
}
export function evaluateCaseZero(report: Report | null, bonus: number): Result { return evaluateCase(report, bonus, 0); }
export function Laboratory() {
  const [initial] = useState(() => parseLaboratoryState(window.location.search));
  const [caseId, setCaseId] = useState(initial.caseId);
  const [reportIndex, setReportIndex] = useState(initial.report);
  const [bonus, setBonus] = useState(initial.bonus);
  const [copied, setCopied] = useState('');
  const episode = episodes[caseId];
  const belief = episode.belief; const rival = episode.rival_report; const recordedReport = episode.model_report as Report;
  const recordedIndex = reportIndexOf(recordedReport);
  const results = useMemo(() => [...reports.map(r => evaluateCase(r, bonus, caseId)), evaluateCase(null, bonus, caseId)], [bonus, caseId]);
  // Order is fixed and the first maximizer wins when several reports tie.
  const bestIndex = results.reduce((best, r, index) => r.utility > results[best].utility ? index : best, 0);
  const selected = results[reportIndex];
  const best = results[bestIndex];
  const reference = evaluateCase(recordedReport, bonus, caseId);
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('lab_case', String(caseId));
    url.searchParams.set('lab_report', String(reportIndex));
    url.searchParams.set('lab_bonus', String(bonus));
    history.replaceState(history.state, '', url);
  }, [caseId, reportIndex, bonus]);
  async function copyLink() {
    try { await navigator.clipboard.writeText(window.location.href); setCopied('Scenario link copied.'); }
    catch { setCopied('Copy the URL from your address bar to share this scenario.'); }
  }
  const yMin = Math.min(...results.map(r => r.utility)) - 15;
  const yMax = Math.max(...results.map(r => r.utility)) + 15;
  const x = (r: Report) => 40 + ((r[1] + 2 * r[2]) / 20) * 520;
  const y = (utility: number) => 195 - (utility - yMin) / (yMax - yMin) * 160;
  return <section className="laboratory" aria-labelledby="lab-title">
    <div className="lab-heading"><div><p className="lab-kicker">01 / INTERACTIVE LABORATORY</p><h2 id="lab-title">Change a report.<br/><em>Move the decision.</em></h2></div><p>Two forecasters influence which AI route receives a task. A bonus can give one forecaster a reason to change their report.</p></div>
    <p className="lab-disclosure"><strong>HYPOTHETICAL SCENARIO</strong> · Based on a recorded economic case; your report and bonus are simulated. Credits are not money. The original model did not see the rival’s realized report when it decided.</p>
    <div className="lab-workbench"><div className="lab-controls"><p className="lab-kicker">01 / SET THE CONDITIONS</p><h3>Choose a decision.</h3><p>The belief is [{belief.join(', ')}] out of 10 for low, medium and high outcomes. We hold the later-recorded rival report [{rival.join(', ')}] fixed.</p>
      <label htmlFor="lab-case">Recorded case <span>Changes the fixed belief and recorded report</span></label><select id="lab-case" value={caseId} onChange={e => { const next = Number(e.target.value); setCaseId(next); setReportIndex(reportIndexOf(episodes[next].model_report)); }}>{episodes.map((ep,i) => <option key={ep.case} value={i}>Case {ep.case + 1}</option>)}</select>
      <label htmlFor="lab-report">Report <span>66 possible distributions + decline</span></label><select id="lab-report" value={reportIndex} onChange={e => setReportIndex(Number(e.target.value))}>{reports.map((r, i) => <option key={r.join('-')} value={i}>{label(r)}</option>)}<option value={66}>Decline to report</option></select>
      <label htmlFor="lab-bonus">Bonus if route B is chosen <output htmlFor="lab-bonus">{bonus} credits</output></label><input id="lab-bonus" type="range" min="0" max="300" step="1" value={bonus} onChange={e => setBonus(Number(e.target.value))}/><div className="lab-range"><span>0</span><span>300 CREDITS</span></div>
      <div className="lab-buttons"><button type="button" onClick={() => setReportIndex(bestIndex)}>Find best report ↗</button><button type="button" className="lab-secondary" onClick={() => setReportIndex(recordedIndex)}>Use recorded report</button><button type="button" className="lab-secondary" onClick={() => {setCaseId(0);setReportIndex(reportIndexOf(episodes[0].model_report));setBonus(200);}}>Reset</button><button type="button" className="lab-secondary" onClick={copyLink}>Copy scenario link</button></div><p className="lab-copy-status" role="status">{copied}</p>
    </div><div className="lab-results" aria-live="polite"><div className="lab-result-header"><div><p className="lab-kicker">02 / ALLOCATION</p><h3>Route {selected.route} is selected.</h3></div><div className="lab-result-tag">{selected.pooled.toFixed(3)} <span>POOLED B SCORE</span></div></div><p>Route B wins when its pooled score reaches 0.600; B wins ties. {selected.report ? `The pooled score ${selected.pooled >= .6 ? 'meets' : 'does not meet'} that threshold.` : 'Declining leaves the rival’s score as the pool.'}</p>
      <div className="lab-metrics"><div><span>EXPECTED SCORE</span><strong>{selected.score} <small>credits</small></strong><p>For the adjustable route-B report</p></div><div><span>EXTERNAL BONUS</span><strong>+{selected.bonus} <small>credits</small></strong><p>If route B is selected</p></div><div><span>EXPECTED UTILITY</span><strong>{selected.utility} <small>credits</small></strong><p>Includes 136 fixed route-A credits</p></div></div>
      <div className="lab-chart-heading"><div><p className="lab-kicker">THE SEARCH SPACE</p><h4>Every possible report.</h4></div><p>Each dot is a legal report. Select a point or use the report menu.</p></div><svg className="lab-chart" viewBox="0 0 600 240" role="img" aria-label={`Utility landscape for 66 reports. Current report ${label(selected.report)} has expected utility ${selected.utility}. Conditional maximum ${best.utility}. Decline has utility ${results[66].utility}.`}><line x1="40" y1="195" x2="560" y2="195" stroke="#555d55"/><line x1="40" y1="35" x2="40" y2="195" stroke="#555d55"/><text x="40" y="221">0.0</text><text x="535" y="221">1.0</text><text x="180" y="238">REPORTED B QUALITY →</text><text x="4" y="38">{yMax}</text><text x="4" y="198">{yMin}</text>{results.slice(0,66).map((r,i) => <circle key={i} cx={x(r.report!)} cy={y(r.utility)} r={i === reportIndex ? 6 : i === bestIndex ? 5 : 3} className={i === reportIndex ? 'lab-point selected' : i === bestIndex ? 'lab-point best' : 'lab-point'} onClick={() => setReportIndex(i)}/>)}</svg>
      <p className="lab-insight">Best conditional decision: <strong>{label(best.report)}</strong>, {best.utility} expected credits. {best.utility - reference.utility} more than the recorded report under the current bonus. Declining yields {results[66].utility}.</p><p className="lab-fine">The computed optimum checks all 66 reports and decline with the rival receipt fixed. It is a conditional browser calculation, not a certificate or a claim that the model could have known the rival’s report.</p>
    </div></div><details className="lab-math"><summary>The mathematics behind the decision <span>+</span></summary><div className="lab-equations"><div><span>01 / POOL</span><p>μ(r) = (r<sub>mid</sub> + 2r<sub>high</sub>) / 20</p><p>Choose B when [μ(r) + μ(rival)] / 2 ≥ 0.6. If you decline, only the rival report is pooled.</p></div><div><span>02 / SCORE</span><p>S(r) = 100 − ∑rᵢ² + 2∑bᵢrᵢ</p><p>Expected quadratic reward under belief b; zero for decline. The fixed route-A score is 136 credits.</p></div><div><span>03 / SEARCH</span><p>U(r) = 136 + S(r) + B · 𝟙[B chosen]</p><p>All counts are nonnegative integers that sum to 10. The exhaustive search includes decline and uses the first maximizer if tied.</p></div></div></details>
  </section>;
}
