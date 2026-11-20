"""Original KAOS candle-window dataset for optional chart-pattern CNN experiments.

Builds normalized OHLCV tensors directly from historical closed candles;
no third-party code or chart screenshots, no trained/deployed network.
The label and future outcomes are segregated from the input tensor.
"""
import argparse
import json
import math
from pathlib import Path


def windows(export, *, lookback=24, horizon_bars=5, max_rows=10000):
    if type(lookback) is not int or not 5 <= lookback <= 256:
        raise ValueError("lookback must be an integer between 5 and 256")
    if type(horizon_bars) is not int or not 1 <= horizon_bars <= 200:
        raise ValueError("horizon_bars must be an integer between 1 and 200")
    seconds = export.get("seconds")
    if seconds not in (60, 300, 900):
        raise ValueError("source must have 60, 300 or 900-second candles")
    symbol = export.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("missing market symbol")
    records = export.get("candles")
    if not isinstance(records, list) or len(records) < lookback + horizon_bars + 1:
        raise ValueError("not enough closed candles")
    if len(records) > max_rows:
        raise ValueError("dataset exceeds bounded input size")
    source = records[0].get("source")
    if not isinstance(source, str) or not source:
        raise ValueError("missing price source")

    rows = sorted(records, key=lambda b: b["ts"])
    interval_ms = seconds * 1000
    times = []
    for row in rows:
        if (row.get("source") != source or row.get("symbol") != symbol or
                row.get("seconds") != seconds):
            raise ValueError("mixed source, symbol, or candle interval")
        stamp = row.get("ts")
        if type(stamp) is not int or stamp <= 0 or stamp % interval_ms:
            raise ValueError("invalid or unaligned timestamp")
        times.append(stamp)
        values = [row.get(k) for k in ("open", "high", "low", "close", "volume")]
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
            raise ValueError("invalid candle values")
        o, h, l, c, v = values
        if min(o, h, l, c) <= 0 or v < 0 or l > min(o, c) or h < max(o, c):
            raise ValueError("inconsistent OHLCV")
    if len(set(times)) != len(times):
        raise ValueError("duplicate candle timestamps")

    out = []
    # Decision occurs at the CLOSE of the last candle in the window.
    for end in range(lookback - 1, len(rows) - horizon_bars):
        begin = end + 1 - lookback
        exit_idx = end + horizon_bars
        if any(times[k + 1] - times[k] != interval_ms
               for k in range(begin, exit_idx)):
            continue
        recent = rows[begin:end+1]
        base = recent[0]["open"]
        if base <= 0:
            continue
        # Features are chart-invariant relative prices + normalized log-volume.
        # All normalization statistics come ONLY from current/past window.
        vols = [math.log1p(b["volume"]) for b in recent]
        vmean = sum(vols)/len(vols)
        variance = sum((x-vmean)**2 for x in vols)/len(vols)
        vscale = max(math.sqrt(variance), 1e-8)
        tensor = [
            [(b[k]/base)-1.0 for k in ("open", "high", "low", "close")]
            + [(vols[i]-vmean)/vscale]
            for i, b in enumerate(recent)
        ]
        entry = rows[end+1]["open"]
        exit_price = rows[exit_idx]["close"]
        out.append({
            "symbol": symbol, "price_source": source,
            "seconds": seconds, "lookback_bars": lookback,
            "horizon_bars": horizon_bars,
            "decision_ms": times[end] + interval_ms,
            "label_end_ms": times[exit_idx] + interval_ms,
            "tensor_ohlcv": tensor,
            "label_up": int(exit_price > entry),
            "future_return_proxy": exit_price/entry-1,
            "research_only": True
        })
    return {
        "status": "research_only_untrained",
        "symbol": symbol, "price_source": source, "seconds": seconds,
        "lookback_bars": lookback, "horizon_bars": horizon_bars,
        "feature_shape": [lookback, 5], "rows": out,
        "limitations": [
            "candle-sequence representation is an experimental CNN input, not proof of predictability",
            "returns use indicative next-open fills, not actual broker execution",
            "labels overlap: purge chronological splits before model fitting",
            "no 5-second or 30-second outputs from minute-only archive"
        ]
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--lookback", type=int, default=24)
    p.add_argument("--horizon-bars", type=int, default=5)
    args = p.parse_args()
    result = windows(json.loads(Path(args.input).read_text()),
                     lookback=args.lookback, horizon_bars=args.horizon_bars)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(result["rows"]), "status": result["status"]}))
