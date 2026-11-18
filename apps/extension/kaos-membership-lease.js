/* Shared deadline check. Blocks new entries; never closes broker positions. */
(function(root){
 'use strict';
 function allowed(deadline,at){if(deadline==null)return true;const end=Date.parse(deadline);return Number.isFinite(end)&&end>(at==null?Date.now():at);}
 function fromLicense(license){return license?.membershipStatus==='TRIAL'?(license.expiresAt||'INVALID_TRIAL_DEADLINE'):null;}
 const lease={allowed,fromLicense};root.KaosMembershipLease=lease;
 if(typeof module!=='undefined')module.exports=lease;
})(globalThis);
