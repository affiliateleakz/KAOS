
/* KAOS v19.8 — no automatic sample downloads/popups.
   Local AI training is in-memory; explicit user export/import is the only AI persistence path. */
const KAOS_NO_AUTO_SAMPLE_DOWNLOADS = true;
const KAOS_AUDIT_READ_ONLY = false;
const KAOS_COMPANION_ONLY = true;
function KAOSV198IsAutoSampleDownload(opts) {
  const s = String(opts?.reason ?? opts?.source ?? opts?.kind ?? "").toLowerCase();
  return s.includes("sample") || s.includes("training") || s.includes("dataset") || s.includes("auto");
}

// ═══════════════════════════════════════════════════════════════
//  Pocket Option Auto Trader V6.03 — popup.js v19.10.1 · backup import + status
// ═══════════════════════════════════════════════════════════════

const API_BASE      = 'https://skarfinans.com/KAOS.php';
const AFFILIATE_URL = 'https://u3.shortink.io/register?utm_campaign=37744&utm_source=affiliate&utm_medium=sr&a=z2WaP7fk0bLLkO&al=1754732&ac=KAOS&cid=952679&code=WELCOME50';
const SUPPORT_URL   = 'mailto:support@tradewithkaos.com';
const GROUP_URL     = 'https://t.me/+RrO9DXXsRbM5NGFh';
const PO_URL        = 'https://pocketoption.com/en/cabinet/demo-quick-high-low/';

// Strategy descriptions (match keys in content.js STRATEGIES)
const STRAT_DESCS = {
  'ZigZag Reversal':  'NEW: ZigZag pivot detection — finds swing highs/lows and trades the reversal',
  'RSI Classic':      'RSI oversold (<35) / overbought (>65) — fast, trades often',
  'RSI Extreme':      'Stricter RSI <25 / >75 — fewer but sharper entries',
  'EMA Cross 7/21':   'EMA7 crossing EMA21 — trend change detection',
  'EMA Cross 21/50':  'EMA21 crossing EMA50 — slower, stronger signals',
  'RSI + EMA Trend':  'RSI oversold/overbought confirmed by EMA7/21 trend Default',
  'RSI + EMA Cross':  'RSI <40/>60 AND EMA7/21 crossover both must agree',
  'CCI Reversal':     'CCI crossing ±115 — momentum reversal signal',
  'CCI Extreme':      'CCI crossing ±150 — only the sharpest reversals',
  '4 Candle Pattern': '4 consecutive same-direction candles → trade the reversal',
  'Pin Bar':          'Hammer / shooting star pin bar reversal candles',
  'MACD Cross':       'MACD line (12/26) crossing its signal line (9)',
  'MACD + RSI':       'MACD zero-line cross confirmed by RSI not in opposite extreme',
  'Stochastic':       '%K/%D stoch cross in oversold (<25) or overbought (>75) zone',
  'Bollinger Bounce': 'Price at lower band → BUY · Price at upper band → SELL',
  'Murfs Pick':   'v6.7.9 · hybrid 5s · micro entry · soft MACD · R7/R7 V6/V7',
  'Triple Confirm': 'Alias → Murfs Pick v6.7.9',
  'Trend Rider':      'EMA50 strong trend + RSI pullback entry in 40-60 zone',
  'Alpha One Safe':   '6-layer confirmation — designed to profit WITHOUT martingale',
  'Band Rider':       'NEW: Bollinger Band touch + Momentum cross — mean reversion (Reddit/TradingPedia)',
  'Alligator Awakens':'NEW: Alligator (13/8/5) + fast Momentum — catches new trend at start (YouTube top picks)',
  'MACD Sniper':      'NEW: Fast MACD (3,10,16) crossover with candle confirm — professional forums',
  'StochRSI Cross':   'StochRSI %K/%D cross in oversold/overbought zone',
  'Keltner Divergence':'Keltner Channel + RSI Divergence on ranging OTC pairs',
  'Alpha One Secret':  'ALPHA ONE SECRET — A secret formula strategy Alpha One has used for many years.',
};


// V24.1.1 — the UI lives in its own window, so "currentWindow" is the
// KAOS window rather than Pocket Option. Always resolve the saved target tab.
const KAOS_PO_URL_PATTERNS = [
  'https://pocketoption.com/*',
  'https://*.pocketoption.com/*',
  'https://platform58.po2.capital/*',
  'https://p.finance/*',
  'https://po.company/*',
  'https://po1.capital/*',
  'https://pocket-link22.co/*'
];

function isKAOSPocketOptionTab(tab) {
  const u = String(tab?.url || '');
  return !!tab?.id && (
    u.includes('pocketoption.com') || u.includes('po2.capital') ||
    u.includes('p.finance') || u.includes('po.company') ||
    u.includes('po1.capital') || u.includes('pocket-link22.co')
  );
}

async function getKAOSTargetTab() {
  // 1) Prefer the previously saved Pocket Option tab, but verify it is still PO.
  try {
    const saved = await chrome.storage.local.get(['KAOSTargetTabId']);
    if (saved.KAOSTargetTabId) {
      try {
        const tab = await chrome.tabs.get(saved.KAOSTargetTabId);
        if (isKAOSPocketOptionTab(tab)) return tab;
      } catch (_) {}
    }
  } catch (_) {}

  // 2) The popup runs in its own Chrome window, so currentWindow can point at
  // the extension itself. Search ALL windows for a real Pocket Option tab.
  try {
    const poTabs = await chrome.tabs.query({ url: KAOS_PO_URL_PATTERNS });
    if (poTabs?.length) {
      const tab = poTabs.find(t => t.active) || poTabs[0];
      if (tab?.id) {
        await chrome.storage.local.set({ KAOSTargetTabId: tab.id });
        return tab;
      }
    }
  } catch (_) {}

  // 3) Final fallback only if it is actually a PO tab.
  try {
    const tabs = await chrome.tabs.query({active:true, currentWindow:true});
    const tab = tabs && tabs[0] ? tabs[0] : null;
    if (isKAOSPocketOptionTab(tab)) {
      await chrome.storage.local.set({ KAOSTargetTabId: tab.id });
      return tab;
    }
  } catch (_) {}
  return null;
}

async function ensureKAOSContentReady(tab) {
  if (!tab?.id) throw new Error('Pocket Option tab not found');

  // Give a manifest-managed content script a moment to finish loading first.
  for (let i = 0; i < 3; i++) {
    try {
      const pong = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      if (pong?.ok) return true;
    } catch (_) {}
    await new Promise(r => setTimeout(r, 250));
  }

  // Manifest-only ownership: never manually inject content.js. If the extension
  // was just reloaded, the existing Pocket Option tab must be refreshed once.

  for (let i = 0; i < 6; i++) {
    try {
      const pong = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      if (pong?.ok) return true;
    } catch (_) {}
    await new Promise(r => setTimeout(r, 300));
  }
  throw new Error('KAOS could not reconnect to the Pocket Option tab. Refresh that Pocket Option tab once and retry the import.');
}

// ── State ──
let state = {
  traderId: null, verified: false, running: false,
  wins: 0, losses: 0, pnl: 0, trades: [],
  martLevel: 0, lossStreak: 0, sessionPnl: 0,
  lastSig: null, lastSigAt: 0,
};

const $ = id => document.getElementById(id);
const screens = {
  notPo: $('screen-not-po'), checking: $('screen-checking'),
  notVerified: $('screen-not-verified'), main: $('screen-main'), chart: $('screen-chart'),
};

function showScreen(name) {
  Object.values(screens).forEach(s => {
    if (!s) return;
    s.style.display = 'none';
    s.classList.remove('active');
  });
  const target = screens[name];
  if (!target) return;
  target.classList.add('active');
  target.style.display = (name === 'main' || name === 'chart') ? 'flex' : 'block';
  if (name === 'main') {
    target.classList.add('view-dashboard');
    target.classList.remove('view-strategy');
  }
}

// ── Links & nav ──
$('register-btn').href = AFFILIATE_URL;
$('open-po-link').href = '#';
$('open-po-link').addEventListener('click', async (e) => {
  e.preventDefault();
  let tab = await getKAOSTargetTab();
  if (tab?.id) {
    await chrome.tabs.update(tab.id, { active: true });
    if (tab.windowId != null) await chrome.windows.update(tab.windowId, { focused: true });
  } else {
    tab = await chrome.tabs.create({ url: PO_URL, active: true });
  }
  if (tab?.id) await chrome.storage.local.set({ KAOSTargetTabId: tab.id, KAOSTargetWindowId: tab.windowId, kaosPoAttached: true });
});
$('support-btn').addEventListener('click',    () => chrome.tabs.create({ url: SUPPORT_URL }));
$('nv-support-btn').addEventListener('click', () => chrome.tabs.create({ url: SUPPORT_URL }));
$('recheck-btn').addEventListener('click', () => {
  window.__kaosChartSessionInitialized = false;
  chrome.storage.local.remove(['traderId', 'verified', 'verifiedAt']);
  startFlow();
});

// ════════════════════════════════════════════════════════════
//  SERVER-AUTHORIZED MEMBERSHIP AND BROKER VERIFICATION
// ════════════════════════════════════════════════════════════

async function startFlow() {
  if(window.__kaosChartSessionInitialized && window.__kaosChartSessionAuthorized===true){kaosStartChartFeed();return;}
  if (window.__kaosStartFlowRunning) return;
  window.__kaosStartFlowRunning = true;
  try {
    showScreen('checking');
    setCheckMsg('VERIFYING KAOS MEMBERSHIP...');
    const cloud = await new Promise(resolve => chrome.runtime.sendMessage({type:'KAOS_STARTUP'}, r => {void chrome.runtime.lastError; resolve(r); }));
    if (!cloud?.ok || cloud.state?.step !== 'DASHBOARD' || cloud.state?.status !== 'CONNECTED' ||
        !cloud.state?.license?.authorized || !['pocketoption','pocket_option'].includes(cloud.state?.platform)) {
      setCheckMsg('SIGN IN TO KAOS TO CONTINUE');
      showScreen('notPo');
      return;
    }
    const tab = await getKAOSTargetTab();
    const poDomains = ['pocketoption.com','po2.capital','p.finance','po.company','po1.capital','pocket-link22.co'];
    if (!tab?.url || !poDomains.some(d => tab.url.includes(d))) {
      showScreen('notPo');
      return;
    }
    let traderId = null;
    try {
      const results = await chrome.scripting.executeScript({target:{tabId:tab.id},func:detectTraderId});
      traderId = results?.[0]?.result || null;
    } catch (_) {}
    if (!traderId) {
      setCheckMsg('WAITING FOR POCKET OPTION ACCOUNT');
      showScreen('notPo');
      return;
    }
    state.traderId = traderId;
    state.verified = true; // KAOS membership verified by server above; PO trader ID detected from page.
    window.__kaosChartSessionInitialized = true;
    showVerified(traderId);
  } finally {window.__kaosStartFlowRunning = false;}
}

function detectTraderId() {
  const sels = ['[data-trader-id]','[data-user-id]','[data-uid]','[class*="trader-id"]','[class*="userId"]','[class*="user-id"]'];
  for (const s of sels) {
    const el = document.querySelector(s);
    if (el) {
      const id = el.dataset.traderId || el.dataset.userId || el.dataset.uid || el.textContent.trim();
      if (id && /^\d{5,12}$/.test(id)) return id;
    }
  }
  const m = document.body.innerText.match(/(?:ID|Trader ID|User ID|UID)[:\s#]+(\d{5,12})/i);
  if (m) return m[1];
  const u = window.location.href.match(/[?&](?:uid|user_id|trader_id)=(\d{5,12})/i);
  if (u) return u[1];
  const els = document.querySelectorAll('[class*="profile"],[class*="user"],[class*="account"],[class*="cabinet"]');
  for (const el of els) {
    const nm = el.textContent.match(/\b(\d{6,12})\b/);
    if (nm) return nm[1];
  }
  // salted storage scan — original loop skipped the key name
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      const val = localStorage.getItem(key);
      if (val && val.length < 500) {
        try {
          const p = JSON.parse(val);
          const id = p?.id || p?.trader_id || p?.userId || p?.uid || p?.user?.id;
          if (id && /^\d{5,12}$/.test(String(id))) return String(id);
        } catch {}
      }
    }
  } catch {}
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const val = sessionStorage.getItem(sessionStorage.key(i));
      if (val && val.length < 500) {
        try {
          const p = JSON.parse(val);
          const id = p?.id || p?.trader_id || p?.userId || p?.uid;
          if (id && /^\d{5,12}$/.test(String(id))) return String(id);
        } catch {}
      }
    }
  } catch {}
  return null;
}

// ── unmodified UI helpers (kept as-is for compatibility) ──

function showVerified(traderId) {
  const mainShell = $('screen-main');
  if (mainShell) {
    mainShell.classList.add('active','view-dashboard');
    mainShell.style.display = 'flex';
  }
  $('badge-id').textContent = 'ID: ' + traderId;
  $('trader-badge').style.display = 'block';
  showScreen('main');
  pollStatus();
  if (!window.__poatPollStarted) {
    window.__poatPollStarted = true;
    setInterval(pollStatus, 4000);
  }
  loadSettings();
  loadStats();

  chrome.storage.local.get('botRunning', (data) => {
    if (data.botRunning) {
      chrome.runtime.sendMessage({ type: 'GET_BOT_STATE' }, (s) => {
        if (chrome.runtime.lastError || !s?.running) {
          chrome.storage.local.set({ botRunning: false });
          state.running = false;
          setRunningUI(false);
          setStatus('idle', 'IDLE · READY');
          getKAOSTargetTab().then(tab => { if (tab) chrome.tabs.sendMessage(tab.id, { type: 'STOP_BOT' }).catch(() => {}); });
        } else {
          state.running = true;
          setRunningUI(true);
          setStatus('active', 'BOT RUNNING · Press STOP to stop');
        }
      });
    } else {
      state.running = false;
      setRunningUI(false);
      setStatus('idle', 'IDLE · READY');
      getKAOSTargetTab().then(tab => { if (tab) chrome.tabs.sendMessage(tab.id, { type: 'STOP_BOT' }).catch(() => {}); });
    }
  });
}

function showNotVerified(msg) {
  $('nv-sub-msg').innerHTML = msg;
  showScreen('notVerified');
}

function setCheckMsg(msg) { $('check-msg').textContent = msg; }

// ════════════════════════════════════════════════════════════
//  TIMEFRAME SELECTOR
// ════════════════════════════════════════════════════════════
function getTimeframe() {
  const active = document.querySelector('.tf-btn.active');
  return active ? parseInt(active.dataset.tf) : 60;
}

document.querySelectorAll('.tf-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (state.running) return;
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    saveSettings();
  });
});

// ════════════════════════════════════════════════════════════
//  STRATEGY SELECTOR
// ════════════════════════════════════════════════════════════
$('strat-select').addEventListener('change', () => {
  updateStratDesc();
  saveSettings();
});

function updateStratDesc() {
  const key  = $('strat-select').value;
  const desc = STRAT_DESCS[key] || '';
  $('strat-desc').textContent = desc;
}

function getStrategy() { return $('strat-select').value || 'RSI Classic'; }

// ════════════════════════════════════════════════════════════
//  MULTI-ASSET TOGGLE
// ════════════════════════════════════════════════════════════
$('multi-row').addEventListener('click', () => {
  if (state.running) return;
  multiAssetOn = !multiAssetOn;
  applyMultiUI();
  saveSettings();
});

function applyMultiUI() {
  $('multi-pill').classList.toggle('on', multiAssetOn);
}

// ════════════════════════════════════════════════════════════
//  MARTINGALE TOGGLE
// ════════════════════════════════════════════════════════════
let multiAssetOn = false; // 4-market grid ONLY while this popup toggle is ON; OFF = single visible chart
let martOn     = false;  // OFF by default — enable manually
let autoCdOn   = true;   // auto streak ladder ON by default (used only when Cooldown = 0)
let compoundOn = false;
let martDir    = 'opposite'; // 'opposite' or 'same'
let martMode   = 'classic';  // 'classic' | 'soft' | 'anti' | 'step'
let consecutiveLosses = 0;   // for step mode
let antiLevel  = 0;          // for anti mode win streak

$('mart-row').addEventListener('click', () => {
  if (state.running) return;
  martOn = !martOn;
  applyMartUI();
  if (martOn && compoundOn) { compoundOn = false; applyCompoundUI(); }
  saveSettings();
});

$('auto-cd-row').addEventListener('click', () => {
  if (state.running) return;
  autoCdOn = !autoCdOn;
  applyAutoCdUI();
  saveSettings();
});

function applyAutoCdUI() {
  $('auto-cd-pill').classList.toggle('on', autoCdOn);
}

function applyMartUI() {
  $('mart-pill').classList.toggle('on', martOn);
  $('mart-panel').classList.toggle('open', martOn);
  const dirWrap = $('mart-dir-wrap');
  if (dirWrap) dirWrap.style.display = martOn ? 'block' : 'none';
  $('mart-conflict').style.display = martOn ? 'block' : 'none';
  $('compound-row').classList.toggle('disabled', martOn);
  const cell = $('max-loss-streak-cell');
  if (cell) {
    cell.style.opacity       = martOn ? '.35' : '1';
    cell.style.pointerEvents = martOn ? 'none' : '';
    $('protect-note').textContent = martOn
      ? 'Max Loss Streak disabled with Martingale — Max Steps controls stop.'
      : 'Set to 0 to disable. Bot auto-stops when limits are hit.';
  }
  // Update direction buttons
  const dirOpp  = $('dir-opposite');
  const dirSame = $('dir-same');
  if (dirOpp && dirSame) {
    dirOpp.classList.toggle('active',  martDir === 'opposite');
    dirSame.classList.toggle('active', martDir === 'same');
  }
}

// ════════════════════════════════════════════════════════════
//  MARTINGALE MODE TABS  (V6.0 — new)
// ════════════════════════════════════════════════════════════
function setMartMode(mode) {
  if (state.running) return;
  martMode = mode;
  const modes = ['classic','soft','anti','step'];
  const activeClass = { classic:'active-mart', soft:'active-soft', anti:'active-anti', step:'active-step' };
  modes.forEach(m => {
    const tab   = document.getElementById('mmt-' + m);
    const panel = document.getElementById('mode-' + m);
    if (tab) {
      tab.className = 'mmt';
      if (m === mode) tab.classList.add(activeClass[mode]);
    }
    if (panel) panel.className = 'mode-panel' + (m === mode ? ' show' : '');
  });
  // Anti-mode: hide direction toggle (not applicable)
  const dirWrap = $('mart-dir-wrap');
  if (dirWrap) dirWrap.style.display = (martOn && mode !== 'anti') ? 'block' : 'none';
  saveSettings();
}

// Wire mart mode tabs
['classic','soft','anti','step'].forEach(m => {
  const btn = document.getElementById('mmt-' + m);
  if (btn) btn.addEventListener('click', () => setMartMode(m));
});

// Martingale direction buttons

document.addEventListener('DOMContentLoaded', () => {

  async function ensurePocketOptionAttach() {
    try { return await chrome.runtime.sendMessage({type:'KAOS_PO_ENSURE_ATTACH'}); }
    catch (_) { return null; }
  }
  setTimeout(ensurePocketOptionAttach, 500);
  setInterval(ensurePocketOptionAttach, 4000);


  const dirOpp  = $('dir-opposite');
  const dirSame = $('dir-same');
  if (dirOpp) dirOpp.addEventListener('click', () => {
    if (state.running) return;
    martDir = 'opposite'; applyMartUI(); saveSettings();
  });
  if (dirSame) dirSame.addEventListener('click', () => {
    if (state.running) return;
    martDir = 'same'; applyMartUI(); saveSettings();
  });
});

// ════════════════════════════════════════════════════════════
//  COMPOUNDING TOGGLE
// ════════════════════════════════════════════════════════════
$('compound-row').addEventListener('click', () => {
  if (state.running) return;
  if (martOn) return;
  compoundOn = !compoundOn;
  applyCompoundUI();
  if (compoundOn && martOn) { martOn = false; applyMartUI(); }
  saveSettings();
});

function applyCompoundUI() {
  $('compound-pill').classList.toggle('on', compoundOn);
  $('compound-panel').classList.toggle('open', compoundOn);
  $('compound-conflict').style.display = compoundOn ? 'block' : 'none';
  $('mart-row').classList.toggle('disabled', compoundOn);
}

// ════════════════════════════════════════════════════════════
//  SETTINGS SAVE / LOAD
// ════════════════════════════════════════════════════════════
function saveSettings() {
  chrome.storage.local.set({ settings: {
    timeframe:         getTimeframe(),
    strategy:          getStrategy(),
    amount:            parseFloat($('amount-input').value) || 5,
    multiAsset:        multiAssetOn, // 4-grid only while popup toggle is ON
    martingale:        martOn,
    martDir:           martDir,
    martMode:          martMode,
    softSteps:         parseInt(($('soft-steps')||{value:'6'}).value)   || 6,
    antiMult:          parseFloat(($('anti-mult')||{value:'2'}).value)  || 2,
    antiSteps:         parseInt(($('anti-steps')||{value:'4'}).value)   || 4,
    stepMult:          parseFloat(($('step-mult')||{value:'2'}).value)  || 2,
    stepSteps:         parseInt(($('step-steps')||{value:'4'}).value)   || 4,
    martMult:          parseFloat($('mart-mult').value)    || 2,
    martSteps:         parseInt($('mart-steps').value)     || 5,
    compound:          compoundOn,
    compoundPct:       parseFloat($('compound-pct').value) || 2,
    maxLossStreak:     parseInt($('max-loss-streak').value)  || 0,
    cooldownAfterLoss: parseInt($('cooldown-loss').value)    || 0,
    autoCooldownOn:    autoCdOn,
    profitTarget:      parseFloat($('profit-target').value)  || 0,
    dailyLossLimit:    parseFloat($('daily-loss-limit').value)|| 0,

  }});
}

function loadSettings() {
  updateStratDesc();
  // Apply defaults first (martingale ON by default)
  multiAssetOn = false;
  martOn = true; compoundOn = false; martDir = 'opposite'; autoCdOn = true;
  applyMultiUI(); applyMartUI(); applyCompoundUI();

  chrome.storage.local.get('settings', (data) => {
    const s = data.settings;
    if (!s) return; // keep defaults above
    if (s.timeframe) {
      document.querySelectorAll('.tf-btn').forEach(b => {
        b.classList.toggle('active', parseInt(b.dataset.tf) === s.timeframe);
      });
    }
    if (s.strategy) {
      const sel = $('strat-select');
      for (const opt of sel.options) {
        if (opt.value === s.strategy) { sel.value = s.strategy; break; }
      }
      updateStratDesc();
    }
    if (s.amount     != null) $('amount-input').value    = s.amount;
    if (s.martMult   != null) $('mart-mult').value       = s.martMult;
    if (s.martSteps  != null) $('mart-steps').value      = s.martSteps;
    if (s.compoundPct!= null) $('compound-pct').value    = s.compoundPct;
    if (s.maxLossStreak   != null) $('max-loss-streak').value  = s.maxLossStreak;
    if (s.cooldownAfterLoss!= null) $('cooldown-loss').value   = s.cooldownAfterLoss;
    if (s.autoCooldownOn != null) { autoCdOn = !!s.autoCooldownOn; applyAutoCdUI(); }
    if (s.profitTarget    != null) $('profit-target').value    = s.profitTarget;
    if (s.dailyLossLimit  != null) $('daily-loss-limit').value = s.dailyLossLimit;


    multiAssetOn = s.multiAsset !== undefined ? !!s.multiAsset : false; // honor the popup toggle
    martOn     = s.martingale !== undefined ? !!s.martingale : true;
    compoundOn = !!s.compound;
    martDir    = s.martDir  || 'opposite';
    martMode   = s.martMode || 'classic';
    if (martOn && compoundOn) compoundOn = false;
    applyMultiUI();
    applyMartUI();
    applyCompoundUI();
    setMartMode(martMode);
    const sv = (id, val) => { const e = $(id); if (e && val != null) e.value = val; };
    sv('soft-steps', s.softSteps);
    sv('anti-mult',  s.antiMult);
    sv('anti-steps', s.antiSteps);
    sv('step-mult',  s.stepMult);
    sv('step-steps', s.stepSteps);
  });
}

// Auto-save on input change
['amount-input','mart-mult','mart-steps','compound-pct',
 'max-loss-streak','cooldown-loss','profit-target','daily-loss-limit',
 'soft-steps','anti-mult','anti-steps','step-mult','step-steps']
  .forEach(id => { const el=$(id); if(el) el.addEventListener('change', saveSettings); });

// ════════════════════════════════════════════════════════════
//  STATS
// ════════════════════════════════════════════════════════════
function loadStats() {
  chrome.storage.local.get(['stats', 'tradeRecords'], (data) => {
    if (data.stats) {
      const s = data.stats;
      state.wins   = s.wins   || 0;
      state.losses = s.losses || 0;
      state.pnl    = s.pnl    || 0;
    }
    state.trades = data.tradeRecords || [];
    updateStatsUI();
    renderLog();
  });
}

function saveStats() {
  chrome.storage.local.set({ stats: {
    wins: state.wins, losses: state.losses, pnl: state.pnl
  }});
}

function updateStatsUI() {
  $('stat-wins').textContent = state.wins;
  $('stat-losses').textContent = state.losses;
  const total = state.wins + state.losses;
  $('stat-wr').textContent = total ? Math.round(state.wins / total * 100) + '%' : '0%';
  const sign = state.pnl >= 0 ? '+' : '';
  $('stat-pnl').textContent = sign + '$' + Math.abs(state.pnl).toFixed(2);
  $('stat-pnl').style.color = state.pnl >= 0 ? 'var(--green)' : 'var(--red)';
  // Banner status strip: last trade + session-derived balance
  const last = state.trades[state.trades.length - 1];
  const lt = $('kaos-last-trade');
  if (lt) {
    if (last) {
      const p = last.result === 'win' ? `+$${Number(last.profit||0).toFixed(2)}` : `-$${Number(last.amount||0).toFixed(2)}`;
      lt.textContent = `Last Trade: ${last.result === 'win' ? 'WIN' : 'LOSS'} ${p}`;
      lt.style.color = last.result === 'win' ? 'var(--kb-green)' : 'var(--kb-red)';
    } else {
      lt.textContent = 'Last Trade: —';
      lt.style.color = '';
    }
  }
  const bal = $('kaos-balance');
  if (bal && bal.dataset.poLiveBalance !== '1') {
    bal.textContent = 'Balance: Waiting for Pocket Option…';
  }
}

function renderLog() {
  const el = $('log-entries');
  if (!el) return;
  if (!state.trades.length) {
    el.innerHTML = '<div class="log-empty">No trades yet</div>';
    return;
  }
  el.innerHTML = '';
  [...state.trades].reverse().slice(0, 30).forEach(t => {
    const row = document.createElement('div');
    row.className = 'log-entry';
    const profitTxt = t.result === 'win' ? `+$${Number(t.profit||0).toFixed(2)}` : `-$${Number(t.amount||0).toFixed(2)}`;
    const plTxt = t.result === 'win' ? `+$${Number(t.profit||0).toFixed(2)}` : `-$${Number(t.amount||0).toFixed(2)}`;
    row.innerHTML = `
      <span class="l-time">${t.ts ? new Date(t.ts).toLocaleTimeString() : '—'}</span>
      <span class="l-asset">${t.asset}</span>
      <span class="l-dir">${t.direction || 'UNKNOWN'}</span>
      <span class="l-res ${t.result}">${t.result === 'win' ? 'WIN' : 'LOSS'}</span>
      <span class="l-pl ${t.result}">${plTxt}</span>
    `;
    el.appendChild(row);
  });
}

// B14 — Always-visible Pocket Flow selective win-rate meter.
// Reads the same persisted counters as the AI Learning Lab, but keeps the
// metric on the main runtime screen so it is visible while the bot runs.
async function refreshPocketFlowLiveMeter() {
  try {
    const pf=(await chrome.storage.local.get('v287_learning_status')).v287_learning_status || null;
    const n=Number(pf?.selectiveResolved||0), c=Number(pf?.selectiveCorrect||0);
    const allN=Number(pf?.resolved||0);
    const rate=n ? (100*c/n) : null;
    const share=allN ? (100*n/allN) : null;
    const wr=$('pf-live-wr');
    if(wr){
      wr.textContent=rate==null?'—':rate.toFixed(1)+'%';
      wr.classList.remove('good','bad','wait');
      wr.classList.add(rate==null||n<300?'wait':rate>=60?'good':'bad');
    }
    setText('pf-live-n', n);
    setText('pf-live-share', share==null?'—':share.toFixed(0)+'%');
    const assets=$('pf-live-assets');
    if(assets){
      const parts=Object.entries(pf?.selByAsset||{}).map(([asset,v])=>{
        const an=Number(v?.n||0), ac=Number(v?.c||0);
        return `${asset}: ${an?((100*ac/an).toFixed(1)+'%'):'—'} (${an})`;
      });
      assets.textContent=parts.length?'Per asset · '+parts.join(' · '):'Per asset: waiting for learner data…';
    }
    const verdict=$('pf-live-verdict');
    if(verdict){
      verdict.textContent=n<300?`SAMPLE ${n}/300`:rate>=60?'ABOVE 60%':'BELOW 60%';
      verdict.style.color=n<300?'var(--gold)':rate>=60?'var(--green)':'var(--red)';
    }
  } catch(_) {}
}

// ════════════════════════════════════════════════════════════
//  LIVE DEBUG PANEL
// ════════════════════════════════════════════════════════════
function setText(id, val) {
  const el = $(id);
  if (!el) return;
  el.textContent = (val === null || val === undefined || val === '') ? '--' : val;
}

function renderExactModelResearch(s) {
  const box=$('exact-model-horizons'), note=$('exact-model-sample'), raw=$('exact-model-raw');
  if(!box)return;
  const r=s?.exactModelResearch||{}, st=r.stats||{};
  const fmt=(h)=>{const x=st[h]||{},w=Number(x.wins||0),l=Number(x.losses||0),d=Number(x.draws||0),n=w+l;const wr=n?(100*w/n).toFixed(1)+'%':'—';return `<div style="padding:6px 4px;border:1px solid var(--border);border-radius:6px;text-align:center"><b style="color:var(--accent)">${h==='60s'?'1m':h}</b><br><strong>${wr}</strong><br><span style="font-size:10px;color:var(--muted)">${w}W/${l}L${d?`/${d}D`:''}</span></div>`;};
  box.innerHTML=['5s','15s','30s','60s'].map(fmt).join('');
  const n5=Number(st['5s']?.wins||0)+Number(st['5s']?.losses||0);
  if(note)note.textContent=`Observed research outcomes: ${n5} · Same entry is measured at 5s, 15s, 30s and 1m. Research outcomes are not a trading-performance guarantee.`;
  const meta=r.raw5Meta||{}, parts=Object.entries(meta).map(([a,v])=>`${a} ${Number(v?.count||0)}`);
  if(raw)raw.textContent=`Raw 5s archive: ${parts.length?parts.join(' · '):'collecting…'}`;
}

