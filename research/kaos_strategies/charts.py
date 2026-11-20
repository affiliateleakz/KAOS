"""Charts for the library report.

    python charts.py     # writes out/fig-*.png

Two things are worth looking at and nothing else: whether a strategy beats the drift-matched
placebo, and what its equity curve does after costs. Both are plotted on the same out-of-sample
slice the scoreboard uses.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import core
import evaluate
import strategies  # noqa: F401

OUT = Path(__file__).resolve().parent / "out"
GOLD, GREY, RED, GREEN = "#c9a227", "#8a8f98", "#c0392b", "#2e7d4f"


def collect():
    results, curves = [], {}
    for sid, strategy in core.REGISTRY.items():
        if strategy.signal_fn is None:
            continue
        res = evaluate.evaluate(strategy)
        results.append(res)
        frames = []
        for _, asset, tf, df in evaluate.iter_pairs(strategy):
            _, sig = strategy.signal_fn(df, dict(strategy.params))
            cut = int(len(df) * 0.6)
            if strategy.mode == "expiry":
                tr = evaluate.expiry_trades(df, sig, int(strategy.exit.get("expiry_bars", 3)), cut, len(df))
            else:
                tr = evaluate.bracket_trades(df, sig, strategy.exit, 0.02, cut, len(df))
            if not tr.empty:
                frames.append(tr[["entry_ts", "pnl_atr", "outcome"]])
        if frames:
            curves[sid] = pd.concat(frames).sort_values("entry_ts")
    return results, curves


def fig_scoreboard(results):
    names = {"pulse-range": "Pulse\n(range MR)", "drive-trend": "Drive\n(trend pullback)",
             "orb-equity": "ORB\n(US open)", "fx-session-breakout": "FX session\n(London)",
             "crypto-ignition": "Ignition\n(expansion)", "binary-fade": "Binary\n(range fade)"}
    scored = [r for r in results if r["pooled"].get("n")]
    labels = [names.get(r["id"], r["id"]) for r in scored]
    real = [r["pooled"]["excess_pp"] for r in scored]
    plac = [r["placebo"].get("excess_pp", 0) for r in scored]
    exp = [r["pooled"]["expectancy_atr"] for r in scored]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    y = np.arange(len(scored))[::-1]
    axes[0].barh(y + 0.2, real, height=0.38, color=GOLD, label="strategy")
    axes[0].barh(y - 0.2, plac, height=0.38, color=GREY, label="drift-matched placebo")
    axes[0].axvline(0, color="black", lw=0.8)
    axes[0].set_yticks(y, labels, fontsize=8)
    axes[0].set_title("Win rate minus barrier parity (pp)", fontsize=10)
    axes[0].legend(fontsize=8, loc="lower right")
    axes[0].grid(axis="x", alpha=0.25)

    colors = [GREEN if e > 0 else RED for e in exp]
    axes[1].barh(y, exp, height=0.5, color=colors)
    axes[1].axvline(0, color="black", lw=0.8)
    axes[1].set_yticks(y, labels, fontsize=8)
    axes[1].set_title("Expectancy per trade after costs (ATR / unit staked)", fontsize=10)
    axes[1].grid(axis="x", alpha=0.25)
    fig.suptitle("KAOS strategy library - out-of-sample scoreboard", fontsize=12, x=0.02, ha="left")
    fig.text(0.02, 0.01, "Parity is what a driftless random walk produces with the same brackets; the placebo "
                         "matches entry count and long/short mix on the same bars.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(OUT / "fig-scoreboard.png", dpi=150)
    plt.close(fig)


def fig_equity(curves):
    names = {"pulse-range": "Pulse", "drive-trend": "Drive", "orb-equity": "ORB",
             "fx-session-breakout": "FX session", "crypto-ignition": "Ignition", "binary-fade": "Binary fade"}
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for sid, df in curves.items():
        if sid not in names:
            continue
        pnl = df["pnl_atr"].to_numpy(float)
        if sid == "binary-fade":
            continue  # different unit (per unit staked), plotted separately below
        ax.plot(np.arange(1, len(pnl) + 1), np.cumsum(pnl), lw=1.6, label=f"{names[sid]} (n={len(pnl)})")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("trade number (pooled across pairs, out of sample)")
    ax.set_ylabel("cumulative ATR")
    ax.set_title("Pooled equity after 0.02 ATR per side - bracketed strategies", fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig-equity.png", dpi=150)
    plt.close(fig)

    if "binary-fade" in curves:
        pnl = curves["binary-fade"]["pnl_atr"].to_numpy(float)
        fig, ax = plt.subplots(figsize=(11, 3.6))
        ax.plot(np.arange(1, len(pnl) + 1), np.cumsum(pnl), color=RED, lw=1.6)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xlabel("bet number")
        ax.set_ylabel("cumulative units staked")
        ax.set_title("Binary fade at 0.80 payout - break-even needs 55.6% wins", fontsize=11)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / "fig-equity-binary.png", dpi=150)
        plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    results, curves = collect()
    fig_scoreboard(results)
    fig_equity(curves)
    for sid, df in curves.items():
        df.to_csv(OUT / f"trades-{sid}.csv", index=False)
    print("wrote", sorted(p.name for p in OUT.glob("fig-*.png")))


if __name__ == "__main__":
    main()
