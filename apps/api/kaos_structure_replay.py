"""Research-only chronological price action replay. No broker orders."""
from collections import Counter
from kaos_trend_pause import validate
from kaos_structure_research import signal

def replay(candles, *, expiry_bars=4, lookback=12):
    if not isinstance(expiry_bars,int) or isinstance(expiry_bars,bool) or not 1<=expiry_bars<=240:
        raise ValueError("expiry_bars must be between 1 and 240")
    if not isinstance(lookback,int) or not 5<=lookback<=100:
        raise ValueError("lookback must be between 5 and 100")
    bars=validate(candles)
    trades=[]
    if len(bars)<lookback+4:
        return {"trades":[],"summary":{"trades":0,"wins":0,"losses":0,"ties":0,"win_rate_ex_ties":None,"trades_per_hour":None,"data_hours":0}}
    steps=[bars[i]["ts"]-bars[i-1]["ts"] for i in range(1,len(bars))]
    if min(steps)!=max(steps):
        raise ValueError("Replay requires uniform candle intervals with no gaps")
    interval=steps[0]
    if interval not in (5000,15000,30000,60000,300000,900000):
        raise ValueError("Unsupported candle interval in milliseconds")
    last_exit=-1
    for i in range(lookback+3,len(bars)-expiry_bars):
        entry=bars[i]
        if entry["ts"]<=last_exit:
            continue
        decision=signal(bars[:i],lookback=lookback)
        if decision is None:
            continue
        exit_bar=bars[i+expiry_bars]
        direction=decision["direction"]
        start=entry["open"];end=exit_bar["open"]
        outcome="TIE" if start==end else ("WIN" if (end>start)==(direction=="CALL") else "LOSS")
        trades.append({"entry_ts":entry["ts"],"exit_ts":exit_bar["ts"],"entry_price":start,"exit_price":end,
          "direction":direction,"setup":decision["setup"],"level":decision["level"],"outcome":outcome,"research_only":True})
        last_exit=exit_bar["ts"]
    counts=Counter(t["outcome"] for t in trades)
    decisive=counts["WIN"]+counts["LOSS"]
    hours=(bars[-1]["ts"]-bars[0]["ts"])/3600000
    return {"trades":trades,"summary":{"trades":len(trades),"wins":counts["WIN"],"losses":counts["LOSS"],
      "ties":counts["TIE"],"win_rate_ex_ties":round(100*counts["WIN"]/decisive,2) if decisive else None,
      "trades_per_hour":round(len(trades)/hours,2) if hours else None,"data_hours":round(hours,3),
      "evaluation":"raw_directional_only_no_fees_spread_slippage_or_payout","profitable":None}}
