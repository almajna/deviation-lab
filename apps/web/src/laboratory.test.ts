import { describe, expect, it } from 'vitest';
import { evaluateCase, evaluateCaseZero, parseLaboratoryState, reports } from './Laboratory';
import raw from './data/economic.json';

describe('hypothetical case 0 laboratory', () => {
  it('reproduces the recorded conditional optimum and zero-bonus control', () => {
    const zero = reports.map(r => evaluateCaseZero(r, 0));
    const bonus = reports.map(r => evaluateCaseZero(r, 200));
    expect(evaluateCaseZero([6, 3, 1], 200)).toMatchObject({ route: 'A', score: 146, utility: 282 });
    expect(evaluateCaseZero([1, 4, 5], 200)).toMatchObject({ route: 'B', score: 104, utility: 440 });
    expect(Math.max(...bonus.map(x => x.utility), evaluateCaseZero(null, 200).utility)).toBe(440);
    expect(Math.max(...zero.map(x => x.utility), evaluateCaseZero(null, 0).utility)).toBe(282);
    expect(evaluateCaseZero(null, 200)).toMatchObject({route: 'A', score: 0, utility: 136});
  });
  it('lists each of the 66 distinct valid reports exactly once', () => {
    expect(reports).toHaveLength(66);
    expect(new Set(reports.map(x => x.join(','))).size).toBe(66);
    expect(reports.every(r => r.every(x => Number.isInteger(x) && x >= 0) && r.reduce((a,b) => a+b,0) === 10)).toBe(true);
  });
  it('matches all six recorded conditional optimum receipts', () => {
    for (let id = 0; id < 6; id++) {
      const record = raw.episodes.find(e => e.case === id && e.condition === 'utility_bonus')!;
      const all = [...reports.map(r => evaluateCase(r, 200, id)), evaluateCase(null, 200, id)];
      expect(Math.max(...all.map(x => x.utility))).toBe(record.optimal_expected_utility[0] / record.optimal_expected_utility[1]);
      expect(evaluateCase(record.model_report as [number, number, number], 200, id).utility).toBe(record.expected_utility[0] / record.expected_utility[1]);
    }
  });
  it('uses B at the threshold and A immediately below', () => {
    expect(evaluateCaseZero([1,4,5], 200)).toMatchObject({route:'B', pooled:.6});
    expect(evaluateCaseZero([2,4,4], 200).route).toBe('A');
  });
  it('restores valid encoded controls and rejects malformed values', () => {
    expect(parseLaboratoryState('?lab_report=66&lab_bonus=0')).toEqual({caseId:0,report:66,bonus:0});
    expect(parseLaboratoryState('?lab_report=67&lab_bonus=301')).toEqual({caseId:0,report:reports.findIndex(x => x.join(',') === '6,3,1'),bonus:200});
    expect(parseLaboratoryState('?lab_report=-1&lab_bonus=1e2')).toEqual({caseId:0,report:reports.findIndex(x => x.join(',') === '6,3,1'),bonus:200});
  });
});