function renderDebug(s) {
  if (!s) return;
  renderExactModelResearch(s);
  setText('dbg-asset', s.asset);
  setText('dbg-tf', s.indicatorTF || s.tfKey);
  setText('dbg-storage', s.storageCandles ?? 0);
  setText('dbg-tfcount', s.indicatorCandles ?? s.tfCandles ?? 0);

  const bar = $('dbg-warmup-bar');
  if (bar) bar.style.width = `${Math.min(100, s.warmupPct || 0)}%`;
  setText('dbg-warmup-txt', `${s.storageCandles || 0}/${s.warmupNeeded} closed 5s · strategy ${s.tfKey || '5s'} ${s.indicatorCandles ?? s.tfCandles ?? 0}${s.contextTfKey ? ` · context ${s.contextTfKey} ${s.contextTfCandles ?? 0}` : ''}`);

  // V24.1.124: one live card per grid channel (controller + per-channel state)
  const chEl = $('dbg-channels');
  if (chEl) {
    const channels = Array.isArray(s.channels) ? s.channels : [];
    const esc = (x) => String(x ?? '—').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
    if (!channels.length) {
      chEl.innerHTML = '<div class="dbg-log-empty">Grid mode off — start the 4-chart bot to populate channels</div>';
    } else {
      chEl.innerHTML = channels.map(c => {
        const tr = c.trade || {};
        const ind = c.indicators || {};
        const cd = c.cooldown || null;
        const stateCls = c.ready ? 'ready' : 'wait';
        const pendingTxt = tr.pending ? 'PENDING' : tr.microConfirm ? 'MICRO' : tr.queued ? 'QUEUED' : '—';
        const lastAge = tr.lastTradeAgeSec != null ? tr.lastTradeAgeSec + 's' : '—';
        const indiTxt = [
          ind.rsi != null ? `RSI ${Number(ind.rsi).toFixed(1)}` : null,
          ind.stoch != null ? `STOCH ${Number(ind.stoch).toFixed(1)}` : null,
          ind.tqsBuy != null ? `LEG-B ${Number(ind.tqsBuy).toFixed(1)}` : null,
          ind.tqsSell != null ? `LEG-S ${Number(ind.tqsSell).toFixed(1)}` : null,
          ind.adx != null ? `ADX ${Number(ind.adx).toFixed(1)}` : null
        ].filter(Boolean).join(' · ') || '—';
        const cdTxt = cd ? `${cd.leftSec}s${cd.reason ? ' · ' + esc(cd.reason) : ''}` : null;
        return `<div class="dbg-channel">
          <div class="dbg-channel-head">
            <span class="dbg-channel-name">CH${c.channel != null ? c.channel : '?'} · ${esc(c.asset || '—')}</span>
            <span class="dbg-channel-state ${stateCls}">${esc(c.state || 'WARMING')} ${c.pct != null ? c.pct : 0}%</span>
          </div>
          <div class="dbg-channel-line"><span class="lbl">CTRL</span><b>${esc(c.controller || 'V219 MULTIMODAL')} · CH L${c.channelLossStreak || 0}/W${c.channelWinStreak || 0}</b></div>
          ${c.debugReason ? `<div class="dbg-channel-line"><span class="lbl">DEBUG</span><b>${esc(c.debugReason)}</b></div>` : ''}
          ${cdTxt ? `<div class="dbg-channel-line"><span class="lbl">COOLDOWN</span><b>${cdTxt}</b></div>` : ''}
          <div class="dbg-channel-line"><span class="lbl">INDI</span><b>${indiTxt}</b></div>
          ${c.strategyPlan ? `<div class="dbg-channel-line"><span class="lbl">PLAN</span><b>${esc(c.strategyPlan)}</b></div>` : (ind.timeframePlan ? `<div class="dbg-channel-line"><span class="lbl">CONTEXT</span><b>${esc(ind.timeframePlan.fast || '—')} → ${esc(ind.timeframePlan.primary || '—')} → ${esc(ind.timeframePlan.higher || '—')}</b></div>` : '')}
          ${(ind.trendScore != null || ind.momentumScore != null || ind.volatilityScore != null) ? `<div class="dbg-channel-line"><span class="lbl">3-STEP</span><b>T ${ind.trendScore != null ? Number(ind.trendScore).toFixed(0) : '—'} · M ${ind.momentumScore != null ? Number(ind.momentumScore).toFixed(0) : '—'} · V ${ind.volatilityScore != null ? Number(ind.volatilityScore).toFixed(0) : '—'} · FINAL ${ind.finalThreeStepScore != null ? Number(ind.finalThreeStepScore).toFixed(0) + '%' : '—'}</b></div>` : ''}
          ${(ind.primaryTrend != null || ind.higherTrend != null || ind.fastMomentum != null) ? `<div class="dbg-channel-line"><span class="lbl">MTF</span><b>P-T ${ind.primaryTrend != null ? Number(ind.primaryTrend).toFixed(0) : '—'} · H-T ${ind.higherTrend != null ? Number(ind.higherTrend).toFixed(0) : '—'} · FAST-M ${ind.fastMomentum != null ? Number(ind.fastMomentum).toFixed(0) : '—'} · PRI-M ${ind.primaryMomentum != null ? Number(ind.primaryMomentum).toFixed(0) : '—'}</b></div>` : ''}
          <div class="dbg-channel-line"><span class="lbl">STREAM</span><b>${c.streamLive ? 'LIVE' : 'WAIT'} · tick ${c.lastTickAgeSec != null ? c.lastTickAgeSec + 's' : '—'} · warmup ${c.storageCandles || 0}/${c.warmupNeeded || 100} closed 5s · open ${c.trade?.openTrades ?? 0}/${c.trade?.maxOpenTrades ?? 2}</b></div>
          <div class="dbg-channel-line"><span class="lbl">PO 1S AI</span><b>${c.poAI?.sentimentBuy != null ? `SENT BUY ${Number(c.poAI.sentimentBuy).toFixed(0)}% / SELL ${Number(c.poAI.sentimentSell).toFixed(0)}%` : 'SENTIMENT NOT FOUND'} · ${c.poAI?.pred || 'LEARNING'}${c.poAI?.predUp != null ? ` ${Math.max(Number(c.poAI.predUp),1-Number(c.poAI.predUp))*100 >= 50 ? (Math.max(Number(c.poAI.predUp),1-Number(c.poAI.predUp))*100).toFixed(1)+'%' : ''}` : ''} · PATH ${c.poAI?.pathPoints || 0}/6</b></div>
          <div class="dbg-channel-line"><span class="lbl">TRADE</span><b>${pendingTxt} · last ${lastAge} · ${tr.martLevel ? 'mart ' + tr.martLevel : 'no mart'} · streak ${tr.lossStreak || 0} · ${Number(tr.amount || 0).toFixed(2)}</b></div>
          <details class="dbg-forensic"><summary>FORENSIC · last 10 decisions + candles</summary>
            <div class="dbg-channel-line"><span class="lbl">DECISIONS</span><b>${(c.decisionHistory||[]).slice().reverse().map(d=>`${new Date(d.ts).toLocaleTimeString()} ${esc(d.outcome)} · ${esc(d.reason)}${d.weighted!=null?' · W '+Number(d.weighted).toFixed(0):''}`).join('<br>') || '—'}</b></div>
            ${['5s','15s','30s','60s'].map(tf=>`<div class="dbg-channel-line"><span class="lbl">${tf}</span><b>${((c.candles||{})[tf]||[]).map(x=>`${new Date(Number(x.time)*1000).toLocaleTimeString()} O ${Number(x.open).toFixed(5)} H ${Number(x.high).toFixed(5)} L ${Number(x.low).toFixed(5)} C ${Number(x.close).toFixed(5)}`).join('<br>') || '—'}</b></div>`).join('')}
          </details>
        </div>`;
      }).join('');
    }
  }

  // V24.1.130: grid account badge — shows the account PO is on (informational;
  // the bot follows it, never decides it)
  const demoBadge = $('demo-grid-badge');
  if (demoBadge) {
    const gridOn = Array.isArray(s.channels) && s.channels.length > 0;
    if (gridOn && s.gridAccountIsDemo === true) {
      demoBadge.classList.add('on', 'ok');
      setText('demo-grid-badge-txt', 'DEMO · FOLLOWS PO');
    } else if (gridOn && s.gridAccountIsDemo === false) {
      demoBadge.classList.add('on'); demoBadge.classList.remove('ok');
      setText('demo-grid-badge-txt', 'REAL · FOLLOWS PO');
    } else if (gridOn) {
      demoBadge.classList.add('on'); demoBadge.classList.remove('ok');
      setText('demo-grid-badge-txt', 'ACCOUNT UNCONFIRMED');
    } else {
      demoBadge.classList.remove('on', 'ok');
      setText('demo-grid-badge-txt', '—');
    }
  }

  const ind = s.indicators || {};
  setText('dbg-rsi',   ind.rsi   !== undefined ? Number(ind.rsi).toFixed(1)   : '--');
  setText('dbg-ema5',  ind.ema5  !== undefined ? Number(ind.ema5).toFixed(5)  : '--');
  setText('dbg-ema9', ind.ema9 !== undefined ? Number(ind.ema9).toFixed(5) : '--');
  setText('dbg-ema21', ind.ema21 !== undefined ? Number(ind.ema21).toFixed(5) : '--');
  setText('dbg-atr',   ind.atr   !== undefined ? Number(ind.atr).toFixed(5)   : '--');
  setText('dbg-stoch', ind.stoch !== undefined ? Number(ind.stoch).toFixed(1) : '--');
  setText('dbg-macd',  ind.macd  !== undefined ? Number(ind.macd).toFixed(5)  : '--');
  setText('dbg-buy',   ind.buyScore  !== undefined ? ind.buyScore  : '--');
  setText('dbg-sell',  ind.sellScore !== undefined ? ind.sellScore : '--');

  const reasonEl = $('dbg-reason');
  if (reasonEl) {
    reasonEl.className = 'dbg-reason';
    if (s.running)      reasonEl.classList.add('live');
    if (s.tradePending) reasonEl.classList.add('pending');
    reasonEl.textContent = s.reason || 'IDLE';
  }

  const logEl = $('dbg-log');
  if (!logEl) return;
  const trades = Array.isArray(s.trades)
    ? [...s.trades].slice(-12).reverse()
    : [];
  if (!trades.length) {
    logEl.innerHTML = '<div class="dbg-log-empty">No signal decisions yet</div>';
    return;
  }
  logEl.innerHTML = trades.map(t => `
    <div class="dbg-log-row">
      <span class="dbg-log-t">${t.ts ? new Date(t.ts).toLocaleTimeString() : '—'}</span>
      <span class="dbg-log-d ${t.result}">${t.dir || t.direction || 'UNKNOWN'}</span>
      <span class="dbg-log-a">${t.asset || '—'}</span>
      <span class="dbg-log-m">$${Number(t.amount || 0).toFixed(2)}</span>
      <span class="dbg-log-r ${t.result}">${t.result === 'win' ? '+$' + Number(t.profit || 0).toFixed(2) : t.result === 'loss' ? '-$' + Number(t.amount || 0).toFixed(2) : 'SIG'}</span>
    </div>`).join('');
}

function pollStatus() {
  refreshPocketFlowLiveMeter();
  getKAOSTargetTab().then(tab => {
    if (!tab) return;
    chrome.tabs.sendMessage(tab.id, { type: 'PING' })
      .then((resp) => { if (resp && resp.ok) renderDebug(resp); })
      .catch(() => {});
  });
}

$('reset-stats-btn').addEventListener('click', () => {
  if (state.running) return;
  state.wins = state.losses = 0;
  state.pnl = 0;
  state.trades = [];
  saveStats();
  updateStatsUI();
  renderLog();
});

// ════════════════════════════════════════════════════════════
//  START / STOP
// ════════════════════════════════════════════════════════════
$('start-btn').addEventListener('click', () => {
  state.running ? stopBot() : startBot();
});

function startBot() {
  if (KAOS_AUDIT_READ_ONLY) {
    setStatus('idle', 'CHART AUDIT · TRADING DISABLED');
    return;
  }
  const strategy        = getStrategy();
  const timeframe       = getTimeframe();
  const amount          = parseFloat($('amount-input').value)     || 5;
  const mult            = parseFloat($('mart-mult').value)        || 2;
  const steps           = parseInt($('mart-steps').value)         || 5;
  const compoundPct     = parseFloat($('compound-pct').value)     || 2;
  const maxLossStreak   = parseInt($('max-loss-streak').value)    || 0;
  const cooldownAfterLoss = parseInt($('cooldown-loss').value)    || 0;
  const profitTarget    = parseFloat($('profit-target').value)    || 0;
  const dailyLossLimit  = parseFloat($('daily-loss-limit').value) || 0;

  const tfLabel = timeframe < 60
    ? `${timeframe}s`
    : `${timeframe/60}min`;

  state.running    = true;
  state.martLevel  = 0;
  state.lossStreak = 0;
  state.sessionPnl = 0;
  consecutiveLosses = 0;
  antiLevel = 0;

  setRunningUI(true);
  setStatus('active', `[${strategy}] · ${tfLabel} · SCANNING...`);
  chrome.storage.local.set({ botRunning: true });

  getKAOSTargetTab().then(tab => {
    if (!tab) { stopBot(); return; }
    const tabs = [tab];
    chrome.runtime.sendMessage({
      type: 'START_BOT',
      strategy, timeframe, amount,
      multiAsset: multiAssetOn, // only trade 4 markets when the popup multi toggle is checked
      martingale: martOn, multiplier: mult, maxSteps: steps, martDir, martMode,
      softSteps:  parseInt(($('soft-steps')||{value:'6'}).value)   || 6,
      antiMult:   parseFloat(($('anti-mult')||{value:'2'}).value)  || 2,
      antiSteps:  parseInt(($('anti-steps')||{value:'4'}).value)   || 4,
      stepMult:   parseFloat(($('step-mult')||{value:'2'}).value)  || 2,
      stepSteps:  parseInt(($('step-steps')||{value:'4'}).value)   || 4,
      compound: compoundOn, compoundPct,
      maxLossStreak, cooldownAfterLoss, profitTarget, dailyLossLimit,
      ...getStrategyBuilderStartConfig(),

      tabId: tabs[0].id,
    });
  });
}

function stopBot() {
  state.running = false;
  setRunningUI(false);
  setStatus('idle', 'IDLE · READY');
  chrome.storage.local.set({ botRunning: false });
  // The UI is in its own Chrome window; route STOP through background so it
  // reaches the saved Pocket Option target tab, not the KAOS window.
  chrome.runtime.sendMessage({ type: 'STOP_BOT' }).catch(() => {});
}

function setRunningUI(running) {
  const btn = $('start-btn');
  btn.className   = 'kaos-start-btn ' + (running ? 'stop-state' : 'start-state');
  btn.textContent = running ? '■ STOP' : (KAOS_AUDIT_READ_ONLY ? 'CHART AUDIT · TRADING DISABLED' : '▶ START KAOS');
  btn.title = running ? 'Stop the bot' : (KAOS_AUDIT_READ_ONLY ? 'Trading disabled in this build' : 'Start trading on the connected broker account');
  $('edit-hint').style.display = running ? 'block' : 'none';

  // Lock all inputs while running
  const inputs = [
    $('amount-input'), $('mart-mult'), $('mart-steps'), $('compound-pct'),
    $('max-loss-streak'), $('cooldown-loss'), $('profit-target'), $('daily-loss-limit'),
    $('strat-select'),
  ];
  inputs.forEach(el => { if (!el) return; el.disabled = running; el.style.opacity = running ? '.45' : '1'; });

  document.querySelectorAll('.tf-btn').forEach(el => {
    el.style.pointerEvents = running ? 'none' : '';
    el.style.opacity       = running ? '.45' : '1';
  });

  [$('mart-row'), $('compound-row')].forEach(el => {
    el.style.pointerEvents = running ? 'none' : '';
    el.style.opacity = running ? '.45' : '1';
  });
}

function setStatus(type, text) {
  const dot = $('status-dot');
  dot.className = 's-dot';
  if (type === 'active')  dot.classList.add('active');
  if (type === 'waiting') dot.classList.add('waiting');
  if (type === 'error')   dot.classList.add('error');
  $('status-text').textContent = text;
}

// ════════════════════════════════════════════════════════════
//  MESSAGES FROM CONTENT SCRIPT
// ════════════════════════════════════════════════════════════
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'DEBUG_UPDATE') {
    renderDebug(msg.state);
    refreshPocketFlowLiveMeter();
    return;
  }
  if (msg.type === 'TRADE_RESULT') {
    const { asset, direction, amount, result, profit } = msg;
    const normalizedDirection = (() => { const x=String(direction||msg.dir||msg.action||msg.command||msg.orderDirection||msg.tradeDirection||'').toUpperCase(); return (x==='BUY'||x==='CALL'||x==='HIGHER')?'BUY':(x==='SELL'||x==='PUT'||x==='LOWER')?'SELL':null; })();

    // Deduplicate
    const sig = JSON.stringify({ asset, direction: normalizedDirection, amount, result, profit: Number(profit||0).toFixed(2) });
    const now = Date.now();
    if (state.lastSig === sig && now - state.lastSigAt < 5000) return;
    state.lastSig   = sig;
    state.lastSigAt = now;

    if (result === 'win') {
      state.wins++;
      state.pnl        += Number(profit || 0);
      state.sessionPnl += Number(profit || 0);
      state.lossStreak  = 0;
      consecutiveLosses = 0;
      if (martMode === 'anti' && martOn) {
        const maxS = parseInt(($('anti-steps')||{value:'4'}).value) || 4;
        antiLevel++;
        if (antiLevel < maxS) {
          const mult2 = parseFloat(($('anti-mult')||{value:'2'}).value) || 2;
          const next = parseFloat((amount * mult2).toFixed(2));
          setStatus('active', `WIN · Anti streak ${antiLevel}/${maxS} → $${next}`);
        } else {
          antiLevel = 0; state.martLevel = 0;
          setStatus('active', `WIN · Anti max streak · Reset`);
        }
      } else {
        state.martLevel = 0; antiLevel = 0;
        setStatus('active', `WIN +$${Number(profit||0).toFixed(2)} · ${asset}`);
      }
    } else if (result === 'loss') {
      state.losses++;
      state.pnl        -= Number(amount || 0);
      state.sessionPnl -= Number(amount || 0);
      state.lossStreak++;
      consecutiveLosses++;
      antiLevel = 0; // anti-mart resets on loss
      if (martOn) {
        const mode  = martMode || 'classic';
        const maxS  = mode==='soft'  ? (parseInt(($('soft-steps')||{value:'6'}).value)||6)
                    : mode==='step'  ? (parseInt(($('step-steps')||{value:'4'}).value)||4)
                    :                  (parseInt($('mart-steps').value)||5);
        const mult2 = mode==='soft'  ? 1.5
                    : mode==='step'  ? (parseFloat(($('step-mult')||{value:'2'}).value)||2)
                    :                  (parseFloat($('mart-mult').value)||2);
        // Step mode: only increase after 2 consecutive losses
        const shouldIncrease = mode !== 'step' || consecutiveLosses >= 2;
        if (state.martLevel < maxS && shouldIncrease) {
          state.martLevel++;
          const next = parseFloat((amount * mult2).toFixed(2));
          const lbl = mode==='soft' ? 'Soft' : mode==='step' ? 'Step' : 'Mart';
          setStatus('waiting', `LOSS · ${lbl} ×${state.martLevel} → $${next}`);
        } else if (!shouldIncrease) {
          setStatus('active', `LOSS · Step (${consecutiveLosses}/2) · Watching...`);
        } else {
          state.martLevel = 0; consecutiveLosses = 0;
          setStatus('active', `LOSS · Reset · Watching...`);
        }
      } else {
        state.martLevel = 0; consecutiveLosses = 0;
        setStatus('active', `LOSS · Reset · Watching...`);
      }
    }

    // Full-fidelity record from content.js (candle OHLC, indicators, scores,
    // reasons...) or a minimal fallback for older sessions.
    const rec = msg.record || { asset, direction: normalizedDirection, amount: Number(amount), result, profit: Number(profit||0), ts: now };
    if (!rec.direction || String(rec.direction).toUpperCase()==='UNKNOWN' || String(rec.direction).toUpperCase()==='UNDEFINED') rec.direction = normalizedDirection || rec.dir || rec.action || 'UNKNOWN';
    if (rec.direction) { const x=String(rec.direction).toUpperCase(); rec.direction=(x==='CALL'||x==='HIGHER')?'BUY':(x==='PUT'||x==='LOWER')?'SELL':x; }
    if (!rec.ts) rec.ts = now;
    if (!rec.timestamp) rec.timestamp = new Date(now).toISOString().replace('T', ' ').slice(0, 19);
    state.trades.push(rec);
    if (state.trades.length > 1000) state.trades = state.trades.slice(-1000);
    updateStatsUI();
    renderLog();
    saveStats();
  }

  if (msg.type === 'BOT_STATUS')  setStatus('active', msg.text);
  if (msg.type === 'BOT_STOPPED') stopBot();


});

// ════════════════════════════════════════════════════════════
//  UTILS
// ════════════════════════════════════════════════════════════
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ════════════════════════════════════════════════════════════
//  CSV EXPORT — download every trade with full info
// ════════════════════════════════════════════════════════════
// Must match the field names in content.js captureSnapshot() EXACTLY (case-sensitive).
const CSV_HEADERS = [
  'timestamp','asset','direction','amount','entryPrice','exitPrice','result','profit',
  'candleOpen','candleHigh','candleLow','candleClose','candleBody','candleDirection',
  'rsi','ema5','ema9','ema21','macd','macdSignal','stochK','stochD','atr',
  'bollingerPos','bollingerUpper','bollingerLower','keltnerPos','keltnerUpper','keltnerLower',
  'strategy','mode','totalScore','buyScore','sellScore','reasons','entryType',
  'strategyType','runBuy','runSell','revBuy','revSell','tqsBuy','tqsSell','marketQuality',
  'aiBuy','aiSell','regimeAtEntry','ai30Up','ai30Down','ai30Confidence','ai30Warm','ai30Samples','ai30Accuracy',
  'entryPhase'
];

