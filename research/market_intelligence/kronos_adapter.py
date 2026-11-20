"""KAOS Kronos external-model research adapter (offline only).

No hosted service, production import, orders or automatic model downloads.
Run with --execute ONLY in a separately installed, trusted Kronos environment.
Kronos upstream: https://github.com/shiyu-coder/Kronos (MIT).
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path

ALLOWED_INTERVALS = (60, 300, 900)
MODEL_CONFIGS = {
    "mini": {"model": "NeoQuasar/Kronos-mini", "tokenizer": "NeoQuasar/Kronos-Tokenizer-2k", "max_context": 2048},
    "small": {"model": "NeoQuasar/Kronos-small", "tokenizer": "NeoQuasar/Kronos-Tokenizer-base", "max_context": 512},
    "base": {"model": "NeoQuasar/Kronos-base", "tokenizer": "NeoQuasar/Kronos-Tokenizer-base", "max_context": 512},
}


def prepare(export, *, lookback=128, pred_len=5, model_name="mini"):
    """Reject incomplete, heterogeneous or discontinuous candle windows.

    Timestamps are UTC open times; the last observed bar is assumed closed by
    the owner archive's export contract. This cannot verify live freshness.
    """
    config = MODEL_CONFIGS.get(model_name)
    if config is None:
        raise ValueError("unsupported Kronos model variant")
    if type(lookback) is not int or not 32 <= lookback <= config["max_context"]:
        raise ValueError("lookback outside supported context")
    if type(pred_len) is not int or not 1 <= pred_len <= 120:
        raise ValueError("invalid future candle count")
    seconds=export.get("seconds")
    if type(seconds) is not int or seconds not in ALLOWED_INTERVALS:
        raise ValueError("unsupported candle interval; 5s and 30s are not validated")
    symbol=export.get("symbol")
    klass=export.get("asset_class")
    if not isinstance(symbol,str) or not symbol.strip() or klass not in ("crypto","stock","forex"):
        raise ValueError("missing market or asset class")
    source_rows=export.get("candles")
    if not isinstance(source_rows,list) or len(source_rows)<lookback:
        raise ValueError("insufficient candle history")
    if len(source_rows)>100000:
        raise ValueError("unbounded input")
    rows=sorted(source_rows,key=lambda b:b["ts"])
    interval=seconds*1000
    feed=rows[-1].get("source")
    if not isinstance(feed,str) or not feed:
        raise ValueError("missing price source")
    for row in rows:
        if (row.get("symbol")!=symbol or row.get("seconds")!=seconds or
                row.get("source")!=feed or row.get("asset_class",klass)!=klass):
            raise ValueError("mixed market, source or timeframe")
        stamp=row.get("ts")
        if type(stamp) is not int or stamp<=0 or stamp%interval:
            raise ValueError("invalid candle UTC timestamp")
        vals=[row.get(k) for k in ("open","high","low","close","volume")]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):
            raise ValueError("invalid OHLCV")
        o,h,l,c,v=vals
        if min(o,h,l,c)<=0 or v<0 or l>min(o,c) or h<max(o,c):
            raise ValueError("inconsistent OHLCV")
    if len({r["ts"] for r in rows})!=len(rows):
        raise ValueError("duplicate timestamps")
    used=rows[-lookback:]
    if any(b["ts"]-a["ts"]!=interval for a,b in zip(used,used[1:])):
        raise ValueError("missing candles in context; refuse forward fill")
    # Model expects a historical UTC timestamp series and future timestamps.
    # No future candles enter input, only deterministic future time coordinates.
    historical=[dt.datetime.fromtimestamp(r["ts"]/1000,dt.timezone.utc).isoformat()
                for r in used]
    last_close=used[-1]["ts"]+interval
    future=[dt.datetime.fromtimestamp((last_close+i*interval)/1000,dt.timezone.utc).isoformat()
            for i in range(pred_len)]
    return {
        "status":"research_input_ready_not_forecast",
        "model_variant":model_name,"model_id":config["model"],
        "tokenizer_id":config["tokenizer"],"max_context":config["max_context"],
        "symbol":symbol,"asset_class":klass,"source":feed,"seconds":seconds,
        "lookback":lookback,"pred_len":pred_len,"decision_ms":last_close,
        "historical_timestamps_utc":historical,"future_timestamps_utc":future,
        "ohlcv":[{k:float(r[k]) for k in ("open","high","low","close","volume")}
                 for r in used],
        "note":"Offline research input; future time labels are not future price observations",
    }


def forecast(prepared, *, model_directory, device="cpu", sample_count=1):
    """Explicit opt-in external Kronos inference in isolated Python environment.

    Caller supplies a trusted local checkout on PYTHONPATH; model weights are
    retrieved by upstream only upon explicit invocation. Validate downloaded
    weights provenance and provider-specific terms first.
    """
    if prepared.get("status")!="research_input_ready_not_forecast":
        raise ValueError("unvalidated research input")
    if device not in ("cpu","cuda:0"):
        raise ValueError("unsupported device")
    if type(sample_count) is not int or not 1<=sample_count<=10:
        raise ValueError("sample_count must be 1..10")
    if not model_directory:
        raise ValueError("specify the trusted Kronos checkout")
    import sys
    import pandas as pd
    checkpoint=Path(model_directory).resolve()
    if not (checkpoint/"model"/"__init__.py").is_file():
        raise ValueError("model_directory must be a trusted Kronos source checkout")
    sys.path.insert(0,str(checkpoint))
    try:
        from model import Kronos, KronosTokenizer, KronosPredictor
        tokenizer=KronosTokenizer.from_pretrained(prepared["tokenizer_id"])
        model=Kronos.from_pretrained(prepared["model_id"])
        predictor=KronosPredictor(model,tokenizer,max_context=prepared["max_context"],device=device)
        frame=pd.DataFrame(prepared["ohlcv"])
        x_time=pd.to_datetime(prepared["historical_timestamps_utc"],utc=True).tz_localize(None).to_series(index=range(len(frame)))
        y_time=pd.to_datetime(prepared["future_timestamps_utc"],utc=True).tz_localize(None).to_series(index=range(prepared["pred_len"]))
        out=predictor.predict(df=frame,x_timestamp=x_time,
                              y_timestamp=y_time,pred_len=prepared["pred_len"],
                              T=1.0,top_p=.9,sample_count=sample_count,verbose=False)
        candles=out[["open","high","low","close","volume"]].to_dict(orient="records")
        if len(candles)!=prepared["pred_len"]:
            raise ValueError("unexpected predicted candle count")
        for r in candles:
            vals=list(r.values())
            if any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in vals):
                raise ValueError("non-finite forecast")
            if min(r["open"],r["high"],r["low"],r["close"])<=0 or r["volume"]<0:
                raise ValueError("invalid model forecast")
        return {"status":"unvalidated_research_forecast","model":prepared["model_id"],
                "symbol":prepared["symbol"],"decision_ms":prepared["decision_ms"],
                "timestamps_utc":prepared["future_timestamps_utc"],
                "forecast_ohlcv":candles,"sample_count":sample_count,
                "authority":"RESEARCH_ONLY","verified_accuracy":None,
                "note":"No known live trading advantage. Not an execution-ready signal."}
    finally:
        sys.path.remove(str(checkpoint))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--lookback",type=int,default=128)
    p.add_argument("--pred-len",type=int,default=5)
    p.add_argument("--model",choices=sorted(MODEL_CONFIGS),default="mini")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--kronos-checkout")
    p.add_argument("--device",choices=["cpu","cuda:0"],default="cpu")
    a=p.parse_args()
    prepared=prepare(json.loads(Path(a.input).read_text()),lookback=a.lookback,
                     pred_len=a.pred_len,model_name=a.model)
    if a.execute:
        if not a.kronos_checkout:
            p.error("--execute requires --kronos-checkout")
        result=forecast(prepared,model_directory=a.kronos_checkout,device=a.device)
    else:
        result=prepared
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"symbol":result["symbol"]}))


if __name__=="__main__":
    main()
