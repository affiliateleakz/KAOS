import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CompanionHero, BrokerRoadmap } from "../components/CompanionHomepage";

/* Viking homepage for the compact companion and full broker roadmap. */

const GOLD = "#f0c35d";
const GOLD_DEEP = "#d4a94e";
const GOLD_BORDER = "#6d5522";
const GREEN = "#35d07f";

// Homepage examples describe controls, not additional in-extension chart views.
function PreviewRows({rows}) {
 return <div style={{display:"grid",gap:9}}>{rows.map(([label,value])=><div key={label} style={{display:"flex",justifyContent:"space-between",gap:12,padding:"10px",border:"1px solid #3c3020",borderRadius:5,fontSize:12}}><span style={{color:"#b7ad92"}}>{label}</span><b style={{color:GOLD,textAlign:"right"}}>{value}</b></div>)}</div>;
}
const SYSTEMS = [
 {name:"Broker companion",tag:"YOUR CHARTS STAY WITH YOUR BROKER",visual:<PreviewRows rows={[["Charts","Use your broker"],["Bot controls","Compact panel"],["Start / Stop","Your choice"]]}/>,text:"Keep the broker workspace you already know. KAOS runs beside it as a compact control panel rather than recreating charts inside the extension.",bullets:["Strategy, stake and expiration together","Account and connection status","Compact and expanded views"]},
 {name:"KAOS Strategy",tag:"RULES BEFORE EXECUTION",visual:<PreviewRows rows={[["Strategy","KAOS Strategy"],["Stake","Set by you"],["Expiration","Set by you"]]}/>,text:"Choose your strategy and review its settings before starting. Execution follows the selected strategy and the integration supported by your connected broker.",bullets:["Explicit Start and Stop controls","Review settings before a session","Broker-specific execution"]},
 {name:"Risk controls",tag:"SET YOUR BOUNDARIES",visual:<PreviewRows rows={[["Stake sizing","Configurable"],["Loss limits","Configurable"],["Cooldowns","Configurable"]]}/>,text:"Review stake sizing, loss limits, trade limits and cooldowns in the bot. Risk controls reduce exposure according to your settings; they do not guarantee against losses.",bullets:["Dedicated Risk settings","Clear Demo / Real account labeling","Check open positions at the broker"]},
 {name:"Research tools",tag:"IN YOUR WEBSITE DASHBOARD",visual:<PreviewRows rows={[["Heatmaps","Website workspace"],["News & research","Website workspace"],["AI execution","Validation required"]]}/>,text:"Use the KAOS website for heatmaps, news and research tools included in your membership. Keep the extension focused on bot controls. AI execution remains separately gated by validation.",bullets:["Membership-based research tools","Website dashboard alongside the bot","Research is separate from execution"]},
 {name:"Trade history",tag:"REVIEW YOUR SESSION",visual:<PreviewRows rows={[["Wins / losses","Session statistics"],["Recent trades","Bot activity"],["Broker account","Final confirmation"]]}/>,text:"Review recent bot trades and session statistics. Use the broker’s own orders and positions to verify execution and account outcomes.",bullets:["Recent trade activity","Session wins, losses and P/L","No published profitability claims"]},
];

