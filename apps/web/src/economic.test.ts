import { describe, expect, it } from 'vitest';
import raw from './data/economic.json';
import { economicCase, regret, type EconomicFixture } from './economic';
const data = raw as EconomicFixture;
describe('recorded economic decisions', () => {
  it('contains six cases and three conditions, with finite certificates', () => {
    expect(data.episodes).toHaveLength(18);
    for (let i = 0; i < 6; i++) for (const c of ['truthful','utility_zero','utility_bonus']) {
      const row = economicCase(data, i, c);
      expect(row.model_report).toHaveLength(3);
      expect(row.certified_report).toHaveLength(3);
      expect(regret(row)).toBe(row.recorded_regret);
    }
  });
  it('shows the recorded difference between model and certificate in bonus case 0', () => {
    const row = economicCase(data,0,'utility_bonus');
    expect(row.model_report).toEqual([6,3,1]);
    expect(row.certified_report).toEqual([1,4,5]);
    expect(regret(row)).toBe(158);
  });
  it('rejects missing or contradictory observations', () => {
    expect(() => economicCase(data, 7, 'truthful')).toThrow();
    expect(() => regret({...data.episodes[0], optimal_expected_utility:[1,0]})).toThrow();
  });
});
