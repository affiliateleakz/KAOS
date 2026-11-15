/* Presentation and explicit navigation/Stop controls. Never starts trading automatically. */
(() => {
  function mount() {
    document.querySelectorAll('.kaos-app-workspace,.kaos-terminal-workspace').forEach(workspace => {
      const bar = document.createElement('div');
      bar.className = 'kaos-session-strip';
      bar.setAttribute('aria-label', 'Trading session status');
      for (const key of ['connection', 'account', 'bot']) {
        const item = document.createElement('span'); item.dataset.sessionStatus = key; bar.appendChild(item);
      }
      const size = document.createElement('button');size.type='button';size.dataset.sessionSize='';
      size.addEventListener('click',()=>{
        const mode=document.body.classList.contains('kaos-mini')?'max':'mini';
        document.querySelector('.kaos-view-btn[data-kaos-mode="'+mode+'"]')?.click();
      });bar.appendChild(size);
      const stop = document.createElement('button'); stop.type = 'button'; stop.textContent = 'Stop bot';
      stop.dataset.sessionStop = ''; stop.addEventListener('click', () => { if (typeof stopBot === 'function') stopBot(); });
      bar.appendChild(stop); workspace.prepend(bar);
      if(document.body.classList.contains('kaos-companion')){
        const nav=document.createElement('nav');nav.className='kaos-companion-nav';nav.setAttribute('aria-label','Bot navigation');
        for(const [view,label] of [['dashboard','Bot'],['strategy','Strategy'],['risk','Risk'],['history','Trades'],['settings','Settings']]){
          const button=document.createElement('button');button.type='button';button.textContent=label;button.dataset.companionView=view;
          button.addEventListener('click',()=>window.kaosRoute?.(view));nav.appendChild(button);
        }
        const website=document.createElement('a');website.href='https://tradingwithkaos.com/dashboard';website.target='_blank';website.rel='noopener noreferrer';website.textContent='KAOS website';nav.appendChild(website);
        bar.appendChild(nav);
        if(workspace.closest('#screen-main')){
          const note=document.createElement('section');note.className='kaos-companion-summary';
          const title=document.createElement('h1');title.textContent='Your trading command center';
          const asset=document.createElement('p');asset.dataset.companionAsset='';asset.textContent='Select a market in Pocket Option';
          const hint=document.createElement('p');hint.dataset.companionGuidance='';hint.setAttribute('role','status');hint.textContent='Checking your broker connection…';
          const broker=document.createElement('button');broker.type='button';broker.textContent='Show Pocket Option';
          broker.addEventListener('click',async()=>{try{const tab=await getKAOSTargetTab();if(tab){await chrome.tabs.update(tab.id,{active:true});if(tab.windowId!=null)await chrome.windows.update(tab.windowId,{focused:true});}}catch(_){}});
          note.append(title,asset,hint,broker);bar.after(note);
        }
      }
    });
    function update() {
      const authorized = window.__kaosChartSessionAuthorized === true;
      const running = typeof state !== 'undefined' && state.running === true;
      const fresh = authorized && typeof terminalData !== 'undefined' && terminalData?.engineReady === true && typeof kaosCompanionStatusAt !== 'undefined' && Date.now()-kaosCompanionStatusAt < 15000;
      const demo = fresh ? terminalData.accountIsDemo : null;
      const connection = !authorized ? 'Broker not connected' : fresh ? 'Broker responding' : 'Broker connection unconfirmed';
      if(document.body.classList.contains('kaos-companion')){
        const asset=document.querySelector('[data-companion-asset]');
        if(asset)asset.textContent=fresh&&terminalData.asset?terminalData.asset:'No current market confirmed';
        const hint=document.querySelector('[data-companion-guidance]');
        if(hint)hint.textContent=!fresh?'Open Pocket Option and check that you are signed in. Broker status is unavailable; the bot may still be running.':demo===null?'Confirm Demo or Real in Pocket Option before starting.':running?'Bot is running. Use Stop bot to request a stop; check open positions in Pocket Option.':!terminalData.asset?'Select a market in Pocket Option, then review your strategy and risk settings.':demo===false?'Real account selected. Review your stake and risk limits before you choose Start KAOS.':'Demo account selected. Review your strategy and risk limits, then choose Start KAOS.';
        document.querySelectorAll('[data-companion-view]').forEach(button=>{
          const active=button.closest('#screen-main')?.classList.contains('view-'+button.dataset.companionView);
          if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
        });
      }
      document.querySelectorAll('.kaos-session-strip').forEach(bar => {
        bar.querySelector('[data-session-status=connection]').textContent = connection;
        const account = bar.querySelector('[data-session-status=account]');
        account.textContent = demo === true ? 'DEMO ACCOUNT' : demo === false ? 'REAL ACCOUNT' : 'Account type unconfirmed';
        account.dataset.real = String(demo === false);
        bar.querySelector('[data-session-status=bot]').textContent = running ? 'BOT RUNNING' : 'BOT STOPPED';
        const stop = bar.querySelector('[data-session-stop]'); stop.disabled = !running;
        bar.querySelector('[data-session-size]').textContent=document.body.classList.contains('kaos-mini')?'Expand':'Compact beside broker';
      });
      document.querySelectorAll('.kaos-nav-btn[data-kaos-view]').forEach(button => {
        const screen = button.closest('.screen');
        const active = screen?.classList.contains('view-' + button.dataset.kaosView) || button.classList.contains('active');
        if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
      });
    }
    update(); setInterval(update, 1000);
  }
  document.addEventListener('DOMContentLoaded', mount, {once:true});
})();
