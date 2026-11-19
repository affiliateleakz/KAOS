"""Pool every out-of-sample trade from the frozen configuration into one account.

Individual markets are noisy because a 5m range setup only fires a few dozen times per
slice. The question a trader actually asks is different: if the same rule had been run
on all of these markets at once, what would the account have done? This script answers
that, then draws the report figures.

Run:  PYTHONPATH=. python3 report_charts.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data
from backtest import metrics, simulate_entries
from portability import FROZEN
from study import BASKET, COST_ATR, SPLIT, asset_class, prepare, pulse_entries
from strategy import DEFAULT

OUT = Path(__file__).with_name("out")
CLASS_COLOUR = {"crypto": "#e0a83a", "fx": "#4a90d9", "equity": "#3aa76d"}


def collect():
    rows, trades = [], []
    for asset, tf in BASKET:
        df = data.load(asset, tf)
        n = len(df)
        cut = int(n * SPLIT)
        _, reg, sig, atr = prepare(df, DEFAULT)
        tr = simulate_entries(df.iloc[cut:].reset_index(drop=True),
                              pulse_entries(sig, reg, cut, n), atr,
                              FROZEN["tp"], FROZEN["sl"], FROZEN["bars"], COST_ATR, "pulse")
        if tr.empty:
            continue
        m = metrics(tr, FROZEN["tp"], FROZEN["sl"])
        rows.append({"asset": asset, "tf": tf, "class": asset_class(asset), **m})
        tr = tr.copy()
        tr["asset"], tr["tf"], tr["class"] = asset, tf, asset_class(asset)
        trades.append(tr)
    return pd.DataFrame(rows), pd.concat(trades, ignore_index=True)


def pooled(trades: pd.DataFrame) -> dict:
    t = trades.sort_values("exit_ts").reset_index(drop=True)
    pnl = t["pnl_atr"].to_numpy()
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    wins = t["outcome"].isin(["tp", "tp_gap"])
    losses = t["outcome"].isin(["sl", "sl_gap"])
    gross_win, gross_loss = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    return {"n": int(len(t)), "wr": float(wins.sum() / max((wins | losses).sum(), 1)),
            "pnl_wr": float((pnl > 0).mean()), "exp": float(pnl.mean()),
            "total_atr": float(pnl.sum()), "pf": float(gross_win / gross_loss),
            "max_dd_atr": float(np.max(peak - eq)), "time_share": float((t["outcome"] == "time").mean()),
            "avg_bars": float(t["bars"].mean())}


def fig_wr_by_pair(rows: pd.DataFrame, path: Path):
    d = rows.sort_values(["class", "asset", "tf"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(14.5, 6.0))
    labels = [f"{r.asset}\n{r.tf}" for r in d.itertuples()]
    x = np.arange(len(d))
    ax.bar(x, d["wr"], color=[CLASS_COLOUR[c] for c in d["class"]])
    ax.axhline(0.625, color="#888", ls="--", lw=1, label="barrier parity 62.5%")
    ax.axhline(0.65, color="#c0392b", ls=":", lw=1.2, label="65% target")
    for i, r in enumerate(d.itertuples()):
        ax.text(i, r.wr + 0.012, f"{r.wr * 100:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.4, rotation=90)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("out-of-sample win rate on decided trades")
    ax.set_title("KAOS Strategy - one frozen parameter set, 42 market/timeframe pairs\n"
                 "orange = crypto, blue = FX, green = equities", fontsize=11)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_equity(trades: pd.DataFrame, path: Path):
    t = trades.sort_values("exit_ts").reset_index(drop=True)
    eq = np.cumsum(t["pnl_atr"].to_numpy())
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.plot(eq, lw=1.1, color="#1f3d7a")
    ax.fill_between(np.arange(len(eq)), 0, eq, where=eq >= 0, color="#3aa76d", alpha=0.18)
    ax.fill_between(np.arange(len(eq)), 0, eq, where=eq < 0, color="#c0392b", alpha=0.18)
    ax.set_title(f"Pooled out-of-sample equity - all 42 markets, {len(t)} trades "
                 f"({eq[-1]:+.1f} ATR, cost 0.02 ATR/side)")
    ax.set_xlabel("trade (ordered by exit time)")
    ax.set_ylabel("cumulative ATR")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_timeframe(rows: pd.DataFrame, path: Path):
    order = ["1m", "5m", "15m", "1h", "4h"]
    g = rows.groupby("tf").agg(wr=("wr", "mean"), n=("n", "sum"), pairs=("wr", "size")).reindex(order).dropna()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(g.index, g["wr"], color="#1f3d7a", width=0.55)
    ax.axhline(0.625, color="#888", ls="--", lw=1, label="parity 62.5%")
    ax.axhline(0.65, color="#c0392b", ls=":", lw=1.2, label="65% target")
    for i, (tf, r) in enumerate(g.iterrows()):
        ax.text(i, r["wr"] + 0.01, f"{r['wr'] * 100:.1f}%\n{int(r['pairs'])} pairs", ha="center", fontsize=8)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("mean win rate")
    ax.set_title("Win rate by timeframe (frozen geometry, out of sample)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_expectancy(rows: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.linspace(-3, 3, 25)
    for cls, colour in CLASS_COLOUR.items():
        v = rows.loc[rows["class"] == cls, "expectancy_atr"].clip(-3, 3)
        ax.hist(v, bins=bins, alpha=0.55, label=f"{cls} (n={len(v)})", color=colour)
    ax.axvline(0, color="#333", lw=1)
    ax.set_title("Out-of-sample expectancy per trade, ATR units (frozen geometry)")
    ax.set_xlabel("expectancy (ATR)")
    ax.set_ylabel("market/timeframe pairs")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    rows, trades = collect()
    p = pooled(trades)
    by_class = {}
    for cls in ("crypto", "fx", "equity"):
        t = trades[trades["class"] == cls]
        if len(t):
            by_class[cls] = pooled(t)
    by_tf = {}
    for tf in ("1m", "5m", "15m", "1h", "4h"):
        t = trades[trades["tf"] == tf]
        if len(t):
            by_tf[tf] = pooled(t)

    (OUT / "portfolio.json").write_text(json.dumps(
        {"pooled": p, "by_class": by_class, "by_timeframe": by_tf}, indent=2))
    trades.sort_values("exit_ts").to_csv(OUT / "pooled_trades.csv", index=False)

    fig_wr_by_pair(rows, OUT / "fig_wr_by_pair.png")
    fig_equity(trades, OUT / "fig_pooled_equity.png")
    fig_timeframe(rows, OUT / "fig_wr_by_timeframe.png")
    fig_expectancy(rows, OUT / "fig_expectancy.png")

    print("pooled:", json.dumps(p, indent=2))
    print("by class:", json.dumps(by_class, indent=2))
    print("by tf:", json.dumps(by_tf, indent=2))


if __name__ == "__main__":
    main()