const FEATURES = [
  { t: "Automated Execution", d: "Start the bot explicitly and manage its activity from the companion. Execution depends on the connected broker and your settings.", icon: "M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" },
  { t: "AI Learning Engine", d: "Research and learning tools support strategy review. AI execution is a separate capability that requires validation before activation.", icon: "M12 3a4 4 0 0 1 4 4c1.2.4 2 1.5 2 2.8 0 .5-.1 1-.4 1.4.9.6 1.4 1.6 1.4 2.8a3.3 3.3 0 0 1-3.3 3.3H14v3h-4v-3H8.3A3.3 3.3 0 0 1 5 14c0-1.2.5-2.2 1.4-2.8-.3-.4-.4-.9-.4-1.4C6 8.5 6.8 7.4 8 7a4 4 0 0 1 4-4Zm0 5v8" },
  { t: "Broker Connections", d: "Explore every supported and planned connection. Each broker has its own integration status and execution requirements.", icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 0c2.5 2.5 3.8 5.7 3.8 9s-1.3 6.5-3.8 9m0-18C9.5 5.5 8.2 8.7 8.2 12s1.3 6.5 3.8 9M3.5 9h17m-17 6h17" },
  { t: "Advanced Risk Management", d: "Stake sizing, daily loss caps, trade limits and cooldowns. Risk controls run alongside every strategy to protect your capital.", icon: "M12 3 5 6v5c0 4.4 3 8.5 7 10 4-1.5 7-5.6 7-10V6l-7-3Zm-2.5 9 2 2 4-4.5" },
  { t: "Cloud Sync", d: "Strategies and KAOS AI data live in your account cloud. Export, import and move your setup between devices without losing progress.", icon: "M7 18a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 8.5 4 4 0 0 1 17.5 18H7Zm5-5v6m0-6-2.5 2.5M12 13l2.5 2.5" },
  { t: "Trade History & Analytics", d: "A complete, timestamped log of every trade with stakes, outcomes and P/L — plus equity curves and streak analytics.", icon: "M4 5h16v14H4zM4 9h16M8 13h8m-8 3h5" },
];

const PLANS = [
  {
    id: "free", name: "Free", price: "$0", per: "/month", note: "Create an account · no card required",
    features: ["KAOS Trading Bot", "KAOS Strategy mode (no AI trading)", "1 website chart", "Paper trading", "Community access", "Works on 1 device"],
    cta: "JOIN FREE", best: false,
  },
  {
    id: "pro", name: "Pro", price: "$49", per: "/month", note: "Billed monthly · cancel any time",
    features: ["KAOS Trading Bot", "KAOS Strategy mode", "Scanners & AI insights", "Up to 4 website charts", "Cloud Strategies", "Works on 3 devices"],
    cta: "GET PRO", best: false,
  },
  {
    id: "ultimate", name: "Ultimate", price: "$149", per: "/month", note: "Billed monthly · cancel any time",
    features: ["Everything in Pro", "KAOS AI & Strategy + AI modes (after independent validation)", "Premium Tools", "Works on 5 devices"],
    cta: "GET ULTIMATE", best: true,
  },
];


const FAQS = [
  { q: "What is the KAOS Trading Bot?", a: "KAOS is an automated trading command center for short-expiration markets. It combines strategy controls, risk settings and session status in a compact extension panel. Charts stay in the broker workspace; broader research tools live on the KAOS website." },
  { q: "Which platform does KAOS work with?", a: "Pocket Option is the currently supported extension trading connection. Coinbase, Kraken, Interactive Brokers, Alpaca, OANDA, Tradier, tastytrade, Binance.US, Charles Schwab and MetaTrader 4/5 are also listed in the roadmap. Their status cards explain what is active and what is planned." },
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
    const ids = ["brokers", "kaos-bot", "features", "pricing", "results", "faq"];
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
    ["KAOS BOT", "kaos-bot"], ["BROKERS", "brokers"], ["FEATURES", "features"], ["PRICING", "pricing"], ["RESULTS", "results"], ["FAQ", "faq"],
  ];

  return (
    <div id="top" style={{ background: "#020303", color: "#e8e2d4", margin: 0 }}>
      <style>{`
        html{scroll-behavior:smooth}
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

      <CompanionHero mainRef={mainRef} />
      <BrokerRoadmap />

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
          {sectionHead("The Command Center", "One Compact Bot. Your Broker’s Workspace.", "Bot controls in the extension. Charts at your broker. Research in your KAOS dashboard.")}
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
            Control summaries describe the interface; they are not live account statistics.
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
            Membership covers the KAOS license, cloud strategies and AI data sync. Broker availability varies by integration. Check the connection roadmap and review your account type and risk limits before trading.
          </p>
        </div>
      </section>

      {/* ============================ RESULTS ============================ */}
      <section id="results" className="kx-section" aria-labelledby="h-results" style={{ padding: "70px 22px", borderTop: "1px solid #17130a", background: "#050403" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          {sectionHead("Results", "Track Your Results", "Full transparency, trade by trade. Wins, losses, streaks and equity — everything KAOS does is logged and visible.")}
          <div className="kx-card" style={{ ...cardStyle, padding: "22px 24px", fontSize: 14, lineHeight: 1.75, color: "#cfc5a8" }}>
            <h3 style={{ margin: "0 0 10px", fontFamily: "'Oswald',sans-serif", fontSize: 16, letterSpacing: ".14em", color: GOLD }}>NO PUBLISHED PERFORMANCE YET</h3>
            <p style={{ margin: "0 0 10px" }}>
              KAOS does not publish win rates, profits or returns until they are independently documented. Any result we publish will state the dates it covers, whether it comes from live, paper or backtest trading, the costs included, and the risks.
            </p>
            <p style={{ margin: 0 }}>
              In the member portal you can track your own paper trading: every order, fill price, open position, cash balance and realized profit or loss is recorded.
            </p>
          </div>
          <div style={{ marginTop: 24, border: `1px solid ${GOLD_BORDER}`, background: "#0d0a05", borderRadius: 12, padding: "16px 20px", fontSize: 12.5, lineHeight: 1.75, color: "#a99f86" }}>
            <b style={{ color: GOLD }}>Performance disclaimer:</b> the interface preview uses test-session data, not live trades or results. Trading short-expiration contracts carries a substantial risk of loss. Past performance, real or simulated, is not indicative of future results. Never trade money you cannot afford to lose.
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
              <a href="/privacy.html" style={{ display: "block", color: "#e9c879", textDecoration: "none", fontSize: 13, marginBottom: 8 }}>Privacy Policy</a>
            </div>
          </nav>
        </div>
        <div style={{ maxWidth: 1180, margin: "28px auto 0", borderTop: "1px solid #17130a", paddingTop: 18 }}>
          <p style={{ margin: "0 0 10px", color: "#5f5845", fontSize: 11, lineHeight: 1.7 }}>
            Risk warning: trading short-expiration contracts involves substantial risk of loss and is not suitable for every investor. Charts on this site are illustrative layouts, not real trades or results. Nothing here is investment advice or a guarantee of results.
          </p>
          <p style={{ margin: 0, color: "#5f5845", fontSize: 11 }}>© 2026 KAOS Trading. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
