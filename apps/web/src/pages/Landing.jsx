import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

/* =====================================================================================
   KAOS TRADING — one-page product site (2.2.0)
   Top of page: the user-approved Viking artwork (/kaos-home-target.png, 1536x1024)
   served pixel-exact, with a transparent hotspot nav overlay.
   Below it: real content sections the navigation scrolls to:
   KAOS BOT, FEATURES, PRICING, RESULTS, FAQ + footer.
   ===================================================================================== */

const GOLD = "#f0c35d";
const GOLD_DEEP = "#d4a94e";
const GOLD_BORDER = "#6d5522";
const GREEN = "#35d07f";
const RED = "#ff5c5c";

/* ---------------------------------------------------------------- helpers ---------- */
const hotspots = [
  // Top navigation bar (percentage coordinates of the 1536x1024 artwork)
  { label: "Home",    left: 30.0, top: 1.0,  width: 5.3,  height: 5.4, href: "#top" },
  { label: "KAOS Bot", left: 36.2, top: 1.0,  width: 7.3,  height: 5.4, href: "#kaos-bot" },
  { label: "Features", left: 44.3, top: 1.0,  width: 7.1,  height: 5.4, href: "#features" },
  { label: "Pricing",  left: 52.2, top: 1.0,  width: 6.6,  height: 5.4, href: "#pricing" },
  { label: "Results",  left: 60.0, top: 1.0,  width: 6.5,  height: 5.4, href: "#results" },
  { label: "FAQ",      left: 67.2, top: 1.0,  width: 5.0,  height: 5.4, href: "#faq" },
  { label: "Login",    left: 76.7, top: 1.2,  width: 8.2,  height: 4.9, to: "/login" },
  { label: "Get KAOS", left: 85.4, top: 1.2,  width: 11.0, height: 4.9, to: "/register" },
  // Hero buttons
  { label: "Get KAOS Trading Bot", left: 6.1,  top: 43.0, width: 24.5, height: 5.7, to: "/register" },
  { label: "Watch Demo",           left: 31.8, top: 43.0, width: 16.6, height: 5.7, href: "#kaos-bot" },
  // Bottom call to action on the artwork
  { label: "Start Trading With KAOS", left: 80.6, top: 92.0, width: 17.2, height: 5.4, to: "/register" },
];

const hotspotStyle = (h) => ({
  position: "absolute",
  left: `${h.left}%`,
  top: `${h.top}%`,
  width: `${h.width}%`,
  height: `${h.height}%`,
  display: "block",
});

/* Deterministic sample series (same every render) */
const CANDLES_A = [
  [40, 55, 30, 50], [50, 62, 44, 58], [58, 60, 40, 46], [46, 70, 42, 66],
  [66, 78, 60, 72], [72, 74, 52, 58], [58, 66, 50, 62], [62, 88, 58, 84],
  [84, 90, 74, 78], [78, 86, 70, 84], [84, 96, 80, 92], [92, 100, 84, 96],
];
const CANDLES_B = [
  [70, 74, 52, 56], [56, 64, 50, 60], [60, 68, 56, 64], [64, 66, 44, 50],
  [50, 58, 44, 54], [54, 62, 48, 58], [58, 72, 56, 68], [68, 70, 58, 62],
  [62, 78, 60, 74], [74, 80, 68, 76], [76, 88, 72, 84], [84, 92, 78, 88],
];

function CandleChart({ data = CANDLES_A, height = 120, w = 300 }) {
  const min = Math.min(...data.map((c) => c[2]));
  const max = Math.max(...data.map((c) => c[1]));
  const span = max - min || 1;
  const step = w / data.length;
  const y = (v) => height - 8 - ((v - min) / span) * (height - 16);
  return (
    <svg viewBox={`0 0 ${w} ${height}`} style={{ width: "100%", height, display: "block" }} preserveAspectRatio="none" aria-hidden="true">
      <line x1="0" y1={height * 0.55} x2={w} y2={height * 0.42} stroke="#3f6fae" strokeWidth="1.4" strokeDasharray="5 4" />
      <line x1="0" y1={height * 0.7} x2={w} y2={height * 0.58} stroke={GOLD_DEEP} strokeWidth="1.4" strokeDasharray="2 4" />
      {data.map((c, i) => {
        const x = i * step + step / 2;
        const up = c[3] >= c[0];
        const col = up ? GREEN : RED;
        const top = y(Math.max(c[0], c[3]));
        const bot = y(Math.min(c[0], c[3]));
        return (
          <g key={i}>
            <line x1={x} y1={y(c[1])} x2={x} y2={y(c[2])} stroke={col} strokeWidth="1.2" />
            <rect x={x - step * 0.28} y={top} width={step * 0.56} height={Math.max(2, bot - top)} fill={col} rx="1" />
          </g>
        );
      })}
    </svg>
  );
}

function MiniLine({ height = 70, rising = true }) {
  const pts = rising
    ? "0,58 20,52 40,55 60,40 80,45 100,32 120,37 140,24 160,29 180,16 200,20 220,10"
    : "0,20 22,26 44,22 66,36 88,32 110,44 132,40 154,52 176,48 200,60";
  const pts2 = rising
    ? "0,40 25,44 50,36 75,42 100,30 125,36 150,26 175,32 200,24"
    : "0,52 25,46 50,50 75,38 100,44 125,32 150,38 175,28 200,34";
  return (
    <svg viewBox="0 0 220 70" preserveAspectRatio="none" style={{ width: "100%", height, display: "block" }} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={GREEN} strokeWidth="2" />
      <polyline points={pts2} fill="none" stroke={RED} strokeWidth="1.6" opacity="0.85" />
    </svg>
  );
}

