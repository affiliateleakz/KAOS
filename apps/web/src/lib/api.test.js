import { describe, it, expect } from 'vitest';
import { formatApiErrorDetail, errMsg } from './api';

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
  it('distinguishes server and timeout failures from invalid credentials',()=>{
    expect(errMsg({response:{status:500,data:{}}})).toContain('server error (500)');
    expect(errMsg({code:'ECONNABORTED'})).toContain('too long');
    expect(errMsg({response:{status:401,data:{detail:'Invalid email or password'}}})).toBe('Invalid email or password');
  });
});
