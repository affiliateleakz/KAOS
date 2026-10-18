document.getElementById('kaos-open-research')?.addEventListener('click',()=>chrome.tabs.create({url:chrome.runtime.getURL('kaos-research.html')}));
