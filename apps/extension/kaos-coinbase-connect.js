/* Coinbase credentials are configured on the authenticated KAOS API page. */
(()=>{'use strict';
document.addEventListener('kaos-coinbase-setup',()=>{
 window.KAOSBroker?.choose('coinbase');
});
})();
