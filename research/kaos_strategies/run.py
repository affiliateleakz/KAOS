"""Score every registered strategy and write the results tables.

    python run.py            # score and write out/results.json, out/pairs.csv, out/RESULTS-table.md

Chronological convention: indicators are computed on the full cached series (all of them are
causal), entries are split 60/40 by index, and only the last 40% is scored. The placebo uses
the same slice, the same number of entries and the same long/short mix.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import core
import evaluate
import strategies  # noqa: F401  (import side effect: registers the strategies)

OUT = Path(__file__).resolve().parent / "out"


def fmt(x, nd=3):
    if isinstance(x, float):
        if x != x:
            return "-"
        return f"{x:.{nd}f}"
    return str(x)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    results = []
    rows = []
    for sid, strategy in core.REGISTRY.items():
        print(f"[score] {sid}", flush=True)
        res = evaluate.evaluate(strategy)
        res["verdict"] = evaluate.verdict(res)
        results.append(res)
        for r in res["rows"]:
            rows.append({"strategy": sid, **r})

    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    pd.DataFrame(rows).to_csv(OUT / "pairs.csv", index=False)

    lines = ["| Strategy | Class | Mode | Trades (OOS) | Win rate | Parity | Excess pp | z | Exp (ATR/bet) | PF | Placebo exp | Lift pp | p | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        p, pl = r.get("pooled", {}), r.get("placebo", {})
        lines.append("| {name} | {cls} | {mode} | {n} | {wr}% | {par}% | {ex} | {z} | {exp} | {pf} | {plexp} | {lift} | {pv} | {v} |".format(
            name=r["name"], cls=", ".join(core.get(r["id"]).asset_classes), mode=r["mode"],
            n=p.get("n", 0), wr=fmt(p.get("wr", float("nan")) * 100 if p.get("n") else float("nan"), 1),
            par=fmt(p.get("parity", float("nan")) * 100 if p.get("n") else float("nan"), 1),
            ex=fmt(p.get("excess_pp", float("nan")), 1),
            exp=fmt(p.get("expectancy_atr", float("nan")), 3),
            pf=fmt(p.get("pf", float("nan")), 2),
            z=fmt(p.get("z_vs_parity", float("nan")), 2),
            pv=fmt(r.get("p_value", float("nan")), 2),
            plexp=fmt(pl.get("expectancy_atr", float("nan")), 3),
            lift=fmt(r.get("lift_pp", float("nan")), 1),
            v=r["verdict"]))
    table = "\n".join(lines) + "\n"
    (OUT / "RESULTS-table.md").write_text(table)
    print("\n" + table)




if __name__ == "__main__":
    main()
