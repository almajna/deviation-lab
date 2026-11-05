export type EconomicEpisode = {case: number; condition: string; belief: number[]; model_report: number[]; rival_report: number[]; certified_report: number[]; allocation: string[]; expected_utility: number[]; optimal_expected_utility: number[]; realized_utility: number; recorded_regret: number; expected_gain_vs_signal: string; certificate_sha256: string};
export type EconomicFixture = {schema_version: string; source_sha256: string; source_url: string; protocol_url: string; episodes: EconomicEpisode[]};
export function economicCase(data: EconomicFixture, caseId: number, condition: string): EconomicEpisode {
  const rows = data.episodes.filter(e => e.case === caseId && e.condition === condition);
  if (rows.length !== 1) throw new Error('Missing or duplicate economic receipt');
  return rows[0];
}
export function regret(row: EconomicEpisode): number {
  const [a,b] = row.optimal_expected_utility; const [c,d] = row.expected_utility;
  if (![a,b,c,d].every(Number.isSafeInteger) || b <= 0 || d <= 0) throw new Error('Invalid rational utility');
  return a / b - c / d;
}