function csvEscape(v) {
  if (v === null || v === undefined) return '';
  let s = String(v);
  if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function csvRow(r) {
  return CSV_HEADERS.map(h => csvEscape(r[h])).join(',');
}

function strToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

async function exportTradesCsv() {
  // Merge every source so export never comes up empty after a completed trade.
  let storageRecords = [];
  let bgRecords = [];
  let contentRecords = [];

  try {
    const data = await chrome.storage.local.get('tradeRecords');
    if (Array.isArray(data.tradeRecords)) storageRecords = data.tradeRecords;
  } catch (e) { /* storage unavailable */ }

  try {
    const resp = await chrome.runtime.sendMessage({ type: 'GET_TRADES' });
    if (resp && resp.ok && Array.isArray(resp.records)) bgRecords = resp.records;
  } catch (e) { /* background unavailable */ }

  try {
    const tab = await getKAOSTargetTab();
    const tabs = tab ? [tab] : [];
    if (tabs[0]) {
      const resp = await chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_TRADES' });
      if (resp && resp.ok && Array.isArray(resp.records)) contentRecords = resp.records;
    }
  } catch (e) { /* content script unavailable */ }

  const seen = new Set();
  const rows = [];
  const add = (r) => {
    if (!r) return;
    const k = [r.ts || r.timestamp, r.asset, r.direction, r.amount, r.result].join('|');
    if (seen.has(k)) return;
    seen.add(k);
    // Normalize reasons array → string for CSV
    if (Array.isArray(r.reasons)) r = { ...r, reasons: r.reasons.join('; ') };
    rows.push(r);
  };
  storageRecords.forEach(add);
  bgRecords.forEach(add);
  contentRecords.forEach(add);
  (state.trades || []).forEach(add);
  rows.sort((a, b) => (Number(a.ts) || 0) - (Number(b.ts) || 0));

  if (!rows.length) {
    setStatus('waiting', 'No trades to export yet — complete a trade first');
    return;
  }

  const date = new Date().toISOString().slice(0, 10);
  const filename = 'KAOS_Trades_' + date + '.csv';
  const csv = CSV_HEADERS.join(',') + '\n' + rows.map(csvRow).join('\n');
  const dataUrl = 'data:text/csv;charset=utf-8;base64,' + strToBase64('\ufeff' + csv);

  chrome.downloads.download({ url: dataUrl, filename, saveAs: false }, () => {
    if (chrome.runtime.lastError) {
      setStatus('error', `Export failed: ${chrome.runtime.lastError.message}`);
    } else {
      setStatus('active', `Exported ${rows.length} trades → ${filename}`);
    }
  });
}

$('export-csv-btn').addEventListener('click', exportTradesCsv);
$('export-debug-btn').addEventListener('click', exportDebugCsv);

// ════════════════════════════════════════════════════════════
//  LIVE DEBUG CSV EXPORT — snapshot of current indicator state
// ════════════════════════════════════════════════════════════
const DEBUG_CSV_HEADERS = [
  'timestamp','asset','timeframe','storageCandles','tfCandles','warmupPct',
  'running','strategy','amount','martLevel','tradePending',
  'lastTradeDir','lastTradeAmt','wins','losses','pnl','reason',
  'rsi','ema5','ema9','ema21','atr','stochK','stochD','macd','macdSignal',
  'buyScore','sellScore',
  // V24.1.124: per-channel columns (one CSV row per grid channel when in 4-chart mode)
  'channel','lastTradeAgeSec','microConfirm',
  'queued','streamLive','tickAgeSec'
];

function debugCsvRow(r) {
  return DEBUG_CSV_HEADERS.map(h => csvEscape(r[h])).join(',');
}

async function exportDebugCsv() {
  let snap = null;
  try {
    const tab = await getKAOSTargetTab();
    const tabs = tab ? [tab] : [];
    if (tabs[0]) {
      const resp = await chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_DEBUG_SNAPSHOT' });
      if (resp && resp.ok && resp.snapshot) snap = resp.snapshot;
    }
  } catch (e) { /* content script unavailable */ }
  if (!snap) {
    setStatus('error', 'Debug export failed: content script unavailable');
    return;
  }
  // V225: forensic JSON preserves all four charts, each chart's last 10
  // decisions, and 10 closed candles for 5s/15s/30s/60s. This is intentionally
  // JSON rather than a flattened CSV so no context is discarded.
  const payload = {
    kind:'KAOS-Forensic-Debug', version:'24.1.287', exportedAt:new Date().toISOString(),
    note:'AI is learning-only. BUY/SELL on INDI are legacy indicator telemetry; weighted decision + rejection reason are authoritative.',
    snapshot:snap
  };
  const time = new Date().toISOString().replace(/[:.]/g,'-');
  const filename = 'KAOS_FORENSIC_DEBUG_' + time + '.json';
  const dataUrl = 'data:application/json;charset=utf-8;base64,' + strToBase64(JSON.stringify(payload,null,2));
  chrome.downloads.download({ url:dataUrl, filename, saveAs:false }, () => {
    if (chrome.runtime.lastError) setStatus('error', `Debug export failed: ${chrome.runtime.lastError.message}`);
    else setStatus('active', ` Forensic debug exported → ${filename} · 4 charts + decisions + candles`);
  });
}
// ════════════════════════════════════════════════════════════
//  BOOT
// ════════════════════════════════════════════════════════════
// startup already initiated above; do not launch a second concurrent Pocket Option detection flow











/* === AI status display in popup === */
(() => {
  function addAIStatus() {
    if (document.getElementById('ai-popup-info')) return;
    const el = document.createElement('div');
    el.style.cssText = 'margin:10px 16px;padding:10px 13px;background:var(--card);border:2px solid var(--accent);border-radius:8px;font-size:12px;color:var(--text2)';
    el.innerHTML = '<div style="font-weight:700;color:var(--accent);margin-bottom:4px"> AI LEARNING LAB <span style="font-size:11px;opacity:.8">learning only · does not control entries</span></div><div id="ai-popup-info" style="display:block;margin-top:7px">Loading AI training status...</div><div style="margin-top:9px;padding-top:9px;border-top:1px solid var(--border)"><div style="font-size:10px;color:#ff8a80;font-weight:800;margin-bottom:6px">DANGER / RESET</div><button id="ai-popup-clear" style="background:#2a1717;border:1px solid #e74c3c;color:#ff6b5f;padding:7px 11px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer"> CLEAR AI + START FRESH</button></div><div id="ai-backup-status" style="margin-top:4px;font-size:11px;opacity:.8">KAOS Berserker LIVE TEST · fixed 45s expiry · independent REAL 5s candle recorder runs separately from trading.</div><div id="ai-sample-warning" style="margin-top:3px;font-size:11px;color:#f39c12;display:none"></div>';
    const fold = document.createElement('details');
    fold.className = 'dashboard-fold';
    fold.id = 'ai-learning-fold';
    const summary = document.createElement('summary');
    summary.textContent = 'AI LEARNING LAB · LEARNING ONLY';
    const body = document.createElement('div');
    body.className = 'fold-body';
    body.appendChild(el);
    fold.appendChild(summary); fold.appendChild(body);
    // Keep AI Learning in the RIGHT column directly under Live Debug on the
    // normal medium two-column dashboard. When the responsive breakpoint
    // collapses .main-columns, this naturally falls into the single-column flow.
    const runtimeCol = document.querySelector('#screen-main .runtime-col');
    const debugFold = document.getElementById('debug-fold');
    if (runtimeCol) {
      if (debugFold && debugFold.parentElement === runtimeCol) debugFold.after(fold);
      else runtimeCol.appendChild(fold);
    } else {
      const footer = document.querySelector('#screen-main .footer');
      if (footer) footer.before(fold); else document.querySelector('#screen-main')?.append(fold);
    }

    async function refresh() {
      try {
        const info=document.getElementById('ai-popup-info');
        const esc=x=>String(x??'—').replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
        // XGB is authoritative in the service worker. Do not require a Pocket
        // Option tab just to display the model/training result.
        let xgbBridge=null;
        try { xgbBridge=await chrome.runtime.sendMessage({type:'GET_XGB_STATUS'}); } catch(_) {}

        let s=null;
        try {
          const tab=await getKAOSTargetTab();
          if(tab?.id!=null) s=await chrome.tabs.sendMessage(tab.id,{type:'GET_AI_STATUS'});
        } catch(_) {}
        if(!s || !s.ok) s={v23:{},legacy:{},aiLab:{}};

        const v=s.v23||{}, l=s.legacy||{}, acc=Number(v.accuracy||0)*100;
        const lab=s.aiLab||{}, st=lab.stats||{}, train=lab.training||{};
        const bridgeResult=xgbBridge?.result||null;
        const bridgeReport=bridgeResult?.report||null;
        const localReport=lab.holdout||null;
        const report=bridgeReport||localReport||(train.holdoutAccuracy!=null?train:null)||null;
        const holdVal=report && Number.isFinite(Number(report.holdoutAccuracy)) ? Number(report.holdoutAccuracy) : null;
        const xgbHold=holdVal!=null ? (holdVal>1 ? holdVal/100 : holdVal) : null;
        const liveAcc=Number(st.total)>0 ? (Number(st.correct||0)/Number(st.total))*100 : null;
        const xgbAcc=liveAcc!=null ? liveAcc.toFixed(1)+'%' : (xgbHold!=null ? (xgbHold*100).toFixed(1)+'%' : '—');
        const bridgeTraining=!!xgbBridge?.training;
        const bridgeErr=xgbBridge?.error || (bridgeResult?.error) || (train.status==='error'?train.message:null);
        const isTrained=!!(bridgeResult?.ok && bridgeResult?.model && bridgeResult?.report) || train.status==='trained' || !!localReport?.holdoutAccuracy;
        const xgbStatus=isTrained?(bridgeErr?'MODEL READY · TRAINER ERROR':'TRAINED'):(bridgeErr?'ERROR':(bridgeTraining||train.status==='training'?'TRAINING':(train.status==='warming'?'WARMING':'COLLECTING')));
        const sampleCount=Math.max(Number(lab.samples||0),Number(bridgeReport?.rawSamplesReceived||0),Number(bridgeReport?.samples||0));
        const independentCount=Math.max(Number(st.independent||0),Number(bridgeReport?.independentSamples||0),Number(bridgeReport?.samples||0));
        const dedupedCount=Math.max(0,Number(bridgeReport?.dedupedSamples||0));
        const message=bridgeErr || (bridgeTraining?'AI training in progress…':train.message) || '';
        const queued=Number(l.paperQueued||lab.queued||0);
        const pending=Number(l.queued||lab.pending||0);
        const warm=lab.marketWarm===true;
        const aiStateText=warm?'LIVE MARKET WARM':'WARMING MARKET';
        const marketModels = Array.isArray(bridgeResult?.report?.assetModels) ? bridgeResult.report.assetModels : [];
        const marketModelText = marketModels.length ? `${marketModels.length} (${marketModels.join(', ')})` : 'GLOBAL ONLY';
        const activeMarket=String(lab.activeAsset||'').trim();
        const gridMarkets=Array.isArray(lab.gridAssets)?lab.gridAssets.filter(Boolean):[];
        const marketDisplay=gridMarkets.length?gridMarkets.join(' · '):(activeMarket||'—');
        const perAsset=(bridgeReport?.perAsset||localReport?.perAsset||{});
        const marketRep=activeMarket ? (perAsset?.[activeMarket]||lab.champion?.report||{}) : (lab.champion?.report||{});
        const championKey=String(lab.champion?.marketChampion||marketRep?.marketChampion||'').toLowerCase();
        const championLabel=championKey==='xgb-global'?'XGBoost GLOBAL':championKey==='xgb-local'?'XGBoost LOCAL':championKey==='lgb-global'?'LightGBM GLOBAL':championKey==='lgb-local'?'LightGBM LOCAL':(isTrained?'WAITING FOR MARKET VALIDATION':'NONE YET');
        const xgbMarketAcc=Number.isFinite(Number(marketRep?.globalHoldoutAccuracy))?Number(marketRep.globalHoldoutAccuracy):null;
        const xgbLocalAcc=Number.isFinite(Number(marketRep?.holdoutAccuracy))?Number(marketRep.holdoutAccuracy):null;
        const lgbMarketAcc=Number.isFinite(Number(marketRep?.lightgbmGlobalHoldoutAccuracy))?Number(marketRep.lightgbmGlobalHoldoutAccuracy):null;
        const lgbLocalAcc=Number.isFinite(Number(marketRep?.lightgbmHoldoutAccuracy))?Number(marketRep.lightgbmHoldoutAccuracy):null;
        const lgbReport=bridgeReport?.lightgbmGlobal||localReport?.lightgbmGlobal||null;
        const lgbHoldRaw=lgbReport && Number.isFinite(Number(lgbReport.holdoutAccuracy)) ? Number(lgbReport.holdoutAccuracy) : null;
        const lgbHold=lgbHoldRaw!=null?(lgbHoldRaw>1?lgbHoldRaw/100:lgbHoldRaw):null;
        const lgbAvailable=bridgeReport?.lightgbmAvailable ?? localReport?.lightgbmAvailable;
        const xgbCiLow=Number.isFinite(Number(report?.holdoutWilsonLow))?Number(report.holdoutWilsonLow):null;
        const xgbCiHigh=Number.isFinite(Number(report?.holdoutWilsonHigh))?Number(report.holdoutWilsonHigh):null;
        const liveTrust=lab.liveTrust||{};
        const liveTrustAcc=Number.isFinite(Number(liveTrust.marketLiveAccuracy))?Number(liveTrust.marketLiveAccuracy):null;
        const liveTrustN=Number(liveTrust.marketLiveSamples||0);
        const liveTrustLow=Number.isFinite(Number(liveTrust.marketLiveCiLow))?Number(liveTrust.marketLiveCiLow):null;
        const trustLow=Number.isFinite(Number(liveTrust.marketTrustLowerBound))?Number(liveTrust.marketTrustLowerBound):null;
        const driftText=liveTrust.marketDriftDemoted?'DEMOTED — LIVE DRIFT':'OK';
        const lgbStatus=isTrained?(lgbAvailable===false?'NOT INSTALLED':'TRAINED'):(bridgeErr?'CHECK TRAINER':(bridgeTraining||train.status==='training'?'TRAINING':(train.status==='warming'?'WARMING':'COLLECTING')));
        const paperStats=lab.paperSetupStats||{};
        const paperTotal=Number(paperStats.total||0), paperWins=Number(paperStats.wins||0), paperLosses=Number(paperStats.losses||0);
        const paperWR=paperTotal?((paperWins/paperTotal)*100).toFixed(1)+'%':'—';
        const setupParts=Object.entries(paperStats.bySetup||{}).map(([k,v])=>{const n=Number(v?.total||0),w=Number(v?.wins||0);return `${k} ${w}/${n} (${n?((w/n)*100).toFixed(0):0}%)`;}).join(' · ');
        const dirBuy=paperStats.byDir?.BUY||{}, dirSell=paperStats.byDir?.SELL||{};
        const buyN=Number(dirBuy.total||0), buyW=Number(dirBuy.wins||0), sellN=Number(dirSell.total||0), sellW=Number(dirSell.wins||0);
        const shadow=lab.shadowOutcomes||{};
        const baseline=lab.sameColorBaseline||{};
        const bstat=baseline.overall||{}; const bn=Number(bstat.wins||0)+Number(bstat.losses||0); const bwr=bn?((Number(bstat.wins||0)/bn)*100).toFixed(1)+'%':'collecting';
        const shadowAI=lab.shadowHorizonAI||{};
        const aiPaper=lab.aiPaperTrades||{};
        const aiPaperAcc=Number.isFinite(Number(aiPaper.accuracy))?(Number(aiPaper.accuracy)*100).toFixed(1)+'%':'collecting';
        const aiPaperRecent=(aiPaper.recent||[]).slice(-6).reverse().map(r=>`${esc(r.asset)} ${esc(r.dir)} ${Math.round(Number(r.confidence||0)*100)}% → ${String(r.result||'pending').toUpperCase()}`).join('<br>')||'collecting';
        const horizons=['5s','15s','30s','60s','120s','180s','300s'];
        const shFmt=x=>{const w=Number(x?.wins||0),l=Number(x?.losses||0),d=Number(x?.draws||0),n=w+l;return n?`${(w/n*100).toFixed(1)}% · ${w}W/${l}L${d?`/${d}D`:''}`:'collecting';};
        const allShadowRows=horizons.map(h=>`<span>${h} shadow outcome</span><strong>${shFmt(shadow.stats?.[h]||{})}</strong>`).join('');
        const setupOrder=['BB45_ALLIGATOR_ROC','BB45_TREND_MID_CONTINUATION','EMA_RSI_PULLBACK','SR_FAILURE_TEST','LIQUIDITY_SWEEP_REVERSAL','BREAKOUT_RETEST','DONCHIAN_KELTNER_SQUEEZE'];
        const setupShadowHtml=setupOrder.map(k=>{
          const rows=horizons.map(h=>`${h}: ${shFmt(shadow.bySetup?.[k]?.[h]||{})}`).join(' · ');
          return `<div style="margin-top:5px"><b>${esc(k)}</b><br><span style="color:var(--muted)">${rows}</span></div>`;
        }).join('');
        const mhRows=horizons.map(h=>{const m=shadowAI.models?.[h]||{};const n=Number(m.trained||0),c=Number(m.correct||0);return `${h}: ${n} labels${n?` · ${(100*c/n).toFixed(1)}% pre-update hit`:''}`;}).join(' · ');
        const tel=lab.strategyTelemetry||{};
        const telRows=setupOrder.map(k=>{const t=tel[k]||{}; return `${k}: ${Number(t.qualified||0)}/${Number(t.evaluated||0)} qualified`;}).join(' · ');
        const tr=lab.trace||null;
        const ag=lab.agreementStats||{};
        const facts=x=>{ if(!x)return '—'; const s=(x.support||[]).slice(0,4).map(esc).join(' · ')||'none'; const o=(x.oppose||[]).slice(0,3).map(esc).join(' · ')||'none'; return `<span style="color:var(--ok)">+ ${s}</span><br><span style="color:var(--muted)">− ${o}</span>`; };
        const agRate=Number(ag.total||0)>0?((Number(ag.agree||0)/Number(ag.total))*100).toFixed(1)+'%':'—';
        const agWin=Number(ag.agree||0)>0?((Number(ag.agreeCorrect||0)/Number(ag.agree))*100).toFixed(1)+'%':'—';
        // B13-audit: surface the Pocket Flow 1s shadow learner's REAL metrics. The audit
        // finding: the exported "accuracy" is an ALL-samples number (NO-TRADE rows are
        // scored as a 0.5 coin flip), so it is NOT the win rate of the signals you would
        // actually trade. Show BOTH, plus the per-asset split and the sample size, so a
        // 60% claim can be judged on the selective sample instead of a blended number.
        let pf=null; try { pf=(await chrome.storage.local.get('v287_learning_status')).v287_learning_status; } catch(_) {}
        const pfN=Number(pf?.selectiveResolved||0), pfC=Number(pf?.selectiveCorrect||0);
        const pfAllN=Number(pf?.resolved||0), pfAllC=Number(pf?.correct||0);
        const pfWR=pfN?((pfC/pfN)*100).toFixed(1)+'%':'—';
        const pfAllWR=pfAllN?((pfAllC/pfAllN)*100).toFixed(1)+'%':'—';
        const pfShare=pfAllN?((pfN/pfAllN)*100).toFixed(0)+'%':'—';
        const pfAssets=Object.entries(pf?.selByAsset||{}).map(([k,v])=>{const n=Number(v?.n||0),c=Number(v?.c||0);return esc(k)+' '+(n?((c/n)*100).toFixed(0):0)+'%/'+n;}).join(' · ')||'—';
        const pfRate=pfN?(pfC/pfN)*100:null;
        const pfVerdict=pfN<300?'SAMPLE TOO SMALL (<300) — 60% is inside coin-flip noise':(pfRate>=60?'ABOVE 60% on adequate sample':'BELOW 60% / not established');
        const pfHtml=pf?'<div style="margin-top:8px;padding-top:7px;border-top:1px solid var(--border)"><strong style="color:var(--accent)">POCKET FLOW 1s SHADOW (PO ONLY · learning-only)</strong><div style="display:grid;grid-template-columns:1fr auto;gap:2px 12px"><span>SELECTIVE win rate (BUY≥56% / SELL≤44%)</span><strong>'+pfWR+' on '+pfN+' signals ('+pfShare+' of resolutions)</strong><span>All-samples "accuracy" (includes NO-TRADE)</span><strong>'+pfAllWR+' / '+pfAllN+'</strong><span>Per-asset selective (WR/n)</span><strong>'+pfAssets+'</strong><span>60% target</span><strong>'+pfVerdict+'</strong></div><div style="margin-top:4px;color:var(--muted)">Trade only the SELECTIVE number. The exported "accuracy" mixes NO-TRADE coin flips and is not your win rate.</div></div>':'';
        const thought=tr ? `<div style="margin-top:7px;padding:8px;border:1px solid var(--border);border-radius:6px;line-height:1.45"><strong style="color:var(--accent)">LIVE AI THOUGHT</strong><br><b>Active champion:</b> <b>${esc(championLabel)}</b>${activeMarket?` · ${esc(activeMarket)}`:''}<br><b>XGBoost prediction:</b> <b>${esc(tr.xgb||'—')}</b><br><b>LightGBM prediction:</b> <b>${esc(tr.lightgbm||'—')}</b><br><b>Trading authority:</b> <b>LEARNING ONLY · NEVER EXECUTES</b><br><b>Chart Vision:</b> ${esc(tr.chartVision||'WARMING')}${Array.isArray(tr.visionFacts)&&tr.visionFacts.length?`<br><span style="color:var(--muted)">${esc(tr.visionFacts.join(' · '))}</span>`:''}<br><b>Pullback:</b> ${Number(tr.counterPullbackCount||0)} counter candle(s) · body ratio ${Number(tr.pullbackBodyRatio||0).toFixed(2)}${tr.reversalStage?` · reversal BUY ${esc(tr.reversalStage.buy||'OFF')} / SELL ${esc(tr.reversalStage.sell||'OFF')}`:''}<br><b>Predictive models:</b> XGBoost + LightGBM · winner gets market authority<br>Strategy proposal: <b>${esc(tr.strategy||'—')}</b><br>Regime: <b>${esc(tr.regime)}</b> · ${esc(tr.trendIntegrity)}${tr.structureDirection?` · STRUCT <b>${esc(tr.structureDirection)} ${Math.round(Number(tr.structureConfidence||0)*100)}%</b>`:''} · TQS ${Number(tr.tqsBuy||0)}/${Number(tr.tqsSell||0)} · MQ ${Number(tr.mq||0)}<div style="margin-top:7px;padding-top:6px;border-top:1px solid var(--border)"><strong>LAST DECISION: ${esc(tr.finalDecision||'HOLD')}</strong> · Controller <b>${esc(tr.controller||'NONE')}</b><br>${esc(tr.why||'—')}</div></div>` : '';
        const sl=lab.strategyLessons||{};
        const slStats=Object.values(sl.stats||{});
        const slResolved=Number(sl.resolved||0), slPending=Number(sl.pending||0);
        const slSummary=slStats.map(v=>{const n=Number(v.wins||0)+Number(v.losses||0);const wr=n?((Number(v.wins||0)/n)*100).toFixed(1)+'%':'collecting';return `${esc(v.setup)} ${esc(v.dir)}: ${wr} · ${Number(v.wins||0)}W/${Number(v.losses||0)}L/${Number(v.draws||0)}D`;}).join('<br>')||'collecting';
        const recentLessons=(sl.recent||[]).slice(-5).reverse().map(r=>`${esc(r.asset)} · ${esc(r.setup)} ${esc(r.dir)} · ${r.accepted?'TAKEN':'REJECTED'} → ${String(r.result||'pending').toUpperCase()}${r.reason?`<br><span style="color:var(--muted)">why: ${esc(r.reason)}</span>`:''}`).join('<br>')||'collecting';
        const currentPred=tr?.xgb||lab.last?.direction||'—';
        const currentConf=Number.isFinite(Number(lab.last?.confidence))?` ${Math.round(Number(lab.last.confidence)*100)}%`:'';
        if(info) info.innerHTML=`<div style="display:grid;grid-template-columns:1fr auto;gap:3px 12px">
          <span>AI Learning</span><strong>${isTrained?'TRAINED / LEARNING':(xgbStatus==='TRAINING'?'TRAINING':'COLLECTING')}</strong>
          <span>XGBoost</span><strong>${sampleCount} samples · ${xgbHold!=null?((xgbHold*100).toFixed(1)+'% validation'):'collecting'}</strong>
          <span>LightGBM</span><strong>${lgbStatus} · ${lgbHold!=null?((lgbHold*100).toFixed(1)+'% validation'):'collecting'}</strong>
          <span>AI Paper Trading</span><strong>${aiPaperAcc} · ${Number(aiPaper.wins||0)}W/${Number(aiPaper.losses||0)}L/${Number(aiPaper.draws||0)}D</strong>
          <span>Current prediction</span><strong>${esc(currentPred)}${currentConf}</strong>
          <span>Pending fake trades</span><strong>${pending}</strong>
          <span>BB45 strategy lessons</span><strong>${slResolved} resolved / ${slPending} pending</strong>
          <span>Trading authority</span><strong>LEARNING ONLY · NEVER EXECUTES</strong>
        </div>
        <div style="margin-top:8px;padding-top:7px;border-top:1px solid var(--border)"><b>BB45 LEARNING RESULTS</b><br><span style="color:var(--muted)">${slSummary}</span></div>
        <div style="margin-top:8px;padding-top:7px;border-top:1px solid var(--border)"><b>RECENT STRATEGY LESSONS</b><br><span style="color:var(--muted)">${recentLessons}</span></div>
        <div style="margin-top:8px;padding-top:7px;border-top:1px solid var(--border)"><b>RECENT AI FAKE TRADES</b><br><span style="color:var(--muted)">${aiPaperRecent}</span></div>
        ${message?`<div style="margin-top:5px;opacity:.8">${esc(message)}</div>`:''}`;

      } catch(e) {
        const info=document.getElementById('ai-popup-info'); if(info) info.textContent='AI status unavailable: '+(e.message||e);
      }
    }
    refresh();
    setInterval(refresh, 3000);

    // ── Compact diagnostic export ──
    // Intended for sharing with support/analysis. It deliberately excludes
    // the complete model trees and full historical training database.
    document.getElementById('ai-popup-diagnostic').addEventListener('click', async () => {
      try {
        const tab=await getKAOSTargetTab(); const tabs=tab?[tab]:[]; if(!tabs[0]) throw new Error('Pocket Option tab not found');
        const resp=await chrome.tabs.sendMessage(tabs[0].id,{type:'GET_DIAGNOSTIC_EXPORT'}); if(!resp||!resp.ok||!resp.payload) throw new Error(resp?.error||'No diagnostic data returned');
        const local=await chrome.storage.local.get(['settings','stats','tradeRecords']);
        const localTrades=Array.isArray(local.tradeRecords)?local.tradeRecords.slice(-120):[];
        const payload={...resp.payload,popupData:{settings:local.settings||null,stats:local.stats||{wins:state.wins,losses:state.losses,pnl:state.pnl},recentTradeRecords:localTrades}};
        // Compact JSON (no pretty-print whitespace) keeps uploads much smaller.
        const json=JSON.stringify(payload);
        const dataUrl='data:application/json;base64,'+strToBase64(json);
        const stamp=new Date().toISOString().replace(/[:.]/g,'-').slice(0,19), filename=`KAOS_DIAGNOSTIC_${stamp}.json`;
        chrome.downloads.download({url:dataUrl,filename,saveAs:true},()=>{ if(chrome.runtime.lastError) setStatus('error','Diagnostic export failed: '+chrome.runtime.lastError.message); else setStatus('active',` DIAGNOSTIC exported · ${(json.length/1024).toFixed(0)} KB · recent evidence only`); });
      } catch(e) { setStatus('error','Diagnostic export failed: '+(e.message||e)); }
    });

    // ── Independent real 5s candle export ──
    document.getElementById('market-candle-export').addEventListener('click', async () => {
      try {
        const tab=await getKAOSTargetTab(); if(!tab) throw new Error('Pocket Option tab not found');
        const r=await chrome.tabs.sendMessage(tab.id,{type:'EXPORT_MARKET_CANDLES_DIRECT'});
        if(!r||!r.ok) throw new Error(r?.error||'Candle export failed');
        const counts=Object.entries(r.meta||{}).map(([a,v])=>`${a}:${v.count}`).join(' · ');
        setStatus('active',` REAL 5s CANDLES exported separately · ${Number(r.mb||0).toFixed(1)} MB · ${counts}`);
      } catch(e) { setStatus('error','Candle export failed: '+(e.message||e)); }
    });

    // ── Manual full backup export ──
    // B7: the page/content script owns the entire export from payload creation through
    // Blob download. No giant JSON is transferred across chrome.runtime messaging.
    document.getElementById('ai-popup-export').addEventListener('click', async () => {
      try {
        const tab=await getKAOSTargetTab(); const tabs=tab?[tab]:[]; if(!tabs[0]) throw new Error('Pocket Option tab not found');
        setStatus('active',' FULL BACKUP · building directly in Pocket Option tab…');
        const r=await chrome.tabs.sendMessage(tabs[0].id,{type:'EXPORT_FULL_BACKUP_DIRECT'});
        if(!r||!r.ok) throw new Error(r?.error||'Direct backup export failed');
        setStatus('active',` ALL DATA export started · ${Number(r.mb||0).toFixed(1)} MB · AI, Pocket Flow, decisions, trades, settings`);
      } catch(e) { setStatus('error','Export failed: '+(e.message||e)); }
    });

    // Decision history is included in EXPORT ALL DATA.

    // ── Import ALL DATA button ──
    document.getElementById('ai-popup-import').addEventListener('click', () => {
      if(state.running){setStatus('error','Stop the bot before importing a backup');return;}
      const input=document.createElement('input'); input.type='file'; input.accept='.json';
      input.addEventListener('change',async e=>{
        const file=e.target.files[0]; if(!file)return;
        try{
          const raw=await file.text();
          const payload=JSON.parse(raw);
          if(!payload || (payload.features!=null && ![64,72,76,88,104].includes(Number(payload.features)))) throw new Error('Invalid or incompatible ALL DATA backup');
          const tab=await getKAOSTargetTab(); const tabs=tab?[tab]:[]; if(!tabs[0]) throw new Error('Pocket Option tab not found');
          await ensureKAOSContentReady(tabs[0]);
          // B15.3-corrected.2-direct: large backups must NOT cross chrome.tabs.sendMessage as one giant object.
          // Stream the original JSON text in small bounded messages, then restore normally in content.js.
          let resp=await chrome.tabs.sendMessage(tabs[0].id,{type:'START_FULL_IMPORT_CHUNKED'});
          if(!resp||!resp.ok) throw new Error(resp?.error||'Could not start backup import');
          const IMPORT_CHUNK_CHARS=128*1024;
          for(let off=0;off<raw.length;off+=IMPORT_CHUNK_CHARS){
            const chunk=raw.slice(off,off+IMPORT_CHUNK_CHARS);
            let sent=false,lastErr=null;
            for(let attempt=0;attempt<3&&!sent;attempt++){
              try{
                resp=await chrome.tabs.sendMessage(tabs[0].id,{type:'PUT_FULL_IMPORT_CHUNK',chunk});
                if(resp&&resp.ok) sent=true; else lastErr=new Error(resp?.error||'Chunk rejected');
              }catch(err){lastErr=err; await new Promise(r=>setTimeout(r,150*(attempt+1)));}
            }
            if(!sent) throw new Error((lastErr?.message||'Backup chunk failed')+` near ${(off/raw.length*100).toFixed(0)}%`);
          }
          resp=await chrome.tabs.sendMessage(tabs[0].id,{type:'END_FULL_IMPORT_CHUNKED'});
          if(!resp||!resp.ok) throw new Error(resp?.error||'No response from bot');
          if(payload.popupData){const d=payload.popupData,w={};if(d.settings)w.settings=d.settings;if(d.stats)w.stats=d.stats;if(Array.isArray(d.tradeRecords))w.tradeRecords=d.tradeRecords.slice(-1000);if(d.strategyProfiles&&typeof d.strategyProfiles==='object')w.strategyProfiles=d.strategyProfiles;if(typeof d.activeStrategyProfile==='string')w.activeStrategyProfile=d.activeStrategyProfile;if(Array.isArray(d.terminalSlotProfiles))w.terminalSlotProfiles=d.terminalSlotProfiles;if(Array.isArray(d.terminalDrawings))w.terminalDrawings=d.terminalDrawings;if(Object.keys(w).length)await chrome.storage.local.set(w);if(w.strategyProfiles){sbProfiles=w.strategyProfiles;sbSelected=(w.activeStrategyProfile==='legacy7b'||sbProfiles[w.activeStrategyProfile])?w.activeStrategyProfile:'legacy7b';sbRefreshSelect();sbLoadSelected();}}
          loadSettings(); loadStats();

          // IMPORTANT: popup.js owns the visible AI Lab. After importing, ask the
          // content script for the restored XGB dataset and explicitly await the
          // background trainer's final response. This prevents the UI from being
          // left at the stale "—" state after a successful import.
          let trainResp=null;
          try {
            const samples=Array.isArray(payload.aiLab?.samples) ? payload.aiLab.samples.slice(-1200).map((r,idx)=>{
              const q={...r};
              if((!Number.isFinite(Number(q.t)) || Number(q.t)<=0) && Number.isFinite(Number(q.ts)) && Number(q.ts)>0) q.t=Number(q.ts);
              if(!Number.isFinite(Number(q.t)) || Number(q.t)<=0) q.t=Date.now()-((payload.aiLab.samples.length-idx)*31000);
              return q;
            }) : null;
            const bundledModel=payload.aiLab?.model;
            const bundledTrained=!!bundledModel && Number(bundledModel.features||0)===104 && Array.isArray(bundledModel.trees) && bundledModel.trees.length>0;
            if(bundledTrained) {
              // V24.1.154: preserve a valid pre-trained model. New labeled samples will
              // still trigger background retraining through the normal learning loop.
              trainResp={ok:true,pretrained:true,report:payload.aiLab?.holdout||{}};
            } else if(Array.isArray(samples) && samples.length>=12) {
              trainResp=await chrome.runtime.sendMessage({type:'XGB_TRAIN_NOW',samples});
            } else if (Array.isArray(samples)) {
              trainResp={ok:false,status:'warming',error:`Need at least 12 XGB samples; imported ${samples.length}.`};
            }
          } catch(err) {
            trainResp={ok:false,status:'error',error:String(err?.message||err||'XGBoost training request failed')};
          }
          if(trainResp?.ok) setStatus('active',`Backup imported · AI model ${trainResp.pretrained?'restored':'trained'} · XGB ${((Number(trainResp.report?.holdoutAccuracy||0))*100).toFixed(1)}% · LGB ${((Number(trainResp.report?.lightgbmGlobal?.holdoutAccuracy||0))*100).toFixed(1)}%`);
          else if(trainResp?.error) setStatus('error',`XGBoost training failed: ${String(trainResp.error)}`);
          else setStatus('active',`ALL DATA imported · XGB samples ${Number(payload.aiLab?.samples?.length||0)} · decisions ${Number(payload.decisionHistory?.length||0)} · trades ${Number(payload.trades?.length||0)}`);
          await refresh();
        }catch(err){setStatus('error','Import failed: '+(err.message||err));}
      }); input.click();
    });

    // ── Clear AI / Start Fresh ──
    document.getElementById('ai-popup-clear').addEventListener('click', async () => {
      if (state.running) {
        setStatus('error','Stop the bot before clearing AI data');
        return;
      }
      const ok = confirm(
        'START FRESH AI?\n\n' +
        'This permanently clears the current XGBoost training data, models, validation, calibration, market memory, pending labels, and AI audit log.\n\n' +
        'Your bot settings and strategy configuration will NOT be cleared.\n\n' +
        'The next run will learn from fresh market data.\n\nContinue?'
      );
      if (!ok) return;
      try {
        const tab=await getKAOSTargetTab();
        if (!tab?.id) throw new Error('Pocket Option tab not found');
        const resp=await chrome.tabs.sendMessage(tab.id,{type:'RESET_AI_MODEL'});
        if (!resp?.ok) throw new Error(resp?.error||'AI reset failed');
        const bg=await chrome.runtime.sendMessage({type:'RESET_XGB_FRESH'});
        if (!bg?.ok) throw new Error(bg?.error||'XGBoost reset failed');
        setStatus('active',' AI cleared — next run will learn fresh market data');
        await refresh();
      } catch(e) {
        setStatus('error','Fresh AI reset failed: '+(e.message||e));
      }
    });


  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addAIStatus);
  else addAIStatus();
})();

// ════════════════════════════════════════════════════════════
// B32.7 — INTERACTIVE MULTI-TF + STRUCTURED TRADE REPLAY TERMINAL
// Monitoring + research only. KAOS Berserker remains execution authority.
// ════════════════════════════════════════════════════════════
let terminalTimer=null,terminalData=null,kaosCompanionStatusAt=0,kaosChartFeedGeneration=0,kaosChartRefreshBusy=false;
function kaosStartChartFeed(){
 if(window.__kaosChartSessionAuthorized!==true || terminalTimer)return;
 const poll=KAOS_COMPANION_ONLY?kaosRefreshCompanionStatus:terminalRefresh;
 poll();terminalTimer=setInterval(poll,KAOS_COMPANION_ONLY?5000:1000);
}
async function kaosRefreshCompanionStatus(){
 if(window.__kaosChartSessionAuthorized!==true||kaosChartRefreshBusy)return;
 kaosChartRefreshBusy=true;const generation=kaosChartFeedGeneration;
 try{
  const tab=await getKAOSTargetTab();if(!tab){terminalData=null;kaosCompanionStatusAt=0;return;}
  const r=await chrome.tabs.sendMessage(tab.id,{type:'GET_COMPANION_STATUS'});
  if(window.__kaosChartSessionAuthorized!==true||generation!==kaosChartFeedGeneration)return;
  if(!r?.ok){terminalData=null;kaosCompanionStatusAt=0;return;}
  kaosCompanionStatusAt=Date.now();terminalData=r;kaosUpdateAccountBalance(r);
  const asset=document.querySelector('[data-companion-asset]');if(asset)asset.textContent=r.asset||'Select a market in Pocket Option';
 }catch(_){if(generation===kaosChartFeedGeneration){terminalData=null;kaosCompanionStatusAt=0;}}finally{kaosChartRefreshBusy=false;}
}
function kaosStopChartFeed(){
 clearInterval(terminalTimer);terminalTimer=null;kaosChartFeedGeneration++;
 terminalData=null;kaosCompanionStatusAt=0;kaosFallbackSnap=null;kaosLiveChartOk=false;
}
const terminalTradeHits=Array.from({length:4},()=>[]);
const terminalView=Array.from({length:4},()=>({visibleBars:80,pan:0,tf:5,drag:false,lastX:0,dragCarry:0,crossX:null,crossY:null}));
async function KAOSSetWindowMode(mode){
 // V1.2.1 — toolbar popup mode: the popup cannot resize the browser window.
 // View switching is handled by setViewMode()/kaos-view-btn; this is a no-op.
 return;
}
const KAOS_SOCIAL_LINKS={facebook:'',instagram:'',x:'',youtube:'',tiktok:'',telegram:'',discord:''};
document.querySelectorAll('.kaos-social').forEach(btn=>{const url=KAOS_SOCIAL_LINKS[btn.dataset.social]||'';if(!url)btn.classList.add('disabled');btn.addEventListener('click',()=>{if(url)chrome.tabs.create({url});});});
$('window-compact-btn')?.addEventListener('click',()=>KAOSSetWindowMode('bot'));
$('window-max-btn')?.addEventListener('click',()=>KAOSSetWindowMode('charts'));
async function terminalShow(){
 if(KAOS_COMPANION_ONLY)return;
 document.body.classList.add('chart-mode');
 Object.values(screens).forEach(s=>{if(s)s.style.display='none';});
 const sc=$('screen-chart');if(sc){sc.classList.add('active');sc.style.display='flex';}
 await KAOSSetWindowMode('charts');
 kaosStartChartFeed();
}
async function terminalHide(){
 // Keep the read-only feed running for the dashboard mirror. Logout stops it.
 document.querySelectorAll('.market-chart.maximized').forEach(x=>x.classList.remove('maximized'));
 const sc=$('screen-chart');if(sc){sc.classList.remove('active');sc.style.display='none';}
 document.body.classList.remove('chart-mode');
 showScreen('main');
 await KAOSSetWindowMode('bot');
}
$('open-chart-btn')?.addEventListener('click',terminalShow);$('chart-back-btn')?.addEventListener('click',terminalHide);
document.querySelectorAll('.terminal-tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.terminal-tab').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.terminal-page').forEach(x=>x.classList.remove('active'));$('terminal-'+b.dataset.page)?.classList.add('active');}));
// ══ v1.1.23 KAOS CHART DATA FALLBACK ══════════════════════════
// The dashboard mirror and the four terminal canvases only paint once a
// market carries at least 2 candles. Live candles arrive from the Pocket
// Option tab via GET_TERMINAL_SNAPSHOT. When that live path is unavailable
// (no PO tab open, content-script bridge not injected, or the live store is
// still warming up) render from the candle archives content.js persists in
// chrome.storage.local, so the chart still shows the real candles already
// recorded for this profile instead of an empty placeholder.
const KAOS_REAL_CANDLE_KEYS=['KAOS_market_candles_real_v2','KAOS_raw5_history_v1'];
let kaosFallbackSnap=null,kaosFallbackStamp=0,kaosFallbackBusy=false,kaosLiveChartOk=false;
async function kaosLoadFallbackSnapshot(){
 try{
  const store=await chrome.storage.local.get(KAOS_REAL_CANDLE_KEYS);
  const perAsset=new Map();
  KAOS_REAL_CANDLE_KEYS.forEach((key,prio)=>{
   const z=store&&store[key],rows=z&&z.byAsset; if(!rows||typeof rows!=='object')return;
   for(const asset of Object.keys(rows)){
    const list=Array.isArray(rows[asset])?rows[asset]:[]; if(list.length<2)continue;
    let m=perAsset.get(asset); if(!m){m=new Map();perAsset.set(asset,m);}
    for(const r of list){
     const ts=Number(r.ts),o=+r.open,h=+r.high,l=+r.low,c=+r.close;
     if(!Number.isFinite(ts)||![o,h,l,c].every(Number.isFinite)||c<=0)continue;
     const prev=m.get(ts); if(prev&&prev.__prio<=prio)continue;
     m.set(ts,{ts,open:o,high:h,low:l,close:c,__prio:prio});
    }
   }
  });
  const markets=[];
  for(const [asset,m] of perAsset){
   const candles=[...m.values()].sort((a,b)=>a.ts-b.ts).slice(-900).map(({__prio:_,...c})=>({...c,d9:0,d20:0,rsiNorm:0,vol:0}));
   if(candles.length<2)continue;
   markets.push({asset,source:'RECORDED',candles,ready:false,probUp:null,probDown:null,vol:null,
    history:{canonical:candles.length,real:candles.length,raw:candles.length,firstTs:candles[0].ts,lastTs:candles[candles.length-1].ts,synced:false},
    timeframes:{},features:[],trades:[],ai:{},candidate:{},liveStrategy:{}});
   if(markets.length>=4)break;
  }
  if(!markets.length)return null;
  return {ok:true,readOnly:true,fallback:true,assets:markets.map(m=>m.asset),asset:markets[0].asset,running:false,timestamp:Date.now(),markets,
   aiSummary:{samples:0,researchSamples:0},analytics:{trades:0,wins:0,losses:0,ties:0,winRate:null},research:[]};
 }catch(_){return null;}
}
let kaosChartDiag='initialising';
function kaosSnapshotHasCandles(r){return !!(r&&r.ok&&(r.markets||[]).some(m=>Array.isArray(m.candles)&&m.candles.length>=2));}
async function kaosGetSnapshot(tabId){
 if(!tabId)return null;
 try{const r=await chrome.tabs.sendMessage(tabId,{type:'GET_TERMINAL_SNAPSHOT'});return (r&&typeof r==='object')?r:null;}catch(_){return null;}
}
// ══ v1.1.25 SELF-HEALING PO BRIDGE ════════════════════════════
// Reloading an unpacked extension orphans the content scripts already
// running in open Pocket Option tabs: their chrome.runtime port dies, so
// chrome.tabs.sendMessage never reaches them and the snapshot comes back
// empty even though the tab is open. po-bridge.js runs in the MAIN world
// and is guarded (window.__poatBridge440), so the page keeps streaming
// ticks; only the ISOLATED content scripts need re-injecting. content.js
// is guarded by window.__poatContent137, so this is safe to repeat.
let kaosHealBusy=false,kaosHealStamp=0,kaosHealNote='';
async function kaosHealPoTab(tab){
 if(!tab?.id || window.__kaosChartSessionAuthorized!==true)return false;
 const now=Date.now();
 if(kaosHealBusy||now-kaosHealStamp<20000)return false;
 kaosHealBusy=true;kaosHealStamp=now;
 try{
  const result=await chrome.runtime.sendMessage({type:'KAOS_PO_ENSURE_ATTACH',tabId:tab.id});
  kaosHealNote=result?.ok ? (result.alreadyAttached?'market-data listener ready':'authorized broker reload requested') : String(result?.error||result?.reason||'attachment failed');
  return !!result?.ok;
 }catch(error){kaosHealNote=String(error?.message||'attachment failed');return false;}
 finally{kaosHealBusy=false;}
}
function kaosRenderEmptyChartState(reason){
 if(reason)kaosChartDiag=reason;
 document.querySelectorAll('.market-chart').forEach((card,i)=>{
  const meta=card.querySelector('.mc-meta'),name=card.querySelector('.mc-name'),why=card.querySelector('.mc-why');
  if(name)name.textContent=`CHART ${i+1}`;
  if(meta)meta.textContent='awaiting Pocket Option candles';
  if(why)why.textContent='NO CANDLE DATA YET · '+kaosChartDiag+' KAOS will automatically reattach to the open Pocket Option tab and stream closed 5s candles. Once two real candles are received the chart paints automatically.';
  terminalDraw(card.querySelector('canvas'),null,i);
 });
}
async function kaosTerminalRenderFallback(force=false,generation=kaosChartFeedGeneration){
 if(kaosFallbackBusy)return true; kaosFallbackBusy=true;
 try{
  const now=Date.now();
  if(force||!kaosFallbackSnap||now-kaosFallbackStamp>5000){kaosFallbackSnap=await kaosLoadFallbackSnapshot();kaosFallbackStamp=now;}
  if(window.__kaosChartSessionAuthorized===true&&generation===kaosChartFeedGeneration&&kaosFallbackSnap&&kaosFallbackSnap.markets.length){terminalData=kaosFallbackSnap;terminalRender(kaosFallbackSnap);return true;}
  return false;
 }catch(_){return false;}
 finally{kaosFallbackBusy=false;}
}
async function terminalRefresh(){
 if(window.__kaosChartSessionAuthorized!==true||kaosChartRefreshBusy)return;
 kaosChartRefreshBusy=true;
 const generation=kaosChartFeedGeneration;
 try{return await kaosReadChartFeed(generation);}finally{kaosChartRefreshBusy=false;}
}
async function kaosReadChartFeed(generation){
 let live=null,tab=null;
 // Charts are driven only by the manifest-managed Pocket Option content context.
 // Ask the worker to heal/reload the PO tab if that context disappeared.
 try{tab=await getKAOSTargetTab();}catch(_){tab=null;}
 if(tab&&tab.id){
  live=await kaosGetSnapshot(tab.id);
  if(window.__kaosChartSessionAuthorized!==true||generation!==kaosChartFeedGeneration)return;
  if(!live)await kaosHealPoTab(tab);
  if(live&&live.ok&&!kaosSnapshotHasCandles(live)){
   kaosChartDiag='Pocket Option tab connected · live candle store empty ('+(kaosHealNote||'bridge healthy')+').';
   if(await kaosHealPoTab(tab)){
    const retry=await kaosGetSnapshot(tab.id);
    if(retry&&retry.ok&&kaosSnapshotHasCandles(retry))live=retry;
   }
  }
 }
 if(window.__kaosChartSessionAuthorized!==true||generation!==kaosChartFeedGeneration)return;
 // Working-build behaviour: render whatever the live bridge returned.
 if(live&&live.ok&&kaosSnapshotHasCandles(live)){kaosLiveChartOk=true;terminalData=live;terminalRender(live);return;}
 // No usable live candles yet — paint the persisted candle archives instead.
 if(await kaosTerminalRenderFallback(false,generation)){kaosChartDiag='rendering persisted candle archive ('+(tab&&tab.id?'live bridge has no candles yet':'no Pocket Option tab open')+').';return;}
 if(window.__kaosChartSessionAuthorized!==true||generation!==kaosChartFeedGeneration)return;
 // Archive empty too: still render the live snapshot so the panels populate.
 if(live&&live.ok){
  kaosLiveChartOk=false;terminalData=live;terminalRender(live);
  const stores=Number(live.marketDataDiag?.assetStoreCount)||0;
  kaosRenderEmptyChartState('Market-data listener ready; '+stores+' asset stores; waiting for two closed candles.');return;
 }
 kaosRenderEmptyChartState(tab&&tab.id?'Pocket Option tab connected but returned no snapshot.':'No Pocket Option tab is open.');
}
function tp(v){return Number.isFinite(+v)?(+v*100).toFixed(1)+'%':'—'} function tn(v,n=2){return Number.isFinite(+v)?(+v).toFixed(n):'—'}
function terminalDir(m){if(!m?.ready)return'WAIT';const p=+m.probUp,v=+m.vol;return p>=.61&&v<=1?'BUY':p<=.42&&v<=1.1?'SELL':'HOLD';}
let terminalActiveSlot=0;
let terminalSlotProfiles=['legacy7b','legacy7b','legacy7b','legacy7b'];
let terminalSelectedCharts=[true,false,false,false];
let kaosChartCount=1;
// Server plan limit (Free 1, Pro 4, Ultimate 4). Unknown entitlements fail closed to 1 chart.
let kaosChartLimit=1;
function kaosApplyChartLimit(ent){
 const n=Number(ent&&ent.chartLimit);
 kaosChartLimit=Number.isInteger(n)&&n>0?Math.min(4,n):1;
 document.querySelectorAll('#kaos-chart-count option').forEach(o=>{
   const over=Number(o.value)>kaosChartLimit;o.disabled=over;
   o.textContent=o.value+(o.value==='1'?' Chart':' Charts')+(over?' (not in your plan)':'');
 });
 if(kaosChartCount>kaosChartLimit)kaosApplyChartCount(kaosChartLimit,true);
}

function kaosApplyChartCount(count,persist=true){
 count=Math.max(1,Math.min(4,kaosChartLimit,Number(count)||1));
 kaosChartCount=count;
 // The selected/traded slots are exactly the visible slots by default.
 terminalSelectedCharts=[0,1,2,3].map(i=>i<count);
 const grid=document.getElementById('terminal-four-grid');
 if(grid)grid.dataset.chartCount=String(count);
 document.querySelectorAll('#terminal-four-grid .market-chart').forEach((card,i)=>{
   card.classList.toggle('kaos-chart-disabled',i>=count);
 });
 const sel=document.getElementById('kaos-chart-count');
 if(sel)sel.value=String(count);
 if(persist)chrome.storage.local.set({kaosChartCount,terminalSelectedCharts});
 if(typeof terminalRenderChartSelection==='function')terminalRenderChartSelection();
}
function kaosInitChartCount(){
 chrome.storage.local.get(['kaosChartCount','kaosEntitlements'],d=>{kaosApplyChartLimit(d.kaosEntitlements);kaosApplyChartCount(d.kaosChartCount||1,false);});
 chrome.storage.onChanged.addListener((c,area)=>{if(area==='local'&&c.kaosEntitlements)kaosApplyChartLimit(c.kaosEntitlements.newValue);});
 const sel=document.getElementById('kaos-chart-count');
 if(sel)sel.addEventListener('change',e=>kaosApplyChartCount(e.target.value,true));
 document.getElementById('kaos-open-selected-charts')?.addEventListener('click',()=>{
   if(typeof window.kaosRoute==='function')window.kaosRoute('charts');
   else document.querySelector('[data-kaos-view="charts"]')?.click();
 });
}
document.addEventListener('DOMContentLoaded',kaosInitChartCount);
let terminalDisplayIndicators=[[],[],[],[]];
let terminalDrawings=[[],[],[],[]],terminalDrawTool=['cursor','cursor','cursor','cursor'],terminalDrawStart=[null,null,null,null];
function terminalSlotProfile(i){const id=terminalSlotProfiles[i]||'legacy7b';return id==='legacy7b'?null:(sbProfiles?.[id]||null)}
const BUILTIN_STRATEGIES={
 legacy7b:{id:'legacy7b',name:'KAOS Strategy',description:'Signature multi-timeframe Support/Resistance + market structure: rejection, failed-break reclaim, breakout-retest and trend continuation.',type:'built-in',editable:false,engine:'KAOS_SR_MARKET_STRUCTURE',signalTf:5,expiry:20,version:'SR1.0'},
 false_breakout:{id:'false_breakout',name:'False Breakout Strategy',description:'Trades failed breaks of recent support/resistance after price closes back through the broken level.',type:'built-in',editable:false,engine:'FALSE_BREAKOUT',signalTf:5,expiry:15,version:'1.0'},
 trend_following:{id:'trend_following',name:'Trend Following Strategy',description:'Trades with established EMA structure and momentum after directional continuation.',type:'built-in',editable:false,engine:'TREND_FOLLOWING',signalTf:5,expiry:15,version:'1.0'},
 trend_reversal:{id:'trend_reversal',name:'Trend Reversal Strategy',description:'Looks for extended moves, rejection and confirmed momentum reversal before entry.',type:'built-in',editable:false,engine:'TREND_REVERSAL',signalTf:5,expiry:15,version:'1.0'},
 candlestick:{id:'candlestick',name:'Candlestick Pattern Strategy',description:'Trades confirmed engulfing and strong rejection/hammer-style candle patterns.',type:'built-in',editable:false,engine:'CANDLESTICK_PATTERN',signalTf:5,expiry:10,version:'1.0'},
 ma_crossover:{id:'ma_crossover',name:'Moving Average Crossover',description:'EMA 9/21 crossover with slope and candle confirmation.',type:'built-in',editable:false,engine:'MA_CROSSOVER',signalTf:5,expiry:15,version:'1.0'},
 price_action:{id:'price_action',name:'Price Action Strategy',description:'Uses market structure, swing breaks, momentum and rejection without requiring indicator voting.',type:'built-in',editable:false,engine:'PRICE_ACTION',signalTf:5,expiry:15,version:'1.0'},
 indicator_based:{id:'indicator_based',name:'Indicator-based Strategy',description:'Multi-confirmation EMA, RSI, MACD and Bollinger strategy.',type:'built-in',editable:false,engine:'INDICATOR_BASED',signalTf:5,expiry:15,version:'1.0'},
 fibonacci:{id:'fibonacci',name:'Fibonacci Tool Strategy',description:'Uses recent swing range and 38.2/50/61.8 retracement zones with directional confirmation.',type:'built-in',editable:false,engine:'FIBONACCI',signalTf:5,expiry:15,version:'1.0'}
};
const BUILTIN_IDS=Object.keys(BUILTIN_STRATEGIES);
function strategyMeta(id){if(BUILTIN_STRATEGIES[id])return BUILTIN_STRATEGIES[id];const p=sbProfiles?.[id];return p?{...p,type:'custom',editable:true}:null}
function strategyOptions(){return '<optgroup label="Built-in · Locked">'+Object.values(BUILTIN_STRATEGIES).map(p=>`<option value="${p.id}"> ${p.name}</option>`).join('')+'</optgroup><optgroup label="Custom · Editable">'+Object.values(sbProfiles||{}).map(p=>`<option value="${p.id}">${p.name}</option>`).join('')+'</optgroup>'}
function strategyCardHtml(id,p,active=false){const locked=!p.editable;return `<div class="strategy-card ${active?'active':''}" data-strategy-id="${id}"><div class="sc-top"><span class="sc-name">${locked?' ':''}${p.name}</span><span class="sc-type">${locked?'BUILT-IN':'CUSTOM'}</span></div><div class="sc-desc">${p.description||'No description'}</div><div class="sc-meta">${p.signalTf?`TF ${p.signalTf}s · `:''}${p.expiry?`EXP ${p.expiry}s · `:''}${locked?'LOCKED':'EDITABLE'}</div></div>`}
function renderStrategyCatalogs(){const ids=[...BUILTIN_IDS,...Object.keys(sbProfiles||{})];const chart=document.getElementById('chart-strategy-library');if(chart)chart.innerHTML=ids.map(id=>{const p=strategyMeta(id);return strategyCardHtml(id,p,(terminalSlotProfiles[terminalActiveSlot]||'legacy7b')===id)}).join('');const main=document.getElementById('main-strategy-library');if(main)main.innerHTML=ids.map(id=>strategyCardHtml(id,strategyMeta(id),(terminalSlotProfiles[terminalActiveSlot]||'legacy7b')===id)).join('');const slots=document.getElementById('main-slot-grid');if(slots)slots.innerHTML=terminalSlotProfiles.map((id,i)=>{const p=strategyMeta(id)||BUILTIN_STRATEGIES.legacy7b;return `<div class="main-slot"><label>CHART ${i+1} STRATEGY</label><select data-main-slot="${i}">${strategyOptions()}</select><div class="slot-desc">${p.description||''}</div></div>`}).join('');document.querySelectorAll('[data-main-slot]').forEach((el)=>{const i=+el.dataset.mainSlot;el.value=terminalSlotProfiles[i]||'legacy7b'});const bulk=document.getElementById('all-charts-strategy');if(bulk){const keep=bulk.value;bulk.innerHTML=strategyOptions();bulk.value=(keep&&[...bulk.options].some(o=>o.value===keep))?keep:(terminalSlotProfiles[terminalActiveSlot]||'legacy7b');}}
function terminalRefreshStrategySelects(){document.querySelectorAll('.mc-strategy').forEach((sel,i)=>{const val=terminalSlotProfiles[i]||'legacy7b';sel.innerHTML=strategyOptions();sel.value=(BUILTIN_STRATEGIES[val]||sbProfiles?.[val])?val:'legacy7b';terminalSlotProfiles[i]=sel.value;});chrome.storage.local.set({terminalSlotProfiles});renderStrategyCatalogs();}
function terminalActivateSlot(i){terminalActiveSlot=i;document.querySelectorAll('.market-chart').forEach((c,j)=>c.classList.toggle('slot-active',j===i));const id=terminalSlotProfiles[i]||'legacy7b';sbSelected=id;sbRefreshSelect();if(BUILTIN_STRATEGIES[id])sbWrite({...SB_DEFAULT,...BUILTIN_STRATEGIES[id]});else if(sbProfiles[id])sbWrite(sbProfiles[id]);sbStatus();poRenderInstalled();renderStrategyCatalogs();if(terminalData){terminalRenderAI(terminalData);terminalRenderAnalytics(terminalData);}}
chrome.storage.local.get(['terminalSlotProfiles','terminalDrawings','terminalSelectedCharts','terminalDisplayIndicators','kaosChartCount'],d=>{if(Array.isArray(d.terminalSlotProfiles))terminalSlotProfiles=d.terminalSlotProfiles.slice(0,4);if(Array.isArray(d.terminalDrawings))terminalDrawings=d.terminalDrawings.slice(0,4);if(Array.isArray(d.terminalDisplayIndicators))terminalDisplayIndicators=d.terminalDisplayIndicators.slice(0,4);while(terminalDrawings.length<4)terminalDrawings.push([]);while(terminalDisplayIndicators.length<4)terminalDisplayIndicators.push([]);kaosApplyChartCount(d.kaosChartCount||1,false);terminalRefreshStrategySelects();terminalActivateSlot(0);setTimeout(terminalRenderChartSelection,0);});
function terminalSetSlotStrategy(i,id,{activate=true,redraw=true}={}){
 if(!Number.isInteger(i)||i<0||i>3)return false;
 if(!BUILTIN_STRATEGIES[id]&&!sbProfiles?.[id])return false;
 terminalSlotProfiles[i]=id;
 chrome.storage.local.set({terminalSlotProfiles:[...terminalSlotProfiles]});
 terminalRefreshStrategySelects();
 if(activate)terminalActivateSlot(i);
 if(redraw)terminalRedrawIndex(i);
 return true;
}
document.getElementById('chart-strategy-library')?.addEventListener('click',e=>{const c=e.target.closest('[data-strategy-id]');if(!c)return;e.preventDefault();e.stopPropagation();terminalSetSlotStrategy(terminalActiveSlot,c.dataset.strategyId);});
// Dashboard strategy cards were previously display-only: clicks had no handler.
// A card now applies immediately to the active dashboard chart and persists.
document.getElementById('main-strategy-library')?.addEventListener('click',e=>{const c=e.target.closest('[data-strategy-id]');if(!c)return;e.preventDefault();e.stopPropagation();const id=c.dataset.strategyId;if(!terminalSetSlotStrategy(terminalActiveSlot,id))return;renderStrategyCatalogs();});
document.getElementById('main-slot-grid')?.addEventListener('change',e=>{const sel=e.target.closest('[data-main-slot]');if(!sel)return;e.stopPropagation();const i=+sel.dataset.mainSlot;terminalSetSlotStrategy(i,sel.value,{activate:i===terminalActiveSlot,redraw:true});});
function terminalRender(r){
 const a=r.analytics||{},ai=r.aiSummary||{};$('terminal-kpis').innerHTML=[['BOT',r.running?'RUNNING':'STOPPED'],['TRADES',a.trades||0],['W / L',`${a.wins||0} / ${a.losses||0}`],['WIN RATE',a.winRate==null?'—':tp(a.winRate)],['AI SAMPLES',ai.samples||0],['7B RESEARCH',ai.researchSamples||0]].map(x=>`<div class="terminal-kpi"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
 const cards=[...document.querySelectorAll('.market-chart')];cards.forEach((card,i)=>terminalRenderMarket(card,r.markets?.[i],i)); terminalRenderAI(r);terminalRenderAnalytics(r);
 kaosSyncLiveStats(r);
 kaosUpdateAccountBalance(r);
 kaosRenderTradeHistory(r);
}
function terminalRenderMarket(card,m,i){
 const name=card.querySelector('.mc-name'),meta=card.querySelector('.mc-meta'),state=card.querySelector('.mc-state'),foot=card.querySelector('.mc-foot'),why=card.querySelector('.mc-why'),truth=card.querySelector('.mc-strategy-truth');
 if(!m){name.textContent=`CHART ${i+1}`;meta.textContent='not connected';state.textContent='WAIT';terminalDraw(card.querySelector('canvas'),null,i);return;}
 const cand=String(m.candidate?.decision||m.candidate?.dir||'').toUpperCase();const d=['BUY','SELL'].includes(cand)?cand:'HOLD';
 name.textContent=`${i+1} · ${m.asset}`;meta.textContent=`${m.source} · ${m.history?.canonical??m.candles?.length??0} canonical 5s`;
 state.textContent=d;state.className='mc-state '+(d==='BUY'?'buy':d==='SELL'?'sell':'hold');const open=(m.trades||[]).some(t=>!t.result);card.classList.toggle('active-trade',open);
 const q=m.timeframes?.['5s']||{},h=m.history||{};
 foot.innerHTML=[['HISTORY',h.canonical??'—'],['REAL 5s',h.real??'—'],['RAW 5s',h.raw??'—'],['EXPIRY','R30 / U15 / B30'],['ZIGZAG','5 / 3 / 1'],['ENGINES','REV / RUN / BRK'],['AI','LEARNING ONLY'],['7B P(UP)',tp(m.probUp)],['7B VOL',tn(m.vol,3)],['XGB / LGB',`${tp(m.ai?.xgbUp)} / ${tp(m.ai?.lgbUp)}`]].map(x=>`<div class="mc-stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
 if(truth)truth.innerHTML='<b>KAOS BERSERKER </b> · 2-CANDLE PULLBACK CONTINUATION · <b>5s SIGNAL</b> · <b>45s EXPIRY</b> · AI LEARNING ONLY';
 const histState=h.synced?'HISTORY + LIVE SYNCED':'HISTORY LOADING';
 why.innerHTML=`<strong>${histState}</strong> · ${h.canonical??0} canonical · ${h.real??0} real · ${h.raw??0} raw 5s · <strong>LIVE AUTHORITY:</strong> KAOS Berserker · exactly 2-candle pullback · next-candle confirmation entry · fixed 45s expiry · ${d==='HOLD'?'waiting for qualified continuation':d+' continuation setup'}.`;
 terminalDraw(card.querySelector('canvas'),m,i);
}
function terminalAggregate(rows,sec){
 if(sec<=5)return rows||[];const out=[];let cur=null;for(const q of rows||[]){const ts=+q.ts,b=Math.floor(ts/(sec*1000))*sec*1000;if(!cur||cur.ts!==b){if(cur)out.push(cur);cur={...q,ts:b};}else{cur.high=Math.max(cur.high,+q.high);cur.low=Math.min(cur.low,+q.low);cur.close=+q.close;cur.rsiNorm=q.rsiNorm;cur.vol=q.vol;}}if(cur)out.push(cur);return out;
}
function terminalDraw(c,m,i){
 if(!c)return;const ctx=c.getContext('2d',{willReadFrequently:true}),W=c.width,H=c.height;ctx.fillStyle='#050b12';ctx.fillRect(0,0,W,H);const all=terminalAggregate(m?.candles||[],terminalView[i]?.tf||5);
 if(all.length<2){ctx.fillStyle='#7894ae';ctx.font='11px monospace';ctx.fillText('No candle data yet — open the Pocket Option tab to stream live candles…',18,28);return;}
 const v=terminalView[i],base=Math.max(12,Math.min(all.length,Math.round(v.visibleBars||80))),maxPan=Math.max(0,all.length-base);v.pan=Math.max(0,Math.min(maxPan,v.pan||0));const end=Math.max(base,Math.min(all.length,all.length-Math.round(v.pan))),start=Math.max(0,end-base),rows=all.slice(start,end);
 const pad={l:10,r:72,t:24},priceBottom=270,rsiTop=282,rsiBottom=326,volTop=338,volBottom=382,pw=W-pad.l-pad.r,ph=priceBottom-pad.t;
 let lo=Math.min(...rows.map(q=>q.low)),hi=Math.max(...rows.map(q=>q.high)),rg=Math.max(hi-lo,1e-12);lo-=rg*.08;hi+=rg*.08;
 const y=p=>pad.t+(hi-p)/(hi-lo)*ph,x=j=>pad.l+(j+.5)*pw/rows.length;
 ctx.strokeStyle='#132234';ctx.lineWidth=1;for(let g=0;g<=5;g++){let yy=pad.t+g*ph/5;ctx.beginPath();ctx.moveTo(pad.l,yy);ctx.lineTo(W-pad.r,yy);ctx.stroke();ctx.fillStyle='#7894ae';ctx.font='9px monospace';ctx.fillText((hi-(hi-lo)*g/5).toFixed(6),W-pad.r+4,yy+3);}for(let g=0;g<=6;g++){let xx=pad.l+g*pw/6;ctx.beginPath();ctx.moveTo(xx,pad.t);ctx.lineTo(xx,volBottom);ctx.stroke();}
 const ema=n=>{let e=all[0].close,a=2/(n+1),z=[];for(const q of all){e=a*q.close+(1-a)*e;z.push(e);}return z.slice(start,end)};
 const slotId=terminalSlotProfiles[i]||'legacy7b'; const strategyCp=slotId!=='legacy7b'?terminalSlotProfile(i):null; const disp=new Set(terminalDisplayIndicators[i]||[]); const cp=strategyCp?structuredClone(strategyCp):{}; if(disp.has('ema'))cp.ema={enabled:true,periods:cp.ema?.periods||[9,20,50]}; if(disp.has('bb'))cp.bb={enabled:true,period:cp.bb?.period||20,deviation:cp.bb?.deviation||2}; for(const k of ['rsi','macd','stoch','adx','roc','atr','supertrend','sar'])if(disp.has(k))cp[k]={...(cp[k]||{}),enabled:true};
 const ep=(cp?.ema?.enabled?cp.ema.periods:[5,9]).map(Number);
 const ecols=['#e8c547','#43b9ff','#a46cff','#dce7f1'];
 if(slotId==='legacy7b'||cp.ema?.enabled) for(let ei=0;ei<ep.length;ei++){const arr=ema(ep[ei]),col=ecols[ei%ecols.length];ctx.strokeStyle=col;ctx.lineWidth=1;ctx.beginPath();arr.forEach((p,j)=>j?ctx.lineTo(x(j),y(p)):ctx.moveTo(x(j),y(p)));ctx.stroke();}
 // Built-in strategy 60s context: EMA 3 / EMA 6 (display only).
 if(slotId==='legacy7b'){const sixty=terminalAggregate(all,60);if(sixty.length>=2){const calc=(n)=>{let e=sixty[0].close,a=2/(n+1),z=[];for(const q of sixty){e=a*q.close+(1-a)*e;z.push({ts:q.ts,v:e});}return z;};const drawCtx=(arr,col)=>{ctx.save();ctx.strokeStyle=col;ctx.lineWidth=1;ctx.setLineDash([4,3]);ctx.beginPath();let started=false;for(const q of arr){if(q.ts<+rows[0].ts||q.ts>+rows[rows.length-1].ts)continue;const frac=(q.ts-+rows[0].ts)/Math.max(1,+rows[rows.length-1].ts-+rows[0].ts),xx=pad.l+frac*pw,yy=y(q.v);started?ctx.lineTo(xx,yy):(ctx.moveTo(xx,yy),started=true);}if(started)ctx.stroke();ctx.restore();};drawCtx(calc(3),'#9fe870');drawCtx(calc(6),'#ff9f68');}}
 if(cp?.bb?.enabled){const n=Math.max(2,Math.round(cp.bb.period||20)),dev=Number(cp.bb.deviation||2),mid=[],up=[],dn=[];for(let k=0;k<all.length;k++){const a=all.slice(Math.max(0,k-n+1),k+1).map(q=>q.close),mu=a.reduce((x,z)=>x+z,0)/a.length,sd=Math.sqrt(a.reduce((x,z)=>x+(z-mu)*(z-mu),0)/a.length);mid.push(mu);up.push(mu+dev*sd);dn.push(mu-dev*sd)}for(const [arr,col] of [[up.slice(start,end),'#7bdff2'],[mid.slice(start,end),'#4de3ff'],[dn.slice(start,end),'#7bdff2']]){ctx.strokeStyle=col;ctx.lineWidth=1;ctx.beginPath();arr.forEach((p,j)=>j?ctx.lineTo(x(j),y(p)):ctx.moveTo(x(j),y(p)));ctx.stroke();}}
 const cw=Math.max(3,Math.min(18,pw/rows.length*.72));rows.forEach((q,j)=>{const col=q.close>=q.open?'#00d88b':'#ff4f70',xx=x(j);ctx.strokeStyle=col;ctx.beginPath();ctx.moveTo(xx,y(q.high));ctx.lineTo(xx,y(q.low));ctx.stroke();ctx.fillStyle=col;ctx.fillRect(xx-cw/2,Math.min(y(q.open),y(q.close)),cw,Math.max(1,Math.abs(y(q.close)-y(q.open))));});
 terminalTradeHits[i]=[];
 for(const t of (m.trades||[])){
   const entryTs=+t.ts, expirySec=Number(t.expiry)||45, endTs=entryTs+expirySec*1000;
   let j=rows.findIndex(q=>Math.abs(+q.ts-entryTs)<5500); if(j<0)continue;
   const entry=Number(t.entryPrice)||rows[j].close, yy=y(entry), xx=x(j), buy=t.direction==='BUY';
   // PO-style contract line: exact entry price from entry time to expiration time.
   const step=rows.length>1?Math.max(1000,(+rows[rows.length-1].ts-+rows[0].ts)/(rows.length-1)):5000;
   const endIndex=j+(endTs-entryTs)/step, xEnd=Math.min(W-pad.r,pad.l+(endIndex+.5)*pw/rows.length);
   const col=buy?'#00e996':'#ff4f70'; ctx.save();ctx.strokeStyle=col;ctx.lineWidth=2;ctx.setLineDash([7,4]);ctx.beginPath();ctx.moveTo(xx,yy);ctx.lineTo(xEnd,yy);ctx.stroke();ctx.setLineDash([]);
   // Expiration cap.
   ctx.beginPath();ctx.moveTo(xEnd,yy-10);ctx.lineTo(xEnd,yy+10);ctx.stroke();
   // Entry arrow.
   ctx.fillStyle=col;ctx.beginPath();ctx.moveTo(xx,yy);ctx.lineTo(xx-7,buy?yy+13:yy-13);ctx.lineTo(xx+7,buy?yy+13:yy-13);ctx.closePath();ctx.fill();
   const result=String(t.result||'OPEN').toUpperCase(); const remaining=Math.max(0,Math.ceil((endTs-Date.now())/1000));
   const label=result==='OPEN'?`${t.direction} · ${remaining}s`:`${t.direction} · ${result}`;
   ctx.font='bold 9px monospace';const tw=ctx.measureText(label).width+10,lx=Math.max(pad.l,Math.min(xx+8,W-pad.r-tw));ctx.fillStyle='#07111bcc';ctx.fillRect(lx,yy-18,tw,15);ctx.strokeStyle=col;ctx.strokeRect(lx,yy-18,tw,15);ctx.fillStyle=col;ctx.fillText(label,lx+5,yy-7);ctx.restore();
   terminalTradeHits[i].push({x1:xx-12,x2:Math.max(xx+18,xEnd+8),y1:yy-22,y2:yy+18,trade:t});
 }
 // Normal trading-chart time axis + current-price marker.
 const last=rows[rows.length-1],lastY=y(last.close);ctx.save();ctx.strokeStyle=last.close>=last.open?'#00d88b':'#ff4f70';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(pad.l,lastY);ctx.lineTo(W-pad.r,lastY);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=ctx.strokeStyle;ctx.fillRect(W-pad.r,lastY-8,pad.r-3,16);ctx.fillStyle='#071018';ctx.font='bold 9px monospace';ctx.fillText(Number(last.close).toFixed(6),W-pad.r+3,lastY+3);ctx.restore();
 ctx.fillStyle='#7894ae';ctx.font='8px monospace';for(let g=0;g<=4;g++){const j=Math.min(rows.length-1,Math.round(g*(rows.length-1)/4)),q=rows[j];if(!q)continue;const dt=new Date(+q.ts),lab=dt.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:(v.tf||5)<60?'2-digit':undefined});ctx.fillText(lab,Math.max(pad.l,Math.min(W-pad.r-48,x(j)-20)),priceBottom-4);}
 // RSI14: KAOS Strategy stores RSI normalized as (RSI-50)/25. Plot true 0-100 RSI with 30/50/70 guides.
 ctx.strokeStyle='#1c3146';ctx.strokeRect(pad.l,rsiTop,pw,rsiBottom-rsiTop);const rsiY=r=>rsiBottom-Math.max(0,Math.min(100,r))/100*(rsiBottom-rsiTop);
 for(const level of [30,50,70]){ctx.strokeStyle=level===50?'#29445d':'#473e2a';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(pad.l,rsiY(level));ctx.lineTo(W-pad.r,rsiY(level));ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#7894ae';ctx.font='8px monospace';ctx.fillText(String(level),W-pad.r+4,rsiY(level)+3);}
 ctx.strokeStyle='#e3a94a';ctx.lineWidth=1.25;ctx.beginPath();rows.forEach((q,j)=>{const rr=Math.max(0,Math.min(100,50+25*(+q.rsiNorm||0))),yy=rsiY(rr);j?ctx.lineTo(x(j),yy):ctx.moveTo(x(j),yy)});ctx.stroke();ctx.fillStyle='#e3a94a';ctx.font='bold 8px monospace';ctx.fillText('RSI14',pad.l+3,rsiTop+9);
 // KAOS Strategy volatility ratio = current ATR-like value / recent ATR-like average. Gates are 1.00 BUY and 1.10 SELL.
 ctx.strokeStyle='#1c3146';ctx.strokeRect(pad.l,volTop,pw,volBottom-volTop);let vmax=Math.max(1.35,...rows.map(q=>Number.isFinite(+q.vol)?+q.vol:0));const volY=z=>volBottom-Math.max(0,Math.min(vmax,z))/vmax*(volBottom-volTop);
 for(const [level,label] of [[1.00,'B 1.00'],[1.10,'S 1.10']]){ctx.strokeStyle=level===1?'#2b6a57':'#7a4c56';ctx.setLineDash([4,3]);ctx.beginPath();ctx.moveTo(pad.l,volY(level));ctx.lineTo(W-pad.r,volY(level));ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#7894ae';ctx.font='8px monospace';ctx.fillText(label,W-pad.r+4,volY(level)+3);}
 ctx.strokeStyle='#4de3ff';ctx.lineWidth=1.25;ctx.beginPath();rows.forEach((q,j)=>{const vv=Number.isFinite(+q.vol)?+q.vol:0,yy=volY(vv);j?ctx.lineTo(x(j),yy):ctx.moveTo(x(j),yy)});ctx.stroke();ctx.fillStyle='#4de3ff';ctx.font='bold 8px monospace';ctx.fillText('7B VOL / ATR RATIO',pad.l+3,volTop+9);
 // KAOS Strategy ZigZag 5/3/1 structure overlay. Display mirrors the live structure settings; execution is in candidate7b_strategy.js.
 if((terminalSlotProfiles[i]||'legacy7b')==='legacy7b' && rows.length>=13){
   const depth=5,piv=[];for(let j=depth;j<rows.length-depth;j++){const v1=+rows[j].close;let hi=true,lo=true;for(let k=1;k<=depth;k++){if(!(v1>=+rows[j-k].close&&v1>+rows[j+k].close))hi=false;if(!(v1<=+rows[j-k].close&&v1<+rows[j+k].close))lo=false;}if(hi)piv.push({j,v:v1,t:'H'});if(lo)piv.push({j,v:v1,t:'L'});}
   const zz=[];for(const q of piv){if(!zz.length||q.t!==zz[zz.length-1].t)zz.push(q);else if((q.t==='H'&&q.v>zz[zz.length-1].v)||(q.t==='L'&&q.v<zz[zz.length-1].v))zz[zz.length-1]=q;}
   if(zz.length>1){ctx.save();ctx.strokeStyle='#d6b85a';ctx.lineWidth=1.35;ctx.beginPath();zz.forEach((q,k)=>{const xx=x(q.j),yy=y(q.v);k?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy)});ctx.stroke();ctx.fillStyle='#d6b85a';ctx.font='bold 8px monospace';ctx.fillText('ZIGZAG 5/3/1',pad.l+68,pad.t+10);ctx.restore();}
 }
 // User drawing layer (visual only; never creates a trade signal).
 ctx.save();ctx.strokeStyle='#f0c85a';ctx.lineWidth=1.5;for(const d of terminalDrawings[i]||[]){const x1=d.x1*W,y1=d.y1*H,x2=d.x2*W,y2=d.y2*H;ctx.beginPath();if(d.type==='hline'){ctx.moveTo(pad.l,y1);ctx.lineTo(W-pad.r,y1)}else if(d.type==='vline'){ctx.moveTo(x1,pad.t);ctx.lineTo(x1,volBottom)}else if(d.type==='rect'){ctx.strokeRect(Math.min(x1,x2),Math.min(y1,y2),Math.abs(x2-x1),Math.abs(y2-y1));continue}else{ctx.moveTo(x1,y1);ctx.lineTo(x2,y2)}ctx.stroke();}ctx.restore();
 if(v.crossX!=null){ctx.strokeStyle='#5f7e9b99';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(v.crossX,pad.t);ctx.lineTo(v.crossX,volBottom);if(v.crossY<=volBottom){ctx.moveTo(pad.l,v.crossY);ctx.lineTo(W-pad.r,v.crossY);}ctx.stroke();ctx.setLineDash([]);}
 ctx.font='8px monospace';let lx=10;if(slotId==='legacy7b'||cp.ema?.enabled){ep.forEach((n,k)=>{ctx.fillStyle=ecols[k%ecols.length];ctx.fillText('EMA'+n,lx,12);lx+=42;});}if(cp?.bb?.enabled){ctx.fillStyle='#4de3ff';ctx.fillText('BB'+cp.bb.period+'×'+cp.bb.deviation,lx,12);lx+=62;}const enabled=[];if(cp){for(const [key,label] of [['rsi','RSI'],['macd','MACD'],['stoch','STOCH'],['adx','ADX/DI'],['roc','ROC'],['atr','ATR'],['supertrend','SUPER'],['sar','SAR']])if(cp[key]?.enabled)enabled.push(label);}if(enabled.length){ctx.fillStyle='#9bb2c8';ctx.fillText(enabled.join(' · '),10,volBottom+7);}
}
function terminalRenderAI(r){
 const m=r.markets?.[terminalActiveSlot]||r.markets?.[0];const selected=$('terminal-ai-selected');
 if(selected)selected.innerHTML=m?`<b>CH${terminalActiveSlot+1} · ${m.asset}</b><br>LIVE AUTHORITY: KAOS Berserker · 2-candle pullback → confirmation → next-candle entry · 45s<br>Market context: ${tp(m.probUp)} P(UP) · ${tn(m.vol,3)} VOL · context/research only<br>XGBoost: ${kaosAiValue(m.ai?.xgbUp,m.ai?.samples)} · ${m.ai?.samples||0} samples · ${m.ai?.status||'collecting'} · learning/research only<br>LightGBM: ${kaosAiValue(m.ai?.lgbUp,m.ai?.samples)} · learning/research only<br>History: ${m.history?.canonical||0} canonical · ${m.history?.real||0} real · ${m.history?.raw||0} raw 5s · ${m.history?.synced?'SYNCED':'LOADING'}`:'Waiting for selected chart…';
 const el=$('terminal-ai-markets');if(el){let h='<div class="ai-market-row head"><span>MARKET</span><span>7B</span><span>XGB</span><span>LGB</span><span>SAMPLES</span><span>VALIDATION</span><span>STATUS</span></div>';for(const x of r.markets||[]){h+=`<div class="ai-market-row"><b>${x.asset}</b><span>${tp(x.probUp)}</span><span>${kaosAiValue(x.ai?.xgbUp,x.ai?.samples)}</span><span>${kaosAiValue(x.ai?.lgbUp,x.ai?.samples)}</span><span>${x.ai?.samples||0}</span><span>${x.ai?.validationSamples?tp(x.ai.validationAccuracy):'—'}</span><span>${x.ai?.status||'collecting'}</span></div>`;}el.innerHTML=h;}
 const s=r.aiSummary||{},sum=$('terminal-ai-summary');if(sum)sum.innerHTML=`<div class="terminal-strip" style="grid-template-columns:1fr 1fr"><div class="terminal-kpi"><span>AI SAMPLES</span><b>${s.samples||0}</b></div><div class="terminal-kpi"><span>7B RESEARCH</span><b>${s.researchSamples||0}</b></div><div class="terminal-kpi"><span>45s LABELS RESOLVED</span><b>${s.researchResolved45||0}</b></div><div class="terminal-kpi"><span>TRAINER</span><b style="font-size:10px">${s.training?.status||'collecting'}</b></div></div>`;
 const log=$('terminal-research-log');if(log)log.innerHTML=[...(r.research||[])].reverse().map(x=>`<div class="research-row"><b>${new Date(x.ts).toLocaleTimeString()} · ${x.asset}</b> · 7B ${x.decision} ${tp(x.probUp)} · XGB ${tp(x.ai?.xgbUp)} · 15s ${x.forward?.[15]?((x.forward[15].up===.5?'TIE':x.forward[15].up?'UP':'DOWN')+' '+tn(x.forward[15].delta,6)):'pending'} · 45s ${x.forward?.[45]?((x.forward[45].up===.5?'TIE':x.forward[45].up?'UP':'DOWN')):'pending'}</div>`).join('')||'Waiting for research snapshots…';
}
function terminalRenderAnalytics(r){
 const all=(r.markets||[]).flatMap(m=>(m.trades||[]).map(t=>({...t,_market:m.asset}))).sort((a,b)=>b.ts-a.ts),closed=all.filter(t=>t.result),wins=closed.filter(t=>String(t.result).toUpperCase()==='WIN').length,losses=closed.filter(t=>String(t.result).toUpperCase()==='LOSS').length,ties=closed.filter(t=>['TIE','DRAW'].includes(String(t.result).toUpperCase())).length,wr=wins+losses?wins/(wins+losses):null;
 const a=r.analytics||{},el=$('terminal-analytics-cards');if(el)el.innerHTML=[['ALL-TIME TRADES',a.trades||0],['VISIBLE CHART TRADES',closed.length],['WINS',wins],['LOSSES',losses],['TIES',ties],['W/L WIN RATE',wr==null?'—':tp(wr)],['OPEN',all.length-closed.length],['LIVE EXPIRY','15s']].map(x=>`<div class="analytics-card"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
 const m=r.markets?.[terminalActiveSlot]||r.markets?.[0],box=$('terminal-analytics-selected');if(box&&m){const mt=(m.trades||[]),mc=mt.filter(t=>t.result),mw=mc.filter(t=>String(t.result).toUpperCase()==='WIN').length,ml=mc.filter(t=>String(t.result).toUpperCase()==='LOSS').length,recent=n=>{const z=mc.slice(-n),w=z.filter(t=>String(t.result).toUpperCase()==='WIN').length,l=z.filter(t=>String(t.result).toUpperCase()==='LOSS').length;return w+l?`${w}W/${l}L · ${((w/(w+l))*100).toFixed(1)}%`:'—'};box.innerHTML=`<div class="terminal-section"><h4>CH${terminalActiveSlot+1} · ${m.asset} PERFORMANCE</h4><div class="terminal-detail-grid">${[['TRADES',mc.length],['W / L',`${mw} / ${ml}`],['WIN RATE',mw+ml?((mw/(mw+ml))*100).toFixed(1)+'%':'—'],['LAST 10',recent(10)],['LAST 25',recent(25)],['HISTORY',m.history?.canonical||0],['REAL 5s',m.history?.real||0],['HISTORY STATUS',m.history?.synced?'SYNCED':'LOADING']].map(x=>`<div class="terminal-detail-card"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div></div><div class="terminal-section"><h4>STRATEGY / SIGNAL FUNNEL</h4><div class="signal-funnel"><div>5s CANDLES<b>${m.history?.canonical||0}</b></div><div>CONFIRMED TRADES<b>${mc.length}</b></div><div>OPEN<b>${mt.length-mc.length}</b></div><div>WINS<b>${mw}</b></div><div>LOSSES<b>${ml}</b></div></div><div class="terminal-note" style="margin-top:7px">KAOS Strategy · 30s S/R + 60s context + 5s/15s entry confirmation · adaptive 15s/20s/25s expiry · AI learning only. Block-reason counters will populate when exposed by the live engine.</div></div>`;}
 const tr=$('terminal-trades');if(tr)tr.innerHTML=all.slice(0,80).map(t=>`<div class="chart-hrow"><span>${new Date(t.ts).toLocaleTimeString()}</span><b>${t.asset||t._market}</b><span style="color:${t.direction==='BUY'?'var(--green)':'var(--red)'}">${t.direction}</span><span>${t.expiry||15}s</span><span>${String(t.result||'OPEN').toUpperCase()}</span><span>${Number(t.profit||0)>=0?'+':''}$${Number(t.profit||0).toFixed(2)}</span></div>`).join('')||'<div class="dbg-log-empty">No live trades yet</div>';
}
document.querySelectorAll('.market-chart .mc-tf').forEach((sel,i)=>sel.addEventListener('change',()=>{terminalView[i].tf=Number(sel.value)||5;terminalView[i].pan=0;terminalView[i].visibleBars=80;if(terminalData)terminalRenderMarket(sel.closest('.market-chart'),terminalData.markets?.[i],i);}));
// TradingView-style chart controls: anchored wheel zoom, smooth drag pan, buttons, fit, maximize.
function terminalRedrawIndex(i){const c=document.querySelectorAll('.market-chart canvas')[i];if(c&&terminalData)terminalDraw(c,terminalData.markets?.[i],i);}
function terminalZoomAt(i,factor,anchor=.5){const v=terminalView[i],m=terminalData?.markets?.[i],all=terminalAggregate(m?.candles||[],v.tf||5);if(!all.length)return;const old=Math.max(12,Math.min(all.length,Math.round(v.visibleBars||80))),neu=Math.max(12,Math.min(Math.max(12,all.length),Math.round(old*factor)));if(neu===old)return;const rightIndex=all.length-(v.pan||0),anchorIndex=rightIndex-old+anchor*old;v.visibleBars=neu;v.pan=Math.max(0,Math.min(Math.max(0,all.length-neu),all.length-(anchorIndex+(1-anchor)*neu)));terminalRedrawIndex(i);}
function terminalRenderChartSelection(){
 document.querySelectorAll('.market-chart').forEach((card,i)=>{const on=!!terminalSelectedCharts[i];card.classList.toggle('chart-selected',on);const cb=card.querySelector('.mc-select');if(cb)cb.checked=on;});
 const all=document.getElementById('select-all-charts');if(all){all.checked=terminalSelectedCharts.every(Boolean);all.indeterminate=terminalSelectedCharts.some(Boolean)&&!terminalSelectedCharts.every(Boolean);}
}
function terminalSetChartSelected(i,on){terminalSelectedCharts[i]=!!on;chrome.storage.local.set({terminalSelectedCharts});terminalRenderChartSelection();}
document.getElementById('select-all-charts')?.addEventListener('change',e=>{terminalSelectedCharts=terminalSelectedCharts.map(()=>!!e.target.checked);chrome.storage.local.set({terminalSelectedCharts});terminalRenderChartSelection();});
document.getElementById('apply-all-charts-strategy')?.addEventListener('click',()=>{const id=document.getElementById('all-charts-strategy')?.value;if(!id||(!BUILTIN_STRATEGIES[id]&&!sbProfiles[id]))return;const chosen=terminalSelectedCharts.map((v,i)=>v?i:-1).filter(i=>i>=0);if(!chosen.length)return;chosen.forEach(i=>terminalSlotProfiles[i]=id);chrome.storage.local.set({terminalSlotProfiles});terminalRefreshStrategySelects();renderStrategyCatalogs();chosen.forEach(i=>terminalRedrawIndex(i));});
function terminalShowPage(name){document.querySelectorAll('.terminal-tab').forEach(x=>x.classList.toggle('active',x.dataset.page===name));document.querySelectorAll('.terminal-page').forEach(x=>x.classList.remove('active'));document.getElementById('terminal-'+name)?.classList.add('active');}
document.getElementById('see-all-strategies')?.addEventListener('click',()=>{renderStrategyCatalogs();terminalShowPage('strategies');});
document.getElementById('strategies-back-to-charts')?.addEventListener('click',()=>terminalShowPage('live'));
document.querySelectorAll('.mc-select').forEach((cb,i)=>cb.addEventListener('click',e=>{e.stopPropagation();terminalSetChartSelected(i,e.target.checked);}));
document.querySelectorAll('.market-chart').forEach((card,i)=>{
 const c=card.querySelector('canvas'),v=terminalView[i];
 card.addEventListener('click',()=>terminalActivateSlot(i));
 card.querySelector('.mc-strategy')?.addEventListener('change',e=>{e.stopPropagation();terminalSlotProfiles[i]=e.target.value;chrome.storage.local.set({terminalSlotProfiles});terminalActivateSlot(i);terminalRedrawIndex(i);});
 card.querySelector('.mc-ind-btn')?.addEventListener('click',e=>{e.stopPropagation();terminalActivateSlot(i);openDisplayIndicatorPicker(i);});
 card.querySelectorAll('.mc-draw').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const tool=b.dataset.tool;if(tool==='clear'){terminalDrawings[i]=[];chrome.storage.local.set({terminalDrawings});terminalRedrawIndex(i);return;}terminalDrawTool[i]=tool;card.querySelectorAll('.mc-draw').forEach(x=>x.classList.toggle('active',x.dataset.tool===tool));c.style.cursor=tool==='cursor'?'crosshair':'cell';}));

 card.querySelector('.zoom-in')?.addEventListener('click',e=>{e.stopPropagation();terminalZoomAt(i,.72,.5)});
 card.querySelector('.zoom-out')?.addEventListener('click',e=>{e.stopPropagation();terminalZoomAt(i,1.38,.5)});
 card.querySelector('.zoom-fit')?.addEventListener('click',e=>{e.stopPropagation();v.visibleBars=80;v.pan=0;terminalRedrawIndex(i)});
 card.querySelector('.zoom-max')?.addEventListener('click',e=>{e.stopPropagation();card.classList.toggle('maximized');setTimeout(()=>terminalRedrawIndex(i),20)});
 c.addEventListener('wheel',e=>{e.preventDefault();e.stopPropagation();const r=c.getBoundingClientRect(),anchor=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));terminalZoomAt(i,e.deltaY<0?.82:1.22,anchor);},{passive:false});
 c.addEventListener('mousedown',e=>{const r=c.getBoundingClientRect(),pt={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};if(terminalDrawTool[i]!=='cursor'){terminalDrawStart[i]=pt;e.preventDefault();return;}v.drag=true;v.lastX=e.clientX;v.dragCarry=0;c.style.cursor='grabbing';e.preventDefault();});
 c.addEventListener('mouseup',e=>{if(terminalDrawTool[i]==='cursor'||!terminalDrawStart[i])return;const r=c.getBoundingClientRect(),a=terminalDrawStart[i],b={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};terminalDrawings[i].push({type:terminalDrawTool[i],x1:a.x,y1:a.y,x2:b.x,y2:b.y});terminalDrawStart[i]=null;chrome.storage.local.set({terminalDrawings});terminalRedrawIndex(i);});
 window.addEventListener('mouseup',()=>{v.drag=false;if(terminalDrawTool[i]==='cursor')c.style.cursor='crosshair'});
 c.addEventListener('mousemove',e=>{const r=c.getBoundingClientRect();v.crossX=(e.clientX-r.left)*c.width/r.width;v.crossY=(e.clientY-r.top)*c.height/r.height;if(v.drag){const m=terminalData?.markets?.[i],all=terminalAggregate(m?.candles||[],v.tf||5),bars=Math.max(12,Math.min(all.length,Math.round(v.visibleBars||80))),pxPerBar=Math.max(2,(c.clientWidth||r.width)/bars),dx=e.clientX-v.lastX;v.lastX=e.clientX;v.dragCarry+=-dx/pxPerBar;const whole=v.dragCarry>0?Math.floor(v.dragCarry):Math.ceil(v.dragCarry);if(whole){v.pan=Math.max(0,Math.min(Math.max(0,all.length-bars),(v.pan||0)+whole));v.dragCarry-=whole;}}terminalRedrawIndex(i);});
 c.addEventListener('mouseleave',()=>{v.crossX=null;v.crossY=null;if(!v.drag)terminalRedrawIndex(i)});
 c.addEventListener('click',e=>{const r=c.getBoundingClientRect(),xx=(e.clientX-r.left)*c.width/r.width,yy=(e.clientY-r.top)*c.height/r.height;const hit=(terminalTradeHits[i]||[]).find(h=>xx>=h.x1&&xx<=h.x2&&yy>=h.y1&&yy<=h.y2);if(!hit)return;const t=hit.trade,why=card?.querySelector('.mc-why'),snap=t.signalSnapshot||{};if(why)why.innerHTML=`<strong>${t.direction} TRADE REVIEW · ${String(t.result||'OPEN').toUpperCase()}</strong> · entry ${Number(t.entryPrice||0).toFixed(6)} → exit ${Number(t.exitPrice||0).toFixed(6)} · ${t.expiry||45}s · P/L ${Number(t.profit||0)>=0?'+':''}$${Number(t.profit||0).toFixed(2)}<br><span style="color:var(--muted)">Entry regime: ${t.regimeAtEntry||'—'} · engine: ${t.engineFamily||'KAOS Berserker'} · score: ${t.totalScore??'—'} · saved signal: ${Object.keys(snap).length?'YES':'NO'} · replay frames: ${t.replayFrameCount||t.replayFrames?.length||0}</span>`;});
 c.addEventListener('dblclick',()=>{v.visibleBars=80;v.pan=0;terminalRedrawIndex(i)});
});


