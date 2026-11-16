var kaosPocketOptionBalance=null;
var kaosPocketOptionBalanceIsDemo=null;

// KAOS 1.6.7 — confirms the isolated Pocket Option content bridge is alive.
chrome.runtime.onMessage.addListener((msg,_sender,sendResponse)=>{
  if(msg&&msg.type==='KAOS_PO_PING'){sendResponse({ok:true,ts:Date.now()});return false;}
});
function kaosReadVisibleBalance(){
  try{
    // Only Pocket Option account-balance-specific elements. Never use generic
    // ".balance" because it can match unrelated controls/amounts.
    const sels=[
      '[data-test="balance"]','[data-testid="balance"]',
      '[data-testid="account-balance"]','[data-test="account-balance"]',
      '.balance-info-block__balance','.balance-info__balance',
      '.user-balance__value','.account-balance__value',
      '[class*="balance-info"] [class*="value"]'
    ];
    const parse=(txt)=>{
      txt=String(txt||'').replace(/\u00a0/g,' ').replace(/,/g,'');
      const ms=[...txt.matchAll(/(?:\$|USD\s*)(-?\d+(?:\.\d{1,2})?)/gi)];
      if(ms.length)return Number(ms[ms.length-1][1]);
      const n=txt.trim().match(/^(-?\d+(?:\.\d{1,2})?)$/);
      return n?Number(n[1]):null;
    };
    for(const sel of sels){
      for(const el of document.querySelectorAll(sel)){
        if(!el || el.offsetParent===null) continue;
        const v=parse(el.textContent);
        if(Number.isFinite(v)) return v;
      }
    }

    // Text-label fallback: locate a visible Balance label and inspect only its
    // immediate account widget, not the whole document.
    for(const el of document.querySelectorAll('div,span,p')){
      if(el.offsetParent===null)continue;
      const t=(el.textContent||'').trim();
      if(!/^balance:?$/i.test(t))continue;
      const box=el.parentElement;
      if(!box)continue;
      const v=parse(box.textContent);
      if(Number.isFinite(v))return v;
    }
  }catch(_){}
  return null;
}

// KAOS 1.6.6: background can verify an already-open Pocket Option tab has the
// content bridge attached. This avoids requiring a manual browser refresh.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'KAOS_PO_PING') {
    sendResponse({ ok:true, attached:true, href:location.href, ts:Date.now() });
    return false;
  }
});

// ⚑ KAOS V24.1.287-B23-BB-OUTER-BAND-EXHAUSTION-LOCK — deterministic 15s BB lanes · 60s expiry
// B3 engine/cursor fixes + per-asset pending resolution + persistent learner + OTC isolation + storage-churn fix
// V282: fixes the permanent-HOLD dead zone found in the 2026-09-23 forensic export. v194's
//   RANGE/CHOP router handed 34/40 decisions to the V227 range controller, which then
//   re-classified the SAME market with a stricter, different formula and refused every
//   handoff while the directional engine rejected the same markets -> zero trades.
//   V282 (1) makes the router verdict authoritative for the range controller, (2) adds a
//   bounded participation floor keyed to the per-asset consecutive-HOLD streak, and
//   (3) exempts the RANGE_REVERSAL family from the V281 directional conviction rules.
// KAOS V24.1.287-B15.10.11 — AUTO HIGH-PAYOUT GRID · KEEP >=90% · REPLACE <90% WITH >=92% · 50-CANDLE WARMUP
// V283: SIMPLE 30S EDGE ENGINE — live execution bypasses the accumulated V194/V222 entry maze.
// Candle clock repair prevents wall-clock catch-up from fabricating dozens of 5s candles per second.
// V281: V281_CONVICTION_LEVEL blocks ONLY the three structurally-losing buckets found
//   in the 1004-trade post-mortem, keeping ~56% of trade volume while lifting win rate
//   from 49.2% to ~52.6% and flipping EV/trade from -0.058 to +0.006. It is LOOSE by
//   design (LEVEL 1 keeps ~76% volume); set V281_CONVICTION_ENABLED = false to disable.
//   Rationale + full evidence table in RELEASE_V24.1.281.md.
// V280: V280_PAYOUT_FLOOR_PCT (default 90) rejects a directional entry when the live
//   payout sits under the floor. It is a RESIDUAL backstop below the 92% auto-switch
//   threshold; set V280_PAYOUT_FLOOR_PCT = 0 to disable. Rationale + evidence in
//   RELEASE_V24.1.280.md (low-payout tail cost ~191,390 over the 1004-trade log).
// V276.1: a grid chart whose live payout is UNDER 92% auto-rotates to a >=92% pair
//   (rotates only when a unique >=92% replacement exists; never parks the channel).
// V276.1: demo-only execution gate removed — the bot trades whatever account
//   Pocket Option has active (DEMO or REAL).
// V24.1.151: Reversal-quality pass without global tightening; all payout-based eligibility/switch gating disabled.
// Payout may still be displayed/recorded and used by EV analytics, but low payout alone cannot block a signal.

console.info('[KAOS BUILD] V24.1.287-B21 · BB WINNER PRO (15s BB20/2) + ACTIVE MID-BAND BB CHOP · 60S EXPIRY · NO LEGACY REGIME VETO · RAW 5S ARCHIVE · SHADOW-ONLY AI');
// ═══════════════════════════════════════════════════════════════
//  V24.1.141 HOLD-LOOSEN PATCH
//  • FIX: pullback body now has a true ATR-normalized measurement; the old
//    pullbackBodyRatio (body/anchor-body) is retained for compatibility only.
//  • FIX: BREAKOUT_RETEST stores the broken support/resistance level, requires
//    price to move away first, then revisit that level, then resume direction.
//    The old implementation could mark a retest true on the same scan it armed.
//  V24.1.141 MORE-FREQUENT LIVE ENTRY TUNING: selective HOLD gates loosened
//  across trend/resume/pullback/range/reversal; 12s per-asset re-entry gap.
//  Performance tracking remains diagnostic only — never PAPER ONLY.
//  • NEW: MOMENTUM_CONTINUATION catches clean with-trend runners that do not
//    produce a textbook 1-2 candle pullback, without lowering every threshold.
//  • NEW: RANGE_REJECTION trades only the outer range quartiles after an actual
//    directional rejection/15s turn; the middle of the range remains no-trade.
//  • REVERSALS: structure/15s failure evidence can confirm before every lagging
//    DMI/MACD condition fully flips; multiple independent confirmations required.
//  • ADAPTIVE GATE: exact buckets need more evidence before dominating; low-N
//    BUILDING_EDGE can seed when quality is strong and edge is near target, while
//    established below-breakeven buckets remain demoted.
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
//  V24.1.137: MORE CANDIDATE FAMILIES VIA THE PAIR-ADAPTIVE QUALITY FUNNEL
//  (user-approved design)
//  • FIX — V118 CTX MISSED THE FUNNEL FIELDS: structure direction/confidence/
//    scores, pullback count/closed-count/body-ratio/structure-break/anchor/
//    continuation, patternEligible and entry-quality lived ONLY on the global
//    /indicators/ node (lastIndicators), never on the per-channel ctx object that
//    all four lastIndicatorCtx stores share — so ind?.pullbackContinuation* and
//    ind?.structure* reads in v116CleanCoreProposal were permanently dead
//    (structure always NEUTRAL). One Object.assign now mirrors those fields onto
//    the ctx before the first store, null-guarded exactly like the adx mirror.
//  • NEW FAMILY — TREND_PULLBACK: with-trend re-entry on a confirmed 1-2 bar
//    counter-pullback (structure-confirmed trend, no anchor break, bounded body,
//    mid-band rsi/stoch), funnel-gated by TQS/MQ/trade-votes/15s differential.
//  • BREAKOUT_RETEST window 60s → 120s — a fresh break + revisit needs more room.
//  • OBSERVABILITY — no-candidate holds now explain WHY the funnel refused
//    (cleanCore.why on the channel line); holdReasonKey classifies 'no qualified
//    location' as no-location instead of other.
//  V24.1.136: PREDICTOR SUBSYSTEM REMOVED (user-approved)
//  • The standalone 30s paper predictor (V24.1.94 observer block, dashboard,
//    toggle, CSV columns, backup/diagnostic/restore fields) is DELETED.
//  • AI (XGBoost/LightGBM teacher + V118 setup engine) is the ONLY signal and
//    trade driver; every channel executes through v116CleanCoreDecision.
//  V24.1.135: TRADE MORE · TRADE SOONER (user-approved design)
//  • A1 FASTER SCAN CADENCE — the signal-check interval drops 5s → 3s
//    (SIGNAL_SCAN_MS). Every scan re-evaluates all warm channels, so the
//    faster loop finds the same setups sooner.
//  • A2 SETTLE-LINKED RE-SCAN — when a trade settles (win/lose/draw) and the
//    per-channel/global pending lock clears, armSettleRescan() forces one
//    signal check 400ms later (SETTLE_RESCAN_DELAY_MS) instead of waiting up
//    to a full cadence for the next opportunity. Deduped (one pending timer),
//    re-checks isRunning at fire time, and martingale paths that already
//    scheduled the next step skip it (their early returns come first).
//  • A3 COLD-START PROVISIONAL SEED BAR 86/52 → 84/50 — 86/52 was unreachable
//    for ordinary forex TREND_RESUME setups (realistic score band ~79-88;
//    crypto carried the +2 family bonus, so in practice ONLY crypto could
//    clear 86) and the per-asset evidence n only increments when a trade fires:
//    a cold start on forex deadlocked in PROVISIONAL forever. 84/50 matches
//    the BUILDING_EDGE setup bar so ordinary setups can seed evidence; from
//    n>=10 the payout-aware shrink-vs-breakeven tier ladder (BUILDING_EDGE /
//    QUALIFIED / PROVEN) takes over, so seeding quality stays bounded. No other
//    gate threshold changed; the strongDisagree XGB veto stays intact.
//  • C HOLD-REASON COUNTERS — aiState.holdCounters tallies every
//    evalAssetSignal skip and checkSignals cooldown/park/watchdog/no-panels
//    hold by normalized reason (warmup · ctx-error · ctx-not-ready · asset-lock
//    · re-entry-gap · no-location · ai-veto · no-panels ·
//    cooldown · park · watchdog · other) in total + per-asset, plus a last
//    entry; exported in the full backup and the diagnostic export so an export
//    shows WHY the bot held instead of trading. Session-only, never restored.
//  V24.1.134: GRID CHART-SWITCH FIX — changing one chart must never pause the
//  other channels while the new chart warms. The old scanAssets.length < 4
//  hard-return ("waiting for 4 visible chart panels") halted the WHOLE grid
//  whenever a chart change left 1-3 visible panels (slot mid-switch, briefly
//  empty, or the same asset in two slots deduping multiScanAssets to 3), and
//  the monolithic "GRID WARMUP x/4" marquee suppressed per-channel READY/parked
//  lines while any one chart warmed. Now only ZERO visible panels holds; with
//  1-3 visible the bot trades whatever panels are live (one notice per panel-
//  count transition), and each warming chart reports its own per-channel line
//  ("CH2 EURUSD Warmup 45%") inside the joined summary so a chart swap can no
//  longer mask the other channels' state. Warmup remains strictly per chart.
//  V24.1.133: V118 SETUP ENGINE IS THE SOLE TRADE DRIVER — the predictor-driver
//  execution branch is deleted. The predictor NEVER decides a trade again: it
//  remains a per-channel paper observer/learner that reads the same indicators,
//  keeps the candidate + accuracy dashboard populated ("what were my indicators
//  doing") and keeps feeding the AI learning pipeline with real-outcome labels —
//  all observation/learning/dashboard code is byte-identical to the proven
//  V118-only era. Hard-coded veto parks (60s payout floor, 30m EV rest) now
//  follow the user's popup cooldown semantics (cooldownAfterLoss / autoCooldownOn
//  ladder), per channel in grid mode, floored at 15s. Emergency stops unchanged:
//  8-loss 60m hard stop · RISK market ban · 30m maxLossStreak channel park.
//  V24.1.132: GRID PAYOUT-FLOOR AUTO-SWITCH — a multi-grid channel whose live
//  payout drops below the 80% floor now rotates its chart slot to the best ≥92%
//  market (SWITCH_ASSET_SLOT) instead of only parking 60s: armed from the signal
//  veto or a per-channel watchdog, confirmed on the CHART_SLOTS republish within
//  8s; failed/timeout targets are blacklisted 10 min so the next attempt picks a
//  different ≥92% market. Single-market mode is unchanged.
//  V24.1.131: PAYOUT FLOOR 80% · REALIZED-EV REST · DATA-INTEGRITY SCALE GUARD.
//  • LIVE PAYOUT FLOOR — fireTrade now vetoes any execution while the asset's live
//    payout is below 80%. V24.1.91's 92% rule only steered chart selection and its
//    dead `const pp = payoutPct(assetName);` let a payout collapse (e.g. DOGE_otc
//    0.92 → 0.29) trade straight through. The floor parks the channel/session 60s.
//  • REALIZED-EV REST — per-asset rolling window (25 settled trades) compares a
//    shrinkage-adjusted realized winrate vs the payout's breakeven winrate and parks
//    the channel/session 30m when realized EV is clearly negative. Persisted under
//    chrome.storage key KAOSEvStateV131 (debounced), survives page reloads.
//  • DATA-INTEGRITY SCALE GUARD — live ticks and HISTORY seeds whose price scale
//    deviates >6× or <1/6× from the recent-close median are rejected; 15 rejects
//    purge that asset's price/indicator state and park it 45s to re-warm cleanly.
//  V24.1.130: FOLLOWS POCKET OPTION — the bot trades whatever account is active
//  in PO (DEMO or REAL). The real-money option stays OUT of the bot UI; the
//  account choice belongs to Pocket Option alone. No bot-side account gate.
//  V24.1.128: per-channel indicator context fix — the strategy ctx pass inside
//  STRATEGIES.fn tagged every channel's ctx under the single activeAsset key because
//  getLiveTFView() views never carried __assetName, so only CH1 (activeAsset) ever
//  passed the ctxFresh gate and CH2-CH4 stayed on 'INDICATOR CONTEXT NOT READY'.
//  evalAssetSignal now stamps each live TF view with the asset being evaluated.
//  V24.1.125: marquee can no longer stay frozen on "GRID WARMUP" when every
//  channel is READY — publishGridWarmupStatus now emits "GRID READY n/n" and
//  the checkSignals loop tail always pushes the current summary line.
//  VALIDATION FIX PATCH 2026-08-26: direction labels + independent walk-forward validation
//  Pocket Option Auto Trader — content.js v23.0.0 — v19.0.5 base: TQS gate + gate diagnostics + curB-scope fix + market ranking + per-market risk + backup system + Tier 3 gate fix + LossMem time-decay recovery + graduated AI gate + reversal-aware RSI blocker · v19.0.6: confEma floor + tradeTypeStats backfill + calib soft mode in learning + LossMem saturation cap
//
//  v20.1.1 FIXES: restore reachable generic T3 fallback for SKIP setups; require
//  indicator-side dominance and AI-direction agreement when AI is decisive.
//
//  TIMEFRAME ARCHITECTURE:
//    BASKET/STORAGE = 5s  only for building higher-timeframe candles
//    30s expiry     = primary indicators on 30s + secondary confirmation on 15s
//    60s expiry     = primary indicators on 60s + secondary confirmation on 30s
//    Other expiries = primary = expiry TF; secondary = one step below
//    IMPORTANT: no strategy indicator, signal, reversal, or entry filter
//                 reads the raw 5s basket directly.
//
//  v7.3.0 CHANGES:
//  1. 5s data is aggregation/basket data only.
//  2. 30s trades use 30s primary + 15s secondary.
//  3. 60s trades use 60s primary + 30s secondary.
//  4. Removed 5s micro entry confirmation/reversal veto.
//  5. Runner timing and reversal persistence use the configured TFs.
//  6. Evaluation occurs when the secondary TF closes, not every raw 5s candle.
//// ═══════════════════════════════════════════════════════════════
(function () {
  'use strict';
  const KAOS_AUDIT_READ_ONLY = false;
  console.info('[KAOS BUILD] 1.7.22 · manual Start/Stop trading enabled');
  if (window.__poatContent137) return;
  window.__poatContent137 = true;

  // ── Bot state ────────────────────────────────────────────────
  let isRunning      = false;
  let botConfig      = null;
  // AI-controlled (autonomous) execution needs the server to say so: fail closed when unknown.
  let kaosAiExecutionAllowed = false;
  let kaosChartLimit = 1;  // server plan limit (Free 1, Pro 4, Ultimate 4); unknown -> 1
  function kaosApplyEntitlements(ent){
    const cl = Number(ent && ent.chartLimit);
    kaosChartLimit = Number.isInteger(cl) && cl > 0 ? Math.min(4, cl) : 1;
    kaosAiExecutionAllowed = !!(ent && ent.aiExecutionLocked === false && Array.isArray(ent.modes) && ent.modes.includes('AI'));
  }
  try {
    chrome.storage.local.get('kaosEntitlements', r => kaosApplyEntitlements(r && r.kaosEntitlements));
    chrome.storage.onChanged.addListener((c, area) => { if (area === 'local' && c.kaosEntitlements) kaosApplyEntitlements(c.kaosEntitlements.newValue); });
  } catch (_) {}
  let multiAssetMode = false;  // single (default) or multi-asset scanning
  let tradePending   = false;  // global: still used for single mode + staleness
  let currentAmount  = 5;
  let martLevel      = 0;
  let consecutiveLosses = 0;   // step mode
  let antiLevel      = 0;      // anti mode win streak
  let lastTradeDir   = null;
  let lastTradeAsset = '';
  let lastTradeAmt   = 0;
  let sessionWins    = 0;
  let sessionLosses  = 0;
  let sessionPnl     = 0;
  let lossStreak     = 0;
  let winStreak      = 0;
  let compoundLevel  = 0;
  let cooldownUntil  = 0;
  let compoundBase   = 0;
  let tradeIdCounter = 1;

  // ── Per-asset state (multi-asset mode) ───────────────────────
  const assetTradePending    = {};   // asset → boolean compatibility flag
  // B15.10.8 — up to two independently-qualified overlapping trades per visible market.
  const MAX_CONCURRENT_TRADES_PER_ASSET = 2;
  const assetOpenTradeCount = Object.create(null);
  const assetLastSetupKey = Object.create(null);
  const assetLastSetupAt = Object.create(null);
  const pendingSnapshotQueuesByAsset = Object.create(null);
  const openTradeCount = asset => Math.max(0, Number(assetOpenTradeCount[asset] || 0));
  const syncAssetPending = asset => (assetTradePending[asset] = openTradeCount(asset) > 0);
  const canOpenAnotherTrade = asset => openTradeCount(asset) < MAX_CONCURRENT_TRADES_PER_ASSET;
  const assetMartLevel       = {};   // asset → number
  const assetConsLosses      = {};   // asset → number (step mode)
  const assetAntiLevel       = {};   // asset → number (anti mode)
  const assetCurrentAmount   = {};   // asset → number

  function initAssetState(asset) {
    initChannelState(asset);
    if (!(asset in assetTradePending)) {
      assetTradePending[asset]  = false;
      assetOpenTradeCount[asset] = 0;
      assetMartLevel[asset]     = 0;
      assetConsLosses[asset]    = 0;
      assetAntiLevel[asset]     = 0;
      assetCurrentAmount[asset] = botConfig?.amount || 5;
    }
  }

  const assetLastTrade = {};   // assetName → timestamp of last trade
  let lastGateShown = '';              // V24.1.124: last status-bar reason pushed (dedupe)
  let gridAccountIsDemo = null;        // V24.1.130: tracks the PO account type for display/badge only.
                                       // The bot NEVER decides demo vs real — it follows the account
                                       // selected in the Pocket Option page (grid and single-chart).
  // V24.1.124 FULLY INDEPENDENT CHANNEL STATE: every grid channel owns its own
  // cooldown, consecutive-loss streak, indicator snapshot and debug reason, so
  // one channel losing or trading can never block or pace another channel.
  // Only STOP, session-level risk limits, AI model storage and the popup UI
  // remain global.
  const channelState = Object.create(null);
  function initChannelState(asset) {
    if (!channelState[asset]) {
      channelState[asset] = {
        cooldownUntil: 0,      // per-channel cooldown (multi mode only)
        cooldownReason: null,
        lossStreak: 0,         // per-channel consecutive losses (multi mode only)
        winStreak: 0,
        indicators: null,      // per-channel indicator snapshot for the debug panel
        lastDebugReason: 'IDLE',
        lastTradeAt: 0,
        lastLossAt: 0,
        lastLossDir: null,
        decisionHistory: [],   // V225: persistent last 20 evaluations for this chart
        debugSeq: 0,
        recentResults: []      // V276: rolling W/L market-health window
      };
    }
    return channelState[asset];
  }
  function gridChannelIndex(assetName) {
    if (!multiAssetMode) return 0;
    const idx = multiScanAssets().indexOf(assetName);
    return idx < 0 ? 0 : idx + 1;
  }
  const assetData      = {};
  const assetPayouts   = {};
  const assetAvailable = {};
  const knownAssets    = new Set();
  const MULTI_MIN_PAYOUT = 0; // V24.1.151: payout does not gate multi-chart eligibility

  // ── V24.1.131: payout floor · realized-EV rest · data-integrity scale guard ──
  const TRADE_MIN_PAYOUT_PCT = 0;           // V24.1.151: payout floor fully disabled
  const EV_REST_STORE_KEY = 'KAOSEvStateV131';  // chrome.storage.local key (per-asset EV windows)
  const EV_REST_ROLLING_WINDOW = 25;        // settled trades kept per asset (rolling)
  const EV_REST_PRIOR = 6;                  // shrinkage prior: +6 wins over +12 pseudo trades
  const EV_REST_MIN_TRADES = 25;            // settled trades needed before EV rest may veto
  const EV_REST_SAVE_DEBOUNCE_MS = 1500;
  const EV_REST_WR_HYSTERESIS = 0.004;      // 0.4pp hysteresis below payout breakeven winrate

  // ── V24.1.280: PAYOUT-AWARE ENTRY FLOOR (evidence-driven backstop) ─────────
  // Post-mortem of the 1004-trade log: 64 winning trades settled below 90% payout
  // and the low-payout tail cost ~191,390 in forgone profit, while the break-even
  // win rate climbs steeply as payout falls (52.08% @92%, 55.25% @81%, 68.49% @46%).
  // The grid already auto-rotates any chart under 92% (AUTO_SWITCH_BELOW_PCT), so
  // this constant is a BACKSTOP for residual / declared-low payouts that survive the
  // rotation. It is deliberately set BELOW the 92% switch threshold so it never
  // contradicts the switch policy. Set V280_PAYOUT_FLOOR_PCT = 0 to disable it.
  const V280_PAYOUT_FLOOR_PCT = 90;         // hard live-payout floor for a directional entry

  // ── V24.1.281: CONVICTION GATE (evidence-driven, intentionally LOOSE) ──────
  // Post-mortem of the 1004-trade log (WR 49.2%, break-even 52.97% at 88.8% mean
  // payout) isolated three structurally-losing buckets. Blocking only those keeps
  // ~56% of trade volume and lifts WR to ~52.6% (EV/trade -0.058 -> +0.006). The
  // rule is ASYMMETRIC on purpose: shorting into weakness did NOT mirror (the
  // bear side tested WORSE), consistent with the assets' mild upward drift.
  //   LEVEL 1 (~76% volume, WR 51.1%): block counter-trend LONG in a bear regime;
  //     block SHORT while RSI<30 (oversold).
  //   LEVEL 2 (~56% volume, WR 52.6%): also require a bull-regime BUY to show
  //     pullback pressure (sellScore>=3) — i.e. buy the dip, not the breakout tail.
  // Set V281_CONVICTION_ENABLED = false to disable; lower the LEVEL to loosen.
  const V281_CONVICTION_ENABLED = true;
  const V281_CONVICTION_LEVEL   = 2;   // 1 = loose · 2 = also require bull-pullback
  const V281_PULLBACK_MIN_SELL  = 3;   // LEVEL 2: min sellScore for a bull-regime BUY

  // ── V24.1.282: PARTICIPATION FLOOR + ROUTER/CONTROLLER UNIFICATION ─────────
  // The 2026-09-23 forensic export showed a PERMANENT HOLD: v194's RANGE/CHOP
  // router fired on `weakPersistence && backtracking` (no chop requirement) and
  // handed 34/40 decisions to the V227 range-reversal controller, which then
  // re-classified the SAME market with a STRICTER, different formula
  // (rangeLike needs chop>=42/38) and refused every handoff. The directional
  // engine rejects the same markets (no +/-10 structural edge), so the bot sat
  // out indefinitely -- directly contradicting the operator directive
  // "don't make it so tight it never makes a trade".
  //
  // V282 does two things:
  //   (1) UNIFICATION: the router verdict is authoritative. When v194 routes a
  //       chart to the range controller, the controller now honours the handoff
  //       instead of re-deriving a contradictory classification.
  //   (2) PARTICIPATION FLOOR: a bounded, per-asset escalation keyed to the
  //       consecutive-HOLD streak. After V282_HOLD_STREAK_TRIGGER HOLDs the
  //       structural need relaxes by one step and the range controller's
  //       edge/score thresholds widen by one tier; a second tier opens at
  //       V282_HOLD_STREAK_TIER2. The floor NEVER bypasses the payout floor (V280),
  //       EV rest, DANGER guards, the V276 severe-momentum veto, or the STOP
  //       invariant -- it only lets a qualified-but-not-perfect setup trade.
  const V282_PARTICIPATION_ENABLED   = true;
  const V282_HOLD_STREAK_TRIGGER     = 15;   // HOLDs before TIER 1 relaxation
  const V282_HOLD_STREAK_TIER2       = 40;   // HOLDs before TIER 2 relaxation
  const V282_DIR_STRUCTURAL_RELAX    = 2;    // structural need 10 -> 8 -> 6 signed
  const V282_RANGE_SCORE_FLOOR       = 64;   // V227 base score floor
  const V282_SCORE_RELAX_PER_TIER    = 4;    // score floor 64 -> 60 -> 56
  const V282_EDGE_BAND_RELAX         = 0.16; // band edge relax per tier
  const V282_EDGE_RSI_RELAX          = 6;    // RSI edge widen per tier
  const V282_STRONG_TREND_ADX        = 28;   // ADX that marks an expanding/directional market
  const V282_STRONG_TREND_MIN_SCORE  = 66;   // min confidence for the strong-trend V234 exception
  const DATA_GUARD_RATIO_MIN = 1 / 6;
  const DATA_GUARD_RATIO_MAX = 6;
  const DATA_GUARD_REJECT_PURGE = 15;       // scale rejects before the asset state is purged
  const DATA_GUARD_COOLDOWN_MS = 45 * 1000; // purge parks the channel/session 45s to re-warm
  const DATA_GUARD_REF_TAIL = 30;           // closes used for the median reference
  const DATA_GUARD_MIN_REF = 5;             // minimum closes before a scale reference exists

  // ── V24.1.133: user-cooldown veto parks (replaces the V24.1.131 hard-coded
  // PAYOUT_FLOOR_PARK_MS 60s and EV_REST_PARK_MS 30m parks) ─────────────────
  // The popup "cooldown after loss" setting is the source of truth. A payout-floor
  // veto or a realized-EV rest parks the channel/session for cooldownAfterLoss
  // seconds (never below VETO_MIN_PARK_SEC). When the user cooldown is 0 the
  // autoCooldownOn ladder applies — mirroring the loss-cooldown ladder exactly:
  // 3+ losses 5m, 5+ losses 15m, 8+ losses 60m (the 8-loss arm is an emergency
  // hard stop and always wins). Other emergency stops stay hard-coded and are
  // untouched: 8-loss 60m hard stop · RISK market ban · 30m maxLossStreak park.
  const VETO_MIN_PARK_SEC = 15;        // anti-spam floor for any veto park
  const VETO_LADDER_8_SEC  = 60 * 60;  // 8+ losses → 60m (emergency stop)
  const VETO_LADDER_5_SEC  = 15 * 60;  // 5+ losses → 15m
  const VETO_LADDER_3_SEC  = 5 * 60;   // 3+ losses → 5m

  // vetoParkSec(ch): whole SECONDS for a veto park. ch = per-channel state in
  // grid mode, or null in single mode (the global lossStreak is then the streak).
  function vetoParkSec(ch) {
    const userCd = parseInt(botConfig?.cooldownAfterLoss || 0, 10);
    if (Number.isFinite(userCd) && userCd > 0) return Math.max(VETO_MIN_PARK_SEC, userCd);
    const autoCdOn = botConfig?.autoCooldownOn !== false;
    const streakRef = ch ? (ch.lossStreak || 0) : lossStreak;
    if (autoCdOn && streakRef >= 8) return VETO_LADDER_8_SEC; // 8-loss emergency stop
    if (autoCdOn && streakRef >= 5) return VETO_LADDER_5_SEC;
    if (autoCdOn && streakRef >= 3) return VETO_LADDER_3_SEC;
    return VETO_MIN_PARK_SEC;
  }

  // parkTxt(sec): human park text — "45s" / "5m" / "2m 30s" for statuses.
  function parkTxt(sec) {
    const s = Math.max(0, Math.round(Number(sec) || 0));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60), r = s % 60;
    return r ? `${m}m ${r}s` : `${m}m`;
  }

  // ── V24.1.135 A1/A2: faster scan cadence + settle-linked re-scan ───────────
  const SIGNAL_SCAN_MS = 3000;           // A1: checkSignals cadence (was inline 5000 = 5s)
  const SETTLE_RESCAN_DELAY_MS = 400;    // A2: settle → forced re-scan delay

  const assetEvState = Object.create(null); // per-asset { seq:['w'|'l',…], pays:[…], updatedAt }
  let   assetEvSaveTimer = null;

  function evPersistSoon() {
    if (assetEvSaveTimer) clearTimeout(assetEvSaveTimer);
    assetEvSaveTimer = setTimeout(() => {
      assetEvSaveTimer = null;
      try {
        chrome.storage.local.set({ [EV_REST_STORE_KEY]: JSON.parse(JSON.stringify(assetEvState)) });
      } catch (e) { /* storage unavailable — EV rest degrades to in-memory only */ }
    }, EV_REST_SAVE_DEBOUNCE_MS);
  }

  function loadEvState() {
    try {
      chrome.storage.local.get(EV_REST_STORE_KEY, (data) => {
        const stored = data && data[EV_REST_STORE_KEY];
        if (!stored || typeof stored !== 'object') return;
        Object.keys(assetEvState).forEach(k => delete assetEvState[k]);
        Object.assign(assetEvState, stored);
      });
    } catch (e) { /* storage unavailable — start with empty EV windows */ }
  }

  // V24.1.131: record one settled trade into the per-asset realized-EV window.
  function recordEvRealized(asset, result, amount, profit) {
    if (!asset || (result !== 'win' && result !== 'loss')) return;
    const st = assetEvState[asset] || (assetEvState[asset] = { seq: [], pays: [], updatedAt: 0 });
    st.seq.push(result === 'win' ? 'w' : 'l');
    if (result === 'win') {
      const amt = Number(amount);
      let pay = (Number.isFinite(amt) && amt > 0) ? ((Number(profit) / amt) * 100) : 0;
      if (!Number.isFinite(pay) || pay <= 0) pay = payoutPct(asset);
      if (Number.isFinite(pay) && pay > 0) st.pays.push(pay);
      if (st.pays.length > EV_REST_ROLLING_WINDOW) st.pays.splice(0, st.pays.length - EV_REST_ROLLING_WINDOW);
    }
    if (st.seq.length > EV_REST_ROLLING_WINDOW) st.seq.splice(0, st.seq.length - EV_REST_ROLLING_WINDOW);
    st.updatedAt = Date.now();
    evPersistSoon();
  }

  // V24.1.131: single-shot veto that parks the channel/session while the rolling
  // realized winrate (shrinkage-adjusted, 0.4pp hysteresis) sits below the payout's
  // breakeven winrate. Clears the window so the market gets a fresh 25-trade sample
  // after the park expires instead of re-vetoing instantly.
  // V24.1.133: the park is no longer a hard-coded 30m — it follows the user's
  // popup cooldown semantics via vetoParkSec() (per channel in grid mode).
  function evRestDecision(asset, payRefLive) {
    const st = assetEvState[asset];
    const n = st && Array.isArray(st.seq) ? st.seq.length : 0;
    if (!st || n < EV_REST_MIN_TRADES) return { veto: false };
    let wins = 0;
    for (let i = 0; i < n; i++) if (st.seq[i] === 'w') wins++;
    let payRef = 0;
    if (wins >= 2 && Array.isArray(st.pays) && st.pays.length >= 2) {
      let s = 0;
      for (let i = 0; i < st.pays.length; i++) s += st.pays[i];
      payRef = s / st.pays.length;
    }
    if (!(payRef > 0)) payRef = Number(payRefLive) || 0;
    if (!(payRef > 0)) return { veto: false }; // no payout reference — cannot judge EV
    const breakeven = 100 / (100 + payRef); // winrate needed to break even at payRef payout
    const shrunkWr = (wins + EV_REST_PRIOR) / (n + EV_REST_PRIOR * 2);
    if (shrunkWr >= breakeven - EV_REST_WR_HYSTERESIS) return { veto: false };
    const chLabel = multiAssetMode ? `CH${gridChannelIndex(asset)} ${asset}` : asset;
    const parkSec = vetoParkSec(multiAssetMode ? initChannelState(asset) : null);
    const parkedReason = `${chLabel} · EV rest · ${wins}/${n} wins · wr ${(shrunkWr * 100).toFixed(1)}% < breakeven ${(breakeven * 100).toFixed(1)}% @ ${payRef.toFixed(1)}% payout · parked ${parkTxt(parkSec)}`;
    if (multiAssetMode) {
      const ch = initChannelState(asset);
      ch.cooldownUntil = Date.now() + parkSec * 1000;
      ch.cooldownReason = parkedReason;
      ch.lastDebugReason = `EV REST · parked ${parkTxt(parkSec)}`;
    } else {
      cooldownUntil = Date.now() + parkSec * 1000;
      lastDebugReason = `EV REST · ${asset} · parked ${parkTxt(parkSec)}`;
    }
    st.seq = [];
    st.pays = [];
    st.updatedAt = Date.now(); // fresh window after the park expires
    evPersistSoon();
    aiLog('TRADE_VETOED_EV_REST', { asset, wins, n, shrunkWr: +shrunkWr.toFixed(4), breakeven: +breakeven.toFixed(4), payRef: +payRef.toFixed(2), parkSec, parkMs: parkSec * 1000 }, true);
    return { veto: true, parkedReason };
  }

  // ── Data-integrity scale guard helpers (V24.1.131) ────────────────────────
  function guardMedian(vals) {
    const arr = Array.isArray(vals) ? vals.filter(v => Number.isFinite(Number(v)) && Number(v) > 0) : [];
    if (arr.length < DATA_GUARD_MIN_REF) return 0;
    const s = arr.map(Number).sort((x, y) => x - y);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  function guardRatioOk(price, med) {
    if (!(Number.isFinite(price) && price > 0 && Number.isFinite(med) && med > 0)) return true;
    const r = price / med;
    return r >= DATA_GUARD_RATIO_MIN && r <= DATA_GUARD_RATIO_MAX;
  }

  // V24.1.131: wipe one asset's price/indicator state in place and park its
  // channel 45s so it re-warms from clean data. Mirrors the MARKET_SWITCH cleanup.
  function guardPurgeAsset(asset, a) {
    if (!asset) return;
    const act = a || getAsset(asset);
    if (act) {
      act.prices = []; act.rates = {}; act.tf = {};
      act.lastBucket = null; act.lastClosed = -1; act.newCandle = false;
      act.lastPrice = 0; act.lastTickSec = 0; act._dgRejects = 0;
      delete act.__priceVisionState; delete act.__revState; delete act.__fastStructureState;
    }
    delete lastIndicatorCtx[asset];
    delete lastTickPrice[asset];
    delete microTicksByAsset[asset];
    delete microLastAssessment[asset];
    clearMicroPending(asset, 'data guard purge');
    delete assetTickCount[asset];
    if (window.__poatBurst) delete window.__poatBurst[asset];
    if (assetTradePending) assetTradePending[asset] = false;
    for (let i = pendingChartTrades.length - 1; i >= 0; i--) {
      if (pendingChartTrades[i].asset === asset) pendingChartTrades.splice(i, 1);
    }
    if (multiAssetMode) {
      const ch = initChannelState(asset);
      ch.cooldownUntil = Date.now() + DATA_GUARD_COOLDOWN_MS;
      ch.cooldownReason = 'data guard purge (scale mismatch)';
      ch.lastDebugReason = `Data guard · state purged · parked ${Math.round(DATA_GUARD_COOLDOWN_MS / 1000)}s`;
    } else {
      cooldownUntil = Date.now() + DATA_GUARD_COOLDOWN_MS;
      lastDebugReason = `Data guard · ${asset} state purged · parked ${Math.round(DATA_GUARD_COOLDOWN_MS / 1000)}s`;
    }
    sendStatus(`🧹 DATA GUARD · ${asset} scale mismatch · state purged · re-warming ${Math.round(DATA_GUARD_COOLDOWN_MS / 1000)}s`);
    aiLog('DATA_GUARD_PURGED', { asset, parkMs: DATA_GUARD_COOLDOWN_MS }, true);
  }

  // V24.1.131: reject a live tick whose price scale deviates >6× or <1/6× from the
  // recent-close median. Returns true = caller must drop the tick. Counts rejects on
  // the asset (no reset on recovery) and purges at DATA_GUARD_REJECT_PURGE.
  function guardRejectTickScale(asset, price, a) {
    if (!asset || !a || !Array.isArray(a.prices)) return false;
    const med = guardMedian(a.prices.slice(-DATA_GUARD_REF_TAIL));
    if (!(med > 0)) return false; // no reference yet — cannot judge scale
    if (guardRatioOk(price, med)) return false;
    a._dgRejects = (a._dgRejects || 0) + 1;
    const k = a._dgRejects;
    const ratio = price / med;
    const dir = ratio >= 1 ? `${ratio.toFixed(2)}× above` : `${(1 / ratio).toFixed(2)}× below`;
    if (k === 1 || k % 50 === 0) {
      sendStatus(`⚠️ DATA GUARD · ${asset} tick ${dir} median ${med} · ${k} rejects`);
      aiLog('DATA_GUARD_TICK_REJECT', { asset, price, med, ratio: Math.abs(ratio), rejects: k }, k === 1);
    }
    if (k >= DATA_GUARD_REJECT_PURGE) {
      guardPurgeAsset(asset, a);
      return true;
    }
    return true;
  }

  // V24.1.131: veto seeding/merging a HISTORY snapshot whose scale contradicts the
  // live close median. Cold live (no reference yet) always accepts the first seed.
  function guardRejectHistoryScale(asset, hist, a) {
    if (!asset || !Array.isArray(hist) || !a || !Array.isArray(a.prices)) return false;
    const liveMed = guardMedian(a.prices.slice(-DATA_GUARD_REF_TAIL));
    if (!(liveMed > 0)) return false; // cold live — accept history as the initial seed
    const histMed = guardMedian(hist.slice(-DATA_GUARD_REF_TAIL));
    if (!(histMed > 0)) return false;
    if (guardRatioOk(histMed, liveMed)) return false;
    const ratio = histMed / liveMed;
    const dir = ratio >= 1 ? `${ratio.toFixed(2)}× above` : `${(1 / ratio).toFixed(2)}× below`;
    aiLog('DATA_GUARD_HISTORY_REJECT', { asset, histMed, liveMed, ratio: Math.abs(ratio) }, false);
    sendStatus(`⚠️ DATA GUARD · ${asset} HISTORY ${dir} live · seed skipped`);
    return true; // skip this history snapshot
  }

  // ── V24.1.132: grid payout-floor auto-switch — rotate a <80% slot to a ≥92% market ──
  const PAYOUT_SWITCH_DEBOUNCE_MS = 15 * 1000;      // V276: brief anti-flap gap; re-check payout continuously
  const PAYOUT_SWITCH_AWAY_TTL_MS = 10 * 60 * 1000; // do not re-target a market we just left or failed to reach
  const PAYOUT_SWITCH_TIMEOUT_MS = 8 * 1000;        // bridge SWITCH_ASSET_SLOT confirmation timeout
  const AUTO_SWITCH_BELOW_PCT = 90;                // B15.10.9: keep any visible chart at >=90%; rotate only when live payout falls below 90%
  const AUTO_SWITCH_TARGET_PCT = 92;                // B15.10.9: replacement target must be >=92%
  const PERF_ROTATE_WINDOW = 20;                    // V276: react before a weak market can bleed for 20 trades
  const PERF_ROTATE_MIN_TRADES = 12;                 // early enough to protect the session, large enough to avoid 2-3 trade noise
  const PERF_ROTATE_MIN_LOSSES = 6;                 // deterioration must include real losses
  const PERF_ROTATE_EDGE_BUFFER = 0.00;             // rotate only below payout-adjusted break-even
  const PERF_ROTATE_AWAY_TTL_MS = 30 * 60 * 1000;  // failing market stays out longer before it may be selected again

  loadEvState(); // V24.1.131: restore persisted realized-EV windows
  const assetTickCount = {};
  let   activeAsset    = '';
  let   chartSelectedAsset = '';
  // V24.1.97: single-mode market is locked for the whole run. Background
  // tick bursts may populate data, but they can never change the trade asset.
  let   sessionLockedAsset = '';
  // V121: fixed four-chart grid mode. The four visible Pocket Option panels are
  // the complete market set for this run. Each panel warms, evaluates and trades
  // independently; there is no off-screen rotation or chart switching.
  const favoriteAssets = new Set();
  let   favoritesSyncedAt = 0;
  let   favoriteSyncTimer = null;
  let   gridRefreshTimer = null;
  const pendingChartTrades = [];
  const visibleChartSlots = Object.create(null); // slotId -> asset
  // ── V24.1.132: grid payout-floor auto-switch state ───────────────────
  const slotSwitchPending  = Object.create(null); // slotId -> { fromAsset, toAsset, at }
  const payoutSwitchAwayAt = Object.create(null); // asset -> ts: left this <80% market; no bounce-back
  const payoutSwitchFailAt = Object.create(null); // asset -> ts: switch to this ≥92% market failed/timed out
  const slotLastSwitchAt   = Object.create(null); // slotId -> ts: last payout-switch attempt (5-min debounce)
  let   gridRotationCursor = 0;
  let   pendingChartSwitchAsset = '';
  let   pendingChartSwitchSlot = '';
  let   pendingChartSwitchAt = 0;
  let   chartSelectedAt = 0;
  let   lastStartedAsset = '';
  const assetStaleTimers = Object.create(null);
  const assetMartTimers  = Object.create(null);

  // ── Live debug state (popup panel) ──
  const DEBUG_TRADE_LOG_MAX = 20;
  // V24.1.168 MULTI-ASSET STATE ISOLATION
  // Every chart gets its own indicator workspace. Legacy strategy/core code still
  // reads/writes `lastIndicators`, but evalAssetSignal switches that reference to
  // the asset being evaluated before ANY indicator calculation. This prevents
  // RSI/EMA/ATR/structure/quality state from one grid chart leaking into another.
  function newIndicatorState() {
    return {
      rsi: null, ema5: null, ema9: null, ema21: null,
      atr: null, stoch: null, stochD: null, macd: null, macdSignal: null,
      bollUpper: null, bollLower: null, keltUpper: null, keltLower: null,
      buyScore: 0, sellScore: 0,
      aiAccuracy: 0
    };
  }
  const indicatorStateByAsset = Object.create(null);
  let lastIndicators = newIndicatorState();
  function useIndicatorState(asset) {
    const key = String(asset || '__single__');
    if (!indicatorStateByAsset[key]) indicatorStateByAsset[key] = newIndicatorState();
    lastIndicators = indicatorStateByAsset[key];
    return lastIndicators;
  }
  let lastDebugReason = 'IDLE';
  let lastDebugAt = 0;
  let lastGridPanelCount = 4; // V24.1.134: visible-panel count from the last multi-grid scan (assume full grid) — drives one-shot partial-grid notices
  const debugState = { trades: [] };
  // Persistent AI audit log: model lifecycle, imports, warmup, predictions,
  // ensemble decisions, training results, errors, and trade outcomes.
  const AI_EVENT_LOG_MAX = 2000;
  const AI_EVENT_LOG = [];
  let aiLogLastPersist = 0;
  function aiLog(event, data = {}, persist = false) {
    const row = { ts: Date.now(), event: String(event), ...(data && typeof data === 'object' ? data : {message:String(data)}) };
    AI_EVENT_LOG.push(row);
    if (AI_EVENT_LOG.length > AI_EVENT_LOG_MAX) AI_EVENT_LOG.splice(0, AI_EVENT_LOG.length - AI_EVENT_LOG_MAX);
    try { console.info('[AI-AUDIT]', row); } catch (_) {}
    if (persist || Date.now() - aiLogLastPersist > 1500) {
      aiLogLastPersist = Date.now();
      try { chrome.runtime.sendMessage({type:'AI_EVENT_LOG', entry:row}).catch(()=>{}); } catch (_) {}
    }
    return row;
  }

  // ── FULL-FIDELITY TRADE RECORDS (CSV export / analysis) ──
  // Every completed trade keeps a full snapshot: candle OHLC, indicators,
  // scores, reasons — captured at signal time, completed at result time.
  const TRADE_RECORD_MAX = 5000;      // memory bound; popup export merges this store
  const DECISION_HISTORY_MAX = 12000; // every AI evaluation, including HOLDs
  const decisionHistory = [];
  const decisionPending = [];
  let decisionIdCounter = 1;
  const tradeRecords    = [];         // finished trades, newest at the end

  // V24.1.183 — ALL-HORIZON SHADOW OUTCOME TRACKER
  // Every qualified strategy signal is measured at every supported horizon.
  // Measurement only: these timers never place orders or change execution decisions.
  const SHADOW_OUTCOME_MAX = 5000;
  const SHADOW_HORIZONS = Object.freeze([
    ['5s',5000], ['15s',15000], ['30s',30000], ['60s',60000],
    ['120s',120000], ['180s',180000], ['300s',300000]
  ]);
  const makeShadowStat=()=>({total:0,wins:0,losses:0,draws:0});
  const shadowOutcomeState = { records: [], stats: Object.fromEntries(SHADOW_HORIZONS.map(([h])=>[h,makeShadowStat()])), bySetup: {}, byContext: {} };
  let shadowOutcomeId = 1;

  function shadowOutcomeResult(dir, entry, exit) {
    const e=Number(entry), x=Number(exit);
    if (!Number.isFinite(e) || !Number.isFinite(x) || e<=0 || x<=0) return null;
    const d=String(dir||'').toUpperCase();
    const eps=Math.max(1e-12, Math.abs(e)*1e-10);
    if (Math.abs(x-e) <= eps) return 'draw';
    if (d==='BUY') return x>e ? 'win' : 'loss';
    if (d==='SELL') return x<e ? 'win' : 'loss';
    return null;
  }

  function shadowEnsureSchema() {
    if(!shadowOutcomeState.stats || typeof shadowOutcomeState.stats!=='object') shadowOutcomeState.stats={};
    if(!shadowOutcomeState.bySetup || typeof shadowOutcomeState.bySetup!=='object') shadowOutcomeState.bySetup={};
    if(!shadowOutcomeState.byContext || typeof shadowOutcomeState.byContext!=='object') shadowOutcomeState.byContext={};
    for(const [h] of SHADOW_HORIZONS) if(!shadowOutcomeState.stats[h]) shadowOutcomeState.stats[h]=makeShadowStat();
    for(const bs of Object.values(shadowOutcomeState.bySetup)) {
      if(!bs || typeof bs!=='object') continue;
      for(const [h] of SHADOW_HORIZONS) if(!bs[h]) bs[h]=makeShadowStat();
    }
    for(const bs of Object.values(shadowOutcomeState.byContext)) {
      if(!bs || typeof bs!=='object') continue;
      for(const [h] of SHADOW_HORIZONS) if(!bs[h]) bs[h]=makeShadowStat();
    }
  }

  function shadowOutcomeBump(horizon, result, setup, rec=null) {
    shadowEnsureSchema();
    if (!result || !shadowOutcomeState.stats[horizon]) return;
    const st=shadowOutcomeState.stats[horizon];
    st.total++;
    if (result==='win') st.wins++; else if (result==='loss') st.losses++; else st.draws++;
    const key=String(setup||'UNKNOWN');
    const bs=shadowOutcomeState.bySetup[key] || (shadowOutcomeState.bySetup[key]={});
    for(const [h] of SHADOW_HORIZONS) if(!bs[h]) bs[h]=makeShadowStat();
    const b=bs[horizon]; b.total++;
    if (result==='win') b.wins++; else if (result==='loss') b.losses++; else b.draws++;
    if(rec){
      const regime=String(rec.regime||'UNKNOWN'), dir=String(rec.dir||'UNKNOWN');
      const ck=`${key}|${dir}|${regime}`;
      const cs=shadowOutcomeState.byContext[ck] || (shadowOutcomeState.byContext[ck]={});
      for(const [h] of SHADOW_HORIZONS) if(!cs[h]) cs[h]=makeShadowStat();
      const c=cs[horizon]; c.total++;
      if(result==='win') c.wins++; else if(result==='loss') c.losses++; else c.draws++;
    }
  }

  function persistShadowOutcomeState() {
    // V195 QUOTA-SAFE: raw shadow records remain in RAM/full manual backup.
    // chrome.storage.local keeps only compact aggregate telemetry so multi-horizon
    // research cannot exhaust the extension storage quota.
    try {
      const r=chrome.storage.local.set({ shadowOutcomeState: {
        records: [], stats: shadowOutcomeState.stats, bySetup: shadowOutcomeState.bySetup,
        byContext: shadowOutcomeState.byContext, shadowOutcomeId, quotaSafe:true
      }});
      if(r && typeof r.catch==='function') r.catch(()=>{});
    } catch(_) {}
  }

  function resolveShadowOutcome(id, horizon) {
    const rec=shadowOutcomeState.records.find(r=>r.id===id);
    if (!rec || rec[horizon]?.result) return;
    const exit=Number((getAsset(rec.asset)||{}).lastPrice || lastTickPrice[rec.asset] || 0);
    const result=shadowOutcomeResult(rec.dir, rec.entryPrice, exit);
    if (!result) return;
    rec[horizon]={result,exitPrice:exit,resolvedAt:Date.now()};
    shadowOutcomeBump(horizon,result,rec.setup,rec);
    // V24.1.184: train the horizon-specific AI on market direction, not trade P/L.
    // UP=1 / DOWN=0 preserves one label meaning across BUY and SELL setups.
    if(Array.isArray(rec.x) && rec.x.length===AI_FEATURES){
      const eps=Math.max(1e-12,Math.abs(Number(rec.entryPrice)||0)*1e-10);
      if(Math.abs(exit-Number(rec.entryPrice))>eps){
        const marketUp=exit>Number(rec.entryPrice)?1:0;
        rec[horizon].ai=mhTrain(horizon,rec.x,marketUp,{asset:rec.asset,setup:rec.setup,dir:rec.dir,signalTs:rec.ts});
        persistShadowHorizonAI();
      }
    }
    persistShadowOutcomeState();
    const st=shadowOutcomeState.stats[horizon];
    const wr=x=>x.total ? (100*x.wins/Math.max(1,x.wins+x.losses)).toFixed(1) : '—';
    aiLog('SHADOW_HORIZON_RESULT',{asset:rec.asset,dir:rec.dir,setup:rec.setup,horizon,result,entry:rec.entryPrice,exit,winRate:wr(st)},false);
    if(horizon==='180s') {
      const summary=SHADOW_HORIZONS.map(([h])=>`${h} ${wr(shadowOutcomeState.stats[h])}%`).join(' · ');
      console.info(`[SHADOW ALL] ${rec.asset} ${rec.dir} ${rec.setup} · ${summary}`);
    }
  }

  function queueShadowOutcomeComparison(assetName, sig, entryPrice) {
    const px=Number(entryPrice || (getAsset(assetName)||{}).lastPrice || lastTickPrice[assetName] || 0);
    const dir=String(sig?.dir||'').toUpperCase();
    if (!assetName || !px || (dir!=='BUY' && dir!=='SELL')) return null;
    const indCtx=lastIndicatorCtx?.[assetName]?.ctx || null;
    const fx=aiFeatures(assetName,px,indCtx);
    const regime=String(v189Context(assetName)?.state || lastIndicatorCtx?.[assetName]?.ctx?.regime || 'UNKNOWN');
    const rec={id:shadowOutcomeId++,ts:Date.now(),asset:assetName,dir,regime,
      setup:String(sig?.tradeType||sig?.mode||'TRADE'),score:Number(sig?.str||0),confidence:Number(sig?.confidence||0),entryPrice:px,
      x:Array.isArray(fx)&&fx.length===AI_FEATURES?fx.slice():null,
      aiPredictions:Object.fromEntries(SHADOW_HORIZONS.map(([h])=>[h,mhPredict(h,fx)]))};
    for(const [h] of SHADOW_HORIZONS) rec[h]={result:null,exitPrice:null,resolvedAt:null};
    shadowOutcomeState.records.push(rec);
    if (shadowOutcomeState.records.length>SHADOW_OUTCOME_MAX) shadowOutcomeState.records.splice(0,shadowOutcomeState.records.length-SHADOW_OUTCOME_MAX);
    for(const [h,ms] of SHADOW_HORIZONS) setTimeout(()=>resolveShadowOutcome(rec.id,h),ms);
    return rec.id;
  }

  try {
    chrome.storage.local.get('shadowOutcomeState', d=>{
      const x=d?.shadowOutcomeState; if(!x||typeof x!=='object') return;
      if(Array.isArray(x.records)) shadowOutcomeState.records=x.records.slice(-SHADOW_OUTCOME_MAX);
      if(x.stats&&typeof x.stats==='object') shadowOutcomeState.stats=x.stats;
      if(x.bySetup&&typeof x.bySetup==='object') shadowOutcomeState.bySetup=x.bySetup;
      if(x.byContext&&typeof x.byContext==='object') shadowOutcomeState.byContext=x.byContext;
      shadowEnsureSchema();
      shadowOutcomeId=Math.max(Number(x.shadowOutcomeId||1), ...shadowOutcomeState.records.map(r=>Number(r.id||0)+1), 1);
    });
  } catch(_) {}

  // V24.1.232 — SAME-COLOR 30s BASELINE BENCHMARK + PREDICTIVE ENGINE
  // Every visible chart gets one shadow prediction per newly closed 30s candle:
  // green previous candle => BUY, red previous candle => SELL. It never clicks.
  // This is the deliberately simple baseline the live decision engine must beat.
  const sameColorBaseline = {version:1, overall:makeShadowStat(), byAsset:{}, recent:[], lastBucket:{}};
  function v231BaselineStat(asset){ return sameColorBaseline.byAsset[asset] || (sameColorBaseline.byAsset[asset]=makeShadowStat()); }
  function v231BumpBaseline(asset,result){
    for(const st of [sameColorBaseline.overall,v231BaselineStat(asset)]){
      st.total++; if(result==='win')st.wins++; else if(result==='loss')st.losses++; else st.draws++;
    }
  }
  function v231ResolveBaseline(rec){
    const exit=Number((getAsset(rec.asset)||{}).lastPrice || lastTickPrice[rec.asset] || 0);
    const result=shadowOutcomeResult(rec.dir,rec.entryPrice,exit); if(!result)return;
    rec.result=result; rec.exitPrice=exit; rec.resolvedAt=Date.now(); v231BumpBaseline(rec.asset,result);
    try{ chrome.storage.local.set({sameColorBaseline:{version:1,overall:sameColorBaseline.overall,byAsset:sameColorBaseline.byAsset,recent:sameColorBaseline.recent.slice(-120),lastBucket:sameColorBaseline.lastBucket}}).catch(()=>{}); }catch(_){}
  }
  function v231QueueSameColorBaseline(assetName){
    const a=getAsset(assetName); if(!a)return;
    const p=v181Series(assetName,'30s'); if(!Array.isArray(p)||p.length<3)return;
    const bucket=Math.floor(Date.now()/30000);
    if(sameColorBaseline.lastBucket[assetName]===bucket)return;
    // Wait until just after the boundary so p[-1] is the fully closed previous candle.
    const tf=a.tf?.['30s']; const candles=Array.isArray(tf?.candles)?tf.candles:null;
    let o=null,c=null;
    if(candles?.length){ const q=candles[candles.length-1]; o=Number(q?.open); c=Number(q?.close); }
    if(!Number.isFinite(o)||!Number.isFinite(c)){ c=Number(p[p.length-1]); o=Number(p[p.length-2]); }
    if(!Number.isFinite(o)||!Number.isFinite(c)||Math.abs(c-o)<=Math.max(1e-12,Math.abs(c)*1e-10))return;
    const dir=c>o?'BUY':'SELL'; const entry=Number(a.lastPrice||lastTickPrice[assetName]||0); if(!entry)return;
    sameColorBaseline.lastBucket[assetName]=bucket;
    const rec={ts:Date.now(),asset:assetName,dir,previousOpen:o,previousClose:c,entryPrice:entry,result:null,exitPrice:null};
    sameColorBaseline.recent.push(rec); if(sameColorBaseline.recent.length>240)sameColorBaseline.recent.splice(0,sameColorBaseline.recent.length-240);
    setTimeout(()=>v231ResolveBaseline(rec),30000);
  }
  setInterval(()=>{ if(!isRunning)return; try{ for(const a of (multiAssetMode?multiScanAssets():[activeAsset]).filter(Boolean)) v231QueueSameColorBaseline(a); }catch(_){} },750);
  try{ chrome.storage.local.get('sameColorBaseline',d=>{const x=d?.sameColorBaseline;if(!x)return;Object.assign(sameColorBaseline.overall,x.overall||{});sameColorBaseline.byAsset=x.byAsset||{};sameColorBaseline.recent=Array.isArray(x.recent)?x.recent.slice(-120):[];sameColorBaseline.lastBucket=x.lastBucket||{};}); }catch(_){}

  function v231PredictiveEvidence(assetName, px, dir){
    try{
      const x=aiFeatures(assetName,px,lastIndicatorCtx?.[assetName]?.ctx||null); if(!Array.isArray(x)||x.length!==AI_FEATURES)return {points:0,ready:false};
      const m=shadowHorizonAI.models?.['30s']||{}; const n=Number(m.trained||0), total=Number(m.total||m.trained||0), correct=Number(m.correct||0);
      const hit=total>0?correct/total:0; const p=mhPredict('30s',x); const aligned=dir==='BUY'?p:1-p;
      // AI earns authority only after enough resolved live/back-data labels and > random historical hit rate.
      if(n<40 || hit<0.53) return {points:0,ready:false,trained:n,hitRate:hit,up:p,aligned};
      let points=0;
      if(aligned>=0.68)points=8; else if(aligned>=0.60)points=5; else if(aligned>=0.55)points=2;
      else if(aligned<=0.32)points=-10; else if(aligned<=0.40)points=-6; else if(aligned<=0.45)points=-3;
      return {points,ready:true,trained:n,hitRate:hit,up:p,aligned};
    }catch(_){return {points:0,ready:false};}
  }

  // ════════════════════════════════════════════════════════════
  // V24.1.234 — UNIVERSAL EXPERIENCE MEMORY
  // Capture EVERY 30s opportunity on EVERY visible chart, including HOLDs and
  // same-color shadows. Freeze the complete pre-outcome state, then attach
  // future labels at 30/60/120/180/300s. This is learning telemetry; outcomes
  // never leak into the feature snapshot used to make the prediction.
  const EXPERIENCE_MAX = 6000;
  const experienceMemory = {version:1, records:[], byAsset:{}, lastBucket:{}, resolved30:0};
  let experienceId = 1;
  function v234Safe(v,depth=0){
    if(depth>3) return null;
    if(v==null || typeof v==='string' || typeof v==='boolean') return v;
    if(typeof v==='number') return Number.isFinite(v)?v:null;
    if(Array.isArray(v)) return v.slice(-20).map(x=>v234Safe(x,depth+1));
    if(typeof v==='object') { const o={}; for(const [k,x] of Object.entries(v).slice(0,120)) { if(typeof x!=='function') o[k]=v234Safe(x,depth+1); } return o; }
    return null;
  }
  function v234Frame(asset,tf){
    try{ const f=v198FrameScore(asset,tf); if(!f)return null; return v234Safe({tf,ready:f.ready,n:f.n,trend:f.trend,momentum:f.momentum,rsi:f.rsi,adx:f.adx,chop:f.chop,pathEfficiency:f.pathEfficiency,bandSigned:f.bandSigned,signedExtension:f.signedExtension,atr:f.atr,ema5:f.ema5,ema9:f.ema9,ema21:f.ema21,stochK:f.stochK,stochD:f.stochD,macd:f.macd,macdSignal:f.macdSignal}); }catch(_){return null;}
  }
  function v234Candles(asset,tf,n=12){
    try{ const a=getAsset(asset), c=a?.tf?.[tf]?.candles; if(!Array.isArray(c))return []; return c.slice(-n).map(q=>({t:q.t??q.time??null,open:Number(q.open),high:Number(q.high),low:Number(q.low),close:Number(q.close)})); }catch(_){return [];}
  }
  function v234LatestDecision(asset){
    try{ const h=channelState?.[asset]?.decisionHistory; return Array.isArray(h)&&h.length?v234Safe(h[h.length-1]):null; }catch(_){return null;}
  }
  function v234BaselineDir(asset){
    try{ const p=v181Series(asset,'30s'), a=getAsset(asset), c=a?.tf?.['30s']?.candles; let o,cx; if(Array.isArray(c)&&c.length){const q=c[c.length-1];o=Number(q.open);cx=Number(q.close);} else {o=Number(p[p.length-2]);cx=Number(p[p.length-1]);} if(!Number.isFinite(o)||!Number.isFinite(cx)||o===cx)return 'DRAW'; return cx>o?'BUY':'SELL'; }catch(_){return null;}
  }
  function v234Outcome(entry,exit){ const eps=Math.max(1e-12,Math.abs(entry)*1e-10); if(Math.abs(exit-entry)<=eps)return 'DRAW'; return exit>entry?'BUY':'SELL'; }
  function v234Resolve(id,h){
    const rec=experienceMemory.records.find(r=>r.id===id); if(!rec||rec.labels?.[h])return;
    const exit=Number((getAsset(rec.asset)||{}).lastPrice||lastTickPrice[rec.asset]||0); if(!exit)return;
    const actual=v234Outcome(rec.entryPrice,exit); const label={resolvedAt:Date.now(),exitPrice:exit,actualDirection:actual,buyResult:actual==='BUY'?'win':actual==='SELL'?'loss':'draw',sellResult:actual==='SELL'?'win':actual==='BUY'?'loss':'draw'};
    const base=rec.sameColorDirection; label.sameColorResult=base==='BUY'?label.buyResult:base==='SELL'?label.sellResult:'draw';
    const bot=rec.botDecision?.dir; label.botResult=bot==='BUY'?label.buyResult:bot==='SELL'?label.sellResult:'hold';
    const xgb=Number(rec.models?.xgbUp), lgb=Number(rec.models?.lgbUp), online=Number(rec.models?.onlineUp);
    label.xgbResult=Number.isFinite(xgb)?((xgb>=.5?'BUY':'SELL')===actual?'win':actual==='DRAW'?'draw':'loss'):'na';
    if(rec.aiPaperTrade){
      rec.aiPaperTrade.result=label.xgbResult; rec.aiPaperTrade.exitPrice=exit; rec.aiPaperTrade.resolvedAt=Date.now();
      rec.aiPaperTrade.actualDirection=actual; rec.aiPaperTrade.changePct=(exit-rec.entryPrice)/Math.max(Math.abs(rec.entryPrice),1e-12);
      rec.aiPaperTrade.outcomeWhy=`Predicted ${rec.aiPaperTrade.dir}; market finished ${actual} after 30s (${(rec.aiPaperTrade.changePct*100).toFixed(4)}%). The model trains on the frozen 104-feature entry snapshot plus this future-direction label.`;
    }
    label.lgbResult=Number.isFinite(lgb)?((lgb>=.5?'BUY':'SELL')===actual?'win':actual==='DRAW'?'draw':'loss'):'na';
    label.onlineResult=Number.isFinite(online)?((online>=.5?'BUY':'SELL')===actual?'win':actual==='DRAW'?'draw':'loss'):'na';
    // Attribution candidates are descriptive measurements, not claimed causes.
    label.analysis={botEntered:bot==='BUY'||bot==='SELL',botReason:rec.botDecision?.reason||rec.botDecision?.debug||null,baselineBeatBot:(label.sameColorResult==='win'&&label.botResult!=='win'),framesAtEntry:rec.frameSummary};
    rec.labels[h]=label;
    if(actual!=='DRAW' && Array.isArray(rec.features) && rec.features.length===AI_FEATURES){ mhTrain(h,rec.features,actual==='BUY'?1:0,{asset:rec.asset,setup:'EVERY_30S_OPPORTUNITY',dir:bot||'HOLD',signalTs:rec.ts}); persistShadowHorizonAI(); }
    if(h==='30s') experienceMemory.resolved30++;
  }
  function v234Capture(asset){
    const a=getAsset(asset); if(!a||!aiMarketWarmupReady(asset))return;
    const bucket=Math.floor(Date.now()/30000); if(experienceMemory.lastBucket[asset]===bucket)return;
    const px=Number(a.lastPrice||lastTickPrice[asset]||0); if(!px)return;
    const ctx=lastIndicatorCtx?.[asset]?.ctx||null, x=aiFeatures(asset,px,ctx); if(!Array.isArray(x)||x.length!==AI_FEATURES)return;
    experienceMemory.lastBucket[asset]=bucket;
    const frames={}; for(const tf of ['5s','15s','30s','60s','120s','180s','300s']) frames[tf]=v234Frame(asset,tf);
    const decision=v234LatestDecision(asset);
    let lab={}; try{lab=aiLabScore(x,asset)||{};}catch(_){}
    const xgbUp=Number.isFinite(Number(lab.xgboost))?Number(lab.xgboost):null;
    const aiPaperDir=xgbUp==null?'WAIT':(xgbUp>=0.5?'BUY':'SELL');
    const aiPaperConfidence=xgbUp==null?0:Math.max(xgbUp,1-xgbUp);
    const rec={id:experienceId++,ts:Date.now(),bucket,asset,entryPrice:px,features:x.slice(),sameColorDirection:v234BaselineDir(asset),botDecision:decision,
      aiPaperTrade:{dir:aiPaperDir,confidence:aiPaperConfidence,reason:`XGBoost ${aiPaperDir} ${(aiPaperConfidence*100).toFixed(1)}% · regime ${ctx?.regime||'UNKNOWN'} · bot ${decision?.dir||'HOLD'} · ${decision?.reason||decision?.debug||'no live setup'}`},
      models:{onlineUp:mhPredict('30s',x),xgbUp,lgbUp:Number.isFinite(Number(lab.lightgbm))?Number(lab.lightgbm):null},
      indicators:v234Safe(ctx),frames,candles:Object.fromEntries(['5s','15s','30s','60s','120s','180s','300s'].map(tf=>[tf,v234Candles(asset,tf,12)])),
      frameSummary:Object.fromEntries(Object.entries(frames).map(([tf,f])=>[tf,f?{trend:f.trend,momentum:f.momentum,rsi:f.rsi,adx:f.adx,extension:f.signedExtension}:null])),labels:{}};
    experienceMemory.records.push(rec); if(experienceMemory.records.length>EXPERIENCE_MAX)experienceMemory.records.splice(0,experienceMemory.records.length-EXPERIENCE_MAX);
    const st=experienceMemory.byAsset[asset]||(experienceMemory.byAsset[asset]={captured:0}); st.captured++;
    // Feed the canonical native/XGB dataset on every opportunity too; canonical dedupe prevents duplicates.
    try{ aiQueueSample(asset,px,'universal',ctx,null,{tradeType:'EVERY_30S_OPPORTUNITY',setupType:'EVERY_30S_OPPORTUNITY',marketClass:ctx?.regime||'UNKNOWN',classifierDecision:decision?.dir||'HOLD'}); }catch(_){}
    for(const [h,ms] of [['30s',30000],['60s',60000],['120s',120000],['180s',180000],['300s',300000]]) setTimeout(()=>v234Resolve(rec.id,h),ms);
  }
  setInterval(()=>{ if(!isRunning)return; try{for(const a of (multiAssetMode?multiScanAssets():[activeAsset]).filter(Boolean))v234Capture(a);}catch(_){} },750);

  let   pendingSnapshot = null;       // single-mode compatibility snapshot
  const pendingSnapshotsByAsset = Object.create(null);
  const lastTickPrice   = {};         // asset → most recent stream price (entry/exit approx)


  // ════════════════════════════════════════════════════════════
  //  ADAPTIVE AI — 30 SECOND DIRECTION PREDICTOR
  //  This is an on-device online-learning model. It never uses future
  //  candles while making a prediction. Each sample is labeled only after
  //  its 30s horizon has elapsed, then the model updates its weights.
  // ════════════════════════════════════════════════════════════
  // V24.1.177: the candidate was discovered against the stored 30s outcome labels.
  // AI remains learning-only; the target is restored to the same 30s horizon used by the backtest.
  const AI_HORIZON_MS = 30000;
  const AI_BACKUP_SCHEMA = 7;
  const AI_FEATURES = 104;              // V219: 88 market/indicator + 16 rolling visual/video features               // 76 prior + 12 dedicated 15s fast-context features (v24.1.99)

  // V24.1.184 — MULTI-HORIZON SHADOW AI
  // Seven independent online logistic learners consume the exact 88-feature
  // snapshot captured when a qualified strategy signal appears.  Each learner
  // receives its own future-market UP/DOWN label only when that horizon resolves.
  // These models are learning/telemetry only and NEVER approve, veto or modify trades.
  const MH_AI_MAX_SAMPLES = 5000;
  const MH_AI_LR = 0.012;
  const MH_AI_L2 = 0.00015;
  const makeMhModel = h => ({horizon:h,w:new Array(AI_FEATURES).fill(0),b:0,trained:0,correct:0,total:0,up:0,down:0,last:null});
  const shadowHorizonAI = {
    version:1,
    models:Object.fromEntries(SHADOW_HORIZONS.map(([h])=>[h,makeMhModel(h)])),
    samples:[],
    bySetup:{},
    updatedAt:0
  };

  function mhSigmoid(z){ z=Math.max(-20,Math.min(20,Number(z)||0)); return 1/(1+Math.exp(-z)); }
  function mhPredict(horizon,x){
    const m=shadowHorizonAI.models?.[horizon];
    if(!m || !Array.isArray(x) || x.length!==AI_FEATURES) return 0.5;
    let z=Number(m.b)||0;
    for(let i=0;i<AI_FEATURES;i++) z += (Number(m.w[i])||0) * (Number(x[i])||0);
    return mhSigmoid(z);
  }
  function mhEnsureModel(h){
    if(!shadowHorizonAI.models || typeof shadowHorizonAI.models!=='object') shadowHorizonAI.models={};
    let m=shadowHorizonAI.models[h];
    if(!m || !Array.isArray(m.w) || m.w.length!==AI_FEATURES) m=shadowHorizonAI.models[h]=makeMhModel(h);
    return m;
  }
  function mhTrain(horizon,x,label,meta={}){
    if(!Array.isArray(x) || x.length!==AI_FEATURES) return null;
    const y=Number(label)>=0.5?1:0, m=mhEnsureModel(horizon), p=mhPredict(horizon,x);
    const err=y-p;
    const lr=MH_AI_LR/Math.sqrt(1 + Number(m.trained||0)/250);
    for(let i=0;i<AI_FEATURES;i++){
      const xi=Math.max(-6,Math.min(6,Number(x[i])||0));
      m.w[i]=(Number(m.w[i])||0) + lr*(err*xi - MH_AI_L2*(Number(m.w[i])||0));
    }
    m.b=(Number(m.b)||0) + lr*err;
    const pred=p>=0.5?1:0;
    m.trained++; m.total++; if(pred===y)m.correct++; if(y)m.up++; else m.down++;
    m.last={t:Date.now(),p,label:y,asset:meta.asset||'',setup:meta.setup||'',dir:meta.dir||''};
    shadowHorizonAI.updatedAt=Date.now();
    const row={policyId:AI_POLICY_ID,t:Date.now(),signalTs:Number(meta.signalTs||0),asset:meta.asset||'',setup:meta.setup||'',dir:meta.dir||'',horizon,label:y,predictedUp:p,correct:pred===y,x:x.slice()};
    shadowHorizonAI.samples.push(row);
    if(shadowHorizonAI.samples.length>MH_AI_MAX_SAMPLES) shadowHorizonAI.samples.splice(0,shadowHorizonAI.samples.length-MH_AI_MAX_SAMPLES);
    const sk=String(meta.setup||'UNKNOWN');
    const bs=shadowHorizonAI.bySetup[sk]||(shadowHorizonAI.bySetup[sk]={});
    const st=bs[horizon]||(bs[horizon]={total:0,correct:0,up:0,down:0});
    st.total++; if(pred===y)st.correct++; if(y)st.up++; else st.down++;
    return {predictedUp:p,label:y,correct:pred===y,trained:m.trained};
  }
  function persistShadowHorizonAI(){
    // V195 QUOTA-SAFE: the 88-feature raw horizon samples are intentionally not
    // mirrored into chrome.storage.local. They remain in RAM and FULL BACKUP.
    // Persist only models + compact aggregate statistics across browser reloads.
    try{
      const r=chrome.storage.local.set({shadowHorizonAI:{version:shadowHorizonAI.version,models:shadowHorizonAI.models,samples:[],bySetup:shadowHorizonAI.bySetup,updatedAt:shadowHorizonAI.updatedAt,quotaSafe:true}});
      if(r && typeof r.catch==='function') r.catch(()=>{});
    }catch(_){}
  }
  try{ chrome.storage.local.get('shadowHorizonAI',d=>{
    const x=d?.shadowHorizonAI; if(!x||typeof x!=='object') return;
    if(x.models&&typeof x.models==='object') shadowHorizonAI.models=x.models;
    for(const [h] of SHADOW_HORIZONS) mhEnsureModel(h);
    if(Array.isArray(x.samples)) shadowHorizonAI.samples=x.samples.slice(-MH_AI_MAX_SAMPLES);
    if(x.bySetup&&typeof x.bySetup==='object') shadowHorizonAI.bySetup=x.bySetup;
    shadowHorizonAI.updatedAt=Number(x.updatedAt||0);
  }); }catch(_){}
  const PAPER_SETUP_VALIDATION_MODE = false; // v24.1.81: live demo + XGB/LGB training restored
  const AI_HIDDEN = 32;
  const AI_MAX_SAMPLES = 2500;
  const AI_MIN_TRAINED = 750;
  const AI_LEARNING_MODE = true;
  const AI_PAPER_INTERVAL_MS = 30000; // one independent forecast per 30s horizon
  const AI_LEARNING_RATE = 0.004; // reduced after fixing labels; online data is noisy // v20: lower LR to reduce short-horizon overfitting and oscillation
  const AI_REPLAY_COUNT = 12; // lower replay to reduce overfitting to recent noisy samples // v19.7 high-training replay            // past samples replayed per flush cycle
  const AI_REPLAY_MAX_AGE = 5000; // retain full rolling training window        // max age (samples) of replay candidates
  const AI_VAL_WINDOW = 500; // honest walk-forward validation                // rolling validation window size
  const AI_INDEPENDENT_CANDLE_MS = 30000;   // only count 1st sample per 60s target candle as independent
  const AI_L2 = 0.0008;
  const AI_MOMENTUM = 0.85;
  const AI_ABSTAIN_ZONE = 0.20;        // p between 0.30-0.70 → AI says "I DON'T KNOW"
  const AI_BACKUP_INTERVAL = 25;       // full export every N paper samples labeled (v19.0.2)
  // v19.10: automatic JSON backup downloads are disabled. Model state remains in chrome.storage.local.
  const AI_AUTO_BACKUP_DOWNLOADS = false;
  const AI_MIN_MOVE = 1e-8;             // 60s binary label: only true/nearly-exact ties are FLAT
  const AI_TRADE_RESULT_TIMEOUT_MS = 300000; // 5 min; fall back to candle label after this
  const AI_TRAIN_EPOCHS = 1; // online learner: one replay pass per flush              // v19.7: repeated replay passes
  const AI_MAX_TRAINED_BUDGET = 30000;     // v19.7: high training ceiling
  const AI_SAVE_BEST_VALIDATION = true;    // preserve walk-forward metrics

  // -- Market Quality + Trade Memory thresholds (v17.6.0) --
  const MQ_MIN_QUALITY = 60;
  const TM_MIN_TRADES = 25;
  const TM_MIN_WINRATE = 0.38;
  const TM_CONFIDENCE_BUCKETS = [0, 0.55, 0.65, 0.75, 0.85, 0.95, 1.01];
  const TRADE_MEMORY_MAX = 500;
  const RECENT_RESULTS_WINDOW = 20;
  const KEY_MARKETS = {};

  // -- Trade Quality Score (v18.0.0) --
  const TQS_ALLOW = 85;            // 85+ → trade allowed with normal confidence
  const TQS_CAUTION = 70;          // 70-85 → require higher confidence, skip if marginal
  const TQS_SKIP = 70;             // below 70 → skip trade entirely

  // -- Time-of-Day learning (v18.0.0) --
  const TOD_MIN_SAMPLES = 8;       // minimum trades per hour bucket to use TOD factor
  const TOD_FLOOR = 0.50;          // minimum multiplier — even bad hours get some edge

  // -- Market Ranking (v18.0.0) --
  const MRK_MIN_TRADES = 15;       // minimum trades to include in market ranking
  const MRK_WINDOW = 24 * 60 * 60 * 1000;  // 24h window for recent market performance
  const MRK_AVOID_WINRATE = 0.45;  // markets below this are flagged as AVOID

  // -- Magnitude-based label tiers (v18.0.0) --
  // Strong moves teach the model what GOOD signals look like
  // Weak moves teach the model what NOISE looks like
  const LABEL_STRONG = 0.003;       // |changePct| >= 0.3% = strong move
  const LABEL_WEAK = 0.001;         // |changePct| >= 0.1% = weak but meaningful
  // Below LABEL_WEAK = noise (treated as draw, no training)

  // -- Do-Nothing Reward (v18.0.0) --
  const DNR_MAX_MOVE = 0.0003;      // if price moved less than this after abstain → correct skip
  const DNR_REWARD_LR = 0.008;      // mild positive reinforcement for correct skips

  // -- Loss Memory (v18.0.0 / v19.0.4 time-decay) --
  const LM_MAX_STORED = 200;        // max loss patterns to store
  const LM_SIMILARITY_THRESHOLD = 0.65; // cosine similarity threshold for pattern match
  const LM_CONFIDENCE_PENALTY = 0.20;   // max confidence reduction when pattern matches
  const LM_HALF_LIFE_MS = 30 * 60 * 1000; // 30 min — patterns older than this have half weight
  const LM_RECOVERY_MS = 30 * 60 * 1000; // 30 min without losses → penalty fades to 0

  // -- Trade Type Classifier (v19.0.0) --
  // Separates reversal setups (exhausted trends, wicks, RSI extremes)
  // from runner setups (strong momentum, EMA fan-out, continuation candles).
  // Each trade type gets different confidence thresholds and feature emphasis.
  const TT_REVERSAL_MARGIN = 15;    // reversal_score must exceed runner_score by this to classify REVERSAL
  const TT_RUNNER_MARGIN = 15;      // runner_score must exceed reversal_score by this to classify RUNNER
  const TT_REV_THR_WARM = 0.65;     // reversal trade confidence threshold (warm)
  const TT_REV_THR_COLD = 0.62;     // reversal trade confidence threshold (cold)
  const TT_RUN_THR_WARM = 0.72;     // runner trade confidence threshold (warm) — runners need stronger signals
  const TT_RUN_THR_COLD = 0.68;     // runner trade confidence threshold (cold)

  // -- Enhanced risk (v18.0.0) --
  const RISK_PER_MARKET_LOSSES = 5;     // same-market consecutive losses before ban
  const RISK_MARKET_BAN_MS = 30 * 60000; // 30 min per-market ban

  // -- MARKET REGIME HELPER (v17.6.0) --
  function getMarketRegime(asset) {
    const a = getAsset(asset);
    const p30 = getLiveTFView(a, '30s').prices;
    if (p30.length < 20) return 'WARMING_UP';
    const structure = swingStructureZigZag(p30.slice(-40));
    return structure.trend || 'NEUTRAL';
  }

  function aiXavier(fanIn, len) {
    const scale = Math.sqrt(2 / fanIn);
    const a = new Array(len);
    for (let i = 0; i < len; i++) a[i] = (Math.random() * 2 - 1) * scale;
    return a;
  }

  const aiState = {
    version: 3,
    // Layer 1: 56→32  Leaky ReLU  (row-major: w1[neuron * AI_FEATURES + input])
    w1: aiXavier(AI_FEATURES, AI_FEATURES * AI_HIDDEN),
    b1: new Array(AI_HIDDEN).fill(0),
    // Layer 2: 32→1  sigmoid
    w2: aiXavier(AI_HIDDEN, AI_HIDDEN),
    b2: 0,
    // Momentum buffers
    vw1: new Array(AI_FEATURES * AI_HIDDEN).fill(0),
    vb1: new Array(AI_HIDDEN).fill(0),
    vw2: new Array(AI_HIDDEN).fill(0),
    vb2: 0,
    trained: 0,
    correct: 0,
    total: 0,
    samples: [],
    lastPrediction: null,
    lastAt: 0,
    lastPaperAt: {},
    lastSampleCandle: {},       // asset → 30s-aligned timestamp; used to count independent samples
    paperQueued: 0,
    paperLabeled: 0,
    paperCorrect: 0,
    loaded: false,
    savePending: false,
    _saveTimer: null,
    _persistTimer: null,
    _lastBackupAt: 0,
    _lastBackupLabeled: 0,
    labeledDataset: [],
    // Calibration trackers
    confEma: 0.5,
    accEma: 0.5,
    calibAlpha: 0.008,
    pendingTradeSamples: {},
    // ── Walk-forward validation ──
    // Each sample is validated on the model state BEFORE training on it.
    // This gives honest out-of-sample accuracy, not inflated training-set accuracy.
    valCorrect: 0,           // rolling window: correct pre-training predictions
    valTotal: 0,             // rolling window: total validated samples
    valWindow: [],           // FIFO queue of {correct:bool} for last 500 samples
    valAccuracy: 0,          // current validation accuracy (0-1)
    valRecent: 0,             // accuracy of last 100 validation samples
    // AI readiness — derived from validation stats
    independentSamples: 0,   // count of 30s-aligned independent paper samples
    // Per-market (per-asset) accuracy tracking
    marketStats: {},
    // V24.1.28: shared V23/XGB sample-pair audit. Updated only when the same
    // 64-feature snapshot is available to both models, then resolved with the
    // exact same 30s UP/DOWN label.
    aiAgreementStats: {total:0,agree:0,disagree:0,agreeCorrect:0,v23Correct:0,xgbCorrect:0,last100:[]},
    // Per-regime accuracy tracking
    regimeStats: {},
    // -- Trade Outcome Memory (v17.6.0) --
    tradeMemory: [],
    tradeStats: {},
    // -- Market Quality Listener (v17.6.0) --
    marketQuality: {},
    // -- Trade outcome tracker (v17.6.0) --
    recentTradeResults: {},
    // V24.1.135 C: HOLD-REASON COUNTERS — why evalAssetSignal/checkSignals held
    // instead of trading. Session-only observability {total,byAsset,last}; never
    // persisted and never restored from a backup.
    holdCounters: { total: {}, byAsset: {}, last: null },
    MQ_TREND_TAU: 0.05,
    MQ_VOL_TAU: 0.05,
    MQ_CHOP_TAU: 0.05,
    // -- Loss Memory (v18.0.0) -- stores detailed losing-trade context for pattern matching
    lossMemory: [],           // [{asset, direction, hour, regime, rsi, trendBull, trendBear, candlePattern, lossPct, ts}]
    // -- Do-Nothing Tracker (v18.0.0) -- counts correct abstentions
    correctAbstains: 0,
    // -- Market Ranking (v18.0.0) --
    marketRanking: {},         // {asset: {winRate, trades, recentWinRate, recentTrades, rank, recommendation}}
    // -- Trade Type Classifier (v19.0.0) --
    tradeTypeStats: {},         // {REVERSAL: {correct,total}, RUNNER: {correct,total}}
    paperSetupStats: { total:0, wins:0, losses:0, draws:0, bySetup:{}, byDir:{BUY:{total:0,wins:0,losses:0},SELL:{total:0,wins:0,losses:0}}, recent:[] },
    setupEdgeStats: {}, // V118 persistent asset+regime+setup+direction success memory
    // v19.10: realized performance by entry strategy/direction.
    strategyPerformance: {
      RUNNER: { BUY: { trades:0, wins:0, losses:0, draws:0, profit:0 }, SELL: { trades:0, wins:0, losses:0, draws:0, profit:0 } },
      REVERSAL: { BUY: { trades:0, wins:0, losses:0, draws:0, profit:0 }, SELL: { trades:0, wins:0, losses:0, draws:0, profit:0 } },
      GENERIC: { BUY: { trades:0, wins:0, losses:0, draws:0, profit:0 }, SELL: { trades:0, wins:0, losses:0, draws:0, profit:0 } }
    },
    // v19.10.1: outcome buckets for strategy diagnosis; measurement only.
    strategyBuckets: {},
    _assetLossStreak: {},
    _marketBanUntil: {},
    _lastLossAt: 0                // v19.0.4: timestamp of last loss for recovery tracking
  };

  // Cached per-asset indicator context for paper learning — ensures training
  // features mirror the full 48-dim vector used by the live DECISION path.
  // Populated by evalAssetSignal every tick; consumed by aiPaperLearnHeartbeat.
  const lastIndicatorCtx = {};
  function aiSigmoid(x) {
    if (x >= 0) { const z = Math.exp(-Math.min(x, 40)); return 1 / (1 + z); }
    const z = Math.exp(Math.max(x, -40)); return z / (1 + z);
  }


  // ════════════════════════════════════════════════════════════
  //  V23 ADAPTIVE LINEAR AI — independent from the legacy NN/controller
  //  Online logistic classifier with a single, explicit owner of its decision.
  //  It never calls aiCtrlApply() and cannot be vetoed by the legacy controller.
  // ════════════════════════════════════════════════════════════
  const V23_AI = {
    version: 2, lr: 0.006, l2: 0.0005, minSamples: 60,
    entryThreshold: 0.62, shadowThreshold: 0.70,
    // V23 v2: independent entries also require proven out-of-sample accuracy.
    // A 62% confidence read from a model that is actually wrong 55% of the
    // time must never override the strategy engine.
    minAccuracy: 0.52,
    w: new Array(AI_FEATURES).fill(0), b: 0, trained: 0,
    correct: 0, total: 0, val: [], last: null
  };


  // ════════════════════════════════════════════════════════════
  // XGBOOST ML LAB (v24.1)
  // V23 remains available as the existing online ML baseline. XGBoost is
  // XGBoost and LightGBM are the active native boosted-tree families.
  // Random Forest, Neural Net and the old generic Ensemble modules remain removed.
  // Both boosted-tree families receive/score the labeled
  // sample and is retrained automatically from the rolling dataset.
  // No AI data/model is written to disk automatically.
  // ════════════════════════════════════════════════════════════
  // V24.1.174 POLICY-AWARE LEARNING — every labeled observation is tagged
  // with the execution policy that generated it. Native training strongly prefers
  // the current policy so strategy revisions are not blended 1:1 with obsolete
  // entry rules. Historical rows remain available as a small context population.
  const AI_POLICY_ID = 'V24.1.238_CANONICAL_AI_PLUMBING';
  const AI_POLICY_PARENT = 'V24.1.189_REGIME_ROUTED_STRUCTURE_ADAPTIVE_EXPIRY_POLICY';
  const AI_POLICY_SCHEMA = 2;

  const AI_LAB = {
    version: 3, samples: [], maxSamples: 5000,
    model: null, stats: {total:0,correct:0,independent:0,livePredictions:0,liveUsed:0,liveSkipped:0},
    // V24.1.72: persistent market memory. Each symbol keeps its own sample
    // balance and rolling prediction results so switching markets also switches
    // the AI's trust context instead of reusing a generic confidence blindly.
    marketProfiles: {},
    last: null, training: {status:'collecting',samples:0,message:''}, holdout: {}
  };
  // 1.6.44: persist actual AI learning rows across browser shutdowns.
  // Storage is restored once on startup; never manufacture successful outcomes.
  let KAOS_AI_STORE_KEY='kaos_ai_lab_persistent_v2_unbound';
  let kaosModelMember=null;
  let kaosAiRestored=false,kaosAiDirty=false,kaosAiLastSave=0;
  try{setInterval(()=>{if(kaosAiRestored && AI_LAB.samples.length){kaosAiDirty=true;kaosPersistAiLab();}},30000);}catch(_){}
  function kaosPersistAiLab(force=false){
    if(!kaosAiRestored || !kaosAiDirty)return;
    const now=Date.now();if(!force && now-kaosAiLastSave<30000)return;
    kaosAiLastSave=now;kaosAiDirty=false;
    const payload={version:1,savedAt:now,samples:AI_LAB.samples.slice(-AI_LAB.maxSamples),model:AI_LAB.model,stats:AI_LAB.stats,training:AI_LAB.training,holdout:AI_LAB.holdout,marketProfiles:AI_LAB.marketProfiles};
    try{chrome.storage.local.set({[KAOS_AI_STORE_KEY]:payload},()=>{if(chrome.runtime.lastError){kaosAiDirty=true;console.warn('[KAOS AI] Save failed',chrome.runtime.lastError.message);}});}catch(_){kaosAiDirty=true;}
  }
  async function kaosRefreshMemberModel(){
    try{
      const response=await chrome.runtime.sendMessage({type:'KAOS_GET_TRAINED_MODEL',scope:'pocket_option:binary:5s:20s:'+(kaosPocketOptionBalanceIsDemo===true?'paper':'real')});
      const data=response?.data;
      if(!response?.ok || !data?.member){AI_LAB.model=null;return;}
      if(kaosModelMember!==data.member){
        kaosModelMember=data.member;KAOS_AI_STORE_KEY='kaos_ai_lab_persistent_v2_'+data.member;
        AI_LAB.model=null;AI_LAB.samples=[];AI_LAB.holdout={};AI_LAB.marketProfiles={};
        const stored=await chrome.storage.local.get(KAOS_AI_STORE_KEY);const saved=stored?.[KAOS_AI_STORE_KEY];
        if(saved)aiLabRestore({...saved,model:null});
      }
      if(data.available && Number(data.model?.features)===AI_FEATURES && data.model?.targetHorizonMs===20000 && Array.isArray(data.model?.trees)){
        AI_LAB.model={...data.model,researchOnly:true};AI_LAB.training={status:'research-ready',message:'Validated member model loaded for research; execution requires separate approval'};
      }else{AI_LAB.model=null;AI_LAB.training={status:'collecting',message:data.pretrainedAccess?'No published pretrained model is available yet':'Personal AI starts untrained. Train your own model in KAOS AI.'};}
      kaosAiRestored=true;kaosAiDirty=true;kaosPersistAiLab(true);
    }catch(_){AI_LAB.model=null;}
  }
  kaosRefreshMemberModel();
  try{setInterval(kaosRefreshMemberModel,300000);}catch(_){}
  try{window.addEventListener('pagehide',()=>kaosPersistAiLab(true));}catch(_){}
  function clampProb(v){ return Math.max(0,Math.min(1,Number.isFinite(Number(v))?Number(v):0.5)); }
  function aiMarketKey(asset){ return String(asset||'').trim(); }
  function aiMarketProfile(asset){
    const key=aiMarketKey(asset);
    if(!key) return null;
    if(!AI_LAB.marketProfiles || typeof AI_LAB.marketProfiles!=='object') AI_LAB.marketProfiles={};
    if(!AI_LAB.marketProfiles[key]) AI_LAB.marketProfiles[key]={asset:key,samples:0,up:0,down:0,predTotal:0,predCorrect:0,recent:[],lastSeenAt:0,sources:{},setupStats:{}};
    if(!AI_LAB.marketProfiles[key].setupStats || typeof AI_LAB.marketProfiles[key].setupStats!=='object') AI_LAB.marketProfiles[key].setupStats={};
    return AI_LAB.marketProfiles[key];
  }
  function aiRebuildMarketProfiles(){
    const old=AI_LAB.marketProfiles&&typeof AI_LAB.marketProfiles==='object'?AI_LAB.marketProfiles:{};
    const next={};
    for(const row of (AI_LAB.samples||[])){
      const key=aiMarketKey(row?.asset); if(!key) continue;
      const prev=old[key]||{};
      const p=next[key]||(next[key]={asset:key,samples:0,up:0,down:0,predTotal:Number(prev.predTotal||0),predCorrect:Number(prev.predCorrect||0),recent:Array.isArray(prev.recent)?prev.recent.slice(-80):[],lastSeenAt:Number(prev.lastSeenAt||0),sources:{...(prev.sources||{})},setupStats:{...(prev.setupStats||{})}});
      p.samples++; if(Number(row.label)>=0.5)p.up++;else p.down++; p.lastSeenAt=Math.max(p.lastSeenAt,Number(row.t||0));
      const src=String(row.source||'unknown'); p.sources[src]=(p.sources[src]||0)+1;
      const sk=String(row.setupKey||'').trim();
      if(sk){
        const st=p.setupStats[sk]||(p.setupStats[sk]={total:0,up:0,down:0});
        st.total++; if(Number(row.label)>=0.5)st.up++;else st.down++;
      }
    }
    AI_LAB.marketProfiles=next;
  }
  function aiWilsonCI(correct,total,z=1.96){
    const n=Math.max(0,Number(total)||0), k=Math.max(0,Math.min(n,Number(correct)||0));
    if(!n) return {low:0,high:1,p:0.5,n:0};
    const p=k/n, z2=z*z, den=1+z2/n;
    const center=(p+z2/(2*n))/den;
    const margin=(z*Math.sqrt((p*(1-p)+z2/(4*n))/n))/den;
    return {low:Math.max(0,center-margin),high:Math.min(1,center+margin),p,n};
  }
  function aiMarketTrust(asset,selection,rawP){
    const key=aiMarketKey(asset);
    const marketRep=AI_LAB.holdout?.perAsset?.[key]||{};
    const profile=aiMarketProfile(key)||{};
    const source=selection?.source||'global';
    const family=selection?.family||'xgboost';
    const holdoutN=family==='lightgbm' && source==='local' ? Number(marketRep?.lightgbmHoldoutSamples||0) : Number(marketRep?.holdoutSamples||0);
    const holdoutAcc=family==='lightgbm'
      ? (source==='local' ? Number(marketRep?.lightgbmHoldoutAccuracy) : Number(marketRep?.lightgbmGlobalHoldoutAccuracy))
      : (source==='local' ? Number(marketRep?.holdoutAccuracy) : Number(marketRep?.globalHoldoutAccuracy));
    const holdoutCorrect=Number.isFinite(holdoutAcc)?Math.round(holdoutAcc*holdoutN):0;
    const holdoutCI=aiWilsonCI(holdoutCorrect,holdoutN);
    const recent=Array.isArray(profile.recent)?profile.recent.slice(-50):[];
    const recentN=recent.length, recentCorrect=recent.filter(Boolean).length;
    const recentAcc=recentN?recentCorrect/recentN:NaN, recentCI=aiWilsonCI(recentCorrect,recentN);
    const liveN=Number(profile.predTotal||0), liveCorrect=Number(profile.predCorrect||0);
    const liveAcc=liveN?liveCorrect/liveN:NaN, liveCI=aiWilsonCI(liveCorrect,liveN);
    const hasHoldout=Number.isFinite(holdoutAcc)&&holdoutN>=20;
    const hasLive=Number.isFinite(liveAcc)&&liveN>=30;
    let trustAcc=hasHoldout?holdoutAcc:0.5;
    if(hasLive){ const hw=Math.min(0.70,holdoutN/(holdoutN+30)); trustAcc=hasHoldout?(trustAcc*hw+liveAcc*(1-hw)):liveAcc; }
    const drift=hasHoldout&&liveN>=50&&((holdoutAcc-liveAcc)>=0.07 || liveAcc<0.52);
    const evidence=Math.min(holdoutN||0, hasLive?liveN:holdoutN||0);
    const lowerBound=hasLive?Math.min(holdoutCI.low,liveCI.low):holdoutCI.low;
    let tier='TRAINED';
    if(drift) tier='ADVISORY';
    else if(!hasHoldout || holdoutN<40 || lowerBound<0.50) tier='TRAINED';
    else if(lowerBound<0.52) tier='ADVISORY';
    else if(lowerBound<0.53 || evidence<50) tier='VALIDATED';
    else if(lowerBound<0.54 || evidence<80) tier='TRUSTED';
    else tier='AUTHORITY';
    const nFactor=Math.max(0,Math.min(1,evidence/100));
    const accFactor=Math.max(0,Math.min(1,(lowerBound-0.50)/0.08));
    const reliability=drift?0:nFactor*accFactor;
    const rp=clampProb(rawP), calibrated=0.5+(rp-0.5)*reliability;
    return {asset:key,tier,source,holdoutAccuracy:Number.isFinite(holdoutAcc)?holdoutAcc:null,holdoutSamples:holdoutN,holdoutCiLow:holdoutCI.low,holdoutCiHigh:holdoutCI.high,recentAccuracy:Number.isFinite(recentAcc)?recentAcc:null,recentSamples:recentN,recentCiLow:recentCI.low,liveAccuracy:Number.isFinite(liveAcc)?liveAcc:null,liveSamples:liveN,liveCiLow:liveCI.low,liveCiHigh:liveCI.high,driftDemoted:drift,trustAccuracy:trustAcc,trustLowerBound:lowerBound,evidence,reliability,rawUp:rp,calibratedUp:clampProb(calibrated),profileSamples:Number(profile.samples||0),upSamples:Number(profile.up||0),downSamples:Number(profile.down||0)};
  }
  function aiMarketAwareTrainingRows(asset){
    const key=aiMarketKey(asset);
    const all=Array.isArray(AI_LAB.samples)?AI_LAB.samples:[];
    // V24.1.154: train the prediction models primarily on the setup families that
    // can actually become trades. The old feed was dominated by predictor-driver,
    // background-control and breakout-retest observations, which diluted the label
    // distribution the live entry engine actually cares about.
    const executableFamilies=new Set(['TREND_PULLBACK','MOMENTUM_CONTINUATION','TREND_BREAKOUT','STRUCTURE_CONTINUATION','TREND_FLOW','TREND_ALIGNMENT','CONFIRMED_REVERSAL','RANGE_REJECTION','TREND_RESUME','HIGH_VALUE_RUNNER','CRYPTO_RUNNER_CONTINUATION','SELL_EXHAUSTION','BUY_EXHAUSTION']);
    const qualified=all.filter(r=>executableFamilies.has(String(r?.tradeType||'')) && (r?.source==='trade' || r?.source==='setup'));
    const base=qualified.length>=120?qualified:all;
    // Policy-aware curriculum: once the current strategy has enough labeled rows,
    // train primarily on those rows. Keep at most 20% historical context rather
    // than treating old entry policies as if they were generated by this one.
    const current=base.filter(r=>String(r?.policyId||'')===AI_POLICY_ID);
    // V238: AI is learning-only, so do not strand the native trainer at 9/12 merely
    // because the execution-policy id changed. All restored rows have already been
    // normalized to the canonical 104-feature schema. Prefer current-policy rows,
    // then backfill with the newest compatible historical rows until the native
    // trainer has a useful, diverse chronological window. Current rows are kept
    // newest and therefore receive the trainer's recency emphasis.
    const historical=base.filter(r=>String(r?.policyId||'')!==AI_POLICY_ID);
    const pool=historical.slice(-900).concat(current.slice(-600)).sort((a,b)=>Number(a?.t||0)-Number(b?.t||0)).slice(-1200);
    if(!key) return pool.slice(-1200);
    const local=pool.filter(r=>aiMarketKey(r?.asset)===key).slice(-700);
    const other=pool.filter(r=>aiMarketKey(r?.asset)!==key).slice(-500);
    return other.concat(local).sort((a,b)=>Number(a?.t||0)-Number(b?.t||0)).slice(-1200);
  }
  function modelPredictTree(node,x){
    if(!node)return 0; let n=node;
    while(n && n.leaf==null){ const f=Number(n.f||0),v=Number(x[f]||0),t=Number(n.t||0); n=v<t?n.l:n.r; if(!n)return 0; }
    return Number(n&&n.leaf!=null?n.leaf:0);
  }
  // V24.1.65 CHAMPION / CHALLENGER MODEL SELECTION
  // The global model remains champion by default. A per-market model is only
  // promoted after it proves a real edge on the SAME chronological holdout for
  // that asset. Merely existing is no longer enough to replace the global AI.
  function xgbSelectionForAsset(model, asset){
    if(!model) return {model:null,source:'none',family:'none',reason:'no-model'};
    const key=String(asset||'');
    const rep=AI_LAB.holdout?.perAsset?.[key]||{};
    const xLocal=model.assetModels?.[key]||null;
    const lGlobal=model.lightgbmGlobal||null;
    const lLocal=model.lightgbmAssetModels?.[key]||null;
    const champion=String(rep?.marketChampion||'');
    const choices={
      'xgb-global':{model,source:'global',family:'xgboost',acc:Number(rep?.globalHoldoutAccuracy),n:Number(rep?.holdoutSamples||0)},
      'xgb-local':{model:xLocal,source:'local',family:'xgboost',acc:Number(rep?.holdoutAccuracy),n:Number(rep?.holdoutSamples||0)},
      'lgb-global':{model:lGlobal,source:'global',family:'lightgbm',acc:Number(rep?.lightgbmGlobalHoldoutAccuracy),n:Number(rep?.holdoutSamples||0)},
      'lgb-local':{model:lLocal,source:'local',family:'lightgbm',acc:Number(rep?.lightgbmHoldoutAccuracy),n:Number(rep?.lightgbmHoldoutSamples||0)}
    };
    let picked=choices[champion];
    if(!picked?.model || !Array.isArray(picked.model.trees) || !picked.model.trees.length){
      // V24.1.154: when no market-specific champion exists, compare the two global
      // families on the same chronological holdout instead of blindly falling back
      // to XGBoost. This lets the stronger global family be the visible learner.
      const gx=Number(AI_LAB.holdout?.holdoutAccuracy);
      const gl=Number(AI_LAB.holdout?.lightgbmGlobal?.holdoutAccuracy);
      const gn=Number(AI_LAB.holdout?.holdoutSamples||0);
      if(lGlobal && gn>=30 && Number.isFinite(gl) && Number.isFinite(gx) && gl>=gx+0.02){
        picked={model:lGlobal,source:'global',family:'lightgbm',acc:gl,n:gn};
        return {...picked,reason:'global-holdout-champion-lightgbm',report:rep,marketChampion:'lgb-global'};
      }
      const fallback=choices['xgb-global']; picked=fallback;
      return {...picked,reason:'global-holdout-champion-xgb',report:rep,marketChampion:'xgb-global'};
    }
    // Winning is not enough: authority still requires a real current-market
    // holdout with >=20 samples and >=55% accuracy downstream.
    return {...picked,reason:'market-champion-'+champion,report:rep,marketChampion:champion};
  }
  function xgbModelForAsset(model, asset){
    return xgbSelectionForAsset(model,asset).model;
  }

  // V24.1.95 SHADOW PREDICTIONS: score XGBoost and LightGBM independently
  // on every valid feature snapshot even while neither model has trading authority.
  // Authority gates control execution only; they must never suppress prediction %.
  function aiPredictBundle(bundle,x){
    if(!bundle||!Array.isArray(bundle.trees)||!bundle.trees.length||!Array.isArray(x)) return null;
    let margin=Number(bundle.base||0);
    for(const t of bundle.trees) margin+=modelPredictTree(t,x);
    return clampProb(1/(1+Math.exp(-Math.max(-30,Math.min(30,margin)))));
  }
  function aiFamilySelectionForAsset(model, asset, family){
    if(!model) return {model:null,source:'none',family,reason:'no-model'};
    const key=String(asset||'');
    const rep=AI_LAB.holdout?.perAsset?.[key]||{};
    if(family==='lightgbm'){
      const global=model.lightgbmGlobal||null, local=model.lightgbmAssetModels?.[key]||null;
      const gAcc=Number(rep?.lightgbmGlobalHoldoutAccuracy), lAcc=Number(rep?.lightgbmHoldoutAccuracy), lN=Number(rep?.lightgbmHoldoutSamples||0);
      const useLocal=!!local && String(rep?.marketChampion||'')==='lgb-local' && lN>=50 && Number(rep?.selectionSamples||0)>=40 && Number.isFinite(lAcc);
      return {model:useLocal?local:global,source:useLocal?'local':'global',family:'lightgbm',reason:useLocal?'local-better':'global-default'};
    }
    const global=model, local=model.assetModels?.[key]||null;
    const useLocal=!!local && !!rep?.localEligible;
    return {model:useLocal?local:global,source:useLocal?'local':'global',family:'xgboost',reason:useLocal?'local-eligible':'global-default'};
  }
  function aiShadowPredictions(asset,x){
    const xs=aiFamilySelectionForAsset(AI_LAB.model,asset,'xgboost');
    const ls=aiFamilySelectionForAsset(AI_LAB.model,asset,'lightgbm');
    const xRaw=aiPredictBundle(xs.model,x), lRaw=aiPredictBundle(ls.model,x);
    const xTrust=xRaw==null?null:aiMarketTrust(asset,xs,xRaw);
    const lTrust=lRaw==null?null:aiMarketTrust(asset,ls,lRaw);
    // V24.1.106: the visible XGB/LGB percentage is ALWAYS the model's real raw
    // probability. Market-trust calibration remains available inside `trust`
    // for authority gating, but it must never flatten the UI back to 50%.
    const shadowPreview=(raw,trust)=> raw==null ? null : raw;
    return {
      xgb:{rawUp:xRaw,previewUp:shadowPreview(xRaw,xTrust),source:xs.source,trust:xTrust},
      lightgbm:{rawUp:lRaw,previewUp:shadowPreview(lRaw,lTrust),source:ls.source,trust:lTrust}
    };
  }

  function xgbPredict(model,x,asset){
    const chosen=xgbModelForAsset(model,asset);
    if(!chosen||!Array.isArray(chosen.trees)||!chosen.trees.length)return null;
    let margin=Number(chosen.base||0);
    for(const t of chosen.trees) margin+=modelPredictTree(t,x);
    return clampProb(1/(1+Math.exp(-Math.max(-30,Math.min(30,margin)))));
  }
  function aiLabScore(x,asset){
    const selection=xgbSelectionForAsset(AI_LAB.model,asset);
    const chosen=selection.model;
    const p=xgbPredict(AI_LAB.model,x,asset);
    AI_LAB.last=p;
    if (p != null) AI_LAB.stats.livePredictions=(AI_LAB.stats.livePredictions||0)+1;
    lastIndicators.aiLab={xgboost:p,modelReady:!!AI_LAB.model,marketModel:selection.source==='local',modelSource:selection.source,
      selectionReason:selection.reason,marketModelSamples:Number(chosen?.totalSamples||0),training:AI_LAB.training?.status||'collecting'};
    return {xgboost:p};
  }

  function aiXgbLive(asset, x) {
    const warm = aiMarketWarmupReady(asset);
    const selection=xgbSelectionForAsset(AI_LAB.model,asset);
    const chosen=selection.model;
    const trained = !!chosen && Array.isArray(chosen.trees) && chosen.trees.length > 0;
    const marketSpecific=selection.source==='local';
    const marketRep=AI_LAB.holdout?.perAsset?.[String(asset||'')];
    const rep=marketSpecific ? (marketRep||{}) : (AI_LAB.holdout||{});
    const validationSamples=Number(rep?.holdoutSamples||0);
    const validationAccuracy=Number(rep?.holdoutAccuracy||0);
    const learnedSamples=Number(chosen?.totalSamples||AI_LAB.samples.length||0);
    const shadows=aiShadowPredictions(asset,x);
    const rawP = trained ? xgbPredict(AI_LAB.model, x, asset) : null;
    const trust = rawP==null ? null : aiMarketTrust(asset,selection,rawP);
    const marketValidated=!!trust && trust.holdoutSamples>=40 && Number(trust.trustLowerBound||0)>=0.52 && !trust.driftDemoted;
    const validated = learnedSamples >= 150 && validationSamples >= 40 && validationAccuracy >= 0.55 && marketValidated;
    const previewP = trust ? trust.calibratedUp : rawP;
    const rawDirection = rawP == null ? null : (rawP >= 0.5 ? 'BUY' : 'SELL');
    const rawConfidence = rawP == null ? 0 : Math.abs(rawP - 0.5) * 2;
    const previewDirection = previewP == null ? null : (previewP >= 0.5 ? 'BUY' : 'SELL');
    const previewConfidence = previewP == null ? 0 : Math.abs(previewP - 0.5) * 2;
    // ADVISORY/TRAINED tiers are never allowed to become AI authority. VALIDATED
    // and TRUSTED can participate under the downstream context gates; AUTHORITY
    // has earned direct market-specific trust.
    const authorityEligible=!!trust && ['VALIDATED','TRUSTED','AUTHORITY'].includes(trust.tier);
    const p = (warm && trained && validated && authorityEligible) ? previewP : null;
    const direction = p == null ? null : (p >= 0.5 ? 'BUY' : 'SELL');
    const confidence = p == null ? 0 : Math.abs(p - 0.5) * 2;
    const trainerStatus=String(AI_LAB.training?.status||'collecting');
    const trainerError=trainerStatus==='error';
    let status = trainerStatus;
    if (!trained) status = trainerError ? 'trainer-error-no-model' : (status || 'collecting');
    else if (!warm) status = trainerError ? 'model-ready · trainer-error · market-warmup' : 'market-warmup';
    else if (!marketValidated) status = `${trust?.tier||'TRAINED'} · NOT TRUSTED · market ${(Number(trust?.trustAccuracy||0)*100).toFixed(1)}%/${Number(trust?.holdoutSamples||0)}`;
    else if (!validated) status = trainerError ? 'model-preview · trainer-error · learning-validation' : 'learning-validation';
    else status = `${trust?.tier||'VALIDATED'} · MARKET ${(Number(trust?.trustAccuracy||0)*100).toFixed(1)}%/${Number(trust?.holdoutSamples||0)}`;
    const state = {live: p != null, warm, trained, validated, direction, confidence, up:p,
      previewUp:previewP,previewDirection,previewConfidence,rawUp:rawP,rawDirection,rawConfidence,
      samples:AI_LAB.samples.length,status,marketSpecific,modelSource:selection.source,modelFamily:selection.family||'xgboost',marketChampion:selection.marketChampion||'xgb-global',selectionReason:selection.reason,
      localShadowAccuracy:Number(marketRep?.holdoutAccuracy||0),localShadowSamples:Number(marketRep?.samples||0),
      globalOnMarketAccuracy:Number.isFinite(Number(marketRep?.globalHoldoutAccuracy))?Number(marketRep.globalHoldoutAccuracy):null,
      marketValidationSamples:Number(marketRep?.holdoutSamples||0),
      marketSamples:learnedSamples,validationSamples,validationAccuracy,
      marketTrustTier:trust?.tier||'TRAINED',marketTrustAccuracy:Number(trust?.trustAccuracy||0),marketTrustLowerBound:Number(trust?.trustLowerBound||0),marketTrustEvidence:Number(trust?.evidence||0),marketReliability:Number(trust?.reliability||0),marketProfileSamples:Number(trust?.profileSamples||0),marketUpSamples:Number(trust?.upSamples||0),marketDownSamples:Number(trust?.downSamples||0),marketRecentAccuracy:trust?.recentAccuracy,marketLiveAccuracy:trust?.liveAccuracy,marketLiveSamples:Number(trust?.liveSamples||0),marketLiveCiLow:Number(trust?.liveCiLow||0),marketDriftDemoted:!!trust?.driftDemoted,
      shadowXgbUp:shadows?.xgb?.previewUp??null,shadowXgbRawUp:shadows?.xgb?.rawUp??null,shadowXgbSource:shadows?.xgb?.source||'none',
      shadowLgbUp:shadows?.lightgbm?.previewUp??null,shadowLgbRawUp:shadows?.lightgbm?.rawUp??null,shadowLgbSource:shadows?.lightgbm?.source||'none'};
    lastIndicators.xgbAI = state;
    if (p != null) AI_LAB.stats.liveUsed=(AI_LAB.stats.liveUsed||0)+1;
    else AI_LAB.stats.liveSkipped=(AI_LAB.stats.liveSkipped||0)+1;
    return state;
  }
  function aiLabRecordSample(s,label){
    if(!s||!Array.isArray(s.x)||s.x.length!==AI_FEATURES)return;
    const marketLabel=Number(label)>=.5?1:0;
    const sourceCandleDir=String(s.sourceCandleDir||'').toUpperCase();
    const continuationLabel=(s.targetKind==='CONTINUE_VS_REVERSE' && (sourceCandleDir==='BUY'||sourceCandleDir==='SELL'))
      ? ((sourceCandleDir==='BUY'&&marketLabel===1)||(sourceCandleDir==='SELL'&&marketLabel===0)?1:0) : null;
    const row={policyId:s.policyId||AI_POLICY_ID,policyParent:s.policyParent||AI_POLICY_PARENT,policySchema:Number(s.policySchema||AI_POLICY_SCHEMA),asset:s.asset,t:s.t,candleTs:Number(s.candleTs||Math.floor(Number(s.t||0)/AI_INDEPENDENT_CANDLE_MS)*AI_INDEPENDENT_CANDLE_MS),label:marketLabel,x:s.x.slice(),independent:!!s.independent,source:s.source,sources:Array.isArray(s.sources)?s.sources.slice():[s.source],tradeType:s.tradeType||null,setupDir:s.setupDir||null,setupKey:s.setupKey||null,regime:s.regime||null,targetKind:s.targetKind||null,sourceCandleDir:s.sourceCandleDir||null,continuationLabel,classifierDecision:s.classifierDecision||null,continueScore:Number.isFinite(Number(s.continueScore))?Number(s.continueScore):null,reversalScore:Number.isFinite(Number(s.reversalScore))?Number(s.reversalScore):null,runLength:Number.isFinite(Number(s.runLength))?Number(s.runLength):null};
    AI_LAB.samples.push(row);
    kaosAiDirty=true;kaosPersistAiLab();
    if(AI_LAB.samples.length>AI_LAB.maxSamples)AI_LAB.samples.splice(0,AI_LAB.samples.length-AI_LAB.maxSamples);
    const pred=s.aiLabPrediction?.xgboost;
    const mp=aiMarketProfile(row.asset);
    if(mp){
      mp.samples++; if(row.label>=0.5)mp.up++;else mp.down++; mp.lastSeenAt=Number(row.t||Date.now());
      const src=String(row.source||'unknown'); mp.sources[src]=(mp.sources[src]||0)+1;
      const sk=String(row.setupKey||'').trim(); if(sk){const st=mp.setupStats[sk]||(mp.setupStats[sk]={total:0,up:0,down:0});st.total++;if(row.label>=0.5)st.up++;else st.down++;}
    }
    if(pred!=null){
      const correct=(pred>=.5?1:0)===row.label;
      AI_LAB.stats.total++;if(correct)AI_LAB.stats.correct++;if(row.independent)AI_LAB.stats.independent++;
      if(mp){mp.predTotal++;if(correct)mp.predCorrect++;mp.recent.push(!!correct);if(mp.recent.length>80)mp.recent.splice(0,mp.recent.length-80);}
    }
    // Market-aware training payload: reserve more of the fixed native-host window
    // for the market currently producing the label, while retaining global diversity.
    try {
      chrome.runtime.sendMessage({type:'XGB_TRAIN_NOW', samples:aiMarketAwareTrainingRows(row.asset), activeMarket:row.asset}).catch(()=>{});
    } catch(e) {}
  }
  // 1.6.45: bootstrap native training from restored/imported REAL labels.
  // Native host is optional: failures are visible and no synthetic win records are made.
  let kaosBootstrapTimer=null;
  function kaosBootstrapNativeTraining(reason='restore') {
    if(kaosBootstrapTimer)clearTimeout(kaosBootstrapTimer);
    kaosBootstrapTimer=setTimeout(async()=>{
      kaosBootstrapTimer=null;
      const valid=(AI_LAB.samples||[]).filter(r=>Array.isArray(r?.x)&&r.x.length===AI_FEATURES &&
        (r.label===0||r.label===1) && Number.isFinite(Number(r.t)));
      if(valid.length<40){
        AI_LAB.training={status:'collecting',samples:valid.length,message:'Need at least 40 valid labeled 104-feature observations'};
        return;
      }
      const market=String(valid[valid.length-1].asset||'');
      const rows=aiMarketAwareTrainingRows(market);
      AI_LAB.training={status:'training',samples:rows.length,message:'Restored samples; requesting native model training ('+reason+')'};
      try {
        const result=await chrome.runtime.sendMessage({type:'XGB_TRAIN_NOW',samples:rows,activeMarket:market});
        if(result?.ok===false){
          AI_LAB.training={status:'error',samples:rows.length,message:'Native trainer: '+String(result.error||'unavailable')};
          aiLog('XGB_BOOTSTRAP_FAILED',{reason,error:result.error||'unavailable'},true);
        }
      } catch(e) {
        AI_LAB.training={status:'error',samples:rows.length,message:'Native trainer unavailable: '+String(e.message||e)};
        aiLog('XGB_BOOTSTRAP_FAILED',{reason,error:String(e.message||e)},true);
      }
      kaosAiDirty=true;kaosPersistAiLab(true);
    },1500);
  }
  function aiLabRestore(p){
    if(!p||typeof p!=='object')return false;
    if(Array.isArray(p.samples)){
      AI_LAB.samples=p.samples.slice(-AI_LAB.maxSamples).map((r,idx)=>{
        const q={...r};
        if(!q.policyId) q.policyId='LEGACY_PRE_V24.1.173';
        if(!q.policySchema) q.policySchema=0;
        if(Array.isArray(q.x)&&[64,72,76,88].includes(q.x.length)) q.x=q.x.concat(new Array(AI_FEATURES-q.x.length).fill(0));
        // Normalize legacy/synthetic timestamp naming so native training,
        // market profiles and deduplication all see a real unique event time.
        if(!Number.isFinite(Number(q.t)) || Number(q.t)<=0){
          const alt=Number(q.ts);
          q.t=Number.isFinite(alt)&&alt>0 ? alt : (Date.now()-((p.samples.length-idx)*31000));
        }
        return q;
      }).filter(r=>Array.isArray(r.x)&&r.x.length===AI_FEATURES);
    }
    // An older 64/72/76-feature tree model cannot safely score 88-feature data. Keep its labeled
    // rows, discard only the old model, and retrain both competitors on import.
    if(p.model && Number(p.model.features||0)===AI_FEATURES)AI_LAB.model=p.model; else AI_LAB.model=null;
    if(p.stats)AI_LAB.stats=p.stats;
    if(p.holdout)AI_LAB.holdout=p.holdout;
    if(p.marketProfiles&&typeof p.marketProfiles==='object')AI_LAB.marketProfiles=p.marketProfiles;
    if(p.training)AI_LAB.training=p.training;
    aiRebuildMarketProfiles();
    kaosAiDirty=true;kaosPersistAiLab(true);
    if(AI_LAB.samples.length>=40)kaosBootstrapNativeTraining('AI import or restore');
    return true;
  }

  // ════════════════════════════════════════════════════════════
  // V24.1.56 PULLBACK / REVERSAL PATTERN AI
  // Separate from the 76-feature UP/DOWN models so imported V23/XGB models
  // remain schema-compatible. This learner answers a different question:
  // when a strong trend has 1-2 counter-trend candles, is the move more likely
  // to CONTINUE with the original trend or become a TRUE REVERSAL?
  // ════════════════════════════════════════════════════════════
  const PATTERN_AI = {
    version:1, features:12, lr:0.018, l2:0.001, minSamples:40, minAccuracy:0.52,
    w:new Array(12).fill(0), b:0, trained:0, total:0, correct:0, val:[], last:null
  };
  function patternSigmoid(z){ return 1/(1+Math.exp(-Math.max(-20,Math.min(20,z)))); }
  function patternFeatures(ind){
    if(!ind) return null;
    const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
    const trend=String(ind.patternTrendDir||ind.structureDirection||'NEUTRAL');
    if(trend!=='BUY'&&trend!=='SELL') return null;
    const sign=trend==='BUY'?1:-1;
    const plus=n(ind.plusDI), minus=n(ind.minusDI), diDen=Math.max(1,Math.abs(plus)+Math.abs(minus));
    const tqsAdv=trend==='BUY'?n(ind.tqsBuy)-n(ind.tqsSell):n(ind.tqsSell)-n(ind.tqsBuy);
    const vals=[
      sign,
      Math.max(-1,Math.min(1,n(ind.structureConfidence)*2-1)),
      Math.max(-1,Math.min(1,n(ind.emaDeviation)/2))*sign,
      Math.max(-1,Math.min(1,n(ind.emaSpread)/1.5)),
      Math.max(-1,Math.min(1,((plus-minus)/diDen)*sign)),
      Math.max(-1,Math.min(1,n(ind.macdAccel)/0.05))*sign,
      Math.max(-1,Math.min(1,n(ind.rsiSlope)/5))*sign,
      Math.max(0,Math.min(1,n(ind.counterPullbackCount)/2)),
      Math.max(-1,Math.min(1,1-n(ind.pullbackBodyRatio,1)/1.5)),
      ind.pullbackBrokeStructure? -1 : 1,
      Math.max(-1,Math.min(1,tqsAdv/50)),
      Math.max(-1,Math.min(1,(n(ind.marketQuality,50)-50)/30))
    ];
    return vals;
  }
  function patternPredict(ind){
    const x=patternFeatures(ind);
    if(!x) return {continuation:0.5,reversal:0.5,confidence:0,warm:false,trained:PATTERN_AI.trained,accuracy:PATTERN_AI.total?PATTERN_AI.correct/PATTERN_AI.total:0,x:null};
    let z=PATTERN_AI.b; for(let i=0;i<PATTERN_AI.features;i++) z+=PATTERN_AI.w[i]*x[i];
    const continuation=patternSigmoid(z), acc=PATTERN_AI.total?PATTERN_AI.correct/PATTERN_AI.total:0;
    const out={continuation,reversal:1-continuation,confidence:Math.abs(continuation-0.5)*2,warm:PATTERN_AI.trained>=PATTERN_AI.minSamples,trained:PATTERN_AI.trained,accuracy:acc,x};
    PATTERN_AI.last=out; lastIndicators.patternAI=out; return out;
  }
  function patternTrain(x,label){
    if(!Array.isArray(x)||x.length!==PATTERN_AI.features) return;
    const y=Number(label)>=0.5?1:0;
    let z=PATTERN_AI.b; for(let i=0;i<PATTERN_AI.features;i++) z+=PATTERN_AI.w[i]*Number(x[i]||0);
    const p=patternSigmoid(z), pred=p>=0.5?1:0, err=y-p;
    PATTERN_AI.total++; if(pred===y) PATTERN_AI.correct++; PATTERN_AI.val.push(pred===y); if(PATTERN_AI.val.length>500)PATTERN_AI.val.shift();
    for(let i=0;i<PATTERN_AI.features;i++){ const xi=Number(x[i]||0); PATTERN_AI.w[i]+=PATTERN_AI.lr*(err*xi-PATTERN_AI.l2*PATTERN_AI.w[i]); }
    PATTERN_AI.b+=PATTERN_AI.lr*err; PATTERN_AI.trained++;
  }

  function v23Sigmoid(z) { return 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z)))); }
  function v23Features(x) {
    if (!Array.isArray(x)) return null;
    const out = new Array(AI_FEATURES);
    for (let i=0;i<AI_FEATURES;i++) {
      const v = Number(x[i] || 0);
      out[i] = Math.max(-3, Math.min(3, Number.isFinite(v) ? v : 0));
    }
    return out;
  }
  function v23PredictFromX(x) {
    const f=v23Features(x); if (!f) return {up:0.5,down:0.5,direction:null,confidence:0,warm:false};
    let z=V23_AI.b;
    for(let i=0;i<AI_FEATURES;i++) z += V23_AI.w[i]*f[i];
    const up=v23Sigmoid(z), down=1-up;
    const direction=up>=0.5?'BUY':'SELL';
    return {up,down,direction,confidence:Math.abs(up-0.5)*2,warm:V23_AI.trained>=V23_AI.minSamples,x:f};
  }
  function v23Predict(asset, price, ind) { return v23PredictFromX(aiFeatures(asset,price,ind)); }
  function v23Train(x,label) {
    const f=v23Features(x); if(!f) return;
    const y=Number(label)>=0.5?1:0;
    const pred=v23PredictFromX(f).up, err=y-pred;
    const lr=V23_AI.lr/(1+V23_AI.trained/3000);
    for(let i=0;i<AI_FEATURES;i++) V23_AI.w[i]+=lr*(err*f[i]-V23_AI.l2*V23_AI.w[i]);
    V23_AI.b+=lr*err; V23_AI.trained++;
  }
  // Quality bar for strategy signals that V23 lets through while it is
  // still learning (bootstrap) or waiting below its confidence threshold.
  // Dedicated run/rev, regime-first and deterministic paths already carry
  // their own strong gates (MQ, TQS, vote counts) and may always pass.
  // Generic AI-tier signals need real confidence AND a TQS floor so a fresh
  // model can't push marginal setups into the market.
  function v23StrategyQualityOk(sig) {
    if (!sig || !sig.dir) return false;
    const mode = String(sig.mode || '').toLowerCase();
    if (['run-rev','v22-deterministic','v21-regime-first'].includes(mode)) return true;
    const conf = Number(sig.confidence) || 0;
    const tqs  = Number(sig.tqs) || 0;
    return conf >= 0.45 && tqs >= 70;
  }

  function aiContextSummary(ind, direction) {
    const d = direction === 'SELL' ? 'SELL' : 'BUY';
    const support = [], oppose = [];
    const add = (ok, yes, no) => { if (ok === true && yes) support.push(yes); else if (ok === false && no) oppose.push(no); };
    const r = Number(ind?.rsi ?? ind?.rsi30 ?? lastIndicators?.rsi ?? 50);
    const st = Number(ind?.stoch ?? lastIndicators?.stoch ?? 50);
    const e5 = Number(ind?.ema5 ?? lastIndicators?.ema5 ?? 0);
    const e9 = Number(ind?.ema9 ?? lastIndicators?.ema9 ?? 0);
    const e21 = Number(ind?.ema21 ?? lastIndicators?.ema21 ?? 0);
    const macd = Number(ind?.macd ?? lastIndicators?.macd ?? 0);
    const macdSignal = Number(ind?.macdSignal ?? lastIndicators?.macdSignal ?? 0);
    const tqs = d === 'BUY' ? Number(ind?.tqsBuy ?? lastIndicators?.tqsBuy ?? 0) : Number(ind?.tqsSell ?? lastIndicators?.tqsSell ?? 0);
    const oppTqs = d === 'BUY' ? Number(ind?.tqsSell ?? lastIndicators?.tqsSell ?? 0) : Number(ind?.tqsBuy ?? lastIndicators?.tqsBuy ?? 0);
    const run = d === 'BUY' ? Number(ind?.runnerBuy ?? lastIndicators?.runnerBuyScore ?? 0) : Number(ind?.runnerSell ?? lastIndicators?.runnerSellScore ?? 0);
    const rev = d === 'BUY' ? Number(ind?.revBuy ?? lastIndicators?.v19RevBuy ?? 0) : Number(ind?.revSell ?? lastIndicators?.v19RevSell ?? 0);
    const regime = String(ind?.regime || lastIndicators?.regime || 'UNKNOWN');
    const bullBreak = !!(ind?.liveBearBreak || lastIndicators?.liveBearBreak);
    const bearBreak = !!(ind?.liveBullBreak || lastIndicators?.liveBullBreak);

    if (d === 'BUY') {
      add(e5 > e9 && e9 >= e21, 'EMA stack bullish', 'EMA stack not bullish');
      add(macd >= macdSignal, 'MACD above signal', 'MACD below signal');
      if (r <= 35) support.push(`RSI ${r.toFixed(0)} oversold`); else if (r >= 70) oppose.push(`RSI ${r.toFixed(0)} overbought`);
      if (st <= 25) support.push(`Stoch ${st.toFixed(0)} oversold (reversal setup)`); else if (st >= 80) oppose.push(`Stoch ${st.toFixed(0)} overbought / chase risk`);
      if (regime === 'TRENDING_BULL') support.push('broad regime bullish');
      if (regime === 'TRENDING_BEAR') oppose.push('broad regime bearish');
      if (bearBreak) support.push('bear→bull live break');
      if (bullBreak) oppose.push('bull→bear live break');
    } else {
      add(e5 < e9 && e9 <= e21, 'EMA stack bearish', 'EMA stack not bearish');
      add(macd <= macdSignal, 'MACD below signal', 'MACD above signal');
      if (r >= 65) support.push(`RSI ${r.toFixed(0)} overbought`); else if (r <= 30) oppose.push(`RSI ${r.toFixed(0)} oversold`);
      if (st >= 75) support.push(`Stoch ${st.toFixed(0)} overbought (reversal setup)`); else if (st <= 20) oppose.push(`Stoch ${st.toFixed(0)} oversold / chase risk`);
      if (regime === 'TRENDING_BEAR') support.push('broad regime bearish');
      if (regime === 'TRENDING_BULL') oppose.push('broad regime bullish');
      if (bullBreak) support.push('bull→bear live break');
      if (bearBreak) oppose.push('bear→bull live break');
    }
    if (run >= 4) support.push(`runner score ${run}`);
    if (rev >= 4) support.push(`reversal score ${rev}`);
    if (tqs >= 60) support.push(`TQS ${tqs}`); else if (tqs < 50) oppose.push(`TQS only ${tqs}`);
    if (oppTqs >= tqs + 10) oppose.push(`opposite TQS ${oppTqs}`);
    return {direction:d,support:support.slice(0,5),oppose:oppose.slice(0,4)};
  }

  // ═══════════════════════════════════════════════════════════════
  // V24.1.34 PRICE-STRUCTURE VISION LAYER
  // Gives both AI decision paths a chart-like structural read without
  // changing the existing 64-feature model schema/weights mid-training.
  // It reads raw price structure (not pixels): swings, HH/HL/LH/LL,
  // support/resistance, channel slope, breakout/failure, acceleration,
  // pullback vs reversal, and recent directional persistence.
  // ═══════════════════════════════════════════════════════════════
  function aiPriceVision(asset, currentPrice) {
    const a = getAsset(asset);
    const px = Number(currentPrice || a?.lastPrice || 0);
    if (!a || !px) return {ready:false,direction:'NEUTRAL',up:0.5,confidence:0,label:'NO DATA',facts:[]};
    const p5 = Array.isArray(a.prices) ? a.prices.slice() : [];
    const p15 = getLiveTFView(a,'15s').prices || [];
    const p30 = getLiveTFView(a,'30s').prices || [];
    if (p5.length < 24 || p30.length < 10) return {ready:false,direction:'NEUTRAL',up:0.5,confidence:0,label:'WARMING',facts:[]};

    const norm=(v,scale)=>Math.max(-1,Math.min(1,(Number(v)||0)/Math.max(Number(scale)||0,1e-9)));
    const av=Math.max(atr(p30,7),Math.abs(px)*0.00035,1e-9);
    const last=(arr,n=1)=>arr.length>=n?Number(arr[arr.length-n]||0):0;
    const slope=(arr,n)=>arr.length>n?norm(last(arr)-Number(arr[arr.length-1-n]||last(arr)),Math.max(av*n*0.75,Math.abs(px)*0.001)):0;

    // Confirmed local swing pivots from closes. Use a slightly wider confirmation
    // than v24.1.34 so one noisy 5s wiggle cannot flip the whole structure read.
    const pivots=[];
    const src=p5.slice(-100);
    for(let i=3;i<src.length-3;i++){
      const v=src[i];
      const left=src.slice(i-3,i), right=src.slice(i+1,i+4);
      if(left.every(x=>v>=x)&&right.every(x=>v>x)) pivots.push({type:'H',value:v,i});
      if(left.every(x=>v<=x)&&right.every(x=>v<x)) pivots.push({type:'L',value:v,i});
    }
    const highs=pivots.filter(x=>x.type==='H').slice(-4);
    const lows=pivots.filter(x=>x.type==='L').slice(-4);
    const h1=highs.at(-1)?.value, h2=highs.at(-2)?.value;
    const l1=lows.at(-1)?.value, l2=lows.at(-2)?.value;
    const swingPad=av*0.12;
    const higherHigh=Number.isFinite(h1)&&Number.isFinite(h2)&&h1>h2+swingPad;
    const lowerHigh=Number.isFinite(h1)&&Number.isFinite(h2)&&h1<h2-swingPad;
    const higherLow=Number.isFinite(l1)&&Number.isFinite(l2)&&l1>l2+swingPad;
    const lowerLow=Number.isFinite(l1)&&Number.isFinite(l2)&&l1<l2-swingPad;

    const window=p5.slice(-42);
    const recentHigh=Math.max(...window), recentLow=Math.min(...window);
    const priorWindow=p5.slice(-84,-14);
    const priorHigh=priorWindow.length?Math.max(...priorWindow):recentHigh;
    const priorLow=priorWindow.length?Math.min(...priorWindow):recentLow;
    const distRes=(recentHigh-px)/av, distSup=(px-recentLow)/av;
    const nearResistance=distRes>=0&&distRes<0.75;
    const nearSupport=distSup>=0&&distSup<0.75;

    const v5=slope(p5,3), v15=slope(p15,2), v30=slope(p30,2);
    const channel=slope(p30,Math.min(8,p30.length-1));
    const channelStrongBull=channel>0.16, channelStrongBear=channel<-0.16;
    const accel=Math.max(-1,Math.min(1,v5-v30*0.55));
    const bullishMomentum=v5>0.12&&v15>0.03;
    const bearishMomentum=v5<-0.12&&v15<-0.03;
    const breakoutUp=px>priorHigh+av*0.12;
    const breakoutDown=px<priorLow-av*0.12;
    const failedUp=last(p5,2)>priorHigh&&px<priorHigh-av*0.06;
    const failedDown=last(p5,2)<priorLow&&px>priorLow+av*0.06;

    // Structural confirmation: a full bull/bear call needs two compatible clues.
    // A single lower high inside a rising channel is a pullback/transition, not a bear trend.
    const bullStructureVotes=(higherHigh?1:0)+(higherLow?1:0)+(channelStrongBull?1:0)+(v30>0.08?1:0)+(breakoutUp?1:0);
    const bearStructureVotes=(lowerHigh?1:0)+(lowerLow?1:0)+(channelStrongBear?1:0)+(v30<-0.08?1:0)+(breakoutDown?1:0);
    const bullConfirmed=(higherHigh&&higherLow)||(bullStructureVotes>=3&&!(lowerLow&&channelStrongBear));
    const bearConfirmed=(lowerHigh&&lowerLow)||(bearStructureVotes>=3&&!(higherHigh&&channelStrongBull));

    let score=0;
    const facts=[];
    if(higherHigh){score+=0.55;facts.push('higher high');}
    if(higherLow){score+=0.70;facts.push('higher low');}
    if(lowerHigh){score-=0.55;facts.push('lower high');}
    if(lowerLow){score-=0.70;facts.push('lower low');}
    // Broader channel gets more weight than one recent swing.
    score += channel*1.05 + v30*0.55 + v15*0.42 + v5*0.22;
    if(bullishMomentum){score+=0.38;facts.push('bullish momentum');}
    if(bearishMomentum){score-=0.38;facts.push('bearish momentum');}
    if(breakoutUp){score+=0.62;facts.push('upside breakout');}
    if(breakoutDown){score-=0.62;facts.push('downside breakdown');}
    if(failedUp){score-=0.58;facts.push('failed upside breakout');}
    if(failedDown){score+=0.58;facts.push('failed downside break');}
    if(nearResistance){score-=0.12;facts.push('near resistance');}
    if(nearSupport){score+=0.12;facts.push('near support');}

    let rawState='MIXED';
    if(channelStrongBull && v5<-0.10 && !bearConfirmed){rawState='BULL PULLBACK';facts.push('pullback inside bull structure');score+=0.18;}
    else if(channelStrongBear && v5>0.10 && !bullConfirmed){rawState='BEAR PULLBACK';facts.push('pullback inside bear structure');score-=0.18;}
    else if(bearConfirmed && !bullConfirmed){rawState='BEAR STRUCTURE';}
    else if(bullConfirmed && !bearConfirmed){rawState='BULL STRUCTURE';}
    else if(breakoutDown && bearStructureVotes>=2){rawState='BREAKDOWN';}
    else if(breakoutUp && bullStructureVotes>=2){rawState='BREAKOUT';}
    else if((bullStructureVotes>=2&&bearStructureVotes>=2) || (channelStrongBull&&lowerHigh) || (channelStrongBear&&higherLow)) rawState='TRANSITION';

    score=Math.max(-2.6,Math.min(2.6,score));
    const rawUp=1/(1+Math.exp(-score));
    const rawDir=rawUp>=0.5?'BUY':'SELL';

    // Hysteresis: require two consecutive opposite structural confirmations before
    // flipping BULL STRUCTURE <-> BEAR STRUCTURE. A true breakout/breakdown may flip immediately.
    const prev=a.__priceVisionState||{state:'MIXED',direction:'NEUTRAL',oppStreak:0};
    const prevBull=['BULL STRUCTURE','BREAKOUT','BULL PULLBACK'].includes(prev.state);
    const prevBear=['BEAR STRUCTURE','BREAKDOWN','BEAR PULLBACK'].includes(prev.state);
    let state=rawState, oppStreak=0;
    const hardBull=breakoutUp&&bullStructureVotes>=3;
    const hardBear=breakoutDown&&bearStructureVotes>=3;
    if(prevBull && ['BEAR STRUCTURE','BREAKDOWN'].includes(rawState) && !hardBear){
      oppStreak=(prev.oppStreak||0)+1;
      if(oppStreak<2){state='TRANSITION'; facts.push('bear reversal awaiting confirmation'); score=Math.max(score,-0.35);}
    } else if(prevBear && ['BULL STRUCTURE','BREAKOUT'].includes(rawState) && !hardBull){
      oppStreak=(prev.oppStreak||0)+1;
      if(oppStreak<2){state='TRANSITION'; facts.push('bull reversal awaiting confirmation'); score=Math.min(score,0.35);}
    }
    if(state===rawState) oppStreak=0;

    const up=1/(1+Math.exp(-score));
    const direction=up>=0.5?'BUY':'SELL';
    let confidence=Math.abs(up-0.5)*2;
    if(state==='TRANSITION'||state==='MIXED') confidence*=0.68;
    if((nearSupport&&direction==='SELL')||(nearResistance&&direction==='BUY')) confidence*=0.84;
    const label=`${state} · ${direction} ${(Math.max(up,1-up)*100).toFixed(0)}%`;
    a.__priceVisionState={state,direction,oppStreak,score,ts:Date.now()};
    return {ready:true,up,direction,confidence,score,label,state,rawState,facts:facts.slice(0,8),
      higherHigh,higherLow,lowerHigh,lowerLow,nearResistance,nearSupport,
      breakoutUp,breakoutDown,failedUp,failedDown,channelSlope:channel,
      velocity5:v5,velocity15:v15,velocity30:v30,acceleration:accel,
      bullStructureVotes,bearStructureVotes,bullConfirmed,bearConfirmed,
      support:recentLow,resistance:recentHigh,distSupportAtr:distSup,distResistanceAtr:distRes};
  }

  function aiIndicatorPrior(ind, vision) {
    const n = v => Number(v || 0);
    const tB=n(ind?.tqsBuy ?? lastIndicators?.tqsBuy), tS=n(ind?.tqsSell ?? lastIndicators?.tqsSell);
    const rB=n(ind?.runnerBuy ?? lastIndicators?.runnerBuyScore), rS=n(ind?.runnerSell ?? lastIndicators?.runnerSellScore);
    const vB=n(ind?.revBuy ?? lastIndicators?.v19RevBuy), vS=n(ind?.revSell ?? lastIndicators?.v19RevSell);
    const trB=n(ind?.tradBuy), trS=n(ind?.tradSell);
    const mq=Math.max(0,Math.min(100,n(ind?.marketQuality ?? lastIndicators?.marketQuality)));
    const regime=String(ind?.regime || lastIndicators?.regime || 'UNKNOWN');
    const bullBreak=!!(ind?.liveBearBreak || lastIndicators?.liveBearBreak); // bull -> bear
    const bearBreak=!!(ind?.liveBullBreak || lastIndicators?.liveBullBreak); // bear -> bull
    // Shared directional prior from the indicator engine. It is deliberately
    // bounded so it informs both AIs without replacing their learned models.
    let score=0;
    score += Math.max(-2.0,Math.min(2.0,(tB-tS)/18));
    score += Math.max(-1.2,Math.min(1.2,(trB-trS)/8));
    score += Math.max(-0.9,Math.min(0.9,(rB-rS)/8));
    score += Math.max(-0.9,Math.min(0.9,(vB-vS)/7));
    if (regime==='TRENDING_BULL') score += 0.45;
    if (regime==='TRENDING_BEAR') score -= 0.45;
    if (bearBreak) score += 0.75;
    if (bullBreak) score -= 0.75;
    // Price-structure vision is a bounded shared input. V24.1.36 reduces its
    // authority until exported outcome data proves it adds predictive value.
    // It can break ties and identify structure, but cannot overwhelm both models.
    if (vision?.ready) score += Math.max(-0.72, Math.min(0.72, Number(vision.score||0) * 0.32));
    score *= (0.55 + 0.45*(mq/100));
    const up=1/(1+Math.exp(-score));
    return {up,direction:up>=0.5?'BUY':'SELL',confidence:Math.abs(up-0.5)*2,score,tqsBuy:tB,tqsSell:tS,tradBuy:trB,tradSell:trS,runnerBuy:rB,runnerSell:rS,revBuy:vB,revSell:vS,mq,regime,vision:vision||null};
  }
  function aiReliabilityWeights(v23Acc,xgbAcc){
    const va=Math.max(0.45,Math.min(0.70,Number(v23Acc)||0.5));
    const xa=Math.max(0.45,Math.min(0.70,Number(xgbAcc)||0.5));
    const vr=0.10+Math.max(0,va-0.50), xr=0.10+Math.max(0,xa-0.50);
    const z=vr+xr||1;
    return {v23:vr/z,xgb:xr/z};
  }

  function recordAiDecision(asset, price, trace, models, sharedX) {
    try {
      const now=Date.now();
      const rec={
        id: decisionIdCounter++, ts:now, due:now+AI_HORIZON_MS,
        asset:String(asset||''), price:Number(price||0), targetMs:AI_HORIZON_MS,
        finalDecision:String(trace?.finalDecision||'HOLD'), controller:String(trace?.controller||'NONE'),
        why:String(trace?.why||''), disagreementType:String(trace?.disagreementType||'NONE'), agreement:!!trace?.agreement,
        regime:String(trace?.regime||'UNKNOWN'), trendIntegrity:String(trace?.trendIntegrity||''),
        tqsBuy:Number(trace?.tqsBuy||0), tqsSell:Number(trace?.tqsSell||0), mq:Number(trace?.mq||0),
        strategy:String(trace?.strategy||'NO PROPOSAL'), indicatorPrior:String(trace?.indicatorPrior||''),
        chartVision:String(trace?.chartVision||''), visionDirection:String(trace?.visionDirection||'NEUTRAL'), visionUp:Number(trace?.visionUp??0.5), visionConfidence:Number(trace?.visionConfidence||0), visionState:String(trace?.visionState||''), visionFacts:Array.isArray(trace?.visionFacts)?trace.visionFacts.slice():[],
        indicatorUp:Number(models?.indicatorUp ?? 0.5), rawV23Up:Number(models?.rawV23Up ?? 0.5), rawXgbUp:Number.isFinite(Number(models?.rawXgbUp))?Number(models.rawXgbUp):null,
        v23Up:Number(models?.v23Up ?? 0.5), xgbUp:Number.isFinite(Number(models?.xgbUp))?Number(models.xgbUp):null,
        ensembleUp:Number(models?.ensembleUp ?? 0.5),
        preferredDirection:Number(models?.ensembleUp ?? 0.5)>=0.5?'BUY':'SELL',
        weights:models?.weights?{...models.weights}:null,
        resolved:false, actualDirection:null, futurePrice:null, changePct:null, decisionCorrect:null, holdPreferredWouldWin:null,
        snapshotId:`D:${String(asset||'')}:${now}:${Math.round(Number(price||0)*1e8)}`,
        featureHash:Array.isArray(sharedX)?sharedX.slice(0,8).map(v=>Number(v||0).toFixed(4)).join('|'):null
      };
      decisionHistory.push(rec); decisionPending.push(rec);
      if(decisionHistory.length>DECISION_HISTORY_MAX) decisionHistory.splice(0,decisionHistory.length-DECISION_HISTORY_MAX);
      if(decisionPending.length>2400) decisionPending.splice(0,decisionPending.length-2400);
      aiLog('DECISION_RECORDED',{id:rec.id,asset:rec.asset,decision:rec.finalDecision,controller:rec.controller,agreement:rec.agreement,disagreementType:rec.disagreementType},false);
      return rec;
    } catch(_) { return null; }
  }

  function flushDecisionHistory() {
    const now=Date.now();
    for(let i=decisionPending.length-1;i>=0;i--){
      const r=decisionPending[i];
      if(!r || r.resolved){ decisionPending.splice(i,1); continue; }
      if(Number(r.due||0)>now) continue;
      const a=getAsset(r.asset); const future=Number(a?.lastPrice||0);
      if(!future || !r.price) continue;
      const ch=(future-r.price)/Math.max(Math.abs(r.price),1e-9);
      r.futurePrice=future; r.changePct=ch; r.resolved=true; r.resolvedAt=now;
      if(Math.abs(ch)<AI_MIN_MOVE){ r.actualDirection='FLAT'; r.decisionCorrect=null; r.holdPreferredWouldWin=null; }
      else {
        r.actualDirection=ch>0?'BUY':'SELL';
        if(r.finalDecision==='BUY'||r.finalDecision==='SELL') r.decisionCorrect=r.finalDecision===r.actualDirection;
        else r.holdPreferredWouldWin=r.preferredDirection===r.actualDirection;
      }
      aiLog('DECISION_RESOLVED',{id:r.id,asset:r.asset,decision:r.finalDecision,actual:r.actualDirection,correct:r.decisionCorrect,holdPreferredWouldWin:r.holdPreferredWouldWin,changePct:r.changePct},false);
      decisionPending.splice(i,1);
    }
  }

  function v23Decision(asset, price, ind, strategySig) {
    // ONE synchronized 64-feature snapshot feeds BOTH V23 and XGBoost.
    const sharedX=aiFeatures(asset,price,ind);
    const rawV23=v23PredictFromX(sharedX); V23_AI.last=rawV23;
    const acc = V23_AI.total > 0 ? V23_AI.correct / V23_AI.total : 0;
    const xgb = sharedX ? aiXgbLive(asset, sharedX) : {live:false,warm:false,trained:false,direction:null,confidence:0,up:null,status:'no-features'};
    const v23Warm = !!rawV23.warm && V23_AI.total >= V23_AI.minSamples && acc >= V23_AI.minAccuracy;
    const bothLive = v23Warm && xgb.live;

    // Common indicator prior: both model decisions see the same summary of
    // TQS/MQ, traditional votes, runner/reversal scores, regime and live break.
    // Raw model probabilities remain logged separately for auditability.
    const vision=aiPriceVision(asset,price);
    lastIndicators.chartVision=vision;
    const prior=aiIndicatorPrior(ind,vision);
    const PRIOR_W = bothLive ? 0.22 : 0.15;
    const v23Up=(1-PRIOR_W)*rawV23.up + PRIOR_W*prior.up;
    const xgbUp=xgb.live ? ((1-PRIOR_W)*xgb.up + PRIOR_W*prior.up) : null;
    // V24.1.43: keep a prior-adjusted XGB preview available while validation is
    // still building. Preview can CONFIRM a high-quality strategy setup, but it
    // cannot independently choose a direction or bypass risk/quality gates.
    const xgbPreviewUp=xgb.previewUp==null?null:((1-0.15)*xgb.previewUp + 0.15*prior.up);
    const v23Dir=v23Up>=0.5?'BUY':'SELL', v23Conf=Math.abs(v23Up-0.5)*2;
    const xgbDir=xgbUp==null?null:(xgbUp>=0.5?'BUY':'SELL'), xgbConf=xgbUp==null?0:Math.abs(xgbUp-0.5)*2;
    const xgbPreviewDir=xgbPreviewUp==null?null:(xgbPreviewUp>=0.5?'BUY':'SELL');
    const xgbPreviewConf=xgbPreviewUp==null?0:Math.abs(xgbPreviewUp-0.5)*2;

    const xgbVal=Number(xgb.validationAccuracy||AI_LAB.holdout?.holdoutAccuracy||0.5);
    const weights=aiReliabilityWeights(acc,xgbVal);
    let ensembleUp=v23Up, ensembleDirection=v23Dir, ensembleConfidence=v23Conf;
    let agreement=true;
    if (bothLive) {
      ensembleUp=weights.v23*v23Up + weights.xgb*xgbUp;
      ensembleDirection=ensembleUp>=0.5?'BUY':'SELL';
      ensembleConfidence=Math.abs(ensembleUp-0.5)*2;
      agreement=v23Dir===xgbDir;
    }
    const ensemble={rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,up:ensembleUp,direction:ensembleDirection,confidence:ensembleConfidence,agreement,bothLive,v23Warm,xgbLive:xgb.live,xgbStatus:xgb.status,indicatorPrior:prior,weights};

    const tqsBuy=Number(ind?.tqsBuy ?? lastIndicators?.tqsBuy ?? 0)||0;
    const tqsSell=Number(ind?.tqsSell ?? lastIndicators?.tqsSell ?? 0)||0;
    const mqNow=Number(ind?.marketQuality ?? lastIndicators?.marketQuality ?? 0)||0;
    const regimeNow=String(ind?.regime || lastIndicators?.regime || 'UNKNOWN');
    const liveBearBreak=!!(ind?.liveBearBreak || lastIndicators?.liveBearBreak);
    const liveBullBreak=!!(ind?.liveBullBreak || lastIndicators?.liveBullBreak);
    const sideProb=(direction,up)=>direction==='BUY'?Number(up??0.5):1-Number(up??0.5);
    const v23FavProb=sideProb(v23Dir,v23Up), xgbFavProb=xgbUp==null?null:sideProb(xgbDir,xgbUp), ensFavProb=sideProb(ensembleDirection,ensembleUp);
    const rawV23Text=`raw ${rawV23.direction} ${(sideProb(rawV23.direction,rawV23.up)*100).toFixed(0)}%`;
    const rawXgbText=xgb.live?`raw ${xgb.direction} ${(sideProb(xgb.direction,xgb.up)*100).toFixed(0)}%`:
      (xgb.previewDirection?`preview ${xgb.previewDirection} ${(sideProb(xgb.previewDirection,xgb.previewUp)*100).toFixed(0)}% · ${xgb.status}`:String(xgb.status||'warming'));
    const v23Text=`${v23Dir} ${(v23FavProb*100).toFixed(0)}%`;
    const xgbText=xgbUp!=null?`${xgbDir} ${(xgbFavProb*100).toFixed(0)}%`:String(xgb.status||'warming');
    const ensText=`${ensembleDirection} ${(ensFavProb*100).toFixed(0)}%`;
    const priorText=`${prior.direction} ${(sideProb(prior.direction,prior.up)*100).toFixed(0)}%`;
    const integrityText=liveBearBreak?'BULL→BEAR BREAK':liveBullBreak?'BEAR→BULL BREAK':'trend intact';
    const strategyDir=strategySig?.dir||null;
    const strategyText=strategyDir?`${strategyDir} · ${strategySig.mode||'strategy'} · TQS ${Number(strategySig.tqs||0)}`:'NO PROPOSAL';
    const v23Ctx=aiContextSummary(ind,v23Dir);
    const xgbContextDir=xgbDir||xgb.previewDirection||null;
    const xgbCtx=xgbContextDir?{...aiContextSummary(ind,xgbContextDir),live:!!xgb.live,status:xgb.status,
      preview:!xgb.live,previewUp:xgb.previewUp,validated:!!xgb.validated,warm:!!xgb.warm,
      validationSamples:Number(xgb.validationSamples||0),validationAccuracy:Number(xgb.validationAccuracy||0),marketSamples:Number(xgb.marketSamples||0)}:
      {direction:'WAITING',support:[`XGB ${xgb.status||'collecting'}`],oppose:[],live:false,status:xgb.status||'collecting',preview:true,validated:!!xgb.validated,warm:!!xgb.warm,validationSamples:Number(xgb.validationSamples||0),validationAccuracy:Number(xgb.validationAccuracy||0),marketSamples:Number(xgb.marketSamples||0)};

    const hardDisagreement=bothLive&&!agreement&&v23Conf>=0.30&&xgbConf>=0.30;
    const softDisagreement=bothLive&&!agreement&&!hardDisagreement;
    const traceBase={v23:v23Text,xgb:xgbText,ensemble:ensText,rawV23:rawV23Text,rawXgb:rawXgbText,indicatorPrior:priorText,
      agreement,bothLive,disagreementType:hardDisagreement?'HARD':softDisagreement?'SOFT':'NONE',weights,regime:regimeNow,trendIntegrity:integrityText,
      tqsBuy,tqsSell,mq:mqNow,strategy:strategyText,v23Context:v23Ctx,xgbContext:xgbCtx,
      chartVision:vision?.label||'WARMING',visionDirection:vision?.direction||'NEUTRAL',visionUp:Number(vision?.up??0.5),visionConfidence:Number(vision?.confidence||0),visionState:vision?.state||'',visionFacts:Array.isArray(vision?.facts)?vision.facts.slice():[],
      finalDecision:'HOLD',controller:'NONE',why:'evaluating'};
    const commitTrace=(finalDecision,controller,why,extra={})=>{lastIndicators.aiDecisionTrace={...traceBase,finalDecision,controller,why,...extra};lastIndicators.aiLastDecision={finalDecision,controller,why,ts:Date.now()};if(why!=='evaluating')recordAiDecision(asset,price,lastIndicators.aiDecisionTrace,{rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,weights},sharedX);};
    lastIndicators.v23AI={rawUp:rawV23.up,up:v23Up,direction:v23Dir,confidence:v23Conf,trained:V23_AI.trained,warm:rawV23.warm,accuracy:acc};
    lastIndicators.xgbAI={rawUp:xgb.up,up:xgbUp,direction:xgbDir,confidence:xgbConf,live:xgb.live,status:xgb.status,marketSpecific:xgb.marketSpecific,marketSamples:xgb.marketSamples,previewUp:xgb.previewUp,previewDirection:xgb.previewDirection,previewConfidence:xgb.previewConfidence,validated:xgb.validated,validationSamples:xgb.validationSamples,validationAccuracy:xgb.validationAccuracy,warm:xgb.warm};
    lastIndicators.aiEnsemble=ensemble; lastIndicators.aiIndicatorPrior=prior;
    commitTrace('HOLD','NONE','evaluating');
    aiLog('PREDICTION',{asset,rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,visionUp:vision?.up,visionState:vision?.state,ensembleUp,direction:ensembleDirection,confidence:ensembleConfidence,agreement,disagreementType:traceBase.disagreementType,bothLive,weights,v23Trained:V23_AI.trained,xgbTrained:xgb.trained,strategyDir},false);

    const dirTqs=d=>d==='BUY'?tqsBuy:tqsSell;
    const counterRegime=d=>(d==='SELL'&&regimeNow==='TRENDING_BULL')||(d==='BUY'&&regimeNow==='TRENDING_BEAR');
    const counterBreakOk=d=>(d==='SELL'&&liveBearBreak)||(d==='BUY'&&liveBullBreak);
    const qualityOk=d=>mqNow>=53&&dirTqs(d)>=53&&(!counterRegime(d)||counterBreakOk(d));
    const priorSupports=d=>prior.direction===d&&prior.confidence>=0.08;
    const priorFavProb=d=>sideProb(d,prior.up);
    const visionAligned=d=>!!vision?.ready && vision.direction===d && vision.confidence>=0.18;
    const trendAligned=d=>(d==='BUY'&&(regimeNow==='TRENDING_BULL'||liveBullBreak||visionAligned('BUY')))||(d==='SELL'&&(regimeNow==='TRENDING_BEAR'||liveBearBreak||visionAligned('SELL')));
    // Strong-trend capture: when BOTH AIs agree, the shared indicator prior is
    // very strong, and live trend structure agrees, TQS becomes a soft quality
    // input instead of an absolute veto. This is specifically for the clean
    // directional moves that v24.1.29 was skipping at TQS ~47-52.
    const strongTrendQualityOk=d=>mqNow>=50&&dirTqs(d)>=47&&prior.direction===d&&priorFavProb(d)>=0.70&&trendAligned(d)&&(!counterRegime(d)||counterBreakOk(d));

    // V24.1.43 anti-chase / exhaustion guard.
    // A model is not allowed to enter AFTER a move is already stretched into
    // support/resistance just because the trend indicators are still pointing
    // the same way. This specifically blocks the bad late SELL seen when Stoch
    // was ~15 at the recent low while price-structure vision leaned bullish.
    const stNow=Number(ind?.stoch ?? lastIndicators?.stoch ?? 50);
    const rsiNow=Number(ind?.rsi ?? ind?.rsi30 ?? lastIndicators?.rsi ?? 50);
    const visionOpposes=d=>!!vision?.ready && vision.direction && vision.direction!==d && Number(vision.confidence||0)>=0.10;
    const visionBreakSupports=d=>!!vision?.ready && ((d==='BUY'&&['BREAKOUT','BULL STRUCTURE'].includes(String(vision.state||'')))||(d==='SELL'&&['BREAKDOWN','BEAR STRUCTURE'].includes(String(vision.state||''))));
    const exhaustedAgainst=d=>(d==='SELL'&&(stNow<=20||rsiNow<=30))||(d==='BUY'&&(stNow>=80||rsiNow>=70));
    const aiAntiChaseBlocked=d=>exhaustedAgainst(d)&&(!visionBreakSupports(d)||visionOpposes(d));

    // V24.1.49 bootstrap exhaustion filter. Strategy-bootstrap was responsible
    // for virtually every entry in the 35-trade audit, including late BUYs at
    // RSI ~70 / Stoch ~85. A mature extreme now needs an actual price-structure
    // breakout/breakdown AND stronger TQS before bootstrap can follow it.
    const bootstrapExhausted=d=>(d==='BUY'&&(rsiNow>=68&&stNow>=78))||(d==='SELL'&&(rsiNow<=32&&stNow<=22));
    const bootstrapFreshBreak=d=>visionBreakSupports(d)||counterBreakOk(d);

    // V24.1.49 STRUCTURE-DIRECT ROUTE:
    // If the legacy strategy engine produces NO PROPOSAL, a confirmed fast
    // structure break may create its own proposal when price-structure vision,
    // the shared indicator prior and XGBoost all agree. MQ is contextual here:
    // low-40s is acceptable only under this unusually strong alignment.
    const visionStateNow=String(vision?.state||'');
    const hardStructureBreak=d=>(d==='SELL'&&(liveBearBreak||visionStateNow==='BREAKDOWN')) ||
      (d==='BUY'&&(liveBullBreak||visionStateNow==='BREAKOUT'));
    const xgbSupportDir=xgb.live?xgbDir:xgbPreviewDir;
    const xgbSupportUp=xgb.live?xgbUp:xgbPreviewUp;
    const xgbSupportConf=xgb.live?xgbConf:xgbPreviewConf;
    const structureCandidate=!strategyDir && hardStructureBreak('SELL')?'SELL':
      (!strategyDir && hardStructureBreak('BUY')?'BUY':null);
    if(structureCandidate){
      const sd=structureCandidate;
      const visionStrong=!!vision?.ready && vision.direction===sd && Number(vision.confidence||0)>=0.55;
      const priorStrong=prior.direction===sd && priorFavProb(sd)>=0.76;
      const xgbSupports=xgbSupportDir===sd && xgbSupportConf>=0.10; // ~55%+ favored side
      const v23HardOpposes=v23Dir!==sd && v23Conf>=0.30;
      const tqsDirect=dirTqs(sd);
      const contextualMqOk=mqNow>=40 && tqsDirect>=45;
      const directAntiChase=!aiAntiChaseBlocked(sd);
      if(visionStrong&&priorStrong&&xgbSupports&&!v23HardOpposes&&contextualMqOk&&directAntiChase){
        const xv=sideProb(sd,xgbSupportUp);
        const vv=sideProb(sd,v23Up);
        const why=`STRUCTURE DIRECT ${sd} · ${vision?.label||visionStateNow} · IND ${priorText} · ${xgb.live?'XGB':'XGB preview'} ${(xv*100).toFixed(0)}% · V23 ${(vv*100).toFixed(0)}% · TQS ${tqsDirect} · MQ ${mqNow}`;
        const sig={dir:sd,mode:'structure-direct',str:Math.round(Math.max(Number(vision.confidence||0),priorFavProb(sd),xv)*100),
          confidence:Math.max(Number(vision.confidence||0),priorFavProb(sd),xv),tradeType:'STRUCTURE_ALIGNMENT',tqs:tqsDirect,
          reason:why,reasons:['confirmed fast structure break','price-structure vision confirms','indicator prior confirms','XGBoost supports','contextual MQ gate'],
          measurement:{strategy:'STRUCTURE_DIRECT',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,visionUp:Number(vision?.up??0.5),tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
        commitTrace(sd,'STRUCTURE_DIRECT',why,{structureDirect:true,decisionContext:aiContextSummary(ind,sd)});
        aiLog('AI_ENTRY',{asset,dir:sd,controller:'STRUCTURE_DIRECT',why},true);
        return {sig,reason:why};
      }
    }

    // V24.1.43 EARLY AI CO-PILOT:
    // Before both models earn full live authority, they may CONFIRM a strong
    // strategy proposal. They cannot invent a direction or bypass risk gates.
    const earlyStrategyDir=strategySig?.dir||null;
    const earlyV23Ready=V23_AI.trained>=40;
    const earlyXgbReady=!!xgb.trained && xgbPreviewDir!=null;
    const earlyModelsAgree=!!earlyStrategyDir && earlyV23Ready && earlyXgbReady &&
      v23Dir===earlyStrategyDir && xgbPreviewDir===earlyStrategyDir;
    const earlyModelStrength=v23Conf>=0.16 && xgbPreviewConf>=0.16; // ~=58% each
    const earlyQuality=!!earlyStrategyDir && mqNow>=54 && dirTqs(earlyStrategyDir)>=58 &&
      prior.direction===earlyStrategyDir && priorFavProb(earlyStrategyDir)>=0.68 &&
      (!counterRegime(earlyStrategyDir)||counterBreakOk(earlyStrategyDir));
    if(!bothLive && earlyModelsAgree && earlyModelStrength && earlyQuality &&
       !aiAntiChaseBlocked(earlyStrategyDir) && v23StrategyQualityOk(strategySig)){
      const xv=sideProb(earlyStrategyDir,xgbPreviewUp);
      const vv=sideProb(earlyStrategyDir,v23Up);
      const why=`AI CO-PILOT ${earlyStrategyDir} · strategy + V23 ${(vv*100).toFixed(0)}% + XGB preview ${(xv*100).toFixed(0)}% agree · IND ${priorText} · TQS ${dirTqs(earlyStrategyDir)} · MQ ${mqNow}`;
      const sig={...strategySig,mode:'ai-copilot',tradeType:'AI_COPILOT',
        confidence:Math.max(Number(strategySig.confidence||0),Math.min(vv,xv)),
        reason:why,reasons:[...(Array.isArray(strategySig.reasons)?strategySig.reasons:[]),
          'V23 confirms strategy','XGBoost preview confirms strategy','indicator prior confirms','XGB not yet independent']};
      commitTrace(earlyStrategyDir,'AI_COPILOT',why,{earlyAi:true,xgbPreviewUp,v23Up});
      aiLog('AI_ENTRY',{asset,dir:earlyStrategyDir,controller:'AI_COPILOT',why},true);
      return {sig,reason:why};
    }

    // Agreement path: lower than the old ~81% favored-side requirement because
    // both independent models + indicators must now line up on the same snapshot.
    const ENSEMBLE_EDGE_MIN=0.24; // ~=62% favored-side probability
    const TREND_CAPTURE_EDGE_MIN=0.20; // ~=60% favored-side when BOTH AIs + strong indicators align
    const normalAgreementOk=qualityOk(ensembleDirection)&&priorSupports(ensembleDirection);
    const trendCaptureOk=ensembleConfidence>=TREND_CAPTURE_EDGE_MIN&&strongTrendQualityOk(ensembleDirection);
    if(bothLive&&agreement&&ensembleConfidence>=TREND_CAPTURE_EDGE_MIN&&(normalAgreementOk||trendCaptureOk)&&!aiAntiChaseBlocked(ensembleDirection)){
      const captureTag=normalAgreementOk?'AI AGREEMENT':'AI TREND CAPTURE';
      const why=`${captureTag} ${ensembleDirection} ${(ensFavProb*100).toFixed(0)}% · V23 ${v23Text} · XGB ${xgbText} · IND ${priorText} · VISION ${vision?.label||'—'} · TQS ${dirTqs(ensembleDirection)} · MQ ${mqNow}`;
      const sig={dir:ensembleDirection,mode:'v23+xgb-ai',str:Math.round(ensembleConfidence*100),confidence:sideProb(ensembleDirection,ensembleUp),tradeType:'AI_ENSEMBLE',tqs:dirTqs(ensembleDirection),reason:why,reasons:['same feature snapshot','V23 + XGBoost agree',normalAgreementOk?'normal quality gate':'strong trend capture gate','indicator prior confirms',vision?.ready?'price-structure vision active':'vision warming'],measurement:{strategy:'V23+XGB',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,agreement,tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
      commitTrace(ensembleDirection,'ENSEMBLE',why,{decisionContext:aiContextSummary(ind,ensembleDirection)}); aiLog('AI_ENTRY',{asset,dir:ensembleDirection,controller:'ENSEMBLE',why},true); return {sig,reason:why};
    }

    // Soft disagreement: let a clearly stronger model win only when the shared
    // indicator prior, TQS/MQ and live trend integrity support that same side.
    const XGB_EDGE_MIN=0.32, V23_EDGE_MIN=0.36; // ~66% / 68% favored-side; still stricter than ensemble
    const independentQualityOk=d=>qualityOk(d)||(mqNow>=52&&dirTqs(d)>=49&&prior.direction===d&&priorFavProb(d)>=0.75&&trendAligned(d)&&(!counterRegime(d)||counterBreakOk(d)));
    if(bothLive&&softDisagreement){
      if(xgbConf>=XGB_EDGE_MIN&&v23Conf<=0.26&&priorSupports(xgbDir)&&independentQualityOk(xgbDir)&&!aiAntiChaseBlocked(xgbDir)){
        const why=`SOFT DISAGREEMENT → XGB ${xgbDir} ${(xgbFavProb*100).toFixed(0)}% wins · V23 only ${(v23FavProb*100).toFixed(0)}% ${v23Dir} · IND ${priorText} · TQS ${dirTqs(xgbDir)} · MQ ${mqNow}`;
        const sig={dir:xgbDir,mode:'xgb-ai',str:Math.round(xgbConf*100),confidence:sideProb(xgbDir,xgbUp),tradeType:'XGB_SOFT_WIN',tqs:dirTqs(xgbDir),reason:why,reasons:['soft model disagreement','XGBoost stronger','indicator prior confirms'],measurement:{strategy:'XGBoost',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,agreement:false,tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
        commitTrace(xgbDir,'XGBOOST',why,{decisionContext:aiContextSummary(ind,xgbDir)}); aiLog('AI_ENTRY',{asset,dir:xgbDir,controller:'XGBOOST',why},true); return {sig,reason:why};
      }
      if(v23Conf>=V23_EDGE_MIN&&xgbConf<=0.26&&priorSupports(v23Dir)&&independentQualityOk(v23Dir)&&!aiAntiChaseBlocked(v23Dir)){
        const why=`SOFT DISAGREEMENT → V23 ${v23Dir} ${(v23FavProb*100).toFixed(0)}% wins · XGB only ${(xgbFavProb*100).toFixed(0)}% ${xgbDir} · IND ${priorText} · TQS ${dirTqs(v23Dir)} · MQ ${mqNow}`;
        const sig={dir:v23Dir,mode:'v23-ai',str:Math.round(v23Conf*100),confidence:sideProb(v23Dir,v23Up),tradeType:'V23_SOFT_WIN',tqs:dirTqs(v23Dir),reason:why,reasons:['soft model disagreement','V23 stronger','indicator prior confirms'],measurement:{strategy:'V23',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,agreement:false,tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
        commitTrace(v23Dir,'V23',why,{decisionContext:aiContextSummary(ind,v23Dir)}); aiLog('AI_ENTRY',{asset,dir:v23Dir,controller:'V23',why},true); return {sig,reason:why};
      }
    }

    // Independent model path is still available when the other model is weak,
    // but never through a hard disagreement.
    if(!hardDisagreement&&xgb.live&&xgbConf>=XGB_EDGE_MIN&&priorSupports(xgbDir)&&independentQualityOk(xgbDir)&&!aiAntiChaseBlocked(xgbDir)&&(!v23Warm||v23Dir===xgbDir||v23Conf<0.26)){
      const why=`XGB INDEPENDENT ${xgbDir} ${(xgbFavProb*100).toFixed(0)}% · IND ${priorText} · V23 ${v23Text} · TQS ${dirTqs(xgbDir)} · MQ ${mqNow}`;
      const sig={dir:xgbDir,mode:'xgb-ai',str:Math.round(xgbConf*100),confidence:sideProb(xgbDir,xgbUp),tradeType:'XGB_INDEPENDENT',tqs:dirTqs(xgbDir),reason:why,reasons:['XGBoost strong','indicator prior confirms'],measurement:{strategy:'XGBoost',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,agreement,tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
      commitTrace(xgbDir,'XGBOOST',why,{decisionContext:aiContextSummary(ind,xgbDir)}); aiLog('AI_ENTRY',{asset,dir:xgbDir,controller:'XGBOOST',why},true); return {sig,reason:why};
    }
    if(!hardDisagreement&&v23Warm&&v23Conf>=V23_EDGE_MIN&&priorSupports(v23Dir)&&independentQualityOk(v23Dir)&&!aiAntiChaseBlocked(v23Dir)&&(!xgb.live||xgbDir===v23Dir||xgbConf<0.26)){
      const why=`V23 INDEPENDENT ${v23Dir} ${(v23FavProb*100).toFixed(0)}% · IND ${priorText} · XGB ${xgbText} · TQS ${dirTqs(v23Dir)} · MQ ${mqNow}`;
      const sig={dir:v23Dir,mode:'v23-ai',str:Math.round(v23Conf*100),confidence:sideProb(v23Dir,v23Up),tradeType:'V23_INDEPENDENT',tqs:dirTqs(v23Dir),reason:why,reasons:['V23 strong','indicator prior confirms'],measurement:{strategy:'V23',rawV23Up:rawV23.up,rawXgbUp:xgb.up,v23Up,xgbUp,indicatorUp:prior.up,ensembleUp,agreement,tqsBuy,tqsSell,mq:mqNow,regime:regimeNow}};
      commitTrace(v23Dir,'V23',why,{decisionContext:aiContextSummary(ind,v23Dir)}); aiLog('AI_ENTRY',{asset,dir:v23Dir,controller:'V23',why},true); return {sig,reason:why};
    }

    if ((bothLive&&agreement&&aiAntiChaseBlocked(ensembleDirection)) || (xgb.live&&aiAntiChaseBlocked(xgbDir)) || (v23Warm&&aiAntiChaseBlocked(v23Dir))) {
      const d = bothLive&&agreement ? ensembleDirection : (xgb.live&&aiAntiChaseBlocked(xgbDir) ? xgbDir : v23Dir);
      const why=`HOLD · ANTI-CHASE ${d} blocked · Stoch ${stNow.toFixed(0)} · RSI ${rsiNow.toFixed(0)} · VISION ${vision?.label||'—'} · waiting for reset/pullback or confirmed break`;
      commitTrace('HOLD','NONE',why,{antiChase:true,stoch:stNow,rsi:rsiNow});
      aiLog('AI_WAIT',{asset,reason:why},true);
      return {skip:true,reason:why};
    }

    // Strategy remains proposal-only once both AIs are live; bootstrap fallback
    // survives only while one/both models are not ready.
    if(strategySig&&strategySig.dir&&v23StrategyQualityOk(strategySig)){
      const sd=strategySig.dir;
      if(bothLive){
        const why=`HOLD · STRATEGY PROPOSAL ${sd} · AI final authority · ${hardDisagreement?'HARD DISAGREEMENT':softDisagreement?'SOFT DISAGREEMENT':'AI gates not met'} · IND ${priorText}`;
        commitTrace('HOLD','NONE',why,{strategyProposal:sd}); aiLog('AI_WAIT',{asset,reason:why},true); return {skip:true,reason:why};
      }

      // V24.1.49 PRE-AUTHORITY AI VETO.
      // V23/XGB still cannot invent a trade before validation, but if BOTH
      // models independently lean against the bootstrap proposal with useful
      // confidence, the indicator engine must wait instead of blindly firing.
      // A very strong fresh breakout can override this veto so we do not freeze
      // clean trend continuation entries.
      const opp=sd==='BUY'?'SELL':'BUY';
      const v23Opposes=v23Dir===opp && v23Conf>=0.10;          // ~55%+
      const xgbPreviewOpposes=xgbPreviewDir===opp && xgbPreviewConf>=0.12; // ~56%+
      const bothPreviewOppose=earlyV23Ready&&earlyXgbReady&&v23Opposes&&xgbPreviewOpposes;
      const strongBootstrapOverride=Number(strategySig.tqs||0)>=80&&mqNow>=60&&bootstrapFreshBreak(sd)&&prior.direction===sd&&priorFavProb(sd)>=0.72;
      if(bothPreviewOppose&&!strongBootstrapOverride){
        const vv=sideProb(opp,v23Up), xv=sideProb(opp,xgbPreviewUp);
        const why=`HOLD · AI BOOTSTRAP VETO ${sd} · V23 ${opp} ${(vv*100).toFixed(0)}% + XGB preview ${opp} ${(xv*100).toFixed(0)}% · TQS ${Number(strategySig.tqs||0)} · MQ ${mqNow}`;
        commitTrace('HOLD','AI_BOOTSTRAP_VETO',why,{strategyProposal:sd,v23Opposes:true,xgbPreviewOpposes:true});
        aiLog('AI_WAIT',{asset,reason:why},true); return {skip:true,reason:why};
      }

      const exhaustedBootstrap=bootstrapExhausted(sd);
      const exhaustionOverride=bootstrapFreshBreak(sd)&&Number(strategySig.tqs||0)>=75&&mqNow>=56&&prior.direction===sd;
      if(exhaustedBootstrap&&!exhaustionOverride){
        const why=`HOLD · BOOTSTRAP EXHAUSTION ${sd} · RSI ${rsiNow.toFixed(0)} · Stoch ${stNow.toFixed(0)} · needs fresh break + TQS 75+`;
        commitTrace('HOLD','BOOTSTRAP_EXHAUSTION',why,{strategyProposal:sd,rsi:rsiNow,stoch:stNow});
        aiLog('AI_WAIT',{asset,reason:why},true); return {skip:true,reason:why};
      }

      if(mqNow>=55&&(!counterRegime(sd)||counterBreakOk(sd)||Number(strategySig.tqs||0)>=75)){
        const why=`STRATEGY BOOTSTRAP ${sd} · AI not fully live · TQS ${Number(strategySig.tqs||0)} · MQ ${mqNow}`;
        commitTrace(sd,'STRATEGY_BOOTSTRAP',why); return {sig:{...strategySig,mode:'strategy-bootstrap'},reason:why};
      }
    }

    const blockers=[];
    if(hardDisagreement) blockers.push('HARD V23/XGB disagreement');
    else if(softDisagreement) blockers.push('soft disagreement without clear winner');
    if(!priorSupports(ensembleDirection)) blockers.push(`indicators favor ${prior.direction}`);
    if(mqNow<53) blockers.push(`MQ ${mqNow}<53`);
    if(dirTqs(ensembleDirection)<53&&!strongTrendQualityOk(ensembleDirection)) blockers.push(`${ensembleDirection} TQS ${dirTqs(ensembleDirection)}<53 (trend-capture min 47)`);
    const reason=`HOLD · V23 ${v23Text} · XGB ${xgbText} · IND ${priorText} · ENS ${ensText} · ${agreement?'AGREE':hardDisagreement?'HARD DISAGREE':'SOFT DISAGREE'} · ${regimeNow} · ${integrityText}${blockers.length?' · '+blockers.join(' · '):''}`;
    commitTrace('HOLD','NONE',reason,{blockers}); aiLog('AI_WAIT',{asset,reason},false); return {skip:true,reason};
  }

  function aiForward(x) {
    // 64→32 Leaky ReLU hidden layer (v19.0.0 expansion) (row-major storage)
    const h = new Array(AI_HIDDEN);
    for (let j = 0; j < AI_HIDDEN; j++) {
      let sum = aiState.b1[j];
      const base = j * AI_FEATURES;
      for (let i = 0; i < AI_FEATURES; i++) sum += (x[i] || 0) * (aiState.w1[base + i] || 0);
      h[j] = sum > 0 ? sum : sum * 0.01;  // Leaky ReLU — prevents dead neurons
    }
    // 32→1 sigmoid output
    let out = aiState.b2;
    for (let j = 0; j < AI_HIDDEN; j++) out += h[j] * (aiState.w2[j] || 0);
    return { raw: out, prob: aiSigmoid(out), hidden: h };
  }

  function aiNormalize(v, scale) {
    if (!isFinite(v) || !isFinite(scale) || scale === 0) return 0;
    return Math.max(-1, Math.min(1, v / scale));
  }

  function aiSlope(prices, n) {
    if (!prices || prices.length < n + 1) return 0;
    const a = prices[prices.length - n - 1], b = prices[prices.length - 1];
    return aiNormalize(b - a, Math.max(Math.abs(a) * 0.003, 1e-9));
  }

  function aiSetupKey(ind, meta=null) {
    if (ind) {
      if (ind.runnerBuyFresh) return 'RUNNER_BUY';
      if (ind.runnerSellFresh) return 'RUNNER_SELL';
      if (ind.reversalBuyFresh) return 'REVERSAL_BUY';
      if (ind.reversalSellFresh) return 'REVERSAL_SELL';
    }
    const raw=String(meta?.setupType||meta?.tradeType||'').toUpperCase();
    const dir=String(meta?.setupDir||'').toUpperCase();
    if (raw.includes('REVERS') && (dir==='BUY'||dir==='SELL')) return `REVERSAL_${dir}`;
    if ((raw.includes('RUNNER')||raw.includes('PULLBACK')||raw.includes('BREAKOUT')) && (dir==='BUY'||dir==='SELL')) return `RUNNER_${dir}`;
    if (ind?.regime==='TRENDING_BULL') return 'REGIME_BULL';
    if (ind?.regime==='TRENDING_BEAR') return 'REGIME_BEAR';
    return 'GENERIC';
  }

  function aiHistoricalSetupEdge(asset, ind) {
    const mp=aiMarketProfile(asset);
    const key=aiSetupKey(ind);
    const st=mp?.setupStats?.[key];
    const n=Number(st?.total||0);
    if(n<12) return 0;
    // Bayesian shrinkage toward 50% prevents a tiny setup history from becoming
    // a strong feature. Positive means this market historically resolves UP.
    const up=Number(st?.up||0);
    const p=(up+6)/(n+12);
    return Math.max(-1,Math.min(1,(p-0.5)*2));
  }

  // ════════════════════════════════════════════════════════════
  // V219 MULTIMODAL VISUAL MEMORY
  // Background captures the visible 4-chart grid every ~3 seconds, extracts
  // pixels in RAM, and sends ONLY compact visual measurements here. Images are
  // never persisted. The newest 10 minutes are maintained as rolling summaries.
  // Old images can therefore never become live evidence after a reload.
  // ════════════════════════════════════════════════════════════
  const V219_VISUAL_FEATURES=16;
  function v219MigrateFeatureVector(x){
    if(!Array.isArray(x)) return x;
    if(x.length===88) return x.concat(new Array(16).fill(0));
    return x;
  }
  function v219MigrateImportedSamples(root){
    const seen=new WeakSet();
    function walk(v){
      if(!v||typeof v!=='object'||seen.has(v)) return;
      seen.add(v);
      if(Array.isArray(v)){
        for(let i=0;i<v.length;i++){
          const q=v[i];
          if(q&&typeof q==='object'&&Array.isArray(q.x)&&q.x.length===88) q.x=v219MigrateFeatureVector(q.x);
          else walk(q);
        }
      } else {
        if(Array.isArray(v.x)&&v.x.length===88) v.x=v219MigrateFeatureVector(v.x);
        for(const k of Object.keys(v)) walk(v[k]);
      }
    }
    walk(root); return root;
  }
  const v219VisualByAsset=Object.create(null);
  function v219VisualVector(asset){
    const v=v219VisualByAsset[String(asset||'')];
    if(!v || !Array.isArray(v.features) || v.features.length!==V219_VISUAL_FEATURES) return new Array(V219_VISUAL_FEATURES).fill(0);
    // stale visual context is never used as current evidence
    if(Date.now()-Number(v.at||0)>10000) return new Array(V219_VISUAL_FEATURES).fill(0);
    return v.features.map(x=>Math.max(-1,Math.min(1,Number(x)||0)));
  }
  function v219SyncVisionAssets(){
    try{
      const rows=Object.keys(visibleChartSlots).sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true}))
        .map(k=>String(visibleChartSlots[k]||'')).filter(Boolean).slice(0,4);
      if(rows.length) chrome.runtime.sendMessage({type:'V219_VISION_GRID_ASSETS',assets:rows}).catch(()=>{});
    }catch(_){}
  }
  function aiFeatures(asset, currentPrice, ind) {
    const a = getAsset(asset);
    const px = Number(currentPrice || a.lastPrice || 0);
    if (!px) return null;
    const tf = k => k === '5s' ? a.prices.slice() : getLiveTFView(a, k).prices;
    const p5 = tf('5s'), p15 = tf('15s'), p30 = tf('30s'), p1m = tf('60s'), p3m = tf('180s'), p5m = tf('300s');
    const out = [];
    const add = v => out.push(Math.max(-1, Math.min(1, Number(v) || 0)));
    const ret = p => p.length >= 2 ? aiNormalize(p[p.length-1] - p[p.length-2], Math.max(Math.abs(p[p.length-2]) * 0.001, 1e-9)) : 0;
    const trend = p => p.length >= 8 ? aiNormalize(ema(p,5) - ema(p,9), Math.max(atr(p,7), Math.abs(p[p.length-1])*0.001, 1e-9)) : 0;
    const mom = p => p.length >= 6 ? aiSlope(p, Math.min(5, p.length-1)) : 0;
    const rs = p => p.length >= 8  ? (rsi(p,5)  - 50) / 50 : 0;
    const mac = p => {
      if (p.length < 12) return 0;
      const e3=ema(p,3), e10=ema(p,10), av=Math.max(atr(p,7), Math.abs(px)*0.001,1e-9);
      return aiNormalize(e3-e10,av);
    };
    const structure = p => {
      if (p.length < 8) return 0;
      const zz = swingStructureZigZag(p);
      return zz.trend === 'TRENDING_BULL' || zz.trend === 'BULLISH' ? 1 : zz.trend === 'TRENDING_BEAR' || zz.trend === 'BEARISH' ? -1 : 0;
    };
    const cWickUp = (c) => { if (!c) return 0; const rng = c[1]-c[2]; return rng > 0 ? (c[1]-Math.max(c[0],c[3]))/rng : 0; };
    const cWickLo = (c) => { if (!c) return 0; const rng = c[1]-c[2]; return rng > 0 ? (Math.min(c[0],c[3])-c[2])/rng : 0; };
    const now = a.lastTickSec || Math.floor(Date.now()/1000);
    const curB = BUCKET_SEC * Math.floor(now / BUCKET_SEC);
    const prevB = curB - BUCKET_SEC;
    // Features 0-17: 6 timeframes × 3 (return, trend, RSI)
    for (const p of [p5,p15,p30,p1m,p3m,p5m]) { add(ret(p)); add(trend(p)); add(rs(p)); }
    // Features 18-23: candle anatomy (body/wick/shape for 30s micro-decisions)
    {
      const prev2B = curB - BUCKET_SEC*2;
      const prev3B = curB - BUCKET_SEC*3;
      const cBodyPct = (c) => { if (!c) return 0; const rng = c[1]-c[2]; return rng > 0 ? Math.abs(c[3]-c[0])/rng : 0; };
      const cSign  = (c) => c && c[3] >= c[0] ? 1 : c ? -1 : 0;
      const c1 = a.rates[prevB], c2 = a.rates[prev2B], c3 = a.rates[prev3B];
      add(cBodyPct(c1));                           // 18: candle body %
      add(cWickUp(c1));                            // 19: upper wick %
      add(cWickLo(c1));                            // 20: lower wick %
      add(c1 && (c1[1]-c1[2])>0 ? (c1[3]-c1[0])/(c1[1]-c1[2]) : 0); // 21: signed body/range
      add(cSign(c2) * cBodyPct(c2));               // 22: prev candle body (signed)
      add((cSign(c1) + cSign(c2) + cSign(c3)) / 3); // 23: last 3 candle dir (-1..1)
    }
    // Features 24-31: micro velocity + session (faster signals for 15s/30s window)
    // Features 32-55: strategy indicator context (requires fresh `ind` for learning samples)
    // 48: Last 5 candle net direction
    {
      let dirSum = 0, dirCnt = 0;
      for (let i = 1; i <= 5; i++) {
        const c = a.rates[curB - BUCKET_SEC*i];
        if (c) { dirSum += (c[3] >= c[0] ? 1 : -1); dirCnt++; }
      }
      add(dirCnt > 0 ? dirSum / dirCnt : 0);
    }
    // 49: Price velocity 5s
    add(p5.length >= 2 ? aiNormalize(p5[p5.length-1] - p5[p5.length-2], Math.max(Math.abs(p5[p5.length-2])*0.001, 1e-9)) : 0);
    // 50: Price velocity 10s
    add(p5.length >= 4 ? aiNormalize(p5[p5.length-1] - p5[p5.length-4], Math.max(Math.abs(p5[p5.length-4])*0.001, 1e-9)) : 0);
    // 51: Price velocity 15s
    add(p15.length >= 2 ? aiNormalize(p15[p15.length-1] - p15[p15.length-2], Math.max(Math.abs(p15[p15.length-2])*0.001, 1e-9)) : 0);
    // 52: Price velocity 30s
    add(p30.length >= 2 ? aiNormalize(p30[p30.length-1] - p30[p30.length-2], Math.max(Math.abs(p30[p30.length-2])*0.001, 1e-9)) : 0);
    // 53: Acceleration — is short-term velocity faster than medium-term?
    {
      const v5 = p5.length >= 2 ? (p5[p5.length-1] - p5[p5.length-2]) : 0;
      const v15 = p15.length >= 2 ? (p15[p15.length-1] - p15[p15.length-2]) : 0;
      add(v5 > 0 && v15 > 0 ? 1 : v5 < 0 && v15 < 0 ? -1 : v5 > v15 ? 0.5 : -0.5);
    }
    // 54-55: Session hour (cyclic encoding)
    { const utcH = new Date().getUTCHours(); add(Math.sin(2*Math.PI*utcH/24)); add(Math.cos(2*Math.PI*utcH/24)); }
    if (ind) {
      add(aiNormalize(ind.runnerBuy||0, 12));
      add(aiNormalize(ind.runnerSell||0, 12));
      add(aiNormalize(ind.revBuy||0, 10));
      add(aiNormalize(ind.revSell||0, 10));
      add(ind.runBuyConf||0);
      add(ind.runSellConf||0);
      add(ind.revBuyConf||0);
      add(ind.revSellConf||0);
      add(ind.strongBullTrend ? 1 : 0);
      add(ind.strongBearTrend ? 1 : 0);
      add(ind.transitionBull ? 1 : 0);
      add(ind.transitionBear ? 1 : 0);
      add(ind.nearResistance ? 1 : 0);
      add(ind.nearSupport ? 1 : 0);
      add(ind.zzBullBias ? 1 : 0);
      add(ind.zzBearBias ? 1 : 0);
      add(aiNormalize((ind.entryPos||0.5)-0.5, 0.5));
      add(ind.regime === 'TRENDING_BULL' ? 1 : ind.regime === 'TRENDING_BEAR' ? -1 : 0);
      add(ind.rsiNeutral ? 1 : 0);
      add((ind.bandExtremeBuy ? 1 : 0) - (ind.bandExtremeSell ? 1 : 0));
      add((ind.directionalBullLock ? 1 : 0) - (ind.directionalBearLock ? 1 : 0));
      add(aiNormalize((ind.confirmBullVotes||0)-(ind.confirmBearVotes||0), 5));
      add(ind.macdAboveZero ? 1 : ind.macdBelowZero ? -1 : 0);
      add(ind.runnerBuyFresh ? 1 : ind.runnerSellFresh ? -1 : ind.reversalBuyFresh ? 0.5 : ind.reversalSellFresh ? -0.5 : 0);
    } else {
      for (let i = 0; i < 24; i++) add(0);
    }
    // Features 56-63: Reversal/Runner detection (v19.0.0)
    // 56: RSI distance from nearest extreme (normalized, -1..1)
    {
      const rsiVal = rsi(p30, 5);
      const distAbove = rsiVal > 70 ? -(rsiVal - 70) / 30 : 0;
      const distBelow = rsiVal < 30 ? (30 - rsiVal) / 30 : 0;
      add(distAbove + distBelow);
    }
    // 57: Upper wick / total range (reversal sell signal when large)
    { const c = a.rates[curB]; add(cWickUp(c)); }
    // 58: Lower wick / total range (reversal buy signal when large)
    { const c = a.rates[curB]; add(cWickLo(c)); }
    // 59: Failed breakout detection (-1=failed bull break, 1=failed bear break, 0=none)
    {
      const c = a.rates[curB], cp = a.rates[prevB];
      if (c && cp && c[2] > 0 && cp[2] > 0) {
        const brokeHigh = c[1] > cp[1] && c[3] < c[0];
        const brokeLow  = c[2] < cp[2] && c[3] > c[0];
        add(brokeHigh ? -1 : brokeLow ? 1 : 0);
      } else { add(0); }
    }
    // 60: EMA spread (ema5 - ema21) normalized — wide spread = strong runner
    {
      const e5 = ema(p30, 5), e21 = ema(p30, 21);
      add(aiNormalize(e5 - e21, Math.max(atr(p30, 7), Math.abs(px) * 0.001, 1e-9)));
    }
    // 61: Momentum acceleration — is 5s velocity increasing relative to 15s ago?
    {
      const vNow  = p5.length >= 2 ? (p5[p5.length-1] - p5[p5.length-2]) : 0;
      const vPrev = p5.length >= 5 ? (p5[p5.length-3] - p5[p5.length-5]) : 0;
      add(vNow > 0 && vPrev > 0 ? 1 : vNow < 0 && vPrev < 0 ? -1 : vNow > vPrev ? 0.5 : vNow < vPrev ? -0.5 : 0);
    }
    // 62: Candle direction streak — last 5 candles same direction?
    {
      let streak = 0;
      for (let i = 0; i < 5; i++) {
        const c = a.rates[curB - BUCKET_SEC * i];
        if (c) streak += (c[3] >= c[0] ? 1 : -1);
      }
      add(Math.max(-1, Math.min(1, streak / 5)));
    }
    // 63: Composite type score (reversal_score - runner_score, normalized to -1..1)
    {
      const rsiVal = rsi(p30, 5);
      let revScore = 0, runScore = 0;
      if (rsiVal > 68) revScore += 25;
      else if (rsiVal > 60) revScore += 15;
      if (rsiVal < 32) revScore += 25;
      else if (rsiVal < 40) revScore += 15;
      const curC = a.rates[curB];
      if (curC) {
        const rng = curC[1]-curC[2];
        if (rng > 0) {
          const uw = (curC[1]-Math.max(curC[0],curC[3]))/rng;
          const lw = (Math.min(curC[0],curC[3])-curC[2])/rng;
          if (uw > 0.6) revScore += 20;
          if (lw > 0.6) revScore += 20;
        }
      }
      const e5 = ema(p30, 5), e9 = ema(p30, 9), e21 = ema(p30, 21);
      if (e5 > e9 && e9 > e21) runScore += 25;
      if (e5 < e9 && e9 < e21) runScore += 25;
      const adxVal = adx(p30, 7);
      if (adxVal > 35) runScore += 20;
      else if (adxVal > 25) runScore += 10;
      const v5 = p5.length >= 2 ? (p5[p5.length-1] - p5[p5.length-2]) / Math.max(Math.abs(p5[p5.length-2])*0.001, 1e-9) : 0;
      const v15 = p15.length >= 2 ? (p15[p15.length-1] - p15[p15.length-2]) / Math.max(Math.abs(p15[p15.length-2])*0.001, 1e-9) : 0;
      if (Math.abs(v5) > Math.abs(v15) && v5 * v15 > 0) runScore += 15;
      add(aiNormalize(revScore - runScore, 50));
    }

    // Features 64-71: MARKET BEHAVIOR MEMORY (v24.1.75)
    // These deliberately describe behavior rather than adding more indicators.
    // 64: volatility regime — recent 30s ATR vs slower 30s ATR.
    {
      const fastAtr=Math.max(atr(p30,5),1e-9), slowAtr=Math.max(atr(p30,14),Math.abs(px)*1e-9,1e-9);
      add(aiNormalize(fastAtr-slowAtr,slowAtr));
    }
    // 65: volatility change — newest 5s absolute movement vs prior 5s movement block.
    {
      const absMoves=[]; for(let i=Math.max(1,p5.length-12);i<p5.length;i++) absMoves.push(Math.abs(p5[i]-p5[i-1]));
      const split=Math.max(1,Math.floor(absMoves.length/2));
      const oldM=absMoves.slice(0,split), newM=absMoves.slice(split);
      const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0;
      const base=Math.max(avg(oldM),Math.abs(px)*1e-9,1e-9); add(aiNormalize(avg(newM)-avg(oldM),base));
    }
    // 66: signed trend persistence — consistency of the last eight 30s moves.
    {
      let sum=0,n=0; for(let i=Math.max(1,p30.length-8);i<p30.length;i++){const d=p30[i]-p30[i-1]; if(d!==0){sum+=d>0?1:-1;n++;}}
      add(n?sum/n:0);
    }
    // 67: signed directional efficiency — net displacement / total path over 10×30s.
    {
      const n=Math.min(10,p30.length-1); if(n<2){add(0);} else {
        const start=p30.length-1-n, net=p30[p30.length-1]-p30[start]; let path=0;
        for(let i=start+1;i<p30.length;i++) path+=Math.abs(p30[i]-p30[i-1]);
        add(path>1e-12?net/path:0);
      }
    }
    // 68: chop persistence — direction-flip density of recent 30s movement.
    {
      const dirs=[]; for(let i=Math.max(1,p30.length-10);i<p30.length;i++){const d=p30[i]-p30[i-1];if(d!==0)dirs.push(d>0?1:-1);}
      let flips=0; for(let i=1;i<dirs.length;i++) if(dirs[i]!==dirs[i-1])flips++;
      const rate=dirs.length>1?flips/(dirs.length-1):0.5; add(rate*2-1);
    }
    // 69: distance traveled over the last three 30s windows, normalized by ATR.
    {
      const n=Math.min(3,p30.length-1), av=Math.max(atr(p30,7),Math.abs(px)*0.001,1e-9);
      add(n>0?aiNormalize(p30[p30.length-1]-p30[p30.length-1-n],av*3):0);
    }
    // 70: broader distance traveled over the last six 30s windows.
    {
      const n=Math.min(6,p30.length-1), av=Math.max(atr(p30,7),Math.abs(px)*0.001,1e-9);
      add(n>0?aiNormalize(p30[p30.length-1]-p30[p30.length-1-n],av*6):0);
    }
    // 71: this exact market's historical UP/DOWN behavior under the same setup family.
    add(aiHistoricalSetupEdge(asset,ind));

    // Features 72-75: Bollinger Band (14,2) measurements. These are AI/context
    // measurements only; they never issue BUY/SELL instructions by themselves.
    {
      const bb = (series) => {
        if (!Array.isArray(series) || series.length < 14) return null;
        const w = series.slice(-14);
        const mid = w.reduce((a,b)=>a+b,0) / w.length;
        const variance = w.reduce((a,b)=>a + (b-mid)*(b-mid),0) / w.length;
        const sd = Math.sqrt(Math.max(0, variance));
        return { mid, upper: mid + 2*sd, lower: mid - 2*sd, width: 4*sd };
      };
      const curBB = bb(p30);
      const prevBB = p30.length >= 15 ? bb(p30.slice(0,-1)) : null;
      const av = Math.max(atr(p30,7), Math.abs(px)*0.001, 1e-9);
      if (curBB && curBB.width > 1e-12) {
        // 72: position inside the band: -1 lower band, 0 midline, +1 upper band.
        add(((px-curBB.lower)/curBB.width - 0.5) * 2);
        // 73: band width relative to ATR(7): larger = more expanded volatility.
        add(aiNormalize(curBB.width, av*4));
        // 74: band-width expansion/contraction vs the prior 30s observation.
        add(prevBB && prevBB.width > 1e-12 ? aiNormalize(curBB.width-prevBB.width, prevBB.width) : 0);
        // 75: signed distance outside the bands in ATR units; 0 while inside.
        const outside = px > curBB.upper ? (px-curBB.upper) : px < curBB.lower ? (px-curBB.lower) : 0;
        add(aiNormalize(outside, av));
      } else { add(0); add(0); add(0); add(0); }
    }

    // Features 76-87: dedicated 15s fast-context stack for the 30s target.
    // These are inputs to the learners, not hard trade instructions.
    {
      const av15=Math.max(atr(p15,7),Math.abs(px)*0.001,1e-9);
      const e5_15=ema(p15,5), e9_15=ema(p15,9), e21_15=ema(p15,21);
      add(aiNormalize(e5_15-e9_15,av15));                                      // 76
      add(aiNormalize(e9_15-e21_15,av15));                                    // 77
      const r15=p15.length>=8?rsi(p15,7):50, rp15=p15.length>=9?rsi(p15.slice(0,-1),7):r15;
      add((r15-50)/50);                                                        // 78
      add(aiNormalize(r15-rp15,10));                                           // 79
      const mf=emaSeries(p15,5), ms=emaSeries(p15,13), mm=[];
      for(let i=0;i<p15.length;i++) if(Number.isFinite(mf[i])&&Number.isFinite(ms[i])) mm.push(mf[i]-ms[i]);
      const mSig=mm.length?ema(mm,6):0, mNow=mm.length?mm.at(-1):0, mPrev=mm.length>1?mm.at(-2):mNow;
      add(aiNormalize(mNow-mSig,av15*0.15));                                    // 80
      add(aiNormalize(mNow-mPrev,av15*0.10));                                  // 81
      const dm15=dmiAdx(p15,7);
      add(aiNormalize(Number(dm15.plusDI||0)-Number(dm15.minusDI||0),30));       // 82
      add(aiNormalize(Number(dm15.adx||0)-20,30));                              // 83
      if(p15.length>=14){
        const w=p15.slice(-14), mid=w.reduce((a,b)=>a+b,0)/w.length;
        const sd=Math.sqrt(w.reduce((a,b)=>a+(b-mid)*(b-mid),0)/w.length);
        const width=4*sd; add(width>1e-12?((px-(mid-2*sd))/width-.5)*2:0);       // 84
        add(aiNormalize(width,av15*4));                                         // 85
      } else { add(0); add(0); }
      const zz15=swingStructureZigZag(p15);
      add(zz15.trend==='TRENDING_BULL'||zz15.trend==='BULLISH'?1:zz15.trend==='TRENDING_BEAR'||zz15.trend==='BEARISH'?-1:0); // 86
      const dir15=(e5_15>e9_15&&e9_15>e21_15?1:e5_15<e9_15&&e9_15<e21_15?-1:0);
      const e5_30=ema(p30,5),e9_30=ema(p30,9),e21_30=ema(p30,21);
      const dir30=(e5_30>e9_30&&e9_30>e21_30?1:e5_30<e9_30&&e9_30<e21_30?-1:0);
      add(dir15&&dir30?(dir15===dir30?dir15:-dir30):0);                          // 87
    }

    // Features 88-103: rolling visual/video memory. These summarize the
    // current chart's last ~30s, ~2m and up to 10m of visual movement.
    // They are learned jointly with market data + indicators by XGB/LGB.
    for(const vf of v219VisualVector(asset)) add(vf);

    return out.slice(0, AI_FEATURES);
  }

  // ================================================================
  //  MARKET QUALITY LISTENER (v17.6.0)
  //  Assesses whether current market conditions favor trading.
  //  Returns { qualityScore, trendStrength, volatility, chopScore, allowTrade, details }
  // ================================================================
  function aiAssessMarketQuality(asset, ind) {
    const a = getAsset(asset);
    const p5  = getLiveTFView(a, '5s').prices;
    const p15 = getLiveTFView(a, '15s').prices;
    const p30 = getLiveTFView(a, '30s').prices;
    if (p30.length < 8) return { qualityScore: 0, allowTrade: false, details: 'WARMING' };

    const px = a.lastPrice || p5[p5.length - 1] || 0;
    if (!px) return { qualityScore: 0, allowTrade: false, details: 'NO_DATA' };

    // 1. TREND STRENGTH: multi-timeframe EMA alignment (0-100)
    let trendScore = 0, trendEvidence = 0, trendLabel = 'NEUTRAL';
    const emaFast = [ema(p5, 3), ema(p5, 5), ema(p5, 9)];
    const emaMed  = [ema(p15, 3), ema(p15, 5), ema(p15, 9), ema(p15, 20)];
    const emaSlow = [ema(p30, 5), ema(p30, 9), ema(p30, 20)];
    // 5s EMA alignment
    if (emaFast[0] > emaFast[1] && emaFast[1] > emaFast[2]) { trendScore += 15; trendEvidence += 15; }
    else if (emaFast[0] < emaFast[1] && emaFast[1] < emaFast[2]) { trendScore += 10; trendEvidence -= 15; }
    // 15s EMA alignment
    if (emaMed[0] > emaMed[1] && emaMed[1] > emaMed[2]) { trendScore += 20; trendEvidence += 20; }
    else if (emaMed[0] < emaMed[1] && emaMed[1] < emaMed[2]) { trendScore += 15; trendEvidence -= 20; }
    // 30s EMA alignment
    if (emaSlow[0] > emaSlow[1] && emaSlow[1] > emaSlow[2]) { trendScore += 25; trendEvidence += 25; }
    else if (emaSlow[0] < emaSlow[1] && emaSlow[1] < emaSlow[2]) { trendScore += 18; trendEvidence -= 25; }
    // Price vs EMAs
    const pVsEma5  = px > emaFast[1] ? 5 : px < emaFast[1] ? -5 : 0;
    const pVsEma20 = px > emaMed[3] ? 10 : px < emaMed[3] ? -10 : 0;
    trendEvidence += pVsEma5 + pVsEma20;
    trendScore += Math.abs(pVsEma5) + Math.abs(pVsEma20);
    if (trendEvidence > 30) trendLabel = 'STRONG_BULL';
    else if (trendEvidence > 10) trendLabel = 'BULLISH';
    else if (trendEvidence < -30) trendLabel = 'STRONG_BEAR';
    else if (trendEvidence < -10) trendLabel = 'BEARISH';

    // 2. VOLATILITY: ATR5 vs ATR20 ratio (0-100, 50=normal)
    const atr5 = atr(p30, 5);
    const atr20 = atr(p30, 20);
    let volScore = 50, volLabel = 'NORMAL';
    if (atr20 > 0) {
      const vr = atr5 / Math.max(atr20, 1e-9);
      if (vr > 2.0)      { volScore = 10; volLabel = 'EXTREME'; }
      else if (vr > 1.5) { volScore = 25; volLabel = 'HIGH'; }
      else if (vr > 1.2) { volScore = 50; volLabel = 'ACTIVE'; }
      else if (vr > 0.8) { volScore = 70; volLabel = 'NORMAL'; }
      else if (vr > 0.5) { volScore = 55; volLabel = 'LOW'; }
      else               { volScore = 30; volLabel = 'DEAD'; }
    }

    // 3. CHOP DETECTION: candle direction alternation (0-100, 100=clean trend)
    let flipCount = 0;
    const lookback = Math.min(20, p30.length - 1);
    if (lookback >= 4) {
      const recent = p30.slice(-lookback);
      for (let i = 1; i < recent.length; i++) {
        if ((recent[i] >= recent[i-1]) !== (recent[i-1] >= (recent[i-2] || recent[i-1]))) flipCount++;
      }
    }
    const chopRaw = lookback >= 4 ? flipCount / (lookback - 1) : 0.5;
    const chopScore = Math.round(100 - chopRaw * 100);
    let chopLabel = 'NEUTRAL';
    if (chopScore > 75) chopLabel = 'TRENDING';
    else if (chopScore > 55) chopLabel = 'MOSTLY_TREND';
    else if (chopScore > 35) chopLabel = 'MIXED';
    else chopLabel = 'CHOPPY';

    // 4. COMBINED QUALITY SCORE (0-100)
    const trendPQ = Math.min(100, Math.max(0, trendScore * 1.2));
    const volPQ   = volScore;
    const chopPQ  = chopScore;
    const qualityScore = Math.round((trendPQ * 0.35) + (volPQ * 0.35) + (chopPQ * 0.30));

    // Smooth with EMA per asset
    if (!aiState.marketQuality[asset]) {
      aiState.marketQuality[asset] = { trendStrength: trendPQ, volatility: volPQ, chopScore: chopPQ, qualityScore, lastUpdate: Date.now() };
    } else {
      const mq = aiState.marketQuality[asset];
      mq.trendStrength = mq.trendStrength * (1 - aiState.MQ_TREND_TAU) + trendPQ * aiState.MQ_TREND_TAU;
      mq.volatility    = mq.volatility * (1 - aiState.MQ_VOL_TAU) + volPQ * aiState.MQ_VOL_TAU;
      mq.chopScore     = mq.chopScore * (1 - aiState.MQ_CHOP_TAU) + chopPQ * aiState.MQ_CHOP_TAU;
      mq.qualityScore  = Math.round((mq.trendStrength * 0.35) + (mq.volatility * 0.35) + (mq.chopScore * 0.30));
      mq.lastUpdate    = Date.now();
      mq.trendLabel    = trendLabel;
      mq.volLabel      = volLabel;
      mq.chopLabel     = chopLabel;
    }

    const mq = aiState.marketQuality[asset];
    return {
      qualityScore: mq.qualityScore,
      trendStrength: mq.trendStrength,
      volatility: mq.volatility,
      chopScore: mq.chopScore,
      allowTrade: mq.qualityScore >= MQ_MIN_QUALITY,
      details: trendLabel + '|' + volLabel + '|' + chopLabel,
      trendLabel, volLabel, chopLabel
    };
  }

  // ================================================================
  //  TRADE OUTCOME MEMORY (v17.6.0)
  //  Records completed trades and builds per-setup statistics.
  //  Called from onTradeResult after each trade completes.
  // ================================================================
  function aiRecordTradeResult(asset, direction, confidence, result, profit, regime, ind) {
    if (!asset || !direction || !result) return;

    // 1. Store full trade record
    const record = {
      asset, direction, confidence,
      result,
      profit: Number(profit) || 0,
      regime: regime || 'UNKNOWN',
      indicators: ind ? {
        regime: ind.regime,
        trendBull: ind.strongBullTrend || false,
        trendBear: ind.strongBearTrend || false
      } : {},
      timestamp: Date.now()
    };
    aiState.tradeMemory.push(record);
    while (aiState.tradeMemory.length > TRADE_MEMORY_MAX) aiState.tradeMemory.shift();

    // 2. Update recent results per asset
    if (!aiState.recentTradeResults[asset]) aiState.recentTradeResults[asset] = [];
    aiState.recentTradeResults[asset].push({ result, direction, confidence, timestamp: Date.now() });
    while (aiState.recentTradeResults[asset].length > RECENT_RESULTS_WINDOW) {
      aiState.recentTradeResults[asset].shift();
    }

    // 3. Update tradeStats: per asset, per direction, per confidence bucket
    if (!aiState.tradeStats[asset]) aiState.tradeStats[asset] = {};
    if (!aiState.tradeStats[asset][direction]) aiState.tradeStats[asset][direction] = {};

    let bucketKey = 'ALL';
    for (let b = 0; b < TM_CONFIDENCE_BUCKETS.length - 1; b++) {
      if (confidence >= TM_CONFIDENCE_BUCKETS[b] && confidence < TM_CONFIDENCE_BUCKETS[b+1]) {
        const lo = Math.round(TM_CONFIDENCE_BUCKETS[b] * 100);
        const hi = Math.round(TM_CONFIDENCE_BUCKETS[b+1] * 100);
        bucketKey = lo + '-' + hi;
        break;
      }
    }

    if (!aiState.tradeStats[asset][direction][bucketKey]) {
      aiState.tradeStats[asset][direction][bucketKey] = { trades: 0, wins: 0, profit: 0 };
    }
    const ts = aiState.tradeStats[asset][direction][bucketKey];
    ts.trades++;
    if (result === 'win') ts.wins++;
    ts.profit += Number(profit) || 0;
    ts.winRate = ts.trades > 0 ? ts.wins / ts.trades : 0;
    ts.avgProfit = ts.trades > 0 ? ts.profit / ts.trades : 0;

    console.log('[AI-MEM] ' + asset + ' ' + direction + ' @' + (confidence*100).toFixed(0) + '% -> ' + result +
      ' | bucket ' + bucketKey + ': ' + ts.wins + '/' + ts.trades + '=' + (ts.winRate*100).toFixed(0) + '%' +
      ' | P&L ' + (ts.profit >= 0 ? '+' : '') + ts.profit.toFixed(2));
  }

  // ================================================================
  //  TRADE MEMORY LOOKUP (v17.6.0)
  //  Returns historical win rate for a given asset/direction/confidence.
  //  Falls back: exact bucket -> direction -> asset -> insufficient data.
  // ================================================================
  function aiCheckTradeMemory(asset, direction, confidence) {
    if (!asset || !direction) return { winRate: 0.5, trades: 0, allowTrade: true, fallbackLevel: 'NO_DATA' };

    const dirStats = aiState.tradeStats[asset] && aiState.tradeStats[asset][direction];
    if (!dirStats) return { winRate: 0.5, trades: 0, allowTrade: true, fallbackLevel: 'NO_DATA' };

    // Find confidence bucket
    let bucketKey = 'ALL';
    for (let b = 0; b < TM_CONFIDENCE_BUCKETS.length - 1; b++) {
      if (confidence >= TM_CONFIDENCE_BUCKETS[b] && confidence < TM_CONFIDENCE_BUCKETS[b+1]) {
        const lo = Math.round(TM_CONFIDENCE_BUCKETS[b] * 100);
        const hi = Math.round(TM_CONFIDENCE_BUCKETS[b+1] * 100);
        bucketKey = lo + '-' + hi;
        break;
      }
    }

    // Level 1: exact asset + direction + confidence bucket
    let bucket = dirStats[bucketKey];
    if (bucket && bucket.trades >= TM_MIN_TRADES) {
      return {
        winRate: bucket.winRate, trades: bucket.trades,
        allowTrade: bucket.winRate >= TM_MIN_WINRATE,
        fallbackLevel: 'EXACT', bucketKey, avgProfit: bucket.avgProfit
      };
    }

    // Level 2: asset + direction (all confidences)
    let dirTotal = { trades: 0, wins: 0 };
    for (const [bk, bs] of Object.entries(dirStats)) {
      if (bk !== 'ALL') { dirTotal.trades += bs.trades; dirTotal.wins += bs.wins; }
    }
    if (dirTotal.trades >= TM_MIN_TRADES) {
      const wr = dirTotal.trades > 0 ? dirTotal.wins / dirTotal.trades : 0;
      return { winRate: wr, trades: dirTotal.trades, allowTrade: wr >= TM_MIN_WINRATE, fallbackLevel: 'DIRECTION', bucketKey };
    }

    // Level 3: asset (all directions)
    let assetTotal = { trades: 0, wins: 0 };
    const assetStats = aiState.tradeStats[asset] || {};
    for (const [dd, ds] of Object.entries(assetStats)) {
      for (const [bk, bs] of Object.entries(ds)) {
        assetTotal.trades += bs.trades; assetTotal.wins += bs.wins;
      }
    }
    if (assetTotal.trades >= TM_MIN_TRADES) {
      const wr = assetTotal.trades > 0 ? assetTotal.wins / assetTotal.trades : 0;
      return { winRate: wr, trades: assetTotal.trades, allowTrade: wr >= TM_MIN_WINRATE, fallbackLevel: 'ASSET', bucketKey };
    }

    // Level 4: not enough data
    return { winRate: 0.5, trades: dirTotal.trades + assetTotal.trades, allowTrade: true, fallbackLevel: 'INSUFFICIENT_DATA' };
  }

  // ================================================================
  //  COSINE SIMILARITY between two normalized vectors (0-1)
  // ================================================================
  function aiCosineSim(a, b) {
    let dot = 0, na = 0, nb = 0;
    const n = Math.min(a.length, b.length);
    for (let i = 0; i < n; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
    const denom = Math.sqrt(na) * Math.sqrt(nb);
    return denom > 1e-9 ? (dot / denom + 1) / 2 : 0.5; // map to 0-1
  }

  // ================================================================
  //  LOSS PATTERN MATCHING (v18.0.0 / v19.0.4 time-decay)
  //  Builds a compact feature vector from indicator context, then
  //  checks similarity against past losses. Returns a confidence
  //  penalty (0 = no match, up to LM_CONFIDENCE_PENALTY for strong match).
  //  v19.0.4: Each stored pattern decays exponentially with age
  //  (half-life LM_HALF_LIFE_MS); older losses carry less weight.
  //  Additionally, if no losses in LM_RECOVERY_MS, penalty fades to 0
  //  even if patterns match — the bot recovers from losing streaks.
  // ================================================================
  function aiCheckLossPattern(asset, direction, ind) {
    if (!aiState.lossMemory.length) return 0;
    const now = Date.now();

    // Recovery factor: if enough time passed since last loss, penalty fades
    const lastLossAt = aiState._lastLossAt || 0;
    const sinceLastLoss = now - lastLossAt;
    const recoveryFactor = lastLossAt > 0
      ? Math.max(0, 1 - sinceLastLoss / LM_RECOVERY_MS)
      : 1.0;
    // recoveryFactor: 1.0 right after loss → 0.0 after LM_RECOVERY_MS
    if (recoveryFactor <= 0) return 0;

    // Build normalized feature vector from current context
    const h = new Date().getUTCHours();
    const curr = [
      ind.strongBullTrend ? 1 : (ind.strongBearTrend ? -1 : 0),
      ind.macdAboveZero ? 1 : (ind.macdBelowZero ? -1 : 0),
      ind.rsiNeutral ? 0 : (ind.rsi && ind.rsi > 70 ? 1 : (ind.rsi && ind.rsi < 30 ? -1 : 0)),
      ind.runnerBuyFresh ? 1 : (ind.runnerSellFresh ? -1 : 0),
      ind.nearResistance ? 1 : 0,
      ind.nearSupport ? -1 : 0,
      ind.zzBullBias ? 1 : (ind.zzBearBias ? -1 : 0),
      Math.sin(2*Math.PI*h/24),
      Math.cos(2*Math.PI*h/24)
    ];
    let bestSim = 0, matches = 0;
    let weightedSimTotal = 0, totalWeight = 0;
    for (const lm of aiState.lossMemory) {
      if (lm.direction !== direction) continue;
      if (lm.asset !== asset) continue;
      const sim = aiCosineSim(curr, lm.vec);
      if (sim > bestSim) bestSim = sim;
      if (sim > LM_SIMILARITY_THRESHOLD) {
        // Time-decay weight: patterns older than half-life count less
        const age = now - (lm.ts || now);
        const decayWeight = Math.pow(0.5, age / LM_HALF_LIFE_MS);
        matches++;
        weightedSimTotal += sim * decayWeight;
        totalWeight += decayWeight;
      }
    }
    // Need at least 3 effective weighted matches (after time decay)
    if (matches < 3 || totalWeight < 1.5) return 0;
    const avgWeightedSim = weightedSimTotal / totalWeight;
    const memorySaturation = aiState.lossMemory.length / LM_MAX_STORED;
    const penaltyScale = memorySaturation > 0.75 ? Math.max(0.30, 1 - memorySaturation * 0.7) : 1.0;
    const penalty = LM_CONFIDENCE_PENALTY * Math.min(1, avgWeightedSim * 1.5) * recoveryFactor * penaltyScale;
    return Math.min(LM_CONFIDENCE_PENALTY, penalty);
  }

  // ================================================================
  //  MARKET RANKING (v18.0.0)
  //  Computes per-market win rates from tradeStats and ranks best/worst.
  // ================================================================
  function aiComputeMarketRanking() {
    const now = Date.now();
    const ranking = {};
    for (const [asset, dirs] of Object.entries(aiState.tradeStats)) {
      let total = 0, wins = 0;
      let recentTotal = 0, recentWins = 0;
      for (const [dir, buckets] of Object.entries(dirs)) {
        for (const [bk, bs] of Object.entries(buckets)) {
          total += bs.trades || 0;
          wins += bs.wins || 0;
        }
      }
      // Recent: check tradeMemory for last 24h
      const recent = (aiState.tradeMemory || []).filter(t =>
        t.asset === asset && (now - t.timestamp) < MRK_WINDOW
      );
      recentTotal = recent.length;
      recentWins = recent.filter(t => t.result === 'win').length;
      ranking[asset] = {
        winRate: total > 0 ? wins / total : 0,
        trades: total,
        recentWinRate: recentTotal > 0 ? recentWins / recentTotal : (total > 0 ? wins / total : 0),
        recentTrades: recentTotal
      };
    }
    // Sort by recent win rate (fall back to all-time)
    const sorted = Object.entries(ranking)
      .filter(([_, r]) => r.trades >= MRK_MIN_TRADES)
      .sort((a, b) => {
        const ra = a[1].recentTrades >= 5 ? a[1].recentWinRate : a[1].winRate;
        const rb = b[1].recentTrades >= 5 ? b[1].recentWinRate : b[1].winRate;
        return rb - ra;
      });
    for (let i = 0; i < sorted.length; i++) {
      const [asset, r] = sorted[i];
      r.rank = i + 1;
      r.recommendation = r.winRate >= 0.55 ? 'PREFER' : r.winRate < MRK_AVOID_WINRATE ? 'AVOID' : 'NEUTRAL';
    }
    aiState.marketRanking = ranking;
    return { ranking, sorted };
  }

  // ================================================================
  //  TIME-OF-DAY FACTOR (v18.0.0)
  //  Returns a multiplier (0.5-1.5) based on historical win rate
  //  for this asset × hour-of-day combination.
  // ================================================================
  function aiTimeOfDayFactor(asset) {
    const ms = aiState.marketStats[asset];
    if (!ms || !ms._hours) return 1.0;
    const h = new Date().getUTCHours();
    const bucket = ms._hours[h];
    if (!bucket || bucket.total < TOD_MIN_SAMPLES) return 1.0;
    const wr = bucket.correct / bucket.total;
    // Map win rate to multiplier: 40%→0.55, 50%→1.0, 60%→1.3, 70%→1.5
    return Math.max(TOD_FLOOR, Math.min(1.5, 1.0 + (wr - 0.5) * 2.5));
  }

  // ================================================================
  //  TRADE QUALITY SCORE (v18.0.0)
  //  Aggregates AI confidence, indicator alignment, market context,
  //  candle structure, and historical win rate into a 0-100 score.
  //  90-100: strong setup → allow
  //  75-90:  marginal   → require extra confidence
  //  <75:    skip
  // ================================================================
  function aiTradeQualityScore(asset, direction, px, ind, aiConf, memResult, mq) {
    if (!ind) return 50; // no indicator context → neutral
    let score = 0;
    const a = getAsset(asset);

    // 1. AI confidence (0-25 pts): higher conviction = higher quality
    score += Math.min(25, aiConf * 25);

    // 2. EMA/trend alignment (0-15 pts)
    if (direction === 'BUY') {
      if (ind.strongBullTrend) score += 15;
      else if (ind.transitionBull) score += 10;
      else if (!ind.strongBearTrend) score += 5;
    } else {
      if (ind.strongBearTrend) score += 15;
      else if (ind.transitionBear) score += 10;
      else if (!ind.strongBullTrend) score += 5;
    }

    // 3. MACD agreement (0-10 pts)
    if (direction === 'BUY' && ind.macdAboveZero) score += 10;
    else if (direction === 'SELL' && ind.macdBelowZero) score += 10;
    else if (!ind.macdAboveZero && !ind.macdBelowZero) score += 5;

    // 4. RSI positioning (0-10 pts) — neutral RSI gives room to run
    if (ind.rsiNeutral) score += 10;
    else score += 4;

    // 5. Candle quality (0-15 pts) — using most recent 5s bucket
    const now = a.lastTickSec || Math.floor(Date.now()/1000);
    const curB = BUCKET_SEC * Math.floor(now / BUCKET_SEC);
    const c = a.rates[curB];
    if (c) {
      const rng = c[1] - c[2];
      if (rng > 0) {
        const body = Math.abs(c[3] - c[0]);
        const bodyPct = body / rng;
        const wickUp = (c[1] - Math.max(c[0],c[3])) / rng;
        const wickLo = (Math.min(c[0],c[3]) - c[2]) / rng;
        const bullish = c[3] >= c[0];
        if (direction === 'BUY') {
          if (wickUp < 0.3 && bodyPct > 0.4 && bullish) score += 15;
          else if (wickUp < 0.5 && bodyPct > 0.25) score += 8;
          else if (wickUp < 0.7) score += 4;
        } else {
          if (wickLo < 0.3 && bodyPct > 0.4 && !bullish) score += 15;
          else if (wickLo < 0.5 && bodyPct > 0.25) score += 8;
          else if (wickLo < 0.7) score += 4;
        }
      }
    }

    // 6. Market quality (0-15 pts)
    score += (mq.qualityScore / 100) * 15;

    // 7. Historical win rate for this setup (0-10 pts)
    score += Math.min(10, memResult.winRate * 10);

    return Math.round(Math.min(100, Math.max(0, score)));
  }


  // ── Trade Type Classifier (v19.0.0) ────────────────────────────
  // Classifies the current market setup as REVERSAL, RUNNER, or SKIP
  // based on indicator context (RSI extremes, wick structure, EMA spread,
  // ADX strength, velocity acceleration, failed breakouts).
  // Each trade type gets different confidence thresholds in the gate.
  function aiClassifyTradeType(ind) {
    if (!ind) return { type: 'SKIP', reversalScore: 0, runnerScore: 0 };
    let revScore = 0, runScore = 0;

    // ── Reversal Score (0-100) ──
    // High RSI extremes = strong reversal potential
    const rsi30 = ind.rsi30 !== undefined ? ind.rsi30 : 50;
    if (rsi30 > 68) revScore += 25;
    else if (rsi30 > 60) revScore += 15;
    else if (rsi30 > 55) revScore += 8;
    if (rsi30 < 32) revScore += 25;
    else if (rsi30 < 40) revScore += 15;
    else if (rsi30 < 45) revScore += 8;

    // Wick rejection: large wicks signal price rejection at extremes
    if (ind.wickUp !== undefined && ind.wickUp > 0.6) revScore += 20;
    else if (ind.wickUp > 0.4) revScore += 10;
    if (ind.wickLo !== undefined && ind.wickLo > 0.6) revScore += 20;
    else if (ind.wickLo > 0.4) revScore += 10;

    // Failed breakout: price broke structure but reversed
    if (ind.failedBreakout) {
      revScore += 25;
    }

    // Stretched from EMA: reversion tendency when price is far from moving average
    if (ind.emaDeviation !== undefined) {
      const absDev = Math.abs(ind.emaDeviation);
      if (absDev > 2.5) revScore += 15;
      else if (absDev > 1.5) revScore += 10;
    }

    // ── Runner Score (0-100) ──
    // EMA fan-out: aligned ribbons = momentum regime
    if (ind.emaSpread !== undefined && ind.emaSpread > 1.0) runScore += 25;
    else if (ind.emaSpread !== undefined && ind.emaSpread > 0.5) runScore += 15;

    // ADX strength: high ADX = trending market great for runners
    const adx = ind.adx !== undefined ? ind.adx : 20;
    if (adx > 35) runScore += 20;
    else if (adx > 25) runScore += 12;
    else if (adx > 20) runScore += 6;

    // Momentum acceleration: velocity increasing in trade direction
    if (ind.momentumAccel !== undefined && ind.momentumAccel > 0.5) runScore += 20;
    else if (ind.momentumAccel > 0) runScore += 10;

    // Candle streak: consecutive candles in same direction
    if (ind.candleStreak !== undefined) {
      const absStreak = Math.abs(ind.candleStreak);
      if (absStreak > 3) runScore += 20;
      else if (absStreak > 1) runScore += 10;
    }

    // ── Classification ──
    let type = 'SKIP';
    if (revScore > runScore + TT_REVERSAL_MARGIN && revScore >= 30) type = 'REVERSAL';
    else if (runScore > revScore + TT_RUNNER_MARGIN && runScore >= 30) type = 'RUNNER';

    return { type, reversalScore: revScore, runnerScore: runScore };
  }



  // ═══════════════════════════════════════════════════════════════
  // V20.1 AI DECISION CONTROLLER
  // One owner chooses BUY / SELL / WAIT after regime classification.
  // Existing strategy output remains a feature source, not the final owner.
  // ═══════════════════════════════════════════════════════════════
  const AI_CTRL = {
    minSamples: 750,
    minValidation: 250,
    minEdge: 0.025,
    minConfidence: 0.64,
    reversalConfidence: 0.60,
    runnerConfidence: 0.66,
    maxChop: 0.62,
    disagreementPenalty: 0.12,
    recent: {},
    stats: { decisions:0, buy:0, sell:0, wait:0, overrides:0, assisted:0 }
  };

  function aiCtrlClamp(v, lo=0, hi=1) { return Math.max(lo, Math.min(hi, Number(v)||0)); }
  function aiCtrlSignedDir(dir) { return String(dir||'').toUpperCase()==='BUY' ? 1 : -1; }

  function aiCtrlRegime(ind) {
    const adx = Number(ind?.adx ?? 20);
    const spread = Math.abs(Number(ind?.emaSpread ?? 0));
    const accel = Math.abs(Number(ind?.momentumAccel ?? 0));
    const rsi = Number(ind?.rsi30 ?? ind?.rsi ?? 50);
    const dev = Math.abs(Number(ind?.emaDeviation ?? 0));
    const wick = Math.max(Number(ind?.wickUp ?? 0), Number(ind?.wickLo ?? 0));
    const trend = aiCtrlClamp((adx-16)/28)*0.42 + aiCtrlClamp(spread/1.4)*0.30 + aiCtrlClamp(accel/1.2)*0.28;
    const reversal = Math.max(aiCtrlClamp((Math.abs(rsi-50)-12)/28), aiCtrlClamp((dev-1.0)/2.5), aiCtrlClamp((wick-0.35)/0.65));
    const chop = aiCtrlClamp(1 - trend*0.85) * (0.55 + 0.45*aiCtrlClamp(1-Math.abs(rsi-50)/20));
    if (reversal > trend + 0.12 && reversal > 0.45) return { name: rsi >= 50 ? 'REVERSAL_DOWN' : 'REVERSAL_UP', trend, reversal, chop };
    if (chop > 0.62 && trend < 0.45) return { name:'CHOP', trend, reversal, chop };
    if (trend >= 0.48) return { name:'TREND', trend, reversal, chop };
    return { name:'MIXED', trend, reversal, chop };
  }

  function aiCtrlCandidate(asset, price, ind, strategySig) {
    const raw = aiPredict(asset, price);
    const type = aiClassifyTradeType(ind || {});
    const regime = aiCtrlRegime(ind || {});
    const stratDir = normalizeTradeDirection(strategySig?.dir);
    const modelDir = raw.direction;
    const modelConf = raw.confidence;
    const mq = aiAssessMarketQuality(asset, ind || {});
    const direction = modelDir || stratDir;
    if (!direction) return { action:'WAIT', reason:'AI no direction', raw, type, regime, mq };

    const mem = aiCheckTradeMemory(asset, direction, raw.up);
    const dirAgree = stratDir && modelDir ? stratDir === modelDir : true;
    let quality = 0.42*modelConf + 0.22*(mq.qualityScore/100) + 0.16*regime.trend + 0.12*mem.winRate + 0.08*(dirAgree?1:0);
    if (type.type === 'REVERSAL') quality += 0.08*regime.reversal;
    if (type.type === 'RUNNER') quality += 0.08*regime.trend;
    if (!dirAgree) quality -= AI_CTRL.disagreementPenalty;
    if (regime.name === 'CHOP') quality -= 0.25*regime.chop;
    quality = aiCtrlClamp(quality);

    let threshold = type.type === 'REVERSAL' ? AI_CTRL.reversalConfidence :
                    type.type === 'RUNNER' ? AI_CTRL.runnerConfidence : AI_CTRL.minConfidence;
    const validated = aiState.trained >= AI_CTRL.minSamples && aiState.valTotal >= AI_CTRL.minValidation &&
      (aiState.valCorrect / Math.max(1, aiState.valTotal)) >= 0.50 + AI_CTRL.minEdge;
    const autonomousRequested = botConfig?.aiAutonomous === true || botConfig?.aiMode === 'autonomous';
    const autonomous = autonomousRequested && validated && kaosAiExecutionAllowed;

    let action='WAIT', reason='AI abstain';
    if (regime.chop > AI_CTRL.maxChop && type.type === 'SKIP') reason='AI CHOP';
    else if (mq.allowTrade === false && !autonomous) reason='AI market-quality veto';
    else if (modelConf < AI_ABSTAIN_ZONE) reason='AI low confidence';
    else if (quality < threshold) reason=`AI quality ${Math.round(quality*100)} < ${Math.round(threshold*100)}`;
    else if (!mem.allowTrade && aiState.valTotal >= AI_CTRL.minValidation) reason='AI loss-memory veto';
    else if (!dirAgree && modelConf < 0.80) reason='AI/strategy disagreement';
    else { action=direction; reason = autonomous ? `AI autonomous ${type.type||'GENERIC'}` : `AI assisted ${type.type||'GENERIC'}`; }

    AI_CTRL.stats.decisions++;
    if (action==='BUY') AI_CTRL.stats.buy++; else if (action==='SELL') AI_CTRL.stats.sell++; else AI_CTRL.stats.wait++;
    return { action, reason, quality, threshold, autonomous, validated, raw, type, regime, mq, mem, strategyDir:stratDir, modelDir };
  }

  function aiCtrlApply(asset, price, ind, strategySig) {
    const d = aiCtrlCandidate(asset, price, ind, strategySig);
    lastIndicators.aiController = {
      action:d.action, reason:d.reason, quality:Math.round((d.quality||0)*100),
      regime:d.regime?.name, type:d.type?.type, autonomous:!!d.autonomous,
      validated:!!d.validated, modelDirection:d.modelDir, strategyDirection:d.strategyDir
    };
    // Without server-granted AI execution (Free, Pro, or Ultimate before validation) the AI is
    // advisory only: it must not place, veto or override the strategy's trade.
    if (!kaosAiExecutionAllowed || AI_LAB.model?.researchOnly===true) {
      lastIndicators.aiController.advisoryOnly = true;
      return { sig:Object.assign({}, strategySig, { aiAdvisory:d }), aiDecision:d, advisoryOnly:true };
    }
    if (d.action === 'WAIT') return { skip:true, reason:d.reason, aiDecision:d };
    const out = Object.assign({}, strategySig);
    if (d.autonomous) {
      if (normalizeTradeDirection(out.dir) !== d.action) AI_CTRL.stats.overrides++;
      out.dir = d.action;
      out.tradeType = d.type?.type === 'SKIP' ? 'AI' : d.type.type;
      out.mode = 'ai-autonomous';
      out.reason = `${d.reason} · Q${Math.round(d.quality*100)}`;
    } else {
      // Assisted mode still requires the strategy direction to agree. The AI is a gate,
      // so an immature model cannot silently take over execution.
      if (normalizeTradeDirection(out.dir) !== d.action) return { skip:true, reason:'AI assisted disagreement', aiDecision:d };
      AI_CTRL.stats.assisted++;
      out.tradeType = out.tradeType || d.type?.type || 'AI_ASSISTED';
      out.aiDecision = d;
    }
    out.aiDecision = d;
    return { sig:out, aiDecision:d };
  }

  function aiPredict(asset, price) {
    const x = aiFeatures(asset, price);
    if (!x) return { up:0.5, down:0.5, direction:null, confidence:0, warm:false, samples:aiState.trained };
    const fwd = aiForward(x);
    const p = fwd.prob;
    const direction = p >= 0.5 ? 'BUY' : 'SELL';
    const confidence = Math.abs(p - 0.5) * 2;
    const pred = { up:p, down:1-p, direction, confidence, warm:aiState.trained >= AI_MIN_TRAINED, samples:aiState.trained, x };
    aiState.lastPrediction = pred; aiState.lastAt = Date.now();
    return pred;
  }

  // V24.1.15: AI/XGB learning must respect the same market warmup used by
  // the indicator engine. Training from an imported historical dataset does
  // NOT use this gate; this gate only prevents new live/paper samples from
  // being created before the current asset has enough 5s + indicator-TF data.
  function aiMarketWarmupReady(asset) {
    try {
      const a = getAsset(asset);
      if (!a || !Array.isArray(a.prices)) return false;
      const expiry = parseInt(botConfig?.timeframe || 30, 10);
      const tfKey = expiryToTF(expiry);
      const tf = getTF(a, tfKey);
      // AI collection uses the same practical warmup as the strategy engine:
      // 40 closed 5s candles plus 8 primary/secondary TF candles.  Requiring
      // 25 primary-TF candles here delayed 30s AI collection by ~12.5 minutes
      // and made a fresh session look like the AI was dead.
      const tfSlowKey = expiryToSecondaryTF(expiry);
      const tfSlow = getTF(a, tfSlowKey);
      const storageReady = a.prices.length >= 40;
      const tfReady = !!tf && Array.isArray(tf.prices) && tf.prices.length >= 8;
      const slowReady = !!tfSlow && Array.isArray(tfSlow.prices) && tfSlow.prices.length >= 8;
      return storageReady && tfReady && slowReady;
    } catch (_) { return false; }
  }

  function aiQueueSample(asset, price, source='paper', ind, tradeId=null, meta=null) {
    const px = Number(price);
    if (!aiMarketWarmupReady(asset)) {
      aiState._warmupRejected = (aiState._warmupRejected || 0) + 1;
      return false;
    }
    const x = aiFeatures(asset, px, ind);
    if (!x || !isFinite(px) || px <= 0) return false;
    const nonZero = x.reduce((c, v) => c + (Math.abs(v) > 1e-9 ? 1 : 0), 0);
    if (nonZero < 14) {
      aiState._rejected = (aiState._rejected || 0) + 1;
      if (aiState._rejected === 1 || aiState._rejected % 100 === 0) {
        console.debug(`[AI] Rejected ${aiState._rejected} low-quality samples so far (nonZero=${nonZero}/${AI_FEATURES} for ${asset}). Waiting for higher-TF candles to accumulate.`);
      }
      return false;
    }
    const a = getAsset(asset);
    const aiLabPrediction = aiLabScore(x, asset);
    const xgbP0 = Number(aiLabPrediction?.xgboost);
    const p = Number.isFinite(xgbP0) ? xgbP0 : 0.5;
    const regime = ind ? (ind.regime || 'UNKNOWN') : 'UNKNOWN';
    // V24.1.112: ONE canonical observation per asset per 60s target candle.
    // setup/paper/trade are metadata sources, not separate independent rows.
    const nowTs=Date.now();
    const candleTs = Math.floor(nowTs / AI_INDEPENDENT_CANDLE_MS) * AI_INDEPENDENT_CANDLE_MS;
    aiState.canonicalSampleCandle = aiState.canonicalSampleCandle || {};
    const canonicalKey=`${asset}:${candleTs}`;
    const existing=aiState.samples.find(q=>q && q.canonicalKey===canonicalKey);
    if(existing){
      existing.sources=Array.from(new Set([...(existing.sources||[existing.source]),source]));
      if(source==='setup'){
        existing.policyId=AI_POLICY_ID; existing.policyParent=AI_POLICY_PARENT; existing.policySchema=AI_POLICY_SCHEMA;
        existing.source='setup'; existing.qualifiedSetup=true;
        existing.tradeType=meta?.tradeType||meta?.setupType||existing.tradeType;
        existing.setupDir=meta?.setupDir||existing.setupDir;
        existing.setupScore=Number.isFinite(Number(meta?.setupScore))?Number(meta.setupScore):existing.setupScore;
        existing.setupConfidence=Number.isFinite(Number(meta?.setupConfidence))?Number(meta.setupConfidence):existing.setupConfidence;
        existing.marketClass=meta?.marketClass||existing.marketClass||null;
        existing.targetKind=meta?.targetKind||existing.targetKind||null;
        existing.sourceCandleDir=meta?.sourceCandleDir||existing.sourceCandleDir||null;
        existing.classifierDecision=meta?.classifierDecision||existing.classifierDecision||null;
        existing.continueScore=Number.isFinite(Number(meta?.continueScore))?Number(meta.continueScore):existing.continueScore;
        existing.reversalScore=Number.isFinite(Number(meta?.reversalScore))?Number(meta.reversalScore):existing.reversalScore;
        existing.runLength=Number.isFinite(Number(meta?.runLength))?Number(meta.runLength):existing.runLength;
        existing.setupKey=aiSetupKey(ind,meta)||existing.setupKey;
      }
      if(source==='trade' && tradeId!=null) { existing.policyId=AI_POLICY_ID; existing.policyParent=AI_POLICY_PARENT; existing.policySchema=AI_POLICY_SCHEMA; }
      if(source==='trade' && tradeId!=null) existing.tradeIds=Array.from(new Set([...(existing.tradeIds||[]),String(tradeId)]));
      aiLog('AI_SAMPLE_MERGED',{asset,source,canonicalKey,sources:existing.sources},false);
      return true;
    }
    aiState.canonicalSampleCandle[asset]=candleTs;
    const isIndependent = true;

    const sampleDue = nowTs + AI_HORIZON_MS;
    const sampleObj = {
      policyId:AI_POLICY_ID, policyParent:AI_POLICY_PARENT, policySchema:AI_POLICY_SCHEMA,
      asset, t:nowTs, candleTs, canonicalKey, due:sampleDue, price:px, x,
      predicted:p >= 0.5 ? 1 : 0, predictedUp:p, source, sources:[source], regime,
      abstained: Math.abs(p - 0.5) < AI_ABSTAIN_ZONE,
      tickSec: a ? a.lastTickSec : undefined,
      independent: isIndependent,
      tradeId: (source === 'trade') ? tradeId : null,
      tradeType: meta?.tradeType || meta?.setupType || null,
      setupDir: meta?.setupDir || null,
      setupScore: Number.isFinite(Number(meta?.setupScore)) ? Number(meta.setupScore) : null,
      setupConfidence: Number.isFinite(Number(meta?.setupConfidence)) ? Number(meta.setupConfidence) : null,
      marketClass: meta?.marketClass || null,
      qualifiedSetup: source === 'setup',
      targetKind: meta?.targetKind || null,
      sourceCandleDir: meta?.sourceCandleDir || null,
      classifierDecision: meta?.classifierDecision || null,
      continueScore: Number.isFinite(Number(meta?.continueScore)) ? Number(meta.continueScore) : null,
      reversalScore: Number.isFinite(Number(meta?.reversalScore)) ? Number(meta.reversalScore) : null,
      runLength: Number.isFinite(Number(meta?.runLength)) ? Number(meta.runLength) : null,
      setupKey: aiSetupKey(ind, meta)
    };
    try { globalThis.KaosExpiryCollector?.snapshot(asset,px,x,nowTs,meta?.marketClass || meta?.tradeType || lastIndicators?.cleanCore?.marketClass); } catch (_) {}
    sampleObj.aiLabPrediction = aiLabPrediction;
    sampleObj.snapshotId = `${asset}:${sampleObj.t}:${Math.round(px*1e8)}`;
    const xgbP = Number(aiLabPrediction?.xgboost);
    // XGB-only mode: no secondary learner sample is queued.
    aiState.samples.push(sampleObj);
    aiLog('AI_SAMPLE_QUEUED', {asset,source,independent:isIndependent,snapshotId:sampleObj.snapshotId,predicted:sampleObj.predicted,predictedUp:p,xgbUp:Number.isFinite(xgbP)?xgbP:null,xgbOnly:true,queued:aiState.samples.length,paperQueued:aiState.paperQueued+1}, false);

    // V24.1.112: trade outcomes remain trade analytics only; XGB labels always use the same 60s future-market target.

    aiState.paperQueued += source === 'paper' ? 1 : 0;
    if (aiState.samples.length > AI_MAX_SAMPLES) aiState.samples.splice(0, aiState.samples.length-AI_MAX_SAMPLES);
    return true;
  }

  function aiTrainOne(x, label, lrMult) {
    lrMult = Number.isFinite(lrMult) ? lrMult : 1;
    if (!Array.isArray(x) || x.length !== AI_FEATURES) throw new Error('invalid feature vector');
    // Direction model target: 1 = UP/BUY direction, 0 = DOWN/SELL direction.
    // Never use JS truthiness here: values such as 0.02 and 0.48 are both truthy
    // and previously collapsed almost every continuous label into class 1.
    label = Number(label);
    if (!Number.isFinite(label)) throw new Error('invalid label');
    label = label >= 0.5 ? 1 : 0;
    const fwd = aiForward(x);
    const err = label - fwd.prob;
    const lr = (AI_LEARNING_RATE / (1 + aiState.trained / 5000)) * lrMult;

    // Keep a snapshot of output weights. Hidden gradients must use the weights
    // from the same forward pass, not weights already changed earlier in this step.
    const w2Before = aiState.w2.slice();
    const dOut = err * fwd.prob * (1 - fwd.prob);

    for (let j = 0; j < AI_HIDDEN; j++) {
      const grad = dOut * fwd.hidden[j] - AI_L2 * aiState.w2[j];
      aiState.vw2[j] = AI_MOMENTUM * aiState.vw2[j] + lr * grad;
      aiState.w2[j] += aiState.vw2[j];
    }
    aiState.vb2 = AI_MOMENTUM * aiState.vb2 + lr * dOut;
    aiState.b2 += aiState.vb2;

    for (let j = 0; j < AI_HIDDEN; j++) {
      const reluGrad = fwd.hidden[j] > 0 ? 1 : 0.01;
      const dHidden = reluGrad * dOut * w2Before[j];
      const base = j * AI_FEATURES;
      for (let i = 0; i < AI_FEATURES; i++) {
        const grad = dHidden * (Number(x[i]) || 0) - AI_L2 * aiState.w1[base + i];
        aiState.vw1[base + i] = AI_MOMENTUM * aiState.vw1[base + i] + lr * grad;
        aiState.w1[base + i] += aiState.vw1[base + i];
      }
      aiState.vb1[j] = AI_MOMENTUM * aiState.vb1[j] + lr * dHidden;
      aiState.b1[j] += aiState.vb1[j];
    }
    return fwd.prob;
  }

  function aiSetStatus(p) {
    lastIndicators.aiPrediction = {
      up: p.up, down: p.down, direction:p.direction,
      confidence:p.confidence, trained:p.samples, warm:p.warm
    };
    lastIndicators.aiLearning = {
      mode: AI_LEARNING_MODE ? 'PAPER_LEARNING' : 'OFF',
      queued: aiState.paperQueued, labeled: aiState.paperLabeled,
      accuracy: aiState.paperLabeled ? aiState.paperCorrect / aiState.paperLabeled : null
    };
  }

  function aiFlush() {
    flushDecisionHistory();
    const now = Date.now();
    const keep=[];
    for (const s of aiState.samples) {
      if (s.due > now) { keep.push(s); continue; }
      const a=getAsset(s.asset);
      if (!a) { keep.push(s); continue; }
      const future=Number(a.lastPrice||0);
      if (!future || !s.price) { keep.push(s); continue; }
      if (s.tickSec !== undefined && a.lastTickSec <= s.tickSec) { keep.push(s); continue; }

      // ── MIN_MOVE filter: skip samples where price barely moved ──
      const changePct = (future - s.price) / Math.max(s.price, 1e-9);
      if (Math.abs(changePct) < AI_MIN_MOVE) { keep.push(s); continue; }

      // ── Direction labeling ──
      // The network output is interpreted as probability of UP. Therefore every
      // training label must also mean UP=1 / DOWN=0. The previous code sometimes
      // trained the network on "was my previous prediction correct?", which makes
      // SELL+win train toward UP and corrupts the target.
      // V24.1.112 canonical target: every source learns the same future market direction.
      // Never substitute trade P&L as a second label for the same 30s candle.
      const dirUp = future > s.price;
      const label = dirUp ? 1 : 0;
      const isCorrect = (s.predicted === label);

      // XGB-only mode: Pattern AI training disabled.

      // ── v21: neutral/no-move abstentions are NOT direction labels. ──
      // A binary UP/DOWN classifier cannot learn a neutral 0.5 target via a hard
      // threshold. Count the abstention diagnostically and skip validation/training.
      if (s.source === 'paper' && s.abstained && Math.abs(changePct) < DNR_MAX_MOVE) {
        s._dnr = true;
        aiState.correctAbstains = (aiState.correctAbstains || 0) + 1;
        continue;
      }

      // (dirUp and isCorrect already computed above — skipped)
      // V24.1.73 XGB-only: V23 agreement audit and V23 training disabled.
      if (isCorrect) aiState.correct++;
      aiState.total++;
      if (s.source === 'paper') {
        aiState.paperLabeled++;
        if (isCorrect) aiState.paperCorrect++;
      }

      // ── Walk-forward validation (BEFORE training on this sample) ──
      // Only independent paper forecasts (one per 60s horizon) enter validation.
      // Overlapping 5s forecasts shared the same future move and artificially
      // amplified noise and made the displayed validation unstable.
      const validationEligible = !!s.independent;
      if (validationEligible) {
        aiState.valWindow.push({ correct: isCorrect });
        if (isCorrect) aiState.valCorrect++;
        while (aiState.valWindow.length > AI_VAL_WINDOW) {
          const old = aiState.valWindow.shift();
          if (old && old.correct) aiState.valCorrect--;
        }
        aiState.valTotal = aiState.valWindow.length;
        aiState.valAccuracy = aiState.valTotal ? aiState.valCorrect / aiState.valTotal : 0;
        const recentSlice = aiState.valWindow.slice(-100);
        const recentCorrect = recentSlice.filter(v => v.correct).length;
        aiState.valRecent = recentSlice.length ? recentCorrect / recentSlice.length : 0;
      }
      if (s.independent) aiState.independentSamples++;

      // ── Per-regime accuracy tracking ──
      const rKey = s.regime || 'UNKNOWN';
      if (!aiState.regimeStats[rKey]) aiState.regimeStats[rKey] = { correct: 0, total: 0 };
      aiState.regimeStats[rKey].total++;
      if (isCorrect) aiState.regimeStats[rKey].correct++;

      // ── v24.1.80 INDICATOR PAPER VALIDATION ──
      // Score the setup engine against the actual 60s future direction independently
      // of any XGB/LGB prediction. This lets us prove entry logic before training AI.
      if (s.source === 'setup' && (s.setupDir === 'BUY' || s.setupDir === 'SELL')) {
        const ps = aiState.paperSetupStats || (aiState.paperSetupStats={total:0,wins:0,losses:0,draws:0,bySetup:{},byDir:{BUY:{total:0,wins:0,losses:0},SELL:{total:0,wins:0,losses:0}},recent:[]});
        const setupName = String(s.tradeType || 'SETUP');
        const setupWin = (s.setupDir === 'BUY' && label === 1) || (s.setupDir === 'SELL' && label === 0);
        ps.total++;
        if (setupWin) ps.wins++; else ps.losses++;
        if (!ps.bySetup[setupName]) ps.bySetup[setupName]={total:0,wins:0,losses:0};
        ps.bySetup[setupName].total++;
        if (setupWin) ps.bySetup[setupName].wins++; else ps.bySetup[setupName].losses++;
        const d=ps.byDir[s.setupDir] || (ps.byDir[s.setupDir]={total:0,wins:0,losses:0});
        d.total++; if(setupWin)d.wins++; else d.losses++;
        const setupMarketClass=String(s.marketClass||s.regime||'UNKNOWN');
        ps.recent.push({t:s.t,asset:s.asset,setup:setupName,dir:s.setupDir,marketClass:setupMarketClass,regime:s.regime||'UNKNOWN',win:setupWin,label,score:s.setupScore,confidence:s.setupConfidence,changePct});
        if(ps.recent.length>400) ps.recent.splice(0,ps.recent.length-400);
        v118RecordSetupEdge(s.asset,setupMarketClass,setupName,s.setupDir,setupWin,s.t);
        aiLog('PAPER_SETUP_RESOLVED',{asset:s.asset,setup:setupName,dir:s.setupDir,win:setupWin,label,score:s.setupScore,changePct,paperWins:ps.wins,paperLosses:ps.losses},false);
      }

      // ── Per-trade-type accuracy tracking (v19.0.0) ──
      const tt = s.tradeType || 'UNKNOWN';
      if (tt !== 'UNKNOWN' && tt !== 'SKIP') {
        if (!aiState.tradeTypeStats[tt]) aiState.tradeTypeStats[tt] = { correct: 0, total: 0 };
        aiState.tradeTypeStats[tt].total++;
        if (isCorrect) aiState.tradeTypeStats[tt].correct++;
      }

      // ── Per-market (per-asset) accuracy tracking ──
      const mkt = s.asset || 'UNKNOWN';
      if (!aiState.marketStats[mkt]) aiState.marketStats[mkt] = { correct: 0, total: 0, _hours: {} };
      if (!aiState.marketStats[mkt]._hours) aiState.marketStats[mkt]._hours = {};
      aiState.marketStats[mkt].total++;
      if (isCorrect) aiState.marketStats[mkt].correct++;
      const h = new Date(s.t).getUTCHours();
      if (!aiState.marketStats[mkt]._hours[h]) aiState.marketStats[mkt]._hours[h] = { correct:0, total:0 };
      aiState.marketStats[mkt]._hours[h].total++;
      if (isCorrect) aiState.marketStats[mkt]._hours[h].correct++;

      // ── Calibration update ──
      const predConf = Math.abs(s.predictedUp - 0.5) * 2;
      aiState.confEma = aiState.confEma * (1 - aiState.calibAlpha) + predConf * aiState.calibAlpha;
      aiState.confEma = Math.max(aiState.confEma, 0.05);
      aiState.accEma = aiState.accEma * (1 - aiState.calibAlpha) + (isCorrect ? 1 : 0) * aiState.calibAlpha;

      // ── Amplified feedback ──
      let lrMult = 1.0;
      if (s.source === 'trade') {
        // Trade labels are now real P&L outcomes — much higher signal quality.
        // Correct trades get massive positive reinforcement; wrong trades get
        // strong negative gradient to correct the error.
        lrMult = isCorrect ? 4.0 : 3.0;  // real-money feedback dominates learning
      } else if (isCorrect && !s._dnr) {
        lrMult = 1.2;  // mild reinforcement for correct paper predictions
      }

      // ── Do-Nothing Reward lrMult: DNR samples already handled above (lrMult stays 1.0) ──

      // ── Regime-adaptive learning rate ──
      if (s.regime === 'TRENDING_BULL' || s.regime === 'TRENDING_BEAR') {
        lrMult *= 1.3;
      } else if (s.regime === 'RANGING' || s.regime === 'CHOPPY') {
        lrMult *= 0.7;
      }

      // ── Magnitude-based label quality (v18.0.0) ──
      const absPct = Math.abs(changePct);
      let labelQuality;
      if (absPct >= LABEL_STRONG) labelQuality = isCorrect ? 'STRONG_WIN' : 'BAD_LOSS';
      else if (absPct >= LABEL_WEAK) labelQuality = isCorrect ? 'WEAK_WIN' : 'WEAK_LOSS';
      else labelQuality = isCorrect ? 'NOISE_WIN' : 'NOISE_LOSS';

      // ── Magnitude-tiered lrMult (v19.0.0): strong moves get amplified feedback ──
      if (!s._dnr && s.source !== 'trade') {
        if (isCorrect) {
          if (labelQuality === 'STRONG_WIN') lrMult *= 1.5;
          else if (labelQuality === 'WEAK_WIN') lrMult *= 1.0;
          else lrMult *= 0.5; // noise correct — don't overfit random guesses
        } else {
          if (labelQuality === 'BAD_LOSS') lrMult *= 2.0;
          else if (labelQuality === 'WEAK_LOSS') lrMult *= 1.3;
          else lrMult *= 0.6; // noise loss — ignore random noise
        }
      }

      // ── Loss Memory: store detailed context of every loss (v18.0.0) ──
      if (!isCorrect && (labelQuality === 'BAD_LOSS' || labelQuality === 'WEAK_LOSS') && s.source !== 'trade') {
        // Build compact context vector for cosine similarity matching
        const lmVec = [
          aiNormalize(s.predictedUp - 0.5, 0.5),
          labelQuality === 'BAD_LOSS' ? 1 : 0.5,
          Math.sin(2*Math.PI*(new Date(s.t).getUTCHours())/24),
          Math.cos(2*Math.PI*(new Date(s.t).getUTCHours())/24)
        ];
        // Merge with feature vector first 4 dimensions for richer matching
        if (s.x && s.x.length >= 4) {
          lmVec.push(...s.x.slice(0, 4).map((v, i) => aiNormalize(v || 0, 1)));
        }
        aiState._lastLossAt = Date.now();
        aiState.lossMemory.push({
          asset: s.asset,
          direction: s.predicted === 1 ? 'BUY' : 'SELL',
          hour: new Date(s.t).getUTCHours(),
          regime: s.regime || 'UNKNOWN',
          lossPct: changePct,
          labelQuality,
          vec: lmVec,
          ts: s.t || Date.now()
        });
        while (aiState.lossMemory.length > LM_MAX_STORED) aiState.lossMemory.shift();
      }

      // V24.1.100 SCHEMA BRIDGE — queued samples can still be 64/72/76 features
      // if they were created before the 88-feature upgrade (or restored from an older backup).
      // Normalize them BEFORE they are copied into the labeled dataset or sent to XGB/LGB.
      if (Array.isArray(s.x) && [48,56,64,72,76].includes(s.x.length) && s.x.length < AI_FEATURES) {
        s.x = s.x.concat(new Array(AI_FEATURES - s.x.length).fill(0));
      }

      aiState.labeledDataset.push({
        policyId:s.policyId||AI_POLICY_ID, policyParent:s.policyParent||AI_POLICY_PARENT, policySchema:Number(s.policySchema||AI_POLICY_SCHEMA),
        asset:s.asset, t:s.t, due:s.due, price:s.price,
        predicted:s.predicted, predictedUp:s.predictedUp,
        label, correct:isCorrect, labelQuality, x:Array.isArray(s.x)?s.x.slice():s.x,
        source:s.source, tradeType:s.tradeType||null, setupDir:s.setupDir||null,
        setupScore:s.setupScore??null, setupConfidence:s.setupConfidence??null,
        qualifiedSetup:!!s.qualifiedSetup
      });
      if (!PAPER_SETUP_VALIDATION_MODE) {
        aiLabRecordSample(s,label);
      }
      aiLog('AI_SAMPLE_LABELED', {asset:s.asset,source:s.source,label,correct:isCorrect,changePct,aiTrained:aiState.trained,xgbOnly:true,xgbSamples:AI_LAB.samples.length}, false);
      if (aiState.labeledDataset.length > 5000) {
        aiState.labeledDataset.splice(0, aiState.labeledDataset.length - 5000);
      }
      if (!s.x || !Array.isArray(s.x) || s.x.length !== AI_FEATURES) {
        console.warn('[AI] Skipping malformed sample — x:', typeof s.x, Array.isArray(s.x) ? s.x.length : 'N/A');
        continue;
      }
      // V24.1.73 XGB-only: legacy neural optimizer disabled.
      // Labels still flow into AI_LAB/XGBoost and market-specific trust metrics.
    }
    // V24.1.73 XGB-only: legacy neural experience replay disabled.

    aiState.samples=keep;
    if (aiState.total > 0) lastIndicators.aiAccuracy = aiState.correct / aiState.total;
    // AI persistence is manual-only; export from the popup when finished.
  }

  // Automatic AI persistence/load was intentionally removed in V23.
  // Manual full backup is provided through GET_FULL_BACKUP below.

  // ── Auto-calibrated confidence threshold ──
  // Tracks EMA of model confidence vs actual accuracy. If the model is
  // overconfident (conf >> acc), it raises the threshold to compensate.
  // Low confidence NEVER lowers the threshold — an uncertain model
  // should not get easier trade entry. Only overconfidence is penalized.
  function aiCalibratedThreshold(baseThreshold) {
    const conf = aiState.confEma;
    const acc = aiState.accEma;
    if (conf < 0.01 || acc < 0.01) return baseThreshold;
    const ratio = conf / Math.max(acc, 0.01);
    // Ratio > 1.0 = overconfident → raise threshold
    // Ratio <= 1.0 = uncertain or accurate → keep base threshold
    const adj = ratio > 1.0 ? Math.min(1.25, ratio) : 1.0;
    const calib = baseThreshold * adj;
    return Math.min(0.88, calib);
  }

  // AI state is intentionally session-memory only.
  // Use the popup's EXPORT AI + DATA button to persist it manually.
  aiState._flushTimer = setInterval(aiFlush, 1000);

  // Last CLOSED expiry-TF candle [o,h,l,c,t] for the given asset/TF key.
  function closedTFCandle(act, tfKey) {
    const cfg = TF_MAP[tfKey];
    const tf  = getTF(act, tfKey);
    if (!cfg || !tf || tf.lastGroupStart === undefined) return null;
    const c = tf.rates[tf.lastGroupStart - cfg.sec];   // candle that just closed
    if (!c) return null;
    return { open: c[0], high: c[1], low: c[2], close: c[3], time: c[4] };
  }

  function posOf(price, upper, lower) {
    if (price <= lower) return 'lower';
    if (price >= upper) return 'upper';
    return 'middle';
  }

  function captureSnapshot(dir, amount, entryType, sig, assetOverride) {
    const asset = assetOverride || activeAsset || lastTradeAsset;
    // V24.1.188: snapshot the expiry actually chosen for this strategy, not
    // the popup's legacy context timeframe. Also read the indicator workspace
    // belonging to THIS asset so delayed multi-chart execution cannot export
    // EMA/RSI/ATR values from whichever chart happened to evaluate last.
    const expiry = Math.max(5, parseInt(sig?.executionExpiry || botConfig?.timeframe || 30, 10)); // V197 selected execution expiry
    const tfKey  = expiryToTF(expiry);
    const ind    = indicatorStateByAsset[String(asset||'')] || lastIndicators;
    const frozen = sig?.measurement?.signalSnapshot || null;
    let candle = null, tfClose = null, storageCandles = 0;
    if (asset) {
      const act = getAsset(asset);
      // B26: deterministic BB families are generated from a source candle that may
      // differ from the expiry TF (Runner/Winner 15s source + 60s expiry, Chop 15s
      // source + 5s expiry). CSV must record THAT frozen source candle, never the
      // expiry candle. Legacy families retain the old expiry-TF snapshot behavior.
      candle = frozen ? {open:Number(frozen.open),high:Number(frozen.high),low:Number(frozen.low),close:Number(frozen.close),time:Number(frozen.sourceSeq)} : closedTFCandle(act, tfKey);
      const sourceTf = frozen?.sourceTf || tfKey;
      const tf = getTF(act, sourceTf);
      tfClose = tf?.prices?.length ? tf.prices[tf.prices.length - 1] : null;
      storageCandles = act.prices.length;
    }
    const refPrice = lastTickPrice[asset] || candle?.close || tfClose || 0;
    const body = candle ? Math.abs(candle.close - candle.open) : null;
    const cDir = frozen?.candleDirection || (candle ? (candle.close > candle.open ? 'bullish' : candle.close < candle.open ? 'bearish' : 'flat') : null);

    // Derived fields
    const stratDef = STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick'];
    const min5s = v241WarmupTarget(asset ? getAsset(asset) : null, stratDef.minPrices || 40);
    const warmupPct = Math.min(100, Math.round((storageCandles / min5s) * 100));
    const spread = candle ? ((candle.high - candle.low) / (candle.close || 1)) : null;
    const volatility = (ind.atr && refPrice) ? ((ind.atr / refPrice) * 100) : null;
    const tradeId = tradeIdCounter++;
    // B32.6 Trade Replay Recorder: structured market/model frames are much more
    // useful to the learner than compressed screen video. Keep ~60s of 7B state
    // before entry; finalizeTrade appends everything through contract close.
    const replayPre = (typeof C7B_RESEARCH !== 'undefined' ? C7B_RESEARCH : []).filter(r=>r.asset===asset && r.ts>=Date.now()-60000).map(r=>({
      ts:r.ts,price:r.price,probUp:r.probUp,vol:r.vol,decision:r.decision,source:r.source,
      x:Array.isArray(r.x)?r.x.slice():[],ai:r.ai?{...r.ai}:null
    }));

    return {
      ts: Date.now(),
      accountMode: typeof kaosPocketOptionBalanceIsDemo==='boolean'?(kaosPocketOptionBalanceIsDemo?'DEMO':'REAL'):'UNKNOWN',
      featureVector: (()=>{try{const v=aiFeatures(asset,refPrice,ind);return Array.isArray(v)&&v.length===104?v.slice():null;}catch(_){return null;}})(),
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      asset, direction: dir, amount: Number(amount) || 0,
      entryType: entryType || 'signal',
      entryPrice: refPrice, exitPrice: null, result: null, profit: null,
      replayVersion: 1, replayStartTs: replayPre.length ? replayPre[0].ts : Date.now(), replayFrames: replayPre,
      candleOpen:  candle?.open  ?? null, candleHigh: candle?.high ?? null,
      candleLow:   candle?.low   ?? null, candleClose: candle?.close ?? null,
      candleBody: body, candleDirection: cDir,
      rsi: frozen?.rsi14 ?? ind.rsi, ema5: ind.ema5, ema9: frozen?.ema9 ?? ind.ema9, ema21: frozen?.ema21 ?? ind.ema21,
      macd: ind.macd, macdSignal: ind.macdSignal ?? null,
      stochK: ind.stoch, stochD: ind.stochD ?? null, atr: ind.atr,
      bollingerUpper: frozen?.bbUpper ?? ind.bollUpper ?? null, bollingerLower: frozen?.bbLower ?? ind.bollLower ?? null,
      bollingerPos: (ind.bollUpper != null && ind.bollLower != null)
        ? (frozen ? (frozen.bbPosition<=-0.75?'lower':frozen.bbPosition>=0.75?'upper':'middle') : posOf(refPrice, ind.bollUpper, ind.bollLower)) : null,
      keltnerUpper: ind.keltUpper ?? null, keltnerLower: ind.keltLower ?? null,
      keltnerPos: (ind.keltUpper != null && ind.keltLower != null)
        ? posOf(refPrice, ind.keltUpper, ind.keltLower) : null,
      strategy: botConfig?.strategy || 'Murfs Pick',
      mode: sig?.mode || ind.mode || null,
      totalScore: sig ? (Number.isFinite(Number(sig.str)) ? Number(sig.str) : (Number.isFinite(Number(sig.measurement?.finalThreeStepScore)) ? Number(sig.measurement.finalThreeStepScore) : null)) : null,
      buyScore: ind.buyScore ?? null, sellScore: ind.sellScore ?? null,
      reasons: sig?.reasons || [],
      // ── New extended fields ──
      tradeID: tradeId,
      expiry: expiry,
      indicatorTimeframe: frozen?.sourceTf || tfKey,
      signalCandleId: frozen?.sourceSeq ?? null,
      signalSnapshot: frozen ? {...frozen} : null,
      storageCandles: storageCandles,
      warmupPercent: warmupPct,
      spread: spread,
      volatility: volatility,
      marketSession: null,
      martingaleLevel: martLevel,
      compoundLevel: compoundLevel,
      winStreak: winStreak,
      lossStreak: lossStreak,
      sessionPnL: sessionPnl,
      ai30Up: ind.aiPrediction?.up ?? null,
      ai30Down: ind.aiPrediction?.down ?? null,
      ai30Confidence: ind.aiPrediction?.confidence ?? null,
      ai30Warm: !!ind.aiPrediction?.warm,
      ai30Samples: ind.aiPrediction?.trained ?? 0,
      ai30Accuracy: ind.aiAccuracy ?? null,
      // v19.10 strategy measurement fields
      strategyType: 'GENERIC',
      runBuy: null, runSell: null, revBuy: null, revSell: null,
      tqsBuy: null, tqsSell: null, marketQuality: null,
      aiBuy: null, aiSell: null, regimeAtEntry: ind.regime || null,
      entryPhase: sig?.entryPhase ?? null,
      // ── V24.1.279 ENGINE ATTRIBUTION ──
      // One canonical tag per executed trade so we can always tell WHICH engine
      // was responsible and whether AI actually contributed to the entry score.
      engineFamily: String(sig?.tradeType || sig?.measurement?.marketClass || ind?.marketClass || 'UNKNOWN'),
      engineMode: sig?.mode || ind?.mode || null,
      strategyVersion: sig?.measurement?.strategyVersion || null,
      strategyEngine: sig?.measurement?.engine || sig?.measurement?.setup || sig?.tradeType || null,
      scoreBreakdown: (sig?.measurement?.scoreBreakdown || ind?.scoreBreakdown || null),
      aiPredictivePoints: Number((sig?.measurement?.scoreBreakdown || ind?.scoreBreakdown || {}).aiPredictive ?? 0),
      aiPredictiveAuthoritative: !!((sig?.measurement?.scoreBreakdown || ind?.scoreBreakdown || {}).aiPredictiveAuthoritative),
    };
  }

  // Persist a finished trade to memory + chrome.storage (survives popup close / SW sleep).
  function persistTradeRecord(snap) {
    if (!snap) return;
    tradeRecords.push(snap);
    if (tradeRecords.length > TRADE_RECORD_MAX) tradeRecords.shift();
    try {
      chrome.storage.local.get('tradeRecords', (data) => {
        const trades = Array.isArray(data.tradeRecords) ? data.tradeRecords : [];
        trades.push(snap);
        if (trades.length > 1000) trades.splice(0, trades.length - 1000);
        chrome.storage.local.set({ tradeRecords: trades });
      });
    } catch (e) { /* extension context gone */ }
  }

  // v19.10: realized strategy performance measurement. This does not alter
  // entry thresholds or decisions; it only records what happened after entry.
  function recordStrategyPerformance(snap) {
    if (!snap || !snap.direction) return;
    const type = snap.strategyType === 'RUNNER' || snap.strategyType === 'REVERSAL' ? snap.strategyType : 'GENERIC';
    const dir = snap.direction === 'SELL' ? 'SELL' : 'BUY';
    if (!aiState.strategyPerformance[type]) aiState.strategyPerformance[type] = {};
    if (!aiState.strategyPerformance[type][dir]) aiState.strategyPerformance[type][dir] = { trades:0, wins:0, losses:0, draws:0, profit:0 };
    const st = aiState.strategyPerformance[type][dir];
    st.trades++;
    if (snap.result === 'win') st.wins++;
    else if (snap.result === 'loss') st.losses++;
    else if (snap.result === 'draw') st.draws++;
    st.profit += Number(snap.profit) || 0;
    st.winRate = st.trades ? st.wins / st.trades : 0;

    // v19.10.1: bucket the exact entry context. This is diagnostic only and
    // intentionally does not alter any entry threshold or trade decision.
    const bucket = (prefix, value, ranges) => {
      const n = Number(value);
      if (!Number.isFinite(n)) return `${prefix}:NA`;
      for (const r of ranges) if (n < r.max) return `${prefix}:${r.label}`;
      return `${prefix}:${ranges[ranges.length - 1].label}`;
    };
    const key = [
      type, dir,
      bucket('TQS', snap.direction === 'BUY' ? snap.tqsBuy : snap.tqsSell, [
        {max:50,label:'0-49'},{max:60,label:'50-59'},{max:70,label:'60-69'},{max:101,label:'70+'}
      ]),
      bucket('MQ', snap.marketQuality, [
        {max:50,label:'0-49'},{max:60,label:'50-59'},{max:70,label:'60-69'},{max:101,label:'70+'}
      ]),
      bucket('RSI', snap.rsi, [
        {max:20,label:'0-19'},{max:40,label:'20-39'},{max:60,label:'40-59'},{max:80,label:'60-79'},{max:101,label:'80+'}
      ]),
      `REG:${snap.regimeAtEntry || 'UNKNOWN'}`
    ].join('|');
    if (!aiState.strategyBuckets || typeof aiState.strategyBuckets !== 'object') aiState.strategyBuckets = {};
    const b = aiState.strategyBuckets[key] || { strategyType:type, direction:dir, trades:0, wins:0, losses:0, draws:0, profit:0,
      tqs: snap.direction === 'BUY' ? snap.tqsBuy : snap.tqsSell, mq:snap.marketQuality, rsi:snap.rsi, regime:snap.regimeAtEntry || 'UNKNOWN' };
    b.trades++;
    if (snap.result === 'win') b.wins++;
    else if (snap.result === 'loss') b.losses++;
    else if (snap.result === 'draw') b.draws++;
    b.profit += Number(snap.profit) || 0;
    b.winRate = b.trades ? b.wins / b.trades : 0;
    b.lastTs = Date.now();
    aiState.strategyBuckets[key] = b;

    // Keep the diagnostic map bounded so it cannot grow without limit.
    const keys = Object.keys(aiState.strategyBuckets);
    if (keys.length > 500) {
      keys.sort((a,b) => (aiState.strategyBuckets[a].lastTs||0) - (aiState.strategyBuckets[b].lastTs||0));
      for (let i=0; i<keys.length-500; i++) delete aiState.strategyBuckets[keys[i]];
    }
  }

  // Attach the result to the pending snapshot and archive it.
  // Always produces a record — even if pendingSnapshot was lost (reload, race, etc.).
  function getPendingSnapshot(asset) {
    const q=asset && pendingSnapshotQueuesByAsset[asset];
    if(Array.isArray(q)&&q.length) return q[0];
    return (asset && pendingSnapshotsByAsset[asset]) || pendingSnapshot || null;
  }
  function setPendingSnapshot(asset,snap) {
    if(asset){
      if(!Array.isArray(pendingSnapshotQueuesByAsset[asset])) pendingSnapshotQueuesByAsset[asset]=[];
      pendingSnapshotQueuesByAsset[asset].push(snap);
      pendingSnapshotsByAsset[asset]=pendingSnapshotQueuesByAsset[asset][0];
    }
    if(!multiAssetMode) pendingSnapshot=snap;
  }
  function clearPendingSnapshot(asset) {
    const q=asset && pendingSnapshotQueuesByAsset[asset];
    if(Array.isArray(q)&&q.length){
      q.shift();
      if(q.length) pendingSnapshotsByAsset[asset]=q[0];
      else { delete pendingSnapshotQueuesByAsset[asset]; delete pendingSnapshotsByAsset[asset]; }
    } else if(asset) delete pendingSnapshotsByAsset[asset];
    if(!multiAssetMode || (pendingSnapshot && (!asset || pendingSnapshot.asset===asset))) pendingSnapshot=null;
  }

  function finalizeTrade(asset, result, profit, amountHint) {
    let snap = getPendingSnapshot(asset);
    clearPendingSnapshot(asset);
    if (!snap) {
      snap = captureSnapshot(lastTradeDir || 'BUY', amountHint || lastTradeAmt || 0, 'recovery', null, asset);
      snap.asset = asset || snap.asset || lastTradeAsset || '';
    }
    const durableDir = normalizeTradeDirection(
      snap.direction || pendingTradeDirections[asset] || lastTradeDir
    );
    if (durableDir) snap.direction = durableDir;
    snap.result = result;
    if (result === 'win') snap.profit = Number(profit) || 0;
    else if (result === 'draw') snap.profit = 0;
    else snap.profit = -(Number(snap.amount) || Number(amountHint) || 0);
    snap.exitPrice = lastTickPrice[asset] || lastTickPrice[snap.asset] || snap.entryPrice || null;
    snap.resultTs = Date.now();
    // Complete the structured replay through expiration/result. De-duplicate by ts.
    try {
      const seen=new Set((snap.replayFrames||[]).map(r=>r.ts));
      for(const r of C7B_RESEARCH){
        if(r.asset!==snap.asset || r.ts<(snap.replayStartTs||snap.ts-60000) || r.ts>snap.resultTs+5000 || seen.has(r.ts)) continue;
        (snap.replayFrames||(snap.replayFrames=[])).push({ts:r.ts,price:r.price,probUp:r.probUp,vol:r.vol,decision:r.decision,source:r.source,x:Array.isArray(r.x)?r.x.slice():[],ai:r.ai?{...r.ai}:null,forward:r.forward?JSON.parse(JSON.stringify(r.forward)):null});
        seen.add(r.ts);
      }
      snap.replayFrames.sort((a,b)=>a.ts-b.ts);
      snap.replayEndTs=snap.resultTs;
      snap.replayFrameCount=snap.replayFrames.length;
    } catch(_) {}
    if (Array.isArray(snap.reasons)) snap.reasons = snap.reasons.join('; ');
    recordStrategyPerformance(snap);
    persistTradeRecord(snap);
    // AI state is intentionally not persisted automatically. Export manually from the popup.
    return snap;
  }

  function recordTradeDebug(dir, asset, amount, result, profit) {
    debugState.trades.push({ dir, asset, amount: Number(amount) || 0, result, profit: Number(profit) || 0, ts: Date.now() });
    if (debugState.trades.length > DEBUG_TRADE_LOG_MAX) {
      debugState.trades = debugState.trades.slice(-DEBUG_TRADE_LOG_MAX);
    }
  }

  // Full debug snapshot → popup. Throttled 400ms unless forced.
  function sendDebug(extra, force) {
    const now = Date.now();
    if (!force && now - lastDebugAt < 400) return;
    lastDebugAt = now;
    if (extra && extra.reason) lastDebugReason = extra.reason;

    const stratDef = STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick'];

    const asset = activeAsset || '';
    const debugIndicators = asset && indicatorStateByAsset[asset] ? indicatorStateByAsset[asset] : lastIndicators;
    // B32.20.3 — the live built-in authority is the 5s micro-trend engine.
    // Do not label the selected expiry/context TF (for example 60s) as the
    // strategy's candle count. That made a correctly bootstrapped 200x5s
    // market appear to have only ~16 candles and implied a false warmup gate.
    let tfKey = '5s', tfCandles = 0, storageCandles = 0, contextTfKey = null, contextTfCandles = 0;
    if (asset && botConfig) {
      const act = getAsset(asset);
      storageCandles = act.prices.length;
      const slot = botConfig?.strategyEngine==='MIXED_SLOTS' ? strategySlotForAsset(asset) : null;
      const customMode = botConfig?.strategyEngine==='CUSTOM_CONFIRM' || !!slot?.profile;
      if (customMode) {
        const cfg = slot?.profile || botConfig?.strategyProfile || {};
        tfKey = `${Math.max(5, Number(cfg.signalTf)||30)}s`;
        tfCandles = getLiveTFView(act, tfKey).prices.length;
      } else {
        tfKey = '5s';
        // act.prices is the canonical closed-5s strategy store populated by HISTORY_BACKFILL.
        tfCandles = act.prices.length;
      }
      contextTfKey = expiryToTF(parseInt(botConfig.timeframe || 30, 10));
      contextTfCandles = getLiveTFView(act, contextTfKey).prices.length;
    }
    const min5s = v241WarmupTarget(asset ? getAsset(asset) : null, stratDef.minPrices || 40);

    safeSend({
      type: 'DEBUG_UPDATE',
      state: {
        asset, tfKey, storageCandles, tfCandles, contextTfKey, contextTfCandles,
        warmupNeeded: min5s,
        warmupPct: Math.min(100, Math.round((storageCandles / min5s) * 100)),
        running: isRunning,
        strategy: botConfig?.strategy || 'Murfs Pick',
        timeframe: botConfig?.timeframe || 30,
        amount: currentAmount, martLevel, tradePending,
        lastTradeDir, lastTradeAmt,
        wins: sessionWins, losses: sessionLosses, pnl: sessionPnl,
        winStreak, lossStreak, compoundLevel, tradeIdCounter,
        reason: lastDebugReason,
        updatedAt: now,
        indicators: { ...debugIndicators },
        trades: debugState.trades.slice(-DEBUG_TRADE_LOG_MAX),
        ...(extra || {})
      }
    });
  }

  // ★ STORAGE timeframe — 5 seconds. Everything below derives from it ★
  const BUCKET_SEC = 5;
  let prewarmReplayActive = false;
  const prewarmReplayAssets = new Set();
  const MAX_PRICES = 3600;     // 5s storage — 5h of closes

  // ── Indicator timeframes, built from the 5s storage ──
  const TF_MAP = {
    '5s':   { sec: 5,   mult: 1  },
    '10s':  { sec: 10,  mult: 2  },
    '15s':  { sec: 15,  mult: 3  },
    '30s':  { sec: 30,  mult: 6  },
    '60s':  { sec: 60,  mult: 12 },
    '120s': { sec: 120, mult: 24 },
    '180s': { sec: 180, mult: 36 },   // 3-minute expiries
    '300s': { sec: 300, mult: 60 }
  };

  // Trade expiry (seconds) → PRIMARY indicator TF key.
  function expiryToTF(expirySec) {
    const keys = Object.keys(TF_MAP).sort((a, b) => TF_MAP[a].sec - TF_MAP[b].sec);
    let best = keys[0];
    for (const k of keys) { if (TF_MAP[k].sec <= expirySec) best = k; else break; }
    return best;   // primary: 30→30s · 60→60s · 120→120s · etc.
  }

  // Secondary indicator TF = one step below the primary expiry TF.
  // 30s→15s · 60s→30s · 120s→60s · 180s→120s · 300s→180s
  function expiryToSecondaryTF(expirySec) {
    const expiryTF = expiryToTF(expirySec);
    if (expiryTF === '15s') return '15s';
    const keys = Object.keys(TF_MAP).sort((a, b) => TF_MAP[a].sec - TF_MAP[b].sec);
    const idx = keys.indexOf(expiryTF);
    return idx > 0 ? keys[idx - 1] : '15s';
  }

  // Normalize PO tick timestamps → epoch seconds.
  // Stream may send seconds OR milliseconds; HISTORY candles vary.
  function toEpochSec(t) {
    let n = Number(t);
    if (!isFinite(n) || n <= 0) return Math.floor(Date.now() / 1000);
    if (n > 1e12) n = Math.floor(n / 1000);       // ms
    else if (n > 1e10) n = Math.floor(n / 1000);  // µs-ish
    return Math.floor(n);
  }

  function getAsset(name) {
    if (!assetData[name]) assetData[name] = {
      prices: [], rates: {}, lastBucket: null, lastClosed: -1, newCandle: false,
      lastPrice: 0, lastTickSec: 0,
      tf: {}
    };
    return assetData[name];
  }

  function getTF(a, tfKey) {
    if (!a.tf) a.tf = {};
    if (!a.tf[tfKey]) a.tf[tfKey] = {
      prices: [], rates: {}, lastGroupStart: undefined,
      open: 0, high: 0, low: 0, count: 0,
      lastClose: 0, lastT: 0, newCandle: false
    };
    return a.tf[tfKey];
  }

  // Return a read-only strategy view containing CLOSED higher-TF candles
  // plus the CURRENT forming higher-TF candle. The forming candle is built
  // from the 5s basket, but indicators themselves remain strictly on the
  // configured higher timeframe (30s/15s for 30s expiry, 60s/30s for 60s).
  // This lets the strategy re-check every 5s without waiting for a full
  // secondary-TF candle to close.
  function getLiveTFView(a, tfKey) {
    const s = getTF(a, tfKey);
    const prices = s.prices.slice();
    if (s.count > 0 && isFinite(s.lastClose) && s.lastClose > 0) {
      const groupStart = s.lastGroupStart;
      const lastStored = prices.length ? prices[prices.length - 1] : null;
      // s.prices contains only CLOSED TF candles. Append the current
      // in-progress candle exactly once as the live close.
      if (groupStart !== undefined && s.lastClose !== lastStored) {
        prices.push(s.lastClose);
      } else if (groupStart !== undefined && prices.length === 0) {
        prices.push(s.lastClose);
      }
    }
    return Object.assign({}, s, { prices });
  }

  // V24.1.288 — PERMANENT RAW CLOSED-5S CANDLE ARCHIVE
  // Independent of AI/sample buffers. Uses unlimited chrome.storage.local and
  // persists compact OHLC rows per asset so overnight market history survives.
  const RAW5_KEY='KAOS_raw5_history_v1';
  const raw5History={byAsset:{},loaded:false,dirty:false,lastSave:0};
  try{chrome.storage.local.get(RAW5_KEY,d=>{try{const z=d&&d[RAW5_KEY];if(z&&z.byAsset&&typeof z.byAsset==='object')raw5History.byAsset=z.byAsset;raw5History.loaded=true;}catch(_){raw5History.loaded=true;}});}catch(_){raw5History.loaded=true;}
  function raw5Archive(asset,b,c){
    asset=String(asset||'').trim(); if(!asset||!Array.isArray(c)||c.length<4)return;
    const ts=Number(b)*1000, row={ts,open:Number(c[0]),high:Number(c[1]),low:Number(c[2]),close:Number(c[3]),closeTs:Number(c[4]||b+BUCKET_SEC)*1000};
    if(![row.open,row.high,row.low,row.close].every(Number.isFinite))return;
    const a=raw5History.byAsset[asset]||(raw5History.byAsset[asset]=[]), last=a[a.length-1];
    if(last&&Number(last.ts)===ts){a[a.length-1]=row;} else if(!last||Number(last.ts)<ts){a.push(row);} else {const i=a.findIndex(x=>Number(x.ts)===ts);if(i>=0)a[i]=row;else{a.push(row);a.sort((x,y)=>Number(x.ts)-Number(y.ts));}}
    raw5History.dirty=true;
  }
  function raw5Persist(force=false){
    const now=Date.now(); if(!raw5History.dirty||(!force&&now-raw5History.lastSave<30000))return;
    raw5History.lastSave=now; raw5History.dirty=false;
    try{chrome.storage.local.set({[RAW5_KEY]:{version:1,updatedAt:now,byAsset:raw5History.byAsset}});}catch(_){raw5History.dirty=true;}
  }
  setInterval(()=>raw5Persist(false),30000);
  try{addEventListener('pagehide',()=>raw5Persist(true));}catch(_){}
  function raw5Meta(){const out={};for(const [asset,a] of Object.entries(raw5History.byAsset)){out[asset]={count:a.length,firstTs:a.length?Number(a[0].ts):null,lastTs:a.length?Number(a[a.length-1].ts):null};}return out;}


  // B31 — INDEPENDENT REAL-CANDLE RECORDER. This archive is deliberately separate
  // from strategy decisions, AI samples, trades, HOLDs and synthetic gap-fill candles.
  const MARKET_CANDLE_KEY='KAOS_market_candles_real_v2';
  const marketCandleHistory={version:2,byAsset:{},loaded:false,dirty:false,lastSave:0};
  try{chrome.storage.local.get(MARKET_CANDLE_KEY,d=>{try{const z=d&&d[MARKET_CANDLE_KEY];if(z&&z.byAsset)marketCandleHistory.byAsset=z.byAsset;marketCandleHistory.loaded=true;}catch(_){marketCandleHistory.loaded=true;}});}catch(_){marketCandleHistory.loaded=true;}
  function marketCandleArchive(asset,b,c){asset=String(asset||'').trim();if(!asset||!Array.isArray(c)||c.length<4)return;const row={ts:Number(b)*1000,open:+c[0],high:+c[1],low:+c[2],close:+c[3],closeTs:Number(c[4]||b+BUCKET_SEC)*1000};if(![row.open,row.high,row.low,row.close].every(Number.isFinite))return;const a=marketCandleHistory.byAsset[asset]||(marketCandleHistory.byAsset[asset]=[]),last=a[a.length-1];if(last&&+last.ts===row.ts)a[a.length-1]=row;else if(!last||+last.ts<row.ts)a.push(row);else{const i=a.findIndex(x=>+x.ts===row.ts);if(i>=0)a[i]=row;else{a.push(row);a.sort((x,y)=>+x.ts-+y.ts);}}marketCandleHistory.dirty=true;}
  function marketCandlePersist(force=false){const now=Date.now();if(!marketCandleHistory.dirty||(!force&&now-marketCandleHistory.lastSave<15000))return;marketCandleHistory.lastSave=now;marketCandleHistory.dirty=false;try{chrome.storage.local.set({[MARKET_CANDLE_KEY]:{version:2,updatedAt:now,source:'Pocket Option observed REAL closed 5s candles only; no synthetic carry-forward',byAsset:marketCandleHistory.byAsset}});}catch(_){marketCandleHistory.dirty=true;}}
  function marketCandleMeta(){const o={};for(const [a,r] of Object.entries(marketCandleHistory.byAsset))o[a]={count:r.length,firstTs:r.length?+r[0].ts:null,lastTs:r.length?+r[r.length-1].ts:null};return o;}
  setInterval(()=>marketCandlePersist(false),15000);try{addEventListener('pagehide',()=>marketCandlePersist(true));}catch(_){}

  // Roll one CLOSED 5s candle [o,h,l,c,t] up into every indicator TF.
  // LENIENT close: TF boundary pass closes even if some 5s buckets empty.
  function feedTF(a, b, c) {
    for (const k of Object.keys(TF_MAP)) {
      const cfg = TF_MAP[k];
      const s = getTF(a, k);
      const groupStart = Math.floor(b / cfg.sec) * cfg.sec;
      if (s.lastGroupStart === undefined) {
        s.lastGroupStart = groupStart;
        s.open = c[0]; s.high = c[1]; s.low = c[2]; s.count = 1;
      } else if (groupStart === s.lastGroupStart) {
        if (c[1] > s.high) s.high = c[1];
        if (c[2] < s.low)  s.low  = c[2];
        s.count++;
      } else {
        if (s.count > 0) {
          s.rates[s.lastGroupStart] = [s.open, s.high, s.low, s.lastClose, s.lastT];
          s.prices.push(s.lastClose);
          if (s.prices.length > MAX_PRICES) s.prices.shift();
          s.newCandle = true;
        }
        s.lastGroupStart = groupStart;
        s.open = c[0]; s.high = c[1]; s.low = c[2]; s.count = 1;
      }
      s.lastClose = c[3];
      s.lastT = c[4] || (b + cfg.sec);
    }
  }

  // Close one completed 5s bucket. Empty OTC gaps carry-forward last close
  // so warmup never freezes on sparse ticks.
  function tryCloseBucket(a, b, allowCarry) {
    if (b <= a.lastClosed) return false;
    let c = a.rates[b];
    const isRealObservedCandle = !!c;
    if (!c) {
      if (!allowCarry) return false;
      const px = a.lastPrice || (a.prices.length ? a.prices[a.prices.length - 1] : 0);
      if (!px) return false;
      c = [px, px, px, px, b + BUCKET_SEC];
      a.rates[b] = c;
    }
    a.prices.push(c[3]);
    if (a.prices.length > MAX_PRICES) a.prices.shift();
    a.lastPrice = c[3];
    a.newCandle = true;
    feedTF(a, b, c);
    raw5Archive(a.__assetName || '', b, c);
    raw5Persist(false);
    // Independent research archive: REAL observed candles only. Never record carry-forward gaps.
    if (isRealObservedCandle) { marketCandleArchive(a.__assetName || '', b, c); marketCandlePersist(false); }
    a.lastClosed = b;
    return true;
  }

  // Close every completed bucket up to (but not including) endBucket.
  function closeThrough(a, endBucket) {
    if (a.lastBucket === null || a.lastBucket === undefined) return 0;
    if (a.lastClosed < 0) {
      // First close: start at first known bucket, not from -1 + 1 walking forever
      a.lastClosed = a.lastBucket - BUCKET_SEC;
    }
    let n = 0;
    const start = a.lastClosed + BUCKET_SEC;
    // Safety: never walk more than ~2 minutes of buckets in one call
    const maxSteps = 24;
    let steps = 0;
    for (let x = start; x < endBucket && steps < maxSteps; x += BUCKET_SEC, steps++) {
      if (tryCloseBucket(a, x, true)) n++;
    }
    // ── V24.1.287-B3 HARDENING (ported from V283-B2) ───────────────────────
    // If the 24-step budget ran out while the cursor is still behind the live
    // bucket, the feed had a HOLE (broker timestamp jump, reconnect, idle gap,
    // or a seconds/milliseconds format swing). The original code kept the whole
    // deficit, so EVERY later tick manufactured another 24 carry-forward
    // candles — a ratchet adding hundreds of synthetic 5s closes per minute that
    // corrupted every TF series and inflated the CANDLES counter. A hole is
    // missing data, not 24 real closes: resync the cursor and resume from live.
    const cursorNow = start + steps * BUCKET_SEC;
    if (steps >= maxSteps && cursorNow < endBucket) {
      a.lastClosed = endBucket - BUCKET_SEC;
      if (Date.now() - (a.lastResyncLog || 0) > 10000) {
        a.lastResyncLog = Date.now();
        try {
          aiLog('V283_CANDLE_CURSOR_RESYNC', {
            src: 'closeThrough',
            missingSec: endBucket - cursorNow,
            candlesAtResync: a.prices.length
          }, true);
        } catch (_) {}
      }
    }
    return n;
  }

  // Rebuild every TF close-series from the 5s storage after HISTORY.
  function rebuildTF(a) {
    const base = a.prices;
    for (const k of Object.keys(TF_MAP)) {
      const cfg = TF_MAP[k];
      const s = getTF(a, k);
      s.prices = [];
      for (let i = 0; i + cfg.mult <= base.length; i += cfg.mult) {
        s.prices.push(base[i + cfg.mult - 1]);
      }
      s.lastGroupStart = undefined;
      s.count = 0;
      // Mark ready so strategy can fire once live stream produces next TF close
      s.newCandle = s.prices.length >= 3;
      if (s.prices.length) s.lastClose = s.prices[s.prices.length - 1];
    }
  }

  // ── WALL-CLOCK 5s CLOSER ────────────────────────────────────
  // Closes completed buckets even when OTC ticks are sparse.
  // Uses last tick time when available (correct clock), else wall clock.
  setInterval(() => {
    if (!isRunning) return;
    const wallSec = Math.floor(Date.now() / 1000);
    for (const name of Object.keys(assetData)) {
      // B15.10.24: never manufacture/close candles for a market that is no
      // longer one of the visible four chart slots.
      if (multiAssetMode && Object.keys(visibleChartSlots).length > 0 &&
          !Object.values(visibleChartSlots).includes(name)) continue;
      const a = assetData[name];
      if (a.lastBucket === null || a.lastBucket === undefined) continue;
      const cur = BUCKET_SEC * Math.floor(wallSec / BUCKET_SEC);
      // V283 CLOCK-SKEW GUARD: never let wall time manufacture a backlog of
      // synthetic 5s candles. Broker timestamps can be offset from local time;
      // the old closeThrough(a, cur) would then append up to 24 carry-forward
      // candles EVERY SECOND until the clocks caught up (visible as the candle
      // counter racing upward). STREAM advancement remains authoritative. The
      // wall closer may close only the current broker bucket once it is due.
      const brokerBucket = Number(a.lastBucket);
      if (Number.isFinite(brokerBucket) && cur >= brokerBucket + BUCKET_SEC && a.lastClosed < brokerBucket) {
        tryCloseBucket(a, brokerBucket, true);
      }
    }
  }, 1000);

  // ── INDEPENDENT AI LEARNING HEARTBEAT — fires every 5s regardless of STREAM ticks
  // The wall-clock closer above keeps assetData fresh; this ensures data collection
  // and labeling continue even when the Pocket Option WebSocket is quiet.
  setInterval(() => {
    if (!isRunning || !AI_LEARNING_MODE) return;
    const now = Date.now();
    if (multiAssetMode) {
      for (const name of multiScanAssets()) aiBackgroundLearnHeartbeat(name);
    } else if (activeAsset) {
      aiBackgroundLearnHeartbeat(activeAsset);
    } else if (knownAssets.size > 0) {
      // Fallback: if activeAsset was never set (no STREAM ticks yet),
      // use the first known asset from HISTORY or load-state so the
      // AI still collects data.
      for (const name of knownAssets) { aiBackgroundLearnHeartbeat(name); break; }
    }
  }, 5000);

  // ════════════════════════════════════════════════════════════
  //  INDICATORS — pure functions; fed with the expiry-TF close series
  // ════════════════════════════════════════════════════════════
  function rsi(prices, period = 14) {
    if (prices.length < period + 1) return 50;
    let g = 0, l = 0;
    for (let i = prices.length - period; i < prices.length; i++) {
      const d = prices[i] - prices[i - 1];
      if (d >= 0) g += d; else l -= d;
    }
    const ag = g / period, al = l / period;
    return al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  }

  function ema(prices, period) {
    if (!prices.length) return 0;
    if (prices.length < period) return prices[prices.length - 1];
    const k = 2 / (period + 1);
    let e = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
    for (let i = period; i < prices.length; i++) e = prices[i] * k + e * (1 - k);
    return e;
  }

  // Full EMA series (SMA seed) — needed for proper MACD signal line
  function emaSeries(prices, period) {
    const n = prices.length;
    if (!n) return [];
    const out = new Array(n).fill(NaN);
    const k = 2 / (period + 1);
    if (n < period) {
      let e = prices[0];
      out[0] = e;
      for (let i = 1; i < n; i++) {
        e = prices[i] * k + e * (1 - k);
        out[i] = e;
      }
      return out;
    }
    let e = 0;
    for (let i = 0; i < period; i++) e += prices[i];
    e /= period;
    out[period - 1] = e;
    for (let i = period; i < n; i++) {
      e = prices[i] * k + e * (1 - k);
      out[i] = e;
    }
    return out;
  }

  function atr(prices, period = 20) {
    if (prices.length < period + 1) return 0;
    let trSum = 0;
    for (let i = prices.length - period; i < prices.length; i++) {
      trSum += Math.abs(prices[i] - prices[i - 1]);
    }
    return trSum / period;
  }

  function calcStochRSI(prices, rsiPeriod = 14, stochPeriod = 14) {
    if (prices.length < rsiPeriod + stochPeriod + 2) return null;
    const rsiArr = [];
    for (let i = rsiPeriod; i <= prices.length - 1; i++) {
      rsiArr.push(rsi(prices.slice(0, i + 1), rsiPeriod));
    }
    if (rsiArr.length < stochPeriod) return null;
    const window = rsiArr.slice(-stochPeriod);
    const highRSI = Math.max(...window);
    const lowRSI  = Math.min(...window);
    if (highRSI === lowRSI) return 50;
    return ((rsiArr[rsiArr.length - 1] - lowRSI) / (highRSI - lowRSI)) * 100;
  }

  // Close-based Wilder DMI/ADX. We only have closed-price series here, so
  // directional movement is derived consistently from close-to-close movement.
  // +DI/-DI supplies direction; ADX supplies trend strength.
  function dmiAdx(closes, period = 14) {
    const n = closes.length;
    if (n < period * 2 + 1) return { adx:null, plusDI:null, minusDI:null, dx:null };
    const up = [], dn = [], tr = [];
    for (let i = 1; i < n; i++) {
      const u = closes[i] - closes[i - 1];
      const d = closes[i - 1] - closes[i];
      up.push(u > 0 && u > d ? u : 0);
      dn.push(d > 0 && d > u ? d : 0);
      tr.push(Math.max(Math.abs(u), Math.abs(d)));
    }
    let sTR = 0, sUP = 0, sDN = 0;
    for (let i = 0; i < period; i++) { sTR += tr[i]; sUP += up[i]; sDN += dn[i]; }
    const dxs = [];
    let plusDI = 0, minusDI = 0, dx = 0;
    const pushDx = () => {
      plusDI = sTR > 0 ? 100 * sUP / sTR : 0;
      minusDI = sTR > 0 ? 100 * sDN / sTR : 0;
      const den = plusDI + minusDI;
      dx = den > 0 ? 100 * Math.abs(plusDI - minusDI) / den : 0;
      dxs.push(dx);
    };
    pushDx();
    for (let i = period; i < tr.length; i++) {
      sTR = sTR - sTR / period + tr[i];
      sUP = sUP - sUP / period + up[i];
      sDN = sDN - sDN / period + dn[i];
      pushDx();
    }
    if (dxs.length < period) return { adx:null, plusDI, minusDI, dx };
    let a = dxs.slice(0, period).reduce((x, y) => x + y, 0) / period;
    for (let i = period; i < dxs.length; i++) a = (a * (period - 1) + dxs[i]) / period;
    return { adx:a, plusDI, minusDI, dx };
  }
  function adx(closes, period = 14) { return dmiAdx(closes, period).adx; }

  // 1-D Kalman on closes — separates real moves from noise.
  // q (drift) small, r (measurement noise) scales with ATR. z = innovation z-score.
  // ════════════════════════════════════════════════════════════
  //  FAST ZIGZAG SWING STRUCTURE — pivots + reversal.
  //  Confirmed ZigZag pivots can change directional bias once price
  //  has moved away from the pivot with bearish/bullish follow-through.
  // ════════════════════════════════════════════════════════════
  // V24.1.90 — hard-default ZigZag for 30s structure: 5 / 3 / 1
  const ZIGZAG_DEPTH = 5;
  const ZIGZAG_DEVIATION = 3;
  const ZIGZAG_BACKSTEP = 1;

  function swingStructureZigZag(prices, depth = ZIGZAG_DEPTH, deviation = ZIGZAG_DEVIATION, backstep = ZIGZAG_BACKSTEP) {
    // ZigZag regime engine: depth=5, deviation=3, backstep=1.
    // Confirmed swings determine the market regime; individual 30s candles do not.
    if (!prices || prices.length < depth * 2 + 3) {
      return { valid:false, upper:null, lower:null, topCount:0, botCount:0,
        lastPivot:null, prevPivot:null, pivots:[], trend:'MIXED' };
    }
    const pivots = [];
    const last = prices.length - 1;
    // V24.1.90: 5/3/1 means depth/deviation/backstep, but deviation must not
    // be treated as a literal percent of FX price.  A 3% move is enormous on
    // OTC/FX and starves the structure engine of pivots.  Scale the deviation
    // to recent ATR instead: deviation=3 => 0.30 ATR minimum swing.
    const zzAtr = Math.max(1e-12, atr(prices, Math.min(7, Math.max(2, prices.length-1))) || 0);
    const devMove = zzAtr * (Math.max(0, Number(deviation) || 3) / 10);
    for (let i = depth; i <= last - depth; i++) {
      let hi = true, lo = true;
      for (let k = 1; k <= depth; k++) {
        if (!(prices[i] >= prices[i-k] && prices[i] > prices[i+k])) hi = false;
        if (!(prices[i] <= prices[i-k] && prices[i] < prices[i+k])) lo = false;
      }
      if (!hi && !lo) continue;
      const type = hi ? 'TOP' : 'BOTTOM', price = prices[i];
      const prev = pivots[pivots.length - 1];
      if (!prev) { pivots.push({type,index:i,price}); continue; }
      if (prev.type === type) {
        if (i - prev.index <= Math.max(1, backstep) &&
            ((type === 'TOP' && price > prev.price) || (type === 'BOTTOM' && price < prev.price))) {
          pivots[pivots.length - 1] = {type,index:i,price};
        }
        continue;
      }
      const move = Math.abs(price - prev.price);
      if (move >= devMove) pivots.push({type,index:i,price});
    }
    const recent = pivots.slice(-10);
    const lastPivot = recent.length ? recent[recent.length - 1] : null;
    const prevPivot = recent.length >= 2 ? recent[recent.length - 2] : null;
    let trend = 'MIXED';
    if (recent.length >= 3) {
      const highs = recent.filter(x => x.type === 'TOP');
      const lows = recent.filter(x => x.type === 'BOTTOM');
      const hh = highs.length >= 2 && highs.at(-1).price > highs.at(-2).price;
      const hl = lows.length >= 2 && lows.at(-1).price > lows.at(-2).price;
      const lh = highs.length >= 2 && highs.at(-1).price < highs.at(-2).price;
      const ll = lows.length >= 2 && lows.at(-1).price < lows.at(-2).price;
      if (hh && hl) trend = 'TRENDING_BULL';
      else if (lh && ll) trend = 'TRENDING_BEAR';
      else if (lastPivot && prevPivot) {
        if (lastPivot.type === 'BOTTOM' && lastPivot.price > prevPivot.price) trend = 'BULLISH';
        else if (lastPivot.type === 'TOP' && lastPivot.price < prevPivot.price) trend = 'BEARISH';
      }
    }
    const highs = recent.filter(x => x.type === 'TOP');
    const lows = recent.filter(x => x.type === 'BOTTOM');
    const upper = highs.length ? highs.at(-1).price : null;
    const lower = lows.length ? lows.at(-1).price : null;
    return { valid:recent.length >= 2,
      upper, lower,
      topCount:highs.length, botCount:lows.length, topR2:null, botR2:null,
      lastPivot, prevPivot, pivots:recent, trend, depth, deviation, backstep };
  }

  // ════════════════════════════════════════════════════════════
  //  STRATEGY — MURFS PICK (three independent modes: Runner · Reversal · No Trade)
  // ════════════════════════════════════════════════════════════
  // V24.1.262: live-only startup now requires 100 closed 5s candles.
  // A successful Pocket Option history or visible-chart backfill counts as market
  // context immediately; it is not forced to collect 100 NEW live candles.
  // Primary/secondary/all-plan TF minimums still apply, so a tiny/invalid seed
  // cannot bypass indicator readiness.
  function v241WarmupTarget(a, base=50) {
    const normal=Math.max(1,Number(base)||50);
    const seed=a?.__historyBackfill;
    const seeded=Number(seed?.buckets||0);
    if(seed && seeded>=12) return Math.max(12,Math.min(normal,seeded));
    return normal;
  }

  const STRATEGIES = {

    'Murfs Pick': {
      minPrices: 50,
      desc: 'Murfs Pick v24.1.81 — 30–60s adaptive stack: EMA5/9/21 · RSI7 · StochRSI7 · MACD5/13/6 · ADX/DMI7 · ATR7 · BB14/2',
      fn(a, slow, basket) {
        const p = a.prices;
        if (p.length < 8) return { dir: null, reason: 'Building series ' + p.length + '/8' };

        const last = p[p.length - 1];
        const prev = p[p.length - 2];
        const prev2 = p[p.length - 3];

        // Shared basics (both modes need price + ATR for filters)
        const atrV = atr(p, 7);
        if (atrV <= 0) return { dir: null, reason: 'Dead market · NO TRADE' };
        // Long ATR baseline for volatility-regime comparison. This must be
        // initialized before volRatio is calculated later in indicator context.
        // Fall back to the fast ATR while the longer window is still warming.
        const atrLongRaw = p.length >= 21 ? atr(p, 20) : atrV;
        const atrLong = Number.isFinite(atrLongRaw) && atrLongRaw > 0 ? atrLongRaw : atrV;

        // ADX is a PRIMARY-TF indicator. Define it before any regime/gate
        // logic that references adxV. Never derive ADX from the 5s basket.
        const dmi = dmiAdx(p, 7);
        const adxV = dmi.adx;
        const plusDI = Number(dmi.plusDI || 0);
        const minusDI = Number(dmi.minusDI || 0);
        const dmiBull = plusDI > minusDI + 3;
        const dmiBear = minusDI > plusDI + 3;
        const dmiStrong = adxV != null && adxV >= 24;

        // Kalman trend estimate — calculated from the PRIMARY indicator timeframe.
        // 5s basket data is intentionally not used here.
        const kalR = Math.max((atrV * 0.20) ** 2, Number.EPSILON);
        const kalQ = Math.max((atrV * 0.05) ** 2, Number.EPSILON);
        // V24.1.56: Kalman removed from trading authority.
        const e5  = ema(p, 5);
        const e9 = ema(p, 9);
        const e21 = ema(p, 21);
        // V24.1.57b: initialize EMA-stack state at the first possible point.
        // Use var deliberately here to eliminate temporal-dead-zone failures
        // even if surrounding strategy/context code takes an alternate path.
        var emaStackBull = e5 > e9 && e9 > e21;
        var emaStackBear = e5 < e9 && e9 < e21;
        // Chop veto REMOVED (v7 fixes) — it was a global early-return that
        // killed reversals in their best environment (tight range). Runner
        // gates already reject chop via emaSpreadOk/regTrend; reversals now
        // score normally and rely on band-extreme + RSI + persistence.
        const emaSpread = atrV > 0 ? Math.abs(e5 - e21) / atrV : 0;

        Object.assign(lastIndicators, { atr: atrV, ema5: e5, ema9: e9, ema21: e21, emaSpread });

        // V24.1.81 fast Bollinger context for 30–60s: BB(14,2).
        // Location only — bands never issue a trade by themselves.
        let bbMid=null, bbUpper=null, bbLower=null, bbWidthAtr=0, bbPos=0;
        if (p.length >= 14) {
          const bw=p.slice(-14), mid=bw.reduce((x,y)=>x+y,0)/bw.length;
          const variance=bw.reduce((x,y)=>x+(y-mid)*(y-mid),0)/bw.length;
          const sd=Math.sqrt(Math.max(0,variance));
          bbMid=mid; bbUpper=mid+2*sd; bbLower=mid-2*sd;
          bbWidthAtr=atrV>0?(bbUpper-bbLower)/atrV:0;
          bbPos=(bbUpper>bbLower)?((last-bbLower)/(bbUpper-bbLower)):0.5;
        }
        Object.assign(lastIndicators,{bollMid:bbMid,bollUpper:bbUpper,bollLower:bbLower,bbWidthAtr,bbPos,
          bbNearLower:bbLower!=null && last<=bbLower+atrV*0.12,
          bbNearUpper:bbUpper!=null && last>=bbUpper-atrV*0.12});

        // ── v19.0.0: extra indicator fields for trade type classifier ──
        // RSI(30) — wider lookback for reversal detection
        lastIndicators.rsi30 = p.length >= 31 ? rsi(p, 30) : (lastIndicators.slowRSI || 50);
        // EMA deviation: how far price is from EMA21 in ATR units
        lastIndicators.emaDeviation = (atrV > 0 && e21) ? ((last - e21) / atrV) : 0;
        // Momentum acceleration: Kalman slope change (2nd derivative)
        // Candle streak: consecutive closes in same direction
        let streak = 0, streakDir = 0;
        for (let i = p.length - 1; i >= Math.max(1, p.length - 5); i--) {
          const d = p[i] > (p[i-1] || p[i]) ? 1 : (p[i] < (p[i-1] || p[i]) ? -1 : 0);
          if (d !== 0 && (streakDir === 0 || d === streakDir)) { streak++; streakDir = d; }
          else if (d !== 0) break;
          else streakDir = 0;
        }
        lastIndicators.candleStreak = streak > 0 ? streakDir * streak : 0;

        const priceUp   = last > prev;
        const priceDown = last < prev;

        // Slow TF RSI — shared veto only (blocks hard-against trades)
        let slowRSI = 50;
        if (slow && slow.prices && slow.prices.length >= 3) {
          slowRSI = rsi(slow.prices, 9);
          lastIndicators.slowRSI = slowRSI;
        }
        // slowBlocks computed after nearExhaust/chase (extreme + extension only)

        // ═══════════════════════════════════════════════════════════
        //  MODE 1 — RUNNER (trend follow)
        //  Indicators: EMA5/9/21 · DMI/ADX · MACD5/13/6 · RSI slope · ATR7 · ZigZag structure
        //  NO RSI, NO Bollinger, NO Keltner, NO StochRSI
        // ═══════════════════════════════════════════════════════════
        let runnerBuy = 0, runnerSell = 0;
        const runBuyReasons = [], runSellReasons = [];
        let runBuyConf = 0, runSellConf = 0;

        // V24.1.56 — lean indicator stack. Regression/Kalman no longer have
        // trading authority. Trend location/extension is measured with EMA + ATR.
        const aboveMid = last > e9;
        const belowMid = last < e9;
        // EMA-stack state was initialized immediately after EMA5/9/21 above.
        const emaDeviationNow = atrV > 0 ? (last - e21) / atrV : 0;
        const coreTrendUp = emaStackBull;
        const coreTrendDown = emaStackBear;
        const chaseBuy = emaDeviationNow >= 2.0;
        const chaseSell = emaDeviationNow <= -2.0;
        const nearExhaustBuy = !chaseBuy && emaDeviationNow >= 1.55;
        const nearExhaustSell = !chaseSell && emaDeviationNow <= -1.55;

        // Slow-TF RSI is only a directional veto. It does not become a
        // primary indicator and it is never sourced from the 5s basket.
        const slowBlocksBuy = (slowRSI >= 82);
        const slowBlocksSell = (slowRSI <= 18);

        // MACD 5/13/6 — full series signal
        const emaFastS = emaSeries(p, 5);
        const emaSlowS = emaSeries(p, 13);
        const macdSeries = [];
        for (let i = 0; i < p.length; i++) {
          const f = emaFastS[i], s = emaSlowS[i];
          macdSeries.push((isNaN(f) || isNaN(s)) ? NaN : f - s);
        }
        const macdValid = macdSeries.filter(x => !isNaN(x));
        const sigSeries = emaSeries(macdValid, 6);
        const macd = macdValid.length ? macdValid[macdValid.length - 1] : 0;
        const macdP = macdValid.length > 1 ? macdValid[macdValid.length - 2] : macd;
        const macdP2 = macdValid.length > 2 ? macdValid[macdValid.length - 3] : macdP;
        const macdSignal = sigSeries.length && !isNaN(sigSeries[sigSeries.length - 1])
          ? sigSeries[sigSeries.length - 1] : macd;
        const macdAboveZero = macd > 0;
        const macdBelowZero = macd < 0;
        const macdAboveSignal = macd > macdSignal;
        const macdBelowSignal = macd < macdSignal;
        // Stronger step — ignore lower-TF noise
        const macdStep = atrV * 0.015;
        const macdRising  = macd > macdP + macdStep && macdP >= macdP2;
        const macdFalling = macd < macdP - macdStep && macdP <= macdP2;
        // Full triple MACD still scores bonus; hard gate uses softer support
        const macdBullAligned = macdAboveZero && macdRising && macdAboveSignal;
        const macdBearAligned = macdBelowZero && macdFalling && macdBelowSignal;
        const macdBullSupport = macdAboveSignal || (macdAboveZero && macdRising);
        const macdBearSupport = macdBelowSignal || (macdBelowZero && macdFalling);
        // MACD acceleration: second derivative. Positive means bullish momentum
        // is strengthening; negative means bearish momentum is strengthening.
        const macdAccel = (macd - macdP) - (macdP - macdP2);
        const macdAccelNorm = atrV > 0 ? macdAccel / atrV : 0;
        const macdBullAccel = macdAccelNorm > 0.008;
        const macdBearAccel = macdAccelNorm < -0.008;

        // EMA stack was defined above before core trend/context references.
        const emaSpreadOk  = emaSpread >= 0.20; // balanced: reject only very flat EMA stacks
        const twoBull = last > prev && prev > prev2;
        const twoBear = last < prev && prev < prev2;

        // RSI dynamics for regime-aware interpretation. An extreme by itself
        // is not a reversal signal in a strong trend.
        const runnerRsi = rsi(p, 7);
        const runnerRsiPrev = p.length > 8 ? rsi(p.slice(0,-1), 7) : runnerRsi;
        const runnerRsiSlope = runnerRsi - runnerRsiPrev;
        const rsiMomentumBull = runnerRsi >= 52 && runnerRsiSlope > 0.8;
        const rsiMomentumBear = runnerRsi <= 48 && runnerRsiSlope < -0.8;
        const rsi5Back = p.length >= 13 ? rsi(p.slice(0,-5), 7) : runnerRsi;
        const price5Back = p.length >= 6 ? p[p.length-6] : last;
        const bearishRsiDivergence = last > price5Back + atrV*0.15 && runnerRsi < rsi5Back - 3;
        const bullishRsiDivergence = last < price5Back - atrV*0.15 && runnerRsi > rsi5Back + 3;

        // Secondary-TF timing. 30s expiry uses 15s; 60s expiry uses 30s.
        // Raw 5s basket data is never used for indicators or entry decisions.
        const confirmP = (slow && slow.prices && slow.prices.length >= 3)
          ? slow.prices : p;
        const cLast = confirmP[confirmP.length - 1];
        const cPrev = confirmP[confirmP.length - 2];
        const cPrev2 = confirmP[confirmP.length - 3];

        const confirmEma5 = ema(confirmP, 5);
        const confirmEma9 = ema(confirmP, 9);
        const confirmEma21 = ema(confirmP, 21);
        const confirmEmaBull = confirmEma5 > confirmEma9 && confirmEma9 > confirmEma21;
        const confirmEmaBear = confirmEma5 < confirmEma9 && confirmEma9 < confirmEma21;

        const confirmRsi = confirmP.length >= 8 ? rsi(confirmP, 7) : 50;
        const confirmRsiPrev = confirmP.length >= 9
          ? rsi(confirmP.slice(0, -1), 7) : confirmRsi;
        const confirmRsiUp = confirmRsi > confirmRsiPrev && (confirmRsi-confirmRsiPrev) >= 1.0;
        const confirmRsiDown = confirmRsi < confirmRsiPrev && (confirmRsiPrev-confirmRsi) >= 1.0;
        const confirmBull2 = cLast > cPrev && cPrev > cPrev2;
        const confirmBear2 = cLast < cPrev && cPrev < cPrev2;

        // V24.1.98: calculate the FULL paired fast-timeframe stack independently.
        // For a 30s expiry confirmP is the live 15s series. The 30s primary
        // still decides market direction; this stack exists to improve WHEN
        // the entry is taken, not to replace the primary setup.
        const confirmDmi = dmiAdx(confirmP, 7);
        const confirmAdx = confirmDmi.adx;
        const confirmPlusDI = Number(confirmDmi.plusDI || 0);
        const confirmMinusDI = Number(confirmDmi.minusDI || 0);
        const confirmDmiBull = confirmPlusDI > confirmMinusDI + 3;
        const confirmDmiBear = confirmMinusDI > confirmPlusDI + 3;

        const cFastSeries = emaSeries(confirmP, 5);
        const cSlowSeries = emaSeries(confirmP, 13);
        const cMacdSeries = [];
        for (let i = 0; i < confirmP.length; i++) {
          const f = cFastSeries[i], sl = cSlowSeries[i];
          cMacdSeries.push((isNaN(f) || isNaN(sl)) ? NaN : f - sl);
        }
        const cMacdValid = cMacdSeries.filter(x => !isNaN(x));
        const cSignalSeries = emaSeries(cMacdValid, 6);
        const confirmMacd = cMacdValid.length ? cMacdValid.at(-1) : 0;
        const confirmMacdPrev = cMacdValid.length > 1 ? cMacdValid.at(-2) : confirmMacd;
        const confirmMacdSignal = cSignalSeries.length && !isNaN(cSignalSeries.at(-1))
          ? cSignalSeries.at(-1) : confirmMacd;
        const confirmMacdBull = confirmMacd > confirmMacdSignal && confirmMacd >= confirmMacdPrev;
        const confirmMacdBear = confirmMacd < confirmMacdSignal && confirmMacd <= confirmMacdPrev;

        let confirmBbMid=null, confirmBbUpper=null, confirmBbLower=null, confirmBbPos=0.5;
        if (confirmP.length >= 14) {
          const cbw=confirmP.slice(-14), cm=cbw.reduce((x,y)=>x+y,0)/cbw.length;
          const cv=cbw.reduce((x,y)=>x+(y-cm)*(y-cm),0)/cbw.length;
          const cs=Math.sqrt(Math.max(0,cv));
          confirmBbMid=cm; confirmBbUpper=cm+2*cs; confirmBbLower=cm-2*cs;
          confirmBbPos=confirmBbUpper>confirmBbLower ? (cLast-confirmBbLower)/(confirmBbUpper-confirmBbLower) : 0.5;
        }
        const confirmBbBullOk = confirmBbMid == null || cLast >= confirmBbMid || confirmBbPos <= 0.35;
        const confirmBbBearOk = confirmBbMid == null || cLast <= confirmBbMid || confirmBbPos >= 0.65;

        // Six independent fast categories: price action, EMA 5/9/21, RSI7,
        // MACD 5/13/6, DMI/ADX7 and Bollinger 14/2 location. We deliberately
        // do not require all six; 15s is a timing layer, not a new strict gate.
        const confirmBullVotes =
          (confirmBull2 ? 1 : 0) +
          (confirmEmaBull || (cLast > confirmEma5 && confirmEma5 >= confirmEma9) ? 1 : 0) +
          (confirmRsiUp ? 1 : 0) +
          (confirmMacdBull ? 1 : 0) +
          (confirmDmiBull ? 1 : 0) +
          (confirmBbBullOk ? 1 : 0);

        const confirmBearVotes =
          (confirmBear2 ? 1 : 0) +
          (confirmEmaBear || (cLast < confirmEma5 && confirmEma5 <= confirmEma9) ? 1 : 0) +
          (confirmRsiDown ? 1 : 0) +
          (confirmMacdBear ? 1 : 0) +
          (confirmDmiBear ? 1 : 0) +
          (confirmBbBearOk ? 1 : 0);

        const confirmBullStack = confirmBullVotes >= 4 && confirmBullVotes >= confirmBearVotes + 2;
        const confirmBearStack = confirmBearVotes >= 4 && confirmBearVotes >= confirmBullVotes + 2;

        const zzConfirm = swingStructureZigZag(confirmP);
        const confirmAtr = confirmP.length >= 8 ? atr(confirmP, 7) : atrV;
        const zzTop = zzConfirm.valid && zzConfirm.upper != null &&
          cLast >= zzConfirm.upper - confirmAtr * 0.20;
        const zzBottom = zzConfirm.valid && zzConfirm.lower != null &&
          cLast <= zzConfirm.lower + confirmAtr * 0.20;

        // IMPORTANT: a confirmed ZigZag TOP/BOTTOM is a structural
        // reversal candidate, not merely an exhaustion warning.
        // Wait for price to move away from the confirmed pivot and
        // require directional follow-through before flipping bias.
        const zzPivot = zzConfirm.lastPivot;
        const zzPrevPivot = zzConfirm.prevPivot;
        const zzPivotAge = zzPivot ? (confirmP.length - 1 - zzPivot.index) : Infinity;
        const zzStructuralBull = zzConfirm.trend === 'TRENDING_BULL' || zzConfirm.trend === 'BULLISH';
        const zzStructuralBear = zzConfirm.trend === 'TRENDING_BEAR' || zzConfirm.trend === 'BEARISH';
        const zzBearFlip =
          !!zzPivot &&
          zzPivot.type === 'TOP' &&
          zzPivotAge >= 2 &&
          cLast < zzPivot.price - confirmAtr * 0.10 &&
          (confirmBearVotes >= 3 || confirmBear2);
        const zzBullFlip =
          !!zzPivot &&
          zzPivot.type === 'BOTTOM' &&
          zzPivotAge >= 2 &&
          cLast > zzPivot.price + confirmAtr * 0.10 &&
          (confirmBullVotes >= 3 || confirmBull2);

        const confirmBearReversal =
          zzBearFlip ||
          (confirmBearVotes >= 4 &&
            (zzTop || confirmBear2 || (cLast < confirmEma5 && cLast < confirmEma9)));
        const confirmBullReversal =
          zzBullFlip ||
          (confirmBullVotes >= 4 &&
            (zzBottom || confirmBull2 || (cLast > confirmEma5 && cLast > confirmEma9)));

        const freshBullResume =
          cLast > cPrev && cPrev <= cPrev2 && cLast > confirmEma5;
        const freshBearResume =
          cLast < cPrev && cPrev >= cPrev2 && cLast < confirmEma5;

        // New trend detection: primary + paired secondary TF only.
        const primaryBullStep =
          last > prev && prev >= prev2 && last > e5 && macdBullSupport;
        const primaryBearStep =
          last < prev && prev <= prev2 && last < e5 && macdBearSupport;

        const transitionBull =
          emaStackBull && primaryBullStep &&
          confirmBullVotes >= 2 && cLast > confirmEma5 &&
          !confirmBearReversal;

        const transitionBear =
          emaStackBear && primaryBearStep &&
          confirmBearVotes >= 2 && cLast < confirmEma5 &&
          !confirmBullReversal;

        // Hard stale-direction lock: once both TFs align, the old
        // opposite signal is no longer eligible.
        const directionalBullLock =
          !zzBearFlip &&
          emaStackBull && dmiBull && macdBullSupport &&
          confirmBullVotes >= 2 && cLast > confirmEma5 &&
          !confirmBearReversal;

        const directionalBearLock =
          !zzBullFlip &&
          emaStackBear && dmiBear && macdBearSupport &&
          confirmBearVotes >= 2 && cLast < confirmEma5 &&
          !confirmBullReversal;

        // Structural ZigZag bias has priority over stale trend indicators.
        // Once a TOP has broken bearish, BUY setup logic is disabled until
        // a confirmed BOTTOM breaks bullish (and vice versa).
        const zzBearBias = zzBearFlip || (zzStructuralBear && !zzBullFlip);
        const zzBullBias = zzBullFlip || (zzStructuralBull && !zzBearFlip);

        // v24.1.37 — ZigZag CONTINUATION patterns for RUNNER entries.
        // BUY: rising swing highs + rising swing lows, then price resumes up
        //      from the most recent confirmed BOTTOM (HH -> HL -> continuation).
        // SELL: falling swing lows + falling swing highs, then price resumes down
        //       from the most recent confirmed TOP (LL -> LH -> continuation).
        const zzRecent = Array.isArray(zzConfirm.pivots) ? zzConfirm.pivots : [];
        const zzHighs = zzRecent.filter(x => x && x.type === 'TOP');
        const zzLows  = zzRecent.filter(x => x && x.type === 'BOTTOM');
        const zzHH = zzHighs.length >= 2 && zzHighs.at(-1).price > zzHighs.at(-2).price;
        const zzHL = zzLows.length  >= 2 && zzLows.at(-1).price  > zzLows.at(-2).price;
        const zzLH = zzHighs.length >= 2 && zzHighs.at(-1).price < zzHighs.at(-2).price;
        const zzLL = zzLows.length  >= 2 && zzLows.at(-1).price  < zzLows.at(-2).price;
        const zzLastBottom = zzLows.length ? zzLows.at(-1) : null;
        const zzLastTop = zzHighs.length ? zzHighs.at(-1) : null;
        const zzBullContinuation =
          zzHH && zzHL && !!zzLastBottom &&
          cLast > zzLastBottom.price + confirmAtr * 0.18 &&
          cLast > confirmEma5 && confirmBullVotes >= 2 &&
          !confirmBearReversal;
        const zzBearContinuation =
          zzLL && zzLH && !!zzLastTop &&
          cLast < zzLastTop.price - confirmAtr * 0.18 &&
          cLast < confirmEma5 && confirmBearVotes >= 2 &&
          !confirmBullReversal;

        // Strong continuation can establish runner direction even while slower
        // trend labels are still catching up. It does NOT bypass
        // chase, market-ban, loss-memory or opposite-direction safety locks.
        const zzRunnerBull = zzBullContinuation && !zzBearBias;
        const zzRunnerBear = zzBearContinuation && !zzBullBias;

        // Entry confirmation is entirely timeframe-paired:
        // 30s expiry -> 30s primary + 15s secondary.
        // 60s expiry -> 60s primary + 30s secondary.
        // The current LIVE secondary-TF candle must confirm direction.
        const secondaryBullConfirm =
          (freshBullResume || confirmBullStack) &&
          confirmBullVotes >= 3 &&
          !confirmBearReversal &&
          !confirmBearStack;
        const secondaryBearConfirm =
          (freshBearResume || confirmBearStack) &&
          confirmBearVotes >= 3 &&
          !confirmBullReversal &&
          !confirmBullStack;

        const runnerBullTiming = secondaryBullConfirm || zzRunnerBull;
        const runnerBearTiming = secondaryBearConfirm || zzRunnerBear;

        lastIndicators.runnerConfirm = {
          primaryTF: a.__tfKey || null,
          secondaryTF: a.__slowKey || null,
          confirmed: runnerBullTiming ? 'BUY' : runnerBearTiming ? 'SELL' : null,
          checkedEvery: '5s',
          livePrimary: true,
          liveSecondary: true,
          bullVotes: confirmBullVotes,
          bearVotes: confirmBearVotes,
          fastStack: confirmBullStack ? 'BUY' : confirmBearStack ? 'SELL' : 'NEUTRAL',
          ema521: confirmEmaBull ? 'BUY' : confirmEmaBear ? 'SELL' : 'MIXED',
          macd5136: confirmMacdBull ? 'BUY' : confirmMacdBear ? 'SELL' : 'MIXED',
          rsi7: confirmRsi,
          adx7: confirmAdx,
          plusDI7: confirmPlusDI,
          minusDI7: confirmMinusDI,
          bb14Pos: confirmBbPos
        };

        Object.assign(lastIndicators, {
          confirmBullVotes, confirmBearVotes,
          confirmBullStack, confirmBearStack,
          confirmEma5, confirmEma9, confirmEma21,
          confirmRsi, confirmAdx, confirmPlusDI, confirmMinusDI,
          confirmMacd, confirmMacdSignal, confirmBbPos,
          confirmBullReversal, confirmBearReversal,
          zzConfirmValid: zzConfirm.valid,
          zzConfirmUpper: zzConfirm.upper,
          zzConfirmLower: zzConfirm.lower,
          zzConfirmTop: zzTop,
          zzConfirmBottom: zzBottom,
          zzLastPivot: zzPivot,
          zzPivotAge: Number.isFinite(zzPivotAge) ? zzPivotAge : null,
          zzBearFlip,
          zzBullFlip,
          zzHH, zzHL, zzLH, zzLL,
          zzBullContinuation,
          zzBearContinuation,
          zzRunnerBull,
          zzRunnerBear,
          transitionBull,
          transitionBear,
          directionalBullLock,
          directionalBearLock
        });

        const volRatio   = atrV / atrLong;
        const trendScore = (adxV !== null && adxV >= 25) || emaSpread >= 0.35;
        const rangeScore = (adxV !== null && adxV < 20) && emaSpread < 0.30;

        // Regime classification is informational and must recognize an
        // established trend even when the stricter *entry transition*
        // conditions have not fired on this exact bar. Previously, a bull run
        // could display MIXED simply because transitionBull required a very
        // specific one-bar sequence (including secondary-TF votes). That made
        // the dashboard disagree with the actual market structure.
        //
        // Use several independent primary-TF trend clues: EMA stack, DMI/MACD
        // slope/fit, price location, and Kalman slope. Do not require ADX or a
        // transition event just to label an already-established trend.
        // Live trend-integrity check.  A broad trend regime can lag
        // a fast reversal by several bars.  Do not keep calling the market
        // TRENDING_BULL/TRENDING_BEAR when the paired live timeframe is
        // already breaking the other way.
        const liveBearBreak =
          cLast < confirmEma5 &&
          confirmBearVotes >= 3 &&
          (primaryBearStep || confirmBearReversal || confirmBear2);

        const liveBullBreak =
          cLast > confirmEma5 &&
          confirmBullVotes >= 3 &&
          (primaryBullStep || confirmBullReversal || confirmBull2);

        // Store live trend-integrity only after both break variables exist.
        // This avoids the temporal-dead-zone ReferenceError that previously
        // aborted indicator evaluation before regime/TQS/MQ could finish.
        Object.assign(lastIndicators, {
          liveBullBreak,
          liveBearBreak,
          trendIntegrity: liveBearBreak ? 'BULL_BREAKING_BEAR' : liveBullBreak ? 'BEAR_BREAKING_BULL' : 'INTACT'
        });

        const clearBullStructure =
          emaStackBull && dmiBull && !liveBearBreak &&
          (macdBullSupport || runnerRsiSlope > 0);

        const clearBearStructure =
          emaStackBear && dmiBear && !liveBullBreak &&
          (macdBearSupport || runnerRsiSlope < 0);

        let regime = 'MIXED';
        if (volRatio >= 1.8 && adxV !== null && adxV < 18) {
          regime = 'CHAOTIC';
        } else if (liveBearBreak && !liveBullBreak) {
          // A fast bearish break invalidates a stale bullish label immediately.
          // Only call it a full bear trend once the primary structure agrees;
          // otherwise show MIXED while the reversal is developing.
          regime = (emaStackBear || transitionBear || zzBearFlip) ? 'TRENDING_BEAR' : 'MIXED';
        } else if (liveBullBreak && !liveBearBreak) {
          regime = (emaStackBull || transitionBull || zzBullFlip) ? 'TRENDING_BULL' : 'MIXED';
        } else if (clearBullStructure && !clearBearStructure) {
          regime = 'TRENDING_BULL';
        } else if (clearBearStructure && !clearBullStructure) {
          regime = 'TRENDING_BEAR';
        } else if (transitionBull && !transitionBear) {
          regime = 'TRENDING_BULL';
        } else if (transitionBear && !transitionBull) {
          regime = 'TRENDING_BEAR';
        } else if (trendScore && !rangeScore) {
          regime = emaStackBull ? 'TRENDING_BULL' : emaStackBear ? 'TRENDING_BEAR' : 'TRENDING';
        } else if (rangeScore && !trendScore) {
          regime = 'RANGING';
        }
        lastIndicators.regime = regime;
        Object.assign(lastIndicators, {
          adx: adxV, plusDI, minusDI, dmiBull, dmiBear,
          macdAccel: macdAccelNorm, rsiSlope: runnerRsiSlope,
          bearishRsiDivergence, bullishRsiDivergence
        });

        if (regime === 'CHAOTIC') {
          return { dir: null, reason: 'CHAOTIC · vol ↑ no trend · NO TRADE' };
        }
        // Move size: last bar must be a real step, not a tick
        // Raw-bar move filter REMOVED (v7) — Kalman noise-filtered slope replaces it

        // V24.1.50 FAST STRUCTURE BREAK / REJECTION
        // Reacts to the live primary-TF candle before slower EMA/regime labels catch up.
        // A sharp opposite displacement through the recent micro swing invalidates the
        // stale runner direction for ~one expiry, while allowing the opposite reversal
        // side to be evaluated normally.
        const fastStruct = a.__fastStructureState || (a.__fastStructureState = {
          blockBuyUntil:0, blockSellUntil:0, lastBearAt:0, lastBullAt:0
        });
        const curOpen = Number(a.open || prev || last);
        const curHigh = Number(a.high || Math.max(curOpen,last));
        const curLow  = Number(a.low  || Math.min(curOpen,last));
        const curClose= Number(a.lastClose || last);
        const prevMicro = p.slice(Math.max(0,p.length-7), Math.max(0,p.length-1));
        const recentMicroHigh = prevMicro.length ? Math.max(...prevMicro) : prev;
        const recentMicroLow  = prevMicro.length ? Math.min(...prevMicro) : prev;
        const bodyAtr = atrV > 0 ? Math.abs(curClose-curOpen)/atrV : 0;
        const bearBodyAtr = atrV > 0 ? (curOpen-curClose)/atrV : 0;
        const bullBodyAtr = atrV > 0 ? (curClose-curOpen)/atrV : 0;
        const upperWickAtr = atrV > 0 ? (curHigh-Math.max(curOpen,curClose))/atrV : 0;
        const lowerWickAtr = atrV > 0 ? (Math.min(curOpen,curClose)-curLow)/atrV : 0;
        const microBreakDown = curClose < recentMicroLow - atrV*0.05 || (p.length>=4 && curClose < Math.min(p[p.length-2],p[p.length-3]));
        const microBreakUp   = curClose > recentMicroHigh + atrV*0.05 || (p.length>=4 && curClose > Math.max(p[p.length-2],p[p.length-3]));
        const rejectedRecentHigh = curHigh >= recentMicroHigh - atrV*0.18 && curClose < curOpen && (upperWickAtr>=0.18 || bearBodyAtr>=0.55);
        const rejectedRecentLow  = curLow  <= recentMicroLow  + atrV*0.18 && curClose > curOpen && (lowerWickAtr>=0.18 || bullBodyAtr>=0.55);
        const fastBearBreak = bearBodyAtr >= 0.50 && (microBreakDown || rejectedRecentHigh);
        const fastBullBreak = bullBodyAtr >= 0.50 && (microBreakUp || rejectedRecentLow);
        const fastBlockMs = Math.max(15000, Math.round((parseInt(botConfig?.timeframe||30,10))*850));
        if (fastBearBreak && Date.now()-fastStruct.lastBearAt > 4000) {
          fastStruct.blockBuyUntil = Date.now()+fastBlockMs; fastStruct.lastBearAt=Date.now();
        }
        if (fastBullBreak && Date.now()-fastStruct.lastBullAt > 4000) {
          fastStruct.blockSellUntil = Date.now()+fastBlockMs; fastStruct.lastBullAt=Date.now();
        }
        const fastBuyInvalidated = fastStruct.blockBuyUntil > Date.now();
        const fastSellInvalidated = fastStruct.blockSellUntil > Date.now();
        Object.assign(lastIndicators,{fastBearBreak,fastBullBreak,fastBuyInvalidated,fastSellInvalidated,fastBodyAtr:bodyAtr});

        // V24.1.56 PRICE-STRUCTURE BACKBONE
        // Direction is driven by swing sequence + EMA/DMI/MACD and fresh structure breaks.
        // This is deliberately faster than the old indicator-heavy
        // regime label so an obvious LH/LL sequence cannot remain TRENDING_BULL.
        let structureBullScore = 0, structureBearScore = 0;
        if (zzHH) structureBullScore += 2;
        if (zzHL) structureBullScore += 2;
        if (zzLH) structureBearScore += 2;
        if (zzLL) structureBearScore += 2;
        if (emaStackBull) structureBullScore += 1;
        if (emaStackBear) structureBearScore += 1;
        if (macdBullSupport) structureBullScore += 1;
        if (macdBearSupport) structureBearScore += 1;
        if (dmiBull) structureBullScore += dmiStrong ? 2 : 1;
        if (dmiBear) structureBearScore += dmiStrong ? 2 : 1;
        if (transitionBull || zzBullFlip || liveBullBreak) structureBullScore += 2;
        if (transitionBear || zzBearFlip || liveBearBreak) structureBearScore += 2;
        if (fastBullBreak) structureBullScore += 3;
        if (fastBearBreak) structureBearScore += 3;
        const structureMargin = structureBullScore - structureBearScore;
        const structureTotal = Math.max(1, structureBullScore + structureBearScore);
        let structureConfidence = Math.min(1, Math.abs(structureMargin) / Math.max(3, structureTotal * 0.60));
        let structureDirection = 'NEUTRAL';
        if (structureMargin >= 2 && structureBullScore >= 3) structureDirection = 'BUY';
        else if (structureMargin <= -2 && structureBearScore >= 3) structureDirection = 'SELL';
        // If pivots lag, EMA + DMI + MACD can resolve neutral structure.
        if (structureDirection === 'NEUTRAL' && emaStackBull && dmiBull && macdBullSupport && !fastBuyInvalidated) {
          structureDirection='BUY'; structureBullScore=Math.max(structureBullScore,4);
        } else if (structureDirection === 'NEUTRAL' && emaStackBear && dmiBear && macdBearSupport && !fastSellInvalidated) {
          structureDirection='SELL'; structureBearScore=Math.max(structureBearScore,4);
        }
        if (structureDirection!=='NEUTRAL') {
          const sm=structureBullScore-structureBearScore, st=Math.max(1,structureBullScore+structureBearScore);
          structureConfidence=Math.max(structureConfidence,Math.min(1,Math.abs(sm)/Math.max(3,st*0.60)));
        }

        // Strong price structure is allowed to correct a lagging informational
        // regime immediately. Full HH+HL or LH+LL earns the trend label directly;
        // otherwise a high score produces TRENDING only when the opposite side is weak.
        if (structureDirection === 'BUY' && !fastBuyInvalidated && (zzHH && zzHL || structureBullScore >= 6)) regime = 'TRENDING_BULL';
        else if (structureDirection === 'SELL' && !fastSellInvalidated && (zzLH && zzLL || structureBearScore >= 6)) regime = 'TRENDING_BEAR';
        else if (structureDirection === 'BUY' && regime === 'TRENDING_BEAR' && structureBullScore >= structureBearScore + 3) regime = 'MIXED';
        else if (structureDirection === 'SELL' && regime === 'TRENDING_BULL' && structureBearScore >= structureBullScore + 3) regime = 'MIXED';

        // V24.1.56 PULLBACK / REVERSAL CANDLE MAP
        // 1-2 opposite candles are a pullback until they break the last with-trend
        // candle high/low. No regression channel is used anywhere in this decision.
        const rateKeys=Object.keys(a.rates||{}).map(Number).filter(Number.isFinite).sort((x,y)=>x-y);
        const closedPrimary=rateKeys.slice(-5).map(k=>a.rates[k]).filter(c=>Array.isArray(c)&&c.length>=4);
        const livePrimary=[curOpen,curHigh,curLow,curClose,Date.now()/1000];
        const cBull=c=>c&&Number(c[3])>Number(c[0]);
        const cBear=c=>c&&Number(c[3])<Number(c[0]);
        const cBody=c=>c?Math.abs(Number(c[3])-Number(c[0])):0;
        const trendForPattern=structureDirection==='BUY'||structureDirection==='SELL'?structureDirection:(regime==='TRENDING_BULL'?'BUY':regime==='TRENDING_BEAR'?'SELL':'NEUTRAL');
        let counterPullbackCount=0, pullbackBodySum=0, pullbackAnchor=null;
        if(trendForPattern!=='NEUTRAL') {
          const counterFn=trendForPattern==='BUY'?cBear:cBull;
          for(let i=closedPrimary.length-1;i>=0&&counterPullbackCount<3;i--){
            const c=closedPrimary[i];
            if(counterFn(c)){ counterPullbackCount++; pullbackBodySum+=cBody(c); }
            else { pullbackAnchor=c; break; }
          }
          const liveCounter=counterFn(livePrimary);
          if(liveCounter){ counterPullbackCount=Math.min(3,counterPullbackCount+1); pullbackBodySum+=cBody(livePrimary); }
        }
        if(!pullbackAnchor && closedPrimary.length) pullbackAnchor=closedPrimary[Math.max(0,closedPrimary.length-counterPullbackCount-1)]||closedPrimary[0];
        const anchorBody=Math.max(cBody(pullbackAnchor),atrV*0.12,1e-9);
        const avgPullbackBody=counterPullbackCount?(pullbackBodySum/counterPullbackCount):0;
        // Compatibility ratio: average pullback body vs anchor body.
        const pullbackBodyRatio=counterPullbackCount?Math.min(3,avgPullbackBody/anchorBody):0;
        // V24.1.139: actual ATR-normalized pullback size used by the V118 entry engine.
        const pullbackBodyAtr=counterPullbackCount?Math.min(3,avgPullbackBody/Math.max(atrV,1e-9)):0;
        const anchorHigh=pullbackAnchor?Number(pullbackAnchor[1]):recentMicroHigh;
        const anchorLow=pullbackAnchor?Number(pullbackAnchor[2]):recentMicroLow;
        const pullbackBrokeStructure=trendForPattern==='SELL' ? curClose>anchorHigh+atrV*0.04 : trendForPattern==='BUY' ? curClose<anchorLow-atrV*0.04 : false;
        const currentWithTrend=trendForPattern==='SELL'?cBear(livePrimary):trendForPattern==='BUY'?cBull(livePrimary):false;
        let closedCounterCount=0;
        if(trendForPattern!=='NEUTRAL'){ const cf=trendForPattern==='BUY'?cBear:cBull; for(let i=closedPrimary.length-1;i>=0&&closedCounterCount<3;i--){if(cf(closedPrimary[i]))closedCounterCount++;else break;} }
        const continuationMomentumBuy=currentWithTrend && emaStackBull && dmiBull && macdBullSupport && runnerRsiSlope>=-0.2;
        const continuationMomentumSell=currentWithTrend && emaStackBear && dmiBear && macdBearSupport && runnerRsiSlope<=0.2;
        const pullbackContinuationSell=trendForPattern==='SELL'&&closedCounterCount>=1&&closedCounterCount<=2&&continuationMomentumSell&&!pullbackBrokeStructure;
        const pullbackContinuationBuy=trendForPattern==='BUY'&&closedCounterCount>=1&&closedCounterCount<=2&&continuationMomentumBuy&&!pullbackBrokeStructure;
        const patternEligible=(trendForPattern==='BUY'||trendForPattern==='SELL')&&counterPullbackCount>=1&&counterPullbackCount<=2;

        Object.assign(lastIndicators,{
          regime, structureDirection, structureConfidence, structureBullScore, structureBearScore,
          structurePattern: zzHH&&zzHL?'HH-HL':zzLH&&zzLL?'LH-LL':zzHH?'HH':zzHL?'HL':zzLH?'LH':zzLL?'LL':'MIXED',
          patternTrendDir:trendForPattern,counterPullbackCount,pullbackClosedCount:closedCounterCount,pullbackBodyRatio,pullbackBodyAtr,pullbackBrokeStructure,pullbackAnchorHigh:anchorHigh,pullbackAnchorLow:anchorLow,
          pullbackContinuationBuy,pullbackContinuationSell,patternEligible
        });

        // Hard pre-gates for Runner TRADE only (scores always computed for popup)
        // Core trend on ind-TF; timing trigger on secondary TF; chase hard; exhaust soft.
        const transitionSpreadOk = emaSpread >= 0.15;
        // v8: score is the main filter. These gates protect against only the
        // most dangerous setups instead of requiring every indicator to agree.
        const runnerBuyChecks = {
          'EMA stack bull': emaStackBull || zzRunnerBull,
          'EMA spread': emaSpreadOk || (transitionBull && transitionSpreadOk) || zzRunnerBull,
          'Trend momentum': (coreTrendUp || transitionBull || zzRunnerBull || (dmiBull && macdBullSupport)),
          'DMI bull': !dmiStrong || dmiBull,
          'MACD bull support': macdBullSupport,
          'Secondary confirmation': (runnerBullTiming || transitionBull || (confirmBullVotes >= 2 && cLast > confirmEma5)),
          'Not chase': !chaseBuy,
          'No fast bear break': !fastBuyInvalidated,
          'ZigZag direction': !zzBearBias
        };
        const runnerSellChecks = {
          'EMA stack bear': emaStackBear || zzRunnerBear,
          'EMA spread': emaSpreadOk || (transitionBear && transitionSpreadOk) || zzRunnerBear,
          'Trend momentum': (coreTrendDown || transitionBear || zzRunnerBear || (dmiBear && macdBearSupport)),
          'DMI bear': !dmiStrong || dmiBear,
          'MACD bear support': macdBearSupport,
          'Secondary confirmation': (runnerBearTiming || transitionBear || (confirmBearVotes >= 2 && cLast < confirmEma5)),
          'Not chase': !chaseSell,
          'No fast bull break': !fastSellInvalidated,
          'ZigZag direction': !zzBullBias
        };
        // Loosened runner gate: score + core structure + fresh entry-quality
        // decide the trade. Slow RSI is advisory, not a hard blocker.
        // V24.1.49: the old gate CALCULATED DMI/MACD checks but did not
        // actually require them.  That let a high runner score enter after the
        // move was already mature.  A runner now needs trend structure + DMI +
        // MACD + fresh secondary timing + anti-chase confirmation.
        const runnerBuyGate  = runnerBuyChecks['EMA stack bull'] &&
          runnerBuyChecks['EMA spread'] && runnerBuyChecks['Trend momentum'] &&
          runnerBuyChecks['DMI bull'] && runnerBuyChecks['MACD bull support'] &&
          runnerBuyChecks['Secondary confirmation'] && runnerBuyChecks['Not chase'] &&
          runnerBuyChecks['No fast bear break'] && runnerBuyChecks['ZigZag direction'];
        const runnerSellGate = runnerSellChecks['EMA stack bear'] &&
          runnerSellChecks['EMA spread'] && runnerSellChecks['Trend momentum'] &&
          runnerSellChecks['DMI bear'] && runnerSellChecks['MACD bear support'] &&
          runnerSellChecks['Secondary confirmation'] && runnerSellChecks['Not chase'] &&
          runnerSellChecks['No fast bull break'] && runnerSellChecks['ZigZag direction'];
        lastIndicators.runnerBuyChecks  = runnerBuyChecks;
        lastIndicators.runnerSellChecks = runnerSellChecks;

        // ── Runner BUY scoring (always — live popup; gates block trade only) ──
        if (emaStackBull && emaSpreadOk) { runnerBuy += 2; runBuyConf++; runBuyReasons.push('EMA stack wide'); }
        if (aboveMid && emaStackBull)    { runnerBuy += 1; runBuyConf++; runBuyReasons.push('Above mid'); }
        if (macdAboveSignal)             { runnerBuy += 1; runBuyReasons.push('MACD >signal'); }
        if (macdBullAligned)             { runnerBuy += 2; runBuyConf++; runBuyReasons.push('MACD bull aligned'); }
        if (macdBullAccel)               { runnerBuy += 1; runBuyReasons.push('MACD accelerating'); }
        if (dmiStrong && dmiBull)         { runnerBuy += 2; runBuyConf++; runBuyReasons.push('+DI leads / ADX strong'); }
        if (rsiMomentumBull)              { runnerBuy += 1; runBuyReasons.push('RSI momentum rising'); }
        if (bearishRsiDivergence)         { runnerBuy -= 2; runBuyReasons.push('Bear RSI divergence -2'); }
        if (last > prev && prev > prev2 && (p.length < 4 || prev2 > p[p.length - 4])) {
          runnerBuy += 1; runBuyConf++; runBuyReasons.push('3+ bull');
        }
        if (slowRSI >= 45 && slowRSI <= 72 && emaStackBull) { runnerBuy += 1; runBuyReasons.push('Slow ok'); }
        // Steep slope was on ~all trades (not discriminative) — only award stronger slope

        if (runnerBullTiming)             { runnerBuy += 1; runBuyConf++; runBuyReasons.push((a.__slowKey || 'Secondary') + ' confirmed bull'); }
        if (transitionBull)               { runnerBuy += 2; runBuyConf++; runBuyReasons.push('Bull trend transition'); }
        if (zzRunnerBull)                 { runnerBuy += 3; runBuyConf += 2; runBuyReasons.push('ZigZag HH-HL continuation +3'); }
        if (nearExhaustBuy)              { runnerBuy -= 1; runBuyReasons.push('Near exhaustion -1'); }
        if (zzBearBias)                   { runnerBuy = Math.min(runnerBuy, 0); runBuyReasons.push('ZigZag bearish reversal'); }
        if (zzBullFlip)                   { runnerSell += 2; runSellConf++; runSellReasons.push('ZigZag bullish reversal'); }

        // ── Runner SELL scoring (always — live popup; gates block trade only) ──
        if (emaStackBear && emaSpreadOk) { runnerSell += 2; runSellConf++; runSellReasons.push('EMA stack wide'); }
        // CSV: "Below mid" SELL ~33% WR (2W-4L) — no longer awards points
        if (macdBelowSignal)             { runnerSell += 1; runSellReasons.push('MACD <signal'); }
        if (macdBearAligned)             { runnerSell += 2; runSellConf++; runSellReasons.push('MACD bear aligned'); }
        if (macdBearAccel)               { runnerSell += 1; runSellReasons.push('MACD accelerating'); }
        if (dmiStrong && dmiBear)         { runnerSell += 2; runSellConf++; runSellReasons.push('-DI leads / ADX strong'); }
        if (rsiMomentumBear)              { runnerSell += 1; runSellReasons.push('RSI momentum falling'); }
        if (bullishRsiDivergence)         { runnerSell -= 2; runSellReasons.push('Bull RSI divergence -2'); }
        // Prefer fresh resume timing over mature 3+ bear (late chase)
        if (runnerBearTiming) {
          runnerSell += 1; runSellConf++; runSellReasons.push((a.__slowKey || 'Secondary') + ' confirmed bear');
        }
        if (transitionBear)              { runnerSell += 2; runSellConf++; runSellReasons.push('Bear trend transition'); }
        if (zzRunnerBear)                { runnerSell += 3; runSellConf += 2; runSellReasons.push('ZigZag LL-LH continuation +3'); }
        else if (last < prev && prev < prev2 && (p.length < 4 || prev2 < p[p.length - 4])) {
          runnerSell += 1; runSellReasons.push('3+ bear');
        }
        if (slowRSI >= 28 && slowRSI <= 55 && emaStackBear) { runnerSell += 1; runSellReasons.push('Slow ok'); }

        if (nearExhaustSell)             { runnerSell -= 1; runSellReasons.push('Near exhaustion -1'); }
        if (zzBullBias)                   { runnerSell = Math.min(runnerSell, 0); runSellReasons.push('ZigZag bullish reversal'); }
        if (zzBearFlip)                   { runnerSell += 2; runSellConf++; runSellReasons.push('ZigZag bearish reversal'); }

        // ═══════════════════════════════════════════════════════════
        //  MODE 2 — REVERSAL CONTEXT
        //  Core indicators: RSI7 · StochRSI7 · EMA5/9/21 · DMI/ADX7 · MACD5/13/6 · BB14/2 · structure
        // ═══════════════════════════════════════════════════════════
        let revBuy = 0, revSell = 0;
        const revBuyReasons = [], revSellReasons = [];
        let revBuyConf = 0, revSellConf = 0;

        const r     = rsi(p, 7);
        const rPrev = rsi(p.slice(0, -1), 7);

        // Bollinger/Keltner removed from trade scoring in V24.1.56.
        const nearKL=false, nearKU=false, nearBL=false, nearBU=false;

        // StochRSI 7/7 — fast timing for 30–60s entries
        const kCurr = calcStochRSI(p, 7, 7);
        const kPrev = calcStochRSI(p.slice(0, -1), 7, 7);
        const stochOK = kCurr !== null && kPrev !== null;
        const stochOversold  = stochOK && kCurr < 25;
        const stochOverbought = stochOK && kCurr > 75;
        const stochRising  = stochOK && kCurr > kPrev;
        const stochFalling = stochOK && kCurr < kPrev;
        const strongTrendBull = dmiStrong && dmiBull && emaStackBull && (coreTrendUp || zzRunnerBull);
        const strongTrendBear = dmiStrong && dmiBear && emaStackBear && (coreTrendDown || zzRunnerBear);
        // In a strong trend, oscillator extremes are continuation/exhaustion
        // context, not automatic fade signals. Reversal scoring requires a turn
        // or divergence before the extreme contributes strongly.
        const stochRevBuy = stochOversold && (!strongTrendBear || stochRising || bullishRsiDivergence);
        const stochRevSell = stochOverbought && (!strongTrendBull || stochFalling || bearishRsiDivergence);

        // RSI slope
        const rsiSlopeUp   = r > rPrev && (r - rPrev) >= 1.2;
        const rsiSlopeDown = r < rPrev && (rPrev - r) >= 1.2;

        // Reversal persistence — the extreme must hold 2+ consecutive bars.
        // Single-bar spikes used to stack 6+ points and fire a fade that
        // was really just noise (biggest structural weakness in v6.7.x).
        // Persist on primary-TF state; raw 5s basket re-evaluations cannot advance it
        const revHost = a;
        const revState = revHost.__revState || (revHost.__revState = {
          buyStreak: 0, sellStreak: 0, lastFastCount: 0
        });
        if (revState.lastFastCount !== p.length) {
          revState.lastFastCount = p.length;
          revState.buyStreak  = r < 32 ? revState.buyStreak + 1 : 0;
          revState.sellStreak = r > 68 ? revState.sellStreak + 1 : 0;
        }

        Object.assign(lastIndicators, { rsi:r, stoch:kCurr, macd, macdSignal });

        // ── Anti-pullback: don't fade against a clear EMA trend ──
        // Pullback in uptrend looks "overbought" briefly → fake SELL
        // Pullback in downtrend looks "oversold" briefly → fake BUY
        // Soft pullback: only fake if stack AND slope both against the fade
        // (OR was too tight — any down-slope blocked every rev BUY)
        const pullbackFakeBuy  = emaStackBear && dmiBear && macdBearSupport;
        const pullbackFakeSell = emaStackBull && dmiBull && macdBullSupport;

        // Hard band extreme required (mid-channel = not a real reversal)
        const bandExtremeBuy  = !!lastIndicators.nearSupport || !!lastIndicators.bbNearLower || r < 24;
        const bandExtremeSell = !!lastIndicators.nearResistance || !!lastIndicators.bbNearUpper || r > 76;
        // Strong-trend guard — never fade a real trend (runner-style protection)
        const strongBullTrend = emaStackBull && dmiBull && macdAboveZero;
        const strongBearTrend = emaStackBear && dmiBear && macdBelowZero;

        // RSI dead zone — mid-range has no reverse edge (CSV: weak mid RSI)
        const rsiNeutral = r > 45 && r < 55;

        // Always SCORE reverse for popup live display.
        // Pullback / band / slow gates only block the TRADE decision below.
        if (!rsiNeutral) {
          if (r < 28)              { revBuy += 1; revBuyConf++; revBuyReasons.push('RSI OS ' + r.toFixed(0)); }
          if (r < 22)              { revBuy += 1; revBuyReasons.push('RSI deep OS'); }
          if (rsiSlopeUp)          { revBuy += 1; revBuyConf++; revBuyReasons.push('RSI turning up'); }
          if (bullishRsiDivergence) { revBuy += 2; revBuyConf++; revBuyReasons.push('Bull RSI divergence +2'); }
          if (stochRevBuy)            { revBuy += 1; revBuyConf++; revBuyReasons.push(strongTrendBear ? 'Stoch OS + turn/div' : 'Stoch OS'); }
          if (priceUp)             { revBuy += 1; revBuyConf++; revBuyReasons.push('Price up'); }
          if (last > prev && prev > prev2) { revBuy += 1; revBuyReasons.push('2 bull'); }
          if (slowRSI < 45)        { revBuy += 1; revBuyReasons.push('Slow bias'); }

          if (r > 72)              { revSell += 1; revSellConf++; revSellReasons.push('RSI OB ' + r.toFixed(0)); }
          if (r > 78)              { revSell += 1; revSellReasons.push('RSI deep OB'); }
          if (rsiSlopeDown)        { revSell += 1; revSellConf++; revSellReasons.push('RSI turning down'); }
          if (bearishRsiDivergence){ revSell += 2; revSellConf++; revSellReasons.push('Bear RSI divergence +2'); }
          if (stochRevSell)           { revSell += 1; revSellConf++; revSellReasons.push(strongTrendBull ? 'Stoch OB + turn/div' : 'Stoch OB'); }
          if (priceDown)           { revSell += 1; revSellConf++; revSellReasons.push('Price down'); }
          if (last < prev && prev < prev2) { revSell += 1; revSellReasons.push('2 bear'); }
          if (slowRSI > 55)        { revSell += 1; revSellReasons.push('Slow bias'); }
        }


        // Popup buy/sell = best mode score (was rev-only → stuck 0 on runner/pullback)
        lastIndicators.buyScore        = Math.max(runnerBuy, revBuy);
        lastIndicators.sellScore       = Math.max(runnerSell, revSell);
        lastIndicators.runnerBuyScore  = runnerBuy;
        lastIndicators.runnerSellScore = runnerSell;
        lastIndicators.v19RevBuy     = revBuy;
        lastIndicators.v19RevSell    = revSell;

        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // DECISION — AI-FIRST: AI makes every trade call.
        // Indicators are features that help the AI learn, not gatekeepers.
        // ═══════════════════════════════════════════════════════════

        // Clamp after near-exhaust penalties
        if (runnerBuy < 0) runnerBuy = 0;
        if (runnerSell < 0) runnerSell = 0;
        lastIndicators.buyScore        = Math.max(runnerBuy, revBuy);
        lastIndicators.sellScore       = Math.max(runnerSell, revSell);
        lastIndicators.runnerBuyScore  = runnerBuy;
        lastIndicators.runnerSellScore = runnerSell;

        // Entry-quality firewall — computed as AI features, not hard gates
        const entryLookback = Math.min(18, Math.max(8, p.length - 1));
        const entryWindow = p.slice(-entryLookback - 1, -1);
        const entryHigh = entryWindow.length ? Math.max(...entryWindow) : last;
        const entryLow  = entryWindow.length ? Math.min(...entryWindow) : last;
        const entryRange = Math.max(entryHigh - entryLow, atrV * 0.25, 1e-9);
        const entryPos = (last - entryLow) / entryRange;
        const liveOpen = Number.isFinite(a.open) && a.open > 0 ? a.open : prev;
        const liveGreen = last > liveOpen;
        const liveRed = last < liveOpen;
        const closeUp = last > prev;
        const closeDown = last < prev;
        const twoGreen = last > prev && prev > prev2;
        const twoRed = last < prev && prev < prev2;
        const sellAtBottom = entryPos <= 0.24;
        const buyAtTop = entryPos >= 0.76;
        const freshBearTurn = closeDown &&
          (prev >= prev2 || last < prev - atrV * 0.03) &&
          (liveRed || rsiSlopeDown || stochFalling);
        const freshBullTurn = closeUp &&
          (prev <= prev2 || last > prev + atrV * 0.03) &&
          (liveGreen || rsiSlopeUp || stochRising);
        const runnerSellFresh = closeDown && !twoGreen && !sellAtBottom && (liveRed || freshBearTurn);
        const runnerBuyFresh = closeUp && !twoRed && !buyAtTop && (liveGreen || freshBullTurn);
        const reversalSellFresh = freshBearTurn && !sellAtBottom && !twoGreen;
        const reversalBuyFresh = freshBullTurn && !buyAtTop && !twoRed;
        lastIndicators.entryQuality = {
          entryPos, entryHigh, entryLow, liveGreen, liveRed, twoGreen, twoRed,
          sellAtBottom, buyAtTop, runnerSellFresh, runnerBuyFresh,
          reversalSellFresh, reversalBuyFresh
        };

        // ── S/R ZONES: pivot-based support/resistance detection ──
        const SR_LOOKBACK = 24;
        const srPivots = [];
        for (let i = SR_LOOKBACK; i < p.length - SR_LOOKBACK; i++) {
          const left = p.slice(i - SR_LOOKBACK, i);
          const right = p.slice(i + 1, i + SR_LOOKBACK + 1);
          const cur = p[i];
          const isHigh = left.every(v => v < cur) && right.every(v => v < cur);
          const isLow = left.every(v => v > cur) && right.every(v => v > cur);
          if (isHigh) srPivots.push({ price: cur, type: 'high' });
          if (isLow) srPivots.push({ price: cur, type: 'low' });
        }
        const srHighs = srPivots.filter(x => x.type === 'high').map(x => x.price).sort((a,b) => b-a);
        const srLows = srPivots.filter(x => x.type === 'low').map(x => x.price).sort((a,b) => a-b);
        const closestResistance = srHighs.length ? srHighs[0] : null;
        const closestSupport = srLows.length ? srLows[0] : null;
        const srZone = atrV * 0.5;
        const nearResistance = closestResistance !== null && Math.abs(last - closestResistance) <= srZone;
        const nearSupport = closestSupport !== null && Math.abs(last - closestSupport) <= srZone;
        const resBreakdown = nearResistance && last > closestResistance && closeUp;
        const suppBreakdown = nearSupport && last < closestSupport && closeDown;
        lastIndicators.srZones = { nearResistance, nearSupport, resBreakdown, suppBreakdown, closestResistance, closestSupport, srZone };

        // ── v19.0.0: wick estimates from close prices (no OHLC available) ──
        // Approximate upper/lower wick ratio using last 3 candles' closes vs ATR
        const prev2Close = p[p.length - 3] || p[p.length - 2] || last;
        const range3 = Math.max(last, p[p.length - 2] || last, prev2Close) - Math.min(last, p[p.length - 2] || last, prev2Close);
        lastIndicators.wickUp = (range3 > 0 && atrV > 0) ? ((last - (p[p.length - 2] || last)) / atrV) : 0;
        lastIndicators.wickUp = Math.max(0, Math.min(1, lastIndicators.wickUp));
        lastIndicators.wickLo = (range3 > 0 && atrV > 0) ? (((p[p.length - 2] || last) - last) / atrV) : 0;
        lastIndicators.wickLo = Math.max(0, Math.min(1, lastIndicators.wickLo));

        // ── v19.0.0: failed breakout detection from SR zones ──
        // Price tests resistance and retreats, or tests support and bounces back
        lastIndicators.failedBreakout = false;
        if (closestResistance !== null && closestSupport !== null && atrV > 0) {
          const distToRes = (closestResistance - last) / atrV;
          const distToSup = (last - closestSupport) / atrV;
          const priceChg = (p.length >= 2) ? ((last - p[p.length - 2]) / atrV) : 0;
          // Failed resistance breakout: was above closestResistance but now below
          if (p.length >= 3) {
            const prevPrev = p[p.length - 3] || p[p.length - 2] || last;
            const brokeAbove = prevPrev > closestResistance && p[p.length - 2] > closestResistance && last < closestResistance;
            const brokeBelow = prevPrev < closestSupport && p[p.length - 2] < closestSupport && last > closestSupport;
            lastIndicators.failedBreakout = brokeAbove || brokeBelow;
          }
          // Alternate: price within 0.5 ATR of resistance and retreating
          if (!lastIndicators.failedBreakout && distToRes < 0.5 && distToRes > -0.1 && priceChg < -0.3) {
            lastIndicators.failedBreakout = true;
          }
          // Alternate: price within 0.5 ATR of support and bouncing
          if (!lastIndicators.failedBreakout && distToSup < 0.5 && distToSup > -0.1 && priceChg > 0.3) {
            lastIndicators.failedBreakout = true;
          }
        }

        // ── Build enriched AI feature vector from ALL indicators ──
        const aiPrice = last;
        const aiAsset = a.__assetName || activeAsset || lastTradeAsset || '';
        // v19.12.4: initialize before any regime-first code can reference it.
        // Using var here avoids a temporal-dead-zone from later gate code.
        var mktBanned = (aiState._marketBanUntil && (aiState._marketBanUntil[aiAsset] || 0) > Date.now());
        const indicatorCtx = {
          runnerBuy, runnerSell, revBuy, revSell,
          runBuyConf, runSellConf, revBuyConf, revSellConf,
          strongBullTrend, strongBearTrend,
          transitionBull, transitionBear,
          nearResistance, nearSupport,
          zzBullBias, zzBearBias,
          entryPos,
          regime,
          rsiNeutral,
          bandExtremeBuy, bandExtremeSell,
          directionalBullLock, directionalBearLock,
          liveBullBreak, liveBearBreak,
          fastBearBreak, fastBullBreak, fastBuyInvalidated, fastSellInvalidated,
          // Market quality is computed immediately after this base context is
          // assembled. Do NOT reference `mq` here before it exists.
          marketQuality: 0,
          contextReady: true,
          confirmBullVotes, confirmBearVotes,
          macdAboveZero, macdBelowZero,
          runnerBuyFresh, runnerSellFresh, reversalBuyFresh, reversalSellFresh,
          // v24.1.63: expose reversal-structure evidence to the consolidated
          // setup router. Metadata only; the 64-feature XGB schema is unchanged.
          zzBullFlip, zzBearFlip, confirmBullReversal, confirmBearReversal,
          dmiBull, dmiBear, macdBullSupport, macdBearSupport, emaStackBull, emaStackBear,
          atr: atrV,
          // Extra live metadata for transparent AI explanations only. These are
          // NOT additional model dimensions; aiFeatures remains exactly 64.
          rsi: r, stoch: kCurr, macd, macdSignal, ema5: e5, ema9: e9, ema21: e21,
          // ── v19.0.0: real indicator values for trade type classifier ──
          rsi30: lastIndicators.rsi30,
          wickUp: lastIndicators.wickUp || 0,
          wickLo: lastIndicators.wickLo || 0,
          failedBreakout: lastIndicators.failedBreakout || false,
          emaSpread: lastIndicators.emaSpread || 0,
          emaDeviation: lastIndicators.emaDeviation || 0,
          adx: lastIndicators.adx || 20,
          plusDI: lastIndicators.plusDI || 0, minusDI: lastIndicators.minusDI || 0,
          macdAccel: lastIndicators.macdAccel || 0, rsiSlope: lastIndicators.rsiSlope || 0,
          bullishRsiDivergence: !!lastIndicators.bullishRsiDivergence,
          bearishRsiDivergence: !!lastIndicators.bearishRsiDivergence,
          momentumAccel: lastIndicators.momentumAccel || 0,
          candleStreak: lastIndicators.candleStreak || 0,
          // V24.1.93 indicator-context metadata — mirrors live indicator values;
          // it does not change any trading score, setup gate, or AI feature.
          bbPos: lastIndicators.bbPos ?? null,
          bbWidthAtr: lastIndicators.bbWidthAtr ?? null,
          bollUpper: lastIndicators.bollUpper ?? null,
          bollLower: lastIndicators.bollLower ?? null,
          // V24.1.100: full 15s fast context is now visible to Context and AI.
          fast15Ema5: confirmEma5, fast15Ema9: confirmEma9, fast15Ema21: confirmEma21,
          fast15EmaBull: confirmEmaBull, fast15EmaBear: confirmEmaBear,
          fast15Rsi: confirmRsi, fast15RsiSlope: confirmRsi-confirmRsiPrev,
          fast15Macd: confirmMacd, fast15MacdSignal: confirmMacdSignal,
          fast15MacdBull: confirmMacdBull, fast15MacdBear: confirmMacdBear,
          fast15Adx: confirmAdx, fast15PlusDI: confirmPlusDI, fast15MinusDI: confirmMinusDI,
          fast15DmiBull: confirmDmiBull, fast15DmiBear: confirmDmiBear,
          fast15BbPos: confirmBbPos, fast15BullVotes: confirmBullVotes, fast15BearVotes: confirmBearVotes,
          fast15BullStack: confirmBullStack, fast15BearStack: confirmBearStack,
          fast15ZigzagBull: zzStructuralBull, fast15ZigzagBear: zzStructuralBear
        };
        // V24.1.137: mirror the pair-adaptive quality-funnel context (structure,
        // pullback, entry-quality) onto this ctx BEFORE the first store. All four
        // lastIndicatorCtx stores below share this same object, so one merge here
        // reaches every channel. Mirrors read lastIndicators (global /indicators/
        // node) with null-guards, matching the adx mirror style above.
        Object.assign(indicatorCtx,{
          structureDirection: String(lastIndicators.structureDirection||'NEUTRAL'),
          structureConfidence: Number(lastIndicators.structureConfidence)||0,
          structureBullScore: Number(lastIndicators.structureBullScore)||0,
          structureBearScore: Number(lastIndicators.structureBearScore)||0,
          counterPullbackCount: Number(lastIndicators.counterPullbackCount)||0,
          pullbackClosedCount: Number(lastIndicators.pullbackClosedCount)||0,
          pullbackBodyRatio: Number(lastIndicators.pullbackBodyRatio)||0,
          pullbackBodyAtr: Number(lastIndicators.pullbackBodyAtr)||0,
          pullbackBrokeStructure: !!lastIndicators.pullbackBrokeStructure,
          pullbackAnchorHigh: Number(lastIndicators.pullbackAnchorHigh)||0,
          pullbackAnchorLow: Number(lastIndicators.pullbackAnchorLow)||0,
          pullbackContinuationBuy: !!lastIndicators.pullbackContinuationBuy,
          pullbackContinuationSell: !!lastIndicators.pullbackContinuationSell,
          patternEligible: !!lastIndicators.patternEligible,
          entryQuality: lastIndicators.entryQuality || null
        });
        indicatorCtx.sellAtBottom=!!(lastIndicators.entryQuality&&lastIndicators.entryQuality.sellAtBottom);
        indicatorCtx.buyAtTop=!!(lastIndicators.entryQuality&&lastIndicators.entryQuality.buyAtTop);
        lastIndicatorCtx[aiAsset] = { ctx: indicatorCtx, ts: Date.now() };
        const aiX = aiFeatures(aiAsset, aiPrice, indicatorCtx);
        const aiPred = aiX ? (() => {
          const raw = aiForward(aiX).prob;
          const direction = raw >= 0.5 ? 'BUY' : 'SELL';
          const confidence = Math.abs(raw - 0.5) * 2;
          return { up: raw, down: 1-raw, direction, confidence, warm: aiState.trained >= AI_MIN_TRAINED, samples: aiState.trained };
        })() : { up:0.5, down:0.5, direction:null, confidence:0, warm:false, samples:aiState.trained };
        aiSetStatus(aiPred);

        const aiBuyConf  = aiPred.up;
        const aiSellConf = aiPred.down;
        const aiWarm = aiPred.warm;

        // ── 3-TIER AI DECISION GATE ──
        // Tier 1: AI at calibrated threshold (warm=68% base, cold=55%)
        // Tier 2: AI at relaxed 55% with no safety vetoes
        // Tier 3: Traditional indicator consensus (never lets bot go silent)
        //
        // AI ABSTENTION ZONE: raw probability between 0.40-0.60 means
        // the neural net is essentially saying 30/70 — it has no edge.
        // In this zone, Tiers 1+2 are skipped and Tier 3 (indicators) takes over.
        // -- Trade Type Classifier (v19.0.0): adjust gate thresholds per setup type --
        const tradeTypeResult = aiClassifyTradeType(indicatorCtx);
        // v19.0.6: backfill tradeType on most recent paper sample for tradeTypeStats tracking
        const recentSamples = aiState.samples;
        for (let si = recentSamples.length - 1; si >= 0; si--) {
          const s = recentSamples[si];
          if (s.asset === aiAsset && !s.tradeType) { s.tradeType = tradeTypeResult.type; break; }
        }
        // v19.0.5: Graduated AI gate — instead of hard-blocking at 55% valAcc,
        // allow partial AI participation in 50-55% zone with stricter confirmation.
        // Below 50%: hard gate (AI too unreliable).
        // 50-55%: learning mode — AI can fire Tier 1/2 at lowered thresholds.
        // 55%+: full AI authority with normal thresholds.
        const aiBootstrap = (Number(aiState?.independentSamples ?? aiState?.indepSamples ?? 0) < 1000);
        const aiLearning = aiBootstrap || (aiState.valTotal >= 50 && aiState.valAccuracy >= 0.50 && aiState.valAccuracy < 0.55);
        let aiWarmThr = aiWarm ? aiCalibratedThreshold(0.70) : 0.68;
        let aiColdThr = 0.65;
        if (tradeTypeResult.type === 'REVERSAL') {
          aiWarmThr = Math.max(aiWarmThr, TT_REV_THR_WARM);
          aiColdThr = Math.max(aiColdThr, TT_REV_THR_COLD);
        } else if (tradeTypeResult.type === 'RUNNER') {
          aiWarmThr = Math.max(aiWarmThr, TT_RUN_THR_WARM);
          aiColdThr = Math.max(aiColdThr, TT_RUN_THR_COLD);
        }
        // v19.0.5: in learning mode (valAcc 50-55%), lower thresholds so AI can participate
        if (aiLearning) {
          aiWarmThr = 0.60;
          aiColdThr = 0.55;
        }
        const aiAbstain = Math.abs(aiBuyConf - 0.5) < AI_ABSTAIN_ZONE;

        // -- Market Quality Check (v17.6.0) --
        const mq = aiAssessMarketQuality(aiAsset, indicatorCtx);
        const mqVeto = mq.allowTrade === false && aiState.valTotal >= 250;
        // Complete the live context only after MQ exists. V24.1.23 referenced
        // mq.qualityScore while constructing indicatorCtx, throwing a TDZ
        // ReferenceError every strategy evaluation and leaving AI with {}.
        indicatorCtx.marketQuality = Number(mq.qualityScore) || 0;
        indicatorCtx.contextReady = true;
        lastIndicatorCtx[aiAsset] = { ctx: indicatorCtx, ts: Date.now() };

        // -- Trade Memory Check (v17.6.0) --
        const memBuy  = aiCheckTradeMemory(aiAsset, 'BUY', aiBuyConf);
        const memSell = aiCheckTradeMemory(aiAsset, 'SELL', aiSellConf);

        // -- Confidence Calibration (v18.0.0): NN × MQ × memory × timeOfDay --
        // Each factor modulates raw NN confidence; TOD factor learns per-market×hour winrates.
        const mqFactor = Math.max(0.25, mq.qualityScore / 100);
        const memBuyFactor = Math.max(0.25, memBuy.winRate);
        const memSellFactor = Math.max(0.25, memSell.winRate);
        const todFactor = aiTimeOfDayFactor(aiAsset);
        // v19.0.6: in learning mode, skip MQ/mem/TOD multipliers to avoid crushing weak signals
        const calBuyConf  = aiLearning ? aiBuyConf : aiBuyConf * mqFactor * memBuyFactor * todFactor;
        const calSellConf = aiLearning ? aiSellConf : aiSellConf * mqFactor * memSellFactor * todFactor;
        const calHistoryFloor = Math.min(memBuy.winRate, memSell.winRate);
        // Floor calibrated confidence to historical accuracy — never trust AI more than real results.
        // v19.0.5: In learning mode, skip the floor so the AI can accumulate trade outcomes.
        // The floor is meant for proven models; an immature model with poor history gets crushed.
        const finalBuyConf = aiLearning
          ? calBuyConf
          : Math.min(calBuyConf, Math.max(0.50, calHistoryFloor + 0.12));
        const finalSellConf = aiLearning
          ? calSellConf
          : Math.min(calSellConf, Math.max(0.50, calHistoryFloor + 0.12));
        // Trade Quality Scores
        var __poStrategyTqsBuy = aiTradeQualityScore(aiAsset, 'BUY', aiPrice, indicatorCtx, aiBuyConf, memBuy, mq);
        var __poStrategyTqsSell = aiTradeQualityScore(aiAsset, 'SELL', aiPrice, indicatorCtx, aiSellConf, memSell, mq);
        // Attach the final quality measurements to the live context used by
        // V23/XGBoost routing. They are decision metadata, not new model
        // dimensions, so the 64-feature backup/model schema stays compatible.
        indicatorCtx.tqsBuy = __poStrategyTqsBuy;
        indicatorCtx.tqsSell = __poStrategyTqsSell;
        indicatorCtx.marketQuality = mq.qualityScore;
        lastIndicatorCtx[aiAsset] = { ctx: indicatorCtx, ts: Date.now() };
        lastIndicators.tqsBuy = __poStrategyTqsBuy;
        lastIndicators.tqsSell = __poStrategyTqsSell;
        lastIndicators.marketQuality = mq.qualityScore;
        // v21.0: initialize REV/RUN scores before ANY regime/return path can read them.
        // This fixes ReferenceError: Cannot access 'v19RunBuy' before initialization.
        const v19RevBuy = Number(revBuy) || 0;
        const v19RevSell = Number(revSell) || 0;
        const v19RunBuy = Number(runnerBuy) || 0;
        const v19RunSell = Number(runnerSell) || 0;

        // ================================================================
        // v22 DETERMINISTIC ENTRY ENGINE
        // The previous stack could accumulate enough evidence and still end
        // in HOLD because AI/MQ/legacy tier gates contradicted each other.
        // v22 uses the strategy evidence as the primary decision source.
        // AI remains diagnostic/advisory only; it cannot veto an otherwise
        // qualified setup. Existing risk/cooldown/execution controls remain
        // downstream and continue to protect against duplicate entries.
        // ================================================================
        const v22BuyScore = v19RunBuy + v19RevBuy + ((regime === 'TRENDING_BULL' || regime === 'BULL') ? 1 : 0);
        const v22SellScore = v19RunSell + v19RevSell + ((regime === 'TRENDING_BEAR' || regime === 'BEAR') ? 1 : 0);
        const v22Dir = v22BuyScore > v22SellScore ? 'BUY' : v22SellScore > v22BuyScore ? 'SELL' : null;
        const v22Best = Math.max(v22BuyScore, v22SellScore);
        const v22Margin = Math.abs(v22BuyScore - v22SellScore);
        const v22Tqs = v22Dir === 'BUY' ? __poStrategyTqsBuy : __poStrategyTqsSell;
        const v22Mem = v22Dir === 'BUY' ? memBuy : memSell;
        const v22DirectionalLock = v22Dir === 'BUY' ? directionalBearLock : directionalBullLock;
        const v22TradeType = v22Dir === 'BUY' && v19RevBuy > v19RunBuy ? 'REVERSAL' :
          (v22Dir === 'SELL' && v19RevSell > v19RunSell ? 'REVERSAL' : 'RUNNER');
        // RUNNER is intentionally disabled later in this strategy because its
        // measured results were below break-even. The older V22 early-return
        // used to bypass that protection. Keep V22 only for reversal-quality
        // setups so the routing rules are internally consistent.
        const v22Qualified = !!v22Dir && v22TradeType !== 'RUNNER' && v22Best >= 7 && v22Margin >= 2 &&
          v22Tqs >= 55 && !mktBanned && !v22DirectionalLock && v22Mem.allowTrade !== false;

        lastIndicators.v22 = {
          buyScore: v22BuyScore, sellScore: v22SellScore, margin: v22Margin,
          tqs: v22Tqs, qualified: v22Qualified, dir: v22Dir,
          aiAdvisory: true, regime
        };

        if (v22Qualified) {
          lastIndicators.mode = 'v22';
          lastIndicators.entryPath = 'DETERMINISTIC';
          console.info('[KAOS v22 DECISION]', {
            path: 'deterministic', dir: v22Dir, buyScore: v22BuyScore, sellScore: v22SellScore,
            margin: v22Margin, tqs: v22Tqs, regime, aiBuy: finalBuyConf, aiSell: finalSellConf,
            mq: mq.qualityScore, note: 'AI advisory; deterministic evidence qualified'
          });
          return {
            dir: v22Dir, mode: 'v22-deterministic', str: Math.min(95, 60 + v22Best * 4),
            buy: Math.round(finalBuyConf * 100), sell: Math.round(finalSellConf * 100),
            confidence: v22Dir === 'BUY' ? finalBuyConf : finalSellConf,
            tqs: v22Tqs,
            reasons: [`V22Score=${v22BuyScore}/${v22SellScore}`, `margin=${v22Margin}`, `TQS=${v22Tqs}`, `regime=${regime}`, 'AI=advisory'],
            reason: `⚡ V22 ${v22Dir} · Score ${v22BuyScore}/${v22SellScore} · TQS ${v22Tqs} · ${regime} · AI advisory`,
            tradeType: v22TradeType,
            tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
            measurement: { strategy: 'V22', runBuy: v19RunBuy, runSell: v19RunSell, revBuy: v19RevBuy, revSell: v19RevSell,
              scoreBuy: v22BuyScore, scoreSell: v22SellScore, margin: v22Margin, tqsBuy: __poStrategyTqsBuy, tqsSell: __poStrategyTqsSell,
              mq: mq.qualityScore, aiBuy: finalBuyConf, aiSell: finalSellConf, regime }
          };
        }

        // ================================================================
        // v19.12 REGIME-FIRST ENTRY ENGINE
        // RUNNER execution remains disabled.  The live entry decision now
        // starts with regime + entry-location + confirmation, then allows
        // the existing AI/T1/T2/T3 logic to act as advisory/secondary logic.
        // This is intentionally conservative: no trade in MIXED/UNKNOWN,
        // no chasing extended price, and no fading a strong trend.
        // ================================================================
        const v1912Price = Number(last) || 0;
        const v1912Atr = Number(atrV) || 0;
        const v1912Ema9 = Number(e9) || 0;
        const v1912Ema21 = Number(e21) || 0;
        const v1912AtrDist = v1912Atr > 0 ? Math.abs(v1912Price - v1912Ema9) / v1912Atr : 0;
        const v1912BullRegime = regime === 'TRENDING_BULL' || regime === 'BULL';
        const v1912BearRegime = regime === 'TRENDING_BEAR' || regime === 'BEAR';
        const v1912RangeRegime = regime === 'RANGING';
        const v1912MixedRegime = regime === 'MIXED' || regime === 'UNKNOWN' || regime === 'SKIP';
        const v1912ChaseBuy = v1912BullRegime && v1912AtrDist > 1.35;
        const v1912ChaseSell = v1912BearRegime && v1912AtrDist > 1.35;
        const v1912BullLocation = !v1912ChaseBuy && v1912Price >= v1912Ema9 - v1912Atr * 0.35;
        const v1912BearLocation = !v1912ChaseSell && v1912Price <= v1912Ema9 + v1912Atr * 0.35;
        const v1912BullConfirm = runnerBuy >= 5 && __poStrategyTqsBuy >= 60 && mq.qualityScore >= 55 &&
          (macdBullAligned || runnerBullTiming || transitionBull) &&
          !directionalBearLock && !mktBanned && memBuy.allowTrade !== false;
        const v1912BearConfirm = runnerSell >= 5 && __poStrategyTqsSell >= 60 && mq.qualityScore >= 55 &&
          (macdBearAligned || runnerBearTiming || transitionBear) &&
          !directionalBullLock && !mktBanned && memSell.allowTrade !== false;
        const v1912RevBuyConfirm = revBuy >= 4 && __poStrategyTqsBuy >= 58 && mq.qualityScore >= 52 &&
          (rsiSlopeUp || stochRising) && (bandExtremeBuy || r < 30) &&
          !strongBearTrend && !mktBanned && memBuy.allowTrade !== false && !directionalBearLock;
        const v1912RevSellConfirm = revSell >= 4 && __poStrategyTqsSell >= 58 && mq.qualityScore >= 52 &&
          (rsiSlopeDown || stochFalling) && (bandExtremeSell || r > 70) &&
          !strongBullTrend && !mktBanned && memSell.allowTrade !== false && !directionalBullLock;

        // Regime-first: continuation only in the matching trend; reversal only
        // in a range or at a confirmed exhaustion point. Mixed/unknown waits.
        const v1912Buy = !v1912MixedRegime &&
          ((v1912BullRegime && v1912BullConfirm && v1912BullLocation) ||
           ((v1912RangeRegime || !v1912BullRegime) && v1912RevBuyConfirm));
        const v1912Sell = !v1912MixedRegime &&
          ((v1912BearRegime && v1912BearConfirm && v1912BearLocation) ||
           ((v1912RangeRegime || !v1912BearRegime) && v1912RevSellConfirm));

        lastIndicators.v1912 = {
          regime, atrDist: Number(v1912AtrDist.toFixed(2)),
          chaseBuy: v1912ChaseBuy, chaseSell: v1912ChaseSell,
          bullConfirm: v1912BullConfirm, bearConfirm: v1912BearConfirm,
          revBuyConfirm: v1912RevBuyConfirm, revSellConfirm: v1912RevSellConfirm,
          regimeFirst: true
        };

        // Dedicated v19.12 path is deliberately before the legacy generic gate.
        if (v1912Buy || v1912Sell) {
          const v1912Dir = v1912Buy ? 'BUY' : 'SELL';
          const v1912IsRev = v1912Buy ? v1912RevBuyConfirm && !v1912BullConfirm : v1912RevSellConfirm && !v1912BearConfirm;
          lastIndicators.mode = 'v19.12';
          lastIndicators.entryPath = v1912IsRev ? 'REV12' : 'REGIME12';
          console.info('[KAOS v21 DECISION]', {
            path:'v19.12', dir:v1912Dir, regime, runBuy:v19RunBuy, runSell:v19RunSell,
            revBuy:v19RevBuy, revSell:v19RevSell,
            tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell,
            aiBuy:finalBuyConf, aiSell:finalSellConf, mq:mq.qualityScore,
            aiMode: aiBootstrap ? 'ADVISORY_BOOTSTRAP' : 'ACTIVE'
          });
          return {
            dir: v1912Dir, mode: 'v21-regime-first', str: v1912IsRev ? 68 : 72,
            buy: Math.round(finalBuyConf * 100), sell: Math.round(finalSellConf * 100),
            confidence: v1912Dir === 'BUY' ? finalBuyConf : finalSellConf,
            tqs: v1912Dir === 'BUY' ? __poStrategyTqsBuy : __poStrategyTqsSell,
            reasons: [v1912IsRev ? 'confirmedReversal' : 'regimeContinuation',
              `Regime=${regime}`, `TQS=${v1912Dir === 'BUY' ? __poStrategyTqsBuy : __poStrategyTqsSell}`,
              `MQ=${mq.qualityScore}`, `RUN=${v19RunBuy}/${v19RunSell}`, `REV=${v19RevBuy}/${v19RevSell}`,
              `ATRdist=${v1912AtrDist.toFixed(2)}`],
            reason: `🧠 v19.12 ${v1912IsRev ? 'REV' : 'REGIME'} ${v1912Dir} · ${regime} · TQS ${v1912Dir === 'BUY' ? __poStrategyTqsBuy : __poStrategyTqsSell} · MQ ${mq.qualityScore} · AI advisory`,
            tradeType: v1912IsRev ? 'REVERSAL' : 'REGIME',
            tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
            measurement: { strategy: v1912IsRev ? 'REV12' : 'REGIME12', runBuy:v19RunBuy, runSell:v19RunSell,
              revBuy:v19RevBuy, revSell:v19RevSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore,
              aiBuy:finalBuyConf, aiSell:finalSellConf, regime, rsi:r, atrDist:v1912AtrDist }
          };
        }

        // -- Validation gate (v19.0.5 graduated) --
        // Below 50% valAcc: hard gate — AI too unreliable, Tier 3 only.
        // 50-55% valAcc: learning mode — AI participates with lowered thresholds + no floor.
        // 55%+: full AI authority with normal gates.
        let aiGated = false;
        if (aiBootstrap) {
          // Clean-training bootstrap: poor/empty validation must NOT prevent
          // qualified paper trades. AI is advisory while it learns.
          aiGated = false;
          sendDebug({ reason: `🎓 AI BOOTSTRAP · valAcc ${(aiState.valAccuracy*100).toFixed(1)}% · valTotal ${aiState.valTotal} · ${aiPred.samples} trained · AI advisory` });
          console.log(`[MP] AI BOOTSTRAP — AI advisory; qualified paper trades continue until 1000 independent samples`);
        } else if (aiState.valAccuracy < 0.50) {
          // v19.7: low validation is advisory; REV/RUN + TQS decide.
          aiGated = false;
          sendDebug({ reason: `🧠 AI ADVISORY · valAcc ${(aiState.valAccuracy*100).toFixed(1)}% · ${aiPred.samples} trained · REV/RUN + TQS decide` });
        } else if (aiLearning) {
          sendDebug({ reason: `🎓 AI LEARNING · valAcc ${(aiState.valAccuracy*100).toFixed(1)}% (50-55% zone) · valTotal ${aiState.valTotal} · ${aiPred.samples} trained · partial AI access` });
          console.log(`[MP] AI LEARNING — val accuracy ${(aiState.valAccuracy*100).toFixed(1)}% — partial AI (thr=60/55%, no floor)`);
        }

        // ── Tier 1: full gate ──
        const t1BuyVetoed  = (directionalBearLock) ||
                             (zzBearBias && aiBuyConf < 0.65) ||
                             (nearResistance && !resBreakdown && aiBuyConf < 0.60);
        const t1SellVetoed = (directionalBullLock) ||
                             (zzBullBias && aiSellConf < 0.65) ||
                             (nearSupport && !suppBreakdown && aiSellConf < 0.60);
        // -- Per-market loss streak ban (v18.0.0) --
        if (!aiState._assetLossStreak) aiState._assetLossStreak = {};
        if (!aiState._marketBanUntil) aiState._marketBanUntil = {};
        mktBanned = (aiState._marketBanUntil[aiAsset] || 0) > Date.now();

        // -- Loss Pattern Memory (v18.0.0) -- check if this setup looks like past losers
        const lossPenaltyBuy  = aiCheckLossPattern(aiAsset, 'BUY', indicatorCtx);
        const lossPenaltySell = aiCheckLossPattern(aiAsset, 'SELL', indicatorCtx);
        // If this exact setup lost badly in the past, penalize calibrated confidence
        const lpmBuyConf  = Math.max(0, calBuyConf - lossPenaltyBuy);
        const lpmSellConf = Math.max(0, calSellConf - lossPenaltySell);
        // Log loss-memory hits to console for dashboard visibility
        if (lossPenaltyBuy > 0.01 || lossPenaltySell > 0.01) {
          console.log(`[AI] 🧠 Loss pattern match: ${aiAsset} BUY -${(lossPenaltyBuy*100).toFixed(0)}% SELL -${(lossPenaltySell*100).toFixed(0)}% (${aiState.lossMemory.length} patterns)`);
        }

        const t1BuyOk  = !aiGated && !mqVeto && !aiAbstain && !mktBanned && finalBuyConf >= aiWarmThr && !t1BuyVetoed && memBuy.allowTrade !== false && __poStrategyTqsBuy >= TQS_ALLOW;
        const t1SellOk = !aiGated && !mqVeto && !aiAbstain && !mktBanned && finalSellConf >= aiWarmThr && !t1SellVetoed && memSell.allowTrade !== false && __poStrategyTqsSell >= TQS_ALLOW;

        // ── Tier 2: relaxed — lower threshold, no vetoes, TQS ≥ CAUTION ──
        const t2BuyOk  = !aiGated && !mqVeto && !aiAbstain && !mktBanned && !t1BuyOk && !t1SellOk && finalBuyConf >= aiColdThr && memBuy.allowTrade !== false && __poStrategyTqsBuy >= TQS_CAUTION;
        const t2SellOk  = !aiGated && !mqVeto && !aiAbstain && !mktBanned && !t1BuyOk && !t1SellOk && !t2BuyOk && finalSellConf >= aiColdThr && memSell.allowTrade !== false && __poStrategyTqsSell >= TQS_CAUTION;

        // ── Tier 3: traditional indicator consensus fallback ──
        // If the AI is cold or uncertain, use the indicator-based signals
        // that were computed above to keep the bot trading.
        const tradBuyConf  = runnerBuy + revBuy + (confirmBullVotes >= 3 ? 1 : 0) + (confirmBullReversal ? 2 : 0) + (transitionBull ? 2 : 0);
        const tradSellConf = runnerSell + revSell + (confirmBearVotes >= 3 ? 1 : 0) + (confirmBearReversal ? 2 : 0) + (transitionBear ? 2 : 0);
        // Shared indicator consensus metadata consumed by BOTH V23/XGB router paths.
        indicatorCtx.tradBuy = tradBuyConf; indicatorCtx.tradSell = tradSellConf;
        lastIndicatorCtx[aiAsset] = { ctx: indicatorCtx, ts: Date.now() };
        // v19.0.5: T3 is the TRADITIONAL INDICATOR tier — no AI endorsement needed.
        // Learning mode (valAcc 50-55%): consensus >= 1, TQS >= 70, no AI floor,
        //   no cross-direction check — directional locks handle regime filtering.
        // Normal mode (valAcc 55%+): consensus >= 3, TQS >= 70, AI >= 35%.
        // RSI blocker is reversal-aware — reversals happen at extremes by definition.
        

/* V19_9_4_ENTRY_LOGIC_SAFE
   Scope-safe REV/RUN entry thresholds. Never references undeclared score variables.
*/
const V19_9_ENTRY_LOGIC = true;
// v24.1.37: RUNNER execution re-enabled with ZigZag continuation structure.
// Runner entries still require direction/TQS/MQ/safety gates; strong HH-HL or
// LL-LH continuation structure can satisfy the trend-timing portion of the gate.
const V19_11_RUN_ENTRIES_ENABLED = true;
const v19SetupType = tradeTypeResult?.type || 'SKIP';
// v19.9.4: use the scores already computed in this decision scope.
// The previous build incorrectly looked for them on lastIndicators, so a
// classified RUNNER could still fall through to the generic AI gate.
// v19.11: hard stop RUNNER entries before any generic AI/T1/T2/T3 path can
// reinterpret a RUNNER setup as a normal trade. This is intentional for the
// A/B measurement period; it does not alter the classifier or training data.
if (!V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER') {
  lastIndicators.mode = 'run-rev';
  lastIndicators.entryPath = 'RUN_DISABLED';
  const runSide = v19RunBuy >= v19RunSell ? 'BUY' : 'SELL';
  const runTqs = runSide === 'BUY' ? __poStrategyTqsBuy : __poStrategyTqsSell;
  const runBlockReason = `RUN_DISABLED · ${runSide} Run ${v19RunBuy}/${v19RunSell} · TQS ${Math.round(runTqs)} · MQ ${mq.qualityScore}`;
  lastDebugReason = runBlockReason;
  return { skip: true, reason: runBlockReason, tradeType: 'RUNNER', measurement: { runBuy:v19RunBuy, runSell:v19RunSell, revBuy:v19RevBuy, revSell:v19RevSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore, aiBuy:finalBuyConf, aiSell:finalSellConf, regime:regime } };
}
const v19RevStrong = v19SetupType === 'REVERSAL' && Math.max(v19RevBuy, v19RevSell) >= 3;
const v19RunStrong = v19SetupType === 'RUNNER' && Math.max(v19RunBuy, v19RunSell) >= 4;
const v19MqFloor = v19SetupType === 'REVERSAL' ? (v19RevStrong ? 48 : 52)
                 : v19SetupType === 'RUNNER' ? 60 : 65;
// Generic/SKIP setups must still have a real T3 path. 999 made the
// traditional fallback mathematically impossible, so SKIP setups could
// never trade even when the indicator consensus was valid.
const v19TqsFloor = v19SetupType === 'REVERSAL' ? (v19RevStrong ? 55 : 60)
                  : v19SetupType === 'RUNNER' ? 65 : 65;

// v24.1.43: declare reversal-aware RSI blockers before the dedicated
// REV/RUN routing reads them. This fixes the TDZ ReferenceError only.
const rsiBuyBlocked = slowBlocksBuy && tradeTypeResult.type !== 'REVERSAL';
const rsiSellBlocked = slowBlocksSell && tradeTypeResult.type !== 'REVERSAL';

// v19.9.5: HARD REV/RUN ROUTING
// Qualified REV/RUN setups return directly instead of falling through to
// generic AI abstention/T1/T2/T3 gates. Safety filters remain active.
const v24145BuyExhausted = runnerRsi >= 68 && kCurr !== null && kCurr >= 78;
const v24145SellExhausted = runnerRsi <= 32 && kCurr !== null && kCurr <= 22;
const v24145BuyFreshContinuation = (zzRunnerBull || transitionBull || liveBullBreak) &&
  runnerBuyChecks['DMI bull'] && runnerBuyChecks['MACD bull support'] &&
  __poStrategyTqsBuy >= 75 && mq.qualityScore >= 56;
const v24145SellFreshContinuation = (zzRunnerBear || transitionBear || liveBearBreak) &&
  runnerSellChecks['DMI bear'] && runnerSellChecks['MACD bear support'] &&
  __poStrategyTqsSell >= 75 && mq.qualityScore >= 56;
const v195RunBuyOk =
  V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerBuyGate &&
  v19RunBuy >= (zzRunnerBull ? 4 : 5) && __poStrategyTqsBuy >= (zzRunnerBull ? 55 : 60) &&
  mq.qualityScore >= 50 && !mktBanned && memBuy.allowTrade !== false &&
  !directionalBearLock && !fastBuyInvalidated && (!v24145BuyExhausted || v24145BuyFreshContinuation);
const v195RunSellOk =
  V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerSellGate &&
  v19RunSell >= (zzRunnerBear ? 4 : 5) && __poStrategyTqsSell >= (zzRunnerBear ? 55 : 60) &&
  mq.qualityScore >= 50 && !mktBanned && memSell.allowTrade !== false &&
  !directionalBullLock && !fastSellInvalidated && (!v24145SellExhausted || v24145SellFreshContinuation);
const v195RevBuyOk =
  v19SetupType === 'REVERSAL' && v19RevBuy >= 3 && __poStrategyTqsBuy >= 55 &&
  mq.qualityScore >= 48 && !mktBanned && memBuy.allowTrade !== false &&
  !directionalBearLock && !rsiBuyBlocked;
const v195RevSellOk =
  v19SetupType === 'REVERSAL' && v19RevSell >= 3 && __poStrategyTqsSell >= 55 &&
  mq.qualityScore >= 48 && !mktBanned && memSell.allowTrade !== false &&
  !directionalBullLock && !rsiSellBlocked;

// Dedicated path is evaluated before generic AI gates.
if (v195RunBuyOk || v195RevBuyOk) {
  lastIndicators.mode = 'run-rev';
  lastIndicators.entryPath = v195RunBuyOk ? 'RUN' : 'REV';
  return {
    dir: 'BUY', mode: 'run-rev', str: v195RunBuyOk ? 70 : 65,
    buy: Math.round(finalBuyConf * 100), sell: Math.round(finalSellConf * 100),
    confidence: finalBuyConf, tqs: __poStrategyTqsBuy,
    reasons: [v195RunBuyOk ? 'runnerEntry' : 'reversalEntry',
      `Run=${v19RunBuy}/${v19RunSell}`, (zzRunnerBull ? 'ZZ=HH-HL' : zzRunnerBear ? 'ZZ=LL-LH' : 'ZZ=none'), `Rev=${v19RevBuy}/${v19RevSell}`,
      `TQS=${__poStrategyTqsBuy}`, `MQ=${mq.qualityScore}`],
    reason: `🤖 ${v195RunBuyOk ? 'RUN' : 'REV'} BUY · Run ${v19RunBuy}/${v19RunSell} · Rev ${v19RevBuy}/${v19RevSell} · TQS ${__poStrategyTqsBuy} · MQ ${mq.qualityScore} · AI advisory`,
    tradeType: tradeTypeResult.type,
    tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
    measurement: { runBuy:v19RunBuy, runSell:v19RunSell, revBuy:v19RevBuy, revSell:v19RevSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore, aiBuy:finalBuyConf, aiSell:finalSellConf, regime:regime }
  };
}
if (v195RunSellOk || v195RevSellOk) {
  lastIndicators.mode = 'run-rev';
  lastIndicators.entryPath = v195RunSellOk ? 'RUN' : 'REV';
  return {
    dir: 'SELL', mode: 'run-rev', str: v195RunSellOk ? 70 : 65,
    buy: Math.round(finalBuyConf * 100), sell: Math.round(finalSellConf * 100),
    confidence: finalSellConf, tqs: __poStrategyTqsSell,
    reasons: [v195RunSellOk ? 'runnerEntry' : 'reversalEntry',
      `Run=${v19RunBuy}/${v19RunSell}`, (zzRunnerBull ? 'ZZ=HH-HL' : zzRunnerBear ? 'ZZ=LL-LH' : 'ZZ=none'), `Rev=${v19RevBuy}/${v19RevSell}`,
      `TQS=${__poStrategyTqsSell}`, `MQ=${mq.qualityScore}`],
    reason: `🤖 ${v195RunSellOk ? 'RUN' : 'REV'} SELL · Run ${v19RunBuy}/${v19RunSell} · Rev ${v19RevBuy}/${v19RevSell} · TQS ${__poStrategyTqsSell} · MQ ${mq.qualityScore} · AI advisory`,
    tradeType: tradeTypeResult.type,
    tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
    measurement: { runBuy:v19RunBuy, runSell:v19RunSell, revBuy:v19RevBuy, revSell:v19RevSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore, aiBuy:finalBuyConf, aiSell:finalSellConf, regime:regime }
  };
}

const t3MinConsensus = aiLearning ? 1 : 3;
        const t3MinTqs = aiBootstrap ? 55 : TQS_SKIP;
        // rsiBuyBlocked / rsiSellBlocked are declared above before the dedicated route.
        // v19.9.4: dedicated REV/RUN entry paths.
        // A classified REVERSAL/RUNNER must not fall back into the generic
        // AI-abstain/T1/T2/T3 confidence gates. AI remains advisory here.
        const v193RevBuyOk =
          v19SetupType === 'REVERSAL' &&
          v19RevBuy >= 3 &&
          __poStrategyTqsBuy >= 55 &&
          mq.qualityScore >= 48 &&
          !mktBanned &&
          memBuy.allowTrade !== false &&
          !directionalBearLock &&
          !rsiBuyBlocked;

        const v193RevSellOk =
          v19SetupType === 'REVERSAL' &&
          v19RevSell >= 3 &&
          __poStrategyTqsSell >= 55 &&
          mq.qualityScore >= 48 &&
          !mktBanned &&
          memSell.allowTrade !== false &&
          !directionalBullLock &&
          !rsiSellBlocked;

        const v193RunBuyOk =
          V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerBuyGate &&
          (!v24145BuyExhausted || v24145BuyFreshContinuation) &&
          v19RunBuy >= 5 &&
          __poStrategyTqsBuy >= 60 &&
          mq.qualityScore >= 50 &&
          !mktBanned &&
          memBuy.allowTrade !== false &&
          !directionalBearLock;

        const v193RunSellOk =
          V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerSellGate &&
          (!v24145SellExhausted || v24145SellFreshContinuation) &&
          v19RunSell >= 5 &&
          __poStrategyTqsSell >= 60 &&
          mq.qualityScore >= 50 &&
          !mktBanned &&
          memSell.allowTrade !== false &&
          !directionalBullLock;

        // For an extreme RSI continuation, allow a qualified RUNNER to proceed
        // only when runner evidence is strong and TQS is stronger.
        const v193ExtremeRunSell =
          V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerSellGate && v24145SellFreshContinuation &&
          v19RunSell >= 6 &&
          __poStrategyTqsSell >= 65 &&
          mq.qualityScore >= 50 &&
          !mktBanned &&
          memSell.allowTrade !== false &&
          !directionalBullLock;

        const v193ExtremeRunBuy =
          V19_11_RUN_ENTRIES_ENABLED && v19SetupType === 'RUNNER' && runnerBuyGate && v24145BuyFreshContinuation &&
          v19RunBuy >= 6 &&
          __poStrategyTqsBuy >= 65 &&
          mq.qualityScore >= 50 &&
          !mktBanned &&
          memBuy.allowTrade !== false &&
          !directionalBearLock;

        // Generic T3 is a true fallback: require indicator-side dominance,
        // but let an uncertain AI abstain.  When AI has a clear direction,
        // never let T3 take the opposite side (prevents the old "bull run
        // but SELL" failure mode).
        const t3AiBuyAligned  = aiAbstain || aiBuyConf >= aiSellConf;
        const t3AiSellAligned = aiAbstain || aiSellConf > aiBuyConf;

        const t3BuyOk  = !t1BuyOk && !t1SellOk && !t2BuyOk && !t2SellOk &&
                         (
                           v193RevBuyOk || v193RunBuyOk || v193ExtremeRunBuy ||
                           (
                             tradBuyConf >= t3MinConsensus &&
                             tradBuyConf > tradSellConf &&
                             t3AiBuyAligned &&
                             !directionalBearLock && !rsiBuyBlocked &&
                             (aiLearning || finalBuyConf >= 0.35) &&
                             __poStrategyTqsBuy >= Math.max(t3MinTqs, v19TqsFloor) &&
                             !mqVeto
                           )
                         );

        const t3SellOk = !t1BuyOk && !t1SellOk && !t2BuyOk && !t2SellOk && !t3BuyOk &&
                         (
                           v193RevSellOk || v193RunSellOk || v193ExtremeRunSell ||
                           (
                             tradSellConf >= t3MinConsensus &&
                             tradSellConf > tradBuyConf &&
                             t3AiSellAligned &&
                             !directionalBullLock && !rsiSellBlocked &&
                             (aiLearning || finalSellConf >= 0.35) &&
                             __poStrategyTqsSell >= Math.max(t3MinTqs, v19TqsFloor) &&
                             !mqVeto
                           )
                         );

        // ── Which tier fired? ──
        let gateTier = 0;
        const aiBuyOk  = t1BuyOk  ? (gateTier=1, true) : t2BuyOk  ? (gateTier=2, true) : t3BuyOk  ? (gateTier=3, true) : false;
        const aiSellOk = t1SellOk ? (gateTier=1, true) : t2SellOk ? (gateTier=2, true) : t3SellOk ? (gateTier=3, true) : false;

        // ── Gate log — advisory display ──
        const finalDir = aiBuyOk ? 'BUY' : aiSellOk ? 'SELL' : null;
        const tierTag = aiGated ? 'HARD-LOCK' : aiLearning ? 'AI-LRN' : aiAbstain && gateTier === 3 ? 'TRAD(abstain)' : gateTier === 1 ? 'AI' : gateTier === 2 ? 'AI-LOOSE' : gateTier === 3 ? 'TRAD' : 'HOLD';
        const v193Path = v193RevBuyOk || v193RevSellOk ? 'REV' :
                         v193RunBuyOk || v193RunSellOk || v193ExtremeRunBuy || v193ExtremeRunSell ? 'RUN' : '';
        // V24.1.152: this entire legacy tier calculation is retained ONLY to feed
        // learning/calibration statistics. It is not on the live execution path.
        // Do not display old execution terms such as MQ_VETO, ABSTAIN, BLOCKED,
        // T1/T2 or HARD-LOCK because they falsely imply AI can stop a trade.
        const learnDir = aiBuyConf >= aiSellConf ? 'BUY' : 'SELL';
        const gateLog =
            `🧠 AI-LRN ONLY · observes ${learnDir} ${(Math.max(aiBuyConf,aiSellConf)*100).toFixed(0)}% ` +
            `· raw ${(aiBuyConf*100).toFixed(0)}/${(aiSellConf*100).toFixed(0)} ` +
            `· TQS ${__poStrategyTqsBuy}/${__poStrategyTqsSell} ` +
            `· Trad B=${tradBuyConf}/S=${tradSellConf} ` +
            `· Run B=${runnerBuy}/S=${runnerSell} · Rev B=${revBuy}/S=${revSell} ` +
            `· type=${tradeTypeResult.type} · regime=${regime}${liveBearBreak?' [BULL→BEAR BREAK]':liveBullBreak?' [BEAR→BULL BREAK]':''} ` +
            `· MQ=${mq.qualityScore} · samples=${AI_LAB.samples.length} · NO TRADE AUTHORITY`;
        sendDebug({ reason: gateLog }, true);
        console.log(`[AI-LRN] ${gateLog}`);

        // ── AI BUY (any tier) ──
        if (aiBuyOk) {
            lastIndicators.mode = gateTier === 3 ? 'trad' : 'ai';
            const baseStr = gateTier === 1 ? (finalBuyConf >= 0.80 ? 80 : 65) : gateTier === 2 ? 55 : tradBuyConf >= 5 ? 70 : 55;
            return {
                dir: 'BUY',
                mode: lastIndicators.mode,
                str: baseStr,
                buy: Math.round(finalBuyConf * 100),
                sell: Math.round(finalSellConf * 100),
                confidence: finalBuyConf,
                tqs: __poStrategyTqsBuy,
                reasons: [gateTier === 1 ? 'aiFirst' : gateTier === 2 ? 'aiLoose' : 'tradConsensus', `conf=${(finalBuyConf*100).toFixed(0)}%`, `tqs=${__poStrategyTqsBuy}`, `samples=${aiPred.samples}`, `tier=${gateTier}`],
                reason: `🤖 ${tierTag} BUY · conf ${(finalBuyConf*100).toFixed(0)}% · TQS ${__poStrategyTqsBuy} · samples ${aiPred.samples} · Run ${runnerBuy}/${runnerSell} Rev ${revBuy}/${revSell}`,
                tradeType: tradeTypeResult.type, tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
                measurement: { runBuy:runnerBuy, runSell:runnerSell, revBuy:revBuy, revSell:revSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore, aiBuy:finalBuyConf, aiSell:finalSellConf, regime:regime }
            };
        }

        // ── AI SELL (any tier) ──
        if (aiSellOk) {
            lastIndicators.mode = gateTier === 3 ? 'trad' : 'ai';
            const baseStr = gateTier === 1 ? (finalSellConf >= 0.80 ? 80 : 65) : gateTier === 2 ? 55 : tradSellConf >= 5 ? 70 : 55;
            return {
                dir: 'SELL',
                mode: lastIndicators.mode,
                str: baseStr,
                buy: Math.round(finalBuyConf * 100),
                sell: Math.round(finalSellConf * 100),
                confidence: finalSellConf,
                tqs: __poStrategyTqsSell,
                reasons: [gateTier === 1 ? 'aiFirst' : gateTier === 2 ? 'aiLoose' : 'tradConsensus', `conf=${(finalSellConf*100).toFixed(0)}%`, `tqs=${__poStrategyTqsSell}`, `samples=${aiPred.samples}`, `tier=${gateTier}`],
                reason: `🤖 ${tierTag} SELL · conf ${(finalSellConf*100).toFixed(0)}% · TQS ${__poStrategyTqsSell} · samples ${aiPred.samples} · Run ${runnerBuy}/${runnerSell} Rev ${revBuy}/${revSell}`,
                tradeType: tradeTypeResult.type, tradeTypeScores: { reversal: tradeTypeResult.reversalScore, runner: tradeTypeResult.runnerScore },
                measurement: { runBuy:runnerBuy, runSell:runnerSell, revBuy:revBuy, revSell:revSell, tqsBuy:__poStrategyTqsBuy, tqsSell:__poStrategyTqsSell, mq:mq.qualityScore, aiBuy:finalBuyConf, aiSell:finalSellConf, regime:regime }
            };
        }

        // ── HOLD — legacy strategy-context telemetry only ──
        // V24.1.154: AI is learning-only. The old execution blocker strings were
        // removed in V24.1.152, so keep these locals explicitly defined to avoid
        // ReferenceErrors when Murfs Pick is evaluated for indicator context.
        const blockers = [];
        const whyBlocked = '';
        lastIndicators.mode = null;
        const holdStatus =
            `⏸ HOLD [${regime}] · AI B=${(finalBuyConf*100).toFixed(0)}% S=${(finalSellConf*100).toFixed(0)}% ` +
            `· TQS B=${__poStrategyTqsBuy} S=${__poStrategyTqsSell} ` +
            `· Trad B=${tradBuyConf}/S=${tradSellConf}` +
            (t1BuyVetoed ? ' · BUY VETOED' : '') +
            (t1SellVetoed ? ' · SELL VETOED' : '') +
            (!aiWarm ? ' · AI COLD' : '') +
            (mktBanned ? ' · BANNED' : '') +
            whyBlocked;
        sendStatus(holdStatus);
        return {
            dir: null,
            mode: null,
            reason: holdStatus,
            blockers
        };
      }   // close fn(a, slow, basket)
    },    // close 'Murfs Pick'

    // Alias: old dropdown / saved config still says Triple Confirm
    'Triple Confirm': {
      minPrices: 50,
      desc: 'Alias → Murfs Pick v7.5.0',
      fn: function (a, slow, basket) {
        return STRATEGIES['Murfs Pick'].fn(a, slow, basket);
      }
    }
  };      // close STRATEGIES

  // ════════════════════════════════════════════════════════════
  //  MESSAGING UTILITIES
  // ════════════════════════════════════════════════════════════
  function safeSend(msg) {
    try {
      const p = chrome.runtime.sendMessage(msg);
      // Mirror settled bot trades into the KAOS cloud sync channel.  The normal TRADE_RESULT
      // message still feeds the popup/background exactly as before; this second message is
      // telemetry only and can never place or repeat a Pocket Option order.
      if (msg && msg.type === 'TRADE_RESULT') {
        const r = msg.record || {};
        const cloudTrade = {
          tradeId: r.tradeID || r.tradeId || null,
          signalId: r.tradeID || r.tradeId || null,
          asset: msg.asset || r.asset,
          direction: msg.direction || r.direction,
          amount: Number(msg.amount ?? r.amount ?? 0),
          expiration: r.expiry != null ? String(r.expiry) + 's' : null,
          strategy: r.strategyEngine || r.strategy || r.engineFamily || botConfig?.strategy || 'KAOS_STRATEGY',
          engine: r.strategyEngine || r.engineFamily || null,
          engineMode: r.engineMode || null,
          strategyVersion: r.strategyVersion || null,
          tradingMode: 'STRATEGY',
          accountMode: r.accountMode||'UNKNOWN', sampleType: r.accountMode==='DEMO'?'PAPER':r.accountMode==='REAL'?'REAL':'UNKNOWN',
          entryPrice: r.entryPrice ?? null,
          settlementPrice: r.exitPrice ?? null,
          exitPrice: r.exitPrice ?? null,
          outcome: String(msg.result || r.result || '').toUpperCase().replace('DRAW','TIE'),
          result: String(msg.result || r.result || '').toUpperCase().replace('DRAW','TIE'),
          pnl: Number(r.profit ?? msg.profit ?? 0),
          timeframe: '5s', // Canonical 104-feature base; strategy timeframe remains in the trade record.
          timestamp: new Date(msg.timestamp || Date.now()).toISOString(),
          decisionAt: Number(r.ts)||null, settledAt: Number(r.resultTs)||Number(msg.timestamp)||Date.now(),
          featureVector: Array.isArray(r.featureVector) ? r.featureVector : (Array.isArray(r.x) ? r.x : null),
          aiPrediction: r.aiPrediction || null,
          aiConfidence: r.aiConfidence || null,
          aiModelVersion: r.aiModelVersion || null
        };
        chrome.runtime.sendMessage({ type: 'KAOS_TRADE_EVENT', eventType: 'TRADE_RESULT', trade: cloudTrade }).catch(() => {});
      }
      if (p && typeof p.catch === 'function') p.catch(() => {
        isRunning = false;
        tradePending = false;
        clearTimeout(window.__poatStaleLock);
      });
    } catch (e) {
      isRunning = false;
      tradePending = false;
      clearTimeout(window.__poatStaleLock);
    }
  }

  function sendStatus(t) { safeSend({ type: 'BOT_STATUS', text: t }); }

  // ════════════════════════════════════════════════════════════
  //  COMPOUNDING
  // ════════════════════════════════════════════════════════════
  function applyCompounding(winProfit) {
    if (!botConfig?.compound) return;
    const pct = parseFloat(botConfig?.compoundPct || 2);
    const bal = compoundBase + sessionPnl;
    if (bal <= 0) return;
    const next = parseFloat((bal * pct / 100).toFixed(2));
    if (next >= 0.01) {
      currentAmount = next;
      sendStatus(`📈 Compound: ~$${bal.toFixed(2)} balance · next $${currentAmount}`);
    }
  }

  // ════════════════════════════════════════════════════════════
  //  TRADE RESULT
  // ════════════════════════════════════════════════════════════
  function pnlStr() { return `${sessionPnl >= 0 ? '+' : ''}$${sessionPnl.toFixed(2)}`; }

  function reportWinrate() {
    const total = sessionWins + sessionLosses;
    if (total > 0 && total % 10 === 0) {
      sendStatus(`📊 Winrate ${(sessionWins / total * 100).toFixed(1)}% (${sessionWins}/${total}) · ${pnlStr()}`);
    }
  }

  // Resolve pending trade sample with actual P&L outcome.
  // Called by onTradeResult after win/lose/draw is determined.
  function aiResolveTradeForAsset(assetName, outcome, direction) {
    if (!assetName) return;
    // Find the oldest unresolved pending trade sample for this asset
    let bestKey = null, bestT = Infinity;
    for (const [k, v] of Object.entries(aiState.pendingTradeSamples)) {
      if (v && v.asset === assetName && v.pending && v.t < bestT) {
        bestT = v.t; bestKey = k;
      }
    }
    if (bestKey && aiState.pendingTradeSamples[bestKey]) {
      aiState.pendingTradeSamples[bestKey].outcome = outcome;
      aiState.pendingTradeSamples[bestKey].dir = direction;
      aiState.pendingTradeSamples[bestKey].pending = false;
      // v17.7.1: force immediate training by setting the sample's due time to now.
      // Without this, aiFlush() skips the sample for up to AI_TRADE_RESULT_TIMEOUT_MS (5 min)
      // because s.due > now is checked before the trade-outcome resolution path.
      for (const s of aiState.samples) {
        if (s.tradeId === bestKey) { s.due = 0; break; }
      }
      console.log(`[AI] Trade ${bestKey} resolved: ${direction} → ${outcome} — training immediately`);
    }
  }

  // v19.12.5: authoritative order-direction ledger; survives async open/close races.
  const pendingOrderDirections = Object.create(null);
  // v19.12.7: direction captured at request time, per asset, to survive async/multi-asset races.
  const pendingTradeDirections = Object.create(null);
  const normalizeTradeDirection = (v) => { const x=String(v||'').toUpperCase(); return (x==='BUY'||x==='CALL'||x==='HIGHER')?'BUY':(x==='SELL'||x==='PUT'||x==='LOWER')?'SELL':null; };
  const rememberTradeDirection = (asset, dir, id) => { const d=normalizeTradeDirection(dir); if(!d)return; if(asset){pendingOrderDirections[asset]=d; pendingTradeDirections[asset]=d;} if(id!=null)pendingOrderDirections['#'+id]=d; };
  const resolveTradeDirection = (asset,id,fallback) => normalizeTradeDirection(fallback)||(id!=null&&pendingOrderDirections['#'+id])||(asset&&pendingTradeDirections[asset])||(asset&&pendingOrderDirections[asset])||normalizeTradeDirection(getPendingSnapshot(asset)?.direction)||null;

  function onTradeResult(msg) {
    const { profit, amount, win, lose, draw } = msg;
    const asset = msg.asset || lastTradeAsset;
    if (multiAssetMode && asset) { clearTimeout(assetStaleTimers[asset]); delete assetStaleTimers[asset]; }
    else clearTimeout(window.__poatStaleLock);
    const oldestPending=getPendingSnapshot(asset);
    const resolvedDirection = resolveTradeDirection(asset,msg.id||msg.deal_id,msg.direction||msg.dir||msg.command||oldestPending?.direction||lastTradeDir)||'UNKNOWN';
    lastTradeDir = resolvedDirection;
    if (asset && resolvedDirection !== 'UNKNOWN') rememberTradeDirection(asset, resolvedDirection, msg.id || msg.deal_id);

    // ── Per-asset state accessors (multi-mode) vs globals (single-mode) ──
    const getML = () => multiAssetMode ? (assetMartLevel[asset] || 0) : martLevel;
    const setML = (v) => { if (multiAssetMode) { initAssetState(asset); assetMartLevel[asset] = v; } else martLevel = v; };
    const getCL = () => multiAssetMode ? (assetConsLosses[asset] || 0) : consecutiveLosses;
    const setCL = (v) => { if (multiAssetMode) { initAssetState(asset); assetConsLosses[asset] = v; } else consecutiveLosses = v; };
    const getAL = () => multiAssetMode ? (assetAntiLevel[asset] || 0) : antiLevel;
    const setAL = (v) => { if (multiAssetMode) { initAssetState(asset); assetAntiLevel[asset] = v; } else antiLevel = v; };
    const getCA = () => multiAssetMode ? (assetCurrentAmount[asset] || botConfig?.amount || 5) : currentAmount;
    const setCA = (v) => { if (multiAssetMode) { initAssetState(asset); assetCurrentAmount[asset] = v; } else currentAmount = v; };
    const relTP = () => { if (multiAssetMode) { initAssetState(asset); assetOpenTradeCount[asset]=Math.max(0,openTradeCount(asset)-1); syncAssetPending(asset); } else tradePending=false; };
    const setTP = () => { if (multiAssetMode) { initAssetState(asset); assetOpenTradeCount[asset]=Math.min(MAX_CONCURRENT_TRADES_PER_ASSET,openTradeCount(asset)+1); syncAssetPending(asset); } else tradePending=true; };

    if (draw) {
      aiLog('TRADE_RESULT', {asset,direction:lastTradeDir,result:'draw',profit:0}, true);
      relTP();
      const rec = finalizeTrade(asset, 'draw', 0, amount);
      aiResolveTradeForAsset(asset, 'draw', lastTradeDir);
      aiRecordTradeResult(asset, lastTradeDir, getPendingSnapshot(asset)?.confidence || 0.5, 'draw', 0, getMarketRegime(asset), lastIndicators);
      safeSend({ type: 'TRADE_RESULT', asset, direction: lastTradeDir, amount: lastTradeAmt || amount, result: 'draw', profit: 0, timestamp: Date.now(), record: rec });
      recordTradeDebug(lastTradeDir, asset, lastTradeAmt || amount, 'draw', 0);
      sendStatus(`🔄 DRAW · Resuming`);
      armSettleRescan(); // V24.1.135 A2: draw cleared the pending lock → find the next opportunity now
      return;
    }

    if (win) {
      aiLog('TRADE_RESULT', {asset,direction:lastTradeDir,result:'win',profit:Number(profit)||0}, true);
      recordEvRealized(asset, 'win', amount, profit); // V24.1.131: realized-EV window (persisted)
      if (aiState._assetLossStreak) aiState._assetLossStreak[asset] = 0;
      sessionWins++; sessionPnl += profit; lossStreak = 0; winStreak++;
      if (multiAssetMode) { const ch = initChannelState(asset); ch.winStreak++; ch.lossStreak = 0; ch.recentResults.push(1); if(ch.recentResults.length>PERF_ROTATE_WINDOW) ch.recentResults.splice(0,ch.recentResults.length-PERF_ROTATE_WINDOW); }
      aiResolveTradeForAsset(asset, 'win', lastTradeDir);
      aiRecordTradeResult(asset, lastTradeDir, getPendingSnapshot(asset)?.confidence || 0.5, 'win', profit, getMarketRegime(asset), lastIndicators);
      relTP();
      if (botConfig?.compound) {
        compoundLevel++;
        applyCompounding(profit);
      } else {
        setML(0); setCL(0); setAL(0); setCA(botConfig?.amount || 5);
      }
      sendStatus(`✅ WIN +${profit.toFixed(2)} · ${pnlStr()}`);
      const rec = finalizeTrade(asset, 'win', profit, amount);
      safeSend({ type: 'TRADE_RESULT', asset, direction: lastTradeDir, amount: lastTradeAmt || amount, result: 'win', profit, timestamp: Date.now(), record: rec });
      recordTradeDebug(lastTradeDir, asset, lastTradeAmt || amount, 'win', profit);
      reportWinrate();
      if (checkRiskLimits()) return;
      armSettleRescan(); // V24.1.135 A2: win cleared the pending lock → re-scan soon for the next setup
    }

    if (lose) {
      aiLog('TRADE_RESULT', {asset,direction:lastTradeDir,result:'loss',profit:Number(profit)||0}, true);
      recordEvRealized(asset, 'loss', amount, profit); // V24.1.131: realized-EV window (persisted)
      // Per-market loss tracking (v18.0.0)
      if (!aiState._assetLossStreak) aiState._assetLossStreak = {};
      if (!aiState._marketBanUntil) aiState._marketBanUntil = {};
      aiState._assetLossStreak[asset] = (aiState._assetLossStreak[asset] || 0) + 1;
      if (aiState._assetLossStreak[asset] >= RISK_PER_MARKET_LOSSES) {
        aiState._marketBanUntil[asset] = Date.now() + RISK_MARKET_BAN_MS;
        sendStatus(`🚫 ${asset} banned ${Math.round(RISK_MARKET_BAN_MS/60000)}min — ${aiState._assetLossStreak[asset]} consecutive losses`);
      }
      sessionLosses++; sessionPnl -= amount; lossStreak++; winStreak = 0;
      const ch = multiAssetMode ? initChannelState(asset) : null;
      if (ch) { ch.lossStreak++; ch.winStreak = 0; ch.lastLossAt = Date.now(); ch.lastLossDir = String(lastTradeDir||'').toUpperCase(); ch.recentResults.push(0); if(ch.recentResults.length>PERF_ROTATE_WINDOW) ch.recentResults.splice(0,ch.recentResults.length-PERF_ROTATE_WINDOW); }
      aiResolveTradeForAsset(asset, 'loss', lastTradeDir);
      aiRecordTradeResult(asset, lastTradeDir, getPendingSnapshot(asset)?.confidence || 0.5, 'loss', -(amount || 0), getMarketRegime(asset), lastIndicators);
      // Cooldown after a loss. The user's popup setting is the source of
      // truth and must NEVER be silently overridden by the streak ladder
      // (previously Math.max(userCd, autoCd) forced 300s on top of a 10s
      // user choice after just 3 losses). The auto ladder only applies when
      // the user has not set their own cooldown. The 8-loss hard stop is the
      // only thing that can supersede a user cooldown.
      // V24.1.124: in grid mode the streak and cooldown are PER CHANNEL — the
      // ladder below uses the channel's own streak and parks only that channel.
      const userCd = parseInt(botConfig?.cooldownAfterLoss || 0);
      const autoCdOn = botConfig?.autoCooldownOn !== false;
      let cdSec = 0, cdReason = null;
      const streakRef = ch ? ch.lossStreak : lossStreak;
      if (streakRef >= 8) {
        // hard stop — session pause 60 min (user can Stop/Start to resume early)
        cdSec = 60 * 60;
        cdReason = ch
          ? `🛑 CH${gridChannelIndex(asset)} ${asset} · ${streakRef} losses · channel paused 60m`
          : `🛑 ${streakRef} losses · session pause 60m · Stop/Start to resume early`;
      } else if (userCd > 0) {
        cdSec = userCd;
        cdReason = `⏸ ${streakRef} loss streak · user cooldown ${userCd}s`;
      } else if (autoCdOn && streakRef >= 5) {
        cdSec = 15 * 60;
        cdReason = `⏸ ${streakRef} losses · auto cooldown 15m`;
      } else if (autoCdOn && streakRef >= 3) {
        cdSec = 5 * 60;
        cdReason = `⏸ ${streakRef} losses · auto cooldown 5m`;
      }
      if (cdReason) sendStatus(cdReason);
      if (cdSec > 0) {
        if (ch) {
          ch.cooldownUntil = Date.now() + cdSec * 1000;
          ch.cooldownReason = cdReason;
          ch.lastDebugReason = cdReason;
        } else {
          cooldownUntil = Date.now() + cdSec * 1000;
        }
      }
      const rec = finalizeTrade(asset, 'loss', 0, amount);
      safeSend({ type: 'TRADE_RESULT', asset, direction: lastTradeDir, amount: lastTradeAmt || amount, result: 'loss', profit: 0, timestamp: Date.now(), record: rec });
      recordTradeDebug(lastTradeDir, asset, lastTradeAmt || amount, 'loss', 0);
      reportWinrate();

      if (checkRiskLimits()) return;

      setCL(getCL() + 1);
      setAL(0);
      const useMart = botConfig?.martingale;
      const mode    = botConfig?.martMode || 'classic';

      if (useMart && mode === 'anti') {
        setML(0); setCL(0); setCA(botConfig?.amount || 5);
        relTP();
        sendStatus(`❌ LOSS · Anti reset ${getCA()} · ${pnlStr()}`);
        return;
      }

      let maxSteps, mult, modeLabel;
      if (mode === 'soft') {
        maxSteps  = parseInt(botConfig?.softSteps || 6);
        mult      = 1.5;
        modeLabel = 'Soft';
      } else if (mode === 'step') {
        maxSteps  = parseInt(botConfig?.stepSteps || 4);
        mult      = parseFloat(botConfig?.stepMult || 2);
        modeLabel = 'Step';
      } else {
        maxSteps  = parseInt(botConfig?.maxSteps || 5);
        mult      = parseFloat(botConfig?.multiplier || 2);
        modeLabel = 'Mart';
      }

      const cls = getCL();
      const mLevel = getML();
      const shouldIncrease = (mode !== 'step') || (cls >= 2);

      if (useMart && mLevel < maxSteps && shouldIncrease) {
        setML(mLevel + 1);
        const newAmt = parseFloat((amount * mult).toFixed(2));
        setCA(newAmt);
        if (mode === 'step') setCL(0);
        const martDir = botConfig?.martDir || 'opposite';
        const nextDir = martDir === 'same'
          ? lastTradeDir
          : (lastTradeDir === 'BUY' ? 'SELL' : 'BUY');
        const nextAmt = getCA();
        sendStatus(`❌ LOSS · ${modeLabel} ×${getML()}/${maxSteps} · ${nextDir} ${nextAmt}`);

        lastTradeDir = nextDir; lastTradeAsset = asset; lastTradeAmt = nextAmt;
        assetLastTrade[asset] = Date.now() / 1000;
        const martSnapshot = captureSnapshot(nextDir, nextAmt, 'mart', null, asset);
        setPendingSnapshot(asset, martSnapshot);

        setTP();

        const tpAsset = asset;  // capture in closure for multi-mode safety
        if (multiAssetMode) {
          clearTimeout(assetStaleTimers[tpAsset]);
          assetStaleTimers[tpAsset] = setTimeout(() => {
            initAssetState(tpAsset);
            if (assetTradePending[tpAsset]) {
              assetTradePending[tpAsset] = false;
              sendStatus(`⚠ Mart lock expired · ${tpAsset} · Resuming`);
            }
            delete assetStaleTimers[tpAsset];
          }, (parseInt(botConfig?.timeframe || 60, 10) + 30) * 1000);
        } else {
          clearTimeout(window.__poatStaleLock);
          window.__poatStaleLock = setTimeout(() => {
            if (tradePending) { tradePending = false; sendStatus(`⚠ Trade lock expired · Resuming`); }
          }, (parseInt(botConfig?.timeframe || 60, 10) + 30) * 1000);
        }

        const tpDir = nextDir, tpAmt = nextAmt;
        const martTimer = setTimeout(() => {
          if (!isRunning || window.__poatStopped) {
            if (multiAssetMode) { initAssetState(tpAsset); assetTradePending[tpAsset] = false; }
            else tradePending = false;
            return;
          }
          window.postMessage({ _poatCmd: true, type: 'PLACE_TRADE', dir: tpDir, asset: tpAsset, slotId: multiAssetMode ? slotForAsset(tpAsset) : '', amount: tpAmt }, '*');
          sendStatus(`⚡ ${modeLabel} ${tpDir} ${tpAmt} · ${tpAsset}`);
        }, 800);
        if (multiAssetMode) assetMartTimers[tpAsset] = martTimer; else window.__poatMartTimer = martTimer;

      } else if (useMart && mode === 'step' && !shouldIncrease) {
        relTP();
        sendStatus(`❌ LOSS · Step (${cls}/2) · Watching...`);

      } else if (useMart && mLevel >= maxSteps) {
        setML(0); setCL(0); setCA(botConfig?.amount || 5);
        relTP();
        sendStatus(`❌ LOSS · Max ${modeLabel} steps · Reset · ${pnlStr()}`);

      } else {
        setML(0); setCL(0); setCA(botConfig?.amount || 5);
        relTP();
        sendStatus(`❌ LOSS · Reset · ${pnlStr()}`);
      }
      armSettleRescan(); // V24.1.135 A2: after a loss that did not schedule a
      // martingale step (anti-mart returns above; maxed/reset paths land here), the
      // pending lock is clear — find the next setup immediately. When a step WAS
      // scheduled, setTP() re-armed the pending lock, so this rescan no-ops at fire
      // time (armSettleRescan re-checks the pending flags).
    }
  }

  // ════════════════════════════════════════════════════════════
  //  RISK
  // ════════════════════════════════════════════════════════════
  function stopBotByRisk(reason) {
    isRunning = false; tradePending = false;
    clearTimeout(window.__poatStaleLock);
    window.postMessage({ _poatCmd: true, type: 'STOP' }, '*');
    safeSend({ type: 'BOT_STOPPED' });
    sendStatus(`🛡 ${reason} · Bot stopped`);
  }

  function checkRiskLimits() {
    const useMart = botConfig?.martingale;
    const maxLS   = parseInt(botConfig?.maxLossStreak || 0);
    const maxLoss = parseFloat(botConfig?.dailyLossLimit || 0);
    const target  = parseFloat(botConfig?.profitTarget || 0);

    // Per-market ban check (v18.0.0) — if all active markets are banned, stop
    if (aiState._marketBanUntil && multiAssetMode) {
      const activeAssets = multiAssetMode ? multiScanAssets() : (activeAsset ? [activeAsset] : []);
      if (activeAssets.length > 0) {
        const allBanned = activeAssets.every(a => (aiState._marketBanUntil[a] || 0) > Date.now());
        if (allBanned) {
          sendStatus(`🚫 All markets banned — waiting for bans to expire`);
          return false; // don't stop bot, just wait
        }
      }
    }

    // V24.1.124: in grid mode the max-loss-streak limit is enforced PER CHANNEL
    // inside checkSignals (30-minute channel park), so one channel hitting its
    // streak must never stop the whole bot. Single mode keeps the global stop.
    if (!multiAssetMode && !useMart && maxLS > 0 && lossStreak >= maxLS) {
      stopBotByRisk(`Max loss streak (${lossStreak})`); return true;
    }
    if (maxLoss > 0 && sessionPnl <= -Math.abs(maxLoss)) {
      stopBotByRisk(`Loss limit -${Math.abs(sessionPnl).toFixed(2)}`); return true;
    }
    if (target > 0 && sessionPnl >= target) {
      stopBotByRisk(`Target ${pnlStr()} reached`); return true;
    }
    return false;
  }

  // ════════════════════════════════════════════════════════════
  //  V24.1.50 CONSOLIDATED SETUP ENGINE
  //  Execution is generated by exactly three setup families:
  //    1) TREND_PULLBACK
  //    2) CONFIRMED_REVERSAL
  //    3) BREAKOUT_RETEST
  //  Legacy strategy code still computes the indicator context, but its
  //  BUY/SELL proposal no longer executes directly.
  // ════════════════════════════════════════════════════════════
  const consolidatedSetupState = Object.create(null);

  function consolidatedSetupProposal(asset, price, ind) {
    const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
    const tB=n(ind?.tqsBuy), tS=n(ind?.tqsSell), mq=n(ind?.marketQuality);
    const trB=n(ind?.tradBuy), trS=n(ind?.tradSell);
    const rsi=n(ind?.rsi ?? ind?.rsi30,50), st=n(ind?.stoch,50);
    const mac=n(ind?.macdAccel), rs=n(ind?.rsiSlope);
    const regime=String(ind?.regime||'UNKNOWN');
    const vision=aiPriceVision(asset,price);
    lastIndicators.chartVision=vision;
    const vDir=vision?.direction||'NEUTRAL', vConf=n(vision?.confidence);
    const now=Date.now();
    const stt=consolidatedSetupState[asset]||(consolidatedSetupState[asset]={});
    const pattern=patternPredict(ind);
    const patternTrusted=pattern.warm && pattern.accuracy>=PATTERN_AI.minAccuracy;
    const failed=!!ind?.failedBreakout;
    const bullDiv=!!ind?.bullishRsiDivergence, bearDiv=!!ind?.bearishRsiDivergence;
    const structureDir=String(ind?.structureDirection||'NEUTRAL');
    const structureConf=n(ind?.structureConfidence);
    const structureBull=n(ind?.structureBullScore), structureBear=n(ind?.structureBearScore);
    const bullTrendVotes=[!!ind?.strongBullTrend,regime==='TRENDING_BULL',!!ind?.zzBullBias,n(ind?.plusDI)>n(ind?.minusDI)+3,vDir==='BUY'&&vConf>=0.18,structureDir==='BUY',structureDir==='BUY'&&structureConf>=0.55,!!ind?.fast15BullStack].filter(Boolean).length;
    const bearTrendVotes=[!!ind?.strongBearTrend,regime==='TRENDING_BEAR',!!ind?.zzBearBias,n(ind?.minusDI)>n(ind?.plusDI)+3,vDir==='SELL'&&vConf>=0.18,structureDir==='SELL',structureDir==='SELL'&&structureConf>=0.55,!!ind?.fast15BearStack].filter(Boolean).length;
    // A fresh continuation can be proven either by the legacy fresh-candle flag
    // OR by strong backbone direction plus renewed MACD/RSI momentum. This catches
    // repeated LH->resume and HL->resume entries the old one-bar trigger missed.
    const bullMomentumResume=(mac>0.002 && rs>0.15) || mac>0.008 || rs>0.55;
    const bearMomentumResume=(mac<-0.002 && rs<-0.15) || mac<-0.008 || rs<-0.55;
    // BUY timing: ZigZag is context only. A BUY resumption must show current
    // bullish price/momentum behavior so we do not enter one candle late on a stale swing.
    const bullResume=(!!ind?.runnerBuyFresh && (mac>0 || rs>0)) || !!ind?.liveBullBreak || !!ind?.fastBullBreak || !!ind?.pullbackContinuationBuy ||
      (!!ind?.zzRunnerBull && (mac>0 || rs>0.08)) || !!ind?.fast15BullStack || (structureDir==='BUY'&&structureConf>=0.55&&bullMomentumResume);
    const bearResume=(!!ind?.runnerSellFresh && (mac<0 || rs<0)) || !!ind?.liveBearBreak || !!ind?.fastBearBreak || !!ind?.zzRunnerBear || !!ind?.pullbackContinuationSell || !!ind?.fast15BearStack || (structureDir==='SELL'&&structureConf>=0.55&&bearMomentumResume);
    const bullPullback=(!!ind?.pullbackContinuationBuy || !!ind?.nearSupport || !!ind?.transitionBull || st<=50 || rsi<=55 || (!!ind?.zzHL&&structureDir==='BUY')) && rsi<67 && st<85;
    const bearPullback=(!!ind?.pullbackContinuationSell || !!ind?.nearResistance || !!ind?.transitionBear || st>=50 || rsi>=45 || (!!ind?.zzLH&&structureDir==='SELL')) && rsi>31 && st>12;

    const candidates=[];
    const add=(setup,dir,score,reason)=>candidates.push({setup,dir,score,reason});

    // 1) Trend pullback continuation: trade the RESUMPTION, not the extension.
    const bullStructureOk=(structureDir==='BUY'&&structureConf>=0.48&&structureBull>=structureBear+1) || structureDir==='NEUTRAL';
    const bearStructureOk=(structureDir==='SELL'&&structureConf>=0.48&&structureBear>=structureBull+1) || structureDir==='NEUTRAL';
    const adxNow=n(ind?.adx,20);
    const mqState=aiState.marketQuality?.[asset]||{};
    const chopQuality=n(mqState.chopScore,50);
    const hardChop=(regime==='SKIP'||regime==='UNKNOWN'||chopQuality<40);
    const bullIndicatorAligned=!!ind?.emaStackBull && !!ind?.dmiBull && n(ind?.plusDI)>n(ind?.minusDI)+2 && (!!ind?.macdBullSupport || mac>0);
    const bearIndicatorAligned=!!ind?.emaStackBear && !!ind?.dmiBear && n(ind?.minusDI)>n(ind?.plusDI)+2 && (!!ind?.macdBearSupport || mac<0);
    const bullTqsMin=58, bearTqsMin=58;
    const bullMqMin=50, bearMqMin=50;
    const continuationAdxOk=adxNow>=16;
    const bullTrendContext=(regime==='TRENDING_BULL' || (regime==='MIXED'&&bullTrendVotes>=4));
    const bearTrendContext=(regime==='TRENDING_BEAR' || (regime==='MIXED'&&bearTrendVotes>=4));

    // V24.1.106 REGIME-TRANSITION SHIELD
    // A 30s trend may still look intact during the first seconds of a real turn.
    // Treat a strong OPPOSITE 15s stack as transition risk, so a developing
    // reversal is not mislabeled as an ordinary pullback/resume entry.
    const f15Bull=n(ind?.fast15BullVotes), f15Bear=n(ind?.fast15BearVotes);
    const bullTransitionRisk =
      (!!ind?.fast15BearStack && f15Bear>=4 && f15Bear>=f15Bull+2) ||
      (!!ind?.fast15ZigzagBear && f15Bear>=3 && rs<-0.20 && mac<0) ||
      (!!ind?.transitionBear && f15Bear>=3 && rs<-0.12);
    const bearTransitionRisk =
      (!!ind?.fast15BullStack && f15Bull>=4 && f15Bull>=f15Bear+2) ||
      (!!ind?.fast15ZigzagBull && f15Bull>=3 && rs>0.20 && mac>0) ||
      (!!ind?.transitionBull && f15Bull>=3 && rs>0.12);
    lastIndicators.regimeTransition={bullRisk:bullTransitionRisk,bearRisk:bearTransitionRisk,fast15Bull:f15Bull,fast15Bear:f15Bear};

    // V24.1.115 HIGH-VALUE RUNNER — SWEET-SPOT + FRESH-RESUME GATE
    // V113 proved the core EMA/ATR + Stochastic + candle-body detector could
    // recognize runners, but live diagnostics showed it could still enter too
    // late after an already-extended impulse.  V114 keeps the same core setup
    // and adds ENTRY-LOCATION protections rather than globally tightening the bot:
    //   • established but not overextended EMA5↔EMA21 separation: 0.75..1.75 ATR
    //   • directional closed-candle body: 0.20..1.25 ATR (no giant chase candle)
    //   • fresh 15s/structure resume, not merely an already-existing trend
    //   • EMA/DMI/MACD alignment + ADX persistence
    //   • RSI/Stochastic/Bollinger exhaustion ceilings
    //   • TQS/MQ remain modest quality gates
    // AI/XGB/LGB remain fully enabled and learn the actual 30s outcome.
    const expiryNow=parseInt(botConfig?.timeframe||30,10);
    const primaryKeyNow=expiryToTF(expiryNow);
    const primaryAct=assetData?.[asset];
    const hvCandle=primaryAct ? closedTFCandle(primaryAct,primaryKeyNow) : null;
    const atrRaw=Number(ind?.atr), e5Raw=Number(ind?.ema5), e21Raw=Number(ind?.ema21), stRaw=Number(ind?.stoch);
    const hvIndicatorsValid=Number.isFinite(atrRaw)&&atrRaw>0&&Number.isFinite(e5Raw)&&Number.isFinite(e21Raw)&&Number.isFinite(stRaw);
    const atrNow=hvIndicatorsValid?atrRaw:1;
    const e5Now=hvIndicatorsValid?e5Raw:0, e21Now=hvIndicatorsValid?e21Raw:0;
    const ema521Atr=hvIndicatorsValid?(e5Now-e21Now)/atrNow:0;
    const hvBodySignedAtr=hvCandle ? (n(hvCandle.close)-n(hvCandle.open))/atrNow : 0;
    const hvBodyAtr=Math.abs(hvBodySignedAtr);
    const hvBullCandle=!!hvCandle && hvBodySignedAtr>0;
    const hvBearCandle=!!hvCandle && hvBodySignedAtr<0;
    const hv30s=expiryNow===30;
    const hvBbPos=n(ind?.bbPos,0.5);
    const hvBullResume=!!ind?.runnerBuyFresh || !!ind?.liveBullBreak || !!ind?.fastBullBreak || !!ind?.pullbackContinuationBuy ||
      (structureDir==='BUY'&&structureConf>=0.55&&bullMomentumResume);
    const hvBearResume=!!ind?.runnerSellFresh || !!ind?.liveBearBreak || !!ind?.fastBearBreak || !!ind?.pullbackContinuationSell ||
      (structureDir==='SELL'&&structureConf>=0.55&&bearMomentumResume);
    const hvBullSweetSpot=ema521Atr>=0.75 && ema521Atr<=1.75 && hvBodyAtr>=0.20 && hvBodyAtr<=1.25;
    const hvBearSweetSpot=ema521Atr<=-0.75 && ema521Atr>=-1.75 && hvBodyAtr>=0.20 && hvBodyAtr<=1.25;
    const hvBullExhaustionOk=rsi<70 && st>=30 && st<90 && hvBbPos<0.94;
    const hvBearExhaustionOk=rsi>30 && st<=70 && st>10 && hvBbPos>0.06;
    const highValueBull=hv30s && hvIndicatorsValid && !hardChop && !bullTransitionRisk && bullTrendContext &&
      bullTrendVotes>=3 && bullIndicatorAligned && adxNow>=18 && hvBullSweetSpot && hvBullCandle && hvBullExhaustionOk &&
      f15Bull>=4 && f15Bull>=f15Bear+2 && !!ind?.fast15BullStack && hvBullResume &&
      !ind?.fastBuyInvalidated && tB>=56 && mq>=48 && trB>=trS;
    const highValueBear=hv30s && hvIndicatorsValid && !hardChop && !bearTransitionRisk && bearTrendContext &&
      bearTrendVotes>=3 && bearIndicatorAligned && adxNow>=18 && hvBearSweetSpot && hvBearCandle && hvBearExhaustionOk &&
      f15Bear>=4 && f15Bear>=f15Bull+2 && !!ind?.fast15BearStack && hvBearResume &&
      !ind?.fastSellInvalidated && tS>=56 && mq>=48 && trS>=trB;
    if(highValueBull){
      const score=84+Math.min(5,(ema521Atr-0.75)*4)+Math.min(4,(hvBodyAtr-0.20)*4)+Math.min(4,f15Bull-f15Bear)+Math.min(3,(adxNow-18)*0.15);
      add('HIGH_VALUE_RUNNER','BUY',score,`HIGH-VALUE RUNNER BUY · sweet spot EMA5-21 ${ema521Atr.toFixed(2)} ATR · body ${hvBodyAtr.toFixed(2)} ATR · 15s ${f15Bull}-${f15Bear} · RSI ${rsi.toFixed(0)} · fresh resume`);
    }
    if(highValueBear){
      const score=84+Math.min(5,((-ema521Atr)-0.75)*4)+Math.min(4,(hvBodyAtr-0.20)*4)+Math.min(4,f15Bear-f15Bull)+Math.min(3,(adxNow-18)*0.15);
      add('HIGH_VALUE_RUNNER','SELL',score,`HIGH-VALUE RUNNER SELL · sweet spot EMA5-21 ${(-ema521Atr).toFixed(2)} ATR · body ${hvBodyAtr.toFixed(2)} ATR · 15s ${f15Bear}-${f15Bull} · RSI ${rsi.toFixed(0)} · fresh resume`);
    }
    lastIndicators.highValueRunner={
      eligible30s:hv30s,ema521Atr,bodyAtr:hvBodyAtr,stoch:st,rsi,bbPos:hvBbPos,
      bullSweetSpot:hvBullSweetSpot,bearSweetSpot:hvBearSweetSpot,
      bullResume:hvBullResume,bearResume:hvBearResume,bull:highValueBull,bear:highValueBear
    };

    // V24.1.111 CRYPTO RUNNER ENGINE
    // Crypto/crypto-OTC frequently forms longer directional legs than the FX/OTC
    // markets used to tune the original pullback engine. Join an established leg
    // without demanding a deep pullback, but only while 30s trend + 15s stack +
    // EMA/DMI + live momentum agree. The transition shield above remains the hard
    // handoff boundary: once the opposite 15s structure develops, continuation is
    // blocked and the confirmed-reversal engine gets control.
    const cryptoSymbol=String(asset||'').toUpperCase().replace(/[^A-Z0-9-]/g,'');
    const isCrypto=/^(BTC|ETH|SOL|XRP|DOGE|ADA|BNB|LTC|BCH|DOT|AVAX|LINK|TRX|TON|SHIB|MATIC|POL|XLM|ETC|UNI|ATOM|AAVE|NEAR|ICP|FIL|SUI|APT|ARB|OP|PEPE)(?:-?(?:USD|USDT|USDC)|_OTC|USD_OTC)/.test(cryptoSymbol);
    // V114: do not let the crypto continuation engine chase an exhausted impulse
    // or enter directly against a large opposite closed 30s candle.
    const cryptoBullLocationOk = (!hvCandle || hvBodySignedAtr>=-0.55) && hvBodyAtr<=1.50 && rsi<70 && st<90 && hvBbPos<0.95;
    const cryptoBearLocationOk = (!hvCandle || hvBodySignedAtr<=0.55) && hvBodyAtr<=1.50 && rsi>30 && st>10 && hvBbPos>0.05;
    const cryptoBullRunner=isCrypto && !hardChop && !bullTransitionRisk && bullTrendContext &&
      bullTrendVotes>=3 && bullIndicatorAligned && adxNow>=18 && f15Bull>=4 && f15Bull>=f15Bear+2 &&
      !!ind?.fast15BullStack && bullResume && cryptoBullLocationOk && rs>0.05 && mac>=0 &&
      !ind?.fastBuyInvalidated && tB>=56 && mq>=48 && trB>=trS;
    const cryptoBearRunner=isCrypto && !hardChop && !bearTransitionRisk && bearTrendContext &&
      bearTrendVotes>=3 && bearIndicatorAligned && adxNow>=18 && f15Bear>=4 && f15Bear>=f15Bull+2 &&
      !!ind?.fast15BearStack && bearResume && cryptoBearLocationOk && rs<-0.05 && mac<=0 &&
      !ind?.fastSellInvalidated && tS>=56 && mq>=48 && trS>=trB;
    if(cryptoBullRunner){
      const score=74+Math.min(8,(tB-56)*0.30)+Math.min(6,(mq-48)*0.20)+Math.min(6,(adxNow-18)*0.22)+Math.min(5,f15Bull-f15Bear);
      add('CRYPTO_RUNNER_CONTINUATION','BUY',score,`CRYPTO RUNNER BUY · 30s trend + 15s ${f15Bull}-${f15Bear} · EMA/DMI/MACD aligned · ADX ${adxNow.toFixed(0)} · live momentum resumed`);
    }
    if(cryptoBearRunner){
      const score=74+Math.min(8,(tS-56)*0.30)+Math.min(6,(mq-48)*0.20)+Math.min(6,(adxNow-18)*0.22)+Math.min(5,f15Bear-f15Bull);
      add('CRYPTO_RUNNER_CONTINUATION','SELL',score,`CRYPTO RUNNER SELL · 30s trend + 15s ${f15Bear}-${f15Bull} · EMA/DMI/MACD aligned · ADX ${adxNow.toFixed(0)} · live momentum resumed`);
    }
    if(!hardChop && !bullTransitionRisk && bullTrendContext && bullTrendVotes>=2 && bullStructureOk && bullIndicatorAligned && continuationAdxOk && bullPullback && bullResume && !ind?.fastBuyInvalidated && tB>=bullTqsMin && mq>=bullMqMin && trB>=trS){
      const score=70+Math.min(9,(tB-bullTqsMin)*0.35)+Math.min(7,(mq-bullMqMin)*0.24)+Math.min(6,(adxNow-16)*0.25)+Math.min(5,bullTrendVotes)+(ind?.pullbackContinuationBuy?4:0);
      add('TREND_PULLBACK','BUY',score,`trend BUY · EMA/DMI aligned · ADX ${adxNow.toFixed(0)} · structure ${structureDir} ${(structureConf*100).toFixed(0)}% · pullback resumed`);
    }
    if(!hardChop && !bearTransitionRisk && bearTrendContext && bearTrendVotes>=2 && bearStructureOk && bearIndicatorAligned && continuationAdxOk && bearPullback && bearResume && !ind?.fastSellInvalidated && tS>=bearTqsMin && mq>=bearMqMin && trS>=trB){
      const score=70+Math.min(9,(tS-bearTqsMin)*0.35)+Math.min(7,(mq-bearMqMin)*0.24)+Math.min(6,(adxNow-16)*0.25)+Math.min(5,bearTrendVotes)+(ind?.pullbackContinuationSell?4:0);
      add('TREND_PULLBACK','SELL',score,`trend SELL · EMA/DMI aligned · ADX ${adxNow.toFixed(0)} · structure ${structureDir} ${(structureConf*100).toFixed(0)}% · pullback resumed`);
    }

    // RANGE REJECTION — separate engine for markets where trend logic has no edge.
    // Requires weak trend, a band/SR edge, oscillator turn, and rejection momentum.
    const bbPos=n(ind?.bbPos,0.5), bbWidthAtr=n(ind?.bbWidthAtr,0);
    const rangeRegime=(regime==='RANGING'||regime==='MIXED') && adxNow<20 && !ind?.strongBullTrend && !ind?.strongBearTrend;
    const rangeQuality=mq>=50 && chopQuality>=42 && bbWidthAtr>=0.35;
    const rangeBuyLocation=!!ind?.nearSupport || !!ind?.bbNearLower || bbPos<=0.18;
    const rangeSellLocation=!!ind?.nearResistance || !!ind?.bbNearUpper || bbPos>=0.82;
    const rangeBuyTurn=(rsi<=42 && st<=35 && (rs>0.05 || mac>0.0008 || !!ind?.reversalBuyFresh));
    const rangeSellTurn=(rsi>=58 && st>=65 && (rs<-0.05 || mac<-0.0008 || !!ind?.reversalSellFresh));
    if(rangeRegime && rangeQuality && rangeBuyLocation && rangeBuyTurn && !ind?.fastBuyInvalidated && tB>=56){
      add('RANGE_REJECTION','BUY',70+Math.min(8,(58-rsi)*0.30)+Math.min(6,(35-st)*0.18),
          `RANGE edge BUY · ADX ${adxNow.toFixed(0)} · BB/SR rejection · RSI/Stoch turn`);
    }
    if(rangeRegime && rangeQuality && rangeSellLocation && rangeSellTurn && !ind?.fastSellInvalidated && tS>=56){
      add('RANGE_REJECTION','SELL',70+Math.min(8,(rsi-58)*0.30)+Math.min(6,(st-65)*0.18),
          `RANGE edge SELL · ADX ${adxNow.toFixed(0)} · BB/SR rejection · RSI/Stoch turn`);
    }

    // 2) REVERSAL TRIGGER ENGINE — EXHAUSTION -> FAILURE -> BREAK -> HOLD -> CONFIRM.
    // V24.1.70: ZigZag is CONTEXT ONLY. It no longer arms, confirms, or vetoes a
    // reversal. Reversals are triggered by live price/momentum behavior so the bot
    // does not wait for a lagging swing label before recognizing a turn.
    const revAtr=Math.max(1e-9,n(ind?.atr,Math.abs(price)*0.00008));
    const emaDev=n(ind?.emaDeviation,0);
    const raw5=(getAsset(asset)?.prices||[]).filter(Number.isFinite);
    const micro=raw5.slice(-8);
    const priorMicro=micro.slice(0,-1);
    const microHi=priorMicro.length?Math.max(...priorMicro):n(price);
    const microLo=priorMicro.length?Math.min(...priorMicro):n(price);
    const last3=priorMicro.slice(-3);
    const microBreakHi=last3.length?Math.max(...last3):microHi;
    const microBreakLo=last3.length?Math.min(...last3):microLo;

    const oldBear=regime==='TRENDING_BEAR' || !!ind?.strongBearTrend || (structureDir==='SELL'&&structureConf>=0.52);
    const oldBull=regime==='TRENDING_BULL' || !!ind?.strongBullTrend || (structureDir==='BUY'&&structureConf>=0.52);
    const buyExhaustion=oldBear && (
      rsi<=30 || st<=18 || emaDev<=-0.70 || bullDiv || !!ind?.nearSupport || !!ind?.bbNearLower || failed
    );
    const sellExhaustion=oldBull && (
      rsi>=70 || st>=82 || emaDev>=0.70 || bearDiv || !!ind?.nearResistance || !!ind?.bbNearUpper || failed
    );

    // Arm only at genuine exhaustion. Track the extreme while the old trend is
    // still pushing. A new extreme does NOT trigger a trade; it simply moves the
    // failure reference point.
    if(buyExhaustion){
      if(!stt.revBuy) stt.revBuy={stage:'EXHAUSTED',armedAt:now,extreme:n(price),breakLevel:microBreakHi,breakAt:0};
      stt.revBuy.extreme=Math.min(n(stt.revBuy.extreme,n(price)),n(price));
      stt.revBuy.breakLevel=Math.max(n(stt.revBuy.breakLevel,microBreakHi),microBreakHi);
    }
    if(sellExhaustion){
      if(!stt.revSell) stt.revSell={stage:'EXHAUSTED',armedAt:now,extreme:n(price),breakLevel:microBreakLo,breakAt:0};
      stt.revSell.extreme=Math.max(n(stt.revSell.extreme,n(price)),n(price));
      stt.revSell.breakLevel=Math.min(n(stt.revSell.breakLevel,microBreakLo),microBreakLo);
    }

    // Momentum failure: price must actually reject the extreme while the old move
    // loses force. This is intentionally independent of ZigZag.
    const buyReject=!!stt.revBuy && n(price)>=n(stt.revBuy.extreme)+revAtr*0.14;
    const sellReject=!!stt.revSell && n(price)<=n(stt.revSell.extreme)-revAtr*0.14;
    const buyMomentumFailure=(rs>0.10 || mac>0.0015 || !!ind?.reversalBuyFresh || !!ind?.confirmBullReversal || bullDiv || failed);
    const sellMomentumFailure=(rs<-0.10 || mac<-0.0015 || !!ind?.reversalSellFresh || !!ind?.confirmBearReversal || bearDiv || failed);
    if(stt.revBuy?.stage==='EXHAUSTED' && buyReject && buyMomentumFailure){
      stt.revBuy.stage='FAILURE'; stt.revBuy.failureAt=now; stt.revBuy.breakLevel=Math.max(n(stt.revBuy.breakLevel,microBreakHi),microBreakHi);
    }
    if(stt.revSell?.stage==='EXHAUSTED' && sellReject && sellMomentumFailure){
      stt.revSell.stage='FAILURE'; stt.revSell.failureAt=now; stt.revSell.breakLevel=Math.min(n(stt.revSell.breakLevel,microBreakLo),microBreakLo);
    }

    // Micro-structure break after failure. The bot must clear the recent 5s
    // counter-swing with a small ATR margin and directional momentum.
    const buyBreakRaw=!!stt.revBuy && stt.revBuy.stage==='FAILURE' && n(price)>n(stt.revBuy.breakLevel)+revAtr*0.04 &&
      (rs>0.15 || mac>0.002 || !!ind?.fastBullBreak || !!ind?.liveBullBreak || !!ind?.macdBullSupport);
    const sellBreakRaw=!!stt.revSell && stt.revSell.stage==='FAILURE' && n(price)<n(stt.revSell.breakLevel)-revAtr*0.04 &&
      (rs<-0.15 || mac<-0.002 || !!ind?.fastBearBreak || !!ind?.liveBearBreak || !!ind?.macdBearSupport);
    if(buyBreakRaw){ stt.revBuy.stage='BREAK'; stt.revBuy.breakAt=now; stt.revBuy.breakPrice=n(price); }
    if(sellBreakRaw){ stt.revSell.stage='BREAK'; stt.revSell.breakAt=now; stt.revSell.breakPrice=n(price); }

    // Failed break -> restart from exhaustion instead of firing late or flipping
    // blindly. Expire stale attempts quickly because the target horizon is 30s.
    if(stt.revBuy?.stage==='BREAK' && n(price)<n(stt.revBuy.breakLevel)-revAtr*0.02){ stt.revBuy.stage='EXHAUSTED'; stt.revBuy.breakAt=0; }
    if(stt.revSell?.stage==='BREAK' && n(price)>n(stt.revSell.breakLevel)+revAtr*0.02){ stt.revSell.stage='EXHAUSTED'; stt.revSell.breakAt=0; }
    if(stt.revBuy && now-n(stt.revBuy.armedAt)>45000) stt.revBuy=null;
    if(stt.revSell && now-n(stt.revSell.armedAt)>45000) stt.revSell=null;
    if(ind?.pullbackContinuationSell && !buyExhaustion) stt.revBuy=null;
    if(ind?.pullbackContinuationBuy && !sellExhaustion) stt.revSell=null;

    // Confirmation votes are deliberately NON-ZIGZAG. They measure whether the
    // new direction has actually taken control after the break.
    const buyRevVotes=[
      !!ind?.confirmBullReversal, !!ind?.reversalBuyFresh,
      !!ind?.dmiBull, !!ind?.macdBullSupport, !!ind?.emaStackBull,
      structureDir==='BUY'&&structureConf>=0.60,
      rs>0.25, mac>0.002,
      vDir==='BUY'&&vConf>=0.20
    ].filter(Boolean).length;
    const sellRevVotes=[
      !!ind?.confirmBearReversal, !!ind?.reversalSellFresh,
      !!ind?.dmiBear, !!ind?.macdBearSupport, !!ind?.emaStackBear,
      structureDir==='SELL'&&structureConf>=0.60,
      rs<-0.25, mac<-0.002,
      vDir==='SELL'&&vConf>=0.20
    ].filter(Boolean).length;

    // Short hold prevents single-tick fakeouts without waiting so long that a
    // 30-second reversal entry becomes a chase. Strong old trends need one extra
    // independent vote.
    const buyHeld=!!stt.revBuy?.breakAt && now-stt.revBuy.breakAt>=1800 && n(price)>n(stt.revBuy.breakLevel)+revAtr*0.02;
    const sellHeld=!!stt.revSell?.breakAt && now-stt.revSell.breakAt>=1800 && n(price)<n(stt.revSell.breakLevel)-revAtr*0.02;
    const buyNeed=ind?.strongBearTrend?4:3;
    const sellNeed=ind?.strongBullTrend?4:3;
    const buyStructureBreak=buyHeld && buyRevVotes>=buyNeed;
    const sellStructureBreak=sellHeld && sellRevVotes>=sellNeed;

    const reversalLockActive=Number(stt.reversalLockUntil||0)>now;
    const reversalAiBuyOk=(!patternTrusted || pattern.reversal>=0.48) && !(reversalLockActive&&stt.reversalLockDir==='SELL');
    const reversalAiSellOk=(!patternTrusted || pattern.reversal>=0.48) && !(reversalLockActive&&stt.reversalLockDir==='BUY');
    if(buyStructureBreak && reversalAiBuyOk && tB>=58 && mq>=48 && trB>=trS && rsi<=52 && !ind?.fastBuyInvalidated){
      const score=78+Math.min(8,(tB-62)*0.28)+Math.min(5,(mq-52)*0.18)+Math.min(6,buyRevVotes)+(bullDiv?3:0)+(failed?2:0)+(patternTrusted?(pattern.reversal-0.5)*10:0);
      add('CONFIRMED_REVERSAL','BUY',score,`EXHAUSTION -> FAILURE -> BREAK held ${Math.round((now-stt.revBuy.breakAt)/1000)}s -> ${buyRevVotes} non-ZigZag confirmations${patternTrusted?` · PatternAI REV ${(pattern.reversal*100).toFixed(0)}%`:''}`);
      stt.revBuy=null; stt.reversalLockDir='BUY'; stt.reversalLockUntil=now+Math.max(30000,parseInt(botConfig?.timeframe||30,10)*1000);
    }
    if(sellStructureBreak && reversalAiSellOk && tS>=58 && mq>=48 && trS>=trB && rsi>=48 && !ind?.fastSellInvalidated){
      const score=78+Math.min(8,(tS-62)*0.28)+Math.min(5,(mq-52)*0.18)+Math.min(6,sellRevVotes)+(bearDiv?3:0)+(failed?2:0)+(patternTrusted?(pattern.reversal-0.5)*10:0);
      add('CONFIRMED_REVERSAL','SELL',score,`EXHAUSTION -> FAILURE -> BREAK held ${Math.round((now-stt.revSell.breakAt)/1000)}s -> ${sellRevVotes} non-ZigZag confirmations${patternTrusted?` · PatternAI REV ${(pattern.reversal*100).toFixed(0)}%`:''}`);
      stt.revSell=null; stt.reversalLockDir='SELL'; stt.reversalLockUntil=now+Math.max(30000,parseInt(botConfig?.timeframe||30,10)*1000);
    }
    lastIndicators.reversalStage={
      buy:buyStructureBreak?'CONFIRMED':(stt.revBuy?.stage||'OFF'),
      sell:sellStructureBreak?'CONFIRMED':(stt.revSell?.stage||'OFF'),
      buyVotes:buyRevVotes,sellVotes:sellRevVotes,
      zigzagAuthority:false
    };

    // 3) Breakout/retest: arm on the break, enter only AFTER price revisits the
    // break area and momentum resumes. This prevents end-of-candle chasing.
    const freshBullBreak=!!ind?.fastBullBreak || !!ind?.liveBullBreak || (vision?.state==='BREAKOUT'&&vDir==='BUY'&&vConf>=0.20);
    const freshBearBreak=!!ind?.fastBearBreak || !!ind?.liveBearBreak || (vision?.state==='BREAKDOWN'&&vDir==='SELL'&&vConf>=0.20);
    if(!hardChop && freshBullBreak && tB>=58 && mq>=50 && adxNow>=16 && bullIndicatorAligned){ stt.bull={at:now,price:n(price),retested:false}; stt.bear=null; }
    if(!hardChop && freshBearBreak && tS>=58 && mq>=50 && adxNow>=16 && bearIndicatorAligned){ stt.bear={at:now,price:n(price),retested:false}; stt.bull=null; }
    for(const k of ['bull','bear']) if(stt[k] && now-stt[k].at>65000) stt[k]=null;
    if(stt.bull && n(price)<=stt.bull.price) stt.bull.retested=true;
    if(stt.bear && n(price)>=stt.bear.price) stt.bear.retested=true;
    if(stt.bull?.retested && !bullTransitionRisk && bullResume && bullIndicatorAligned && adxNow>=16 && tB>=60 && mq>=50 && trB>=trS && rsi<72 && st<92 && !ind?.fastBuyInvalidated){
      const score=76+Math.min(8,(tB-66)*0.35)+Math.min(5,(mq-58)*0.2);
      add('BREAKOUT_RETEST','BUY',score,'bull break armed · level retested · bullish momentum resumed');
      stt.bull=null;
    }
    if(stt.bear?.retested && !bearTransitionRisk && bearResume && bearIndicatorAligned && adxNow>=16 && tS>=60 && mq>=50 && trS>=trB && rsi>28 && st>8 && !ind?.fastSellInvalidated){
      const score=76+Math.min(8,(tS-66)*0.35)+Math.min(5,(mq-58)*0.2);
      add('BREAKOUT_RETEST','SELL',score,'bear break armed · level retested · bearish momentum resumed');
      stt.bear=null;
    }

    if(!candidates.length){
      lastIndicators.consolidatedSetup={setup:'NONE',reason:`waiting · PB ${n(ind?.pullbackClosedCount)} candles · REV ${lastIndicators.reversalStage?.buy||'OFF'}/${lastIndicators.reversalStage?.sell||'OFF'} · PatternAI ${pattern.warm?`CONT ${(pattern.continuation*100).toFixed(0)} / REV ${(pattern.reversal*100).toFixed(0)}`:'LEARNING'} · TQS ${Math.round(tB)}/${Math.round(tS)} · MQ ${Math.round(mq)}`};
      return null;
    }
    candidates.sort((a,b)=>b.score-a.score);
    const c=candidates[0];
    const tqs=c.dir==='BUY'?tB:tS;
    const confidence=Math.max(0.60,Math.min(0.90,c.score/100));
    const sig={dir:c.dir,mode:`setup-${c.setup.toLowerCase().replaceAll('_','-')}`,tradeType:c.setup,str:Math.round(c.score),confidence,tqs,
      reason:`${c.setup} ${c.dir} · ${c.reason} · TQS ${Math.round(tqs)} · MQ ${Math.round(mq)}`,
      reasons:[c.setup,c.reason,'consolidated 3-setup engine'],
      measurement:{setup:c.setup,tqsBuy:tB,tqsSell:tS,mq,tradBuy:trB,tradSell:trS,rsi,stoch:st,regime,vision:vision?.label||'—',counterPullbackCount:n(ind?.counterPullbackCount),pullbackBodyRatio:n(ind?.pullbackBodyRatio),pullbackBodyAtr:n(ind?.pullbackBodyAtr),patternContinuation:pattern.continuation,patternReversal:pattern.reversal}};
    lastIndicators.consolidatedSetup={setup:c.setup,dir:c.dir,score:c.score,reason:sig.reason};
    return sig;
  }

  // V24.1.73 XGBOOST-ONLY 30s AUTHORITY + MARKET-AWARE TRUST
  // Rules/indicators describe the market and protect data quality; they do NOT
  // create the trade direction. XGBoost is the primary learned 30s predictor.
  // XGBoost is the only predictive learner. All other logic is context/HOLD-only.
  function xgbConsolidatedDecision(asset, price, ind, setupSig) {
    const sharedX=aiFeatures(asset,price,ind);
    const xgb=sharedX?aiXgbLive(asset,sharedX):{live:false,trained:false,previewUp:null,status:'no-features'};
    const vision=aiPriceVision(asset,price); lastIndicators.chartVision=vision;
    const prior=aiIndicatorPrior(ind,vision); // context only, never creates direction
    const pattern=patternPredict(ind); // legacy context only; never votes or trains in XGB-only mode
    const rawV23={up:0.5,down:0.5,direction:null,confidence:0,warm:false};
    const v23Acc=0;

    const clamp=p=>Math.max(0.001,Math.min(0.999,Number(p)));
    const fav=(d,p)=>d==='BUY'?p:1-p;
    const dir=p=>p>=0.5?'BUY':'SELL';

    // Model readiness is based on unseen/rolling validation, not just "trained".
    // V24.1.88 CONTEXT-CHAMPION HANDOFF: XGB may learn/preview while context
    // trades generate real outcomes, but it cannot own direction until its
    // real current-market validation accuracy BEATS the measured context trades.
    const ps=aiState.paperSetupStats||{total:0,wins:0,losses:0,recent:[]};
    // V24.1.90: benchmark XGB against the actual context trades being made.
    // Indicator tuning improves those trades; the benchmark should reflect the
    // real teacher performance rather than a hidden stricter subset.
    const allContextRecent=(Array.isArray(ps.recent)?ps.recent:[]).slice(-50);
    const assetContextRecent=allContextRecent.filter(r=>String(r?.asset||'')===String(asset||''));
    const contextBenchRows=(assetContextRecent.length>=10?assetContextRecent:allContextRecent);
    const contextBenchN=contextBenchRows.length;
    const contextBenchWins=contextBenchRows.filter(r=>r?.win===true).length;
    const contextWinRate=contextBenchN?contextBenchWins/contextBenchN:0;
    const aiMarketAccuracy=Number(xgb.marketTrustAccuracy||0);
    const aiMarketSamples=Number(xgb.marketValidationSamples||0);
    const contextBenchmarkReady=contextBenchN>=10;
    const aiBeatsContext=contextBenchmarkReady && aiMarketSamples>=20 && aiMarketAccuracy>contextWinRate;
    const xgbReady=!!xgb.live && !!xgb.validated && aiMarketSamples>=20 && aiMarketAccuracy>=0.55 && aiBeatsContext && ['VALIDATED','TRUSTED','AUTHORITY'].includes(String(xgb.marketTrustTier||''));
    const v23Ready=false;
    const patternReady=false;

    const xUp=xgbReady?clamp(xgb.up):null;
    const vUp=null;

    // V24.1.73 XGB-ONLY: one predictive model, one probability.
    // Structure, indicators, runner and reversal logic may HOLD, but no second
    // learner can dilute, override or manufacture the direction.
    let weighted=0, weight=0;
    if(xUp!=null){ weighted += xUp; weight += 1.0; }

    // Pattern AI is conditional. It answers CONTINUATION vs REVERSAL relative to
    // the established structure; translate that into UP probability only when a
    // real 1-2 candle counter-trend event exists. Never use it in ordinary flow.
    const trendDir=String(ind?.patternTrendDir||ind?.structureDirection||'NEUTRAL');
    const pullbackCount=Number(ind?.counterPullbackCount||0);
    let patternUp=null; // XGB-only: Pattern AI never contributes probability.

    const ensembleUp=weight>0?weighted/weight:0.5;
    const aiDir=dir(ensembleUp);
    const aiFav=fav(aiDir,ensembleUp);
    const aiEdge=Math.abs(ensembleUp-0.5);

    // Market-quality rules are safety/data filters only. They may HOLD, but they
    // can never manufacture BUY/SELL. This keeps the actual direction AI-owned.
    const mq=Number(ind?.marketQuality||0);
    // V24.1.88: TQS values must exist in THIS decision scope. They were
    // previously declared only inside consolidatedSetupProposal(), causing
    // ReferenceError: tB/tS is not defined during cold-start bootstrap.
    const tB=Number(ind?.tqsBuy||0), tS=Number(ind?.tqsSell||0);
    const atrNow=Number(ind?.atr||lastIndicators?.atr||0);
    const priceNow=Math.max(Math.abs(Number(price)||0),1e-9);
    const atrRel=atrNow/priceNow;
    const dataOk=Array.isArray(sharedX) && sharedX.length===AI_FEATURES && sharedX.every(Number.isFinite);
    const marketOk=Number.isFinite(mq) && mq>=38 && Number.isFinite(atrRel) && atrRel>0;

    // Anti-chase is a HOLD-only protection. It never reverses the AI direction.
    const stNow=Number(ind?.stoch ?? lastIndicators?.stoch ?? 50);
    const rsiNow=Number(ind?.rsi ?? ind?.rsi30 ?? lastIndicators?.rsi ?? 50);
    const exhausted=(aiDir==='BUY'&&(stNow>=92||rsiNow>=78)) || (aiDir==='SELL'&&(stNow<=8||rsiNow<=22));

    const shadowFmt=(up)=>{ if(up==null||!Number.isFinite(Number(up))) return '—'; const p=clamp(Number(up)), d=p>=0.5?'BUY':'SELL'; return `${d} ${(fav(d,p)*100).toFixed(1)}%`; };
    const xText=xgb.shadowXgbUp!=null
      ? `${shadowFmt(xgb.shadowXgbUp)} · SHADOW ${String(xgb.shadowXgbSource||'global').toUpperCase()} · raw ${shadowFmt(xgb.shadowXgbRawUp)}`
      : (xgb.trained?`LEARNING · ${xgb.status||'collecting'}`:`LEARNING · no XGB model`);
    const lText=xgb.shadowLgbUp!=null
      ? `${shadowFmt(xgb.shadowLgbUp)} · SHADOW ${String(xgb.shadowLgbSource||'global').toUpperCase()} · raw ${shadowFmt(xgb.shadowLgbRawUp)}`
      : `LEARNING · no LightGBM model`;
    const vText='DISABLED · XGB-ONLY';
    const setupText=setupSig?`${setupSig.tradeType||setupSig.mode||'CONTEXT'} ${setupSig.dir||''}`:'NONE';

    const base={
      strategy:`CONTEXT ${setupText}`, ensemble:`${aiDir} ${(aiFav*100).toFixed(1)}% · AI-FIRST`,
      v23:vText,xgb:xText,lightgbm:lText,rawV23:vText,rawXgb:xText,rawLightgbm:lText,
      indicatorPrior:`${prior.direction} ${(fav(prior.direction,prior.up)*100).toFixed(0)}% · CONTEXT ONLY`,
      chartVision:vision?.label||'WARMING',visionDirection:vision?.direction||'NEUTRAL',visionConfidence:Number(vision?.confidence||0),visionFacts:Array.isArray(vision?.facts)?vision.facts.slice():[],
      weights:{xgb:xUp!=null?1.0:0,v23:0,pattern:0},
      disagreementType:'XGB_ONLY',agreement:true,
      tqsBuy:Number(ind?.tqsBuy||0),tqsSell:Number(ind?.tqsSell||0),mq,regime:String(ind?.regime||'UNKNOWN'),trendIntegrity:String(ind?.trendIntegrity||''),
      structureDirection:String(ind?.structureDirection||'NEUTRAL'),structureConfidence:Number(ind?.structureConfidence||0),
      counterPullbackCount:pullbackCount,pullbackBodyRatio:Number(ind?.pullbackBodyRatio||0),reversalStage:lastIndicators.reversalStage||null,
      patternAI:{disabled:true,continuation:0.5,reversal:0.5,confidence:0,warm:false,trained:0,accuracy:0},
      aiFirst:true,xgbReady,v23Ready:false,patternReady:false,ensembleUp,aiEdge,xgbOnly:true,
      contextBenchmark:{ready:contextBenchmarkReady,samples:contextBenchN,wins:contextBenchWins,winRate:contextWinRate,aiSamples:aiMarketSamples,aiAccuracy:aiMarketAccuracy,aiBeatsContext}
    };
    const trace=(finalDecision,controller,why)=>{
      lastIndicators.aiDecisionTrace={...base,finalDecision,controller,why};
      lastIndicators.aiLastDecision={finalDecision,controller,why,ts:Date.now()};
      recordAiDecision(asset,price,lastIndicators.aiDecisionTrace,{rawV23Up:null,rawXgbUp:xgb.rawUp??xgb.previewUp,v23Up:null,xgbUp:xUp,indicatorUp:prior.up,ensembleUp,weights:base.weights},sharedX);
    };

    if (PAPER_SETUP_VALIDATION_MODE) {
      const ps=aiState.paperSetupStats||{total:0,wins:0,losses:0};
      const setupText=setupSig?`${setupSig.tradeType||setupSig.mode} ${setupSig.dir} ${Number(setupSig.str||0).toFixed(0)}`:'NONE';
      const wr=ps.total?((ps.wins/ps.total)*100).toFixed(1):'—';
      const why=`HOLD · PAPER SETUP VALIDATION · ${setupText} · hypothetical ${ps.wins||0}W/${ps.losses||0}L (${wr}%) · AI training/execution paused`;
      trace('HOLD','PAPER_SETUP_VALIDATION',why);
      return {skip:true,reason:why};
    }

    if(!dataOk || !marketOk){
      const why=`HOLD · DATA/QUALITY FILTER · MQ ${Math.round(mq)} · ATR ${Number.isFinite(atrRel)?(atrRel*100).toFixed(4)+'%':'—'}`;
      trace('HOLD','AI_FIRST_LEARN',why); return {skip:true,reason:why};
    }
    if(!xgbReady){
      // V24.1.59 CONTROLLED COLD START
      // XGB may be unvalidated for a while (or temporarily lose validation after
      // a retrain). Do not deadlock the bot. A strict setup/context bootstrap may
      // generate REAL 30s outcomes until XGB earns authority again. Bootstrap
      // never teaches its opinion to XGB; the model is still labeled only from
      // the actual 30-second future price.
      const learned=Math.max(0,Number(xgb.marketSamples||0));

      // V24.1.85 BOOTSTRAP DEADLOCK FIX
      // A qualified setup is preferred, but it is no longer mandatory.
      // Previously both a pretrained model and a completely fresh model could
      // sit at HOLD indefinitely because bDir was null whenever setupSig was NONE.
      const setupDir=(setupSig?.dir==='BUY'||setupSig?.dir==='SELL')?setupSig.dir:null;
      // V24.1.86: bootstrap uses the model's RAW probability.
      // `previewUp` is deliberately calibrated toward 50% until the current
      // market has validation history. Using previewUp here caused a deadlock:
      // the raw pretrained model could be 64-78% while bootstrap still saw 50%.
      const bootstrapRaw0=(xgb.rawUp!==null && xgb.rawUp!==undefined && xgb.rawUp!=='' && Number.isFinite(Number(xgb.rawUp)))
        ? clamp(Number(xgb.rawUp))
        : ((xgb.previewUp!==null && xgb.previewUp!==undefined && xgb.previewUp!=='' && Number.isFinite(Number(xgb.previewUp)))
            ? clamp(Number(xgb.previewUp)) : null);
      const preview0=bootstrapRaw0;
      const previewDir0=preview0==null?null:dir(preview0);
      const previewConf0=preview0==null?0:fav(previewDir0,preview0);

      const priorDir0=(prior.direction==='BUY'||prior.direction==='SELL')?prior.direction:null;
      const priorConf0=priorDir0?fav(priorDir0,clamp(prior.up)):0.5;
      const visionDir0=(vision?.direction==='BUY'||vision?.direction==='SELL')?vision.direction:null;
      const visionConf0=Number(vision?.confidence||0);
      const structureDir0=(String(ind?.structureDirection||'NEUTRAL')==='BUY'||String(ind?.structureDirection||'NEUTRAL')==='SELL')
        ? String(ind?.structureDirection) : null;
      const structureConf0=Number(ind?.structureConfidence||0);
      const regime0=String(ind?.regime||'UNKNOWN');
      const regimeDir0=regime0==='TRENDING_BULL'?'BUY':(regime0==='TRENDING_BEAR'?'SELL':null);

      // Direction priority during bootstrap:
      // 1) real qualified CONTEXT setup,
      // 2) strong live CONTEXT consensus.
      // XGB is allowed to preview and learn here, but it is NOT allowed to choose
      // trade direction until xgbReady proves it beats the context benchmark.
      let bDir=setupDir;
      let bootstrapSource=setupDir?'SETUP':null;
      if(!bDir){
        const candidates=['BUY','SELL'];
        let bestDir=null,bestVotes=0;
        for(const d0 of candidates){
          const pv=(priorDir0===d0&&priorConf0>=0.60)?1:0;
          const vv=(visionDir0===d0&&visionConf0>=0.58)?1:0;
          const sv=(structureDir0===d0&&structureConf0>=0.52)?1:0;
          const rv=(regimeDir0===d0)?1:0;
          const emaV=d0==='BUY'?!!ind?.emaStackBull:!!ind?.emaStackBear;
          const dmiV=d0==='BUY'?!!ind?.dmiBull:!!ind?.dmiBear;
          const mv=(emaV&&dmiV)?1:0;
          const tqsV=d0==='BUY' ? ((tB>=54 && tB>=tS+4)?1:0) : ((tS>=54 && tS>=tB+4)?1:0);
          const votes=pv+vv+sv+rv+mv+tqsV;
          if(votes>bestVotes){ bestVotes=votes; bestDir=d0; }
        }
        if(bestVotes>=3){ bDir=bestDir; bootstrapSource='FRESH_CONTEXT'; }
      }

      const bScore=Number(setupSig?.str||0);
      const bConf=Number(setupSig?.confidence||0);
      const priorFav=bDir?fav(bDir,clamp(prior.up)):0.5;
      const visionFav=!!bDir && vision?.direction===bDir && Number(vision?.confidence||0)>=0.55;
      const structureFav=!!bDir && String(ind?.structureDirection||'NEUTRAL')===bDir && Number(ind?.structureConfidence||0)>=0.50;
      const regimeFav=!!bDir && ((bDir==='BUY'&&regime0==='TRENDING_BULL')||(bDir==='SELL'&&regime0==='TRENDING_BEAR'));
      const emaDmiFav=!!bDir && (bDir==='BUY'? (!!ind?.emaStackBull&&!!ind?.dmiBull) : (!!ind?.emaStackBear&&!!ind?.dmiBear));
      const tqsFav=!!bDir && (bDir==='BUY' ? (tB>=54 && tB>=tS+4) : (tS>=54 && tS>=tB+4));
      const contextVotes=(prior.direction===bDir&&priorFav>=0.58?1:0)+(visionFav?1:0)+(structureFav?1:0)+(regimeFav?1:0)+(emaDmiFav?1:0)+(tqsFav?1:0);
      // V24.1.79: null is NOT a probability. Number(null) === 0 in JavaScript,
      // which previously created a fake ~100% SELL preview during cold start.
      // Only accept an actual numeric preview emitted by a real model.
      const previewRaw=(xgb.rawUp!==null && xgb.rawUp!==undefined && xgb.rawUp!=='' && Number.isFinite(Number(xgb.rawUp)))
        ? Number(xgb.rawUp) : xgb.previewUp;
      const preview=(previewRaw!==null && previewRaw!==undefined && previewRaw!=='' && Number.isFinite(Number(previewRaw)))
        ? clamp(Number(previewRaw)) : null;
      const previewFav=bDir&&preview!=null?fav(bDir,preview):0.5;
      const bootstrapExtreme=bDir && ((bDir==='BUY'&&(stNow>=90||rsiNow>=75))||(bDir==='SELL'&&(stNow<=10||rsiNow<=25)));

      // If we have enough labeled rows but still no model, do not keep placing
      // bootstrap trades. A healthy trainer should leave warming quickly. This
      // catches stale 64/72-feature native trainers and other backend stalls.
      const trainerMsg=String(AI_LAB.training?.message||'');
      const mUsable=trainerMsg.match(/(\d+)\s*\/\s*12\s+labeled samples/i);
      const nativeUsable=mUsable?Number(mUsable[1]):null;
      const trainerStalled=learned>=24 && !AI_LAB.model &&
        ((nativeUsable!=null && nativeUsable<12) || String(AI_LAB.training?.status||'').toLowerCase()==='error');
      if(trainerStalled){
        // V24.1.103: a native-host failure must disable learned AI authority, not
        // deadlock the CONTEXT teacher. Context can keep producing real 30s labels
        // while the native host is repaired. Never let an unavailable trainer stop
        // otherwise-qualified context trades.
        const nativeDetail = trainerMsg && !/AI TRAINER STALLED/i.test(trainerMsg) ? trainerMsg : 'native host unavailable or returned an error';
        const why=`AI TRAINER OFFLINE · ${learned} labels stored · ${nativeDetail} · run Repair-AIDataHost.bat from this version`;
        AI_LAB.training={...AI_LAB.training,status:'error',samples:learned,message:why};
        trace('HOLD','AI_TRAINER_OFFLINE',why); aiLog('AI_TRAINER_STALLED',{asset,learned,nativeUsable,trainerMsg,contextTeacherContinues:true},true);
        // Do not return/skip here. XGB remains without authority because AI_LAB.model
        // is null, but the normal CONTEXT/bootstrap path below remains available.
      }

      // Bootstrap authority now supports qualified CONTEXT setups only.
      // V24.1.115 QUALITY-FIRST TEACHER GATE:
      // The latest BNB diagnostic showed that a globally strict bot could still
      // execute poor *locations* inside otherwise-valid continuation setups.
      // Protect the teacher data at the execution boundary:
      //   • never bootstrap BREAKOUT_RETEST while its accumulated context edge is < break-even
      //   • require stronger evidence for ordinary TREND_PULLBACK / crypto continuation
      //   • reject giant chase candles, large opposite closed candles, and hard oscillator exhaustion
      //   • keep CONFIRMED_REVERSAL and V114 HIGH_VALUE_RUNNER as the premium setup families
      // Observation/paper labels continue for every family, so nothing is hidden from AI.
      let bootstrapOk=false, bootstrapStage='';
      const bootstrapSetupName=String(setupSig?.tradeType||setupSig?.mode||'');
      const qAtr=Math.max(1e-12,Number(ind?.atr)||0);
      const qAct=assetData?.[asset];
      const qClosed=qAct ? closedTFCandle(qAct,expiryToTF(parseInt(botConfig?.timeframe||30,10))) : null;
      const qBodySigned=qClosed ? (n(qClosed.close)-n(qClosed.open))/qAtr : 0;
      const qBodyAtr=Math.abs(qBodySigned);
      const qOppositeClosed=!!bDir && ((bDir==='BUY'&&qBodySigned<=-0.35)||(bDir==='SELL'&&qBodySigned>=0.35));
      const qChase=qBodyAtr>1.35;
      const qOscExhaust=!!bDir && ((bDir==='BUY'&&(stNow>=88||rsiNow>=72))||(bDir==='SELL'&&(stNow<=15||rsiNow<=28)));
      const qContinuation=['TREND_PULLBACK','BREAKOUT_RETEST','CRYPTO_RUNNER_CONTINUATION','HIGH_VALUE_RUNNER'].includes(bootstrapSetupName);
      const qLocationOk=!qContinuation || (!qOppositeClosed && !qChase && !qOscExhaust);
      let qSetupGate=false;
      if(bootstrapSetupName==='CONFIRMED_REVERSAL') qSetupGate=(bScore>=68 && bConf>=0.60 && contextVotes>=2);
      else if(bootstrapSetupName==='HIGH_VALUE_RUNNER') qSetupGate=(bScore>=84 && bConf>=0.60 && contextVotes>=2 && qLocationOk);
      else if(bootstrapSetupName==='TREND_PULLBACK') qSetupGate=(bScore>=72 && bConf>=0.62 && contextVotes>=2 && qLocationOk);
      else if(bootstrapSetupName==='CRYPTO_RUNNER_CONTINUATION') qSetupGate=(bScore>=80 && bConf>=0.62 && contextVotes>=2 && qLocationOk);
      else if(bootstrapSetupName==='BREAKOUT_RETEST') qSetupGate=false; // observe/learn only until revalidated above break-even
      lastIndicators.bootstrapQuality={setup:bootstrapSetupName,score:bScore,confidence:bConf,contextVotes,bodyAtr:qBodyAtr,oppositeClosed:qOppositeClosed,chase:qChase,oscExhaust:qOscExhaust,locationOk:qLocationOk,setupGate:qSetupGate};

      if(bDir && mq>=48 && !bootstrapExtreme){
        if(bootstrapSource==='SETUP'){
          if(qSetupGate){
            if(learned<25){
              bootstrapOk=true; bootstrapStage='SEED_QUALITY_SETUP';
            } else if(learned<60){
              bootstrapOk=(preview==null || previewFav>=0.44); bootstrapStage='GUIDED_QUALITY_SETUP';
            } else {
              bootstrapOk=(preview!=null && previewFav>=0.52); bootstrapStage='HANDOFF_QUALITY_SETUP';
            }
          }
        } else if(bootstrapSource==='FRESH_CONTEXT'){
          // V24.1.108: FRESH_CONTEXT is observation/learning context only.
          // The 1W/9L AUDUSD run showed that generic cold-start entries were
          // being executed without a qualified setup.  Do not risk money merely
          // to create labels; actual bootstrap execution now requires SETUP.
          bootstrapOk=false;
          bootstrapStage='FRESH_CONTEXT_OBSERVE';
        }
      }

      if(bootstrapOk){
        const sourceConf=bootstrapSource==='FRESH_CONTEXT' ? Math.min(0.64,0.56+contextVotes*0.02)
          : Math.max(0.58,Math.min(0.76,bConf||0.60));
        const confidence=sourceConf;
        const setupName=setupSig?.tradeType||setupSig?.mode||bootstrapSource||'CONTEXT';
        const why=`COLD-START ${bootstrapStage} ${bDir} ${(confidence*100).toFixed(1)}% · source ${bootstrapSource||'—'} · setup ${setupName} ${bScore.toFixed(0)} · context ${contextVotes}/6 · XGB preview ${preview==null?'—':(previewFav*100).toFixed(1)+'%'} · ${learned} market labels`;
        const sig={...(setupSig||{}),dir:bDir,mode:'cold-start-bootstrap',tradeType:`BOOTSTRAP_${setupName}`,confidence,reason:why,
          reasons:[...(Array.isArray(setupSig?.reasons)?setupSig.reasons:[]),'controlled bootstrap to prevent learning deadlock','actual 30s outcome remains the training label'],
          measurement:{...(setupSig?.measurement||{}),strategy:'COLD_START_BOOTSTRAP',bootstrapStage,bootstrapSource,learnedSamples:learned,xgbPreviewUp:preview,xgbPreviewFav:previewFav,xgbValidationAccuracy:Number(xgb.validationAccuracy||0),xgbValidationSamples:Number(xgb.validationSamples||0),contextVotes}};
        // V24.1.90: no extra teacher-only timing veto here; the corrected
        // context indicators determine setup quality without suppressing trade flow.
        trace(bDir,'COLD_START_BOOTSTRAP',why); aiLog('BOOTSTRAP_ENTRY',{asset,dir:bDir,stage:bootstrapStage,why},true);
        return {sig,reason:why};
      }

      const benchText=contextBenchmarkReady
        ? `AI ${(aiMarketAccuracy*100).toFixed(1)}%/${aiMarketSamples} vs CONTEXT ${(contextWinRate*100).toFixed(1)}%/${contextBenchN}`
        : `CONTEXT BENCHMARK ${contextBenchN}/10`;
      const waitWhy=bDir
        ? `HOLD · CONTEXT LEARNING · ${benchText} · source ${bootstrapSource||'NONE'} · setup ${setupSig?.tradeType||setupSig?.mode||'NONE'} ${bScore.toFixed(0)} · context ${contextVotes}/6`
        : `HOLD · AI MUST BEAT CONTEXT · ${benchText} · ${xText} · waiting for context direction/benchmark`;
      trace('HOLD','AI_FIRST_LEARN',waitWhy); return {skip:true,reason:waitWhy};
    }

    // V24.1.64 REVERSAL AUTHORITY SHIELD
    // Preserve same-trend runner behavior. Only counter-trend AI entries are gated.
    // A trained XGB prediction is NOT enough by itself to call a reversal while the
    // current regime still says the opposite trend. The reversal engine must have
    // actually confirmed the flip (or the new structure must be independently strong).
    const regimeNow=String(ind?.regime||'UNKNOWN');
    const structureNow=String(ind?.structureDirection||'NEUTRAL');
    const structureNowConf=Number(ind?.structureConfidence||0);
    const revStageNow=lastIndicators.reversalStage||{};
    const counterTrend=(aiDir==='BUY'&&regimeNow==='TRENDING_BEAR') || (aiDir==='SELL'&&regimeNow==='TRENDING_BULL');
    const setupReversalConfirmed=!!setupSig && setupSig.tradeType==='CONFIRMED_REVERSAL' && setupSig.dir===aiDir;
    const stageReversalConfirmed=(aiDir==='BUY'&&revStageNow.buy==='CONFIRMED') || (aiDir==='SELL'&&revStageNow.sell==='CONFIRMED');
    const independentStructureFlip=(structureNow===aiDir && structureNowConf>=0.68 &&
      ((aiDir==='BUY'&&!!ind?.macdBullSupport&&Number(ind?.rsiSlope||0)>0.20) ||
       (aiDir==='SELL'&&!!ind?.macdBearSupport&&Number(ind?.rsiSlope||0)<-0.20)));
    const reversalConfirmed=setupReversalConfirmed || stageReversalConfirmed || independentStructureFlip;
    if(counterTrend && !reversalConfirmed){
      const why=`HOLD · REVERSAL NOT CONFIRMED · AI ${aiDir} ${(aiFav*100).toFixed(1)}% against ${regimeNow} · REV ${revStageNow.buy||'OFF'}/${revStageNow.sell||'OFF'} · structure ${structureNow} ${(structureNowConf*100).toFixed(0)}%`;
      trace('HOLD','AI_FIRST_REVERSAL_SHIELD',why); return {skip:true,reason:why};
    }

    // V24.1.87 BUY TIMING SHIELD
    // BUY-only. The prior weak spot was entering after bullish momentum had already
    // peaked. Wait for re-acceleration when BUY is stale/extended; do not modify SELL.
    if(aiDir==='BUY' && !reversalConfirmed){
      const buySlopeNow=Number(ind?.rsiSlope ?? lastIndicators?.rsiSlope ?? 0);
      const buyEmaNow=Number(ind?.emaDeviation ?? lastIndicators?.emaDeviation ?? 0);
      const buyFreshNow=!!ind?.runnerBuyFresh || !!ind?.pullbackContinuationBuy || !!ind?.fastBullBreak || !!ind?.liveBullBreak;
      const buyUpperNow=!!ind?.nearResistance || !!ind?.bbNearUpper;
      const buyFadingNow=buySlopeNow<=0 && !ind?.macdBullSupport && !ind?.fastBullBreak && !ind?.liveBullBreak;
      const buyLateNow=(buyEmaNow>=0.70 && rsiNow>=60) || (rsiNow>=67 && stNow>=82) || (buyUpperNow && buySlopeNow<0.18);
      if(!buyFreshNow && (buyFadingNow || buyLateNow)){
        const why=`HOLD · BUY TIMING · wait for re-acceleration · AI BUY ${(aiFav*100).toFixed(1)}% · RSI ${rsiNow.toFixed(0)} · Stoch ${stNow.toFixed(0)} · slope ${buySlopeNow.toFixed(2)} · EMA21 ${buyEmaNow.toFixed(2)} ATR${buyUpperNow?' · upper barrier':''}`;
        trace('HOLD','AI_FIRST_BUY_TIMING',why); return {skip:true,reason:why};
      }
    }

    // V24.1.66 LATE-EXTENSION SHIELD
    // HOLD-only. Preserve the AI direction and preserve fresh continuation entries,
    // but do not chase an established trend after price has already stretched too
    // far from EMA21. The latest real EURCHF run showed the weakness concentrated
    // in late TRENDING_BULL BUYs, so the soft bull-side guard is deliberately more
    // sensitive while SELL remains protected only at a hard exhaustion extreme.
    const emaDevNow=Number(ind?.emaDeviation ?? lastIndicators?.emaDeviation ?? 0);
    const sameTrend=(aiDir==='BUY'&&regimeNow==='TRENDING_BULL') || (aiDir==='SELL'&&regimeNow==='TRENDING_BEAR');
    const continuationSetup=!!setupSig && setupSig.dir===aiDir &&
      (setupSig.tradeType==='TREND_PULLBACK' || setupSig.tradeType==='BREAKOUT_RETEST' || setupSig.tradeType==='CRYPTO_RUNNER_CONTINUATION' || setupSig.tradeType==='HIGH_VALUE_RUNNER');
    const freshContinuation=aiDir==='BUY'
      ? (!!ind?.runnerBuyFresh || !!ind?.pullbackContinuationBuy || !!ind?.fastBullBreak || !!ind?.liveBullBreak)
      : (!!ind?.runnerSellFresh || !!ind?.pullbackContinuationSell || !!ind?.fastBearBreak || !!ind?.liveBearBreak);
    const hardLateExtension=(aiDir==='BUY'&&emaDevNow>=2.60) || (aiDir==='SELL'&&emaDevNow<=-2.60);
    const softBullLateExtension=aiDir==='BUY' && regimeNow==='TRENDING_BULL' && !continuationSetup && !freshContinuation &&
      emaDevNow>=0.45 && rsiNow>=55 && stNow>=88;
    const lateExtensionBlocked=sameTrend && (hardLateExtension || softBullLateExtension);
    if(lateExtensionBlocked){
      const why=`HOLD · LATE EXTENSION · AI ${aiDir} ${(aiFav*100).toFixed(1)}% · ${regimeNow} · EMA21 ${emaDevNow.toFixed(2)} ATR · RSI ${rsiNow.toFixed(0)} · Stoch ${stNow.toFixed(0)} · ${continuationSetup?'setup continuation':'no fresh continuation setup'}${freshContinuation?' · fresh momentum':' · stale/mature leg'}`;
      trace('HOLD','AI_FIRST_EXTENSION_SHIELD',why); return {skip:true,reason:why};
    }

    // V24.1.72 MARKET-AWARE AUTHORITY GATE
    // The active symbol owns its trust state. TRAINED/ADVISORY can learn and
    // preview but cannot command AI-FIRST trades. VALIDATED needs two independent
    // real-context confirmations; TRUSTED needs one; AUTHORITY can stand alone.
    const marketTier=String(xgb.marketTrustTier||'TRAINED');
    const setupAgrees=!!setupSig && setupSig.dir===aiDir && Number(setupSig.str||0)>=68;
    const structureAgrees=structureNow===aiDir && structureNowConf>=0.58;
    const visionAgrees=vision?.direction===aiDir && Number(vision?.confidence||0)>=0.35;
    const priorAgrees=prior.direction===aiDir && fav(aiDir,clamp(prior.up))>=0.58;
    const realContextVotes=[setupAgrees,structureAgrees,visionAgrees,priorAgrees].filter(Boolean).length;
    if(marketTier==='TRAINED' || marketTier==='ADVISORY'){
      const why=`HOLD · XGB ${marketTier} ONLY · ${asset} market trust ${(Number(xgb.marketTrustAccuracy||0)*100).toFixed(1)}%/${Number(xgb.marketValidationSamples||0)} · raw ${xgb.rawUp==null?'—':(fav(xgb.rawDirection||aiDir,xgb.rawUp)*100).toFixed(1)+'%'} · calibrated ${(aiFav*100).toFixed(1)}%`;
      trace('HOLD','AI_MARKET_ADVISORY',why); return {skip:true,reason:why};
    }
    const neededMarketVotes=marketTier==='VALIDATED'?2:(marketTier==='TRUSTED'?1:0);
    if(realContextVotes<neededMarketVotes){
      const why=`HOLD · XGB ${marketTier} · ${asset} ${(Number(xgb.marketTrustAccuracy||0)*100).toFixed(1)}%/${Number(xgb.marketValidationSamples||0)} needs ${neededMarketVotes} market confirmation${neededMarketVotes===1?'':'s'} · got ${realContextVotes}`;
      trace('HOLD','AI_MARKET_TRUST_TIER',why); return {skip:true,reason:why};
    }

    // V24.1.62 LOOSE DEMO MODE: allow the trained AI to act earlier.
    // 55% is intentionally looser than the prior 58% gate for higher trade frequency.
    const MIN_AI_PROB=0.55;
    if(aiFav<MIN_AI_PROB){
      const why=`HOLD · AI EDGE TOO SMALL · ${aiDir} ${(aiFav*100).toFixed(1)}% < ${(MIN_AI_PROB*100).toFixed(0)}% · XGB ${xText}`;
      trace('HOLD','AI_FIRST',why); return {skip:true,reason:why};
    }
    if(exhausted && aiFav<0.60){
      const why=`HOLD · AI ${aiDir} ${(aiFav*100).toFixed(1)}% but EXTREME ENTRY LOCATION · RSI ${rsiNow.toFixed(0)} · Stoch ${stNow.toFixed(0)}`;
      trace('HOLD','AI_FIRST_RISK',why); return {skip:true,reason:why};
    }

    const confidence=aiFav;
    const why=`XGB-ONLY ${aiDir} ${(confidence*100).toFixed(1)}% · ${xgb.marketTrustTier||'VALIDATED'} ${asset} ${(Number(xgb.marketTrustAccuracy||0)*100).toFixed(1)}%/${Number(xgb.marketValidationSamples||0)} · setup ${setupText}`;
    const sig={dir:aiDir,mode:'ai-first-30s',tradeType:'AI_30S_PREDICTION',str:Math.round(aiEdge*200),confidence,tqs:aiDir==='BUY'?Number(ind?.tqsBuy||0):Number(ind?.tqsSell||0),reason:why,
      reasons:['30s XGBoost probability','XGBoost-only predictive authority','market-specific trust/calibration','rules are HOLD-only'],
      measurement:{strategy:'XGB_ONLY_30S',ensembleUp,xgbUp:xUp,xgbRawUp:xgb.rawUp,indicatorUp:prior.up,xgbValidationAccuracy:Number(xgb.validationAccuracy||0),xgbValidationSamples:Number(xgb.validationSamples||0),xgbMarketTrustTier:xgb.marketTrustTier,xgbMarketTrustAccuracy:Number(xgb.marketTrustAccuracy||0),xgbMarketValidationSamples:Number(xgb.marketValidationSamples||0),xgbMarketReliability:Number(xgb.marketReliability||0),xgbMarketProfileSamples:Number(xgb.marketProfileSamples||0),mq,setupContext:setupText}};
    trace(aiDir,'AI_FIRST_30S',why); aiLog('AI_ENTRY',{asset,dir:aiDir,controller:'AI_FIRST_30S',why},true);
    return {sig,reason:why};
  }

  // ════════════════════════════════════════════════════════════
  //  V24.1.97 — MICRO ENTRY CONFIRMATION
  //  Keeps only a tiny rolling tick window in RAM. It does NOT store raw ticks
  //  in AI exports or on disk. A qualified setup waits briefly, then the latest
  //  1–3 second Pocket Option movement may SUPPORT, stay NEUTRAL, or strongly
  //  CONTRADICT the requested direction. Only strong contradiction cancels.
  // ════════════════════════════════════════════════════════════
  const MICRO_BUFFER_MS = 12000;
  const MICRO_MAX_TICKS = 500;
  const MICRO_CONFIRM_MIN_MS = 650;
  const MICRO_CONFIRM_MAX_MS = 1800;
  const microTicksByAsset = Object.create(null);
  const microPendingByAsset = Object.create(null);
  const microLastAssessment = Object.create(null);

  function microRecordTick(asset, price, atMs=Date.now()) {
    if (!asset || !Number.isFinite(Number(price))) return;
    const now = Number(atMs) || Date.now();
    const buf = microTicksByAsset[asset] || (microTicksByAsset[asset] = []);
    buf.push({t:now,p:Number(price)});
    const cutoff = now - MICRO_BUFFER_MS;
    while (buf.length && (buf[0].t < cutoff || buf.length > MICRO_MAX_TICKS)) buf.shift();
  }

  function microPriceAtOrBefore(buf, target, fallback) {
    for (let i=buf.length-1;i>=0;i--) if (buf[i].t <= target) return buf[i].p;
    return fallback;
  }

  function microSampleAtOrBefore(buf, target) {
    for (let i=buf.length-1;i>=0;i--) {
      if (buf[i].t <= target) return buf[i];
    }
    return null;
  }

  function microAssess(asset, dir) {
    const buf = microTicksByAsset[asset] || [];
    const now = Date.now();
    const lastObj = buf.at(-1) || null;
    const last = Number(lastTickPrice[asset] || lastObj?.p || 0);
    if (!last || buf.length < 5) return {state:'NEUTRAL',reason:'micro data building',ticks:buf.length};

    const atr = Math.max(Math.abs(Number(lastIndicatorCtx[asset]?.ctx?.atr || 0)), Math.abs(last)*1e-8, 1e-12);
    const sign = String(dir).toUpperCase()==='SELL' ? -1 : 1;

    // V206: sample three distinct historical anchors. Do NOT substitute the
    // oldest tick when an interval is missing; that was causing 1s/2s/3s
    // readings to collapse into effectively the same measurement.
    const s1 = microSampleAtOrBefore(buf, now-1000);
    const s2 = microSampleAtOrBefore(buf, now-2000);
    const s3 = microSampleAtOrBefore(buf, now-3000);

    if (!s1 || !s2 || !s3 || !(s1.t > s2.t && s2.t > s3.t)) {
      return {state:'NEUTRAL',reason:'micro intervals not distinct',ticks:buf.length,at:now};
    }

    // Reject stale anchors. Each sample should represent roughly its intended
    // second, not a many-seconds-old fallback point.
    const lag1=Math.abs((now-1000)-s1.t);
    const lag2=Math.abs((now-2000)-s2.t);
    const lag3=Math.abs((now-3000)-s3.t);
    if (lag1>900 || lag2>1100 || lag3>1300) {
      return {state:'NEUTRAL',reason:'micro intervals sparse',ticks:buf.length,lag1,lag2,lag3,at:now};
    }

    const p0=last, p1=Number(s1.p), p2=Number(s2.p), p3=Number(s3.p);

    // Independent one-second segments in the trade direction.
    const seg1=((p0-p1)/atr)*sign;   // newest second
    const seg2=((p1-p2)/atr)*sign;   // prior second
    const seg3=((p2-p3)/atr)*sign;   // oldest second

    // Cumulative windows retained for diagnostics/backward compatibility.
    const r1=seg1;
    const r2=seg1+seg2;
    const r3=seg1+seg2+seg3;

    const recent = buf.filter(x=>x.t>=now-3000);
    let up=0,down=0;
    for(let i=1;i<recent.length;i++) {
      const d=recent[i].p-recent[i-1].p;
      if(d>0) up++; else if(d<0) down++;
    }
    const moves=up+down;
    const rawImbalance=moves ? (up-down)/moves : 0;
    const imbalance=rawImbalance*sign;

    // True acceleration compares consecutive independent segments.
    const accel12=seg1-seg2;
    const accel23=seg2-seg3;
    const freshResume = seg1>0.018 && (seg1>seg2-0.01) && accel12>-0.025;
    const deceleratingHard = seg1<0 || accel12<-0.07;

    const against=[
      seg1<-0.025,
      seg2<-0.045,
      r2<-0.07,
      r3<-0.10,
      imbalance<-0.22,
      deceleratingHard
    ].filter(Boolean).length;

    const support=[
      seg1>0.018,
      seg2>-0.015,
      r2>0.035,
      r3>0.055,
      imbalance>0.10,
      freshResume,
      accel12>0.015
    ].filter(Boolean).length;

    const strongContradiction =
      against>=3 ||
      (seg1<-0.04 && imbalance<-0.12) ||
      (r2<-0.10 && seg1<0);

    // SUPPORT now requires a genuinely fresh newest segment, not merely a
    // positive 3-second cumulative move.
    const strongSupport =
      !strongContradiction &&
      freshResume &&
      support>=4;

    const state = strongContradiction ? 'CONTRADICT' : (strongSupport ? 'SUPPORT' : 'NEUTRAL');

    return {
      state,dir:String(dir).toUpperCase(),ticks:recent.length,
      r1Atr:r1,r2Atr:r2,r3Atr:r3,
      seg1Atr:seg1,seg2Atr:seg2,seg3Atr:seg3,
      accel:accel12,accelPrev:accel23,imbalance,
      freshResume,support,against,
      lag1,lag2,lag3,
      at:now
    };
  }

  function clearMicroPending(asset, why='') {
    const q=microPendingByAsset[asset];
    if(q?.timer) clearTimeout(q.timer);
    delete microPendingByAsset[asset];
    if(why) aiLog('MICRO_CONFIRM_CLEAR',{asset,why},false);
  }

  function queueMicroConfirmation(asset, sig, tfKey, expiry, chartConfirmed) {
    if (!isRunning || window.__poatStopped) return false;
    if (!asset || !sig?.dir) return false;
    if (microPendingByAsset[asset]) return false;
    const now=Date.now();
    microPendingByAsset[asset]={asset,sig,tfKey,expiry,chartConfirmed:!!chartConfirmed,queuedAt:now,timer:null};
    const initial=microAssess(asset,sig.dir);
    microLastAssessment[asset]=initial;
    sendStatus(`⏱ ENTRY CHECK · ${asset} ${sig.dir} · micro ${initial.state}`);
    const timer=setTimeout(()=>processMicroConfirmation(asset,true),MICRO_CONFIRM_MAX_MS+40);
    microPendingByAsset[asset].timer=timer;
    aiLog('MICRO_CONFIRM_QUEUED',{asset,dir:sig.dir,initial},false);
    return true;
  }

  function processMicroConfirmation(asset, force=false) {
    if (!isRunning || window.__poatStopped) { clearMicroPending(asset,'bot stopped'); return false; }
    const q=microPendingByAsset[asset];
    if(!q || (!multiAssetMode && tradePending) || (multiAssetMode && !canOpenAnotherTrade(asset))) return false;
    const age=Date.now()-q.queuedAt;
    if(age<MICRO_CONFIRM_MIN_MS && !force) return false;
    const m=microAssess(asset,q.sig.dir);
    microLastAssessment[asset]=m;
    // Strong support may enter as soon as the minimum watch window completes.
    if(m.state==='SUPPORT' && age>=MICRO_CONFIRM_MIN_MS) {
      clearMicroPending(asset);
      aiLog('MICRO_CONFIRM_PASS',{asset,dir:q.sig.dir,age,state:m.state,metrics:m},false);
      sendStatus(`✅ ENTRY CHECK · ${asset} ${q.sig.dir} · micro support`);
      return fireTrade(q.asset,q.sig,q.tfKey,q.expiry,q.chartConfirmed,true,m);
    }
    // Strong contradiction is allowed a short chance to recover, then cancels.
    if(m.state==='CONTRADICT' && (age>=1200 || force)) {
      clearMicroPending(asset);
      aiLog('MICRO_CONFIRM_BLOCK',{asset,dir:q.sig.dir,age,metrics:m},true);
      lastDebugReason=`MICRO BLOCK · ${q.sig.dir} contradicted by live 1–3s movement`;
      sendStatus(`⛔ ENTRY CHECK · ${asset} ${q.sig.dir} cancelled · live movement reversed`);
      if (multiAssetMode) setTimeout(()=>processNextMultiChartTrade('micro-block'),50);
      return false;
    }
    // Legacy non-UNIFIED_MTF queue only. Unified MTF never comes through this
    // timer path; it performs its own immediate micro-data and contradiction checks.
    if(force || age>=MICRO_CONFIRM_MAX_MS) {
      clearMicroPending(asset);
      aiLog('MICRO_CONFIRM_NEUTRAL_PASS',{asset,dir:q.sig.dir,age,metrics:m},false);
      sendStatus(`✅ ENTRY CHECK · ${asset} ${q.sig.dir} · neutral · setup retained`);
      return fireTrade(q.asset,q.sig,q.tfKey,q.expiry,q.chartConfirmed,true,m);
    }
    return false;
  }

  // ════════════════════════════════════════════════════════════
  //  SHARED SIGNAL LOGIC — compute signal for one asset
  //  Returns { asset, sig, tfKey, expiry } or null (no trade)
  // ════════════════════════════════════════════════════════════

  // ════════════════════════════════════════════════════════════
  //  V24.1.118 SELECTIVE SETUP EDGE — PAYOUT-AWARE / PAIR+REGIME+DIR
  //  Replaces the accumulated bootstrap/3-setup execution maze while preserving
  //  the proven bridge, warmup, indicator context, 15s stack, micro confirmation,
  //  AI feature collection, XGB/LGB training and trust protections.
  // ════════════════════════════════════════════════════════════
  const cleanCoreState = Object.create(null);

  // V118 setup-edge memory. The direction model still learns the canonical future
  // 30s market label, but execution permission is now earned by the exact setup:
  // asset + clean-core market class + setup family + direction.
  const V118_PAYOUT = 0.92;
  const V118_BREAK_EVEN_WR = 1 / (1 + V118_PAYOUT); // 52.0833% at 92% payout
  const V118_TARGET_WR = Math.max(0.56, V118_BREAK_EVEN_WR + 0.03);

  function v118WilsonLower(wins, n, z=1.645) {
    n=Number(n||0); wins=Number(wins||0);
    if(n<=0) return 0;
    const p=wins/n, z2=z*z, den=1+z2/n;
    const center=p+z2/(2*n);
    const spread=z*Math.sqrt((p*(1-p)+z2/(4*n))/n);
    return Math.max(0,(center-spread)/den);
  }


  function v118NormalizeFamily(family) {
    const f=String(family||'SETUP').toUpperCase();
    if(['TREND_RESUME','TREND_PULLBACK','MOMENTUM_CONTINUATION','TREND_FLOW','TREND_ALIGNMENT','HIGH_VALUE_RUNNER','CRYPTO_RUNNER_CONTINUATION'].includes(f)) return 'TREND_RESUME';
    if(f.includes('BREAKOUT')) return 'BREAKOUT_RETEST';
    if(f.includes('REVERS')) return 'CONFIRMED_REVERSAL';
    return f;
  }

  function v118EdgeKey(asset, marketClass, family, dir) {
    return [String(asset||'UNKNOWN'),String(marketClass||'*'),String(family||'SETUP'),String(dir||'*')].join('|');
  }

  function v118EnsureEdgeStats() {
    aiState.setupEdgeStats = aiState.setupEdgeStats || {};
    if(aiState._v118EdgeSeeded) return aiState.setupEdgeStats;
    // Seed the new persistent directional buckets from the most recent V117 paper
    // history so importing the existing 2k+ sample backup does not mean starting over.
    const recent=Array.isArray(aiState.paperSetupStats?.recent)?aiState.paperSetupStats.recent:[];
    for(const r of recent){
      const asset=String(r?.asset||''); const family=v118NormalizeFamily(r?.setup||'SETUP'); const dir=String(r?.dir||'');
      if(!asset || !['BUY','SELL'].includes(dir)) continue;
      const keys=[v118EdgeKey(asset,'*',family,dir),v118EdgeKey(asset,'*',family,'*')];
      for(const key of keys){
        const st=aiState.setupEdgeStats[key]||(aiState.setupEdgeStats[key]={n:0,wins:0,losses:0,lastTs:0});
        st.n++; if(r?.win===true) st.wins++; else st.losses++; st.lastTs=Math.max(Number(st.lastTs||0),Number(r?.t||0));
      }
    }
    aiState._v118EdgeSeeded=true;
    return aiState.setupEdgeStats;
  }

  function v118RecordSetupEdge(asset, marketClass, family, dir, win, ts) {
    family=v118NormalizeFamily(family);
    const stats=v118EnsureEdgeStats();
    const keys=[
      v118EdgeKey(asset,marketClass,family,dir),
      v118EdgeKey(asset,'*',family,dir),
      v118EdgeKey(asset,'*',family,'*')
    ];
    for(const key of keys){
      const st=stats[key]||(stats[key]={n:0,wins:0,losses:0,lastTs:0});
      st.n++; if(win)st.wins++; else st.losses++; st.lastTs=Number(ts||Date.now());
    }
  }

  function v118SetupPerformance(asset, marketClass, family, dir) {
    family=v118NormalizeFamily(family);
    const stats=v118EnsureEdgeStats();
    const exact=stats[v118EdgeKey(asset,marketClass,family,dir)]||{n:0,wins:0,losses:0};
    const directional=stats[v118EdgeKey(asset,'*',family,dir)]||{n:0,wins:0,losses:0};
    const familyAll=stats[v118EdgeKey(asset,'*',family,'*')]||{n:0,wins:0,losses:0};

    // V24.1.139 hierarchical evidence. Exact market-class buckets are useful, but
    // they are too noisy at 10-12 samples to override a much larger pair/setup
    // history. Require 20 exact observations before exact-regime authority; before
    // that, fall back to same-direction setup evidence, then pair/setup evidence.
    const src=exact.n>=20?exact:(directional.n>=12?directional:familyAll);
    const n=Number(src.n||0), wins=Number(src.wins||0), wr=n?wins/n:0;
    // Beta(4,4) still shrinks hot streaks toward 50%, but does not freeze a good
    // 10-20 trade bucket as aggressively as the old Beta(6,6) prior.
    const shrunk=(wins+4)/(n+8);
    const lower=v118WilsonLower(wins,n);
    return {n,wins,losses:Number(src.losses||Math.max(0,n-wins)),wr,shrunk,lower,
      evidence:exact.n>=20?'EXACT_REGIME':(directional.n>=12?'PAIR_SETUP_DIR':'PAIR_SETUP'),
      exactN:Number(exact.n||0),directionalN:Number(directional.n||0),familyN:Number(familyAll.n||0)};
  }

  function v118AdaptiveGate(asset, marketClass, family, dir, score, mq) {
    // V24.1.141: performance stats are TRACKING ONLY. They never force a valid
    // setup into paper-only or block demo/real execution. User account mode remains
    // the sole execution-mode choice; setup performance is retained for diagnostics.
    const perf=v118SetupPerformance(asset,marketClass,family,dir);
    const livePayoutPct=payoutPct(asset);
    const payout=(livePayoutPct>0&&livePayoutPct<=100)?livePayoutPct/100:V118_PAYOUT;
    const breakEven=1/(1+payout);
    const target=Math.max(0.56,breakEven+0.03);
    let tier='TRACKING';
    if(perf.n>=40 && perf.wr>=0.60) tier='PROVEN_TRACKING';
    else if(perf.n>=20 && perf.wr<breakEven-0.01) tier='WEAK_TRACKING';
    else if(perf.n>=12) tier='BUILDING_TRACKING';
    return {...perf,allow:true,tier,breakEven,target,payoutPct:livePayoutPct};
  }

  // V24.1.181 — THREE-STRATEGY FORWARD TEST
  // These are deliberately separate deterministic strategy families.  Every
  // qualified family is shadow-recorded at both 30s and 60s, even when another
  // family wins execution priority.  AI remains learning/telemetry only.
  const v181ShadowLast = Object.create(null);
  // V24.1.185 telemetry only: show whether each family is being evaluated/qualifying.
  // This does not approve, veto, score, or place trades.
  const v181StrategyTelemetry = {
    TREND_RESUME:{evaluated:0,qualified:0,lastQualifiedAt:0},
    EMA_RSI_PULLBACK:{evaluated:0,qualified:0,lastQualifiedAt:0},
    SR_FAILURE_TEST:{evaluated:0,qualified:0,lastQualifiedAt:0},
    DONCHIAN_KELTNER_SQUEEZE:{evaluated:0,qualified:0,lastQualifiedAt:0},
    LIQUIDITY_SWEEP_REVERSAL:{evaluated:0,qualified:0,lastQualifiedAt:0},
    BREAKOUT_RETEST:{evaluated:0,qualified:0,lastQualifiedAt:0}
  };
  function v181TelemetryEval(name, sig){
    const t=v181StrategyTelemetry[name]||(v181StrategyTelemetry[name]={evaluated:0,qualified:0,lastQualifiedAt:0});
    t.evaluated++;
    if(sig){ t.qualified++; t.lastQualifiedAt=Date.now(); }
    return sig;
  }

  function v181QueueStrategyShadow(asset, sig, entryPrice) {
    if (!sig) return null;
    const key = `${asset}|${sig.tradeType}|${sig.dir}`;
    const now = Date.now();
    // Do not count the same still-forming setup every 3-second scan as a new
    // independent signal.  One observation per family/direction every 20 sec.
    if (now - Number(v181ShadowLast[key] || 0) < 20000) return null;
    v181ShadowLast[key] = now;
    return queueShadowOutcomeComparison(asset, {...sig, shadowOnly:true}, entryPrice);
  }

  function v181Series(asset, tfKey) {
    const a=getAsset(asset);
    if(!a) return [];
    try { return getLiveTFView(a, tfKey)?.prices?.map(Number).filter(Number.isFinite) || []; }
    catch(_) { return []; }
  }

  // V24.1.189 — regime/structure helpers. Close-only because Pocket Option feed
  // storage is a closed-price series; no synthetic exchange volume is invented.
  function v189LinReg(prices, period=20){
    const a=prices.slice(-period); if(a.length<period) return {slope:0,fit:0,dev:0};
    const n=a.length, xm=(n-1)/2, ym=a.reduce((x,y)=>x+y,0)/n;
    let num=0,den=0; for(let i=0;i<n;i++){num+=(i-xm)*(a[i]-ym);den+=(i-xm)*(i-xm);}
    const slope=den?num/den:0, fit=ym+slope*((n-1)-xm), dev=a[n-1]-fit;
    return {slope,fit,dev};
  }
  function v189Chop(prices, period=14){
    const a=prices.slice(-(period+1)); if(a.length<period+1) return 50;
    let path=0; for(let i=1;i<a.length;i++) path+=Math.abs(a[i]-a[i-1]);
    const hi=Math.max(...a), lo=Math.min(...a), span=hi-lo;
    if(span<=0||path<=0) return 100;
    return Math.max(0,Math.min(100,100*Math.log10(path/span)/Math.log10(period)));
  }
  function v189SupertrendProxy(prices, period=10, mult=2.2){
    if(prices.length<period+3) return {dir:0,band:prices.at(-1)||0};
    const av=atr(prices,period)||1e-12, mid=ema(prices,period), cur=prices.at(-1);
    const upper=mid+mult*av, lower=mid-mult*av;
    const lr=v189LinReg(prices,period);
    const dir=(cur>mid&&lr.slope>0)?1:((cur<mid&&lr.slope<0)?-1:0);
    return {dir,band:dir>=0?lower:upper,upper,lower};
  }
  function v189ZigStructure(prices, depth=5, deviationAtr=3, backstep=1){
    if(prices.length<18) return {dir:0,label:'MIXED',lastHigh:null,lastLow:null};
    const av=atr(prices,14)||1e-12, piv=[];
    for(let i=depth;i<prices.length-depth;i++){
      const w=prices.slice(i-depth,i+depth+1), v=prices[i];
      if(v===Math.max(...w)) piv.push({i,v,t:'H'});
      if(v===Math.min(...w)) piv.push({i,v,t:'L'});
    }
    const f=[]; for(const q of piv){ if(!f.length||q.t!==f.at(-1).t){f.push(q);continue;} if((q.t==='H'&&q.v>f.at(-1).v)||(q.t==='L'&&q.v<f.at(-1).v)) f[f.length-1]=q; }
    const hs=f.filter(x=>x.t==='H').slice(-2), ls=f.filter(x=>x.t==='L').slice(-2);
    let dir=0,label='MIXED';
    if(hs.length===2&&ls.length===2){ if(hs[1].v>hs[0].v+0.05*av&&ls[1].v>ls[0].v+0.05*av){dir=1;label='HH_HL';} else if(hs[1].v<hs[0].v-0.05*av&&ls[1].v<ls[0].v-0.05*av){dir=-1;label='LH_LL';} }
    return {dir,label,lastHigh:hs.at(-1)?.v??null,lastLow:ls.at(-1)?.v??null,depth,deviationAtr,backstep};
  }
  function v189Context(asset){
    const p=v181Series(asset,'30s'); if(p.length<52) return null;
    const av=atr(p,14)||Math.abs(p.at(-1))*1e-6, lr=v189LinReg(p,24), chop=v189Chop(p,14), st=v189SupertrendProxy(p,10,2.2), zz=v189ZigStructure(p,5,3,1);
    const e13=ema(p,13),e48=ema(p,48), sep=(e13-e48)/Math.max(av,1e-12), slopeAtr=lr.slope/Math.max(av,1e-12);
    let state='MIXED';
    if(chop>=58) state='CHOP_RANGE';
    else if(st.dir===1&&sep>0.15&&slopeAtr>0.015) state='TREND_BULL';
    else if(st.dir===-1&&sep<-0.15&&slopeAtr<-0.015) state='TREND_BEAR';
    else if(chop<=48&&Math.abs(slopeAtr)>0.02) state='DIRECTIONAL';
    return {state,chop,supertrend:st,linreg:lr,zigzag:zz,atr:av,ema13:e13,ema48:e48,sepAtr:sep,slopeAtr};
  }


  // V24.1.201 — THREE-STEP ADAPTIVE MTF + ENTRY LOCATION / EXHAUSTION GUARD
  // Each relevant timeframe is reduced to three independent dimensions:
  //   1) TREND      — EMA structure/slope + ADX/DMI + ZigZag structure
  //   2) MOMENTUM   — RSI + MACD-style impulse + recent price acceleration
  //   3) VOLATILITY — ATR/chop + Bollinger/location/extension quality
  // The selected expiry owns the plan. The primary timeframe decides direction,
  // the higher timeframe confirms structure, and the faster timeframe times entry.
  // Faster data can delay an entry but can never reverse the structural direction.
  function v198FrameScore(asset, tfKey) {
    const p=v181Series(asset,tfKey);
    // V199: role-based warmup is enforced by the controller. A frame can
    // produce a useful read with 10+ closes, so a 30s trade no longer waits
    // ~26 minutes just to accumulate 26 one-minute candles.
    if(p.length<8) return {tf:tfKey,ready:false,n:p.length,trend:0,momentum:0,volatility:50,dir:'NEUTRAL'};
    const cur=p.at(-1), prev=p.at(-2), prev2=p.at(-3);
    const period=Math.min(14,Math.max(5,Math.floor(p.length/3)));
    const av=atr(p,period)||Math.max(Math.abs(cur)*1e-6,1e-12);
    const avLong=atr(p,Math.min(Math.max(period+3,8),Math.max(8,p.length-1)))||av;
    // Use 5/9/21 once enough history exists. During startup, compress the
    // periods proportionally so trend structure remains meaningful instead
    // of EMA(21) degenerating to the last price on a short higher-TF series.
    const slowP = p.length>=26 ? 21 : Math.max(9, Math.min(21, Math.floor(p.length*0.70)));
    const midP  = p.length>=26 ? 9  : Math.max(5, Math.min(slowP-2, Math.floor(slowP*0.55)));
    const fastP = p.length>=26 ? 5  : Math.max(3, Math.min(midP-1, Math.floor(midP*0.60)));
    const e5=ema(p,fastP), e9=ema(p,midP), e21=ema(p,slowP);
    const r=rsi(p,period);
    const rPrev=rsi(p.slice(0,-1),period);
    const lr=v189LinReg(p,Math.min(24,p.length-2));
    const dx=dmiAdx(p,period);
    const zz=v189ZigStructure(p,5,3,1);
    const emaSpread=(e5-e21)/Math.max(av,1e-12);
    const slope=lr.slope/Math.max(av,1e-12);

    // STEP 1 — TREND. Keep correlated EMA evidence from dominating by capping
    // the stack/spread contribution and adding independent DMI + structure reads.
    let trend=0;
    if(e5>e9&&e9>e21) trend+=34;
    else if(e5<e9&&e9<e21) trend-=34;
    trend+=Math.max(-18,Math.min(18,emaSpread*15));
    trend+=Math.max(-18,Math.min(18,slope*230));
    const adx=Number(dx?.adx||0), plus=Number(dx?.plusDI||0), minus=Number(dx?.minusDI||0);
    const dmiStrength=Math.min(16,Math.max(0,adx-12)*0.6);
    if(plus>minus+2) trend+=dmiStrength;
    else if(minus>plus+2) trend-=dmiStrength;
    if(zz.dir===1) trend+=10; else if(zz.dir===-1) trend-=10;
    trend=Math.max(-100,Math.min(100,trend));

    // STEP 2 — MOMENTUM. RSI gives state, its slope gives turn/resume, while
    // a MACD-style EMA impulse and two-candle acceleration capture immediacy.
    const e5Prev=ema(p.slice(0,-1),fastP), e13=ema(p,Math.max(midP+2,Math.min(slowP-1,13))), e13Prev=ema(p.slice(0,-1),Math.max(midP+2,Math.min(slowP-1,13)));
    const macdNow=(e5-e13)/Math.max(av,1e-12);
    const macdPrev=(e5Prev-e13Prev)/Math.max(av,1e-12);
    const impulse1=(cur-prev)/Math.max(av,1e-12);
    const impulse2=(cur-prev2)/Math.max(av,1e-12);
    let momentum=0;
    momentum+=Math.max(-28,Math.min(28,(r-50)*1.05));
    momentum+=Math.max(-16,Math.min(16,(r-rPrev)*2.2));
    momentum+=Math.max(-24,Math.min(24,macdNow*30));
    momentum+=Math.max(-12,Math.min(12,(macdNow-macdPrev)*55));
    momentum+=Math.max(-14,Math.min(14,impulse1*20));
    momentum+=Math.max(-10,Math.min(10,impulse2*9));
    momentum=Math.max(-100,Math.min(100,momentum));

    // STEP 3 — VOLATILITY / LOCATION QUALITY. This is intentionally unsigned:
    // it judges whether current conditions are tradable, not BUY vs SELL.
    const chop=v189Chop(p,Math.min(14,p.length-1));

    // V218 RANGE/CHOP DETECTOR — directional efficiency measures whether price
    // actually travels somewhere or merely oscillates back and forth.
    // 1.0 = nearly straight directional travel; 0.0 = heavy backtracking/chop.
    const effN=Math.min(14,p.length-1);
    const effSlice=p.slice(-(effN+1));
    let effPath=0;
    for(let i=1;i<effSlice.length;i++) effPath+=Math.abs(Number(effSlice[i])-Number(effSlice[i-1]));
    const effNet=effSlice.length>1?Math.abs(Number(effSlice.at(-1))-Number(effSlice[0])):0;
    const pathEfficiency=effPath>0?Math.max(0,Math.min(1,effNet/effPath)):0;

    const extension=Math.abs(cur-e21)/Math.max(av,1e-12);
    const atrRatio=av/Math.max(avLong,1e-12);
    const win=p.slice(-Math.min(20,p.length));
    const mean=win.reduce((a,b)=>a+b,0)/win.length;
    const sd=Math.sqrt(win.reduce((a,b)=>a+(b-mean)*(b-mean),0)/Math.max(1,win.length));
    const bandSigned=sd>0?(cur-mean)/(2*sd):0;
    const bandZ=Math.abs(bandSigned);
    const signedExtension=(cur-e21)/Math.max(av,1e-12);
    let volatility=72;
    if(chop>58) volatility-=Math.min(30,(chop-58)*1.45);
    else if(chop<48) volatility+=Math.min(10,(48-chop)*0.55);
    if(extension>1.55) volatility-=Math.min(28,(extension-1.55)*18);
    else if(extension>=0.18&&extension<=1.15) volatility+=7;
    if(bandZ>1.10) volatility-=Math.min(18,(bandZ-1.10)*18);
    if(atrRatio<0.55) volatility-=16;
    else if(atrRatio>2.20) volatility-=14;
    else if(atrRatio>=0.75&&atrRatio<=1.65) volatility+=6;
    if(adx>=18) volatility+=5;
    volatility=Math.max(0,Math.min(100,volatility));

    return {tf:tfKey,ready:true,n:p.length,trend,momentum,volatility,rsi:r,adx,
      plusDI:plus,minusDI:minus,emaSpreadAtr:emaSpread,slopeAtr:slope,extensionAtr:extension,
      atrRatio,chop,pathEfficiency,bandZ,bandSigned,signedExtension,zigzag:zz.label,periods:{fast:fastP,mid:midP,slow:slowP},dir:trend>=16?'BUY':trend<=-16?'SELL':'NEUTRAL'};
  }

  // Expiry-relative three-chart plan. 30s and 1m exactly follow the requested
  // hierarchy: 30s => 15s/30s/1m, 1m => 30s/1m/3m.
  function v197TimeframePlan(expirySec) {
    const e=Math.max(5,Number(expirySec||30));
    if(e<=5)   return {fast:'5s', primary:'5s', higher:'15s'};
    if(e<=15)  return {fast:'5s', primary:'15s', higher:'30s'};
    if(e<=30)  return {fast:'15s',primary:'30s', higher:'60s'};
    if(e<=60)  return {fast:'30s',primary:'60s', higher:'180s'};
    if(e<=120) return {fast:'60s',primary:'120s',higher:'300s'};
    if(e<=180) return {fast:'60s',primary:'180s',higher:'300s'};
    return {fast:'180s',primary:'300s',higher:'300s'};
  }


  function v203RecentTradeEdge(asset, dir, expirySec) {
    const wantDir=String(dir||'').toUpperCase();
    const wantExp=Math.max(5,Number(expirySec||botConfig?.timeframe||30));
    const rows=(tradeRecords||[]).filter(t=>{
      const r=String(t?.result||'').toLowerCase();
      if(r!=='win' && r!=='loss') return false;
      if(String(t?.asset||'')!==String(asset||'')) return false;
      if(String(t?.direction||'').toUpperCase()!==wantDir) return false;
      if(String(t?.strategyType||t?.marketClassAtEntry||'').toUpperCase()!=='UNIFIED_MTF') return false;
      return Number(t?.expiry||wantExp)===wantExp;
    }).slice(-24);
    const n=rows.length;
    const wins=rows.filter(t=>String(t.result).toLowerCase()==='win').length;
    const wr=n?wins/n:0.5;
    return {n,wins,losses:n-wins,wr};
  }

  function v208MicroReady(asset, dir) {
    const q=microAssess(asset,dir);
    const segmentsFinite =
      Number.isFinite(Number(q?.seg1Atr)) &&
      Number.isFinite(Number(q?.seg2Atr)) &&
      Number.isFinite(Number(q?.seg3Atr));
    const missing =
      !q ||
      q.reason==='micro intervals not distinct' ||
      q.reason==='micro intervals sparse' ||
      q.reason==='micro data building' ||
      !segmentsFinite;
    return {ready:!missing,q:q||null};
  }

  function v203MicroQuality(asset, dir, assessment=null) {
    const q=assessment || microAssess(asset,dir);
    if(!q || q.state==='NEUTRAL' || q.state==='BYPASS')
      return {score:50,bonus:0,block:false,state:q?.state||'NEUTRAL',raw:q||null};
    if(q.state==='SUPPORT') {
      const strength=Math.min(10,
        2+Number(q.support||0)*1.25+
        Math.max(0,Number(q.imbalance||0))*6+
        Math.max(0,Number(q.accel||0))*10);
      return {score:Math.min(100,66+strength),bonus:Math.min(4,Math.round(strength/3)),block:false,state:'SUPPORT',raw:q};
    }
    const severe =
      Number(q.against||0)>=4 ||
      Number(q.seg1Atr||0)<-0.05 ||
      (Number(q.r2Atr||0)<-0.10 && Number(q.seg1Atr||0)<0);
    const penalty=Math.min(14,
      5+Number(q.against||0)*1.6+
      Math.max(0,-Number(q.imbalance||0))*7+
      Math.max(0,-Number(q.accel||0))*8);
    return {score:Math.max(0,40-penalty),bonus:-Math.min(7,Math.round(penalty/2)),block:severe,state:'CONTRADICT',raw:q};
  }



  function v206FastReclaim(asset, fastTf, dir) {
    const p=v181Series(asset,fastTf);
    if(!p || p.length<7) return {ok:false,reason:'fast history building',n:p?.length||0};

    const d=String(dir||'').toUpperCase();
    const a=p.map(Number).filter(Number.isFinite);
    const cur=a.at(-1), p1=a.at(-2), p2=a.at(-3), p3=a.at(-4);
    const av=Math.max(atr(a,Math.min(7,a.length-1))||0,Math.abs(cur)*1e-8,1e-12);

    const e5=ema(a,Math.min(5,a.length));
    const e5Prev=ema(a.slice(0,-1),Math.min(5,a.length-1));
    const e9=ema(a,Math.min(9,a.length));
    const e9Prev=ema(a.slice(0,-1),Math.min(9,a.length-1));

    const latestMove=(cur-p1)/av;
    const priorMove=(p1-p2)/av;
    const olderMove=(p2-p3)/av;

    if(d==='BUY'){
      const hadPullback =
        p1<=e5Prev+0.12*av ||
        priorMove<0 ||
        olderMove<0;
      const reclaimed =
        cur>e5 &&
        cur>p1 &&
        e5>=e9-0.08*av;
      const notChasing =
        latestMove<0.85 &&
        (cur-e5)/av<0.70;
      return {
        ok:hadPullback&&reclaimed&&notChasing,
        hadPullback,reclaimed,notChasing,
        latestMove,priorMove,olderMove,
        price:cur,ema5:e5,ema9:e9,ema5Prev:e5Prev,ema9Prev:e9Prev,
        reason:!hadPullback?'no 15s pullback':(!reclaimed?'no 15s EMA reclaim':(!notChasing?'15s BUY chase':'BUY reclaim')),
        n:a.length
      };
    } else {
      const hadPullback =
        p1>=e5Prev-0.12*av ||
        priorMove>0 ||
        olderMove>0;
      const rejected =
        cur<e5 &&
        cur<p1 &&
        e5<=e9+0.08*av;
      const notChasing =
        latestMove>-0.85 &&
        (e5-cur)/av<0.70;
      return {
        ok:hadPullback&&rejected&&notChasing,
        hadPullback,rejected,notChasing,
        latestMove,priorMove,olderMove,
        price:cur,ema5:e5,ema9:e9,ema5Prev:e5Prev,ema9Prev:e9Prev,
        reason:!hadPullback?'no 15s pullback':(!rejected?'no 15s EMA rejection':(!notChasing?'15s SELL chase':'SELL rejection')),
        n:a.length
      };
    }
  }

  function v205EntryState(primary, fast, dir) {
    const d=String(dir||'').toUpperCase();
    const side=d==='BUY'?1:-1;
    const rsi=Number(primary?.rsi||50);
    const directionalRsi=d==='BUY'?rsi:(100-rsi);
    const sideExtension=Number(primary?.signedExtension||0)*side;
    const sideBand=Number(primary?.bandSigned||0)*side;
    const fastAligned=Number(fast?.momentum||0)*side;
    const primaryAligned=Number(primary?.momentum||0)*side;

    const stretched =
      sideExtension>0.72 ||
      sideBand>0.88 ||
      directionalRsi>68;

    const exhausted =
      directionalRsi>78 ||
      sideExtension>1.28 ||
      sideBand>1.18 ||
      (directionalRsi>72 && sideExtension>0.88) ||
      (directionalRsi>72 && sideBand>0.98);

    // A good short-expiry continuation should resume after a pullback. On a
    // stretched setup, require positive fast-frame resumption, but reject an
    // already vertical fast burst because that is usually a chase entry.
    const resume =
      fastAligned>=6 &&
      primaryAligned>=8 &&
      fastAligned<=58;

    return {
      stretched,exhausted,resume,
      directionalRsi,sideExtension,sideBand,fastAligned,primaryAligned
    };
  }

  // V24.1.281 — CONVICTION GATE helper. Reads the SAME per-asset indicator state that
  // captureSnapshot() records (indicatorStateByAsset[asset] || lastIndicators) so this
  // rule reproduces the historical post-mortem exactly. Returns a reason to BLOCK, or
  // null to allow. It is deliberately loose: only three proven-losing buckets.
  function v281ConvictionBlock(dir, assetName, setup) {
    if (!V281_CONVICTION_ENABLED || !dir) return null;
    // V24.1.282 — FAMILY SCOPE. The three V281 rules were measured on the
    // DIRECTIONAL (UNIFIED_MTF) population of the 1004-trade log. They are
    // momentum-continuation rules and are structurally WRONG for the V227
    // range-reversal (mean-reversion) family: "no counter-trend long in a bear
    // regime" forbids the exact dip-buy the range controller is designed to
    // take. Exempt RANGE_REVERSAL so the gate never fights the wrong engine.
    if (['RANGE_REVERSAL','V283_SIMPLE_30S'].includes(String(setup || '').toUpperCase())) return null;
    const key = String(assetName || activeAsset || '');
    const ind = indicatorStateByAsset[key] || lastIndicators || {};
    const regime = String(ind.regime || '').toUpperCase();
    const rsi = Number(ind.rsi);
    const sellScore = Number(ind.sellScore || 0);
    // 1) Counter-trend LONG while the legacy regime says BEAR (hist WR 39.7%, n=58).
    if (regime === 'TRENDING_BEAR' && dir === 'BUY')
      return `V281 CONVICTION · L${V281_CONVICTION_LEVEL} · counter-trend long in bear regime (hist WR 39.7%)`;
    // 2) SHORT while oversold RSI<30 (hist WR 44.4%, n=187).
    if (dir === 'SELL' && Number.isFinite(rsi) && rsi < 30)
      return `V281 CONVICTION · L${V281_CONVICTION_LEVEL} · oversold short · RSI ${rsi.toFixed(1)}<30 (hist WR 44.4%)`;
    // 3) LEVEL 2 only: bull-regime LONG that is a breakout tail, not a dip — require
    //    measurable pullback pressure (sellScore>=3) (hist WR ~47% without it).
    if (V281_CONVICTION_LEVEL >= 2 && regime === 'TRENDING_BULL' && dir === 'BUY' && sellScore < V281_PULLBACK_MIN_SELL)
      return `V281 CONVICTION · L2 · bull long without pullback · sellScore ${sellScore.toFixed(0)}<${V281_PULLBACK_MIN_SELL} (hist WR ~47%)`;
    return null;
  }

  function v194UnifiedSignal(asset, px) {
    const expiry=Math.max(5,parseInt(botConfig?.timeframe||30,10));
    const plan=v197TimeframePlan(expiry);
    const frames={};
    for(const tf of ['5s','15s','30s','60s','120s','180s','300s']) frames[tf]=v198FrameScore(asset,tf);
    const fast=frames[plan.fast], primary=frames[plan.primary], higher=frames[plan.higher];
    // V233: every decision also reads the complete 5s→5m ladder. Short frames
    // identify the turn/entry; 60s/120s/180s/300s determine whether that turn
    // is a pullback inside a larger trend or a genuine multi-frame reversal.
    const f5=frames['5s'], f15=frames['15s'], f30=frames['30s'], f60=frames['60s'], f120=frames['120s'], f180=frames['180s'], f300=frames['300s'];
    const longFrames=[f60,f120,f180,f300].filter(Boolean);
    const longWeights=[0.40,0.27,0.20,0.13];
    const longTrend=longFrames.reduce((z,f,i)=>z+Number(f.trend||0)*(longWeights[i]||0),0);
    const longMomentum=longFrames.reduce((z,f,i)=>z+Number(f.momentum||0)*(longWeights[i]||0),0);
    const longBull=longFrames.filter(f=>Number(f.trend||0)>12).length;
    const longBear=longFrames.filter(f=>Number(f.trend||0)<-12).length;
    const longConsensus=longBull-longBear;

    // Always publish the current three-step read, including HOLD states. This
    // feeds the popup so Trend/Momentum/Volatility are visible before a trade.
    const publish=(extra={})=>{
      lastIndicators.threeStep={
        version:'V233', expiry, plan, frames, longContext:{longTrend,longMomentum,longBull,longBear,longConsensus},
        fastN:fast?.n||0, primaryN:primary?.n||0, higherN:higher?.n||0,
        ...extra, ts:Date.now()
      };
    };
    const reject=(reason,extra={})=>{
      lastIndicators.v194HoldReason=reason;
      publish({state:'HOLD',reason,...extra});
      return null;
    };
    lastIndicators.v194HoldReason='';

    // Role-based startup requirements. Higher-TF context needs fewer closes
    // than the primary decision frame; fast timing gets enough samples to avoid
    // reacting to a couple of noisy candles.
    const fastNeed=8, primaryNeed=8, higherNeed=8;
    if(!fast?.ready || (fast?.n||0)<fastNeed || !primary?.ready || (primary?.n||0)<primaryNeed || !higher?.ready || (higher?.n||0)<higherNeed)
      return reject(`V218 MTF warmup · ${plan.fast} ${fast?.n||0}/${fastNeed} · ${plan.primary} ${primary?.n||0}/${primaryNeed} · ${plan.higher} ${higher?.n||0}/${higherNeed}`,
        {warmup:{fastNeed,primaryNeed,higherNeed}});

    // V218 MARKET CLASSIFIER — reject sideways oscillation BEFORE the runner
    // engine gets a direction. EMA alignment alone is not a trend.
    //
    // We require evidence of persistent travel using independent measurements:
    // ADX (trend persistence), Choppiness Index, and path efficiency
    // (net displacement / total traveled distance). This specifically prevents
    // a single upswing inside a range from being promoted to TRENDING_BULL.
    const pAdx=Number(primary.adx||0);
    const hAdx=Number(higher.adx||0);
    const pChop=Number(primary.chop||50);
    const hChop=Number(higher.chop||50);
    const pEff=Number(primary.pathEfficiency||0);
    const hEff=Number(higher.pathEfficiency||0);

    const weakPersistence = pAdx < 23;
    const backtracking = pEff < 0.35;
    const severeBacktracking = pEff < 0.20;
    const choppyStructure = pChop > 55;
    const higherNotConfirmingTrend = hAdx < 20 && hEff < 0.35;

    const rangeChop =
      (weakPersistence && backtracking) ||
      (severeBacktracking && choppyStructure) ||
      (backtracking && choppyStructure && higherNotConfirmingTrend);

    // V222: do not force a continuation through a range. Hand RANGE/CHOP to
    // the dedicated mean-reversion controller below instead of simply sitting
    // out thousands of evaluations or treating range oscillation as a trend.
    if(rangeChop)
      return reject(`RANGE/CHOP · route to range reversal · ADX ${pAdx.toFixed(1)} · efficiency ${(pEff*100).toFixed(0)}% · chop ${pChop.toFixed(1)}`,
        {marketClass:'RANGE_CHOP',pAdx,hAdx,pChop,hChop,pEff,hEff,weakPersistence,backtracking,severeBacktracking,choppyStructure,higherNotConfirmingTrend});

    // STEP 1 — TREND. Primary owns direction; higher-TF context confirms it.
    const pTrend=Number(primary.trend||0), hTrend=Number(higher.trend||0);
    const structuralSigned=pTrend*0.58+hTrend*0.12+longTrend*0.30;
    // V24.1.282 — participation floor: the structural edge need relaxes from ±10
    // to ±8 (TIER 1) then ±6 (TIER 2) after a long consecutive-HOLD streak. This
    // only widens the ENTRY threshold; the DANGER guards, payout floor, V276
    // momentum veto and score floor below are all unchanged.
    const v282tierDir=v282Tier(v282AssetKey(asset));
    const structuralNeed=Math.max(4,10-v282tierDir*V282_DIR_STRUCTURAL_RELAX);
    let dir=structuralSigned>=structuralNeed?'BUY':structuralSigned<=-structuralNeed?'SELL':null;
    if(!dir) return reject(`SCORE · no directional edge · ${plan.primary}/${plan.higher} ${structuralSigned.toFixed(1)} needs ±${structuralNeed}`,{pTrend,hTrend,structuralSigned,structuralNeed,v282tier:v282tierDir});

    // V208: unified structure is the direction authority. The old
    // `lastIndicators.regime` comes from the legacy context strategy and was
    // observed to disagree with the unified 30s/60s structure (for example,
    // both MTF frames bearish while legacy regime said TRENDING_BULL).
    // Keep it only as telemetry; it must not veto the unified decision.
    const liveRegime=String(lastIndicators?.regime||'').toUpperCase();

    const side=dir==='BUY'?1:-1;
    const pAligned=pTrend*side, hAligned=hTrend*side;
    const longAligned=longTrend*side, longMomentumAligned=longMomentum*side;

    // ── V24.1.280 — PAYOUT-AWARE ENTRY FLOOR ─────────────────────────────────
    // Only fires once a genuine directional candidate exists (post-direction), so it
    // never floods HOLD telemetry but always blocks a real entry when the live payout
    // is below the floor. The grid auto-switch (AUTO_SWITCH_BELOW_PCT=92) normally
    // rotates such a chart away first; this is the residual backstop. Disable by
    // setting V280_PAYOUT_FLOOR_PCT = 0 at the top of this file.
    const livePayoutForEntry=payoutPct(asset?.__assetName || activeAsset || '');
    if(V280_PAYOUT_FLOOR_PCT>0 && livePayoutForEntry>0 && livePayoutForEntry<V280_PAYOUT_FLOOR_PCT) {
      const beWr=100/(1+livePayoutForEntry/100);
      return reject(`V280 PAYOUT FLOOR · live payout ${livePayoutForEntry.toFixed(1)}% < ${V280_PAYOUT_FLOOR_PCT}% · break-even WR ${beWr.toFixed(1)}% · ${dir} skipped`,
        {dir,pTrend,hTrend,pAligned,hAligned,structuralSigned,livePayoutPct:livePayoutForEntry,breakEvenWr:beWr,payoutFloor:V280_PAYOUT_FLOOR_PCT});
    }

    // ── V24.1.281 — CONVICTION GATE (directional) ─────────────────────────────
    // Blocks only the three historically-negative buckets (see top of file). Placed
    // AFTER the V280 payout check (payout is the strongest lever) and BEFORE the
    // DANGER/location guards so the surfaced HOLD reason is the strongest structural
    // one. At LEVEL 2 it keeps ~56% of historical trade volume; LEVEL 1 keeps ~76%.
    const v281Reason=v281ConvictionBlock(dir, asset?.__assetName || activeAsset || '');
    if(v281Reason) return reject(v281Reason,
      {dir,pTrend,hTrend,structuralSigned,conviction:'V281',convictionLevel:V281_CONVICTION_LEVEL});

    if(pAligned<-12) return reject(`DANGER · ${plan.primary} structure strongly opposes trade · ${pAligned.toFixed(1)}`,{dir,pTrend,hTrend,pAligned,hAligned,structuralSigned});
    if(hAligned<-35 && longAligned<-20) return reject(`DANGER · higher-timeframe ladder severely conflicts · ${hAligned.toFixed(1)} / long ${longAligned.toFixed(1)}`,{dir,pTrend,hTrend,pAligned,hAligned,structuralSigned});
    const trendQuality=Math.max(0,Math.min(100,52+pAligned*0.30+Math.max(-25,hAligned)*0.10+Math.max(-30,longAligned)*0.18));

    // STEP 2 — MOMENTUM. Primary momentum matters most. The fast frame is a
    // timing layer only: a normal pullback can delay or lower confidence but it
    // cannot reverse the structural direction by itself.
    const fastAligned=Number(fast.momentum||0)*side;
    const primaryAligned=Number(primary.momentum||0)*side;
    // V228: ordinary opposite momentum is a score/timing penalty, not a pre-score HOLD.
    // Only an extreme simultaneous 15s + 30s contradiction remains a safety veto.
    if(primaryAligned<-55 && fastAligned<-55) return reject(`DANGER · severe ${plan.fast}/${plan.primary} momentum contradiction · ${fastAligned.toFixed(1)}/${primaryAligned.toFixed(1)}`,
      {dir,trendQuality,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned});
    const momentumSigned=primaryAligned*0.80+fastAligned*0.20;
    const momentumQuality=Math.max(0,Math.min(100,55+momentumSigned*0.48));

    // STEP 3 — VOLATILITY / LOCATION. This is quality, never direction.
    let volatilityQuality=Math.round(Number(primary.volatility||0)*0.65+Number(higher.volatility||0)*0.25+Number(fast.volatility||0)*0.10);

    // V201 ENTRY LOCATION / EXHAUSTION GUARD. Trend strength is not the same
    // as entry quality. A 30s BUY at the top of an already stretched bullish
    // impulse (or SELL at the bottom of a stretched bearish impulse) is a poor
    // short-expiry location even when every trend indicator agrees. This guard
    // is symmetric and ATR-normalized so it remains portable across markets
    // and selected expiries.
    const signedExt=Number(primary.signedExtension||0);
    const sideExtension=signedExt*side; // positive = stretched in trade direction
    const sideBand=Number(primary.bandSigned||0)*side;
    const directionalRsi=dir==='BUY'?Number(primary.rsi||50):(100-Number(primary.rsi||50));

    // V228 — LOCATION/TIMING ARE SCORED BEFORE HOLD. Exhaustion, stretch,
    // pullback momentum and ordinary fast-frame disagreement reduce the final
    // weighted score instead of erasing it. This lets forensic history show
    // HOLD 58 -> 61 -> 63 -> READY 66 as timing improves.
    const entryState=v205EntryState(primary,fast,dir);
    const fastTrigger=v206FastReclaim(asset,plan.fast,dir);

    let locationPenalty=0;
    let timingPenalty=0;
    let momentumPenalty=0;
    let locationState='HEALTHY';

    if(sideExtension>0.90) locationPenalty+=Math.min(18,(sideExtension-0.90)*20);
    if(sideBand>0.90) locationPenalty+=Math.min(12,(sideBand-0.90)*20);
    if(directionalRsi>74) locationPenalty+=Math.min(12,(directionalRsi-74)*0.8);
    if(entryState.exhausted) locationPenalty+=10;
    if(entryState.stretched && !fastTrigger.ok) timingPenalty+=8;
    if(!entryState.stretched && fastTrigger.n>=7 && !fastTrigger.notChasing) timingPenalty+=7;
    if(primaryAligned<0) momentumPenalty+=Math.min(10,Math.abs(primaryAligned)*0.18);
    if(fastAligned<0) timingPenalty+=Math.min(9,Math.abs(fastAligned)*0.16);
    if(hAligned<0) locationPenalty+=Math.min(8,Math.abs(hAligned)*0.12);

    if(locationPenalty>=18) locationState='EXHAUSTED';
    else if(locationPenalty>=10) locationState='STRETCHED';
    else if(locationPenalty>=5) locationState='CAUTION';

    volatilityQuality=Math.max(0,Math.round(volatilityQuality-Math.min(18,locationPenalty*0.45)));

    // V208 — MICRO ENTRY QUALITY. Distinct micro data is required, but its
    // directional state is separate: SUPPORT adds a small bonus, NEUTRAL is
    // allowed, and only strong CONTRADICT can veto.
    // V209: micro samples never gate a qualified rules setup. If valid micro
    // exists, use it as a small quality adjustment; if not, remain neutral.
    const microReady=v208MicroReady(asset,dir);
    const microQuality=v203MicroQuality(asset,dir,microReady.ready?microReady.q:null);
    if(microQuality.block && primaryAligned<10 && Number(microQuality.raw?.seg1Atr||0)<-0.35)
      return reject(`MICRO · ${dir} contradicted · seg1 ${Number(microQuality.raw?.seg1Atr||0).toFixed(2)} ATR · seg2 ${Number(microQuality.raw?.seg2Atr||0).toFixed(2)} ATR`,
        {dir,trendQuality,momentumQuality,volatilityQuality,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,
         microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw,fastTrigger});

    // V205 — keep recent pair/direction results for diagnostics only. The V204
    // rolling penalty experiment reacted after the losing sequence had already
    // happened, so live permission is based on current structure/location.
    const recentEdge=v203RecentTradeEdge(asset,dir,expiry);

    // V223 WEIGHTED SCORE ENGINE — independent evidence categories add to 100.
    // Ordinary disagreement costs points instead of creating another HOLD gate.
    // Only genuine danger conditions above remain hard vetoes.
    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const structurePts=clamp(Math.round(7 + pAligned*0.15 + Math.max(-15,hAligned)*0.05 + Math.max(-25,longAligned)*0.10),0,25);
    const momentumPts=clamp(Math.round(7 + primaryAligned*0.10 + fastAligned*0.04 - momentumPenalty),0,15);
    let timingPts=clamp(Math.round(10 + fastAligned*0.10),0,16);
    if(fastTrigger.ok) timingPts+=4;
    else if(fastTrigger.n>=7 && fastTrigger.notChasing) timingPts+=1;
    timingPts=clamp(Math.round(timingPts-timingPenalty),0,20);
    const contextPts=clamp(Math.round(5 + hAligned*0.035 + longAligned*0.055 + longMomentumAligned*0.015),0,10);
    const boundaryPts=clamp(Math.round(15-Math.min(15,locationPenalty)),0,15);
    let priceActionPts=clamp(Math.round(5 + primaryAligned*0.04 + fastAligned*0.03),0,8);
    if(fastTrigger.ok) priceActionPts+=2;
    priceActionPts=clamp(priceActionPts,0,10);
    const volatilityPts=clamp(Math.round(volatilityQuality/20),0,5);
    const predictiveAI=v231PredictiveEvidence(asset?.__assetName || activeAsset || '',px,dir);
    // ── V24.1.279 — AI AUTHORITY RECONCILIATION ──
    // Earlier builds declared "AI execution authority: false" in telemetry while
    // predictiveAI.points was silently added to the live confidence score. That
    // contradiction is resolved with an asymmetric, earned-authority rule:
    //   • NEGATIVE points (model argues AGAINST this entry) always apply — a weak
    //     model may still veto a bad trade; this direction is protective.
    //   • POSITIVE points (model argues FOR this entry) apply only once the 30s
    //     shadow model has earned authority: >=40 resolved labels AND a raw
    //     hit-rate >= 0.55 (above the 92%-payout break-even 52.08%).
    // Until then AI stays learning-only and contributes exactly 0 supportive
    // points, so per-trade telemetry now matches real behaviour.
    const aiPredictiveRaw=Number(predictiveAI.points||0);
    const aiPredictiveAuthoritative=!!predictiveAI.ready && Number(predictiveAI.trained||0)>=40 && Number(predictiveAI.hitRate||0)>=0.55;
    const aiPredictivePoints=aiPredictiveRaw<0 ? aiPredictiveRaw : (aiPredictiveAuthoritative ? aiPredictiveRaw : 0);
    const scoreBreakdown={structure:structurePts,momentum:momentumPts,timing:timingPts,contextAllTF:contextPts,boundary:boundaryPts,priceAction:priceActionPts,volatility:volatilityPts,aiPredictive:aiPredictivePoints,aiPredictiveRaw,aiPredictiveAuthoritative};
    let confidence=structurePts+momentumPts+timingPts+contextPts+boundaryPts+priceActionPts+volatilityPts+aiPredictivePoints;
    confidence += clamp(Number(microQuality.bonus||0),-3,3);
    confidence=clamp(Math.round(confidence),0,94);
    const adaptiveFloor=64;
    const entryQuality=timingPts+boundaryPts;
    const freshBreakout=!!fastTrigger.ok && timingPts>=8 && primaryAligned>=18 && fastAligned>=0;

    // V276 — PRIMARY-HORIZON MOMENTUM CONFIRMATION.
    // The latest losing run showed high-score 30s trades being approved even
    // while 30s momentum was still strongly moving AGAINST the requested side.
    // Structure may identify the larger trend, but for a 30s expiry we wait
    // for the primary candle itself to turn back with that trend before entry.
    // This is deliberately narrow: it only applies to severe primary-momentum
    // conflict and does not raise the global score floor.
    try {
      if(primaryAligned <= -22) {
        const pSeries=v181Series(asset?.__assetName || activeAsset || '', plan.primary);
        const primaryClosedMove=(Array.isArray(pSeries) && pSeries.length>=2)
          ? (Number(pSeries.at(-1))-Number(pSeries.at(-2)))*side : 0;
        const primaryTurned=primaryClosedMove>0;
        const exceptionalTurn=primaryTurned && fastAligned>=12 && fastTrigger.ok;
        if(!exceptionalTurn) {
          return reject(`V276 PRIMARY MOMENTUM · ${dir} waits for ${plan.primary} turn · PRI ${primaryAligned.toFixed(1)} · FAST ${fastAligned.toFixed(1)}`,
            {dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,
             adaptiveFloor,entryQuality,freshBreakout,primaryClosedMove,primaryTurned,exceptionalTurn,recentEdge,
             microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw});
        }
      }
    } catch(_) { }

    // V238 ALL-TF PREDICTIVE FLOOR. A high structure/context score is not enough for
    // a 30s expiry when the bot is entering at the end of the current impulse.
    // Keep the complete weighted score for diagnostics, but require usable
    // timing + location unless this is a genuinely fresh aligned breakout.
    // V24.1.282 — STRONG-TREND EXCEPTION. The 2026-09-23 forensic run showed a
    // clear expanding trend (AUDCAD ADX 57.3, SELL score 13/15) refused purely
    // because no boundary tag existed (BND 0): the gate demanded a pullback tag
    // on a market that was already travelling. A high-ADX market with an aligned
    // primary structure and a strong weighted score is a legitimate continuation
    // entry, so it no longer needs the boundary/pullback tag. This does NOT lower
    // the score floor or any safety guard; it only removes the boundary TAG
    // requirement when the trend itself is the evidence.
    const v282StrongTrend = pAdx>=V282_STRONG_TREND_ADX && pAligned>=20 && confidence>=V282_STRONG_TREND_MIN_SCORE;
    if(timingPts<5 || (entryQuality<12 && !freshBreakout && !v282StrongTrend) || (boundaryPts<=1 && !freshBreakout && !v282StrongTrend))
      return reject(`V234 ENTRY QUALITY · SCORE ${confidence}/100 · TIME ${timingPts} + BND ${boundaryPts} = ${entryQuality} · ${freshBreakout?'fresh breakout':(v282StrongTrend?'strong trend '+pAdx.toFixed(1):'wait for pullback/reload')}`,
        {dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,
         adaptiveFloor,entryQuality,freshBreakout,v282StrongTrend,pAdx,recentEdge,microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw});

    // V276 — MATURE IMPULSE / CHASE PROTECTION.
    // A fresh fast breakout is not automatically a good 30s entry when the
    // primary and multiple higher frames are already deeply extended in the
    // same direction. Wait for a reload instead of buying/selling the tail.
    try {
      const extFrames=['60s','120s','180s','300s']
        .map(tf=>Number(frames?.[tf]?.signedExtension||0)*side)
        .filter(Number.isFinite);
      const matureHigher=extFrames.filter(v=>v>=1.75).length;
      const maturePrimary=sideExtension>=1.45;
      if(maturePrimary && matureHigher>=2) {
        return reject(`V276 MATURE IMPULSE · ${dir} extended ${sideExtension.toFixed(2)} ATR on ${plan.primary} + ${matureHigher} higher frames · wait for reload`,
          {dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,
           adaptiveFloor,entryQuality,freshBreakout,maturePrimary,matureHigher,sideExtension,recentEdge});
      }
    } catch(_) { }

    // V229 SAME-SWING RE-ENTRY GUARD. Do not keep taking the same direction
    // every expiry while price is still in the same stretched impulse. A real
    // pullback/reload or a fresh breakout can re-arm it; otherwise wait 60s.
    const directionalAsset=asset?.__assetName || activeAsset || '';
    const priorDirEntry=v229DirectionalEntryState[directionalAsset];
    if(priorDirEntry && priorDirEntry.dir===dir && Date.now()-priorDirEntry.at<60000) {
      const reloaded=sideExtension<=0.65 && boundaryPts>=6 && timingPts>=7;
      if(!reloaded && !freshBreakout)
        return reject(`V234 SAME SWING · ${dir} already traded ${Math.round((Date.now()-priorDirEntry.at)/1000)}s ago · wait for reload`,
          {dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,
           adaptiveFloor,entryQuality,freshBreakout,reloaded,recentEdge});
    }

    if(confidence<adaptiveFloor) return reject(`V234 SCORE ${confidence}/100 < ${adaptiveFloor} · STR ${structurePts} MOM ${momentumPts} TIME ${timingPts} CTX ${contextPts} BND ${boundaryPts} PA ${priceActionPts} VOL ${volatilityPts} AI ${Number(predictiveAI.points||0)}`,
      {dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,
       adaptiveFloor,entryQuality,freshBreakout,recentEdge,microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw});

    const structureTags=[];
    try{
      const legacy=[v193TrendResume(asset,px),v181EmaRsiPullback(asset,px),v189BreakoutRetest(asset,px),v189LiquiditySweep(asset,px)];
      for(const q of legacy) if(q?.tradeType) structureTags.push(q.tradeType);
    }catch(_){ }

    const structuralAgreement=Math.max(0,Math.min(1,(pAligned>=12?0.72:0)+(hAligned>=0?0.28:0)));
    publish({state:'READY',dir,trendQuality,momentumQuality,volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,entryQuality,freshBreakout,
      pTrend,hTrend,pAligned,hAligned,fastAligned,primaryAligned,structuralSigned,structuralAgreement,structureTags,
      sideExtension,sideBand,directionalRsi,locationPenalty,locationState,
      microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw,recentEdge,adaptiveFloor,entryState,fastTrigger,liveRegime,locationPenalty,timingPenalty,momentumPenalty});
    return {dir,mode:'v208-full-conflict-cleanup',tradeType:'UNIFIED_MTF',str:confidence,confidence:confidence/100,
      reason:`V234 ${dir} · SCORE ${confidence}/100 · STR ${structurePts} MOM ${momentumPts} TIME ${timingPts} CTX ${contextPts} BND ${boundaryPts} PA ${priceActionPts} VOL ${volatilityPts} AI ${Number(predictiveAI.points||0)}`,
      reasons:['UNIFIED_MTF','V234_EVERYTHING_LEARNING','Structure 25','Momentum 15','Timing 20','All-TF Context 10','Boundary 15','Price Action 10','Volatility 5','Predictive AI ±10','primary timeframe owns direction','60s/120s/180s/300s confirm long trend vs reversal','fast timeframe times entry','AI multi-horizon learning'],
      measurement:{setup:'UNIFIED_MTF',marketClass:'UNIFIED_MTF',executionExpiry:expiry,
        trendScore:trendQuality,momentumScore:momentumQuality,volatilityScore:volatilityQuality,finalThreeStepScore:confidence,scoreBreakdown,
        structuralSigned,pTrend,hTrend,structuralAgreement,structureTags,frames,timeframePlan:plan,
        fastMomentum:fastAligned,primaryMomentum:primaryAligned,higherAligned:hAligned,longTrend,longAligned,longMomentum,longMomentumAligned,longConsensus,
        sideExtension,sideBand,directionalRsi,locationPenalty,locationState,
        microQuality:microQuality.score,microState:microQuality.state,micro:microQuality.raw,
        recentTradeSamples:recentEdge.n,recentTradeWins:recentEdge.wins,recentTradeWinRate:recentEdge.wr,adaptiveFloor,entryQuality,freshBreakout,entryState,fastTrigger,liveRegime,locationPenalty,timingPenalty,momentumPenalty,
        rangeClassifier:{marketClass:'DIRECTIONAL',primaryAdx:pAdx,higherAdx:hAdx,primaryChop:pChop,higherChop:hChop,primaryEfficiency:pEff,higherEfficiency:hEff},
        scoreWeights:{structure:25,momentum:15,timing:20,context60:10,boundary:15,priceAction:10,volatility:5,aiPredictive:10},predictiveAI,expiryPolicy:'V234_EVERYTHING_LEARNING_DIRECTIONAL'} };
  }

  // V24.1.222 — ACTIVE RANGE REVERSAL CONTROLLER
  // The overnight V218 run spent >30k evaluations in HOLD, mostly RANGE/CHOP.
  // In that market class a runner is the wrong tool. This controller trades
  // reversion from the outer part of the local distribution only after the
  // 15s frame has stopped pushing farther outward. It deliberately uses the
  // same UNIFIED_MTF execution path so warmup/data integrity remain unchanged.
  const v227RangeEntryState = Object.create(null);
  // V229: remember actual directional executions so one impulse cannot be hit repeatedly.
  // State is stamped only when an order is actually sent, not merely when a signal becomes READY.
  const v229DirectionalEntryState = Object.create(null);

  // ── V24.1.282 — PARTICIPATION FLOOR state ────────────────────────────────
  // Per-asset consecutive-HOLD streak. Incremented once per evaluation when
  // NEITHER the directional engine NOR the range controller produces a signal,
  // and reset to 0 the moment any signal is produced. It drives v282Tier().
  // This is deliberately observation-only bookkeeping: it gates nothing except
  // the bounded relaxation below, and it can never exceed the safety guards.
  const v282HoldStreak = Object.create(null);
  function v282AssetKey(asset) { return String((asset && asset.__assetName) || activeAsset || ''); }
  // v282Tier(): 0 = normal, 1 = first relaxation, 2 = second relaxation.
  function v282Tier(assetName) {
    if (!V282_PARTICIPATION_ENABLED) return 0;
    const n = v282HoldStreak[String(assetName || activeAsset || '')] || 0;
    if (n >= V282_HOLD_STREAK_TIER2) return 2;
    if (n >= V282_HOLD_STREAK_TRIGGER) return 1;
    return 0;
  }

  function v222RangeReversalSignal(asset, px, routerCtx) {
    const expiry=Math.max(5,parseInt(botConfig?.timeframe||30,10));
    const plan=v197TimeframePlan(expiry);
    const fast=v198FrameScore(asset,plan.fast), primary=v198FrameScore(asset,plan.primary), higher=v198FrameScore(asset,plan.higher);
    if(!fast?.ready || !primary?.ready || !higher?.ready || fast.n<8 || primary.n<8 || higher.n<8) return null;

    const pAdx=Number(primary.adx||0), pChop=Number(primary.chop||50), pEff=Number(primary.pathEfficiency||0);
    const hTrend=Number(higher.trend||0), pTrend=Number(primary.trend||0);
    // V227: low efficiency by itself is NOT a range. Low CHOP values are often
    // directional/expanding markets, which caused the losing countertrend fades.
    //
    // V24.1.282 — ROUTER/CONTROLLER UNIFICATION. The 2026-09-23 forensic run proved
    // this function was refusing handoffs it had been sent: v194 routed 34/40
    // decisions here on `weakPersistence && backtracking`, then this STRICTER,
    // independent `rangeLike` formula returned null for the very same market
    // (e.g. AEDCNY ADX 22.0 / eff 33% / chop 29.3 -> routed, then refused). That is
    // a permanent dead zone: directional engine declines AND range engine declines.
    // The router verdict is now authoritative. When v194 classified the chart as
    // RANGE/CHOP we accept the handoff, and a bounded participation tier widens the
    // entry thresholds after a long HOLD streak (see v282Tier).
    const v282tier=v282Tier(v282AssetKey(asset));
    const routerRouted=!!(routerCtx && routerCtx.rangeChop);
    const rangeLike=routerRouted
      ? true
      : ((pAdx<25 && pEff<0.42 && pChop>=42) || (pAdx<20 && pEff<0.30 && pChop>=38));
    if(!rangeLike) return null;

    const band=Number(primary.bandSigned||0), r=Number(primary.rsi||50);
    const fMom=Number(fast.momentum||0), pMom=Number(primary.momentum||0);
    const ext=Number(primary.signedExtension||0);
    let dir=null;
    // V24.1.282: the outer-band / RSI edges widen by one step per participation tier
    // so a long HOLD streak resolves into a real mean-reversion entry instead of a
    // permanent sit-out. Tier 0 keeps the original V227 thresholds exactly.
    const bandRelax=v282tier*V282_EDGE_BAND_RELAX, rsiRelax=v282tier*V282_EDGE_RSI_RELAX;
    const buyEdge=(band<=-(0.42-bandRelax) && r<=46+rsiRelax) || (band<=-(0.28-bandRelax) && r<=39+rsiRelax);
    const sellEdge=(band>= (0.42-bandRelax) && r>=54-rsiRelax) || (band>= (0.28-bandRelax) && r>=61-rsiRelax);
    if(buyEdge && fMom>=-14 && pMom>=-42) dir='BUY';
    if(sellEdge && fMom<= 14 && pMom<= 42) dir=dir?null:'SELL';
    if(!dir) return null;

    const side=dir==='BUY'?1:-1;
    const directionalRsi=dir==='BUY'?r:(100-r);
    const higherAligned=hTrend*side, primaryAligned=pTrend*side;

    // V266 — CLEAR-TREND COUNTERTRADE GUARD.
    // Preserve V263's controller and frequency, but do not let the RANGE fade
    // engine fire against an obvious directional run merely because price is
    // overbought/oversold. A countertrend entry requires an actual 30s reversal
    // sequence plus 15s/30s momentum turning with it.
    const p30=v181Series(asset,'30s');
    if(p30.length>=12) {
      const recent=p30.slice(-11);
      let green=0, red=0;
      for(let i=1;i<recent.length;i++) {
        if(recent[i]>recent[i-1]) green++;
        else if(recent[i]<recent[i-1]) red++;
      }
      const last1=recent.at(-1)-recent.at(-2);
      const last2=recent.at(-2)-recent.at(-3);
      const strongBullRun=(green>=8 && red<=2) || (pTrend>=45 && hTrend>=35);
      const strongBearRun=(red>=8 && green<=2) || (pTrend<=-45 && hTrend<=-35);
      const confirmedBearTurn=last1<0 && last2<0 && fMom<=-10 && pMom<=-8;
      const confirmedBullTurn=last1>0 && last2>0 && fMom>=10 && pMom>=8;
      if(dir==='SELL' && strongBullRun && !confirmedBearTurn) return null;
      if(dir==='BUY' && strongBearRun && !confirmedBullTurn) return null;
    }
    // V227: a range fade cannot fight an established 60s trend. Moderate
    // disagreement remains a score penalty; only a strong conflict is a veto.
    if(higherAligned < -35) return null;

    // Require a real 15s turn/resume event at the boundary. This prevents
    // selling merely because price is high or buying merely because it is low.
    const fastSeries=v181Series(asset,plan.fast);
    if(fastSeries.length<4) return null;
    const a=Number(fastSeries.at(-3)), b=Number(fastSeries.at(-2)), c=Number(fastSeries.at(-1));
    const prevMove=b-a, lastMove=c-b;
    const turnCandle=(lastMove*side)>0 && ((prevMove*side)<=0 || (fMom*side)>=6);
    if(!turnCandle) return null;

    // Never fade a breakout/expansion that is still driving outward.
    const outwardTrend=primaryAligned < -42;
    const outwardFast=fMom*side < -28;
    const expanding=(Math.abs(ext)>0.95 || pChop<40 || pAdx>=27);
    if((outwardTrend && outwardFast) || (outwardTrend && expanding)) return null;

    // Do not attack the same boundary repeatedly without a reset toward the
    // middle of the range. A 30s time escape prevents this from killing frequency.
    const assetName=asset?.__assetName || activeAsset || '';
    const prev=v227RangeEntryState[assetName];
    if(prev && prev.dir===dir && Date.now()-prev.at<30000 && Math.abs(band)>=0.24) return null;

    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const boundaryPts=clamp(Math.round(8 + Math.max(0,(Math.abs(band)-0.28)*24)),0,25);
    const momentumPts=clamp(Math.round(8 + Math.max(0,(50-directionalRsi)*0.55) + Math.max(0,(fMom*side+14)*0.08)),0,20);
    const timingPts=clamp(Math.round(10 + Math.max(0,(fMom*side+10)*0.14) + ((prevMove*side)<=0?3:0)),0,20);
    const structurePts=clamp(Math.round(10 + Math.max(0,(24-pAdx)*0.22) + Math.max(0,(0.40-pEff)*10) + Math.max(0,(pChop-42)*0.10)),0,15);
    const priceActionPts=clamp(Math.round(6 + Math.max(0,(lastMove*side)/(Math.max(1e-9,Number(primary.atr||1)))*2)),0,10);
    // 60s context now has real authority: aligned/neutral earns points; opposing
    // higher structure removes them instead of every range trade getting ~5.
    const contextPts=clamp(Math.round(5 + higherAligned*0.10),0,10);
    let score=boundaryPts+momentumPts+timingPts+structurePts+priceActionPts+contextPts;
    if(higherAligned<0) score-=clamp(Math.round(Math.abs(higherAligned)*0.12),0,8);
    if(primaryAligned<-20) score-=clamp(Math.round((Math.abs(primaryAligned)-20)*0.10),0,6);
    score=clamp(Math.round(score),0,92);
    const scoreBreakdown={boundary:boundaryPts,momentum:momentumPts,timing:timingPts,rangeStructure:structurePts,priceAction:priceActionPts,contextAllTF:contextPts};
    // V24.1.282: participation floor lowers the range score floor by one step per tier
    // (64 -> 60 -> 56). Never below 48.
    const v282RangeFloor=Math.max(48,V282_RANGE_SCORE_FLOOR - v282tier*V282_SCORE_RELAX_PER_TIER);
    if(score<v282RangeFloor) return null;
    v227RangeEntryState[assetName]={dir,at:Date.now(),band};
    return {dir,mode:'v227-range-context-turn',tradeType:'UNIFIED_MTF',str:score,confidence:score/100,
      reason:`V227 RANGE ${dir} · SCORE ${score}/100 · BND ${boundaryPts} MOM ${momentumPts} TIME ${timingPts} RNG ${structurePts} PA ${priceActionPts} CTX ${contextPts}`,
      reasons:['UNIFIED_MTF','V227_RANGE_CONTEXT_TURN','Boundary 25','Momentum 20','Timing 20','Range Structure 15','Price Action 10','All-TF Context 10','15s turn required','60s strong-conflict veto','range expansion protection','same-swing re-entry protection'],
      measurement:{setup:'RANGE_REVERSAL',marketClass:'RANGE_CHOP',executionExpiry:expiry,timeframePlan:plan,
        frames:{[plan.fast]:fast,[plan.primary]:primary,[plan.higher]:higher},finalThreeStepScore:score,scoreBreakdown,
        structuralAgreement:0.72,trendScore:Math.max(0,100-Math.abs(pTrend)),momentumScore:Math.max(0,100-Math.abs(pMom)),volatilityScore:Number(primary.volatility||50),
        bandSigned:band,rsi:r,fastMomentum:fMom,primaryMomentum:pMom,higherTrend:hTrend,higherAligned,primaryTrend:pTrend,primaryAligned,extensionAtr:ext,
        turnEvent:{prevMove,lastMove,fastMomentum:fMom},
        rangeClassifier:{marketClass:'RANGE_CHOP',primaryAdx:pAdx,primaryChop:pChop,primaryEfficiency:pEff},
        expiryPolicy:'V227_RANGE_CONTEXT_TURN'} };
  }

  function v193TrendResume(asset, px) {
    // V193: active continuation path for clean established trends. V192 could
    // sit for long periods waiting for a pullback or breakout-retest even while
    // 30s/15s structure remained strongly aligned. This setup does NOT chase
    // extremes: it requires stacked 30s EMAs, matching 15s momentum, controlled
    // ATR extension, and a fresh resume candle in the regime direction.
    const p=v181Series(asset,'30s'), q=v181Series(asset,'15s');
    if(p.length<52 || q.length<24) return null;
    const c=v189Context(asset); if(!c) return null;
    const cur=Number(px||p.at(-1)), prev=p.at(-2), prev2=p.at(-3);
    const av=c.atr || Math.abs(cur)*1e-6;
    const e5=ema(p,5), e9=ema(p,9), e21=ema(p,21), e21p=ema(p.slice(0,-1),21);
    const r=rsi(p,14);
    const q5=ema(q,5), q9=ema(q,9), qcur=q.at(-1), qprev=q.at(-2);
    const ext=Math.abs(cur-e21)/Math.max(av,1e-12);
    const bullRegime=c.state==='TREND_BULL'||(c.state==='DIRECTIONAL'&&c.supertrend.dir===1&&c.slopeAtr>0.015);
    const bearRegime=c.state==='TREND_BEAR'||(c.state==='DIRECTIONAL'&&c.supertrend.dir===-1&&c.slopeAtr<-0.015);
    const freshUp=cur>prev && (prev<=prev2 || cur-prev>=0.08*av);
    const freshDn=cur<prev && (prev>=prev2 || prev-cur>=0.08*av);
    const buy=bullRegime && e5>e9 && e9>e21 && e21>=e21p && q5>q9 && qcur>qprev && freshUp && r>=50 && r<=72 && ext<=1.30;
    const sell=bearRegime && e5<e9 && e9<e21 && e21<=e21p && q5<q9 && qcur<qprev && freshDn && r<=50 && r>=28 && ext<=1.30;
    if(!buy&&!sell) return null;
    const dir=buy?'BUY':'SELL';
    let score=77;
    if(Math.abs(c.sepAtr)>=0.30) score+=3;
    if(Math.abs(c.slopeAtr)>=0.025) score+=3;
    if(ext<=0.85) score+=2;
    if(c.zigzag.dir===(buy?1:-1)) score+=2;
    score=Math.min(90,score);
    return {dir,mode:'v193-30s-execution-multi-horizon-shadow',tradeType:'TREND_RESUME',str:score,confidence:score/100,
      reason:`V193 trend-resume · ${dir} · 30s EMA5/9/21 + 15s momentum · RSI ${r.toFixed(1)} · ${c.state}`,
      reasons:['TREND_RESUME','30s EMA5/9/21 stack','30s regime alignment','15s EMA5/9 momentum','fresh resume candle','ATR anti-chase','AI learning only'],
      measurement:{setup:'TREND_RESUME',marketClass:'TREND_RESUME',regime:c.state,ema5:e5,ema9:e9,ema21:e21,rsi14:r,extensionAtr:ext,linregSlopeAtr:c.slopeAtr,zigzag:c.zigzag.label,atr:av}};
  }

  function v181EmaRsiPullback(asset, px) {
    // Published-style trend/pullback/resumption architecture:
    // EMA 13/48 trend, RSI pullback to the middle zone, then price resumes back
    // through EMA13 in the macro-trend direction.  30s chart, 60s target.
    const p=v181Series(asset,'30s');
    if(p.length<52) return null;
    const cur=Number(px||p.at(-1)), prev=p.at(-2), prev2=p.at(-3);
    const e13=ema(p,13), e48=ema(p,48);
    const e13Prev=ema(p.slice(0,-1),13), e48Prev=ema(p.slice(0,-1),48);
    const r=rsi(p,14), rPrev=rsi(p.slice(0,-1),14);
    const av=atr(p,14) || Math.abs(cur)*1e-6;
    const trendUp=e13>e48;
    const trendDn=e13<e48;
    const recent=p.slice(-4,-1);
    const recentTouchedUp=recent.some(v=>v<=e13Prev+0.35*av);
    const recentTouchedDn=recent.some(v=>v>=e13Prev-0.35*av);
    const c=v189Context(asset); if(!c) return null;
    // V191: a pullback entry is continuation only. It may not fight the
    // established 30s regime. This blocks BUY-in-bear / SELL-in-bull cases.
    const contextBuy=(c.state==='TREND_BULL'||(c.state==='DIRECTIONAL'&&c.supertrend.dir===1&&c.slopeAtr>0.012));
    const contextSell=(c.state==='TREND_BEAR'||(c.state==='DIRECTIONAL'&&c.supertrend.dir===-1&&c.slopeAtr<-0.012));
    const buy=contextBuy && trendUp && recentTouchedUp && cur>e13 && cur>prev && r>=48 && r<=70 && r>=rPrev;
    const sell=contextSell && trendDn && recentTouchedDn && cur<e13 && cur<prev && r<=52 && r>=30 && r<=rPrev;
    if(!buy && !sell) return null;
    const dir=buy?'BUY':'SELL';
    let score=72;
    if(Math.abs(e13-e48)>=0.35*av) score+=4;
    if((buy&&r>=52)||(sell&&r<=48)) score+=3;
    if((buy&&prev2<prev&&cur>prev)||(sell&&prev2>prev&&cur<prev)) score+=2;
    score=Math.min(84,score);
    return {dir,mode:'v218-range-aware-v209-core',tradeType:'EMA_RSI_PULLBACK',str:score,confidence:score/100,
      reason:`V187 EMA/RSI pullback · ${dir} · EMA13/48 trend · RSI ${r.toFixed(1)}`,
      reasons:['EMA_RSI_PULLBACK','EMA13/48 macro trend','RSI14 pullback/resumption','AI learning only'],
      measurement:{setup:'EMA_RSI_PULLBACK',marketClass:'TREND_PULLBACK',ema13:e13,ema48:e48,rsi14:r,atr:av,regime:lastIndicatorCtx[asset]?.ctx?.regime||null}};
  }

  function v181SrFailureTest(asset, px) {
    // V24.1.190 STRUCTURE-FIRST S/R FAILURE TEST.
    // A boundary touch alone is no longer enough. Execution requires an actual
    // excursion beyond the range, a close back inside, momentum turning with the
    // rejection, and a non-trending/choppy structure. Strong directional markets
    // are left to pullback or breakout-retest logic instead of being faded.
    const p=v181Series(asset,'30s');
    if(p.length<52) return null;
    const c=v189Context(asset); if(!c) return null;
    const cur=Number(px||p.at(-1)), prev=p.at(-2);
    const base=p.slice(-18,-3); if(base.length<12) return null;
    const resistance=Math.max(...base), support=Math.min(...base);
    const av=c.atr || Math.abs(cur)*1e-6;
    const r=rsi(p,14), rPrev=rsi(p.slice(0,-1),14);
    const insideTop=(resistance-cur)/Math.max(av,1e-12);
    const insideBottom=(cur-support)/Math.max(av,1e-12);
    const excursionUp=(prev-resistance)/Math.max(av,1e-12);
    const excursionDn=(support-prev)/Math.max(av,1e-12);
    const rangeState=(c.state==='CHOP_RANGE'||c.state==='MIXED');
    const weakTrend=Math.abs(c.sepAtr)<0.22 && Math.abs(c.slopeAtr)<0.035;
    if(!rangeState && !weakTrend) return null;

    const falseUp=excursionUp>=0.055 && insideTop>=0.030 && cur<prev && r<=rPrev-2 && r>=52;
    const falseDn=excursionDn>=0.055 && insideBottom>=0.030 && cur>prev && r>=rPrev+2 && r<=48;
    if(!falseUp && !falseDn) return null;
    const dir=falseDn?'BUY':'SELL';
    const excursion=dir==='SELL'?excursionUp:excursionDn;
    let score=79 + Math.min(7,Math.max(0,excursion*6));
    if(c.state==='CHOP_RANGE') score+=4;
    if((dir==='SELL'&&c.zigzag.dir<=0)||(dir==='BUY'&&c.zigzag.dir>=0)) score+=2;
    score=Math.min(92,score);
    return {dir,mode:'v218-range-aware-v209-core',tradeType:'SR_FAILURE_TEST',str:score,confidence:score/100,
      reason:`V190 S/R failure-test · ${dir} · true sweep/re-entry · ${c.state}`,
      reasons:['SR_FAILURE_TEST','18-candle close boundary','minimum 0.055 ATR excursion','close back inside range','RSI turn','range/weak-trend structure','AI learning only'],
      measurement:{setup:'SR_FAILURE_TEST',marketClass:'RANGE_REJECTION',support,resistance,rsi14:r,excursionAtr:excursion,insideAtr:dir==='SELL'?insideTop:insideBottom,atr:av,regime:c.state,choppiness:c.chop,linregSlopeAtr:c.slopeAtr,trendSepAtr:c.sepAtr,zigzag531:c.zigzag.label}};
  }

  function v181SqueezeBreakout(asset, px) {
    // Donchian/Keltner-style compression + momentum breakout.  Compression is
    // measured on the prior 20 closes; breakout must clear that range with EMA
    // slope and RSI momentum in the same direction.
    const p=v181Series(asset,'30s');
    if(p.length<28) return null;
    const cur=Number(px||p.at(-1));
    const prior=p.slice(-21,-1);
    const high=Math.max(...prior), low=Math.min(...prior);
    const av=atr(p.slice(0,-1),14) || Math.abs(cur)*1e-6;
    const center=ema(p.slice(0,-1),20);
    const donWidth=high-low;
    const keltWidth=3.0*av; // ±1.5 ATR around EMA20
    const compressed=donWidth<=keltWidth*1.80;
    const e9=ema(p,9), e9Prev=ema(p.slice(0,-1),9);
    const r=rsi(p,14);
    const buy=compressed && cur>high+0.02*av && e9>=e9Prev && r>=52 && r<=78;
    const sell=compressed && cur<low-0.02*av && e9<=e9Prev && r<=48 && r>=22;
    if(!buy && !sell) return null;
    const dir=buy?'BUY':'SELL';
    const breakAtr=dir==='BUY'?(cur-high)/av:(low-cur)/av;
    let score=76 + Math.min(7,Math.max(0,breakAtr*8));
    if((buy&&r>=60)||(sell&&r<=40)) score+=3;
    score=Math.min(88,score);
    return {dir,mode:'v218-range-aware-v209-core',tradeType:'DONCHIAN_KELTNER_SQUEEZE',str:score,confidence:score/100,
      reason:`V187 squeeze breakout · ${dir} · compressed range · RSI ${r.toFixed(1)}`,
      reasons:['DONCHIAN_KELTNER_SQUEEZE','20-candle Donchian compression','Keltner-style ATR envelope','momentum breakout confirmation','AI learning only'],
      measurement:{setup:'DONCHIAN_KELTNER_SQUEEZE',marketClass:'SQUEEZE_BREAKOUT',donchianHigh:high,donchianLow:low,donchianWidth:donWidth,keltnerWidth:keltWidth,rsi14:r,breakAtr,atr:av,regime:lastIndicatorCtx[asset]?.ctx?.regime||null}};
  }

  function v189LiquiditySweep(asset, px){
    // V190: make the dedicated sweep setup the primary reversal family. It uses a
    // fresher 15-candle boundary and requires a decisive return inside the range.
    const p=v181Series(asset,'30s'); if(p.length<52) return null;
    const c=v189Context(asset); if(!c) return null;
    const cur=Number(px||p.at(-1)), prev=p.at(-2), base=p.slice(-15,-3), hi=Math.max(...base), lo=Math.min(...base), av=c.atr;
    const r=rsi(p,14), rp=rsi(p.slice(0,-1),14);
    const upExc=(prev-hi)/Math.max(av,1e-12), dnExc=(lo-prev)/Math.max(av,1e-12);
    const backInUp=(hi-cur)/Math.max(av,1e-12), backInDn=(cur-lo)/Math.max(av,1e-12);
    const sweptHigh=upExc>=0.050 && backInUp>=0.030 && cur<prev && r<=rp-2 && r>=52;
    const sweptLow=dnExc>=0.050 && backInDn>=0.030 && cur>prev && r>=rp+2 && r<=48;
    if(!sweptHigh&&!sweptLow) return null;
    const dir=sweptLow?'BUY':'SELL';
    // V191: dedicated reversal execution is range/mixed only. Do not fade an
    // established trend or directional expansion with a 1-candle sweep signal.
    if(c.state==='TREND_BULL'||c.state==='TREND_BEAR'||c.state==='DIRECTIONAL') return null;
    const excursion=dir==='SELL'?upExc:dnExc;
    const score=Math.min(94,84+Math.min(6,excursion*7)+(c.state==='CHOP_RANGE'?4:0)+(c.zigzag.dir===(dir==='BUY'?1:-1)?2:0));
    return {dir,mode:'v218-range-aware-v209-core',tradeType:'LIQUIDITY_SWEEP_REVERSAL',str:score,confidence:score/100,
      reason:`V190 liquidity sweep · ${dir} · decisive failed boundary · ${c.state}`,
      reasons:['LIQUIDITY_SWEEP_REVERSAL','15-candle liquidity boundary','minimum sweep excursion','decisive close back inside','RSI turn','ZigZag 5/3/1 structure'],
      measurement:{setup:'LIQUIDITY_SWEEP_REVERSAL',marketClass:'LIQUIDITY_SWEEP',regime:c.state,choppiness:c.chop,linregSlopeAtr:c.slopeAtr,zigzag:c.zigzag.label,rsi14:r,excursionAtr:excursion,atr:av}};
  }

  function v189BreakoutRetest(asset, px){
    // V190: slightly broader but still structural breakout-retest. The initial
    // break must occur two candles ago, the prior candle must revisit the level,
    // and the current candle must resume in the breakout direction.
    const p=v181Series(asset,'30s'); if(p.length<52) return null;
    const c=v189Context(asset); if(!c||c.state==='CHOP_RANGE') return null;
    const cur=Number(px||p.at(-1)), prev=p.at(-2), prev2=p.at(-3), base=p.slice(-20,-4), hi=Math.max(...base), lo=Math.min(...base), av=c.atr;
    const r=rsi(p,14);
    const buyBreak=prev2>hi+0.015*av;
    const buyRetest=prev>=hi-0.18*av && prev<=hi+0.18*av;
    const buyResume=cur>hi+0.005*av && cur>prev && c.slopeAtr>0.006 && c.supertrend.dir>=0 && r>=48 && r<=78;
    const sellBreak=prev2<lo-0.015*av;
    const sellRetest=prev<=lo+0.18*av && prev>=lo-0.18*av;
    const sellResume=cur<lo-0.005*av && cur<prev && c.slopeAtr<-0.006 && c.supertrend.dir<=0 && r<=52 && r>=22;
    const buy=buyBreak&&buyRetest&&buyResume, sell=sellBreak&&sellRetest&&sellResume;
    if(!buy&&!sell) return null;
    const dir=buy?'BUY':'SELL';
    let score=84+Math.min(6,Math.abs(c.slopeAtr)*35);
    if(c.zigzag.dir===(buy?1:-1)) score+=3;
    if((buy&&c.state==='TREND_BULL')||(sell&&c.state==='TREND_BEAR')) score+=3;
    score=Math.min(95,score);
    return {dir,mode:'v218-range-aware-v209-core',tradeType:'BREAKOUT_RETEST',str:score,confidence:score/100,
      reason:`V190 breakout-retest · ${dir} · break/revisit/resume · ${c.state}`,
      reasons:['BREAKOUT_RETEST','20-candle structure boundary','break two candles ago','level retest','resume candle','Linear Regression slope','Supertrend direction','ZigZag 5/3/1 structure'],
      measurement:{setup:'BREAKOUT_RETEST',marketClass:'BREAKOUT_RETEST',regime:c.state,choppiness:c.chop,linregSlopeAtr:c.slopeAtr,supertrendDir:c.supertrend.dir,zigzag:c.zigzag.label,rsi14:r,atr:av}};
  }


  // V24.1.187 — FORWARD-EVIDENCE STRATEGY-SPECIFIC EXPIRIES
  // Frozen from the 2026-09-07 V184/V186 forward checkpoint. These are
  // deterministic execution settings; AI remains learning-only with zero authority.
  // The 30s strategy signal definitions are unchanged. Only the order horizon differs.
  const V187_STRATEGY_EXPIRY = Object.freeze({
    EMA_RSI_PULLBACK: 120,
    SR_FAILURE_TEST: 5,
    DONCHIAN_KELTNER_SQUEEZE: 15,
    LIQUIDITY_SWEEP_REVERSAL: 5,
    BREAKOUT_RETEST: 30
  });

  function v191DirectionAligned(ctx, sig) {
    if(!ctx || !sig) return false;
    const dir=String(sig.dir||'').toUpperCase(), family=String(sig.tradeType||'').toUpperCase();
    if(!['BUY','SELL'].includes(dir)) return false;

    // B15.1 CLEAN TEST: BB45 + Alligator/ROC was backtested without the legacy
    // V191 market-regime veto. Once this strategy itself has qualified the
    // direction, do not let TREND/MIXED/CHOP legacy state cancel the entry.
    // Data-integrity, warmup, execution, payout/EV and platform-safety checks
    // remain unchanged.
    if(String(family||'').startsWith('BB45_') || String(family||'').startsWith('CANDIDATE_B_') || family==='CANDIDATE_7B' || family==='BB_WINNER_PRO' || family==='BB_RUNNER' || family==='BB_CHOP' || family==='SMC_BOS_ST_ATR') return true;

    // V198: the unified controller is expiry-relative. Re-check the exact
    // primary/higher frames used by the signal rather than hard-wiring 30s.
    if(family==='UNIFIED_MTF') {
      const m=sig.measurement||{}, plan=m.timeframePlan||v197TimeframePlan(sig.executionExpiry||botConfig?.timeframe||30);
      const side=dir==='BUY'?1:-1;
      const pFrame=m.frames?.[plan.primary], hFrame=m.frames?.[plan.higher];
      const pTrend=Number(pFrame?.trend||0)*side, hTrend=Number(hFrame?.trend||0)*side;
      const agreement=Number(m.structuralAgreement||0);
      const finalScore=Number(m.finalThreeStepScore||sig.str||0);
      if(String(m.setup||'').toUpperCase()==='RANGE_REVERSAL') {
        // Range reversals intentionally oppose the local trend at an outer edge;
        // validate their range classifier/score rather than trend alignment.
        const rc=m.rangeClassifier||{};
        const rangeStillValid=(Number(rc.primaryEfficiency||1)<0.48) || (Number(rc.primaryChop||0)>52);
        return rangeStillValid && finalScore>=56;
      }
      if(agreement<0.50 || pTrend<10 || hTrend<-14 || finalScore<56) return false;
      return true;
    }

    if(ctx.state==='TREND_BULL') return dir==='BUY';
    if(ctx.state==='TREND_BEAR') return dir==='SELL';
    if(ctx.state==='DIRECTIONAL') {
      if(dir==='BUY') return ctx.supertrend.dir===1 && ctx.slopeAtr>0.010;
      return ctx.supertrend.dir===-1 && ctx.slopeAtr<-0.010;
    }
    if(ctx.state==='MIXED'||ctx.state==='CHOP_RANGE')
      return ['SR_FAILURE_TEST','LIQUIDITY_SWEEP_REVERSAL'].includes(family);
    return false;
  }

  function v191ExecutionExpiry(sig, ctx) {
    // V198: actual demo execution follows the selected popup expiry.
    if(['BB_WINNER_PRO','BB_RUNNER','BB_CHOP','SMC_BOS_ST_ATR','CANDIDATE_7B','CUSTOM_STRATEGY'].includes(String(sig?.tradeType||'').toUpperCase())) return Math.max(5, parseInt(sig?.executionExpiry || 60, 10));
    if(String(sig?.tradeType||'').toUpperCase().startsWith('BBPLUS_')) return Math.max(5, parseInt(sig?.executionExpiry || 30, 10));
    if(String(sig?.tradeType||'').toUpperCase().startsWith('BB45_')) return 30;
    if(String(sig?.tradeType||'').toUpperCase().startsWith('CANDIDATE_B_')) return Math.max(5, parseInt(sig?.executionExpiry || 30, 10));
    // B32.20.7: strategy-declared execution expiry is authoritative. The popup/context
    // timeframe must never overwrite a live strategy's order duration (MICRO_TREND_CYCLE=15s).
    return Math.max(5, parseInt(sig?.executionExpiry || botConfig?.timeframe || 30, 10));
  }

  function v187ExecutionExpiry(sig) {
    // Compatibility wrapper used by telemetry/snapshots.
    return v191ExecutionExpiry(sig, null);
  }

  function v191PriceSeriesIntegrity(asset) {
    const a=getAsset(asset), live=Number(a?.lastPrice||0);
    const expiry=Math.max(5,parseInt(botConfig?.timeframe||30,10));
    const plan=v197TimeframePlan(expiry), key=plan.primary||expiryToTF(expiry);
    const p=v181Series(asset,key);
    if(!a || !Number.isFinite(live) || live<=0 || p.length<12) return {ok:false,reason:`missing live/${key} series`};
    const recent=p.slice(-24).filter(Number.isFinite);
    if(recent.length<12) return {ok:false,reason:`insufficient valid ${key} closes`};
    const sorted=[...recent].sort((x,y)=>x-y), median=sorted[Math.floor(sorted.length/2)];
    const rel=Math.abs(median-live)/Math.max(Math.abs(live),1e-12);
    const av=atr(recent,7)||Math.abs(live)*1e-6;
    const atrGap=Math.abs(median-live)/Math.max(av,1e-12);
    const ok=rel<=0.03 && atrGap<=35;
    return {ok,live,median,rel,atrGap,tf:key,reason:ok?'ok':`${key} history scale mismatch rel=${rel.toFixed(4)} atrGap=${atrGap.toFixed(1)}`};
  }

  // V24.1.287 — POCKET OPTION 1-SECOND + MARKET-SENTIMENT LEARNING COLLECTOR
  // Records the actual Pocket Option chart price once per second and attempts to
  // read the visible Market Sentiment percentages from the platform DOM. Each
  // observation is labeled 30 seconds later and trains an independent online
  // BUY/SELL probability model. Learning/shadow only: no execution authority.
  const V287_MAX=30000, V287_HORIZON=30000;
  const v287State={samples:[],pending:[],resolved:0,correct:0,w:Array(16).fill(0),b:0,models:{},last:null,lastSent:null,lastAsset:'',version:'287-B13',_ticks:{},sentimentByAsset:{},lastByAsset:{},selN:0,selC:0,selByAsset:{},lastPersistResolved:-1,_lastFlowPersist:0};
  try{chrome.storage.local.get('v287_learning_status',d=>{try{const z=d&&d.v287_learning_status;if(!z)return;/* B13 intentionally does not import B11/B12 10D weights: feature/model meaning changed. */if(String(z.version||'').includes('B13')){if(Array.isArray(z.w)&&z.w.length===16)v287State.w=z.w.map(Number);if(Number.isFinite(Number(z.b)))v287State.b=Number(z.b);if(z.models&&typeof z.models==='object')v287State.models=z.models;}v287State.resolved=Number(z.resolved)||0;v287State.correct=Number(z.correct)||0;v287State.selN=Number(z.selN)||0;v287State.selC=Number(z.selC)||0;if(z.selByAsset&&typeof z.selByAsset==='object')v287State.selByAsset=z.selByAsset;}catch(_){}});}catch(_){}
  // B11-audit (H1 fix): the raw forward samples ARE the evidence the user exports,
  // so they are now snapshotted durably. The live in-memory arrays remain the export
  // source of truth; this snapshot only matters when a page reload would otherwise
  // drop every raw row while keeping the accuracy counters (which is what B11 did).
  function v287SnapshotFlow(){
    try{
      v287State._lastFlowPersist=Date.now();
      chrome.storage.local.set({v287_flow_data:{version:'287-B13',ts:Date.now(),resolved:v287State.resolved,correct:v287State.correct,samples:v287State.samples.slice(-V287_MAX),pending:v287State.pending.slice(-200)}});
    }catch(_){}
  }
  function v287RestoreFlow(){
    try{chrome.storage.local.get('v287_flow_data',d=>{try{const z=d&&d.v287_flow_data;if(!z)return;if(!v287State.samples.length&&Array.isArray(z.samples)&&z.samples.length)v287State.samples=z.samples;if(!v287State.pending.length&&Array.isArray(z.pending))v287State.pending=z.pending;}catch(_){}});}catch(_){}
  }
  v287RestoreFlow();
  try{ if(typeof addEventListener==='function'){ addEventListener('pagehide',()=>v287SnapshotFlow()); addEventListener('visibilitychange',()=>{ if(document&&document.visibilityState==='hidden') v287SnapshotFlow(); else if(document&&document.visibilityState==='visible'){ try{ for(const a of (multiAssetMode?multiScanAssets():[activeAsset]).filter(Boolean).slice(0,4)) requestPrevious200(a,true); }catch(_){} } }); } }catch(_){}
  function v287Sigmoid(z){z=Math.max(-20,Math.min(20,z));return 1/(1+Math.exp(-z));}
  function v287Sentiment(asset){
    // B11: primary source is the page-context bridge, which reads sentiment
    // inside each visible chart panel. DOM fallback remains for single-chart layouts.
    try{
      const cached=v287State.sentimentByAsset?.[asset];
      if(cached && Date.now()-Number(cached.t||0)<5000 && Number.isFinite(cached.buy) && Number.isFinite(cached.sell)) return cached;
      const pct=(txt)=>(String(txt||'').match(/\d{1,3}(?:\.\d+)?\s*%/g)||[]).map(x=>Number(x.replace(/[^\d.]/g,''))).filter(x=>Number.isFinite(x)&&x>=0&&x<=100);
      const accept=(vals,source)=>{for(let i=0;i<vals.length;i++)for(let j=i+1;j<vals.length;j++){const a=vals[i],b=vals[j];if(Math.abs(a+b-100)<=2)return {buy:a,sell:b,source,t:Date.now()};}return null;};
      const direct=[...document.querySelectorAll('[class*="sentiment" i],[data-test*="sentiment" i],[data-testid*="sentiment" i],[aria-label*="sentiment" i],[title*="sentiment" i],[class*="mood" i]')];
      for(const el of direct){const r=accept(pct((el.innerText||'')+' '+(el.getAttribute('aria-label')||'')+' '+(el.getAttribute('title')||'')),'content-dom');if(r)return r;}
    }catch(_){}
    return null;
  }
  function v287Features(asset,px,sent){
    // B10: PO only. Sample the live price once/sec while the visible 5s candle
    // is still forming. This reconstructs the intra-candle path without OCR.
    const a=getAsset(asset); if(!a)return null;
    const q=v287State._ticks[asset]||(v287State._ticks[asset]=[]);
    const now=Date.now(); q.push({t:now,p:px}); while(q.length&&now-q[0].t>35000)q.shift();
    const atAge=(ms)=>{let best=q[0];for(const e of q){if(now-e.t>=ms)best=e;else break;}return best;};
    const ret=(ms)=>{const z=atAge(ms);return z&&z.p?((px-z.p)/z.p)*10000:0;};
    const recent5=q.filter(e=>now-e.t<=5200);
    const open5=recent5.length?recent5[0].p:px;
    let hi5=px,lo5=px;
    for(const e of recent5){if(e.p>hi5)hi5=e.p;if(e.p<lo5)lo5=e.p;}
    // B11-audit (F1 fix): express the 5s candle-path terms in the SAME basis-point
    // units as ret() below (1e-4 of price). The previous 1e-7 factor was ~1000x too
    // small, so body5/range5/rejection hit the +/-4 clamp on any move larger than
    // ~0.04 pip and carried no information (range5 was effectively a constant +4).
    const scale=Math.max(Math.abs(open5)*1e-4,1e-12);
    const body5=(px-open5)/scale;
    const range5=(hi5-lo5)/scale;
    const upperReject=(hi5-Math.max(open5,px))/scale;
    const lowerReject=(Math.min(open5,px)-lo5)/scale;
    const r1=ret(1000),r3=ret(3000),r5=ret(5000),r15=ret(15000),r30=ret(30000);
    const buy=sent?sent.buy:50, imb=(buy-50)/50;
    const prev=v287State.lastSent&&v287State.lastSent.asset===asset?v287State.lastSent:null;
    const sVel=prev?((buy-prev.buy)/Math.max(1,(now-prev.t)/1000))/10:0;
    // 10 dimensions: immediate velocity, 3s/5s path, 30s context,
    // live 5s body/range/rejection balance, sentiment level and velocity.
    return [r1/5,r3/8,r5/12,r15/25,r30/35,body5/8,range5/12,(lowerReject-upperReject)/8,imb,sVel]
      .map(v=>Math.max(-4,Math.min(4,Number(v)||0)));
  }
  // B13: expand the raw 10D observation with interactions that B12 could not learn
  // directly: short acceleration, 1s-vs-5s impulse, sentiment x momentum,
  // sentiment/price divergence, rejection x sentiment, and sentiment velocity x impulse.
  function v287Expand(x){
    if(!Array.isArray(x))return Array(16).fill(0);
    const a=x.map(v=>Number(v)||0),imb=a[8]||0;
    const ex=[...a.slice(0,10), (a[0]||0)-(a[2]||0), (a[1]||0)-(a[2]||0), imb*(a[2]||0), imb*(a[4]||0), imb*(a[7]||0), (a[9]||0)*(a[0]||0)];
    return ex.map(v=>Math.max(-4,Math.min(4,v)));
  }
  function v287Model(asset){
    const k=String(asset||'UNKNOWN'); let m=v287State.models[k];
    if(!m||!Array.isArray(m.w)||m.w.length!==16)m=v287State.models[k]={w:Array(16).fill(0),b:0,n:0,correct:0};
    return m;
  }
  function v287RawPredict(w,b,e){let z=Number(b)||0;for(let i=0;i<e.length;i++)z+=(Number(w?.[i])||0)*e[i];return v287Sigmoid(z);}
  function v287Predict(x,asset){
    const e=v287Expand(x),pg=v287RawPredict(v287State.w,v287State.b,e),m=v287Model(asset),pa=v287RawPredict(m.w,m.b,e);
    // Asset-specific behavior dominates once it has enough labels; global model
    // remains a stabilizer during cold start instead of mixing four markets equally.
    const alpha=Math.min(.80,Math.max(0,(Number(m.n)||0)/500)*.80);
    return pg*(1-alpha)+pa*alpha;
  }
  function v287Learn(x,y,asset){
    const e=v287Expand(x),lr=.010,decay=.9997;
    const pg=v287RawPredict(v287State.w,v287State.b,e),eg=y-pg;
    for(let i=0;i<e.length;i++)v287State.w[i]=v287State.w[i]*decay+lr*eg*e[i]; v287State.b+=lr*eg;
    const m=v287Model(asset),pa=v287RawPredict(m.w,m.b,e),ea=y-pa;
    for(let i=0;i<e.length;i++)m.w[i]=m.w[i]*decay+lr*ea*e[i]; m.b+=lr*ea; m.n=(m.n||0)+1; if(((pa>=.5)?1:0)===y)m.correct=(m.correct||0)+1;
    return v287Predict(x,asset);
  }
  function v287ResolveAll(){
    const now=Date.now(),keep=[];
    for(const r of v287State.pending){
      if(now<r.due){keep.push(r);continue;}
      const a=getAsset(r.asset), nowPx=Number(a?.lastPrice||0);
      if(!Number.isFinite(nowPx)||nowPx<=0){keep.push(r);continue;}
      if(nowPx===r.price){r.outcome='DRAW';}
      else {const y=nowPx>r.price?1:0;r.outcome=y?'BUY':'SELL';const pu=Number(r.predUp);r.correct=((pu>=.5)?1:0)===y;r.selective=(pu>=.56||pu<=.44);v287State.resolved++;if(r.correct)v287State.correct++;if(r.selective){v287State.selN=(v287State.selN||0)+1;if(r.correct)v287State.selC=(v287State.selC||0)+1;const bk=String(r.asset||'UNKNOWN');const b=v287State.selByAsset[bk]||(v287State.selByAsset[bk]={n:0,c:0});b.n++;if(r.correct)b.c++;}v287Learn(r.x,y,r.asset);}
      r.exitPrice=nowPx;r.resolvedAt=now;v287State.samples.push(r);
    }
    v287State.pending=keep; if(v287State.samples.length>V287_MAX)v287State.samples.splice(0,v287State.samples.length-V287_MAX);
  }
  function v287PersistLearning(){
    if(v287State.resolved===v287State.lastPersistResolved)return;
    if(v287State.resolved!==0 && (v287State.resolved%10)!==0)return;
    v287State.lastPersistResolved=v287State.resolved;
    try{chrome.storage.local.set({v287_learning_status:{version:'287-B13',resolved:v287State.resolved,correct:v287State.correct,accuracy:v287State.resolved?v287State.correct/v287State.resolved:0,allSamplesAccuracy:v287State.resolved?v287State.correct/v287State.resolved:0,selectiveResolved:v287State.selN,selectiveCorrect:v287State.selC,selectiveAccuracy:v287State.selN?v287State.selC/v287State.selN:0,selByAsset:v287State.selByAsset,last:v287State.last,w:v287State.w,b:v287State.b,models:v287State.models}});}catch(_){}
  }
  function v287CollectOne(asset){
    if(!asset)return;
    const a=getAsset(asset),px=Number(a?.lastPrice||0); if(!Number.isFinite(px)||px<=0)return;
    const sent=v287Sentiment(asset),x=v287Features(asset,px,sent),p=x?v287Predict(x,asset):.5;
    const now=Date.now(),q=v287State._ticks[asset]||[],path5=q.filter(e=>now-e.t<=5200).map(e=>({dt:Math.max(0,now-e.t),p:e.p}));
    const rec={ts:now,due:now+V287_HORIZON,asset,price:px,path5,sentimentBuy:sent?.buy??null,sentimentSell:sent?.sell??null,sentimentSource:sent?.source||null,x,predUp:p,pred:p>=.56?'BUY':p<=.44?'SELL':'NO TRADE',shadowOnly:true,executionAuthority:false,learningSource:'PO_1S_SHADOW'};
    v287State.pending.push(rec);
    v287State.lastByAsset[asset]={...rec,resolved:v287State.resolved,accuracy:v287State.resolved?v287State.correct/v287State.resolved:0};
    v287State.last=v287State.lastByAsset[asset];
    if(sent)v287State.lastSent={asset,buy:sent.buy,t:now}; v287State.lastAsset=asset;
  }
  function v287Collect(){
    try{
      v287ResolveAll();
      const assets=multiAssetMode?multiScanAssets():[lastIndicators?.asset||lastTradeAsset||activeAsset||chartSelectedAsset||v287State.lastAsset||''];
      for(const asset of [...new Set(assets.filter(Boolean))].slice(0,4)) v287CollectOne(asset);
      if(v287State.pending.length>1200)v287State.pending.splice(0,v287State.pending.length-1200);
      v287PersistLearning();
      // B11-audit: durable snapshot of raw forward samples (throttled + on pagehide).
      if(Date.now()-(v287State._lastFlowPersist||0)>20000) v287SnapshotFlow();
    }catch(_){}
  }
  setInterval(v287Collect,1000);

  // V24.1.287-B10 — SHADOW 1S PO LEARNER + NORMAL BOT EXECUTION
  // External Binance microstructure removed. Crypto, FX, OTC and other assets
  // are learned from the currently selected Pocket Option market using the
  // 1-second PO price + PO Market Sentiment collector above.

  // V24.1.287 — POCKET FLOW SHADOW + SIMPLE 30-SECOND EDGE ENGINE
  // One direction score, one confidence threshold, one exhaustion check.
  // 30s structure owns direction; 15s/5s time the entry; 60s is context only.
  // No ADX/chop router, range sub-engine, participation floor, pullback tag,
  // boundary gate, legacy regime veto, or AI execution authority.
  // V24.1.288 — LIVE TEST: BB(50,1.5) mean-reversion entry gated by
  // 15s Alligator/ROC direction. This is the exact mechanical test candidate:
  // lower-band cross => BUY only in bullish Alligator + positive ROC;
  // upper-band cross => SELL only in bearish Alligator + negative ROC; 5s expiry.
  function v288BbAlligatorRocSignal(assetName, px){
    // B15.6: restored EXACT B15.1 / 20-for-20 candidate.
    // BB(50,1.5) on CLOSED 5s candles + 15s Alligator (Lips 3 shift1,
    // Jaws 10 shift5) + 15s ROC(7). No pullback/continuation variants.
    const a=getAsset(assetName); if(!a)return null;
    const p5=getTF(a,'5s').prices.map(Number).filter(Number.isFinite);
    const p15=getTF(a,'15s').prices.map(Number).filter(Number.isFinite);
    if(p5.length<52||p15.length<18)return null;
    const bbAt=(end)=>{const q=p5.slice(end-45,end);if(q.length<45)return null;const m=q.reduce((x,y)=>x+y,0)/45;const sd=Math.sqrt(q.reduce((z,v)=>z+(v-m)*(v-m),0)/45);return {lo:m-1.5*sd,hi:m+1.5*sd,mid:m};};
    const smmaSeries=(arr,n)=>{if(arr.length<n)return[];const o=Array(arr.length).fill(NaN);let v=arr.slice(0,n).reduce((x,y)=>x+y,0)/n;o[n-1]=v;for(let i=n;i<arr.length;i++){v=(v*(n-1)+arr[i])/n;o[i]=v;}return o;};
    const prev=p5.length-1, cur=p5.length;
    const bbPrev=bbAt(prev),bbCur=bbAt(cur); if(!bbPrev||!bbCur)return null;
    const cPrev=p5[p5.length-2],cNow=p5[p5.length-1];
    const lips=smmaSeries(p15,3),jaws=smmaSeries(p15,10);
    const li=lips.length-1-1, ji=jaws.length-1-5;
    if(li<0||ji<0||!Number.isFinite(lips[li])||!Number.isFinite(jaws[ji]))return null;
    const rocLookback=7, roc=p15.length>rocLookback?(p15[p15.length-1]-p15[p15.length-1-rocLookback])/Math.max(Math.abs(p15[p15.length-1-rocLookback]),1e-12):0;
    const LOWER_BB_MIN_ROC7=0.00020; // B15.10: tested lower-band strength gate (+0.02%); upper-band logic intentionally unchanged
    const bull=lips[li]>jaws[ji]&&roc>=LOWER_BB_MIN_ROC7, bear=lips[li]<jaws[ji]&&roc<0;
    const alligatorState=lips[li]>jaws[ji]?'BULL':lips[li]<jaws[ji]?'BEAR':'FLAT';
    const rocState=roc>0?'POS':roc<0?'NEG':'FLAT';
    // Exact historical candidate: cross OUTSIDE the BB in the confirmed direction.
    const lowerCross=cPrev>=bbPrev.lo&&cNow<bbCur.lo;
    const upperCross=cPrev<=bbPrev.hi&&cNow>bbCur.hi;
    let dir=null;if(lowerCross&&bull)dir='BUY';else if(upperCross&&bear)dir='SELL';
    const bbState=lowerCross?'LOWER-CROSS':upperCross?'UPPER-CROSS':'NO-CROSS';
    const rawOuterDir=lowerCross?'BUY':upperCross?'SELL':null;
    if(rawOuterDir) aiQueueStrategyLesson(assetName,cNow,lastIndicatorCtx?.[assetName]?.ctx||null,{setup:rawOuterDir==='BUY'?'BB45_OUTER_LOWER':'BB45_OUTER_UPPER',dir:rawOuterDir,accepted:!!dir,
      reason:dir?'ALL_CONFIRMATIONS_PASSED':(rawOuterDir==='BUY'&&roc<LOWER_BB_MIN_ROC7?'LOWER_ROC7_BELOW_0.02PCT':'ALLIGATOR_ROC_DIRECTION_MISMATCH'),score:80,confidence:.80,
      measurement:{bbState,roc15:roc,alligator:alligatorState,bbLower:bbCur.lo,bbUpper:bbCur.hi,close:cNow}});
    // B15.10.12: latest accumulated strategy evidence shows outer-band reversal
    // is the unstable leg. Keep recording its qualified candidates for learning,
    // but do not send them to execution until a robust exhaustion/reclaim rule
    // proves itself out-of-sample.
    const outerWouldQualify=!!dir;
    dir=null;
    lastIndicators.bb50Live={asset:assetName,bb:bbState,tier:'LEARNING_ONLY_OUTER',alligator:alligatorState,roc:rocState,roc15:roc,qualified:false,wouldQualify:outerWouldQualify,ts:Date.now()};
    if(!dir){lastIndicators.v194HoldReason=`BB45 EXACT · ${bbState} · ALLIGATOR ${alligatorState} · ROC ${rocState} ${(roc*100).toFixed(4)}%`;return null;}
    // Bug-fixed execution: one decision per newly CLOSED 5s candle, never stale/live candle.
    const closed5=Number(a.lastClosed||0);
    if(!v288BbAlligatorRocSignal._seen)v288BbAlligatorRocSignal._seen=Object.create(null);
    if(!closed5||v288BbAlligatorRocSignal._seen[assetName]===closed5)return null;
    v288BbAlligatorRocSignal._seen[assetName]=closed5;
    const closeAgeMs=Math.max(0,Date.now()-((closed5+5)*1000));
    if(closeAgeMs>3500){lastIndicators.v194HoldReason=`BB45 EXACT · STALE 5S CLOSE ${Math.round(closeAgeMs)}ms`;return null;}
    return {dir,mode:'bb45-alligator-roc7-30s-test',tradeType:'BB45_ALLIGATOR_ROC',str:80,confidence:.80,executionExpiry:30,
      reason:`BB45/1.5 ${dir} cross · 15s Alligator ${alligatorState} · ROC ${(roc*100).toFixed(4)}% · LIVE 30s · shadow 5/15/60s`,
      reasons:['BB45_1.5_CROSS','ALLIGATOR_15S','ROC7_CONFIRM','FRESH_CLOSED_5S','BB45_ROC7_30S_DEMO_TEST'],
      measurement:{setup:'BB45_ALLIGATOR_ROC',model:'BB45_ROC7_30S_TEST',executionExpiry:30,shadowExpiries:[5,15,30,60],bbPeriod:45,bbDeviation:1.5,bbLower:bbCur.lo,bbUpper:bbCur.hi,alligatorLips:lips[li],alligatorJaws:jaws[ji],roc15:roc}};
  }

  // B15.9-MORE-TRADES: second entry family for directional continuation.
  // The original BB45 outer-band entry above is unchanged. This setup only
  // triggers on a fresh CLOSED 5s cross of the BB45 middle line when the
  // shifted 15s Alligator and ROC7 both confirm direction and the shifted
  // Alligator lines are themselves moving in that direction.
  function v288BbMidTrendContinuationSignal(assetName, px){
    const a=getAsset(assetName); if(!a)return null;
    const p5=getTF(a,'5s').prices.map(Number).filter(Number.isFinite);
    const p15=getTF(a,'15s').prices.map(Number).filter(Number.isFinite);
    if(p5.length<52||p15.length<20)return null;
    const bbAt=(end)=>{const q=p5.slice(end-45,end);if(q.length<45)return null;const m=q.reduce((x,y)=>x+y,0)/45;const sd=Math.sqrt(q.reduce((z,v)=>z+(v-m)*(v-m),0)/45);return {lo:m-1.5*sd,hi:m+1.5*sd,mid:m};};
    const smmaSeries=(arr,n)=>{if(arr.length<n)return[];const o=Array(arr.length).fill(NaN);let v=arr.slice(0,n).reduce((x,y)=>x+y,0)/n;o[n-1]=v;for(let i=n;i<arr.length;i++){v=(v*(n-1)+arr[i])/n;o[i]=v;}return o;};
    const prev=p5.length-1, cur=p5.length;
    const bbPrev=bbAt(prev),bbCur=bbAt(cur); if(!bbPrev||!bbCur)return null;
    const cPrev=p5[p5.length-2],cNow=p5[p5.length-1];
    const lips=smmaSeries(p15,3),jaws=smmaSeries(p15,10);
    const li=lips.length-1-1, ji=jaws.length-1-5;
    const lipPrev=li-1, jawPrev=ji-1;
    if(lipPrev<0||jawPrev<0||![lips[li],jaws[ji],lips[lipPrev],jaws[jawPrev]].every(Number.isFinite))return null;
    const rocLookback=7, base=p15[p15.length-1-rocLookback];
    const roc=p15.length>rocLookback?(p15[p15.length-1]-base)/Math.max(Math.abs(base),1e-12):0;
    // B15.10.12: raw-chart replay showed the weak continuation entries were the
    // near-zero ROC crosses. Require at least 0.01% directional ROC7 so the
    // mid-band cross has real 15s momentum instead of barely drifting over it.
    const MID_MIN_ROC7=0.00010;
    const bullAlign=lips[li]>jaws[ji]&&roc>=MID_MIN_ROC7;
    const bearAlign=lips[li]<jaws[ji]&&roc<=-MID_MIN_ROC7;
    const bullSlope=lips[li]>lips[lipPrev]&&jaws[ji]>=jaws[jawPrev];
    const bearSlope=lips[li]<lips[lipPrev]&&jaws[ji]<=jaws[jawPrev];
    const midUp=cPrev<=bbPrev.mid&&cNow>bbCur.mid;
    const midDown=cPrev>=bbPrev.mid&&cNow<bbCur.mid;
    // B15.10: immediate 15s MACD 5/13/6 confirmation. This keeps the tested
    // middle-line trigger but rejects crosses whose immediate momentum is already
    // pointing the other way. It is intentionally NOT a regime veto.
    const ef=emaSeries(p15,5), es=emaSeries(p15,13), macdSeries=[];
    for(let i=0;i<p15.length;i++) macdSeries.push(Number.isFinite(ef[i])&&Number.isFinite(es[i])?ef[i]-es[i]:NaN);
    const macdValid=macdSeries.filter(Number.isFinite), macdSigSeries=emaSeries(macdValid,6);
    const macdNow=macdValid.length?macdValid[macdValid.length-1]:0;
    const macdSig=macdSigSeries.length&&Number.isFinite(macdSigSeries[macdSigSeries.length-1])?macdSigSeries[macdSigSeries.length-1]:macdNow;
    const macdBull=macdNow>macdSig, macdBear=macdNow<macdSig;
    // Directional RSI is deliberately only a 50-line confirmation, not an
    // overbought/oversold filter: BUY momentum must be above 50; SELL below 50.
    const rsi15=rsi(p15,14);
    const rsiBull=Number.isFinite(rsi15)&&rsi15>=50;
    const rsiBear=Number.isFinite(rsi15)&&rsi15<=50;
    let dir=null;
    if(midUp&&bullAlign&&bullSlope&&macdBull&&rsiBull)dir='BUY';
    else if(midDown&&bearAlign&&bearSlope&&macdBear&&rsiBear)dir='SELL';
    const rawMidDir=midUp?'BUY':midDown?'SELL':null;
    if(rawMidDir) aiQueueStrategyLesson(assetName,cNow,lastIndicatorCtx?.[assetName]?.ctx||null,{setup:'BB45_TREND_MID_CONTINUATION',dir:rawMidDir,accepted:!!dir,
      reason:dir?'ALL_CONFIRMATIONS_PASSED':(!((rawMidDir==='BUY'&&bullAlign)||(rawMidDir==='SELL'&&bearAlign))?'ALLIGATOR_ROC_MISMATCH':!((rawMidDir==='BUY'&&bullSlope)||(rawMidDir==='SELL'&&bearSlope))?'ALLIGATOR_SLOPE_MISMATCH':'MACD_DIRECTION_MISMATCH'),
      score:78,confidence:.78,measurement:{roc15:roc,macd15:macdNow,macdSignal15:macdSig,bullAlign,bearAlign,bullSlope,bearSlope,bbMid:bbCur.mid,close:cNow}});
    if(!dir)return null;

    const closed5=Number(a.lastClosed||0);
    if(!v288BbMidTrendContinuationSignal._seen)v288BbMidTrendContinuationSignal._seen=Object.create(null);
    if(!closed5||v288BbMidTrendContinuationSignal._seen[assetName]===closed5)return null;
    const closeAgeMs=Math.max(0,Date.now()-((closed5+5)*1000));
    if(closeAgeMs>3500)return null;
    v288BbMidTrendContinuationSignal._seen[assetName]=closed5;

    const alligatorState=lips[li]>jaws[ji]?'BULL':'BEAR';
    return {dir,mode:'bb45-mid-trend-roc7-30s-test',tradeType:'BB45_TREND_MID_CONTINUATION',str:78,confidence:.78,executionExpiry:30,
      reason:`BB45 MID ${dir} continuation · 15s Alligator ${alligatorState} + slope · ROC ${(roc*100).toFixed(4)}% · MACD ${macdNow>macdSig?'BULL':'BEAR'} · LIVE 30s`,
      reasons:['BB45_MID_CROSS','ALLIGATOR_15S_TREND_SLOPE','ROC7_CONFIRM','MACD_15S_DIRECTION_CONFIRM','FRESH_CLOSED_5S','BB45_MID_CONTINUATION_30S_DEMO_TEST'],
      measurement:{setup:'BB45_TREND_MID_CONTINUATION',model:'BB45_MID_TREND_ROC7_MACD_30S_TEST',executionExpiry:30,bbPeriod:45,bbDeviation:1.5,bbMid:bbCur.mid,alligatorLips:lips[li],alligatorJaws:jaws[ji],roc15:roc,macd15:macdNow,macdSignal15:macdSig}};
  }



  // V24.1.287-B25 — BB WINNER PRO + BB RUNNER + HARD EXECUTION REVALIDATION
  // Three deterministic 15s lanes, all 60s expiry. AI remains learning-only.
  // Priority: Winner outer-band reversal > Runner directional continuation > Chop range mean-reversion.
  // V24.1.287-B31 — CANDIDATE 7B LIVE FORWARD TEST
  // Frozen from the marked 2026-09-26 research checkpoint. 45s expiry.
  // AI model is a fixed scorer only; it does NOT retrain or change live.
  const C7B_MODEL={"baseline":0.0419266362354085,"trees":[[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.046085207052330594,"f":35,"th":0.05442848695598713,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0030443820781537816,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.21697670777036807,"f":39,"th":0.9338573129441344,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.003864068638400306,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.319317048643792,"f":32,"th":0.13892758638871666,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.0009027706186332477,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.019039356687685218,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.018036197853704142,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.044287467710994975,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":5,"leaf":0},{"v":0.052646916054907976,"f":13,"th":-2.797197143473522,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.03198126151586712,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0008511654686605046,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.24605014841809913,"f":36,"th":0.5714285714285302,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.020531055925171855,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-7.532449527599028e-05,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017348133877866555,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.042470569316026476,"f":35,"th":0.05442848695598713,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.002944569536252905,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.2047885140289725,"f":39,"th":0.9338573129441344,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.0038042295753505087,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.3026660822521705,"f":32,"th":0.13892758638871666,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.0007199286101926176,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.018119265327651887,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016688560308173173,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.040816360563324286,"f":33,"th":-1.3529086155578578,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.023041104979769092,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.069993451488207,"f":38,"th":-0.6150600199211639,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.005586826186946479,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.16256704961845642,"f":39,"th":1.0040333802062598,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.0010522198118872617,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.015575986939443348,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016055961659509378,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.039140378028432524,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":5,"leaf":0},{"v":0.0523349680484084,"f":13,"th":-2.797197143473522,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.030606031307040277,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0008967612708249582,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.22952801922136565,"f":36,"th":0.5714285714285302,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.01937454335873585,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0001304496959337149,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.015448941575652481,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.03753175201399308,"f":33,"th":-1.3529086155578578,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.02216374044603199,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0655018487521871,"f":38,"th":-0.6150600199211639,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.005330140115187219,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.15324218025556616,"f":39,"th":1.016889173823875,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.0016633221528439056,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016294565377185467,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014866211509797767,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":21,"th":2.2238986456247902,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.03599802165127308,"f":35,"th":0.05442848695598713,"ml":1,"l":2,"r":7,"leaf":0},{"v":0.0710260205107453,"f":33,"th":2.005299179920432,"ml":1,"l":3,"r":6,"leaf":0},{"v":0.026684533526451965,"f":39,"th":1.085795552883873,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.0007572761205064337,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.023118031186674257,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.022013263988800734,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.007426171497928105,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014306579543415803,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":35,"th":0.9404106126025169,"ml":1,"l":1,"r":6,"leaf":0},{"v":-0.03325051170603233,"f":22,"th":0.9746808271435627,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0011892090686656518,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.3678277084666952,"f":19,"th":1.1344988136587792,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.017860030725569055,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.034564506451160895,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.36631578636315265,"f":13,"th":0.8791740666797117,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.013289326670214046,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02268081992182837,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":35,"th":0.9404106126025169,"ml":1,"l":1,"r":6,"leaf":0},{"v":-0.03185676005233767,"f":22,"th":0.9746808271435627,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0011418706539811701,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.3527455627841182,"f":19,"th":1.1344988136587792,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.017161695138449493,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.03368240652088924,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.3523765598926462,"f":33,"th":1.6279371964483496,"ml":1,"l":7,"r":8,"leaf":0},{"v":0.02099405364223477,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01619563178412045,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":30,"th":1.057636456291128,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.04005201887969795,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0019604360496648246,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.24511665922766412,"f":22,"th":0.2686962267940572,"ml":1,"l":4,"r":7,"leaf":0},{"v":-0.02070049709069165,"f":18,"th":-0.015379683060155849,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.013809023154233952,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01043438481834277,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.026091073425252635,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.010834739922640144,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.024899073066231674,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016934728960472385,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.5106443426078524,"f":34,"th":-0.5055372726807154,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.021330498390417334,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.02765726495693316,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.013316839117120166,"f":19,"th":0.943744249346778,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.008949550010484508,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.001840245861121205,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.4689862236882748,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.03297305440005105,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012450146016560082,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.022024482839107337,"f":33,"th":-1.3529086155578578,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.018387007213091916,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.04671614557005221,"f":24,"th":0.7088544590247209,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.003474596950985576,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.015394007780802271,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.024159148597790052,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016195454000034963,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.48801885989617494,"f":34,"th":-0.5055372726807154,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.020765619715659996,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.026500899814256337,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012728209637451735,"f":29,"th":1.1850758944878461,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.00014357600180475762,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.028413698461018884,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.45217199185836526,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.03183041793732563,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012041843869095115,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.020919098153088154,"f":3,"th":-1.124515511828844,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.006709145699131653,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.08446833246035383,"f":3,"th":-0.4565453457348409,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.016155935064342805,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00020897672781879082,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.017670919059421288,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.02072070446834298,"f":3,"th":2.4268700530862626,"ml":1,"l":3,"r":8,"leaf":0},{"v":-0.06310604448648253,"f":30,"th":-0.1318726913925372,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.002822868748378036,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.1983890736548197,"f":30,"th":-0.0012952890078552532,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.029029835460694042,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.004678790876270076,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.013126880675764676,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.02323351768864669,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.015442514707876458,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":4,"leaf":0},{"v":-0.018844187741835813,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012490289428418486,"f":19,"th":0.9476643473189138,"ml":0,"l":5,"r":8,"leaf":0},{"v":0.20216997989230226,"f":37,"th":0.11529024234479895,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.016887393747601925,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.003519823082552335,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0018452386512698665,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":25,"th":-0.6219717612020879,"ml":0,"l":1,"r":6,"leaf":0},{"v":0.32349307293817836,"f":23,"th":-0.9032066575925227,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.03177479009876593,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017389799393849388,"f":32,"th":-0.061832171309903775,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.014508634999967879,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.033535586112112256,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.027647300119905596,"f":30,"th":1.057636456291128,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.002894300854960024,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.009751171530711863,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":36,"th":0.8163716814207014,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.027814200686890774,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0025783740706978213,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.24228825162523882,"f":22,"th":-0.29434148717247266,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.002391479454429745,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.40240380475385606,"f":30,"th":1.7714935269373713,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.020401879050274782,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017540143527521087,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012517820816176669,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.4329114375178641,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.030445573617608707,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01141430532407792,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.019815545239821063,"f":3,"th":-1.124515511828844,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.006212150674571175,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.07879239143310467,"f":3,"th":-0.4565453457348409,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.01538132957404481,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00011668687610890529,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.022352066195745663,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01463041410489755,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.45490343041313225,"f":34,"th":-0.4695741780756018,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.015585443609652616,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0259032422310231,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012365328129607682,"f":29,"th":1.1850758944878461,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.00014040711936524346,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.027645401617462373,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.01689390927308128,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01951357490160196,"f":3,"th":2.4268700530862626,"ml":1,"l":3,"r":8,"leaf":0},{"v":-0.058927916907241355,"f":30,"th":-0.1318726913925372,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.0027034928238708067,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.1869464070070516,"f":30,"th":-0.0012952890078552532,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.027544867958372105,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.004380986294197257,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012217705518909324,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.42091449001588394,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.029496078412470622,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010846561150603085,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.019178122437017286,"f":36,"th":0.7789473684210994,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.0521918984819583,"f":36,"th":0.32323232323009615,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.0015539663827427,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010898043051381867,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.011210465571169299,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.01928876811594776,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0183876429505316,"f":25,"th":-0.6219717612020879,"ml":0,"l":3,"r":6,"leaf":0},{"v":0.38646440410657107,"f":20,"th":-2.15829724668144,"ml":0,"l":4,"r":5,"leaf":0},{"v":-0.019454040573535943,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.021147683895786334,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012171598513047043,"f":20,"th":-1.056065483702678,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.01627449306601182,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0007056833869281048,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":4,"th":0.9729918776838109,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.018847090615678675,"f":19,"th":0.8100717011676702,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.030658325499283445,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0325195457134646,"f":38,"th":-0.6150600199211639,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.0052734968667314235,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.09858350259286307,"f":36,"th":0.7789473684210994,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.005775635843712883,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.009967042665437012,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016500984928447305,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.407177275104716,"f":31,"th":1.4040299816571642,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.02658590449185503,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.020079180869908276,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.018775909897717876,"f":3,"th":2.4268700530862626,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.05657815949170664,"f":30,"th":-0.1318726913925372,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.002549093571842863,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0071330441524315846,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.011726169957881146,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.02138127290740545,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.013860720590635226,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":4,"leaf":0},{"v":-0.017633100104334606,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012310618890802235,"f":29,"th":1.1850758944878461,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.003147483078937055,"f":19,"th":0.9476643473189138,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.007629767265024773,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.002577914396156967,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.026932609895608306,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.018523967100092794,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017782491701185094,"f":25,"th":-0.6219717612020879,"ml":0,"l":3,"r":6,"leaf":0},{"v":0.3639985530796456,"f":20,"th":-2.15829724668144,"ml":0,"l":4,"r":5,"leaf":0},{"v":-0.01916450097746532,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.020086464663109954,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010918212086481393,"f":20,"th":-1.056065483702678,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.015765035051658348,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0007212030270896524,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":1.1735950929427066,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.018155302954512124,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.002478352058137878,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.18056574914667942,"f":37,"th":0.530085177921065,"ml":0,"l":4,"r":7,"leaf":0},{"v":-0.4017331262808904,"f":34,"th":-0.2227000083121596,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.0059441237744711295,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.023439821739726408,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.001141206529535921,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0160807063559806,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.3963196781239875,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.028010848152931915,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010581843972846821,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.018043662280733695,"f":33,"th":-1.3529086155578578,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.015591535593383908,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03886168396487486,"f":24,"th":0.7088544590247209,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.002893375353106185,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012920850175227625,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.020786151809329044,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.013439936249829072,"f":28,"th":-2.0795661948375574,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.5200536111648351,"f":29,"th":1.0393426515867183,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.004453072452175026,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03976546083618971,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.006805351946818818,"f":2,"th":-2.793597393162266,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.025716974051914986,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.000495973203357002,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.01780722354136,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017047318592652558,"f":25,"th":-0.6219717612020879,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.013722581999634484,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.009930719937959801,"f":20,"th":-1.056065483702678,"ml":0,"l":5,"r":6,"leaf":0},{"v":-0.015078273167702773,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.017801038063881797,"f":9,"th":0.9415626455965697,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.008141191029305833,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0017168323133520335,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":4,"th":0.9729918776838109,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.017409645538100246,"f":19,"th":0.8100717011676702,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.029125910979869933,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03034060440856712,"f":38,"th":-0.6150600199211639,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.005019304877956586,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.09294806218123493,"f":39,"th":1.0040333802062598,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.0005266666036423175,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.009921008211478594,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.015381416567079111,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":1.1735950929427066,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.017177565508441607,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.002373616837679012,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.17229759845679493,"f":33,"th":-0.4344513455903317,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.00521632326061514,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.31792117361123196,"f":37,"th":0.5498105526209022,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.023741713525272958,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00176751256355866,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.01534843649947814,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.01994095651459254,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012875361056745083,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":4,"leaf":0},{"v":-0.01677694628332484,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.012032044967284189,"f":29,"th":1.1850758944878461,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.0028670417802568824,"f":19,"th":0.9476643473189138,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.007193550789142197,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0024231796553483764,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.025980100025301045,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":35,"th":1.315288438754212,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.017706648213569372,"f":22,"th":0.9746808271435627,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0010540014270382736,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.21394317192811893,"f":19,"th":1.0599740461681102,"ml":1,"l":4,"r":7,"leaf":0},{"v":-0.36489413988938363,"f":34,"th":0.47889533629437475,"ml":0,"l":5,"r":6,"leaf":0},{"v":-0.026660938320085675,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0038614335812407192,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016856884179469265,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014675177187469676,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.3724181426618995,"f":31,"th":1.4040299816571642,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.02481988547706302,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.019764427599174555,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.017062384909249044,"f":3,"th":2.3776596236797665,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.05264828310924567,"f":24,"th":0.5286630831787109,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.0011115480473158927,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.02462134516183002,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.010630455470257929,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.017123381477313845,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016344801813737795,"f":25,"th":-0.6219717612020879,"ml":0,"l":3,"r":8,"leaf":0},{"v":0.3235068919221922,"f":23,"th":-0.9032066575925227,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.029508486660827588,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.03613994328676791,"f":23,"th":-0.2873229572135411,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.021452108288211136,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02559123587578536,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00036141797192060807,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.01927562361661542,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012415372877193288,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":4,"leaf":0},{"v":-0.01614523202902918,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.011542101952321474,"f":29,"th":1.1850758944878461,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.002918844706247704,"f":39,"th":1.016889173823875,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.003012312092819156,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.005545103202549915,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02523176267779711,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.36472375796658213,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.026287252484321594,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01058794930386663,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0163942480799038,"f":3,"th":-1.0149273806872112,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.004941612549779989,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.06972684902325192,"f":3,"th":-0.4565453457348409,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.017340882575146654,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.00023310584763678964,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":1.1735950929427066,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.016368687944774474,"f":36,"th":0.32323232323009615,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0022882604875428137,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.1655174113405437,"f":33,"th":-0.4344513455903317,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.004951858939573486,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.3047325802462098,"f":37,"th":0.5498105526209022,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.02272951685804087,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0017305544720662193,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014635016956852029,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.01649572453894219,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.015757854572549673,"f":25,"th":-0.6219717612020879,"ml":0,"l":3,"r":6,"leaf":0},{"v":0.3069483194395641,"f":20,"th":-2.15829724668144,"ml":0,"l":4,"r":5,"leaf":0},{"v":-0.019528023316342083,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.01758560215403228,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.008251494845924254,"f":20,"th":-1.056065483702678,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.014446613761321869,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0007365556372599483,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.018684378566259634,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012165946842262038,"f":1,"th":-1.8327641477718482,"ml":0,"l":3,"r":8,"leaf":0},{"v":-0.23814717999471044,"f":23,"th":0.18232253641231624,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.01991586344151909,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.07940817318165345,"f":22,"th":0.8679013418347961,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.01873823774051387,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.015490621501825843,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.001072826302935161,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":34,"th":0.7594469089173903,"ml":1,"l":1,"r":4,"leaf":0},{"v":-0.02087246320592279,"f":22,"th":0.9746808271435627,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0010248427517644924,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.011678983223918247,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.2790628754922077,"f":33,"th":1.6279371964483496,"ml":1,"l":5,"r":6,"leaf":0},{"v":0.0231053932687118,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.4359252916709468,"f":33,"th":2.0655991226619017,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.045693256258862405,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014131892800585867,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.35116634684397363,"f":31,"th":1.4040299816571642,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.023665741191836304,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01929805703835459,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016364693415334645,"f":3,"th":2.4268700530862626,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.049309729308666256,"f":24,"th":0.5286630831787109,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.0009845810513780305,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.022754456863544027,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.010257829801839605,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":31,"th":-2.7666491386349885,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.02202039937462538,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010160163439216868,"f":34,"th":-0.6182230807567949,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.47370506563063125,"f":33,"th":-0.2221840244016388,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.0035803919476093717,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.04055036785777728,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.008450272345378195,"f":19,"th":0.8100717011676702,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.027963093717452585,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00016586992744684203,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":9,"th":0.9354362474520657,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.00583259985834331,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03961675096552434,"f":37,"th":1.1735950929427066,"ml":1,"l":3,"r":8,"leaf":0},{"v":-0.06328243916721493,"f":35,"th":0.06657741381117262,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.0017270867109189208,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.20076629716278357,"f":19,"th":1.1530884217488768,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.009743997895645135,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.029481302767177503,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.016319097920079472,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":27,"th":1.572251533568255,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.00845075438637017,"f":4,"th":0.2407955827633103,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.001987709677636462,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.12591686353424597,"f":19,"th":1.1395282122949708,"ml":1,"l":4,"r":7,"leaf":0},{"v":-0.17334783521545116,"f":32,"th":-1.1353435892770591,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.011347036481808443,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.009922704070423574,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.023354818387748395,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0248258343510641,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":35,"th":1.315288438754212,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.01613185686704467,"f":39,"th":1.085795552883873,"ml":1,"l":2,"r":7,"leaf":0},{"v":-0.04319553039275217,"f":39,"th":1.0282626634219585,"ml":1,"l":3,"r":4,"leaf":0},{"v":0.0009588926949407517,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.25576380885690964,"f":33,"th":1.7982671398102303,"ml":1,"l":5,"r":6,"leaf":0},{"v":-0.014438514395376901,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.008177435618725592,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.010721584135890494,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.013361711346389948,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":38,"th":-0.6150600199211639,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.00493451676967877,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.04491751528158855,"f":39,"th":0.9464443724916992,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.0060573223518669015,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.1378739806153826,"f":37,"th":0.6088093725597182,"ml":1,"l":5,"r":6,"leaf":0},{"v":-0.009182004895313239,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.1160166882697155,"f":23,"th":-2.1004634453551088,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.033327249649944816,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.007943222002252339,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.33878345864304693,"f":31,"th":1.4040299816571642,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.022783042505733403,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.018334934977841232,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01560000058041193,"f":3,"th":2.3776596236797665,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.047900619445375804,"f":24,"th":0.5286630831787109,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.000980358757030433,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.02309885237672555,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.00967464885948113,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":37,"th":-1.3127254110387467,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.017927113271537534,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.011674104715896302,"f":36,"th":-0.833333333313596,"ml":0,"l":3,"r":4,"leaf":0},{"v":-0.015484413691315702,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.011311054453393556,"f":29,"th":1.1850758944878461,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.002694980130895632,"f":39,"th":1.016889173823875,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.002810747371767785,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.005171896003118283,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.024446583494170088,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":17,"th":1.2883822329932202,"ml":1,"l":1,"r":8,"leaf":0},{"v":0.017265649860593806,"f":37,"th":-1.3127254110387467,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.021650114860613807,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0029074603079987087,"f":1,"th":-1.8327641477718482,"ml":0,"l":4,"r":7,"leaf":0},{"v":-0.22481448128637374,"f":23,"th":0.18232253641231624,"ml":1,"l":5,"r":6,"leaf":0},{"v":-0.019020544633932518,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.003284996211871435,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0017660592990836489,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.013586108586039909,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":31,"th":-2.7666491386349885,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.021115396492308744,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.009566479287660967,"f":34,"th":-0.6182230807567949,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.4608098840986465,"f":33,"th":-0.2221840244016388,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.0030908025316012844,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03894104896037126,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.008563330600948509,"f":13,"th":-0.7981239894616955,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.006932914983902319,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0016174767386716554,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":4,"th":0.9729918776838109,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.015338277602438203,"f":1,"th":0.6038230062926496,"ml":1,"l":2,"r":7,"leaf":0},{"v":0.05732631221312267,"f":1,"th":-1.8327641477718482,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.15372334222447967,"f":23,"th":0.18232253641231624,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.014947181782585408,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0046634367925472075,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.005081578413166718,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.005932811050173086,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.013472960864207082,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":38,"th":-0.6150600199211639,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.004816033199997348,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.04416129990358191,"f":39,"th":0.9464443724916992,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.005750976488240543,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.13313616526006955,"f":37,"th":0.6088093725597182,"ml":1,"l":5,"r":6,"leaf":0},{"v":-0.008823192135790978,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.10914675267809319,"f":23,"th":-2.1004634453551088,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.03245997985782542,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.007575999642585289,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":36,"th":0.32323232323009615,"ml":1,"l":1,"r":4,"leaf":0},{"v":0.05548853400521419,"f":19,"th":1.0407777622301138,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.005445674297043646,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.006685402769417905,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.09824091062150467,"f":37,"th":0.6088093725597182,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.31726391582033536,"f":13,"th":-0.7480885634357548,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.004199779659539531,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01930182518972037,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.005264716331186208,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":19,"th":0.0,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.024028869244518428,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.008228302355550459,"f":25,"th":1.4577486582431294,"ml":1,"l":3,"r":8,"leaf":0},{"v":0.001147285434260247,"f":25,"th":0.5311125550872808,"ml":1,"l":4,"r":5,"leaf":0},{"v":-0.0015545538050494906,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.1869967695798962,"f":33,"th":1.6279371964483496,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.01179110422783364,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016554949284552513,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.026328635461779708,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.015256136872307407,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014116068443570336,"f":5,"th":0.0663471843757624,"ml":1,"l":3,"r":8,"leaf":0},{"v":0.09497469163784898,"f":29,"th":1.018333100947102,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.009267105477418677,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.11011930023041709,"f":33,"th":-0.9084394756159146,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.030916062442023128,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00025419435090116236,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.003000291358125523,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":31,"th":-2.7666491386349885,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.020557828057498336,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.009732757908475961,"f":34,"th":-0.6182230807567949,"ml":0,"l":3,"r":6,"leaf":0},{"v":-0.4456395875944782,"f":33,"th":-0.2221840244016388,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.0029850923772230032,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03762618472295626,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.007793780161663042,"f":27,"th":1.572251533568255,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.00011947184561981408,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.028875089958597416,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":33,"th":-1.3529086155578578,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.32571384152807226,"f":31,"th":1.4040299816571642,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.02199866483866508,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.01781535678767662,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.015445386471527427,"f":24,"th":0.7088544590247209,"ml":1,"l":5,"r":8,"leaf":0},{"v":-0.04130647227308661,"f":22,"th":0.9746808271435627,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.000124417343081741,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.011026495465359243,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.011100943899408201,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":17,"th":1.2883822329932202,"ml":1,"l":1,"r":8,"leaf":0},{"v":0.016141770188898667,"f":37,"th":-1.3127254110387467,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.020902788151219126,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.00229710380379053,"f":28,"th":-2.0795661948375574,"ml":0,"l":4,"r":5,"leaf":0},{"v":-0.018277739518678015,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02109149112598764,"f":31,"th":-2.7666491386349885,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.032426917590946215,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0003000786829925079,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.013050908152727119,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":29,"th":0.8340830122024803,"ml":0,"l":1,"r":6,"leaf":0},{"v":0.32818228332868926,"f":25,"th":1.4577486582431294,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.024237830095592102,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.26175142326762707,"f":3,"th":0.5306666600827403,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.0146551545092135,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.030331671409243494,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.015240537784941586,"f":38,"th":-0.6150600199211639,"ml":0,"l":7,"r":8,"leaf":0},{"v":0.004519989949028674,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0026262958388652852,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":9,"th":0.9354362474520657,"ml":0,"l":1,"r":8,"leaf":0},{"v":0.13497562232202737,"f":34,"th":0.5076677539474413,"ml":1,"l":2,"r":5,"leaf":0},{"v":0.05911458387704444,"f":32,"th":1.890230229176792,"ml":1,"l":3,"r":4,"leaf":0},{"v":0.00468392101625601,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.03035297889380471,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.6061993383599668,"f":2,"th":3.1521853528501103,"ml":1,"l":6,"r":7,"leaf":0},{"v":0.037838349148634855,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.016966683700648525,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0014759265807264622,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":36,"th":0.32323232323009615,"ml":1,"l":1,"r":2,"leaf":0},{"v":0.0021030933716529748,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0935485517221375,"f":37,"th":0.6088093725597182,"ml":1,"l":3,"r":8,"leaf":0},{"v":-0.3032109076977325,"f":33,"th":-0.4344513455903317,"ml":0,"l":4,"r":5,"leaf":0},{"v":0.0027986317410125623,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.4850273965927345,"f":27,"th":-0.28952156479764024,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.0050069669831534795,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.026419885890969014,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.005055312291961686,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":18,"th":-2.3924071751015727,"ml":0,"l":1,"r":2,"leaf":0},{"v":-0.014741870715167568,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.013514681582445877,"f":5,"th":0.0663471843757624,"ml":1,"l":3,"r":8,"leaf":0},{"v":0.09133324525743874,"f":29,"th":1.018333100947102,"ml":1,"l":4,"r":5,"leaf":0},{"v":0.008912984234796662,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.10592189668932661,"f":33,"th":-0.9084394756159146,"ml":0,"l":6,"r":7,"leaf":0},{"v":-0.030067283404491902,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.00019468493440879663,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0028903469696337026,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":19,"th":0.0,"ml":0,"l":1,"r":2,"leaf":0},{"v":0.023013010969420038,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.008146116140598387,"f":25,"th":1.4577486582431294,"ml":1,"l":3,"r":8,"leaf":0},{"v":0.0008206909731701579,"f":25,"th":0.5311125550872808,"ml":1,"l":4,"r":7,"leaf":0},{"v":-0.037778669639455274,"f":33,"th":-1.4113173220879038,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.022148042071444395,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.0024053886159839002,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.007211576245177796,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.02519112301026183,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":38,"th":-0.6150600199211639,"ml":0,"l":1,"r":4,"leaf":0},{"v":0.11359619180287084,"f":29,"th":1.0774577052380365,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.008193064941995835,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010041838719592118,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.042198158698878344,"f":39,"th":0.9464443724916992,"ml":0,"l":5,"r":6,"leaf":0},{"v":0.005434833238770344,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.12643418080014387,"f":28,"th":2.258937135427141,"ml":1,"l":7,"r":8,"leaf":0},{"v":-0.006367726526057615,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.018127854232165144,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":17,"th":1.2883822329932202,"ml":1,"l":1,"r":8,"leaf":0},{"v":0.015417005717943171,"f":37,"th":-1.3127254110387467,"ml":0,"l":2,"r":3,"leaf":0},{"v":0.02019660132441834,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0020652293321710537,"f":28,"th":-2.0795661948375574,"ml":0,"l":4,"r":5,"leaf":0},{"v":-0.01767785024933981,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02023085664846624,"f":31,"th":-2.7666491386349885,"ml":0,"l":6,"r":7,"leaf":0},{"v":0.03143468351408642,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0002843704441374044,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.012483229061328873,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":27,"th":1.572251533568255,"ml":1,"l":1,"r":8,"leaf":0},{"v":-0.007933512832957006,"f":4,"th":0.2407955827633103,"ml":1,"l":2,"r":5,"leaf":0},{"v":0.04691450969101793,"f":23,"th":-2.2760195799931533,"ml":0,"l":3,"r":4,"leaf":0},{"v":0.035382091100728735,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.0011650139330686856,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.11879659218449432,"f":19,"th":1.1395282122949708,"ml":1,"l":6,"r":7,"leaf":0},{"v":-0.006566361616009953,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.02243767100998628,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.022441739953328543,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}],[{"v":0.0,"f":34,"th":0.7594469089173903,"ml":1,"l":1,"r":4,"leaf":0},{"v":-0.018340002568555072,"f":22,"th":0.9746808271435627,"ml":1,"l":2,"r":3,"leaf":0},{"v":0.0009738821219125198,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.010693271739244765,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.2452314646499766,"f":33,"th":1.6279371964483496,"ml":1,"l":5,"r":6,"leaf":0},{"v":0.020705405735417216,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":-0.3990515449778876,"f":33,"th":2.0655991226619017,"ml":0,"l":7,"r":8,"leaf":0},{"v":-0.043373421409845285,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1},{"v":0.014551381977483943,"f":0,"th":0.0,"ml":0,"l":0,"r":0,"leaf":1}]]};
  const C7B_META={"features":["d9","d20","s2050","s50100","sl20","rsi","body","r1","r3","vol","d9_10","d20_10","s2050_10","s50100_10","sl20_10","rsi_10","body_10","r1_10","r3_10","vol_10","d9_30","d20_30","s2050_30","s50100_30","sl20_30","rsi_30","body_30","r1_30","r3_30","vol_30","d9_60","d20_60","s2050_60","s50100_60","sl20_60","rsi_60","body_60","r1_60","r3_60","vol_60"],"expiry_seconds":45,"sleeves":{"AUDUSD_otc":{"BUY":{"threshold":0.65,"vol_max":1.0},"SELL":{"threshold":0.56,"vol_max":1.1}},"BTCUSD_otc":{"BUY":{"threshold":0.61,"vol_max":1.0},"SELL":{"threshold":0.58,"vol_max":1.4}},"EURTRY_otc":{"BUY":{"threshold":0.59,"vol_max":1.0},"SELL":{"threshold":0.58,"vol_max":1.0}},"EURCHF_otc":{"BUY":{"threshold":0.61,"vol_max":0.9}}},"execution":{"same_market_lock_seconds":45,"one_entry_per_timestamp":true},"training_split":"first 60% only","final_holdout":"80-100% unopened"};
  const C7B_FEATURES=C7B_META.features;
  function c7bEwm(a,alpha){const o=new Array(a.length).fill(NaN);let e=NaN;for(let i=0;i<a.length;i++){const v=Number(a[i]);if(!Number.isFinite(v)){o[i]=e;continue;}e=Number.isFinite(e)?alpha*v+(1-alpha)*e:v;o[i]=e;}return o;}
  function c7bFeatureSeries(rows){
    const n=rows.length,O=rows.map(r=>+r.open),H=rows.map(r=>+r.high),L=rows.map(r=>+r.low),C=rows.map(r=>+r.close),T=rows.map(r=>+r.ts);
    const tr=new Array(n);for(let i=0;i<n;i++){const pc=i?C[i-1]:C[i];tr[i]=Math.max(H[i]-L[i],Math.abs(H[i]-pc),Math.abs(L[i]-pc));}
    const atr=c7bEwm(tr,1/14), e9=c7bEwm(C,2/10),e20=c7bEwm(C,2/21),e50=c7bEwm(C,2/51),e100=c7bEwm(C,2/101);
    const gain=new Array(n).fill(NaN),loss=new Array(n).fill(NaN);for(let i=1;i<n;i++){const d=C[i]-C[i-1];gain[i]=Math.max(d,0);loss[i]=Math.max(-d,0);}
    const ag=c7bEwm(gain,1/14),al=c7bEwm(loss,1/14), out=[];
    for(let i=0;i<n;i++){const A=Math.max(Math.abs(atr[i]||0),1e-12);let rsi=0;if(Number.isFinite(ag[i])&&Number.isFinite(al[i])){const rs=al[i]===0?Infinity:ag[i]/al[i];rsi=(100-100/(1+rs)-50)/25;}
      let vm=NaN;if(i>=14){let z=0,cnt=0;for(let j=Math.max(0,i-39);j<=i;j++)if(Number.isFinite(atr[j])){z+=atr[j];cnt++;}if(cnt>=15)vm=atr[i]/(z/cnt);}
      out.push({t:T[i],d9:(C[i]-e9[i])/A,d20:(C[i]-e20[i])/A,s2050:(e20[i]-e50[i])/A,s50100:(e50[i]-e100[i])/A,sl20:i>=3?(e20[i]-e20[i-3])/A:NaN,rsi,body:(C[i]-O[i])/Math.max(H[i]-L[i],1e-12),r1:i?((C[i]-C[i-1])/A):NaN,r3:i>=3?((C[i]-C[i-3])/A):NaN,vol:vm});
    }return out;
  }
  function c7bAgg(raw,sec){const ms=sec*1000,need=sec/5,out=[];let i=0;while(i<raw.length){const b=Math.floor(raw[i].ts/ms)*ms,g=[];while(i<raw.length&&Math.floor(raw[i].ts/ms)*ms===b)g.push(raw[i++]);if(g.length!==need)continue;let ok=true;for(let j=0;j<g.length;j++)if(+g[j].ts!==b+j*5000){ok=false;break;}if(!ok)continue;out.push({ts:b+ms,open:+g[0].open,high:Math.max(...g.map(x=>+x.high)),low:Math.min(...g.map(x=>+x.low)),close:+g[g.length-1].close});}return out;}
  function c7bLatestAt(series,t){let lo=0,hi=series.length-1,b=-1;while(lo<=hi){const m=(lo+hi)>>1;if(series[m].t<=t){b=m;lo=m+1;}else hi=m-1;}return b>=0?series[b]:null;}
  function c7bStrategyRows(asset){
    // B32.20.5 — ONE CANONICAL 5s STRATEGY VIEW.
    // The diagnostic proved the main Pocket Option 5s store could already contain 1,200+
    // candles while the micro engine still reported 14..23/24 from the separate research
    // archive. Never let the smaller side archive hide a larger chart-history bootstrap.
    // Build one timestamp-deduped view every evaluation. The canonical PO chart store wins
    // on duplicate timestamps because it is the same 5s series used by the rest of KAOS.
    asset=String(asset||'').trim();
    const merged=new Map();
    const put=(r,priority)=>{
      if(!r)return; const ts=Number(r.ts),o=Number(r.open),h=Number(r.high),l=Number(r.low),c=Number(r.close);
      if(!Number.isFinite(ts)||![o,h,l,c].every(Number.isFinite)||c<=0)return;
      const prev=merged.get(ts); if(prev&&prev.priority>priority)return;
      merged.set(ts,{ts,open:o,high:h,low:l,close:c,closeTs:Number(r.closeTs)||ts+5000,priority});
    };
    for(const r of (marketCandleHistory.byAsset[asset]||[]))put(r,1);
    for(const r of (raw5History.byAsset[asset]||[]))put(r,2);
    const a=getAsset(asset);
    if(a&&a.rates){
      const keys=Object.keys(a.rates).map(Number).filter(Number.isFinite).sort((x,y)=>x-y);
      for(const b of keys){const q=a.rates[b];if(!Array.isArray(q)||q.length<4)continue;put({ts:b*1000,open:q[0],high:q[1],low:q[2],close:q[3],closeTs:(b+5)*1000},3);}
    }
    const rows=[...merged.values()].sort((x,y)=>x.ts-y.ts).slice(-3600).map(({priority,...r})=>r);
    const chartN=a&&a.rates?Object.keys(a.rates).length:0, realN=(marketCandleHistory.byAsset[asset]||[]).length, rawN=(raw5History.byAsset[asset]||[]).length;
    const source=chartN>=24?'CANONICAL_PO_5S':realN>=24?'REAL_ARCHIVE':rawN>=24?'RAW5_ARCHIVE':'MERGED_5S';
    return {rows,source,counts:{canonical:chartN,real:realN,raw:rawN,merged:rows.length}};
  }
  function c7bVector(asset){
    const src=c7bStrategyRows(asset),rows=src.rows;if(rows.length<120)return null;const base=c7bFeatureSeries(rows),cur=base[base.length-1],t=cur.t,v=[];
    const maps={5:cur};for(const tf of [10,30,60]){const z=c7bFeatureSeries(c7bAgg(rows,tf));maps[tf]=c7bLatestAt(z,t);}
    const names=['d9','d20','s2050','s50100','sl20','rsi','body','r1','r3','vol'];
    for(const tf of [5,10,30,60]){const q=maps[tf];for(const nm of names){let x=q?Number(q[nm]):NaN;v.push(Number.isFinite(x)?x:0);}}
    return {x:v,t,vol:Number.isFinite(cur.vol)?cur.vol:0,rawCount:rows.length,historySource:src.source};
  }
  function c7bProb(x){let z=Number(C7B_MODEL.baseline)||0;for(const tree of C7B_MODEL.trees){let i=0;for(;;){const n=tree[i];if(n.leaf){z+=n.v;break;}const v=x[n.f];i=(!Number.isFinite(v)?!!n.ml:v<=n.th)?n.l:n.r;}}return 1/(1+Math.exp(-z));}
  // B32.3 terminal research stream. 7B's 40-feature schema is intentionally kept
  // separate from the existing 104-feature AI trainer. These records let us test
  // 7B/AI agreement and multiple forward horizons without changing live authority.
  const C7B_RESEARCH=[]; const C7B_RESEARCH_MAX=5000;
  function c7bResearchCapture(asset,fv,p,vol,price){
    const now=Number(fv?.t)||Date.now(), px=Number(price);
    // Resolve forward outcomes for older observations when enough time has elapsed.
    for(let i=Math.max(0,C7B_RESEARCH.length-500);i<C7B_RESEARCH.length;i++){
      const r=C7B_RESEARCH[i]; if(r.asset!==asset||!Number.isFinite(px))continue;
      for(const h of [5,10,15,30,45,60]) if(r.forward[h]==null && now-r.ts>=h*1000) r.forward[h]={price:px,delta:px-r.price,up:px>r.price?1:px<r.price?0:.5};
    }
    const prev=C7B_RESEARCH[C7B_RESEARCH.length-1]; if(prev&&prev.asset===asset&&prev.ts===now)return;
    const ai=indicatorStateByAsset[String(asset||'')]||{};
    C7B_RESEARCH.push({ts:now,asset,price:Number.isFinite(px)?px:null,probUp:p,vol,x:fv.x.slice(),source:fv.historySource,
      decision:(p>=.61&&vol<=1?'BUY':p<=.42&&vol<=1.1?'SELL':'HOLD'),
      ai:{xgbUp:ai?.xgbAI?.previewUp??ai?.xgbAI?.rawUp??null,lgbUp:ai?.xgbAI?.shadowLgbUp??null,status:ai?.xgbAI?.status||'collecting'},forward:{5:null,10:null,15:null,30:null,45:null,60:null}});
    if(C7B_RESEARCH.length>C7B_RESEARCH_MAX)C7B_RESEARCH.splice(0,C7B_RESEARCH.length-C7B_RESEARCH_MAX);
  }
  // B32.18 — MARKET-STATE / CONFIRMED-REVERSAL EXECUTION GATE
  // KAOS Strategy still finds directional opportunities. This layer decides whether
  // a counter-trend opportunity is actually executable. Oversold/overbought is NOT
  // confirmation. A reversal must first print price-action evidence and then break
  // short-term structure. One confirmed transition can be consumed only once;
  // subsequent same-direction trades must be continuation/runner opportunities.
  const C7B_MARKET_STATE=Object.create(null);
  function c7bReversalStructure(assetName, dir, fv){
    const src=c7bStrategyRows(assetName), r=src.rows.slice(-18);
    if(r.length<8)return {confirmed:false,pattern:'NONE',reason:'not enough 5s structure'};
    const eps=1e-12;
    const body=x=>Math.abs(x.close-x.open), range=x=>Math.max(x.high-x.low,eps);
    const bull=x=>x.close>x.open, bear=x=>x.close<x.open;
    const lowerWick=x=>Math.min(x.open,x.close)-x.low, upperWick=x=>x.high-Math.max(x.open,x.close);
    const a=r[r.length-3], b=r[r.length-2], c=r[r.length-1];
    const bullEngulf=bear(a)&&bull(b)&&b.open<=a.close&&b.close>=a.open&&body(b)>=body(a)*0.9;
    const bearEngulf=bull(a)&&bear(b)&&b.open>=a.close&&b.close<=a.open&&body(b)>=body(a)*0.9;
    const hammer=(lowerWick(b)>=Math.max(body(b)*1.8,range(b)*0.45))&&(upperWick(b)<=range(b)*0.28)&&(b.close>=b.low+range(b)*0.55);
    const shooting=(upperWick(b)>=Math.max(body(b)*1.8,range(b)*0.45))&&(lowerWick(b)<=range(b)*0.28)&&(b.close<=b.low+range(b)*0.45);
    // Double bottom/top: two local extremes separated by a bounce/pullback, then
    // confirmation must close through the intervening neckline. Tolerance scales
    // from the recent price range so it works across currencies/crypto/OTC prices.
    const q=r.slice(-12), recentRange=Math.max(...q.map(x=>x.high))-Math.min(...q.map(x=>x.low));
    const tol=Math.max(recentRange*0.12,Math.abs(c.close)*0.00002);
    let doubleBottom=false,doubleTop=false,dbNeck=-Infinity,dtNeck=Infinity;
    for(let i=1;i<q.length-5;i++){
      if(q[i].low<=q[i-1].low&&q[i].low<=q[i+1].low){
        for(let j=i+3;j<q.length-1;j++) if(q[j].low<=q[j-1].low&&q[j].low<=q[j+1].low&&Math.abs(q[j].low-q[i].low)<=tol){
          const neck=Math.max(...q.slice(i,j+1).map(x=>x.high)); if(c.close>neck){doubleBottom=true;dbNeck=neck;}
        }
      }
      if(q[i].high>=q[i-1].high&&q[i].high>=q[i+1].high){
        for(let j=i+3;j<q.length-1;j++) if(q[j].high>=q[j-1].high&&q[j].high>=q[j+1].high&&Math.abs(q[j].high-q[i].high)<=tol){
          const neck=Math.min(...q.slice(i,j+1).map(x=>x.low)); if(c.close<neck){doubleTop=true;dtNeck=neck;}
        }
      }
    }
    // Confirmation is deliberately AFTER the reversal candle/pattern: latest 5s
    // close must break the immediate structure created before it.
    const prior3=r.slice(-5,-1);
    const swingHigh=Math.max(...prior3.map(x=>x.high)), swingLow=Math.min(...prior3.map(x=>x.low));
    const bullBreak=bull(c)&&c.close>swingHigh;
    const bearBreak=bear(c)&&c.close<swingLow;
    const higherLow=Math.min(b.low,c.low)>Math.min(...r.slice(-8,-3).map(x=>x.low));
    const lowerHigh=Math.max(b.high,c.high)<Math.max(...r.slice(-8,-3).map(x=>x.high));
    const bullPattern=bullEngulf||hammer||doubleBottom;
    const bearPattern=bearEngulf||shooting||doubleTop;
    const confirmed=dir==='BUY' ? ((bullPattern&&bullBreak)||(doubleBottom&&c.close>dbNeck)||(higherLow&&bullBreak))
                                : ((bearPattern&&bearBreak)||(doubleTop&&c.close<dtNeck)||(lowerHigh&&bearBreak));
    const pattern=dir==='BUY'?(doubleBottom?'DOUBLE_BOTTOM':bullEngulf?'BULL_ENGULF':hammer?'HAMMER':higherLow?'HIGHER_LOW':'NONE')
                             :(doubleTop?'DOUBLE_TOP':bearEngulf?'BEAR_ENGULF':shooting?'SHOOTING_STAR':lowerHigh?'LOWER_HIGH':'NONE');
    // B32.19 Price Action Toolkit: expose structure/support/resistance/neckline
    // evidence to the execution log/UI. These are observations; they do not trade
    // by themselves. A counter-trend entry still requires confirmed structure.
    const localSupport=Math.min(...q.slice(-8).map(x=>x.low));
    const localResistance=Math.max(...q.slice(-8).map(x=>x.high));
    const neckline=dir==='BUY'?(Number.isFinite(dbNeck)?dbNeck:swingHigh):(Number.isFinite(dtNeck)?dtNeck:swingLow);
    const bos=dir==='BUY'?bullBreak:bearBreak;
    const rejection=dir==='BUY'?hammer:shooting;
    const engulfing=dir==='BUY'?bullEngulf:bearEngulf;
    const structure=dir==='BUY'?(higherLow?'HIGHER_LOW':bullBreak?'BULL_BOS':'BOTTOM_WATCH'):(lowerHigh?'LOWER_HIGH':bearBreak?'BEAR_BOS':'TOP_WATCH');
    return {confirmed,pattern,bullBreak,bearBreak,higherLow,lowerHigh,swingHigh,swingLow,localSupport,localResistance,neckline,bos,rejection,engulfing,structure,sourceTs:fv?.t||0,
      reason:confirmed?`${pattern} + ${dir==='BUY'?'bullish':'bearish'} structure break`:`${pattern} watch · waiting for ${dir==='BUY'?'bullish':'bearish'} structure break`};
  }
  function c7bMarketStateGate(assetName,dir,fv){
    const x=fv?.x||[];
    // 30s/60s trend structure from KAOS Strategy's own frozen feature vector.
    const t30=(Number(x[22])||0)+(Number(x[23])||0)+(Number(x[24])||0);
    const t60=(Number(x[32])||0)+(Number(x[33])||0)+(Number(x[34])||0);
    const bearish=t30<0&&t60<0, bullish=t30>0&&t60>0;
    const counter=(dir==='BUY'&&bearish)||(dir==='SELL'&&bullish);
    const st=C7B_MARKET_STATE[assetName]||(C7B_MARKET_STATE[assetName]={trend:'MIXED',transitionSeq:0,consumedKey:null,last:null});
    const trend=bearish?'DOWNTREND':bullish?'UPTREND':'MIXED'; st.trend=trend;
    if(!counter){
      st.last={state:trend,dir,kind:'CONTINUATION',allowed:true,at:Date.now()};
      return {allowed:true,kind:'CONTINUATION',state:trend,reason:`${trend} ${dir} continuation`,priceAction:null};
    }
    const rv=c7bReversalStructure(assetName,dir,fv);
    const key=`${dir}:${rv.pattern}:${rv.sourceTs}`;
    if(!rv.confirmed){
      st.last={state:dir==='BUY'?'BOTTOM_WATCH':'TOP_WATCH',dir,kind:'REVERSAL_WATCH',allowed:false,pattern:rv.pattern,at:Date.now()};
      return {allowed:false,kind:'REVERSAL_WATCH',state:dir==='BUY'?'BOTTOM_WATCH':'TOP_WATCH',reason:rv.reason,pattern:rv.pattern,priceAction:rv};
    }
    if(st.consumedKey===key){
      return {allowed:false,kind:'REVERSAL_CONSUMED',state:'REVERSAL_CONFIRMED',reason:`${rv.pattern} confirmation already consumed`,pattern:rv.pattern,priceAction:rv};
    }
    st.transitionSeq++; st.consumedKey=key;
    st.last={state:'REVERSAL_CONFIRMED',dir,kind:'REVERSAL_CONFIRMATION',allowed:true,pattern:rv.pattern,transitionSeq:st.transitionSeq,at:Date.now()};
    return {allowed:true,kind:'REVERSAL_CONFIRMATION',state:'REVERSAL_CONFIRMED',reason:rv.reason,pattern:rv.pattern,transitionSeq:st.transitionSeq,priceAction:rv};
  }

  // B32.20 — 5s MICRO-TREND CYCLE ENGINE
  // Trades complete short 5-second legs (often ~5–20 candles) that can combine
  // into a larger 1-minute trend. 1m is context only; it does not veto a valid
  // 5s leg. Pocket Option-style fast ZigZag settings are represented as 1/2/2.
  const C7B_MICRO_STATE=Object.create(null);
  function c7bMicroTrendSignal(assetName,fv){
    const src=c7bStrategyRows(assetName), rows=src.rows.slice(-80);
    if(rows.length<24)return {dir:null,state:'WARMUP',reason:'need 24 closed 5s candles'};
    const closes=rows.map(x=>+x.close), cur=rows.at(-1), prev=rows.at(-2);
    const av=Math.max(atr(closes,14)||0,Math.abs(cur.close)*1e-7,1e-12);
    const e5=ema(closes,5), e9=ema(closes,9);
    const zz=v189ZigStructure(closes,1,2,2);
    const oneMin=c7bAgg(rows,60), mClose=oneMin.map(x=>+x.close);
    const mE3=mClose.length>=3?ema(mClose,3):NaN, mE6=mClose.length>=6?ema(mClose,6):NaN;
    const oneMinContext=Number.isFinite(mE3)&&Number.isFinite(mE6)?(mE3>mE6?'BULLISH':mE3<mE6?'BEARISH':'MIXED'):'MIXED';
    const last5=rows.slice(-5), prior=rows.slice(-9,-1);
    const breakUp=cur.close>Math.max(...prior.slice(-4).map(x=>x.high));
    const breakDn=cur.close<Math.min(...prior.slice(-4).map(x=>x.low));
    const net3=(cur.close-rows.at(-4).close)/av;
    const net5=(cur.close-rows.at(-6).close)/av;
    const bullImpulse=cur.close>prev.close && e5>e9 && net3>0.10;
    const bearImpulse=cur.close<prev.close && e5<e9 && net3<-0.10;
    const bullStructure=zz.dir===1 || (e5>e9 && net5>0.30) || breakUp;
    const bearStructure=zz.dir===-1 || (e5<e9 && net5<-0.30) || breakDn;
    const st=C7B_MICRO_STATE[assetName]||(C7B_MICRO_STATE[assetName]={state:'MIXED',legSeq:0,candidate:null,candidateBars:0,lastEntryLeg:null,lastDir:null});
    let next=st.state;
    if(st.state==='UPTREND'){
      if(bearStructure&&bearImpulse){st.candidate=st.candidate==='SELL'?'SELL':'SELL';st.candidateBars=(st.candidate==='SELL'?st.candidateBars:0)+1;if(breakDn||zz.dir===-1||st.candidateBars>=2)next='DOWNTREND';}
      else {st.candidate=null;st.candidateBars=0;}
    }else if(st.state==='DOWNTREND'){
      if(bullStructure&&bullImpulse){st.candidate='BUY';st.candidateBars=(st.candidate==='BUY'?st.candidateBars:0)+1;if(breakUp||zz.dir===1||st.candidateBars>=2)next='UPTREND';}
      else {st.candidate=null;st.candidateBars=0;}
    }else{
      if(bullStructure&&bullImpulse)next='UPTREND'; else if(bearStructure&&bearImpulse)next='DOWNTREND';
    }
    let transition=false;
    if(next!==st.state&&next!=='MIXED'){st.state=next;st.legSeq++;st.candidate=null;st.candidateBars=0;transition=true;}
    const dir=st.state==='UPTREND'&&bullImpulse?'BUY':st.state==='DOWNTREND'&&bearImpulse?'SELL':null;
    const entryKind=transition?'MICRO_TREND_CONFIRMATION':(dir?'MICRO_TREND_CONTINUATION':'MICRO_TREND_HOLD');
    const aligned1m=(dir==='BUY'&&oneMinContext==='BULLISH')||(dir==='SELL'&&oneMinContext==='BEARISH');
    return {dir,state:st.state,entryKind,legSeq:st.legSeq,zigzag:'1/2/2',zigzagStructure:zz.label,oneMinContext,aligned1m,
      ema5:e5,ema9:e9,net3Atr:net3,net5Atr:net5,breakUp,breakDn,bullImpulse,bearImpulse,
      reason:dir?`${st.state} ${dir} · 5s leg #${st.legSeq} · ZigZag 1/2/2 ${zz.label} · 1m ${oneMinContext}${aligned1m?' aligned':' pullback/counter-context'}`:`${st.state} · waiting for 5s leg continuation`};
  }

  function v290BBPlusSignal(assetName,px){
    // B32.21: deterministic three-engine KAOS Strategy authority.
    // Uses the exact same frozen definitions documented in STRATEGY_SPEC_CANDIDATE_7B.md.
    const _c7mod=window.KAOSCandidate7B;
    if(_c7mod){
      const _src=c7bStrategyRows(assetName), _rows=(_src?.rows||[]);
      if(_rows.length>=40){
        const _s=_c7mod.signal(_rows);
        // One signal per completed 5s bar and asset, even across repeated price ticks.
        const _lastClosed=Number(_rows.at(-1)?.closeTs||0);
        const _seen=v290BBPlusSignal._seen||(v290BBPlusSignal._seen=Object.create(null));
        if(_lastClosed<=Number(_seen[assetName]||0))return null;
        _seen[assetName]=_lastClosed;
        if(_s?.conflict){ lastIndicators.v194HoldReason=`C7B conflict · ${_s.reason}`; return null; }
        if(_s?.dir){
          lastIndicators.candidate7B={asset:assetName,threeEngine:true,engine:_s.engine,expiry:_s.expiry,signals:_s.signals||[],historySource:_src.source};
          return {dir:_s.dir,mode:'kaos-exhaustion-snapback',tradeType:'CANDIDATE_7B',str:Math.round((_s.confidence||.6)*100),confidence:_s.confidence||.6,executionExpiry:_s.expiry,
            reason:`KAOS STRATEGY ${_s.engine} ${_s.dir} · ${_s.reason} · ${_s.expiry}s`,reasons:['KAOS_STRATEGY','SR_MARKET_STRUCTURE',_s.engine,`${_s.expiry}S_EXPIRY`],measurement:{setup:`KAOS_SR_${_s.engine}`,engine:_s.engine,executionExpiry:_s.expiry,threeEngine:true,strategyVersion:'SR1.1',aiExecutionAuthority:false}};
        }
        lastIndicators.v194HoldReason='KAOS Strategy · waiting for confirmed structure'; return null;
      }
      // Do not silently execute the legacy micro-trend strategy when S/R warmup is incomplete.
      lastIndicators.v194HoldReason='KAOS Strategy · waiting for closed S/R history';
      return null;
    }
    // B32.20: the live trade clock is the closed 5s micro-trend cycle. KAOS Strategy
    // remains scored on every candle and is logged as agreement/context, but a
    // strong 5s leg no longer has to wait for a long 30s/60s regime to become old.
    const researchedSleeve=C7B_META.sleeves[assetName]||null;
    // B32.20.1: micro-trend trading only needs the already-bootstrapped 5s structure.
    // The frozen KAOS Strategy context model still needs 120 candles, but it is context
    // only and must never hold live micro trading hostage while that history fills.
    const microSrc=c7bStrategyRows(assetName), microRows=microSrc.rows||[];
    if(microRows.length<24)return null;
    const microTs=Number(microRows.at(-1)?.ts||0);
    const seen=v290BBPlusSignal._seen||(v290BBPlusSignal._seen=Object.create(null));
    if(microTs<=(Number(seen[assetName])||0))return null; seen[assetName]=microTs;
    const fv=c7bVector(assetName);
    let p=NaN, vol=NaN, modelDir=null;
    if(fv){
      p=c7bProb(fv.x); vol=fv.vol; c7bResearchCapture(assetName,fv,p,vol,px);
      modelDir=p>=0.61&&vol<=1.00?'BUY':p<=0.42&&vol<=1.10?'SELL':null;
    }
    const micro=c7bMicroTrendSignal(assetName,fv);
    const dir=micro.dir;
    lastIndicators.candidate7B={probUp:Number.isFinite(p)?p:null,probDown:Number.isFinite(p)?1-p:null,vol:Number.isFinite(vol)?vol:null,asset:assetName,sourceTs:(fv?.t??microTs),strategyCandles:microRows.length,historySource:microSrc.source,realArchiveCandles:(marketCandleHistory.byAsset[assetName]||[]).length,expiry:15,universal:true,researchSleeve:!!researchedSleeve,
      marketState:micro.state,entryKind:micro.entryKind,zigzag:'1/2/2',zigzagStructure:micro.zigzagStructure,oneMinContext:micro.oneMinContext,modelDirection:modelDir,microTrend:micro};
    if(!dir){lastIndicators.v194HoldReason=`5s MICRO · ${assetName} · ${micro.reason}`;bumpHoldCount(assetName,'5s MICRO HOLD');return null;}
    const modelAgreement=modelDir===dir;
    const modelOpposes=modelDir&&modelDir!==dir;
    // A frozen 45s model disagreement is context, not a veto, because this strategy
    // deliberately targets a much shorter 15s horizon and short 5s legs.
    const confBase=Math.min(.94,.62+Math.min(.18,Math.abs(micro.net3Atr)*.08)+(micro.aligned1m?.05:0)+(modelAgreement?.05:0));
    return {dir,mode:'micro-5s-cycle-live',tradeType:'MICRO_TREND_CYCLE',str:Math.round(confBase*100),confidence:confBase,executionExpiry:15,
      reason:`${micro.entryKind} ${dir} · ${micro.reason} · 7B ${modelDir||'HOLD'} P(up) ${Number.isFinite(p)?(p*100).toFixed(1)+'%':'n/a'} · LIVE 15s`,
      reasons:['MICRO_TREND_CYCLE','5S_PRIMARY','ZIGZAG_1_2_2',micro.entryKind,micro.aligned1m?'1M_ALIGNED':'1M_COUNTER_CONTEXT',modelAgreement?'7B_AGREES':modelOpposes?'7B_OPPOSES':'7B_HOLD','15S_EXPIRY'],
      measurement:{setup:'C7B_MICRO_TREND_CYCLE',model:'C7B_HGB_45S_CONTEXT',modelTrainingHorizon:45,marketState:micro.state,entryKind:micro.entryKind,microLegSeq:micro.legSeq,zigzag:'1/2/2',zigzagStructure:micro.zigzagStructure,oneMinContext:micro.oneMinContext,oneMinAligned:micro.aligned1m,ema5:micro.ema5,ema9:micro.ema9,net3Atr:micro.net3Atr,net5Atr:micro.net5Atr,breakUp:micro.breakUp,breakDn:micro.breakDn,modelDirection:modelDir,modelAgreement,executionExpiry:15,probUp:Number.isFinite(p)?p:null,probDown:Number.isFinite(p)?1-p:null,vol:Number.isFinite(vol)?vol:null,researchSleeve:!!researchedSleeve,sourceTs:microTs,signalSnapshot:{capturedAt:Date.now(),realRawCount:microRows.length,historySource:microSrc.source}}};
  }

  // V24.1.287-B15.10.13 — CANDIDATE B FORWARD TEST
  // Asymmetric strategy from the raw-candle research pass:
  //   SELL continuation: 60s structure, 10s expiry.
  //   BUY exhaustion/reclaim: 30s structure, 45s expiry.
  // AI remains learning-only. One decision per newly closed source candle.
  function v289CandidateBSignal(assetName, px){
    const a=getAsset(assetName); if(!a)return null;

    // B15.10.21: DO NOT rebuild TF caches on every strategy scan.
    // feedTF() already advances 15s/30s/60s from each newly closed 5s candle.
    // Rebuilding here destroyed live bucket state and re-grouped by array index,
    // which could make Candidate B evaluate malformed/stale higher-TF structure.

    const p60=getTF(a,'60s').prices.map(Number).filter(Number.isFinite);
    const p30=getTF(a,'30s').prices.map(Number).filter(Number.isFinite);
    const p15=getTF(a,'15s').prices.map(Number).filter(Number.isFinite);
    const closed5=Number(a.lastClosed||0);
    if(!closed5)return null;

    const macdState=(arr,fast=5,slow=13,signal=4)=>{
      if(arr.length<slow+signal+4)return null;
      const ef=emaSeries(arr,fast), es=emaSeries(arr,slow), m=[];
      for(let i=0;i<arr.length;i++)m.push(Number.isFinite(ef[i])&&Number.isFinite(es[i])?ef[i]-es[i]:NaN);
      const valid=m.filter(Number.isFinite), sig=emaSeries(valid,signal);
      if(!valid.length||!sig.length)return null;
      const mn=valid[valid.length-1], sn=sig[sig.length-1];
      return Number.isFinite(mn)&&Number.isFinite(sn)?{macd:mn,signal:sn,hist:mn-sn}:null;
    };
    const stoch14=(arr)=>{
      if(arr.length<14)return 50;
      const w=arr.slice(-14), lo=Math.min(...w), hi=Math.max(...w), c=arr[arr.length-1];
      return hi===lo?50:100*(c-lo)/(hi-lo);
    };
    const bbAt=(arr,end,period=20,dev=2)=>{
      const q=arr.slice(end-period,end); if(q.length<period)return null;
      const mid=q.reduce((x,y)=>x+y,0)/period;
      const sd=Math.sqrt(q.reduce((z,v)=>z+(v-mid)*(v-mid),0)/period);
      return {lo:mid-dev*sd,mid,hi:mid+dev*sd};
    };

    // SELL continuation engine — all five directional components agree.
    if(p60.length>=55){
      const e21=ema(p60,21), e50=ema(p60,50), m=macdState(p60,5,13,4);
      const c=p60[p60.length-1], mom3=c-p60[p60.length-4], bb=bbAt(p60,p60.length,20,2), st=stoch14(p60);
      const sell=!!m&&!!bb&&e21<e50&&m.hist<0&&mom3<0&&c<bb.mid&&st<50;
      const sourceSeq=p60.length;
      if(sell){
        if(!v289CandidateBSignal._seenSell)v289CandidateBSignal._seenSell=Object.create(null);
        if(sourceSeq>(Number(v289CandidateBSignal._seenSell[assetName])||0)){
          v289CandidateBSignal._seenSell[assetName]=sourceSeq;
          return {dir:'SELL',mode:'candidate-b-sell-continuation',tradeType:'CANDIDATE_B_SELL',str:82,confidence:.82,executionExpiry:10,
            reason:`Candidate B SELL · 60s EMA21<50 · MACD5/13/4 hist<0 · MOM3<0 · below BB20 mid · STOCH14<50 · LIVE 10s`,
            reasons:['CANDIDATE_B','SELL_CONTINUATION','EMA21_50_60S','MACD_5_13_4_60S','MOM3_60S','BB20_MID_60S','STOCH14_60S'],
            measurement:{setup:'CANDIDATE_B_SELL',model:'CANDIDATE_B_ASYMMETRIC',executionExpiry:10,ema21:e21,ema50:e50,macdHist:m.hist,mom3,bbMid:bb.mid,stoch14:st}};
        }
      }
    }


    // BUY continuation / runner engine — fills Candidate B's bullish-trend gap.
    // 60s establishes the trend; 15s waits for a pause -> re-acceleration so
    // the bot does not blindly BUY every candle during an extended move.
    if(p60.length>=55 && p15.length>=24){
      const e21=ema(p60,21), e50=ema(p60,50), m60=macdState(p60,5,13,4);
      const c60=p60[p60.length-1], mom3=c60-p60[p60.length-4], bb60=bbAt(p60,p60.length,20,2), st60=stoch14(p60);

      const e9Now=ema(p15,9), e9Prev=ema(p15.slice(0,-1),9);
      const m15=macdState(p15,5,13,4);
      const m15Prev=macdState(p15.slice(0,-1),5,13,4);
      const n15=p15.length, c15=p15[n15-1], prev15=p15[n15-2], prev2_15=p15[n15-3];

      const establishedBull=!!m60&&!!bb60&&e21>e50&&m60.hist>0&&mom3>0&&c60>bb60.mid&&st60>50;
      const pauseThenGo=prev15<=prev2_15 && c15>prev15;
      const fastReclaim=prev15<=e9Prev && c15>e9Now;
      const fastMomentum=!!m15&&!!m15Prev&&m15.hist>0&&m15.hist>m15Prev.hist;

      // Lane A: original pullback/reclaim continuation.
      const pullbackRunner=establishedBull&&pauseThenGo&&fastReclaim&&fastMomentum;

      // Lane B: momentum continuation for clean bull runs that never pull back
      // far enough to satisfy Lane A.  Require price above the fast EMA,
      // consecutive rising 15s closes and strengthening positive MACD.
      const momentumRunner=establishedBull&&c15>e9Now&&c15>prev15&&prev15>prev2_15&&fastMomentum;
      const runner=pullbackRunner||momentumRunner;
      const runnerLane=pullbackRunner?'PULLBACK_RECLAIM':'MOMENTUM_CONTINUATION';

      const sourceSeq=p15.length;
      if(runner){
        if(!v289CandidateBSignal._seenRunner)v289CandidateBSignal._seenRunner=Object.create(null);
        if(sourceSeq>(Number(v289CandidateBSignal._seenRunner[assetName])||0)){
          v289CandidateBSignal._seenRunner[assetName]=sourceSeq;
          return {dir:'BUY',mode:'candidate-b-buy-continuation-runner',tradeType:'CANDIDATE_B_BUY_RUNNER',str:80,confidence:.80,executionExpiry:30,
            reason:`Candidate B BUY RUNNER · ${runnerLane} · established 60s bull trend · 15s confirmation · LIVE 30s`,
            reasons:['CANDIDATE_B','BUY_CONTINUATION_RUNNER',runnerLane,'EMA21_50_60S','MACD_5_13_4_60S','MOM3_60S','BB20_MID_60S','STOCH14_60S','15S_MACD_REACCELERATION'],
            measurement:{setup:'CANDIDATE_B_BUY_RUNNER',runnerLane,model:'CANDIDATE_B_ASYMMETRIC_PLUS_DUAL_RUNNER',executionExpiry:30,ema21:e21,ema50:e50,macdHist60:m60.hist,mom3,bbMid60:bb60.mid,stoch14:st60,ema9_15:e9Now,macdHist15:m15.hist,macdHist15Prev:m15Prev.hist}};
        }
      }
    }

    // BUY reversal engine — exact research rule.
    // 30s OHLC signal / 45s expiry.
    if(p30.length>=30){
      const tf30=getTF(a,'30s');
      const rateKeys=Object.keys(tf30.rates||{}).map(Number).filter(Number.isFinite).sort((x,y)=>x-y);
      const candles30=rateKeys.slice(-p30.length).map(k=>tf30.rates[k]).filter(c=>Array.isArray(c)&&c.length>=4);

      if(candles30.length>=30){
        const n=p30.length, c=p30[n-1];
        const cur=candles30[candles30.length-1];
        const prevC=candles30[candles30.length-2];
        const bbNow=bbAt(p30,n,20,2);

        const rNow=rsi(p30,14);
        const rPrev=rsi(p30.slice(0,-1),14);
        const r2=rsi(p30.slice(0,-2),14);

        const mNow=macdState(p30,5,13,4);
        const mPrev=macdState(p30.slice(0,-1),5,13,4);

        let lowerTouched=false;
        for(let back=0; back<3; back++){
          const endN=n-back;
          const bb=bbAt(p30,endN,20,2);
          const candle=candles30[candles30.length-1-back];
          if(bb && candle && Number(candle[2])<=bb.lo){
            lowerTouched=true;
            break;
          }
        }

        const closeBackAbove=!!bbNow && c>bbNow.lo;
        const recentOversold=Math.min(rNow,rPrev,r2)<30;
        const rsiRising=rNow>rPrev;
        const bullishCandle=Number(cur[3])>Number(cur[0]);
        const osmaRising=!!mNow && !!mPrev && mNow.hist>mPrev.hist;
        const breaksPrevHigh=Number(cur[3])>Number(prevC[1]);

        const buy=lowerTouched && closeBackAbove && recentOversold &&
                  rsiRising && bullishCandle && osmaRising && breaksPrevHigh;

        const sourceSeq=p30.length;
        if(buy){
          if(!v289CandidateBSignal._seenBuy)v289CandidateBSignal._seenBuy=Object.create(null);
          if(sourceSeq>(Number(v289CandidateBSignal._seenBuy[assetName])||0)){
            v289CandidateBSignal._seenBuy[assetName]=sourceSeq;
            return {
              dir:'BUY',
              mode:'candidate-b-buy-reversal',
              tradeType:'CANDIDATE_B_BUY',
              str:84,
              confidence:.84,
              executionExpiry:45,
              reason:`Candidate B BUY REVERSAL · exact 30s OHLC rule · LIVE 45s`,
              reasons:[
                'CANDIDATE_B','BUY_REVERSAL_EXACT',
                'BB20_LOWER_TOUCH_RECLAIM_30S',
                'RSI14_LT30_RISING_30S',
                'BULLISH_CANDLE_30S',
                'OSMA_5_13_4_RISING_30S',
                'BREAK_PREV_HIGH_30S'
              ],
              measurement:{
                setup:'CANDIDATE_B_BUY',
                model:'CANDIDATE_B_BEST3_MIXED_TF',
                executionExpiry:45,
                rsi14:rNow,rsiPrev:rPrev,
                bbLower:bbNow?.lo,
                osma:mNow?.hist,osmaPrev:mPrev?.hist,
                prevHigh:Number(prevC[1]),
                close:Number(cur[3])
              }
            };
          }
        }
      }
    }
    return null;
  }

  function v283Simple30Signal(assetName, px) {
    const asset=getAsset(assetName);
    if(!asset) return null;
    const frames={};
    for(const tf of ['5s','15s','30s','60s']) frames[tf]=v198FrameScore(assetName,tf);
    const f5=frames['5s'], f15=frames['15s'], f30=frames['30s'], f60=frames['60s'];
    const reject=(reason,extra={})=>{
      lastIndicators.v194HoldReason=`V283 SIMPLE · ${reason}`;
      lastIndicators.threeStep={version:'V283_SIMPLE_30S',state:'HOLD',reason:lastIndicators.v194HoldReason,plan:{fast:'15s',primary:'30s',higher:'60s'},frames,...extra,ts:Date.now()};
      return null;
    };
    if(!f15?.ready||!f30?.ready||!f60?.ready||(f15.n||0)<8||(f30.n||0)<8||(f60.n||0)<8)
      return reject(`warmup · 15s ${f15?.n||0}/8 · 30s ${f30?.n||0}/8 · 60s ${f60?.n||0}/8`);

    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const t30=Number(f30.trend||0), m30=Number(f30.momentum||0);
    const m15=Number(f15.momentum||0), t60=Number(f60.trend||0), m5=Number(f5?.momentum||0);
    // Weighted signed evidence. Positive=BUY, negative=SELL. The 30s horizon
    // carries 60% of the vote; fast timing 25%; 60s context only 15%.
    let edge=t30*0.35 + m30*0.25 + m15*0.20 + t60*0.15 + m5*0.05;

    // Small direct price-action vote from the last three CLOSED 30s moves.
    const p30=v181Series(assetName,'30s');
    if(Array.isArray(p30)&&p30.length>=5){
      let pa=0;
      for(let i=p30.length-3;i<p30.length;i++) pa += Math.sign(Number(p30[i])-Number(p30[i-1]));
      edge += pa*2.0; // max ±6; cannot dominate indicators
    }

    const absEdge=Math.abs(edge);
    const minEdge=12; // intentionally participatory; still rejects genuinely ambiguous reads
    if(absEdge<minEdge) return reject(`unclear direction · edge ${edge.toFixed(1)} needs ±${minEdge}`,{edge});
    const dir=edge>0?'BUY':'SELL', side=dir==='BUY'?1:-1;

    // Only one market-quality veto: don't chase a very stretched 30s impulse
    // when the 15s timing frame has already turned against it.
    const ext=Number(f30.signedExtension||0)*side;
    const fastAligned=m15*side;
    if(ext>2.20 && fastAligned<0)
      return reject(`exhausted ${dir} · 30s extension ${ext.toFixed(2)} ATR + 15s momentum ${fastAligned.toFixed(1)}`,{edge,dir,sideExtension:ext,fastAligned});

    // If 60s strongly disagrees, demand a stronger 30s/15s edge rather than
    // vetoing the trade outright. This keeps reversals possible.
    const higherAligned=t60*side;
    if(higherAligned<-35 && absEdge<24)
      return reject(`weak reversal · edge ${absEdge.toFixed(1)} <24 while 60s opposes ${higherAligned.toFixed(1)}`,{edge,dir,higherAligned});

    const score=clamp(Math.round(50+absEdge*0.82),60,92);
    const scoreBreakdown={edge:Number(edge.toFixed(2)),trend30:Number((t30*0.35).toFixed(2)),momentum30:Number((m30*0.25).toFixed(2)),momentum15:Number((m15*0.20).toFixed(2)),trend60:Number((t60*0.15).toFixed(2)),momentum5:Number((m5*0.05).toFixed(2))};
    lastIndicators.v194HoldReason='';
    lastIndicators.threeStep={version:'V283_SIMPLE_30S',state:'READY',dir,reason:`V283 SIMPLE ${dir} · EDGE ${edge.toFixed(1)} · SCORE ${score}`,plan:{fast:'15s',primary:'30s',higher:'60s'},frames,
      trendQuality:clamp(Math.round(50+t30*side*0.5),0,100),momentumQuality:clamp(Math.round(50+(m30*0.65+m15*0.35)*side*0.5),0,100),volatilityQuality:Number(f30.volatility||0),
      finalThreeStepScore:score,scoreBreakdown,pTrend:t30,hTrend:t60,fastAligned:m15*side,primaryAligned:m30*side,structuralSigned:edge,structuralAgreement:((t30*side>0)?0.7:0)+((t60*side>=0)?0.3:0),adaptiveFloor:60,ts:Date.now()};
    return {dir,mode:'v283-simple-30s',tradeType:'V283_SIMPLE_30S',str:score,confidence:score/100,
      reason:`V283 SIMPLE ${dir} · EDGE ${edge.toFixed(1)} · SCORE ${score}/100 · 30s trend ${t30.toFixed(1)} · 30s mom ${m30.toFixed(1)} · 15s mom ${m15.toFixed(1)} · 60s trend ${t60.toFixed(1)}`,
      reasons:['V283_SIMPLE_30S','30s direction','15s timing','60s context','single weighted edge','AI learning only'],
      measurement:{setup:'V283_SIMPLE_30S',marketClass:'SIMPLE_DIRECTIONAL',executionExpiry:30,finalThreeStepScore:score,scoreBreakdown,frames,timeframePlan:{fast:'15s',primary:'30s',higher:'60s'},
        structuralSigned:edge,pTrend:t30,hTrend:t60,fastMomentum:m15*side,primaryMomentum:m30*side,higherAligned,sideExtension:ext,adaptiveFloor:60,predictiveAI:{authority:false}}};
  }


  // B32.9 — USER-EDITABLE DETERMINISTIC STRATEGY ENGINE
  // Completely separate from frozen KAOS Strategy. AI remains learning-only.
  function sbEma(vals,p){p=Math.max(2,Math.round(p||2));if(!vals.length)return[];const a=2/(p+1),o=[vals[0]];for(let i=1;i<vals.length;i++)o.push(a*vals[i]+(1-a)*o[i-1]);return o;}
  function sbAtr(rows,p=14){if(rows.length<2)return[];const tr=rows.map((r,i)=>i?Math.max(r.high-r.low,Math.abs(r.high-rows[i-1].close),Math.abs(r.low-rows[i-1].close)):r.high-r.low);const a=1/Math.max(2,p),out=[tr[0]];for(let i=1;i<tr.length;i++)out.push(a*tr[i]+(1-a)*out[i-1]);return out;}
  function sbRsi(vals,p=14){if(vals.length<2)return 50;let g=0,l=0,a=1/Math.max(2,p);for(let i=1;i<vals.length;i++){const d=vals[i]-vals[i-1],up=Math.max(0,d),dn=Math.max(0,-d);if(i===1){g=up;l=dn}else{g=a*up+(1-a)*g;l=a*dn+(1-a)*l}}return l<=1e-12?100:100-100/(1+g/l)}
  function sbStoch(rows,p=14){const w=rows.slice(-Math.max(2,p));if(!w.length)return 50;const hi=Math.max(...w.map(r=>r.high)),lo=Math.min(...w.map(r=>r.low)),c=w[w.length-1].close;return hi===lo?50:100*(c-lo)/(hi-lo)}
  function sbAdx(rows,p=14){if(rows.length<p+3)return{adx:0,plus:50,minus:50};let trs=[],plus=[],minus=[];for(let i=1;i<rows.length;i++){const r=rows[i],q=rows[i-1],up=r.high-q.high,dn=q.low-r.low;trs.push(Math.max(r.high-r.low,Math.abs(r.high-q.close),Math.abs(r.low-q.close)));plus.push(up>dn&&up>0?up:0);minus.push(dn>up&&dn>0?dn:0)}const n=Math.min(p,trs.length),sum=a=>a.slice(-n).reduce((x,y)=>x+y,0),tr=sum(trs)||1e-12,pdi=100*sum(plus)/tr,mdi=100*sum(minus)/tr;let dx=[];for(let end=Math.max(p,1);end<=trs.length;end++){const t=trs.slice(end-p,end).reduce((a,b)=>a+b,0)||1e-12,pp=100*plus.slice(end-p,end).reduce((a,b)=>a+b,0)/t,mm=100*minus.slice(end-p,end).reduce((a,b)=>a+b,0)/t;dx.push(100*Math.abs(pp-mm)/(pp+mm||1))}return{adx:dx.slice(-p).reduce((a,b)=>a+b,0)/Math.max(1,Math.min(p,dx.length)),plus:pdi,minus:mdi}}
  function sbSupertrend(rows,p=10,mult=3){if(rows.length<p+3)return 0;const atr=sbAtr(rows,p);let upper=0,lower=0,trend=1;for(let i=0;i<rows.length;i++){const mid=(rows[i].high+rows[i].low)/2,bu=mid+mult*(atr[i]||0),bl=mid-mult*(atr[i]||0);if(i===0){upper=bu;lower=bl;continue}upper=(bu<upper||rows[i-1].close>upper)?bu:upper;lower=(bl>lower||rows[i-1].close<lower)?bl:lower;if(trend>0&&rows[i].close<lower)trend=-1;else if(trend<0&&rows[i].close>upper)trend=1}return trend}
  function sbSar(rows,step=.02,max=.2){if(rows.length<4)return 0;let bull=rows[1].close>=rows[0].close,sar=bull?rows[0].low:rows[0].high,ep=bull?rows[0].high:rows[0].low,af=step;for(let i=1;i<rows.length;i++){sar=sar+af*(ep-sar);const r=rows[i];if(bull){sar=Math.min(sar,rows[i-1].low,i>1?rows[i-2].low:rows[i-1].low);if(r.low<sar){bull=false;sar=ep;ep=r.low;af=step}else if(r.high>ep){ep=r.high;af=Math.min(max,af+step)}}else{sar=Math.max(sar,rows[i-1].high,i>1?rows[i-2].high:rows[i-1].high);if(r.high>sar){bull=true;sar=ep;ep=r.high;af=step}else if(r.low<ep){ep=r.low;af=Math.min(max,af+step)}}}return bull?1:-1}
  function strategySlotForAsset(assetName){
    const slots=(Array.isArray(botConfig?.strategySlots)?botConfig.strategySlots:[]).slice(0,kaosChartLimit);
    return slots.find(x=>x&&x.asset===assetName)||null;
  }
  function kaosBuiltinSignal(rows,cfg){
    if(!rows||rows.length<35)return null;const c=rows.at(-1),p=rows.at(-2),p2=rows.at(-3),cl=rows.map(r=>+r.close),engine=String(cfg.engine||'');
    const e9=sbEma(cl,9).at(-1),e21=sbEma(cl,21).at(-1),e9p=sbEma(cl.slice(0,-1),9).at(-1),e21p=sbEma(cl.slice(0,-1),21).at(-1),rsi=sbRsi(cl,14),atr=sbAtr(rows,14).at(-1)||1e-12;
    const body=Math.abs(c.close-c.open),range=Math.max(c.high-c.low,1e-12),bodyFrac=body/range,green=c.close>c.open,red=c.close<c.open;
    const hi20=Math.max(...rows.slice(-21,-1).map(x=>x.high)),lo20=Math.min(...rows.slice(-21,-1).map(x=>x.low));
    const out=(dir,reason,confidence=.68)=>({dir,engine,expiry:Number(cfg.expiry)||15,confidence,reason,signals:[{dir,engine,reason}]});
    if(engine==='FALSE_BREAKOUT'){
      if(c.high>hi20&&c.close<hi20&&red&&bodyFrac>.35)return out('SELL','failed break above 20-bar resistance · closed back below level',.72);
      if(c.low<lo20&&c.close>lo20&&green&&bodyFrac>.35)return out('BUY','failed break below 20-bar support · closed back above level',.72);
    }
    if(engine==='TREND_FOLLOWING'){
      const slope=(e9-e9p)/atr;if(e9>e21&&slope>.05&&green&&c.close>p.high)return out('BUY','EMA 9/21 uptrend · positive slope · bullish continuation break');
      if(e9<e21&&slope<-.05&&red&&c.close<p.low)return out('SELL','EMA 9/21 downtrend · negative slope · bearish continuation break');
    }
    if(engine==='TREND_REVERSAL'){
      const downMove=(rows.at(-2).close-rows.at(-8).close)/atr,upMove=(rows.at(-2).close-rows.at(-8).close)/atr;
      if(downMove<-1.8&&rsi<38&&green&&c.close>p.high&&bodyFrac>.45)return out('BUY','extended downswing · RSI low · bullish reversal confirmation',.71);
      if(upMove>1.8&&rsi>62&&red&&c.close<p.low&&bodyFrac>.45)return out('SELL','extended upswing · RSI high · bearish reversal confirmation',.71);
    }
    if(engine==='CANDLESTICK_PATTERN'){
      const bullEng=green&&p.close<p.open&&c.open<=p.close&&c.close>=p.open,bearEng=red&&p.close>p.open&&c.open>=p.close&&c.close<=p.open;
      const lower=(Math.min(c.open,c.close)-c.low)/range,upper=(c.high-Math.max(c.open,c.close))/range;
      if(bullEng||(green&&lower>.55&&bodyFrac>.2))return out('BUY',bullEng?'bullish engulfing pattern':'bullish rejection / hammer pattern',.67);
      if(bearEng||(red&&upper>.55&&bodyFrac>.2))return out('SELL',bearEng?'bearish engulfing pattern':'bearish rejection / shooting-star pattern',.67);
    }
    if(engine==='MA_CROSSOVER'){
      if(e9p<=e21p&&e9>e21&&green)return out('BUY','EMA 9 crossed above EMA 21 with bullish close',.66);
      if(e9p>=e21p&&e9<e21&&red)return out('SELL','EMA 9 crossed below EMA 21 with bearish close',.66);
    }
    if(engine==='PRICE_ACTION'){
      const hi5=Math.max(...rows.slice(-6,-1).map(x=>x.high)),lo5=Math.min(...rows.slice(-6,-1).map(x=>x.low));
      if(green&&bodyFrac>.5&&c.close>hi5&&p.close>p2.close)return out('BUY','higher-price structure · strong bullish candle · 5-bar swing break',.69);
      if(red&&bodyFrac>.5&&c.close<lo5&&p.close<p2.close)return out('SELL','lower-price structure · strong bearish candle · 5-bar swing break',.69);
    }
    if(engine==='INDICATOR_BASED'){
      const mf=sbEma(cl,12),ms=sbEma(cl,26),macd=mf.at(-1)-ms.at(-1),macdPrev=mf.at(-2)-ms.at(-2);let buy=0,sell=0;
      if(e9>e21)buy++;else if(e9<e21)sell++;if(rsi>52&&rsi<72)buy++;else if(rsi<48&&rsi>28)sell++;if(macd>macdPrev)buy++;else if(macd<macdPrev)sell++;if(green)buy++;else if(red)sell++;
      if(buy>=3&&buy>sell)return out('BUY',`multi-indicator confirmation ${buy} BUY / ${sell} SELL`,.65+buy*.02);if(sell>=3&&sell>buy)return out('SELL',`multi-indicator confirmation ${sell} SELL / ${buy} BUY`,.65+sell*.02);
    }
    if(engine==='FIBONACCI'){
      const w=rows.slice(-31,-1),hi=Math.max(...w.map(x=>x.high)),lo=Math.min(...w.map(x=>x.low)),span=hi-lo;if(span>0){const f382=hi-span*.382,f50=hi-span*.5,f618=hi-span*.618,tol=Math.max(atr*.18,span*.015),near=x=>Math.min(Math.abs(c.close-f382),Math.abs(c.close-f50),Math.abs(c.close-f618))<=tol;
        const trend=w.at(-1).close>w[0].close?1:-1;if(near()&&trend>0&&green&&c.close>p.high)return out('BUY','bull trend · Fibonacci retracement zone · bullish confirmation',.68);if(near()&&trend<0&&red&&c.close<p.low)return out('SELL','bear trend · Fibonacci retracement zone · bearish confirmation',.68);}
    }
    return null;
  }
  function customStrategySignal(assetName,px,forcedCfg=null){
    const cfg=forcedCfg||botConfig?.strategyProfile;if(!cfg)return null;
    const src=c7bStrategyRows(assetName),base=src.rows||[],tf=Math.max(5,Number(cfg.signalTf)||30),rows=(tf===5?base:c7bAgg(base,tf));if(rows.length<120/tf*5+35)return null;
    if(cfg.engine&&cfg.engine!=='CUSTOM_CONFIRM'){
      const last=rows.at(-1),seen=customStrategySignal._seen||(customStrategySignal._seen=Object.create(null)),sk=assetName+'|'+cfg.id;if(+last.ts<=(seen[sk]||0))return null;seen[sk]=+last.ts;
      const b=kaosBuiltinSignal(rows,cfg);lastIndicators.customStrategy={profileId:cfg.id,profileName:cfg.name,engine:cfg.engine,builtin:true,signal:b?.dir||null,expiry:Number(cfg.expiry)||15};return b;
    }
    const last=rows[rows.length-1],seen=customStrategySignal._seen||(customStrategySignal._seen=Object.create(null));const sk=assetName+'|'+cfg.id;if(+last.ts<=(seen[sk]||0))return null;seen[sk]=+last.ts;
    const c=rows.map(r=>+r.close),votes=[],details={},add=(name,side,val)=>{if(side){votes.push({name,side,val});details[name]={side,val}}};
    const ep=(cfg.ema?.periods||[9,20,50,100]).map(x=>Math.max(2,+x||2)), em=ep.map(p=>sbEma(c,p).at(-1));if(cfg.ema?.enabled)add('EMA',em[0]>em[1]&&em[1]>em[2]?1:em[0]<em[1]&&em[1]<em[2]?-1:0,{periods:ep,values:em});
    const rsi=sbRsi(c,+cfg.rsi?.period||14);if(cfg.rsi?.enabled)add('RSI',rsi<=+cfg.rsi.low?1:rsi>=+cfg.rsi.high?-1:0,rsi);
    const mf=sbEma(c,+cfg.macd?.fast||12),ms=sbEma(c,+cfg.macd?.slow||26),ml=mf.map((v,i)=>v-(ms[i]??v)),sg=sbEma(ml,+cfg.macd?.signal||9),macd=ml.at(-1),macsig=sg.at(-1);if(cfg.macd?.enabled)add('MACD',macd>macsig?1:macd<macsig?-1:0,{macd,signal:macsig});
    const bp=Math.max(2,+cfg.bb?.period||20),bw=c.slice(-bp),mean=bw.reduce((a,b)=>a+b,0)/bw.length,sd=Math.sqrt(bw.reduce((a,b)=>a+(b-mean)**2,0)/bw.length),dev=+cfg.bb?.deviation||2,upper=mean+dev*sd,lower=mean-dev*sd;if(cfg.bb?.enabled)add('BOLLINGER',last.close<=lower?1:last.close>=upper?-1:0,{upper,mean,lower});
    const stoch=sbStoch(rows,+cfg.stoch?.period||14);if(cfg.stoch?.enabled)add('STOCH',stoch<=+cfg.stoch.low?1:stoch>=+cfg.stoch.high?-1:0,stoch);
    const adx=sbAdx(rows,+cfg.adx?.period||14);if(cfg.adx?.enabled&&adx.adx>=+cfg.adx.min)add('ADX',adx.plus>adx.minus?1:-1,adx);else details.ADX=adx;
    const rp=Math.max(1,+cfg.roc?.period||7),roc=c.length>rp&&c.at(-(rp+1))?100*(c.at(-1)/c.at(-(rp+1))-1):0;if(cfg.roc?.enabled){const rt=Math.abs(+cfg.roc.threshold||0);add('ROC',roc>rt?1:roc<-rt?-1:0,roc)}
    const atrs=sbAtr(rows,+cfg.atr?.period||14),atr=atrs.at(-1)||0,atrAvg=atrs.slice(-40).reduce((a,b)=>a+b,0)/Math.max(1,atrs.slice(-40).length),atrNorm=atrAvg?atr/atrAvg:1;details.ATR={atr,norm:atrNorm};if(cfg.atr?.enabled&&atrNorm>+cfg.atr.maxNorm){lastIndicators.cleanCore={marketClass:'CUSTOM_ATR_GATE',setup:'NONE',reason:`CUSTOM HOLD · ATR norm ${atrNorm.toFixed(2)} > ${(+cfg.atr.maxNorm).toFixed(2)}`};return null}
    const sup=sbSupertrend(rows,+cfg.supertrend?.period||10,+cfg.supertrend?.multiplier||3);if(cfg.supertrend?.enabled)add('SUPERTREND',sup,sup>0?'BULL':'BEAR');
    const sar=sbSar(rows,+cfg.sar?.step||.02,+cfg.sar?.max||.2);if(cfg.sar?.enabled)add('SAR',sar,sar>0?'BULL':'BEAR');
    const buys=votes.filter(v=>v.side>0).length,sells=votes.filter(v=>v.side<0).length,min=Math.max(1,+cfg.minConfirmations||3);let dir=null;if(buys>=min&&buys>sells)dir='BUY';else if(sells>=min&&sells>buys)dir='SELL';
    lastIndicators.customStrategy={profileId:cfg.id,profileName:cfg.name,signalTf:tf,expiry:+cfg.expiry||45,buys,sells,min,votes,details,historySource:src.source};
    if(!dir)return null;const score=Math.min(99,50+Math.max(buys,sells)*7);return{dir,mode:'custom-confirm-live',tradeType:'CUSTOM_STRATEGY',str:score,confidence:score/100,executionExpiry:Math.max(5,+cfg.expiry||45),reason:`CUSTOM ${dir} · ${cfg.name} · ${buys} BUY / ${sells} SELL votes · need ${min}`,reasons:votes.filter(v=>v.side===(dir==='BUY'?1:-1)).map(v=>v.name),measurement:{setup:'CUSTOM_STRATEGY',model:'USER_STRATEGY_BUILDER',profileId:cfg.id,profileName:cfg.name,profileVersion:1,profileSnapshot:JSON.parse(JSON.stringify(cfg)),signalTf:tf,executionExpiry:Math.max(5,+cfg.expiry||45),buyVotes:buys,sellVotes:sells,minConfirmations:min,indicatorDetails:details,signalSnapshot:{capturedAt:Date.now(),profileId:cfg.id,profileName:cfg.name,settings:JSON.parse(JSON.stringify(cfg))}}};
  }

  // B32.11 — strategy-lab backtester. Uses the same indicator formulas and vote semantics as CUSTOM_STRATEGY.
  function sbBacktestProfile(assetName,cfg){
    const src=c7bStrategyRows(assetName),base=src.rows||[],tf=Math.max(5,Number(cfg.signalTf)||30),rows=(tf===5?base:c7bAgg(base,tf));
    const warm=Math.max(110,Math.max(...(cfg.ema?.periods||[9,20,50,100]),+cfg.macd?.slow||26,+cfg.bb?.period||20,+cfg.stoch?.period||14,+cfg.adx?.period||14,+cfg.atr?.period||14)+15);
    const expiry=Math.max(5,+cfg.expiry||45),min=Math.max(1,+cfg.minConfirmations||3),trades=[];let lockUntil=0;
    const evalAt=(rr)=>{const last=rr.at(-1),c=rr.map(r=>+r.close),votes=[],add=(side)=>{if(side)votes.push(side)};
      const ep=(cfg.ema?.periods||[9,20,50,100]).map(x=>Math.max(2,+x||2)),em=ep.map(p=>sbEma(c,p).at(-1));if(cfg.ema?.enabled)add(em[0]>em[1]&&em[1]>em[2]?1:em[0]<em[1]&&em[1]<em[2]?-1:0);
      const rsi=sbRsi(c,+cfg.rsi?.period||14);if(cfg.rsi?.enabled)add(rsi<=+cfg.rsi.low?1:rsi>=+cfg.rsi.high?-1:0);
      const mf=sbEma(c,+cfg.macd?.fast||12),ms=sbEma(c,+cfg.macd?.slow||26),ml=mf.map((v,i)=>v-(ms[i]??v)),sg=sbEma(ml,+cfg.macd?.signal||9),macd=ml.at(-1),macsig=sg.at(-1);if(cfg.macd?.enabled)add(macd>macsig?1:macd<macsig?-1:0);
      const bp=Math.max(2,+cfg.bb?.period||20),bw=c.slice(-bp),mean=bw.reduce((a,b)=>a+b,0)/bw.length,sd=Math.sqrt(bw.reduce((a,b)=>a+(b-mean)**2,0)/bw.length),dev=+cfg.bb?.deviation||2,upper=mean+dev*sd,lower=mean-dev*sd;if(cfg.bb?.enabled)add(last.close<=lower?1:last.close>=upper?-1:0);
      const stoch=sbStoch(rr,+cfg.stoch?.period||14);if(cfg.stoch?.enabled)add(stoch<=+cfg.stoch.low?1:stoch>=+cfg.stoch.high?-1:0);
      const adx=sbAdx(rr,+cfg.adx?.period||14);if(cfg.adx?.enabled&&adx.adx>=+cfg.adx.min)add(adx.plus>adx.minus?1:-1);
      const rp=Math.max(1,+cfg.roc?.period||7),roc=c.length>rp&&c.at(-(rp+1))?100*(c.at(-1)/c.at(-(rp+1))-1):0;if(cfg.roc?.enabled){const rt=Math.abs(+cfg.roc.threshold||0);add(roc>rt?1:roc<-rt?-1:0)}
      const atrs=sbAtr(rr,+cfg.atr?.period||14),atr=atrs.at(-1)||0,aw=atrs.slice(-40),atrAvg=aw.reduce((a,b)=>a+b,0)/Math.max(1,aw.length),atrNorm=atrAvg?atr/atrAvg:1;if(cfg.atr?.enabled&&atrNorm>+cfg.atr.maxNorm)return null;
      if(cfg.supertrend?.enabled)add(sbSupertrend(rr,+cfg.supertrend?.period||10,+cfg.supertrend?.multiplier||3));if(cfg.sar?.enabled)add(sbSar(rr,+cfg.sar?.step||.02,+cfg.sar?.max||.2));
      const buys=votes.filter(x=>x>0).length,sells=votes.filter(x=>x<0).length;return buys>=min&&buys>sells?'BUY':sells>=min&&sells>buys?'SELL':null;};
    for(let i=warm;i<rows.length-1;i++){const r=rows[i];if(+r.ts<lockUntil)continue;const dir=evalAt(rows.slice(0,i+1));if(!dir)continue;const targetTs=+r.ts+expiry*1000;let j=i+1;while(j<rows.length&&+rows[j].ts<targetTs)j++;if(j>=rows.length)break;const entry=+r.close,exit=+rows[j].close,res=exit===entry?'TIE':((dir==='BUY'&&exit>entry)||(dir==='SELL'&&exit<entry))?'WIN':'LOSS';trades.push({ts:+r.ts,dir,entry,exit,result:res});lockUntil=targetTs;}
    let w=0,l=0,t=0,ls=0,maxLs=0;for(const q of trades){if(q.result==='WIN'){w++;ls=0}else if(q.result==='LOSS'){l++;ls++;maxLs=Math.max(maxLs,ls)}else t++;}const hours=rows.length>1?(+rows.at(-1).ts-+rows[0].ts)/36e5:0;return{asset:assetName,source:src.source,trades:trades.length,wins:w,losses:l,ties:t,winRate:w+l?w/(w+l):null,maxLossStreak:maxLs,tradesPerHour:hours?trades.length/hours:0,hours};
  }


  // B32.26 — unified backtest for built-in KAOS engines and custom Strategy Builder profiles.
  // Signals are evaluated only from candles closed at that historical moment. Entry is the
  // next available real 5s candle open; settlement is the first real 5s close at/after expiry.
  function sbBacktestAny(assetName,cfg){
    if(!cfg||!cfg.engine)throw new Error('Strategy profile required');
    if(cfg.engine==='CUSTOM_CONFIRM')return sbBacktestProfile(assetName,cfg);
    const src=c7bStrategyRows(assetName),base=(src.rows||[]).filter(r=>Number.isFinite(+r.ts)).sort((a,b)=>+a.ts-+b.ts),tf=Math.max(5,Number(cfg.signalTf)||5),sigRows=(tf===5?base:c7bAgg(base,tf));
    const expiry=Math.max(5,Number(cfg.expiry)||15),trades=[];let lockUntil=0;
    for(let i=35;i<sigRows.length;i++){
      const signalBar=sigRows[i],signalTs=+signalBar.ts;if(signalTs<lockUntil)continue;
      const sig=kaosBuiltinSignal(sigRows.slice(0,i+1),cfg);if(!sig?.dir)continue;
      let ei=0;while(ei<base.length&&+base[ei].ts<=signalTs)ei++;if(ei>=base.length)break;
      const entryBar=base[ei],entryTs=+entryBar.ts,entry=+entryBar.open,targetTs=entryTs+expiry*1000;let xi=ei;while(xi<base.length&&+base[xi].ts<targetTs)xi++;if(xi>=base.length)break;
      const exit=+base[xi].close,res=exit===entry?'TIE':((sig.dir==='BUY'&&exit>entry)||(sig.dir==='SELL'&&exit<entry))?'WIN':'LOSS';trades.push({ts:entryTs,signalTs,dir:sig.dir,entry,exit,result:res});lockUntil=targetTs;
    }
    let w=0,l=0,t=0,ls=0,maxLs=0;for(const q of trades){if(q.result==='WIN'){w++;ls=0}else if(q.result==='LOSS'){l++;ls++;maxLs=Math.max(maxLs,ls)}else t++;}
    const hours=base.length>1?(+base.at(-1).ts-+base[0].ts)/36e5:0;return{asset:assetName,source:src.source,trades:trades.length,wins:w,losses:l,ties:t,winRate:w+l?w/(w+l):null,maxLossStreak:maxLs,tradesPerHour:hours?trades.length/hours:0,hours};
  }

  function v116CleanCoreProposal(asset, price, ind) {
    const act=getAsset(asset);
    if(!act){ lastIndicators.cleanCore={marketClass:'NO_DATA',setup:'NONE',reason:'No asset data'}; return null; }
    const px=Number(price||act.lastPrice||0);
    const strategyAsset=String((typeof asset==='string'?asset:asset?.__assetName) || activeAsset || '');
    const _slot=botConfig?.strategyEngine==='MIXED_SLOTS'?strategySlotForAsset(strategyAsset):null;
    const _customMode=botConfig?.strategyEngine==='CUSTOM_CONFIRM'||!!_slot?.profile;
    const _legacySlot=botConfig?.strategyEngine==='MIXED_SLOTS'&&!_slot?.profile;
    const _cfg=_slot?.profile||botConfig?.strategyProfile||null;
    const sig=_customMode?customStrategySignal(strategyAsset,px,_cfg):v290BBPlusSignal(strategyAsset,px);
    if(!sig){
      if(_customMode){
        const cs=lastIndicators.customStrategy||{};
        const waitReason=cs.profileName?`CUSTOM READY · ${cs.profileName} · ${cs.buys||0} BUY / ${cs.sells||0} SELL confirmations · need ${cs.min||_cfg?.minConfirmations||3}`:`CUSTOM HISTORY · ${strategyAsset} · waiting for enough real candles`;
        lastIndicators.cleanCore={marketClass:'CUSTOM_STRATEGY_READY',setup:'NONE',reason:waitReason};lastIndicators.consolidatedSetup={setup:'NONE',reason:waitReason};return null;
      }
      const _c7src=c7bStrategyRows(strategyAsset), _c7n=_c7src.rows.length;
      const _microReady=_c7n>=24;
      const _c7last=lastIndicators.candidate7B||null;
      const waitReason=!_microReady ? `5s MICRO HISTORY · ${strategyAsset} ${_c7n}/24 usable closed candles · loading chart history.` :
        _c7last ? `5s MICRO READY · ${strategyAsset} · ${_c7last.historySource||_c7src.source} ${_c7n} candles · ${_c7last.marketState||'MIXED'} · waiting for next valid 5s leg.` :
        `5s MICRO READY · ${strategyAsset} · ${_c7src.source} ${_c7n} candles · evaluating next closed 5s candle.`;
      lastIndicators.cleanCore={marketClass:_microReady?'MICRO_TREND_READY':'MICRO_TREND_WARMUP',setup:'NONE',reason:waitReason};
      lastIndicators.consolidatedSetup={setup:'NONE',reason:waitReason};
      return null;
    }
    const m=sig.measurement||{};
    // B19-audit FIX: ema60_10 belonged to the retired BB45 measurement and is never
    // populated by the Winner PRO / BB Chop measurement objects, so it exported as
    // a permanent null. Record the BB mid (real Winner/Chop field) instead.
    lastIndicators.cleanCore={marketClass:sig.tradeType,setup:sig.tradeType,dir:sig.dir,score:sig.str,rsi14:m.rsi14,bbMid:m.bbMid,bbLower:m.bbLower,bbUpper:m.bbUpper};
    lastIndicators.consolidatedSetup={setup:sig.tradeType,dir:sig.dir,score:sig.str,reason:sig.reason};
    return sig;
  }

  function v116CleanCoreDecision(asset, price, ind, setupSig) {
    if(!setupSig) return {skip:true,reason:`HOLD · CANDIDATE 7B · ${lastIndicators.cleanCore?.reason||'waiting for qualified entry'}`};
    const _bbType=String(setupSig.tradeType||'').toUpperCase();
    const sig={...setupSig,mode:_bbType==='MICRO_TREND_CYCLE'?'micro-5s-cycle-live':_bbType==='BB_CHOP'?'bb-chop-live':_bbType==='BB_RUNNER'?'bb-runner-live':'candidate-7b-live',confidence:Number(setupSig.confidence||.86),
      reason:`${String(setupSig.reason||'BB WINNER PRO')} · direct deterministic execution`};
    const _custom=String(sig.tradeType||'').toUpperCase()==='CUSTOM_STRATEGY';
    lastIndicators.aiDecisionTrace={strategy:_custom?(sig.measurement?.profileName||botConfig?.strategyProfileName||'CUSTOM_STRATEGY'):'KAOS_TWO_CANDLE_PULLBACK_CONTINUATION',finalDecision:sig.dir,controller:_custom?'CUSTOM_RULE_ENGINE':'KAOS_CONTINUATION_DIRECT',why:sig.reason,aiExecutionAuthority:false,note:_custom?'B32.9 user-editable deterministic strategy; AI learning only.':'B32.24.0: KAOS two-candle pullback continuation; next-candle entry / 45s expiry; AI learning only.'};
    lastIndicators.aiLastDecision={finalDecision:sig.dir,controller:'7B_DIRECT',why:sig.reason,ts:Date.now(),aiExecutionAuthority:false};
    return {sig,reason:sig.reason};
  }

  function evalAssetSignal(assetName) {
    // V24.1.168: select this chart's private indicator workspace before any
    // strategy/context/core code runs. All downstream `lastIndicators` writes
    // are therefore scoped to this asset for the duration of this evaluation.
    useIndicatorState(assetName);
    if (!multiAssetMode && sessionLockedAsset && assetName !== sessionLockedAsset) {
      return holdReturn(assetName, {skip:true,reason:`ASSET LOCK · ${assetName} ≠ ${sessionLockedAsset}`});
    }
    const key = botConfig?.strategy || 'Murfs Pick';
    const strat = STRATEGIES[key] || STRATEGIES['Murfs Pick'];
    const act = getAsset(assetName);
    const expiry = Math.max(5, parseInt(botConfig?.timeframe || 30, 10)); // V198: selected expiry drives the MTF plan.

    // V198 primary/secondary views follow the selected expiry. The unified controller
    // separately reads its expiry-relative fast/primary/higher judgement plan.
    const tfKey  = expiryToTF(expiry);
    const slowKey = expiryToSecondaryTF(expiry);
    // Strategy views are rebuilt on EVERY check (every SIGNAL_SCAN_MS = 3s).
    // They contain closed higher-TF candles plus the current forming candle.
    // The 5s data is only the aggregation basket; no raw 5s indicator is used.
    // V24.1.5 warmup repair: if 5s history is already sufficient but a higher-TF
    // cache is stale/empty (e.g. after Start reset or history/live handoff), rebuild
    // it before applying the existing readiness gate. This does not change signals.
    const stratMin5s = v241WarmupTarget(act, strat.minPrices || 40);
    if (act.prices.length >= stratMin5s) {
      const fastStored = getTF(act, tfKey).prices.length;
      const slowStored = getTF(act, slowKey).prices.length;
      if (fastStored < 8 || slowStored < 8) rebuildTF(act);
    }
    const tfFast = getLiveTFView(act, tfKey);
    const tfSlow = getLiveTFView(act, slowKey);
    // V227: visible READY and execution readiness use the SAME 15s/30s/60s plan.
    const warmPlan=v197TimeframePlan(expiry);
    const warmFast=getLiveTFView(act,warmPlan.fast), warmPrimary=getLiveTFView(act,warmPlan.primary), warmHigher=getLiveTFView(act,warmPlan.higher);

    // V24.1.128 PER-CHANNEL INDICATOR CONTEXT FIX. The strategy pass inside
    // STRATEGIES[...].fn tags every computed ctx with `a.__assetName || activeAsset`,
    // but __assetName is only stamped on the asset object (line below) — the live TF
    // views returned by getLiveTFView() are shallow clones that never carry it. In a
    // 4-channel grid every channel therefore overwrote the SAME lastIndicatorCtx
    // entry under the current activeAsset key, so only the chart matching activeAsset
    // ever passed the ctxFresh gate below while CH2-CH4 spun forever on
    // 'INDICATOR CONTEXT NOT READY' with no INDI pass. Tag each view with
    // the asset actually being evaluated so ctx lands under its own per-channel key.
    tfFast.__assetName = assetName;
    tfSlow.__assetName = assetName;

    const tfMin = 8;
    const slowMin = 8;
    const storageReady = act.prices.length >= stratMin5s;
    const tfReady = tfFast.prices.length >= tfMin;
    const slowReady = tfSlow.prices.length >= slowMin;
    const fullPlanReady = warmFast.prices.length>=8 && warmPrimary.prices.length>=8 && warmHigher.prices.length>=8;

    // V24.1.67 MARKET WARMUP AUTHORITY GATE
    // A trained/imported AI model is only the prediction engine; it is NOT a
    // bypass around current-market readiness.  Every execution path must wait
    // until the SAME asset has enough fresh 5s storage + primary/secondary TF
    // context for the bot/indicator engine.  Previously evalAssetSignal checked
    // only the higher-TF views, so 8 live TF candles could become available while
    // the raw 5s basket was still below the bot's warmup requirement, allowing
    // AI-FIRST to trade while the UI correctly still showed Warmup < 100%.
    // B15.10.8: ONE warmup gate only. Once the market has 50 closed 5s candles,
    // START means START. Higher-TF views are context/telemetry, never a second
    // hidden warmup percentage or startup blocker.
    if (!storageReady) {
      const pct = Math.floor(Math.min(100, (act.prices.length / stratMin5s) * 100));
      lastDebugReason = `Warmup ${pct}% · 5s ${act.prices.length}/${stratMin5s}`;
      return holdReturn(assetName, { skip: true, reason: 'warmup', warmupPct: pct });
    }

    // IMPORTANT: Do NOT wait for a new 15s/30s candle here.
    // The strategy is checked every scan (~3s) against the LIVE higher-TF candles.
    // This catches a transition during the forming 15s/30s candle while
    // keeping every indicator on its proper configured timeframe.
    act.__assetName = assetName;
    act.__expirySeconds = expiry;
    act.__tfKey = tfKey;
    act.__slowKey = slowKey;
    act.newCandle = false;

    let sig = null;
    const evalStartedAt = Date.now();
    try {
      sig = strat.fn(tfFast, tfSlow, null);
    } catch (err) {
      const msg = (err && err.message) ? err.message : String(err);
      // Never let XGBoost make a decision from blank/stale indicators.
      // V24.1.23 continued after a strategy exception, which produced
      // UNKNOWN / TQS 0/0 / MQ 0 while the status bar still showed warmup.
      lastDebugReason = 'INDICATOR CONTEXT ERROR: ' + msg;
      aiLog('INDICATOR_CONTEXT_ERROR', {asset:assetName,message:msg}, true);
      console.error('[POAT] strategy/indicator context error', err);
      return holdReturn(assetName, { skip:true, reason:lastDebugReason }); // V24.1.135 C: counted
    }

    const ctxEntry = lastIndicatorCtx[assetName];
    const ctxFresh = !!(ctxEntry && ctxEntry.ctx && ctxEntry.ctx.contextReady === true &&
      ctxEntry.ts >= evalStartedAt - 50 && (Date.now() - ctxEntry.ts) < 10000);
    if (!ctxFresh) {
      lastDebugReason = 'INDICATOR CONTEXT NOT READY · waiting for fresh strategy pass';
      return holdReturn(assetName, { skip:true, reason:lastDebugReason }); // V24.1.135 C: counted
    }
    const liveInd = ctxEntry.ctx;
    const livePrice = Number((getAsset(assetName)||{}).lastPrice || lastTickPrice[assetName] || tfFast.prices.at(-1) || 0);

    // V24.1.124: every channel owns its own indicator snapshot so the debug
    // panel always shows the channel that was actually evaluated — never a
    // shared lastIndicators object overwritten by whichever channel ran last.
    const ch = initChannelState(assetName);
    ch.indicators = {
      price: livePrice,
      rsi: liveInd?.rsi ?? liveInd?.rsi30 ?? null,
      ema5: liveInd?.ema5 ?? null,
      ema9: liveInd?.ema9 ?? null,
      ema21: liveInd?.ema21 ?? null,
      atr: liveInd?.atr ?? null,
      stoch: liveInd?.stoch ?? null,
      stochD: lastIndicators?.stochD ?? null,
      macd: liveInd?.macd ?? null,
      macdSignal: liveInd?.macdSignal ?? null,
      buyScore: lastIndicators?.buyScore ?? liveInd?.tradBuy ?? null,
      sellScore: lastIndicators?.sellScore ?? liveInd?.tradSell ?? null,
      tqsBuy: liveInd?.tqsBuy ?? null,
      tqsSell: liveInd?.tqsSell ?? null,
      marketQuality: liveInd?.marketQuality ?? null,
      adx: liveInd?.adx ?? null,
      plusDI: liveInd?.plusDI ?? null,
      minusDI: liveInd?.minusDI ?? null,
      regime: liveInd?.regime ?? 'UNKNOWN',
      marketClass: lastIndicators?.cleanCore?.marketClass ?? null,
      setup: lastIndicators?.cleanCore?.setup ?? null,
      ts: Date.now()
    };

    // V24.1.118 SELECTIVE EDGE CORE: legacy strategy still computes indicator context only.
    // Execution now flows through one regime-first rules engine. The old consolidated
    // bootstrap/AI_FIRST_LEARN decision maze remains in the file for rollback/history
    // but is no longer on the live execution path.
    const legacySig = sig;
    sig = v116CleanCoreProposal(assetName, livePrice, liveInd);

    // V199: refresh the per-channel UI snapshot AFTER the three-step engine has
    // run. V198 captured this before v116CleanCoreProposal(), so the popup could
    // never display the new Trend/Momentum/Volatility decision fields.
    {
      const ts=lastIndicators?.threeStep || {};
      const cc=lastIndicators?.cleanCore || {};
      ch.indicators = {
        ...(ch.indicators||{}),
        marketClass: cc.marketClass ?? ch.indicators?.marketClass ?? null,
        setup: cc.setup ?? ch.indicators?.setup ?? null,
        trendScore: ts.trendQuality ?? cc.trend ?? null,
        momentumScore: ts.momentumQuality ?? cc.momentum ?? null,
        volatilityScore: ts.volatilityQuality ?? cc.volatility ?? null,
        finalThreeStepScore: ts.finalThreeStepScore ?? null,
        primaryTrend: ts.pTrend ?? null,
        higherTrend: ts.hTrend ?? null,
        fastMomentum: ts.fastAligned ?? null,
        primaryMomentum: ts.primaryAligned ?? null,
        timeframePlan: ts.plan ?? v197TimeframePlan(parseInt(botConfig?.timeframe||30,10)),
        threeStepState: ts.state ?? 'HOLD',
        threeStepReason: ts.reason ?? lastIndicators?.v194HoldReason ?? null,
        scoreBreakdown: ts.scoreBreakdown ?? cc.scoreBreakdown ?? null,
        weightedDir: ts.dir ?? cc.dir ?? null,
        adaptiveFloor: ts.adaptiveFloor ?? 64,
        ts: Date.now()
      };
    }
    // Queue every clean candidate, including all qualified setup candidates,
    // using the real 30-second future market direction as the label.
    // B15.10.32 HYBRID ONLY: no AI/legacy learning queue on the live decision path.

    // V209: ONE LIVE TRADE DRIVER. The selected-expiry three-step rules engine
    // (Trend / Momentum / Volatility) owns BUY / SELL / NO TRADE.
    // IMPORTANT: AI samples, model training state, labeled outcomes, holdout
    // counts, and micro sample readiness have ZERO authority to delay a trade.
    // XGBoost/LightGBM and micro telemetry observe/learn in parallel only.
    const v23 = v116CleanCoreDecision(assetName, livePrice, liveInd, sig);
    if (v23.skip) {
      // V24.1.282: a proposal-level signal that the decision engine still refuses
      // (re-entry gap, veto park, payout/EV guard) must ALSO feed the participation
      // floor, otherwise a chart blocked downstream never escalates its tier.
      { const v282sk=v282AssetKey(null)||String(assetName||''); v282HoldStreak[v282sk]=(v282HoldStreak[v282sk]||0)+1; }
      lastDebugReason = v23.reason;
      return holdReturn(assetName, { skip:true, reason:v23.reason }); // V24.1.135 C: counted
    }
    sig = v23.sig;
    aiLog('FINAL_DECISION', {asset:assetName,dir:sig.dir,mode:sig.mode,controller:String(sig.mode||'').startsWith('consolidated-')?'SETUP_ENGINE':sig.mode==='xgb-ai'?'XGBOOST':sig.mode==='v23+xgb-ai'?'ENSEMBLE':sig.mode==='v23-ai'?'V23':'STRATEGY',confidence:sig.confidence,reason:sig.reason,xgb:lastIndicators.xgbAI,trace:lastIndicators.aiDecisionTrace}, true);
    console.info('[KAOS V118 DECISION]', {asset:assetName, dir:sig.dir, mode:sig.mode, reason:sig.reason, confidence:sig.confidence, xgb:AI_LAB.last});

    // V24.1.188: actual order expiry is selected by strategy family from the
    // frozen forward-evidence map above. The global popup timeframe still drives
    // the legacy context pass, but it no longer forces every strategy to 60s.
    // B15-audit FIX: B15's release note claims the BB45/Alligator/ROC strategy
    // forces a 5-second expiry, but v191ExecutionExpiry() was never called on the
    // live path and the popup timeframe (default 60s) overwrote it here. Route
    // through v191ExecutionExpiry so BB50_ALLIGATOR_ROC always executes at 5s
    // while every other family keeps the popup-selected expiry.
    const executionExpiry = v191ExecutionExpiry(sig, null);
    sig.executionExpiry = executionExpiry;
    const executionTfKey = expiryToTF(executionExpiry);
    // B15.10.4: a live middle-BB order no longer hides a later independent outer-BB setup.
    const setupKey=String(sig?.tradeType||sig?.mode||'UNKNOWN').toUpperCase();
    const closed5Key=Number(getAsset(assetName)?.lastClosed||0);
    const sourceKey=Number(sig?.measurement?.sourceSeq||0) || closed5Key;
    const uniqueSetupKey=`${setupKey}:${sourceKey}`;
    if(multiAssetMode && !canOpenAnotherTrade(assetName))
      return holdReturn(assetName,{skip:true,reason:`max ${MAX_CONCURRENT_TRADES_PER_ASSET} open trades`});
    if(assetLastSetupKey[assetName]===uniqueSetupKey)
      return holdReturn(assetName,{skip:true,reason:'duplicate setup/candle'});
    if(Date.now()-Number(assetLastSetupAt[assetName]||0)<4500)
      return holdReturn(assetName,{skip:true,reason:'fresh 5s entry spacing'});
    return {asset:assetName,sig,tfKey:executionTfKey,expiry:executionExpiry,uniqueSetupKey};
  }

  // B25 HARD RUNNER EXECUTION GUARD — revalidate the exact 15s setup at the
  // order boundary. A Runner signal is rejected if its source candle is stale,
  // RSI/candle direction no longer qualifies, or live price has entered the
  // outer-band exhaustion zone. This prevents a valid earlier continuation
  // signal from being executed after the move is already stretched.
  function v290RunnerExecutionGuard(assetName, sig) {
    if(String(sig?.tradeType||'').toUpperCase()!=='BB_RUNNER') return {ok:true};
    const a=getAsset(assetName); if(!a)return {ok:false,reason:'runner guard: no asset'};
    const frozen=sig?.measurement?.signalSnapshot;
    if(!frozen)return {ok:false,reason:'runner guard: missing frozen signal snapshot'};
    const t=getTF(a,'15s');
    const ks=Object.keys(t?.rates||{}).map(Number).filter(Number.isFinite).sort((x,y)=>x-y);
    const liveSeq=Number(ks[ks.length-1]||0), sourceSeq=Number(frozen.sourceSeq||0);
    if(!sourceSeq || liveSeq!==sourceSeq)return {ok:false,reason:`runner guard: stale 15s candle ${sourceSeq} -> ${liveSeq}`};
    const o=Number(frozen.open),h=Number(frozen.high),l=Number(frozen.low),c=Number(frozen.close);
    const r=Number(frozen.rsi14),e9=Number(frozen.ema9),e21=Number(frozen.ema21);
    const mid=Number(frozen.bbMid),lo=Number(frozen.bbLower),hi=Number(frozen.bbUpper),half=(hi-lo)/2;
    const closePos=Number(frozen.bbPosition),midSlope=Number(frozen.midSlope),emaSpread=Number(frozen.emaSpread),widthRatio=Number(frozen.widthRatio),bodyFrac=Number(frozen.bodyFrac);
    if(![o,h,l,c,r,e9,e21,mid,lo,hi,half,closePos,midSlope,emaSpread,widthRatio,bodyFrac].every(Number.isFinite)||!(half>0))return {ok:false,reason:'runner guard: invalid frozen snapshot'};
    const livePx=Number(a.lastPrice||c), livePos=(livePx-mid)/half;
    const bullTrend=e9>e21&&midSlope>=.040&&emaSpread>=.025;
    const bearTrend=e9<e21&&midSlope<=-.040&&emaSpread>=.025;
    const common=bodyFrac>=.20&&widthRatio>=.86&&widthRatio<=1.48;
    const dir=String(sig?.dir||'').toUpperCase();
    const ok = dir==='BUY'
      ? common&&bullTrend&&c>o&&c>mid&&closePos>=.18&&closePos<.75&&r>=53&&r<=65&&h<hi&&livePx<hi&&livePos<.75
      : dir==='SELL'
      ? common&&bearTrend&&c<o&&c<mid&&closePos<=-.18&&closePos>-.75&&r<=47&&r>=35&&l>lo&&livePx>lo&&livePos>-.75
      : false;
    return {ok,reason:ok?'':`runner guard: ${dir} rejected · frozen RSI ${r.toFixed(1)} · closeZone ${closePos.toFixed(2)} · liveZone ${livePos.toFixed(2)} · body ${(bodyFrac*100).toFixed(0)}%`,rsi:r,closePos,livePos,bodyFrac,sourceSeq};
  }

  function fireTrade(assetName, sig, tfKey, expiry, chartConfirmed = false, microConfirmed = false, microAssessment = null) {
    // V276.1: FOLLOWS POCKET OPTION — no account-type gate. Autonomous execution
    // runs on whatever account Pocket Option has active (DEMO or REAL); the
    // real/demo choice belongs to PO alone. The previous V198 demo-only gate
    // (`gridAccountIsDemo !== true -> return`) blocked EVERY REAL account and
    // contradicted V24.1.130. An unknown account type now only triggers one
    // account probe for the badge — it never blocks execution.
    // B32.20.7: resolve once from the signal. MICRO_TREND_CYCLE declares 15s and
    // must not inherit the 60s context/popup timeframe.
    expiry = v191ExecutionExpiry(sig, null);
    if (gridAccountIsDemo == null) {
      try { window.postMessage({_poatCmd:true,type:'ACCOUNT_PROBE'}, '*'); } catch(_) {}
    }

    // V24.1.188 multi-chart execution can arrive after a micro-confirm delay.
    // Re-bind the legacy indicator reference to this trade's own asset before
    // any execution-time telemetry/snapshot work.
    useIndicatorState(assetName);
    // V24.1.108 HARD STOP INVARIANT: no delayed micro/chart callback may ever
    // reach the execution boundary after STOP has been pressed.
    if (!isRunning || window.__poatStopped) {
      aiLog('TRADE_BLOCKED_STOPPED',{asset:assetName,dir:sig?.dir||null},true);
      return false;
    }
    initAssetState(assetName);
    const _b25RunnerGuard=v290RunnerExecutionGuard(assetName,sig);
    if(!_b25RunnerGuard.ok){
      aiLog('TRADE_BLOCKED_B25_RUNNER_GUARD',{asset:assetName,dir:sig?.dir||null,reason:_b25RunnerGuard.reason,rsi:_b25RunnerGuard.rsi,closePos:_b25RunnerGuard.closePos,livePos:_b25RunnerGuard.livePos},true);
      bumpHoldCount(assetName,'B25 · runner execution guard');
      sendStatus(`⛔ RUNNER GUARD · ${assetName} · ${_b25RunnerGuard.reason}`);
      return false;
    }
    // B15.2 CLEAN STRATEGY AUTHORITY: BB45/Alligator/ROC is the live strategy.
    // Legacy KAOS conviction, payout/EV, regime and micro-confirmation gates
    // must not alter the mechanical candidate we are forward-testing.
    const isBB45AlligatorRoc = String(sig?.tradeType||'').toUpperCase().startsWith('BBPLUS_') || String(sig?.tradeType||'').toUpperCase().startsWith('BB45_') || String(sig?.tradeType||'').toUpperCase().startsWith('CANDIDATE_B_') || String(sig?.tradeType||'').toUpperCase()==='CANDIDATE_7B';

    // V198: execution uses the user-selected expiry and its matching primary TF.
    // B15-audit FIX: BB45/Alligator/ROC is hard-pinned to 5s regardless of the
    // popup timeframe (B15 allowed the default 60s to override the test candidate).
    // B32.20.7: do not recompute from botConfig here. The signal's executionExpiry
    // remains authoritative all the way to PLACE_TRADE.
    expiry = v191ExecutionExpiry(sig, null);
    tfKey = expiryToTF(expiry);
    if(sig) sig.executionExpiry = expiry;

    // V24.1.97 single-mode invariant: never execute a background-stream asset.
    if (!multiAssetMode) {
      if (!sessionLockedAsset || assetName !== sessionLockedAsset) {
        aiLog('TRADE_BLOCKED_SINGLE_ASSET_LOCK',{signalAsset:assetName,lockedAsset:sessionLockedAsset,chartAsset:chartSelectedAsset},true);
        sendStatus(`⛔ ASSET LOCK · signal ${assetName} ≠ locked ${sessionLockedAsset||'unknown'}`);
        return false;
      }
      if (!chartSelectedAsset || chartSelectedAsset !== sessionLockedAsset) {
        aiLog('TRADE_BLOCKED_VISIBLE_CHART_LOCK',{signalAsset:assetName,lockedAsset:sessionLockedAsset,chartAsset:chartSelectedAsset},true);
        sendStatus(`⛔ CHART LOCK · chart ${chartSelectedAsset||'unknown'} ≠ ${sessionLockedAsset}`);
        return false;
      }
    }

    // ─────────────────────────────────────────────────────────────────────
    // V24.1.131 — LIVE PAYOUT FLOOR + REALIZED-EV REST (execution vetoes).
    // V24.1.91's 92% rule only steered chart selection and the `const pp =
    // payoutPct(assetName)` at this spot was dead — a payout collapse (e.g.
    // DOGE_otc 0.92 → 0.29) traded straight through. Every execution now
    // enforces a live 80% payout floor plus a realized-EV rest veto, in single
    // AND grid mode.
    if (!isBB45AlligatorRoc) {
      // While any channel/session park is active, execution stays blocked: bail
      // silently so re-entries do not re-arm the park or re-log the veto.
      const alreadyParked = multiAssetMode
        ? Date.now() < initChannelState(assetName).cooldownUntil
        : Date.now() < cooldownUntil;
      if (alreadyParked) return false;

      // ── V24.1.281 — CONVICTION GATE (universal execution backstop) ──────────
      // Enforced here so EVERY family (UNIFIED_MTF, momentum, range-reversal,
      // single-chart and grid) is covered, not just the directional engine, matching
      // how the 1004-trade post-mortem was measured. It does NOT park the channel —
      // it only declines this one entry, so trade volume stays healthy. Set
      // V281_CONVICTION_ENABLED = false (top of file) to disable.
      // V24.1.282: pass the setup family so the gate exempts RANGE_REVERSAL
      // (mean reversion), which the directional rules would otherwise veto wrongly.
      const _execFamily=String(sig?.tradeType||'').toUpperCase();
      const isCandidateB = _execFamily.startsWith('CANDIDATE_B_');
      const isB23DirectBB = ['BB_WINNER_PRO','BB_RUNNER','BB_CHOP','SMC_BOS_ST_ATR','CANDIDATE_7B','CUSTOM_STRATEGY'].includes(_execFamily);
      // B23: V281 was calibrated on the retired directional population and must
      // not override the deterministic BB controller. It remains available to
      // legacy/non-BB families only.
      const v281Block = (isCandidateB||isB23DirectBB) ? '' : v281ConvictionBlock(sig?.dir, assetName, sig?.measurement?.setup || sig?.tradeType);
      if (v281Block) {
        aiLog('TRADE_BLOCKED_V281_CONVICTION', { asset: assetName, dir: sig?.dir || null, reason: v281Block, level: V281_CONVICTION_LEVEL }, true);
        const ch281 = multiAssetMode ? initChannelState(assetName) : null;
        if (ch281) ch281.lastDebugReason = v281Block;
        bumpHoldCount(assetName, 'V281 · conviction');
        sendStatus(`⛔ CONVICTION · ${assetName} · ${v281Block}`);
        return false;
      }

      const pp = payoutPct(assetName);
      // V24.1.151: payout percentage is informational only; it cannot veto, park, or switch a trade.

      if (pp <= 0) {
        aiLog('TRADE_PAYOUT_UNKNOWN_ALLOWED', { asset: assetName, raw: assetPayouts[assetName] }, false);
      } else if (!isCandidateB && V280_PAYOUT_FLOOR_PCT > 0 && pp < V280_PAYOUT_FLOOR_PCT) {
        // ── V24.1.280 — PAYOUT-AWARE ENTRY FLOOR (universal execution choke point) ──
        // Enforced here so EVERY family (UNIFIED_MTF, momentum, range-reversal,
        // single-chart and grid) is covered, not just the directional engine. This is
        // the residual backstop below AUTO_SWITCH_BELOW_PCT=92; when a ≥92% rotation
        // target exists the watchdog switches the chart first, so this branch only
        // fires when the chart genuinely cannot be rotated right now. Set
        // V280_PAYOUT_FLOOR_PCT = 0 (top of file) to disable.
        const beWr = 100 / (1 + pp / 100);
        aiLog('TRADE_BLOCKED_PAYOUT_FLOOR', { asset: assetName, dir: sig?.dir || null, payout: pp, floor: V280_PAYOUT_FLOOR_PCT, breakEvenWr: beWr }, true);
        const ch = multiAssetMode ? initChannelState(assetName) : null;
        if (ch) ch.lastDebugReason = `V280 PAYOUT FLOOR · ${pp.toFixed(1)}% < ${V280_PAYOUT_FLOOR_PCT}%`;
        bumpHoldCount(assetName, 'V280 · payout floor');
        sendStatus(`⛔ PAYOUT FLOOR · ${assetName} ${pp.toFixed(1)}% < ${V280_PAYOUT_FLOOR_PCT}% · break-even WR ${beWr.toFixed(1)}%`);
        return false;
      } else {
        // V24.1.278: REALIZED-EV REST APPLIES TO EVERY FAMILY — including the
        // unified MTF engine. Until now UNIFIED_MTF was exempted ('advisory only'),
        // so the engine that places essentially all trades ran with NO realized-EV
        // protection: a market could bleed indefinitely (the log shows AVAX_otc
        // alone at -110k+) with nothing to stop it. The window was always being
        // filled (recordEvRealized fires on every win/loss); only the veto was
        // switched off. Shrinkage-adjusted (prior 6W/6L) and 0.4pp-hysteresis, so
        // it parks on real deterioration, not on a 3-trade cold streak, and it
        // clears the window afterwards so the market gets a fresh 25-trade trial.
        const ev = isCandidateB ? null : evRestDecision(assetName, pp);
        if (ev && ev.veto) {
          sendStatus(`⛔ EV REST · ${ev.parkedReason}`);
          return false;
        }
      }
    }

    // Multi-grid execution discipline: multi-trading may ONLY execute on an asset
    // that is actually rendered on one of the four grid charts (its live payout
    // already cleared the 80% floor above), and the visible Pocket Option chart
    // must match the signal asset before click.
    if (multiAssetMode) {
      // V121 fixed-grid allow-list: only the four currently visible chart assets
      // may execute. Star/favorite discovery is informational only in this mode.
      if (!slotForAsset(assetName)) {
        aiLog('TRADE_BLOCKED_NOT_VISIBLE_GRID_ASSET',{asset:assetName,slots:{...visibleChartSlots}},true);
        sendStatus(`⛔ GRID · ${assetName} is not one of the 4 visible charts`);
        return false;
      }
      const slotId = slotForAsset(assetName);
      // B32.20.8: selected-chart identity is an execution invariant. A strategy
      // signal may execute only through the slot currently published for that
      // exact asset; stale/background symbols are never allowed to borrow a slot.
      if (slotId && String(visibleChartSlots[slotId]||'') !== String(assetName||'')) {
        aiLog('TRADE_BLOCKED_VISIBLE_ASSET_MISMATCH',{signalAsset:assetName,slotId,slotAsset:visibleChartSlots[slotId],slots:{...visibleChartSlots}},true);
        sendStatus(`⛔ ASSET MISMATCH · ${slotId} shows ${visibleChartSlots[slotId]||'—'} · signal ${assetName}`);
        return false;
      }
      if (!chartConfirmed && !slotId) {
        enqueueMultiChartTrade(assetName,sig,tfKey,expiry);
        return false;
      }
      if (!slotId) {
        aiLog('TRADE_BLOCKED_GRID_SLOT_MISMATCH',{signalAsset:assetName,slots:{...visibleChartSlots}},true);
        sendStatus(`⛔ GRID LOCK · ${assetName} is not in a visible chart slot`);
        return false;
      }
    }

    // Legacy paper-validation backstop (disabled in v24.1.81).
    if (PAPER_SETUP_VALIDATION_MODE) {
      aiLog('TRADE_BLOCKED_PAPER_VALIDATION',{asset:assetName,dir:sig?.dir||null,setup:sig?.tradeType||sig?.mode||null},true);
      sendStatus(`🧪 PAPER VALIDATION · ${assetName} · no trade executed`);
      return false;
    }

    // V24.1.67 FINAL EXECUTION BACKSTOP
    // Do not trust any upstream caller to have applied warmup correctly.  This
    // makes market readiness a hard invariant at the actual click boundary for
    // AI-FIRST, cold-start/bootstrap, runner, reversal, breakout, and multi-asset.
    const strat = STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick'];
    const act = getAsset(assetName);
    const min5s = v241WarmupTarget(act, strat.minPrices || 40);

    // V191 FINAL INTEGRITY + REGIME BACKSTOP. Re-check at execution time because
    // micro confirmation can delay the click after the original setup scan.
    const integrity=v191PriceSeriesIntegrity(assetName);
    if(!integrity.ok){
      aiLog('TRADE_BLOCKED_SERIES_INTEGRITY',{asset:assetName,dir:sig?.dir||null,...integrity},true);
      sendStatus(`⛔ DATA INTEGRITY · ${assetName} · ${integrity.reason}`);
      return false;
    }
    if (String(sig?.tradeType||'').toUpperCase() === 'UNIFIED_MTF') {
      const planNow=v197TimeframePlan(parseInt(expiry || botConfig?.timeframe || 30,10));
      const primaryNow=v198FrameScore(assetName,planNow.primary);
      const higherNow=v198FrameScore(assetName,planNow.higher);
      const sideNow=String(sig?.dir||'').toUpperCase()==='SELL'?-1:1;
      const pNow=Number(primaryNow?.trend||0)*sideNow;
      const hNow=Number(higherNow?.trend||0)*sideNow;
      const isRangeReversal=String(sig?.measurement?.setup||'').toUpperCase()==='RANGE_REVERSAL';
      if(isRangeReversal) {
        const pEff=Number(primaryNow?.pathEfficiency||1), pChop=Number(primaryNow?.chop||0);
        if(!primaryNow?.ready || !higherNow?.ready || (pEff>=0.50 && pChop<=50)) {
          aiLog('TRADE_BLOCKED_RANGE_BROKE_OUT',{asset:assetName,dir:sig?.dir||null,pEff,pChop},true);
          sendStatus(`⛔ RANGE BROKE · ${assetName} · reversal cancelled`);
          return false;
        }
      } else if (!primaryNow?.ready || !higherNow?.ready || pNow < 8 || hNow < -18) {
        aiLog('TRADE_BLOCKED_MTF_DIRECTION_CHANGED',{asset:assetName,dir:sig?.dir||null,primary:planNow.primary,higher:planNow.higher,pTrend:pNow,hTrend:hNow},true);
        sendStatus(`⛔ MTF CHANGED · ${assetName} · ${sig?.dir||'?'} structure no longer aligned`);
        return false;
      }
    } else if (!isBB45AlligatorRoc) {
      const execCtx=v189Context(assetName);
      if(!v191DirectionAligned(execCtx,sig)){
        aiLog('TRADE_BLOCKED_REGIME_MISMATCH',{asset:assetName,dir:sig?.dir||null,tradeType:sig?.tradeType||null,state:execCtx?.state||null},true);
        sendStatus(`⛔ REGIME CHANGED · ${assetName} · ${sig?.dir||'?'} ${sig?.tradeType||''} no longer aligned`);
        return false;
      }
    }
    const primaryKey = tfKey || expiryToTF(parseInt(expiry || botConfig?.timeframe || 30, 10));
    const secondaryKey = expiryToSecondaryTF(parseInt(expiry || botConfig?.timeframe || 30, 10));
    const primary = getLiveTFView(act, primaryKey);
    const secondary = getLiveTFView(act, secondaryKey);
    const marketWarm = !!act && Array.isArray(act.prices) && act.prices.length >= min5s;
    if (!marketWarm) {
      const storagePct = Math.min(100, ((act?.prices?.length || 0) / min5s) * 100);
      const pct = Math.floor(storagePct);
      lastDebugReason = `HOLD · MARKET WARMUP ${pct}% · 5s ${act?.prices?.length || 0}/${min5s}`;
      sendStatus(`📡 ${assetName} · Warmup ${pct}% · 5s ${act?.prices?.length || 0}/${min5s}`);
      aiLog('TRADE_BLOCKED_MARKET_WARMUP',{asset:assetName,pct,storage:act?.prices?.length||0,min5s,primaryKey,primaryCount:primary?.prices?.length||0,secondaryKey,secondaryCount:secondary?.prices?.length||0,requestedDir:sig?.dir||null},true);
      return false;
    }

    // V24.1.158: classified candle setups are candle-close timing strategies. Its
    // shadow edge is measured from the qualified 30s close, so delaying the real
    // click by 0.65-1.8s can turn a good continuation into a late entry. Execute
    // this family immediately at the qualified close. All other setup families
    // retain the existing micro-confirmation behavior.
    const unifiedThreeStep = String(sig?.tradeType || '').toUpperCase()==='UNIFIED_MTF';
    const instantCandleContinuation = isBB45AlligatorRoc || ['CANDLE_CONTINUATION','CANDLE_REVERSAL','TREND_ALIGNMENT'].includes(String(sig?.tradeType || '').toUpperCase());
    if (!microConfirmed && unifiedThreeStep) {
      microAssessment = microAssess(assetName, sig?.dir);
      microLastAssessment[assetName] = microAssessment;

      const microIntervalsReady =
        microAssessment &&
        microAssessment.reason!=='micro intervals not distinct' &&
        microAssessment.reason!=='micro intervals sparse' &&
        microAssessment.reason!=='micro data building' &&
        Number.isFinite(Number(microAssessment.seg1Atr)) &&
        Number.isFinite(Number(microAssessment.seg2Atr)) &&
        Number.isFinite(Number(microAssessment.seg3Atr));

      if(!microIntervalsReady) {
        // V209: missing/sparse micro is NOT a trade blocker. Candle warmup and
        // the 30s/60s/15s rules engine already established trade readiness.
        // Keep this only as telemetry so the micro stream can be debugged.
        aiLog('MICRO_DATA_UNAVAILABLE_ADVISORY',{
          asset:assetName,dir:sig?.dir||null,tradeType:sig?.tradeType||null,
          reason:microAssessment?.reason||'micro building',
          state:microAssessment?.state||'NEUTRAL'
        },false);
      }

      // Only valid, fresh micro data can veto, and only for severe contradiction.
      const execMicroQuality=microIntervalsReady
        ? v203MicroQuality(assetName,sig?.dir,microAssessment)
        : {score:50,bonus:0,block:false,state:'UNAVAILABLE',raw:microAssessment};
      if(microIntervalsReady && execMicroQuality.block) {
        aiLog('TRADE_BLOCKED_FRESH_MICRO_CONTRADICTION',{
          asset:assetName,dir:sig?.dir||null,state:microAssessment.state,
          seg1Atr:microAssessment.seg1Atr,seg2Atr:microAssessment.seg2Atr,
          against:microAssessment.against,imbalance:microAssessment.imbalance
        },true);
        bumpHoldCount(assetName, `micro contradiction · ${sig?.dir||'?'} entry cancelled`);
        if (lastIndicators && typeof lastIndicators === 'object') {
          lastIndicators.v194HoldReason = `micro contradiction · ${sig?.dir||'?'} entry cancelled`;
        }
        return false;
      }

      microConfirmed = true;
      aiLog('MICRO_ENTRY_QUALITY_UNIFIED_MTF',{
        asset:assetName,dir:sig?.dir||null,tradeType:sig?.tradeType||null,state:microAssessment?.state||'NEUTRAL',
        support:microAssessment?.support||0,against:microAssessment?.against||0,r2Atr:microAssessment?.r2Atr??null,seg1Atr:microAssessment?.seg1Atr??null,seg2Atr:microAssessment?.seg2Atr??null,seg3Atr:microAssessment?.seg3Atr??null
      },false);
    } else if (!microConfirmed && instantCandleContinuation) {
      microConfirmed = true;
      microAssessment = {
        state:'BYPASS',
        reason:'Qualified BB45/Alligator/ROC or aligned-flow setup executes immediately; no legacy micro veto',
        at:Date.now()
      };
      aiLog('MICRO_CONFIRM_BYPASS_CLASSIFIED_CANDLE',{
        asset:assetName,dir:sig?.dir||null,tradeType:sig?.tradeType||null,reason:microAssessment.reason
      },false);
    } else if (!microConfirmed) {
      queueMicroConfirmation(assetName, sig, tfKey, expiry, chartConfirmed);
      return false;
    }

    const amt = multiAssetMode ? assetCurrentAmount[assetName] : currentAmount;

    if (multiAssetMode) {
      if(!canOpenAnotherTrade(assetName)) return false;
      assetOpenTradeCount[assetName]=openTradeCount(assetName)+1;
      syncAssetPending(assetName);
      const setupKey=String(sig?.tradeType||sig?.mode||'UNKNOWN').toUpperCase();
      const closed5Key=Number(getAsset(assetName)?.lastClosed||0);
      const sourceKey=Number(sig?.measurement?.sourceSeq||0) || closed5Key;
      assetLastSetupKey[assetName]=`${setupKey}:${sourceKey}`;
      assetLastSetupAt[assetName]=Date.now();
    } else {
      tradePending=true;
    }
    lastTradeDir  = normalizeTradeDirection(sig.dir) || sig.dir;
    lastTradeAsset = assetName;
    const requestedDirection = normalizeTradeDirection(sig.dir);
    if (requestedDirection) {
      pendingTradeDirections[assetName] = requestedDirection;
      rememberTradeDirection(assetName, requestedDirection);
    }
    lastTradeAmt   = amt;
    assetLastTrade[assetName] = Date.now() / 1000;
    if (sig?.measurement?.marketClass === 'UNIFIED_MTF' || sig?.measurement?.expiryPolicy === 'V234_EVERYTHING_LEARNING_DIRECTIONAL') {
      const executedEntryPrice = Number((getAsset(assetName)||{}).lastPrice || lastTickPrice[assetName] || 0);
      v229DirectionalEntryState[assetName] = {dir:String(sig.dir||'').toUpperCase(), at:Date.now(), price:executedEntryPrice};
    }
    if (multiAssetMode) initChannelState(assetName).lastTradeAt = Date.now(); // V24.1.124 per-channel stamp
    const entrySnapshot = captureSnapshot(sig.dir, amt, 'signal', sig, assetName);
    entrySnapshot.microEntry = microAssessment || microLastAssessment[assetName] || null;
    setPendingSnapshot(assetName, entrySnapshot);
    // v19.10: snapshot the exact strategy/gate context at entry so realized
    // performance can be separated into RUNNER / REVERSAL / GENERIC.
    const entryType = String(sig.tradeType || '').toUpperCase();
    const dedicatedPath = ['run-rev','ai-autonomous'].includes(String(sig.mode || '').toLowerCase()) ||
      (Array.isArray(sig.reasons) && sig.reasons.some(r => /^(runnerEntry|reversalEntry)$/.test(String(r))));
    entrySnapshot.strategyType = entryType || (String(sig.mode||'').toLowerCase()==='ai-autonomous' ? 'AI' : 'GENERIC');
    const mm = sig.measurement || {};
    entrySnapshot.runBuy = Number(mm.runBuy ?? 0) || 0;
    entrySnapshot.runSell = Number(mm.runSell ?? 0) || 0;
    entrySnapshot.revBuy = Number(mm.revBuy ?? 0) || 0;
    entrySnapshot.revSell = Number(mm.revSell ?? 0) || 0;
    entrySnapshot.tqsBuy = Number(mm.tqsBuy ?? sig.tqs ?? 0) || 0;
    entrySnapshot.tqsSell = Number(mm.tqsSell ?? 0) || 0;
    // V24.1.133: every real trade comes from the V118 setup engine: mm.mq first
    // (historical behavior), then the V118 proposal's sig.marketQuality as the
    // fallback.
    entrySnapshot.marketQuality = Number((mm.mq ?? sig.marketQuality) ?? 0) || 0;
    entrySnapshot.aiBuy = Number(mm.aiBuy ?? lastIndicators.aiPrediction?.up ?? 0.5);
    entrySnapshot.aiSell = Number(mm.aiSell ?? lastIndicators.aiPrediction?.down ?? 0.5);
    entrySnapshot.regimeAtEntry = mm.regime || lastIndicatorCtx[assetName]?.ctx?.regime || null;
    entrySnapshot.marketClassAtEntry = mm.marketClass || lastIndicatorCtx[assetName]?.ctx?.cleanCore?.marketClass || null;

    // V24.1.188: mirror this exact real entry into all configured shadow horizons.
    // Measurement only — shadow timers do not create extra Pocket Option orders.
    entrySnapshot.shadowOutcomeId = sig?.v181ShadowOutcomeId || queueShadowOutcomeComparison(assetName, sig, entrySnapshot.entryPrice);

    if (multiAssetMode) {
      clearTimeout(assetStaleTimers[assetName]);
      assetStaleTimers[assetName] = setTimeout(() => {
        if(assetTradePending[assetName]){
          assetOpenTradeCount[assetName]=0; syncAssetPending(assetName);
          sendStatus(`⚠ Trade lock expired · ${assetName} · Resuming`);
        }
        delete assetStaleTimers[assetName];
      }, (expiry + 30) * 1000);
    } else {
      clearTimeout(window.__poatStaleLock);
      window.__poatStaleLock = setTimeout(() => {
        if (tradePending) { tradePending = false; sendStatus(`⚠ Trade lock expired · Resuming`); }
      }, (expiry + 30) * 1000);
    }

    const _orderExpiry = Math.max(5, Number(expiry || sig?.executionExpiry || 15));
    aiLog('EXECUTION_EXPIRY_TRACE',{asset:assetName,tradeType:sig?.tradeType||null,signalExpiry:Number(sig?.executionExpiry||0),resolvedExpiry:_orderExpiry,contextTimeframe:Number(botConfig?.timeframe||0)},true);
    console.info('[KAOS EXPIRY TRACE]',{asset:assetName,tradeType:sig?.tradeType,signalExpiry:sig?.executionExpiry,resolvedExpiry:_orderExpiry,contextTimeframe:botConfig?.timeframe});
    window.postMessage({ _poatCmd: true, type: 'PLACE_TRADE', dir: sig.dir, asset: assetName, slotId: multiAssetMode ? slotForAsset(assetName) : '', amount: amt, expiry: _orderExpiry }, '*');
    // Cloud telemetry: record the exact live signal/order intent under the same account used by
    // tradingwithkaos.com. This is reporting only; Pocket Option execution remains above.
    try {
      chrome.runtime.sendMessage({ type: 'KAOS_TRADE_EVENT', eventType: 'SIGNAL_GENERATED', trade: {
        tradeId: entrySnapshot?.tradeID || null, signalId: entrySnapshot?.tradeID || null,
        asset: assetName, direction: sig.dir, amount: amt, expiration: String(_orderExpiry) + 's',
        strategy: botConfig?.strategy || 'KAOS Strategy', strategyVersion: '7B', tradingMode: 'STRATEGY',
        entryPrice: entrySnapshot?.entryPrice ?? null, confidence: sig.confidence ?? sig.str ?? null,
        timestamp: new Date().toISOString()
      }}).catch(() => {});
    } catch (_) {}

    // V24.1.60: avoid double-counting the same qualified setup as both a
    // setup sample and a trade sample. If this execution was NOT preceded by a
    // recent qualified setup snapshot, retain the trade sample as a fallback.
    const tradeInd = lastIndicatorCtx[assetName];
    const tradeIndCtx = (tradeInd && (Date.now() - tradeInd.ts) < 30000) ? tradeInd.ctx : undefined;
    const recentSetupAt = Number((aiState.lastQualifiedSetupAt||{})[assetName] || 0);
    if (Date.now() - recentSetupAt > 12000) {
      aiQueueSample(assetName, (getAsset(assetName)||{}).lastPrice || lastTickPrice[assetName] || 0, 'trade', tradeIndCtx, entrySnapshot?.tradeID,
        {tradeType:sig.tradeType||sig.mode||'TRADE',setupDir:sig.dir,setupScore:sig.str,setupConfidence:sig.confidence});
    }

    const key = botConfig?.strategy || 'Murfs Pick';
    sendStatus(`⚡ [${key}] ${sig.dir} ${amt} · ${expiry}s · ${sig.tradeType||tfKey} · ${assetName}`);
    recordTradeDebug(sig.dir, assetName, amt, 'signal', 0);
    sendDebug({ reason: `Signal ${sig.dir} · ${sig.reason || 'score ' + sig.str}`, force: true });
  }

  // ════════════════════════════════════════════════════════════
  //  SIGNAL CHECK — runs every SIGNAL_SCAN_MS (3s); indicators use live paired
  //  higher-TF candles. checkSignals(true) bypasses the cadence throttle (used by
  //  armSettleRescan) but still stamps lastSignalCheckAt so a forced scan can
  //  never stack into a scan storm beyond the normal cadence.
  // ════════════════════════════════════════════════════════════
  let lastSignalCheckAt = 0;
  let settleRescanTimer = null;  // V24.1.135 A2: single pending settle-linked re-scan

  // armSettleRescan(): schedule ONE forced signal check shortly after a trade
  // settles so the next opportunity is found immediately instead of on the next
  // cadence tick. Dedupes to a single pending timer (a later settle just
  // re-arms it). Fire-time guard re-checks isRunning/__poatStopped and the
  // pending flags, so STOP_BOT needs no extra hook and martingale paths that
  // already scheduled the next step never reach the arm call sites anyway.
  function armSettleRescan() {
    if (settleRescanTimer) clearTimeout(settleRescanTimer);
    settleRescanTimer = setTimeout(() => {
      settleRescanTimer = null;
      if (!isRunning || window.__poatStopped) return;
      if (multiAssetMode || !tradePending) {
        try { checkSignals(true); } catch (e) { /* keep the loop alive */ }
      }
    }, SETTLE_RESCAN_DELAY_MS);
  }

  // ── V24.1.135 C: HOLD-REASON COUNTERS (observability) ─────────────────────
  // Normalize a skip/cooldown/park/watchdog reason string into a compact key.
  function holdReasonKey(reason) {
    const r = String(reason || 'other').toLowerCase();
    if (!r || r === 'other' || r === 'skip') return 'other';
    if (r.indexOf('context error') !== -1) return 'ctx-error';
    if (r.indexOf('context not ready') !== -1 || r.indexOf('context not fresh') !== -1) return 'ctx-not-ready';
    if (r.indexOf('warmup') !== -1) return 'warmup';
    if (r.indexOf('re-entry') !== -1 || r.indexOf('reentry') !== -1) return 're-entry-gap';
    if (r.indexOf('asset lock') !== -1 || r.indexOf('chart lock') !== -1 || r.indexOf('grid lock') !== -1) return 'asset-lock';
    if (r.indexOf('clean-core location') !== -1 || r.indexOf('no location') !== -1 ||
        r.indexOf('no qualified location') !== -1 || r.indexOf('no clean') !== -1 ||
        r.indexOf('unsupported_tf') !== -1) return 'no-location';
    if (r.indexOf('veto') !== -1 || r.indexOf('xgb') !== -1 || r.indexOf('disagree') !== -1 ||
        r.indexOf('ai wait') !== -1 || r.indexOf('abstain') !== -1) return 'ai-veto';
    if (r.indexOf('no visible') !== -1 || r.indexOf('no chart') !== -1 || r.indexOf('no panels') !== -1) return 'no-panels';
    if (r.indexOf('watchdog') !== -1 || r.indexOf('payout floor') !== -1 || r.indexOf('payout-floor') !== -1) return 'watchdog';
    if (r.indexOf('cooldown') !== -1) return 'cooldown';
    if (r.indexOf('park') !== -1 || r.indexOf('pause') !== -1 || r.indexOf('paused') !== -1 ||
        r.indexOf('banned') !== -1 || r.indexOf('hard stop') !== -1 || r.indexOf('loss streak') !== -1) return 'park';
    return 'other';
  }

  // bumpHoldCount(): +1 on total[key] and byAsset[asset][key]; stores last. The
  // counters must never break the signal path, so everything is try/catch'd.
  function bumpHoldCount(assetName, reason) {
    try {
      if (!aiState.holdCounters || typeof aiState.holdCounters !== 'object') {
        aiState.holdCounters = { total: {}, byAsset: {}, last: null };
      }
      const key = holdReasonKey(reason);
      const name = String(assetName || 'ALL');
      aiState.holdCounters.total[key] = (aiState.holdCounters.total[key] || 0) + 1;
      const ba = aiState.holdCounters.byAsset[name] || (aiState.holdCounters.byAsset[name] = {});
      ba[key] = (ba[key] || 0) + 1;
      aiState.holdCounters.last = { asset: name, key, detail: String(reason || '').slice(0, 200), at: Date.now() };
    } catch (e) { /* never break the signal path */ }
  }

  // holdReturn(): count a skip result then return it unchanged — single-line
  // wrap used at the evalAssetSignal early-return sites.
  function holdReturn(assetName, ret) {
    if (ret && ret.skip) bumpHoldCount(assetName, ret.reason);
    return ret;
  }

  // V24.1.60 QUALIFIED-SETUP LEARNING
  // The old build sampled the market every 5s, so XGB mostly learned ordinary
  // market noise. The new primary population is one real 30s outcome for each
  // qualified setup event. A sparse background control sample is retained only
  // to stop the model from seeing setups in complete isolation.
  const AI_SETUP_SAMPLE_COOLDOWN_MS = 30000;
  const AI_BACKGROUND_SAMPLE_INTERVAL_MS = 120000;

  // B15.10.3 — STRATEGY-SPECIALIST LESSONS.
  // Every BB45 candidate is frozen at the moment it appears, including candidates
  // rejected by our hand-written confirmation rules.  The 30s future result is
  // attached later.  This is learning telemetry only and NEVER places/cancels a trade.
  const aiStrategyLessons = {records:[], stats:{}, lastSeen:{}, max:1200};
  function aiStrategyStatKey(setup,dir){ return `${String(setup||'UNKNOWN')}|${String(dir||'HOLD')}`; }
  function aiQueueStrategyLesson(assetName, price, ind, meta={}) {
    try {
      if(!AI_LEARNING_MODE || !assetName || !Number(price)) return false;
      const dir=(meta.dir==='BUY'||meta.dir==='SELL')?meta.dir:null; if(!dir)return false;
      const setup=String(meta.setup||'BB45_UNKNOWN');
      const closed5=Number((getAsset(assetName)||{}).lastClosed||0);
      const dedupe=`${assetName}|${setup}|${dir}|${closed5||Math.floor(Date.now()/5000)}`;
      if(aiStrategyLessons.lastSeen[dedupe]) return false;
      aiStrategyLessons.lastSeen[dedupe]=Date.now();
      const x=aiFeatures(assetName,Number(price),ind||lastIndicatorCtx?.[assetName]?.ctx||null);
      if(!Array.isArray(x)||x.length!==AI_FEATURES)return false;
      let pred={}; try{pred=aiLabScore(x,assetName)||{};}catch(_){}
      const rec={id:`SL:${Date.now()}:${Math.random().toString(36).slice(2,7)}`,ts:Date.now(),asset:assetName,setup,dir,
        accepted:!!meta.accepted,reason:String(meta.reason||''),entryPrice:Number(price),features:x.slice(),
        xgbUp:Number.isFinite(Number(pred.xgboost))?Number(pred.xgboost):null,
        context:v234Safe({regime:ind?.regime||null,measurement:meta.measurement||null,reasons:meta.reasons||[]}),result:'pending'};
      aiStrategyLessons.records.push(rec); if(aiStrategyLessons.records.length>aiStrategyLessons.max)aiStrategyLessons.records.splice(0,aiStrategyLessons.records.length-aiStrategyLessons.max);
      // Feed the same frozen snapshot to the canonical direction learner.  Accepted
      // and rejected setup candidates therefore teach from identical 30s targets.
      aiQueueSample(assetName,Number(price),'setup',ind,null,{tradeType:setup,setupType:setup,setupDir:dir,
        setupScore:Number(meta.score||0),setupConfidence:Number(meta.confidence||0),acceptedByStrategy:!!meta.accepted,
        rejectionReason:meta.accepted?null:String(meta.reason||'FILTER_REJECTED'),marketClass:ind?.regime||null});
      setTimeout(()=>{
        try{
          const exit=Number((getAsset(assetName)||{}).lastPrice||lastTickPrice[assetName]||0); if(!exit)return;
          rec.exitPrice=exit; rec.resolvedAt=Date.now();
          const eps=Math.max(1e-12,Math.abs(rec.entryPrice)*1e-10);
          const actual=Math.abs(exit-rec.entryPrice)<=eps?'DRAW':exit>rec.entryPrice?'BUY':'SELL'; rec.actualDirection=actual;
          rec.result=actual==='DRAW'?'draw':actual===dir?'win':'loss';
          rec.outcomeWhy=`${setup} ${dir} ${rec.accepted?'accepted':'rejected'} → ${rec.result.toUpperCase()} after 30s; ${(100*(exit-rec.entryPrice)/Math.max(Math.abs(rec.entryPrice),1e-12)).toFixed(4)}% move`;
          const key=aiStrategyStatKey(setup,dir), st=aiStrategyLessons.stats[key]||(aiStrategyLessons.stats[key]={setup,dir,wins:0,losses:0,draws:0,accepted:0,rejected:0,total:0});
          st.total++; st[rec.result==='win'?'wins':rec.result==='loss'?'losses':'draws']++; if(rec.accepted)st.accepted++;else st.rejected++;
        }catch(_){}
      },30000);
      return true;
    } catch(_) { return false; }
  }

  function aiQueueQualifiedSetup(assetName, price, ind, setupSig) {
    if (!AI_LEARNING_MODE || !assetName || !setupSig) return false;
    const dir = setupSig.dir === 'BUY' || setupSig.dir === 'SELL' ? setupSig.dir : null;
    const score = Number(setupSig.str || 0);
    const conf = Number(setupSig.confidence || 0);
    if (!dir || score < 68 || conf < 0.62) return false;
    const now = Date.now();
    aiState.lastQualifiedSetupAt = aiState.lastQualifiedSetupAt || {};
    if (now - Number(aiState.lastQualifiedSetupAt[assetName] || 0) < AI_SETUP_SAMPLE_COOLDOWN_MS) return false;
    const ok = aiQueueSample(assetName, price, 'setup', ind, null, {
      setupType: setupSig.tradeType || setupSig.mode || 'QUALIFIED_SETUP',
      setupDir: dir,
      setupScore: score,
      setupConfidence: conf,
      marketClass: setupSig?.measurement?.marketClass || lastIndicators.cleanCore?.marketClass || null,
      targetKind: setupSig?.measurement?.candleClassifier ? 'CONTINUE_VS_REVERSE' : null,
      sourceCandleDir: setupSig?.measurement?.candleClassifier?.sourceCandleDir || null,
      classifierDecision: setupSig?.measurement?.candleClassifier?.decision || null,
      continueScore: setupSig?.measurement?.candleClassifier?.continueScore,
      reversalScore: setupSig?.measurement?.candleClassifier?.reversalScore,
      runLength: setupSig?.measurement?.candleClassifier?.runLength
    });
    if (ok) {
      aiState.lastQualifiedSetupAt[assetName] = now;
      aiLog('AI_SETUP_SAMPLE_QUEUED', {asset:assetName,dir,score,confidence:conf,setup:setupSig.tradeType||setupSig.mode||'QUALIFIED_SETUP'}, false);
    }
    return ok;
  }

  function aiBackgroundLearnHeartbeat(assetName) {
    if (!AI_LEARNING_MODE || !assetName) return;
    const a = getAsset(assetName);
    const px = Number(a && a.lastPrice || lastTickPrice[assetName] || 0);
    if (!a || !px) return;
    const now = Date.now();
    aiState.lastBackgroundAt = aiState.lastBackgroundAt || {};
    if (now - Number(aiState.lastBackgroundAt[assetName] || 0) < AI_BACKGROUND_SAMPLE_INTERVAL_MS) return;
    const ctxEntry = lastIndicatorCtx[assetName];
    const indFresh = !!(ctxEntry && ctxEntry.ctx && (now - ctxEntry.ts) < 15000);
    if (!indFresh) return;
    // Never let a background sample crowd a nearby setup sample.
    const recentSetupAt = Number((aiState.lastQualifiedSetupAt||{})[assetName] || 0);
    if (now - recentSetupAt < AI_SETUP_SAMPLE_COOLDOWN_MS) return;
    aiState.lastBackgroundAt[assetName] = now;
    aiQueueSample(assetName, px, 'paper', ctxEntry.ctx, null, {setupType:'BACKGROUND_CONTROL'});
  }

  function multiScanAssets() {
    // V121: the four visible chart panels are the complete multi-market allow-list.
    // This intentionally ignores off-screen favorites so all active markets can warm
    // continuously and no chart needs to be rotated or switched.
    const count=botConfig?.chartCount==null?4:Number(botConfig.chartCount);
    const limit=Number.isInteger(count)&&count>0?Math.min(4,kaosChartLimit,count):1;
    return [...new Set(visibleGridAssets())].filter(Boolean).slice(0,limit);
  }

  function getActiveAssets() {
    // V24.1.122e: backward-compatible alias. Some earlier builds exposed the
    // active-market allow-list as getActiveAssets(); after the multiScanAssets()
    // rename a stale caller would throw "getActiveAssets is not defined" and abort
    // the tick. Guarantee it always resolves to the same list the bot actually
    // trades so no caller can blow up the loop on a partial/legacy load.
    return multiAssetMode ? multiScanAssets() : (activeAsset ? [activeAsset] : []);
  }

  function slotForAsset(assetName) {
    for (const [slotId,a] of Object.entries(visibleChartSlots)) if (a===assetName) return slotId;
    return '';
  }

  function visibleGridAssets() { return Object.values(visibleChartSlots).filter(Boolean); }

  // V24.1.124: the global 4-channel pace gate was REMOVED. Each channel now
  // trades at its own rate, governed by its per-channel cooldown and its own
  // expiry-based re-entry gap, so one channel can never pace-block another.

  // V24.1.226 FORENSIC DEBUG — keep what the bot actually saw instead of
  // replacing the popup reason every ~3 seconds. Each visible chart exposes the
  // last 20 decisions plus the previous 10 OHLC candles on 5s/15s/30s/60s.
  function v225ClosedCandles(assetName, tfKey, limit=10) {
    const act=getAsset(assetName), tf=getTF(act,tfKey), cfg=TF_MAP[tfKey];
    if(!tf || !cfg) return [];
    const keys=Object.keys(tf.rates||{}).map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
    const current=Number(tf.lastGroupStart);
    return keys.filter(k=>!Number.isFinite(current)||k<current).slice(-limit).map(k=>{
      const c=tf.rates[k];
      return c ? {time:Number(c[4]??k),open:Number(c[0]),high:Number(c[1]),low:Number(c[2]),close:Number(c[3])} : null;
    }).filter(Boolean);
  }
  function v225RecordDecision(assetName, reason, outcome='HOLD', sig=null) {
    const ch=initChannelState(assetName), ind=ch.indicators||{};
    const m=sig?.measurement||{};
    const text=String(reason||'').trim();
    const prev=ch.decisionHistory?.at(-1);
    // Keep changed decisions, and refresh repeated reasons at most once per 5s.
    if(prev && prev.reason===text && Date.now()-prev.ts<5000) return;
    const b=ind.scoreBreakdown||{};
    const row={seq:++ch.debugSeq,ts:Date.now(),outcome,reason:text,
      buy:Number.isFinite(Number(ind.buyScore))?Number(ind.buyScore):null,
      sell:Number.isFinite(Number(ind.sellScore))?Number(ind.sellScore):null,
      weighted:Number.isFinite(Number(m.finalThreeStepScore))?Number(m.finalThreeStepScore):(Number.isFinite(Number(sig?.str))?Number(sig.str):(Number.isFinite(Number(ind.finalThreeStepScore))?Number(ind.finalThreeStepScore):null)),
      weightedDir:sig?.dir||ind.weightedDir||null, setup:m.setup||ind.setup||null, marketClass:m.marketClass||ind.marketClass||null,
      scoreBreakdown:(m.scoreBreakdown&&Object.keys(m.scoreBreakdown).length?m.scoreBreakdown:b), rsi:ind.rsi??null,stoch:ind.stoch??null,adx:ind.adx??null,
      primaryTrend:m.primaryTrend??ind.primaryTrend??null,higherTrend:m.higherTrend??ind.higherTrend??null,
      fastMomentum:m.fastMomentum??ind.fastMomentum??null,primaryMomentum:m.primaryMomentum??ind.primaryMomentum??null,
      entryPrice:ind.price??null,
      entryCandles:Object.fromEntries(['5s','15s','30s','60s','120s','180s','300s'].map(tf=>[tf,v225ClosedCandles(assetName,tf,10)])),
      allTimeframes:Object.fromEntries(['5s','15s','30s','60s','120s','180s','300s'].map(tf=>[tf,v234Frame(assetName,tf)])),
      canonicalFeatures:(()=>{try{const x=aiFeatures(assetName,Number(ind.price||0),lastIndicatorCtx?.[assetName]?.ctx||ind);return Array.isArray(x)&&x.length===AI_FEATURES?x.slice():null;}catch(_){return null;}})()};
    ch.decisionHistory.push(row);
    if(ch.decisionHistory.length>20) ch.decisionHistory.splice(0,ch.decisionHistory.length-20);
  }

  // V24.1.123: per-channel debug row for the popup live panel / CSV export.
  // One row per visible grid asset: warmup + trade state.
  function gridChannelDebugRow(assetName, index) {
    const w = gridWarmupState(assetName);
    const lastTradeAt = assetLastTrade[assetName] || 0;
    let wins = 0, losses = 0;
    for (const t of debugState.trades) {
      if (t.asset !== assetName) continue;
      if (t.result === 'win') wins++;
      else if (t.result === 'loss') losses++;
    }
    return {
      channel: index + 1,
      asset: assetName,
      ...w,
      trade: {
        pending: !!assetTradePending[assetName],
        openTrades: openTradeCount(assetName),
        maxOpenTrades: MAX_CONCURRENT_TRADES_PER_ASSET,
        microConfirm: !!microPendingByAsset[assetName],
        queued: queuedMultiTrade(assetName),
        lastTradeAgeSec: lastTradeAt ? Math.max(0, Math.round(Date.now() / 1000 - lastTradeAt)) : null,
        lastTradeDir: pendingTradeDirections[assetName] || null,
        martLevel: assetMartLevel[assetName] || 0,
        lossStreak: assetConsLosses[assetName] || 0,
        amount: assetCurrentAmount[assetName] || currentAmount,
        wins, losses
      },
      // V24.1.133: per-channel independent state + controller label
      // (V118 setup engine is the sole driver; AI is the only signal source).
      controller: 'CANDIDATE 7B · ZIGZAG 5/3/1 · LIVE',
      strategyPlan: 'REVERSAL 30s · RUNNER 15s · BREAKOUT 30s · ZIGZAG 5/3/1 STRUCTURE',
      debugReason: channelState[assetName]?.lastDebugReason || null,
      indicators: channelState[assetName]?.indicators || null,
      decisionHistory: (channelState[assetName]?.decisionHistory || []).slice(-10),
      candles: { '5s':v225ClosedCandles(assetName,'5s',10), '15s':v225ClosedCandles(assetName,'15s',10), '30s':v225ClosedCandles(assetName,'30s',10), '60s':v225ClosedCandles(assetName,'60s',10) },
      cooldown: (() => {
        const c = channelState[assetName];
        if (!c || !c.cooldownUntil) return null;
        return { leftSec: Math.max(0, Math.round((c.cooldownUntil - Date.now()) / 1000)), reason: c.cooldownReason || null };
      })(),
      channelLossStreak: channelState[assetName]?.lossStreak || 0,
      channelWinStreak: channelState[assetName]?.winStreak || 0,
      marketHealth: marketHealth(assetName),
      poAI: (()=>{const z=v287State.lastByAsset?.[assetName]||null,s=v287State.sentimentByAsset?.[assetName]||null;return {sentimentBuy:s?.buy??z?.sentimentBuy??null,sentimentSell:s?.sell??z?.sentimentSell??null,sentimentSource:s?.source||z?.sentimentSource||null,sentimentAgeSec:s?.t?Math.max(0,Math.round((Date.now()-s.t)/1000)):null,pred:z?.pred||null,predUp:z?.predUp??null,pathPoints:Array.isArray(z?.path5)?z.path5.length:0,lastPrice:z?.price??null};})()
    };
  }

  function gridWarmupState(assetName) {
    const act=getAsset(assetName);
    const expiry=parseInt(botConfig?.timeframe||30,10);
    // B32.20.3: separate LIVE STRATEGY timeframe from higher-timeframe context.
    // Built-in Candidate/legacy slots now trade the 5s micro-cycle, so tfCandles
    // must report the bootstrapped 5s store rather than a 60s context aggregation.
    const contextTfKey=expiryToTF(expiry), slowKey=expiryToSecondaryTF(expiry);
    const contextFast=getLiveTFView(act,contextTfKey), tfSlow=getLiveTFView(act,slowKey);
    const slot=botConfig?.strategyEngine==='MIXED_SLOTS'?strategySlotForAsset(assetName):null;
    const customMode=botConfig?.strategyEngine==='CUSTOM_CONFIRM'||!!slot?.profile;
    const cfg=slot?.profile||botConfig?.strategyProfile||{};
    const tfKey=customMode?`${Math.max(5,Number(cfg.signalTf)||30)}s`:'5s';
    const tfFast=customMode?getLiveTFView(act,tfKey):null;
    const plan=v197TimeframePlan(expiry), pFast=getLiveTFView(act,plan.fast), pPrimary=getLiveTFView(act,plan.primary), pHigher=getLiveTFView(act,plan.higher);
    const min5s=v241WarmupTarget(act,(STRATEGIES[botConfig?.strategy]||STRATEGIES['Murfs Pick']).minPrices||40);
    const n=act.prices.length;
    // B15.10.4: displayed warmup is always closed-5s history / one fixed target.
    const storagePct=Math.min(100,(n/min5s)*100);
    const pct=Math.floor(storagePct);
    const lastTickAgeSec=act.lastTickSec?Math.max(0,Math.floor(Date.now()/1000)-Number(act.lastTickSec)):null;
    const streamLive=lastTickAgeSec!=null && lastTickAgeSec<=15;
    // Context is telemetry only for the 5s micro authority; it is never a hidden startup gate.
    const contextReady=contextFast.prices.length>=8&&tfSlow.prices.length>=8&&pFast.prices.length>=8&&pPrimary.prices.length>=8&&pHigher.prices.length>=8;
    const strategyTfCandles=customMode?(tfFast?.prices?.length||0):n;
    const ready=pct>=100;
    const state=ready?'READY':(streamLive?'WARMING 5S':'WAITING FOR STREAM');
    return {asset:assetName,pct,storageCandles:n,warmupNeeded:min5s,tfKey,tfCandles:strategyTfCandles,contextTfKey,contextTfCandles:contextFast.prices.length,slowKey,slowCandles:tfSlow.prices.length,planCandles:{fast:pFast.prices.length,primary:pPrimary.prices.length,higher:pHigher.prices.length},ready,contextReady,streamLive,lastTickAgeSec,state};
  }

  function publishGridWarmupStatus() {
    const assets=multiScanAssets();
    if (!assets.length) return false;
    const rows=assets.map(gridWarmupState);
    lastIndicators.gridWarmup=rows;
    const summary=rows.map((r,i)=>`CH${i+1} ${r.asset} ${r.pct}%${r.streamLive?'':' WAIT'}`).join(' · ');
    const ready=rows.filter(r=>r.ready).length;
    // V24.1.125: when every channel is READY, never label the marquee
    // "GRID WARMUP" — the old code always sent the WARMUP prefix, so a
    // channel flipping from warmup→ready between the eval loop and this
    // recompute could print "GRID WARMUP" beside 100% values.
    if (ready === rows.length) {
      lastDebugReason=`GRID READY ${ready}/${rows.length} · ${summary}`;
      sendStatus(`✅ GRID READY ${ready}/${rows.length} · ${summary}`);
    } else {
      lastDebugReason=`GRID WARMUP ${ready}/${rows.length} ready · ${summary}`;
      sendStatus(`📡 GRID WARMUP ${ready}/${rows.length} · ${summary}`);
    }
    return true;
  }

  function queuedMultiTrade(assetName) {
    return pendingChartTrades.some(q => q.asset === assetName);
  }

  function enqueueMultiChartTrade(assetName, sig, tfKey, expiry) {
    if (!isRunning || !multiAssetMode || !assetName || !sig?.dir) return false;
    if (!slotForAsset(assetName)) return false;
    if (!canOpenAnotherTrade(assetName) || microPendingByAsset[assetName] || queuedMultiTrade(assetName)) return false;
    pendingChartTrades.push({asset:assetName,sig,tfKey,expiry,queuedAt:Date.now()});
    aiLog('FAVORITE_TRADE_QUEUED',{asset:assetName,dir:sig.dir,queueDepth:pendingChartTrades.length},false);
    processNextMultiChartTrade('enqueue');
    return true;
  }

  function dropExpiredMultiQueue() {
    const now=Date.now();
    for (let i=pendingChartTrades.length-1;i>=0;i--) {
      const q=pendingChartTrades[i];
      if (!slotForAsset(q.asset) || now-q.queuedAt>12000 || !canOpenAnotherTrade(q.asset)) pendingChartTrades.splice(i,1);
    }
  }

  function processNextMultiChartTrade(reason='advance') {
    if (!isRunning || !multiAssetMode || window.__poatStopped) return false;
    dropExpiredMultiQueue();
    if (pendingChartSwitchAsset) return false;
    const q=pendingChartTrades[0];
    if (!q) return false;
    const slotId=slotForAsset(q.asset);
    if (!slotId) {
      pendingChartTrades.shift();
      aiLog('GRID_TRADE_DROPPED_NOT_VISIBLE',{asset:q.asset,dir:q.sig?.dir||null,reason},true);
      return processNextMultiChartTrade('drop-not-visible');
    }
    pendingChartTrades.shift();
    sendStatus(`✅ GRID ${slotId} · ${q.asset} · checking entry · ${pendingChartTrades.length} queued`);
    return fireTrade(q.asset,q.sig,q.tfKey,q.expiry,true);
  }

  function checkSignals(force) {
    if (!isRunning || !botConfig) return;
    if (prewarmReplayActive) return;
    const nowCheck = Date.now();
    if (!force && nowCheck - lastSignalCheckAt < SIGNAL_SCAN_MS) return;
    lastSignalCheckAt = nowCheck;
    if (!multiAssetMode && Date.now() < cooldownUntil) {
      const left = Math.ceil((cooldownUntil - Date.now()) / 1000);
      if (left % 30 === 0 || left <= 5) {
        lastDebugReason = `Cooldown ${left}s · streak ${lossStreak}`;
        sendStatus(`⏸ Cooldown ${left}s · loss streak ${lossStreak}`);
      }
      bumpHoldCount(activeAsset, 'COOLDOWN'); // V24.1.135 C
      return;
    }
    if (checkRiskLimits()) return;

    // Sparse background control only. Qualified setup sampling happens after
    // the setup engine identifies an actual opportunity.
    if (multiAssetMode) {
      for (const name of multiScanAssets()) aiBackgroundLearnHeartbeat(name);
    } else if (activeAsset) {
      aiBackgroundLearnHeartbeat(activeAsset);
    }

    if (multiAssetMode) {
      // ── V24.1.124 FIXED FOUR-CHART GRID: scan all visible panels independently.
      // Each channel owns its cooldown, loss streak, indicators and pending state —
      // a losing, cooling-down or parked channel never pauses the other three.
      let anyWarmup = false, warmAsset = null, warmAct = null;
      const scanAssets = multiScanAssets();
      // V24.1.134 GRID CHART-SWITCH FIX: only ZERO visible panels holds. The old
      // <4 hard-return blocked every channel whenever a chart change left the
      // grid at 1-3 visible panels (slot mid-switch, briefly empty, or the same
      // asset in two slots deduping multiScanAssets to 3) — the user saw the
      // whole grid freeze while only the swapped chart needed to warm. Warmup is
      // per chart, so visible panels keep trading on their own schedule. One
      // notice per panel-count transition (lastGridPanelCount) keeps the popup
      // honest about a partial grid without spamming every 3s scan.
      if (scanAssets.length === 0) {
        lastGridPanelCount = 0;
        lastDebugReason = 'HOLD · no visible chart panels detected yet';
        sendStatus('🖥️ GRID · no visible chart panels detected yet…');
        bumpHoldCount('ALL', 'NO VISIBLE CHART PANELS'); // V24.1.135 C
        return;
      }
      if (scanAssets.length < 4 && lastGridPanelCount !== scanAssets.length) {
        lastGridPanelCount = scanAssets.length;
        const gridLive = `🖥️ GRID · ${scanAssets.length}/4 charts live · trading visible panels`;
        if (lastDebugReason !== gridLive) {
          lastDebugReason = gridLive;
          sendStatus(gridLive);
        }
      } else if (lastGridPanelCount !== scanAssets.length) {
        lastGridPanelCount = scanAssets.length;
      }
      const summaryLines = [];
      for (const assetName of scanAssets) {
        initAssetState(assetName);
        const ch = initChannelState(assetName);
        if (!canOpenAnotherTrade(assetName)) continue;

        // V24.1.124 PER-CHANNEL COOLDOWN: only this channel waits.
        if (Date.now() < ch.cooldownUntil) {
          const left = Math.ceil((ch.cooldownUntil - Date.now()) / 1000);
          ch.lastDebugReason = `Cooldown ${left}s · streak ${ch.lossStreak}${ch.cooldownReason ? ' · ' + ch.cooldownReason : ''}`;
          summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} ⏸${left}s`);
          bumpHoldCount(assetName, ch.cooldownReason || 'COOLDOWN'); // V24.1.135 C
          continue;
        }
        // V276 PRIMARY MOMENTUM CONFIRMATION: evaluate the recent market against its actual
        // payout-adjusted break-even WR. Rotation is advisory to chart selection only;
        // it never blocks an otherwise qualified trade when no replacement exists. Replacement stays unique >=92%.
        if (!assetTradePending[assetName] && !queuedMultiTrade(assetName) && performanceRotationNeeded(assetName)) {
          const h=marketHealth(assetName);
          const esc=performanceRotateEscalate(assetName,'watchdog');
          if(esc==='armed') {
            summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} ROTATE ${(h.wr*100).toFixed(0)}% < ${(h.requiredWr*100).toFixed(0)}%`);
            bumpHoldCount(assetName,'MARKET HEALTH · armed switch');
            continue;
          }
          if(esc==='no-target') {
            // V276: do NOT park or suppress this channel just because a replacement
            // is unavailable. Keep scanning/trading normally until a unique >=92%
            // replacement becomes available.
            summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} HEALTH ${(h.wr*100).toFixed(0)}% · no replacement`);
          }
        }
        // V24.1.132 / V276.1: GRID PAYOUT-FLOOR WATCHDOG — evaluated per channel on
        // every scan. A channel whose LIVE payout is under 90% auto-rotates its
        // chart to a unique ≥92% market even when no signal fires. While a switch is
        // pending, the channel does not trade the stale (sub-92%) chart. If no ≥92%
        // replacement exists, the channel keeps trading normally (never parked).
        {
          const pendSlot = slotForAsset(assetName);
          if (!assetTradePending[assetName] && !queuedMultiTrade(assetName) && pendSlot && slotSwitchPending[pendSlot]) {
            summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} ↻ pair switch pending…`);
            bumpHoldCount(assetName, 'WATCHDOG · pair switch pending'); // V24.1.135 C
            continue;
          }
          const wdPp = payoutPct(assetName);
          if (!assetTradePending[assetName] && !queuedMultiTrade(assetName) && wdPp > 0 && wdPp < AUTO_SWITCH_BELOW_PCT) {
            const esc = payoutFloorEscalate(assetName, wdPp, 'watchdog');
            if (esc === 'armed') {
              summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} SWITCHING ≥92%`);
              bumpHoldCount(assetName, 'WATCHDOG · armed switch'); // V24.1.135 C
              continue;
            }
            if (esc === 'no-target') {
              // V276.1: no unique >=92% replacement right now — keep scanning and
              // trading this channel normally instead of parking it.
              summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} ${wdPp.toFixed(0)}% <90% · no ≥92% pair`);
              bumpHoldCount(assetName, 'WATCHDOG · under 90% · no replacement'); // V24.1.135 C
            }
          }
        }
        // V24.1.124 PER-CHANNEL MAX LOSS STREAK (non-martingale only): park only
        // this channel for 30 minutes instead of stopping the whole bot.
        if (!botConfig?.martingale) {
          const maxLS = parseInt(botConfig?.maxLossStreak || 0);
          if (maxLS > 0 && ch.lossStreak >= maxLS) {
            ch.cooldownUntil = Date.now() + 30 * 60 * 1000;
            ch.cooldownReason = `parked ${ch.lossStreak}-loss streak`;
            ch.lastDebugReason = `PARKED ${ch.lossStreak}-loss streak · channel parked 30m`;
            sendStatus(`⛔ CH${gridChannelIndex(assetName)} ${assetName} parked 30m — ${ch.lossStreak} consecutive losses`);
            summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} PARKED`);
            bumpHoldCount(assetName, `MAX-LOSS-STREAK PARK · ${ch.lossStreak} losses`); // V24.1.135 C
            continue;
          }
        }

        const ev = evalAssetSignal(assetName);
        if (!ev || ev.skip) {
          const isWarmup = ev?.reason === 'warmup';
          if (isWarmup) {
            if (!anyWarmup) {
              anyWarmup = true;
              warmAsset = assetName;
              warmAct = getAsset(assetName);
            }
            // V24.1.134: THIS channel's warmup becomes its own summary line. The
            // old monolithic "GRID WARMUP x/4" marquee masked the fact that the
            // other READY/parked channels were fine while one swapped chart
            // warmed. Now a chart change shows "CH2 EURUSD Warmup 45%" while
            // CH1/CH3/CH4 keep their own READY/cooldown/park lines.
            const waRow = getAsset(assetName);
            const tickAgeSec = waRow?.lastTickSec != null ? Math.max(0, Math.floor(Date.now() / 1000) - Number(waRow.lastTickSec)) : null;
            const streamLive = tickAgeSec != null && tickAgeSec <= 15;
            summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} Warmup ${ev.warmupPct != null ? ev.warmupPct : '?'}%${streamLive ? '' : ' WAIT'}`);
          }
          const newReason = ev?.reason || ch.lastDebugReason;
          if (ev?.reason && ev.reason !== 'warmup' && ev.reason !== ch.lastDebugReason && !ev.reason.startsWith('Warmup')) {
            sendStatus(ev.reason.length > 110 ? ev.reason.slice(0, 107) + '…' : ev.reason);
          }
          ch.lastDebugReason = newReason;
          if (ev?.reason && ev.reason !== 'warmup') v225RecordDecision(assetName, ev.reason, 'HOLD');
          if (ev?.reason && ev.reason !== 'warmup') summaryLines.push(`CH${gridChannelIndex(assetName)} ${assetName} ${ev.reason.slice(0, 60)}`);
          continue;
        }

        const readyReason = `CHANNEL ${gridChannelIndex(assetName)} ${assetName} ${ev.sig.dir} READY · V238 ALL-TF PREDICTIVE`;
        if (ch.lastDebugReason !== readyReason) sendStatus(readyReason);
        ch.lastDebugReason = readyReason;
        v225RecordDecision(assetName, ev?.sig?.reason || readyReason, 'READY', ev.sig);
        summaryLines.push(readyReason);
        enqueueMultiChartTrade(ev.asset, ev.sig, ev.tfKey, ev.expiry);
      }
      if (anyWarmup) {
        // V24.1.134: keep the popup warmup rows fresh, but do NOT publish the
        // monolithic "GRID WARMUP x/4" marquee — the per-channel warmup lines
        // pushed above already live in the joined summary, so one warming chart
        // can no longer mask the other channels' READY/cooldown/park state.
        lastIndicators.gridWarmup = multiScanAssets().map(gridWarmupState);
      }
      if (summaryLines.length) {
        // V24.1.125: the old else-branch only stored lastDebugReason without
        // calling sendStatus, so once the last "GRID WARMUP" line was pushed
        // to the marquee and every channel then became READY, the floating
        // status bar stayed frozen on "GRID WARMUP" forever. Always push the
        // current summary line to the marquee (deduped by content) so the
        // status can never go stale.
        const line = summaryLines.join(' · ');
        if (lastDebugReason !== line) {
          lastDebugReason = line;
          sendStatus(line.length > 110 ? line.slice(0, 107) + '…' : line);
        }
      } else if (anyWarmup) {
        // Safety net: a channel is warming but produced no summary line (should
        // not happen — warmup lines are pushed above). Fall back to the row
        // publisher so lastIndicators.gridWarmup and the marquee stay fresh.
        publishGridWarmupStatus();
      }
    } else {
      // ── SINGLE ASSET: original behavior ──
      if (tradePending) return;
      if (!activeAsset) return;

      const ev = evalAssetSignal(activeAsset);
      if (!ev || ev.skip) {
        if (ev?.reason === 'warmup') {
          const act = getAsset(activeAsset);
          const expiry = parseInt(botConfig?.timeframe || 30, 10);
          const tfKey  = expiryToTF(expiry);
          const slowKey = expiryToSecondaryTF(expiry);
          const tfFast = getLiveTFView(act, tfKey);
          const tfSlow = getLiveTFView(act, slowKey);
          const min5sNeeded = v241WarmupTarget(act,(STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick']).minPrices || 40);
          const n = act.prices.length;
          // B15.10.8: warmup percentage has one meaning: closed 5s candles / 50.
          const storagePct = Math.min(100, (n / min5sNeeded) * 100);
          const pct = Math.floor(storagePct);
          const left = Math.max(0, min5sNeeded - n);
          lastDebugReason = `Warmup ${pct}% · 5s ${n}/${min5sNeeded} · ${tfKey} ${tfFast.prices.length}/8 · ${slowKey} ${tfSlow.prices.length}/8`;
          sendStatus(`📡 ${activeAsset} · Warmup ${pct}% · 5s ${n}/${min5sNeeded} · ${tfKey} ${tfFast.prices.length}/8 · ${slowKey} ${tfSlow.prices.length}/8`);
        } else if (ev?.reason && ev.reason !== 'no new candle') {
          lastDebugReason = ev.reason;
          // Show gate/HOLD reasons in status bar so user sees why bot isn't trading
          if (ev.reason.includes('HOLD') || ev.reason.includes('GATED') || ev.reason.includes('ABSTAIN') ||
              ev.reason.includes('LEARNING') || ev.reason.includes('BLOCKED') || ev.reason.includes('AI WAIT') ||
              ev.reason.includes('INDICATOR CONTEXT') || ev.reason.includes('SKIP')) {
            sendStatus(ev.reason.length > 110 ? ev.reason.slice(0, 107) + '...' : ev.reason);
          }
        }
        return;
      }

      fireTrade(ev.asset, ev.sig, ev.tfKey, ev.expiry);
    }
  }

  // V24.1.91 — PAYOUT-AWARE MULTI-ASSET CHART LOCK
  function payoutPct(assetName) {
    let v = Number(assetPayouts[assetName]);
    if (!isFinite(v)) return 0;
    if (v > 0 && v <= 1.5) v *= 100;
    return v;
  }

  function isMultiPayoutEligible(assetName) {
    if (!assetName) return false;
    return payoutPct(assetName) + 1e-9 >= MULTI_MIN_PAYOUT;
  }

  function bestMultiPayoutAsset() {
    const rows = [...knownAssets]
      .filter(isMultiPayoutEligible)
      .map(name => ({name, payout:payoutPct(name), candles:(assetData[name]?.prices?.length||0)}))
      .sort((a,b) => (b.payout-a.payout) || (b.candles-a.candles) || a.name.localeCompare(b.name));
    return rows.length ? rows[0].name : '';
  }

  function requestPocketOptionChartAsset(assetName, reason='fixed-grid') {
    // V121: intentionally disabled. Fixed-grid multi mode never changes a chart.
    return !!slotForAsset(assetName);
  }

  function maintainMultiPayoutChart() {
    // V121..V24.1.131: no-op. Payout was handled by the selective-edge gate;
    // chart assignment remained exactly as the user arranged the four visible
    // panels. V24.1.132 replaces the dead no-op with the live grid payout-floor
    // auto-switch below (payoutFloorEscalate is invoked from fireTrade's veto
    // branch and from checkSignals' per-channel watchdog).
    return;
  }

  // ── V24.1.132: GRID PAYOUT-FLOOR AUTO-SWITCH HELPERS ──────────────────
  // payoutSwitchCandidate(fromAsset): best ≥92% market to rotate a sub-80% slot
  // to. Excludes the current asset, any asset already occupying a visible slot
  // (or an in-flight switch target), broker-disabled markets, and any market this
  // session already switched away from or failed to reach within
  // PAYOUT_SWITCH_AWAY_TTL_MS (no bounce-back / no flapping against a favorite
  // the bridge cannot select). Ranks by payout, then candle warmth, then name.
  function payoutSwitchCandidate(fromAsset) {
    // B15.10.25: payout-driven chart switching disabled. Markets are manual.
    aiLog('PAYOUT_SWITCH_DISABLED_MANUAL_MARKETS',{args:Array.from(arguments)},false);
    return false;

    const now = Date.now();
    const occupied = new Set(Object.values(visibleChartSlots).filter(Boolean));
    for (const sId of Object.keys(slotSwitchPending)) {
      const p = slotSwitchPending[sId];
      if (p && p.toAsset) occupied.add(p.toAsset);
    }
    const pool = knownAssets; // V276: user requested ANY known pair, not favorites-only
    const rows = [];
    for (const name of pool) {
      if (!name || name === fromAsset || occupied.has(name)) continue;
      if (assetAvailable[name] === false) continue;
      const pay = payoutPct(name);
      if (!(pay + 1e-9 >= AUTO_SWITCH_TARGET_PCT)) continue;                      // V276: must be >=92%
      if (now - (payoutSwitchAwayAt[name] || 0) < PAYOUT_SWITCH_AWAY_TTL_MS) continue; // just left this market
      if (now - (payoutSwitchFailAt[name] || 0) < PAYOUT_SWITCH_AWAY_TTL_MS) continue; // just failed to reach it
      rows.push({ name, pay, candles: (assetData[name]?.prices?.length || 0) });
    }
    rows.sort((a, b) => (b.pay - a.pay) || (b.candles - a.candles) || a.name.localeCompare(b.name));
    return rows.length ? rows[0].name : '';
  }

  // payoutFloorEscalate(assetName, pp, via): attempt to rotate a grid channel whose
  // live payout is below the configured floor (B15.10.9: under 90%).
  //   'armed'  → SWITCH_ASSET_SLOT posted to the bridge; the channel stays out of
  //              the trade path until CHART_SLOTS confirms the new chart (or times out).
  //   'no-target' → B15.10.9: no eligible ≥92% market exists right now; the channel
  //              is NOT parked — it keeps trading normally. A sub-92% payout is a
  //              rotate-when-possible rule, never a reason to freeze a chart.
  //   ''       → not multi mode / asset not on a visible slot / per-slot 5-minute
  //              debounce active (slot already switched recently).
  // V24.1.133: the channel is cooldown-parked for the user-cooldown veto park
  // (vetoParkSec — cooldownAfterLoss / autoCooldownOn ladder, floored 15s) in the
  // armed AND parked cases so re-entries can never double-arm or double-park the
  // same slot. (V24.1.131's fixed 60s PAYOUT_FLOOR_PARK_MS no longer exists.)
  function payoutFloorEscalate(assetName, pp, via, forcedSlotId='') {
    // B15.10.9 AUTO HIGH-PAYOUT GRID: chart rotation is enabled again.
    // Keep a slot while payout is >=90%. If it falls below 90%, rotate that
    // slot to a unique available >=92% market. Open/pending trades are protected
    // by the caller; the replacement then follows the normal 50-candle warmup.
    // V276: payout affects CHART SELECTION only. It does not veto a qualified trade.
    if (!(Number(pp) > 0) || Number(pp) >= AUTO_SWITCH_BELOW_PCT) return '';
    // B15.10.11: do not depend on the popup multiAssetMode flag for an already-visible grid.
    // If Pocket Option has published chart slots, those slots are authoritative.
    if (!multiAssetMode && Object.keys(visibleChartSlots).length < 2) return '';
    const slotId = forcedSlotId || slotForAsset(assetName);
    if (!slotId || slotSwitchPending[slotId]) return '';
    const now = Date.now();
    if (now - (slotLastSwitchAt[slotId] || 0) < PAYOUT_SWITCH_DEBOUNCE_MS) return '';
    const target = payoutSwitchCandidate(assetName);
    if (!target) {
      // B15.10.10: knownAssets only contains markets the stream has already exposed.
      // That meant an 87% visible chart could have a 92% market in Pocket Option's
      // picker and still do nothing. Fall back to scanning THIS chart's live asset
      // menu and let the bridge click a visible >=92% option directly.
      slotLastSwitchAt[slotId] = now;
      payoutSwitchAwayAt[assetName] = now;
      slotSwitchPending[slotId] = {fromAsset:assetName,toAsset:'__AUTO_92__',at:now,autoMenu:true};
      try {
        window.postMessage({_poatCmd:true,type:'SWITCH_SLOT_HIGH_PAYOUT',slotId,minPayout:AUTO_SWITCH_TARGET_PCT,fromAsset:assetName,excludedAssets:[...new Set([...Object.values(visibleChartSlots).filter(Boolean),...Object.values(slotSwitchPending).map(p=>p&&p.toAsset).filter(x=>x&&x!=='__AUTO_92__')])]}, '*');
        aiLog('GRID_PAYOUT_SWITCH_MENU_SCAN',{slotId,fromAsset:assetName,fromPayout:Number(pp),need:AUTO_SWITCH_TARGET_PCT,via},true);
        sendStatus(`🔎 ${slotId} ${assetName} ${Number(pp).toFixed(0)}% · finding ≥${AUTO_SWITCH_TARGET_PCT}% market…`);
        return 'armed';
      } catch(e) {
        delete slotSwitchPending[slotId];
        aiLog('GRID_PAYOUT_SWITCH_MENU_ERROR',{slotId,fromAsset:assetName,error:String(e?.message||e)},true);
        return '';
      }
    }
    // Candidate selection already excludes every asset currently occupying any of the 4 slots
    // plus every in-flight target, so duplicate chart pairs cannot be selected.
    slotLastSwitchAt[slotId] = now;
    payoutSwitchAwayAt[assetName] = now;
    slotSwitchPending[slotId] = {fromAsset:assetName,toAsset:target,at:now};
    try {
      window.postMessage({_poatCmd:true,type:'SWITCH_ASSET_SLOT',asset:target,slotId}, '*');
      aiLog('GRID_PAYOUT_SWITCH_ARMED',{slotId,fromAsset:assetName,fromPayout:Number(pp),toAsset:target,toPayout:payoutPct(target),via},true);
      sendStatus(`🔄 ${slotId} ${assetName} ${Number(pp).toFixed(0)}% → ${target} ${payoutPct(target).toFixed(0)}%`);
      return 'armed';
    } catch(e) {
      delete slotSwitchPending[slotId];
      payoutSwitchFailAt[target] = now;
      aiLog('GRID_PAYOUT_SWITCH_ERROR',{slotId,fromAsset:assetName,toAsset:target,error:String(e?.message||e)},true);
      return '';
    }
  }


  // B15.10.11: independent live payout watchdog. The old watchdog lived inside
  // checkSignals(), so chart replacement could silently never arm when a slot did
  // not enter that evaluation path. Drive payout replacement directly from the
  // bridge-published visible chart slots every 2 seconds instead.
  setInterval(() => {
    if (!isRunning) return;
    try {
      for (const [slotId, assetName] of Object.entries(visibleChartSlots)) {
        if (!slotId || !assetName) continue;
        const pp = payoutPct(assetName);
        if (!(pp > 0) || pp >= AUTO_SWITCH_BELOW_PCT) continue;
        if (slotSwitchPending[slotId]) continue;
        if (assetTradePending[assetName] || queuedMultiTrade(assetName) || openTradeCount(assetName) > 0) continue;
        payoutFloorEscalate(assetName, pp, 'live-slot-watchdog', slotId);
      }
    } catch (e) {
      aiLog('GRID_PAYOUT_WATCHDOG_ERROR',{error:String(e?.message||e)},false);
    }
  }, 2000);


  // V276: non-blocking market-health rotation. Never parks/starves a chart solely
  // because of a short rolling sample. After 12+ trades / 6+ losses, a market below
  // its CURRENT payout-adjusted break-even WR becomes eligible for rotation to a
  // unique >=92% market. If no replacement is available, normal signal scanning
  // CONTINUES; market health never parks the channel. Entry/scoring logic is untouched.
  function marketHealth(assetName) {
    const ch=initChannelState(assetName);
    const r=Array.isArray(ch.recentResults)?ch.recentResults.slice(-PERF_ROTATE_WINDOW):[];
    const n=r.length, wins=r.reduce((a,b)=>a+(b===1?1:0),0), losses=n-wins;
    const pp=Math.max(0,Number(payoutPct(assetName))||0);
    const payoutFrac=pp>0?pp/100:(AUTO_SWITCH_TARGET_PCT/100);
    const breakEvenWr=1/(1+payoutFrac);
    const requiredWr=Math.min(0.70,breakEvenWr+PERF_ROTATE_EDGE_BUFFER);
    const wr=n?wins/n:1;
    return {n,wins,losses,wr,payout:pp,breakEvenWr,requiredWr,edge:wr-breakEvenWr};
  }
  function performanceRotationNeeded(assetName) {
    const h=marketHealth(assetName);
    return h.n>=PERF_ROTATE_MIN_TRADES && h.losses>=PERF_ROTATE_MIN_LOSSES && h.wr<h.requiredWr;
  }
  function performanceRotateEscalate(assetName, via='market-health') {
    // B15.5 FIXED GRID: market-health may be logged, but it cannot rotate charts.
    return 'no-target';
    if(!multiAssetMode || !performanceRotationNeeded(assetName)) return '';
    const slotId=slotForAsset(assetName);
    if(!slotId || slotSwitchPending[slotId]) return '';
    const now=Date.now();
    if(now-(slotLastSwitchAt[slotId]||0)<PAYOUT_SWITCH_DEBOUNCE_MS) return '';
    const h=marketHealth(assetName);
    const target=payoutSwitchCandidate(assetName);
    if(!target) {
      aiLog('GRID_MARKET_HEALTH_NO_TARGET',{slotId,fromAsset:assetName,recent:h,needPayout:AUTO_SWITCH_TARGET_PCT},false);
      return 'no-target';
    }
    slotLastSwitchAt[slotId]=now;
    payoutSwitchAwayAt[assetName]=now + (PERF_ROTATE_AWAY_TTL_MS-PAYOUT_SWITCH_AWAY_TTL_MS);
    slotSwitchPending[slotId]={fromAsset:assetName,toAsset:target,at:now,reason:'market-health'};
    try {
      window.postMessage({_poatCmd:true,type:'SWITCH_ASSET_SLOT',asset:target,slotId},'*');
      aiLog('GRID_MARKET_HEALTH_ARMED',{slotId,fromAsset:assetName,recent:h,toAsset:target,toPayout:payoutPct(target),via},true);
      sendStatus(`🛡️ ${slotId} ${assetName} ${(h.wr*100).toFixed(0)}% < target ${(h.requiredWr*100).toFixed(0)}% → ${target} ${payoutPct(target).toFixed(0)}%`);
      return 'armed';
    } catch(e) {
      delete slotSwitchPending[slotId]; payoutSwitchFailAt[target]=now;
      aiLog('GRID_MARKET_HEALTH_ERROR',{slotId,fromAsset:assetName,toAsset:target,error:String(e?.message||e)},true);
      return '';
    }
  }

  // ════════════════════════════════════════════════════════════
  //  BRIDGE LISTENER
  // ════════════════════════════════════════════════════════════
  window.addEventListener('message', (ev) => {
    if (ev.source !== window || !ev.data || !ev.data._poat) return;
    const msg = ev.data;

    if (msg.type === 'PREWARM_RESET') {
      const asset=String(msg.asset||'').trim();
      if (!asset) return;
      const a=getAsset(asset);
      // B15.10.27: historical warmup replaces partial live startup state.
      // A full hour+ of broker buckets is replayed through the normal STREAM path.
      a.prices=[]; a.rates={}; a.tf={}; a.lastClosed=-1; a.lastBucket=null;
      a.newCandle=false; a.lastPrice=0; a.lastTickSec=0;
      const wanted=Number(msg.bucketCount)||200;
      a.__historyBackfill={buckets:0,from:Number(msg.firstBucket)||0,to:Number(msg.lastBucket)||0,at:Date.now(),source:`exact-${wanted}-consecutive`};
      sendStatus(`📚 ${asset} · loading ${wanted} consecutive previous real 5s candles…`);
      return;
    }

    if (msg.type === 'PREWARM_BEGIN') {
      prewarmReplayActive = true;
      if (msg.asset) prewarmReplayAssets.add(String(msg.asset));
      sendStatus(`📚 ${msg.asset||'market'} · replaying previous candles through normal live pipeline…`);
      return;
    }
    if (msg.type === 'PREWARM_DONE') {
      if (msg.asset) prewarmReplayAssets.delete(String(msg.asset));
      if (!prewarmReplayAssets.size) prewarmReplayActive = false;
      const a = msg.asset ? getAsset(String(msg.asset)) : null;
      if (a) {
        // B15.10.27: the last requested historical 5s bucket is already complete,
        // but STREAM normally closes a bucket only when the next bucket arrives.
        // Close that final historical bucket now so all requested history is usable.
        const lastB=Number(msg.lastBucket);
        if(Number.isFinite(lastB) && lastB>0) tryCloseBucket(a,lastB,false);
        const n=a.prices.length, wanted=Number(msg.bucketCount)||200;
        a.__historyBackfill={buckets:n,from:Number(msg.firstBucket)||0,to:lastB||0,at:Date.now(),source:`exact-${wanted}-consecutive`};
        if(n>=wanted-1) sendStatus(`📚 ${msg.asset} · history ready ${n}/${wanted} real 5s candles · 60s strategies prewarmed`);
        else sendStatus(`⚠️ ${msg.asset} · history replay produced ${n}/${wanted} · requesting/using available chart history`);
      }
      return;
    }

    if (msg.type === 'STREAM') {
      if (!Array.isArray(msg.ticks)) return;
      // 1.1.28: Pocket Option can stream prices before it republishes updateHistory/
      // CHART_ASSET. For read-only charts, bind the first real streaming symbol
      // immediately instead of leaving activeAsset blank forever.
      if (!isRunning && !activeAsset && Array.isArray(msg.ticks)) {
        const firstLive=msg.ticks.find(t=>t&&t.asset&&Number(t.price)>0);
        if(firstLive){
          activeAsset=String(firstLive.asset);
          chartSelectedAsset=activeAsset;
          chartSelectedAt=Date.now();
          knownAssets.add(activeAsset);
          try{sendStatus(`📈 ${activeAsset} · live market stream detected`);}catch(_){}
        }
      }
      msg.ticks.forEach(tick => {
        if (typeof tick.asset !== 'string' || !tick.asset || !Number.isFinite(Number(tick.price)) || Number(tick.price) <= 0) return;

        // B15.10.24: In 4-chart mode, Pocket Option can continue publishing
        // background/stale market streams after a chart has been replaced.
        // Those streams must NOT feed candle/TF state, warmup, AI context, or
        // the permanent raw-5s archive. Only the four CHART_SLOTS markets are
        // authoritative once the visible grid has been discovered.
        if (multiAssetMode && Object.keys(visibleChartSlots).length > 0) {
          const visibleNow = new Set(Object.values(visibleChartSlots).filter(Boolean));
          if (!visibleNow.has(String(tick.asset))) return;
        }

        const a = getAsset(tick.asset);
        if (guardRejectTickScale(tick.asset, tick.price, a)) return; // V24.1.131 data-integrity scale guard
        lastTickPrice[tick.asset] = tick.price;   // used for entry/exit price snapshots
        // Shadow-label all requested expirations using observed future ticks only.
        try {
          const c=globalThis.KaosExpiryCollector;
          if(c && c.tick(tick.asset,Number(tick.price),Date.now())){
            const rows=c.drain();
            if(rows.length) chrome.runtime.sendMessage({type:'KAOS_EXPIRY_LABEL_BATCH',samples:rows}).catch(()=>{});
          }
        } catch (_) {}

        // V208: micro timing must use local arrival time. Broker timestamps may be
        // second-quantized or slightly clock-skewed, which made 1s/2s/3s anchors
        // look sparse/not-distinct even while live ticks were flowing.
        microRecordTick(tick.asset, tick.price, Date.now());

        {
          // ── 5s STORAGE bucket (time normalized sec/ms) ──
          const tSec = tick.time ? toEpochSec(tick.time) : Math.floor(Date.now() / 1000);
          a.lastPrice = tick.price;
          a.lastTickSec = tSec;
          const b = BUCKET_SEC * Math.floor(tSec / BUCKET_SEC);

          // B15.10.31 — REAL 1s INTRABAR VIEW INSIDE EACH 5s STORAGE CANDLE.
          // Uses actual STREAM ticks only: no interpolation and no synthetic 1s prices.
          // Each slot stores first/high/low/last for broker-second offsets 0..4.
          if(!a.intra1s) a.intra1s={bucket:null,slots:{},history:[]};
          if(a.intra1s.bucket!==b){
            if(a.intra1s.bucket!==null){
              a.intra1s.history.push({bucket:a.intra1s.bucket,slots:a.intra1s.slots});
              if(a.intra1s.history.length>240) a.intra1s.history.shift();
            }
            a.intra1s.bucket=b; a.intra1s.slots={};
          }
          const secSlot=Math.max(0,Math.min(4,Math.floor(tSec-b)));
          const q=a.intra1s.slots[secSlot];
          if(!q) a.intra1s.slots[secSlot]={open:tick.price,high:tick.price,low:tick.price,close:tick.price,ticks:1,tSec};
          else { q.high=Math.max(q.high,tick.price); q.low=Math.min(q.low,tick.price); q.close=tick.price; q.ticks=(q.ticks||0)+1; q.tSec=tSec; }

          if (!a.rates[b]) a.rates[b] = [tick.price, tick.price, tick.price, tick.price, tSec];
          else {
            if (tick.price > a.rates[b][1]) a.rates[b][1] = tick.price;
            if (tick.price < a.rates[b][2]) a.rates[b][2] = tick.price;
            a.rates[b][3] = tick.price; a.rates[b][4] = tSec;
          }

          // ── Closed-candle push + TF roll-up (carry empty gaps) ──
          if (a.lastBucket === null) {
            a.lastBucket = b;
            if (a.lastClosed < 0) a.lastClosed = b - BUCKET_SEC;
          } else if (b > a.lastBucket) {
            closeThrough(a, b);
            a.lastBucket = b;
          }
          // b === lastBucket → same open candle
          // b < lastBucket  → stale tick kept in rates only
        }

        // ── Active-asset picking (most ticks, with hysteresis) ──
        // Background streams may only choose the active asset in MULTI mode.
        knownAssets.add(tick.asset);
        if (multiAssetMode) {
        if (!KEY_MARKETS[tick.asset]) {
          KEY_MARKETS[tick.asset] = Object.keys(KEY_MARKETS).length / Math.max(1, Object.keys(KEY_MARKETS).length + 1);
        }
        assetTickCount[tick.asset] = (assetTickCount[tick.asset] || 0) + 1;
        const nowMs = Date.now();
        if (!window.__poatBurst) window.__poatBurst = {};
        if (!window.__poatBurst[tick.asset]) window.__poatBurst[tick.asset] = { count: 0, since: nowMs };
        if (nowMs - window.__poatBurst[tick.asset].since < 2000) {
          window.__poatBurst[tick.asset].count++;
        } else {
          window.__poatBurst[tick.asset] = { count: 1, since: nowMs };
        }
        if (window.__poatBurst[tick.asset].count >= 8) {
          if (activeAsset !== tick.asset) {
            activeAsset = tick.asset;
            Object.keys(assetTickCount).forEach(k => {
              if (k !== tick.asset) assetTickCount[k] = Math.floor(assetTickCount[k] * 0.3);
            });
          }
          window.__poatBurst[tick.asset] = { count: 0, since: nowMs };
        } else {
          const thisCount   = assetTickCount[tick.asset];
          const activeCount = assetTickCount[activeAsset] || 0;
          if (!activeAsset || thisCount > activeCount * 1.4 + 10) {
            activeAsset = tick.asset;
          }
        }
        } else if (sessionLockedAsset) {
          activeAsset = sessionLockedAsset;
        }
        if (microPendingByAsset[tick.asset]) processMicroConfirmation(tick.asset,false);
      });
      if (!multiAssetMode && sessionLockedAsset) activeAsset = sessionLockedAsset;
      if (isRunning && (multiAssetMode || !tradePending)) checkSignals();
    }

    if (msg.type === 'CHART_SENTIMENT') {
      const rows=Array.isArray(msg.rows)?msg.rows:[];
      for(const row of rows){const asset=String(row?.asset||'').trim(),buy=Number(row?.buy),sell=Number(row?.sell);if(asset&&Number.isFinite(buy)&&Number.isFinite(sell))v287State.sentimentByAsset[asset]={buy,sell,source:String(row?.source||'bridge-panel'),t:Number(row?.t)||Date.now(),slotId:row?.slotId||''};}
    }

    if (msg.type === 'CHART_SLOTS') {
      // B32.6.1: do NOT erase slotSwitchPending here. Auto-rotation confirmation below
      // needs the reservation to survive the bridge's CHART_SLOTS publication; clearing
      // it here reopened duplicate/race behavior and made confirmations impossible.
      pendingChartSwitchAsset=''; pendingChartSwitchSlot=''; pendingChartSwitchAt=0;
      const rows=Array.isArray(msg.slots)?msg.slots:[];
      const priorSlots={...visibleChartSlots};
      for (const k of Object.keys(visibleChartSlots)) delete visibleChartSlots[k];
      for (const row of rows) {
        const slotId=String(row?.slotId||'').trim(), a=String(row?.asset||'').trim();
        if (!slotId||!a) continue;
        visibleChartSlots[slotId]=a;
        knownAssets.add(a);
      }
      for (const [slotId,oldAsset] of Object.entries(priorSlots)) {
        const newAsset=String(visibleChartSlots[slotId]||'');
        if(!oldAsset||!newAsset||oldAsset===newAsset)continue;
        for(let i=pendingChartTrades.length-1;i>=0;i--){if(pendingChartTrades[i]?.asset===oldAsset)pendingChartTrades.splice(i,1);}
        if(microPendingByAsset[oldAsset])clearMicroPending(oldAsset,'visible chart slot changed');
        delete lastIndicatorCtx[oldAsset];
        const oldState=assetData[oldAsset];
        if(oldState){
          oldState.lastBucket=null;
          oldState.newCandle=false;
        }
        const oldCh=initChannelState(oldAsset); if(oldCh)oldCh.lastDebugReason=`CHART CHANGED · ${slotId} now ${newAsset}`;
        initAssetState(newAsset); aiLog('GRID_MANUAL_CHART_CHANGE',{slotId,fromAsset:oldAsset,toAsset:newAsset},true);
      }
      v219SyncVisionAssets();
      if (multiAssetMode && rows.length) {
        for (const a of [...new Set(rows.map(r=>String(r.asset||'')).filter(Boolean))]) initAssetState(a);
        sendStatus(`🖥️ GRID · ${rows.length}/4 charts live · ${[...new Set(rows.map(r=>r.asset))].join(' · ')}`);
        if (rows.length>=4) setTimeout(()=>publishGridWarmupStatus(),25);
      }
      if (pendingChartSwitchAsset) {
        const arrived=slotForAsset(pendingChartSwitchAsset);
        if (arrived && (!pendingChartSwitchSlot || arrived===pendingChartSwitchSlot)) {
          const target=pendingChartSwitchAsset;
          pendingChartSwitchAsset=''; pendingChartSwitchSlot=''; pendingChartSwitchAt=0;
          aiLog('FAVORITE_GRID_SWITCH_CONFIRMED',{asset:target,slotId:arrived},false);
          setTimeout(()=>processNextMultiChartTrade('grid-confirmed'),80);
        } else if (Date.now()-pendingChartSwitchAt>6000) {
          aiLog('FAVORITE_GRID_SWITCH_TIMEOUT',{asset:pendingChartSwitchAsset,slotId:pendingChartSwitchSlot},true);
          pendingChartSwitchAsset=''; pendingChartSwitchSlot=''; pendingChartSwitchAt=0;
          setTimeout(()=>processNextMultiChartTrade('grid-timeout'),100);
        }
      }
      // ── V24.1.132: confirm or time out armed payout-floor chart switches ──
      if (multiAssetMode) {
        const pNow = Date.now();
        for (const pSlotId of Object.keys(slotSwitchPending)) {
          const pend = slotSwitchPending[pSlotId];
          if (!pend) { delete slotSwitchPending[pSlotId]; continue; }
          const slotNo = /slot-(\d+)/.exec(pSlotId);
          const chTag = slotNo ? `CH${slotNo[1]}` : pSlotId;
          const landedAsset = visibleChartSlots[pSlotId] || '';
          const dynamicMenuLanded = !!(pend.autoMenu && landedAsset && landedAsset !== pend.fromAsset);
          if (visibleChartSlots[pSlotId] === pend.toAsset || dynamicMenuLanded) {
            if (dynamicMenuLanded) pend.toAsset = landedAsset;
            // Bridge republishes CHART_SLOTS ~350ms after the click; the slot now
            // shows the ≥92% target → switch confirmed. The channel stays parked
            // while the fresh chart warms, then resumes under its own rules.
            delete slotSwitchPending[pSlotId];
            const payTo = payoutPct(pend.toAsset);
            aiLog('GRID_SLOT_SWITCH_CONFIRMED', { slotId: pSlotId, fromAsset: pend.fromAsset, toAsset: pend.toAsset, payout: payTo }, true);
            sendStatus(`✅ ${chTag} chart now ${pend.toAsset} (${payTo.toFixed(2)}%) · warming up…`);
          } else if (pNow - pend.at > PAYOUT_SWITCH_TIMEOUT_MS) {
            // No confirmation within 8s: the target chart never landed. Forget the
            // pending switch and remember the target as failed so the next attempt
            // (after this channel's floor-park) picks a different ≥92% market.
            delete slotSwitchPending[pSlotId];
            payoutSwitchFailAt[pend.toAsset] = pNow;
            aiLog('GRID_SLOT_SWITCH_TIMEOUT', { slotId: pSlotId, fromAsset: pend.fromAsset, toAsset: pend.toAsset }, true);
            sendStatus(`⚠ ${chTag} switch to ${pend.toAsset} timed out · parked channel`);
          }
        }
      }
    }

    if (msg.type === 'CHART_ASSET') {
      const a = String(msg.asset || '').trim();
      if (a) {
        chartSelectedAsset = a;
        chartSelectedAt = Date.now();
        knownAssets.add(a);
        if (!multiAssetMode && isRunning && !sessionLockedAsset) {
          sessionLockedAsset = a;
          activeAsset = a;
          lastStartedAsset = a;
          sendStatus(`📡 ${a} · chart locked · warming up…`);
          aiLog('SINGLE_ASSET_LOCK_ESTABLISHED',{asset:a,source:'bridge-chart-state'},true);
        } else if (!multiAssetMode && !isRunning) {
          activeAsset = a;
        }
      }
    }

    if (msg.type === 'HISTORY_BACKFILL') {
      const asset=String(msg.asset||'').trim(), records=Array.isArray(msg.records)?msg.records:[];
      if (!asset || records.length<5) return;
      try {
        const a=getAsset(asset), nowBucket=BUCKET_SEC*Math.floor(Date.now()/1000/BUCKET_SEC);
        const buckets=new Map();
        const normSec=(v)=>toEpochSec(v);
        for(const r of records){
          const t=normSec(r?.time), b=BUCKET_SEC*Math.floor(t/BUCKET_SEC);
          if(!Number.isFinite(b)||b<=0||b>=nowBucket) continue; // completed history only
          let o,h,l,c;
          if(r?.kind==='ohlc') { o=Number(r.open);h=Number(r.high);l=Number(r.low);c=Number(r.close); }
          else { const px=Number(r?.price);o=h=l=c=px; }
          if(![o,h,l,c].every(Number.isFinite)||Math.min(o,h,l,c)<=0||h<Math.max(o,c)||l>Math.min(o,c)) continue;
          const q=buckets.get(b);
          if(!q) buckets.set(b,[o,h,l,c,t]);
          else { q[1]=Math.max(q[1],h);q[2]=Math.min(q[2],l);q[3]=c;q[4]=Math.max(q[4],t); }
        }
        const keys=[...buckets.keys()].sort((x,y)=>x-y);
        // B32: archive only REAL historical buckets immediately. Never archive synthetic gap fills.
        for(const hb of keys){const hq=buckets.get(hb);if(hq){marketCandleArchive(asset,hb,hq);raw5Archive(asset,hb,hq);}}
        marketCandlePersist(true); raw5Persist(true);
        if(keys.length>=12 && (a.prices.length<keys.length || a.prices.length<180)) {
          const liveLast=a.lastPrice||0, liveTick=a.lastTickSec||0;
          a.prices=[];a.rates={};a.tf={};a.lastClosed=-1;a.lastBucket=null;a.newCandle=false;
          let prevClose=0, first=keys[0], last=keys[keys.length-1];
          // Preserve actual broker gaps; never invent flat candles or iterate a huge gap.
          for(const b of keys){
            const q=buckets.get(b);
            a.rates[b]=q; a.prices.push(q[3]); feedTF(a,b,q); a.lastClosed=b; prevClose=q[3];
          }
          if(a.prices.length>MAX_PRICES) a.prices=a.prices.slice(-MAX_PRICES);
          a.lastBucket=last+BUCKET_SEC; a.lastPrice=liveLast||prevClose; a.lastTickSec=liveTick||last;
          a.newCandle=true; knownAssets.add(asset);
          const backfillSource=String(msg.source||'Pocket Option chart history');
          a.__historyBackfill={buckets:a.prices.length,from:first,to:last,at:Date.now(),source:backfillSource};
          sendStatus(`📚 ${asset} · ${backfillSource==='visible-chart-data'?'visual chart fallback':'history'} backfilled ${a.prices.length} aligned 5s candles · verifying live stream…`);
          aiLog('HISTORY_BACKFILL_APPLIED',{asset,buckets:a.prices.length,from:first,to:last,source:backfillSource},true);
          // B32.20.5: history is now immediately authoritative for the live micro engine.
          // Clear per-candle de-duplication so the next evaluation cannot remain stuck on
          // a pre-backfill 8/24 or 23/24 snapshot.
          try{if(v290BBPlusSignal&&v290BBPlusSignal._seen)delete v290BBPlusSignal._seen[asset];}catch(_){}
          try{if(typeof C7B_MICRO_STATE==='object'&&C7B_MICRO_STATE)delete C7B_MICRO_STATE[asset];}catch(_){}
          try{const cv=c7bStrategyRows(asset);aiLog('MICRO_HISTORY_RESYNC',{asset,source:cv.source,counts:cv.counts,usable:cv.rows.length},true);}catch(_){}
        }
      } catch(e) { try{aiLog('HISTORY_BACKFILL_ERROR',{asset,error:String(e?.message||e)},true);}catch(_){} }
    }

    if (msg.type === 'HISTORY') {
      if (!msg.asset || !Array.isArray(msg.prices) || msg.prices.length < 5) return;
      chartSelectedAsset = String(msg.asset);
      chartSelectedAt = Date.now();
      if (!multiAssetMode) {
        if (isRunning && !sessionLockedAsset) {
          // START can arrive before Pocket Option sends/has re-sent history.
          // The first authoritative HISTORY message establishes the permanent
          // single-asset lock so warmup can begin without trusting background ticks.
          sessionLockedAsset = chartSelectedAsset;
          activeAsset = sessionLockedAsset;
          lastStartedAsset = sessionLockedAsset;
          aiLog('SINGLE_ASSET_LOCK_ESTABLISHED',{asset:sessionLockedAsset,source:'history'},true);
        } else if (isRunning && sessionLockedAsset) {
          // Keep the run bound to its START asset. If the user visibly changes
          // the chart mid-run, execution will block until restart rather than
          // silently following a background/history stream.
          activeAsset = sessionLockedAsset;
          if (chartSelectedAsset !== sessionLockedAsset) {
            aiLog('VISIBLE_CHART_CHANGED_DURING_SINGLE_RUN',{lockedAsset:sessionLockedAsset,chartAsset:chartSelectedAsset},true);
          }
        } else {
          const priorAsset = activeAsset;
          activeAsset = chartSelectedAsset;
          if (priorAsset && priorAsset !== activeAsset) {
            Object.keys(assetTickCount).forEach(k => delete assetTickCount[k]);
            if (window.__poatBurst) Object.keys(window.__poatBurst).forEach(k => delete window.__poatBurst[k]);
            delete lastIndicatorCtx[activeAsset];
            const sw = assetData[activeAsset];
            if (sw) { delete sw.__priceVisionState; delete sw.__revState; delete sw.__fastStructureState; }
            aiLog('MARKET_SWITCH', {from:priorAsset,to:activeAsset,source:'chart-history'}, true);
          }
        }
      }
      const a = getAsset(msg.asset);
      knownAssets.add(msg.asset);
      // Apply if history is longer OR live is still warming (<40)
      const needSeed = a.prices.length < msg.prices.length || a.prices.length < 40;
      if (needSeed) {
        const hist = msg.prices.map(x => parseFloat(x)).filter(x => isFinite(x) && x > 0);
        if (hist.length < 5) return;
        if (guardRejectHistoryScale(msg.asset, hist, a)) return; // V24.1.131 data-integrity scale guard: skip mismatched seed/merge
        const lastHist = hist[hist.length - 1];
        const lastLive = a.prices.length ? a.prices[a.prices.length - 1] : null;
        if (lastLive === null || a.prices.length < 10) {
          a.prices = hist.slice(-MAX_PRICES);
        } else if (lastHist === lastLive) {
          a.prices = hist.slice(-MAX_PRICES);
        } else {
          // Merge: history body + recent live tail
          a.prices = [...hist.slice(-200), ...a.prices.slice(-30)].slice(-MAX_PRICES);
        }
        a.lastPrice = a.prices[a.prices.length - 1] || 0;
        // Keep live bucket tracking if stream already running; else wait for first tick
        if (a.lastBucket === null) {
          a.lastClosed = -1;
        } else {
          // Don't re-close history into live; resume from current open bucket
          a.lastClosed = a.lastBucket - BUCKET_SEC;
        }
        a.newCandle = true;
        rebuildTF(a);
        if(isRunning){
          if(!v289CandidateBSignal._seenSell)v289CandidateBSignal._seenSell=Object.create(null);
          if(!v289CandidateBSignal._seenRunner)v289CandidateBSignal._seenRunner=Object.create(null);
          if(!v289CandidateBSignal._seenBuy)v289CandidateBSignal._seenBuy=Object.create(null);
          v289CandidateBSignal._seenSell[msg.asset]=(getTF(a,'60s').prices||[]).length;
          v289CandidateBSignal._seenRunner[msg.asset]=(getTF(a,'15s').prices||[]).length;
          v289CandidateBSignal._seenBuy[msg.asset]=(getTF(a,'30s').prices||[]).length;
        }
        a.__historyBackfill={buckets:a.prices.length,from:null,to:null,at:Date.now(),source:'Pocket Option history seed'};
        sendStatus(`📚 ${msg.asset} · history seeded ${a.prices.length} closes · backfill counts toward warmup`);
      }

      // V120: HISTORY still seeds candle data, but grid execution confirmation comes from CHART_SLOTS.
    }

    if (msg.type === 'FAVORITES') {
      favoriteAssets.clear();
      for (const name of (Array.isArray(msg.assets)?msg.assets:[])) {
        if (name) { favoriteAssets.add(String(name)); knownAssets.add(String(name)); }
      }
      favoritesSyncedAt=Date.now();
      aiLog('FAVORITES_SYNC',{assets:[...favoriteAssets],count:favoriteAssets.size,source:msg.source||'bridge'},true);
      if (!multiAssetMode) sendStatus(favoriteAssets.size ? `⭐ FAVORITES · ${favoriteAssets.size} markets synced` : '⭐ FAVORITES · none detected');
    }

    if (msg.type === 'ASSETS') {
      msg.assets.forEach(x => {
        if (x.name && !isNaN(x.payout)) {
          assetPayouts[x.name] = x.payout;
          assetAvailable[x.name] = x.active !== false;
          knownAssets.add(x.name);
        }
      });
      maintainMultiPayoutChart();
    }

    if (msg.type === 'ASSET_SWITCH_ERROR') {
      for (let i=pendingChartTrades.length-1;i>=0;i--) if (pendingChartTrades[i].asset===msg.asset) pendingChartTrades.splice(i,1);
      if (pendingChartSwitchAsset === msg.asset) { pendingChartSwitchAsset=''; pendingChartSwitchSlot=''; pendingChartSwitchAt=0; }
      // V24.1.132: when the bridge reports the error for a payout-switch we armed
      // (slotId matches slotSwitchPending), tear that pending record down and mark
      // the ≥92% target as failed so payoutSwitchCandidate will not re-target it
      // for PAYOUT_SWITCH_AWAY_TTL_MS. Legacy favorite-grid switches keep the old
      // single-channel error reporting below.
      const handledSwitch = !!(msg.slotId && slotSwitchPending[msg.slotId]);
      if (handledSwitch) {
        const pend = slotSwitchPending[msg.slotId];
        delete slotSwitchPending[msg.slotId];
        payoutSwitchFailAt[pend.toAsset] = Date.now();
        aiLog('GRID_SLOT_SWITCH_ERROR', { slotId: msg.slotId, fromAsset: pend.fromAsset, toAsset: pend.toAsset, reason: msg.reason || 'switch failed' }, true);
        sendStatus(`⚠ chart switch to ${pend.toAsset} failed (${msg.reason || 'switch failed'}) · parked channel`);
      } else {
        sendStatus(`⚠ Could not switch Pocket Option chart to ${msg.asset} · no trade sent`);
        aiLog('MULTI_CHART_SWITCH_ERROR',{asset:msg.asset,reason:msg.reason||'switch failed'},true);
      }
      setTimeout(()=>processNextMultiChartTrade('switch-error'),50);
    }

    if (msg.type === 'ACCOUNT_TYPE') {
      if (typeof msg.isDemo === 'boolean') {
        gridAccountIsDemo = msg.isDemo;
        if (isRunning && window.__poatAcctShown !== msg.isDemo) {
          window.__poatAcctShown = msg.isDemo;
          sendStatus(msg.isDemo
            ? '💵 DEMO account confirmed · strategy execution enabled'
            : '💵 REAL account confirmed · strategy execution enabled (live money)');
        }
      }
    }

    if (msg.type === 'BALANCE') {
      // Authoritative Pocket Option balance comes directly from po-bridge's
      // WebSocket updateBalance event. Do not estimate or scrape it.
      const poBal=Number(msg.balance);
      if(Number.isFinite(poBal)){
        kaosPocketOptionBalance=poBal;
        kaosPocketOptionBalanceIsDemo=typeof msg.isDemo==='boolean'?msg.isDemo:kaosPocketOptionBalanceIsDemo;
      }
      if (botConfig?.compound && compoundBase === 0 && msg.balance > 0) {
        compoundBase = parseFloat(msg.balance);
      }
      // V24.1.130: track the PO account type for display only — the bot follows
      // whatever account PO has active, demo or real.
      if (typeof msg.isDemo === 'boolean') gridAccountIsDemo = msg.isDemo;
      if (isRunning && typeof msg.isDemo === 'boolean' && window.__poatAcctShown !== msg.isDemo) {
        window.__poatAcctShown = msg.isDemo;
        sendStatus(msg.isDemo
          ? '💵 DEMO account · trading paper balance'
          : '💵 REAL account · trading live money');
      }
    }

    if (msg.type === 'BRIDGE_READY')  {
      // V24.1.130: the bridge attaches the confirmed account type on BRIDGE_READY
      // (po-bridge sets it after confirmAccountFromDom on START). Used for
      // display/badge only — it never gates trades. Only assign on a real boolean
      // so a null/unknown value never clobbers a previously confirmed state.
      if (typeof msg.isDemo === 'boolean') gridAccountIsDemo = msg.isDemo;
      if (!isRunning || !sessionLockedAsset) sendStatus(`🔗 Bridge ready · locating visible chart…`);
      else sendStatus(`🔗 Bridge ready · ${sessionLockedAsset} locked · warming up…`);
    }
    if (msg.type === 'BRIDGE_BUSY') {
      sendStatus(`⏳ ${msg.reason||'Trade bridge busy'}${msg.asset?' · '+msg.asset:''}`);
      aiLog('TRADE_EXECUTION_FAILED',{stage:'BRIDGE_BUSY',asset:msg.asset||'',reason:msg.reason||'Trade bridge busy'},true);
      if (multiAssetMode && msg.asset) { initAssetState(msg.asset); assetOpenTradeCount[msg.asset]=Math.max(0,openTradeCount(msg.asset)-1); syncAssetPending(msg.asset); }
      if (multiAssetMode) setTimeout(()=>processNextMultiChartTrade('bridge-busy'),100);
    }
    if (msg.type === 'TRADE_CLICKED') {
      aiLog('TRADE_CLICK_CONFIRMED',{asset:msg.asset||'',direction:msg.direction||'',action:msg.action||'',amount:Number(msg.amount||0)},true);
      sendStatus(`📊 ${msg.action === 'call' ? 'BUY' : 'SELL'} ${msg.amount} · ${msg.asset} · Clicked · awaiting broker confirmation…`);
      if (multiAssetMode) setTimeout(()=>processNextMultiChartTrade('trade-clicked'),120);
    }
    if (msg.type === 'TRADE_ERROR')   {
      sendStatus(`⚠ ${msg.reason}`);
      aiLog('TRADE_EXECUTION_FAILED',{stage:'TRADE_ERROR',asset:msg.asset||'',reason:msg.reason||'unknown'},true);
      if (multiAssetMode && msg.asset) {
        initAssetState(msg.asset);
        assetOpenTradeCount[msg.asset]=Math.max(0,openTradeCount(msg.asset)-1); syncAssetPending(msg.asset);
      } else {
        tradePending = false;
      }
      if (multiAssetMode) setTimeout(()=>processNextMultiChartTrade('trade-error'),100);
    }
    if (msg.type === 'OPEN_ORDER') { const oa=msg.asset || lastTradeAsset; aiLog('BROKER_ORDER_CONFIRMED',{asset:oa,id:msg.id??null,direction:msg.direction||null},true); const d = resolveTradeDirection(oa, msg.id, msg.direction || lastTradeDir) || 'UNKNOWN'; if (d !== 'UNKNOWN') lastTradeDir=d; const ps=getPendingSnapshot(oa); if(ps){ps.__brokerConfirmed=true;ps.__brokerOrderId=msg.id??null;ps.__brokerConfirmedAt=Date.now();if(d!=='UNKNOWN')ps.direction=d;} sendStatus(`✅ Order open · ${d} ${lastTradeAmt} · ${oa}`); }

    if (msg.type === 'CLOSE_ORDER') onTradeResult(msg);
  });

 // ════════════════════════════════════════════════════════════
//  CHROME (POPUP) MESSAGES + DEBUG DATA
// ════════════════════════════════════════════════════════════
try {
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

    // ─────────────────────────────────────────────────────────
    // START BOT
    // ─────────────────────────────────────────────────────────
    if (msg.type === 'START_BOT') {
      if (KAOS_AUDIT_READ_ONLY) { sendResponse({ok:false,error:'Trading disabled during release audit'}); return false; }

      isRunning = true;
      botConfig = msg;
      prewarmReplayActive = false; prewarmReplayAssets.clear();
      for(const k of Object.keys(v219VisualByAsset)) delete v219VisualByAsset[k];
      try { chrome.runtime.sendMessage({type:'V219_VISION_START',tabId:msg.tabId||null}).catch(()=>{}); } catch(_) {}
      setTimeout(v219SyncVisionAssets,800);
      multiAssetMode = !!msg.multiAsset; // multi-grid 4-market mode ONLY when enabled in the popup
      gridAccountIsDemo = null; // V24.1.130: re-read the PO account on every Start (display only)
      lastGateShown = '';
      for (const k of Object.keys(channelState)) delete channelState[k]; // per-channel state resets with each run
      for (const k of Object.keys(indicatorStateByAsset)) delete indicatorStateByAsset[k]; // V24.1.168 isolated indicator workspaces reset with each run
      lastIndicators = newIndicatorState();
      pendingChartTrades.length = 0;
      favoriteAssets.clear();
      for (const k of Object.keys(visibleChartSlots)) delete visibleChartSlots[k];
      favoritesSyncedAt = 0;
      pendingChartSwitchAsset = '';
      pendingChartSwitchSlot = '';
      pendingChartSwitchAt = 0;
      for (const k of Object.keys(slotSwitchPending)) delete slotSwitchPending[k]; // V24.1.132: clear any in-flight payout-floor switch
      clearInterval(favoriteSyncTimer); favoriteSyncTimer=null;

      // V24.1.97: bind single-market mode to the visible asset for the ENTIRE run.
      // No 120-second expiry and no background STREAM reassignment.
      if (!multiAssetMode) {
        const requestedAsset = chartSelectedAsset || activeAsset || lastStartedAsset || '';
        sessionLockedAsset = requestedAsset;
        activeAsset = sessionLockedAsset;
        if (activeAsset && activeAsset !== lastStartedAsset) {
          delete lastIndicatorCtx[activeAsset];
          const aa = assetData[activeAsset];
          if (aa) { delete aa.__priceVisionState; delete aa.__revState; delete aa.__fastStructureState; }
        }
        lastStartedAsset = activeAsset;
      } else {
        sessionLockedAsset = '';
        clearInterval(favoriteSyncTimer); favoriteSyncTimer=null;
        clearInterval(gridRefreshTimer); gridRefreshTimer=null;
        sendStatus('🖥️ GRID · locating visible chart panels…');
      }

      // Clear any old micro-confirm queues; keep only rolling in-memory ticks.
      Object.keys(microPendingByAsset).forEach(k => clearMicroPending(k));

      if (!multiAssetMode && !sessionLockedAsset) {
        sendStatus('📡 Waiting for Pocket Option chart asset…');
        lastDebugReason = 'Waiting for chart asset handshake';
      }

      currentAmount = msg.amount || 5;

      martLevel = 0;
      consecutiveLosses = 0;
      antiLevel = 0;

      tradePending = false;

      lastTradeDir = null;
      lastTradeAsset = '';
      lastTradeAmt = 0;
      Object.keys(pendingOrderDirections).forEach(k => delete pendingOrderDirections[k]);

      sessionWins = 0;
      sessionLosses = 0;
      sessionPnl = 0;
      lossStreak = 0;
      winStreak = 0;
      compoundLevel = 0;
      cooldownUntil = 0;
      compoundBase = 0;
      tradeIdCounter = 1;

      // Reset per-asset TRADE state only — keep candle history so warmup
      // doesn't restart from 0 every Start (HISTORY/STREAM already filled).
      Object.keys(assetTradePending).forEach(k => delete assetTradePending[k]);
      Object.keys(assetMartLevel).forEach(k => delete assetMartLevel[k]);
      Object.keys(assetConsLosses).forEach(k => delete assetConsLosses[k]);
      Object.keys(assetAntiLevel).forEach(k => delete assetAntiLevel[k]);
      Object.keys(assetCurrentAmount).forEach(k => delete assetCurrentAmount[k]);
      Object.keys(assetTickCount).forEach(k => delete assetTickCount[k]);
      // Soft-reset bucket cursors (keep prices/rates/tf)
      Object.keys(assetData).forEach(k => {
        const a = assetData[k];
        if (!a) return;
        a.lastBucket = null;
        a.lastClosed = -1;
        a.newCandle = a.prices && a.prices.length >= 10;
        const startMin5s = (STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick']).minPrices || 40;
        if (a.prices && a.prices.length >= startMin5s) rebuildTF(a);
        if (a.tf) {
          Object.keys(a.tf).forEach(tfk => {
            if (a.tf[tfk]) a.tf[tfk].newCandle = (a.tf[tfk].prices || []).length >= 3;
          });
        }

        // B15.10.17 STARTUP EDGE FIX:
        // Candidate B may only act on a source-TF candle that closes AFTER Start.
        // Previously the _seen maps were empty after an extension reload, so the
        // first scan treated an already-existing historical condition as a brand
        // new signal and placed a trade immediately on every fresh install/start.
        if(!v289CandidateBSignal._seenSell)v289CandidateBSignal._seenSell=Object.create(null);
        if(!v289CandidateBSignal._seenRunner)v289CandidateBSignal._seenRunner=Object.create(null);
        if(!v289CandidateBSignal._seenBuy)v289CandidateBSignal._seenBuy=Object.create(null);
        v289CandidateBSignal._seenSell[k]=(getTF(a,'60s').prices||[]).length;
        v289CandidateBSignal._seenRunner[k]=(getTF(a,'15s').prices||[]).length;
        v289CandidateBSignal._seenBuy[k]=(getTF(a,'30s').prices||[]).length;
        knownAssets.add(k);
      });

      if (window.__poatBurst) {
        Object.keys(window.__poatBurst).forEach(k => {
          delete window.__poatBurst[k];
        });
      }

      clearTimeout(window.__poatStaleLock);
      clearTimeout(window.__poatMartTimer);
      Object.keys(assetStaleTimers).forEach(k => { clearTimeout(assetStaleTimers[k]); delete assetStaleTimers[k]; });
      Object.keys(assetMartTimers).forEach(k => { clearTimeout(assetMartTimers[k]); delete assetMartTimers[k]; });

      window.__poatStopped = false;

      window.postMessage({
        _poatCmd: true,
        type: 'START',
        settings: msg
      }, '*');

      sendStatus(
        `🚀 V120 [${msg.strategy || 'Murfs Pick'}] ` +
        `· ${multiAssetMode ? '4-CHART FAVORITES' : 'SINGLE'} · TF-paired · 5s basket only · R7/V6`
      );

      debugState.trades.length = 0;
      tradeRecords.length = 0;
      pendingSnapshot = null;
      Object.keys(pendingSnapshotsByAsset).forEach(k => delete pendingSnapshotsByAsset[k]);
      lastDebugReason = 'Started · warming up';
      sendDebug({ reason: 'Started · warming up' }, true);

      sendResponse({
        ok: true
      });

      return true;
    }

    // ─────────────────────────────────────────────────────────
    // STOP BOT
    // ─────────────────────────────────────────────────────────
    if (msg.type === 'STOP_BOT') {
      try { chrome.runtime.sendMessage({type:'V219_VISION_STOP'}).catch(()=>{}); } catch(_) {}

      isRunning = false;
      tradePending = false;

      martLevel = 0;
      consecutiveLosses = 0;
      antiLevel = 0;

      currentAmount = botConfig?.amount || 5;

      lossStreak = 0;
      winStreak = 0;
      compoundLevel = 0;
      cooldownUntil = 0;

      // Reset per-asset trade pending flags
      Object.keys(assetTradePending).forEach(k => { assetTradePending[k] = false; });

      clearTimeout(window.__poatStaleLock);
      clearTimeout(window.__poatMartTimer);
      Object.keys(assetStaleTimers).forEach(k => { clearTimeout(assetStaleTimers[k]); delete assetStaleTimers[k]; });
      Object.keys(assetMartTimers).forEach(k => { clearTimeout(assetMartTimers[k]); delete assetMartTimers[k]; });

      window.__poatStopped = true;
      Object.keys(microPendingByAsset).forEach(k => clearMicroPending(k));
      pendingChartTrades.length = 0;
      pendingChartSwitchAsset = '';
      pendingChartSwitchSlot = '';
      pendingChartSwitchAt = 0;
      for (const k of Object.keys(slotSwitchPending)) delete slotSwitchPending[k]; // V24.1.132: clear any in-flight payout-floor switch
      clearInterval(favoriteSyncTimer); favoriteSyncTimer=null;
      clearInterval(gridRefreshTimer); gridRefreshTimer=null;
      favoriteAssets.clear();
      for (const k of Object.keys(visibleChartSlots)) delete visibleChartSlots[k];
      if (!multiAssetMode) { activeAsset = ''; sessionLockedAsset = ''; }

      window.postMessage({
        _poatCmd: true,
        type: 'STOP'
      }, '*');

      sendStatus('⏹ Stopped');
      sendDebug({ reason: 'Stopped' }, true);

      sendResponse({
        ok: true
      });

      return true;
    }

    // B32.20.12 BACKGROUND HISTORY CONTINUITY
    // Chrome may throttle a non-visible Pocket Option page. The service worker
    // periodically asks the content/MAIN-world bridge to refresh exact 5s history
    // for the four verified chart assets. This uses broker history; it does not
    // fabricate candles or bypass the live-stream safety checks.
    if (msg.type === 'BACKGROUND_HISTORY_SYNC') {
      try {
        const assets=(multiAssetMode?multiScanAssets():[activeAsset]).filter(Boolean).slice(0,4);
        let requested=0;
        for(const asset of assets){ try{ if(requestPrevious200(asset,true)) requested++; }catch(_){} }
        sendResponse({ok:true,assets,requested,at:Date.now()});
      } catch(e){ sendResponse({ok:false,error:String(e&&e.message||e)}); }
      return true;
    }

    // ─────────────────────────────────────────────────────────
    // B32.2 LIVE CHART WORKSPACE — READ-ONLY DIAGNOSTIC VIEW
    // Uses KAOS Strategy's own candle/feature pipeline. No execution authority.
    // ─────────────────────────────────────────────────────────
    if (msg.type === 'RUN_STRATEGY_BACKTEST') {
      try {
        const cfg=msg.profile;if(!cfg||!cfg.engine)throw new Error('Strategy profile required');
        const requestedAssets=Array.isArray(msg.assets)?msg.assets.map(String).filter(Boolean):[];const assets=(requestedAssets.length?requestedAssets:(multiAssetMode?multiScanAssets():[activeAsset])).filter(Boolean).slice(0,4),markets=assets.map(a=>sbBacktestAny(a,cfg));
        const summary=markets.reduce((z,m)=>{z.trades+=m.trades;z.wins+=m.wins;z.losses+=m.losses;z.ties+=m.ties;z.maxLossStreak=Math.max(z.maxLossStreak,m.maxLossStreak);z.hours+=m.hours;return z},{trades:0,wins:0,losses:0,ties:0,maxLossStreak:0,hours:0});
        summary.winRate=summary.wins+summary.losses?summary.wins/(summary.wins+summary.losses):null;summary.tradesPerHour=summary.hours?summary.trades/summary.hours:0;
        sendResponse({ok:true,profileName:cfg.name,summary,markets,note:'Historical replay only; no orders placed. Signals use only candles closed at that moment. Built-in engines enter on the next available real 5s candle and settle at/after the selected expiry; same-market lock is held through expiry.'});
      } catch(e){sendResponse({ok:false,error:String(e&&e.message||e)});} return true;
    }

    if(msg.type==='GET_COMPANION_STATUS'){
      sendResponse({ok:true,engineReady:true,running:isRunning,asset:activeAsset||'',markets:[...new Set(visibleGridAssets())].filter(Boolean).slice(0,4).map(asset=>({asset})),accountBalance:kaosPocketOptionBalance,accountIsDemo:kaosPocketOptionBalanceIsDemo});return false;
    }
    if (msg.type === 'GET_C7B_CHART_SNAPSHOT' || msg.type === 'GET_TERMINAL_SNAPSHOT') {
      try {
        // 1.1.27: charts are read-only and must populate before START BOT.
        // Ask the MAIN-world Pocket Option bridge to discover the visible asset
        // and request real broker/chart history on every empty-snapshot cycle.
        try { window.postMessage({_poatCmd:true,type:'MARKET_DATA_PROBE'}, '*'); } catch(_) {}
        const requested=String(msg.asset||'').trim();
        // 1.1.28: never return an empty chart merely because chartSelectedAsset/
        // activeAsset was not published. Use the actual candle stores populated by
        // Pocket Option STREAM/HISTORY as the read-only chart source.
        const populatedAssets=Object.keys(assetData||{}).filter(a=>{
          try{
            const d=assetData[a];
            return !!a && (Number(d?.lastPrice)>0 || (Array.isArray(d?.prices)&&d.prices.length>0));
          }catch(_){return false;}
        }).sort((a,b)=>{
          const da=assetData[a],db=assetData[b];
          const ta=Number(da?.lastTickSec||0),tb=Number(db?.lastTickSec||0);
          const ca=Array.isArray(da?.prices)?da.prices.length:0,cb=Array.isArray(db?.prices)?db.prices.length:0;
          return (tb-ta)||(cb-ca);
        });
        let assets=(multiAssetMode?multiScanAssets():[requested||activeAsset]).filter(Boolean);
        for(const a of populatedAssets) if(!assets.includes(a)) assets.push(a);
        assets=assets.slice(0,4);
        if(!activeAsset && assets.length && !isRunning) activeAsset=assets[0];
        const build=(asset)=>{
          const src=asset?c7bStrategyRows(asset):{rows:[],source:'NONE'}; const rows=(src.rows||[]).slice(-3600);
          const feat=rows.length?c7bFeatureSeries(rows):[]; const lastF=feat.length?feat[feat.length-1]:null; const fv=asset?c7bVector(asset):null;
          const probUp=fv?c7bProb(fv.x):null, vol=fv?.vol??lastF?.vol??null; const tf={};
          if(rows.length)for(const sec of [5,10,30,60]){const rr=sec===5?rows:c7bAgg(rows,sec),ff=rr.length?c7bFeatureSeries(rr):[],q=ff.length?ff[ff.length-1]:null;tf[sec+'s']=q?{d9:q.d9,d20:q.d20,s2050:q.s2050,s50100:q.s50100,sl20:q.sl20,rsi:q.rsi,body:q.body,r1:q.r1,r3:q.r3,vol:q.vol}:null;}
          const chartRows=rows.map((r,i)=>{const f=feat[i]||{};return{ts:+r.ts,open:+r.open,high:+r.high,low:+r.low,close:+r.close,d9:Number(f.d9)||0,d20:Number(f.d20)||0,rsiNorm:Number(f.rsi)||0,vol:Number(f.vol)||0};});
          const closedTrades=tradeRecords.filter(t=>String(t.asset||'')===asset).slice(-40).map(t=>({ts:+t.ts,asset:t.asset,direction:t.direction,entryPrice:+t.entryPrice||null,exitPrice:+t.exitPrice||null,result:t.result||null,profit:+t.profit||0,expiry:+t.expiry||15,brokerConfirmed:true,regimeAtEntry:t.regimeAtEntry||null,engineFamily:t.engineFamily||null,totalScore:t.totalScore??null,signalSnapshot:t.signalSnapshot||null,replayVersion:t.replayVersion||null,replayFrameCount:Number(t.replayFrameCount||t.replayFrames?.length||0),replayStartTs:t.replayStartTs||null,replayEndTs:t.replayEndTs||null,replayFrames:Array.isArray(t.replayFrames)?t.replayFrames.slice(-80):[]})); const openQ=(pendingSnapshotQueuesByAsset[asset]||[]).filter(t=>t&&t.__brokerConfirmed).map(t=>({ts:+t.ts,asset:t.asset,direction:t.direction,entryPrice:+t.entryPrice||null,exitPrice:null,result:null,profit:0,expiry:+t.expiry||15,brokerConfirmed:true,orderId:t.__brokerOrderId||null,engineFamily:t.engineFamily||null,totalScore:t.totalScore??null,signalSnapshot:t.signalSnapshot||null})); const trades=[...closedTrades,...openQ].sort((a,b)=>a.ts-b.ts).slice(-40);
          const ai=indicatorStateByAsset[String(asset||'')]||{}, xa=ai.xgbAI||{}, cand=ai.candidate7B||{};
          const realRows=marketCandleHistory.byAsset[asset]||[], rawRows=raw5History.byAsset[asset]||[];
          const hist={canonical:src.rows?.length||0,real:realRows.length,raw:rawRows.length,firstTs:src.rows?.length?+src.rows[0].ts:null,lastTs:src.rows?.length?+src.rows[src.rows.length-1].ts:null,synced:!!(src.rows?.length>=24)};
          return{asset,source:src.source,candles:chartRows,ready:!!fv,microReady:!!(src.rows?.length>=24),probUp,probDown:probUp==null?null:1-probUp,vol,timeframes:tf,features:fv?C7B_FEATURES.map((name,i)=>({name,value:fv.x[i]})):[],trades,history:hist,
            liveStrategy:{name:'KAOS Strategy',engines:{reversal:{expiry:30},runner:{expiry:15,enabled:false,status:'RESEARCH_PAUSED'},breakout:{expiry:30}},zigzag:'5/3/1',zigzagTf:30,aiRole:'learning/research only',candidate7BRole:'live execution authority'},
            ai:{xgbUp:xa.previewUp??xa.rawUp??null,xgbRawUp:xa.rawUp??null,lgbUp:xa.shadowLgbUp??null,status:xa.status||AI_LAB.training?.status||'collecting',samples:Number(xa.samples||AI_LAB.samples.length||0),validationAccuracy:Number(xa.validationAccuracy||AI_LAB.holdout?.holdoutAccuracy||0),validationSamples:Number(xa.validationSamples||AI_LAB.holdout?.holdoutSamples||0),marketTrustTier:xa.marketTrustTier||'TRAINED',marketTrustAccuracy:Number(xa.marketTrustAccuracy||0),modelSource:xa.modelSource||'none'},candidate:cand};
        };
        const markets=assets.map(build); const asset=requested&&assets.includes(requested)?requested:(assets[0]||requested||activeAsset||''); const one=markets.find(x=>x.asset===asset)||build(asset);
        const wins=tradeRecords.filter(t=>String(t.result||'').toUpperCase()==='WIN').length,losses=tradeRecords.filter(t=>String(t.result||'').toUpperCase()==='LOSS').length,ties=tradeRecords.filter(t=>['TIE','DRAW'].includes(String(t.result||'').toUpperCase())).length;
        const common={ok:true,readOnly:true,assets,asset,running:isRunning,timestamp:Date.now(),
          accountBalance:kaosPocketOptionBalance,accountIsDemo:kaosPocketOptionBalanceIsDemo,balanceSource:kaosPocketOptionBalance==null?'WAITING':'PO_SOCKET_UPDATE_BALANCE',
          marketDataDiag:{activeAsset:String(activeAsset||''),chartSelectedAsset:String(chartSelectedAsset||''),populatedAssets:populatedAssets.slice(0,12),knownAssets:[...knownAssets].slice(0,24),assetStoreCount:Object.keys(assetData||{}).length},
          markets,allTrades:tradeRecords.slice(-500).map(t=>({ts:+t.ts,asset:t.asset,direction:t.direction,amount:+t.amount||0,entryPrice:+t.entryPrice||null,exitPrice:+t.exitPrice||null,result:t.result||null,profit:+t.profit||0,expiry:+t.expiry||15,engineFamily:t.engineFamily||null})),aiSummary:{samples:AI_LAB.samples.length,training:AI_LAB.training,holdout:AI_LAB.holdout,stats:AI_LAB.stats,researchSamples:C7B_RESEARCH.length,researchResolved45:C7B_RESEARCH.filter(x=>x.forward?.[45]!=null).length},analytics:{trades:tradeRecords.length,wins,losses,ties,winRate:(wins+losses)?wins/(wins+losses):null},research:C7B_RESEARCH.slice(-60)};
        sendResponse(msg.type==='GET_TERMINAL_SNAPSHOT'?common:{...common,...one,thresholds:{buy:0.61,sellUpMax:0.42,buyVolMax:1.00,sellVolMax:1.10}});
      } catch(e){ sendResponse({ok:false,error:String(e&&e.message||e)}); }
      return true;
    }

    // ─────────────────────────────────────────────────────────
    // POPUP STATUS REQUEST
    // ─────────────────────────────────────────────────────────
    if (msg.type === 'PING') {

      const asset = activeAsset || '';

      let tfKey = '30s';
      let tfCount = 0;

      if (asset && botConfig) {
        tfKey = expiryToTF(
          parseInt(botConfig.timeframe || 30, 10)
        );

        tfCount = getTF(
          getAsset(asset),
          tfKey
        ).prices.length;
      }

      const totalTrades = sessionWins + sessionLosses;

      const stratDef = STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick'];
      const min5s  = v241WarmupTarget(asset ? getAsset(asset) : null, stratDef.minPrices || 40);
      const gridRowsForPing = multiAssetMode ? multiScanAssets().map(gridWarmupState) : [];
      const storageCandles = multiAssetMode ? gridRowsForPing.reduce((n,r)=>n+Number(r.storageCandles||0),0) : (asset ? getAsset(asset).prices.length : 0);
      const warmupNeededTotal = multiAssetMode ? gridRowsForPing.reduce((n,r)=>n+Number(r.warmupNeeded||0),0) : min5s;
      const warmupPct = multiAssetMode ? (gridRowsForPing.length?Math.floor(gridRowsForPing.reduce((n,r)=>n+Number(r.pct||0),0)/gridRowsForPing.length):0) : Math.min(100, Math.round((storageCandles / min5s) * 100));

      sendResponse({
        ok: true,

        running: isRunning,
        strategy: botConfig?.strategy || 'Murfs Pick',

        asset,
        timeframe: botConfig?.timeframe || 30,

        storageCandles: asset
          ? getAsset(asset).prices.length
          : 0,

        indicatorTF: tfKey,

        indicatorCandles: tfCount,

        sessionWins,
        sessionLosses,

        winRate:
          totalTrades > 0
            ? ((sessionWins / totalTrades) * 100).toFixed(1)
            : '0.0',

        sessionPnl,
        martingaleLevel: martLevel,
        lossStreak,
        winStreak,
        compoundLevel,
        tradeIdCounter,

        currentAmount,
        tradePending,

        lastTradeDir,
        lastTradeAsset,
        lastTradeAmt,

        warmupNeeded: warmupNeededTotal,
        warmupPct,
        indicators: { ...lastIndicators },
        reason: lastDebugReason,

        // V24.1.130: four-channel live panel data + per-channel architecture flags
        gridAccountIsDemo,
        experienceLearning:{version:experienceMemory.version,captured:experienceMemory.records.length,resolved30:experienceMemory.resolved30,byAsset:experienceMemory.byAsset,recent:experienceMemory.records.slice(-80)},
        exactModelResearch:{model:'BB50(50,1.5) + 15s Alligator(3/1,10/5) + ROC(3)',liveExpiry:'5s',shadowExpiries:['5s','15s','30s','60s'],historicalReference:'20W/0L on original small historical sample',stats:JSON.parse(JSON.stringify(shadowOutcomeState.bySetup?.BB50_ALLIGATOR_ROC||{})),overall:JSON.parse(JSON.stringify(shadowOutcomeState.stats)),raw5Meta:raw5Meta(),realMarketCandleMeta:marketCandleMeta(),candidate7B:true,aiAuthority:false},
        channels: multiAssetMode ? multiScanAssets().map((a, i) => gridChannelDebugRow(a, i)) : [],

        timestamp: Date.now(),
        lastBackupAt: aiState._lastBackupAt || 0,
        lastBackupLabeled: aiState._lastBackupLabeled || 0,
        lastLossAt: aiState._lastLossAt || 0,
        lossMemLen: aiState.lossMemory.length
      });

      return true;
    }

    // ─────────────────────────────────────────────────────────
    // ─────────────────────────────────────────────────────────
    // MANUAL FULL BACKUP — AI + trades + session state
    // Nothing here writes AI state to chrome.storage. The popup explicitly
    // requests this object when the user presses EXPORT AI + DATA.
    // ─────────────────────────────────────────────────────────
    let v269FullBackupJsonCache = '';
    let v269FullBackupCacheAt = 0;
    const V271_BACKUP_CHUNK_CHARS = 512 * 1024;

    function buildManualBackupPayload() {
      return {
        kind: 'KAOS-XGBoost-Only-Manual-Backup', version: AI_BACKUP_SCHEMA, architecture:'XGB_LGB_MARKET_CHAMPION',
        exportedAt: new Date().toISOString(), features: AI_FEATURES, hidden: AI_HIDDEN,
        aiPolicy:{id:AI_POLICY_ID,parent:AI_POLICY_PARENT,schema:AI_POLICY_SCHEMA},
        aiTargetHorizonMs: AI_HORIZON_MS,
        timeframeNote: 'V24.1.224: visible market warmup and weighted-score execution readiness are synchronized. No AI-sample, model-validation, holdout, or micro-sample readiness gate can delay a qualified trade after warmup. For 30s: 15s times entry, 30s owns direction, 60s confirms. AI remains learning-only.',
        v23: { disabled:true, legacyCompatibilityOnly:true,
          version: V23_AI.version, lr: V23_AI.lr, l2: V23_AI.l2,
          minSamples: V23_AI.minSamples, entryThreshold: V23_AI.entryThreshold,
          shadowThreshold: V23_AI.shadowThreshold, minAccuracy: V23_AI.minAccuracy,
          w: V23_AI.w.slice(), b: V23_AI.b,
          trained: V23_AI.trained, correct: V23_AI.correct, total: V23_AI.total,
          val: V23_AI.val.slice(-500)
        },
        legacyAI: { disabled:true, legacyCompatibilityOnly:true,
          version: 6, validationSchema: 'direction-v3',
          w1: aiState.w1.slice(), b1: aiState.b1.slice(), w2: aiState.w2.slice(), b2: aiState.b2,
          vw1: aiState.vw1.slice(), vb1: aiState.vb1.slice(), vw2: aiState.vw2.slice(), vb2: aiState.vb2,
          trained: aiState.trained, correct: aiState.correct, total: aiState.total,
          paperQueued: aiState.paperQueued, paperLabeled: aiState.paperLabeled, paperCorrect: aiState.paperCorrect,
          confEma: aiState.confEma, accEma: aiState.accEma,
          regimeStats: aiState.regimeStats, marketStats: aiState.marketStats, aiAgreementStats: aiState.aiAgreementStats,
          labeledDataset: aiState.labeledDataset.slice(-5000),
          samples: aiState.samples.slice(-2500).map(s => ({...s})),
          lossMemory: aiState.lossMemory.slice(-LM_MAX_STORED),
          correctAbstains: aiState.correctAbstains || 0,
          marketRanking: aiState.marketRanking || {},
          _assetLossStreak: aiState._assetLossStreak || {}, _marketBanUntil: aiState._marketBanUntil || {},
          tradeTypeStats: aiState.tradeTypeStats || {}, paperSetupStats: aiState.paperSetupStats || {}, setupEdgeStats: aiState.setupEdgeStats || {}, strategyPerformance: aiState.strategyPerformance || {},
          strategyBuckets: aiState.strategyBuckets || {}, tradeStats: aiState.tradeStats || {},
          tradeMemory: (aiState.tradeMemory || []).slice(-TRADE_MEMORY_MAX), marketQuality: aiState.marketQuality || {},
          valCorrect: aiState.valCorrect, valTotal: aiState.valTotal, valWindow: aiState.valWindow || [],
          valAccuracy: aiState.valAccuracy, valRecent: aiState.valRecent,
          independentSamples: aiState.independentSamples, _lastLossAt: aiState._lastLossAt || 0,
          calibrationSlope: aiState.calibrationSlope, calibrationIntercept: aiState.calibrationIntercept,
          calibrationBins: aiState.calibrationBins
        },
        aiLab: { version: AI_LAB.version, samples: AI_LAB.samples.slice(-AI_LAB.maxSamples), model: AI_LAB.model, stats: AI_LAB.stats, holdout: AI_LAB.holdout, marketProfiles: AI_LAB.marketProfiles, training: AI_LAB.training, events: AI_EVENT_LOG.slice(-AI_EVENT_LOG_MAX) },
        patternAI: {disabled:true,legacyCompatibilityOnly:true,version:PATTERN_AI.version},
        decisionHistory: decisionHistory.slice(-DECISION_HISTORY_MAX).map(r=>({...r})),
        decisionPending: decisionPending.slice(-DECISION_HISTORY_MAX).map(r=>({...r})),
        decisionIdCounter,
        trades: tradeRecords.slice(),
        shadowOutcomes: {records:shadowOutcomeState.records.slice(-SHADOW_OUTCOME_MAX),stats:shadowOutcomeState.stats,bySetup:shadowOutcomeState.bySetup,byContext:shadowOutcomeState.byContext,shadowOutcomeId},
        sameColorBaseline: JSON.parse(JSON.stringify(sameColorBaseline)),
        experienceMemory: {version:experienceMemory.version,records:experienceMemory.records.slice(-EXPERIENCE_MAX),byAsset:experienceMemory.byAsset,lastBucket:experienceMemory.lastBucket,resolved30:experienceMemory.resolved30,experienceId,learningScope:'EVERY 30s opportunity + HOLD + shadow + all timeframes + indicators + reasons + outcomes'},
        shadowHorizonAI: {version:shadowHorizonAI.version,models:shadowHorizonAI.models,samples:shadowHorizonAI.samples.slice(-MH_AI_MAX_SAMPLES),bySetup:shadowHorizonAI.bySetup,updatedAt:shadowHorizonAI.updatedAt,learningOnly:true,executionAuthority:false},
        v287PocketFlowAI: {version:287,samples:v287State.samples.slice(-V287_MAX),pending:v287State.pending.slice(-120),resolved:v287State.resolved,correct:v287State.correct,accuracy:v287State.resolved?v287State.correct/v287State.resolved:0,allSamplesAccuracy:v287State.resolved?v287State.correct/v287State.resolved:0,selectiveResolved:v287State.selN,selectiveCorrect:v287State.selC,selectiveAccuracy:v287State.selN?v287State.selC/v287State.selN:0,selByAsset:v287State.selByAsset,w:v287State.w.slice(),b:v287State.b,models:v287State.models,last:v287State.last,learningOnly:true,executionAuthority:false},
        rawCandleHistory: {version:1,timeframe:'5s',source:'Pocket Option closed candles',byAsset:JSON.parse(JSON.stringify(raw5History.byAsset)),meta:raw5Meta()},
        debugState: JSON.parse(JSON.stringify(debugState)),
        // V24.1.135 C: why the bot held instead of trading (session counters)
        holdCounters: (aiState.holdCounters && JSON.parse(JSON.stringify(aiState.holdCounters))) || null,
        session: { wins:sessionWins, losses:sessionLosses, pnl:sessionPnl, lossStreak, winStreak,
          compoundLevel, tradeIdCounter, lastTradeDir, lastTradeAsset, lastTradeAmt },
        botConfig: botConfig ? {...botConfig} : null
      };
    }


    // ─────────────────────────────────────────────────────────
    // SMALL DIAGNOSTIC EXPORT — designed for sharing/uploading.
    // Keeps enough recent evidence to debug decisions without copying the
    // entire long-term training database or huge historical logs.
    // This export is ANALYSIS ONLY and is not intended as a restore backup.
    // ─────────────────────────────────────────────────────────
    function buildDiagnosticPayload() {
      flushDecisionHistory();
      const recentSamples = AI_LAB.samples.slice(-250).map(r=>({...r}));
      const recentDecisions = decisionHistory.slice(-200).map(r=>({...r}));
      const recentTrades = tradeRecords.slice(-120).map(r=>({...r}));
      const recentEvents = AI_EVENT_LOG.slice(-200).map(r=>({...r}));
      return {
        kind: 'KAOS-Diagnostic-Export',
        diagnosticVersion: 1,
        sourceBackupSchema: AI_BACKUP_SCHEMA,
        architecture: 'XGB_LGB_MARKET_CHAMPION',
        exportedAt: new Date().toISOString(),
        features: AI_FEATURES,
        aiTargetHorizonMs: AI_HORIZON_MS,
        note: 'Compact analysis export. Not a restore backup; full AI training data remains local.',
        activeAsset: String(activeAsset||''),
        favoriteAssets:[...favoriteAssets],
        fixedFourChartGrid:true,
        gridAssets:multiScanAssets(),
        gridWarmup:multiScanAssets().map(gridWarmupState),
        gridAccountIsDemo,
        // V24.1.135 C: why the bot held instead of trading (session counters)
        holdCounters: (aiState.holdCounters && JSON.parse(JSON.stringify(aiState.holdCounters))) || null,
        channelState: Object.fromEntries(Object.entries(channelState).map(([a, c]) => [a, {
          cooldownLeftSec: c.cooldownUntil ? Math.max(0, Math.round((c.cooldownUntil - Date.now()) / 1000)) : null,
          cooldownReason: c.cooldownReason || null,
          lossStreak: c.lossStreak || 0,
          winStreak: c.winStreak || 0,
          lastTradeAt: c.lastTradeAt || null,
          lastDebugReason: c.lastDebugReason || null
        }])),
        gridChannels:multiAssetMode ? multiScanAssets().map((a,i)=>gridChannelDebugRow(a,i)) : [],
        favoriteQueue:pendingChartTrades.map(q=>({asset:q.asset,dir:q.sig?.dir||null,ageMs:Date.now()-q.queuedAt})),
        running: !!isRunning,
        aiLab: {
          totalSamples: AI_LAB.samples.length,
          recentSamples,
          stats: JSON.parse(JSON.stringify(AI_LAB.stats||{})),
          holdout: JSON.parse(JSON.stringify(AI_LAB.holdout||{})),
          marketProfiles: JSON.parse(JSON.stringify(AI_LAB.marketProfiles||{})),
          training: JSON.parse(JSON.stringify(AI_LAB.training||{})),
          modelSummary: AI_LAB.model ? {
            version: AI_LAB.model.version||null,
            features: AI_LAB.model.features||AI_FEATURES,
            modelType: AI_LAB.model.modelType||AI_LAB.holdout?.modelType||null,
            assetModels: Object.keys(AI_LAB.model.assetModels||{}),
            lightgbmAvailable: AI_LAB.holdout?.lightgbmAvailable ?? null
          } : null
        },
        context: {
          paperSetupStats: JSON.parse(JSON.stringify(aiState.paperSetupStats||{})),
          setupEdgeStats: JSON.parse(JSON.stringify(aiState.setupEdgeStats||{})),
          tradeTypeStats: JSON.parse(JSON.stringify(aiState.tradeTypeStats||{})),
          strategyPerformance: JSON.parse(JSON.stringify(aiState.strategyPerformance||{})),
          marketStats: JSON.parse(JSON.stringify(aiState.marketStats||{})),
          marketQuality: JSON.parse(JSON.stringify(aiState.marketQuality||{})),
          agreementStats: JSON.parse(JSON.stringify(aiState.aiAgreementStats||{})),
          correctAbstains: Number(aiState.correctAbstains||0)
        },
        recentDecisions,
        recentTrades,
        recentEvents,
        shadowOutcomes: {records:shadowOutcomeState.records.slice(-250).map(r=>({...r})),stats:JSON.parse(JSON.stringify(shadowOutcomeState.stats)),bySetup:JSON.parse(JSON.stringify(shadowOutcomeState.bySetup)),byContext:JSON.parse(JSON.stringify(shadowOutcomeState.byContext))},
        sameColorBaseline: JSON.parse(JSON.stringify(sameColorBaseline)),
        shadowHorizonAI: {models:JSON.parse(JSON.stringify(shadowHorizonAI.models)),bySetup:JSON.parse(JSON.stringify(shadowHorizonAI.bySetup)),recentSamples:shadowHorizonAI.samples.slice(-250).map(r=>({...r})),updatedAt:shadowHorizonAI.updatedAt,learningOnly:true,executionAuthority:false},
        // B11-audit (I1 fix): the compact Diagnostic export now carries the recent
        // Pocket Flow rows too, so the 1s+sentiment evidence is available without a
        // multi-megabyte ALL DATA backup. Shadow-only; never an execution input.
        v287PocketFlowAI: {version:287,learningSource:'PO_1S_SHADOW',learningOnly:true,executionAuthority:false,samples:v287State.samples.slice(-500).map(r=>({...r})),pending:v287State.pending.slice(-120).map(r=>({...r})),resolved:v287State.resolved,correct:v287State.correct,accuracy:v287State.resolved?v287State.correct/v287State.resolved:0,allSamplesAccuracy:v287State.resolved?v287State.correct/v287State.resolved:0,selectiveResolved:v287State.selN,selectiveCorrect:v287State.selC,selectiveAccuracy:v287State.selN?v287State.selC/v287State.selN:0,selByAsset:v287State.selByAsset,w:v287State.w.slice(),b:v287State.b,models:v287State.models,last:v287State.last},
        debugState: JSON.parse(JSON.stringify(debugState||{})),
        indicators: JSON.parse(JSON.stringify(lastIndicators||{})),
        session: {
          wins:sessionWins, losses:sessionLosses, pnl:sessionPnl,
          lossStreak, winStreak, compoundLevel, tradeIdCounter,
          lastTradeDir, lastTradeAsset, lastTradeAmt
        },
        botConfig: botConfig ? {...botConfig} : null,
        counts: {
          aiSamples: AI_LAB.samples.length,
          decisions: decisionHistory.length,
          pendingDecisions: decisionPending.length,
          trades: tradeRecords.length,
          aiEvents: AI_EVENT_LOG.length
        }
      };
    }

    function restoreLegacyAIState(m) {
      if (!m || typeof m !== 'object') return false;
      if (Array.isArray(m.w1) && m.w1.length === AI_FEATURES * AI_HIDDEN) aiState.w1=m.w1.map(Number);
      if (Array.isArray(m.b1) && m.b1.length === AI_HIDDEN) aiState.b1=m.b1.map(Number);
      if (Array.isArray(m.w2) && m.w2.length === AI_HIDDEN) aiState.w2=m.w2.map(Number);
      if (typeof m.b2==='number') aiState.b2=Number(m.b2);
      if (Array.isArray(m.vw1) && m.vw1.length===AI_FEATURES*AI_HIDDEN) aiState.vw1=m.vw1.map(Number);
      if (Array.isArray(m.vb1) && m.vb1.length===AI_HIDDEN) aiState.vb1=m.vb1.map(Number);
      if (Array.isArray(m.vw2) && m.vw2.length===AI_HIDDEN) aiState.vw2=m.vw2.map(Number);
      if (typeof m.vb2==='number') aiState.vb2=Number(m.vb2);
      const nums=['trained','correct','total','paperQueued','paperLabeled','paperCorrect','confEma','accEma','valCorrect','valTotal','valAccuracy','valRecent','independentSamples','correctAbstains','_lastLossAt'];
      for (const k of nums) if (typeof m[k]==='number') aiState[k]=m[k];
      const objs=['regimeStats','marketStats','aiAgreementStats','marketRanking','_assetLossStreak','_marketBanUntil','tradeTypeStats','paperSetupStats','setupEdgeStats','strategyPerformance','strategyBuckets','tradeStats','marketQuality'];
      for (const k of objs) if (m[k] && typeof m[k]==='object') aiState[k]=m[k];
      aiState._v118EdgeSeeded=!!(m.setupEdgeStats && Object.keys(m.setupEdgeStats).length);
      if (Array.isArray(m.labeledDataset)) aiState.labeledDataset=m.labeledDataset.slice(-5000);
      if (Array.isArray(m.samples)) aiState.samples=m.samples.slice(-2500);
      if (Array.isArray(m.lossMemory)) aiState.lossMemory=m.lossMemory.slice(-LM_MAX_STORED);
      if (Array.isArray(m.tradeMemory)) aiState.tradeMemory=m.tradeMemory.slice(-TRADE_MEMORY_MAX);
      if (Array.isArray(m.valWindow)) aiState.valWindow=m.valWindow.slice(-AI_VAL_WINDOW);
      if (typeof m.calibrationSlope==='number') aiState.calibrationSlope=m.calibrationSlope;
      if (typeof m.calibrationIntercept==='number') aiState.calibrationIntercept=m.calibrationIntercept;
      if (typeof m.calibrationBins==='number') aiState.calibrationBins=m.calibrationBins;
      return true;
    }

    function restoreV23State(v) {
      if (!v || typeof v!=='object') return false;
      if (Array.isArray(v.w) && v.w.length===AI_FEATURES) V23_AI.w=v.w.map(Number);
      if (typeof v.b==='number') V23_AI.b=Number(v.b);
      for (const k of ['trained','correct','total']) if (typeof v[k]==='number') V23_AI[k]=v[k];
      if (Array.isArray(v.val)) V23_AI.val=v.val.slice(-500).map(Boolean);
      if (typeof v.lr==='number') V23_AI.lr=v.lr;
      if (typeof v.l2==='number') V23_AI.l2=v.l2;
      if (typeof v.minSamples==='number') V23_AI.minSamples=v.minSamples;
      if (typeof v.entryThreshold==='number') V23_AI.entryThreshold=v.entryThreshold;
      if (typeof v.shadowThreshold==='number') V23_AI.shadowThreshold=v.shadowThreshold;
      if (typeof v.minAccuracy==='number') V23_AI.minAccuracy=v.minAccuracy;
      V23_AI.last=null;
      return true;
    }

    // FULL DECISION HISTORY — every BUY/SELL/HOLD evaluation + 30s outcome
    if (msg.type === 'GET_DECISION_HISTORY') {
      flushDecisionHistory();
      sendResponse({ok:true, records:decisionHistory.slice()});
      return true;
    }

    // FULL TRADE RECORDS (popup CSV export)
    // ─────────────────────────────────────────────────────────
    if (msg.type === 'GET_TRADES') {
      sendResponse({ ok: true, records: tradeRecords.slice() });
      return true;
    }

    if (msg.type === 'RESET_TRADES') {
      tradeRecords.length = 0;
      pendingSnapshot = null;
      sessionWins = 0;
      sessionLosses = 0;
      sessionPnl = 0;
      lossStreak = 0;
      winStreak = 0;
      compoundLevel = 0;
      tradeIdCounter = 1;
      sendResponse({ ok: true });
      return true;
    }

    // B31 — SEPARATE MARKET-CANDLE EXPORT. Contains no trades, decisions, AI labels or bot outcomes.
    if (msg.type === 'EXPORT_MARKET_CANDLES_DIRECT') {
      try {
        marketCandlePersist(true);
        const payload={kind:'KAOS-Market-Candles',version:2,timeframe:'5s',source:'Pocket Option observed REAL closed candles only',exportedAt:new Date().toISOString(),independentOfTrading:true,meta:marketCandleMeta(),byAsset:JSON.parse(JSON.stringify(marketCandleHistory.byAsset))};
        const json=JSON.stringify(payload),blob=new Blob([json],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a'),stamp=new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
        a.href=url;a.download=`KAOS_MARKET_CANDLES_${stamp}.json`;a.style.display='none';(document.body||document.documentElement).appendChild(a);a.click();a.remove();setTimeout(()=>{try{URL.revokeObjectURL(url);}catch(_){}},60000);
        sendResponse({ok:true,bytes:json.length,mb:json.length/1024/1024,meta:marketCandleMeta()});
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    // B7 DIRECT LARGE BACKUP — build + download in this content-script context.
    // This avoids moving multi-megabyte JSON through extension messaging entirely.
    if (msg.type === 'EXPORT_FULL_BACKUP_DIRECT') {
      try {
        const core=buildManualBackupPayload();
        chrome.storage.local.get(['settings','stats','tradeRecords','strategyProfiles','activeStrategyProfile','terminalSlotProfiles','terminalDrawings'], (local) => {
          try {
            const payload={...core,kind:'KAOS-All-Data-Backup',allDataVersion:1,
              popupData:{settings:local?.settings||null,stats:local?.stats||{wins:sessionWins,losses:sessionLosses,pnl:sessionPnl},tradeRecords:Array.isArray(local?.tradeRecords)?local.tradeRecords:tradeRecords.slice(),strategyProfiles:(local?.strategyProfiles&&typeof local.strategyProfiles==='object')?local.strategyProfiles:{},activeStrategyProfile:typeof local?.activeStrategyProfile==='string'?local.activeStrategyProfile:'legacy7b',terminalSlotProfiles:Array.isArray(local?.terminalSlotProfiles)?local.terminalSlotProfiles:[],terminalDrawings:Array.isArray(local?.terminalDrawings)?local.terminalDrawings:[]}};
            const json=JSON.stringify(payload);
            const blob=new Blob([json],{type:'application/json'});
            const url=URL.createObjectURL(blob);
            const a=document.createElement('a');
            const stamp=new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
            a.href=url; a.download=`KAOS_ALL_DATA_${stamp}.json`; a.style.display='none';
            (document.body||document.documentElement).appendChild(a); a.click(); a.remove();
            setTimeout(()=>{try{URL.revokeObjectURL(url);}catch(_){}},60000);
            sendResponse({ok:true,bytes:json.length,mb:json.length/1024/1024,method:'direct-blob'});
          } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
        });
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'START_FULL_BACKUP_CHUNKED') {
      try {
        v269FullBackupJsonCache = JSON.stringify(buildManualBackupPayload());
        v269FullBackupCacheAt = Date.now();
        sendResponse({ok:true,totalChars:v269FullBackupJsonCache.length,chunkChars:V271_BACKUP_CHUNK_CHARS,totalChunks:Math.ceil(v269FullBackupJsonCache.length/V271_BACKUP_CHUNK_CHARS)});
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }
    if (msg.type === 'GET_FULL_BACKUP_CHUNK') {
      try {
        const i=Math.max(0,Number(msg.index)||0), start=i*V271_BACKUP_CHUNK_CHARS;
        if (!v269FullBackupJsonCache) throw new Error('Backup chunk session is not active');
        // B6: expiry is inactivity-based, not total-export-duration based. Large AI datasets
        // can legitimately take several minutes to cross the extension messaging boundary.
        if (Date.now()-v269FullBackupCacheAt>15*60*1000) throw new Error('Backup chunk session expired after 15 minutes of inactivity');
        v269FullBackupCacheAt = Date.now();
        sendResponse({ok:true,index:i,chunk:v269FullBackupJsonCache.slice(start,start+V271_BACKUP_CHUNK_CHARS)});
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }
    if (msg.type === 'END_FULL_BACKUP_CHUNKED') {
      v269FullBackupJsonCache=''; v269FullBackupCacheAt=0; sendResponse({ok:true}); return true;
    }
    if (msg.type === 'GET_FULL_BACKUP') {
      // Kept for compatibility with older popups; V271 popup uses chunked transfer.
      try { sendResponse({ok:true, payload:buildManualBackupPayload()}); }
      catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'GET_DIAGNOSTIC_EXPORT') {
      try { sendResponse({ok:true, payload:buildDiagnosticPayload()}); }
      catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'GET_AI_STATUS') {
      const acc=V23_AI.total ? V23_AI.correct/V23_AI.total : 0;
      sendResponse({ok:true,
        v23:{disabled:true,trained:0,total:0,correct:0,accuracy:0,warm:false,confidence:0,direction:null,up:0.5,down:0.5,minSamples:0,minAccuracy:0,targetMs:AI_HORIZON_MS},
        legacy:{disabled:true,trained:0,total:0,paperLabeled:aiState.paperLabeled,independentSamples:aiState.independentSamples,valAccuracy:0,valTotal:0,labeled:aiState.labeledDataset.length,queued:aiState.samples.length},
        patternAI:{disabled:true,trained:0,total:0,correct:0,accuracy:0,warm:false,minSamples:0,minAccuracy:0,last:null},
        aiLab:{
          samples:AI_LAB.samples.length,
          queued:aiState.paperQueued||0,
          pending:aiState.samples.length,
          model:!!AI_LAB.model,
          stats:AI_LAB.stats,
          last:AI_LAB.last,
          holdout:AI_LAB.holdout,
          training:AI_LAB.training,
          live:!!AI_LAB.model && AI_LAB.training?.status==='trained',
          activeAsset:String(activeAsset||''),
          gridAssets:multiAssetMode?multiScanAssets():[],
          gridWarmup:multiAssetMode?multiScanAssets().map((a,i)=>({channel:i+1,...gridWarmupState(a)})):[],
          gridSlots:{...visibleChartSlots},
          champion:(()=>{
            try {
              const sel=xgbSelectionForAsset(AI_LAB.model,activeAsset||'');
              const rep=AI_LAB.holdout?.perAsset?.[String(activeAsset||'')]||{};
              return {family:sel?.family||'none',source:sel?.source||'none',marketChampion:sel?.marketChampion||rep?.marketChampion||'none',reason:sel?.reason||'',report:rep};
            } catch(_) { return {family:'none',source:'none',marketChampion:'none',reason:'status-unavailable',report:{}}; }
          })(),
          marketWarm:aiMarketWarmupReady(activeAsset||''),
          liveTrust:lastIndicators.xgbAI||null,
          warmupRejected:aiState._warmupRejected||0,
          featureRejected:aiState._rejected||0,
          paperValidationMode:PAPER_SETUP_VALIDATION_MODE,
          paperSetupStats:aiState.paperSetupStats||{},
          aiPaperTrades:(()=>{const rows=experienceMemory.records.filter(r=>r?.aiPaperTrade&&r?.labels?.['30s']).slice(-80);let wins=0,losses=0,draws=0;for(const r of rows){const z=r.aiPaperTrade.result;if(z==='win')wins++;else if(z==='loss')losses++;else if(z==='draw')draws++;}return {wins,losses,draws,total:rows.length,decided:wins+losses,accuracy:(wins+losses)?wins/(wins+losses):null,recent:rows.slice(-12).map(r=>({t:r.ts,asset:r.asset,dir:r.aiPaperTrade.dir,confidence:r.aiPaperTrade.confidence,result:r.aiPaperTrade.result,entry:r.entryPrice,exit:r.aiPaperTrade.exitPrice,actual:r.aiPaperTrade.actualDirection,reason:r.aiPaperTrade.reason,outcomeWhy:r.aiPaperTrade.outcomeWhy,botReason:r.botDecision?.reason||r.botDecision?.debug||null}))};})(),
          strategyLessons:{stats:JSON.parse(JSON.stringify(aiStrategyLessons.stats)),pending:aiStrategyLessons.records.filter(r=>r.result==='pending').length,resolved:aiStrategyLessons.records.filter(r=>r.result!=='pending').length,recent:aiStrategyLessons.records.slice(-12).map(r=>({t:r.ts,asset:r.asset,setup:r.setup,dir:r.dir,accepted:r.accepted,reason:r.reason,result:r.result,outcomeWhy:r.outcomeWhy||null}))},
          trace:lastIndicators.aiDecisionTrace||null, agreementStats:aiState.aiAgreementStats||null,
          indicators:{regime:lastIndicators.regime||null,trendIntegrity:lastIndicators.trendIntegrity||null,tqsBuy:lastIndicators.tqsBuy||0,tqsSell:lastIndicators.tqsSell||0,marketQuality:lastIndicators.marketQuality||0,runnerBuy:lastIndicators.runnerBuy||0,runnerSell:lastIndicators.runnerSell||0,revBuy:lastIndicators.revBuy||0,revSell:lastIndicators.revSell||0},
          events:AI_EVENT_LOG.slice(-200),
          decisionHistory:{total:decisionHistory.length,resolved:decisionHistory.filter(r=>r.resolved).length,pending:decisionPending.length},
          shadowOutcomes:{stats:shadowOutcomeState.stats,bySetup:shadowOutcomeState.bySetup,byContext:shadowOutcomeState.byContext,recent:shadowOutcomeState.records.slice(-40)},sameColorBaseline:JSON.parse(JSON.stringify(sameColorBaseline)),shadowHorizonAI:{models:shadowHorizonAI.models,bySetup:shadowHorizonAI.bySetup,recent:shadowHorizonAI.samples.slice(-40),updatedAt:shadowHorizonAI.updatedAt,learningOnly:true,executionAuthority:false},strategyTelemetry:JSON.parse(JSON.stringify(v181StrategyTelemetry))
        }
      }); return true;
    }


    if (msg.type === 'V219_VISUAL_FEATURES') {
      try {
        const asset=String(msg.asset||'');
        const f=Array.isArray(msg.features)?msg.features.slice(0,V219_VISUAL_FEATURES):[];
        if(asset && f.length===V219_VISUAL_FEATURES){
          v219VisualByAsset[asset]={features:f,at:Number(msg.at||Date.now()),ageSec:Number(msg.ageSec||0),frames:Number(msg.frames||0),windowSec:Number(msg.windowSec||0)};
          const ii=indicatorStateByAsset[asset]||null;
          if(ii) ii.visualAI={ready:Number(msg.windowSec||0)>=30,learning:true,frames:Number(msg.frames||0),windowSec:Number(msg.windowSec||0),features:f.slice()};
        }
        sendResponse({ok:true});
      } catch(e){ sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    // V238: the registered Windows native host may still emit an 88-feature
    // tree bundle. V236 intentionally sends its first 88 canonical features on
    // the wire. Such trees never reference features 88..103, so they are safe to
    // score against the 104-feature vector after metadata normalization.
    function v238NormalizeNativeModel(model){
      if(!model || typeof model!=='object') return model;
      const n=Number(model.features||0);
      if(n===88) return {...model,features:AI_FEATURES,wireFeatures:88,sourceFeatures:AI_FEATURES,v238Compat:true};
      return model;
    }

    if (msg.type === 'XGB_MODEL_UPDATE') {
      try {
        const p={...(msg.payload||{})}; if(p.model)p.model=v238NormalizeNativeModel(p.model); if(p.lightgbm)p.lightgbm=v238NormalizeNativeModel(p.lightgbm);
        if (p.ok && p.model && Number(p.model.features||AI_FEATURES)===AI_FEATURES) {
          AI_LAB.model=p.model;
          AI_LAB.holdout=p.report||{};
          aiLog('XGB_TRAINED', {samples:p.report?.samples||AI_LAB.samples.length,holdoutAccuracy:p.report?.holdoutAccuracy||0,trainAccuracy:p.report?.trainAccuracy||0}, true);
          AI_LAB.stats = AI_LAB.stats || {total:0,correct:0,independent:0};
          AI_LAB.training={status:'trained',samples:Number(p.report?.samples||AI_LAB.samples.length),holdoutAccuracy:Number(p.report?.holdoutAccuracy||0),trainAccuracy:Number(p.report?.trainAccuracy||0),trainedAt:Date.now(),message:p.message||''};
        } else if (p.status==='rejected') {
          AI_LAB.holdout=p.report||{};
          AI_LAB.training={status:'rejected',samples:Number(p.report?.samples||AI_LAB.samples.length),message:p.message||'Model did not pass holdout validation; prior model retained'};
          aiLog('XGB_REJECTED', {report:p.report||{}}, true);
        } else if (p.status==='warming') {
          AI_LAB.training={status:'warming',samples:Number(p.samples||AI_LAB.samples.length),message:p.message||''};
          aiLog('XGB_WARMING', {samples:p.samples||AI_LAB.samples.length,message:p.message||''}, true);
        } else if (p.error) {
          AI_LAB.training={status:'error',samples:AI_LAB.samples.length,message:p.error};
          aiLog('XGB_ERROR', {error:p.error}, true);
        }
        sendResponse({ok:true});
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'SYNC_XGB_RESULT') {
      try {
        const p={...(msg.payload||{})}; if(p.model)p.model=v238NormalizeNativeModel(p.model); if(p.lightgbm)p.lightgbm=v238NormalizeNativeModel(p.lightgbm);
        if (p.ok && p.model && Number(p.model.features||AI_FEATURES)===AI_FEATURES) {
          AI_LAB.model=p.model;
          AI_LAB.holdout=p.report||{};
          aiLog('XGB_TRAINED', {samples:p.report?.samples||AI_LAB.samples.length,holdoutAccuracy:p.report?.holdoutAccuracy||0,trainAccuracy:p.report?.trainAccuracy||0}, true);
          AI_LAB.training={status:'trained',samples:Number(p.report?.samples||AI_LAB.samples.length),holdoutAccuracy:Number(p.report?.holdoutAccuracy||0),trainAccuracy:Number(p.report?.trainAccuracy||0),trainedAt:Date.now(),message:p.message||''};
        } else if (p.status==='rejected') {
          AI_LAB.holdout=p.report||{};
          AI_LAB.training={status:'rejected',samples:Number(p.report?.samples||AI_LAB.samples.length),message:p.message||'Model did not pass holdout validation; prior model retained'};
          aiLog('XGB_REJECTED', {report:p.report||{}}, true);
        } else if (p.status==='warming') {
          AI_LAB.training={status:'warming',samples:Number(p.samples||AI_LAB.samples.length),message:p.message||''};
          aiLog('XGB_WARMING', {samples:p.samples||AI_LAB.samples.length,message:p.message||''}, true);
        } else if (p.error) {
          AI_LAB.training={status:'error',samples:AI_LAB.samples.length,message:p.error};
          aiLog('XGB_ERROR', {error:p.error}, true);
        }
        sendResponse({ok:true});
      } catch(e) { sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'RESET_AI_MODEL') {
      aiState.w1=aiXavier(AI_FEATURES,AI_FEATURES*AI_HIDDEN); aiState.b1=new Array(AI_HIDDEN).fill(0);
      aiState.w2=aiXavier(AI_HIDDEN,AI_HIDDEN); aiState.b2=0;
      aiState.vw1=new Array(AI_FEATURES*AI_HIDDEN).fill(0); aiState.vb1=new Array(AI_HIDDEN).fill(0);
      aiState.vw2=new Array(AI_HIDDEN).fill(0); aiState.vb2=0;
      aiState.trained=aiState.correct=aiState.total=0; aiState.paperQueued=aiState.paperLabeled=aiState.paperCorrect=0;
      aiState.confEma=aiState.accEma=0.5; aiState.valCorrect=aiState.valTotal=0; aiState.valWindow=[]; aiState.valAccuracy=0; aiState.valRecent=0;
      aiState.independentSamples=0; aiState.regimeStats={}; aiState.marketStats={}; aiState.aiAgreementStats={total:0,agree:0,disagree:0,agreeCorrect:0,v23Correct:0,xgbCorrect:0,last100:[]}; aiState.labeledDataset=[]; aiState.samples=[];
      aiState.lossMemory=[]; aiState.correctAbstains=0; aiState.marketRanking={}; aiState._assetLossStreak={}; aiState._marketBanUntil={};
      aiState._rejected=0; aiState.tradeTypeStats={}; aiState.paperSetupStats={total:0,wins:0,losses:0,draws:0,bySetup:{},byDir:{BUY:{total:0,wins:0,losses:0},SELL:{total:0,wins:0,losses:0}},recent:[]}; aiState.setupEdgeStats={}; aiState._v118EdgeSeeded=true; aiState.strategyBuckets={}; aiState.tradeStats={}; aiState.tradeMemory=[]; aiState.marketQuality={}; aiState._lastLossAt=0;
      aiState.strategyPerformance={RUNNER:{BUY:{trades:0,wins:0,losses:0,draws:0,profit:0},SELL:{trades:0,wins:0,losses:0,draws:0,profit:0}},REVERSAL:{BUY:{trades:0,wins:0,losses:0,draws:0,profit:0},SELL:{trades:0,wins:0,losses:0,draws:0,profit:0}},GENERIC:{BUY:{trades:0,wins:0,losses:0,draws:0,profit:0},SELL:{trades:0,wins:0,losses:0,draws:0,profit:0}}};
      V23_AI.w=new Array(AI_FEATURES).fill(0); V23_AI.b=0; V23_AI.trained=0; V23_AI.correct=0; V23_AI.total=0; V23_AI.val=[]; V23_AI.last=null;
      AI_LAB.samples=[]; AI_LAB.model=null; AI_LAB.stats={total:0,correct:0,independent:0,livePredictions:0,liveUsed:0,liveSkipped:0}; AI_LAB.holdout={}; AI_LAB.marketProfiles={}; AI_LAB.last=null; AI_LAB.training={status:'collecting',samples:0,message:'Fresh AI reset — collecting new market data'};
      PATTERN_AI.w=new Array(PATTERN_AI.features).fill(0); PATTERN_AI.b=0; PATTERN_AI.trained=PATTERN_AI.total=PATTERN_AI.correct=0; PATTERN_AI.val=[]; PATTERN_AI.last=null;
      aiState._warmupRejected=0; aiState._rejected=0;
      AI_EVENT_LOG.length=0; decisionHistory.length=0; decisionPending.length=0; decisionIdCounter=1;
      aiLog('AI_FRESH_RESET', {features:AI_FEATURES,targetMs:AI_HORIZON_MS}, true);
      sendResponse({ok:true}); return true;
    }

    // B14.1: reliable large-backup transport. The popup sends JSON text in
    // bounded chunks so Chrome never has to serialize a multi-megabyte object in one tabs.sendMessage call.
    if (msg.type === 'START_FULL_IMPORT_CHUNKED') {
      window.__KAOSImportChunks=[]; window.__KAOSImportChars=0;
      sendResponse({ok:true}); return true;
    }
    if (msg.type === 'PUT_FULL_IMPORT_CHUNK') {
      if(!Array.isArray(window.__KAOSImportChunks)) window.__KAOSImportChunks=[];
      const part=String(msg.chunk||'');
      window.__KAOSImportChunks.push(part);
      window.__KAOSImportChars=(window.__KAOSImportChars||0)+part.length;
      sendResponse({ok:true,chars:window.__KAOSImportChars}); return true;
    }
    if (msg.type === 'END_FULL_IMPORT_CHUNKED') {
      try {
        const raw=(window.__KAOSImportChunks||[]).join('');
        window.__KAOSImportChunks=[]; window.__KAOSImportChars=0;
        msg={type:'RESTORE_FULL_BACKUP',payload:JSON.parse(raw)};
      } catch(e) {
        window.__KAOSImportChunks=[]; window.__KAOSImportChars=0;
        sendResponse({ok:false,error:'Chunked backup parse failed: '+(e.message||String(e))}); return true;
      }
    }

    if (msg.type === 'RESTORE_FULL_BACKUP' || msg.type === 'RESTORE_AI_BACKUP') {
      try {
        let payload=msg.payload;
        if (!payload || typeof payload!=='object') throw new Error('Invalid backup file');
        if (!payload.kind && payload.features===AI_FEATURES && Array.isArray(payload.w1)) {
          payload={kind:'KAOS-Legacy-Backup',version:AI_BACKUP_SCHEMA,features:payload.features,legacyAI:payload,v23:null};
        }
        if (payload.features!=null && ![64,72,76,88,AI_FEATURES].includes(Number(payload.features)))
        throw new Error(`Feature count mismatch: backup ${payload.features} vs current ${AI_FEATURES}`);
      // V219.2: migrate legacy 88-feature restore payloads BEFORE any downstream
      // schema validation/model restore. Historical visual features are neutral.
      if(Number(payload.features)===88) {
        v219MigrateImportedSamples(payload);
        payload.features=AI_FEATURES;
        payload.migratedFromFeatures=88;
      }
        if (payload.v23) restoreV23State(payload.v23);
        if (payload.legacyAI) restoreLegacyAIState(payload.legacyAI);
        if (payload.aiLab) { aiLabRestore(payload.aiLab); if(Array.isArray(payload.aiLab.events)){ AI_EVENT_LOG.push(...payload.aiLab.events.slice(-AI_EVENT_LOG_MAX)); } aiLog('AI_IMPORT', {samples:AI_LAB.samples.length,modelImported:!!AI_LAB.model}, true); }
        if (payload.patternAI && typeof payload.patternAI==='object') {
          const m=payload.patternAI; if(Array.isArray(m.w)&&m.w.length===PATTERN_AI.features)PATTERN_AI.w=m.w.map(Number); if(typeof m.b==='number')PATTERN_AI.b=Number(m.b);
          for(const k of ['trained','total','correct'])if(typeof m[k]==='number')PATTERN_AI[k]=Number(m[k]); if(Array.isArray(m.val))PATTERN_AI.val=m.val.slice(-500).map(Boolean); PATTERN_AI.last=null;
        }
        // Restore the complete decision audit trail (BUY / SELL / HOLD + outcomes).
        if (Array.isArray(payload.decisionHistory)) {
          decisionHistory.length=0;
          const seen=new Set();
          for (const r of payload.decisionHistory.slice(-DECISION_HISTORY_MAX)) {
            if(!r || typeof r!=='object') continue;
            const key=String(r.id ?? r.snapshotId ?? `${r.ts||''}|${r.asset||''}|${r.finalDecision||''}`);
            if(seen.has(key)) continue; seen.add(key); decisionHistory.push({...r});
          }
          decisionPending.length=0;
          const pendingSrc=Array.isArray(payload.decisionPending)?payload.decisionPending:decisionHistory.filter(r=>!r.resolved);
          for(const r of pendingSrc.slice(-DECISION_HISTORY_MAX)) if(r && typeof r==='object' && !r.resolved) decisionPending.push(r);
          const maxId=decisionHistory.reduce((m,r)=>Math.max(m,Number(r.id)||0),0);
          decisionIdCounter=Math.max(Number(payload.decisionIdCounter)||0,maxId+1,1);
        }
        if (payload.debugState && typeof payload.debugState==='object') {
          try { Object.assign(debugState, JSON.parse(JSON.stringify(payload.debugState))); } catch(_) {}
        }
        if (payload.botConfig && typeof payload.botConfig==='object') botConfig={...payload.botConfig};
        if(payload.rawCandleHistory?.byAsset&&typeof payload.rawCandleHistory.byAsset==='object'){for(const [asset,rows] of Object.entries(payload.rawCandleHistory.byAsset)){if(!Array.isArray(rows))continue;const m=new Map((raw5History.byAsset[asset]||[]).map(r=>[Number(r.ts),r]));for(const r of rows){if(r&&Number.isFinite(Number(r.ts)))m.set(Number(r.ts),r);}raw5History.byAsset[asset]=[...m.values()].sort((x,y)=>Number(x.ts)-Number(y.ts));}raw5History.dirty=true;raw5Persist(true);}
        // V24.1.12: RESTORE only restores data. popup.js owns the single
        // explicit XGBoost training request so import cannot start two competing
        // native-host jobs (popup + content script).
        if (Array.isArray(AI_LAB.samples) && AI_LAB.samples.length >= 40 && !AI_LAB.model) {
          AI_LAB.training = {status:'collecting', samples:AI_LAB.samples.length, message:'AI data restored · waiting for native training request…'};
        } else if (AI_LAB.model) {
          AI_LAB.training = {...(AI_LAB.training||{}),status:'trained',samples:AI_LAB.samples.length,message:'Pretrained XGBoost/LightGBM model restored · learning-only'};
        }
        if (Array.isArray(payload.trades)) { tradeRecords.length=0; payload.trades.slice(-TRADE_RECORD_MAX).forEach(t=>tradeRecords.push(t)); }
        if (payload.shadowOutcomes && typeof payload.shadowOutcomes==='object') {
          const so=payload.shadowOutcomes;
          shadowOutcomeState.records=Array.isArray(so.records)?so.records.slice(-SHADOW_OUTCOME_MAX):[];
          if(so.stats&&typeof so.stats==='object') shadowOutcomeState.stats=so.stats;
          if(so.bySetup&&typeof so.bySetup==='object') shadowOutcomeState.bySetup=so.bySetup;
          if(so.byContext&&typeof so.byContext==='object') shadowOutcomeState.byContext=so.byContext;
          shadowOutcomeId=Math.max(Number(so.shadowOutcomeId||1), ...shadowOutcomeState.records.map(r=>Number(r.id||0)+1), 1);
          persistShadowOutcomeState();
        }
        if (payload.shadowHorizonAI && typeof payload.shadowHorizonAI==='object') {
          const mh=payload.shadowHorizonAI;
          if(mh.models&&typeof mh.models==='object') shadowHorizonAI.models=mh.models;
          for(const [h] of SHADOW_HORIZONS) mhEnsureModel(h);
          if(Array.isArray(mh.samples)) shadowHorizonAI.samples=mh.samples.slice(-MH_AI_MAX_SAMPLES);
          if(mh.bySetup&&typeof mh.bySetup==='object') shadowHorizonAI.bySetup=mh.bySetup;
          shadowHorizonAI.updatedAt=Number(mh.updatedAt||0);
          persistShadowHorizonAI();
        }
        const s=payload.session;
        if (s && typeof s==='object') {
          if (typeof s.wins==='number') sessionWins=s.wins; if (typeof s.losses==='number') sessionLosses=s.losses; if (typeof s.pnl==='number') sessionPnl=s.pnl;
          if (typeof s.lossStreak==='number') lossStreak=s.lossStreak; if (typeof s.winStreak==='number') winStreak=s.winStreak;
          if (typeof s.compoundLevel==='number') compoundLevel=s.compoundLevel; if (typeof s.tradeIdCounter==='number') tradeIdCounter=s.tradeIdCounter;
          if (s.lastTradeDir!=null) lastTradeDir=s.lastTradeDir; if (s.lastTradeAsset!=null) lastTradeAsset=s.lastTradeAsset; if (typeof s.lastTradeAmt==='number') lastTradeAmt=s.lastTradeAmt;
        }
        // Manual-only: do not write imported AI to chrome.storage.
        sendResponse({ok:true,v23Trained:V23_AI.trained,legacyTrained:aiState.trained,labeled:aiState.paperLabeled,trained:V23_AI.trained,decisions:decisionHistory.length,trades:tradeRecords.length,xgbSamples:AI_LAB.samples.length});
      } catch(e) { console.error('[AI] Manual restore failed:',e); sendResponse({ok:false,error:e.message||String(e)}); }
      return true;
    }

    if (msg.type === 'GET_AI_LOG') {
      sendResponse({ok:true, events:AI_EVENT_LOG.slice(-Math.min(AI_EVENT_LOG_MAX, Number(msg.limit||500)))});
      return true;
    }

    if (msg.type === 'GET_DEBUG_SNAPSHOT') {
      const asset = activeAsset || '';
      let tfKey = '5s', storageCandles = 0, tfCandles = 0, contextTfKey = null, contextTfCandles = 0;
      if (asset && botConfig) {
        const act = getAsset(asset);
        storageCandles = act.prices.length;
        const slot = botConfig?.strategyEngine==='MIXED_SLOTS' ? strategySlotForAsset(asset) : null;
        const customMode = botConfig?.strategyEngine==='CUSTOM_CONFIRM' || !!slot?.profile;
        if (customMode) {
          const cfg=slot?.profile||botConfig?.strategyProfile||{};
          tfKey=`${Math.max(5,Number(cfg.signalTf)||30)}s`;
          tfCandles=getLiveTFView(act,tfKey).prices.length;
        } else {
          tfKey='5s';
          tfCandles=act.prices.length;
        }
        contextTfKey=expiryToTF(parseInt(botConfig.timeframe||30,10));
        contextTfCandles=getLiveTFView(act,contextTfKey).prices.length;
      }
      const stratDef = STRATEGIES[botConfig?.strategy] || STRATEGIES['Murfs Pick'];
      const min5s = v241WarmupTarget(asset ? getAsset(asset) : null, stratDef.minPrices || 40);
      sendResponse({
        ok: true,
        snapshot: {
          asset, tfKey, storageCandles, tfCandles, contextTfKey, contextTfCandles,
          warmupNeeded: min5s,
          warmupPct: Math.min(100, Math.round((storageCandles / min5s) * 100)),
          running: isRunning,
          strategy: botConfig?.strategy || 'Murfs Pick',
          timeframe: botConfig?.timeframe || 30,
          amount: currentAmount, martLevel, tradePending,
          lastTradeDir, lastTradeAmt,
          wins: sessionWins, losses: sessionLosses, pnl: sessionPnl,
          winStreak, lossStreak, compoundLevel,
          // V24.1.130: per-channel rows feed the popup live debug panel.
          gridAccountIsDemo,
          channels: multiAssetMode ? multiScanAssets().map((a, i) => gridChannelDebugRow(a, i)) : [],
          reason: lastDebugReason,
          indicators: { ...lastIndicators },
          timestamp: Date.now()
        }
      });
      return true;
    }
  });

  // Console-accessible reset — type this in the PAGE console (F12):
  //   window.postMessage({ _poatResetAI: true }, '*')
  // This lets you trigger a model reset without chrome.* API access.
  window.addEventListener('message', (evt) => {
    if (evt.data && evt.data._poatResetAI) {
      try {
        aiState.w1 = aiXavier(AI_FEATURES, AI_FEATURES * AI_HIDDEN);
        aiState.b1 = new Array(AI_HIDDEN).fill(0);
        aiState.w2 = aiXavier(AI_HIDDEN, AI_HIDDEN);
        aiState.b2 = 0;
        aiState.vw1 = new Array(AI_FEATURES * AI_HIDDEN).fill(0);
        aiState.vb1 = new Array(AI_HIDDEN).fill(0);
        aiState.vw2 = new Array(AI_HIDDEN).fill(0);
        aiState.vb2 = 0;
        aiState.trained = 0;
        aiState.correct = 0;
        aiState.total   = 0;
        aiState.paperQueued = 0;
        aiState.paperLabeled = 0;
        aiState.paperCorrect = 0;
        aiState.confEma = 0.5;
        aiState.accEma = 0.5;
        aiState.valCorrect = 0; aiState.valTotal = 0; aiState.valWindow = []; aiState.valAccuracy = 0;
        aiState.valRecent = 0; aiState.marketStats = {};
        aiState.independentSamples = 0;
        aiState.valCorrect = 0; aiState.valTotal = 0; aiState.valWindow = []; aiState.valAccuracy = 0;
        aiState.valRecent = 0; aiState.marketStats = {};
        aiState.independentSamples = 0;
        aiState.valCorrect = 0; aiState.valTotal = 0; aiState.valWindow = []; aiState.valAccuracy = 0;
        aiState.valRecent = 0; aiState.marketStats = {};
        aiState.independentSamples = 0;
        aiState.regimeStats = {};
        aiState.labeledDataset.length = 0;
        aiState.samples.length = 0;
        aiState.lossMemory.length = 0;
        aiState.correctAbstains = 0;
        aiState.marketRanking = {};
        aiState._assetLossStreak = {};
        aiState._marketBanUntil = {};
        aiState._rejected = 0;
        aiState.tradeTypeStats = {};
        aiState._lastBackupAt = 0;
        aiState._lastBackupLabeled = 0;
        aiState._lastLossAt = 0;
        aiState.savePending = false;
        clearTimeout(aiState._saveTimer);
          console.log('[AI] 🧹 Model fully reset — weights zeroed, dataset cleared, storage wiped');
      } catch(e) {
        console.error('[AI] Reset failed:', e);
      }
    }
  });

} catch (e) {
  console.log('[POAT] Extension context unavailable');
}

  // KAOS 1.6.40 — expose a read-only OpenAI shadow snapshot from INSIDE the
  // main content-engine closure. The previous 1.6.38 shadow timer lived outside
  // this closure and could not see isRunning/activeAsset/indicator state.
  window.__KAOS_GET_OPENAI_SNAPSHOT = function(){
    try{
      const asset=String(activeAsset||'');
      if(!asset)return {running:!!isRunning,snapshot:null};
      const a=getAsset(asset)||{};
      const li=(indicatorStateByAsset?.[asset]||lastIndicators||{});
      const decision=li.aiDecisionTrace||li.aiLastDecision||{};
      const n=v=>{v=Number(v);return Number.isFinite(v)?v:null};
      return {running:!!isRunning,snapshot:{
        asset,
        price:n(a.lastPrice||lastTickPrice?.[asset]),
        regime:String(li.regime||decision.regime||'UNKNOWN'),
        strategyDecision:String(decision.finalDecision||decision.strategy||li.strategyDecision?.dir||'HOLD').toUpperCase(),
        indicators:{rsi:n(li.rsi??li.rsi30),stoch:n(li.stoch),ema5:n(li.ema5),ema9:n(li.ema9),ema21:n(li.ema21),macd:n(li.macd),macdSignal:n(li.macdSignal),atr:n(li.atr),marketQuality:n(li.marketQuality)},
        xgboost:li.xgbAI?{direction:li.xgbAI.direction||null,confidence:n(li.xgbAI.confidence),up:n(li.xgbAI.rawUp??li.xgbAI.up)}:null,
        lightgbm:li.xgbAI?{up:n(li.xgbAI.shadowLgbRawUp??li.xgbAI.shadowLgbUp)}:null,
        decisionTs:Number(li.aiLastDecision?.ts||decision.ts||0)||null,
        source:'KAOS_EXTENSION',shadowOnly:true
      }};
    }catch(e){return {running:false,snapshot:null,error:String(e?.message||e)}}
  };

  console.log('[KAOS V21.0] ✓ 64→32→1 LeakyReLU · trade type classifier (REVERSAL/RUNNER/SKIP) · magnitude-tiered labels · gate diagnostics · curB-scope fix · market ranking + per-market risk + full backup + LossMem time-decay · graduated AI gate · reversal-aware RSI · v19.0.6: confEma floor + tradeTypeStats + calib soft mode + LossMem cap');
})();














/* === KAOS v19.2.1 integrated REV/RUN TradeMind feature layer === */
(function(){
"use strict";
const N=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const C=(v,a=0,b=100)=>Math.max(a,Math.min(b,N(v)));
function tr(vals){const x=vals.map(N);return x.length?x[x.length-1]:0;}
function emaAlign(e7,e25,e99){
  const a=N(e7),b=N(e25),c=N(e99);
  return {bull:a>b&&b>c?100:0,bear:a<b&&b<c?100:0};
}
function divergence(p0,p1,o0,o1){
  const dp=N(p1)-N(p0), dO=N(o1)-N(o0);
  return {bull:dp<0&&dO>0?100:0,bear:dp>0&&dO<0?100:0};
}
function candle(c){
  if(!c)return {};
  const o=N(c.open),h=N(c.high),l=N(c.low),cl=N(c.close);
  const body=Math.abs(cl-o), r=Math.max(1e-9,h-l);
  const up=h-Math.max(o,cl), dn=Math.min(o,cl)-l;
  return {
    hammer:dn>body*2&&up<body&&body/r<.5?100:0,
    shootingStar:up>body*2&&dn<body&&body/r<.5?100:0,
    bullEngulf:cl>o?100:0,bearEngulf:cl<o?100:0
  };
}
function build(f){
  f=f||{};
  const rsi=N(f.rsi,50), st=N(f.stochRsi??f.stoch,50);
  const mac=N(f.macdHist,0), mac0=N(f.macdHistPrev,mac);
  const bb=N(f.bbPosition,.5), atr=N(f.atrExpansion,1), mom=N(f.momentum,0);
  const ea=emaAlign(f.ema7,f.ema25,f.ema99);
  const db=divergence(f.prevLow,f.low,f.prevRsi,rsi);
  const ds=divergence(f.prevHigh,f.high,f.prevRsi,rsi);
  const cc=candle(f.candle);
  const revBull=C((rsi<30?22:0)+(st<20?18:0)+db.bull*.22+cc.hammer*.16+(bb<.08?14:0)+(mom>0?10:0));
  const revBear=C((rsi>70?22:0)+(st>80?18:0)+ds.bear*.22+cc.shootingStar*.16+(bb>.92?14:0)+(mom<0?10:0));
  const runBull=C(ea.bull*.30+(mac>0?18:0)+(mac>mac0?14:0)+(atr>1.05?12:0)+(mom>0?16:0)+(bb>.55?10:0));
  const runBear=C(ea.bear*.30+(mac<0?18:0)+(mac<mac0?14:0)+(atr>1.05?12:0)+(mom<0?16:0)+(bb<.45?10:0));
  const mode=Math.max(revBull,revBear)>=Math.max(runBull,runBear)?"REVERSAL":"RUNNER";
  return {revBull,revBear,runBull,runBear,mode,version:"19.2.1"};
}
globalThis.KAOSV193=Object.freeze({build});
})();



/* v19.2.1 integration hook: make REV/RUN feature builder available to the existing
   decision/training pipeline without replacing its existing gates. */
try {
  if (globalThis.KAOSV193) {
    globalThis.dispatchEvent(new CustomEvent("KAOS_REV_RUN_READY",{detail:{version:"19.2.1"}}));
  }
} catch (_) {}



/* === v19.2.2 CLEAN-TRAINING / AI BOOTSTRAP GATE ===
   During early learning, low validation accuracy must not permanently prevent
   the bot from collecting qualified paper-trading examples.
   AI remains advisory; setup/TQS/risk gates still apply.
*/
(function(){
  "use strict";
  const BOOTSTRAP_INDEPENDENT_SAMPLES = 1000;
  const BOOTSTRAP_MIN_CONF = 0.54;
  const BOOTSTRAP_MIN_TQS = 55;

  globalThis.KAOSBootstrapGate = function(state){
    state = state || {};
    const indep = Number(state.indep ?? state.independent ?? state.independentSamples ?? 0) || 0;
    const valAcc = Number(state.valAcc ?? state.validationAcc ?? 0) || 0;
    const tqs = Number(state.tqs ?? state.score ?? 0) || 0;
    const aiConf = Number(state.aiConf ?? state.confidence ?? 0) || 0;

    if (indep < BOOTSTRAP_INDEPENDENT_SAMPLES) {
      return {
        bootstrap: true,
        aiHardBlock: false,
        qualified: tqs >= BOOTSTRAP_MIN_TQS,
        reason: "AI_BOOTSTRAP_ADVISORY",
        independentSamples: indep,
        validationAcc: valAcc,
        aiConfidence: aiConf
      };
    }

    return {
      bootstrap: false,
      aiHardBlock: valAcc > 0 && valAcc < 0.47,
      qualified: true,
      reason: valAcc > 0 && valAcc < 0.47 ? "AI_GATED_MATURE" : "AI_ALLOWED",
      independentSamples: indep,
      validationAcc: valAcc,
      aiConfidence: aiConf
    };
  };
})();


/* v19.2.2: diagnostic event for live debug */
try {
  if (globalThis.KAOSBootstrapGate) {
    globalThis.dispatchEvent(new CustomEvent("KAOS_BOOTSTRAP_READY", {
      detail: {version:"19.2.2", independentThreshold:1000}
    }));
  }
} catch (_) {}


/* === KAOS v19.3.1 — 1000 INDEPENDENT-sample bootstrap policy === */
(function(){
  "use strict";
  globalThis.KAOSV1931Bootstrap = Object.freeze({
    version: "19.3.1",
    independentSampleThreshold: 1000,
    aiHardGateBeforeThreshold: false,
    modeBeforeThreshold: "ADVISORY",
    modeAfterThreshold: "MATURE_GATE",
    counterName: "independentSamples"
  });
})();


/* v19.3.1: canonical independent-sample bootstrap helper.
   Existing training data is preserved. */
function KAOSIndependentBootstrapState(state) {
  try {
    const s = state || {};
    const indep = Number(
      s.independentSamples ?? s.indepSamples ?? s.indep ?? s.independent ?? 0
    );
    const threshold = 1000;
    const bootstrap = Number.isFinite(indep) ? indep < threshold : true;
    return {
      independentSamples: Number.isFinite(indep) ? indep : 0,
      threshold,
      bootstrap,
      aiHardGate: !bootstrap
    };
  } catch (_) {
    return { independentSamples: 0, threshold: 1000, bootstrap: true, aiHardGate: false };
  }
}


/* ================================================================
   KAOS v19.4 — REV/RUN + 1000 INDEPENDENT SAMPLE CONTROL
   ================================================================ */
const KAOS_V194 = Object.freeze({
  version: "19.4.0",
  independentBootstrapThreshold: 1000,
  paperOnly: true,
  revRunLogging: true
});

function KAOSV194IndependentCount(aiState) {
  const s = aiState || {};
  const n = Number(
    s.independentSamples ??
    s.indepSamples ??
    s.indep ??
    s.independent ??
    0
  );
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

function KAOSV194BootstrapState(aiState) {
  const independentSamples = KAOSV194IndependentCount(aiState);
  return {
    independentSamples,
    threshold: 1000,
    bootstrap: independentSamples < 1000,
    aiGateMode: independentSamples < 1000 ? "ADVISORY" : "MATURE"
  };
}

function KAOSV194RevRunSnapshot(x) {
  const v = x || {};
  const rev = Number(v.reversalScore ?? v.revScore ?? 0);
  const run = Number(v.runnerScore ?? v.runScore ?? 0);
  const type = String(v.tradeType ?? v.type ?? "SKIP").toUpperCase();
  return {
    type: type === "REVERSAL" || type === "RUNNER" ? type : "SKIP",
    reversalScore: Number.isFinite(rev) ? rev : 0,
    runnerScore: Number.isFinite(run) ? run : 0,
    direction: String(v.direction ?? v.dir ?? "NONE").toUpperCase()
  };
}


// KAOS 1.6.38 — Pocket Option AI observation layer.
// Observes information rendered/used by the user's own logged-in Pocket Option session.
// It does NOT access or extract Pocket Option's proprietary AI model.
(function KAOS_PO_AI_OBSERVER(){
  if(window.__KAOS_PO_AI_OBSERVER_1636__) return;
  window.__KAOS_PO_AI_OBSERVER_1636__=true;
  const KEY='kaosPoAiShadow';
  let lastSig='', lastAt=0;

  function txt(el){return String(el?.innerText||el?.textContent||'').replace(/\s+/g,' ').trim();}
  function detect(){
    const body=txt(document.body);
    if(!/AI\s*(Trading|Trader)/i.test(body)) return;

    // Search visible AI-related regions/buttons/dialogs for user-visible direction/expiry.
    const nodes=[...document.querySelectorAll('button,[role="button"],[role="dialog"],.modal,.popup,[class*="ai"],[data-testid*="ai"]')];
    let best='';
    for(const n of nodes){
      const t=txt(n);
      if(/AI\s*(Trading|Trader)/i.test(t) && t.length<1800) best += ' '+t;
    }
    best=best.trim();
    if(!best) return;

    const dir=(best.match(/\b(BUY|CALL|UP)\b/i)?.[1]||best.match(/\b(SELL|PUT|DOWN)\b/i)?.[1]||'').toUpperCase();
    const exp=best.match(/\b(5|10|15|30|45|60)\s*(?:s|sec|seconds?)\b/i)?.[1]||'';
    const sig=[dir,exp,best.slice(0,220)].join('|');
    if(sig===lastSig && Date.now()-lastAt<5000) return;
    lastSig=sig; lastAt=Date.now();

    const rec={
      observedAt:Date.now(),
      source:'pocket_option_ui',
      direction: dir ? ({CALL:'BUY',UP:'BUY',PUT:'SELL',DOWN:'SELL'}[dir]||dir) : null,
      expirySec: exp?Number(exp):null,
      visibleText:best.slice(0,500),
      shadowOnly:true
    };
    try{ chrome.storage.local.set({[KEY]:rec}); }catch(_){}
    try{ chrome.runtime.sendMessage({type:'KAOS_PO_AI_SHADOW',payload:rec}); }catch(_){}
  }
  // KAOS 1.6.41 PERFORMANCE: do NOT observe every attribute/text mutation on
  // Pocket Option. Its chart updates mutate the DOM constantly and the old
  // observer responded by rescanning document.body, starving the chart UI.
  // Pocket AI observation is shadow-only, so a low-frequency visible-tab poll
  // plus an immediate user-click probe preserves the feature without chart lag.
  document.addEventListener('click',e=>{
    const t=txt(e.target?.closest?.('button,[role="button"]')||e.target);
    if(/AI\s*(Trading|Trader)/i.test(t)) setTimeout(()=>{if(!document.hidden)detect()},250);
  },true);
  setInterval(()=>{if(!document.hidden)detect()},6000);
})();


// KAOS 1.6.38 — expose the already-existing XGBoost/LightGBM shadow predictions
// to the KAOS AI Intelligence UI. This does not alter signal or execution logic.
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
  if(msg?.type!=='KAOS_GET_AI_INTELLIGENCE') return;
  try{
    const li=(typeof lastIndicators!=='undefined'&&lastIndicators)||{};
    const x=li.xgbAI||{};
    const lgbRaw=Number(x.shadowLgbRawUp ?? x.shadowLgbUp);
    const xgbRaw=Number(x.rawUp ?? x.up ?? x.shadowXgbRawUp ?? x.shadowXgbUp);
    const strategy=String(li.aiDecisionTrace?.strategy||li.aiLastDecision?.strategy||li.strategyDecision?.dir||'WAITING');
    sendResponse({
      ok:true,
      xgbUp:Number.isFinite(xgbRaw)?xgbRaw:null,
      lgbUp:Number.isFinite(lgbRaw)?lgbRaw:null,
      strategy,
      lightgbmExisting:true,
      shadowOnly:true
    });
  }catch(e){sendResponse({ok:false,error:String(e?.message||e)})}
  return true;
});


// KAOS 1.6.40 — REAL OpenAI Brain shadow feed.
// Uses the read-only bridge exported by the live content engine; no closure leaks.
(function KAOS_OPENAI_SHADOW_FEED(){
  if(window.__KAOS_OPENAI_SHADOW_FEED_1640__)return;
  window.__KAOS_OPENAI_SHADOW_FEED_1640__=true;
  let lastDecisionTs=0,lastCall=0,inflight=false;
  async function tick(){
    if(inflight)return;
    const state=window.__KAOS_GET_OPENAI_SNAPSHOT?.();
    if(!state?.running)return;
    const snap=state.snapshot;
    if(!snap?.asset||!snap?.price)return;
    const dts=Number(snap.decisionTs||0);
    if(!dts||dts===lastDecisionTs||Date.now()-lastCall<10000)return;
    lastDecisionTs=dts;lastCall=Date.now();inflight=true;
    try{await chrome.runtime.sendMessage({type:'KAOS_OPENAI_BRAIN',snapshot:snap});}catch(_){}finally{inflight=false}
  }
  setInterval(()=>{if(!document.hidden)tick()},3000);
})();

