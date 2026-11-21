"""Baked-in provider credentials for this deployment.

=====================================================================
HOW THIS WORKS
=====================================================================
This module is committed to the repository and therefore contains **no
secrets**. Real values live in one of two places, both outside version control:

1. ``kaos_credentials_local.py`` in this same directory (git-ignored). This is
   the "hardcoded on the server" file. Create it once on the host and it
   survives every ``git pull``.
2. Environment variables, including the deployment ``.env``.

Precedence, highest first:

    process environment  >  .env  >  kaos_credentials_local.py  >  nothing

``install()`` never overwrites a variable that is already set, so a rotated key
can be supplied through the environment without editing any file.

=====================================================================
WHY NOT IN THIS FILE
=====================================================================
``github.com/affiliateleakz/KAOS`` is a **public** repository (verified: an
anonymous ``git clone`` succeeds). A secret committed here is published to the
internet permanently and remains in git history after deletion. Keep live keys
on the host, not in the repo. If the repository is ever made private, this file
can hold the values directly.

Env vars installed (the exact names the application reads):

    ALPHA_VANTAGE_API_KEY       Alpha Vantage market data
    FRED_API_KEY                St. Louis Fed economic data
    CLOUDFLARE_ACCOUNT_ID       Cloudflare account (also the R2 endpoint host)
    CLOUDFLARE_API_TOKEN        Cloudflare REST API token (NOT used by R2)
    KAOS_R2_ACCOUNT_ID          R2 S3 API account id
    KAOS_R2_ACCESS_KEY_ID       R2 S3 access key
    KAOS_R2_SECRET_ACCESS_KEY   R2 S3 secret key
    KAOS_R2_BUCKET              R2 bucket for candle archives
    KAOS_R2_ENABLED             "true" turns on R2-backed research/training
    APCA_API_KEY_ID             Alpaca market data / paper account id
    APCA_API_SECRET_KEY         Alpaca market data / paper secret
    KAOS_ALPACA_STOCK_FEED      iex (free) or sip (paid)
"""
import os

# Committed defaults. Empty on purpose: this repository is public.
DEFAULTS = {
    "ALPHA_VANTAGE_API_KEY": "",
    "FRED_API_KEY": "",
    "CLOUDFLARE_ACCOUNT_ID": "",
    "CLOUDFLARE_API_TOKEN": "",
    "KAOS_R2_ACCOUNT_ID": "",
    "KAOS_R2_ACCESS_KEY_ID": "",
    "KAOS_R2_SECRET_ACCESS_KEY": "",
    "KAOS_R2_BUCKET": "kaos-candle-archive",
    "KAOS_R2_ENABLED": "",
    "APCA_API_KEY_ID": "",
    "APCA_API_SECRET_KEY": "",
    "KAOS_ALPACA_STOCK_FEED": "iex",
    "KAOS_ALPACA_PAPER_KEY_ID": "",
    "KAOS_ALPACA_PAPER_SECRET_KEY": "",
}

# Deployment-local overrides. Absent from git by design; see the module docstring.
try:  # pragma: no cover - depends on the host
    from kaos_credentials_local import DEFAULTS as _LOCAL_DEFAULTS
except ImportError:
    _LOCAL_DEFAULTS = {}

if _LOCAL_DEFAULTS:
    DEFAULTS.update({k: v for k, v in _LOCAL_DEFAULTS.items() if v})


def install() -> list:
    """Apply baked-in values for any variable that is not already set.

    Returns the names that were applied. Existing environment values always
    win, so a rotated key can be supplied without touching this file.
    """
    applied = []
    for name, value in DEFAULTS.items():
        if not value:
            continue
        if os.environ.get(name):
            continue
        os.environ[name] = value
        applied.append(name)
    return applied


def summary() -> dict:
    """Non-sensitive readiness view. Never returns secret values."""
    def state(name):
        value = os.environ.get(name, "")
        return {"set": bool(value), "length": len(value)}

    return {
        "alpha_vantage": state("ALPHA_VANTAGE_API_KEY"),
        "fred": state("FRED_API_KEY"),
        "r2": {
            "account": state("KAOS_R2_ACCOUNT_ID"),
            "access_key": state("KAOS_R2_ACCESS_KEY_ID"),
            "secret": state("KAOS_R2_SECRET_ACCESS_KEY"),
            "bucket": os.environ.get("KAOS_R2_BUCKET", ""),
            "enabled": os.environ.get("KAOS_R2_ENABLED", "").lower() == "true",
        },
        "alpaca_market_data": {
            "key_id": state("APCA_API_KEY_ID"),
            "secret": state("APCA_API_SECRET_KEY"),
            "feed": os.environ.get("KAOS_ALPACA_STOCK_FEED", ""),
        },
        "alpaca_paper_orders": {
            "configured": bool(os.environ.get("KAOS_ALPACA_PAPER_KEY_ID")),
            "reason": "Alpaca PAPER orders require a verified per-member broker vault "
                      "connection; a server-side key alone does not enable order placement.",
        },
    }


install()
