// ═══════════════════════════════════════════════════════════════
//  Pocket Option Auto Trader — po-bridge.js v4.4.4 V208 STICKY DEMO HANDSHAKE
//  KEY FIX: Use openedCount (integer) not ID array.
//  successcloseOrder sometimes arrives before successopenOrder,
//  so ID matching caused deals to be skipped → tradePending stuck.
//  Now: all close events while started are forwarded unconditionally.
// ═══════════════════════════════════════════════════════════════
(() => {
  if (window.__poatBridge440) return;
  window.__poatBridge440 = true;

  const state = {
    started:       false,
    pendingAction: null,
    futureDeals:   [],
    openedCount:   0,
    startSum:      null,
    isDemo:        null,  // null until updateBalance arrives — never assume demo or real
    timeframe:     60,
    multiAsset:    false,
    maxConcurrent: 10,
    pendingOrders: Object.create(null),   // orderId -> normalized direction
    activeDirections: Object.create(null), // asset -> normalized direction; survives close-before-open races
    chartAsset:     '',
    chartSlots:     Object.create(null),
    historyRequested: new Set(),
    historySockets: new Set(),
  };

  const post = (obj) => {
    try { window.postMessage({ _poat: true, ...obj }, '*'); } catch(e) {}
  };

  // V24.1.102: chart-asset discovery cannot rely only on Pocket Option replaying
  // updateHistory after START.  On some page loads the history packet happened
  // before the bridge was injected, leaving state.chartAsset empty forever even
  // though live STREAM packets were flowing.  Keep the broker asset list and
  // resolve the visibly selected/current instrument from the DOM.
  const knownAssetNames = new Set();
  // V24.1.122d: assets actually streaming on the live chart sockets THIS session.
  // Each of the 4 chart channels fires updateStream/updateHistory with its own
  // real symbol, so this set is the ground truth for what is really trading.
  // A slot's DOM label can be a garbage chip ("BTCGBP"), but the channel that
  // feeds that panel always reports its true market here — we bind by it.
  const liveStreamAssets = new Set();
  const liveStreamLastSeen = new Map();
  function markLiveStreamAsset(name){const a=String(name||'').trim();if(!a)return;liveStreamAssets.add(a);liveStreamLastSeen.set(a,Date.now());}
  function recentLiveStreamAssets(maxAgeMs=6000){const now=Date.now(),out=[];for(const a of liveStreamAssets){const seen=Number(liveStreamLastSeen.get(a)||0);if(seen&&now-seen<=maxAgeMs)out.push(a);}return out;}
  let chartResolveTimer = null;
  let accountProbeTimer = null;
  let demoConfirmedSticky = false;
  let demoConfirmedAt = 0;
  const normAsset = (x) => String(x || '').toUpperCase()
    .replace(/_OTC/g,'OTC').replace(/[^A-Z0-9]/g,'');
  const visibleEl = (el) => {
    try {
      if (!el || !el.isConnected) return false;
      const r = el.getBoundingClientRect();
      const st = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden' && Number(st.opacity || 1) !== 0;
    } catch(e) { return false; }
  };
  // V24.1.200 — DEMO ACCOUNT HANDSHAKE FIX. Pocket Option currently renders
  // the active paper account as labels such as "QT Demo". Older builds only
  // recognized the exact word "Demo" *and* required a matching visible "Real"
  // tab, leaving state.isDemo=null on the four-chart page. The execution safety
  // gate then correctly refused every READY signal. Detect strong, visible account
  // markers while remaining fail-closed: ambiguous/unknown DOM stays null.
  const confirmAccountFromDom = () => {
    try {
      const textOf=(el)=>(el?.textContent||'').replace(/\s+/g,' ').trim();
      const classify=(raw)=>{
        raw=String(raw||'').trim();
        if(!raw || raw.length>48) return null;
        if(/^(?:qt\s*)?(?:demo|paper|practice)(?:\s*(?:account|balance))?$/i.test(raw)) return true;
        if(/^(?:qt\s*)?(?:real|live)(?:\s*(?:account|balance))?$/i.test(raw)) return false;
        return null;
      };
      const accept=(c)=>{
        if(c===true){
          state.isDemo=true;
          demoConfirmedSticky=true;
          demoConfirmedAt=Date.now();
          return true;
        }
        if(c===false){
          state.isDemo=false;
          demoConfirmedSticky=false;
          demoConfirmedAt=0;
          return false;
        }
        if(demoConfirmedSticky){
          state.isDemo=true;
          return true;
        }
        state.isDemo=null;
        return null;
      };

      const activeSelectors=[
        '[aria-selected="true"]','[aria-current="true"]','[aria-current="page"]',
        '[data-active="true"]','[data-selected="true"]',
        '[class*="account"][class*="active"]','[class*="account"][class*="selected"]',
        '[class*="balance"][class*="active"]','[class*="balance"][class*="selected"]',
        '[class*="switch"][class*="active"]','[class*="switch"][class*="selected"]'
      ];
      for(const sel of activeSelectors){
        for(const el of document.querySelectorAll(sel)){
          if(!visibleEl(el)) continue;
          const c=classify(textOf(el));
          if(c!==null) return accept(c);
        }
      }

      const compact=document.querySelectorAll('header span,header div,[class*="header"] span,[class*="header"] div,[class*="balance"] span,[class*="balance"] div');
      for(const el of compact){
        if(!visibleEl(el)) continue;
        const raw=textOf(el);
        if(raw.length>32) continue;
        const c=classify(raw);
        if(c!==null) return accept(c);
      }

      let sawDemo=false,sawReal=false;
      const scope=document.querySelectorAll('button,[role="tab"],[role="button"],[class*="account"],[class*="balance"],[class*="switch"],[class*="mode"],[class*="segment"]');
      for(const el of scope){
        if(!visibleEl(el)) continue;
        const c=classify(textOf(el));
        if(c===true) sawDemo=true;
        else if(c===false) sawReal=true;
      }
      if(sawDemo&&!sawReal) return accept(true);
      if(sawReal&&!sawDemo) return accept(false);
      return accept(null);
    } catch(e) {
      if(demoConfirmedSticky){
        state.isDemo=true;
        return true;
      }
      state.isDemo=null;
      return null;
    }
  };
  const publishAccountType = (reason='probe') => {
    const v=confirmAccountFromDom();
    post({type:'ACCOUNT_TYPE',isDemo:v,reason});
    return v;
  };
  const startAccountProbe = () => {
    clearInterval(accountProbeTimer);
    publishAccountType('start');
    accountProbeTimer=setInterval(()=>{
      if(!state.started) return;
      publishAccountType('watch');
    },2000);
  };
  const CRYPTO_ALIASES = {
    BTC:['BTC','BITCOIN'], ETH:['ETH','ETHEREUM'], LTC:['LTC','LITECOIN'],
    BCH:['BCH','BITCOINCASH'], XRP:['XRP','RIPPLE'], DOGE:['DOGE','DOGECOIN'],
    ADA:['ADA','CARDANO'], SOL:['SOL','SOLANA'], DOT:['DOT','POLKADOT'],
    BNB:['BNB','BINANCECOIN'], TRX:['TRX','TRON'], AVAX:['AVAX','AVALANCHE'],
    LINK:['LINK','CHAINLINK'], MATIC:['MATIC','POLYGON'], TON:['TON','TONCOIN'],
    USDT:['USDT','TETHER'], USDC:['USDC','USDCOIN'], XLM:['XLM','STELLAR'], ETC:['ETC','ETHEREUMCLASSIC'],
    UNI:['UNI','UNISWAP'], ATOM:['ATOM','COSMOS'], AAVE:['AAVE'], NEAR:['NEAR','NEARPROTOCOL'],
    ICP:['ICP','INTERNETCOMPUTER'], FIL:['FIL','FILECOIN'], SUI:['SUI'], APT:['APT','APTOS'],
    ARB:['ARB','ARBITRUM'], OP:['OP','OPTIMISM'], PEPE:['PEPE'], SHIB:['SHIB','SHIBAINU']
  };
  // V24.1.122: UI chrome words that can sit inside a chart panel (RELOAD button
  // above the asset header, CLOSE, SEARCH, ...) must never be mistaken for an
  // instrument symbol. Exact whole-label hits short-circuit to ''.
  const NON_MARKET_WORDS = new Set([
    'RELOAD','RESET','UPDATE','REFRESH','CANCEL','CLOSE','CLOSED','SEARCH','FILTER',
    'HISTORY','PENDING','TRADE','TRADES','TRADING','SIGNAL','SIGNALS','TIMEFRAME',
    'EXPIRY','AMOUNT','PROFIT','BALANCE','ASSET','ASSETS','MARKET','MARKETS',
    'FAVORITES','FAVOURITE','FAVORITE','SETTINGS','CANDLES','INDICATORS','TEMPLATE',
    'POSITIONS','WATCHLIST','MINIMUM','MAXIMUM','DELETE','CLEAR','APPLY','CONFIRM',
    'CONTINUE','PAUSE','RISK','CLASSIC','NOTIFICATIONS','PROFILE','SUPPORT',
    'RESISTANCE','SESSION','VOLUME','CURRENCY','PAYMENT','DEPOSIT','WITHDRAW',
    'VERIFIED','ORDER','ORDERS','TURBO','SPEED','MODE','DEFAULT','SELECTED','SELECT',
    'ALL','NONE','DAILY','WEEKLY','MONTHLY','TODAY','WEEK','MONTH','YEAR'
  ]);
  // Recognized currency/quote codes used to sanity-check 6-letter concatenated
  // symbols (EURUSD, BTCUSD, GBPJPY...). With this guard, chrome words like
  // RELOAD/SEARCH can no longer be split by the [A-Z]{3}[A-Z]{3} regex into
  // fake symbols because their second half is never a real currency code.
  const CURRENCY_CODES = new Set([
    'USD','EUR','GBP','JPY','AUD','CAD','CHF','NZD','SGD','HKD','RUB','UAH','TRY',
    'BRL','MXN','ZAR','PLN','SEK','NOK','DKK','CZK','HUF','RON','ILS','AED','SAR',
    'KWD','EGP','NGN','KES','INR','PKR','BDT','VND','THB','IDR','MYR','PHP','KRW',
    'CNY','TWD','CLP','ARS','COP','PEN','MUR','GEL','AMD','AZN','KZT','UZS','BGN',
    'MAD','GHS','TZS','UGX','ETB','LKR','NIO','PAB','BOB','CRC','DOP','GTQ','HNL',
    'BHD','OMR','JOD','QAR','LBP','IRR','IQD','AFN','ALL','BAM','BYN','CDF','CUP',
    'DJF','DZD','ERN','FJD','GMD','GNF','GYD','HTG','ISK','JMD','KGS','KHR','KMF',
    'LAK','LRD','LSL','LYD','MDL','MGA','MKD','MNT','MOP','MVR','MWK','MZN','NAD',
    'PGK','PYG','RWF','SBD','SCR','SDG','SLL','SOS','SRD','SSP','SVC','SZL','TJS',
    'TMT','TND','TOP','TTD','UYU','VEF','VES','VUV','WST','XAF','XCD','XOF','XPF',
    'ZMW','ZWL'
  ]);
  function assetAliases(name) {
    const raw=String(name||'').toUpperCase();
    const n=normAsset(raw);
    const out=new Set([n]);
    // Broker symbols are commonly BTCUSD / BTCUSD_otc while the visible header
    // may say BTC/USD, Bitcoin, Bitcoin OTC, Ethereum, etc.
    for (const [code, aliases] of Object.entries(CRYPTO_ALIASES)) {
      if (n.startsWith(code)) aliases.forEach(a=>out.add(normAsset(a)));
    }
    // Also retain the base symbol (BTC from BTCUSD, ETH from ETHUSD, etc.) but
    // only for recognized crypto bases so FX pairs cannot cross-match loosely.
    const cryptoBase=Object.keys(CRYPTO_ALIASES).find(code=>n.startsWith(code));
    if (cryptoBase) out.add(cryptoBase);
    return [...out].filter(Boolean);
  }
  function resolveVisibleChartAsset() {
    if (!knownAssetNames.size) return '';
    const rows = [...knownAssetNames].map(name => ({name, n:normAsset(name), aliases:assetAliases(name)})).filter(x=>x.n);
    const sels = [
      '[data-asset]','[data-symbol]','[data-pair]','[data-instrument]',
      '[class*=current]','[class*=selected]','[class*=active]',
      '[class*=asset]','[class*=symbol]','[class*=pair]','[class*=instrument]'
    ];
    const els = [...document.querySelectorAll(sels.join(','))];
    let best = null;
    for (const el of els) {
      if (!visibleEl(el)) continue;
      const cls = String(el.className || '').toLowerCase();
      const attrs = [el.getAttribute('data-asset'),el.getAttribute('data-symbol'),el.getAttribute('data-pair'),el.getAttribute('data-instrument')].filter(Boolean);
      const txt = String(el.textContent || '').trim();
      // Asset menus can contain hundreds of pairs.  Ignore large containers so
      // only the selected/current instrument label is eligible.
      if (txt.length > 48 && !attrs.length) continue;
      const bagN = normAsset([...attrs,txt].join(' '));
      if (!bagN) continue;
      for (const row of rows) {
        const exactAlias=row.aliases.find(a=>a.length>=3 && (normAsset(txt)===a || attrs.some(v=>normAsset(v)===a)));
        const containedAlias=row.aliases.find(a=>a.length>=3 && bagN.includes(a));
        if (!exactAlias && !containedAlias) continue;
        let score = 0;
        if (attrs.some(a => normAsset(a) === row.n)) score += 12;
        if (normAsset(txt) === row.n) score += 10;
        else if (bagN.includes(row.n)) score += 4;
        // V24.1.110: crypto headers often use the coin name rather than the
        // broker wire symbol (Bitcoin vs BTCUSD_otc). Give exact aliases enough
        // weight to satisfy the same visible-chart safety threshold.
        if (exactAlias && exactAlias !== row.n) score += 11;
        else if (containedAlias && containedAlias !== row.n) score += 7;
        if (/selected|current|active|chosen|opened/.test(cls)) score += 8;
        if (el.getAttribute('aria-selected') === 'true') score += 12;
        if (el.getAttribute('aria-current') === 'true') score += 12;
        // Prefer compact labels near the top/chart header over rows in long lists.
        const r = el.getBoundingClientRect();
        if (r.width < 420 && r.height < 100) score += 3;
        if (!best || score > best.score) best = {asset:row.name, score};
      }
    }
    return best && best.score >= 10 ? best.asset : '';
  }
  function publishResolvedChartAsset(source='dom') {
    const asset = resolveVisibleChartAsset();
    if (!asset) return false;
    if (state.chartAsset !== asset) state.chartAsset = asset;
    post({type:'CHART_ASSET', asset, source});
    return true;
  }
  function startChartResolutionBurst() {
    clearInterval(chartResolveTimer);
    let tries = 0;
    publishResolvedChartAsset('dom-start');
    chartResolveTimer = setInterval(() => {
      tries++;
      if (publishResolvedChartAsset('dom-retry') || tries >= 12) {
        clearInterval(chartResolveTimer);
        chartResolveTimer = null;
      }
    }, 400);
  }


  // V120 — Pocket Option can show four independent chart panels at once. Discover
  // each panel and bind its visible instrument to that panel's own BUY/SELL buttons.
  // This lets open positions overlap without relying on one global chartAsset.
  let chartSlotsTimer = null;
  function canonicalAssetFromVisibleLabel(text) {
    const raw=String(text||'').toUpperCase().replace(/\u00A0/g,' ').replace(/[\n\r\t]+/g,' ');
    const whole=raw.trim().replace(/[^A-Z0-9]/g,'');
    if (!whole) return '';
    // V24.1.122: a label that is ONLY chrome text (RELOAD, RESET, HISTORY, ...)
    // is never an instrument. Previously RELOAD sailed through the 6-letter
    // regex below and became a fake slot asset that could never warm up.
    if (NON_MARKET_WORDS.has(whole)) return '';

    // First reconcile against symbols already observed on Pocket Option's socket.
    const bag=normAsset(raw);
    let best=''; let bestScore=-1;
    for (const name of knownAssetNames) {
      const nn=normAsset(name), baseNoOtc=nn.replace(/OTC$/,'');
      for (const a0 of assetAliases(name)) {
        const a=normAsset(a0); if (a.length<3) continue;
        let score=-1;
        if (bag===a) score=120+a.length;
        else if (bag.includes(a)) score=80+a.length;
        else if (a.includes(bag) && bag.length>=5) score=45+bag.length;
        if (score>bestScore) { best=name; bestScore=score; }
      }
      if (baseNoOtc && baseNoOtc.length>=5 && bag.includes(baseNoOtc)) {
        const score=92+baseNoOtc.length;
        if (score>bestScore) { best=name; bestScore=score; }
      }
    }
    if (bestScore>=0) return best;

    // V121.5: DOM discovery must not depend on a socket asset having arrived first.
    // Convert visible chart labels like "AUD/CAD OTC" directly to the broker symbol.
    const otc=/\bOTC\b/.test(raw);
    // V24.1.122: both halves of a parsed pair must be plausible money codes.
    // Chrome words (RELOAD→REL/OAD, SEARCH→SEA/RCH, CALL/PUT) can no longer be
    // forged into symbols by the raw 6-letter split.
    let m=raw.match(/\b([A-Z]{3})\s*[\/\-]\s*([A-Z]{3})\b/);
    if (m) {
      const baseOk=CURRENCY_CODES.has(m[1]) || Object.prototype.hasOwnProperty.call(CRYPTO_ALIASES,m[1]);
      const quoteOk=CURRENCY_CODES.has(m[2]);
      if (baseOk && quoteOk) return `${m[1]}${m[2]}${otc?'_otc':''}`;
      m=null;
    }
    if (!m) m=raw.match(/\b([A-Z]{3})([A-Z]{3})\b/);
    if (m) {
      const baseOk=CURRENCY_CODES.has(m[1]) || Object.prototype.hasOwnProperty.call(CRYPTO_ALIASES,m[1]);
      const quoteOk=CURRENCY_CODES.has(m[2]);
      if (baseOk && quoteOk) return `${m[1]}${m[2]}${otc?'_otc':''}`;
    }

    const crypto=[
      ['BITCOIN','BTCUSD'],['BTC','BTCUSD'],['ETHEREUM','ETHUSD'],['ETH','ETHUSD'],
      ['DOGECOIN','DOGEUSD'],['DOGE','DOGEUSD'],['LITECOIN','LTCUSD'],['LTC','LTCUSD'],
      ['TONCOIN','TONUSD'],['TON','TONUSD'],['SOLANA','SOLUSD'],['SOL','SOLUSD'],
      ['CARDANO','ADAUSD'],['ADA','ADAUSD'],['RIPPLE','XRPUSD'],['XRP','XRPUSD'],
      ['BNB','BNBUSD'],['TRON','TRXUSD'],['TRX','TRXUSD'],['POLKADOT','DOTUSD'],['DOT','DOTUSD'],
      ['AVALANCHE','AVAXUSD'],['AVAX','AVAXUSD'],['CHAINLINK','LINKUSD'],['LINK','LINKUSD'],
      ['POLYGON','MATICUSD'],['MATIC','MATICUSD'],['POL','POLUSD'],['STELLAR','XLMUSD'],['XLM','XLMUSD'],
      ['ETHEREUM CLASSIC','ETCUSD'],['ETC','ETCUSD'],['UNISWAP','UNIUSD'],['UNI','UNIUSD'],
      ['COSMOS','ATOMUSD'],['ATOM','ATOMUSD'],['AAVE','AAVEUSD'],['NEAR PROTOCOL','NEARUSD'],['NEAR','NEARUSD'],
      ['INTERNET COMPUTER','ICPUSD'],['ICP','ICPUSD'],['FILECOIN','FILUSD'],['FIL','FILUSD'],
      ['SUI','SUIUSD'],['APTOS','APTUSD'],['APT','APTUSD'],['ARBITRUM','ARBUSD'],['ARB','ARBUSD'],
      ['OPTIMISM','OPUSD'],['OP','OPUSD'],['SHIBA INU','SHIBUSD'],['SHIB','SHIBUSD'],['PEPE','PEPEUSD']
    ];
    for (const [label,symbol] of crypto) {
      if (new RegExp(`\\b${label}\\b`).test(raw)) return `${symbol}${otc?'_otc':''}`;
    }
    return '';
  }
  function assetFromPanelText(text) { return canonicalAssetFromVisibleLabel(text); }
  // V24.1.122: rank how strongly a DOM element really announces its instrument.
  // The old code returned the FIRST compact element that mapped to anything, so
  // a RELOAD button or a stray BTC/GBP chip sorted before the asset header and
  // hijacked the slot. Scoring every candidate picks the true header instead.
  function labelMatchScore(text, mapped) {
    const txt=String(text||'').trim();
    const bag=normAsset(txt);
    if (!bag) return -1;
    const nN=normAsset(mapped);
    let s=0;
    // B32.20.8: the V122 socket bonus used to be +500, which made a stale
    // subscribed symbol beat the market name visibly shown in this chart slot.
    // Socket presence is useful corroboration, never chart identity authority.
    if ([...knownAssetNames].some(n=>normAsset(n)===nN)) s+=25;
    if (/\bOTC\b/i.test(txt)) s+=180;                               // visible OTC header is strong evidence
    s+=Math.max(0, 34-bag.length);
    if (bag===nN) s+=140;
    else if (bag.endsWith(nN)||bag.startsWith(nN)) s+=45;
    // Human-facing instrument names are normally the actual Pocket Option header.
    if (/\b(BITCOIN|ETHEREUM|DOGECOIN|LITECOIN|AVALANCHE|SOLANA|CARDANO|POLKADOT|CHAINLINK|TONCOIN|TRON)\b/i.test(txt)) s+=120;
    return s;
  }
  function assetFromPanel(root) {
    if (!root) return '';
    const scored=[];
    const seen=new Set();
    const pushScore=(txt,el,extra)=>{
      const t=String(txt||'').trim(); if (!t) return;
      const mapped=canonicalAssetFromVisibleLabel(t); if (!mapped) return;
      const key=normAsset(t)+'|'+mapped; if (seen.has(key)) return; seen.add(key);
      const r=el?.getBoundingClientRect?.();
      scored.push({asset:mapped, score:labelMatchScore(t,mapped)+(extra||0), top:r?r.top:0, left:r?r.left:0});
    };
    const attrEls=[root,...root.querySelectorAll('[data-asset],[data-symbol],[data-pair],[data-instrument],[data-current-symbol]')];
    for (const el of attrEls) {
      for (const k of ['data-asset','data-symbol','data-pair','data-instrument','data-current-symbol']) {
        const v=el.getAttribute?.(k); if (!v) continue;
        pushScore(v, el, 70);
      }
    }
    const els=[root,...root.querySelectorAll('button,[role="button"],span,div')].filter(visibleEl);
    const compact=els.filter(el=>{
      const r=el.getBoundingClientRect(); const t=String(el.textContent||'').trim();
      return r.width>18 && r.width<360 && r.height>8 && r.height<90 && t.length>=3 && t.length<=70;
    });
    for (const el of compact.slice(0,160)) pushScore(el.textContent, el, 0);
    if (!scored.length) return canonicalAssetFromVisibleLabel(String(root.textContent||''));
    scored.sort((a,b)=>(b.score-a.score)||(a.top-b.top)||(a.left-b.left));
    return scored[0].asset;
  }
  // V24.1.122: if a panel's discovered asset is not a symbol the socket has
  // confirmed live (knownAssetNames), re-match the panel's full text against the
  // aliases of every known streaming asset. This is what repairs slots whose
  // header chip was misread or was missing when the DOM was first scanned — the
  // 1200ms grid watch re-publishes as soon as the real names arrive.
  // V24.1.122c: the asset HEADER (e.g. "Bitcoin OTC") may live on an ANCESTOR
  // of the discovered panel element, not on the panel.el itself. discoverChartPanels
  // can return a compact BUY/SELL or canvas container that omits the header text,
  // so a Bitcoin panel could be left bound to a stray chip label (BTCGBP) forever.
  // Walk up the ancestor chain to gather the full panel chrome before deducing asset.
  function panelFullText(panel) {
    try {
      const parts=[]; let el=panel?.el;
      for (let up=0; el && up<6; up++, el=el.parentElement) {
        const t=String(el.textContent||'').trim(); if (t) parts.push(t);
        const r=el.getBoundingClientRect?.();
        if (!r || r.width>window.innerWidth*0.9 || r.height>window.innerHeight*0.9) break;
      }
      return parts.join(' ');
    } catch(e) { return String(panel?.el?.textContent||''); }
  }
  function resolvePanelAssetToKnown(panel) {
    if (!panel) return '';
    // B32.20.9: slot identity is LOCAL to the discovered chart container.
    // Never walk ancestors that can span neighboring charts; that was the root
    // cause of a 2x2 grid collapsing onto one readable AUD/CNY header.
    const local=assetFromPanel(panel.el);
    return String(local || panel.asset || '').trim();
  }
  // V24.1.122d: bind panels to the symbols truly streaming this session.
  // When a slot's discovered label is NOT a live asset (e.g. a DOM chip like
  // "BTCGBP", or a missing header), assign it the live-stream symbol that no
  // other panel already claimed.  Live stream channels are authoritative, so
  // this repairs any panel whose header text is unrecognizable — it can only
  // touch a slot whose current asset is not actually streaming, and it never
  // overwrites a working slot.
  function bindPanelsToLive(panels) {
    if (!Array.isArray(panels)) return panels;
    const recent=recentLiveStreamAssets(6000); if(!recent.length)return panels;
    const seen=new Set(),live=[]; for(const name of recent){const n=normAsset(name);if(n.length<3||seen.has(n))continue;seen.add(n);live.push({name,n});}
    if(!live.length)return panels; const hasLive=(p)=>{const n=normAsset(p.asset);return !!n&&seen.has(n);};
    // B32.20.8: an `_otc` suffix does NOT prove a DOM guess is the selected
    // chart. Only a recent live match is corroboration; otherwise leave the
    // visible-label resolver in charge instead of preserving a stale OTC symbol.
    const broken=panels.filter(p=>!hasLive(p)); if(!broken.length)return panels;
    const claimed=new Set(); for(const p of panels){const n=normAsset(p.asset);if(hasLive(p)&&n)claimed.add(n);}
    const unclaimed=live.filter(x=>!claimed.has(x.n));
    // Only positional-fill when the mapping is unambiguous. Never overwrite a
    // readable visible label just because extra background subscriptions exist.
    if(broken.length!==unclaimed.length)return panels;
    let bi=0; for(const p of panels){if(hasLive(p))continue; const vis=canonicalAssetFromVisibleLabel(panelFullText(p)); p.asset=vis||unclaimed[bi++].name;} return panels;
  }
  function isBuyButton(el) {
    const c=String(el?.className||'').toLowerCase(), t=String(el?.textContent||'').trim().toUpperCase();
    return c.includes('btn-call')||c.includes('btn-green-light')||c.includes('btn-higher')||t==='BUY'||t==='CALL'||t==='HIGHER'||(/BUY|CALL|HIGHER/.test(t)&&t.length<40);
  }
  function isSellButton(el) {
    const c=String(el?.className||'').toLowerCase(), t=String(el?.textContent||'').trim().toUpperCase();
    return c.includes('btn-put')||c.includes('btn-red')||c.includes('btn-lower')||t==='SELL'||t==='PUT'||t==='LOWER'||(/SELL|PUT|LOWER/.test(t)&&t.length<40);
  }
  function panelButtons(root) {
    const all=[...root.querySelectorAll('button,[role="button"]')].filter(visibleEl);
    return {buy:all.find(isBuyButton)||null,sell:all.find(isSellButton)||null};
  }
  function discoverChartPanels() {
    const candidates=[];
    const seenRoots=new Set();

    // Path A: trade controls, for layouts where each chart owns BUY/SELL buttons.
    const buyCandidates=[...document.querySelectorAll('.btn-call,.btn-green-light,.btn-higher,button,[role="button"]')].filter(visibleEl).filter(isBuyButton);
    for (const buy of buyCandidates) {
      let cur=buy;
      for (let up=0;up<20&&cur?.parentElement;up++,cur=cur.parentElement) {
        const r=cur.getBoundingClientRect?.(); if (!r||r.width<150||r.height<110) continue;
        const pb=panelButtons(cur); if (!pb.buy||!pb.sell) continue;
        const asset=assetFromPanel(cur); if (!asset) continue;
        candidates.push({el:cur,asset,rect:r,area:r.width*r.height,source:'buttons'}); break;
      }
    }

    // Path B: chart canvases/SVGs. Pocket Option's 4-chart layout can render chart
    // controls differently, so do not require BUY/SELL buttons just to detect slots.
    const visualNodes=[...document.querySelectorAll('canvas,svg,[class*="chart"],[class*="Chart"]')].filter(visibleEl);
    for (const node of visualNodes) {
      const nr=node.getBoundingClientRect?.();
      if (!nr||nr.width<180||nr.height<90) continue;
      let cur=node;
      for (let up=0;up<14&&cur?.parentElement;up++,cur=cur.parentElement) {
        const r=cur.getBoundingClientRect?.();
        if (!r||r.width<220||r.height<130||r.width>window.innerWidth*0.98||r.height>window.innerHeight*0.98) continue;
        const asset=assetFromPanel(cur); if (!asset) continue;
        const key=`${Math.round(r.left/20)}:${Math.round(r.top/20)}:${asset}`;
        if (!seenRoots.has(key)) {
          seenRoots.add(key); candidates.push({el:cur,asset,rect:r,area:r.width*r.height,source:'chart'});
        }
        break;
      }
    }

    // Path C: compact visible instrument labels themselves. This is the final
    // fallback and is independent of WebSocket timing.
    const labelNodes=[...document.querySelectorAll('[data-asset],[data-symbol],[data-pair],[data-instrument],[class*="asset"],[class*="symbol"],[class*="pair"]')].filter(visibleEl);
    for (const label of labelNodes) {
      const asset=assetFromPanelText(label.getAttribute?.('data-asset')||label.getAttribute?.('data-symbol')||label.getAttribute?.('data-pair')||label.getAttribute?.('data-instrument')||label.textContent);
      if (!asset) continue;
      let cur=label;
      for (let up=0;up<14&&cur?.parentElement;up++,cur=cur.parentElement) {
        const r=cur.getBoundingClientRect?.(); if (!r||r.width<220||r.height<130||r.width>window.innerWidth*0.98||r.height>window.innerHeight*0.98) continue;
        candidates.push({el:cur,asset,rect:r,area:r.width*r.height,source:'label'}); break;
      }
    }

    // B32.20.9 Path D: direct compact instrument-header anchors. Pocket Option's
    // multi-chart layout can use different wrapper classes per slot, so scan all
    // compact visible text nodes and promote each instrument header to its nearest
    // chart-sized ancestor. This is DOM-local and does not depend on socket order.
    const allCompact=[...document.querySelectorAll('span,button,[role="button"],[role="tab"],div')].filter(visibleEl);
    for (const label of allCompact) {
      const lr=label.getBoundingClientRect?.(); const txt=String(label.textContent||'').trim();
      if(!lr||lr.width<18||lr.width>360||lr.height<8||lr.height>80||txt.length<3||txt.length>48) continue;
      const asset=canonicalAssetFromVisibleLabel(txt); if(!asset) continue;
      let cur=label, chosen=null;
      for(let up=0;up<12&&cur?.parentElement;up++,cur=cur.parentElement){
        const r=cur.getBoundingClientRect?.();
        if(!r) continue;
        if(r.width>=220&&r.height>=130&&r.width<=window.innerWidth*0.72&&r.height<=window.innerHeight*0.72){chosen={el:cur,rect:r};break;}
      }
      if(chosen) candidates.push({el:chosen.el,asset,rect:chosen.rect,area:chosen.rect.width*chosen.rect.height,source:'header-anchor'});
    }

    const uniq=[];
    for (const c of candidates.sort((a,b)=>{
      const ap=a.source==='header-anchor'?0:1, bp=b.source==='header-anchor'?0:1;
      return (ap-bp)||(a.area-b.area);
    })) {
      // Same physical chart slot, regardless of which descendant discovered it.
      // Compare centers, not ancestor top-lefts: nested wrappers from neighboring
      // charts can share edges while their chart centers remain distinct.
      const cx=c.rect.left+c.rect.width/2, cy=c.rect.top+c.rect.height/2;
      if (uniq.some(u=>{const ux=u.rect.left+u.rect.width/2,uy=u.rect.top+u.rect.height/2;return Math.abs(ux-cx)<120&&Math.abs(uy-cy)<90;})) continue;
      uniq.push(c);
    }
    uniq.sort((a,b)=>(a.rect.top-b.rect.top)||(a.rect.left-b.rect.left));
    return uniq.slice(0,4).map((c,i)=>({...c,slotId:`slot-${i+1}`}));
  }
  // V240 VISUAL CHART BACKFILL FALLBACK
  // If the initial Pocket Option history packet was missed, inspect the backing
  // data attached to the *visible chart DOM* (React/Vue/chart instances). This
  // reads chart data, not pixels. It is intentionally bounded and read-only.
  const visualBackfillDone = new Set();
  function v240CandleRecord(x){
    try{
      if(Array.isArray(x)){
        if(x.length>=5 && Number.isFinite(Number(x[0])) && [x[1],x[2],x[3],x[4]].every(v=>Number.isFinite(Number(v))))
          return {kind:'ohlc',time:Number(x[0]),open:Number(x[1]),high:Number(x[2]),low:Number(x[3]),close:Number(x[4])};
        if(x.length>=2 && Number.isFinite(Number(x[0])) && Number.isFinite(Number(x[1])))
          return {kind:'tick',time:Number(x[0]),price:Number(x[1])};
      } else if(x && typeof x==='object'){
        const tm=x.time??x.t??x.timestamp??x.ts??x.datetime;
        const o=x.open??x.o, h=x.high??x.h, l=x.low??x.l, c=x.close??x.c??x.value;
        if(tm!=null && [o,h,l,c].every(v=>Number.isFinite(Number(v))))
          return {kind:'ohlc',time:Number(tm),open:Number(o),high:Number(h),low:Number(l),close:Number(c)};
        const px=x.price??x.p??x.value??x.close??x.c;
        if(tm!=null && Number.isFinite(Number(px))) return {kind:'tick',time:Number(tm),price:Number(px)};
      }
    }catch(_){}
    return null;
  }
  function v240FindSeries(root){
    const seen=new WeakSet(), found=[];
    function walk(v,depth){
      if(!v || depth>6 || (typeof v!=='object' && !Array.isArray(v))) return;
      if(typeof v==='object'){ if(seen.has(v)) return; seen.add(v); }
      if(Array.isArray(v)){
        if(v.length>=12){
          const sample=v.slice(Math.max(0,v.length-40)).map(v240CandleRecord).filter(Boolean);
          if(sample.length>=Math.min(10,Math.floor(Math.min(v.length,40)*0.6))){
            const all=v.map(v240CandleRecord).filter(Boolean);
            if(all.length>=12) found.push(all);
          }
        }
        if(depth<4) for(let i=Math.max(0,v.length-8);i<v.length;i++) walk(v[i],depth+1);
        return;
      }
      let keys=[]; try{ keys=Object.keys(v); }catch(_){return;}
      const preferred=keys.filter(k=>/candle|history|series|data|bars|ticks|points|chart/i.test(k)).slice(0,30);
      for(const k of preferred){ try{ walk(v[k],depth+1); }catch(_){} }
    }
    walk(root,0);
    found.sort((a,b)=>b.length-a.length);
    return found[0]||null;
  }
  function v240VisualBackfillProbe(){
    // B32: chart-history capture is independent of trading START/STOP.
    try{
      const panels=discoverChartPanels();
      for(const panel of panels){
        const asset=String(resolvePanelAssetToKnown(panel)||panel.asset||'').trim();
        if(!asset || visualBackfillDone.has(asset)) continue;
        const roots=[panel.el];
        // React/Vue/chart libraries commonly keep the rendered series on private
        // element properties. Inspect only properties of this visible chart tree.
        for(const el of [panel.el,...panel.el.querySelectorAll('canvas,svg,[class*="chart"],[class*="Chart"]')].slice(0,12)){
          try{
            for(const k of Object.getOwnPropertyNames(el)){
              if(/^__react|^__vue|chart|series|data/i.test(k)) roots.push(el[k]);
            }
          }catch(_){}
        }
        let best=null;
        for(const r of roots){ const x=v240FindSeries(r); if(x && (!best||x.length>best.length)) best=x; }
        if(best && best.length>=12){
          visualBackfillDone.add(asset);
          post({type:'HISTORY_BACKFILL',asset,records:best.slice(-6000),source:'visible-chart-data'});
          post({type:'VISUAL_BACKFILL_STATUS',asset,records:best.length,status:'FOUND'});
        }
      }
    }catch(e){}
  }
  // KAOS 1.6.41 PERFORMANCE: deep React/chart-history inspection is expensive.
  // Run it slowly, only while the tab is visible, and stop once all visible slots
  // have been backfilled. Live WebSocket history remains the primary source.
  let v240BackfillTimer=setInterval(()=>{
    if(document.hidden)return;
    if(visualBackfillDone.size>=4){clearInterval(v240BackfillTimer);v240BackfillTimer=null;return;}
    v240VisualBackfillProbe();
  },8000);
  setTimeout(()=>{try{if(v240BackfillTimer){clearInterval(v240BackfillTimer);v240BackfillTimer=null;}}catch(_){}},120000);

  function readSentimentFromRoot(root){
    // B12: Pocket Option has used several sentiment DOM layouts. Do not depend
    // on one class name: scan the panel (and open shadow roots), then accept a
    // BUY/SELL percentage pair only when the two values form ~100%.
    try{
      const roots=[];
      const seenRoots=new Set();
      const addRoot=(r)=>{if(!r||seenRoots.has(r))return;seenRoots.add(r);roots.push(r);try{for(const el of r.querySelectorAll?.('*')||[]){if(el.shadowRoot)addRoot(el.shadowRoot);}}catch(_){}};
      addRoot(root);
      const nums=(txt)=>(String(txt||'').match(/\d{1,3}(?:\.\d+)?\s*%/g)||[]).map(v=>Number(v.replace(/[^\d.]/g,''))).filter(v=>Number.isFinite(v)&&v>=0&&v<=100);
      const pair=(vals)=>{for(let i=0;i<vals.length;i++)for(let j=i+1;j<vals.length;j++){if(Math.abs(vals[i]+vals[j]-100)<=2)return [vals[i],vals[j]];}return null;};
      const labeled=(txt)=>{
        txt=String(txt||'').replace(/\s+/g,' ');
        const get=(labels)=>{const m=txt.match(new RegExp('(?:'+labels+')[^%]{0,80}(\\d{1,3}(?:\\.\\d+)?)\\s*%','i'));return m?Number(m[1]):null;};
        const buy=get('BUY|CALL|HIGHER|UP'), sell=get('SELL|PUT|LOWER|DOWN');
        if(Number.isFinite(buy)&&Number.isFinite(sell)&&Math.abs(buy+sell-100)<=3)return {buy,sell,source:'bridge-labeled'};
        return null;
      };
      for(const r of roots){
        const whole=(r.innerText||r.textContent||'');
        let hit=labeled(whole); if(hit)return hit;
        const selectors='[class*="sentiment" i],[data-test*="sentiment" i],[data-testid*="sentiment" i],[aria-label*="sentiment" i],[title*="sentiment" i],[class*="mood" i],[class*="percent" i],[class*="ratio" i]';
        for(const el of r.querySelectorAll?.(selectors)||[]){
          if(!visibleEl(el))continue;
          const txt=(el.innerText||el.textContent||'')+' '+(el.getAttribute?.('aria-label')||'')+' '+(el.getAttribute?.('title')||'');
          hit=labeled(txt); if(hit)return hit;
          const pr=pair(nums(txt)); if(pr)return {buy:pr[0],sell:pr[1],source:'bridge-widget-pair'};
        }
        // Generic panel fallback. Pocket Option sometimes renders the two values
        // in anonymous spans next to the CALL/PUT controls with no sentiment class.
        const pctEls=[...(r.querySelectorAll?.('span,div,b,strong,p')||[])].filter(el=>{
          if(!visibleEl(el))return false; const t=String(el.textContent||'').trim();
          const rc=el.getBoundingClientRect?.(); return /^\d{1,3}(?:\.\d+)?\s*%$/.test(t)&&(!rc||rc.width<180&&rc.height<80);
        });
        const vals=pctEls.map(el=>({el,v:Number(String(el.textContent).replace(/[^\d.]/g,''))})).filter(x=>Number.isFinite(x.v));
        let best=null,bestDist=Infinity;
        for(let i=0;i<vals.length;i++)for(let j=i+1;j<vals.length;j++){
          if(Math.abs(vals[i].v+vals[j].v-100)>2)continue;
          const a=vals[i].el.getBoundingClientRect(),b=vals[j].el.getBoundingClientRect();
          const d=Math.hypot((a.left+a.width/2)-(b.left+b.width/2),(a.top+a.height/2)-(b.top+b.height/2));
          if(d<bestDist){bestDist=d;best=[vals[i],vals[j]];}
        }
        if(best){
          // DOM order on PO is normally BUY then SELL. If nearby text labels make
          // direction explicit, honor them; otherwise preserve that order.
          const parentText=String(best[0].el.parentElement?.textContent||'')+' '+String(best[1].el.parentElement?.textContent||'');
          hit=labeled(parentText); if(hit)return hit;
          return {buy:best[0].v,sell:best[1].v,source:'bridge-panel-percent-pair'};
        }
      }
    }catch(_){ }
    return null;
  }
  function publishChartSentiment(){
    if(!state.started)return;
    try{
      let panels=discoverChartPanels().map(p=>({...p,asset:resolvePanelAssetToKnown(p)})); panels=bindPanelsToLive(panels);
      const rows=[];
      for(const p of panels){let r=readSentimentFromRoot(p.el);if(!r){let node=p.el.parentElement;for(let up=0;node&&up<3&&!r;up++,node=node.parentElement)r=readSentimentFromRoot(node);}if(r&&p.asset)rows.push({slotId:p.slotId,asset:p.asset,buy:r.buy,sell:r.sell,source:r.source,t:Date.now()});}
      // Single global sentiment widget fallback: bind only to the currently selected/first chart, never fabricate for all four.
      if(!rows.length){const body=readSentimentFromRoot(document.body);const first=panels[0];if(body&&first?.asset)rows.push({slotId:first.slotId,asset:first.asset,buy:body.buy,sell:body.sell,source:'bridge-global-visible',t:Date.now()});}
      post({type:'CHART_SENTIMENT',rows,t:Date.now()});
    }catch(_){}
  }
  function publishChartSlots(source='dom-grid') {
    // V24.1.122: re-bind each discovered panel to a socket-confirmed symbol when
    // the raw DOM read was garbage or missing (RELOAD, BTCGBP from UI chips).
    let panels=discoverChartPanels().map(p=>({...p, asset:resolvePanelAssetToKnown(p)}));
    panels=bindPanelsToLive(panels);
    const slots=panels.map(p=>({slotId:p.slotId,asset:p.asset,left:Math.round(p.rect.left),top:Math.round(p.rect.top)}));
    state.chartSlots=Object.create(null);
    for (const row of slots) state.chartSlots[row.slotId]=row.asset;
    if (slots[0]?.asset) state.chartAsset=slots[0].asset;
    post({type:'CHART_SLOTS',slots,source});
    return slots;
  }
  function startChartSlotsWatch() {
    clearInterval(chartSlotsTimer);
    publishChartSlots('grid-start'); publishChartSentiment();
    // KAOS 1.6.41 PERFORMANCE: DOM grid discovery walks a large Pocket Option tree.
    // 3s is fast enough for chart/asset changes without forcing layout every 1.2s.
    let sentimentBeat=0;
    chartSlotsTimer=setInterval(()=>{
      if(!state.started||document.hidden)return;
      publishChartSlots('grid-watch');
      if((++sentimentBeat%2)===0) publishChartSentiment();
    },3000);
  }
  function findPanelBySlot(slotId, asset='') {
    const panels=discoverChartPanels();
    if (slotId) {
      const p=panels.find(x=>x.slotId===slotId);
      if (p) return p;
    }
    if (asset) return panels.find(x=>x.asset===asset)||null;
    return null;
  }
  function clickPanelAssetMenu(panel) {
    if (!panel?.el) return false;
    const els=[...panel.el.querySelectorAll('button,[role="button"],div,span')].filter(visibleEl);
    const compact=els.filter(el=>{const r=el.getBoundingClientRect(); const txt=String(el.textContent||'').trim(); return r.width<260&&r.height<70&&txt.length>1&&txt.length<48&&!!assetFromPanelText(txt);});
    if (compact.length) { compact.sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top); compact[0].click(); return true; }
    return false;
  }

  // V119 — resolve the markets starred by the user. Primary path reads active
  // star/favorite controls already in the DOM; fallback opens the asset selector,
  // chooses the Favorites tab, maps visible rows back to broker wire symbols, then
  // closes the selector. This is read-only discovery; it never changes favorites.
  function mapTextToKnownAssets(text) {
    const bag=normAsset(text);
    if (!bag) return [];
    const out=[];
    for (const name of knownAssetNames) {
      const aliases=assetAliases(name);
      if (aliases.some(a=>a.length>=3 && bag.includes(a))) out.push(name);
    }
    return out;
  }

  function activeFavoriteControl(el) {
    if (!el) return false;
    const bag=[el.className,el.getAttribute?.('aria-label'),el.getAttribute?.('title'),el.getAttribute?.('data-state')].filter(Boolean).join(' ').toLowerCase();
    if (el.getAttribute?.('aria-pressed')==='true' || el.getAttribute?.('aria-checked')==='true') return true;
    if (/unfavorite|remove.{0,12}favorite|remove.{0,12}favourite/.test(bag)) return true;
    if (/(^|\s|[-_])(active|selected|checked|on|filled|fill)(\s|$|[-_])/.test(bag)) return true;
    return false;
  }

  function scanActiveStarFavorites() {
    const found=new Set();
    const stars=[...document.querySelectorAll('[class*=favorite],[class*=favourite],[class*=star],[aria-label*=favorite i],[aria-label*=favourite i],[title*=favorite i],[title*=favourite i]')];
    for (const star of stars) {
      if (!activeFavoriteControl(star)) continue;
      let row=star;
      for (let up=0;up<6 && row;up++,row=row.parentElement) {
        const txt=String(row.textContent||'').trim();
        if (!txt || txt.length>180) continue;
        const matches=mapTextToKnownAssets(txt);
        if (matches.length===1) { found.add(matches[0]); break; }
      }
    }
    return [...found];
  }

  function findAssetMenuToggle() {
    const sels=['[class*=current-symbol]','[class*=current-asset]','[class*=current-pair]','[class*=asset-select]','[class*=symbol-select]','[class*=pair-select]'];
    for (const sel of sels) {
      const el=[...document.querySelectorAll(sel)].find(visibleEl);
      if (el) return el;
    }
    const c=[...document.querySelectorAll('button,[role=button],div,span')].filter(visibleEl)
      .filter(el=>/[A-Z]{3}\s*\/\s*[A-Z]{3}/.test(String(el.textContent||'')))
      .filter(el=>{const r=el.getBoundingClientRect(); return r.width<420&&r.height<120;});
    return c[0]||null;
  }

  function scanVisibleFavoriteRows(root=document) {
    const found=new Set();
    const rows=[...root.querySelectorAll('li,[role=option],[role=row],button,[class*=asset],[class*=pair],[class*=symbol],[class*=instrument]')].filter(visibleEl);
    for (const row of rows) {
      const txt=String(row.textContent||'').trim();
      if (!txt || txt.length>180) continue;
      const matches=mapTextToKnownAssets(txt);
      if (matches.length===1) found.add(matches[0]);
    }
    return [...found];
  }

  function syncFavorites(reason='manual') {
    const direct=scanActiveStarFavorites();
    // A closed selector may expose only the current row's star. Treat 2+ direct
    // matches as a complete list; otherwise open the Favorites view to avoid a
    // false one-market sync.
    if (direct.length>=2) { post({type:'FAVORITES',assets:direct,source:'active-stars',reason}); return; }
    const toggle=findAssetMenuToggle();
    if (!toggle) { post({type:'FAVORITES',assets:[],source:'menu-not-found',reason}); return; }
    toggle.click();
    setTimeout(()=>{
      const favTab=[...document.querySelectorAll('button,[role=tab],[role=button],div,span')].filter(visibleEl)
        .find(el=>/^\s*(favorites?|favourites?)\s*$/i.test(String(el.textContent||'')));
      if (favTab) favTab.click();
      setTimeout(()=>{
        let root=document;
        if (favTab) {
          let cur=favTab;
          for(let up=0;up<7&&cur;up++,cur=cur.parentElement){
            const r=cur.getBoundingClientRect?.();
            const txt=String(cur.textContent||'');
            if(r&&r.width>240&&r.height>180&&txt.length<5000){ root=cur; }
          }
        }
        let assets=scanVisibleFavoriteRows(root);
        if(!assets.length&&direct.length) assets=direct;
        post({type:'FAVORITES',assets,source:favTab?'favorites-tab':'selector-visible',reason});
        try { document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true})); } catch(e) {}
      },220);
    },220);
  }

  window.addEventListener('message', (ev) => {
    // V276.1: only accept bridge commands posted by THIS window. Before, an
    // injected iframe / cross-frame script could drive START / PLACE_TRADE with
    // arbitrary asset, direction and amount. (A same-origin page script still has
    // DOM-level click access by design — this closes the cross-frame vector.)
    if (ev.source && ev.source !== window) return;
    if (!ev.data || !ev.data._poatCmd) return;
    const cmd = ev.data;


    // KAOS 1.1.27 — READ-ONLY MARKET DATA PROBE
    // The charts must work as soon as Pocket Option is open; the user should not
    // have to press START BOT just to establish chartAsset/history.
    if (cmd.type === 'MARKET_DATA_PROBE') {
      try {
        publishResolvedChartAsset('ui-probe');
        if (state.multiAsset) {
          try { publishChartSlots('ui-probe'); } catch(_) {}
        }
        try { requestVisibleHistoryBurst(); } catch(_) {}
        const assets=new Set();
        if(state.chartAsset) assets.add(state.chartAsset);
        for(const a of Object.values(state.chartSlots||{})) if(a) assets.add(a);
        for(const a of recentLiveStreamAssets(30000)) assets.add(a);
        for(const a of assets) {
          try { requestPrevious200(a,true); } catch(_) {}
        }
        post({type:'MARKET_DATA_PROBE_ACK',asset:state.chartAsset||'',assets:[...assets],at:Date.now()});
      } catch(e) {
        post({type:'MARKET_DATA_PROBE_ACK',asset:state.chartAsset||'',assets:[],error:String(e&&e.message||e),at:Date.now()});
      }
    }

    if (cmd.type === 'START') {
      state.started     = true;
      liveStreamAssets.clear(); liveStreamLastSeen.clear();
      state.futureDeals = [];
      state.historyRequested.clear();
      state.openedCount = 0;
      state.pendingOrders = Object.create(null);
      state.activeDirections = Object.create(null);
      state.startSum    = null;
      state.timeframe   = cmd.settings?.timeframe || 60;
      state.multiAsset  = !!cmd.settings?.multiAsset;
      state.maxConcurrent = Math.max(2, Math.min(10, Number(cmd.settings?.maxConcurrent || 10)));
      // V207: retain a positively confirmed Demo state across START.
      // Unknown remains fail-closed; an explicit Real account clears the sticky flag.
      state.isDemo = demoConfirmedSticky ? true : null;
      startAccountProbe();
      post({ type: 'BRIDGE_READY', isDemo: state.isDemo });
      // V24.1.101: replay the bridge's last known visible chart asset on START.
      // This lets content.js establish its single-asset session lock immediately
      // even when Pocket Option does not emit a fresh history packet at START.
      if (state.chartAsset) post({ type:'CHART_ASSET', asset:state.chartAsset, source:'bridge-cache' });
      // If the cached asset is empty (history was seen before bridge injection),
      // actively discover the visible chart instead of waiting forever.
      startChartResolutionBurst();
      if (state.multiAsset) startChartSlotsWatch();
      requestVisibleHistoryBurst();
    }

    if (cmd.type === 'ACCOUNT_PROBE') {
      publishAccountType('requested');
    }

    if (cmd.type === 'STOP') {
      state.started     = false;
      clearInterval(accountProbeTimer); accountProbeTimer=null;
      liveStreamAssets.clear(); liveStreamLastSeen.clear();
      state.futureDeals = [];
      state.openedCount = 0;
      state.pendingOrders = Object.create(null);
      state.activeDirections = Object.create(null);
      clearInterval(chartSlotsTimer); chartSlotsTimer=null;
      state.chartSlots=Object.create(null);
    }

    if (cmd.type === 'SYNC_FAVORITES') {
      syncFavorites(cmd.reason || 'content');
    }


    // B32.6.1 UNIQUE GRID ROTATION: reserve an auto-selected replacement before
    // another slot scans its menu. This closes the small race where two slots can
    // rotate at nearly the same time and both choose the same otherwise-unused pair.
    window.__poatAutoSwitchReservations = window.__poatAutoSwitchReservations || new Map();
    const autoSwitchReservations = window.__poatAutoSwitchReservations;
    const pruneAutoSwitchReservations = () => { const n=Date.now(); for (const [a,t] of autoSwitchReservations) if (n-t>12000) autoSwitchReservations.delete(a); };

    if (cmd.type === 'SWITCH_SLOT_HIGH_PAYOUT') {
      const slotId=String(cmd.slotId||'').trim();
      const minPayout=Math.max(0,Number(cmd.minPayout)||92);
      const fromAsset=String(cmd.fromAsset||'').trim();
      const hardExcluded=new Set((Array.isArray(cmd.excludedAssets)?cmd.excludedAssets:[]).map(v=>normAsset(v)).filter(Boolean));
      if(fromAsset) hardExcluded.add(normAsset(fromAsset));
      if (!slotId) return;
      const panel=findPanelBySlot(slotId);
      if (!panel) { post({type:'ASSET_SWITCH_ERROR',asset:'AUTO >= '+minPayout+'%',slotId,reason:'Chart slot not found'}); return; }
      if (!clickPanelAssetMenu(panel)) { post({type:'ASSET_SWITCH_ERROR',asset:'AUTO >= '+minPayout+'%',slotId,reason:'Could not open this chart slot asset menu'}); return; }
      setTimeout(()=>{
        pruneAutoSwitchReservations();
        const visibleNow=new Set(Object.values(state.chartSlots||{}).map(v=>normAsset(v)).filter(Boolean));
        for(const x of hardExcluded) visibleNow.add(x);
        for(const x of autoSwitchReservations.keys()) visibleNow.add(x);
        const selectors='button,[role="option"],[role="row"],li,[class*=asset],[class*=pair],[class*=symbol],[class*=instrument]';
        const rows=[...document.querySelectorAll(selectors)].filter(visibleEl);
        const candidates=[];
        for (const el of rows) {
          const txt=String(el.textContent||'').replace(/\s+/g,' ').trim();
          if(!txt||txt.length>220) continue;
          const pm=txt.match(/(?:^|\s)(\d{2,3}(?:\.\d+)?)\s*%/g);
          if(!pm||!pm.length) continue;
          let pay=0;
          for(const token of pm){ const m=token.match(/(\d{2,3}(?:\.\d+)?)/); if(m) pay=Math.max(pay,Number(m[1])||0); }
          if(pay<minPayout) continue;
          // Prefer a clickable option row and avoid the currently selected/visible asset
          // when its label can be resolved from the row text.
          const cleanTxt=txt.replace(/\d{2,3}(?:\.\d+)?\s*%/g,'');
          const n=normAsset(cleanTxt);
          const rowAliases=assetAliases(cleanTxt);
          let duplicate=!!(n && visibleNow.has(n));
          if(!duplicate){
            for(const used of visibleNow){
              const usedAliases=assetAliases(used);
              if(usedAliases.some(a=>a.length>=3 && rowAliases.some(r=>r.length>=3 && (r.includes(a)||a.includes(r))))){ duplicate=true; break; }
            }
          }
          if(duplicate) continue;
          const r=el.getBoundingClientRect();
          const score=pay*100+(el.matches('button,[role="option"],li')?20:0)+(r.width<600?5:0);
          candidates.push({el,pay,score,txt});
        }
        candidates.sort((a,b)=>b.score-a.score);
        const best=candidates[0];
        if(!best){ post({type:'ASSET_SWITCH_ERROR',asset:'AUTO >= '+minPayout+'%',slotId,reason:'No visible >= '+minPayout+'% UNIQUE market found in asset menu'}); return; }
        const reserveKey=normAsset(best.txt.replace(/\d{2,3}(?:\.\d+)?\s*%/g,''));
        if(reserveKey) autoSwitchReservations.set(reserveKey,Date.now());
        best.el.click();
        post({type:'ASSET_SWITCH_REQUESTED',asset:'AUTO >= '+best.pay+'%',slotId});
        setTimeout(()=>publishChartSlots('auto-high-payout-switch'),450);
      },300);
    }

    if (cmd.type === 'SWITCH_ASSET_SLOT') {
      const target=String(cmd.asset||'').trim();
      const slotId=String(cmd.slotId||'').trim();
      if (!target||!slotId) return;
      const panel=findPanelBySlot(slotId);
      if (!panel) { post({type:'ASSET_SWITCH_ERROR',asset:target,slotId,reason:'Chart slot not found'}); return; }
      if (panel.asset===target) { post({type:'CHART_SLOT_ASSET',slotId,asset:target,source:'already-selected'}); return; }
      if (!clickPanelAssetMenu(panel)) { post({type:'ASSET_SWITCH_ERROR',asset:target,slotId,reason:'Could not open this chart slot asset menu'}); return; }
      setTimeout(()=>{
        const targetNorms=assetAliases(target);
        const rows=[...document.querySelectorAll('button,[role="option"],[role="row"],li,[class*=asset],[class*=pair],[class*=symbol],[class*=instrument]')].filter(visibleEl);
        let best=null;
        for (const el of rows) {
          const txt=String(el.textContent||'').trim(); if(!txt||txt.length>180) continue;
          const n=normAsset(txt);
          const match=targetNorms.some(a=>a.length>=3&&n.includes(a));
          if(!match) continue;
          const r=el.getBoundingClientRect();
          let score=(el.matches('button,[role="option"],li')?4:0)+(r.width<500?2:0);
          if(!best||score>best.score) best={el,score};
        }
        if(!best){ post({type:'ASSET_SWITCH_ERROR',asset:target,slotId,reason:'Target favorite not found in slot asset menu'}); return; }
        best.el.click();
        post({type:'ASSET_SWITCH_REQUESTED',asset:target,slotId});
        setTimeout(()=>publishChartSlots('slot-switch'),350);
      },220);
    }

    if (cmd.type === 'SWITCH_ASSET') {
      const target = String(cmd.asset || '').trim();
      if (!target) return;

      const norm = (x) => String(x || '').toUpperCase()
        .replace(/_OTC/g,' OTC').replace(/[^A-Z0-9]/g,'');
      const targetNorm = norm(target);
      const targetPretty = target.replace(/_otc$/i,' OTC').replace(/^([A-Z]{3})([A-Z]{3})/,'$1/$2');

      const isVisible = (el) => {
        if (!el || !el.isConnected) return false;
        const r = el.getBoundingClientRect();
        const st = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden';
      };

      const findTarget = () => {
        const selectors = [
          '[data-asset]','[data-symbol]','[data-pair]','[data-id]',
          '[class*="asset"]','[class*="symbol"]','[class*="pair"]','[class*="instrument"]'
        ];
        const els = [...document.querySelectorAll(selectors.join(','))];
        const scored = [];
        for (const el of els) {
          if (!isVisible(el)) continue;
          const bag = [el.textContent, el.getAttribute('data-asset'), el.getAttribute('data-symbol'),
            el.getAttribute('data-pair'), el.getAttribute('data-id')].filter(Boolean).join(' ');
          const n = norm(bag);
          if (!n.includes(targetNorm)) continue;
          const txt = String(el.textContent || '').trim();
          let score = 0;
          if (norm(txt) === targetNorm) score += 10;
          if (n.startsWith(targetNorm) || n.endsWith(targetNorm)) score += 4;
          if (/item|row|asset|pair|symbol|instrument/i.test(String(el.className||''))) score += 3;
          if (el.matches('button,[role="button"],a,li')) score += 2;
          scored.push({el,score});
        }
        scored.sort((a,b)=>b.score-a.score);
        return scored[0]?.el || null;
      };

      const clickAssetMenu = () => {
        const selectors = [
          '[class*="current-symbol"]','[class*="current-asset"]','[class*="current-pair"]',
          '[class*="asset-select"]','[class*="symbol-select"]','[class*="pair-select"]',
          '[class*="asset"] [class*="current"]','[class*="pair"] [class*="current"]'
        ];
        for (const sel of selectors) {
          const el = [...document.querySelectorAll(sel)].find(isVisible);
          if (el) { el.click(); return true; }
        }
        // Fallback: click a visible compact control showing the currently selected pair.
        const candidates = [...document.querySelectorAll('button,[role="button"],div,span')]
          .filter(isVisible)
          .filter(el => /[A-Z]{3}\s*\/\s*[A-Z]{3}/.test(String(el.textContent||'')))
          .filter(el => el.getBoundingClientRect().width < 420 && el.getBoundingClientRect().height < 120);
        if (candidates.length) { candidates[0].click(); return true; }
        return false;
      };

      let tries = 0;
      const attempt = () => {
        tries++;
        let el = findTarget();
        if (el) {
          // Prefer a clickable ancestor that still represents this single row.
          let clickEl = el;
          for (let up=0; up<3 && clickEl.parentElement; up++) {
            if (clickEl.matches('button,[role="button"],a,li')) break;
            const p = clickEl.parentElement;
            const pt = norm(p.textContent);
            if (!pt.includes(targetNorm)) break;
            clickEl = p;
          }
          clickEl.click();
          post({type:'ASSET_SWITCH_REQUESTED', asset:target, display:targetPretty});
          return;
        }
        if (tries === 1 || tries === 3) clickAssetMenu();
        if (tries < 8) setTimeout(attempt, 350);
        else post({type:'ASSET_SWITCH_ERROR', asset:target, reason:'Could not find target asset in Pocket Option asset selector'});
      };
      attempt();
    }

    if (cmd.type === 'PLACE_TRADE') {
      if (!state.started) { post({type:'TRADE_ERROR',asset:cmd.asset||'',slotId:cmd.slotId||'',reason:'Pocket Option trade bridge is not started'}); return; }
      // V24.1.130: no account-type gate. The bot follows whatever account is
      // active in Pocket Option (DEMO or REAL) — the choice is made in the PO
      // page, never by the bot. openOrder frames keep PO's own account (we never
      // force isDemo); isDemo is tracked only for status/badge display.
      const inFlight = state.futureDeals.length + state.openedCount;
      if ((!state.multiAsset && inFlight > 0) || (state.multiAsset && inFlight >= state.maxConcurrent)) {
        post({ type: 'BRIDGE_BUSY', asset:cmd.asset||'', reason: state.multiAsset ? `Concurrent trade cap ${state.maxConcurrent}` : 'Trade already active' });
        return;
      }
      // V120: in multi-chart mode validate the asset against its specific visible
      // chart slot. Single-chart mode retains the original global chart invariant.
      let targetPanel=null;
      if (state.multiAsset) {
        targetPanel=findPanelBySlot(String(cmd.slotId||''),String(cmd.asset||''));
        if (!targetPanel || String(targetPanel.asset)!==String(cmd.asset||'')) {
          post({type:'TRADE_ERROR',asset:cmd.asset,slotId:cmd.slotId||'',reason:`Grid slot mismatch — ${cmd.slotId||'auto'} is ${targetPanel?.asset||'unknown'} / signal ${cmd.asset||'unknown'}`});
          publishChartSlots('trade-mismatch');
          return;
        }
      } else if (!state.chartAsset || String(state.chartAsset) !== String(cmd.asset || '')) {
        post({type:'TRADE_ERROR', asset:cmd.asset, reason:`Asset lock mismatch — chart ${state.chartAsset||'unknown'} / signal ${cmd.asset||'unknown'}`});
        return;
      }
      const direction = String(cmd.dir || '').toUpperCase() === 'SELL' ? 'SELL' : 'BUY';
      const action = direction === 'BUY' ? 'call' : 'put';
      // V276.1: clamp the stake — an unclamped postMessage amount could otherwise
      // request an arbitrarily large order on a live account.
      const amount = Math.max(1, Math.min(500000, Math.floor(Number(cmd.amount) || 0)));
      const requestedExpiry = Math.max(5, Number(cmd.expiry || state.timeframe || 60));
      state.futureDeals.push({ pair: cmd.asset, action, amount, direction, expiry: requestedExpiry, at: Date.now() });
      post({type:'EXPIRY_TRACE',stage:'BRIDGE_QUEUE',asset:cmd.asset,signalExpiry:Number(cmd.expiry||0),bridgeExpiry:requestedExpiry,contextTimeframe:Number(state.timeframe||0)});
      state.activeDirections[String(cmd.asset || '')] = direction;

      // ★ Click the correct button per direction ★
      // BUY → btn-call (green/higher), SELL → btn-put (red/lower)
      // Clicking the matching button ensures PO's frame already has the right
      // action field — our WS intercept then confirms it rather than mismatching
      let btn = null;
      if (direction === 'BUY') {
        const root = targetPanel?.el || document;
        btn = root.querySelector('.btn-call') ||
          [...root.querySelectorAll('button')].find(b => {
            const c = (b.className||'').toLowerCase(), t = (b.textContent||'').trim().toUpperCase();
            return c.includes('btn-call')||c.includes('btn-green-light')||c.includes('btn-higher')||
                   t==='BUY'||t==='CALL'||t==='HIGHER';
          });
      } else {
        const root = targetPanel?.el || document;
        btn = root.querySelector('.btn-put') ||
          [...root.querySelectorAll('button')].find(b => {
            const c = (b.className||'').toLowerCase(), t = (b.textContent||'').trim().toUpperCase();
            return c.includes('btn-put')||c.includes('btn-red')||c.includes('btn-lower')||
                   t==='SELL'||t==='PUT'||t==='LOWER';
          });
      }

      if (btn) {
        btn.click();
        post({ type: 'TRADE_CLICKED', asset: cmd.asset, slotId:targetPanel?.slotId||cmd.slotId||'', action, direction, amount });
        // B32.21.8: a DOM click is not proof the broker accepted an order. If no
        // websocket OPEN_ORDER consumes this queued deal, release it so one
        // failed click cannot jam every later Candidate 7B signal. No retry is
        // performed here, preventing accidental duplicate live-money orders.
        const queuedAt = state.futureDeals[state.futureDeals.length-1]?.at || Date.now();
        setTimeout(() => {
          const i = state.futureDeals.findIndex(d => d && d.at === queuedAt && d.pair === cmd.asset && d.direction === direction);
          if (i >= 0) {
            state.futureDeals.splice(i,1);
            post({type:'TRADE_ERROR',asset:cmd.asset||'',slotId:targetPanel?.slotId||cmd.slotId||'',reason:'Pocket Option did not confirm the clicked order within 5 seconds'});
          }
        }, 5000);
      } else {
        post({ type: 'TRADE_ERROR', reason: `btn-${action} not found — is PocketOption chart open?` });
        state.futureDeals.pop();
      }
    }
  });

  const parseFrame = (data, channel) => {
    if (data instanceof ArrayBuffer) {
      if (!channel.pendingAction) return;
      try {
        const text = new TextDecoder().decode(new Uint8Array(data));
        let parsed=null;
        try { parsed=JSON.parse(text); } catch(_) {
          const a=text.indexOf('['), o=text.indexOf('{'); const pos=a<0?o:o<0?a:Math.min(a,o);
          if(pos>=0) parsed=JSON.parse(text.slice(pos));
        }
        if(parsed!=null) handlePayload(channel.pendingAction, parsed);
      } catch(e) {}
      channel.pendingAction = null;
      return;
    }
    if (typeof data !== 'string' || data.length <= 6) return;
    try {
      let jsonStr = data.slice(4);
      if (!jsonStr.startsWith('[') && !jsonStr.startsWith('{')) {
        const b = data.indexOf('['), c = data.indexOf('{');
        const pos = b === -1 ? c : c === -1 ? b : Math.min(b, c);
        if (pos === -1) return;
        jsonStr = data.slice(pos);
      }
      const parsed = JSON.parse(jsonStr);
      if (!Array.isArray(parsed) || !parsed[0]) return;
      const map = {
        'updateHistoryNew':'updateHistory','updateHistoryNewFast':'updateHistory','loadHistoryPeriod':'historyPeriod','loadHistoryPeriodFast':'historyPeriod','updateStream':'updateStream',
        'updateAssets':'updateAssets','successupdateBalance':'updateBalance',
        'updateOpenedDeals':'updateOpenedDeals','successopenOrder':'successopenOrder',
        'successcloseOrder':'successcloseOrder','upsignals':'signals',
        'updateSignalForecast':'signals','signals/load':'signals','signals/update':'signals',
      };
      const action = map[parsed[0]];
      if (!action) return;
      const payload = parsed[1];
      const isPlaceholder = payload && typeof payload === 'object' && payload._placeholder === true;
      if (payload !== undefined && !isPlaceholder) {
        handlePayload(action, payload);
        channel.pendingAction = null;
      } else {
        channel.pendingAction = action;
      }
    } catch(e) {}
  };

  const historyRows = (payload, fallbackAsset='') => {
    const out=[]; const seen=new Set();
    const push=(asset,t,p)=>{ asset=String(asset||fallbackAsset||'').trim(); t=Number(t); p=Number(p); if(!asset||!Number.isFinite(t)||!Number.isFinite(p)||p<=0)return; if(t>1e12)t/=1000; const k=asset+'|'+t+'|'+p; if(seen.has(k))return; seen.add(k); out.push({asset,time:t,price:p}); };
    const walk=(x, asset=fallbackAsset, depth=0)=>{
      if(depth>6||x==null)return;
      if(Array.isArray(x)){
        // raw tick [timestamp,price] or [asset,timestamp,price]
        if(x.length>=2 && Number.isFinite(Number(x[0])) && Number.isFinite(Number(x[1]))) push(asset,x[0],x[1]);
        else if(x.length>=3 && typeof x[0]==='string' && Number.isFinite(Number(x[1])) && Number.isFinite(Number(x[2]))) push(x[0],x[1],x[2]);
        else for(const v of x) walk(v,asset,depth+1);
        return;
      }
      if(typeof x==='object'){
        const a=String(x.asset??x.symbol??x.active??asset??'');
        const t=x.time??x.timestamp??x.t; const pr=x.price??x.p??x.close??x.c;
        if(t!=null && pr!=null) push(a,t,pr);
        for(const key of ['history','candles','ticks','data','result','prices']) if(x[key]!=null) walk(x[key],a,depth+1);
      }
    };
    walk(payload,fallbackAsset,0); out.sort((a,b)=>a.time-b.time); return out;
  };

  // B32.20.10: Pocket Option history replies are not uniform across asset classes.
  // Some markets (notably crypto/OTC) can carry most of the historical bars in
  // payload.candles while payload.history is sparse. Preserve those real OHLC bars
  // instead of waiting for the live stream to build the archive one candle at a time.
  const historyOhlcRecords = (payload, fallbackAsset='') => {
    const out=[]; const seen=new Set();
    const push=(asset,t,o,c,h,l)=>{
      asset=String(asset||fallbackAsset||'').trim(); t=Number(t);
      o=Number(o); c=Number(c); h=Number(h); l=Number(l);
      if(t>1e12)t/=1000;
      if(!asset||![t,o,c,h,l].every(Number.isFinite)||c<=0)return;
      const k=asset+'|'+t; if(seen.has(k))return; seen.add(k);
      out.push({asset,time:t,kind:'ohlc',open:o,high:h,low:l,close:c});
    };
    const walk=(x,asset=fallbackAsset,depth=0,key='')=>{
      if(depth>7||x==null)return;
      if(Array.isArray(x)){
        // PO candle wire format: [timestamp, open, close, high, low]
        if((key==='candles'||key==='candle') && x.length>=5 && [0,1,2,3,4].every(i=>Number.isFinite(Number(x[i])))) {
          push(asset,x[0],x[1],x[2],x[3],x[4]); return;
        }
        for(const v of x) walk(v,asset,depth+1,key);
        return;
      }
      if(typeof x==='object'){
        const a=String(x.asset??x.symbol??x.active??asset??'');
        const t=x.time??x.timestamp??x.t;
        if(t!=null && x.open!=null && x.close!=null && x.high!=null && x.low!=null) push(a,t,x.open,x.close,x.high,x.low);
        for(const k of ['candles','candle','data','result']) if(x[k]!=null) walk(x[k],a,depth+1,k);
      }
    };
    walk(payload,fallbackAsset,0,''); out.sort((a,b)=>a.time-b.time); return out;
  };

  const handlePayload = (action, payload) => {
    if (action === 'historyPeriod') {
      try {
        const fallback=String(payload?.asset||payload?.symbol||payload?.active||'');
        const rows=historyRows(payload,fallback);
        const ohlc=historyOhlcRecords(payload,fallback);
        if(ohlc.length){
          const ob=new Map();
          for(const r of ohlc){if(!ob.has(r.asset))ob.set(r.asset,[]);ob.get(r.asset).push(r);}
          for(const [oa,records] of ob) post({type:'HISTORY_BACKFILL',asset:oa,records,source:'loadHistoryPeriod-candles'});
        }
        const by=new Map();
        for(const r of rows){ if(!by.has(r.asset))by.set(r.asset,[]); by.get(r.asset).push(r); }
        for(const [asset,all] of by){
          // B15.10.27: seed one full hour immediately so 60s EMA50 strategies are ready.
          // Never bridge a history gap with synthetic flat candles.
          const nowBucket=5*Math.floor(Date.now()/1000/5);
          const bucketMap=new Map();
          for(const r of all){
            const b=5*Math.floor(r.time/5);
            if(b>=nowBucket) continue; // completed historical buckets only
            if(!bucketMap.has(b)) bucketMap.set(b,[]);
            bucketMap.get(b).push(r);
          }
          const keys=[...bucketMap.keys()].sort((a,b)=>a-b);
          let run=[];
          for(const b of keys){
            if(!run.length || b===run[run.length-1]+5) run.push(b);
            else run=[b];
          }
          if(run.length<200){
            post({type:'PREWARM_NEED_MORE',asset,foundConsecutive:run.length,totalBuckets:keys.length,targetBuckets:200,source:'loadHistoryPeriod'});
            // Do not mark a short broker reply as permanently handled. Ask again
            // with a larger lookback until 200 consecutive completed 5s bars exist.
            setTimeout(()=>requestPrevious200(asset,true),350);
            continue;
          }
          historyRequestState.set(asset,{tries:0,last:Date.now()});
          const chosen=run.slice(-200), chosenSet=new Set(chosen);
          const ticks=all.filter(r=>chosenSet.has(5*Math.floor(r.time/5))).sort((a,b)=>a.time-b.time);
          // Every selected bucket must contain at least one real broker observation.
          if(new Set(ticks.map(r=>5*Math.floor(r.time/5))).size!==200) continue;
          post({type:'PREWARM_BEGIN',asset,source:'loadHistoryPeriod',bucketCount:200,firstBucket:chosen[0],lastBucket:chosen[199]});
          post({type:'PREWARM_RESET',asset,source:'loadHistoryPeriod',bucketCount:200,firstBucket:chosen[0],lastBucket:chosen[199]});
          for(let i=0;i<ticks.length;i+=1000) post({type:'STREAM',ticks:ticks.slice(i,i+1000),historical:true});
          post({type:'PREWARM_DONE',asset,source:'loadHistoryPeriod',bucketCount:200,firstBucket:chosen[0],lastBucket:chosen[199]});
        }
      } catch(e) { post({type:'PREWARM_ERROR',reason:String(e?.message||e)}); }
      return;
    }
    if (action === 'updateHistory') {
      try {
        if (payload && payload.asset) { state.chartAsset = String(payload.asset); knownAssetNames.add(String(payload.asset)); markLiveStreamAsset(String(payload.asset)); }
        const prices = [];
        const backfill = [];
        // V239: preserve Pocket Option's preloaded chart timestamps/OHLC instead of
        // throwing them away and keeping only closes. content.js will align these
        // records into real 5-second buckets before building every higher TF.
        if (Array.isArray(payload.candles)) payload.candles.forEach(c => {
          try {
            if (Array.isArray(c)) {
              if (c[4]!=null) prices.push(parseFloat(c[4]));
              if (c.length>=5 && Number.isFinite(Number(c[0]))) backfill.push({kind:'ohlc',time:Number(c[0]),open:Number(c[1]),high:Number(c[2]),low:Number(c[3]),close:Number(c[4])});
            } else if (c && typeof c==='object') {
              const tm=c.time??c.t??c.timestamp, o=c.open??c.o, h=c.high??c.h, l=c.low??c.l, cl=c.close??c.c;
              if (cl!=null) prices.push(parseFloat(cl));
              if (tm!=null && [o,h,l,cl].every(v=>Number.isFinite(Number(v)))) backfill.push({kind:'ohlc',time:Number(tm),open:Number(o),high:Number(h),low:Number(l),close:Number(cl)});
            }
          } catch(_) {}
        });
        if (Array.isArray(payload.history)) payload.history.forEach(h => {
          try {
            if (Array.isArray(h)) {
              if (h[1]!=null) prices.push(parseFloat(h[1]));
              if (h.length>=2 && Number.isFinite(Number(h[0])) && Number.isFinite(Number(h[1]))) backfill.push({kind:'tick',time:Number(h[0]),price:Number(h[1])});
            } else if (h && typeof h==='object') {
              const tm=h.time??h.t??h.timestamp, px=h.price??h.p??h.close??h.c;
              if (px!=null) prices.push(parseFloat(px));
              if (tm!=null && Number.isFinite(Number(px))) backfill.push({kind:'tick',time:Number(tm),price:Number(px)});
            }
          } catch(_) {}
        });
        if (backfill.length >= 5) { visualBackfillDone.add(String(payload.asset||'')); post({type:'HISTORY_BACKFILL',asset:payload.asset||'',records:backfill.slice(-6000),source:'Pocket Option history'}); }
        if (prices.length >= 5) { post({ type:'HISTORY', asset: payload.asset||'', prices: prices.slice(-1200) }); if (state.started && state.multiAsset) setTimeout(()=>publishChartSlots('history-grid'),0); }
      } catch(e) {}
    }
    if (action === 'updateStream') {
      try {
        if (!Array.isArray(payload)) return;
        const ticks = [];
        payload.forEach(t => {
          if (!Array.isArray(t)||t.length<3) return;
          const p = parseFloat(t[2]);
          const asset = String(t[0]);
          if (asset) { knownAssetNames.add(asset); markLiveStreamAsset(asset); }
          if (!isNaN(p)&&p>0) ticks.push({ asset, time:t[1], price:p });
        });
        if (ticks.length) {
          post({ type:'STREAM', ticks });
          // STREAM often arrives before ASSETS. Once names are known, retry DOM
          // discovery immediately so single-mode warmup can bind and advance.
          if (state.started && !state.chartAsset) publishResolvedChartAsset('dom-stream');
        }
      } catch(e) {}
    }
    if (action === 'updateAssets') {
      try {
        const assets = [];
        if (Array.isArray(payload)) payload.forEach(a => {
          if (Array.isArray(a)&&a.length>=15) {
            const name = String(a[1]);
            if (name) knownAssetNames.add(name);
            assets.push({ name, payout:parseFloat(a[5]), active:!!a[14] });
          }
        });
        if (assets.length) {
          post({ type:'ASSETS', assets });
          if (state.started && !state.chartAsset) publishResolvedChartAsset('dom-assets');
        }
      } catch(e) {}
    }
    if (action === 'updateBalance') {
      try {
        state.isDemo = !!payload.isDemo;
        if(state.isDemo){
          demoConfirmedSticky=true;
          demoConfirmedAt=Date.now();
        } else {
          demoConfirmedSticky=false;
          demoConfirmedAt=0;
        }
        post({ type:'BALANCE', isDemo:state.isDemo, balance:payload.balance });
        post({ type:'ACCOUNT_TYPE', isDemo:state.isDemo, reason:'balance-socket' });
      } catch(e) {}
    }
    if (action === 'updateOpenedDeals') {
      try { state.openedCount = Array.isArray(payload) ? payload.length : 0; } catch(e) {}
    }
    if (action === 'successopenOrder') {
      try {
        if (state.started) {
          state.openedCount++;
          const orderId = payload.id||payload.deal_id;
          const fd = state.futureDeals[0];
          const rawDirection = payload.direction || payload.dir || payload.command || (fd && fd.direction) || (fd && fd.action) || state.activeDirections[String(payload.asset || (fd && fd.pair) || '')];
          const direction = String(rawDirection || '').toUpperCase() === 'SELL' || String(rawDirection || '').toLowerCase() === 'put' || String(rawDirection || '').toLowerCase() === 'lower' ? 'SELL' : (rawDirection ? 'BUY' : null);
          if (orderId != null && direction) state.pendingOrders[String(orderId)] = direction;
          post({ type:'OPEN_ORDER', id: orderId, asset: payload.asset || (fd && fd.pair) || '', direction });
        }
      } catch(e) {}
    }
    if (action === 'successcloseOrder') {
      // ★ KEY FIX: forward ALL close events unconditionally while started ★
      // No ID matching — avoids the race where close arrives before open confirmation
      try {
        if (!state.started) return;
        const deals = payload.deals || (Array.isArray(payload) ? payload : [payload]);
        deals.forEach(deal => {
          if (!deal) return;
          if (state.openedCount > 0) state.openedCount--;
          const profit = parseFloat(deal.profit ?? 0);
          post({
            type:'CLOSE_ORDER', id:deal.id,
            profit, amount: parseFloat(deal.amount ?? deal.sum ?? 0),
            asset: deal.asset||'', command: deal.command,
            direction: (() => {
              const raw = deal.direction || deal.dir || deal.command || state.pendingOrders[String(deal.id)] || state.activeDirections[String(deal.asset || '')] || state.activeDirections[Object.keys(state.activeDirections)[0]];
              const x = String(raw || '').toUpperCase();
              return (x === 'SELL' || x === 'PUT' || x === 'LOWER') ? 'SELL' : (x === 'BUY' || x === 'CALL' || x === 'HIGHER') ? 'BUY' : null;
            })(),
            win: profit > 0, lose: profit < 0, draw: profit === 0,
          });
          if (deal.id != null) delete state.pendingOrders[String(deal.id)];
          const dealAsset = String(deal.asset || '');
          if (dealAsset) delete state.activeDirections[dealAsset];
        });
      } catch(e) {}
    }
  };

  // B32.20.4: request actual 5-second history, not period=1.  The old request
  // asked Pocket Option for 1-second history and then hoped it happened to contain
  // 200 consecutive 5-second buckets. Thin/OTC replies could yield only 8-20 usable
  // buckets, so Raw 5s archive kept climbing live instead of bootstrapping.
  const historyRequestState = new Map();
  function requestPrevious200(asset, force=false){
    asset=String(asset||'').trim(); if(!asset)return false;
    const sockets=[...state.historySockets].filter(ws=>{try{return ws.readyState===1}catch(_){return false}});
    if(!sockets.length)return false;
    const prior=historyRequestState.get(asset)||{tries:0,last:0};
    if(!force && state.historyRequested.has(asset) && Date.now()-prior.last<2500)return false;
    // Never strand a newly selected market after six attempts. Keep retrying at a
    // controlled cadence until a valid broker history reply is accepted.
    if(prior.tries>=6 && Date.now()-prior.last<2500)return false;
    const tries=prior.tries+1;
    historyRequestState.set(asset,{tries,last:Date.now()});
    state.historyRequested.add(asset);
    // period is the broker candle period in seconds. Ask for 5s bars directly.
    // Offset grows on retries so a short first response does not strand the market.
    // Larger windows are important for thin crypto/OTC history replies.
    const offset=Math.min(45000, 4500*Math.max(1,tries));
    const payload={asset,index:Math.floor(Math.random()*900000)+100000,time:Math.floor(Date.now()/1000),offset,period:5};
    const wire='42'+JSON.stringify(['loadHistoryPeriod',payload]);
    for(const ws of sockets){ try{ws._origSend?ws._origSend(wire):ws.send(wire);}catch(_){} }
    post({type:'PREWARM_REQUESTED',asset,period:5,offset,targetBuckets:200,try:tries});
    return true;
  }
  function requestVisibleHistoryBurst(){
    let tries=0; const timer=setInterval(()=>{
      tries++;
      const assets=new Set();
      if(state.chartAsset)assets.add(state.chartAsset);
      for(const a of Object.values(state.chartSlots||{}))if(a)assets.add(a);
      for(const a of recentLiveStreamAssets(15000))assets.add(a);
      for(const a of assets)requestPrevious200(a);
      // Keep the discovery burst alive long enough to cross retry backoff and
      // receive delayed crypto history. Successful assets self-reset their state.
      if(tries>=60)clearInterval(timer);
    },500);
  }

  const OrigWS = window.WebSocket;
  if (!OrigWS || OrigWS.__poatPatched440) return;

  function PocketOptionWS(...args) {
    const ws = new OrigWS(...args);
    state.historySockets.add(ws);
    ws.addEventListener('close',()=>state.historySockets.delete(ws));
    // V121.6: each Pocket Option chart/socket keeps its own two-frame parser state.
    // A single global pendingAction can be overwritten when four chart sockets
    // interleave action/payload frames, which makes only one market appear live.
    const channel = { pendingAction:null };
    ws.addEventListener('message', (ev) => { parseFrame(ev.data, channel); });
    ws._origSend = OrigWS.prototype.send.bind(ws);
    ws.send = function(data) {
      // V276.1: STALE-DEAL GUARD. Only consume a queued deal created in the last
      // 15s. Before, ANY outbound openOrder frame (e.g. a trade the user clicked
      // manually in Pocket Option) shifted and rewrote the OLDEST queued deal —
      // reassigning its asset, amount and expiry to someone else's order.
      const DEAL_TTL_MS = 15000;
      if (state.started && state.futureDeals.length > 0 && typeof data === 'string') {
        while (state.futureDeals.length && (Date.now() - (state.futureDeals[0].at || 0)) > DEAL_TTL_MS) {
          state.futureDeals.shift();
        }
        const bracket = data.indexOf('[');
        if (bracket >= 0 && bracket <= 5 && state.futureDeals.length > 0) {
          try {
            const prefix = data.slice(0, bracket);
            const parsed = JSON.parse(data.slice(bracket));
            if (Array.isArray(parsed) && parsed[0] === 'openOrder' && parsed[1]) {
              const trade = state.futureDeals.shift();
              if (!state.startSum) state.startSum = parsed[1].amount;
              // ★ Replace with bot values — including expiry time ★
              parsed[1].asset  = trade.pair;
              parsed[1].action = trade.action;
              if (trade.amount) parsed[1].amount = trade.amount;
              // Set expiry time in seconds (PO uses 'time' field)
              const orderExpiry = Math.max(5, Number(trade.expiry || state.timeframe || 60));
              parsed[1].time   = orderExpiry;
              post({type:'EXPIRY_TRACE',stage:'OPEN_ORDER_REWRITE',asset:trade.pair,bridgeExpiry:Number(trade.expiry||0),orderExpiry,originalOrderTime:Number(parsed?.[1]?.time||0)});
              // ★ Do NOT force isDemo — let PO's frame keep whatever account type it was
              // Overriding this caused real account trades to go to demo silently
              ws._origSend(prefix + JSON.stringify(parsed));
              return;
            }
          } catch(e) {}
        }
      }
      ws._origSend(data);
    };
    return ws;
  }

  PocketOptionWS.prototype        = OrigWS.prototype;
  PocketOptionWS.CONNECTING       = OrigWS.CONNECTING;
  PocketOptionWS.OPEN             = OrigWS.OPEN;
  PocketOptionWS.CLOSING          = OrigWS.CLOSING;
  PocketOptionWS.CLOSED           = OrigWS.CLOSED;
  PocketOptionWS.__poatPatched440 = true;
  window.WebSocket = PocketOptionWS;

  console.log('[POAT Bridge v4.4.2] ✓ four independent socket/parser channels + robust four-chart grid');
  window.__poatTest = {
    canonical: canonicalAssetFromVisibleLabel,
    resolve: resolvePanelAssetToKnown,
    bindLive: bindPanelsToLive,
    live: liveStreamAssets,
    known: knownAssetNames,
    panelFull: panelFullText
  };
})();
