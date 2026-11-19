"""Isolated Mongo analytics lifecycle; no external visitor lookup or live customer data."""

import asyncio
from datetime import timedelta
import json
import os
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
import visitor_analytics as analytics
import analytics_geo as geo


def test_country_index_and_proxy_spoofing(monkeypatch):
    assert geo.country("8.8.8.8") == "US"
    assert geo.country("2001:4860:4860::8888") not in (
        "ZZ",
        "",
    )  # Anycast country is an estimate, not a fixed residency claim.
    assert geo.country("127.0.0.1") == "ZZ"
    assert geo.country("192.168.0.1") == "ZZ"
    assert geo.country("bad-ip") == "ZZ"
    request = SimpleNamespace(
        client=SimpleNamespace(host="8.8.4.4"), headers={"x-forwarded-for": "1.1.1.1"}
    )
    monkeypatch.delenv("KAOS_ANALYTICS_TRUSTED_PROXIES", raising=False)
    assert geo.client_address(request) == "8.8.4.4"
    monkeypatch.setenv("KAOS_ANALYTICS_TRUSTED_PROXIES", "10.0.0.0/8")
    request.client.host = "10.0.0.5"
    request.headers["x-forwarded-for"] = "1.1.1.1, 8.8.8.8"
    assert geo.client_address(request) == "8.8.8.8"


