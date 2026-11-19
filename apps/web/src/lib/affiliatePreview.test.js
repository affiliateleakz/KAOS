import {it,expect} from 'vitest';
import {commissionPreview} from './affiliatePreview';
it('uses membership rates and rounds each qualifying payment before multiplying referrals',()=>{
 expect(commissionPreview(4900,[10,0,0],[1,0,0]).total).toBe(490);
 expect(commissionPreview(4900,[30,15,0],[1,0,0]).total).toBe(1470);
 expect(commissionPreview(4900,[50,25,5],[1,1,1]).total).toBe(3920);
 expect(commissionPreview(11,[5,0,0],[3,0,0]).total).toBe(3);
 expect(commissionPreview(4900,[50,25,5],[0,0,0]).total).toBe(0);
});
it('rejects invalid financial inputs',()=>{
 expect(commissionPreview(-1,[10,0,0],[1,0,0])).toBeNull();
 expect(commissionPreview(4900,[10,0],[1,0,0])).toBeNull();
 expect(commissionPreview(4900,[10,0,0],[1.5,0,0])).toBeNull();
});
