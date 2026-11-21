#!/usr/bin/env python3
"""Backfill the KAOS R2 candle archive from a local JSON/JSONL bar file.

Writes the exact schema the Cloudflare collector uses, so the archive stays
readable by kaos_r2_archive.read_archive():

    key   candles/v1/{source}/{asset_class}/{symbol}/{seconds}s/{YYYY-MM-DD}.json
    body  {"schema": "kaos_candles_v1", "candles": [ {...}, ... ]}

Safety:
  * additive only - a day whose object already exists is skipped, never merged
    or overwritten, preserving the collector's "keep first archived version"
    invariant;
  * every bar is validated against the same OHLCV rules as
    kaos_r2_archive.normalize() and rejected if it would fail;
  * dry run by default; requires --apply to write.

Credentials come from kaos_credentials (env / .env / the git-ignored
kaos_credentials_local.py). Nothing is hardcoded here.

Examples:
    # report current archive coverage for the symbol, write nothing
    python3 backfill-r2-candles.py --symbol BTC-USD --asset-class crypto --check

    # show what would be written
    python3 backfill-r2-candles.py --symbol BTC-USD --asset-class crypto \\
        --file BTC-USD.json.gz --source coinbase_exchange_public

    # write it
    python3 backfill-r2-candles.py --symbol BTC-USD --asset-class crypto \\
        --file BTC-USD.json.gz --source coinbase_exchange_public --apply
"""
import argparse
import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

SECONDS = 60
DEFAULT_SOURCE = "coinbase_exchange_public"
MAX_OBJECT_BYTES = 1_400_000  # read_archive refuses objects over 1,500,000


def load_credentials():
    live = os.environ.get("KAOS_LIVE_API_ROOT") or os.path.expanduser(
        "~/tradingwithkaos.com/backend")
    api_dir = os.path.join(live, "apps", "api")
    if os.path.isdir(api_dir):
        sys.path.insert(0, api_dir)
    try:
        import kaos_credentials  # noqa: F401  installs missing env vars
    except ImportError:
        pass  # fall back to plain environment variables

    cfg = {
        "account": os.environ.get("KAOS_R2_ACCOUNT_ID", ""),
        "key": os.environ.get("KAOS_R2_ACCESS_KEY_ID", ""),
        "secret": os.environ.get("KAOS_R2_SECRET_ACCESS_KEY", ""),
        "bucket": os.environ.get("KAOS_R2_BUCKET", "kaos-candle-archive"),
    }
    missing = [k for k in ("account", "key", "secret") if not cfg[k]]
    if missing:
        raise SystemExit(
            "Missing R2 settings: " + ", ".join("KAOS_R2_" + m.upper() for m in missing))
    return cfg


def client(cfg):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url="https://{}.r2.cloudflarestorage.com".format(cfg["account"]),
        aws_access_key_id=cfg["key"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            connect_timeout=20,
            read_timeout=120,
            retries={"max_attempts": 5, "mode": "adaptive"},
        ),
    )


def list_existing(s3, bucket):
    keys, token = set(), None
    while True:
        kw = {"Bucket": bucket, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        page = s3.list_objects_v2(**kw)
        keys.update(obj["Key"] for obj in page.get("Contents", []))
        if not page.get("IsTruncated"):
            return keys
        token = page.get("NextContinuationToken")


def load_bars(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "candles" in data:
        data = data["candles"]
    if not isinstance(data, list):
        raise SystemExit("Expected a JSON list of bars, or {candles: [...]}")
    return data


def valid(row, symbol, asset_class, source):
    """Mirror kaos_r2_archive.normalize() validation exactly."""
    try:
        ts = row["ts"]
        o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
        v = row.get("volume")
        v = None if v is None else float(v)
    except (KeyError, TypeError, ValueError):
        return False
    if not isinstance(ts, int) or isinstance(ts, bool):
        return False
    if row.get("symbol") != symbol or row.get("asset_class") != asset_class:
        return False
    if row.get("seconds") != SECONDS or row.get("source") != source:
        return False
    if ts <= 0 or ts % (SECONDS * 1000) != 0:
        return False
    if not all(x > 0 for x in (o, h, l, c)):
        return False
    if l > min(o, c) or h < max(o, c):
        return False
    if v is not None and (v != v or v < 0):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--asset-class", required=True,
                    choices=["stock", "etf", "crypto", "forex"])
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--file", help="JSON or JSON.gz list of {ts,open,high,low,close,volume}")
    ap.add_argument("--check", action="store_true", help="report coverage only")
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = ap.parse_args()

    cfg = load_credentials()
    s3 = client(cfg)
    existing = list_existing(s3, cfg["bucket"])
    prefix = "candles/v1/{}/{}/{}/{}s/".format(
        args.source, args.asset_class, args.symbol, SECONDS)
    have = sorted(k.rsplit("/", 1)[-1][:10] for k in existing if k.startswith(prefix))
    print("bucket: {}  existing objects: {}".format(cfg["bucket"], len(existing)))
    print("{} {}: {} archived day-file(s){}".format(
        args.symbol, args.source, len(have),
        (" [{} .. {}]".format(have[0], have[-1]) if have else "")))

    if args.check:
        for day in have:
            print("  " + day)
        return 0

    if not args.file:
        raise SystemExit("--file is required unless --check is used")

    bars = load_bars(args.file)
    by_day, rejected = defaultdict(list), 0
    for bar in bars:
        row = {
            "ts": int(bar["ts"]),
            "symbol": args.symbol,
            "asset_class": args.asset_class,
            "seconds": SECONDS,
            "source": args.source,
            "open": float(bar["open"]),
            "high": float(bar["high"]),
            "low": float(bar["low"]),
            "close": float(bar["close"]),
            "volume": float(bar["volume"]) if bar.get("volume") is not None else None,
        }
        if not valid(row, args.symbol, args.asset_class, args.source):
            rejected += 1
            continue
        day = datetime.fromtimestamp(row["ts"] / 1000, timezone.utc).date().isoformat()
        by_day[day].append(row)

    print("source bars: {}  days: {}  rejected: {}".format(
        len(bars), len(by_day), rejected))
    print("mode: {}".format("APPLY" if args.apply else "DRY RUN"))

    written = skipped = 0
    for day in sorted(by_day):
        key = "{}{}.json".format(prefix, day)
        rows = sorted(by_day[day], key=lambda r: r["ts"])
        if key in existing:
            print("  skip   {}  ({} bars, already archived)".format(day, len(rows)))
            skipped += 1
            continue
        body = json.dumps({"schema": "kaos_candles_v1", "candles": rows},
                          separators=(",", ":")).encode()
        if len(body) > MAX_OBJECT_BYTES:
            print("  SKIP   {}  {}B exceeds the archive read limit".format(day, len(body)))
            skipped += 1
            continue
        print("  {:6} {}  {} bars, {}B".format(
            "write" if args.apply else "would", day, len(rows), len(body)))
        if args.apply:
            s3.put_object(Bucket=cfg["bucket"], Key=key, Body=body,
                          ContentType="application/json")
        written += 1

    print("written={} skipped_existing={} rejected_bars={}".format(
        written, skipped, rejected))
    if not args.apply:
        print("dry run: nothing changed. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
