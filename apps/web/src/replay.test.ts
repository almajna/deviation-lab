import { describe, expect, it } from 'vitest';
import raw from './data/routing.json';
import { findCase, measured, replayAt, conditions, type Fixture } from './replay';
const data = raw as Fixture;
describe('recorded routing replay', () => {
  it('covers each requested execution, seed and condition', () => {
    expect(data.runs).toHaveLength(2);
    for (const run of data.runs) for (const seed of [7, 11, 23]) for (const condition of conditions) {
      const c = findCase(run, 'latency', seed, condition);
      expect(c.rows.map(r => r.phase)).toEqual([...Array(4).fill('warmup'), ...Array(20).fill('measured')]);
      expect(measured(c).A + measured(c).B).toBe(20);
    }
  });
  it('recomputes the registered allocation differences', () => {
    const gains = data.runs.map(run => [7,11,23].map(seed => measured(findCase(run,'latency',seed,'inflated')).B - measured(findCase(run,'latency',seed,'honest')).B));
    expect(gains).toEqual([[0,0,20],[13,13,20]]);
    const run = data.runs[1];
    expect(conditions.map(c => measured(findCase(run,'stream',7,c)).B)).toEqual([0,0,20]);
  });
  it('uses the preceding snapshot and rejects unavailable positions and cases', () => {
    const c = findCase(data.runs[0], 'latency', 7, 'honest');
    expect(replayAt(c,0).priorCache).toBeNull();
    expect(replayAt(c,1).priorCache).toEqual(c.rows[0].latency_cache);
    expect(() => replayAt(c,24)).toThrow();
    expect(() => findCase(data.runs[0],'latency',999,'honest')).toThrow();
  });
});
