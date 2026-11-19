/* Restore an authorized chart session after sign-in and broker navigation.
   Connection uses the existing server/device gate; no Start Bot/order messages. */
(function () {
  'use strict';
  var ready = false, attached = false, connecting = false, generation = 0;
  function verified(state) {
    return !!(state && state.step === 'DASHBOARD' && state.status === 'CONNECTED' &&
      state.license && state.license.authorized &&
      (state.platform === 'pocketoption' || state.platform === 'pocket_option'));
  }
  function refreshCharts() {
    if (ready && attached) {
      window.__kaosChartSessionAuthorized = true;
      if (typeof startFlow === 'function') startFlow();
      if (typeof kaosStartChartFeed === 'function') kaosStartChartFeed();
    }
  }
  function connect() {
    if (!ready || attached || connecting) { refreshCharts(); return; }
    connecting = true;
    var current = generation;
    chrome.runtime.sendMessage({ type: 'KAOS_CONNECT_PLATFORM', platform: 'pocketoption', remember: true }, function (response) {
      var error = chrome.runtime.lastError;
      if (current !== generation) return;
      connecting = false;
      if (error || !response || !response.ok || !verified(response.state)) {
        if (typeof setCheckMsg === 'function') setCheckMsg(response && response.error || 'Chart connection failed. Select your broker and try again.');
        if (window.KAOSBroker) window.KAOSBroker.show(response && response.error || 'Chart connection failed. Try connecting again.');
        return;
      }
      attached = true;
      refreshCharts();
    });
  }
  document.addEventListener('kaos-cloud-state-changed', function (event) {
    chrome.storage.local.get('kaosSelectedBroker', function(saved) {
      if (saved.kaosSelectedBroker === 'coinbase') {ready=false;attached=false;connecting=false;generation++;window.__kaosChartSessionAuthorized=false;if(typeof kaosStopChartFeed==='function')kaosStopChartFeed();return;}
    var detail = event.detail || {};
    ready = verified(detail.state);
    if (!ready) { attached = false; connecting = false; generation++; window.__kaosChartSessionInitialized = false; window.__kaosChartSessionAuthorized = false; if(typeof kaosStopChartFeed === 'function')kaosStopChartFeed(); return; }
    if (detail.brokerAttached) attached = true;
    connect();
    });
  });
  if (chrome.tabs && chrome.tabs.onUpdated) {
    chrome.tabs.onUpdated.addListener(function (tabId, change) {
      if (!ready || !attached || change.status !== 'complete') return;
      chrome.storage.local.get(['KAOSTargetTabId'], function (saved) {
        if (saved.KAOSTargetTabId === tabId) refreshCharts();
      });
    });
  }
})();
