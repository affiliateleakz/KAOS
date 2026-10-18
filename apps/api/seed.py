"""Demo data seeding. All records clearly marked is_demo=True."""
import os
from datetime import timedelta
from db import db, new_id, now, now_iso
from auth import hash_password
from services import set_setting
from routes_billing import DEFAULT_PLANS

DEMO_PASSWORD = os.environ.get("KAOS_DEMO_PASSWORD", "")


async def seed_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError("ADMIN_PASSWORD must be set")
    existing = await db.users.find_one({"$or": [{"email": email}, {"username": "owner"}]})
    if existing is None:
        await db.users.insert_one({
            "id": new_id("user"), "email": email, "name": "Platform Owner",
            "username": "owner", "password_hash": hash_password(password),
            "role": "super_admin", "email_verified": True, "token_version": 0,
            "avatar": None, "bio": "Platform administrator", "auth_provider": "password",
            "account_status": "active", "onboarding_step": 9, "affiliate_status": "VERIFIED",
            "membership_status": "ACTIVE", "membership_plan": "ultimate",
            "membership_expires_at": (now() + timedelta(days=365)).isoformat(),
            "stripe_customer_id": None, "stripe_subscription_id": None,
            "extension_access_revoked": False, "license_id": new_id("lic"),
            "is_demo": False, "created_at": now_iso(), "updated_at": now_iso()})
    else:
        from auth import verify_password
        if not verify_password(password, existing.get("password_hash") or ""):
            await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password), "role": "super_admin"}})


async def _make_user(email, name, username, **over):
    doc = {"id": new_id("user"), "email": email.lower(), "name": name, "username": username,
           "password_hash": hash_password(DEMO_PASSWORD), "role": "user", "email_verified": True,
           "token_version": 0, "avatar": None, "bio": f"Demo trader {name}", "auth_provider": "password",
           "account_status": "active", "onboarding_step": 9, "affiliate_status": "VERIFIED",
           "membership_status": "ACTIVE", "membership_plan": "pro",
           "membership_expires_at": (now() + timedelta(days=30)).isoformat(),
           "stripe_customer_id": None, "stripe_subscription_id": None,
           "extension_access_revoked": False, "license_id": new_id("lic"),
           "is_demo": True, "created_at": now_iso(), "updated_at": now_iso()}
    doc.update(over)
    await db.users.insert_one(dict(doc))
    return doc


def is_dev():
    return os.environ.get("KAOS_ENV", "production").lower() in ("development", "dev", "test")