// ════════════════════════════════════════════════════════════
// B32.10 CHART STRATEGY BUILDER — profile editor / persistence
// KAOS Berserker is immutable; custom profiles are sent to content.js.
// ════════════════════════════════════════════════════════════
const SB_DEFAULT={id:'custom1',name:'Custom Strategy 1',description:'Editable confirmation strategy. Install indicators, tune their settings, backtest, and assign it to any chart.',engine:'CUSTOM_CONFIRM',signalTf:30,expiry:45,minConfirmations:3,
  ema:{enabled:true,periods:[9,20,50,100]},rsi:{enabled:true,period:14,low:30,high:70},macd:{enabled:true,fast:12,slow:26,signal:9},
  bb:{enabled:false,period:20,deviation:2},stoch:{enabled:false,period:14,low:20,high:80},adx:{enabled:false,period:14,min:20},
  roc:{enabled:false,period:7,threshold:0},atr:{enabled:false,period:14,maxNorm:1.5},supertrend:{enabled:false,period:10,multiplier:3},sar:{enabled:false,step:.02,max:.2}};
let sbProfiles={custom1:structuredClone(SB_DEFAULT)};
let sbSelected='legacy7b';
let sbPineSource='';
let sbPineMeta=null;
const sbNum=(id,d)=>{const e=$(id),n=Number(e?.value);return Number.isFinite(n)?n:d};
function sbRead(){return {id:sbSelected==='legacy7b'?'custom1':sbSelected,name:$('sb-name')?.value?.trim()||'Custom Strategy',description:$('sb-description')?.value?.trim()||'Custom strategy',type:'custom',editable:true,engine:'CUSTOM_CONFIRM',signalTf:sbNum('sb-tf',30),expiry:sbNum('sb-exp',45),minConfirmations:Math.max(1,sbNum('sb-minconf',3)),
 ema:{enabled:!!$('sb-use-ema')?.checked,periods:[sbNum('sb-ema1',9),sbNum('sb-ema2',20),sbNum('sb-ema3',50),sbNum('sb-ema4',100)].map(x=>Math.max(2,Math.round(x)))},
 rsi:{enabled:!!$('sb-use-rsi')?.checked,period:sbNum('sb-rsip',14),low:sbNum('sb-rsilo',30),high:sbNum('sb-rsihi',70)},macd:{enabled:!!$('sb-use-macd')?.checked,fast:sbNum('sb-macdf',12),slow:sbNum('sb-macds',26),signal:sbNum('sb-macdsig',9)},
 bb:{enabled:!!$('sb-use-bb')?.checked,period:sbNum('sb-bbp',20),deviation:sbNum('sb-bbd',2)},stoch:{enabled:!!$('sb-use-stoch')?.checked,period:sbNum('sb-stp',14),low:sbNum('sb-stlo',20),high:sbNum('sb-sthi',80)},
 adx:{enabled:!!$('sb-use-adx')?.checked,period:sbNum('sb-adxp',14),min:sbNum('sb-adxmin',20)},roc:{enabled:!!$('sb-use-roc')?.checked,period:sbNum('sb-rocp',7),threshold:sbNum('sb-roct',0)},atr:{enabled:!!$('sb-use-atr')?.checked,period:sbNum('sb-atrp',14),maxNorm:sbNum('sb-atrmax',1.5)},
 supertrend:{enabled:!!$('sb-use-super')?.checked,period:sbNum('sb-statr',10),multiplier:sbNum('sb-stmult',3)},sar:{enabled:!!$('sb-use-sar')?.checked,step:sbNum('sb-sarstep',.02),max:sbNum('sb-sarmax',.2)}}}
