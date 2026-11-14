import { describe, it, expect } from 'vitest';
import { formatApiErrorDetail } from './api';

describe('API error presentation', () => {
  it('keeps specific device refusals readable', () => {
    expect(formatApiErrorDetail('Device limit reached (1)')).toBe('Device limit reached (1)');
  });
  it('renders validation arrays instead of object-object', () => {
    expect(formatApiErrorDetail([{ msg: 'Invalid email' }, { msg: 'Password required' }])).toBe('Invalid email Password required');
  });
  it('handles missing errors', () => {
    expect(formatApiErrorDetail(null)).toBe('Something went wrong. Please try again.');
  });
});