async def seed_demo():
    if not is_dev() or not DEMO_PASSWORD:
        return  # demo users only exist in local/dev environments
    if await db.users.find_one({"is_demo": True}):
        return  # already seeded
    await set_setting("plans", DEFAULT_PLANS)
    await set_setting("affiliate", {
        "affiliateUrl": "https://pocketoption.com/?ref=TRADINGPLATFORM",
        "programName": "Pocket Option Partners", "verificationMethod": "manual",
        "instructions": "Create your Pocket Option account using our referral link, then submit your Pocket Option UID here for manual verification by our team."})
    await set_setting("branding", {"productName": "KAOS Trading", "productBot": "KAOS Trading Bot", "tagline": "Trade With KAOS"})
    from services_trading import (DEFAULT_OFFICIAL_STRATEGY, DEFAULT_TRADING_CONFIG, DEFAULT_CONNECTORS)
    await set_setting("official_strategy", DEFAULT_OFFICIAL_STRATEGY)
    await set_setting("trading_config", DEFAULT_TRADING_CONFIG)
    await set_setting("connectors", DEFAULT_CONNECTORS)
    await db.ai_models.insert_one({"id": new_id("model"), "version": "kaos-ai-0.1.0-sim", "status": "deployed",
                                   "notes": "Placeholder simulated model registry entry.", "simulated": True, "createdAt": now_iso()})
    await set_setting("affiliate_program", {"enabled": True, "defaultRatePct": 30, "commissionType": "percentage",
                                            "recurring": True, "attributionWindowDays": 30, "holdDays": 30, "minPayout": 50, "perPlan": {}})
    # Multi-strategy library (official metadata boundaries; real logic migrates from bot source)
    KAOS_STRATS = [
        ("KAOS Berserker", "Signature deterministic strategy: established directional move -> exactly two counter-trend pullback candles -> continuation confirmation -> next-candle entry.",
         {"signalCandleSeconds": 5, "expiration": "45s", "indicators": ["EMA 9", "EMA 21", "ATR"], "pullbackCandles": 2, "confirmation": "continuation/reclaim"}),
        ("False Breakout", "Fade failed breakouts back into range.", {}),
        ("Trend Following", "Enter with the prevailing trend.", {}),
        ("Trend Reversal", "Confirmed reversal structure.", {}),
        ("Candlestick Pattern", "Classic candlestick pattern entries.", {}),
        ("Moving Average Crossover", "MA crossover entries.", {}),
        ("Price Action", "Pure price-action structure.", {}),
        ("Indicator-Based", "Configurable indicator confluence.", {}),
        ("Fibonacci", "Fibonacci retracement/extension entries.", {}),
    ]
    for name, desc, cfg in KAOS_STRATS:
        await db.strategy_library.insert_one({"id": new_id("lib"), "name": name, "description": desc,
                                              "type": "OFFICIAL", "locked": True, "editable": False, "version": 1,
                                              "config": cfg, "boundary": True, "createdAt": now_iso(), "is_demo": True})

    alice = await _make_user("alice@demotrader.com", "Alice Quant", "alice_quant", role="moderator")
    bob = await _make_user("bob@demotrader.com", "Bob Signals", "bob_signals")
    carol = await _make_user("carol@demotrader.com", "Carol Trend", "carol_trend",
                             membership_status="PAST_DUE", affiliate_status="PENDING")
    dave = await _make_user("dave@demotrader.com", "Dave Scalp", "dave_scalp",
                            membership_status="EXPIRED", affiliate_status="NOT_STARTED", onboarding_step=3)

    # Built-in protected strategy metadata
    await db.strategies.insert_one({
        "id": new_id("strat"), "ownerUserId": alice["id"], "ownerUsername": "system",
        "name": "Candidate 7B", "description": "Protected built-in momentum strategy shipped with the extension.",
        "version": 3, "type": "BUILT_IN", "editable": False, "locked": True, "visibility": "PUBLIC",
        "engineType": "signal", "signalTimeframe": "1m", "expiry": "5m",
        "indicators": [{"name": "EMA"}, {"name": "RSI"}], "indicatorSettings": {}, "rules": [], "parameters": {},
        "tags": ["built-in", "momentum"], "category": "momentum", "published": True, "publishedAt": now_iso(),
        "forkedFromStrategyId": None, "forkedFromVersion": None,
        "likesCount": 42, "savesCount": 30, "forksCount": 0, "commentsCount": 1,
        "is_demo": True, "createdAt": now_iso(), "updatedAt": now_iso()})

    async def make_strat(owner, name, desc, inds, tf, exp, pub=True, likes=0, saves=0):
        sid = new_id("strat")
        doc = {"id": sid, "ownerUserId": owner["id"], "ownerUsername": owner["username"],
               "name": name, "description": desc, "version": 1, "type": "CUSTOM", "editable": True, "locked": False,
               "visibility": "PUBLIC" if pub else "PRIVATE", "engineType": "signal", "signalTimeframe": tf, "expiry": exp,
               "indicators": inds, "indicatorSettings": {}, "rules": [], "parameters": {}, "tags": ["demo"], "category": "trend",
               "published": pub, "publishedAt": now_iso() if pub else None, "forkedFromStrategyId": None, "forkedFromVersion": None,
               "likesCount": likes, "savesCount": saves, "forksCount": 0, "commentsCount": 0,
               "is_demo": True, "createdAt": now_iso(), "updatedAt": now_iso()}
        await db.strategies.insert_one(dict(doc))
        await db.strategy_versions.insert_one({"id": new_id("sv"), "strategyId": sid, "version": 1, "name": name,
                                               "changelog": "Initial version", "indicators": inds, "createdAt": now_iso()})
        return doc

    s1 = await make_strat(alice, "EMA Trend Rider", "Follows EMA crossovers on 1m for 5m expiries.",
                          [{"name": "EMA 9"}, {"name": "EMA 21"}], "1m", "5m", True, 18, 12)
    s2 = await make_strat(bob, "RSI Reversal Pro", "Mean-reversion using RSI extremes.",
                          [{"name": "RSI"}, {"name": "Bollinger"}], "5m", "15m", True, 25, 20)
    await make_strat(bob, "Bob Private Draft", "A private WIP strategy.", [{"name": "MACD"}], "1m", "3m", False)
    s3 = await make_strat(carol, "MACD Momentum", "MACD histogram momentum entries.",
                          [{"name": "MACD"}], "15m", "30m", True, 9, 5)

    await db.comments.insert_one({"id": new_id("cmt"), "targetType": "strategy", "targetId": s1["id"],
                                  "authorId": bob["id"], "body": "Great results on EUR/USD, thanks for sharing!",
                                  "parentId": None, "hidden": False, "is_demo": True, "createdAt": now_iso()})
    await db.comments.insert_one({"id": new_id("cmt"), "targetType": "strategy", "targetId": s2["id"],
                                  "authorId": alice["id"], "body": "How does it handle ranging markets?",
                                  "parentId": None, "hidden": False, "is_demo": True, "createdAt": now_iso()})
    await db.strategies.update_one({"id": s1["id"]}, {"$inc": {"commentsCount": 1}})
    await db.strategies.update_one({"id": s2["id"]}, {"$inc": {"commentsCount": 1}})

    await db.follows.insert_one({"followerId": bob["id"], "followingId": alice["id"], "createdAt": now_iso()})
    await db.follows.insert_one({"followerId": carol["id"], "followingId": alice["id"], "createdAt": now_iso()})
    await db.strategy_likes.insert_one({"id": new_id("like"), "strategyId": s1["id"], "userId": bob["id"], "createdAt": now_iso()})
    await db.strategy_saves.insert_one({"id": new_id("save"), "strategyId": s2["id"], "userId": alice["id"], "createdAt": now_iso()})
    await db.strategy_installations.insert_one({"id": new_id("inst"), "strategyId": s2["id"], "userId": alice["id"], "installedVersion": 1, "createdAt": now_iso()})

    await db.notifications.insert_one({"id": new_id("ntf"), "userId": alice["id"], "type": "new_follower",
                                       "message": "bob_signals followed you", "link": "/u/bob_signals",
                                       "read": False, "is_demo": True, "createdAt": now_iso()})
    await db.notifications.insert_one({"id": new_id("ntf"), "userId": alice["id"], "type": "strategy_liked",
                                       "message": "bob_signals liked EMA Trend Rider", "link": f"/community/{s1['id']}",
                                       "read": False, "is_demo": True, "createdAt": now_iso()})

    await db.devices.insert_one({"id": new_id("dev"), "userId": alice["id"], "deviceName": "Alice Chrome (Work)",
                                 "installId": "demo-install-alice-1", "extensionVersion": "1.4.0", "lastIp": "203.0.113.4",
                                 "revoked": False, "lastActive": now_iso(), "is_demo": True, "createdAt": now_iso()})
    await db.devices.insert_one({"id": new_id("dev"), "userId": bob["id"], "deviceName": "Bob Chrome",
                                 "installId": "demo-install-bob-1", "extensionVersion": "1.3.0", "lastIp": "203.0.113.9",
                                 "revoked": False, "lastActive": now_iso(), "is_demo": True, "createdAt": now_iso()})

    await db.affiliate_referrals.insert_one({"id": new_id("aff"), "userId": carol["id"], "poUid": "PO-77345",
                                             "email": "carol@demotrader.com", "note": "Signed up via referral link",
                                             "status": "PENDING", "verifier": "manual", "is_demo": True,
                                             "createdAt": now_iso(), "updatedAt": now_iso()})
    await db.affiliate_verifications.insert_one({"id": new_id("affv"), "userId": carol["id"], "poUid": "PO-77345",
                                                 "status": "MANUAL_REVIEW", "is_demo": True, "createdAt": now_iso()})

    await db.backtest_reports.insert_one({"id": new_id("bt"), "ownerUserId": alice["id"], "strategyId": s1["id"],
                                          "strategyVersion": 1, "market": "EUR/USD", "timeframe": "1m", "expiry": "5m",
                                          "sampleStart": "2026-01-01", "sampleEnd": "2026-03-01", "trades": 240,
                                          "wins": 141, "losses": 92, "ties": 7, "winRate": 58.75, "maxLossStreak": 6,
                                          "provenance": "manual", "verified": False, "is_demo": True, "createdAt": now_iso()})

    await db.indicators.insert_one({"id": new_id("ind"), "ownerUserId": None, "author": "system", "name": "RSI",
                                    "description": "Relative Strength Index", "category": "momentum", "parameters": {"period": 14},
                                    "version": 1, "type": "BUILT_IN", "visibility": "PUBLIC", "is_demo": True,
                                    "createdAt": now_iso(), "updatedAt": now_iso()})
    await db.indicators.insert_one({"id": new_id("ind"), "ownerUserId": alice["id"], "author": "alice_quant",
                                    "name": "Custom Volatility Band", "description": "User-made band indicator",
                                    "category": "volatility", "parameters": {"mult": 2.0}, "version": 1, "type": "CUSTOM",
                                    "visibility": "PUBLIC", "is_demo": True, "createdAt": now_iso(), "updatedAt": now_iso()})

    await db.extension_releases.insert_one({"id": new_id("rel"), "version": "1.4.0",
                                            "releaseNotes": "Cloud sync improvements and license API v1 support.",
                                            "minSupportedVersion": "1.2.0", "recommendedVersion": "1.4.0",
                                            "downloadUrl": "https://chrome.google.com/webstore/detail/demo",
                                            "mandatory": False, "published": True, "is_demo": True, "createdAt": now_iso()})

    # SIMULATED trading telemetry (clearly flagged) so Trading Ops has demo data
    import random
    engines = ["REVERSAL", "RUNNER", "BREAKOUT"]
    exp = {"REVERSAL": "30s", "RUNNER": "15s", "BREAKOUT": "30s"}
    for i in range(24):
        owner = bob if i % 2 == 0 else alice
        eng = engines[i % 3]
        direction = "BUY" if i % 2 == 0 else "SELL"
        sig_id = new_id("sig")
        await db.signals.insert_one({"id": sig_id, "userId": owner["id"], "asset": "EUR/USD", "platform": "pocket_option",
                                     "tradingMode": ["STRATEGY", "AI", "STRATEGY_AI"][i % 3], "engine": eng,
                                     "direction": direction, "expiration": exp[eng], "state": "SIGNAL_DELIVERED",
                                     "simulated": True, "is_demo": True, "createdAt": now_iso()})
        r = i % 5
        if r == 0:
            state, result, pnl, fail = "ORDER_FAILED", None, None, "BROKER_REJECTED"
        elif r == 4:
            state, result, pnl, fail = "TRADE_OPEN", None, None, None
        else:
            state = "TRADE_RESULT"; result = "WIN" if r in (1, 2) else "LOSS"
            pnl = 0.85 if result == "WIN" else -1.0; fail = None
        await db.trades.insert_one({"id": new_id("trade"), "executionAttemptId": f"demo-att-{i}", "signalId": sig_id,
                                    "userId": owner["id"], "deviceId": None, "licenseId": owner.get("license_id"),
                                    "platform": "pocket_option", "asset": "EUR/USD", "direction": direction,
                                    "tradingMode": ["STRATEGY", "AI", "STRATEGY_AI"][i % 3], "engine": eng,
                                    "strategyVersion": "1.0.0", "aiModelVersion": "kaos-ai-0.1.0-sim",
                                    "requestedAmount": 1.0, "requestedExpiration": exp[eng],
                                    "state": state, "result": result, "pnl": pnl, "failureCode": fail,
                                    "entryPrice": 1.0854 if state != "ORDER_FAILED" else None,
                                    "simulated": True, "is_demo": True, "createdAt": now_iso(), "updatedAt": now_iso()})


