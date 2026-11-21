"""Evaluate every eligible continuous segment in a discontinuous R2 archive.

Chronological, fixed rules: segment on every missing source bar, reject short
segments, never bridge a gap, never select segments by their results.
Research only; does not model tradability, fees, spreads or payouts.
"""
from collections import Counter
from kaos_structure_replay import replay
from kaos_r2_research import inspect_history

def gap_aware_replay(rows, seconds, *, expiry_bars=4, lookback=12):
    diagnostics=inspect_history(rows, seconds)
    if not isinstance(expiry_bars,int) or isinstance(expiry_bars,bool) or not 1<=expiry_bars<=240:
        raise ValueError("Invalid expiry_bars")
    if not isinstance(lookback,int) or isinstance(lookback,bool) or not 5<=lookback<=100:
        raise ValueError("Invalid lookback")
    min_bars=lookback+expiry_bars+5
    segments=[]
    current=[]
    interval=seconds*1000
    for bar in rows:
        if current and bar["ts"]-current[-1]["ts"]!=interval:
            segments.append(current)
            current=[]
        current.append(bar)
    if current:
        segments.append(current)
    trades=[]
    segment_metrics=[]
    eligible_bars=0
    hours=0.0
    for index,segment in enumerate(segments):
        usable=len(segment)>=min_bars
        info={"segment_index":index,"bars":len(segment),
              "start_ts":segment[0]["ts"],"last_ts":segment[-1]["ts"],
              "evaluated":usable}
        segment_metrics.append(info)
        if not usable:
            continue
        eligible_bars+=len(segment)
        result=replay(segment,expiry_bars=expiry_bars,lookback=lookback)
        hours+=result["summary"]["data_hours"]
        for trade in result["trades"]:
            # No trades can bridge any provider gap.
            trades.append({**trade,"segment_index":index})
    counts=Counter(trade["outcome"] for trade in trades)
    decisive=counts["WIN"]+counts["LOSS"]
    skipped_bars=len(rows)-eligible_bars
    return {
        "status":"completed" if eligible_bars else "insufficient_contiguous_history",
        "history":{**diagnostics,"segments":len(segments),
                   "eligible_segments":sum(int(x["evaluated"]) for x in segment_metrics),
                   "eligible_bars":eligible_bars,
                   "skipped_bars":skipped_bars,
                   "eligible_fraction":round(eligible_bars/len(rows),4) if rows else 0},
        "segments":segment_metrics,
        "summary":({
            "trades":len(trades),"wins":counts["WIN"],"losses":counts["LOSS"],
            "ties":counts["TIE"],
            "win_rate_ex_ties":round(100*counts["WIN"]/decisive,2) if decisive else None,
            "trades_per_hour":round(len(trades)/hours,2) if hours else None,
            "data_hours":round(hours,3),
            "evaluation":"raw_directional_only_no_fees_spread_slippage_or_payout",
            "profitable":None,
        } if eligible_bars else None),
        "trades":trades,
        "research_only":True,
        "execution_enabled":False,
        "notes":("All eligible contiguous segments included; bars in ineligible short segments excluded. "
                 "No cross-gap trades. Rates refer only to eligible continuous hours."),
    }
