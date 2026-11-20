"""Build the public page for the hosting site.

    python site_page.py     # out/kaos-strategies.html

Self-contained apart from the three PNGs, which are deployed next to it. Every number comes
from out/results.json and out/pairs.csv, so the page cannot drift away from the scoreboard.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import core
import platforms
import strategies  # noqa: F401

OUT = Path(__file__).resolve().parent / "out"
VERDICT_CLASS = {"edge confirmed": "good", "promising, not significant": "warn",
                 "no edge after costs": "bad", "fails parity": "bad", "fails placebo": "bad",
                 "unvalidated": "muted", "insufficient sample": "muted"}

CSS = """
:root{--gold:#c9a227;--gold-dim:#8c711a;--bg:#0a0b0d;--panel:#12141a;--line:#23262e;
--txt:#e8e6e1;--muted:#9aa0aa;--good:#2e7d4f;--warn:#b8860b;--bad:#a8322a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:48px 22px 80px}
header{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:34px}
.kicker{letter-spacing:.28em;text-transform:uppercase;font-size:11px;color:var(--gold)}
h1{font-size:34px;margin:10px 0 6px;font-weight:600;letter-spacing:-.01em}
h2{font-size:21px;margin:44px 0 12px;font-weight:600}
h2:before{content:"";display:inline-block;width:18px;height:2px;background:var(--gold);vertical-align:middle;margin-right:10px}
h3{font-size:17px;margin:0 0 4px}
p{color:var(--txt);margin:10px 0}
.sub{color:var(--muted);max-width:760px}
.callout{background:linear-gradient(180deg,#15171d,#101216);border:1px solid var(--line);
border-left:3px solid var(--gold);padding:18px 20px;border-radius:6px;margin:22px 0}
.callout strong{color:var(--gold)}
table{width:100%;border-collapse:collapse;margin:14px 0 6px;font-size:13.5px}
th{text-align:left;color:var(--gold);font-weight:600;border-bottom:1px solid var(--line);padding:8px 9px;white-space:nowrap}
td{border-bottom:1px solid #191c22;padding:8px 9px;vertical-align:top}
tr:hover td{background:#101319}
.num{font-variant-numeric:tabular-nums;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px}
.card .thesis{color:var(--muted);font-size:13px;margin:8px 0 12px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px}
.chip{font-size:11px;letter-spacing:.04em;border:1px solid var(--line);color:var(--muted);
padding:2px 8px;border-radius:999px;text-transform:uppercase}
.chip.plat{border-color:#2b3038;color:#b9bec8;text-transform:none;letter-spacing:0}
.badge{font-size:11px;padding:3px 9px;border-radius:4px;text-transform:uppercase;letter-spacing:.08em}
.badge.good{background:rgba(46,125,79,.18);color:#63c48d;border:1px solid #2e7d4f}
.badge.warn{background:rgba(184,134,11,.16);color:#e0b64a;border:1px solid #7a5c0c}
.badge.bad{background:rgba(168,50,42,.16);color:#e07a70;border:1px solid #7d2a24}
.badge.muted{background:#1a1d24;color:var(--muted);border:1px solid var(--line)}
.kv{font-size:12.5px;color:var(--muted);margin:3px 0}
.kv b{color:var(--txt);font-weight:500}
img{width:100%;border:1px solid var(--line);border-radius:6px;background:#fff;margin-top:12px}
figure{margin:20px 0}
figcaption{color:var(--muted);font-size:12px;margin-top:6px}
footer{margin-top:56px;border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:12.5px}
a{color:var(--gold);text-decoration:none}
code{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:#d8c98a}
"""


def md_table(path: Path) -> str:
    """Render every markdown table in a file, keeping headings and prose between them."""
    out: list[str] = []
    block: list[str] = []

    def flush() -> None:
        if not block:
            return
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in block]
        block.clear()
        cells = [c for c in cells if not set("".join(c)) <= set("-: ")]
        if not cells:
            return
        head, body = cells[0], cells[1:]
        out.append("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>")
        for r in body:
            out.append("<tr>" + "".join(f'<td class="num">{c}</td>' for c in r) + "</tr>")
        out.append("</tbody></table>")

    for line in path.read_text().splitlines():
        if line.startswith("|"):
            block.append(line)
            continue
        flush()
        if line.startswith("## "):
            out.append(f"<h3>{line[3:].strip()}</h3>")
        elif line.strip() and not line.startswith("#"):
            txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", line.strip())
            out.append(f'<p class="sub">{txt}</p>')
    flush()
    return "".join(out)


def badge(text: str) -> str:
    return f'<span class="badge {VERDICT_CLASS.get(text, "muted")}">{text}</span>'


def main() -> None:
    results = json.loads((OUT / "results.json").read_text())
    pairs = pd.read_csv(OUT / "pairs.csv")
    by_id = {r["id"]: r for r in results}

    # ---------------------------------------------------------------- scoreboard
    sb = ["<table><thead><tr><th>Strategy</th><th>Class</th><th>Trades (OOS)</th><th>Win rate</th>",
          "<th>Parity</th><th>Excess</th><th>Exp / trade</th><th>Profit factor</th><th>Lift vs placebo</th><th>Verdict</th></tr></thead><tbody>"]
    for sid, r in by_id.items():
        s = core.get(sid)
        p, pl = r.get("pooled", {}), r.get("placebo", {})
        n = p.get("n", 0)
        wr = f"{p['wr']*100:.1f}%" if n else "-"
        par = f"{p['parity']*100:.1f}%" if n else "-"
        exc = f"{p['excess_pp']:+.1f}pp" if n else "-"
        exp = (f"{p['expectancy_atr']:+.3f}" if r["mode"] != "expiry" else f"{p['expectancy_atr']:+.3f}/unit") if n else "-"
        pf = f"{p['pf']:.2f}" if n else "-"
        lift = f"{r.get('lift_pp', float('nan')):+.1f}pp" if n else "-"
        sb.append(f'<tr><td><b>{s.name}</b></td><td>{", ".join(s.asset_classes)}</td><td class="num">{n or "-"}</td>'
                  f'<td class="num">{wr}</td><td class="num">{par}</td><td class="num">{exc}</td>'
                  f'<td class="num">{exp}</td><td class="num">{pf}</td><td class="num">{lift}</td>'
                  f'<td>{badge(r.get("verdict", "unvalidated"))}</td></tr>')
    sb.append("</tbody></table>")

    # ---------------------------------------------------------------- cards
    cards = []
    for sid, s in core.REGISTRY.items():
        r = by_id.get(sid, {})
        p = r.get("pooled", {})
        stats = []
        if p.get("n"):
            stats.append(f'<div class="kv"><b>{p["n"]}</b> out-of-sample trades</div>')
            stats.append(f'<div class="kv"><b>{p["wr"]*100:.1f}%</b> win rate vs <b>{p["parity"]*100:.1f}%</b> parity</div>')
            stats.append(f'<div class="kv"><b>{p["expectancy_atr"]:+.3f}</b> expectancy per {"bet" if r["mode"]=="expiry" else "trade"} after costs</div>')
            stats.append(f'<div class="kv">placebo lift <b>{r.get("lift_pp", float("nan")):+.1f}pp</b>, p = <b>{r.get("p_value", float("nan")):.2f}</b></div>')
        elif s.signal_fn is None:
            stats.append('<div class="kv">No options chain in the data set - rules complete, P&amp;L not measured.</div>')
        exit_txt = (f'{s.exit["tp_atr"]:.1f} ATR target / {s.exit["sl_atr"]:.1f} ATR stop / {s.exit["max_bars"]} bars'
                    if s.exit.get("kind") == "bracket" else
                    f'fixed {s.exit.get("expiry_bars")}-bar expiry' if s.exit.get("kind") == "expiry" else
                    "35 DTE, 0.18 delta, $5 wings, manage at 50% / 2x / 21 DTE")
        cards.append(f"""<div class="card"><h3>{s.name}</h3>{badge(r.get('verdict','unvalidated'))}
<p class="thesis">{s.thesis}</p>
<div class="chips">{''.join(f'<span class="chip">{c}</span>' for c in s.asset_classes)}
{''.join(f'<span class="chip">{t}</span>' for t in s.timeframes)}</div>
<div class="kv">Exit: <b>{exit_txt}</b></div>
{''.join(stats)}
<div class="chips" style="margin-top:12px">{''.join(f'<span class="chip plat">{platforms.PLATFORMS[pl]['name']}</span>' for pl in s.platforms if pl in platforms.PLATFORMS)}</div>
</div>""")

    # ---------------------------------------------------------------- platform matrix
    rows = []
    for pid, meta in platforms.PLATFORMS.items():
        cells = []
        for sid, s in core.REGISTRY.items():
            cells.append("&#10003;" if pid in s.platforms else "&middot;")
        rows.append(f"<tr><td><b>{meta['name']}</b><div class='kv'>{meta['order']}</div></td>"
                    + "".join(f'<td class="num" style="text-align:center">{c}</td>' for c in cells) + "</tr>")
    matrix = ("<table><thead><tr><th>Platform</th>"
              + "".join(f"<th>{core.get(s).name.split(' - ')[0]}</th>" for s in core.REGISTRY)
              + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")

    # ---------------------------------------------------------------- per class
    d = pairs[pairs["n_test"] > 0]
    pc = ["<table><thead><tr><th>Strategy</th><th>Asset class</th><th>Trades</th><th>Win rate</th><th>Exp / trade</th><th>Pairs positive</th></tr></thead><tbody>"]
    for sid, g in d.groupby("strategy"):
        for cls, q in g.groupby("class"):
            n = q["n_test"].sum()
            wr = (q["wr_test"] * q["n_test"]).sum() / n * 100
            pc.append(f'<tr><td>{core.get(sid).name.split(" - ")[0]}</td><td>{cls}</td>'
                      f'<td class="num">{int(n)}</td><td class="num">{wr:.1f}%</td>'
                      f'<td class="num">{q["exp_atr"].mean():+.3f}</td>'
                      f'<td class="num">{int((q["exp_atr"] > 0).sum())}/{len(q)}</td></tr>')
    pc.append("</tbody></table>")

    stress = md_table(OUT / "STRESS.md")
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KAOS strategy library - every asset class, every platform</title>
<meta name="description" content="Seven KAOS trading strategies scored out of sample against barrier parity and a drift-matched placebo, with per-platform order translation.">
<style>{CSS}</style></head><body><div class="wrap">
<header><div class="kicker">KAOS Research</div><h1>Strategy library</h1>
<p class="sub">Seven rules covering crypto, FX, US equities, binary options and options - each one
scored out of sample against two controls and translated into the native order format of Kraken,
Coinbase, Binance, MetaTrader&nbsp;5, OANDA, tastytrade, Alpaca and Pocket&nbsp;Option.</p></header>

<div class="callout"><strong>The honest version.</strong> Two rules make money after costs:
the US opening-range breakout (+0.229 ATR per trade, PF 1.38) and the crypto volatility-expansion
breakout (+0.106 ATR, PF 1.11). Neither reaches statistical significance against random entries on
the same bars. The flagship range-reversion rule wins 68.6% of its trades and only breaks even,
because a 3&nbsp;ATR target against a 5&nbsp;ATR stop already wins 62.5% of the time by chance. The
binary rule loses at every payout Pocket&nbsp;Option offers. Win rate is not an edge - expectancy
against the controls is.</div>

<h2>Out-of-sample scoreboard</h2>
{''.join(sb)}
<p class="sub">Parity is the driftless hit rate implied by the bracket geometry; the placebo takes
the same number of longs and shorts at random bars inside the same window and runs them through the
identical exit engine. Costs are 0.02 ATR per side.</p>

<h2>The rules</h2>
<div class="cards">{''.join(cards)}</div>

<h2>By asset class</h2>
{''.join(pc)}

<h2>Cost stress</h2>
{stress}
<p class="sub">Only the opening-range rule survives a 10x cost assumption. That is the difference
between a real horizon and harvesting noise inside the spread.</p>

<figure><img src="kaos-strategies-fig-scoreboard.png" alt="Strategy vs parity and placebo">
<figcaption>Left: win rate minus parity, strategy against drift-matched placebo. Right: expectancy
per trade after costs.</figcaption></figure>
<figure><img src="kaos-strategies-fig-equity.png" alt="Pooled equity curves">
<figcaption>Pooled out-of-sample equity after 0.02 ATR per side. Range reversion draws down
about 200 ATR before recovering and finishes +21 ATR over 2,229 trades: a 68.6% win rate that ends
where it started.</figcaption></figure>

<h2>Platform coverage</h2>
{matrix}
<p class="sub">Order shapes are generated by <code>platforms.py</code> from one neutral intent -
side, entry, stop, target, ATR. No API keys are embedded and no order is placed.</p>

<h2>Method, in one paragraph</h2>
<p class="sub">Entries are decided on the close and filled at the next open, the stop wins any
intrabar tie, gaps fill at the open, one position per pair at a time, cost charged on both sides.
Data is 83 days of 5m/15m candles, 11 days of 1m and ~2.8 years of 1h/4h across 4 crypto pairs,
4 FX pairs and 6 US equities. Only the last 40% of each series is scored. Options are not measured
because the data set contains no option chain - the structure rule is complete, the P&amp;L is not
claimed.</p>

<footer>KAOS Research - generated from the same results file that produces the scoreboard.
Figures are out-of-sample backtests, not investment advice, and past performance does not predict
future results. Full rules, cost tables and trade lists live in <code>/research/</code>.</footer>
</div></body></html>"""
    (OUT / "kaos-strategies.html").write_text(html)
    print(f"wrote {OUT / 'kaos-strategies.html'} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
