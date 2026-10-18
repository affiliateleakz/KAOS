"""Shared, research-only KAOS 3.0 provider integration helpers (stdlib only)."""
from datetime import datetime, timezone
from math import isfinite
from urllib.request import Request, urlopen
import json
import os

INGEST_PATH = '/api/v1/intelligence/ingest'


def utc(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('Invalid timestamp')
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def positive_float(value, default=0.0):
    try:
        n = float(value)
        return n if isfinite(n) and n >= 0 else default
    except (TypeError, ValueError, OverflowError):
        return default


def require_token(value, label):
    if not value or not str(value).strip():
        raise ValueError(f'{label} required in server-side environment')
    return value


def read_json(url, headers=None, opener=urlopen, timeout=20):
    req = Request(url, headers={'User-Agent': 'KAOS-Research-Only/3.0', **(headers or {})})
    with opener(req, timeout=timeout) as response:
        return json.load(response)


def submit(observations, api_base, collector_key=None, opener=urlopen):
    """Send only to configured KAOS API using collector key, never broker API."""
    if not api_base.startswith('https://') and not api_base.startswith('http://127.0.0.1:'):
        raise ValueError('KAOS_API_BASE must be HTTPS (except loopback development)')
    key = require_token(collector_key or os.getenv('KAOS_COLLECTOR_KEY'), 'KAOS_COLLECTOR_KEY')
    accepted = 0
    for i in range(0, len(observations), 250):
        batch = observations[i:i + 250]
        url = api_base.rstrip('/') + INGEST_PATH
        req = Request(url, data=json.dumps(batch, allow_nan=False).encode('utf-8'), method='POST',
                      headers={'Content-Type': 'application/json', 'X-KAOS-Collector-Key': key,
                               'User-Agent': 'KAOS-Research-Only/3.0'})
        with opener(req, timeout=25) as response:
            body = json.load(response)
            accepted += int(body.get('accepted', 0))
    return {'submitted': accepted, 'mode': 'research_only'}