function EquityCurve({ height = 150 }) {
  const pts = "0,132 60,126 120,128 180,110 240,116 300,92 360,100 420,78 480,86 540,64 600,72 660,50 720,58 780,38 840,46 900,26 960,34 1020,16";
  return (
    <svg viewBox="0 0 1020 150" preserveAspectRatio="none" style={{ width: "100%", height, display: "block" }} aria-hidden="true">
      <defs>
        <linearGradient id="kx-eq" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={GREEN} stopOpacity="0.35" />
          <stop offset="100%" stopColor={GREEN} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,150 ${pts} 1020,150`} fill="url(#kx-eq)" />
      <polyline points={pts} fill="none" stroke={GREEN} strokeWidth="3" />
    </svg>
  );
}

function Toggle({ on = true }) {
  return (
    <span style={{
      width: 34, height: 19, borderRadius: 999, display: "inline-flex", alignItems: "center",
      justifyContent: on ? "flex-end" : "flex-start", padding: 2,
      background: on ? "#12503a" : "#26231c", border: `1px solid ${on ? "#1f7a54" : "#3a362b"}`,
      boxShadow: on ? "0 0 8px rgba(53,208,127,.45)" : "none", flexShrink: 0,
    }}>
      <span style={{ width: 13, height: 13, borderRadius: "50%", background: on ? GREEN : "#6b6553" }} />
    </span>
  );
}

const Kpi = ({ label, value, color = GOLD }) => (
  <div style={{ flex: 1, background: "#0e0c08", border: "1px solid #2c2415", borderRadius: 8, padding: "8px 10px", minWidth: 0 }}>
    <div style={{ fontSize: 9, letterSpacing: ".12em", color: "#8d8266", textTransform: "uppercase", whiteSpace: "nowrap" }}>{label}</div>
    <div style={{ fontSize: 17, fontWeight: 700, color, lineHeight: 1.25, whiteSpace: "nowrap" }}>{value}</div>
  </div>
);

/* ---------------------------------------------------------------- data ------------- */
const SYSTEMS = [
  {
    name: "Dashboard", tag: "REAL-TIME TRADING CONTROL",
    visual: (
      <div>
        <div style={{ display: "flex", gap: 6, marginBottom: 8, fontSize: 10, color: "#b7ad92" }}>
          <span style={{ background: "#141109", border: "1px solid #2c2415", borderRadius: 6, padding: "3px 8px" }}>AUDUSD_otc</span>
          <span style={{ background: "#141109", border: "1px solid #2c2415", borderRadius: 6, padding: "3px 8px" }}>30s</span>
          <span style={{ marginLeft: "auto", color: GREEN }}>AUTO</span>
        </div>
        <CandleChart height={120} />
        <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
          <Kpi label="Win Rate" value="78.6%" />
          <Kpi label="Trades" value="127" />
          <Kpi label="P/L" value="+$542.30" color={GREEN} />
        </div>
      </div>
    ),
    text: "Your mission control. Monitor live markets as they move, fire and manage trades without leaving the screen, and watch performance build in real time — session stats, open positions and account status in one place.",
    bullets: ["Live market feed with candlestick charts", "One-click manual override while the bot runs", "Session, daily and lifetime performance at a glance"],
  },
  {
    name: "KAOS Berserker", tag: "SIGNATURE STRATEGY",
    visual: (
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {[["Timeframe", "30 Seconds"], ["Expiration", "30 Seconds"], ["Continuation Mode", true], ["Reversal Mode", true],
          ["ZigZag 5 / 3 / 1", true], ["Supertrend 3 / 1.75", true], ["Parabolic SAR 0.02 / 0.20", true]].map(([k, v]) => (
          <div key={k} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#0e0c08", border: "1px solid #2c2415", borderRadius: 7, padding: "7px 10px", fontSize: 12 }}>
            <span style={{ color: "#cfc5a8" }}>{k}</span>
            {typeof v === "string"
              ? <span style={{ color: GOLD, fontWeight: 700, fontSize: 11 }}>{v}</span>
              : <Toggle on={v} />}
          </div>
        ))}
      </div>
    ),
    text: "The engine behind KAOS. Berserker reads market structure through ZigZag swings, Supertrend direction and Parabolic SAR to catch continuations and reversals on short expirations — the same confluence logic in STRATEGY and STRATEGY+AI modes.",
    bullets: ["Continuation + reversal entry engines, independently toggleable", "Tunable indicator stack: ZigZag, Supertrend, Parabolic SAR", "Built for fast expirations on OTC and live pairs"],
  },
  {
    name: "Multi-Chart", tag: "TRADE MULTIPLE MARKETS",
    visual: (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {["AUDUSD_otc", "EURNZD_otc", "GBPUSD_otc", "BTCUSD_otc"].map((m, i) => (
          <div key={m} style={{ background: "#0e0c08", border: "1px solid #2c2415", borderRadius: 8, padding: "6px 8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "#b7ad92", marginBottom: 4 }}>
              <span>{m}</span><span style={{ color: GOLD }}>30s</span>
            </div>
            <MiniLine rising={i % 2 === 0} height={58} />
          </div>
        ))}
      </div>
    ),
    text: "Run up to four markets side by side and let the bot hunt setups on each of them simultaneously. Forex, crypto, indices and OTC pairs can be mixed freely — each channel keeps its own strategy settings and trade log.",
    bullets: ["Forex · Crypto · Indices · OTC", "Independent per-market strategy channels", "Concurrent entries with per-channel risk limits"],
  },
  {
    name: "KAOS AI", tag: "LEARN · ANALYZE · IMPROVE",
    visual: (
      <div>
        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          <Kpi label="Trained Samples" value="25,287" />
          <Kpi label="Accuracy" value="61.5%" color={GREEN} />
          <Kpi label="Holdout" value="59.5%" color={GREEN} />
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 64, marginBottom: 8 }}>
          {[34, 46, 42, 60, 55, 70, 66, 81, 77, 95].map((h, i) => (
            <span key={i} style={{ flex: 1, height: `${h}%`, background: `linear-gradient(180deg,${GREEN},${GREEN}55)`, borderRadius: 3 }} />
          ))}
        </div>
        <div style={{ fontSize: 11, lineHeight: 1.9, color: "#cfc5a8" }}>
          <div><b style={{ color: GREEN }}>Trade Win</b> — Added to model</div>
          <div><b style={{ color: RED }}>Trade Loss</b> — Added to model</div>
          <div><b style={{ color: GOLD }}>Pattern Match</b> — High probability setup</div>
        </div>
      </div>
    ),
    text: "A self-learning layer that studies every settled trade — wins and losses — and refines its pattern library continuously. With a membership you can run pure AI mode or fuse it with Berserker in STRATEGY+AI mode, and export/import your AI data to move it between machines.",
    bullets: ["Learns from every settled trade, on your own account", "Out-of-sample holdout accuracy shown, not just training fit", "Export / Import AI data — your model, your data"],
  },
  {
    name: "Performance", tag: "TRACK YOUR RESULTS",
    visual: (
      <div>
        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          <Kpi label="Win Rate" value="78.6%" color={GREEN} />
          <Kpi label="Total Trades" value="127" />
          <Kpi label="P/L" value="+$542.30" color={GREEN} />
        </div>
        <EquityCurve height={92} />
      </div>
    ),
    text: "Detailed statistics, full trade history and performance analytics. Every entry is timestamped and graded, so you always know exactly what the bot did, when, and why — with the numbers to back it up.",
    bullets: ["Trade-by-trade history with stakes and outcomes", "Equity curve, streaks and best/worst trade tracking", "Export your stats any time — full transparency"],
  },
];

const FEATURES = [
  { t: "Automated Execution", d: "KAOS watches the markets and executes 24/7 without emotion, hesitation or fatigue — the plan you set is the plan that trades.", icon: "M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" },
  { t: "AI Learning Engine", d: "Every settled trade feeds the model. KAOS AI constantly re-trains on real outcomes from your own account, not stale backtests.", icon: "M12 3a4 4 0 0 1 4 4c1.2.4 2 1.5 2 2.8 0 .5-.1 1-.4 1.4.9.6 1.4 1.6 1.4 2.8a3.3 3.3 0 0 1-3.3 3.3H14v3h-4v-3H8.3A3.3 3.3 0 0 1 5 14c0-1.2.5-2.2 1.4-2.8-.3-.4-.4-.9-.4-1.4C6 8.5 6.8 7.4 8 7a4 4 0 0 1 4-4Zm0 5v8" },
  { t: "Multi-Market Ready", d: "Forex, crypto, indices and OTC — trade several markets at once with independent strategy channels per market.", icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 0c2.5 2.5 3.8 5.7 3.8 9s-1.3 6.5-3.8 9m0-18C9.5 5.5 8.2 8.7 8.2 12s1.3 6.5 3.8 9M3.5 9h17m-17 6h17" },
  { t: "Advanced Risk Management", d: "Stake sizing, daily loss caps, trade limits and cooldowns. Risk controls run alongside every strategy to protect your capital.", icon: "M12 3 5 6v5c0 4.4 3 8.5 7 10 4-1.5 7-5.6 7-10V6l-7-3Zm-2.5 9 2 2 4-4.5" },
  { t: "Cloud Sync", d: "Strategies and KAOS AI data live in your account cloud. Export, import and move your setup between devices without losing progress.", icon: "M7 18a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 8.5 4 4 0 0 1 17.5 18H7Zm5-5v6m0-6-2.5 2.5M12 13l2.5 2.5" },
  { t: "Trade History & Analytics", d: "A complete, timestamped log of every trade with stakes, outcomes and P/L — plus equity curves and streak analytics.", icon: "M4 5h16v14H4zM4 9h16M8 13h8m-8 3h5" },
];

const PLANS = [
  {
    id: "free", name: "Free", price: "$0", per: "/month", note: "Create an account · no card required",
    features: ["KAOS Trading Bot", "KAOS Strategy mode (no AI trading)", "Paper trading", "Community access", "Works on 1 device"],
    cta: "JOIN FREE", best: false,
  },
  {
    id: "pro", name: "Pro", price: "$49", per: "/month", note: "Billed monthly · cancel any time",
    features: ["KAOS Trading Bot", "KAOS Strategy mode", "Scanners & AI insights", "Cloud Strategies", "Works on 3 devices"],
    cta: "GET PRO", best: false,
  },
  {
    id: "ultimate", name: "Ultimate", price: "$149", per: "/month", note: "Billed monthly · cancel any time",
    features: ["Everything in Pro", "KAOS AI mode", "Strategy + AI mode", "Premium Tools", "Works on 5 devices"],
    cta: "GET ULTIMATE", best: true,
  },
];

const TRADES = [
  ["19:42", "AUDUSD_otc", "CALL", "50", "WIN", "+41.50"],
  ["19:38", "GBPUSD_otc", "PUT", "50", "LOSS", "-50.00"],
  ["19:35", "BTCUSD_otc", "CALL", "25", "WIN", "+20.75"],
  ["19:32", "EURNZD_otc", "CALL", "50", "WIN", "+40.00"],
  ["19:28", "AUDUSD_otc", "PUT", "50", "WIN", "+39.00"],
  ["19:24", "DOGE_otc", "CALL", "25", "LOSS", "-25.00"],
  ["19:20", "EURJPY_otc", "PUT", "50", "WIN", "+42.50"],
  ["19:16", "GBPUSD_otc", "CALL", "50", "WIN", "+38.00"],
];

const FAQS = [
  { q: "What is the KAOS Trading Bot?", a: "KAOS is an automated trading command center for short-expiration markets. It combines the KAOS Berserker strategy engine, a self-learning AI layer, multi-market charts and full risk management in one place — you set the rules, KAOS executes them around the clock without emotion." },
  { q: "Which platform does KAOS work with?", a: "KAOS works with Pocket Option. The bot trades on your own Pocket Option account — demo or real — exactly as you have it selected in Pocket Option. KAOS never moves your funds anywhere else." },
  { q: "How does KAOS AI learn?", a: "Every settled trade — win or loss — is added to the model, and KAOS AI re-trains continuously on those real outcomes. It also shows out-of-sample holdout accuracy so you can judge performance honestly, and you can export or import your AI data at any time. Your bot, your data." },
  { q: "Do I need trading experience?", a: "No. KAOS ships with the Berserker strategy pre-configured, so you can start with defaults, watch how it behaves and tune timeframe, expiration, indicators and risk limits as you get comfortable." },
  { q: "What do I get with membership?", a: "Membership unlocks the bot, cloud strategies and the community. All plans are billed monthly. Free gives you the KAOS bot in Strategy mode on 1 device, plus paper trading and the community — AI trading is not included. Pro adds the bot with KAOS Strategy mode, scanners and AI insights on 3 devices. Ultimate adds KAOS AI mode, Strategy + AI mode, Premium Tools and 5 devices." },
  { q: "Can I use KAOS on multiple devices?", a: "Yes. Pro members can run KAOS on up to 3 devices, Ultimate members on up to 5. Your strategies, stats and AI data stay in sync through your account." },
  { q: "Where is my data stored?", a: "Your strategies and AI data belong to your account and can be exported at any time. KAOS is built around one principle: your bot, your data, your KAOS." },
  { q: "Is trading risky?", a: "Yes — and we won't pretend otherwise. Short-expiration trading carries a substantial risk of loss. KAOS is a tool that executes strategy and risk rules consistently; it does not guarantee profit. Never trade money you cannot afford to lose, and consider starting on a demo account." },
];

/* ---------------------------------------------------------------- page ------------- */
const sectionHead = (kicker, title, sub) => (
  <div style={{ textAlign: "center", maxWidth: 860, margin: "0 auto 42px" }}>
    <div style={{ fontSize: 12, letterSpacing: ".35em", color: GOLD_DEEP, marginBottom: 12, textTransform: "uppercase" }}>{kicker}</div>
    <h2 style={{ margin: 0, fontFamily: "'Oswald','Inter',sans-serif", fontSize: "clamp(28px,3.4vw,44px)", lineHeight: 1.12, letterSpacing: ".02em", color: "#f3ead2", textTransform: "uppercase" }}>{title}</h2>
    {sub && <p style={{ margin: "14px auto 0", color: "#a99f86", fontSize: 15, lineHeight: 1.7 }}>{sub}</p>}
  </div>
);

const cardStyle = {
  background: "linear-gradient(180deg,#100e09,#0a0906)",
  border: `1px solid ${GOLD_BORDER}`,
  borderRadius: 14,
  boxShadow: "0 18px 50px rgba(0,0,0,.55), inset 0 1px 0 rgba(240,195,93,.08)",
};

export default function Landing() {
  const [sticky, setSticky] = useState(false);
  const [active, setActive] = useState("");
  const [openFaq, setOpenFaq] = useState(0);
  const mainRef = useRef(null);

  /* Sticky nav visibility + active section tracking */
  useEffect(() => {
    const ids = ["kaos-bot", "features", "pricing", "results", "faq"];
    const onScroll = () => {
      const hero = document.getElementById("kx-hero");
      const gate = hero ? hero.offsetTop + hero.offsetHeight * 0.75 : 400;
      setSticky(window.scrollY > gate);
      let cur = "";
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= 140) cur = id;
      }
      setActive(cur);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* Handle deep-link hashes after React mounts */
  useEffect(() => {
    const jump = () => {
      const { hash } = window.location;
      if (!hash) return;
      const el = document.getElementById(hash.slice(1));
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    const t = setTimeout(jump, 80);
    window.addEventListener("hashchange", jump);
    return () => { clearTimeout(t); window.removeEventListener("hashchange", jump); };
  }, []);

  const navLinks = [
    ["KAOS BOT", "kaos-bot"], ["FEATURES", "features"], ["PRICING", "pricing"], ["RESULTS", "results"], ["FAQ", "faq"],
  ];

  return (
    <div id="top" style={{ background: "#020303", color: "#e8e2d4", margin: 0 }}>
      <style>{`
        html{scroll-behavior:smooth}
        .k-hotspot:focus-visible{outline:2px solid ${GOLD};outline-offset:2px}
        .kx-section{scroll-margin-top:74px}
        .kx-navlink{position:relative;padding:6px 2px;color:#d9d0b8;text-decoration:none;font-size:12.5px;letter-spacing:.14em;white-space:nowrap;transition:color .2s}
        .kx-navlink:hover{color:${GOLD}}
        .kx-navlink.active{color:${GOLD}}
        .kx-navlink.active:after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:${GOLD};border-radius:2px}
        .kx-card{transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease}
        .kx-card:hover{transform:translateY(-4px);border-color:${GOLD_DEEP};box-shadow:0 22px 60px rgba(0,0,0,.6),0 0 0 1px rgba(240,195,93,.15)}
        .kx-cta{display:inline-flex;align-items:center;gap:10px;background:linear-gradient(180deg,#f4cd6d,#c9963a);color:#1c1204;font-weight:800;letter-spacing:.08em;border-radius:10px;padding:14px 26px;text-decoration:none;box-shadow:0 10px 26px rgba(212,169,78,.35);transition:transform .2s,box-shadow .2s}
        .kx-cta:hover{transform:translateY(-2px);box-shadow:0 14px 32px rgba(212,169,78,.5)}
        .kx-ghost{display:inline-flex;align-items:center;gap:10px;border:1px solid ${GOLD_BORDER};color:#e9dfc4;border-radius:10px;padding:14px 26px;text-decoration:none;letter-spacing:.08em;font-weight:600;background:rgba(20,17,9,.6);transition:border-color .2s,color .2s}
        .kx-ghost:hover{border-color:${GOLD};color:${GOLD}}
        details summary::-webkit-details-marker{display:none}
      `}</style>

      {/* ============================ HERO — exact approved artwork ============================ */}
      <main ref={mainRef} id="kx-hero" aria-label="KAOS Trading Bot" style={{ margin: 0, background: "#020303", position: "relative", lineHeight: 0 }}>
        <div style={{ position: "relative", width: "100%", minWidth: 700 }}>
          <img
            src="/kaos-home-target.png"
            alt="KAOS Trading Bot — Trade With KAOS. Automated, intelligent, relentless: real market strategies, AI powered learning, multi-market support and risk management in one command center."
            style={{ display: "block", width: "100%", height: "auto", userSelect: "none" }}
            draggable={false}
          />
          <span id="systems" aria-hidden="true" style={{ position: "absolute", left: 0, top: "54%", width: 1, height: 1 }} />
          <nav aria-label="Homepage navigation" style={{ position: "absolute", inset: 0, lineHeight: "normal" }}>
            {hotspots.map((h) =>
              h.to ? (
                <Link key={h.label} to={h.to} aria-label={h.label} className="k-hotspot" style={hotspotStyle(h)} />
              ) : (
                <a key={h.label} href={h.href} aria-label={h.label} className="k-hotspot" style={hotspotStyle(h)} />
              )
            )}
          </nav>
        </div>
      </main>

      {/* ============================ STICKY MINI-NAV ============================ */}
      <div
        aria-hidden={!sticky}
        style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 60,
          transform: sticky ? "translateY(0)" : "translateY(-110%)",
          transition: "transform .3s ease",
          background: "rgba(4,3,2,.92)", borderBottom: `1px solid ${GOLD_BORDER}`,
          backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
        }}
      >
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "10px 20px", display: "flex", alignItems: "center", gap: 22 }}>
          <a href="#top" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", flexShrink: 0 }}>
            <img src="/kaos-viking.png" alt="" style={{ width: 30, height: 30, objectFit: "contain" }} />
            <span style={{ fontFamily: "'Oswald',sans-serif", color: GOLD, letterSpacing: ".16em", fontSize: 14, fontWeight: 700 }}>KAOS TRADING</span>
          </a>
          <nav aria-label="Section navigation" style={{ display: "flex", gap: 18, overflowX: "auto", scrollbarWidth: "none", marginLeft: 4 }}>
            {navLinks.map(([label, id]) => (
              <a key={id} href={`#${id}`} className={`kx-navlink${active === id ? " active" : ""}`}>{label}</a>
            ))}
          </nav>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
            <Link to="/login" className="kx-navlink">LOGIN</Link>
            <Link to="/register" style={{ background: "linear-gradient(180deg,#f4cd6d,#c9963a)", color: "#1c1204", fontWeight: 800, fontSize: 12.5, letterSpacing: ".1em", padding: "9px 18px", borderRadius: 8, textDecoration: "none", whiteSpace: "nowrap" }}>GET KAOS →</Link>
          </div>
        </div>
      </div>

      {/* ============================ KAOS BOT ============================ */}
      <section id="kaos-bot" className="kx-section" aria-labelledby="h-bot" style={{ padding: "86px 22px 70px", background: "linear-gradient(180deg,#020303,#070604 40%,#020303)" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          {sectionHead("The Command Center", "5 Powerful Systems. 1 Complete Trading Command Center.", "Everything KAOS does, in one place — from watching the market to learning from every single trade. Here is what each system does and why it matters.")}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 22 }}>
            {SYSTEMS.map((s, i) => (
              <article key={s.name} className="kx-card" style={{ ...cardStyle, padding: "22px 20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
                <header>
                  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
                    <h3 style={{ margin: 0, fontFamily: "'Oswald',sans-serif", fontSize: 23, letterSpacing: ".06em", color: GOLD, textTransform: "uppercase" }}>{s.name}</h3>
                    <span style={{ fontSize: 9.5, letterSpacing: ".18em", color: "#8d8266" }}>0{i + 1}</span>
                  </div>
                  <div style={{ fontSize: 10.5, letterSpacing: ".22em", color: "#a99f86", marginTop: 4 }}>{s.tag}</div>
                </header>
                <div style={{ background: "#070604", border: "1px solid #241e11", borderRadius: 10, padding: 10 }}>{s.visual}</div>
                <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.75, color: "#c9c0a8" }}>{s.text}</p>
                <ul style={{ margin: "auto 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 7 }}>
                  {s.bullets.map((b) => (
                    <li key={b} style={{ display: "flex", gap: 9, fontSize: 12.5, color: "#b7ad92", lineHeight: 1.5 }}>
                      <span style={{ color: GREEN, fontWeight: 800 }}>✓</span>{b}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
          <p style={{ textAlign: "center", color: "#6f6753", fontSize: 11.5, marginTop: 22 }}>
            Interface previews use sample data from the KAOS demo environment.
          </p>
        </div>
      </section>

      {/* ============================ FEATURES ============================ */}
      <section id="features" className="kx-section" aria-labelledby="h-feat" style={{ padding: "70px 22px", borderTop: `1px solid #17130a`, background: "#050403" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          {sectionHead("Features", "Built To Trade While You Don't", "Every layer of KAOS exists for one reason: execute a consistent plan, learn from real outcomes, and keep risk under control.")}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(290px,1fr))", gap: 18 }}>
            {FEATURES.map((f) => (
              <div key={f.t} className="kx-card" style={{ ...cardStyle, padding: "22px 22px 24px" }}>
                <div style={{ width: 46, height: 46, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(180deg,#1c1608,#0e0b06)", border: `1px solid ${GOLD_BORDER}`, marginBottom: 14 }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={GOLD} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={f.icon} /></svg>
                </div>
                <h3 style={{ margin: "0 0 8px", fontFamily: "'Oswald',sans-serif", fontSize: 18, letterSpacing: ".05em", color: "#f3ead2", textTransform: "uppercase" }}>{f.t}</h3>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.75, color: "#b3aa92" }}>{f.d}</p>
              </div>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 34 }}>
            <Link to="/register" className="kx-cta">GET KAOS TRADING BOT →</Link>
          </div>
        </div>
      </section>

      {/* ============================ PRICING ============================ */}
      <section id="pricing" className="kx-section" aria-labelledby="h-pricing" style={{ padding: "80px 22px", background: "linear-gradient(180deg,#020303,#0a0805 50%,#020303)" }}>
        <div style={{ maxWidth: 1020, margin: "0 auto" }}>
          {sectionHead("Membership", "Choose Your KAOS Membership", "Monthly memberships. Upgrade, downgrade or cancel from your dashboard at any time.")}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 24, alignItems: "stretch" }}>
            {PLANS.map((p) => (
              <div key={p.id} className="kx-card" style={{ ...cardStyle, position: "relative", padding: "30px 28px 28px", display: "flex", flexDirection: "column", borderColor: p.best ? GOLD_DEEP : GOLD_BORDER, boxShadow: p.best ? "0 0 0 1px rgba(240,195,93,.25), 0 24px 60px rgba(0,0,0,.6)" : cardStyle.boxShadow }}>
                {p.best && (
                  <div style={{ position: "absolute", top: -13, left: "50%", transform: "translateX(-50%)", background: "linear-gradient(180deg,#f4cd6d,#c9963a)", color: "#1c1204", fontWeight: 800, fontSize: 10.5, letterSpacing: ".18em", padding: "6px 14px", borderRadius: 999, whiteSpace: "nowrap" }}>
                    MOST POWERFUL
                  </div>
                )}
                <h3 style={{ margin: 0, fontFamily: "'Oswald',sans-serif", fontSize: 21, letterSpacing: ".12em", color: GOLD }}>{p.name.toUpperCase()}</h3>
                <div style={{ display: "flex", alignItems: "baseline", gap: 6, margin: "14px 0 4px" }}>
                  <span style={{ fontFamily: "'Oswald',sans-serif", fontSize: 52, fontWeight: 700, color: "#f3ead2", lineHeight: 1 }}>{p.price}</span>
                  <span style={{ color: "#8d8266", fontSize: 14 }}>{p.per}</span>
                </div>
                <div style={{ color: "#8d8266", fontSize: 12.5, marginBottom: 20 }}>{p.note}</div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 11, marginBottom: 26 }}>
                  {p.features.map((f) => (
                    <li key={f} style={{ display: "flex", gap: 10, fontSize: 13.5, color: "#cfc5a8", alignItems: "flex-start" }}>
                      <span style={{ color: GREEN, fontWeight: 800, lineHeight: 1.4 }}>✓</span>{f}
                    </li>
                  ))}
                </ul>
                <Link to="/register" className="kx-cta" style={{ marginTop: "auto", justifyContent: "center" }}>{p.cta} →</Link>
              </div>
            ))}
          </div>
          <p style={{ textAlign: "center", color: "#6f6753", fontSize: 12, marginTop: 26, lineHeight: 1.7 }}>
            Membership covers the KAOS license, cloud strategies and AI data sync. The bot trades on your own Pocket Option account — demo or real, your choice, always under your risk limits.
          </p>
        </div>
      </section>

      {/* ============================ RESULTS ============================ */}
      <section id="results" className="kx-section" aria-labelledby="h-results" style={{ padding: "70px 22px", borderTop: "1px solid #17130a", background: "#050403" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          {sectionHead("Results", "Track Your Results", "Full transparency, trade by trade. Wins, losses, streaks and equity — everything KAOS does is logged and visible.")}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 22 }}>
            <Kpi label="Win Rate" value="78.6%" color={GREEN} />
            <Kpi label="Total Trades" value="127" />
            <Kpi label="Wins" value="100" color={GREEN} />
            <Kpi label="Losses" value="24" color={RED} />
            <Kpi label="Win Streak" value="8" />
            <Kpi label="Best Trade" value="+$25.60" color={GREEN} />
            <Kpi label="P / L" value="+$542.30" color={GREEN} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1.4fr))", gap: 22 }}>
            <div className="kx-card" style={{ ...cardStyle, padding: "20px 20px 22px" }}>
              <h3 style={{ margin: "0 0 12px", fontFamily: "'Oswald',sans-serif", fontSize: 16, letterSpacing: ".14em", color: GOLD }}>EQUITY CURVE</h3>
              <EquityCurve height={170} />
              <div style={{ display: "flex", justifyContent: "space-between", color: "#6f6753", fontSize: 10.5, marginTop: 8 }}>
                <span>SESSION START</span><span style={{ color: GREEN }}>+ $542.30</span>
              </div>
            </div>
            <div className="kx-card" style={{ ...cardStyle, padding: "20px 20px 22px" }}>
              <h3 style={{ margin: "0 0 12px", fontFamily: "'Oswald',sans-serif", fontSize: 16, letterSpacing: ".14em", color: GOLD }}>TRADE HISTORY</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 340 }}>
                  <thead>
                    <tr style={{ color: "#8d8266", textAlign: "left", fontSize: 10, letterSpacing: ".14em" }}>
                      {["TIME", "MARKET", "DIR", "STAKE", "RESULT", "P/L"].map((h) => <th key={h} style={{ padding: "6px 8px", borderBottom: "1px solid #2c2415" }}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {TRADES.map((r, i) => (
                      <tr key={i} style={{ color: "#cfc5a8" }}>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e", whiteSpace: "nowrap" }}>{r[0]}</td>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e", whiteSpace: "nowrap" }}>{r[1]}</td>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e", color: r[2] === "CALL" ? GREEN : RED, fontWeight: 700 }}>{r[2]}</td>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e" }}>${r[3]}</td>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e", color: r[4] === "WIN" ? GREEN : RED, fontWeight: 700 }}>{r[4]}</td>
                        <td style={{ padding: "7px 8px", borderBottom: "1px solid #1c180e", color: r[5].startsWith("+") ? GREEN : RED, fontWeight: 700, whiteSpace: "nowrap" }}>{r[5]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="kx-card" style={{ ...cardStyle, padding: "20px 20px 22px", gridColumn: "1/-1" }}>
              <h3 style={{ margin: "0 0 12px", fontFamily: "'Oswald',sans-serif", fontSize: 16, letterSpacing: ".14em", color: GOLD }}>KAOS AI ACTIVITY</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 10, fontSize: 12.5, color: "#cfc5a8" }}>
                {[["19:42", "Trade Win", GREEN, "Added to model"], ["19:38", "Trade Loss", RED, "Added to model"], ["19:35", "Market Update", GOLD, "New data processed"], ["19:32", "Pattern Match", GOLD, "High probability setup"]].map(([t, k, c, d]) => (
                  <div key={t} style={{ display: "flex", gap: 10, background: "#0e0c08", border: "1px solid #2c2415", borderRadius: 8, padding: "10px 12px", alignItems: "center" }}>
                    <span style={{ color: "#6f6753", fontVariantNumeric: "tabular-nums" }}>{t}</span>
                    <span style={{ color: c, fontWeight: 700 }}>{k}</span>
                    <span style={{ color: "#8d8266", marginLeft: "auto", textAlign: "right" }}>{d}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div style={{ marginTop: 24, border: `1px solid ${GOLD_BORDER}`, background: "#0d0a05", borderRadius: 12, padding: "16px 20px", fontSize: 12.5, lineHeight: 1.75, color: "#a99f86" }}>
            <b style={{ color: GOLD }}>Performance disclaimer:</b> the figures on this page are sample data from the KAOS demo environment, shown to illustrate the reporting you get — they are not a promise of results. Trading short-expiration contracts carries a substantial risk of loss. Past performance, real or simulated, is not indicative of future results. Never trade money you cannot afford to lose.
          </div>
        </div>
      </section>

      {/* ============================ FAQ ============================ */}
      <section id="faq" className="kx-section" aria-labelledby="h-faq" style={{ padding: "80px 22px", background: "linear-gradient(180deg,#020303,#080604 60%,#020303)" }}>
        <div style={{ maxWidth: 860, margin: "0 auto" }}>
          {sectionHead("Support", "Frequently Asked Questions", "Everything traders usually ask before getting started with KAOS.")}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {FAQS.map((f, i) => {
              const open = openFaq === i;
              return (
                <div key={f.q} className="kx-card" style={{ ...cardStyle, overflow: "hidden" }}>
                  <button
                    onClick={() => setOpenFaq(open ? -1 : i)}
                    aria-expanded={open}
                    aria-controls={`faq-panel-${i}`}
                    style={{ width: "100%", display: "flex", alignItems: "center", gap: 14, background: "none", border: 0, cursor: "pointer", padding: "18px 22px", textAlign: "left" }}
                  >
                    <span style={{ color: GOLD, fontWeight: 800, fontSize: 13, flexShrink: 0 }}>{String(i + 1).padStart(2, "0")}</span>
                    <span style={{ flex: 1, color: "#f0e8d2", fontWeight: 600, fontSize: 15 }}>{f.q}</span>
                    <span style={{ color: GOLD, fontSize: 18, transform: open ? "rotate(45deg)" : "none", transition: "transform .2s", flexShrink: 0 }}>+</span>
                  </button>
                  {open && (
                    <div id={`faq-panel-${i}`} style={{ padding: "0 22px 20px 52px", color: "#b3aa92", fontSize: 13.5, lineHeight: 1.8 }}>
                      {f.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ textAlign: "center", marginTop: 36 }}>
            <Link to="/register" className="kx-cta">START TRADING WITH KAOS →</Link>
          </div>
        </div>
      </section>

      {/* ============================ FOOTER ============================ */}
      <footer style={{ borderTop: `1px solid ${GOLD_BORDER}`, background: "#040302", padding: "44px 22px 30px" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto", display: "flex", flexWrap: "wrap", gap: 30, justifyContent: "space-between" }}>
          <div style={{ minWidth: 240 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <img src="/kaos-viking.png" alt="" style={{ width: 34, height: 34, objectFit: "contain" }} />
              <div>
                <div style={{ fontFamily: "'Oswald',sans-serif", color: GOLD, letterSpacing: ".14em", fontWeight: 700, fontSize: 15 }}>KAOS TRADING</div>
                <div style={{ fontSize: 9.5, letterSpacing: ".3em", color: "#8d8266" }}>TRADE WITH KAOS</div>
              </div>
            </div>
            <p style={{ margin: 0, color: "#8d8266", fontSize: 12, lineHeight: 1.7, maxWidth: 320 }}>Your bot. Your data. Your KAOS — one command center for the KAOS Trading Bot, KAOS AI, private trading statistics and affiliate earnings.</p>
          </div>
          <nav aria-label="Footer" style={{ display: "flex", gap: 42, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 10.5, letterSpacing: ".22em", color: GOLD_DEEP, marginBottom: 12 }}>SECTIONS</div>
              {[["KAOS Bot", "kaos-bot"], ["Features", "features"], ["Pricing", "pricing"], ["Results", "results"], ["FAQ", "faq"]].map(([l, id]) => (
                <a key={id} href={`#${id}`} style={{ display: "block", color: "#b3aa92", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>{l}</a>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 10.5, letterSpacing: ".22em", color: GOLD_DEEP, marginBottom: 12 }}>ACCOUNT</div>
              <Link to="/login" style={{ display: "block", color: "#b3aa92", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Login</Link>
              <Link to="/register" style={{ display: "block", color: "#b3aa92", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Get KAOS</Link>
              <Link to="/dashboard" style={{ display: "block", color: "#b3aa92", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Dashboard</Link>
              <Link to="/dashboard/affiliate" style={{ display: "block", color: "#b3aa92", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Affiliates</Link>
              <a href="/privacy/" style={{ display: "block", color: "#e9c879", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Privacy Policy</a>
            </div>
          </nav>
        </div>
        <div style={{ maxWidth: 1180, margin: "28px auto 0", borderTop: "1px solid #17130a", paddingTop: 18 }}>
          <p style={{ margin: "0 0 10px", color: "#5f5845", fontSize: 11, lineHeight: 1.7 }}>
            Risk warning: trading short-expiration contracts involves substantial risk of loss and is not suitable for every investor. Sample figures shown on this site come from the KAOS demo environment and do not constitute investment advice or a guarantee of results.
          </p>
          <p style={{ margin: 0, color: "#5f5845", fontSize: 11 }}>© 2026 KAOS Trading. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
