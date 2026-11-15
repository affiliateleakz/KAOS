/* Presentation only. Never sends broker commands or changes trading state. */
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
    });
    function update() {
      const authorized = window.__kaosChartSessionAuthorized === true;
      const running = typeof state !== 'undefined' && state.running === true;
      const demo = authorized && typeof terminalData !== 'undefined' ? terminalData?.accountIsDemo : null;
      document.querySelectorAll('.kaos-session-strip').forEach(bar => {
        bar.querySelector('[data-session-status=connection]').textContent = authorized ? 'Broker connected' : 'Broker not connected';
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
