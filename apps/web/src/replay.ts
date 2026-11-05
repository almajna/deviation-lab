export type Usage = { prompt_tokens: number; completion_tokens: number; total_tokens: number };
export type Row = { index: number; phase: string; provider: string; client_seconds: number; latency_cache: Record<string, unknown> | null; endpoint: { raw_usage: Usage; forwarded_usage: Usage } | null; error: unknown };
export type Case = { mode: string; condition: string; seed: number; rows: Row[] };
export type Run = { job_id: string; job_url: string; source_url: string; raw_sha256: string; cases: Case[] };
export type Fixture = { schema_version: string; runs: Run[] };
export const conditions = ['honest', 'inflated', 'defended'] as const;
export function findCase(run: Run, mode: string, seed: number, condition: string): Case {
  const matches = run.cases.filter(c => c.mode === mode && c.seed === seed && c.condition === condition);
  if (matches.length !== 1 || matches[0].rows.length !== 24) throw new Error('Missing or duplicated evidence case');
  return matches[0];
}
export function measured(c: Case) {
  const rows = c.rows.filter(r => r.phase === 'measured');
  if (rows.length !== 20 || rows.some(r => r.error || !['A', 'B'].includes(r.provider))) throw new Error('Incomplete measured receipts');
  return { A: rows.filter(r => r.provider === 'A').length, B: rows.filter(r => r.provider === 'B').length, mean: rows.reduce((sum, r) => sum + r.client_seconds, 0) / rows.length };
}
/** Previous row's cache is the recorded post-request snapshot available before the selected request.
 * Selector scores and transient random choices were not recorded. */
export function replayAt(c: Case, index: number) {
  if (!Number.isInteger(index) || index < 0 || index >= c.rows.length) throw new Error('Invalid replay position');
  const prior = c.rows.slice(0, index);
  return { row: c.rows[index], priorCache: index ? prior[index - 1].latency_cache : null, counts: { A: prior.filter(r => r.provider === 'A').length, B: prior.filter(r => r.provider === 'B').length } };
}
