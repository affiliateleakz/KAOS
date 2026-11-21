"""Catalog and encrypted storage for the third-party credentials member features need.

Admins enter a key once in /admin/api-keys. Values are encrypted at rest and then
applied to the process environment, so every existing provider call
(`os.getenv(...)` at request time) starts working without a redeploy or a restart.

Nothing here invents data: a provider with no key keeps reporting "not configured"
until an admin supplies one.
"""
import asyncio
import base64
import hashlib
import os
from datetime import datetime, timezone

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from db import db

# Every field's `env` is an environment variable the application already reads.
# `cost` and `get_it_at` are what the admin panel shows next to the input.
INTEGRATIONS = (
    {
        "id": "alpaca",
        "name": "Alpaca Market Data",
        "category": "Market data",
        "powers": ["Stock Heat Map", "Stock/ETF collectors", "Opportunity Radar (stock + ETF observations)"],
        "purpose": "Real US stock and ETF quotes for the heat map and the stock research collectors.",
        "get_it_at": "https://app.alpaca.markets/signup",
        "docs": "https://docs.alpaca.markets/docs/about-market-data-api",
        "cost": "Free: a free Alpaca account includes the IEX feed (partial exchange coverage). "
                "Full SIP coverage needs a paid market-data subscription.",
        "fields": [
            {"env": "APCA_API_KEY_ID", "label": "API Key ID", "secret": False, "hint": "PK…"},
            {"env": "APCA_API_SECRET_KEY", "label": "Secret Key", "secret": True, "hint": "shown once at creation"},
            {"env": "KAOS_ALPACA_STOCK_FEED", "label": "Feed (iex or sip)", "secret": False,
             "hint": "iex", "optional": True, "default": "iex", "public": True},
        ],
    },
    {
        "id": "tradier",
        "name": "Tradier Options",
        "category": "Market data",
        "powers": ["Options activity collector", "Opportunity Radar (options-flow observations)"],
        "purpose": "Listed-options expirations and chains for the options activity research feed.",
        "get_it_at": "https://developer.tradier.com/",
        "docs": "https://documentation.tradier.com/brokerage-api/markets/get-options-chains",
        "cost": "Free sandbox token (delayed data) after a free developer signup.",
        "fields": [
            {"env": "TRADIER_TOKEN", "label": "Access Token", "secret": True, "hint": "sandbox or production token"},
            {"env": "TRADIER_ENV", "label": "Environment (sandbox or production)", "secret": False,
             "hint": "sandbox", "optional": True, "default": "sandbox", "public": True},
        ],
    },
    {
        "id": "oanda",
        "name": "OANDA FX",
        "category": "Market data",
        "powers": ["FX price source", "Multi-asset scanner"],
        "purpose": "Foreign-exchange pricing for the multi-asset view.",
        "get_it_at": "https://www.oanda.com/demo-account/tpa/personal_token",
        "docs": "https://developer.oanda.com/rest-live-v20/introduction/",
        "cost": "Free practice account token.",
        "fields": [
            {"env": "OANDA_API_TOKEN", "label": "Practice API Token", "secret": True, "hint": "practice token"},
            {"env": "OANDA_ENV", "label": "Environment (practice or live)", "secret": False,
             "hint": "practice", "optional": True, "default": "practice", "public": True},
        ],
    },
    {
        "id": "alpha_vantage",
        "name": "Alpha Vantage",
        "category": "Market data",
        "powers": ["Equity/ETF/FX quotes", "Technical indicators", "Fundamental data"],
        "purpose": "Second market-data source for quotes, indicators and symbol search.",
        "get_it_at": "https://www.alphavantage.co/support/#api-key",
        "docs": "https://www.alphavantage.co/documentation/",
        "cost": "Free key: 25 requests/day. Premium plans raise the limit.",
        "fields": [
            {"env": "ALPHA_VANTAGE_API_KEY", "label": "API Key", "secret": True, "hint": "16-character key"},
        ],
    },
    {
        "id": "fred",
        "name": "St. Louis Fed (FRED)",
        "category": "Market data",
        "powers": ["Macro series (rates, CPI, unemployment)", "AI macro context"],
        "purpose": "Official US macro and rate series for research context and regime features.",
        "get_it_at": "https://fred.stlouisfed.org/docs/api/api_key.html",
        "docs": "https://fred.stlouisfed.org/docs/api/fred/",
        "cost": "Free. No request cap for normal research use.",
        "fields": [
            {"env": "FRED_API_KEY", "label": "API Key", "secret": True, "hint": "32-character key"},
        ],
    },
    {
        "id": "cloudflare_r2",
        "name": "Cloudflare R2 candle archive",
        "category": "Internal",
        "powers": ["AI training data", "Paper-loop candle source", "Backtest archives"],
        "purpose": "Private S3-compatible bucket holding the closed-candle history used by the "
                   "training worker and the AI paper loop.",
        "get_it_at": "https://dash.cloudflare.com/?to=/:account/r2/api-tokens",
        "docs": "https://developers.cloudflare.com/r2/api/s3/api/",
        "cost": "R2 storage is billed per GB-month; egress is free.",
        "fields": [
            {"env": "KAOS_R2_ACCOUNT_ID", "label": "Account ID", "secret": True, "hint": "32 hex characters"},
            {"env": "KAOS_R2_ACCESS_KEY_ID", "label": "Access Key ID", "secret": True, "hint": "R2 S3 token"},
            {"env": "KAOS_R2_SECRET_ACCESS_KEY", "label": "Secret Access Key", "secret": True, "hint": "shown once"},
            {"env": "KAOS_R2_BUCKET", "label": "Bucket", "secret": False, "hint": "kaos-candle-archive",
             "optional": True, "default": "kaos-candle-archive", "public": True},
            {"env": "KAOS_R2_ENABLED", "label": "Enabled", "secret": False,
             "toggle": {"on": "true", "off": "false"}, "hint": "true", "optional": True},
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "category": "AI",
        "powers": ["KAOS AI insights", "AI learning lab"],
        "purpose": "Language-model insights on the KAOS AI page. Trading signals do not depend on it.",
        "get_it_at": "https://platform.openai.com/api-keys",
        "docs": "https://platform.openai.com/docs/models",
        "cost": "Paid, pay per token. No free tier for new accounts (as of 2026).",
        "fields": [
            {"env": "OPENAI_API_KEY", "label": "API Key", "secret": True, "hint": "sk-…"},
            {"env": "OPENAI_MODEL", "label": "Model", "secret": False, "hint": "gpt-4o-mini",
             "optional": True, "default": "gpt-4o-mini", "public": True},
        ],
    },
    {
        "id": "stripe",
        "name": "Stripe Billing",
        "category": "Payments",
        "powers": ["Membership checkout", "Subscriptions", "Affiliate commissions"],
        "purpose": "Card payments and subscription state for paid memberships.",
        "get_it_at": "https://dashboard.stripe.com/apikeys",
        "docs": "https://docs.stripe.com/webhooks",
        "cost": "No monthly fee; Stripe charges a percentage per transaction.",
        "fields": [
            {"env": "STRIPE_SECRET_KEY", "label": "Secret Key", "secret": True, "hint": "sk_live_… or sk_test_…"},
            {"env": "STRIPE_WEBHOOK_SECRET", "label": "Webhook Signing Secret", "secret": True,
             "hint": "whsec_…", "optional": True},
        ],
    },
    {
        "id": "google",
        "name": "Google Sign-In",
        "category": "Accounts",
        "powers": ["Google button on the login page"],
        "purpose": "Verifies the Google ID token so members can sign in without a password.",
        "get_it_at": "https://console.cloud.google.com/apis/credentials",
        "docs": "https://developers.google.com/identity/gsi/web/guides/verify-google-id-token",
        "cost": "Free.",
        "fields": [
            {"env": "GOOGLE_CLIENT_ID", "label": "Web Client ID", "secret": False,
             "hint": "…apps.googleusercontent.com", "public": True},
        ],
    },
    {
        "id": "sec_edgar",
        "name": "SEC EDGAR (free, no key)",
        "category": "Filings",
        "powers": ["Political & Wall Street Trades Scanner (Form 4 insider trades)"],
        "purpose": "SEC only requires an identifying User-Agent with a contact email. No key, no account.",
        "get_it_at": "https://www.sec.gov/os/webmaster-faq#developers",
        "docs": "https://www.sec.gov/developer",
        "cost": "Free. SEC asks for max 10 requests/second and a real contact address.",
        "fields": [
            {"env": "KAOS_SEC_USER_AGENT", "label": "App name + contact email", "secret": False,
             "hint": "KAOS Research research@yourdomain.com"},
        ],
    },
    {
        "id": "congress",
        "name": "Congressional disclosures",
        "category": "Filings",
        "powers": ["Political trades (House / Senate filings)"],
        "purpose": "Unlocks congressional disclosure ingestion after you confirm you have reviewed the "
                   "House/Senate public-use terms for your business model.",
        "get_it_at": "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "docs": "https://efdsearch.senate.gov/search/",
        "cost": "Free public data. House filings carry commercial-use restrictions; this switch is your "
                "compliance decision, not a technical one.",
        "fields": [
            {"env": "KAOS_HOUSE_DISCLOSURE_RIGHTS", "label": "House disclosure rights", "secret": False,
             "toggle": {"on": "approved", "off": ""}, "hint": "approved"},
        ],
    },
    {
        "id": "email",
        "name": "Transactional email",
        "category": "Accounts",
        "powers": ["Password reset", "Email verification"],
        "purpose": "Delivers reset and verification links. Without it those flows silently do nothing.",
        "get_it_at": "https://resend.com/api-keys",
        "docs": "https://resend.com/docs/api-reference/emails/send-email",
        "cost": "Resend free tier: 100 emails/day. Any SMTP-compatible provider works if the proxy is pointed at it.",
        "fields": [
            {"env": "INTEGRATION_PROXY_URL", "label": "Provider base URL", "secret": False,
             "hint": "https://api.resend.com", "optional": True},
            {"env": "EMERGENT_EMAIL_KEY", "label": "Provider API key", "secret": True, "hint": "re_…",
             "optional": True},
        ],
    },
    {
        "id": "ethereum",
        "name": "Ethereum RPC",
        "category": "On-chain",
        "powers": ["Ethereum whale collector", "On-chain observations"],
        "purpose": "Read-only JSON-RPC endpoint for the on-chain whale collector.",
        "get_it_at": "https://www.alchemy.com/",
        "docs": "https://docs.alchemy.com/reference/ethereum-api-quickstart",
        "cost": "Alchemy and Infura both have free tiers.",
        "fields": [
            {"env": "ETH_RPC_URL", "label": "HTTPS RPC URL", "secret": True, "hint": "https://eth-mainnet…"},
        ],
    },
    {
        "id": "collector",
        "name": "Collector ingest key",
        "category": "Internal",
        "powers": ["Research collectors → API ingest", "SEC Form 4 refresh"],
        "purpose": "Shared secret the collector workers send so the API accepts their observations.",
        "get_it_at": "https://www.uuidgenerator.net/version4",
        "docs": "docs/INTEGRATIONS.md",
        "cost": "Free. Generate a random value yourself; it never leaves your server.",
        "fields": [
            {"env": "KAOS_COLLECTOR_KEY", "label": "Collector key", "secret": True, "hint": "random 32+ chars"},
        ],
    },
    {
        "id": "broker_vault",
        "name": "Broker credential vault",
        "category": "Internal",
        "powers": ["Coinbase connect page", "Live Coinbase orders"],
        "purpose": "Fernet key that encrypts member Coinbase API secrets at rest.",
        "get_it_at": "http://127.0.0.1:8000/admin/api-keys",
        "docs": "docs/INTEGRATIONS.md",
        "cost": "Free. Generate with: python -c \"from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())\"",
        "fields": [
            {"env": "KAOS_BROKER_VAULT_KEY", "label": "Fernet key", "secret": True, "hint": "44-char urlsafe base64"},
        ],
    },
)
BY_ID = {entry["id"]: entry for entry in INTEGRATIONS}
CATEGORY_ORDER = ("Market data", "Filings", "AI", "Payments", "Accounts", "On-chain", "Internal")

_ENV_ORIGINAL = {}
_APPLIED = set()


def _fernet():
    """Fernet for integration secrets.

    Prefers a dedicated key, then the broker vault key, then a key derived from
    JWT_SECRET so a standard deployment works without extra setup. The derived
    path is a convenience, not key separation: set KAOS_INTEGRATION_VAULT_KEY in
    production.
    """
    material = (os.getenv("KAOS_INTEGRATION_VAULT_KEY") or os.getenv("KAOS_BROKER_VAULT_KEY") or "").strip()
    if material:
        try:
            return Fernet(material.encode())
        except (ValueError, TypeError):
            raise HTTPException(503, "Integration vault key is not a valid Fernet key")
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 16:
        raise HTTPException(503, "Set KAOS_INTEGRATION_VAULT_KEY before saving API keys")
    digest = hashlib.sha256(b"kaos/integration-vault/v1:" + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _mask(value):
    if not value:
        return ""
    return "…" + value[-4:] if len(value) > 8 else "…"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fields_for(provider):
    entry = BY_ID.get(provider)
    if not entry:
        raise HTTPException(404, "Unknown integration")
    return entry, {f["env"]: f for f in entry["fields"]}


def _public_entry(entry, doc):
    stored = (doc or {}).get("values_enc") or {}
    fields = []
    filled = 0
    for field in entry["fields"]:
        current = os.getenv(field["env"], "")
        source = "admin" if field["env"] in stored else ("environment" if current else "none")
        is_set = bool(current) or field["env"] in stored
        if is_set:
            filled += 1
        fields.append({
            "env": field["env"],
            "label": field["label"],
            "secret": field.get("secret", True),
            "optional": field.get("optional", False),
            "toggle": field.get("toggle"),
            "hint": field.get("hint", ""),
            "default": field.get("default"),
            "set": is_set,
            "source": source,
            # Only fields explicitly marked public (feed names, model, client id)
            # are echoed back; every credential is reduced to a 4-character hint.
            "preview": ("" if field.get("toggle") else
                        (current if (current and field.get("public")) else _mask(current))),
        })
    required = [f for f in entry["fields"] if not f.get("optional")]
    ready = bool(required) and all(f["env"] in stored or os.getenv(f["env"]) for f in required)
    return {"id": entry["id"], "name": entry["name"], "category": entry["category"],
            "powers": entry["powers"], "purpose": entry["purpose"],
            "get_it_at": entry["get_it_at"], "docs": entry["docs"], "cost": entry["cost"],
            "fields": fields, "configured_fields": filled, "total_fields": len(entry["fields"]),
            "ready": ready, "updated_at": (doc or {}).get("updated_at"),
            "updated_by": (doc or {}).get("updated_by")}


async def apply_to_env():
    """Load encrypted values into the process environment.

    Database values win over the environment file so an admin edit takes effect
    immediately; removing a stored value restores whatever the environment had.
    """
    try:
        docs = await db.kaos_integration_secrets.find({}, {"_id": 0}).to_list(200)
    except Exception:
        return 0
    desired = {}
    for doc in docs:
        values = doc.get("values_enc") or {}
        if not values:
            continue
        try:
            fernet = _fernet()
        except HTTPException:
            return 0
        for env, token in values.items():
            try:
                desired[env] = fernet.decrypt(token.encode()).decode()
            except (InvalidToken, ValueError, AttributeError):
                continue
    known = {f["env"] for entry in INTEGRATIONS for f in entry["fields"]}
    for env, value in desired.items():
        if env not in known:
            continue
        _ENV_ORIGINAL.setdefault(env, os.environ.get(env))
        os.environ[env] = value
        _APPLIED.add(env)
    for env in list(_APPLIED - set(desired)):
        original = _ENV_ORIGINAL.pop(env, None)
        if original is None:
            os.environ.pop(env, None)
        else:
            os.environ[env] = original
        _APPLIED.discard(env)
    return len(desired)


async def catalog():
    try:
        docs = {d["provider"]: d for d in await db.kaos_integration_secrets.find({}, {"_id": 0}).to_list(200)}
    except Exception:
        docs = {}
    entries = [_public_entry(entry, docs.get(entry["id"])) for entry in INTEGRATIONS]
    entries.sort(key=lambda e: (CATEGORY_ORDER.index(e["category"]) if e["category"] in CATEGORY_ORDER else 99, e["name"]))
    return {
        "integrations": entries,
        "vault_ready": _vault_ready(),
        "vault_source": "KAOS_INTEGRATION_VAULT_KEY" if os.getenv("KAOS_INTEGRATION_VAULT_KEY")
                        else ("KAOS_BROKER_VAULT_KEY" if os.getenv("KAOS_BROKER_VAULT_KEY") else "derived from JWT_SECRET"),
        "keyless": [
            {"name": "DEX Screener", "powers": "Crypto Scanner pair search & token pools",
             "note": "No key. Runs as soon as a member opens the page."},
            {"name": "CoinGecko public API", "powers": "Crypto Heat Map / bubble map",
             "note": "No key. Public market caps and 1h/24h/7d changes; cached server-side because the "
                     "free tier is limited to a few requests per minute."},
            {"name": "Coinbase Exchange public stats", "powers": "Crypto bubble map fallback",
             "note": "No key. Used automatically when CoinGecko is rate limited; majors only, "
                     "sized by 24h dollar volume."},
            {"name": "Yahoo Finance preview", "powers": "Stock Heat Map fallback, news fallback",
             "note": "No key. Used automatically while Alpaca is not configured; unofficial and rate limited."},
            {"name": "Google News RSS", "powers": "Free political & Wall Street headlines",
             "note": "No key. Public RSS index, cached for five minutes; links stay on the publisher's "
                     "news host and are research leads only."},
            {"name": "SEC EDGAR", "powers": "Insider Form 3/4/5 and 13F filings",
             "note": "No key. Only a descriptive User-Agent with a contact email is required; "
                     "set it once under SEC EDGAR in this panel."},
        ],
    }


def _vault_ready():
    try:
        _fernet()
        return True
    except HTTPException:
        return False


async def save(provider, values, admin):
    entry, allowed = _fields_for(provider)
    clean = {}
    for env, raw in (values or {}).items():
        if env not in allowed:
            raise HTTPException(422, f"{env} is not a field of {entry['name']}")
        value = (raw or "").strip()
        field = allowed[env]
        if field.get("toggle"):
            if value not in (field["toggle"]["on"], field["toggle"]["off"], "on", "off", "true", "false"):
                raise HTTPException(422, f"{field['label']} must be on or off")
            value = field["toggle"]["on"] if value in ("on", "true", field["toggle"]["on"]) else field["toggle"]["off"]
        if field.get("secret") and value and len(value) < 8:
            raise HTTPException(422, f"{field['label']} is too short")
        clean[env] = value
    if not clean:
        raise HTTPException(422, "No values supplied")
    fernet = _fernet()
    encrypted = {env: fernet.encrypt(value.encode()).decode() for env, value in clean.items()}
    await db.kaos_integration_secrets.update_one(
        {"provider": provider},
        {"$set": {"provider": provider, "values_enc": encrypted,
                  "updated_at": _now(), "updated_by": (admin or {}).get("email") or (admin or {}).get("id")}},
        upsert=True)
    await apply_to_env()
    return _public_entry(entry, {"values_enc": encrypted, "updated_at": _now()})


async def remove(provider, admin):
    _entry, _allowed = _fields_for(provider)
    doc = await db.kaos_integration_secrets.find_one({"provider": provider}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Nothing stored for this integration")
    await db.kaos_integration_secrets.delete_one({"provider": provider})
    await apply_to_env()
    return {"provider": provider, "removed": True}


# ---------------------------------------------------------------- live checks

async def _get(client, url, **kwargs):
    response = await client.get(url, **kwargs)
    return response


async def _probe_r2():
    """Signed S3 list against the configured bucket. Read-only."""
    account = os.getenv("KAOS_R2_ACCOUNT_ID", "")
    key = os.getenv("KAOS_R2_ACCESS_KEY_ID", "")
    secret = os.getenv("KAOS_R2_SECRET_ACCESS_KEY", "")
    bucket = os.getenv("KAOS_R2_BUCKET", "kaos-candle-archive")
    if not (account and key and secret and bucket):
        return _fail("Add the account ID, access key, secret and bucket first")

    def _list():
        import boto3
        from botocore.config import Config
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=key, aws_secret_access_key=secret,
            region_name="auto",
            config=Config(signature_version="s3v4", connect_timeout=8, read_timeout=12))
        page = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        return int(page.get("KeyCount", 0))

    try:
        count = await asyncio.to_thread(_list)
    except Exception as exc:  # noqa: BLE001 - surfaced to the admin panel
        return _fail(f"R2 rejected the request: {type(exc).__name__}")
    return {"ok": True,
            "detail": f"Bucket '{bucket}' is readable" + (" and contains objects" if count else " (currently empty)"),
            "checked_at": _now()}


async def probe(provider):
    """One bounded live call against the provider using the currently active values."""
    entry, _allowed = _fields_for(provider)
    if provider == "cloudflare_r2":
        return await _probe_r2()
    timeout = httpx.Timeout(12.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        try:
            if provider == "alpaca":
                key, secret = os.getenv("APCA_API_KEY_ID", ""), os.getenv("APCA_API_SECRET_KEY", "")
                if not key or not secret:
                    return _fail("Add the API Key ID and Secret Key first")
                feed = os.getenv("KAOS_ALPACA_STOCK_FEED", "iex")
                r = await _get(client, "https://data.alpaca.markets/v2/stocks/snapshots",
                               params={"symbols": "AAPL", "feed": feed},
                               headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
                return _result(r, {200}, "Alpaca returned a live AAPL snapshot")
            if provider == "tradier":
                token = os.getenv("TRADIER_TOKEN", "")
                if not token:
                    return _fail("Add an access token first")
                host = "https://sandbox.tradier.com" if os.getenv("TRADIER_ENV", "sandbox").lower() != "production" else "https://api.tradier.com"
                r = await _get(client, host + "/v1/markets/quote", params={"symbols": "AAPL"},
                               headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
                return _result(r, {200}, "Tradier returned a live AAPL quote")
            if provider == "oanda":
                token = os.getenv("OANDA_API_TOKEN", "")
                if not token:
                    return _fail("Add a practice token first")
                host = "https://api-fxpractice.oanda.com" if os.getenv("OANDA_ENV", "practice").lower() != "live" else "https://api-fxtrade.oanda.com"
                r = await _get(client, host + "/v3/accounts", headers={"Authorization": f"Bearer {token}"})
                return _result(r, {200}, "OANDA accepted the token")
            if provider == "alpha_vantage":
                key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
                if not key:
                    return _fail("Add an API key first")
                r = await _get(client, "https://www.alphavantage.co/query",
                               params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": key})
                if r.status_code == 200 and "Global Quote" in r.text:
                    return {"ok": True, "detail": "Alpha Vantage returned a live AAPL quote", "checked_at": _now()}
                if "Information" in r.text or "Note" in r.text:
                    return _fail("Alpha Vantage accepted the key but the daily request limit is exhausted")
                return _result(r, {200}, "Alpha Vantage answered")
            if provider == "fred":
                key = os.getenv("FRED_API_KEY", "")
                if not key:
                    return _fail("Add an API key first")
                r = await _get(client, "https://api.stlouisfed.org/fred/series/observations",
                               params={"series_id": "DFF", "api_key": key, "file_type": "json",
                                       "limit": 1, "sort_order": "desc"})
                return _result(r, {200}, "FRED returned the latest effective fed funds rate")
            if provider == "openai":
                key = os.getenv("OPENAI_API_KEY", "")
                if not key:
                    return _fail("Add an API key first")
                r = await _get(client, "https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
                return _result(r, {200}, "OpenAI accepted the key")
            if provider == "stripe":
                key = os.getenv("STRIPE_SECRET_KEY", "")
                if not key:
                    return _fail("Add a secret key first")
                r = await _get(client, "https://api.stripe.com/v1/balance", headers={"Authorization": f"Bearer {key}"})
                return _result(r, {200}, "Stripe accepted the secret key")
            if provider == "google":
                client_id = os.getenv("GOOGLE_CLIENT_ID", "")
                if not client_id:
                    return _fail("Add the web client ID first")
                if not client_id.endswith(".apps.googleusercontent.com"):
                    return _fail("A web client ID ends with .apps.googleusercontent.com")
                return {"ok": True, "detail": "Client ID format is valid. The browser must use the same value.", "checked_at": _now()}
            if provider == "sec_edgar":
                agent = os.getenv("KAOS_SEC_USER_AGENT", "")
                if not agent:
                    return _fail('Set "App name + contact email" first')
                if "@" not in agent:
                    return _fail("SEC requires a contact email inside the User-Agent")
                r = await _get(client, "https://www.sec.gov/files/company_tickers.json",
                               headers={"User-Agent": agent, "Accept-Encoding": "gzip, deflate"})
                return _result(r, {200}, "SEC accepted the User-Agent")
            if provider == "ethereum":
                url = os.getenv("ETH_RPC_URL", "")
                if not url:
                    return _fail("Add an HTTPS RPC URL first")
                r = await client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})
                if r.status_code == 200 and "result" in r.text:
                    return {"ok": True, "detail": "RPC returned the current block number", "checked_at": _now()}
                return _fail(f"RPC answered HTTP {r.status_code} without a result")
            if provider == "congress":
                approved = os.getenv("KAOS_HOUSE_DISCLOSURE_RIGHTS") == "approved"
                return {"ok": True, "detail": "House disclosure ingestion is " + ("unlocked" if approved else "locked"),
                        "checked_at": _now()}
            if provider == "collector":
                return {"ok": bool(os.getenv("KAOS_COLLECTOR_KEY")),
                        "detail": "Collector key is set" if os.getenv("KAOS_COLLECTOR_KEY") else "No collector key",
                        "checked_at": _now()}
            if provider == "broker_vault":
                try:
                    _fernet()
                    return {"ok": True, "detail": "Vault key is usable", "checked_at": _now()}
                except HTTPException as exc:
                    return _fail(exc.detail)
            if provider == "email":
                url = os.getenv("INTEGRATION_PROXY_URL", "")
                key = os.getenv("EMERGENT_EMAIL_KEY", "")
                if not url or not key:
                    return _fail("Add the provider base URL and API key first")
                r = await _get(client, url.rstrip("/") + "/domains", headers={"Authorization": f"Bearer {key}"})
                return _result(r, {200}, "Email provider accepted the key")
        except httpx.HTTPError as exc:
            return _fail(f"Could not reach the provider: {type(exc).__name__}")
    return _fail("No live check exists for this integration")


def _result(response, ok_codes, detail):
    if response.status_code in ok_codes:
        return {"ok": True, "detail": detail, "checked_at": _now()}
    if response.status_code in (401, 403):
        return {"ok": False, "detail": f"Provider rejected the credential (HTTP {response.status_code})", "checked_at": _now()}
    return {"ok": False, "detail": f"Provider answered HTTP {response.status_code}", "checked_at": _now()}


def _fail(detail):
    return {"ok": False, "detail": detail, "checked_at": _now()}
