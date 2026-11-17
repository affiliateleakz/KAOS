"""Unvalidated research model must never become a public/member pretrained bundle."""
import hashlib
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth import get_current_user
import routes_research_models as models


def test_research_model_requires_owner_authentication_and_never_enables_orders():
    app=FastAPI();app.include_router(models.router)
    with TestClient(app) as client:
        endpoint='/api/v1/ai/research/micro-reversion'
        assert client.get(endpoint).status_code==401
        for role in ('user','admin'):
            app.dependency_overrides[get_current_user]=lambda role=role:{'id':'member','role':role,'membership_plan':'ultimate'}
            assert client.get(endpoint).status_code==403
        app.dependency_overrides[get_current_user]=lambda:{'id':'owner','role':'super_admin'}
        response=client.get(endpoint)
        assert response.status_code==200 and response.headers['cache-control']=='private, no-store'
        data=response.json()
        assert data['state']=='failed_adverse_fill_gate'
        assert data['executionEnabled'] is False and data['publishedMemberModel'] is False
        assert data['model']['features'].__len__()==12 and len(data['model']['trees'])==80
        assert 'token' not in data and 'owner' not in data


def test_packaged_research_artifact_matches_frozen_model():
    root=Path(__file__).resolve().parents[2]
    packaged=Path(models.__file__).parent/'research_models/micro_reversion_v1.json'
    source=root/'research/crypto_strategy_v1/browser_model.json'
    assert hashlib.sha256(packaged.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
    model=json.loads(packaged.read_text())
    assert model['executionEnabled'] is False and model['researchOnly'] is True
