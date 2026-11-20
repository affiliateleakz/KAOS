"""KAOS manually triggered historical candle backfill, research export only.

This deliberately never starts an unattended worker, writes to production
databases, or routes through trade execution. Provider access requires explicit
terms acknowledgement. Run from an isolated, permitted research environment.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from tvdatafeed_adapter import INTERVALS, fetch_once, normalize_history


def backfill(records, *, symbol, exchange, asset_class, seconds,
             observed_at_ms, source_tz=None):
    """Produce export compatible with KAOS candle research input consumers."""
    result=normalize_history(records,symbol=symbol,exchange=exchange,
                             asset_class=asset_class,seconds=seconds,
                             source_tz=source_tz,observed_at_ms=observed_at_ms)
    result["format_version"]="kaos_research_ohlcv_v1"
    result["usable_for_training"]=bool(result["closed_bar_count"]>=64 and
                                       result["noncontiguous_intervals"]==0)
    result["training_note"]=(
        "Candidate contiguous historical sample; no provider license, completeness, "
        "real-time status, or market-trading advantage has been established."
        if result["usable_for_training"] else
        "Do not train on this export without resolving missing history or gaps."
    )
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description="KAOS on-demand historical candle export")
    p.add_argument("--provider",choices=["tvdatafeed"],default="tvdatafeed")
    p.add_argument("--symbol",required=True)
    p.add_argument("--exchange",required=True)
    p.add_argument("--asset-class",choices=["stock","etf","crypto","forex"],required=True)
    p.add_argument("--seconds",type=int,choices=sorted(INTERVALS),default=60)
    p.add_argument("--bars",type=int,default=500)
    p.add_argument("--output",required=True)
    p.add_argument("--input-json",help="Offline fixture JSON with records array")
    p.add_argument("--fetch",action="store_true",
                   help="Explicitly fetch an authorized historical sample")
    p.add_argument("--acknowledge-provider-terms",action="store_true",
                   help="Confirm separately verified market-data access rights")
    p.add_argument("--source-timezone",
                   help="Timezone of naive provider stamps; e.g. UTC or America/New_York")
    args=p.parse_args(argv)
    if args.fetch==bool(args.input_json):
        p.error("Choose exactly one of --fetch and --input-json")
    if args.fetch and not args.acknowledge_provider_terms:
        p.error("--fetch requires --acknowledge-provider-terms")
    if not 1<=args.bars<=5000:
        p.error("--bars must be from 1 to 5000")
    tz=None
    if args.source_timezone:
        try: tz=ZoneInfo(args.source_timezone)
        except (ValueError,KeyError): p.error("Invalid --source-timezone")
    if args.fetch:
        if not args.source_timezone:
            p.error("--fetch requires an explicitly verified --source-timezone")
        records=fetch_once(symbol=args.symbol.upper(),exchange=args.exchange.upper(),
                           seconds=args.seconds,n_bars=args.bars)
    else:
        doc=json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        records=doc.get("records")
    result=backfill(records,symbol=args.symbol.upper(),exchange=args.exchange.upper(),
                    asset_class=args.asset_class,seconds=args.seconds,source_tz=tz,
                    observed_at_ms=int(datetime.now(timezone.utc).timestamp()*1000))
    target=Path(args.output)
    if target.exists():
        p.error("Output exists; choose a new filename to avoid overwriting an archive")
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False)
        f.write("\n")
    print(json.dumps({"file":str(target),"bars":result["closed_bar_count"],
                      "gaps":result["noncontiguous_intervals"],
                      "usable_for_training":result["usable_for_training"],
                      "status":result["status"]}))
    return result


if __name__=="__main__":
    main()
