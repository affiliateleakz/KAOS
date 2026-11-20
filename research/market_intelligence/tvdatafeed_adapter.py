"""Optional KAOS TradingView/tvdatafeed historical research adapter.

No dependency on tvdatafeed in production, no secrets persisted, no background
threads, no calls to KAOS trading endpoints, and no commercial-use grant.
Run only with access and redistribution rights verified.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re

INTERVALS = {60: "in_1_minute", 180: "in_3_minute",
             300: "in_5_minute", 900: "in_15_minute",
             1800: "in_30_minute", 3600: "in_1_hour",
             86400: "in_daily"}
MARKET = re.compile(r"^[A-Z0-9_.-]{1,32}$")


def normalize_history(records, *, symbol, exchange, asset_class, seconds,
                      observed_at_ms, source_tz=None, max_bars=5000):
    """Validate one provider history into explicit, closed, UTC OHLCV bars.

    Input rows contain timestamp (timezone-aware ISO/datetime, or source-local
    ISO if an explicit source_tz is supplied), open/high/low/close/volume.
    Missing volume is rejected, never silently replaced with zero.
    """
    if (type(seconds) is not int or seconds not in INTERVALS or
            asset_class not in ("stock", "crypto", "forex", "etf") or
            not isinstance(symbol,str) or not MARKET.fullmatch(symbol) or
            not isinstance(exchange,str) or not MARKET.fullmatch(exchange)):
        raise ValueError("unsupported market, exchange or interval")
    if not isinstance(records,list) or not 1 <= len(records) <= max_bars:
        raise ValueError("history must be 1..5000 records")
    if type(observed_at_ms) is not int or observed_at_ms <= 0:
        raise ValueError("observation timestamp required")
    if source_tz is not None and not hasattr(source_tz, "utcoffset"):
        raise ValueError("source_tz must be timezone")
    bars=[]
    for row in records:
        if not isinstance(row,dict):
            raise ValueError("invalid history row")
        timestamp=row.get("timestamp")
        if isinstance(timestamp,str):
            try:
                timestamp=datetime.fromisoformat(timestamp.replace("Z","+00:00"))
            except ValueError as exc:
                raise ValueError("invalid timestamp") from exc
        if not isinstance(timestamp,datetime):
            raise ValueError("timestamp must be ISO datetime")
        if timestamp.tzinfo is None:
            if source_tz is None:
                raise ValueError("timezone-naive source timestamps need explicit timezone")
            timestamp=timestamp.replace(tzinfo=source_tz)
        when=int(timestamp.astimezone(timezone.utc).timestamp()*1000)
        values=[row.get(k) for k in ("open","high","low","close","volume")]
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
            raise ValueError("invalid or missing OHLCV")
        o,h,l,c,v=values
        if min(o,h,l,c)<=0 or v<0 or l>min(o,c) or h<max(o,c):
            raise ValueError("inconsistent OHLCV")
        ms=seconds*1000
        if when<=0 or when%ms:
            raise ValueError("unaligned UTC candle timestamp")
        # Provider may include a still-forming candle; drop it explicitly.
        if when+ms > observed_at_ms:
            continue
        bars.append({
            "ts":when,"symbol":symbol,"asset_class":asset_class,
            "source":"tradingview_unofficial","exchange":exchange,"seconds":seconds,
            "open":float(o),"high":float(h),"low":float(l),
            "close":float(c),"volume":float(v),
        })
    bars.sort(key=lambda b:b["ts"])
    if len({b["ts"] for b in bars}) != len(bars):
        raise ValueError("duplicate timestamps")
    breaks=sum(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(bars,bars[1:]))
    return {
        "status":"research_only_not_ingested",
        "symbol":symbol,"asset_class":asset_class,
        "source":"tradingview_unofficial","exchange":exchange,
        "seconds":seconds,"observed_at_ms":observed_at_ms,
        "closed_bar_count":len(bars),"noncontiguous_intervals":breaks,
        "candles":bars,
        "warnings":[
            "Unofficial provider; rights and access must be separately verified",
            "No claim of real-time coverage, continuous collection or native second candles",
            "Gaps can reflect market closures or missing data; never forward-fill as genuine candles",
            "Output is local research only and is not submitted to KAOS archives automatically",
        ],
    }


def fetch_once(*,symbol,exchange,seconds,n_bars):
    """One-shot explicit fetch, never starts the TvDatafeedLive thread worker."""
    if type(n_bars) is not int or not 1 <= n_bars <= 5000:
        raise ValueError("n_bars must be 1..5000")
    try:
        from tvDatafeed import TvDatafeed,Interval
    except ImportError as exc:
        raise RuntimeError("Install tvdatafeed in a separate research virtualenv") from exc
    username=os.getenv("TRADINGVIEW_USERNAME")
    password=os.getenv("TRADINGVIEW_PASSWORD")
    if bool(username) != bool(password):
        raise ValueError("Supply both credentials or neither")
    tv=TvDatafeed(username,password) if username else TvDatafeed()
    data=tv.get_hist(symbol=symbol,exchange=exchange,
                     interval=getattr(Interval,INTERVALS[seconds]),n_bars=n_bars)
    if data is None or data.empty:
        raise RuntimeError("No TradingView historical data returned")
    return [
        {"timestamp":stamp.to_pydatetime() if hasattr(stamp,"to_pydatetime") else stamp,
         "open":float(row["open"]),"high":float(row["high"]),
         "low":float(row["low"]),"close":float(row["close"]),
         "volume":float(row["volume"])}
        for stamp,row in data.iterrows()
    ]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--exchange",required=True)
    p.add_argument("--asset-class",choices=["stock","etf","crypto","forex"],required=True)
    p.add_argument("--seconds",type=int,choices=sorted(INTERVALS),default=60)
    p.add_argument("--n-bars",type=int,default=200)
    p.add_argument("--input-json",help="Offline fixture with records array")
    p.add_argument("--fetch",action="store_true",help="Explicitly fetch from unofficial provider")
    p.add_argument("--acknowledge-provider-terms",action="store_true")
    p.add_argument("--source-timezone",default="UTC",
                   help="Explicit timezone for naive source timestamps; defaults UTC ONLY if intentionally selected")
    a=p.parse_args()
    if a.fetch == bool(a.input_json):
        p.error("Choose exactly one of --input-json or --fetch")
    if a.fetch and not a.acknowledge_provider_terms:
        p.error("Live fetch requires --acknowledge-provider-terms")
    if not 1 <= a.n_bars <= 5000:
        p.error("n-bars must be 1..5000")
    from zoneinfo import ZoneInfo
    try:
        tz=ZoneInfo(a.source_timezone)
    except (KeyError,ValueError) as exc:
        p.error("Unknown source timezone")
    if a.fetch:
        records=fetch_once(symbol=a.symbol,exchange=a.exchange,seconds=a.seconds,n_bars=a.n_bars)
    else:
        source=json.loads(Path(a.input_json).read_text())
        records=source.get("records")
    observed_at_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    result=normalize_history(records,symbol=a.symbol.upper(),exchange=a.exchange.upper(),
          asset_class=a.asset_class,seconds=a.seconds,source_tz=tz,
          observed_at_ms=observed_at_ms)
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"closed_bar_count":result["closed_bar_count"]}))

if __name__=="__main__":
    main()
