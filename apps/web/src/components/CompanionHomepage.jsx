import React from "react";
import { Link } from "react-router-dom";
import "./CompanionHomepage.css";

export const BROKER_ROADMAP = [
  ["Pocket Option", "Short-expiration trading", "Supported", "The current KAOS extension connects to Pocket Option. Keep its charts open and manage the bot, strategy, stake and risk in the companion."],
  ["Coinbase", "Crypto", "Trading planned", "Coinbase connection and research groundwork exists. Automated trading through the extension is not active; broker-specific execution remains to be completed."],
  ["Kraken", "Crypto", "Planned", "A future crypto connection in the KAOS broker selector. Account connection, market data and order handling still need integration."],
  ["Interactive Brokers", "Stocks, options, futures & FX", "Planned", "Planned access to a broader range of markets. Instruments and trading permissions will depend on the completed adapter and your broker account."],
  ["Alpaca", "Stocks, ETFs & crypto", "Planned", "Market-data and research components exist. A working research feed does not mean automated extension trading is available."],
  ["OANDA", "Foreign exchange", "Planned", "A planned FX connection. Account permissions, region, order sizes and protective orders need broker-specific handling."],
  ["Tradier", "Stocks & options", "Planned", "Options research groundwork exists. Account connection and automated order execution are separate work and are not active in the extension."],
  ["tastytrade", "Options, stocks & futures", "Planned", "Listed in the broker selector for future integration. Supported instruments and order types will be defined when the adapter is ready."],
  ["Binance.US", "Crypto", "Planned", "A future US crypto connection. Availability will depend on your location, account eligibility and the completed integration."],
  ["Charles Schwab", "Stocks, ETFs & options", "Planned", "A planned brokerage connection. Authentication, market data and trade execution must be integrated before the bot can use it."],
  ["MetaTrader 4 / 5", "Broker-dependent markets", "Planned", "Included in the KAOS connector roadmap. These platforms need a dedicated bridge; instruments and account behavior depend on the connected broker."],
];

export function CompanionHero({mainRef}) {
 return <main ref={mainRef} id="kx-hero" className="kx-companion-home" aria-label="KAOS Trading Bot">
  <header className="kx-home-header">
   <a href="#top" aria-label="KAOS home"><img src="/kaos-logo-horizontal.png" alt="KAOS Trading — Trade With KAOS"/></a>
   <nav aria-label="Homepage navigation">
    <a href="#kaos-bot">The bot</a><a href="#brokers">Brokers</a><a href="#features">Features</a><a href="#pricing">Memberships</a>
    <Link to="/login">Login</Link><Link to="/register" className="kx-home-gold">Get KAOS</Link>
   </nav>
  </header>
  <img className="kx-home-viking" src="/kaos-cinematic-header.jpg" alt="KAOS Viking artwork"/>
  <div className="kx-home-intro">
   <div className="kx-home-pitch">
    <span className="kx-home-eyebrow">YOUR BOT. YOUR DATA. YOUR KAOS.</span>
    <h1>KAOS TRADING BOT</h1>
    <h2>Your broker’s charts.<br/><em>Your KAOS.</em></h2>
    <p>A compact trading companion that works beside your broker. Keep the charts you already use; choose your strategy, set your risk and control the bot from one panel.</p>
    <div className="kx-home-actions"><Link to="/register" className="kx-home-gold">Get KAOS →</Link><a href="#brokers">Explore every broker</a></div>
    <ul><li>Compact controls · no duplicate charts</li><li>Explicit Start and Stop</li><li>Demo / real account status</li></ul>
    <div className="kx-home-connection"><b>More connections. One KAOS.</b><p>Pocket Option is supported today. Explore Coinbase, Kraken, Interactive Brokers and the full connection roadmap below—including integrations not active yet.</p><a href="#brokers">View broker status ↓</a></div>
   </div>
   <figure className="kx-home-bot-preview">
    <div><span>THE KAOS COMPANION</span><b>Actual interface</b></div>
    <img src="/kaos-companion-preview.png" alt="KAOS companion showing broker status, strategy, amount, expiration and Start controls without internal charts"/>
    <figcaption>Captured from the extension with a test session. This is an interface preview, not live account data.</figcaption>
   </figure>
  </div>
 </main>;
}

export function BrokerRoadmap(){
 return <section id="brokers" className="kx-broker-roadmap kx-section" aria-labelledby="broker-roadmap-title">
  <span className="kx-home-eyebrow">THE KAOS CONNECTION ROADMAP</span>
  <h2 id="broker-roadmap-title">Your markets. Your broker. Your bot.</h2>
  <p>Every connection currently listed in KAOS, including future integrations. These are KAOS integration statuses, not statements about a broker’s own services. Planned connections have no promised launch date.</p>
  <div className="kx-broker-grid">{BROKER_ROADMAP.map(([name,markets,status,description])=><article key={name} data-testid="homepage-broker-card">
   <span className={status==="Supported"?"kx-broker-status active":"kx-broker-status"}>{status}</span>
   <h3>{name}</h3><small>{markets}</small><p>{description}</p>
  </article>)}</div>
  <p className="kx-broker-note">Each broker needs its own connection and execution adapter. The compact companion remains the control panel; charts and account access follow the integration supported by that broker.</p>
 </section>;
}