async def write_credentials():
    path = os.environ.get("KAOS_TEST_CREDENTIALS_PATH")
    if not is_dev() or not path:
        return  # never write plaintext credentials outside an explicit local dev opt-in
    content = f"""# Test Credentials

## Admin / Owner (super_admin)
- Email: {os.environ.get('ADMIN_EMAIL')}
- Password: {os.environ.get('ADMIN_PASSWORD')}
- Role: super_admin

## Demo Members (password: {DEMO_PASSWORD})
- alice@demotrader.com  (moderator, ACTIVE, affiliate VERIFIED) username: alice_quant
- bob@demotrader.com    (user, ACTIVE, affiliate VERIFIED)      username: bob_signals
- carol@demotrader.com  (user, PAST_DUE, affiliate PENDING)     username: carol_trend
- dave@demotrader.com   (user, EXPIRED, affiliate NOT_STARTED)  username: dave_scalp

## Auth endpoints (web, cookie-based)
- POST /api/auth/register | /api/auth/login | /api/auth/logout | /api/auth/refresh
- GET  /api/auth/me
- POST /api/auth/forgot-password | /api/auth/reset-password | /api/auth/verify-email
- POST /api/auth/google/session  (Emergent Google OAuth)

## Extension v1 API (bearer tokens in JSON body)
- POST /api/v1/auth/login  -> returns accessToken/refreshToken
- GET  /api/v1/license/status  (Authorization: Bearer <accessToken>)
- POST /api/v1/devices/register | GET /api/v1/devices | DELETE /api/v1/devices/:id
- GET  /api/v1/extension/latest | /api/v1/sync | POST /api/v1/sync

## Stripe test card
- 4242 4242 4242 4242, any future expiry, any CVC
"""
    with open(path, "w") as f:
        f.write(content)
