"""Explicit admin installation of original backtested research drafts. Never overwrites edits."""
import base64
import json
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5,uuid4
from fastapi import APIRouter,Depends
from pymongo.errors import DuplicateKeyError
from auth import require_role
from db import db,now_iso

router=APIRouter(tags=['TradingView Pine starter pack'])
ASSETS=Path(__file__).resolve().parent/'pine_starter_pack'
TITLES={'trend':'Trend Forge','reclaim':'Band Reclaim','breakout':'Breakout Sentinel'}


@router.post('/api/admin/pine-scripts/starter-pack')
async def install(user:dict=Depends(require_role('admin'))):
    created=[];skipped=[]
    for rule,title in TITLES.items():
        identity=uuid5(NAMESPACE_URL,'https://tradingwithkaos.com/pine-pack/v1/'+rule).hex
        if await db.pine_scripts.find_one({'_id':identity}):skipped.append(title);continue
        report=json.loads((ASSETS/(rule+'.results.json')).read_text())
        later=[r for r in report['results'] if r['period']=='later' and r['stress']==1]
        results='; '.join(f"{r['symbol']}: {r['return_pct']:+.2f}% ({r['trades']} trades)" for r in later)
        description=(f'KAOS Strategy — {title}. Original Pine v6 long-only research template with gold/teal chart styling, regime ribbon, ATR brackets, setup alerts and a status panel.\n\n'
          'RESEARCH DRAFT: backtests did not establish a robust edge. Not a proven profitable strategy or recommendation.\n'
          'Chronological 2026 evaluation, hourly candles, 10% equity per entry, no leverage. Retail crypto fee assumption: 0.4% each side plus 2 bps slippage. ETF commission assumption: zero plus 2 bps slippage.\n'
          f'Net sleeve returns: {results}. Sample ends 2026-10-31; data also used in prior KAOS research, so this is not pristine unseen holdout data.\n\n'
          'Setup: open TradingView → Pine Editor → paste the source → Save → Add to chart → Strategy Tester. Begin with a 1-hour chart. Set actual fees/slippage and your evaluation dates in Properties/Inputs. Pine slippage is ticks; the Python study uses basis points, so fills will differ.\n'
          'Python rules were backtested; this Pine source has not been compiled/executed in TradingView. Validate compilation and Strategy Tester behavior before publishing. No live trades were placed.\n'
          'Use alerts for closed-bar setups or strategy order fills; this script does not connect a brokerage account. MIT license; preserve attribution. No options/binary or forex performance claims.')
        now=now_iso()
        row={'_id':identity,'id':identity,'title':'KAOS Strategy — '+title,'description':description,
             'kind':'strategy','market':'Stocks / crypto research','timeframe':'1h','source':(ASSETS/(rule+'.pine')).read_text(),
             'thumbnail':'data:image/jpeg;base64,'+base64.b64encode((ASSETS/(rule+'.jpg')).read_bytes()).decode(),
             'status':'draft','official':True,'featured':False,'author_id':user['id'],'author_name':'KAOS Official',
             'created_at':now,'updated_at':now,'revision':uuid4().hex,'rights_confirmed_at':now,
             'moderation_note':'Keep as research draft until Pine compilation and performance review are complete.',
             'trail':[{'actor_id':user['id'],'at':now,'status':'draft','action':'install-original-pack-v1'}]}
        try:await db.pine_scripts.insert_one(row);created.append(title)
        except DuplicateKeyError:skipped.append(title)
    return {'created':created,'skipped':skipped,'message':'Original KAOS research drafts installed. Existing scripts were not overwritten.'}
