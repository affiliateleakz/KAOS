/**
 * KAOS Cloud UI — startup/auth/platform overlay + compact post-connect status control.
 *
 * This is the ONLY user-facing surface of the KAOS cloud layer. It is intentionally a thin overlay
 * that appears BEFORE the trading dashboard (login → membership/entitlement/device → platform), and
 * collapses to a compact status pill once connected so it never consumes trading-screen space.
 * It talks only to background.js (KaosCloud) via chrome.runtime.sendMessage — no direct API calls,
 * no broker interaction. Injected both on Pocket Option pages and inside the floating popup window.
 */
(function () {
  'use strict';
  if (window.__KAOS_CLOUD_UI__) return;
  window.__KAOS_CLOUD_UI__ = true;
  if (!(chrome && chrome.runtime && chrome.runtime.sendMessage)) return;

  var STATUS_LABEL = {
    CONNECTED: 'KAOS CLOUD · CONNECTED',
    OFFLINE: 'KAOS CLOUD · OFFLINE',
    LICENSE_INVALID: 'LICENSE INVALID',
    DEVICE_NOT_AUTHORIZED: 'DEVICE NOT AUTHORIZED',
    SESSION_EXPIRED: 'SESSION EXPIRED',
    LOGGED_OUT: 'SIGN IN REQUIRED'
  };

  function send(msg) {
    return new Promise(function (resolve) {
      try { chrome.runtime.sendMessage(msg, function (r) { void chrome.runtime.lastError; resolve(r || { ok: false }); }); }
      catch (e) { resolve({ ok: false, error: String(e) }); }
    });
  }

  var host, overlay;
  function mount() {
    if (host) return;
    host = document.createElement('div');
    host.id = 'kaos-cloud-root';
    (document.body || document.documentElement).appendChild(host);
  }
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

  function clear() { if (host) host.innerHTML = ''; }

  function brandHeader() {
    var h = el('div', 'kaos-brand');
    h.appendChild(el('div', 'kaos-mark', '\u16A0')); // Valknut-ish rune glyph
    var t = el('div', 'kaos-brand-text');
    t.appendChild(el('div', 'kaos-brand-title', 'KAOS TRADING'));
    t.appendChild(el('div', 'kaos-brand-sub', 'YOUR BOT. YOUR DATA. YOUR KAOS.'));
    h.appendChild(t);
    return h;
  }

  function panel() {
    clear();
    overlay = el('div', 'kaos-overlay');
    var card = el('div', 'kaos-card');
    overlay.appendChild(card);
    host.appendChild(overlay);
    card.appendChild(brandHeader());
    return card;
  }

  function renderLogin(state) {
    var card = panel();
    card.setAttribute('data-testid', 'kaos-login-panel');
    var status = (state && state.status) || 'LOGGED_OUT';
    if (status === 'SESSION_EXPIRED') card.appendChild(el('div', 'kaos-alert', 'Your KAOS session expired — please sign in again.'));
    var step = el('div', 'kaos-step', 'STEP 1 · SIGN IN TO KAOS');
    card.appendChild(step);
    card.appendChild(el('h1', 'kaos-login-heading', 'Welcome to your trading desk'));
    card.appendChild(el('p', 'kaos-muted', 'Sign in to connect your broker, monitor charts and manage your bot.'));
    var email = el('input', 'kaos-input'); email.type = 'email'; email.placeholder = 'Email'; email.setAttribute('data-testid', 'kaos-login-email');
    var pass = el('input', 'kaos-input'); pass.type = 'password'; pass.placeholder = 'Password'; pass.setAttribute('data-testid', 'kaos-login-password');
    email.id = 'kaos-signin-email'; email.autocomplete = 'username';
    pass.id = 'kaos-signin-password'; pass.autocomplete = 'current-password';
    var emailLabel = el('label', 'kaos-field-label', 'Email address'); emailLabel.htmlFor = email.id;
    var passwordLabel = el('label', 'kaos-field-label', 'Password'); passwordLabel.htmlFor = pass.id;
    card.appendChild(emailLabel); card.appendChild(email); card.appendChild(passwordLabel); card.appendChild(pass);
    var recovery = el('a', 'kaos-link kaos-recovery', 'Forgot password?');
    recovery.href = 'https://tradingwithkaos.com/forgot-password'; recovery.target = '_blank'; recovery.rel = 'noopener noreferrer'; card.appendChild(recovery);
    var err = el('div', 'kaos-error'); err.setAttribute('role', 'alert'); err.style.display = 'none'; card.appendChild(err);

    var google = el('button', 'kaos-btn kaos-btn-google', 'G  CONTINUE WITH GOOGLE');
    google.type = 'button';
    google.setAttribute('data-testid', 'kaos-login-google');
    google.onclick = async function () {
      err.style.display = 'none'; google.disabled = true; google.textContent = 'CONNECTING TO GOOGLE…';
      var result = await send({ type: 'KAOS_GOOGLE_LOGIN' });
      google.disabled = false; google.textContent = 'G  CONTINUE WITH GOOGLE';
      if (!result || !result.ok) { err.textContent = (result && result.error) || 'Google sign-in failed'; err.style.display = 'block'; return; }
      route(result.state);
    };
    card.appendChild(google);

    var divider = el('div', 'kaos-login-divider', 'OR SIGN IN WITH EMAIL');
    card.appendChild(divider);

    var btn = el('button', 'kaos-btn kaos-btn-gold', 'SIGN IN'); btn.setAttribute('data-testid', 'kaos-login-submit');
    card.appendChild(btn);
    btn.onclick = async function () {
      if (btn.disabled) return;
      if (!email.value.trim() || !pass.value) { err.textContent = 'Enter your email address and password.'; err.style.display = 'block'; return; }
      err.style.display = 'none'; btn.disabled = true; btn.textContent = 'VERIFYING…';
      var r = await send({ type: 'KAOS_LOGIN', email: email.value.trim(), password: pass.value });
      btn.disabled = false; btn.textContent = 'SIGN IN';
      if (!r || !r.ok) { err.textContent = (r && r.error) || 'Login failed'; err.style.display = 'block'; return; }
      route(r.state);
    };
    pass.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    email.onkeydown = function (e) { if (e.key === 'Enter') btn.click(); };
    var foot = el('div', 'kaos-foot');
    var link = el('a', 'kaos-link', 'Need an account? Join KAOS →'); link.href = 'https://tradingwithkaos.com/register'; link.target = '_blank';
    foot.appendChild(link);
    card.appendChild(foot);
  }

  function renderOffline() {
    var card = panel(); card.setAttribute('data-testid', 'kaos-offline-panel');
    card.appendChild(el('div', 'kaos-status-big kaos-red', 'KAOS CLOUD · OFFLINE'));
    card.appendChild(el('div', 'kaos-muted', 'KAOS account connection could not be completed. Pocket Option is separate and remains available. Retry the KAOS connection below.'));
    var btn = el('button', 'kaos-btn kaos-btn-green', 'RETRY CONNECTION'); btn.setAttribute('data-testid', 'kaos-offline-retry');
    btn.onclick = async function () { route(await refreshState()); };
    card.appendChild(btn);
    var local = el('button', 'kaos-btn kaos-btn-ghost', 'CONTINUE WITH LOCAL BOT');
    local.setAttribute('data-testid','kaos-offline-local');
    local.onclick = function () {
      clear();
      var wrap=el('div','kaos-pill-wrap');
      wrap.appendChild(el('span','kaos-dot kaos-dot-red'));
      wrap.appendChild(el('span','kaos-pill-text','KAOS CLOUD · OFFLINE · LOCAL BOT ACTIVE'));
      host.appendChild(wrap);
    };
    card.appendChild(local);
  }

  function renderBlocked(state) {
    var card = panel(); card.setAttribute('data-testid', 'kaos-blocked-panel');
    var st = state.status || 'LICENSE_INVALID';
    card.appendChild(el('div', 'kaos-status-big kaos-red', STATUS_LABEL[st] || st));
    var reasons = (state.license && state.license.reasons) || [];
    if (state.detail) card.appendChild(el('div', 'kaos-muted', state.detail));
    else if (st === 'DEVICE_NOT_AUTHORIZED') card.appendChild(el('div', 'kaos-muted', 'This installation is not authorized. Check your registered devices or account access.'));
    else {
      var msgs = (state.license && state.license.reasonMessages) || [];
      if (msgs.length) msgs.forEach(function (m) { card.appendChild(el('div', 'kaos-muted', m)); });
      else card.appendChild(el('div', 'kaos-muted', 'Your KAOS membership or entitlement is not active. ' + (reasons.length ? '(' + reasons.join(', ') + ')' : '')));
    }
    var deviceProblem = st === 'DEVICE_NOT_AUTHORIZED' || st === 'DEVICE_REGISTRATION_FAILED';
    var manage = el('a', 'kaos-btn kaos-btn-gold', deviceProblem ? 'MANAGE DEVICES' : 'MANAGE MEMBERSHIP'); manage.href = deviceProblem ? 'https://tradingwithkaos.com/dashboard/devices' : 'https://tradingwithkaos.com/dashboard'; manage.target = '_blank';
    manage.setAttribute('data-testid', 'kaos-blocked-manage');
    card.appendChild(manage);
    var row = el('div', 'kaos-row');
    var retry = el('button', 'kaos-btn kaos-btn-ghost', 'RE-CHECK'); retry.setAttribute('data-testid', 'kaos-blocked-retry');
    retry.onclick = async function () { route(await refreshState()); };
    var out = el('button', 'kaos-btn kaos-btn-ghost', 'SIGN OUT'); out.setAttribute('data-testid', 'kaos-blocked-logout');
    out.onclick = async function () { await send({ type: 'KAOS_LOGOUT' }); route({ step: 'LOGIN', status: 'LOGGED_OUT' }); };
    row.appendChild(retry); row.appendChild(out); card.appendChild(row);
  }

  async function renderPlatform(state) {
    var card = panel(); card.setAttribute('data-testid', 'kaos-platform-panel');
    card.appendChild(el('div', 'kaos-step', 'CHOOSE YOUR TRADING PLATFORM'));
    var listWrap = el('div', 'kaos-platforms');
    card.appendChild(listWrap);
    var remember = el('label', 'kaos-check');
    var cb = el('input'); cb.type = 'checkbox'; cb.setAttribute('data-testid', 'kaos-remember-platform');
    remember.appendChild(cb); remember.appendChild(el('span', null, 'Remember My Platform'));
    var res = await send({ type: 'KAOS_GET_PLATFORMS' });
    var plats = (res && res.platforms) || [{ id: 'pocket_option', name: 'Pocket Option', status: 'SUPPORTED' }];
    var groups={};
    [['direct','Browser connections'],['keys','API-key brokers'],['upcoming','Other brokers · coming soon']].forEach(function(entry){
      listWrap.appendChild(el('h3','kaos-step',entry[1]));var box=el('div','kaos-platforms');groups[entry[0]]=box;listWrap.appendChild(box);
    });
    plats.forEach(function (p) {
      var coinbase = p.id === 'coinbase';
      var supported = coinbase || (p.status || 'SUPPORTED') === 'SUPPORTED';
      var rowc = el('div', 'kaos-plat' + (supported ? '' : ' kaos-plat-soon'));
      rowc.appendChild(el('div', 'kaos-plat-name', p.name || p.id));
      var connect = el('button', 'kaos-btn kaos-btn-green', coinbase ? 'SET UP COINBASE' : supported ? 'CONNECT' : 'COMING SOON');
      connect.disabled = !supported;
      connect.setAttribute('data-testid', 'kaos-connect-' + (p.id || 'platform'));
      connect.onclick = async function () {
        if (coinbase) {
          if (window.KAOSBroker) {
            clear();
            await window.KAOSBroker.refresh();
            window.KAOSBroker.show();
            await window.KAOSBroker.choose('coinbase');
          } else {
            window.open('https://tradingwithkaos.com/dashboard/api?broker=coinbase','_blank','noopener,noreferrer');
            connect.textContent = 'OPEN KAOS API SETUP';
          }
          return;
        }
        connect.disabled = true; connect.textContent = 'CONNECTING…';
        var r = await send({ type: 'KAOS_CONNECT_PLATFORM', platform: p.id, remember: cb.checked });
        if (!r || !r.ok) {
          connect.disabled = false; connect.textContent = 'CONNECT';
          return;
        }
        var next = r.state || await refreshState();
        route(next);
      };
      rowc.appendChild(connect);
      var group=coinbase||['kraken','binanceus','binance_us'].includes(p.id)?'keys':supported?'direct':'upcoming';
      groups[group].appendChild(rowc);
    });
    card.appendChild(remember);
  }

  function pill(state) {
    clear();
    var wrap = el('div', 'kaos-pill-wrap');
    wrap.setAttribute('data-testid', 'kaos-status-pill');
    var st = (state && state.status) || 'CONNECTED';
    var dot = el('span', 'kaos-dot ' + (st === 'CONNECTED' ? 'kaos-dot-green' : 'kaos-dot-red'));
    var cloud = el('span', 'kaos-pill-text', STATUS_LABEL[st] || st);
    var platName = (state && state.platform) ? String(state.platform).replace('_', ' ').toUpperCase() : null;
    wrap.appendChild(dot); wrap.appendChild(cloud);
    if (platName) { wrap.appendChild(el('span', 'kaos-pill-sep', '·')); wrap.appendChild(el('span', 'kaos-pill-text', platName + ' · CONNECTED')); }
    var menuBtn = el('button', 'kaos-pill-btn', '▾'); menuBtn.setAttribute('data-testid', 'kaos-pill-menu');
    wrap.appendChild(menuBtn);
    var menu = el('div', 'kaos-menu'); menu.style.display = 'none';
    var acct = el('button', 'kaos-menu-item', 'Account'); acct.setAttribute('data-testid', 'kaos-menu-account');
    acct.onclick = function () { window.open('https://tradingwithkaos.com/dashboard', '_blank'); };
    var sw = el('button', 'kaos-menu-item', 'Switch Platform'); sw.setAttribute('data-testid', 'kaos-menu-switch');
    sw.onclick = async function () { await send({ type: 'KAOS_SELECT_PLATFORM', platform: state.platform, remember: false }); route(await refreshState()); };
    var cs = el('button', 'kaos-menu-item', 'Cloud Status'); cs.setAttribute('data-testid', 'kaos-menu-status');
    cs.onclick = async function () { route(await refreshState()); };
    var out = el('button', 'kaos-menu-item kaos-menu-danger', 'Sign Out'); out.setAttribute('data-testid', 'kaos-menu-logout');
    out.onclick = async function () { await send({ type: 'KAOS_LOGOUT' }); route({ step: 'LOGIN', status: 'LOGGED_OUT' }); };
    [acct, sw, cs, out].forEach(function (b) { menu.appendChild(b); });
    menuBtn.onclick = function () { menu.style.display = menu.style.display === 'none' ? 'block' : 'none'; };
    wrap.appendChild(menu);
    host.appendChild(wrap);
  }

  function chartSessionState(state) {
    if (!state) return null;
    // DOM events can be observed by the broker page. Never publish account data.
    return { step: state.step, status: state.status, platform: state.platform,
      license: { authorized: !!(state.license && state.license.authorized) } };
  }

  function route(state) {
    document.dispatchEvent(new CustomEvent('kaos-cloud-state-changed', { detail: { state: chartSessionState(state) } }));
    mount();
    if (!state) { renderOffline(); return; }
    switch (state.step) {
      case 'LOGIN': renderLogin(state); break;
      case 'OFFLINE': renderOffline(); break;
      case 'BLOCKED': renderBlocked(state); break;
      case 'PLATFORM':
        if (document.getElementById('kaos-broker-overlay')) { pill(state); if(window.KAOSBroker)window.KAOSBroker.refresh(); }
        else renderPlatform(state);
        break;
      case 'DASHBOARD': pill(state); break;
      default: renderLogin(state);
    }
  }

  async function refreshState() { var r = await send({ type: 'KAOS_STARTUP' }); return r && r.state ? r.state : { step: 'OFFLINE', status: 'OFFLINE' }; }

  async function boot() { mount(); route(await refreshState()); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
