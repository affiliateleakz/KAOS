import {describe,it,expect} from 'vitest';
import {campaignLink,marketingCopy,BANNER_FORMATS} from './affiliateKit';
describe('affiliate campaign kit',()=>{
 it('preserves referral attribution across campaign links',()=>{
  const link=new URL(campaignLink('https://tradingwithkaos.com/register?ref=KAOS-123','email_welcome'));
  expect(link.searchParams.get('ref')).toBe('KAOS-123');expect(link.searchParams.get('utm_source')).toBe('email_welcome');
 });
 it('includes referral links, disclosures and risk language in every template',()=>{
  for(const template of marketingCopy('https://tradingwithkaos.com/register?ref=KAOS-123')){
   expect(template.body).toContain('ref=KAOS-123');expect(template.body).toContain('affiliate');expect(template.body.toLowerCase()).toMatch(/risk|losses/);
  }
 });
 it('offers social and web banner formats',()=>expect(BANNER_FORMATS.map(f=>[f.width,f.height])).toEqual([[1200,628],[1080,1080],[728,90]]));
});
