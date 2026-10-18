'use strict';document.getElementById('kaos-open-backtester')?.addEventListener('click',()=>{chrome.tabs.create({url:chrome.runtime.getURL('kaos-backtest.html')});});