def test_analytics_end_to_end(monkeypatch):
    assert os.environ["MONGO_URL"] in (
        "mongodb://127.0.0.1:27017",
        "mongodb://localhost:27017",
    )
    assert os.environ["DB_NAME"] == "kaos_test"

    async def scenario():
        client = AsyncIOMotorClient(
            os.environ["MONGO_URL"], serverSelectionTimeoutMS=2000
        )
        database = client["kaos_test_analytics_" + uuid4().hex]
        monkeypatch.setattr(analytics, "db", database)
        monkeypatch.setattr(analytics, "_ready", False)
        monkeypatch.setattr(analytics, "_lock", asyncio.Lock())
        monkeypatch.setenv("FRONTEND_URL", "https://tradingwithkaos.com")
        app = FastAPI()
        app.include_router(analytics.router)
        identities = {
            "a": {
                "id": "affiliate-a",
                "role": "user",
                "membership_status": "ACTIVE",
                "stripe_subscription_id": "sub_fixture_a",
                "membership_expires_at": (
                    analytics.now() + timedelta(days=365)
                ).isoformat(),
            },
            "b": {
                "id": "affiliate-b",
                "role": "user",
                "membership_status": "ACTIVE",
                "stripe_subscription_id": "sub_fixture_b",
                "membership_expires_at": (
                    analytics.now() + timedelta(days=365)
                ).isoformat(),
            },
            "admin": {"id": "admin", "role": "admin"},
            "mod": {"id": "mod", "role": "moderator"},
        }

        async def identity(request: Request):
            user = identities.get(request.headers.get("authorization"))
            if not user:
                raise HTTPException(401, "Sign in")
            return user

        app.dependency_overrides[analytics.get_current_user] = identity
        try:
            await database.affiliate_accounts.insert_many(
                [
                    {"userId": "affiliate-a", "code": "CODE-A", "status": "active"},
                    {"userId": "affiliate-b", "code": "CODE-B", "status": "active"},
                ]
            )
            now = analytics.now()
            ends = (now + timedelta(days=7)).isoformat()
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app, client=("8.8.8.8", 123)),
                base_url="https://api.example.com",
            ) as browser:
                visitor, session = str(uuid4()), str(uuid4())
                base = {
                    "eventId": str(uuid4()),
                    "visitorId": visitor,
                    "sessionId": session,
                    "kind": "pageview",
                    "path": "/checkout?password=do-not-store",
                    "ref": "CODE-A",
                    "source": "email",
                    "medium": "affiliate",
                    "campaign": "launch",
                    "referrer": "https://example.com/path?token=do-not-store",
                    "entry": True,
                }
                for _ in range(2):
                    assert (
                        await browser.post("/api/analytics/visit", json=base)
                    ).status_code == 200
                assert await database.visitor_events.count_documents({}) == 1
                for extra in (
                    {"eventId": str(uuid4())},
                    {
                        "eventId": str(uuid4()),
                        "kind": "click",
                        "target": "https://broker.example/private/secret?token=x",
                    },
                    {
                        "eventId": str(uuid4()),
                        "sessionId": str(uuid4()),
                        "source": "reddit",
                    },
                ):
                    r = await browser.post(
                        "/api/analytics/visit", json={**base, **extra}
                    )
                    assert r.status_code == 200, r.text
                b = {
                    **base,
                    "eventId": str(uuid4()),
                    "visitorId": str(uuid4()),
                    "sessionId": str(uuid4()),
                    "ref": "CODE-B",
                }
                assert (
                    await browser.post("/api/analytics/visit", json=b)
                ).status_code == 200
                await browser.post(
                    "/api/analytics/visit",
                    json={**b, "eventId": str(uuid4())},
                    headers={"DNT": "1"},
                )
                await browser.post(
                    "/api/analytics/visit",
                    json={**b, "eventId": str(uuid4())},
                    headers={"Sec-GPC": "1"},
                )
                await browser.post(
                    "/api/analytics/visit",
                    json={**b, "eventId": str(uuid4())},
                    headers={"User-Agent": "Googlebot"},
                )
                assert await database.visitor_events.count_documents({}) == 5
                rows = await database.visitor_events.find().to_list(10)
                serialized = json.dumps(rows, default=str)
                for private in (
                    "8.8.8.8",
                    "do-not-store",
                    "/private/secret",
                    "password=",
                    visitor,
                    session,
                ):
                    assert private not in serialized
                assert all(row["country"] == "US" for row in rows)
                request = SimpleNamespace(
                    headers={"x-kaos-visitor": visitor, "x-kaos-session": session}
                )
                acquisition = await analytics.acquisition_for(request)
                assert (
                    acquisition["source"] == "email"
                    and acquisition["refCode"] == "CODE-A"
                    and acquisition["country"] == "US"
                )
                await database.users.insert_many(
                    [
                        {
                            "id": "trial-a",
                            "email": "private-trial@example.com",
                            "username": "trial_member",
                            "referredByCode": "CODE-A",
                            "created_at": now.isoformat(),
                            "membership_status": "TRIAL",
                            "membership_plan": "pro",
                            "membership_expires_at": ends,
                            "stripe_subscription_id": "sub_trial",
                            "analyticsAcquisition": acquisition,
                        },
                        {
                            "id": "paid-a",
                            "email": "private-paid@example.com",
                            "username": "paid_member",
                            "referredByCode": "CODE-A",
                            "created_at": now.isoformat(),
                            "membership_status": "ACTIVE",
                            "membership_plan": "ultimate",
                            "membership_expires_at": ends,
                            "stripe_subscription_id": "sub_paid",
                            "analyticsAcquisition": acquisition,
                        },
                        {
                            "id": "paid-b",
                            "email": "other@example.com",
                            "username": "other_member",
                            "referredByCode": "CODE-B",
                            "created_at": now.isoformat(),
                            "membership_status": "ACTIVE",
                            "membership_plan": "pro",
                            "membership_expires_at": ends,
                            "stripe_subscription_id": "sub_other",
                        },
                    ]
                )
                assert (await browser.get("/api/admin/analytics")).status_code == 401
                assert (
                    await browser.get(
                        "/api/admin/analytics", headers={"authorization": "a"}
                    )
                ).status_code == 403
                assert (
                    await browser.get(
                        "/api/admin/analytics", headers={"authorization": "mod"}
                    )
                ).status_code == 403
                own = await browser.get(
                    "/api/affiliate/analytics?affiliate=CODE-B",
                    headers={"authorization": "a"},
                )
                assert own.status_code == 200, own.text
                data = own.json()
                s = data["summary"]
                assert (
                    s["pageviews"] == 3
                    and s["navigationClicks"] == 1
                    and s["referralClicks"] == 2
                )
                assert s["uniqueVisitors"] == 1 and s["visits"] == 2
                assert (
                    s["newAccounts"] == 2
                    and s["trialMembers"] == 1
                    and s["paidMembers"] == 1
                )
                assert len(data["members"]) == 2 and {
                    u["id"] for u in data["members"]
                } == {"trial-a", "paid-a"}
                assert (
                    "private-paid@example.com" not in own.text
                    and "paid-b" not in own.text
                    and "CODE-B" not in own.text
                )
                assert own.headers["cache-control"] == "private, no-store"
                all_visits = await browser.get(
                    "/api/admin/analytics", headers={"authorization": "admin"}
                )
                assert all_visits.json()["summary"]["pageviews"] == 4
                assert all_visits.json()["summary"]["paidMembers"] == 2
                scoped = await browser.get(
                    "/api/admin/analytics?affiliate=CODE-B&location=US&source=email",
                    headers={"authorization": "admin"},
                )
                assert scoped.json()["summary"]["referralClicks"] == 1
                assert (
                    scoped.json()["summary"]["paidMembers"] == 0
                )  # Old account has no geographic acquisition; never invent one.
                assert (
                    await browser.get(
                        "/api/affiliate/analytics?days=500",
                        headers={"authorization": "a"},
                    )
                ).status_code == 422
                counts = await database.affiliate_click_totals.find(
                    {"code": "CODE-A"}
                ).to_list(10)
                assert sum(c["clicks"] for c in counts) == 2
                indexes = await database.visitor_events.index_information()
                assert indexes["expiresAt_1"]["expireAfterSeconds"] == 0
        finally:
            await client.drop_database(database.name)
            client.close()

    asyncio.run(scenario())
