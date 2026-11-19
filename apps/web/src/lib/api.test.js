import { describe, it, expect } from 'vitest';
import { api, apiHtmlProblem, formatApiErrorDetail, errMsg } from './api';

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

it('rejects HTTP 200 bot verification HTML instead of treating it as a successful login', async () => {
  await expect(api.request({url:'/api/auth/login',method:'POST',adapter:async config=>({status:200,statusText:'OK',headers:{'content-type':'text/html'},config,data:'<!doctype html><html><title>Bot Verification</title></html>'})})).rejects.toMatchObject({code:'KAOS_API_HTML',response:{data:{detail:expect.stringContaining('bot-verification')}}});
});
it('preserves JSON API data and gives a separate routing message for other HTML',()=>{
  expect(apiHtmlProblem({status:'ok'})).toBeNull();
  expect(apiHtmlProblem('<html><title>KAOS website</title></html>')).toContain('routing');
});
