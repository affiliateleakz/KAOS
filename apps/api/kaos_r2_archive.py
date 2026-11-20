"""Read private Cloudflare R2 candle archives for owner research and predictions.

R2 is accessed server-to-server with scoped S3 API credentials. Never expose
secrets or the bucket publicly. Only closed, source-identical, validated bars
are accepted; no mixing of Alpaca IEX/SIP or distinct Coinbase feeds.
"""
import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

SYMBOL_STOCK=re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")
SYMBOL_CRYPTO=re.compile(r"^[A-Z0-9]{2,10}-[A-Z]{3,5}$")
SYMBOL_FOREX=re.compile(r"^[A-Z]{3}_[A-Z]{3}$")
ACCOUNT=re.compile(r"^[0-9a-f]{32}$")
SAFE_BUCKET=re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
INTERVALS={60,300,900}

class ArchiveUnavailable(RuntimeError):
    pass

def configured():
    return os.getenv("KAOS_R2_ENABLED","").lower()=="true"

def source_for(asset_class):
    if asset_class=="crypto":
        return "coinbase_exchange_public"
    if asset_class in ("stock","etf"):
        feed=os.getenv("KAOS_R2_ALPACA_FEED","iex")
        if feed not in ("iex","sip"):
            raise ArchiveUnavailable("Unsupported R2 Alpaca feed")
        return "alpaca_"+feed
    if asset_class=="forex":
        mode=os.getenv("KAOS_R2_OANDA_ENVIRONMENT","practice")
        if mode not in ("practice","live"):
            raise ArchiveUnavailable("Unsupported R2 OANDA environment")
        return "oanda_"+mode+"_mid"
    raise ValueError("Unsupported asset class")

def validate_request(symbol,asset_class,seconds,limit):
    patterns={"stock":SYMBOL_STOCK,"etf":SYMBOL_STOCK,
              "crypto":SYMBOL_CRYPTO,"forex":SYMBOL_FOREX}
    if asset_class not in patterns or not patterns[asset_class].fullmatch(symbol):
        raise ValueError("Invalid R2 archive market")
    if seconds not in INTERVALS or not 100<=limit<=5000:
        raise ValueError("Invalid R2 timeframe or limit")
    return source_for(asset_class)

def _client():
    account=os.getenv("KAOS_R2_ACCOUNT_ID","")
    key=os.getenv("KAOS_R2_ACCESS_KEY_ID","")
    secret=os.getenv("KAOS_R2_SECRET_ACCESS_KEY","")
    bucket=os.getenv("KAOS_R2_BUCKET","kaos-candle-archive")
    if not ACCOUNT.fullmatch(account) or not key or not secret or not SAFE_BUCKET.fullmatch(bucket):
        raise ArchiveUnavailable("R2 account credentials not configured")
    client=boto3.client("s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=key,aws_secret_access_key=secret,
        region_name="auto",config=Config(signature_version="s3v4",
            connect_timeout=4,read_timeout=8,retries={"max_attempts":2}))
    return client,bucket

def _fetch_days(symbol,asset_class,seconds,source,limit,now_ms):
    s3,bucket=_client()
    # Use a bounded read window: stocks only trade on market days; crypto 24/7.
    days=32 if limit>300 else 10
    today=datetime.fromtimestamp(now_ms/1000,timezone.utc).date()
    gathered=[]
    for offset in range(days):
        day=today-timedelta(days=offset)
        path=f"candles/v1/{source}/{asset_class}/{symbol}/{seconds}s/{day.isoformat()}.json"
        try:
            result=s3.get_object(Bucket=bucket,Key=path)
        except ClientError as exc:
            error=exc.response.get("Error",{}).get("Code")
            if error in ("NoSuchKey","404","NotFound"):
                continue
            raise ArchiveUnavailable("R2 read unavailable") from exc
        except BotoCoreError as exc:
            raise ArchiveUnavailable("R2 read unavailable") from exc
        try:
            content=result["Body"].read(1_500_001)
            if len(content)>1_500_000:
                raise ArchiveUnavailable("R2 daily archive too large")
            payload=json.loads(content)
        except (ValueError,TypeError,UnicodeError) as exc:
            raise ArchiveUnavailable("Invalid R2 archive document") from exc
        if (payload.get("schema")!="kaos_candles_v1" or
            payload.get("symbol")!=symbol or
            payload.get("asset_class")!=asset_class or
            payload.get("seconds")!=seconds or
            payload.get("source")!=source or
            not isinstance(payload.get("candles"),list)):
            raise ArchiveUnavailable("R2 archive metadata mismatch")
        gathered.extend(payload["candles"])
        if len(gathered)>=limit+1500:
            break
    return gathered

def normalize(rows,symbol,asset_class,seconds,source,now_ms,limit):
    from routes_market_backfill import normalize_bars
    # Reject a mixed-provider archive rather than silently merging data.
    for row in rows:
        if (not isinstance(row,dict) or row.get("symbol")!=symbol
            or row.get("asset_class")!=asset_class or row.get("seconds")!=seconds
            or row.get("source")!=source):
            raise ArchiveUnavailable("R2 candle provider identity mismatch")
    normalized,_=normalize_bars(rows,symbol=symbol,asset_class=asset_class,
                                source=source,seconds=seconds,now_ms=now_ms)
    # normalize_bars caps at 300; validate in 300-bar chunks for owner research.
    return normalized[-limit:]

async def read_archive(symbol,asset_class,seconds,*,limit=300,now_ms=None):
    """Return (closed candles, source). Empty result means no existing R2 files.

    Never bypass credential errors silently in downstream research endpoints.
    """
    if not configured():
        return [],None
    source=validate_request(symbol,asset_class,seconds,limit)
    if now_ms is None:
        now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    rows=await asyncio.to_thread(_fetch_days,symbol,asset_class,seconds,source,limit,now_ms)
    # Preserve up to 5000 bars, source identity and OHLCV validation.
    from routes_market_backfill import normalize_bars
    valid={}
    for offset in range(0,len(rows),300):
        segment,_=normalize_bars(rows[offset:offset+300],symbol=symbol,
            asset_class=asset_class,source=source,seconds=seconds,now_ms=now_ms)
        for bar in segment:
            past=valid.get(bar["ts"])
            if past is not None and past!=bar:
                raise ArchiveUnavailable("Conflicting archived R2 candles")
            valid[bar["ts"]]=bar
    return sorted(valid.values(),key=lambda r:r["ts"])[-limit:],source
