document.getElementById('kaos-micro-paper-open')?.addEventListener('click',()=>chrome.tabs.create({url:chrome.runtime.getURL('kaos-micro-paper.html')}));
