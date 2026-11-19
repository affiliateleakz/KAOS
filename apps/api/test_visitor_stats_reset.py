"""Local-only exclusion/reset authorization checks; no customer data or deletion."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import visitor_analytics as analytics
from auth import get_current_user,get_optional_user


@pytest.mark.parametrize('role',['admin','super_admin','moderator'])
def test_staff_visits_never_touch_tracking_collections(monkeypatch,role):
    monkeypatch.setattr(analytics,'db',object())
    app=FastAPI();app.include_router(analytics.router)
    app.dependency_overrides[get_optional_user]=lambda:{'id':'staff','role':role}
    with TestClient(app) as client:
        response=client.post('/api/analytics/visit',json={'eventId':str(uuid4()),'visitorId':str(uuid4()),'sessionId':str(uuid4()),'path':'/','kind':'pageview'})
    assert response.status_code==200 and response.json()=={'recorded':False}


def test_reset_is_owner_only_and_writes_only_display_baseline(monkeypatch):
    settings=SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(analytics,'db',SimpleNamespace(settings=settings))
    app=FastAPI();app.include_router(analytics.router)
    app.dependency_overrides[get_current_user]=lambda:{'id':'other','role':'user'}
    with TestClient(app) as client:
        assert client.post('/api/admin/analytics/reset').status_code==403
        settings.update_one.assert_not_awaited()
        app.dependency_overrides[get_current_user]=lambda:{'id':'owner','role':'super_admin'}
        response=client.post('/api/admin/analytics/reset')
        assert response.status_code==200 and response.json()['resetAt']
    query,update=settings.update_one.await_args.args
    assert query=={'_id':'visitor_analytics_display_reset'}
    assert update['$set']['resetBy']=='owner'
    assert 'resetAt' in update['$set']