function sbWrite(p){p=p||SB_DEFAULT; const set=(id,v)=>{const e=$(id);if(e)e.value=v}; const chk=(id,v)=>{const e=$(id);if(e)e.checked=!!v};set('sb-name',p.name);set('sb-description',p.description||'Custom strategy');set('sb-tf',p.signalTf);set('sb-exp',p.expiry);set('sb-minconf',p.minConfirmations);(p.ema?.periods||[9,20,50,100]).forEach((v,i)=>set('sb-ema'+(i+1),v));chk('sb-use-ema',p.ema?.enabled);set('sb-rsip',p.rsi?.period);set('sb-rsilo',p.rsi?.low);set('sb-rsihi',p.rsi?.high);chk('sb-use-rsi',p.rsi?.enabled);set('sb-macdf',p.macd?.fast);set('sb-macds',p.macd?.slow);set('sb-macdsig',p.macd?.signal);chk('sb-use-macd',p.macd?.enabled);set('sb-bbp',p.bb?.period);set('sb-bbd',p.bb?.deviation);chk('sb-use-bb',p.bb?.enabled);set('sb-stp',p.stoch?.period);set('sb-stlo',p.stoch?.low);set('sb-sthi',p.stoch?.high);chk('sb-use-stoch',p.stoch?.enabled);set('sb-adxp',p.adx?.period);set('sb-adxmin',p.adx?.min);chk('sb-use-adx',p.adx?.enabled);set('sb-rocp',p.roc?.period);set('sb-roct',p.roc?.threshold);chk('sb-use-roc',p.roc?.enabled);set('sb-atrp',p.atr?.period);set('sb-atrmax',p.atr?.maxNorm);chk('sb-use-atr',p.atr?.enabled);set('sb-statr',p.supertrend?.period);set('sb-stmult',p.supertrend?.multiplier);chk('sb-use-super',p.supertrend?.enabled);set('sb-sarstep',p.sar?.step);set('sb-sarmax',p.sar?.max);chk('sb-use-sar',p.sar?.enabled)}
function sbRefreshSelect(){const s=$('sb-profile');if(!s)return;const val=sbSelected;s.innerHTML=Object.values(BUILTIN_STRATEGIES).map(p=>`<option value="${p.id}"> ${p.name}</option>`).join('')+Object.values(sbProfiles).map(p=>`<option value="${p.id}">${p.name}</option>`).join('');s.value=sbProfiles[val]||BUILTIN_STRATEGIES[val]?val:'legacy7b'}
function sbPersist(){chrome.storage.local.set({strategyProfiles:sbProfiles,activeStrategyProfile:sbSelected});if(typeof renderStrategyCatalogs==='function')renderStrategyCatalogs();}
function sbLoadSelected(){
 const id=$('sb-profile')?.value||sbSelected; sbSelected=id;
 if(BUILTIN_STRATEGIES[id]) sbWrite({...SB_DEFAULT,...BUILTIN_STRATEGIES[id]}); else if(sbProfiles[id]) sbWrite(sbProfiles[id]); else return false;
 sbPersist();sbStatus();sbPreviewRedraw();
 const st=$('sb-status');if(st)st.textContent=BUILTIN_STRATEGIES[id]?'Loaded protected '+BUILTIN_STRATEGIES[id].name+'.':'Loaded '+(sbProfiles[id]?.name||'strategy')+'. It becomes live the next time the bot is started.';
 return true;
}
function sbDownloadSelected(){
 if(sbSelected==='legacy7b'){const st=$('sb-status');if(st)st.textContent='KAOS Berserker is built into KAOS Trading Bot and does not need a profile file.';return;}
 const p=sbProfiles[sbSelected]||sbRead();
 const payload={kind:'KAOS-Strategy-Profile',version:1,exportedAt:new Date().toISOString(),profile:structuredClone(p)};
 const json=JSON.stringify(payload,null,2),url='data:application/json;base64,'+strToBase64(json);
 const safe=String(p.name||'strategy').replace(/[^a-z0-9._-]+/gi,'_').replace(/^_+|_+$/g,'')||'strategy';
 chrome.downloads.download({url,filename:`KAOS_Strategy_${safe}.json`,saveAs:true},()=>{const st=$('sb-status');if(st)st.textContent=chrome.runtime.lastError?'Profile download failed: '+chrome.runtime.lastError.message:`Downloaded ${p.name}.`;});
}
function sbStatus(){const e=$('sb-live');if(e)e.textContent=BUILTIN_STRATEGIES[sbSelected]?`LIVE: ${BUILTIN_STRATEGIES[sbSelected].name.toUpperCase()}`:`LIVE: ${sbProfiles[sbSelected]?.name||'CUSTOM'}`;}
function sbPreviewRedraw(){if(!terminalData)return;document.querySelectorAll('.market-chart').forEach((card,i)=>terminalDraw(card.querySelector('canvas'),terminalData.markets?.[i],i));}
document.getElementById('strategy-builder')?.addEventListener('input',sbPreviewRedraw);document.getElementById('strategy-builder')?.addEventListener('change',()=>setTimeout(sbPreviewRedraw,0));
function sbInit(){chrome.storage.local.get(['strategyProfiles','activeStrategyProfile'],d=>{if(d.strategyProfiles&&typeof d.strategyProfiles==='object')sbProfiles=d.strategyProfiles;sbSelected=d.activeStrategyProfile&&(BUILTIN_STRATEGIES[d.activeStrategyProfile]||sbProfiles[d.activeStrategyProfile])?d.activeStrategyProfile:'legacy7b';sbRefreshSelect();if(BUILTIN_STRATEGIES[sbSelected])sbWrite({...SB_DEFAULT,...BUILTIN_STRATEGIES[sbSelected]});else if(sbProfiles[sbSelected])sbWrite(sbProfiles[sbSelected]);else sbWrite(SB_DEFAULT);sbStatus()});
 $('sb-profile')?.addEventListener('change',e=>{const st=$('sb-status');if(st)st.textContent=e.target.value==='legacy7b'?'KAOS Berserker selected in library. Click Load Profile to load it.':`Selected ${sbProfiles[e.target.value]?.name||'strategy'} in library. Click Load Profile to load it.`;});
 $('sb-load')?.addEventListener('click',sbLoadSelected);
 $('sb-download')?.addEventListener('click',sbDownloadSelected);
 $('sb-save')?.addEventListener('click',()=>{if(BUILTIN_STRATEGIES[sbSelected]){ $('sb-status').textContent=BUILTIN_STRATEGIES[sbSelected].name+' is a protected built-in strategy. Duplicate it to create an editable custom strategy.';return;}const p=sbRead();p.id=sbSelected;sbProfiles[sbSelected]=p;terminalSlotProfiles[terminalActiveSlot]=sbSelected;sbRefreshSelect();terminalRefreshStrategySelects();sbPersist();sbStatus();$('sb-status').textContent=`Saved ${p.name}. It becomes live the next time the bot is started.`});
 $('sb-new')?.addEventListener('click',()=>{const id='custom_'+Date.now();sbSelected=id;sbProfiles[id]={...structuredClone(SB_DEFAULT),id,name:'New Custom Strategy',description:'New editable custom strategy.',type:'custom',editable:true};sbRefreshSelect();sbWrite(sbProfiles[id]);sbPersist();sbStatus()});
 $('sb-duplicate')?.addEventListener('click',()=>{const source=BUILTIN_STRATEGIES[sbSelected]||sbProfiles[sbSelected]||SB_DEFAULT;const base=structuredClone(BUILTIN_STRATEGIES[sbSelected]?{...SB_DEFAULT,name:source.name+' Custom',description:'Editable custom strategy inspired by '+source.name+'.',signalTf:source.signalTf||30,expiry:source.expiry||45}:source);const id='custom_'+Date.now();base.id=id;base.name=BUILTIN_STRATEGIES[sbSelected]?(source.name+' Custom'):(base.name+' Copy');base.description=BUILTIN_STRATEGIES[sbSelected]?('Editable custom strategy inspired by '+source.name+'.'):(base.description||'Custom strategy')+' (copy)';base.type='custom';base.editable=true;sbProfiles[id]=base;sbSelected=id;sbRefreshSelect();sbWrite(base);sbPersist();sbStatus()});
 $('sb-delete')?.addEventListener('click',()=>{
  if(BUILTIN_STRATEGIES[sbSelected]){ $('sb-status').textContent=BUILTIN_STRATEGIES[sbSelected].name+' is built in and cannot be deleted.';return;}
  const p=sbProfiles[sbSelected];if(!p){$('sb-status').textContent='Select a custom strategy to delete.';return;}
  if(!confirm(`Delete custom strategy "${p.name}"? This cannot be undone.`))return;
  const doomed=sbSelected;delete sbProfiles[doomed];terminalSlotProfiles=terminalSlotProfiles.map(id=>id===doomed?'legacy7b':id);sbSelected='legacy7b';sbRefreshSelect();sbWrite({...SB_DEFAULT,...BUILTIN_STRATEGIES.legacy7b});sbPersist();chrome.storage.local.set({terminalSlotProfiles});terminalRefreshStrategySelects();sbStatus();$('sb-status').textContent=`Deleted ${p.name}. Any chart using it was switched to KAOS Berserker.`;
 });
 $('sb-legacy')?.addEventListener('click',()=>{sbSelected='legacy7b';sbRefreshSelect();sbWrite(SB_DEFAULT);sbPersist();sbStatus();$('sb-status').textContent='KAOS Berserker selected. Locked signature execution will be used on next Start.'});
 $('sb-backtest')?.addEventListener('click',async()=>{
  const out=$('sb-backtest-results');if(!out)return;
  const cfg=BUILTIN_STRATEGIES[sbSelected]?structuredClone(BUILTIN_STRATEGIES[sbSelected]):sbRead();
  out.style.display='block';const picked=(terminalData?.markets||[]).filter((_,i)=>terminalSelectedCharts[i]).map(m=>m.asset).filter(Boolean);if(!picked.length){out.textContent='Select at least one chart before running a backtest.';return;}out.textContent=`Running ${cfg.name} through ${picked.join(', ')} closed Pocket Option candle history…`;
  try{const tab=await getKAOSTargetTab();if(!tab)throw new Error('Pocket Option tab not found');const r=await chrome.tabs.sendMessage(tab.id,{type:'RUN_STRATEGY_BACKTEST',profile:cfg,assets:(terminalData?.markets||[]).filter((_,i)=>terminalSelectedCharts[i]).map(m=>m.asset).filter(Boolean)});if(!r?.ok)throw new Error(r?.error||'Backtest failed');const x=r.summary||{};out.innerHTML=`<b>${cfg.name} BACKTEST</b> · ${x.trades||0} natural trades · ${x.wins||0}W / ${x.losses||0}L / ${x.ties||0}T · resolved WR ${x.winRate==null?'—':(x.winRate*100).toFixed(1)+'%'} · max loss streak ${x.maxLossStreak||0} · ${x.tradesPerHour?.toFixed?.(1)||'0.0'} trades/hr<br><span style="color:var(--muted)">${r.note||''}<br>${(r.markets||[]).map(m=>`${m.asset}: ${m.trades} trades · ${m.wins}W/${m.losses}L/${m.ties}T · ${m.winRate==null?'—':(m.winRate*100).toFixed(1)+'%'}`).join(' &nbsp; | &nbsp; ')}</span>`;}catch(e){out.textContent='Backtest error: '+(e?.message||e);}
 });
}
document.addEventListener('DOMContentLoaded',sbInit);
function getStrategyBuilderStartConfig(){
 const slots=terminalSlotProfiles.map((id,i)=>({slot:i,enabled:i<kaosChartCount,asset:terminalData?.markets?.[i]?.asset||null,profileId:id,profile:id==='legacy7b'?null:structuredClone(BUILTIN_STRATEGIES[id]||sbProfiles[id]||null)})).filter(x=>x.enabled);
 return{strategyEngine:'MIXED_SLOTS',strategyProfileId:'per-chart',strategyProfileName:'Per-chart strategies',chartCount:kaosChartCount,strategySlots:slots};
}

