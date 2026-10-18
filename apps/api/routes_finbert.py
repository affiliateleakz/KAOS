"""Authenticated FinBERT shadow analysis; no trading/execution endpoint."""
import asyncio
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from auth import get_current_user
from db import db
from services_trading import get_entitlements
from kaos_finbert import score_headline

router = APIRouter(prefix='/api/v1/ai/finbert', tags=['finbert-shadow'])

class NewsItem(BaseModel):
    headline: str = Field(min_length=1, max_length=2000)
    market: str = Field(min_length=1, max_length=40)
    published_at: datetime
    observed_at: datetime

@router.get('/status')
async def status(user=Depends(get_current_user)):
    return {'enabled': os.getenv('KAOS_FINBERT_ENABLED') == 'enabled', 'mode': 'SHADOW_ONLY', 'model': 'ProsusAI/finbert'}

@router.post('/analyze')
async def analyze(payload: NewsItem, request: Request, user=Depends(get_current_user)):
    if not request.headers.get('authorization', '').startswith('Bearer '):
        raise HTTPException(403, 'Bearer authorization required')
    if user.get('account_status', 'active') != 'active' or user.get('membership_status') not in ('ACTIVE', 'TRIAL'):
        raise HTTPException(403, 'Active membership required')
    if not (await get_entitlements(user)).get('botAccess'):
        raise HTTPException(403, 'Bot access required')
    if os.getenv('KAOS_FINBERT_ENABLED') != 'enabled':
        raise HTTPException(503, 'FinBERT is disabled')
    try:
        result = await asyncio.to_thread(score_headline, payload.headline, payload.published_at, payload.observed_at, payload.market)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'FinBERT model unavailable') from exc
    # Unique event key per user; don't overwrite original observation time or future-leak data.
    await db.kaos_finbert_shadow.update_one(
        {'_id': user['id'] + ':' + result['event_id']},
        {'$setOnInsert': {'user_id': user['id'], **result}}, upsert=True,
    )
    return result
