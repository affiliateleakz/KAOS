import { describe, it, expect } from 'vitest';
import { deviceDate } from './deviceDate';

describe('legacy device activity', () => {
  it('shows unknown instead of invalid date for missing activity', () => {
    expect(deviceDate({})).toBe('Unknown');
    expect(deviceDate({ lastActive: 'invalid' })).toBe('Unknown');
  });
  it('supports the legacy last_active field', () => {
    expect(deviceDate({ last_active: '2026-09-28T22:28:34Z' })).not.toBe('Unknown');
  });
});