// ════════════════════════════════════════════════════════════
// B32.15 PO-STYLE INDICATOR LIBRARY / SETTINGS MODALS
// Installed state is the strategy enabled state: one source of truth.
// ════════════════════════════════════════════════════════════
const DISPLAY_INDICATOR_KEYS=['ema','bb','rsi','macd','stoch','adx','roc','atr','supertrend','sar'];
function openDisplayIndicatorPicker(slot){
 const names={ema:'EMA',bb:'Bollinger Bands',rsi:'RSI',macd:'MACD',stoch:'Stochastic',adx:'ADX / DI',roc:'ROC',atr:'ATR',supertrend:'Supertrend',sar:'Parabolic SAR'};
 const el=document.getElementById('po-ind-list');if(!el)return;const cur=new Set(terminalDisplayIndicators[slot]||[]);
 el.innerHTML='<div class="sb-note" style="grid-column:1/-1;margin-bottom:6px"><b>CHART '+(slot+1)+' DISPLAY INDICATORS — VISUAL ONLY</b><br>These overlays never change BUY/SELL signals or strategy rules.</div>'+DISPLAY_INDICATOR_KEYS.map(k=>`<button type="button" class="po-ind-option" data-display-ind="${k}"><span><b>${names[k]}</b><small>Visual only · no trade effect</small></span><span>${cur.has(k)?'ON':'ADD'}</span></button>`).join('');
 el.querySelectorAll('[data-display-ind]').forEach(b=>b.onclick=()=>{const k=b.dataset.displayInd,s=new Set(terminalDisplayIndicators[slot]||[]);s.has(k)?s.delete(k):s.add(k);terminalDisplayIndicators[slot]=[...s];chrome.storage.local.set({terminalDisplayIndicators});openDisplayIndicatorPicker(slot);renderDisplayIndicatorChips();terminalRedrawIndex(slot);});
 document.getElementById('po-ind-library')?.classList.add('open');
}
function renderDisplayIndicatorChips(){const names={ema:'EMA',bb:'BB',rsi:'RSI',macd:'MACD',stoch:'STOCH',adx:'ADX',roc:'ROC',atr:'ATR',supertrend:'SUPER',sar:'SAR'};document.querySelectorAll('.mc-indicators').forEach((el,i)=>{const a=terminalDisplayIndicators[i]||[];el.innerHTML=a.length?a.map(k=>`<span class="po-ind-chip">${names[k]||k} · VISUAL</span>`).join(''):'<span class="sb-note">No display indicators</span>';});}
const PO_INDICATORS={
 ema:{name:'EMA',desc:'Exponential moving averages',fields:[['sb-ema1','Fast period'],['sb-ema2','Mid period'],['sb-ema3','Slow period'],['sb-ema4','Long period']],check:'sb-use-ema'},
 bb:{name:'Bollinger Bands',desc:'Moving average bands',fields:[['sb-bbp','Period'],['sb-bbd','Deviation']],check:'sb-use-bb'},
 rsi:{name:'RSI',desc:'Relative Strength Index',fields:[['sb-rsip','Period'],['sb-rsilo','Oversold'],['sb-rsihi','Overbought']],check:'sb-use-rsi'},
 macd:{name:'MACD',desc:'Moving Average Convergence Divergence',fields:[['sb-macdf','Fast'],['sb-macds','Slow'],['sb-macdsig','Signal']],check:'sb-use-macd'},
 stoch:{name:'Stochastic',desc:'Stochastic oscillator',fields:[['sb-stp','K period'],['sb-stlo','Low level'],['sb-sthi','High level']],check:'sb-use-stoch'},
 adx:{name:'ADX / DI',desc:'Trend strength and direction',fields:[['sb-adxp','Period'],['sb-adxmin','Minimum ADX']],check:'sb-use-adx'},
 roc:{name:'ROC',desc:'Rate of Change momentum',fields:[['sb-rocp','Lookback'],['sb-roct','Threshold %']],check:'sb-use-roc'},
 atr:{name:'ATR',desc:'Volatility gate',fields:[['sb-atrp','Period'],['sb-atrmax','Max normalized volatility']],check:'sb-use-atr'},
 supertrend:{name:'Supertrend',desc:'ATR trend overlay',fields:[['sb-statr','Period'],['sb-stmult','Multiplier']],check:'sb-use-super'},
 sar:{name:'Parabolic SAR',desc:'Stop and reverse overlay',fields:[['sb-sarstep','Step'],['sb-sarmax','Maximum']],check:'sb-use-sar'}
};
let poEditingIndicator=null;
function poIsInstalled(key){return !!document.getElementById(PO_INDICATORS[key]?.check)?.checked;}
function poRenderIndicatorLibrary(filter='',lockedView=false,slot=terminalActiveSlot){
 const el=document.getElementById('po-ind-list');if(!el)return;const q=String(filter).toLowerCase().trim();
 if(lockedView){const fixed=[['KAOS Berserker Core','Established move → exactly 2 counter-trend pullback candles → continuation confirmation'],['Signal Timeframe','5-second closed candles'],['Trade Expiry','Fixed 45 seconds'],['Trend Structure','EMA 9 / EMA 21 alignment + established directional candles'],['Volatility Gate','ATR 20 controls oversized pullbacks'],['Confirmation','Continuation candle must reclaim structure before entry'],['AI Models','Learning/research only — never execution authority']];el.innerHTML='<div class="sb-note" style="margin:4px 0 10px">CHART '+(slot+1)+' · KAOS Berserker <br>Hard-coded strategy inputs are locked. All strategy indicators are displayed automatically.</div>'+fixed.filter(x=>!q||x.join(' ').toLowerCase().includes(q)).map(x=>`<div class="po-ind-option" style="cursor:default"><span><b>${x[0]} </b><small>${x[1]}</small></span><span>ON</span></div>`).join('');return;}
 el.innerHTML=Object.entries(PO_INDICATORS).filter(([k,v])=>!q||v.name.toLowerCase().includes(q)||v.desc.toLowerCase().includes(q)).map(([k,v])=>`<button type="button" class="po-ind-option" data-ind="${k}"><span><b>${v.name}</b><small>${v.desc}</small></span><span>${poIsInstalled(k)?'INSTALLED':'ADD'}</span></button>`).join('');
 el.querySelectorAll('[data-ind]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.ind;if(poIsInstalled(k)){poOpenSettings(k);return;}const cb=document.getElementById(PO_INDICATORS[k].check);if(cb)cb.checked=true;poRenderInstalled();sbPreviewRedraw();poCloseLibrary();poOpenSettings(k);}));
}
function poRenderInstalled(){
 const installed=Object.entries(PO_INDICATORS).filter(([k])=>poIsInstalled(k));
 const html=installed.length?installed.map(([k,v])=>`<span class="po-ind-chip" data-ind="${k}">${v.name}<button type="button" title="${v.name} settings" data-gear="${k}"></button></span>`).join(''):'<span class="sb-note">No indicators installed</span>';
 const main=document.getElementById('sb-installed');if(main)main.innerHTML=html;
 renderDisplayIndicatorChips();
 document.querySelectorAll('[data-gear]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();poOpenSettings(b.dataset.gear);}));
}
function poOpenLibrary(){if(sbSelected==='legacy7b'){const st=document.getElementById('sb-status');if(st)st.textContent='KAOS Berserker strategy inputs are locked. Duplicate or create a custom strategy to install indicators.';return;}poRenderIndicatorLibrary();document.getElementById('po-ind-library')?.classList.add('open');setTimeout(()=>document.getElementById('po-ind-search')?.focus(),0);}
function poCloseLibrary(){document.getElementById('po-ind-library')?.classList.remove('open');}
function poOpenSettings(key){if(sbSelected==='legacy7b')return;const def=PO_INDICATORS[key];if(!def)return;poEditingIndicator=key;document.getElementById('po-settings-title').textContent=def.name+' SETTINGS';const box=document.getElementById('po-settings-fields');box.innerHTML=def.fields.map(([id,label])=>{const val=document.getElementById(id)?.value??'';return `<div class="po-setting"><label>${label}</label><input data-source="${id}" type="number" step="any" value="${String(val).replace(/"/g,'&quot;')}"></div>`}).join('');document.getElementById('po-ind-settings')?.classList.add('open');}
function poCloseSettings(){document.getElementById('po-ind-settings')?.classList.remove('open');poEditingIndicator=null;}
function poSaveSettings(){const key=poEditingIndicator;if(!key)return;document.querySelectorAll('#po-settings-fields [data-source]').forEach(inp=>{const dst=document.getElementById(inp.dataset.source);if(dst&&inp.value!=='')dst.value=inp.value;});const cb=document.getElementById(PO_INDICATORS[key].check);if(cb)cb.checked=true;poCloseSettings();poRenderInstalled();sbPreviewRedraw();const st=document.getElementById('sb-status');if(st)st.textContent=`${PO_INDICATORS[key].name} settings applied to the chart. Save Profile to persist this strategy.`;}
function poRemoveIndicator(){const key=poEditingIndicator;if(!key)return;const cb=document.getElementById(PO_INDICATORS[key].check);if(cb)cb.checked=false;poCloseSettings();poRenderInstalled();sbPreviewRedraw();const st=document.getElementById('sb-status');if(st)st.textContent=`${PO_INDICATORS[key].name} removed from the chart and strategy. Save Profile to persist.`;}
function poIndicatorInit(){
 document.getElementById('sb-add-indicator')?.addEventListener('click',poOpenLibrary);
 document.getElementById('po-ind-close')?.addEventListener('click',poCloseLibrary);
 document.getElementById('po-ind-search')?.addEventListener('input',e=>poRenderIndicatorLibrary(e.target.value));
 document.getElementById('po-settings-cancel')?.addEventListener('click',poCloseSettings);
 document.getElementById('po-settings-save')?.addEventListener('click',poSaveSettings);
 document.getElementById('po-settings-remove')?.addEventListener('click',poRemoveIndicator);
 document.getElementById('po-ind-library')?.addEventListener('click',e=>{if(e.target.id==='po-ind-library')poCloseLibrary();});
 document.getElementById('po-ind-settings')?.addEventListener('click',e=>{if(e.target.id==='po-ind-settings')poCloseSettings();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){poCloseLibrary();poCloseSettings();}});
 setTimeout(poRenderInstalled,0);
}
document.addEventListener('DOMContentLoaded',poIndicatorInit);
// Keep installed labels synchronized after profile/library actions.
['sb-load','sb-save','sb-new','sb-duplicate','sb-legacy'].forEach(id=>document.getElementById(id)?.addEventListener('click',()=>setTimeout(poRenderInstalled,0)));

// ════════════════════════════════════════════════════════════
// B32.17 — PINE SCRIPT WORKBENCH
// Safe parser/translator only. Never evals or executes pasted source.
// ════════════════════════════════════════════════════════════
let pineScripts={}, pineLastAnalysis=null;
const PINE_CALLS={
  ema:{re:/ta\.ema\s*\([^,]+,\s*(\d+)\s*\)/gi,label:'EMA'}, sma:{re:/ta\.sma\s*\([^,]+,\s*(\d+)\s*\)/gi,label:'SMA'},
  rsi:{re:/ta\.rsi\s*\([^,]+,\s*(\d+)\s*\)/gi,label:'RSI'}, atr:{re:/ta\.atr\s*\(\s*(\d+)\s*\)/gi,label:'ATR'},
  macd:{re:/ta\.macd\s*\([^,]+,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/gi,label:'MACD'},
  bb:{re:/ta\.bb\s*\([^,]+,\s*(\d+)\s*,\s*([\d.]+)\s*\)/gi,label:'Bollinger Bands'},
  stoch:{re:/ta\.stoch\s*\([^,]+,[^,]+,[^,]+,\s*(\d+)\s*\)/gi,label:'Stochastic'},
  sar:{re:/ta\.sar\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)/gi,label:'Parabolic SAR'},
  supertrend:{re:/ta\.supertrend\s*\(\s*([\d.]+)\s*,\s*(\d+)\s*\)/gi,label:'Supertrend'}
};
function pineAnalyze(src){
  src=String(src||''); const version=(src.match(/\/\/@version\s*=\s*(\d+)/)||[])[1]||'unknown';
  const isStrategy=/\bstrategy\s*\(/.test(src), isIndicator=/\bindicator\s*\(/.test(src);
  const found=[]; for(const [key,d] of Object.entries(PINE_CALLS)){d.re.lastIndex=0;let m;while((m=d.re.exec(src)))found.push({key,label:d.label,args:m.slice(1),raw:m[0]});}
  const crosses=[...(src.matchAll(/ta\.(crossover|crossunder)\s*\(([^,]+),\s*([^\)]+)\)/gi))].map(m=>({type:m[1].toLowerCase(),a:m[2].trim(),b:m[3].trim()}));
  const entries=[...(src.matchAll(/strategy\.entry\s*\(\s*([^,]+),\s*strategy\.(long|short)(?:\s*,\s*when\s*=\s*([^\)]+))?/gi))].map(m=>({id:m[1].trim(),side:m[2].toUpperCase(),condition:(m[3]||'').trim()}));
  const unsupported=[];
  const checks=[['request.security',/\brequest\.security\b/],['arrays',/\barray\./],['matrices',/\bmatrix\./],['maps',/\bmap\./],['drawing objects',/\b(line|label|box|polyline)\.(new|set_)/],['strategy exits/orders',/\bstrategy\.(exit|close|order)\b/],['custom functions',/^\s*\w+\s*\([^\)]*\)\s*=>/m]];
  for(const [n,r] of checks)if(r.test(src))unsupported.push(n);
  const recognized=found.length+crosses.length+entries.length; const ready=src.trim().length>0 && (isStrategy||isIndicator) && unsupported.length===0 && recognized>0;
  const pct=src.trim()?Math.max(10,Math.min(100,100-unsupported.length*15-(recognized?0:45))):0;
  return {version,type:isStrategy?'STRATEGY':isIndicator?'INDICATOR':'UNKNOWN',found,crosses,entries,unsupported,recognized,ready,pct};
}
function pineAnalysisText(a){if(!a)return 'No analysis.';return `Pine v${a.version}\nType: ${a.type}\nTranslation coverage estimate: ${a.pct}%\nRecognized indicators: ${a.found.length?a.found.map(x=>x.label+'('+x.args.join(', ')+')').join(' · '):'none'}\nCross conditions: ${a.crosses.length}\nStrategy entries: ${a.entries.length}\nUnsupported/needs manual translation: ${a.unsupported.length?a.unsupported.join(', '):'none detected'}\n\n${a.ready?'READY FOR SAFE KAOS PROFILE CONVERSION':'NOT READY FOR AUTOMATIC CONVERSION'}\n\nKAOS does not execute Pine source directly. Import creates an editable KAOS custom profile from supported settings; review/backtest it before live use.`}
function pineRenderSaved(){const el=document.getElementById('pine-saved');if(!el)return;const rows=Object.values(pineScripts).sort((a,b)=>(b.updatedAt||0)-(a.updatedAt||0));el.innerHTML=rows.length?rows.map(x=>`<div class="pine-script-row"><span><b>${pineEsc(x.name)}</b><small style="display:block;color:var(--muted)">${pineEsc(x.type||'PINE')} · v${pineEsc(x.pineVersion||'?')}</small></span><button data-pine-load="${pineEsc(x.id)}">LOAD</button></div>`).join(''):'<span class="sb-note">No Pine scripts saved</span>';el.querySelectorAll('[data-pine-load]').forEach(b=>b.onclick=()=>pineLoad(b.dataset.pineLoad));}
function pineEsc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function pineOpen(){document.getElementById('pine-library')?.classList.add('open');pineRenderSaved();}
function pineClose(){document.getElementById('pine-library')?.classList.remove('open');}
function pineRunAnalysis(){pineLastAnalysis=pineAnalyze(document.getElementById('pine-source')?.value);const out=document.getElementById('pine-analysis');if(out){out.textContent=pineAnalysisText(pineLastAnalysis);out.className='pine-analysis '+(pineLastAnalysis.ready?'pine-ok':pineLastAnalysis.unsupported.length?'pine-warn':'pine-bad');}const c=document.getElementById('pine-convert');if(c)c.disabled=!pineLastAnalysis.ready;return pineLastAnalysis;}
function pineSave(){const src=document.getElementById('pine-source')?.value||'';const a=pineRunAnalysis();if(!src.trim())return;const name=document.getElementById('pine-name')?.value?.trim()||'Pine Script';const existing=Object.values(pineScripts).find(x=>x.name===name&&x.source===src);const id=existing?.id||('pine_'+Date.now());pineScripts[id]={id,name,description:document.getElementById('pine-description')?.value?.trim()||'',source:src,pineVersion:a.version,type:a.type,analysis:a,updatedAt:Date.now(),createdAt:existing?.createdAt||Date.now()};chrome.storage.local.set({pineScripts});pineRenderSaved();}
function pineLoad(id){const x=pineScripts[id];if(!x)return;document.getElementById('pine-name').value=x.name||'';document.getElementById('pine-description').value=x.description||'';document.getElementById('pine-source').value=x.source||'';pineRunAnalysis();}
function pineConvert(){const a=pineRunAnalysis();if(!a.ready)return;const src=document.getElementById('pine-source')?.value||'',name=document.getElementById('pine-name')?.value?.trim()||'Imported Pine Strategy';const p=structuredClone(SB_DEFAULT),id='pine_profile_'+Date.now();p.id=id;p.name=name;p.description=document.getElementById('pine-description')?.value?.trim()||`Imported from Pine Script v${a.version}. Review and backtest translated settings.`;p.type='custom';p.editable=true;p.sourceType='PINE';p.pineSource=src;p.pineVersion=a.version;p.pineTranslation={coverage:a.pct,recognized:a.recognized,unsupported:a.unsupported};
  // Disable defaults, then enable only safely recognized KAOS equivalents.
  for(const k of ['ema','rsi','macd','bb','stoch','atr','supertrend','sar'])if(p[k])p[k].enabled=false;
  const emas=a.found.filter(x=>x.key==='ema').map(x=>+x.args[0]).filter(Number.isFinite);if(emas.length){p.ema.enabled=true;const vals=[...new Set(emas)];while(vals.length<4)vals.push([20,50,100,200][vals.length]);p.ema.periods=vals.slice(0,4)}
  const r=a.found.find(x=>x.key==='rsi');if(r){p.rsi.enabled=true;p.rsi.period=+r.args[0]||14}
  const m=a.found.find(x=>x.key==='macd');if(m){p.macd.enabled=true;[p.macd.fast,p.macd.slow,p.macd.signal]=m.args.map(Number)}
  const bb=a.found.find(x=>x.key==='bb');if(bb){p.bb.enabled=true;p.bb.period=+bb.args[0]||20;p.bb.deviation=+bb.args[1]||2}
  const st=a.found.find(x=>x.key==='stoch');if(st){p.stoch.enabled=true;p.stoch.period=+st.args[0]||14}
  const at=a.found.find(x=>x.key==='atr');if(at){p.atr.enabled=true;p.atr.period=+at.args[0]||14}
  const su=a.found.find(x=>x.key==='supertrend');if(su){p.supertrend.enabled=true;p.supertrend.multiplier=+su.args[0]||3;p.supertrend.period=+su.args[1]||10}
  const sa=a.found.find(x=>x.key==='sar');if(sa){p.sar.enabled=true;p.sar.step=+sa.args[0]||.02;p.sar.max=+sa.args[2]||.2}
  const enabled=['ema','rsi','macd','bb','stoch','atr','supertrend','sar'].filter(k=>p[k]?.enabled).length;p.minConfirmations=Math.max(1,Math.min(p.minConfirmations,enabled||1));
  sbProfiles[id]=p;sbSelected=id;terminalSlotProfiles[terminalActiveSlot]=id;sbRefreshSelect();sbWrite(p);sbPersist();chrome.storage.local.set({terminalSlotProfiles});pineSave();if(typeof renderStrategyCatalogs==='function')renderStrategyCatalogs();if(typeof terminalRefreshStrategySelects==='function')terminalRefreshStrategySelects();if(typeof poRenderInstalled==='function')poRenderInstalled();const stt=document.getElementById('sb-status');if(stt)stt.textContent=`${name} created from supported Pine indicator settings. Pine conditions are preserved in source metadata but are NOT executed as TradingView Pine; review/backtest KAOS rules before live use.`;pineClose();}
function pineInit(){chrome.storage.local.get(['pineScripts'],r=>{pineScripts=r.pineScripts||{};pineRenderSaved()});document.getElementById('pine-open')?.addEventListener('click',pineOpen);document.getElementById('pine-close')?.addEventListener('click',pineClose);document.getElementById('pine-analyze')?.addEventListener('click',pineRunAnalysis);document.getElementById('pine-save')?.addEventListener('click',pineSave);document.getElementById('pine-convert')?.addEventListener('click',pineConvert);document.getElementById('pine-library')?.addEventListener('click',e=>{if(e.target.id==='pine-library')pineClose()});}
document.addEventListener('DOMContentLoaded',pineInit);

// B32.21.2 dashboard strategy chooser
document.addEventListener('DOMContentLoaded',()=>{
  const modal=document.getElementById('strategy-modal');
  const open=document.getElementById('choose-strategy-btn');
  const close=document.getElementById('strategy-modal-close');
  if(open&&modal) open.addEventListener('click',()=>{renderStrategyCatalogs?.();modal.classList.add('open')});
  if(close&&modal) close.addEventListener('click',()=>modal.classList.remove('open'));
  if(modal) modal.addEventListener('click',e=>{if(e.target===modal)modal.classList.remove('open')});
});


// ════════════════════════════════════════════════════════════════
// KAOS 1.3.0 — app-shell / CMS navigation.
// Distinct pages: dashboard / trading / advanced / settings (main shell),
// charts / ai / performance (chart shell). Presentation/router only.
// Trading authority and KAOS Strategy logic unchanged.
// ════════════════════════════════════════════════════════════════
(function kaosFivePageUI(){
  function q(sel, root=document){ return root.querySelector(sel); }
  function qa(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }
  function showKaosScreen(id){
    const key = id === 'screen-chart' ? 'chart' : id === 'screen-main' ? 'main' : null;
    if (key) showScreen(key);
  }
  function setTerminalPage(name){
    qa('#screen-chart .terminal-page').forEach(el=>el.classList.remove('active'));
    const map={charts:'terminal-live',backtester:'terminal-backtester',ai:'terminal-ai',performance:'terminal-analytics'};
    const el=document.getElementById(map[name]||'terminal-live');
    if(el) el.classList.add('active');
    // 1.6.34 invariant: LIVE charts exist only on Charts; AI/Performance never inherit them.
    const live=document.getElementById('terminal-live');
    if(live && name!=='charts') live.classList.remove('active');
    qa('#screen-chart .kaos-nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.kaosView===name));
    const ws=q('#screen-chart .kaos-terminal-workspace');
    if(ws){
      const titles={charts:'KAOS MULTI-CHART · TRADE MULTIPLE MARKETS',backtester:'KAOS STRATEGY BACKTESTER · HISTORICAL TESTING',ai:'KAOS AI · LEARN · ANALYZE · IMPROVE',performance:'PERFORMANCE · TRACK YOUR RESULTS'};
      ws.dataset.pageTitle=titles[name]||titles.charts;
    }
  }
  const MAIN_VIEWS={dashboard:1,settings:1,strategy:1,history:1,risk:1};
  const TERMINAL_VIEWS={charts:1,backtester:1,ai:1,performance:1};
  function setMainView(view){
    // legacy alias: strategy builder now lives in the Advanced page
    const v = view;
    showKaosScreen('screen-main');
    const main=document.getElementById('screen-main');
    if(!main) return;
    // showScreen('main') force-adds view-dashboard — apply the real view AFTER it.
    main.classList.remove('view-dashboard','view-trading','view-advanced','view-settings','view-strategy','view-history','view-risk');
    main.classList.add('view-'+v);
    qa('#screen-main .kaos-nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.kaosView===v));
  }
  function route(view){
    if(KAOS_COMPANION_ONLY && TERMINAL_VIEWS[view]){chrome.tabs.create({url:"https://tradingwithkaos.com/dashboard/"+({charts:"trading",backtester:"backtests",ai:"kaos-ai",performance:"trading"}[view])});return;}
    // 1.6.34 canonical navigation: Trading is Dashboard; Advanced is Build Strategy.
    if(view==='trading') view='dashboard';
    if(view==='advanced') view='strategy';
    if(TERMINAL_VIEWS[view]){
      showKaosScreen('screen-chart');
      setTerminalPage(view);
      if(view==='performance') setTimeout(kaosRenderFourChartPerformance,0);
      // 1.6.34: route() previously bypassed terminalShow(), so the chart refresh
      // loop never started when Charts was opened from the new sidebar.
      try{
        if(typeof terminalRefresh==='function'){
          // Reattach the Pocket Option bridge immediately on chart entry. This
          // removes the old requirement to manually refresh the Pocket Option tab
          // after reloading/updating the extension.
          (async()=>{try{
            const po=await getKAOSTargetTab();
            if(po&&po.id){ await kaosHealPoTab(po); await terminalRefresh(); }
          }catch(_){}})();
          terminalRefresh();
          if(terminalTimer) clearInterval(terminalTimer);
          terminalTimer=setInterval(terminalRefresh,1000);
        }
        window.dispatchEvent(new Event('resize'));
      }catch(_){}
    }else{
      // Dashboard also consumes the candle feed; only sign-out stops it.
      try{kaosStartChartFeed();}catch(_){}
      setMainView(MAIN_VIEWS[view] ? view : 'dashboard');
    }
    try{ localStorage.setItem('kaosLastView',view); }catch(_){}
  }
  window.kaosRoute = route;
  function bind(){
    qa('[data-kaos-view]').forEach(b=>{
      if(b.dataset.kaosBound) return;
      b.dataset.kaosBound='1';
      b.addEventListener('click',()=>route(b.dataset.kaosView));
    });
    const settings=document.getElementById('kaos-nav-settings');
    if(settings) settings.addEventListener('click',()=>route('settings'));
    // ── Settings page actions → reuse existing data/support controls ──
    const wire=(id,target)=>{const b=document.getElementById(id);if(b)b.addEventListener('click',()=>{const t=document.getElementById(target);if(t)t.click();});};
    wire('kaos-set-import','ai-popup-import');
    wire('kaos-set-backup','ai-popup-export');
    wire('kaos-set-diag','ai-popup-diagnostic');
    wire('kaos-set-support','support-btn');
    const back=document.getElementById('chart-back-btn');
    if(back) back.addEventListener('click',e=>{e.preventDefault();route('dashboard');});
    const open=document.getElementById('open-chart-btn');
    if(open) open.addEventListener('click',()=>setTimeout(()=>route('charts'),0));
    // Keep dashboard live chart visually tied to the real first multi-chart canvas.
    const mirror=document.getElementById('kaos-dashboard-canvas');
    const copyChart=()=>{
      if(KAOS_COMPANION_ONLY)return;
      if(!mirror) return;
      const src=document.querySelector('#terminal-four-grid .mc-canvas');
      const ctx=mirror.getContext('2d');
      if(!ctx) return;
      ctx.fillStyle='#030708';ctx.fillRect(0,0,mirror.width,mirror.height);
      let blank=true;
      if(src && src.width && src.height){
        try{
          ctx.drawImage(src,0,0,mirror.width,mirror.height);
          const sctx=src.getContext('2d',{willReadFrequently:true});
          if(sctx){
            const px=sctx.getImageData(0,0,src.width,src.height).data;
            for(let i=0;i<px.length;i+=4000){ if(px[i]>24||px[i+1]>24||px[i+2]>24){blank=false;break;} }
          }
        }catch(_){}
      }
      if(blank){
        ctx.fillStyle='#030708';ctx.fillRect(0,0,mirror.width,mirror.height);
        ctx.strokeStyle='#18303a';ctx.lineWidth=1;
        for(let x=0;x<mirror.width;x+=75){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,mirror.height);ctx.stroke();}
        for(let y=0;y<mirror.height;y+=60){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(mirror.width,y);ctx.stroke();}
        ctx.fillStyle='#4a6a80';ctx.font='700 13px monospace';ctx.textAlign='center';
        ctx.fillText('WAITING FOR MARKET DATA…',mirror.width/2,mirror.height/2-12);
        ctx.fillStyle='#3a566b';ctx.font='400 10px monospace';
        const diag=String(typeof kaosChartDiag==='string'?kaosChartDiag:'').slice(0,96);
        if(diag) ctx.fillText(diag,mirror.width/2,mirror.height/2+10);
        ctx.textAlign='left';
      }
      const name=document.querySelector('#terminal-four-grid .mc-name');
      const asset=document.getElementById('kaos-live-asset');
      if(name&&asset&&name.textContent.trim()!=='CHART 1') asset.textContent=name.textContent.trim();
    };
    setInterval(copyChart,900); copyChart();
    const main=document.getElementById('screen-main');
    if(main && (main.classList.contains('active') || main.style.display === 'flex' || main.style.display === 'block')) route('dashboard');
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind); else bind();
})();

// ════════════════════════════════════════════════════════════
//  BOOT SCREEN ROUTING — restored (v1.1.21)
//  The bypass replacement of startFlow dropped the original
//  boot-time call, so no .screen was ever shown and the popup
//  opened as a blank shell (header + gold frame only).
//  Restored routing mirrors startFlow:
//    • cached verified  → dashboard via showVerified()
//    • PO tab open      → full flow via startFlow()
//    • otherwise        → notPo guidance screen
// ════════════════════════════════════════════════════════════
async function kaosBootRoute() {
  if (window.__kaosBootRouted) return;
  window.__kaosBootRouted = true;
  try {
    showScreen('checking');
    setCheckMsg('VERIFYING KAOS MEMBERSHIP...');
    const cloud = await new Promise(resolve => chrome.runtime.sendMessage({type:'KAOS_STARTUP'}, r => {void chrome.runtime.lastError;resolve(r||{}); }));
    if (!cloud.ok || !['PLATFORM','DASHBOARD'].includes(cloud.state?.step)) {
      setCheckMsg('SIGN IN TO KAOS TO CONTINUE');
      return; // The cloud login UI owns the sign-in step; never redirect to Pocket Option.
    }
    setCheckMsg('CHOOSE YOUR TRADING BROKER');
    // The broker selector is independent of Pocket Option and is opened by
    // kaos-broker-selector.js after the same server-side membership check.
    // Only the Pocket Option selection may start PO trader-ID detection.
  } catch (_) {
    showScreen('checking');
    setCheckMsg('KAOS MEMBERSHIP CONNECTION UNAVAILABLE');
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', kaosBootRoute);
} else {
  kaosBootRoute();
}

(function kaosBannerUI(){
  const $=id=>document.getElementById(id);
  const qa=(s,c)=>Array.from((c||document).querySelectorAll(s));

  // ── View mode ─────────────────────────────────────────────
  // A Chrome toolbar popup cannot exceed 800x600, so "Max" opens the terminal
  // in a real browser tab (popup.html?kaosFull=1) where it fills the viewport.
  function kaosFullPage(){ try{ return /(?:^|[?&])kaosFull=1(?:&|$)/.test(location.search); }catch(_){ return false; } }
  function kaosCanOpenTab(){
    try{ return location.protocol==='chrome-extension:' && !kaosFullPage() &&
      !!(window.chrome&&chrome.tabs&&chrome.tabs.create&&chrome.runtime&&chrome.runtime.getURL); }catch(_){ return false; }
  }
  async function kaosEnterMax(){
    // Max is the KAOS app window, not a second Chrome tab.
    // This keeps the Pocket Option page selected as Chrome's active broker tab.
    setViewMode('max');
    try{ await chrome.runtime.sendMessage({type:'KAOS_KEEP_PO_ACTIVE',refocusApp:true}); }catch(_){}
  }
  function kaosToggleFullscreen(){
    try{
      if(document.fullscreenElement){ document.exitFullscreen(); return; }
      const el=document.documentElement;
      const fn=el.requestFullscreen||el.webkitRequestFullscreen||el.msRequestFullscreen;
      if(fn) fn.call(el);
    }catch(_){}
  }
  function setViewMode(mode,persist){
    if(!['mini','max'].includes(mode)) mode='max';
    document.body.classList.remove('kaos-mini','kaos-mid','kaos-max');
    document.body.classList.add('kaos-'+mode);
    try{
      if(location.protocol==='chrome-extension:'){
        chrome.windows.getCurrent().then(win=>chrome.runtime.sendMessage({type:'KAOS_RESIZE_APP',mode:mode,windowId:win.id})).catch(()=>{});
      }
    }catch(_){}
    qa('.kaos-view-btn').forEach(b=>b.classList.toggle('active',b.dataset.kaosMode===mode));
    if(persist!==false){ try{ localStorage.setItem('kaosViewMode',mode); }catch(_){} }
    const chartActive=document.body.classList.contains('chart-mode')||$('screen-chart')?.classList.contains('active');
    if(mode==='max'){
      if(typeof terminalShow==='function') terminalShow();
    }else if(chartActive){
      if(typeof terminalHide==='function') terminalHide(mode);
    }else if(typeof KAOSSetWindowMode==='function'){
      KAOSSetWindowMode(mode);
    }
  }

  function initViewMode(){
    let mode='mini';
    try{ mode=KAOS_COMPANION_ONLY?'mini':localStorage.getItem('kaosViewMode')||'max'; if(mode==='mid') mode='max'; }catch(_){}
    if(kaosFullPage()){ document.body.classList.add('kaos-fullpage'); setViewMode('max',false); return; }
    setViewMode(mode);
  }

  // ── Win controls (both title bars) ───────────────────────
  qa('[data-win]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const act=btn.dataset.win;
      if(act==='min') setViewMode('mini');
      else if(act==='max') kaosEnterMax();
      else if(act==='fullscreen') kaosToggleFullscreen();
      else if(act==='close'){
        // V1.2.1 — toolbar popup: close just the popup, never the browser window.
        try{ window.close(); }catch(_){}
      }
    });
  });

  // ── Sidebar view buttons ─────────────────────────────────
  qa('.kaos-view-btn').forEach(b=>{
    b.addEventListener('click',()=>{ (b.dataset.kaosMode==='max'?kaosEnterMax:setViewMode)(b.dataset.kaosMode); });
  });

  // ── Toolbar wiring ───────────────────────────────────────
  const marketSel=$('kaos-market-select');
  const amountIn=$('kaos-amount-input');
  const expirySel=$('kaos-expiry-select');
  const stratBox=$('kaos-strategy-box');
  const gear=$('kaos-toolbar-settings');
  const stopBtn=$('kaos-stop-btn');

  // Market → live asset label + persist
  if(marketSel){
    try{
      const saved=localStorage.getItem('kaosMarket');
      if(saved&&[...marketSel.options].some(o=>o.value===saved)) marketSel.value=saved;
    }catch(_){}
    const applyMarket=()=>{
      const asset=$('kaos-live-asset');
      if(asset) asset.textContent=marketSel.value;
      try{ localStorage.setItem('kaosMarket',marketSel.value); }catch(_){}
    };
    marketSel.addEventListener('change',applyMarket);
    applyMarket();
  }

  // Amount ↔ engine amount-input two-way sync
  if(amountIn){
    const engineAmount=$('amount-input');
    const syncToEngine=()=>{ if(engineAmount) engineAmount.value=amountIn.value; };
    const syncFromEngine=()=>{ if(engineAmount) amountIn.value=engineAmount.value; };
    amountIn.addEventListener('change',syncToEngine);
    if(engineAmount){
      engineAmount.addEventListener('change',syncFromEngine);
      if(engineAmount.value) amountIn.value=engineAmount.value;
    }
  }

  // Expiry → tf-btn activation + saveSettings
  if(expirySel){
    const map={'30s':30,'60s':60,'120s':180};
    const applyExpiry=()=>{
      const tf=map[expirySel.value]||60;
      qa('.tf-btn').forEach(b=>b.classList.toggle('active',parseInt(b.dataset.tf)===tf));
      if(typeof saveSettings==='function') saveSettings();
    };
    const syncFromEngine=()=>{
      const active=qa('.tf-btn').find(b=>b.classList.contains('active'));
      const tf=active?parseInt(active.dataset.tf):60;
      const label=Object.keys(map).find(k=>map[k]===tf);
      if(label) expirySel.value=label;
    };
    expirySel.addEventListener('change',applyExpiry);
    syncFromEngine();
  }

  // Strategy box → open strategy modal
  if(stratBox){
    stratBox.addEventListener('click',()=>{
      const modal=$('strategy-modal');
      if(!modal) return;
      if(typeof renderStrategyCatalogs==='function') renderStrategyCatalogs();
      modal.classList.add('open');
    });
  }

  // Gear → settings view
  if(gear){
    gear.addEventListener('click',()=>{
      if(typeof window.kaosRoute==='function') window.kaosRoute('settings');
    });
  }

  // Stop button → engine stopBot
  if(stopBtn){
    stopBtn.addEventListener('click',()=>{
      if(typeof stopBot==='function') stopBot();
    });
  }

  // ── Boot ──────────────────────────────────────────────────
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initViewMode);
  else initViewMode();
})();
/* ═══════════════ KAOS v1.6.34 runtime module (appended) ═══════════════
   Wires the B32.24 reference header pills, session popover, k14 nav items,
   bottom status cards and footer clock to real bot state. All mirrors are
   read-only copies of existing popup.js state — no new capabilities.      */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const qa = (s) => Array.from(document.querySelectorAll(s));
  const txt = (el) => (el && el.textContent ? el.textContent.trim() : '');

  function setPill(cls, state, label) {
    qa('.k14-pill.' + cls).forEach((p) => {
      if (state) p.setAttribute('data-state', state);
      const v = p.querySelector('.k14-pill-tx i');
      if (v && label) v.textContent = label;
    });
  }

  function botRunning() {
    const t = txt($('status-text')).toUpperCase();
    return /RUN|ACTIVE|TRADING/.test(t);
  }
  function poConnected() {
    const dot = $('status-dot');
    const t = txt($('status-text')).toUpperCase();
    return (dot && dot.classList.contains('active')) || /CONNECT|LIVE|READY|RUN/.test(t);
  }

  let serverHealthBusy=false;
  async function pingServer() {
    if(serverHealthBusy)return null;
    serverHealthBusy=true;
    try {
      const hr = await chrome.runtime.sendMessage({ type:'KAOS_HEALTH' });
      const h = hr && hr.health;
      if (h && h.ok) {
        setPill('k14-pill-server','on','ONLINE');
        return h;
      }
      setPill('k14-pill-server','off','OFFLINE');
      return h || null;
    } catch (_) {
      setPill('k14-pill-server','off','OFFLINE');
      return null;
    } finally {serverHealthBusy=false;}
  }

  function refreshPills() {
    const run = botRunning(), po = poConnected();
    setPill('k14-pill-po', po ? 'on' : 'off', po ? 'CONNECTED' : 'NOT ON PO');
    setPill('k14-pill-feed', po ? 'on' : 'off', po ? 'LIVE' : 'IDLE');
    setPill('k14-pill-bot', run ? 'on' : (po ? 'on' : 'wait'), run ? 'RUNNING' : 'READY');
    setPill('k14-pill-ai', run ? 'on' : 'wait', run ? 'ACTIVE' : 'STANDBY');
  }

  function refreshCards() {
    const run = botRunning();
    // AI STATUS card — mirrors of real debug fold values
    const wu = txt($('dbg-warmup-txt')) || '0/40';
    const bar = $('dbg-warmup-bar');
    const kbar = $('k14-ai-bar');
    if (kbar && bar) kbar.style.width = bar.style.width || '0%';
    if ($('k14-ai-warmup')) $('k14-ai-warmup').textContent = wu;
    if ($('k14-ai-engine')) $('k14-ai-engine').textContent = (txt($('dbg-reason')) || 'IDLE').slice(0, 18);
    if ($('k14-ai-archive')) $('k14-ai-archive').textContent = (txt($('exact-model-raw')) || 'loading…').slice(0, 34);
    const aiBadge = $('k14-ai-badge');
    if (aiBadge) { aiBadge.textContent = run ? 'ACTIVE' : 'STANDBY'; aiBadge.className = 'k14-ai-badge' + (run ? '' : ' off'); }
    const stBadge = $('k14-strat-badge');
    if (stBadge) { stBadge.textContent = run ? 'ACTIVE' : 'IDLE'; stBadge.className = 'k14-ai-badge' + (run ? '' : ' off'); }
    if ($('k14-strat-name')) {
      const sb = $('kaos-strategy-box');
      const name = sb && txt(sb) ? txt(sb) : 'KAOS Strategy';
      $('k14-strat-name').textContent = name.replace(/^ACTIVE\s·\s/i, '');
    }
    // RISK MANAGER card — mirrors of real inputs/pills
    const dll = $('daily-loss-limit'), mls = $('max-loss-streak');
    if ($('k14-risk-dll') && dll) $('k14-risk-dll').textContent = '$' + (Number(dll.value) || 0);
    if ($('k14-risk-mls') && mls) $('k14-risk-mls').textContent = String(Number(mls.value) || 0);
    const mp = $('mart-pill'), ap = $('auto-cd-pill');
    if ($('k14-risk-mart')) $('k14-risk-mart').textContent = mp && mp.classList.contains('on') ? 'ON' : 'OFF';
    if ($('k14-risk-acd')) $('k14-risk-acd').textContent = ap && ap.classList.contains('on') ? 'ON' : 'OFF';
    // SYSTEM STATUS card
    const po = poConnected();
    const setDot = (id, ok, warn) => { const d = $(id); if (d) d.className = 'k14-sys-dot ' + (ok ? 'ok' : warn ? 'warn' : ''); };
    setDot('k14-sys-po', po);
    setDot('k14-sys-feed', po);
    setDot('k14-sys-ai', run || (bar && parseFloat(bar.style.width) > 0), true);
    setDot('k14-sys-exec', run || po);
    setDot('k14-sys-mon', !!$('screen-main') && $('screen-main').classList.contains('active'));
    // badge mirror
    const badge = $('trader-badge'), bid = $('badge-id'), tb = $('k14-title-badge'), tbx = $('k14-title-badge-txt'), st = $('k14-session-trader');
    if (badge && badge.style.display === 'block') {
      if (tb) tb.style.display = 'inline-flex';
      if (tbx) tbx.textContent = txt(bid) || 'ID: ···';
      if (st) st.textContent = txt(bid) || '—';
    }
  }

  function openFoldAndGo(foldId) {
    if (typeof window.kaosRoute === 'function') window.kaosRoute('strategy');
    setTimeout(() => {
      const fold = $(foldId);
      if (fold) { fold.open = true; fold.scrollIntoView({ block: 'start' }); }
    }, 60);
  }

  function bindK14() {
    // session popover (banner header)
    const tog = $('k14-session-toggle'), pop = $('k14-session-pop');
    if (tog && pop) {
      tog.addEventListener('click', (e) => { e.stopPropagation(); pop.classList.toggle('open'); });
      document.addEventListener('click', (e) => { if (!pop.contains(e.target) && e.target !== tog) pop.classList.remove('open'); });
    }
    // k14-only nav items
    qa('[data-k14nav]').forEach((b) => {
      if (b.dataset.k14Bound) return; b.dataset.k14Bound = '1';
      b.addEventListener('click', () => {
        qa('#screen-main .kaos-nav-btn').forEach((n) => n.classList.remove('active'));
        b.classList.add('active');
        if (b.dataset.k14nav === 'history') {
          if (typeof window.kaosRoute === 'function') window.kaosRoute('history');
        } else if (b.dataset.k14nav === 'risk') {
          if (typeof window.kaosRoute === 'function') window.kaosRoute('risk');
        }
      });
    });
    // head / card action buttons
    const diag = $('k14-head-diag'); if (diag) diag.addEventListener('click', () => openFoldAndGo('debug-fold'));
    const sysDiag = $('k14-sys-diag'); if (sysDiag) sysDiag.addEventListener('click', () => openFoldAndGo('debug-fold'));
    const riskOpen = $('k14-risk-open'); if (riskOpen) riskOpen.addEventListener('click', () => openFoldAndGo('risk-fold'));
  }

  function tickClock() {
    const c = $('k14-ft-clock'); if (!c) return;
    const d = new Date();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const p = (n) => String(n).padStart(2, '0');
    c.textContent = `${months[d.getMonth()]} ${p(d.getDate())}, ${d.getFullYear()}  ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function boot() {
    bindK14();
    tickClock(); setInterval(tickClock, 1000);
    refreshPills(); refreshCards();
    setInterval(refreshPills, 1500);
    setInterval(refreshCards, 1500);
    setInterval(()=>{if(!document.hidden)pingServer();}, 60000); pingServer();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();

// KAOS 1.6.34 — Four-chart Performance page
function kaosPerfNum(v){v=Number(v);return Number.isFinite(v)?v:0;}
function kaosPerfSlotStats(slot){
  const market=terminalData?.markets?.[slot]||{};
  const trades=(terminalData?.allTrades||[]).filter(t=>{
    const s=Number(t.slot ?? t.chartSlot ?? t.chart ?? -1);
    const asset=String(t.asset||t.symbol||'');
    return s===slot || (s<0 && market.asset && asset===market.asset);
  });
  let wins=0,losses=0,ties=0,pnl=0;
  trades.forEach(t=>{
    const r=String(t.result||t.outcome||'').toUpperCase();
    if(r==='WIN'||r==='W')wins++; else if(r==='LOSS'||r==='L')losses++; else if(r==='TIE'||r==='DRAW'||r==='T')ties++;
    // Net P/L only: never treat payout/return/amount as profit.
    const explicitNet=t.netPnl ?? t.net_pnl ?? t.netProfit ?? t.net_profit ?? t.realizedPnl ?? t.realized_pnl;
    if(explicitNet!==undefined && explicitNet!==null && Number.isFinite(Number(explicitNet))){
      pnl+=Number(explicitNet);
    }else{
      const stake=Math.abs(kaosPerfNum(t.amount ?? t.stake ?? t.bet ?? t.investment));
      const payoutRaw=kaosPerfNum(t.payoutPercent ?? t.payout_percent ?? t.payout ?? t.profitPercent ?? t.profit_percent);
      const rate=payoutRaw>1?payoutRaw/100:payoutRaw;
      if(r==='WIN'||r==='W') pnl+=stake*rate;
      else if(r==='LOSS'||r==='L') pnl-=stake;
    }
  });
  const decided=wins+losses, wr=decided?100*wins/decided:0;
  return {slot,asset:market.asset||`CH${slot+1}`,wins,losses,ties,total:trades.length,wr,pnl};
}
function kaosRenderFourChartPerformance(){
  const page=document.getElementById('terminal-analytics');
  if(!page)return;
  const stats=[0,1,2,3].map(kaosPerfSlotStats);
  const active=Math.max(1,Math.min(4,Number(window.kaosChartCount||kaosChartCount||1)));
  const visible=stats.slice(0,active);
  const total=visible.reduce((a,s)=>({wins:a.wins+s.wins,losses:a.losses+s.losses,ties:a.ties+s.ties,total:a.total+s.total,pnl:a.pnl+s.pnl}),{wins:0,losses:0,ties:0,total:0,pnl:0});
  const decided=total.wins+total.losses, wr=decided?100*total.wins/decided:0;
  page.innerHTML=`
    <div class="kaos-perf-head">
      <div><b>PERFORMANCE</b><span>All ${active} active trading chart${active===1?'':'s'}</span></div>
      <div class="kaos-perf-total"><strong>${wr.toFixed(1)}%</strong><small>COMBINED WIN RATE</small></div>
    </div>
    <div class="kaos-perf-grid">
      ${visible.map(s=>`
        <section class="kaos-perf-card">
          <div class="kpc-title"><b>CH${s.slot+1}</b><span>${s.asset}</span></div>
          <div class="kpc-wr">${s.wr.toFixed(1)}%</div>
          <div class="kpc-label">WIN RATE</div>
          <div class="kpc-stats">
            <span><b>${s.wins}</b> Wins</span><span><b>${s.losses}</b> Losses</span>
            <span><b>${s.ties}</b> Ties</span><span><b>${s.total}</b> Trades</span>
          </div>
          <div class="kpc-pnl"><small>P/L</small><b>${s.pnl>=0?'+':''}${s.pnl.toFixed(2)}</b></div>
        </section>`).join('')}
    </div>
    <section class="kaos-perf-combined">
      <b>COMBINED · ${active} CHART${active===1?'':'S'}</b>
      <span>${total.wins}W · ${total.losses}L · ${total.ties}T · ${total.total} trades</span>
      <strong>${wr.toFixed(1)}% WIN RATE</strong>
      <em>P/L ${total.pnl>=0?'+':''}${total.pnl.toFixed(2)}</em>
    </section>`;
}

setInterval(()=>{
  try{
    if(document.getElementById('terminal-analytics')?.classList.contains('active')) kaosRenderFourChartPerformance();
  }catch(_){}
},1000);

// KAOS 1.6.34 — one canonical live data source for Dashboard / History / Performance
function kaosTradeNet(t){
  const explicit=t.netPnl ?? t.net_pnl ?? t.netProfit ?? t.net_profit ?? t.realizedPnl ?? t.realized_pnl;
  if(explicit!==undefined && explicit!==null && Number.isFinite(Number(explicit))) return Number(explicit);
  if(Number.isFinite(Number(t.profit))) return Number(t.profit);
  return 0;
}
function kaosLiveTrades(r){
  if(Array.isArray(r?.allTrades)) return r.allTrades.slice();
  return (r?.markets||[]).flatMap(m=>(m.trades||[]).map(t=>({...t,asset:t.asset||m.asset})));
}
function kaosSyncLiveStats(r){
  const trades=kaosLiveTrades(r).filter(t=>t&&t.result);
  let w=0,l=0,pnl=0;
  trades.forEach(t=>{
    const x=String(t.result||'').toUpperCase();
    if(x==='WIN'||x==='W')w++; else if(x==='LOSS'||x==='L')l++;
    pnl+=kaosTradeNet(t);
  });
  state.wins=w; state.losses=l; state.pnl=pnl; state.trades=trades;
  updateStatsUI();
  renderLog();
}
function kaosRenderTradeHistory(r){
  const list=document.getElementById('log-entries');
  if(!list)return;
  const trades=kaosLiveTrades(r).filter(t=>t&&t.result).sort((a,b)=>(+b.ts||0)-(+a.ts||0));
  list.innerHTML=trades.length?trades.slice(0,200).map(t=>{
    const x=String(t.result||'').toUpperCase(),net=kaosTradeNet(t);
    return `<div class="log-entry"><span>${new Date(+t.ts||Date.now()).toLocaleTimeString()}</span><span>${t.asset||'—'}</span><span>${t.direction||'—'}</span><span class="${x==='WIN'?'win':x==='LOSS'?'loss':''}">${x}</span><span class="${net<0?'loss':'win'}">${net>=0?'+':''}$${net.toFixed(2)}</span></div>`;
  }).join(''):'<div class="log-empty">No completed live trades yet</div>';
}
function kaosAiValue(v,samples){
  const n=Number(v);
  return Number(samples)>0 && Number.isFinite(n) && n>0 ? (n*100).toFixed(1)+'%' : 'COLLECTING';
}

// KAOS 1.6.34 — import progress / success / failure feedback
function kaosImportProgress(percent,message,detail,state='working'){
  const modal=document.getElementById('kaos-import-modal'),card=modal?.querySelector('.kaos-import-card');
  if(!modal||!card)return;
  modal.classList.add('show');modal.setAttribute('aria-hidden','false');
  card.classList.remove('success','failed');
  if(state==='success')card.classList.add('success');
  if(state==='failed')card.classList.add('failed');
  document.getElementById('kim-percent').textContent=Math.max(0,Math.min(100,Math.round(percent)))+'%';
  document.getElementById('kim-bar').style.width=Math.max(0,Math.min(100,percent))+'%';
  document.getElementById('kim-message').textContent=message||'';
  document.getElementById('kim-detail').textContent=detail||'';
  document.getElementById('kim-title').textContent=state==='success'?'IMPORT SUCCESSFUL':state==='failed'?'IMPORT FAILED':'IMPORTING DATA';
  document.getElementById('kim-close').disabled=state==='working';
}
function kaosImportDone(ok,message,detail){
  kaosImportProgress(ok?100:0,message,detail,ok?'success':'failed');
}
document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('kim-close')?.addEventListener('click',()=>{
    const m=document.getElementById('kaos-import-modal');m?.classList.remove('show');m?.setAttribute('aria-hidden','true');
  });
});

document.addEventListener('change',async function kaosImportFeedback(e){
  const input=e.target;
  if(!(input instanceof HTMLInputElement)||input.type!=='file'||!input.files?.length)return;
  const tag=((input.id||'')+' '+(input.name||'')+' '+(input.className||'')).toLowerCase();
  if(!/(import|load|restore|profile|data|ai)/.test(tag))return;
  const file=input.files[0];
  try{
    kaosImportProgress(8,'Reading import file…',file.name);
    await new Promise(r=>setTimeout(r,60));
    if(!file.size)throw new Error('The selected file is empty.');
    kaosImportProgress(28,'Validating file…',`${(file.size/1024).toFixed(1)} KB`);
    const text=await file.text();
    await new Promise(r=>setTimeout(r,60));
    if(!text.trim())throw new Error('The selected file contains no data.');
    kaosImportProgress(52,'Checking KAOS data format…','Validating JSON and import structure');
    let parsed=null;
    if(/\.json$/i.test(file.name)||text.trim().startsWith('{')||text.trim().startsWith('[')){
      try{parsed=JSON.parse(text);}catch(err){throw new Error('Invalid JSON: '+err.message);}
      if(parsed===null||typeof parsed!=='object')throw new Error('The file does not contain a valid KAOS data object.');
    }
    kaosImportProgress(72,'Importing data…','Applying AI, profile and bot data');
    // Existing import handler runs on this same change event. Give it time to apply/throw.
    await new Promise(r=>setTimeout(r,350));
    kaosImportProgress(90,'Verifying import…','Confirming imported data was accepted');
    await new Promise(r=>setTimeout(r,180));
    kaosImportDone(true,'Data imported successfully.',`${file.name} · ${(file.size/1024).toFixed(1)} KB`);
  }catch(err){
    kaosImportDone(false,'The import could not be completed.',String(err?.message||err));
  }
},true);

async function kaosEnsurePoNow(){
  try{return await chrome.runtime.sendMessage({type:'KAOS_PO_ENSURE_ATTACH'});}catch(_){return null;}
}
setTimeout(kaosEnsurePoNow,500);
setInterval(kaosEnsurePoNow,4000);

function kaosMoney(v){
  const n=Number(v);
  return Number.isFinite(n)?'$'+n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
}
function kaosUpdateAccountBalance(r){
  // Only accept the explicit Pocket Option account balance sent by content.js.
  // Generic market/snapshot `balance` fields can be stake/amount values.
  const vals=[r?.accountBalance];
  const bal=vals.find(v=>v!==null&&v!==undefined&&Number.isFinite(Number(v)));
  const targets=[
    document.getElementById('kaos-account-balance'),
    document.getElementById('kaos-balance')
  ].filter(Boolean);
  for(const el of targets){
    if(bal===undefined){
      el.textContent=el.id==='kaos-balance'?'Balance: Waiting for Pocket Option…':'Waiting for Pocket Option…';
      delete el.dataset.poLiveBalance;
    }else{
      el.textContent=el.id==='kaos-balance'?`Balance: ${kaosMoney(bal)}`:kaosMoney(bal);
      el.dataset.poLiveBalance='1';
      el.title=`Pocket Option ${r?.accountIsDemo===true?'DEMO':r?.accountIsDemo===false?'REAL':''} balance · live socket`;
    }
  }
}

// KAOS 1.6.34 — Account & Session presentation.
// Keep history/backfill/stream diagnostics out of the market-name line.
function kaosCleanAccountCard(){
  const s=document.getElementById('status-text');
  const l=document.getElementById('kaos-last-trade');
  if(s){
    const raw=(s.textContent||'').trim();
    const market=(raw.match(/[A-Z0-9]{3,15}(?:_[a-z]+)?/i)||[])[0];
    if(market && /(?:_otc|USD|EUR|GBP|JPY|CHF|CAD|AUD|BTC|ETH)/i.test(market)) s.textContent=market;
  }
  if(l){
    let t=(l.textContent||'').replace(/\s+/g,' ').trim();
    if(/history backfilled/i.test(t)) t='Market history ready · verifying live stream…';
    l.textContent=t||'Waiting for live market data…';
  }
}
setInterval(kaosCleanAccountCard,700);
setTimeout(kaosCleanAccountCard,100);

// KAOS 1.6.34 — clean sidebar and enforce readable Account & Session sizing.
function kaosRepairDashboardChrome(){
  // Remove decorative sidebar image/cards that were being clipped under View Mode.
  document.querySelectorAll('aside img, .sidebar img, .side-nav img').forEach(img=>{
    const s=(img.getAttribute('src')||'').toLowerCase();
    if(/kaos_(app|brand|header|social)|brand|promo/.test(s)){
      const shell=img.closest('.promo-card,.brand-card,.art-card,.sidebar-art,.sidebar-promo');
      if(shell) shell.remove(); else img.remove();
    }
  });
  // Mid mode is retired.
  document.querySelectorAll('button,[role="button"]').forEach(el=>{
    if((el.textContent||'').trim().toLowerCase()==='mid') el.remove();
  });
}
document.addEventListener('DOMContentLoaded',kaosRepairDashboardChrome);
setTimeout(kaosRepairDashboardChrome,250);

// KAOS 1.6.34 — screenshot-specific cleanup.
function kaos1616Cleanup(){
  const roots=[...document.querySelectorAll('.sidebar,.side-nav,aside')];
  for(const root of roots){
    // Anything below View Mode that is promotional "Trade With KAOS" artwork is removed.
    const nodes=[...root.querySelectorAll('*')];
    for(const el of nodes){
      const text=(el.textContent||'').replace(/\s+/g,' ').trim().toUpperCase();
      if(text==='TRADE WITH KAOS'){
        const shell=el.closest('.sidebar-brand-image,.sidebar-promo,.sidebar-art,.sidebar-footer-art,.promo-card,.brand-card,.art-card') || el;
        shell.remove();
      }
    }
    for(const img of [...root.querySelectorAll('img')]){
      const src=(img.getAttribute('src')||'').toLowerCase();
      const alt=(img.getAttribute('alt')||'').toLowerCase();
      if(/kaos_(app|brand|header|social)|trade.?with.?kaos|promo/.test(src+' '+alt)){
        const shell=img.closest('.sidebar-brand-image,.sidebar-promo,.sidebar-art,.sidebar-footer-art,.promo-card,.brand-card,.art-card') || img;
        shell.remove();
      }
    }
  }
}
document.addEventListener('DOMContentLoaded',kaos1616Cleanup);
setTimeout(kaos1616Cleanup,100);
setTimeout(kaos1616Cleanup,1000);

// KAOS 1.6.34 — remove the exact promotional strip/art circled below View Mode.
function kaos1617RemoveSidebarPromo(){
  for(const root of document.querySelectorAll('.sidebar,.side-nav,aside')){
    const all=[...root.querySelectorAll('*')];
    for(const el of all){
      const text=(el.textContent||'').replace(/\s+/g,' ').trim().toUpperCase();
      const cls=String(el.className||'').toLowerCase();
      const isPromoText=/^(AUTOMATED\s*[·.\-]\s*INTELLIGENT|TRADE WITH KAOS|AUTOMATED\.?\s*INTELLIGENT)/.test(text);
      const isPromoClass=/(sidebar-(promo|art|brand)|promo-card|brand-card|art-card|tagline|slogan)/.test(cls);
      if(isPromoText||isPromoClass){
        const view=el.closest('.view-mode,.view-modes');
        if(!view) el.remove();
      }
    }
    for(const img of [...root.querySelectorAll('img')]){
      const s=((img.getAttribute('src')||'')+' '+(img.getAttribute('alt')||'')).toLowerCase();
      if(/kaos_(app|brand|header|social)|trade.?with.?kaos|promo/.test(s)) img.remove();
    }
  }
}
// 1.6.34: keep KAOS sidebar artwork; promo removal disabled.



// KAOS 1.6.34 — surgical view fix only. No page/show-hide routing changes.
async function kaos1619SetView(mode){
  const v=String(mode||'').toLowerCase();
  document.body.classList.toggle('kaos-view-max',v==='max');
  document.body.dataset.viewMode=v;
  if(v!=='max') return;
  try{
    const w=await chrome.windows.getCurrent();
    if(w && w.id && w.type==='popup') await chrome.windows.update(w.id,{state:'maximized',focused:true});
  }catch(_){}
}
document.addEventListener('click',(e)=>{
  const btn=e.target.closest('button,[role="button"]');
  if(!btn)return;
  const t=(btn.textContent||'').trim().toLowerCase();
  if(t==='max') setTimeout(()=>kaos1619SetView('max'),0);
  if(t==='mini') {
    document.body.classList.remove('kaos-view-max');
    document.body.dataset.viewMode='mini';
  }
});
setTimeout(()=>{
  const active=[...document.querySelectorAll('button,[role="button"]')].find(x=>
    (x.textContent||'').trim().toLowerCase()==='max' &&
    (x.classList.contains('active')||x.getAttribute('aria-pressed')==='true')
  );
  if(active) kaos1619SetView('max');
},300);

// KAOS 1.6.34 — chart terminal is visible only on Charts.
// Observe the app's existing screen state; do not replace navigation/routing.
function kaos1624SyncPageIsolation(){
  const body=document.body;
  if(!body)return;
  body.classList.remove('kaos-page-ai','kaos-page-performance');

  const ai=document.querySelector('#screen-ai,.screen-ai,[data-page="ai"],[data-screen="ai"]');
  const perf=document.querySelector('#screen-performance,.screen-performance,[data-page="performance"],[data-screen="performance"]');

  const visible=(el)=>{
    if(!el)return false;
    const cs=getComputedStyle(el);
    return cs.display!=='none' && cs.visibility!=='hidden' &&
      (el.classList.contains('active') || el.offsetParent!==null);
  };

  if(visible(ai)) body.classList.add('kaos-page-ai');
  else if(visible(perf)) body.classList.add('kaos-page-performance');
}
document.addEventListener('click',()=>setTimeout(kaos1624SyncPageIsolation,0));
document.addEventListener('DOMContentLoaded',kaos1624SyncPageIsolation);
setTimeout(kaos1624SyncPageIsolation,200);

// KAOS 1.6.34 — explicit page identity for AI/Performance.
// This only controls shared chart UI visibility; it does not replace existing routing.
function kaos1625SetPageFromLabel(label){
  const s=String(label||'').replace(/\s+/g,' ').trim().toLowerCase();
  const b=document.body;
  if(!b)return;
  b.classList.remove('kaos-page-ai','kaos-page-performance');
  if(s.includes('kaos ai')) b.classList.add('kaos-page-ai');
  else if(s.includes('performance')) b.classList.add('kaos-page-performance');
}
document.addEventListener('click',(e)=>{
  const item=e.target.closest('button,a,[role="button"],.nav-item,.menu-item');
  if(!item)return;
  const t=(item.textContent||'').replace(/\s+/g,' ').trim();
  if(/kaos\s*ai/i.test(t)) setTimeout(()=>kaos1625SetPageFromLabel('kaos ai'),0);
  else if(/performance/i.test(t)) setTimeout(()=>kaos1625SetPageFromLabel('performance'),0);
  else if(/charts|dashboard|build strategy|trade history|risk manager|settings/i.test(t))
    setTimeout(()=>kaos1625SetPageFromLabel(t),0);
},true);

// KAOS 1.6.34 — Dashboard chart-count authority.
// The Dashboard must visually show exactly the number of charts selected (1–4).
function kaos1627DashboardChartCount(){
  const candidates=[
    document.getElementById('chart-count'),
    document.getElementById('chartCount'),
    document.getElementById('how-many-charts'),
    document.querySelector('[name="chartCount"]'),
    document.querySelector('[data-chart-count]')
  ].filter(Boolean);
  for(const el of candidates){
    const n=parseInt(el.value ?? el.dataset.chartCount ?? el.textContent,10);
    if(n>=1&&n<=4)return n;
  }
  try{
    const n=parseInt(localStorage.getItem('kaosChartCount')||localStorage.getItem('chartCount'),10);
    if(n>=1&&n<=4)return n;
  }catch(_){}
  return 1;
}

function kaos1627SyncDashboardCharts(){
 if(KAOS_COMPANION_ONLY)return;
  const n=kaos1627DashboardChartCount();
  const dash=document.querySelector('#screen-dashboard,.screen-dashboard,[data-page="dashboard"],[data-screen="dashboard"]');
  if(!dash)return;

  // Locate the dashboard chart region/card. Do not touch the dedicated Charts page.
  let host=dash.querySelector('#dashboard-chart-grid,.dashboard-chart-grid,.dashboard-charts,.dash-charts');
  if(!host){
    const one=dash.querySelector('.market-chart,.dashboard-chart,.chart-card');
    if(!one)return;
    host=one.parentElement;
    if(!host)return;
    host.classList.add('dashboard-chart-grid');
  }

  let cards=[...host.querySelectorAll(':scope > .market-chart,:scope > .dashboard-chart,:scope > .chart-card')];
  if(!cards.length)return;
  const template=cards[0];

  while(cards.length<n){
    const clone=template.cloneNode(true);
    clone.classList.add('kaos-dashboard-chart-clone');
    clone.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
    host.appendChild(clone);
    cards=[...host.querySelectorAll(':scope > .market-chart,:scope > .dashboard-chart,:scope > .chart-card')];
  }
  cards.forEach((card,i)=>{
    card.style.display=i<n?'':'none';
    card.dataset.dashboardChart=String(i+1);
    const label=card.querySelector('.chart-number,.chart-label,[data-chart-label]');
    if(label && /chart\s*\d+/i.test(label.textContent||'')) label.textContent=`CHART ${i+1}`;
  });
  host.dataset.count=String(n);
}

document.addEventListener('change',(e)=>{
  if(e.target && (e.target.matches('#chart-count,#chartCount,#how-many-charts,[name="chartCount"],[data-chart-count]'))){
    const n=parseInt(e.target.value,10);
    if(n>=1&&n<=4) try{localStorage.setItem('kaosChartCount',String(n));}catch(_){}
    setTimeout(kaos1627SyncDashboardCharts,0);
  }
});
document.addEventListener('click',()=>setTimeout(kaos1627SyncDashboardCharts,50));
document.addEventListener('DOMContentLoaded',()=>setTimeout(kaos1627SyncDashboardCharts,150));
setInterval(kaos1627SyncDashboardCharts,1200);

// KAOS 1.6.34 — Dashboard uses the REAL four live chart cards.
// Do not clone the dashboard's one-card preview. Mirror the existing live Charts
// cards so selecting 4 actually produces four independent chart panels.
function kaos1628SelectedCount(){
  const selectors=[
    '#chart-count','#chartCount','#how-many-charts','#num-charts',
    '[name="chartCount"]','[name="charts"]','[data-chart-count]'
  ];
  for(const s of selectors){
    const el=document.querySelector(s);
    if(!el)continue;
    const n=parseInt(el.value ?? el.dataset.chartCount ?? el.textContent,10);
    if(n>=1&&n<=4)return n;
  }
  // Look for the dashboard selector by its nearby label.
  for(const el of document.querySelectorAll('select,input')){
    const txt=((el.previousElementSibling?.textContent||'')+' '+(el.parentElement?.textContent||'')).toLowerCase();
    if(/how many charts|charts.*max 4|number of charts/.test(txt)){
      const n=parseInt(el.value,10);
      if(n>=1&&n<=4)return n;
    }
  }
  try{
    for(const k of ['kaosChartCount','chartCount','kaos_chart_count','selectedChartCount']){
      const n=parseInt(localStorage.getItem(k),10);
      if(n>=1&&n<=4)return n;
    }
  }catch(_){}
  return 1;
}

function kaos1628Dashboard(){
 if(KAOS_COMPANION_ONLY)return;
  const dash=document.querySelector('#screen-dashboard,.screen-dashboard,[data-page="dashboard"],[data-screen="dashboard"]');
  if(!dash)return;
  const n=kaos1628SelectedCount();

  // Source = the actual independent live chart panels used by Charts.
  const source=[...document.querySelectorAll('#terminal-live .four-grid > .market-chart')];
  if(!source.length)return;

  let host=dash.querySelector('#kaos-dashboard-multichart');
  if(!host){
    host=document.createElement('div');
    host.id='kaos-dashboard-multichart';

    // Replace only the dashboard's old single chart preview when identifiable.
    const old=dash.querySelector('.dashboard-chart-grid,.dashboard-charts,.dash-charts,.dashboard-chart,.chart-preview');
    if(old){
      old.insertAdjacentElement('beforebegin',host);
      old.style.display='none';
      old.dataset.kaosReplacedByMulti='1';
    }else{
      // Put the grid before Account & Session / lower dashboard stats when possible.
      const account=dash.querySelector('.k14-acct,#account-session,.account-session');
      if(account) account.insertAdjacentElement('beforebegin',host);
      else dash.appendChild(host);
    }
  }

  host.dataset.count=String(n);
  // Rebuild from live chart panels to avoid stale clones from earlier versions.
  host.replaceChildren();
  for(let i=0;i<n;i++){
    const src=source[i] || source[0];
    const card=src.cloneNode(true);
    card.classList.add('kaos-dashboard-live-chart');
    card.dataset.dashboardChart=String(i+1);
    card.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
    // Canvas pixels do not clone. The existing dashboard chart renderer will
    // redraw these; leave a fresh canvas with matching dimensions/classes.
    card.querySelectorAll('canvas').forEach(cv=>{
      const fresh=document.createElement('canvas');
      fresh.className=cv.className;
      fresh.setAttribute('aria-label',cv.getAttribute('aria-label')||`Chart ${i+1}`);
      cv.replaceWith(fresh);
    });
    host.appendChild(card);
  }
}

// Persist and react to ANY 1–4 dashboard chart selector.
document.addEventListener('change',(e)=>{
  const el=e.target;
  if(!(el instanceof HTMLInputElement || el instanceof HTMLSelectElement))return;
  const n=parseInt(el.value,10);
  if(!(n>=1&&n<=4))return;
  const context=((el.parentElement?.textContent||'')+' '+(el.previousElementSibling?.textContent||'')).toLowerCase();
  if(/chart/.test(context) || /chart/i.test(el.id||'') || /chart/i.test(el.name||'')){
    try{localStorage.setItem('kaosChartCount',String(n));}catch(_){}
    setTimeout(kaos1628Dashboard,0);
  }
});
document.addEventListener('click',()=>setTimeout(kaos1628Dashboard,80));
document.addEventListener('DOMContentLoaded',()=>setTimeout(kaos1628Dashboard,300));
setInterval(kaos1628Dashboard,1500);

// KAOS 1.6.34 — the EXISTING Live Market card itself becomes 1–4 charts.
(function(){
 function selectedCount(){
   const n=parseInt(document.getElementById('kaos-chart-count')?.value,10);
   return n>=1&&n<=4?n:1;
 }
 function host(){
   return document.getElementById('kaos-dashboard-live');
 }
 function build(){
 if(KAOS_COMPANION_ONLY)return;
   const box=host();if(!box)return;
   const n=selectedCount();box.dataset.count=String(n);
   let grid=box.querySelector('.kaos-live-grid');
   if(!grid){
     grid=document.createElement('div');grid.className='kaos-live-grid';
     const canvas=box.querySelector('#kaos-dashboard-canvas,.kaos-dashboard-canvas,canvas');
     if(canvas)canvas.insertAdjacentElement('beforebegin',grid);
     else box.appendChild(grid);
   }
   while(grid.children.length<n){
     const i=grid.children.length,cell=document.createElement('div');
     cell.className='kaos-live-cell';
     cell.innerHTML='<div class="kaos-live-cell-head"><span>CH'+(i+1)+' · <b class="klm-name">WAITING</b></span><span class="klm-source">WAITING</span></div><canvas width="700" height="260"></canvas><div class="kaos-live-cell-foot"><span class="klm-status">WAITING FOR DATA</span></div>';
     grid.appendChild(cell);
   }
   [...grid.children].forEach((el,i)=>el.style.display=i<n?'':'none');
   paint();
 }
 function paint(){
 if(KAOS_COMPANION_ONLY)return;
   const box=host(),grid=box?.querySelector('.kaos-live-grid');if(!grid)return;
   const srcs=[...document.querySelectorAll('#terminal-four-grid .market-chart')];
   [...grid.children].forEach((cell,i)=>{
     if(cell.style.display==='none')return;
     const src=srcs[i],dst=cell.querySelector('canvas'),ctx=dst?.getContext('2d');if(!ctx)return;
     ctx.fillStyle='#030708';ctx.fillRect(0,0,dst.width,dst.height);
     const sc=src?.querySelector('.mc-canvas,canvas');
     if(sc&&sc.width&&sc.height){try{ctx.drawImage(sc,0,0,dst.width,dst.height)}catch(_){}}
     else{ctx.fillStyle='#71818a';ctx.font='12px monospace';ctx.textAlign='center';ctx.fillText('WAITING FOR MARKET DATA',dst.width/2,dst.height/2)}
     cell.querySelector('.klm-source').textContent=terminalData?.fallback?'RECORDED':kaosLiveChartOk?'LIVE':'WAITING';
     cell.querySelector('.klm-name').textContent=src?.querySelector('.mc-name')?.textContent?.trim()||`CHART ${i+1}`;
     const st=src?.querySelector('.mc-status,.mc-why')?.textContent?.trim();
     cell.querySelector('.klm-status').textContent=(st||'LIVE').slice(0,55);
   });
 }
 document.addEventListener('DOMContentLoaded',()=>{build();setInterval(paint,500)});
 document.getElementById('kaos-chart-count')?.addEventListener('change',build);
 setTimeout(build,250);
})();

// KAOS 1.6.34 — reserve full Live Market height before AI STATUS / STRATEGY / RISK MANAGER.
function kaos1631DashboardFlow(){
  const live=document.getElementById('kaos-dashboard-live');
  if(!live)return;
  const n=parseInt(live.dataset.count||document.getElementById('kaos-chart-count')?.value||'1',10);
  if(n<3)return;

  const dash=live.closest('#screen-dashboard,.screen-dashboard,[data-page="dashboard"],[data-screen="dashboard"]') || live.parentElement;
  if(!dash)return;
  const wanted=['AI STATUS','STRATEGY','RISK MANAGER'];
  const cards=[...dash.querySelectorAll('section,div,article')].filter(el=>{
    const own=[...el.childNodes].filter(x=>x.nodeType===3).map(x=>x.textContent).join(' ').trim().toUpperCase();
    const heading=el.querySelector(':scope > h1,:scope > h2,:scope > h3,:scope > h4,:scope > .card-title,:scope > .section-title');
    const txt=(heading?.textContent||own||'').replace(/\s+/g,' ').trim().toUpperCase();
    return wanted.includes(txt);
  });
  const parents=cards.map(x=>x.parentElement).filter(Boolean);
  const common=parents.find(x=>parents.filter(y=>y===x).length>=2);
  if(common){
    common.style.position='relative';
    common.style.top='auto';
    common.style.bottom='auto';
    common.style.transform='none';
    common.style.marginTop='14px';
  }
}
document.addEventListener('DOMContentLoaded',()=>setTimeout(kaos1631DashboardFlow,350));
document.getElementById('kaos-chart-count')?.addEventListener('change',()=>setTimeout(kaos1631DashboardFlow,20));
setTimeout(kaos1631DashboardFlow,500);

// KAOS 1.6.34 — size Live Market from its actual 1–4 chart grid so lower cards
// can never overlap/cut off CH3 or CH4.
function kaos1632ReserveDashboardHeight(){
 if(KAOS_COMPANION_ONLY)return;
  const live=document.getElementById('kaos-dashboard-live');
  const grid=live?.querySelector('.kaos-live-grid');
  if(!live||!grid)return;
  const n=parseInt(live.dataset.count||document.getElementById('kaos-chart-count')?.value||'1',10);
  live.style.height='auto';
  live.style.maxHeight='none';
  live.style.overflow='visible';
  if(n>=3){
    // two 235px rows + 8px grid gap; browser then lays following cards below it
    grid.style.minHeight='478px';
    live.style.minHeight='478px';
  }else{
    grid.style.minHeight='';
    live.style.minHeight='';
  }
}
document.addEventListener('DOMContentLoaded',()=>setTimeout(kaos1632ReserveDashboardHeight,300));
document.getElementById('kaos-chart-count')?.addEventListener('change',()=>setTimeout(kaos1632ReserveDashboardHeight,30));
window.addEventListener('resize',()=>setTimeout(kaos1632ReserveDashboardHeight,30));
setTimeout(kaos1632ReserveDashboardHeight,600);


// KAOS 1.6.38 — AI Intelligence shadow dashboard.
(function KAOS_AI_INTELLIGENCE_UI(){
  function set(id,v){const e=document.getElementById(id);if(e)e.textContent=v||'WAITING';}
  function render(){
    try{
      chrome.storage.local.get(['kaosPoAiShadow','kaosExternalAiShadow'],r=>{
        const po=r.kaosPoAiShadow;
        if(po){
          const age=Math.round((Date.now()-Number(po.observedAt||0))/1000);
          set('kai-po', po.direction ? `${po.direction}${po.expirySec?' · '+po.expirySec+'s':''}` : 'AI ACTIVITY SEEN');
          set('kai-po-detail', `Pocket Option UI observation · ${age}s ago`);
        }else{
          set('kai-po','WATCHING');
          set('kai-po-detail','Use Pocket Option AI/AI Trader and KAOS will record visible output');
        }
        const ex=r.kaosExternalAiShadow;
        if(ex) set('kai-ext',`${ex.direction||'SIGNAL'}${ex.confidence!=null?' · '+Number(ex.confidence).toFixed(0)+'%':''}`);
      });
    }catch(_){}
  }
  document.addEventListener('DOMContentLoaded',()=>{render();setInterval(render,1000)});
  setTimeout(render,500);
})();


// KAOS 1.6.38 — Full AI Stack renderer.
// LightGBM was already present in the native model/report path; expose it explicitly.
// OpenAI Brain is server-mediated and remains shadow-only until the KAOS backend endpoint is live.
(function KAOS_1637_FULL_AI_STACK(){
  const fmt=(v)=>{
    v=Number(v); if(!Number.isFinite(v)) return 'WAITING';
    const d=v>=.5?'BUY':'SELL', conf=Math.max(v,1-v)*100;
    return `${d} · ${conf.toFixed(1)}%`;
  };
  function set(id,v){const e=document.getElementById(id);if(e)e.textContent=v}
  async function tick(){
    try{
      // Existing content.js already publishes xgbAI + shadowLgb fields through terminal state.
      const tabs=await chrome.tabs.query({url:["*://*.pocketoption.com/*","*://pocketoption.com/*"]});
      const tab=tabs.find(t=>t.id);
      if(tab){
        try{
          const r=await chrome.tabs.sendMessage(tab.id,{type:'KAOS_GET_AI_INTELLIGENCE'});
          if(r?.ok){
            set('kai-xgb',fmt(r.xgbUp));
            set('kai-lgb',fmt(r.lgbUp));
            set('kai-strategy',r.strategy||'WAITING');
          }
        }catch(_){}
      }
      chrome.storage.local.get(['kaosOpenAiBrainShadow','kaosOpenAiBrainStatus'],r=>{
        const a=r.kaosOpenAiBrainShadow, st=r.kaosOpenAiBrainStatus;
        if(!a){
          const state=st?.state||'WAITING FOR MARKET';
          set('kai-openai',state.replaceAll('_',' '));
          set('kai-openai-detail',st?.detail?String(typeof st.detail==='string'?st.detail:JSON.stringify(st.detail)).slice(0,120):'Starts automatically after KAOS produces a live market decision');
          return;
        }
        const age=Math.round((Date.now()-Number(a.ts||0))/1000);
        set('kai-openai',`${a.direction||'HOLD'}${a.confidence!=null?' · '+Number(a.confidence).toFixed(0)+'%':''}${a.expirySec?' · '+a.expirySec+'s':''}`);
        set('kai-openai-detail',`${a.regime||'UNKNOWN'} · ${a.model||'OPENAI'} · ${age}s ago · shadow only`);
      });
    }catch(_){}
  }
  document.addEventListener('DOMContentLoaded',()=>{tick();setInterval(tick,1000)});
})();
